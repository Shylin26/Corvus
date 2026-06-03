from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from core.config import settings
from core.envelope import CorvusEnvelope
from core.events import AgentID, EventType
from core.kafka_client import CorvusProducer
from orchestrator.main import incidents, pending_approvals, Orchestrator

log = logging.getLogger(__name__)
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [GATEWAY] %(levelname)s %(message)s",
)

orchestrator: Orchestrator | None = None
producer: CorvusProducer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator, producer
    producer = CorvusProducer()
    orchestrator = Orchestrator()
    asyncio.create_task(orchestrator.run())
    log.info("Gateway started")
    yield
    if producer:
        producer.flush()


app = FastAPI(title="Corvus Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "incidents": len(incidents)}


@app.get("/incidents")
def get_incidents():
    result = []
    for k, v in incidents.items():
        item = {"incident_id": k, **v}
        if hasattr(item.get("started_at"), "isoformat"):
            item["started_at"] = item["started_at"].isoformat()
        if "plan" in item:
            item.pop("plan")
        result.append(item)
    return result


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    incident = incidents.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"incident_id": incident_id, **incident}


@app.get("/approvals/pending")
def get_pending_approvals():
    if not orchestrator:
        return []
    return orchestrator.list_pending()


@app.post("/approvals/{plan_id}/approve")
def approve_plan(plan_id: str):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    success = orchestrator.approve(plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"ok": True, "plan_id": plan_id}


@app.post("/approvals/{plan_id}/reject")
def reject_plan(plan_id: str, body: dict = {}):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    success = orchestrator.reject(plan_id, body.get("note", ""))
    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"ok": True, "plan_id": plan_id}


@app.post("/internal/metrics")
async def push_metric(payload: dict):
    global producer
    if not producer:
        raise HTTPException(status_code=503, detail="Producer not ready")
    try:
        envelope = CorvusEnvelope(
            type=EventType.METRIC,
            source=AgentID.SYSTEM,
            target=AgentID.OBSERVER,
            incident_id=f"metric-{uuid.uuid4().hex[:8]}",
            payload=payload,
        )
        producer.emit(settings.topic_metrics, envelope)
        producer.flush(timeout=2.0)
        return {"ok": True}
    except Exception as e:
        log.error("Failed to push metric: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stream/incidents")
async def stream_incidents():
    async def event_generator():
        last_count = 0
        while True:
            await asyncio.sleep(1)
            current = list(incidents.items())
            if len(current) != last_count:
                last_count = len(current)
                data = [
                    {
                        "incident_id": k,
                        "status":  v.get("status"),
                        "service": v.get("service"),
                    }
                    for k, v in current
                ]
                yield {"data": json.dumps(data)}
    return EventSourceResponse(event_generator())

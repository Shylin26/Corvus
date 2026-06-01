from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from core.config import settings

log = logging.getLogger(__name__)
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [GATEWAY] %(levelname)s %(message)s",
)

# In-memory store — shared with orchestrator via import in full version
# For MVP the gateway holds its own view of state
from orchestrator.main import incidents, pending_approvals, Orchestrator

orchestrator: Orchestrator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    orchestrator = Orchestrator()
    asyncio.create_task(orchestrator.run())
    log.info("Orchestrator started inside gateway")
    yield


app = FastAPI(title="Corvus Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Incidents ─────────────────────────────────────────────

@app.get("/incidents")
def get_incidents():
    return [
        {"incident_id": k, **v, "started_at": v.get("started_at", "").isoformat()
         if hasattr(v.get("started_at", ""), "isoformat") else v.get("started_at", "")}
        for k, v in incidents.items()
    ]


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    incident = incidents.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"incident_id": incident_id, **incident}


# ── Approvals ─────────────────────────────────────────────

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
        raise HTTPException(status_code=404, detail="Plan not found or already processed")
    return {"ok": True, "plan_id": plan_id}


@app.post("/approvals/{plan_id}/reject")
def reject_plan(plan_id: str, body: dict = {}):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    note = body.get("note", "")
    success = orchestrator.reject(plan_id, note)
    if not success:
        raise HTTPException(status_code=404, detail="Plan not found or already processed")
    return {"ok": True, "plan_id": plan_id}


# ── Metrics push (services → gateway → Kafka) ─────────────

@app.post("/internal/metrics")
async def push_metric(payload: dict):
    from core.envelope import CorvusEnvelope
    from core.events import AgentID, EventType
    from core.kafka_client import CorvusProducer
    import uuid

    try:
        producer = CorvusProducer()
        envelope = CorvusEnvelope(
            type=EventType.METRIC,
            source=AgentID.SYSTEM,
            target=AgentID.OBSERVER,
            incident_id=f"metric-{uuid.uuid4().hex[:8]}",
            payload=payload,
        )
        producer.emit(settings.topic_metrics, envelope)
        return {"ok": True}
    except Exception as e:
        log.error("Failed to push metric: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── SSE stream (frontend live updates) ────────────────────

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
                    {"incident_id": k, "status": v.get("status"), "service": v.get("service")}
                    for k, v in current
                ]
                yield {"data": json.dumps(data)}
    return EventSourceResponse(event_generator())


# ── Health ────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "incidents": len(incidents)}

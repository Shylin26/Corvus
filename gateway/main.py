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
from memory.incidents import load_incidents

log = logging.getLogger(__name__)
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [GATEWAY] %(levelname)s %(message)s",
)

producer: CorvusProducer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    producer = CorvusProducer()
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
    return {"status": "ok"}


@app.get("/incidents")
async def get_incidents():
    incidents = await load_incidents()
    return [
        {"incident_id": k, **v}
        for k, v in incidents.items()
    ]


@app.get("/approvals/pending")
async def get_pending_approvals():
    try:
        import asyncpg
        conn = await asyncpg.connect(
            settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        )
        rows = await conn.fetch(
            "SELECT id, incident_id, plan_id, reason, expires_at, plan_json FROM approvals WHERE status='pending'"
        )
        await conn.close()
        return [
            {
                "plan_id":     row["plan_id"],
                "incident_id": row["incident_id"],
                "reason":      row["reason"],
                "expires_at":  row["expires_at"].isoformat(),
                "plan_label":  json.loads(row["plan_json"]).get("label", ""),
                "risk_score":  json.loads(row["plan_json"]).get("risk_score", 1.0),
            }
            for row in rows
        ]
    except Exception as e:
        log.error("Failed to load approvals: %s", e)
        return []


@app.post("/approvals/{plan_id}/approve")
async def approve_plan(plan_id: str):
    try:
        import asyncpg
        conn = await asyncpg.connect(
            settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        )
        await conn.execute(
            "UPDATE approvals SET status='approved', responded_at=NOW() WHERE plan_id=$1",
            plan_id
        )
        await conn.close()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/approvals/{plan_id}/reject")
async def reject_plan(plan_id: str, body: dict = {}):
    try:
        import asyncpg
        conn = await asyncpg.connect(
            settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        )
        await conn.execute(
            "UPDATE approvals SET status='rejected', note=$1, responded_at=NOW() WHERE plan_id=$2",
            body.get("note", ""), plan_id
        )
        await conn.close()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stream/incidents")
async def stream_incidents():
    async def event_generator():
        last_snapshot = None
        while True:
            await asyncio.sleep(2)
            try:
                incidents = await load_incidents()
                data = [
                    {"incident_id": k, "status": v.get("status"), "service": v.get("service")}
                    for k, v in incidents.items()
                ]
                snapshot = json.dumps(data, sort_keys=True)
                if snapshot != last_snapshot:
                    last_snapshot = snapshot
                    yield {"data": snapshot}
            except Exception as e:
                log.error("SSE error: %s", e)
    return EventSourceResponse(event_generator())

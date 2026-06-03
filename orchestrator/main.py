from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from core.config import settings
from core.envelope import CorvusEnvelope, ActionPayload
from core.events import AgentID, EventType, IncidentStatus
from core.kafka_client import CorvusConsumer, CorvusProducer
from memory.incidents import upsert_incident, load_incidents

log = logging.getLogger(__name__)
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [ORCHESTRATOR] %(levelname)s %(message)s",
)

incidents: dict[str, dict] = {}
pending_approvals: dict[str, dict] = {}


class Orchestrator:
    def __init__(self) -> None:
        self.producer = CorvusProducer()
        self.consumer = CorvusConsumer(
            topics=[
                settings.topic_diagnosis,
                settings.topic_plan,
                settings.topic_result,
            ],
            group_id="orchestrator",
        )

    async def load(self) -> None:
        global incidents
        incidents = await load_incidents()
        log.info("Loaded %d incidents from Postgres", len(incidents))

    async def run(self) -> None:
        await self.load()
        log.info("Orchestrator started")
        asyncio.create_task(self._approval_watchdog())
        async for envelope in self.consumer:
            try:
                await self._handle(envelope)
            except Exception as e:
                log.error("Error handling %s: %s", envelope.type, e)

    async def _handle(self, envelope: CorvusEnvelope) -> None:
        incident_id = envelope.incident_id

        # Store event trace for chat interface
        asyncio.create_task(self._store_trace(envelope))

        if envelope.type == EventType.DIAGNOSIS:
            payload = envelope.typed_payload()
            incidents[incident_id] = {
                "status":     IncidentStatus.DIAGNOSING,
                "service":    payload.affected[0] if payload.affected else "unknown",
                "root_cause": payload.root_cause,
                "confidence": payload.confidence,
                "started_at": datetime.now(timezone.utc),
            }
            await upsert_incident(incident_id, incidents[incident_id])
            log.info("Incident %s — diagnosis received (confidence=%.2f)",
                     incident_id, payload.confidence)

        elif envelope.type == EventType.PLAN:
            payload = envelope.typed_payload()
            incidents.setdefault(incident_id, {})
            incidents[incident_id]["status"] = IncidentStatus.PLANNING
            incidents[incident_id]["plan"]   = payload.plans[0]

            if payload.auto_approve and not payload.uncertain:
                log.info("Incident %s — auto-approving plan '%s'",
                         incident_id, payload.plans[0].label)
                await self._dispatch(envelope, payload.plans[0])
            else:
                reason = "uncertain diagnosis" if payload.uncertain else "high risk score"
                log.warning("Incident %s — plan requires human approval (%s)",
                            incident_id, reason)
                incidents[incident_id]["status"] = IncidentStatus.AWAITING_APPROVAL
                pending_approvals[payload.plans[0].plan_id] = {
                    "incident_id": incident_id,
                    "plan":        payload.plans[0],
                    "envelope":    envelope,
                    "reason":      reason,
                    "expires_at":  datetime.now(timezone.utc) + timedelta(minutes=30),
                }
            await upsert_incident(incident_id, incidents[incident_id])

        elif envelope.type == EventType.INCIDENT_DONE:
            payload = envelope.typed_payload()
            status = IncidentStatus.RESOLVED if payload.resolved else IncidentStatus.ROLLED_BACK
            if incident_id in incidents:
                incidents[incident_id]["status"] = status
                await upsert_incident(incident_id, incidents[incident_id])
            log.info("Incident %s — %s", incident_id, status)

    async def _store_trace(self, envelope) -> None:
        try:
            import asyncpg, json
            conn = await asyncpg.connect(
                settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
            )
            await conn.execute(
                "INSERT INTO event_trace (incident_id, envelope_id, event_type, source, target, payload, trace) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT DO NOTHING",
                envelope.incident_id, envelope.id, str(envelope.type),
                str(envelope.source), str(envelope.target),
                json.dumps(envelope.payload), json.dumps(envelope.trace),
            )
            await conn.close()
        except Exception as e:
            pass

    async def _dispatch(self, envelope: CorvusEnvelope, plan) -> None:
        incident_id = envelope.incident_id
        incidents[incident_id]["status"] = IncidentStatus.EXECUTING
        await upsert_incident(incident_id, incidents[incident_id])

        action_envelope = envelope.append_trace(
            AgentID.ORCHESTRATOR,
            f"Dispatching plan '{plan.label}' to executor"
        ).forward_to(
            target=AgentID.EXECUTOR,
            source=AgentID.ORCHESTRATOR,
        )
        action_envelope = action_envelope.model_copy(update={
            "type": EventType.ACTION,
            "payload": ActionPayload(
                plan=plan,
                approved_by=AgentID.ORCHESTRATOR,
            ).model_dump(),
        })
        self.producer.emit(settings.topic_action, action_envelope)
        self.producer.flush()
        log.info("Incident %s — ActionEvent dispatched", incident_id)

    async def _approval_watchdog(self) -> None:
        while True:
            await asyncio.sleep(30)
            now = datetime.now(timezone.utc)
            for plan_id, approval in list(pending_approvals.items()):
                if now > approval["expires_at"]:
                    log.warning("Approval expired for plan %s", plan_id)
                    pending_approvals.pop(plan_id, None)
                    incident_id = approval["incident_id"]
                    if incident_id in incidents:
                        incidents[incident_id]["status"] = IncidentStatus.FAILED
                        await upsert_incident(incident_id, incidents[incident_id])

    def approve(self, plan_id: str, approver: str = "human") -> bool:
        approval = pending_approvals.pop(plan_id, None)
        if not approval:
            return False
        asyncio.create_task(self._dispatch(approval["envelope"], approval["plan"]))
        return True

    def reject(self, plan_id: str, note: str = "") -> bool:
        approval = pending_approvals.pop(plan_id, None)
        if not approval:
            return False
        incident_id = approval["incident_id"]
        incidents[incident_id]["status"] = IncidentStatus.FAILED
        asyncio.create_task(upsert_incident(incident_id, incidents[incident_id]))
        return True

    def list_pending(self) -> list[dict]:
        return [
            {
                "plan_id":     plan_id,
                "incident_id": a["incident_id"],
                "reason":      a["reason"],
                "expires_at":  a["expires_at"].isoformat(),
                "plan_label":  a["plan"].label,
                "risk_score":  a["plan"].risk_score,
            }
            for plan_id, a in pending_approvals.items()
        ]


async def main() -> None:
    orchestrator = Orchestrator()
    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())


async def _store_event_trace(conn, incident_id: str, envelope) -> None:
    import json as _json
    try:
        await conn.execute(
            """
            INSERT INTO event_trace (incident_id, envelope_id, event_type, source, target, payload, trace)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT DO NOTHING
            """,
            incident_id,
            envelope.id,
            envelope.type.value,
            envelope.source.value,
            envelope.target.value,
            _json.dumps(envelope.payload),
            _json.dumps(envelope.trace),
        )
    except Exception as e:
        pass

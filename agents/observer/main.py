"""
Observer Agent
- Consumes metrics from corvus.metrics
- Runs Z-score anomaly detection
- Emits AnomalyEvent to corvus.anomaly within 500ms SLA
"""
import asyncio
import logging
import time
import uuid

from core.config import settings
from core.envelope import CorvusEnvelope
from core.events import AgentID, AnomalySeverity, EventType
from core.kafka_client import CorvusConsumer, CorvusProducer
from agents.observer.detector import AnomalyDetector

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [OBSERVER] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


class ObserverAgent:
    def __init__(self) -> None:
        self.detector  = AnomalyDetector()
        self.producer  = CorvusProducer()
        self.consumer  = CorvusConsumer(
            topics=[settings.topic_metrics],
            group_id="observer-agent",
        )
        # track active incidents to avoid duplicate anomaly spam
        self._active: set[str] = set()

    async def run(self) -> None:
        log.info("Observer agent started — listening on %s", settings.topic_metrics)
        async for envelope in self.consumer:
            await self._handle(envelope)

    async def _handle(self, envelope: CorvusEnvelope) -> None:
        if envelope.type != EventType.METRIC:
            return

        start = time.monotonic()

        p = envelope.typed_payload()
        anomaly = self.detector.ingest(p.service, p.metric, p.value)

        if anomaly is None:
            return

        # Deduplicate — don't spam the same service+metric
        dedup_key = f"{p.service}:{p.metric}"
        if dedup_key in self._active:
            log.debug("Suppressing duplicate anomaly for %s", dedup_key)
            return

        self._active.add(dedup_key)

        incident_id = f"inc-{uuid.uuid4().hex[:8]}"
        log.warning(
            "ANOMALY detected — service=%s metric=%s z=%.2f severity=%s incident=%s",
            anomaly["service"], anomaly["metric"],
            anomaly["z_score"], anomaly["severity"], incident_id,
        )

        anomaly_envelope = CorvusEnvelope(
            type=EventType.ANOMALY,
            source=AgentID.OBSERVER,
            target=AgentID.FORENSICS,
            incident_id=incident_id,
            payload=anomaly,
        ).append_trace(
            AgentID.OBSERVER,
            f"Detected {anomaly['severity']} anomaly on {p.service}/{p.metric} "
            f"(z={anomaly['z_score']}, value={anomaly['current_value']})",
        )

        self.producer.emit(settings.topic_anomaly, anomaly_envelope)
        self.producer.flush()

        elapsed_ms = (time.monotonic() - start) * 1000
        if elapsed_ms > settings.observer_emit_sla_ms:
            log.warning("SLA breach: anomaly emit took %.0fms (SLA=%dms)",
                        elapsed_ms, settings.observer_emit_sla_ms)
        else:
            log.info("Anomaly emitted in %.0fms (incident=%s)", elapsed_ms, incident_id)

    def clear_incident(self, service: str, metric: str) -> None:
        """Called by orchestrator when incident is resolved."""
        self._active.discard(f"{service}:{metric}")


async def main() -> None:
    agent = ObserverAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())

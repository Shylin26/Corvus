"""
Push a fake metric directly to Kafka — bypasses the HTTP services.
Use this when Docker services don't have ports exposed.

Usage:
    python scripts/push_metric.py --service order-service --metric cpu_percent --value 95
"""
import argparse
import uuid
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.envelope import CorvusEnvelope
from core.events import AgentID, EventType
from core.kafka_client import CorvusProducer
from core.config import settings


def push(service: str, metric: str, value: float, count: int = 15):
    producer = CorvusProducer()
    print(f"Pushing {count} metrics: {service}/{metric}={value}")

    # Push baseline first (normal values)
    for i in range(10):
        envelope = CorvusEnvelope(
            type=EventType.METRIC,
            source=AgentID.SYSTEM,
            target=AgentID.OBSERVER,
            incident_id=f"metric-{uuid.uuid4().hex[:8]}",
            payload={
                "service": service,
                "metric":  metric,
                "value":   40.0,   # normal baseline
                "unit":    "percent",
                "host":    service,
            },
        )
        producer.emit(settings.topic_metrics, envelope)

    # Push spike
    for i in range(count):
        envelope = CorvusEnvelope(
            type=EventType.METRIC,
            source=AgentID.SYSTEM,
            target=AgentID.OBSERVER,
            incident_id=f"metric-{uuid.uuid4().hex[:8]}",
            payload={
                "service": service,
                "metric":  metric,
                "value":   value,
                "unit":    "percent",
                "host":    service,
            },
        )
        producer.emit(settings.topic_metrics, envelope)

    producer.flush()
    print(f"Done — {count + 10} messages sent to {settings.topic_metrics}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", default="order-service")
    parser.add_argument("--metric",  default="cpu_percent")
    parser.add_argument("--value",   type=float, default=95.0)
    parser.add_argument("--count",   type=int, default=5)
    args = parser.parse_args()
    push(args.service, args.metric, args.value, args.count)

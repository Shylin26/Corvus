from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from confluent_kafka import Consumer, KafkaError, Producer

from core.config import settings
from core.envelope import CorvusEnvelope

log = logging.getLogger(__name__)


class CorvusProducer:
    def __init__(self) -> None:
        self._producer = Producer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "acks": "all",
            "retries": 5,
            "retry.backoff.ms": 200,
        })

    def emit(self, topic: str, envelope: CorvusEnvelope) -> None:
        self._producer.produce(
            topic,
            key=envelope.incident_id.encode(),
            value=envelope.to_kafka_bytes(),
            on_delivery=self._on_delivery,
        )
        self._producer.poll(0)

    def flush(self, timeout: float = 5.0) -> None:
        self._producer.flush(timeout)

    @staticmethod
    def _on_delivery(err, msg) -> None:
        if err:
            log.error("Kafka delivery failed: %s", err)
        else:
            log.debug("Delivered to %s [%d]", msg.topic(), msg.partition())


class CorvusConsumer:
    def __init__(
        self,
        topics: list[str],
        group_id: str,
        auto_offset_reset: str = "latest",
        poll_timeout: float = 1.0,
    ) -> None:
        self._consumer = Consumer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": auto_offset_reset,
            "enable.auto.commit": True,
        })
        self._consumer.subscribe(topics)
        self._poll_timeout = poll_timeout
        self._running = True
        log.info("Consumer subscribed to %s (group=%s)", topics, group_id)

    def stop(self) -> None:
        self._running = False

    def close(self) -> None:
        self._consumer.close()

    async def __aiter__(self) -> AsyncIterator[CorvusEnvelope]:
        loop = asyncio.get_running_loop()
        try:
            while self._running:
                msg = await loop.run_in_executor(
                    None, self._consumer.poll, self._poll_timeout
                )
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    log.error("Kafka error: %s", msg.error())
                    continue
                try:
                    envelope = CorvusEnvelope.from_kafka_bytes(msg.value())
                    yield envelope
                except Exception as exc:
                    log.error("Failed to deserialise message: %s", exc)
        finally:
            self.close()

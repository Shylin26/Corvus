from __future__ import annotations

import asyncio
import logging
import time

from core.config import settings
from core.envelope import CorvusEnvelope, IncidentDonePayload, StepResultPayload
from core.events import ActionType, AgentID, EventType
from core.kafka_client import CorvusConsumer, CorvusProducer

log = logging.getLogger(__name__)
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [EXECUTOR] %(levelname)s %(message)s",
)

SERVICE_CONTAINERS = {
    "api-gateway":          "corvus-api-gateway",
    "auth-service":         "corvus-auth",
    "order-service":        "corvus-order",
    "inventory-service":    "corvus-inventory",
    "notification-service": "corvus-notification",
}


class DockerActions:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            import docker
            self._client = docker.from_env()
        return self._client

    def restart_service(self, target: str) -> tuple[bool, str]:
        container_name = SERVICE_CONTAINERS.get(target)
        if not container_name:
            return False, f"Unknown service: {target}"
        try:
            container = self._get_client().containers.get(container_name)
            container.restart(timeout=10)
            return True, f"Restarted {container_name}"
        except Exception as e:
            return False, str(e)

    def flush_cache(self, target: str) -> tuple[bool, str]:
        try:
            import redis
            r = redis.from_url(settings.redis_url)
            r.flushdb()
            return True, f"Flushed cache for {target}"
        except Exception as e:
            return False, str(e)

    def notify(self, target: str, params: dict) -> tuple[bool, str]:
        message = params.get("message", "Alert triggered")
        log.warning("NOTIFY [%s]: %s", target, message)
        return True, f"Notified: {message}"

    def execute_step(self, action_type: str, target: str, params: dict) -> tuple[bool, str]:
        if action_type == ActionType.RESTART_SERVICE:
            return self.restart_service(target)
        elif action_type == ActionType.FLUSH_CACHE:
            return self.flush_cache(target)
        elif action_type == ActionType.NOTIFY:
            return self.notify(target, params)
        else:
            return False, f"Unsupported action: {action_type}"

    def compensate_step(self, action_type: str, target: str, params: dict) -> tuple[bool, str]:
        return True, f"No compensation needed for {action_type} on {target}"


class ExecutorAgent:
    def __init__(self) -> None:
        self.producer = CorvusProducer()
        self.consumer = CorvusConsumer(
            topics=[settings.topic_action],
            group_id="executor-agent",
        )
        self.actions = DockerActions()

    async def run(self) -> None:
        log.info("Executor agent started — listening on %s", settings.topic_action)
        async for envelope in self.consumer:
            try:
                await self._handle(envelope)
            except Exception as e:
                log.error("Error in executor: %s", e)

    async def _handle(self, envelope: CorvusEnvelope) -> None:
        if envelope.type != EventType.ACTION:
            return

        incident_id = envelope.incident_id
        payload     = envelope.typed_payload()
        plan        = payload.plan
        steps       = sorted(plan.steps, key=lambda s: s.order)

        log.info("Executing plan '%s' for incident %s (%d steps)",
                 plan.label, incident_id, len(steps))

        start         = time.monotonic()
        executed      = []
        rolled_back   = 0
        final_success = True

        for step in steps:
            log.info("Step %d/%d — %s on %s",
                     step.order, len(steps), step.action_type, step.target)

            loop = asyncio.get_running_loop()
            success, output = await loop.run_in_executor(
                None,
                lambda s=step: self.actions.execute_step(
                    s.action_type, s.target, s.params
                )
            )

            step_envelope = envelope.append_trace(
                AgentID.EXECUTOR,
                f"Step {step.order} ({step.action_type} on {step.target}): "
                f"{'OK' if success else 'FAILED'} — {output}"
            ).forward_to(
                target=AgentID.ORCHESTRATOR,
                source=AgentID.EXECUTOR,
            )
            step_envelope = step_envelope.model_copy(update={
                "type": EventType.STEP_RESULT,
                "payload": StepResultPayload(
                    plan_id=plan.plan_id,
                    step=step,
                    success=success,
                    output=output if success else "",
                    error="" if success else output,
                ).model_dump(),
            })
            self.producer.emit(settings.topic_result, step_envelope)

            if success:
                executed.append(step)
                log.info("Step %d succeeded: %s", step.order, output)
                await asyncio.sleep(2)
            else:
                log.error("Step %d failed: %s — rolling back", step.order, output)
                final_success = False
                for prev_step in reversed(executed):
                    log.info("Rolling back step %d", prev_step.order)
                    _, comp_output = await loop.run_in_executor(
                        None,
                        lambda s=prev_step: self.actions.compensate_step(
                            s.action_type, s.target, s.compensate
                        )
                    )
                    rolled_back += 1
                break

        duration = time.monotonic() - start
        done_envelope = envelope.append_trace(
            AgentID.EXECUTOR,
            f"Incident {'resolved' if final_success else 'rolled back'} in {duration:.1f}s"
        ).forward_to(
            target=AgentID.ORCHESTRATOR,
            source=AgentID.EXECUTOR,
        )
        done_envelope = done_envelope.model_copy(update={
            "type": EventType.INCIDENT_DONE,
            "payload": IncidentDonePayload(
                resolved=final_success,
                rolled_back=not final_success,
                steps_executed=len(executed),
                steps_rolled_back=rolled_back,
                duration_seconds=round(duration, 2),
            ).model_dump(),
        })
        self.producer.emit(settings.topic_result, done_envelope)
        self.producer.flush()

        log.info("Incident %s complete — resolved=%s steps=%d duration=%.1fs",
                 incident_id, final_success, len(executed), duration)


async def main() -> None:
    agent = ExecutorAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())

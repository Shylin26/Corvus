from __future__ import annotations

import asyncio
import json
import logging

import httpx
import ollama

from memory.store import search_runbooks

from core.config import settings
from core.envelope import CorvusEnvelope, DiagnosisPayload, PlanPayload, PlanStep, RemedPlan
from core.events import AgentID, EventType
from core.kafka_client import CorvusConsumer, CorvusProducer

log = logging.getLogger(__name__)
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [FORENSICS] %(levelname)s %(message)s",
)

SYSTEM_PROMPT = """
You are Corvus Forensics — a senior site reliability engineer AI.
You receive anomaly data, recent service logs, and past runbooks.
Your job: diagnose the root cause and propose a remediation plan.

You MUST respond with ONLY valid JSON in this exact structure — no preamble, no markdown:

{
  "root_cause": "one sentence describing why the service is broken",
  "confidence": 0.85,
  "affected": ["service-a", "service-b"],
  "evidence": ["log line or metric that supports your diagnosis"],
  "recommended_actions": ["action 1", "action 2"],
  "plans": [
    {
      "label": "short plan name",
      "rationale": "why this plan",
      "risk_score": 0.2,
      "steps": [
        {
          "order": 1,
          "action_type": "RESTART_SERVICE",
          "target": "order-service",
          "params": {},
          "risk": 0.2,
          "compensate": {}
        }
      ]
    }
  ]
}

action_type must be one of:
RESTART_SERVICE, SCALE_SERVICE, REROUTE_TRAFFIC, FLUSH_CACHE, RESET_CONNECTIONS, NOTIFY

risk_score and risk are floats between 0.0 (safe) and 1.0 (dangerous).
confidence is a float between 0.0 (uncertain) and 1.0 (certain).
Provide 1-3 plans ranked from safest to riskiest.
"""

SERVICE_PORTS = {
    "api-gateway":          3001,
    "auth-service":         3002,
    "order-service":        3003,
    "inventory-service":    3004,
    "notification-service": 3005,
}


def build_prompt(anomaly: dict, logs: list[str], runbooks: list[dict]) -> str:
    anomaly_block = (
        f"SERVICE:  {anomaly['service']}\n"
        f"METRIC:   {anomaly['metric']}\n"
        f"VALUE:    {anomaly['current_value']} (normal: {anomaly['baseline_mean']:.1f} ± {anomaly['baseline_std']:.1f})\n"
        f"Z-SCORE:  {anomaly['z_score']}\n"
        f"SEVERITY: {anomaly['severity']}\n"
    )
    log_block = "\n".join(logs[:30]) if logs else "No logs available."
    if runbooks:
        rb_block = "\n\n".join(
            f"Past incident: {rb['title']}\n"
            f"Root cause: {rb['root_cause']}\n"
            f"Resolution: {rb['resolution']}"
            for rb in runbooks[:2]
        )
    else:
        rb_block = "No similar past incidents found."
    return (
        f"=== ANOMALY ===\n{anomaly_block}\n\n"
        f"=== RECENT LOGS ===\n{log_block}\n\n"
        f"=== SIMILAR PAST INCIDENTS ===\n{rb_block}\n\n"
        f"Diagnose the root cause and produce a remediation plan."
    )


async def fetch_logs(service: str, lines: int = 30) -> list[str]:
    port = SERVICE_PORTS.get(service)
    if not port:
        return []
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"http://localhost:{port}/logs?lines={lines}")
            r.raise_for_status()
            return r.json().get("logs", [])
    except Exception as e:
        log.warning("Could not fetch logs from %s: %s", service, e)
        return [f"[log fetch failed: {e}]"]


async def call_llm(prompt: str) -> dict | None:
    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: ollama.chat(
                model=settings.ollama_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                options={"temperature": 0.1},
            )
        )
        raw = response.message.content.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])
        return json.loads(raw)
    except json.JSONDecodeError as e:
        log.error("LLM returned invalid JSON: %s", e)
        return None
    except Exception as e:
        log.error("LLM call failed: %s", e)
        return None


def parse_llm_response(data: dict) -> tuple[DiagnosisPayload, PlanPayload] | None:
    try:
        diagnosis = DiagnosisPayload(
            root_cause=data["root_cause"],
            confidence=float(data["confidence"]),
            affected=data.get("affected", []),
            evidence=data.get("evidence", []),
            recommended_actions=data.get("recommended_actions", []),
        )
        plans = []
        for p in data.get("plans", []):
            steps = [
                PlanStep(
                    order=s["order"],
                    action_type=s["action_type"],
                    target=s["target"],
                    params=s.get("params", {}),
                    risk=float(s["risk"]),
                    compensate=s.get("compensate", {}),
                )
                for s in p["steps"]
            ]
            plans.append(RemedPlan(
                label=p["label"],
                rationale=p["rationale"],
                risk_score=float(p["risk_score"]),
                steps=steps,
            ))
        plans.sort(key=lambda p: p.risk_score)
        best_risk = plans[0].risk_score if plans else 1.0
        auto_approve = (
            best_risk < settings.planner_auto_approve_threshold
            and diagnosis.confidence >= settings.forensics_min_confidence
        )
        plan_payload = PlanPayload(
            plans=plans,
            auto_approve=auto_approve,
            uncertain=diagnosis.confidence < settings.forensics_min_confidence,
        )
        return diagnosis, plan_payload
    except (KeyError, ValueError, TypeError) as e:
        log.error("Failed to parse LLM response: %s", e)
        return None


def make_fallback(anomaly: dict) -> tuple[DiagnosisPayload, PlanPayload]:
    diagnosis = DiagnosisPayload(
        root_cause="Unable to determine root cause — LLM call failed or returned invalid output.",
        confidence=0.0,
        affected=[anomaly["service"]],
        evidence=[f"Anomaly: {anomaly['metric']} = {anomaly['current_value']} (z={anomaly['z_score']})"],
        recommended_actions=["Manual investigation required"],
    )
    plan = PlanPayload(
        plans=[RemedPlan(
            label="Manual review",
            rationale="Automated diagnosis failed. Human review needed.",
            risk_score=1.0,
            steps=[PlanStep(
                order=1,
                action_type="NOTIFY",
                target=anomaly["service"],
                params={"message": "Automated diagnosis failed — manual review required"},
                risk=1.0,
            )],
        )],
        auto_approve=False,
        uncertain=True,
    )
    return diagnosis, plan


class ForensicsAgent:
    def __init__(self) -> None:
        self.producer = CorvusProducer()
        self.consumer = CorvusConsumer(
            topics=[settings.topic_anomaly],
            group_id="forensics-agent",
        )

    async def run(self) -> None:
        log.info("Forensics agent started — listening on %s", settings.topic_anomaly)
        async for envelope in self.consumer:
            try:
                await self._handle(envelope)
            except Exception as e:
                log.error("Unhandled error processing incident %s: %s",
                          envelope.incident_id, e)

    async def _handle(self, envelope: CorvusEnvelope) -> None:
        if envelope.type != EventType.ANOMALY:
            return

        incident_id = envelope.incident_id
        log.info("Processing incident %s", incident_id)
        anomaly = envelope.typed_payload()

        logs = await fetch_logs(anomaly.service)
        runbooks = await search_runbooks(
            f"{anomaly.service} {anomaly.metric} {anomaly.severity}"
        )
        log.info("Runbook search: found %d similar past incidents", len(runbooks))

        prompt = build_prompt(anomaly.model_dump(), logs, runbooks)
        llm_result = await call_llm(prompt)

        if llm_result is not None:
            parsed = parse_llm_response(llm_result)
        else:
            parsed = None

        if parsed is not None:
            diagnosis_payload, plan_payload = parsed
        else:
            log.warning("Using fallback plan for incident %s", incident_id)
            diagnosis_payload, plan_payload = make_fallback(anomaly.model_dump())

        diagnosis_envelope = envelope.append_trace(
            AgentID.FORENSICS,
            f"Root cause: {diagnosis_payload.root_cause} "
            f"(confidence={diagnosis_payload.confidence:.2f})"
        ).forward_to(
            target=AgentID.ORCHESTRATOR,
            source=AgentID.FORENSICS,
        )
        diagnosis_envelope = diagnosis_envelope.model_copy(update={
            "type":    EventType.DIAGNOSIS,
            "payload": diagnosis_payload.model_dump(),
        })
        self.producer.emit(settings.topic_diagnosis, diagnosis_envelope)

        plan_envelope = envelope.append_trace(
            AgentID.FORENSICS,
            f"Generated {len(plan_payload.plans)} plan(s). "
            f"auto_approve={plan_payload.auto_approve}, "
            f"best_risk={plan_payload.plans[0].risk_score:.2f}"
        ).forward_to(
            target=AgentID.ORCHESTRATOR,
            source=AgentID.FORENSICS,
        )
        plan_envelope = plan_envelope.model_copy(update={
            "type":    EventType.PLAN,
            "payload": plan_payload.model_dump(),
        })
        self.producer.emit(settings.topic_plan, plan_envelope)
        self.producer.flush()

        log.info("Emitted diagnosis + plan for incident %s (auto_approve=%s)",
                 incident_id, plan_payload.auto_approve)


async def main() -> None:
    agent = ForensicsAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())

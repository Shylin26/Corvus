"""
LLM client — swap between Ollama (real) and Mock (fast dev mode).
Set LLM_MODE=mock in .env to use mock, LLM_MODE=ollama for real.
"""
import json
import logging
import asyncio

log = logging.getLogger(__name__)


async def call_llm(prompt: str, system: str) -> dict | None:
    from core.config import settings
    if settings.llm_mode == "mock":
        return _mock_response(prompt)
    return await _ollama_call(prompt, system)


def _mock_response(prompt: str) -> dict:
    """Instant hardcoded response for development — no Ollama needed."""
    service = "order-service"
    for word in ["api-gateway", "auth-service", "order-service",
                 "inventory-service", "notification-service"]:
        if word in prompt:
            service = word
            break
    return {
        "root_cause": f"CPU spike on {service} due to connection pool exhaustion under load",
        "confidence": 0.85,
        "affected": [service],
        "evidence": [f"CPU usage elevated on {service}", "Connection pool metrics degraded"],
        "recommended_actions": [f"Restart {service}", "Monitor connection pool"],
        "plans": [{
            "label": "Restart service",
            "rationale": "Restart clears connection pool and reduces CPU",
            "risk_score": 0.2,
            "steps": [{
                "order": 1,
                "action_type": "RESTART_SERVICE",
                "target": service,
                "params": {},
                "risk": 0.2,
                "compensate": {},
            }]
        }]
    }


async def _ollama_call(prompt: str, system: str) -> dict | None:
    import ollama
    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: ollama.chat(
                model="mistral:7b",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": prompt},
                ],
                options={"temperature": 0.1},
            )
        )
        raw = response.message.content.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])
        return json.loads(raw)
    except Exception as e:
        log.error("Ollama call failed: %s", e)
        return None

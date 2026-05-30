import os
import time
import random
import asyncio
import httpx
from fastapi import FastAPI
from contextlib import asynccontextmanager

SERVICE_NAME = os.getenv("SERVICE_NAME", "api-gateway")
METRICS_PUSH_URL = os.getenv("METRICS_PUSH_URL", "http://host.docker.internal:8000/internal/metrics")

# Fault state — chaos injector flips these
state = {
    "healthy": True,
    "cpu":     random.uniform(20, 40),
    "latency": random.uniform(50, 150),
    "error_rate": 0.01,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(emit_metrics())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

async def emit_metrics():
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(5)
            # drift metrics slightly each tick
            state["cpu"] += random.uniform(-2, 2)
            state["cpu"] = max(5, min(99, state["cpu"]))

            metrics = [
                {"service": SERVICE_NAME, "metric": "cpu_percent",    "value": state["cpu"],        "unit": "percent", "host": SERVICE_NAME},
                {"service": SERVICE_NAME, "metric": "latency_p99_ms", "value": state["latency"],    "unit": "ms",      "host": SERVICE_NAME},
                {"service": SERVICE_NAME, "metric": "error_rate",     "value": state["error_rate"], "unit": "ratio",   "host": SERVICE_NAME},
            ]
            for m in metrics:
                try:
                    await client.post(METRICS_PUSH_URL, json=m, timeout=2)
                except Exception:
                    pass  # gateway might not be up yet

@app.get("/health")
def health():
    return {"service": SERVICE_NAME, "healthy": state["healthy"]}

@app.get("/metrics/current")
def current_metrics():
    return state

@app.post("/chaos")
def inject_chaos(payload: dict):
    """Chaos injector calls this to spike metrics."""
    if "cpu" in payload:
        state["cpu"] = payload["cpu"]
    if "latency" in payload:
        state["latency"] = payload["latency"]
    if "error_rate" in payload:
        state["error_rate"] = payload["error_rate"]
    if "healthy" in payload:
        state["healthy"] = payload["healthy"]
    return {"ok": True, "state": state}

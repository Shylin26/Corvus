import os
import time
import random
import asyncio
import httpx
from collections import deque
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

SERVICE_NAME = os.getenv("SERVICE_NAME", "api-gateway")
METRICS_PUSH_URL = os.getenv("METRICS_PUSH_URL", "http://host.docker.internal:8000/internal/metrics")

state = {
    "healthy":    True,
    "cpu":        random.uniform(20, 40),
    "latency":    random.uniform(50, 150),
    "error_rate": 0.01,
}

log_buffer = deque(maxlen=100)

def write_log(level: str, message: str):
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    log_buffer.append(f"{ts} [{level}] {SERVICE_NAME}: {message}")

def generate_normal_logs():
    messages = [
        "Request handled successfully",
        "Health check passed",
        "Connection pool: 12/50 active",
        "Cache hit ratio: 94%",
        "Response time: {}ms".format(int(state["latency"])),
    ]
    write_log("INFO", random.choice(messages))

def generate_error_logs():
    messages = [
        "ERROR: Connection pool exhausted — waiting for available connection",
        "ERROR: Request timeout after {}ms".format(int(state["latency"])),
        "WARN: CPU usage critical: {}%".format(int(state["cpu"])),
        "ERROR: Failed to connect to upstream service: connection refused",
        "ERROR: Out of memory — GC overhead limit exceeded",
        "WARN: Error rate elevated: {}%".format(int(state["error_rate"] * 100)),
        "ERROR: Database connection failed: too many connections",
    ]
    write_log("ERROR", random.choice(messages))

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
            state["cpu"] += random.uniform(-2, 2)
            state["cpu"] = max(5, min(99, state["cpu"]))

            if state["cpu"] > 80 or state["error_rate"] > 0.1:
                generate_error_logs()
            else:
                generate_normal_logs()

            metrics = [
                {"service": SERVICE_NAME, "metric": "cpu_percent",    "value": state["cpu"],        "unit": "percent", "host": SERVICE_NAME},
                {"service": SERVICE_NAME, "metric": "latency_p99_ms", "value": state["latency"],    "unit": "ms",      "host": SERVICE_NAME},
                {"service": SERVICE_NAME, "metric": "error_rate",     "value": state["error_rate"], "unit": "ratio",   "host": SERVICE_NAME},
            ]
            for m in metrics:
                try:
                    await client.post(METRICS_PUSH_URL, json=m, timeout=2)
                except Exception:
                    pass

@app.get("/health")
def health():
    return {"service": SERVICE_NAME, "healthy": state["healthy"]}

@app.get("/metrics/current")
def current_metrics():
    return state

@app.get("/logs")
def get_logs(lines: int = 30):
    return {"logs": list(log_buffer)[-lines:]}

@app.post("/chaos")
def inject_chaos(payload: dict):
    if "cpu" in payload:
        state["cpu"] = payload["cpu"]
        generate_error_logs()
    if "latency" in payload:
        state["latency"] = payload["latency"]
    if "error_rate" in payload:
        state["error_rate"] = payload["error_rate"]
    if "healthy" in payload:
        state["healthy"] = payload["healthy"]
    return {"ok": True, "state": state}

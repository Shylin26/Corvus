"""
Seed the runbook vector store with synthetic past incidents.
Run once after starting postgres: python scripts/seed_runbooks.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.store import save_runbook

RUNBOOKS = [
    {
        "title": "CPU spike on order-service due to connection pool exhaustion",
        "root_cause": "Database connection pool exhausted causing CPU to spike as threads waited for connections",
        "affected": ["order-service", "api-gateway"],
        "resolution": "Restarted order-service to release connections, increased pool size in config",
        "steps": [
            {"action": "RESTART_SERVICE", "target": "order-service"},
        ],
        "outcome": "resolved",
    },
    {
        "title": "High latency on auth-service due to Redis cache miss storm",
        "root_cause": "Redis cache expired simultaneously causing thundering herd on auth-service",
        "affected": ["auth-service", "api-gateway"],
        "resolution": "Flushed Redis cache and restarted auth-service to rebuild cache gradually",
        "steps": [
            {"action": "FLUSH_CACHE",      "target": "auth-service"},
            {"action": "RESTART_SERVICE",  "target": "auth-service"},
        ],
        "outcome": "resolved",
    },
    {
        "title": "Error storm on inventory-service due to downstream timeout",
        "root_cause": "notification-service became unresponsive causing inventory-service to accumulate timed-out requests",
        "affected": ["inventory-service", "notification-service"],
        "resolution": "Restarted notification-service, error rate normalized within 2 minutes",
        "steps": [
            {"action": "RESTART_SERVICE", "target": "notification-service"},
        ],
        "outcome": "resolved",
    },
    {
        "title": "Full outage on api-gateway due to memory leak",
        "root_cause": "Memory leak in request handler caused OOM kill of api-gateway process",
        "affected": ["api-gateway", "auth-service", "order-service", "inventory-service"],
        "resolution": "Restarted api-gateway, all downstream services recovered automatically",
        "steps": [
            {"action": "RESTART_SERVICE", "target": "api-gateway"},
        ],
        "outcome": "resolved",
    },
    {
        "title": "CPU spike on notification-service due to retry storm",
        "root_cause": "Failed webhook deliveries triggered exponential retry storm consuming all CPU",
        "affected": ["notification-service"],
        "resolution": "Restarted notification-service with backoff config applied",
        "steps": [
            {"action": "RESTART_SERVICE", "target": "notification-service"},
        ],
        "outcome": "resolved",
    },
]


async def main():
    print("Pulling nomic-embed-text model from Ollama...")
    import ollama
    try:
        ollama.pull("nomic-embed-text")
        print("Model ready.")
    except Exception as e:
        print(f"Warning: could not pull model: {e}")

    print(f"Seeding {len(RUNBOOKS)} runbooks...")
    for rb in RUNBOOKS:
        rid = await save_runbook(**rb)
        if rid:
            print(f"  ✓ {rb['title'][:60]}")
        else:
            print(f"  ✗ Failed: {rb['title'][:60]}")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())

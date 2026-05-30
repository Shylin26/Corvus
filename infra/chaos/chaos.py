"""
Chaos injector — randomly breaks services to trigger the agent pipeline.

Usage:
    python infra/chaos/chaos.py                        # random chaos loop
    python infra/chaos/chaos.py --scenario cpu_spike   # specific scenario
    python infra/chaos/chaos.py --service order-service --scenario latency_spike
"""
import argparse
import asyncio
import logging
import random
import httpx

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [CHAOS] %(message)s")

# Service ports on localhost
SERVICES = {
    "api-gateway":          "http://localhost:3001",
    "auth-service":         "http://localhost:3002",
    "order-service":        "http://localhost:3003",
    "inventory-service":    "http://localhost:3004",
    "notification-service": "http://localhost:3005",
}

SCENARIOS = {
    "cpu_spike": {
        "cpu": 95.0,
        "description": "CPU pegged at 95%",
    },
    "latency_spike": {
        "latency": 4500.0,
        "description": "P99 latency spiked to 4500ms",
    },
    "error_storm": {
        "error_rate": 0.45,
        "description": "Error rate at 45%",
    },
    "full_outage": {
        "cpu": 99.0,
        "latency": 9999.0,
        "error_rate": 0.95,
        "healthy": False,
        "description": "Full service outage",
    },
    "recover": {
        "cpu": random.uniform(20, 40),
        "latency": random.uniform(50, 150),
        "error_rate": 0.01,
        "healthy": True,
        "description": "Service recovered to normal",
    },
}


async def inject(service: str, scenario: str) -> None:
    url = SERVICES.get(service)
    if not url:
        log.error("Unknown service: %s", service)
        return

    payload = {k: v for k, v in SCENARIOS[scenario].items() if k != "description"}
    desc    = SCENARIOS[scenario]["description"]

    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(f"{url}/chaos", json=payload, timeout=3)
            r.raise_for_status()
            log.info("%-25s ← %s (%s)", service, scenario, desc)
        except Exception as e:
            log.error("Failed to inject into %s: %s", service, e)


async def random_chaos_loop(interval: int = 30) -> None:
    """Randomly pick a service and scenario every N seconds."""
    log.info("Starting random chaos loop (interval=%ds)", interval)
    while True:
        await asyncio.sleep(interval)
        service  = random.choice(list(SERVICES.keys()))
        scenario = random.choice([s for s in SCENARIOS if s != "recover"])
        await inject(service, scenario)

        # Auto-recover after 60s so the system isn't permanently broken
        await asyncio.sleep(60)
        await inject(service, "recover")


async def main(service: str | None, scenario: str | None, loop: bool) -> None:
    if loop:
        await random_chaos_loop()
    elif service and scenario:
        await inject(service, scenario)
    else:
        # one random hit
        service  = random.choice(list(SERVICES.keys()))
        scenario = random.choice([s for s in SCENARIOS if s != "recover"])
        await inject(service, scenario)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--service",  help="Target service name")
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()), help="Chaos scenario")
    parser.add_argument("--loop",     action="store_true", help="Run random chaos loop forever")
    args = parser.parse_args()

    asyncio.run(main(args.service, args.scenario, args.loop))

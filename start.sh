#!/bin/bash
echo "Starting Corvus..."

# Start native services (no Docker needed)
brew services start kafka 2>/dev/null
brew services start postgresql@16 2>/dev/null
brew services start redis 2>/dev/null

sleep 5
nc -zv localhost 9092 2>&1 | grep -q "succeeded" && echo "✓ Kafka ready" || echo "✗ Kafka not ready — run: brew services start kafka"
pg_isready -h localhost -p 5432 -U corvus 2>/dev/null && echo "✓ Postgres ready" || echo "✗ Postgres not ready"

echo ""
echo "Run agents:"
echo "  source .venv/bin/activate"
echo "  uvicorn gateway.main:app --port 8000 &"
echo "  python -m agents.observer &"
echo "  python -m agents.forensics &"
echo "  python -m agents.executor &"
echo "  python -m orchestrator &"
echo ""
echo "Push test metric:"
echo "  python scripts/push_metric.py --service order-service --metric cpu_percent --value 95"
echo ""
echo "Dashboard: http://localhost:5173"

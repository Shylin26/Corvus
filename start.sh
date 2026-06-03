#!/bin/bash
set -e

echo "◈ Starting Corvus..."

cd "$(dirname "$0")"

# Native services
brew services start kafka 2>/dev/null || true
brew services start postgresql@16 2>/dev/null || true
brew services start redis 2>/dev/null || true

sleep 3

# Check Kafka
nc -zv localhost 9092 2>&1 | grep -q "succeeded" \
  && echo "✓ Kafka" || { echo "✗ Kafka not ready"; exit 1; }

pg_isready -h localhost -p 5432 -U corvus -q \
  && echo "✓ Postgres" || { echo "✗ Postgres not ready"; exit 1; }

echo "✓ Redis assumed up"

source .venv/bin/activate

# Kill old processes
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
pkill -f "agents.observer"   2>/dev/null || true
pkill -f "agents.forensics"  2>/dev/null || true
pkill -f "agents.executor"   2>/dev/null || true
pkill -f "orchestrator.main" 2>/dev/null || true
sleep 1

echo "◈ Starting agents..."
uvicorn gateway.main:app --port 8000 &
sleep 1
python -m agents.observer   &
python -m agents.forensics  &
python -m agents.executor   &
python -m orchestrator      &

sleep 3
echo ""
echo "✓ All agents running"
echo "✓ Dashboard: http://localhost:5173"
echo "✓ Gateway:   http://localhost:8000"
echo ""
echo "Inject chaos:"
echo "  python scripts/push_metric.py --service order-service --metric cpu_percent --value 95"
echo ""
echo "Start frontend (separate terminal):"
echo "  cd frontend && npm run dev"

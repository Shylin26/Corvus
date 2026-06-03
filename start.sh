#!/bin/bash
echo "Starting Corvus..."

# Stop Sentinel containers that conflict
docker stop infra-redis-1 infra-kafka-1 infra-zookeeper-1 infra-publisher-1 \
  infra-diff-extractor-1 infra-inference-1 infra-autoscaler-1 infra-webhook-1 \
  infra-prometheus-1 infra-grafana-1 2>/dev/null

# Start Corvus infrastructure
docker compose up -d
echo "Waiting for Kafka..."
sleep 20

# Check Kafka
nc -zv localhost 9092 2>&1 | grep -q "succeeded" && echo "Kafka ready" || echo "Kafka not ready"

echo ""
echo "Now open 4 terminal tabs and run:"
echo "  Tab 1: source .venv/bin/activate && uvicorn gateway.main:app --reload --port 8000"
echo "  Tab 2: source .venv/bin/activate && python -m agents.observer"
echo "  Tab 3: source .venv/bin/activate && python -m agents.forensics"
echo "  Tab 4: source .venv/bin/activate && python -m agents.executor"
echo ""
echo "Then inject chaos: python infra/chaos/chaos.py --scenario cpu_spike --service order-service"

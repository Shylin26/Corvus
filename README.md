# Corvus

> A self-healing distributed system that observes your infrastructure, diagnoses failures using a local LLM, and autonomously executes fixes — with full explainability at every step.

## What is Corvus?

Most distributed systems fail silently. Alerts fire, engineers scramble, runbooks get consulted — and the same incidents repeat.

Corvus builds an autonomous operations layer on top of a simulated microservices mesh. When something breaks, Corvus detects it, traces the root cause, proposes a ranked remediation plan, executes the fix with rollback capability, and writes a post-mortem — all without human intervention unless the risk is too high.

## Stack

| Layer | Technology |
|---|---|
| LLM | Mistral 7B via Ollama (free, local) |
| Message bus | Redpanda (Kafka-compatible) |
| Database | Postgres + pgvector |
| Cache | Redis |
| Agents | Python 3.11 |
| API | FastAPI |
| Frontend | React + React Flow + Zustand |
| Infra sim | Docker Compose + chaos script |

## Quickstart

\`\`\`bash
cp .env.example .env
ollama pull mistral:7b
docker compose up -d
pip install -e ".[dev]"
python -m agents.observer
\`\`\`

## Build status

- [x] Project scaffold
- [x] Core envelope schema
- [x] Kafka client
- [x] Simulated services + chaos injector
- [ ] Observer agent
- [ ] Forensics + Planner agent
- [ ] Orchestrator + approval gate
- [ ] Executor + saga rollback
- [ ] Frontend dashboard

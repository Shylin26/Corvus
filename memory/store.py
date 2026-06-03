from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import asyncpg
import ollama

from core.config import settings

log = logging.getLogger(__name__)


async def get_conn() -> asyncpg.Connection:
    return await asyncpg.connect(
        settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    )


async def embed(text: str) -> list[float]:
    """Generate embedding using Ollama nomic-embed-text model."""
    try:
        response = ollama.embeddings(
            model="nomic-embed-text",
            prompt=text,
        )
        return response["embedding"]
    except Exception as e:
        log.error("Embedding failed: %s", e)
        return []


async def search_runbooks(description: str, limit: int = 2) -> list[dict]:
    """Find similar past incidents by semantic similarity."""
    embedding = await embed(description)
    if not embedding:
        return []

    try:
        conn = await get_conn()
        rows = await conn.fetch(
            """
            SELECT id, title, root_cause, resolution, steps, outcome
            FROM runbooks
            ORDER BY embedding <=> $1::vector
            LIMIT $2
            """,
            json.dumps(embedding),
            limit,
        )
        await conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        log.error("Runbook search failed: %s", e)
        return []


async def save_runbook(
    title: str,
    root_cause: str,
    affected: list[str],
    resolution: str,
    steps: list[dict],
    outcome: str = "resolved",
    source: str = "postmortem",
) -> str | None:
    """Save a new runbook to the vector store."""
    text = f"{title}. {root_cause}. {resolution}"
    embedding = await embed(text)
    if not embedding:
        return None

    try:
        conn = await get_conn()
        row = await conn.fetchrow(
            """
            INSERT INTO runbooks
                (title, root_cause, affected, resolution, steps, outcome, source, embedding)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::vector)
            RETURNING id
            """,
            title,
            root_cause,
            affected,
            resolution,
            json.dumps(steps),
            outcome,
            source,
            json.dumps(embedding),
        )
        await conn.close()
        runbook_id = str(row["id"])
        log.info("Saved runbook %s", runbook_id)
        return runbook_id
    except Exception as e:
        log.error("Failed to save runbook: %s", e)
        return None

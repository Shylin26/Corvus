from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import asyncpg

from core.config import settings

log = logging.getLogger(__name__)


async def get_conn() -> asyncpg.Connection:
    return await asyncpg.connect(
        settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    )


async def upsert_incident(incident_id: str, data: dict) -> None:
    try:
        conn = await get_conn()
        # Serialize datetime objects
        started_at = data.get("started_at")
        if isinstance(started_at, datetime):
            started_at = started_at.isoformat()

        await conn.execute(
            """
            INSERT INTO incidents (id, status, service, root_cause, updated_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET
                status     = EXCLUDED.status,
                root_cause = EXCLUDED.root_cause,
                updated_at = NOW()
            """,
            incident_id,
            data.get("status", "DETECTING"),
            data.get("service", "unknown"),
            data.get("root_cause"),
        )
        await conn.close()
    except Exception as e:
        log.error("Failed to upsert incident %s: %s", incident_id, e)


async def load_incidents() -> dict:
    try:
        conn = await get_conn()
        rows = await conn.fetch(
            "SELECT id, status, service, root_cause, anomaly_at FROM incidents ORDER BY anomaly_at DESC LIMIT 50"
        )
        await conn.close()
        return {
            row["id"]: {
                "status":     row["status"],
                "service":    row["service"],
                "root_cause": row["root_cause"],
                "started_at": row["anomaly_at"].isoformat() if row["anomaly_at"] else None,
            }
            for row in rows
        }
    except Exception as e:
        log.error("Failed to load incidents: %s", e)
        return {}

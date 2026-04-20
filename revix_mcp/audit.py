"""
Revix MCP · Audit log + idempotencia.

Cada invocación de tool se escribe en `audit_logs` con source="mcp_agent".
Tools de escritura aceptan `idempotency_key`; si se repite, devolvemos la
respuesta anterior desde `mcp_idempotency`.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from .auth import AgentIdentity
from .config import AUDIT_COLLECTION, IDEMPOTENCY_COLLECTION, MCP_ENV


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _summary(result: Any, max_len: int = 500) -> str:
    try:
        s = repr(result)
    except Exception:  # noqa: BLE001
        s = '<no-representable>'
    if len(s) > max_len:
        s = s[:max_len] + '…'
    return s


async def log_tool_call(
    db: AsyncIOMotorDatabase,
    *,
    identity: AgentIdentity,
    tool: str,
    params: dict | None,
    result: Any = None,
    error: Optional[str] = None,
    duration_ms: int = 0,
    idempotency_key: Optional[str] = None,
) -> None:
    """Persiste una entrada de audit log."""
    # Sanitizamos params para no guardar secretos por error
    safe_params = dict(params or {})
    for k in list(safe_params.keys()):
        if 'key' in k.lower() or 'token' in k.lower() or 'password' in k.lower():
            safe_params[k] = '***'

    await db[AUDIT_COLLECTION].insert_one({
        'source': 'mcp_agent',
        'env': MCP_ENV,
        'agent_id': identity.agent_id,
        'agent_name': identity.agent_name,
        'key_id': identity.key_id,
        'tool': tool,
        'params': safe_params,
        'result_summary': _summary(result) if result is not None else None,
        'error': error,
        'duration_ms': int(duration_ms),
        'idempotency_key': idempotency_key,
        'timestamp': _now_iso(),
    })


# ── Idempotencia ──────────────────────────────────────────────────────────────

async def idempotency_lookup(
    db: AsyncIOMotorDatabase,
    *,
    agent_id: str,
    tool: str,
    key: str,
) -> Optional[Any]:
    """Si este (agent_id, tool, key) ya se ejecutó, devuelve su resultado."""
    doc = await db[IDEMPOTENCY_COLLECTION].find_one(
        {'agent_id': agent_id, 'tool': tool, 'key': key},
        {'_id': 0, 'result': 1},
    )
    return doc.get('result') if doc else None


async def idempotency_store(
    db: AsyncIOMotorDatabase,
    *,
    agent_id: str,
    tool: str,
    key: str,
    result: Any,
) -> None:
    """Guarda el resultado para futuros reintentos con la misma key."""
    await db[IDEMPOTENCY_COLLECTION].update_one(
        {'agent_id': agent_id, 'tool': tool, 'key': key},
        {'$set': {
            'agent_id': agent_id, 'tool': tool, 'key': key,
            'result': result, 'created_at': _now_iso(),
        }},
        upsert=True,
    )


class Timer:
    """Helper para medir duration_ms sin try/except/else en cada tool."""

    def __init__(self) -> None:
        self._start = 0.0
        self.ms = 0

    def __enter__(self) -> 'Timer':
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc) -> None:
        self.ms = int((time.perf_counter() - self._start) * 1000)

"""
Revix MCP · Rate limiting por agente.

Algoritmo: sliding window de 60s con un documento por llamada en
`mcp_rate_limits`. Un TTL index elimina automáticamente las entradas
antiguas.

Por agente se almacenan dos umbrales en `mcp_agent_limits`:
  - soft_limit: supera este límite → log warning + audit, pero NO bloquea.
  - hard_limit: supera este límite → se bloquea la ejecución (HTTP 429).

Los límites son editables directamente en Mongo (colección `mcp_agent_limits`).
Si no existe entrada para un agent_id, aplica el default `_FALLBACK`.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

LIMITS_COLLECTION = 'mcp_agent_limits'
USAGE_COLLECTION = 'mcp_rate_limits'
WINDOW_SECONDS = 60

# Defaults si el agente no tiene config en BD
_FALLBACK = (120, 600)

logger = logging.getLogger('revix.mcp.rate_limit')

# ──────────────────────────────────────────────────────────────────────────────
# Cache ligero en memoria (evita golpear Mongo en cada tool call)
# ──────────────────────────────────────────────────────────────────────────────

_LIMITS_CACHE: dict[str, tuple[tuple[int, int], float]] = {}
_CACHE_TTL_S = 30.0


def invalidate_limits_cache() -> None:
    _LIMITS_CACHE.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Excepción y dataclass
# ──────────────────────────────────────────────────────────────────────────────

class RateLimitExceeded(Exception):
    """Se ha superado el hard limit de un agente."""

    def __init__(self, agent_id: str, count: int, hard_limit: int) -> None:
        super().__init__(
            f'Rate limit excedido para agente "{agent_id}": '
            f'{count} llamadas en los últimos {WINDOW_SECONDS}s '
            f'(hard_limit={hard_limit}/min)'
        )
        self.agent_id = agent_id
        self.count = count
        self.hard_limit = hard_limit


@dataclass
class RateLimitResult:
    agent_id: str
    count: int          # llamadas en la ventana (incluyendo esta)
    soft_limit: int
    hard_limit: int
    within_soft: bool   # True si count <= soft_limit
    within_hard: bool   # True si count <= hard_limit

    @property
    def crossed_soft(self) -> bool:
        return not self.within_soft and self.within_hard


# ──────────────────────────────────────────────────────────────────────────────
# Config (límites por agente)
# ──────────────────────────────────────────────────────────────────────────────

async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """Crea índices idempotentes: TTL sobre usage + unique sobre config."""
    try:
        await db[USAGE_COLLECTION].create_index(
            'timestamp', expireAfterSeconds=WINDOW_SECONDS * 2,
            name='ttl_rate_limit_usage',
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f'No se pudo crear TTL index de rate limits: {e}')
    try:
        await db[USAGE_COLLECTION].create_index(
            [('agent_id', 1), ('timestamp', 1)],
            name='idx_agent_ts',
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        await db[LIMITS_COLLECTION].create_index(
            'agent_id', unique=True, name='uniq_agent_id',
        )
    except Exception:  # noqa: BLE001
        pass


async def set_limits(
    db: AsyncIOMotorDatabase,
    *, agent_id: str, soft_limit: int, hard_limit: int,
) -> None:
    assert 0 < soft_limit <= hard_limit, 'soft_limit debe ser <= hard_limit'
    await db[LIMITS_COLLECTION].update_one(
        {'agent_id': agent_id},
        {'$set': {
            'agent_id': agent_id,
            'soft_limit': int(soft_limit),
            'hard_limit': int(hard_limit),
            'updated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        }},
        upsert=True,
    )
    invalidate_limits_cache()


async def seed_default_limits(db: AsyncIOMotorDatabase) -> None:
    """Idempotente: siembra límites por defecto para los 3 agentes actuales.

    Si el documento ya existe, NO se sobrescribe (respeta cambios manuales).
    """
    await ensure_indexes(db)
    defaults = [
        ('kpi_analyst', 120, 600),
        ('auditor', 120, 600),
        ('supervisor_cola', 120, 600),
        ('seguimiento_publico', 60, 300),
    ]
    for agent_id, soft, hard in defaults:
        await db[LIMITS_COLLECTION].update_one(
            {'agent_id': agent_id},
            {'$setOnInsert': {
                'agent_id': agent_id,
                'soft_limit': soft,
                'hard_limit': hard,
                'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'seed': True,
            }},
            upsert=True,
        )
    invalidate_limits_cache()


async def get_limits(db: AsyncIOMotorDatabase, agent_id: str) -> tuple[int, int]:
    """Devuelve (soft_limit, hard_limit) con cache 30s."""
    now = time.monotonic()
    cached = _LIMITS_CACHE.get(agent_id)
    if cached and cached[1] > now:
        return cached[0]
    doc = await db[LIMITS_COLLECTION].find_one(
        {'agent_id': agent_id}, {'_id': 0, 'soft_limit': 1, 'hard_limit': 1},
    )
    if doc and doc.get('soft_limit') and doc.get('hard_limit'):
        limits = (int(doc['soft_limit']), int(doc['hard_limit']))
    else:
        limits = _FALLBACK
    _LIMITS_CACHE[agent_id] = (limits, now + _CACHE_TTL_S)
    return limits


# ──────────────────────────────────────────────────────────────────────────────
# Check + record (sliding window)
# ──────────────────────────────────────────────────────────────────────────────

async def check_and_record(
    db: AsyncIOMotorDatabase,
    *, agent_id: str,
    _now: Optional[datetime] = None,
) -> RateLimitResult:
    """Comprueba si una nueva llamada excede los límites, y la registra si NO.

    Si se supera el `hard_limit`, la llamada NO se registra (así el contador
    no crece más y la carga de BD se mantiene bajo control) y se devuelve el
    resultado con within_hard=False.

    Args:
        _now: inyectable para tests (permite controlar el reloj).
    """
    soft, hard = await get_limits(db, agent_id)
    now = _now or datetime.now(timezone.utc)
    window_start = now.timestamp() - WINDOW_SECONDS

    # Contar llamadas recientes del agente
    count_prev = await db[USAGE_COLLECTION].count_documents({
        'agent_id': agent_id,
        'ts_epoch': {'$gte': window_start},
    })
    count = count_prev + 1  # incluimos la llamada actual en el resultado

    within_hard = count <= hard
    within_soft = count <= soft

    if within_hard:
        # Registramos solo si podemos ejecutar
        await db[USAGE_COLLECTION].insert_one({
            'agent_id': agent_id,
            'timestamp': now,
            'ts_epoch': now.timestamp(),
        })
    else:
        logger.warning(
            f'[rate-limit] HARD limit rebasado: agent={agent_id} '
            f'count={count_prev} hard={hard}',
        )

    return RateLimitResult(
        agent_id=agent_id, count=count,
        soft_limit=soft, hard_limit=hard,
        within_soft=within_soft, within_hard=within_hard,
    )

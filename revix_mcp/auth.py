"""
Revix MCP · Auth · gestión y validación de API keys.

Modelo de almacenamiento (colección `mcp_api_keys`):
  {
    "id": uuid,
    "key_hash": sha256(key),         # nunca se guarda el key en plano
    "key_prefix": "revix_mcp_abcd",  # primeros 20 chars para identificar sin revelar
    "agent_id": "kpi_analyst",
    "agent_name": "KPI Analyst",
    "scopes": ["orders:read", ...],
    "active": bool,
    "rate_limit_per_min": 120,
    "created_at": iso str,
    "created_by": "master@revix.es",
    "last_used_at": iso str | null,
    "revoked_at": iso str | null,
  }

El key en plano solo se muestra UNA VEZ al crearlo (CLI o endpoint admin).
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from . import scopes as _scopes
from .config import API_KEYS_COLLECTION, DEFAULT_RATE_LIMIT_PER_MIN

KEY_PREFIX = 'revix_mcp_'
KEY_BYTES = 32  # 256 bits → base64 da 43 chars. Prefijo + 43 = 52 chars


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def generate_api_key() -> str:
    """Genera una API key aleatoria de alta entropía con prefijo Revix."""
    return KEY_PREFIX + secrets.token_urlsafe(KEY_BYTES)


@dataclass
class AgentIdentity:
    """Resultado de validar una API key — identidad del agente MCP."""
    key_id: str
    agent_id: str
    agent_name: str
    scopes: list[str]
    rate_limit_per_min: int
    key_prefix: str = ''

    def has_scope(self, required: str) -> bool:
        return _scopes.has_scope(self.scopes, required)


class AuthError(Exception):
    """Error de autenticación o autorización."""


# ──────────────────────────────────────────────────────────────────────────────
# Gestión (CLI / admin)
# ──────────────────────────────────────────────────────────────────────────────

async def create_api_key(
    db: AsyncIOMotorDatabase,
    *,
    agent_id: str,
    agent_name: str,
    scopes: list[str],
    created_by: str,
    rate_limit_per_min: int = DEFAULT_RATE_LIMIT_PER_MIN,
) -> tuple[str, dict]:
    """Crea una nueva API key.

    Devuelve (plain_key, doc). `plain_key` solo se muestra esta vez.
    """
    scopes_clean = _scopes.validate_scopes(scopes)
    plain = generate_api_key()
    doc = {
        'id': _hash(plain)[:16],  # key_id público, derivado pero no reversible
        'key_hash': _hash(plain),
        'key_prefix': plain[:20],
        'agent_id': agent_id,
        'agent_name': agent_name,
        'scopes': scopes_clean,
        'active': True,
        'rate_limit_per_min': int(rate_limit_per_min),
        'created_at': _now_iso(),
        'created_by': created_by,
        'last_used_at': None,
        'revoked_at': None,
    }
    await db[API_KEYS_COLLECTION].insert_one(dict(doc))
    return plain, doc


async def revoke_api_key(db: AsyncIOMotorDatabase, key_id: str) -> bool:
    res = await db[API_KEYS_COLLECTION].update_one(
        {'id': key_id, 'active': True},
        {'$set': {'active': False, 'revoked_at': _now_iso()}},
    )
    return res.modified_count == 1


async def list_api_keys(db: AsyncIOMotorDatabase) -> list[dict]:
    cursor = db[API_KEYS_COLLECTION].find(
        {},
        {'_id': 0, 'key_hash': 0},  # nunca devolvemos el hash
    ).sort('created_at', -1)
    return [doc async for doc in cursor]


# ──────────────────────────────────────────────────────────────────────────────
# Validación en cada llamada a tool
# ──────────────────────────────────────────────────────────────────────────────

async def verify_api_key(db: AsyncIOMotorDatabase, key: str) -> AgentIdentity:
    """Valida un key en plano y devuelve la identidad del agente.

    Lanza AuthError si no es válido, está revocado o inactivo.
    Actualiza `last_used_at`.
    """
    if not key or not key.startswith(KEY_PREFIX):
        raise AuthError('API key con formato inválido')

    doc = await db[API_KEYS_COLLECTION].find_one(
        {'key_hash': _hash(key), 'active': True},
    )
    if not doc:
        raise AuthError('API key no reconocida o revocada')

    # Touch last_used_at (fire-and-forget)
    try:
        await db[API_KEYS_COLLECTION].update_one(
            {'id': doc['id']},
            {'$set': {'last_used_at': _now_iso()}},
        )
    except Exception:  # noqa: BLE001
        pass

    return AgentIdentity(
        key_id=doc['id'],
        agent_id=doc['agent_id'],
        agent_name=doc['agent_name'],
        scopes=list(doc.get('scopes', [])),
        rate_limit_per_min=int(doc.get('rate_limit_per_min', DEFAULT_RATE_LIMIT_PER_MIN)),
        key_prefix=doc.get('key_prefix', ''),
    )


def require_scope(identity: AgentIdentity, required: str) -> None:
    """Lanza AuthError si el agente no tiene el scope solicitado."""
    if not identity.has_scope(required):
        raise AuthError(
            f'Scope requerido "{required}" no presente en agente "{identity.agent_id}"'
        )

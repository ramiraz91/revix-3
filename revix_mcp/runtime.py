"""
Revix MCP · Runtime — orquesta la ejecución de cualquier tool.

Este módulo contiene la lógica común que se aplica en CADA llamada:
  1. Validar API key → AgentIdentity
  2. Resolver tool por nombre
  3. Comprobar scope
  4. Sandbox check (si MCP_ENV=preview y tool.sandbox_skip → devolver mock)
  5. Idempotencia (si tool.writes y llega idempotency_key)
  6. Ejecutar handler con timer
  7. Persistir audit_log
  8. Devolver resultado o propagar error envuelto
"""
from __future__ import annotations

import json
import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from .auth import AgentIdentity, AuthError, require_scope, verify_api_key
from .audit import Timer, idempotency_lookup, idempotency_store, log_tool_call
from .config import MCP_ENV
from .rate_limit import RateLimitExceeded, check_and_record
from .tools._registry import get_tool

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Cualquier error durante la ejecución de una tool."""


class ToolRateLimitError(ToolExecutionError):
    """Se superó el hard rate limit. Mapea a HTTP 429 en la capa API."""

    def __init__(self, agent_id: str, count: int, hard_limit: int) -> None:
        super().__init__(
            f'Rate limit excedido para agente "{agent_id}" '
            f'({count} llamadas/min, hard_limit={hard_limit})',
        )
        self.agent_id = agent_id
        self.count = count
        self.hard_limit = hard_limit


async def execute_tool(
    db: AsyncIOMotorDatabase,
    *,
    api_key: str,
    tool_name: str,
    params: dict | None = None,
) -> dict:
    """Punto de entrada único para ejecutar cualquier tool.

    Protege con auth + scopes + audit + idempotencia.
    """
    # 1. Auth
    identity = await verify_api_key(db, api_key)
    return await _execute_tool_with_identity(
        db, identity=identity, tool_name=tool_name, params=params,
    )


async def execute_tool_internal(
    db: AsyncIOMotorDatabase,
    *,
    identity: AgentIdentity,
    tool_name: str,
    params: dict | None = None,
) -> dict:
    """Entrada para agentes INTERNOS (mismo proceso) que ya están autenticados.

    Útil para el orquestador de agentes nativo: crea una identidad en memoria
    (no necesita API key física) y ejecuta tools igualmente con todas las
    comprobaciones de scope + audit + idempotencia.
    """
    return await _execute_tool_with_identity(
        db, identity=identity, tool_name=tool_name, params=params,
    )


async def _execute_tool_with_identity(
    db: AsyncIOMotorDatabase,
    *,
    identity: AgentIdentity,
    tool_name: str,
    params: dict | None = None,
) -> dict:
    params = dict(params or {})
    idempotency_key = params.pop('_idempotency_key', None)

    # 2. Tool
    spec = get_tool(tool_name)
    if not spec:
        await log_tool_call(
            db, identity=identity, tool=tool_name,
            params=params, error='tool_not_found',
        )
        raise ToolExecutionError(f'Tool "{tool_name}" no existe')

    # 3. Scope
    try:
        require_scope(identity, spec.required_scope)
    except AuthError as e:
        await log_tool_call(
            db, identity=identity, tool=tool_name,
            params=params, error=f'scope_denied:{spec.required_scope}',
        )
        raise ToolExecutionError(str(e)) from e

    # 3.b Rate limit (per agente, sliding window 60s)
    rl = await check_and_record(db, agent_id=identity.agent_id)
    if not rl.within_hard:
        await log_tool_call(
            db, identity=identity, tool=tool_name,
            params=params,
            error=f'rate_limit_exceeded:{rl.count}/{rl.hard_limit}',
        )
        raise ToolRateLimitError(
            agent_id=identity.agent_id, count=rl.count, hard_limit=rl.hard_limit,
        )
    if rl.crossed_soft:
        logger.warning(
            f'[rate-limit] SOFT limit rebasado: agent={identity.agent_id} '
            f'count={rl.count} soft={rl.soft_limit} hard={rl.hard_limit}',
        )
        await log_tool_call(
            db, identity=identity, tool=tool_name,
            params=params, duration_ms=0,
            error=f'rate_limit_soft_crossed:{rl.count}/{rl.soft_limit}',
            result={'warning': 'soft_limit_crossed'},
        )

    # 4. Sandbox
    if spec.sandbox_skip and MCP_ENV == 'preview':
        mock = {'sandbox': True, 'message': f'tool "{tool_name}" no ejecutada en preview'}
        await log_tool_call(
            db, identity=identity, tool=tool_name,
            params=params, result=mock, duration_ms=0,
            idempotency_key=idempotency_key,
        )
        return mock

    # 5. Idempotencia (solo tools de escritura)
    if spec.writes and idempotency_key:
        cached = await idempotency_lookup(
            db, agent_id=identity.agent_id, tool=tool_name, key=idempotency_key,
        )
        if cached is not None:
            await log_tool_call(
                db, identity=identity, tool=tool_name,
                params=params, result={'cached': True},
                idempotency_key=idempotency_key,
            )
            return cached

    # 6. Ejecutar
    with Timer() as timer:
        try:
            result = await spec.handler(db, identity, params)
        except ToolExecutionError:
            raise
        except Exception as e:  # noqa: BLE001
            await log_tool_call(
                db, identity=identity, tool=tool_name,
                params=params, error=str(e), duration_ms=timer.ms,
                idempotency_key=idempotency_key,
            )
            raise ToolExecutionError(f'Error ejecutando "{tool_name}": {e}') from e

    # 7. Persistir idempotencia (tools de escritura)
    if spec.writes and idempotency_key:
        await idempotency_store(
            db, agent_id=identity.agent_id, tool=tool_name,
            key=idempotency_key, result=result,
        )

    # 8. Audit
    await log_tool_call(
        db, identity=identity, tool=tool_name,
        params=params, result=result, duration_ms=timer.ms,
        idempotency_key=idempotency_key,
    )

    return result

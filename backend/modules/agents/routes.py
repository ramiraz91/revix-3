"""
API de agentes IA nativos de Revix.

Endpoints (todos bajo /api):
  GET  /api/agents                          → lista agentes visibles
  POST /api/agents/{agent_id}/chat          → envía un mensaje, devuelve respuesta
  GET  /api/agents/{agent_id}/sessions      → sesiones del usuario actual
  GET  /api/agents/sessions/{session_id}    → mensajes de una sesión
  DELETE /api/agents/sessions/{session_id}  → borrar sesión
  GET  /api/agents/audit-logs               → logs MCP recientes (admin)

Endpoint público (sin auth) para el widget de seguimiento:
  POST /api/public/agents/seguimiento/chat  → solo usa el agente seguimiento_publico
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from config import db
from auth import require_auth, require_admin

from .agent_defs import (
    AGENTS, AgentDef, get_agent, list_internal_agents, list_public_agents,
)
from .engine import run_agent_turn

# Propagación de errores del MCP runtime (rate limit → HTTP 429)
import sys
from pathlib import Path
_APP_ROOT = Path(__file__).resolve().parents[3]
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))
from revix_mcp.runtime import ToolRateLimitError  # noqa: E402
from revix_mcp.rate_limit import seed_default_limits  # noqa: E402

logger = logging.getLogger('revix.agents.routes')

router = APIRouter(tags=['agents'])

AGENT_SESSIONS_COLL = 'agent_sessions'
AGENT_MESSAGES_COLL = 'agent_messages'


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _agent_public(a: AgentDef) -> dict:
    return {
        'id': a.id,
        'nombre': a.nombre,
        'descripcion': a.descripcion,
        'emoji': a.emoji,
        'color': a.color,
        'scopes': a.scopes,
        'tools': a.tools,
        'visible_to_public': a.visible_to_public,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Listado de agentes
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/agents')
async def listar_agentes(user: dict = Depends(require_auth)):
    return {'agents': [_agent_public(a) for a in list_internal_agents()]}


# ──────────────────────────────────────────────────────────────────────────────
# Chat con agente interno (CRM)
# ──────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None


@router.post('/agents/{agent_id}/chat')
async def chatear_con_agente(
    agent_id: str,
    body: ChatRequest,
    user: dict = Depends(require_auth),
):
    agent = get_agent(agent_id)
    if not agent or agent.visible_to_public:
        raise HTTPException(status_code=404, detail='Agente no disponible')

    user_id = user.get('id') or user.get('email') or 'unknown'

    # Resolver / crear sesión
    session_id = body.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        await db[AGENT_SESSIONS_COLL].insert_one({
            'id': session_id,
            'agent_id': agent_id,
            'user_id': user_id,
            'created_at': _now_iso(),
            'updated_at': _now_iso(),
            'title': body.message[:60],
        })
    else:
        # Comprueba que la sesión pertenezca al usuario
        sess = await db[AGENT_SESSIONS_COLL].find_one(
            {'id': session_id, 'user_id': user_id},
            {'_id': 0},
        )
        if not sess:
            raise HTTPException(status_code=404, detail='Sesión no encontrada')

    # Cargar historial de la sesión
    cursor = db[AGENT_MESSAGES_COLL].find(
        {'session_id': session_id},
        {'_id': 0, 'role': 1, 'content': 1, 'tool_calls': 1, 'tool_call_id': 1, 'name': 1},
    ).sort('seq', 1)
    history = [m async for m in cursor]
    # Solo roles que el LLM acepta
    history_for_llm = []
    for m in history:
        entry = {'role': m['role'], 'content': m.get('content') or ''}
        if m.get('tool_calls'):
            entry['tool_calls'] = m['tool_calls']
        if m.get('tool_call_id'):
            entry['tool_call_id'] = m['tool_call_id']
        if m.get('name'):
            entry['name'] = m['name']
        history_for_llm.append(entry)

    # Ejecutar turno
    try:
        result = await run_agent_turn(db, agent, history_for_llm, body.message)
    except ToolRateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail={
                'error': 'rate_limit_exceeded',
                'agent_id': e.agent_id,
                'count_last_minute': e.count,
                'hard_limit_per_min': e.hard_limit,
                'message': f'El agente "{e.agent_id}" ha superado su límite de '
                           f'{e.hard_limit} consultas por minuto. Espera un momento '
                           f'e intenta de nuevo.',
            },
        )
    except Exception as e:  # noqa: BLE001
        logger.exception('agent turn failed')
        raise HTTPException(status_code=500, detail=f'Fallo del agente: {e}')

    # Persistir nuevos mensajes (user + assistant + tools intermedios)
    base_seq = len(history)
    full_new = result['messages'][len(history_for_llm):]  # solo lo nuevo
    docs = []
    for i, m in enumerate(full_new):
        docs.append({
            'session_id': session_id,
            'agent_id': agent_id,
            'seq': base_seq + i,
            'role': m.get('role'),
            'content': m.get('content'),
            'tool_calls': m.get('tool_calls'),
            'tool_call_id': m.get('tool_call_id'),
            'name': m.get('name'),
            'created_at': _now_iso(),
        })
    if docs:
        await db[AGENT_MESSAGES_COLL].insert_many(docs)
    await db[AGENT_SESSIONS_COLL].update_one(
        {'id': session_id}, {'$set': {'updated_at': _now_iso()}},
    )

    return {
        'session_id': session_id,
        'reply': result['reply'],
        'tool_calls': result['tool_calls'],
        'iterations': result['iterations'],
        'duration_ms': result['duration_ms'],
        'usage': result.get('usage'),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Gestión de sesiones
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/agents/{agent_id}/sessions')
async def listar_sesiones(
    agent_id: str,
    user: dict = Depends(require_auth),
    limit: int = Query(30, ge=1, le=200),
):
    user_id = user.get('id') or user.get('email') or 'unknown'
    cursor = db[AGENT_SESSIONS_COLL].find(
        {'agent_id': agent_id, 'user_id': user_id},
        {'_id': 0},
    ).sort('updated_at', -1).limit(limit)
    return {'sessions': [s async for s in cursor]}


@router.get('/agents/sessions/{session_id}')
async def obtener_sesion(session_id: str, user: dict = Depends(require_auth)):
    user_id = user.get('id') or user.get('email') or 'unknown'
    sess = await db[AGENT_SESSIONS_COLL].find_one(
        {'id': session_id, 'user_id': user_id}, {'_id': 0},
    )
    if not sess:
        raise HTTPException(status_code=404, detail='Sesión no encontrada')
    cursor = db[AGENT_MESSAGES_COLL].find(
        {'session_id': session_id, 'role': {'$in': ['user', 'assistant']}},
        {'_id': 0, 'role': 1, 'content': 1, 'seq': 1, 'tool_calls': 1, 'created_at': 1},
    ).sort('seq', 1)
    messages = [m async for m in cursor]
    return {'session': sess, 'messages': messages}


@router.delete('/agents/sessions/{session_id}')
async def borrar_sesion(session_id: str, user: dict = Depends(require_auth)):
    user_id = user.get('id') or user.get('email') or 'unknown'
    res = await db[AGENT_SESSIONS_COLL].delete_one(
        {'id': session_id, 'user_id': user_id},
    )
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Sesión no encontrada')
    await db[AGENT_MESSAGES_COLL].delete_many({'session_id': session_id})
    return {'deleted': True}


# ──────────────────────────────────────────────────────────────────────────────
# Audit logs MCP (observabilidad para admins)
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/agents/audit-logs')
async def audit_logs_agentes(
    agent_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(require_admin),
):
    q: dict = {'source': 'mcp_agent'}
    if agent_id:
        q['agent_id'] = agent_id
    cursor = db.audit_logs.find(q, {'_id': 0}).sort('timestamp', -1).limit(limit)
    logs = [d async for d in cursor]
    return {'logs': logs, 'count': len(logs)}


# ──────────────────────────────────────────────────────────────────────────────
# Rate limit · gestión (admin)
# ──────────────────────────────────────────────────────────────────────────────

class UpdateLimitsRequest(BaseModel):
    soft_limit: int = Field(..., ge=1, le=10000)
    hard_limit: int = Field(..., ge=1, le=100000)


@router.get('/agents/rate-limits')
async def get_rate_limits(user: dict = Depends(require_admin)):
    """Lista la configuración actual de rate limit de todos los agentes."""
    cursor = db.mcp_agent_limits.find({}, {'_id': 0}).sort('agent_id', 1)
    limits = [d async for d in cursor]
    # Uso actual en ventana 60s
    from datetime import datetime as _dt, timezone as _tz
    now_epoch = _dt.now(_tz.utc).timestamp()
    for lim in limits:
        count = await db.mcp_rate_limits.count_documents({
            'agent_id': lim['agent_id'],
            'ts_epoch': {'$gte': now_epoch - 60},
        })
        lim['current_count_last_minute'] = count
    return {'agents': limits}


@router.put('/agents/{agent_id}/rate-limits')
async def update_rate_limits(
    agent_id: str,
    body: UpdateLimitsRequest,
    user: dict = Depends(require_admin),
):
    """Actualiza soft_limit / hard_limit de un agente. Invalida la cache."""
    from revix_mcp.rate_limit import set_limits
    if body.soft_limit > body.hard_limit:
        raise HTTPException(status_code=400, detail='soft_limit debe ser <= hard_limit')
    if not get_agent(agent_id):
        raise HTTPException(status_code=404, detail='Agente no existe')
    await set_limits(
        db, agent_id=agent_id,
        soft_limit=body.soft_limit, hard_limit=body.hard_limit,
    )
    return {
        'agent_id': agent_id,
        'soft_limit': body.soft_limit,
        'hard_limit': body.hard_limit,
        'updated': True,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Startup: sembrar límites por defecto de los agentes
# ──────────────────────────────────────────────────────────────────────────────

async def seed_agent_rate_limits_on_startup() -> None:
    """Sembra límites de rate-limit de los 3 agentes. Idempotente."""
    try:
        await seed_default_limits(db)
        logger.info('[agents] rate-limit defaults seeded')
    except Exception as e:  # noqa: BLE001
        logger.warning(f'[agents] no se pudo sembrar rate-limits: {e}')


# ──────────────────────────────────────────────────────────────────────────────
# Endpoint público del agente de seguimiento (sin auth)
# ──────────────────────────────────────────────────────────────────────────────

class PublicChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None  # mantiene memoria en el navegador


@router.post('/public/agents/seguimiento/chat')
async def chat_publico_seguimiento(body: PublicChatRequest):
    agent = get_agent('seguimiento_publico')
    if not agent:
        raise HTTPException(status_code=500, detail='Agente no configurado')

    session_id = body.session_id or str(uuid.uuid4())

    # Historial simple: solo para esta sesión pública (no asociada a usuario)
    cursor = db[AGENT_MESSAGES_COLL].find(
        {'session_id': session_id},
        {'_id': 0, 'role': 1, 'content': 1, 'tool_calls': 1, 'tool_call_id': 1, 'name': 1, 'seq': 1},
    ).sort('seq', 1).limit(40)  # cap para no saturar el prompt
    history = [m async for m in cursor]
    history_for_llm = []
    for m in history:
        entry = {'role': m['role'], 'content': m.get('content') or ''}
        if m.get('tool_calls'):
            entry['tool_calls'] = m['tool_calls']
        if m.get('tool_call_id'):
            entry['tool_call_id'] = m['tool_call_id']
        if m.get('name'):
            entry['name'] = m['name']
        history_for_llm.append(entry)

    try:
        result = await run_agent_turn(db, agent, history_for_llm, body.message)
    except ToolRateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail='Estamos recibiendo muchas consultas. Por favor, espera un '
                   'momento e intenta de nuevo.',
        ) from e
    except Exception:  # noqa: BLE001
        logger.exception('public agent turn failed')
        raise HTTPException(status_code=500, detail='Fallo del asistente. Intenta de nuevo en un momento.')

    base_seq = len(history)
    full_new = result['messages'][len(history_for_llm):]
    docs = []
    for i, m in enumerate(full_new):
        docs.append({
            'session_id': session_id,
            'agent_id': 'seguimiento_publico',
            'seq': base_seq + i,
            'role': m.get('role'),
            'content': m.get('content'),
            'tool_calls': m.get('tool_calls'),
            'tool_call_id': m.get('tool_call_id'),
            'name': m.get('name'),
            'created_at': _now_iso(),
            'public': True,
        })
    if docs:
        await db[AGENT_MESSAGES_COLL].insert_many(docs)

    return {
        'session_id': session_id,
        'reply': result['reply'],
        'duration_ms': result['duration_ms'],
    }

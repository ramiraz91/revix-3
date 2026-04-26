"""
Panel avanzado de agentes (`/crm/agentes`).

Endpoints agregados al conjunto /api/agents/* existente:

  GET  /api/agents/panel/overview             — estado global de todos los agentes
  POST /api/agents/{id}/pause                 — pausa agente (no permite nuevas ejecuciones)
  POST /api/agents/{id}/activate              — reactiva agente
  GET  /api/agents/{id}/timeline              — timeline de audit logs del agente (filtrable)
  GET  /api/agents/{id}/config                — config completa (rate limits + prompt + overrides)
  POST /api/agents/{id}/config                — update rate limits y/o system prompt
  GET  /api/agents/panel/metrics?days=7       — métricas globales (éxito, top tools, errores)
  GET  /api/agents/panel/pending-approvals    — cola de aprobación (placeholder si no hay colección)

Requiere rol admin/master en todo. El audit queda en `audit_logs` y los overrides
de agente en `agent_overrides`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from config import db
from auth import require_auth, require_admin

from .agent_defs import AGENTS, get_agent

logger = logging.getLogger('revix.agents.panel')

router = APIRouter(tags=['agents-panel'])

AGENT_STATES_COLL = 'agent_states'           # { agent_id, estado, pausado_por, updated_at }
AGENT_OVERRIDES_COLL = 'agent_overrides'     # { agent_id, system_prompt, updated_at, updated_by, history[] }
AUDIT_COLL = 'audit_logs'
RATE_LIMITS_COLL = 'mcp_rate_limits'
PENDING_APPROVALS_COLL = 'agent_pending_approvals'


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


async def _get_agent_state(agent_id: str) -> dict:
    doc = await db[AGENT_STATES_COLL].find_one({'agent_id': agent_id}, {'_id': 0})
    return doc or {'agent_id': agent_id, 'estado': 'activo'}


async def _get_agent_stats(agent_id: str, *, since: datetime) -> dict:
    """Stats de actividad del agente desde `since`."""
    match = {'agent_id': agent_id, 'timestamp_dt': {'$gte': since}}
    pipeline = [
        {'$match': match},
        {'$group': {
            '_id': None,
            'total': {'$sum': 1},
            'con_error': {'$sum': {'$cond': [{'$ne': ['$error', None]}, 1, 0]}},
            'dur_media': {'$avg': '$duration_ms'},
            'ultima': {'$max': '$timestamp_dt'},
        }},
    ]
    r = await db[AUDIT_COLL].aggregate(pipeline).to_list(1)
    if not r:
        return {'total': 0, 'con_error': 0, 'ultima': None, 'dur_media': 0,
                'tasa_exito': 100.0}
    d = r[0]
    total = d['total']
    err = d['con_error']
    return {
        'total': total,
        'con_error': err,
        'tasa_exito': round((total - err) / total * 100, 1) if total else 100.0,
        'dur_media': int(d.get('dur_media') or 0),
        'ultima': d['ultima'].isoformat() if d.get('ultima') else None,
    }


async def _get_ultima_accion(agent_id: str) -> Optional[dict]:
    doc = await db[AUDIT_COLL].find_one(
        {'agent_id': agent_id},
        {'_id': 0, 'tool': 1, 'timestamp': 1, 'error': 1, 'duration_ms': 1},
        sort=[('timestamp_dt', -1)],
    )
    return doc


# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════

class AgentCardStats(BaseModel):
    agent_id: str
    nombre: str
    descripcion: str
    emoji: str
    color: str
    estado: str                 # activo | pausado | error
    pausado_por: Optional[str] = None
    tools_count: int
    tools: list[str] = Field(default_factory=list)
    scopes: list[str]
    acciones_hoy: int
    tasa_exito_7d: float
    duracion_media_ms: int
    ultima_accion: Optional[dict] = None
    errores_24h: int


@router.get('/agents/panel/overview')
async def panel_overview(user: dict = Depends(require_auth)):
    now = datetime.now(timezone.utc)
    hoy_inicio = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hace_7d = now - timedelta(days=7)
    hace_24h = now - timedelta(hours=24)

    cards: list[AgentCardStats] = []
    for agent_id, a in AGENTS.items():
        state = await _get_agent_state(agent_id)
        stats_7d = await _get_agent_stats(agent_id, since=hace_7d)
        accs_hoy_r = await db[AUDIT_COLL].count_documents(
            {'agent_id': agent_id, 'timestamp_dt': {'$gte': hoy_inicio}},
        )
        errores_24h = await db[AUDIT_COLL].count_documents(
            {'agent_id': agent_id, 'timestamp_dt': {'$gte': hace_24h},
             'error': {'$ne': None}},
        )
        ultima = await _get_ultima_accion(agent_id)

        estado = state.get('estado', 'activo')
        # Detección de "error" por alta tasa de errores en 24h
        if estado == 'activo' and errores_24h > 10:
            estado = 'error'

        cards.append(AgentCardStats(
            agent_id=agent_id,
            nombre=a.nombre,
            descripcion=a.descripcion,
            emoji=getattr(a, 'emoji', '🤖'),
            color=getattr(a, 'color', '#6366f1'),
            estado=estado,
            pausado_por=state.get('pausado_por'),
            tools_count=len(a.tools),
            tools=list(a.tools),
            scopes=list(a.scopes),
            acciones_hoy=accs_hoy_r,
            tasa_exito_7d=stats_7d['tasa_exito'],
            duracion_media_ms=stats_7d['dur_media'],
            ultima_accion=ultima,
            errores_24h=errores_24h,
        ))

    # Métricas globales arriba
    total_hoy = sum(c.acciones_hoy for c in cards)
    total_errores_24h = sum(c.errores_24h for c in cards)
    mas_activo = max(cards, key=lambda c: c.acciones_hoy, default=None)

    # Pending approvals count
    pending_count = await db[PENDING_APPROVALS_COLL].count_documents({'estado': 'pendiente'})
    # Scheduled tasks próximas 24h
    proximas_24h = await db.scheduled_tasks.count_documents({
        'estado': {'$in': ['activa', 'active']},
        'proxima_ejecucion': {'$lte': (now + timedelta(hours=24)).isoformat()},
    })

    return {
        'agents': [c.model_dump() for c in cards],
        'resumen': {
            'total_agentes': len(cards),
            'acciones_hoy': total_hoy,
            'errores_24h': total_errores_24h,
            'agente_mas_activo': mas_activo.agent_id if mas_activo else None,
            'aprobaciones_pendientes': pending_count,
            'tareas_proximas_24h': proximas_24h,
        },
        'generado_at': now.isoformat(timespec='seconds'),
    }


# ══════════════════════════════════════════════════════════════════════════════
# PAUSE / ACTIVATE
# ══════════════════════════════════════════════════════════════════════════════

def _check_master(user: dict) -> None:
    """Solo el rol 'master' o 'admin' puede pausar/editar agentes."""
    r = user.get('role') or user.get('rol')
    if r not in ('master', 'admin'):
        raise HTTPException(403, 'Solo master/admin puede modificar agentes')


@router.post('/agents/{agent_id}/pause')
async def pausar_agente(agent_id: str, user: dict = Depends(require_admin)):
    _check_master(user)
    if agent_id not in AGENTS:
        raise HTTPException(404, f'Agente {agent_id} no encontrado')
    await db[AGENT_STATES_COLL].update_one(
        {'agent_id': agent_id},
        {'$set': {
            'agent_id': agent_id, 'estado': 'pausado',
            'pausado_por': user.get('email'),
            'updated_at': _now_iso(),
        }},
        upsert=True,
    )
    return {'ok': True, 'agent_id': agent_id, 'estado': 'pausado'}


@router.post('/agents/{agent_id}/activate')
async def activar_agente(agent_id: str, user: dict = Depends(require_admin)):
    _check_master(user)
    if agent_id not in AGENTS:
        raise HTTPException(404, f'Agente {agent_id} no encontrado')
    await db[AGENT_STATES_COLL].update_one(
        {'agent_id': agent_id},
        {'$set': {
            'agent_id': agent_id, 'estado': 'activo',
            'pausado_por': None,
            'updated_at': _now_iso(),
        }},
        upsert=True,
    )
    return {'ok': True, 'agent_id': agent_id, 'estado': 'activo'}


# ══════════════════════════════════════════════════════════════════════════════
# TIMELINE de actividad
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/agents/{agent_id}/timeline')
async def agent_timeline(
    agent_id: str,
    limit: int = Query(100, ge=1, le=500),
    tool: Optional[str] = None,
    resultado: Optional[str] = Query(None, description='ok|error|all'),
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    user: dict = Depends(require_auth),
):
    if agent_id not in AGENTS:
        raise HTTPException(404, 'Agente no encontrado')
    q: dict = {'agent_id': agent_id}
    if tool:
        q['tool'] = tool
    if resultado == 'error':
        q['error'] = {'$ne': None}
    elif resultado == 'ok':
        q['error'] = None
    if desde or hasta:
        ts = {}
        if desde:
            ts['$gte'] = desde
        if hasta:
            ts['$lte'] = hasta
        q['timestamp'] = ts
    items = await db[AUDIT_COLL].find(
        q, {'_id': 0, 'timestamp_dt': 0},
    ).sort('timestamp', -1).limit(limit).to_list(limit)
    return {'items': items, 'total': len(items)}


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG (rate limits + system prompt)
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/agents/{agent_id}/config')
async def get_agent_config(agent_id: str, user: dict = Depends(require_auth)):
    a = get_agent(agent_id)
    if not a:
        raise HTTPException(404, 'Agente no encontrado')
    rate = await db[RATE_LIMITS_COLL].find_one(
        {'agent_id': agent_id}, {'_id': 0, 'soft_limit': 1, 'hard_limit': 1},
    ) or {}
    override = await db[AGENT_OVERRIDES_COLL].find_one(
        {'agent_id': agent_id},
        {'_id': 0, 'system_prompt': 1, 'updated_at': 1, 'updated_by': 1,
         'history': {'$slice': -10}},
    ) or {}
    return {
        'agent_id': agent_id,
        'nombre': a.nombre,
        'system_prompt_default': a.system_prompt,
        'system_prompt_effective': override.get('system_prompt') or a.system_prompt,
        'system_prompt_override': bool(override.get('system_prompt')),
        'rate_limit_soft': rate.get('soft_limit', 120),
        'rate_limit_hard': rate.get('hard_limit', 600),
        'updated_at': override.get('updated_at'),
        'updated_by': override.get('updated_by'),
        'history': override.get('history', []),
        'scopes': list(a.scopes),
        'tools': list(a.tools),
    }


class AgentConfigUpdate(BaseModel):
    rate_limit_soft: Optional[int] = Field(None, ge=1, le=100_000)
    rate_limit_hard: Optional[int] = Field(None, ge=1, le=100_000)
    system_prompt: Optional[str] = Field(None, max_length=20_000)


@router.post('/agents/{agent_id}/config')
async def set_agent_config(
    agent_id: str, payload: AgentConfigUpdate,
    user: dict = Depends(require_admin),
):
    _check_master(user)
    a = get_agent(agent_id)
    if not a:
        raise HTTPException(404, 'Agente no encontrado')
    now = _now_iso()
    changes = []

    # Rate limits
    if payload.rate_limit_soft is not None or payload.rate_limit_hard is not None:
        current = await db[RATE_LIMITS_COLL].find_one({'agent_id': agent_id}, {'_id': 0})
        soft = payload.rate_limit_soft if payload.rate_limit_soft is not None \
            else (current or {}).get('soft_limit', 120)
        hard = payload.rate_limit_hard if payload.rate_limit_hard is not None \
            else (current or {}).get('hard_limit', 600)
        if hard < soft:
            raise HTTPException(400, 'hard_limit debe ser >= soft_limit')
        await db[RATE_LIMITS_COLL].update_one(
            {'agent_id': agent_id},
            {'$set': {
                'agent_id': agent_id,
                'soft_limit': int(soft), 'hard_limit': int(hard),
                'updated_at': now, 'updated_by': user.get('email'),
            }},
            upsert=True,
        )
        changes.append(f'rate limits → {soft}/{hard}')
        # invalidar cache
        try:
            import sys as _s
            _s.path.insert(0, '/app')
            from revix_mcp.rate_limit import invalidate_limits_cache
            invalidate_limits_cache()
        except Exception:
            pass

    # System prompt
    if payload.system_prompt is not None:
        await db[AGENT_OVERRIDES_COLL].update_one(
            {'agent_id': agent_id},
            {
                '$set': {
                    'agent_id': agent_id,
                    'system_prompt': payload.system_prompt,
                    'updated_at': now, 'updated_by': user.get('email'),
                },
                '$push': {
                    'history': {
                        'prompt': payload.system_prompt[:1000],  # snippet
                        'at': now, 'by': user.get('email'),
                    },
                },
            },
            upsert=True,
        )
        changes.append('system_prompt actualizado')

    # Audit log en audit_logs (como cualquier cambio)
    await db[AUDIT_COLL].insert_one({
        'source': 'admin_panel',
        'agent_id': agent_id,
        'tool': '_config_update',
        'params': {'changes': changes},
        'result_summary': None, 'error': None,
        'duration_ms': 0, 'timestamp': now,
        'timestamp_dt': datetime.now(timezone.utc),
        'actor': user.get('email'),
    })

    return {'ok': True, 'agent_id': agent_id, 'changes': changes}


# ══════════════════════════════════════════════════════════════════════════════
# MÉTRICAS globales
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/agents/panel/metrics')
async def panel_metrics(days: int = Query(7, ge=1, le=30),
                        user: dict = Depends(require_auth)):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Acciones por agente
    por_agente = await db[AUDIT_COLL].aggregate([
        {'$match': {'timestamp_dt': {'$gte': since}}},
        {'$group': {
            '_id': '$agent_id',
            'total': {'$sum': 1},
            'errores': {'$sum': {'$cond': [{'$ne': ['$error', None]}, 1, 0]}},
            'dur_media': {'$avg': '$duration_ms'},
        }},
        {'$sort': {'total': -1}},
    ]).to_list(20)

    # Tools más utilizadas
    top_tools = await db[AUDIT_COLL].aggregate([
        {'$match': {'timestamp_dt': {'$gte': since}}},
        {'$group': {'_id': {'agent': '$agent_id', 'tool': '$tool'},
                    'total': {'$sum': 1}}},
        {'$sort': {'total': -1}},
        {'$limit': 15},
    ]).to_list(15)

    # Acciones por día (gráfico)
    por_dia = await db[AUDIT_COLL].aggregate([
        {'$match': {'timestamp_dt': {'$gte': since}}},
        {'$group': {
            '_id': {
                'fecha': {'$dateToString': {'format': '%Y-%m-%d',
                                            'date': '$timestamp_dt'}},
                'agent': '$agent_id',
            },
            'total': {'$sum': 1},
        }},
        {'$sort': {'_id.fecha': 1}},
    ]).to_list(500)

    # Errores más frecuentes
    top_errors = await db[AUDIT_COLL].aggregate([
        {'$match': {'timestamp_dt': {'$gte': since}, 'error': {'$ne': None}}},
        {'$group': {'_id': '$error', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 10},
    ]).to_list(10)

    return {
        'desde': since.isoformat(timespec='seconds'),
        'dias': days,
        'por_agente': [
            {
                'agent_id': d['_id'],
                'total': d['total'],
                'errores': d['errores'],
                'tasa_exito': round((d['total'] - d['errores']) / d['total'] * 100, 1)
                              if d['total'] else 100.0,
                'dur_media_ms': int(d.get('dur_media') or 0),
            }
            for d in por_agente
        ],
        'top_tools': [
            {'agent_id': d['_id']['agent'], 'tool': d['_id']['tool'],
             'total': d['total']}
            for d in top_tools
        ],
        'por_dia': [
            {'fecha': d['_id']['fecha'], 'agent_id': d['_id']['agent'],
             'total': d['total']}
            for d in por_dia
        ],
        'top_errors': [
            {'error': d['_id'][:200] if d['_id'] else 'sin_mensaje',
             'count': d['count']}
            for d in top_errors
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
# PENDING APPROVALS (cola)
# ══════════════════════════════════════════════════════════════════════════════

class PendingApprovalItem(BaseModel):
    id: str
    agent_id: str
    tool: str
    params: dict
    impacto_estimado: Optional[str] = None
    solicitado_en: str
    solicitado_por_key_id: Optional[str] = None
    estado: str = 'pendiente'


@router.get('/agents/panel/pending-approvals')
async def listar_pending_approvals(user: dict = Depends(require_auth)):
    items = await db[PENDING_APPROVALS_COLL].find(
        {'estado': 'pendiente'}, {'_id': 0},
    ).sort('solicitado_en', -1).to_list(100)
    return {'items': items, 'total': len(items)}


class ApprovalDecision(BaseModel):
    decision: str = Field(..., pattern='^(aprobar|rechazar|modificar)$')
    motivo: Optional[str] = None
    params_modificados: Optional[dict] = None


@router.post('/agents/panel/pending-approvals/{approval_id}/decide')
async def decidir_aprobacion(
    approval_id: str, body: ApprovalDecision,
    user: dict = Depends(require_admin),
):
    _check_master(user)
    existing = await db[PENDING_APPROVALS_COLL].find_one(
        {'id': approval_id}, {'_id': 0},
    )
    if not existing:
        raise HTTPException(404, 'Aprobación no encontrada')
    if existing.get('estado') != 'pendiente':
        raise HTTPException(400, f'Aprobación ya en estado {existing.get("estado")}')

    estado_nuevo = {
        'aprobar': 'aprobada', 'rechazar': 'rechazada',
        'modificar': 'modificada',
    }[body.decision]
    update = {
        'estado': estado_nuevo,
        'decidido_por': user.get('email'),
        'decidido_en': _now_iso(),
        'motivo': body.motivo,
    }
    if body.decision == 'modificar' and body.params_modificados is not None:
        update['params'] = body.params_modificados
    await db[PENDING_APPROVALS_COLL].update_one(
        {'id': approval_id}, {'$set': update},
    )
    return {'ok': True, 'approval_id': approval_id, 'estado': estado_nuevo}

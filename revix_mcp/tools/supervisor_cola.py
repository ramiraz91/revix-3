"""
Revix MCP · Tools Fase 2 — Agente Supervisor de Cola Operacional (WRITE).

4 tools:
  1. listar_ordenes_en_riesgo_sla  (read)
  2. marcar_orden_en_riesgo        (write · idempotente)
  3. abrir_incidencia              (write · idempotente · anti-duplicado)
  4. enviar_notificacion           (write · mock en preview)

Todas quedan auditadas por el runtime (audit_logs source='mcp_agent').
Las dos con idempotency_key se cachean en `mcp_idempotency` → reintento seguro.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..auth import AgentIdentity, AuthError, require_scope
from ..config import MCP_ENV
from ._registry import ToolSpec, register
from ._common import validate_input


# ──────────────────────────────────────────────────────────────────────────────
# Constantes del semáforo SLA
# ──────────────────────────────────────────────────────────────────────────────

# Estados de órdenes que están "vivas" (cuenta para SLA)
_ESTADOS_ACTIVOS = [
    'recibido', 'diagnosticando', 'presupuesto_emitido',
    'aprobado', 'reparando', 'reparado',
]

# Umbrales por defecto en horas hasta vencer SLA
_UMBRAL_ROJO_DEFAULT = 24
_UMBRAL_AMARILLO_DEFAULT = 72


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _parse_dt(v) -> Optional[datetime]:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None


# ──────────────────────────────────────────────────────────────────────────────
# 1. listar_ordenes_en_riesgo_sla
# ──────────────────────────────────────────────────────────────────────────────

class ListarOrdenesRiesgoInput(BaseModel):
    umbral_horas: Optional[int] = Field(
        None, ge=1, le=720,
        description='Horas hasta vencer para considerar riesgo. Default: 72 (amarillo)',
    )
    limit: int = Field(100, ge=1, le=500)


def _calcular_riesgo(
    orden: dict, now: datetime, umbral_horas: int,
) -> Optional[dict]:
    """Calcula el nivel de riesgo de una orden. None si no está en riesgo."""
    created = _parse_dt(orden.get('created_at'))
    if not created:
        return None
    sla_dias = int(orden.get('sla_dias') or 5)
    deadline = created + timedelta(days=sla_dias)
    horas_restantes = (deadline - now).total_seconds() / 3600.0

    if horas_restantes <= 0:
        nivel = 'critico'
    elif horas_restantes <= _UMBRAL_ROJO_DEFAULT:
        nivel = 'rojo'
    elif horas_restantes <= umbral_horas:
        nivel = 'amarillo'
    else:
        return None

    return {
        'nivel_riesgo': nivel,
        'horas_restantes': round(horas_restantes, 1),
        'deadline': deadline.isoformat(timespec='seconds'),
    }


async def _listar_ordenes_riesgo_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(ListarOrdenesRiesgoInput, params)
    umbral = p.umbral_horas or _UMBRAL_AMARILLO_DEFAULT
    now = datetime.now(timezone.utc)

    projection = {
        '_id': 0, 'id': 1, 'numero_orden': 1, 'estado': 1,
        'cliente_id': 1, 'tecnico_asignado': 1,
        'dispositivo.marca': 1, 'dispositivo.modelo': 1,
        'sla_dias': 1, 'alerta_sla_enviada': 1,
        'created_at': 1, 'updated_at': 1,
        'marcado_riesgo': 1, 'nivel_riesgo_actual': 1,
    }
    cursor = db.ordenes.find(
        {'estado': {'$in': _ESTADOS_ACTIVOS}},
        projection,
    )

    resultado: list[dict] = []
    async for o in cursor:
        riesgo = _calcular_riesgo(o, now, umbral)
        if not riesgo:
            continue
        o.update(riesgo)
        resultado.append(o)

    # Orden por prioridad (critico > rojo > amarillo) + por horas restantes
    orden_sev = {'critico': 0, 'rojo': 1, 'amarillo': 2}
    resultado.sort(key=lambda x: (orden_sev[x['nivel_riesgo']], x['horas_restantes']))
    resultado = resultado[:p.limit]

    resumen = {'critico': 0, 'rojo': 0, 'amarillo': 0}
    for r in resultado:
        resumen[r['nivel_riesgo']] += 1

    return {
        'total': len(resultado),
        'umbral_horas_amarillo': umbral,
        'resumen': resumen,
        'items': resultado,
    }


register(ToolSpec(
    name='listar_ordenes_en_riesgo_sla',
    description=(
        'Lista las órdenes activas en riesgo de incumplir SLA, ordenadas por '
        'severidad: crítico (fuera de SLA) > rojo (<24h) > amarillo (<umbral, '
        'default 72h). Devuelve horas restantes, deadline, estado y dispositivo. '
        'Pensado para que el Supervisor de Cola priorice el trabajo del día.'
    ),
    required_scope='orders:read',
    input_schema={
        'type': 'object',
        'properties': {
            'umbral_horas': {
                'type': 'integer', 'minimum': 1, 'maximum': 720,
                'description': 'Horas hasta vencer para nivel amarillo (default 72).',
            },
            'limit': {'type': 'integer', 'minimum': 1, 'maximum': 500, 'default': 100},
        },
        'additionalProperties': False,
    },
    handler=_listar_ordenes_riesgo_handler,
))


# ──────────────────────────────────────────────────────────────────────────────
# 2. marcar_orden_en_riesgo
# ──────────────────────────────────────────────────────────────────────────────

class MarcarOrdenRiesgoInput(BaseModel):
    order_id: str = Field(..., min_length=1)
    nivel_riesgo: Literal['amarillo', 'rojo', 'critico']
    motivo: str = Field(..., min_length=3, max_length=500)


async def _marcar_orden_riesgo_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    # Requisito: double scope (orders:read + incidents:write)
    # El registry valida 'incidents:write' (required_scope); añadimos 'orders:read' aquí
    if not identity.has_scope('orders:read'):
        raise AuthError(
            f'Scope requerido "orders:read" no presente en agente "{identity.agent_id}" '
            f'(tool marcar_orden_en_riesgo requiere orders:read + incidents:write)'
        )

    p = validate_input(MarcarOrdenRiesgoInput, params)
    now_iso = _now_iso()

    # Verificar que la orden existe
    orden = await db.ordenes.find_one(
        {'id': p.order_id},
        {'_id': 0, 'id': 1, 'numero_orden': 1, 'nivel_riesgo_actual': 1},
    )
    if not orden:
        return {'success': False, 'error': 'order_not_found', 'order_id': p.order_id}

    # Actualizar la orden + guardar trail en `orden.historial_riesgo`
    await db.ordenes.update_one(
        {'id': p.order_id},
        {
            '$set': {
                'nivel_riesgo_actual': p.nivel_riesgo,
                'marcado_riesgo_motivo': p.motivo,
                'marcado_riesgo_por': f'mcp:{identity.agent_id}',
                'marcado_riesgo_fecha': now_iso,
                'updated_at': now_iso,
            },
            '$push': {
                'historial_riesgo': {
                    'nivel': p.nivel_riesgo,
                    'motivo': p.motivo,
                    'fecha': now_iso,
                    'agent': identity.agent_id,
                },
            },
        },
    )

    return {
        'success': True,
        'order_id': p.order_id,
        'numero_orden': orden.get('numero_orden'),
        'nivel_riesgo_previo': orden.get('nivel_riesgo_actual'),
        'nivel_riesgo_nuevo': p.nivel_riesgo,
        'marcado_en': now_iso,
    }


register(ToolSpec(
    name='marcar_orden_en_riesgo',
    description=(
        'Marca una orden con un nivel de riesgo SLA (amarillo/rojo/crítico) y '
        'registra el motivo. Actualiza la orden e añade un entry al historial '
        'de riesgo. Requiere idempotency_key (el mismo key no re-ejecuta). '
        'Scopes necesarios: orders:read + incidents:write.'
    ),
    required_scope='incidents:write',
    input_schema={
        'type': 'object',
        'properties': {
            'order_id': {'type': 'string'},
            'nivel_riesgo': {'type': 'string', 'enum': ['amarillo', 'rojo', 'critico']},
            'motivo': {'type': 'string', 'minLength': 3, 'maxLength': 500},
            '_idempotency_key': {
                'type': 'string',
                'description': 'Obligatorio: evita re-ejecución ante reintentos',
            },
        },
        'required': ['order_id', 'nivel_riesgo', 'motivo', '_idempotency_key'],
        'additionalProperties': False,
    },
    handler=_marcar_orden_riesgo_handler,
    writes=True,
))


# ──────────────────────────────────────────────────────────────────────────────
# 3. abrir_incidencia
# ──────────────────────────────────────────────────────────────────────────────

class AbrirIncidenciaInput(BaseModel):
    order_id: str = Field(..., min_length=1)
    tipo_incidencia: str = Field(..., min_length=2, max_length=60)
    descripcion: str = Field(..., min_length=3, max_length=1000)
    prioridad: Literal['baja', 'media', 'alta'] = 'media'


async def _abrir_incidencia_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(AbrirIncidenciaInput, params)
    now_iso = _now_iso()

    # 1) Orden existe
    orden = await db.ordenes.find_one(
        {'id': p.order_id},
        {'_id': 0, 'id': 1, 'numero_orden': 1, 'cliente_id': 1},
    )
    if not orden:
        return {'success': False, 'error': 'order_not_found', 'order_id': p.order_id}

    # 2) Anti-duplicado: hay ya una incidencia abierta para esta orden?
    existente = await db.incidencias.find_one(
        {'orden_id': p.order_id, 'estado': 'abierta'},
        {'_id': 0, 'id': 1, 'numero_incidencia': 1, 'tipo': 1, 'created_at': 1},
    )
    if existente:
        ref = existente.get('numero_incidencia') or existente.get('id', '¿?')
        return {
            'success': False,
            'error': 'incidencia_abierta_ya_existe',
            'order_id': p.order_id,
            'incidencia_existente': existente,
            'message': (
                f'Ya hay una incidencia abierta ({ref}) '
                f'para esta orden. Ciérrala antes de abrir otra.'
            ),
        }

    # 3) Crear
    fecha_corta = datetime.now(timezone.utc).strftime('%Y%m%d')
    numero_incidencia = f'INC-{fecha_corta}-{str(uuid.uuid4())[:6].upper()}'
    incidencia_id = str(uuid.uuid4())
    titulo_auto = f'{p.tipo_incidencia.replace("_", " ").title()} · {orden.get("numero_orden", p.order_id[:8])}'

    doc = {
        'id': incidencia_id,
        'numero_incidencia': numero_incidencia,
        'cliente_id': orden.get('cliente_id') or '',
        'orden_id': p.order_id,
        'tipo': p.tipo_incidencia,
        'titulo': titulo_auto,
        'descripcion': p.descripcion,
        'prioridad': p.prioridad,
        'estado': 'abierta',
        'created_at': now_iso,
        'updated_at': now_iso,
        'created_by': f'mcp:{identity.agent_id}',
        'source': 'mcp_agent',
    }
    await db.incidencias.insert_one(dict(doc))

    return {
        'success': True,
        'incidencia_id': incidencia_id,
        'numero_incidencia': numero_incidencia,
        'order_id': p.order_id,
        'estado': 'abierta',
        'prioridad': p.prioridad,
        'created_at': now_iso,
    }


register(ToolSpec(
    name='abrir_incidencia',
    description=(
        'Abre una incidencia asociada a una orden. Si ya existe una incidencia '
        'abierta para la misma orden, NO crea otra (devuelve success=false con '
        '`incidencia_abierta_ya_existe`). Requiere idempotency_key. '
        'Tipos recomendados: retraso_proveedor, averia_secundaria, cliente_no_responde, '
        'material_incorrecto, calidad_reparacion, logistica.'
    ),
    required_scope='incidents:write',
    input_schema={
        'type': 'object',
        'properties': {
            'order_id': {'type': 'string'},
            'tipo_incidencia': {'type': 'string', 'minLength': 2, 'maxLength': 60},
            'descripcion': {'type': 'string', 'minLength': 3, 'maxLength': 1000},
            'prioridad': {'type': 'string', 'enum': ['baja', 'media', 'alta'], 'default': 'media'},
            '_idempotency_key': {'type': 'string', 'description': 'Obligatorio'},
        },
        'required': ['order_id', 'tipo_incidencia', 'descripcion', '_idempotency_key'],
        'additionalProperties': False,
    },
    handler=_abrir_incidencia_handler,
    writes=True,
))


# ──────────────────────────────────────────────────────────────────────────────
# 4. enviar_notificacion
# ──────────────────────────────────────────────────────────────────────────────

class EnviarNotificacionInput(BaseModel):
    destinatario_id: str = Field(..., min_length=1, description='UUID de usuario/técnico destinatario')
    canal: Literal['interno', 'email'] = 'interno'
    mensaje: str = Field(..., min_length=1, max_length=1000)
    referencia_orden: str = Field(..., min_length=1, description='UUID o numero_orden de la orden referenciada')


async def _enviar_notificacion_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(EnviarNotificacionInput, params)
    now_iso = _now_iso()
    preview_mode = MCP_ENV == 'preview'

    mensaje_final = f'[PREVIEW] {p.mensaje}' if preview_mode else p.mensaje

    doc = {
        'id': str(uuid.uuid4()),
        'tipo': f'mcp_{p.canal}',
        'mensaje': mensaje_final,
        'orden_id': p.referencia_orden,
        'usuario_destino': p.destinatario_id,
        'leida': False,
        'created_at': now_iso,
        'source': 'mcp_agent',
        'agent_id': identity.agent_id,
        'canal': p.canal,
        'preview_mock': preview_mode,
    }

    # Siempre persistimos como notificación interna (fácil de auditar)
    await db.notificaciones.insert_one(dict(doc))

    if preview_mode and p.canal == 'email':
        return {
            'success': True,
            'preview': True,
            'message': '[PREVIEW] Email NO enviado (entorno preview). Notificación interna creada como trazabilidad.',
            'notificacion_id': doc['id'],
            'canal_solicitado': p.canal,
            'destinatario_id': p.destinatario_id,
            'referencia_orden': p.referencia_orden,
            'mensaje_preview': mensaje_final,
        }

    # En producción: aquí se integraría Resend/Email real cuando MCP_ENV=production
    # (queda como TODO explícito para Fase 2.1)
    return {
        'success': True,
        'preview': False,
        'notificacion_id': doc['id'],
        'canal': p.canal,
        'destinatario_id': p.destinatario_id,
        'referencia_orden': p.referencia_orden,
        'created_at': now_iso,
    }


register(ToolSpec(
    name='enviar_notificacion',
    description=(
        'Envía una notificación (interna o email) a un usuario del sistema '
        'asociada a una orden. En entorno preview (MCP_ENV=preview) NO envía '
        'emails reales: crea una notificación interna con prefijo [PREVIEW] '
        'y devuelve success con `preview=true`.'
    ),
    required_scope='notifications:write',
    input_schema={
        'type': 'object',
        'properties': {
            'destinatario_id': {'type': 'string', 'description': 'UUID del usuario destinatario'},
            'canal': {'type': 'string', 'enum': ['interno', 'email'], 'default': 'interno'},
            'mensaje': {'type': 'string', 'minLength': 1, 'maxLength': 1000},
            'referencia_orden': {'type': 'string', 'description': 'UUID o numero_orden'},
            '_idempotency_key': {'type': 'string', 'description': 'Opcional: evita reenvío en reintentos'},
        },
        'required': ['destinatario_id', 'canal', 'mensaje', 'referencia_orden'],
        'additionalProperties': False,
    },
    handler=_enviar_notificacion_handler,
    writes=True,
))

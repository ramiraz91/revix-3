"""
Tool de seguimiento público por token · read-only.

Usada por el agente `seguimiento_publico` (widget chat del cliente final).
Devuelve SOLO información mínima apta para el cliente: estado, fechas,
número de orden. Nunca expone datos internos (costes, beneficio, datos
de técnico, materiales con coste, etc.).

El scope `public:track_by_token` es específico — no está cubierto por `*:read`
porque el endpoint es público-restringido: `*:read` NO garantiza acceso aquí.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..auth import AgentIdentity
from ._registry import ToolSpec, register
from ._common import validate_input


class BuscarPorTokenInput(BaseModel):
    token: str = Field(..., min_length=4, description='token_seguimiento de la orden')


# Estados -> texto amable al cliente
_ESTADO_PUBLICO = {
    'pendiente_recibir': 'Pendiente de recibir el dispositivo',
    'recibido': 'Dispositivo recibido en taller',
    'diagnosticando': 'En diagnóstico',
    'presupuesto_emitido': 'Presupuesto enviado, esperando respuesta',
    'aprobado': 'Aprobado · iniciando reparación',
    'reparando': 'En reparación',
    'reparado': 'Reparado · preparando envío',
    'enviado': 'Enviado al cliente',
    'rechazado': 'Presupuesto rechazado',
    'no_reparable': 'No reparable',
}


async def _tracking_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(BuscarPorTokenInput, params)
    token = p.token.strip().upper()

    projection = {
        '_id': 0,
        'numero_orden': 1,
        'estado': 1,
        'es_garantia': 1,
        'dispositivo.marca': 1,
        'dispositivo.modelo': 1,
        'created_at': 1,
        'updated_at': 1,
        'fecha_recibida_centro': 1,
        'fecha_inicio_reparacion': 1,
        'fecha_fin_reparacion': 1,
        'fecha_enviado': 1,
        'fecha_estimada_entrega': 1,
        'presupuesto_emitido': 1,
        'presupuesto_precio': 1,
        'presupuesto_aceptado': 1,
    }
    doc = await db.ordenes.find_one({'token_seguimiento': token}, projection)
    if not doc:
        return {'found': False}

    estado = doc.get('estado') or 'desconocido'
    return {
        'found': True,
        'numero_orden': doc.get('numero_orden'),
        'estado': estado,
        'estado_texto': _ESTADO_PUBLICO.get(estado, estado.replace('_', ' ').capitalize()),
        'es_garantia': bool(doc.get('es_garantia')),
        'dispositivo': {
            'marca': (doc.get('dispositivo') or {}).get('marca'),
            'modelo': (doc.get('dispositivo') or {}).get('modelo'),
        },
        'fechas': {
            'creada': doc.get('created_at'),
            'recibida': doc.get('fecha_recibida_centro'),
            'reparacion_inicio': doc.get('fecha_inicio_reparacion'),
            'reparacion_fin': doc.get('fecha_fin_reparacion'),
            'enviado': doc.get('fecha_enviado'),
            'estimada_entrega': doc.get('fecha_estimada_entrega'),
            'ultima_actualizacion': doc.get('updated_at'),
        },
        'presupuesto': {
            'emitido': bool(doc.get('presupuesto_emitido')),
            'precio': doc.get('presupuesto_precio'),
            'aceptado': doc.get('presupuesto_aceptado'),
        } if doc.get('presupuesto_emitido') else None,
    }


register(ToolSpec(
    name='buscar_por_token_seguimiento',
    description=(
        'Consulta pública del estado de una orden a partir de su token de seguimiento '
        '(12 caracteres, case-insensitive). Devuelve solo información apta para el '
        'cliente final: estado, fechas clave, dispositivo y presupuesto si fue emitido. '
        'No expone costes, beneficios, materiales ni técnico asignado.'
    ),
    required_scope='public:track_by_token',
    input_schema={
        'type': 'object',
        'properties': {
            'token': {'type': 'string', 'minLength': 4},
        },
        'required': ['token'],
        'additionalProperties': False,
    },
    handler=_tracking_handler,
))

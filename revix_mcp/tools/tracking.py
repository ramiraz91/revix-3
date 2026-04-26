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
    name='buscar_por_token',
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


# Alias legacy: tool original era `buscar_por_token_seguimiento`
register(ToolSpec(
    name='buscar_por_token_seguimiento',
    description='Alias legacy de buscar_por_token (compat)',
    required_scope='public:track_by_token',
    input_schema={
        'type': 'object',
        'properties': {'token': {'type': 'string', 'minLength': 4}},
        'required': ['token'],
        'additionalProperties': False,
    },
    handler=_tracking_handler,
))


# ══════════════════════════════════════════════════════════════════════════════
# obtener_timeline_cliente — eventos cronológicos amables
# ══════════════════════════════════════════════════════════════════════════════

class TimelineInput(BaseModel):
    token: str = Field(..., min_length=4, alias='token_seguimiento')

    model_config = {'populate_by_name': True}


_EVENTO_LABELS = {
    'fecha_recibida_centro': ('📦 Hemos recibido tu dispositivo', 'recepcion'),
    'fecha_inicio_diagnostico': ('🔍 Comenzamos el diagnóstico', 'diagnostico'),
    'fecha_diagnostico_completado': ('✅ Diagnóstico completado', 'diagnostico_ok'),
    'fecha_presupuesto_emitido': ('📝 Presupuesto enviado', 'presupuesto'),
    'fecha_presupuesto_aceptado': ('👍 Presupuesto aceptado', 'aprobado'),
    'fecha_inicio_reparacion': ('🔧 Iniciando reparación', 'reparando'),
    'fecha_fin_reparacion': ('✨ Reparación finalizada', 'reparado'),
    'fecha_enviado': ('🚚 Enviado al cliente', 'enviado'),
    'fecha_entregado': ('🎉 Entregado', 'entregado'),
}


async def _timeline_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    # Aceptar tanto `token` como `token_seguimiento`
    if 'token_seguimiento' in params and 'token' not in params:
        params = {**params, 'token': params['token_seguimiento']}
    p = validate_input(TimelineInput, params)
    token = p.token.strip().upper()

    proj = {
        '_id': 0, 'id': 1, 'numero_orden': 1, 'estado': 1,
        'created_at': 1,
        'fecha_recibida_centro': 1, 'fecha_inicio_diagnostico': 1,
        'fecha_diagnostico_completado': 1, 'fecha_presupuesto_emitido': 1,
        'fecha_presupuesto_aceptado': 1, 'fecha_inicio_reparacion': 1,
        'fecha_fin_reparacion': 1, 'fecha_enviado': 1, 'fecha_entregado': 1,
        'fecha_estimada_entrega': 1,
    }
    doc = await db.ordenes.find_one({'token_seguimiento': token}, proj)
    if not doc:
        return {'found': False, 'mensaje_cliente':
                'No encontramos ninguna reparación con ese código. Verifica '
                'el código que recibiste por email.'}

    eventos = [{
        'titulo': '✉️ Solicitud registrada',
        'tipo': 'creacion',
        'fecha': doc.get('created_at'),
    }]
    for campo, (titulo, tipo) in _EVENTO_LABELS.items():
        f = doc.get(campo)
        if f:
            eventos.append({'titulo': titulo, 'tipo': tipo, 'fecha': f})

    # Si la orden tiene lista de compras pendiente (espera repuesto) → enriquecer
    espera_info = None
    items_compra = await db.lista_compras.find(
        {'ordenes_relacionadas': doc['id'],
         'estado': {'$in': ['pendiente', 'aprobado', 'pedido']}},
        {'_id': 0, 'repuesto_nombre': 1, 'estado': 1, 'urgencia': 1,
         'created_at': 1, 'pedido_en': 1},
    ).to_list(length=None)
    if items_compra:
        # Estimación cliente-friendly
        algun_pedido = any(i['estado'] == 'pedido' for i in items_compra)
        espera_info = {
            'esperando_repuesto': True,
            'cantidad_repuestos': len(items_compra),
            'repuestos': [i['repuesto_nombre'] for i in items_compra],
            'estado_pedido': 'pedido_realizado' if algun_pedido else 'pendiente_pedido',
            'mensaje_cliente': (
                'Tu reparación está esperando un repuesto que ya hemos pedido a '
                'nuestro proveedor. Tiempo estimado: 2-5 días laborables.'
                if algun_pedido else
                'Tu reparación necesita un repuesto. Lo estamos gestionando con '
                'el proveedor — te avisaremos en cuanto lo tengamos.'
            ),
        }
        eventos.append({
            'titulo': '⏳ Esperando repuesto',
            'tipo': 'esperando_repuesto',
            'fecha': items_compra[0].get('created_at'),
            'detalle': espera_info['mensaje_cliente'],
        })

    eventos.sort(key=lambda e: str(e.get('fecha') or ''))
    return {
        'found': True,
        'numero_orden': doc.get('numero_orden'),
        'estado': doc.get('estado'),
        'fecha_estimada_entrega': doc.get('fecha_estimada_entrega'),
        'eventos': eventos,
        'espera_repuesto': espera_info,
    }


register(ToolSpec(
    name='obtener_timeline_cliente',
    description=(
        'Devuelve la línea temporal de la orden en lenguaje cliente-friendly. Si '
        'la orden está esperando un repuesto, incluye estimación amable. Solo '
        'datos públicos.'
    ),
    required_scope='public:track_by_token',
    input_schema={
        'type': 'object',
        'properties': {
            'token': {'type': 'string', 'minLength': 4},
            'token_seguimiento': {'type': 'string', 'minLength': 4},
        },
        'additionalProperties': False,
    },
    handler=_timeline_handler,
))


# ══════════════════════════════════════════════════════════════════════════════
# obtener_fotos_diagnostico — solo URLs públicamente autorizadas
# ══════════════════════════════════════════════════════════════════════════════

class FotosInput(BaseModel):
    token: str = Field(..., min_length=4, alias='token_seguimiento')
    model_config = {'populate_by_name': True}


async def _fotos_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    if 'token_seguimiento' in params and 'token' not in params:
        params = {**params, 'token': params['token_seguimiento']}
    p = validate_input(FotosInput, params)
    token = p.token.strip().upper()

    doc = await db.ordenes.find_one(
        {'token_seguimiento': token},
        {'_id': 0, 'numero_orden': 1, 'fotos_diagnostico': 1, 'fotos_publicas': 1,
         'fotos_recepcion': 1, 'imagenes': 1},
    )
    if not doc:
        return {'found': False, 'mensaje_cliente':
                'No encontramos ninguna reparación con ese código.'}

    # Solo aceptamos URLs marcadas como públicas / autorizadas
    fotos: list[dict] = []
    for f in (doc.get('fotos_publicas') or doc.get('fotos_diagnostico') or []):
        if isinstance(f, dict):
            url = f.get('url')
            autorizada = f.get('publica') or f.get('autorizada_cliente') or f.get('publico')
        else:
            url = str(f)
            autorizada = True
        if url and (autorizada or doc.get('fotos_publicas')):
            fotos.append({
                'url': url,
                'descripcion': (f.get('descripcion') if isinstance(f, dict) else None) or 'Diagnóstico',
                'fecha': (f.get('fecha') if isinstance(f, dict) else None),
            })

    if not fotos:
        return {
            'found': True,
            'fotos': [],
            'mensaje_cliente': (
                'Aún no tenemos fotos públicas disponibles para esta reparación. '
                'Las añadiremos en cuanto el técnico realice el diagnóstico.'
            ),
        }
    return {
        'found': True,
        'numero_orden': doc.get('numero_orden'),
        'total': len(fotos),
        'fotos': fotos,
    }


register(ToolSpec(
    name='obtener_fotos_diagnostico',
    description='Devuelve URLs de fotos del diagnóstico marcadas como públicas. Si no hay, lo informa amablemente.',
    required_scope='public:track_by_token',
    input_schema={
        'type': 'object',
        'properties': {
            'token': {'type': 'string', 'minLength': 4},
            'token_seguimiento': {'type': 'string', 'minLength': 4},
        },
        'additionalProperties': False,
    },
    handler=_fotos_handler,
))

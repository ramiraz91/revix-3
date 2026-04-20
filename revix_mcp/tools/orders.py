"""
Tools de órdenes · read-only.

  - buscar_orden(ref): resuelve por UUID, numero_orden o numero_autorizacion.
  - listar_ordenes(filtros): listado paginado con filtros seguros.
"""
from __future__ import annotations

from typing import Optional, List

from pydantic import BaseModel, Field, field_validator

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..auth import AgentIdentity
from ._registry import ToolSpec, register
from ._common import ORDEN_PROJECTION, strip_many, validate_input


# ──────────────────────────────────────────────────────────────────────────────
# buscar_orden
# ──────────────────────────────────────────────────────────────────────────────

class BuscarOrdenInput(BaseModel):
    ref: str = Field(..., min_length=1, description='UUID, numero_orden o numero_autorizacion')


async def _buscar_orden_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(BuscarOrdenInput, params)
    ref = p.ref.strip()

    # Intentar por id, numero_orden, numero_autorizacion (en ese orden)
    doc = await db.ordenes.find_one(
        {'$or': [
            {'id': ref},
            {'numero_orden': ref},
            {'numero_autorizacion': ref},
        ]},
        ORDEN_PROJECTION,
    )
    if not doc:
        return {'found': False, 'ref': ref}

    # Enriquecer con cliente
    cliente = None
    if doc.get('cliente_id'):
        cliente = await db.clientes.find_one(
            {'id': doc['cliente_id']},
            {'_id': 0, 'id': 1, 'nombre': 1, 'apellidos': 1, 'telefono': 1, 'email': 1},
        )

    return {'found': True, 'orden': doc, 'cliente': cliente}


register(ToolSpec(
    name='buscar_orden',
    description=(
        'Busca una orden por identificador flexible: UUID interno, número de orden '
        '(ej "OT-20260420-..."), o número de autorización de aseguradora. '
        'Devuelve los datos de la orden + contacto básico del cliente.'
    ),
    required_scope='orders:read',
    input_schema={
        'type': 'object',
        'properties': {
            'ref': {'type': 'string', 'description': 'UUID, numero_orden o numero_autorizacion'},
        },
        'required': ['ref'],
        'additionalProperties': False,
    },
    handler=_buscar_orden_handler,
))


# ──────────────────────────────────────────────────────────────────────────────
# listar_ordenes
# ──────────────────────────────────────────────────────────────────────────────

class ListarOrdenesInput(BaseModel):
    estado: Optional[str] = None
    tecnico_id: Optional[str] = None
    cliente_id: Optional[str] = None
    es_garantia: Optional[bool] = None
    numero_autorizacion: Optional[str] = None
    desde: Optional[str] = Field(None, description='ISO date/datetime, filtra por created_at')
    hasta: Optional[str] = None
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)

    @field_validator('estado')
    @classmethod
    def _estado_lower(cls, v):
        return v.lower() if v else v


async def _listar_ordenes_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(ListarOrdenesInput, params)
    q: dict = {}
    if p.estado: q['estado'] = p.estado
    if p.tecnico_id: q['tecnico_asignado'] = p.tecnico_id
    if p.cliente_id: q['cliente_id'] = p.cliente_id
    if p.es_garantia is not None: q['es_garantia'] = p.es_garantia
    if p.numero_autorizacion: q['numero_autorizacion'] = p.numero_autorizacion
    if p.desde or p.hasta:
        rng = {}
        if p.desde: rng['$gte'] = p.desde
        if p.hasta: rng['$lte'] = p.hasta
        q['created_at'] = rng

    total = await db.ordenes.count_documents(q)
    projection = {
        '_id': 0, 'id': 1, 'numero_orden': 1, 'numero_autorizacion': 1,
        'estado': 1, 'es_garantia': 1, 'cliente_id': 1, 'tecnico_asignado': 1,
        'dispositivo.marca': 1, 'dispositivo.modelo': 1, 'dispositivo.imei': 1,
        'presupuesto_total': 1, 'created_at': 1, 'updated_at': 1,
    }
    cursor = db.ordenes.find(q, projection).sort('created_at', -1).skip(p.offset).limit(p.limit)
    items = [d async for d in cursor]
    return {'total': total, 'count': len(items), 'offset': p.offset, 'limit': p.limit, 'items': items}


register(ToolSpec(
    name='listar_ordenes',
    description=(
        'Lista órdenes con filtros combinables (estado, técnico, cliente, garantía, '
        'autorización, rango de fechas). Paginado (limit máx 200). Devuelve resumen '
        'con los campos clave; usa buscar_orden para detalle completo.'
    ),
    required_scope='orders:read',
    input_schema={
        'type': 'object',
        'properties': {
            'estado': {'type': 'string'},
            'tecnico_id': {'type': 'string'},
            'cliente_id': {'type': 'string'},
            'es_garantia': {'type': 'boolean'},
            'numero_autorizacion': {'type': 'string'},
            'desde': {'type': 'string', 'description': 'ISO date/datetime'},
            'hasta': {'type': 'string', 'description': 'ISO date/datetime'},
            'limit': {'type': 'integer', 'minimum': 1, 'maximum': 200, 'default': 50},
            'offset': {'type': 'integer', 'minimum': 0, 'default': 0},
        },
        'additionalProperties': False,
    },
    handler=_listar_ordenes_handler,
))

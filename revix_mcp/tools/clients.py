"""
Tools de clientes · read-only.

  - buscar_cliente(q): búsqueda flexible por id, dni, email, teléfono o nombre.
  - obtener_historial_cliente(cliente_id): listado de órdenes de un cliente.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..auth import AgentIdentity
from ._registry import ToolSpec, register
from ._common import CLIENTE_PROJECTION_PUBLIC, validate_input


# ──────────────────────────────────────────────────────────────────────────────
# buscar_cliente
# ──────────────────────────────────────────────────────────────────────────────

class BuscarClienteInput(BaseModel):
    q: str = Field(..., min_length=2, description='UUID, dni, email, teléfono, o nombre/apellidos (parcial)')
    limit: int = Field(10, ge=1, le=50)


async def _buscar_cliente_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(BuscarClienteInput, params)
    q = p.q.strip()
    # Escape básico regex
    import re
    q_safe = re.escape(q)

    # 1) Intentos exactos primero (más baratos + precisos)
    exact = await db.clientes.find_one(
        {'$or': [
            {'id': q},
            {'dni': q},
            {'email': q},
            {'telefono': q},
            {'cif_empresa': q},
        ]},
        CLIENTE_PROJECTION_PUBLIC,
    )
    if exact:
        return {'match_type': 'exact', 'items': [exact], 'count': 1}

    # 2) Búsqueda parcial en nombre/apellidos (case-insensitive)
    rx = {'$regex': q_safe, '$options': 'i'}
    cursor = db.clientes.find(
        {'$or': [
            {'nombre': rx},
            {'apellidos': rx},
            {'email': rx},
            {'telefono': rx},
        ]},
        CLIENTE_PROJECTION_PUBLIC,
    ).limit(p.limit)
    items = [d async for d in cursor]
    return {'match_type': 'fuzzy', 'items': items, 'count': len(items)}


register(ToolSpec(
    name='buscar_cliente',
    description=(
        'Busca clientes por UUID, DNI, email, teléfono, CIF, o por nombre/apellidos '
        '(coincidencia parcial). Prioriza matches exactos; si no hay, devuelve hasta '
        '`limit` resultados por coincidencia parcial.'
    ),
    required_scope='customers:read',
    input_schema={
        'type': 'object',
        'properties': {
            'q': {'type': 'string', 'minLength': 2},
            'limit': {'type': 'integer', 'minimum': 1, 'maximum': 50, 'default': 10},
        },
        'required': ['q'],
        'additionalProperties': False,
    },
    handler=_buscar_cliente_handler,
))


# ──────────────────────────────────────────────────────────────────────────────
# obtener_historial_cliente
# ──────────────────────────────────────────────────────────────────────────────

class HistorialClienteInput(BaseModel):
    cliente_id: str = Field(..., min_length=1)
    limit: int = Field(50, ge=1, le=200)
    incluir_materiales: bool = False


async def _historial_cliente_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(HistorialClienteInput, params)

    # Cliente
    cliente = await db.clientes.find_one(
        {'id': p.cliente_id}, CLIENTE_PROJECTION_PUBLIC,
    )
    if not cliente:
        return {'found': False, 'cliente_id': p.cliente_id}

    projection = {
        '_id': 0, 'id': 1, 'numero_orden': 1, 'estado': 1,
        'es_garantia': 1, 'numero_autorizacion': 1,
        'dispositivo.marca': 1, 'dispositivo.modelo': 1,
        'presupuesto_total': 1, 'coste_total': 1, 'beneficio_estimado': 1,
        'created_at': 1, 'updated_at': 1, 'fecha_enviado': 1,
    }
    if p.incluir_materiales:
        projection['materiales'] = 1

    cursor = db.ordenes.find({'cliente_id': p.cliente_id}, projection) \
        .sort('created_at', -1).limit(p.limit)
    ordenes = [d async for d in cursor]

    # Métricas rápidas
    total_ordenes = await db.ordenes.count_documents({'cliente_id': p.cliente_id})
    facturacion_total = sum((o.get('presupuesto_total') or 0) for o in ordenes)
    en_garantia = sum(1 for o in ordenes if o.get('es_garantia'))

    return {
        'found': True,
        'cliente': cliente,
        'resumen': {
            'total_ordenes': total_ordenes,
            'ordenes_devueltas': len(ordenes),
            'facturacion_periodo': round(facturacion_total, 2),
            'en_garantia': en_garantia,
        },
        'ordenes': ordenes,
    }


register(ToolSpec(
    name='obtener_historial_cliente',
    description=(
        'Devuelve el historial de órdenes de un cliente (UUID). Incluye un resumen '
        '(total de órdenes, facturación, n.º en garantía) y las `limit` más recientes. '
        'Por defecto no devuelve los materiales de cada orden (usar `incluir_materiales=true`).'
    ),
    required_scope='customers:read',
    input_schema={
        'type': 'object',
        'properties': {
            'cliente_id': {'type': 'string'},
            'limit': {'type': 'integer', 'minimum': 1, 'maximum': 200, 'default': 50},
            'incluir_materiales': {'type': 'boolean', 'default': False},
        },
        'required': ['cliente_id'],
        'additionalProperties': False,
    },
    handler=_historial_cliente_handler,
))

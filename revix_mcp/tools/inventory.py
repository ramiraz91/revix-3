"""
Tool de inventario · read-only.

  - consultar_inventario(filtros): stock actual, umbrales, precios.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..auth import AgentIdentity
from ._registry import ToolSpec, register
from ._common import validate_input


class ConsultarInventarioInput(BaseModel):
    q: Optional[str] = Field(None, description='Texto libre — busca en nombre, sku, ean, abreviatura, modelo')
    categoria: Optional[str] = None
    solo_bajo_minimo: bool = False
    solo_sin_stock: bool = False
    proveedor: Optional[str] = None
    es_pantalla: Optional[bool] = None
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)


async def _consultar_inventario_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(ConsultarInventarioInput, params)
    import re

    query: dict = {}
    if p.categoria:
        query['categoria'] = p.categoria
    if p.proveedor:
        query['proveedor'] = p.proveedor
    if p.es_pantalla is not None:
        query['es_pantalla'] = p.es_pantalla
    if p.solo_sin_stock:
        query['stock'] = {'$lte': 0}
    elif p.solo_bajo_minimo:
        # stock <= stock_minimo con expresión
        query['$expr'] = {'$lte': ['$stock', '$stock_minimo']}
    if p.q:
        rx = {'$regex': re.escape(p.q), '$options': 'i'}
        query['$or'] = [
            {'nombre': rx}, {'sku': rx}, {'ean': rx},
            {'abreviatura': rx}, {'modelo_compatible': rx},
            {'sku_proveedor': rx},
        ]

    projection = {
        '_id': 0, 'id': 1, 'nombre': 1, 'categoria': 1, 'sku': 1,
        'abreviatura': 1, 'modelo_compatible': 1, 'proveedor': 1,
        'stock': 1, 'stock_minimo': 1, 'precio_compra': 1, 'precio_venta': 1,
        'ubicacion_fisica': 1, 'es_pantalla': 1, 'calidad_pantalla': 1,
        'ean': 1, 'tiempo_reposicion_dias': 1,
    }

    total = await db.repuestos.count_documents(query)
    cursor = db.repuestos.find(query, projection) \
        .sort([('stock', 1), ('nombre', 1)]) \
        .skip(p.offset).limit(p.limit)
    items = [d async for d in cursor]

    # Etiquetar nivel de stock para conveniencia del agente
    for it in items:
        stock = it.get('stock') or 0
        minimo = it.get('stock_minimo') or 0
        if stock <= 0:
            it['nivel_stock'] = 'sin_stock'
        elif stock <= minimo:
            it['nivel_stock'] = 'bajo_minimo'
        else:
            it['nivel_stock'] = 'ok'

    return {
        'total': total, 'count': len(items),
        'offset': p.offset, 'limit': p.limit,
        'items': items,
    }


register(ToolSpec(
    name='consultar_inventario',
    description=(
        'Consulta el inventario de repuestos con filtros: texto libre (nombre/sku/ean/modelo), '
        'categoría, proveedor, solo bajo stock mínimo, solo sin stock, solo pantallas. '
        'Devuelve stock actual, mínimo, precios, ubicación física y un campo derivado '
        '`nivel_stock` ∈ {sin_stock, bajo_minimo, ok}. Paginado (máx 500).'
    ),
    required_scope='inventory:read',
    input_schema={
        'type': 'object',
        'properties': {
            'q': {'type': 'string'},
            'categoria': {'type': 'string'},
            'solo_bajo_minimo': {'type': 'boolean', 'default': False},
            'solo_sin_stock': {'type': 'boolean', 'default': False},
            'proveedor': {'type': 'string'},
            'es_pantalla': {'type': 'boolean'},
            'limit': {'type': 'integer', 'minimum': 1, 'maximum': 500, 'default': 50},
            'offset': {'type': 'integer', 'minimum': 0, 'default': 0},
        },
        'additionalProperties': False,
    },
    handler=_consultar_inventario_handler,
))

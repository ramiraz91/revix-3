"""
Tools de métricas y dashboard · read-only.

  - obtener_metricas(metrica, periodo): métricas cuantitativas específicas.
  - obtener_dashboard(periodo): snapshot agregado (órdenes + finanzas + inventario).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..auth import AgentIdentity
from ._registry import ToolSpec, register
from ._common import validate_input


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de periodos
# ──────────────────────────────────────────────────────────────────────────────

Periodo = Literal['dia', 'semana', 'mes', 'trimestre', 'año', 'ytd', 'all']


def _rango_periodo(periodo: str) -> tuple[str, str]:
    """Devuelve (inicio_iso, fin_iso) UTC para un periodo dado."""
    now = datetime.now(timezone.utc)
    if periodo == 'dia':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == 'semana':
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
    elif periodo == 'mes':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif periodo == 'trimestre':
        qm = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=qm, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif periodo in ('año', 'ytd'):
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif periodo == 'all':
        start = datetime(1970, 1, 1, tzinfo=timezone.utc)
    else:
        raise ValueError(f'Periodo inválido: {periodo}')
    return start.isoformat(), now.isoformat()


# ──────────────────────────────────────────────────────────────────────────────
# obtener_metricas
# ──────────────────────────────────────────────────────────────────────────────

MetricaKey = Literal[
    'ordenes_por_estado',
    'ordenes_por_tecnico',
    'ordenes_por_dia',
    'ingresos_periodo',
    'coste_periodo',
    'beneficio_periodo',
    'top_modelos_reparados',
    'top_fallos',
    'sla_cumplimiento',
    'ordenes_en_garantia',
    'tasa_aprobacion_presupuestos',
]


class ObtenerMetricasInput(BaseModel):
    metrica: MetricaKey
    periodo: Periodo = 'mes'
    top: int = Field(10, ge=1, le=50)


async def _metricas_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(ObtenerMetricasInput, params)
    start, end = _rango_periodo(p.periodo)

    if p.metrica == 'ordenes_por_estado':
        cursor = db.ordenes.aggregate([
            {'$match': {'created_at': {'$gte': start, '$lte': end}}},
            {'$group': {'_id': '$estado', 'count': {'$sum': 1}}},
            {'$project': {'_id': 0, 'estado': '$_id', 'count': 1}},
            {'$sort': {'count': -1}},
        ])
        items = [d async for d in cursor]
        return {'metrica': p.metrica, 'periodo': p.periodo, 'items': items}

    if p.metrica == 'ordenes_por_tecnico':
        cursor = db.ordenes.aggregate([
            {'$match': {'created_at': {'$gte': start, '$lte': end},
                        'tecnico_asignado': {'$ne': None}}},
            {'$group': {'_id': '$tecnico_asignado', 'count': {'$sum': 1}}},
            {'$project': {'_id': 0, 'tecnico_id': '$_id', 'count': 1}},
            {'$sort': {'count': -1}},
            {'$limit': p.top},
        ])
        items = [d async for d in cursor]
        return {'metrica': p.metrica, 'periodo': p.periodo, 'items': items}

    if p.metrica == 'ordenes_por_dia':
        cursor = db.ordenes.aggregate([
            {'$match': {'created_at': {'$gte': start, '$lte': end}}},
            {'$project': {'d': {'$substr': ['$created_at', 0, 10]}}},
            {'$group': {'_id': '$d', 'count': {'$sum': 1}}},
            {'$sort': {'_id': 1}},
            {'$project': {'_id': 0, 'fecha': '$_id', 'count': 1}},
        ])
        items = [d async for d in cursor]
        return {'metrica': p.metrica, 'periodo': p.periodo, 'items': items}

    if p.metrica in ('ingresos_periodo', 'coste_periodo', 'beneficio_periodo'):
        field = {
            'ingresos_periodo': 'presupuesto_total',
            'coste_periodo': 'coste_total',
            'beneficio_periodo': 'beneficio_estimado',
        }[p.metrica]
        cursor = db.ordenes.aggregate([
            {'$match': {'estado': 'enviado',
                        'fecha_enviado': {'$gte': start, '$lte': end}}},
            {'$group': {
                '_id': None,
                'total': {'$sum': {'$ifNull': [f'${field}', 0]}},
                'count': {'$sum': 1},
            }},
        ])
        docs = [d async for d in cursor]
        total = docs[0]['total'] if docs else 0
        count = docs[0]['count'] if docs else 0
        return {
            'metrica': p.metrica, 'periodo': p.periodo,
            'total': round(float(total), 2), 'ordenes_enviadas': count,
        }

    if p.metrica == 'top_modelos_reparados':
        cursor = db.ordenes.aggregate([
            {'$match': {'created_at': {'$gte': start, '$lte': end}}},
            {'$group': {'_id': '$dispositivo.modelo', 'count': {'$sum': 1}}},
            {'$project': {'_id': 0, 'modelo': '$_id', 'count': 1}},
            {'$sort': {'count': -1}},
            {'$limit': p.top},
        ])
        items = [d async for d in cursor]
        return {'metrica': p.metrica, 'periodo': p.periodo, 'items': items}

    if p.metrica == 'top_fallos':
        cursor = db.ordenes.aggregate([
            {'$match': {'created_at': {'$gte': start, '$lte': end}}},
            {'$group': {'_id': '$dispositivo.daños', 'count': {'$sum': 1}}},
            {'$project': {'_id': 0, 'fallo': '$_id', 'count': 1}},
            {'$sort': {'count': -1}},
            {'$limit': p.top},
        ])
        items = [d async for d in cursor]
        return {'metrica': p.metrica, 'periodo': p.periodo, 'items': items}

    if p.metrica == 'sla_cumplimiento':
        total = await db.ordenes.count_documents(
            {'estado': 'enviado', 'fecha_enviado': {'$gte': start, '$lte': end}},
        )
        fuera = await db.ordenes.count_documents(
            {'estado': 'enviado',
             'fecha_enviado': {'$gte': start, '$lte': end},
             'alerta_sla_enviada': True},
        )
        pct = (100.0 * (total - fuera) / total) if total else 0.0
        return {
            'metrica': p.metrica, 'periodo': p.periodo,
            'total_enviadas': total, 'fuera_sla': fuera,
            'cumplimiento_pct': round(pct, 2),
        }

    if p.metrica == 'ordenes_en_garantia':
        count = await db.ordenes.count_documents(
            {'es_garantia': True, 'created_at': {'$gte': start, '$lte': end}},
        )
        return {'metrica': p.metrica, 'periodo': p.periodo, 'count': count}

    if p.metrica == 'tasa_aprobacion_presupuestos':
        emitidos = await db.ordenes.count_documents(
            {'presupuesto_emitido': True,
             'presupuesto_fecha_emision': {'$gte': start, '$lte': end}},
        )
        aceptados = await db.ordenes.count_documents(
            {'presupuesto_emitido': True,
             'presupuesto_aceptado': True,
             'presupuesto_fecha_emision': {'$gte': start, '$lte': end}},
        )
        rechazados = await db.ordenes.count_documents(
            {'presupuesto_emitido': True,
             'presupuesto_aceptado': False,
             'presupuesto_fecha_emision': {'$gte': start, '$lte': end}},
        )
        pct = (100.0 * aceptados / emitidos) if emitidos else 0.0
        return {
            'metrica': p.metrica, 'periodo': p.periodo,
            'emitidos': emitidos, 'aceptados': aceptados,
            'rechazados': rechazados, 'sin_respuesta': emitidos - aceptados - rechazados,
            'tasa_aceptacion_pct': round(pct, 2),
        }

    # Nunca debe llegar aquí (pydantic Literal)
    raise ValueError(f'Métrica no implementada: {p.metrica}')


register(ToolSpec(
    name='obtener_metricas',
    description=(
        'Devuelve una métrica concreta sobre el periodo indicado. Métricas disponibles: '
        'ordenes_por_estado, ordenes_por_tecnico, ordenes_por_dia, ingresos_periodo, '
        'coste_periodo, beneficio_periodo, top_modelos_reparados, top_fallos, '
        'sla_cumplimiento, ordenes_en_garantia, tasa_aprobacion_presupuestos. '
        'Periodo ∈ dia | semana | mes | trimestre | año | ytd | all.'
    ),
    required_scope='metrics:read',
    input_schema={
        'type': 'object',
        'properties': {
            'metrica': {
                'type': 'string',
                'enum': [
                    'ordenes_por_estado', 'ordenes_por_tecnico', 'ordenes_por_dia',
                    'ingresos_periodo', 'coste_periodo', 'beneficio_periodo',
                    'top_modelos_reparados', 'top_fallos',
                    'sla_cumplimiento', 'ordenes_en_garantia',
                    'tasa_aprobacion_presupuestos',
                ],
            },
            'periodo': {
                'type': 'string',
                'enum': ['dia', 'semana', 'mes', 'trimestre', 'año', 'ytd', 'all'],
                'default': 'mes',
            },
            'top': {'type': 'integer', 'minimum': 1, 'maximum': 50, 'default': 10},
        },
        'required': ['metrica'],
        'additionalProperties': False,
    },
    handler=_metricas_handler,
))


# ──────────────────────────────────────────────────────────────────────────────
# obtener_dashboard
# ──────────────────────────────────────────────────────────────────────────────

class ObtenerDashboardInput(BaseModel):
    periodo: Periodo = 'mes'


async def _dashboard_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(ObtenerDashboardInput, params)
    start, end = _rango_periodo(p.periodo)

    # Órdenes por estado
    cursor = db.ordenes.aggregate([
        {'$match': {'created_at': {'$gte': start, '$lte': end}}},
        {'$group': {'_id': '$estado', 'count': {'$sum': 1}}},
    ])
    estados = {d['_id'] or 'desconocido': d['count'] async for d in cursor}

    # Finanzas (órdenes enviadas en el periodo)
    cursor = db.ordenes.aggregate([
        {'$match': {'estado': 'enviado',
                    'fecha_enviado': {'$gte': start, '$lte': end}}},
        {'$group': {
            '_id': None,
            'ingresos': {'$sum': {'$ifNull': ['$presupuesto_total', 0]}},
            'coste': {'$sum': {'$ifNull': ['$coste_total', 0]}},
            'beneficio': {'$sum': {'$ifNull': ['$beneficio_estimado', 0]}},
            'enviadas': {'$sum': 1},
        }},
    ])
    fin_docs = [d async for d in cursor]
    if fin_docs:
        ingresos = float(fin_docs[0]['ingresos'] or 0)
        coste = float(fin_docs[0]['coste'] or 0)
        beneficio = float(fin_docs[0]['beneficio'] or 0)
        enviadas = int(fin_docs[0]['enviadas'] or 0)
    else:
        ingresos = coste = beneficio = 0.0
        enviadas = 0

    # Inventario global
    inv_total = await db.repuestos.count_documents({})
    inv_bajo = await db.repuestos.count_documents({'$expr': {'$lte': ['$stock', '$stock_minimo']}})
    inv_sin = await db.repuestos.count_documents({'stock': {'$lte': 0}})

    # Valor inventario (proyección ligera)
    valor_cursor = db.repuestos.aggregate([
        {'$match': {'stock': {'$gt': 0}}},
        {'$group': {
            '_id': None,
            'valor_coste': {'$sum': {'$multiply': ['$stock', {'$ifNull': ['$precio_compra', 0]}]}},
            'valor_venta': {'$sum': {'$multiply': ['$stock', {'$ifNull': ['$precio_venta', 0]}]}},
        }},
    ])
    valor_docs = [d async for d in valor_cursor]
    valor_coste = float(valor_docs[0]['valor_coste']) if valor_docs else 0.0
    valor_venta = float(valor_docs[0]['valor_venta']) if valor_docs else 0.0

    # Clientes nuevos en el periodo
    clientes_nuevos = await db.clientes.count_documents(
        {'created_at': {'$gte': start, '$lte': end}},
    )

    total_periodo = sum(estados.values())
    total_enviadas_global = estados.get('enviado', 0)

    return {
        'periodo': p.periodo,
        'rango': {'inicio': start, 'fin': end},
        'ordenes': {
            'total_periodo': total_periodo,
            'por_estado': estados,
            'enviadas_en_periodo': enviadas,
        },
        'finanzas': {
            'ingresos': round(ingresos, 2),
            'coste': round(coste, 2),
            'beneficio': round(beneficio, 2),
            'margen_pct': round(100.0 * beneficio / ingresos, 2) if ingresos else 0.0,
        },
        'inventario': {
            'total_skus': inv_total,
            'bajo_minimo': inv_bajo,
            'sin_stock': inv_sin,
            'valor_coste': round(valor_coste, 2),
            'valor_venta': round(valor_venta, 2),
        },
        'clientes': {
            'nuevos_en_periodo': clientes_nuevos,
        },
    }


register(ToolSpec(
    name='obtener_dashboard',
    description=(
        'Devuelve un snapshot agregado del negocio para un periodo: órdenes por estado, '
        'finanzas (ingresos/coste/beneficio/margen), inventario (SKUs totales, bajo mínimo, '
        'sin stock, valor a coste y venta) y clientes nuevos. Pensado para que el KPI Analyst '
        'construya reports ejecutivos rápidos.'
    ),
    required_scope='dashboard:read',
    input_schema={
        'type': 'object',
        'properties': {
            'periodo': {
                'type': 'string',
                'enum': ['dia', 'semana', 'mes', 'trimestre', 'año', 'ytd', 'all'],
                'default': 'mes',
            },
        },
        'additionalProperties': False,
    },
    handler=_dashboard_handler,
))

"""
Tests Fase 2 · Finance Officer (4 tools).

Cubre casos críticos:
  - listar_facturas_pendientes_cobro: semáforo + filtros antigüedad/cliente/canal
  - emitir_factura_orden: las 5 validaciones ANTES de emitir + emisión OK + rectificativa
  - enviar_recordatorio_cobro: tipo sugerido + bloqueo último_aviso sin previos + preview mock
  - calcular_modelo_303: resultado a_ingresar/a_devolver + aviso legal presente
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from motor.motor_asyncio import AsyncIOMotorClient

from revix_mcp import auth, rate_limit
from revix_mcp.config import (
    API_KEYS_COLLECTION, AUDIT_COLLECTION, DB_NAME, IDEMPOTENCY_COLLECTION, MONGO_URL,
)
from revix_mcp.runtime import execute_tool
from revix_mcp.tools import finance_officer  # noqa: F401 — registro


PFX = 'test_fin_'
ORD_OK = f'{PFX}ord_ok'
ORD_ESTADO_MALO = f'{PFX}ord_mal_estado'
ORD_SIN_TOTALES = f'{PFX}ord_sin_totales'
ORD_CLI_SIN_DATOS = f'{PFX}ord_cli_incompleto'
CLI_OK = f'{PFX}cli_ok'
CLI_INCOMPLETO = f'{PFX}cli_incompleto'
FAC_VIEJA = f'{PFX}fac_vieja'
FAC_NUEVA = f'{PFX}fac_nueva'


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec='seconds')


@pytest_asyncio.fixture
async def db_seed():
    assert DB_NAME != 'production'
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]

    collections = [
        'ordenes', 'clientes', 'facturas', 'contabilidad_series',
        'mcp_recordatorios_cobro', 'notificaciones',
        API_KEYS_COLLECTION, IDEMPOTENCY_COLLECTION, AUDIT_COLLECTION,
        rate_limit.USAGE_COLLECTION, rate_limit.LIMITS_COLLECTION,
    ]
    for col in collections:
        await database[col].delete_many({'id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'agent_id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'orden_id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'factura_id': {'$regex': f'^{PFX}'}})
    # series test
    await database.contabilidad_series.delete_many({'serie': 'TESTFIN'})
    await database.contabilidad_series.delete_many({'serie': 'TESTFINR'})
    rate_limit.invalidate_limits_cache()

    now = datetime.now(timezone.utc)

    # Cliente completo (NIF + dirección)
    await database.clientes.insert_one({
        'id': CLI_OK, 'nombre': 'Ana', 'apellidos': 'Test',
        'email': 'ana@test.com', 'telefono': '600111222',
        'dni': 'T1111111E', 'direccion': 'C/ Real 1, Madrid',
        'tipo_cliente': 'particular',
        'created_at': _iso(now - timedelta(days=60)),
    })
    # Cliente incompleto (sin NIF, sin direccion)
    await database.clientes.insert_one({
        'id': CLI_INCOMPLETO, 'nombre': 'Bob',
        'apellidos': 'SinDatos', 'email': 'bob@test.com',
        'tipo_cliente': 'particular', 'direccion': '',
        'created_at': _iso(now - timedelta(days=60)),
    })

    # Órdenes
    await database.ordenes.insert_many([
        {
            'id': ORD_OK, 'numero_orden': 'OT-FIN-OK', 'cliente_id': CLI_OK,
            'estado': 'enviado', 'fecha_enviado': _iso(now - timedelta(days=1)),
            'presupuesto_total': 200.0, 'base_imponible': 165.29, 'total_iva': 34.71,
            'mano_obra': 50.0,
            'materiales': [{'nombre': 'Pantalla', 'cantidad': 1, 'precio_unitario': 150, 'iva': 21}],
            'created_at': _iso(now - timedelta(days=3)),
            'updated_at': _iso(now),
        },
        {
            'id': ORD_ESTADO_MALO, 'numero_orden': 'OT-FIN-ESTADO-MAL',
            'cliente_id': CLI_OK, 'estado': 'diagnosticando',
            'presupuesto_total': 100.0, 'mano_obra': 30.0,
            'materiales': [{'nombre': 'x', 'cantidad': 1, 'precio_unitario': 70}],
            'created_at': _iso(now), 'updated_at': _iso(now),
        },
        {
            'id': ORD_SIN_TOTALES, 'numero_orden': 'OT-FIN-NO-TOT',
            'cliente_id': CLI_OK, 'estado': 'enviado',
            'presupuesto_total': 0, 'mano_obra': 0, 'materiales': [],
            'created_at': _iso(now - timedelta(days=2)),
            'updated_at': _iso(now),
        },
        {
            'id': ORD_CLI_SIN_DATOS, 'numero_orden': 'OT-FIN-CLIENTE-MAL',
            'cliente_id': CLI_INCOMPLETO, 'estado': 'enviado',
            'presupuesto_total': 80.0, 'mano_obra': 20.0,
            'materiales': [{'nombre': 'x', 'cantidad': 1, 'precio_unitario': 60}],
            'created_at': _iso(now - timedelta(days=3)),
            'updated_at': _iso(now),
        },
    ])

    # Facturas pendientes: una vieja (rojo), una nueva (verde)
    await database.facturas.insert_many([
        {
            'id': FAC_VIEJA, 'tipo': 'venta', 'numero': 'TEST-FAC-VIEJA',
            'cliente_id': CLI_OK, 'cliente_nombre': 'Ana Test',
            'cliente_email': 'ana@test.com',
            'orden_id': 'alguna', 'fecha_emision': _iso(now - timedelta(days=45)),
            'total': 120.0, 'base_imponible': 99.17, 'total_iva': 20.83,
            'estado': 'emitida', 'pendiente_cobro': 120.0,
            'año_fiscal': now.year,
        },
        {
            'id': FAC_NUEVA, 'tipo': 'venta', 'numero': 'TEST-FAC-NUEVA',
            'cliente_id': CLI_OK, 'cliente_nombre': 'Ana Test',
            'cliente_email': 'ana@test.com',
            'orden_id': 'otra', 'fecha_emision': _iso(now - timedelta(days=5)),
            'total': 200.0, 'base_imponible': 165.29, 'total_iva': 34.71,
            'estado': 'emitida', 'pendiente_cobro': 200.0,
            'año_fiscal': now.year,
        },
    ])

    yield database

    # Limpieza post
    for col in collections:
        await database[col].delete_many({'id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'agent_id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'orden_id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'factura_id': {'$regex': f'^{PFX}'}})
    # Facturas creadas por las tools durante el test
    await database.facturas.delete_many(
        {'source': 'mcp_agent', 'created_by': {'$regex': f'mcp:{PFX}'}},
    )
    await database.contabilidad_series.delete_many({'serie': 'TESTFIN'})
    await database.contabilidad_series.delete_many({'serie': 'TESTFINR'})
    rate_limit.invalidate_limits_cache()
    client.close()


async def _make_key(db, agent_id: str, scopes: list[str]) -> str:
    plain, _ = await auth.create_api_key(
        db, agent_id=agent_id, agent_name=agent_id,
        scopes=scopes, created_by='pytest',
    )
    return plain


# ──────────────────────────────────────────────────────────────────────────────
# 1 · listar_facturas_pendientes_cobro
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_listar_pendientes_semaforo(db_seed):
    key = await _make_key(db_seed, f'{PFX}fin1', ['finance:read', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='listar_facturas_pendientes_cobro',
                           params={'cliente_id': CLI_OK})
    ids = {f['id'] for f in r['items']}
    assert FAC_VIEJA in ids and FAC_NUEVA in ids
    semaforo = {f['id']: f['semaforo'] for f in r['items']}
    assert semaforo[FAC_VIEJA] == 'rojo'    # 45 días
    assert semaforo[FAC_NUEVA] == 'verde'   # 5 días
    # Ordenadas por antigüedad descendente
    idx_vieja = next(i for i, f in enumerate(r['items']) if f['id'] == FAC_VIEJA)
    idx_nueva = next(i for i, f in enumerate(r['items']) if f['id'] == FAC_NUEVA)
    assert idx_vieja < idx_nueva
    assert r['total_pendiente_eur'] >= 320.0


@pytest.mark.asyncio
async def test_listar_pendientes_filtro_antiguedad(db_seed):
    key = await _make_key(db_seed, f'{PFX}fin2', ['finance:read', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='listar_facturas_pendientes_cobro',
                           params={'antiguedad_minima_dias': 30, 'cliente_id': CLI_OK})
    ids = {f['id'] for f in r['items']}
    assert FAC_VIEJA in ids
    assert FAC_NUEVA not in ids  # 5 días < 30


# ──────────────────────────────────────────────────────────────────────────────
# 2 · emitir_factura_orden — VALIDACIONES
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_emitir_factura_ok(db_seed):
    key = await _make_key(db_seed, f'{PFX}fin3', ['finance:bill', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='emitir_factura_orden', params={
        'order_id': ORD_OK, 'tipo_factura': 'normal', 'serie_facturacion': 'TESTFIN',
        '_idempotency_key': f'factura_{ORD_OK}',
    })
    assert r['success'] is True
    assert r['numero_factura'].startswith('TESTFIN-')
    assert r['tipo_factura'] == 'normal'
    assert r['cliente']['nif'] == 'T1111111E'

    # Orden marcada
    orden = await db_seed.ordenes.find_one({'id': ORD_OK}, {'_id': 0})
    assert orden.get('facturada') is True
    assert orden.get('factura_id') == r['factura_id']


@pytest.mark.asyncio
async def test_emitir_falla_estado_no_facturable(db_seed):
    key = await _make_key(db_seed, f'{PFX}fin4', ['finance:bill', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='emitir_factura_orden', params={
        'order_id': ORD_ESTADO_MALO, 'tipo_factura': 'normal', 'serie_facturacion': 'TESTFIN',
        '_idempotency_key': f'factura_{ORD_ESTADO_MALO}',
    })
    assert r['success'] is False
    assert r['error'] == 'estado_no_facturable'


@pytest.mark.asyncio
async def test_emitir_falla_sin_totales(db_seed):
    key = await _make_key(db_seed, f'{PFX}fin5', ['finance:bill', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='emitir_factura_orden', params={
        'order_id': ORD_SIN_TOTALES, 'tipo_factura': 'normal', 'serie_facturacion': 'TESTFIN',
        '_idempotency_key': f'factura_{ORD_SIN_TOTALES}',
    })
    assert r['success'] is False
    assert r['error'] == 'totales_incompletos'


@pytest.mark.asyncio
async def test_emitir_falla_cliente_incompleto(db_seed):
    key = await _make_key(db_seed, f'{PFX}fin6', ['finance:bill', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='emitir_factura_orden', params={
        'order_id': ORD_CLI_SIN_DATOS, 'tipo_factura': 'normal', 'serie_facturacion': 'TESTFIN',
        '_idempotency_key': f'factura_{ORD_CLI_SIN_DATOS}',
    })
    assert r['success'] is False
    assert r['error'] == 'cliente_datos_incompletos'
    assert 'NIF/CIF' in r['faltantes']
    assert 'direccion' in r['faltantes']


@pytest.mark.asyncio
async def test_emitir_bloquea_duplicado_normal(db_seed):
    key = await _make_key(db_seed, f'{PFX}fin7', ['finance:bill', 'meta:ping'])
    p1 = {
        'order_id': ORD_OK, 'tipo_factura': 'normal', 'serie_facturacion': 'TESTFIN',
        '_idempotency_key': f'factura_{ORD_OK}_a',
    }
    r1 = await execute_tool(db_seed, api_key=key, tool_name='emitir_factura_orden', params=dict(p1))
    assert r1['success']
    # 2ª factura normal con idempotency DIFERENTE debe fallar por ya emitida
    p2 = dict(p1, _idempotency_key=f'factura_{ORD_OK}_b')
    r2 = await execute_tool(db_seed, api_key=key, tool_name='emitir_factura_orden', params=p2)
    assert r2['success'] is False
    assert r2['error'] == 'factura_ya_emitida'


@pytest.mark.asyncio
async def test_emitir_rectificativa_con_origen(db_seed):
    key = await _make_key(db_seed, f'{PFX}fin8', ['finance:bill', 'meta:ping'])
    # Emite normal primero
    r1 = await execute_tool(db_seed, api_key=key, tool_name='emitir_factura_orden', params={
        'order_id': ORD_OK, 'tipo_factura': 'normal', 'serie_facturacion': 'TESTFIN',
        '_idempotency_key': f'factura_{ORD_OK}_orig',
    })
    # Rectificativa referenciando a la anterior
    r2 = await execute_tool(db_seed, api_key=key, tool_name='emitir_factura_orden', params={
        'order_id': ORD_OK, 'tipo_factura': 'rectificativa', 'serie_facturacion': 'TESTFIN',
        'factura_origen_id': r1['factura_id'],
        '_idempotency_key': f'factura_{ORD_OK}_rect',
    })
    assert r2['success'] is True
    assert r2['tipo_factura'] == 'rectificativa'
    assert 'R-' in r2['numero_factura']


# ──────────────────────────────────────────────────────────────────────────────
# 3 · enviar_recordatorio_cobro
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recordatorio_amistoso_preview(db_seed):
    key = await _make_key(db_seed, f'{PFX}fin9', ['finance:dunning', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='enviar_recordatorio_cobro', params={
        'factura_id': FAC_NUEVA, 'tipo_recordatorio': 'amistoso',
        '_idempotency_key': f'recordatorio_{FAC_NUEVA}_amistoso',
    })
    assert r['success']
    assert r['preview'] is True
    assert r['tipo_sugerido_por_antiguedad'] == 'amistoso'
    assert '[PREVIEW]' in r['mensaje_enviado']


@pytest.mark.asyncio
async def test_recordatorio_ultimo_aviso_bloqueado_sin_previos(db_seed):
    key = await _make_key(db_seed, f'{PFX}fin10', ['finance:dunning', 'meta:ping'])
    # Factura vieja (45 días) pero sin recordatorios previos
    r = await execute_tool(db_seed, api_key=key, tool_name='enviar_recordatorio_cobro', params={
        'factura_id': FAC_VIEJA, 'tipo_recordatorio': 'ultimo_aviso',
        '_idempotency_key': f'recordatorio_{FAC_VIEJA}_ultimo',
    })
    assert r['success'] is False
    assert r['error'] == 'ultimo_aviso_sin_previos'
    assert r['tipo_sugerido'] == 'ultimo_aviso'  # por antigüedad


@pytest.mark.asyncio
async def test_recordatorio_ultimo_aviso_ok_tras_previo(db_seed):
    key = await _make_key(db_seed, f'{PFX}fin11', ['finance:dunning', 'meta:ping'])
    # Envía primero formal
    r1 = await execute_tool(db_seed, api_key=key, tool_name='enviar_recordatorio_cobro', params={
        'factura_id': FAC_VIEJA, 'tipo_recordatorio': 'formal',
        '_idempotency_key': f'recordatorio_{FAC_VIEJA}_formal',
    })
    assert r1['success']
    # Ahora sí puede enviar último aviso
    r2 = await execute_tool(db_seed, api_key=key, tool_name='enviar_recordatorio_cobro', params={
        'factura_id': FAC_VIEJA, 'tipo_recordatorio': 'ultimo_aviso',
        '_idempotency_key': f'recordatorio_{FAC_VIEJA}_ultimo2',
    })
    assert r2['success']
    assert r2['tipo_recordatorio'] == 'ultimo_aviso'


@pytest.mark.asyncio
async def test_recordatorio_warning_mas_severo(db_seed):
    key = await _make_key(db_seed, f'{PFX}fin12', ['finance:dunning', 'meta:ping'])
    # FAC_NUEVA (5 días) sugerido amistoso — pedimos formal → warning
    r = await execute_tool(db_seed, api_key=key, tool_name='enviar_recordatorio_cobro', params={
        'factura_id': FAC_NUEVA, 'tipo_recordatorio': 'formal',
        '_idempotency_key': f'recordatorio_{FAC_NUEVA}_formal',
    })
    assert r['success']
    assert r['warning'] is not None
    assert 'sugerido' in r['warning'].lower()


# ──────────────────────────────────────────────────────────────────────────────
# 4 · calcular_modelo_303
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_modelo_303_aviso_legal_y_calculo(db_seed):
    # Añadir una compra y venta dentro del trimestre actual
    now = datetime.now(timezone.utc)
    await db_seed.facturas.insert_many([
        {
            'id': f'{PFX}v_303_1', 'tipo': 'venta', 'estado': 'emitida',
            'numero': 'V303-1',
            'fecha_emision': _iso(now),
            'base_imponible': 1000, 'total_iva': 210, 'total': 1210,
        },
        {
            'id': f'{PFX}c_303_1', 'tipo': 'compra',
            'numero': 'C303-1',
            'fecha_emision': _iso(now),
            'base_imponible': 500, 'total_iva': 105, 'total': 605,
        },
    ])
    key = await _make_key(db_seed, f'{PFX}fin13', ['finance:fiscal_calc', 'meta:ping'])
    trim = (now.month - 1) // 3 + 1
    r = await execute_tool(db_seed, api_key=key, tool_name='calcular_modelo_303', params={
        'trimestre': trim, 'anno': now.year,
    })
    assert 'aviso_legal' in r
    assert 'asesor fiscal' in r['aviso_legal'].lower()
    assert r['ventas']['iva_repercutido'] >= 210
    assert r['compras']['iva_soportado_deducible'] >= 105
    # resultado = 210 - 105 = 105 → a ingresar
    assert r['resultado']['tipo'] in {'a_ingresar', 'cero'}  # dependiendo de otras facturas

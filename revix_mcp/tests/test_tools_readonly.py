"""
Tests integrales para las 8 tools MCP read-only (Fase 1).

Fixtures insertan datos mock con prefijo `test_mcp_` en la BD `revix_preview`
y los limpian después de cada test. Nunca tocan colecciones de producción
(la DB es `revix_preview` verificada en el fixture).

Tools cubiertas:
  1. buscar_orden
  2. listar_ordenes
  3. buscar_cliente
  4. obtener_historial_cliente
  5. consultar_inventario
  6. obtener_metricas
  7. obtener_dashboard
  8. buscar_por_token_seguimiento
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

from revix_mcp import auth
from revix_mcp.config import (
    API_KEYS_COLLECTION, AUDIT_COLLECTION, DB_NAME, IDEMPOTENCY_COLLECTION, MONGO_URL,
)
from revix_mcp.runtime import ToolExecutionError, execute_tool
from revix_mcp.tools import (  # noqa: F401 — side-effect registro
    clients, inventory, metrics, orders, tracking,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

CLIENTE_ID = 'test_mcp_cli_001'
CLIENTE_ID_2 = 'test_mcp_cli_002'
ORDEN_ID_1 = 'test_mcp_ord_001'
ORDEN_ID_2 = 'test_mcp_ord_002'
ORDEN_ID_3 = 'test_mcp_ord_003'
REPUESTO_ID_1 = 'test_mcp_rep_001'
REPUESTO_ID_2 = 'test_mcp_rep_002'
REPUESTO_ID_3 = 'test_mcp_rep_003'
TOKEN_PUBLIC = 'ABCD1234XYZ'


def _now_iso(delta_days: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=delta_days)).isoformat(timespec='seconds')


@pytest_asyncio.fixture
async def db_with_seed():
    """DB preview + datos mock (clientes, órdenes, repuestos) + limpieza."""
    assert DB_NAME != 'production', 'Tests no corren sobre production'
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]

    # Limpieza previa
    await database.clientes.delete_many({'id': {'$regex': '^test_mcp_'}})
    await database.ordenes.delete_many({'id': {'$regex': '^test_mcp_'}})
    await database.repuestos.delete_many({'id': {'$regex': '^test_mcp_'}})
    for coll in (API_KEYS_COLLECTION, IDEMPOTENCY_COLLECTION):
        await database[coll].delete_many({'agent_id': {'$regex': '^test_'}})
    await database[AUDIT_COLLECTION].delete_many(
        {'source': 'mcp_agent', 'agent_id': {'$regex': '^test_'}},
    )

    # Clientes seed
    await database.clientes.insert_many([
        {
            'id': CLIENTE_ID, 'nombre': 'Luisa', 'apellidos': 'Mock García',
            'dni': 'T00000001E', 'telefono': '600111222', 'email': 'luisa.mock@test.com',
            'direccion': 'C/ Test 1', 'tipo_cliente': 'particular',
            'notas_internas': 'OJO no devolver en respuesta',
            'created_at': _now_iso(-2), 'updated_at': _now_iso(-2),
        },
        {
            'id': CLIENTE_ID_2, 'nombre': 'Pedro', 'apellidos': 'Mock López',
            'dni': 'T00000002F', 'telefono': '600333444', 'email': 'pedro@test.com',
            'direccion': 'C/ Test 2', 'tipo_cliente': 'particular',
            'created_at': _now_iso(-1), 'updated_at': _now_iso(-1),
        },
    ])

    # Órdenes seed
    hoy = _now_iso()
    ayer = _now_iso(-1)
    await database.ordenes.insert_many([
        {
            'id': ORDEN_ID_1,
            'numero_orden': 'OT-TESTMCP-0001',
            'numero_autorizacion': 'AUTH-MCP-1',
            'token_seguimiento': TOKEN_PUBLIC,
            'cliente_id': CLIENTE_ID,
            'dispositivo': {'marca': 'Apple', 'modelo': 'iPhone 14', 'daños': 'pantalla rota'},
            'estado': 'enviado',
            'es_garantia': False,
            'tecnico_asignado': 'tecnico_test_uuid_01',
            'presupuesto_total': 200.0, 'coste_total': 80.0, 'beneficio_estimado': 120.0,
            'presupuesto_emitido': True, 'presupuesto_precio': 200.0,
            'presupuesto_aceptado': True,
            'presupuesto_fecha_emision': ayer,
            'created_at': ayer, 'updated_at': hoy, 'fecha_enviado': hoy,
            'materiales': [{'nombre': 'Pantalla iP14', 'cantidad': 1, 'precio_unitario': 150, 'coste': 60}],
        },
        {
            'id': ORDEN_ID_2,
            'numero_orden': 'OT-TESTMCP-0002',
            'cliente_id': CLIENTE_ID,
            'dispositivo': {'marca': 'Samsung', 'modelo': 'Galaxy S23', 'daños': 'batería'},
            'estado': 'reparando',
            'es_garantia': True,
            'tecnico_asignado': 'tecnico_test_uuid_01',
            'presupuesto_total': 90.0, 'coste_total': 25.0,
            'token_seguimiento': 'TRK000000002',
            'created_at': hoy, 'updated_at': hoy,
            'materiales': [],
        },
        {
            'id': ORDEN_ID_3,
            'numero_orden': 'OT-TESTMCP-0003',
            'cliente_id': CLIENTE_ID_2,
            'dispositivo': {'marca': 'Apple', 'modelo': 'iPhone 14', 'daños': 'pantalla rota'},
            'estado': 'pendiente_recibir',
            'es_garantia': False,
            'token_seguimiento': 'TRK000000003',
            'created_at': hoy, 'updated_at': hoy,
            'materiales': [],
        },
    ])

    # Repuestos seed
    await database.repuestos.insert_many([
        {
            'id': REPUESTO_ID_1, 'nombre': 'Pantalla iPhone 14 OLED',
            'categoria': 'pantalla', 'sku': 'TESTMCP-SCR-IP14',
            'proveedor': 'MobileSentrix', 'stock': 3, 'stock_minimo': 5,
            'precio_compra': 60, 'precio_venta': 150,
            'es_pantalla': True, 'calidad_pantalla': 'hard_oled',
            'modelo_compatible': 'iPhone 14',
            'created_at': _now_iso(-5), 'updated_at': _now_iso(-1),
        },
        {
            'id': REPUESTO_ID_2, 'nombre': 'Batería Samsung S23',
            'categoria': 'bateria', 'sku': 'TESTMCP-BAT-S23',
            'proveedor': 'Utopya', 'stock': 0, 'stock_minimo': 2,
            'precio_compra': 20, 'precio_venta': 45,
            'es_pantalla': False, 'modelo_compatible': 'Galaxy S23',
            'created_at': _now_iso(-10), 'updated_at': _now_iso(-2),
        },
        {
            'id': REPUESTO_ID_3, 'nombre': 'Tornillo pentalobe',
            'categoria': 'accesorio', 'sku': 'TESTMCP-TORN-01',
            'proveedor': 'MobileSentrix', 'stock': 500, 'stock_minimo': 100,
            'precio_compra': 0.05, 'precio_venta': 0.5,
            'es_pantalla': False,
            'created_at': _now_iso(-30), 'updated_at': _now_iso(-30),
        },
    ])

    yield database

    # Limpieza post
    await database.clientes.delete_many({'id': {'$regex': '^test_mcp_'}})
    await database.ordenes.delete_many({'id': {'$regex': '^test_mcp_'}})
    await database.repuestos.delete_many({'id': {'$regex': '^test_mcp_'}})
    for coll in (API_KEYS_COLLECTION, IDEMPOTENCY_COLLECTION):
        await database[coll].delete_many({'agent_id': {'$regex': '^test_'}})
    await database[AUDIT_COLLECTION].delete_many(
        {'source': 'mcp_agent', 'agent_id': {'$regex': '^test_'}},
    )
    client.close()


async def _make_key(db, agent_id: str, scopes: list[str]) -> str:
    plain, _ = await auth.create_api_key(
        db, agent_id=agent_id, agent_name=agent_id,
        scopes=scopes, created_by='pytest',
    )
    return plain


# ──────────────────────────────────────────────────────────────────────────────
# 1 & 2 — Órdenes
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_buscar_orden_por_uuid(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='buscar_orden',
                           params={'ref': ORDEN_ID_1})
    assert r['found'] is True
    assert r['orden']['numero_orden'] == 'OT-TESTMCP-0001'
    assert '_id' not in r['orden']
    assert r['cliente']['nombre'] == 'Luisa'


@pytest.mark.asyncio
async def test_buscar_orden_por_numero(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='buscar_orden',
                           params={'ref': 'OT-TESTMCP-0002'})
    assert r['found'] is True
    assert r['orden']['estado'] == 'reparando'


@pytest.mark.asyncio
async def test_buscar_orden_por_autorizacion(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='buscar_orden',
                           params={'ref': 'AUTH-MCP-1'})
    assert r['found'] is True
    assert r['orden']['id'] == ORDEN_ID_1


@pytest.mark.asyncio
async def test_buscar_orden_no_existe(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='buscar_orden',
                           params={'ref': 'NOEXISTE-0000'})
    assert r['found'] is False


@pytest.mark.asyncio
async def test_listar_ordenes_con_filtros(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    # Todas las del cliente 1
    r = await execute_tool(db, api_key=key, tool_name='listar_ordenes',
                           params={'cliente_id': CLIENTE_ID, 'limit': 10})
    ids = {o['id'] for o in r['items']}
    assert ORDEN_ID_1 in ids and ORDEN_ID_2 in ids
    assert r['total'] >= 2

    # Filtro por estado
    r2 = await execute_tool(db, api_key=key, tool_name='listar_ordenes',
                            params={'estado': 'reparando'})
    for o in r2['items']:
        assert o['estado'] == 'reparando'

    # Filtro garantía
    r3 = await execute_tool(db, api_key=key, tool_name='listar_ordenes',
                            params={'es_garantia': True})
    ids3 = {o['id'] for o in r3['items']}
    assert ORDEN_ID_2 in ids3


@pytest.mark.asyncio
async def test_listar_ordenes_scope_denied(db_with_seed):
    db = db_with_seed
    # solo customers:read → NO cubre orders:read
    key = await _make_key(db, 'test_nope', ['customers:read', 'meta:ping'])
    with pytest.raises(ToolExecutionError, match='orders:read'):
        await execute_tool(db, api_key=key, tool_name='listar_ordenes', params={})


# ──────────────────────────────────────────────────────────────────────────────
# 3 & 4 — Clientes
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_buscar_cliente_exacto_por_dni(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='buscar_cliente',
                           params={'q': 'T00000001E'})
    assert r['match_type'] == 'exact'
    assert r['count'] == 1
    assert r['items'][0]['id'] == CLIENTE_ID
    # notas_internas nunca se devuelve
    assert 'notas_internas' not in r['items'][0]


@pytest.mark.asyncio
async def test_buscar_cliente_fuzzy_por_nombre(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='buscar_cliente',
                           params={'q': 'Mock'})
    assert r['match_type'] == 'fuzzy'
    ids = {c['id'] for c in r['items']}
    assert CLIENTE_ID in ids and CLIENTE_ID_2 in ids


@pytest.mark.asyncio
async def test_historial_cliente_devuelve_resumen_y_ordenes(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='obtener_historial_cliente',
                           params={'cliente_id': CLIENTE_ID})
    assert r['found'] is True
    assert r['resumen']['total_ordenes'] >= 2
    assert r['resumen']['en_garantia'] >= 1
    assert len(r['ordenes']) >= 2
    # Por defecto sin materiales
    assert 'materiales' not in r['ordenes'][0]


@pytest.mark.asyncio
async def test_historial_cliente_con_materiales(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='obtener_historial_cliente',
                           params={'cliente_id': CLIENTE_ID, 'incluir_materiales': True})
    con_materiales = next((o for o in r['ordenes'] if o['id'] == ORDEN_ID_1), None)
    assert con_materiales is not None
    assert isinstance(con_materiales.get('materiales'), list)


# ──────────────────────────────────────────────────────────────────────────────
# 5 — Inventario
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_consultar_inventario_nivel_stock(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='consultar_inventario',
                           params={'q': 'TESTMCP'})
    niveles = {it['id']: it['nivel_stock'] for it in r['items']}
    assert niveles[REPUESTO_ID_1] == 'bajo_minimo'   # 3 <= 5
    assert niveles[REPUESTO_ID_2] == 'sin_stock'     # 0
    assert niveles[REPUESTO_ID_3] == 'ok'            # 500 > 100


@pytest.mark.asyncio
async def test_consultar_inventario_solo_sin_stock(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='consultar_inventario',
                           params={'solo_sin_stock': True, 'q': 'TESTMCP'})
    ids = {it['id'] for it in r['items']}
    assert REPUESTO_ID_2 in ids
    assert REPUESTO_ID_3 not in ids


@pytest.mark.asyncio
async def test_consultar_inventario_filtro_proveedor_y_pantalla(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='consultar_inventario',
                           params={'proveedor': 'MobileSentrix', 'es_pantalla': True, 'q': 'TESTMCP'})
    assert all(it['proveedor'] == 'MobileSentrix' and it['es_pantalla'] for it in r['items'])
    assert any(it['id'] == REPUESTO_ID_1 for it in r['items'])


# ──────────────────────────────────────────────────────────────────────────────
# 6 & 7 — Métricas / Dashboard
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_obtener_metricas_ordenes_por_estado(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='obtener_metricas',
                           params={'metrica': 'ordenes_por_estado', 'periodo': 'mes'})
    estados = {it['estado']: it['count'] for it in r['items']}
    # Nuestras 3 órdenes seed
    assert estados.get('enviado', 0) >= 1
    assert estados.get('reparando', 0) >= 1
    assert estados.get('pendiente_recibir', 0) >= 1


@pytest.mark.asyncio
async def test_obtener_metricas_ingresos(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='obtener_metricas',
                           params={'metrica': 'ingresos_periodo', 'periodo': 'año'})
    # La orden 1 (enviada) tiene presupuesto_total=200
    assert r['total'] >= 200
    assert r['ordenes_enviadas'] >= 1


@pytest.mark.asyncio
async def test_obtener_metricas_top_modelos(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='obtener_metricas',
                           params={'metrica': 'top_modelos_reparados', 'periodo': 'mes', 'top': 5})
    modelos = {it['modelo']: it['count'] for it in r['items']}
    # iPhone 14 aparece 2 veces en seed
    assert modelos.get('iPhone 14', 0) >= 2


@pytest.mark.asyncio
async def test_obtener_dashboard(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='obtener_dashboard',
                           params={'periodo': 'año'})
    assert r['ordenes']['total_periodo'] >= 3
    assert r['finanzas']['ingresos'] >= 200
    assert r['inventario']['total_skus'] >= 3
    assert r['inventario']['sin_stock'] >= 1
    assert r['inventario']['bajo_minimo'] >= 1


# ──────────────────────────────────────────────────────────────────────────────
# 8 — Seguimiento público por token
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tracking_devuelve_info_minima(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_public', ['public:track_by_token', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='buscar_por_token_seguimiento',
                           params={'token': TOKEN_PUBLIC})
    assert r['found'] is True
    assert r['numero_orden'] == 'OT-TESTMCP-0001'
    assert r['estado'] == 'enviado'
    assert 'coste' not in r  # nunca exponer coste
    assert 'materiales' not in r
    assert 'tecnico' not in str(r)  # no técnico
    assert r['dispositivo']['marca'] == 'Apple'
    # Presupuesto emitido y aceptado → campo presupuesto presente
    assert r['presupuesto'] is not None
    assert r['presupuesto']['aceptado'] is True


@pytest.mark.asyncio
async def test_tracking_token_inexistente(db_with_seed):
    db = db_with_seed
    key = await _make_key(db, 'test_public', ['public:track_by_token', 'meta:ping'])
    r = await execute_tool(db, api_key=key, tool_name='buscar_por_token_seguimiento',
                           params={'token': 'NO-EXISTE-XXX'})
    assert r['found'] is False


@pytest.mark.asyncio
async def test_tracking_wildcard_read_no_basta(db_with_seed):
    """*:read NO cubre public:track_by_token (seguridad estricta)."""
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])
    with pytest.raises(ToolExecutionError, match='public:track_by_token'):
        await execute_tool(db, api_key=key, tool_name='buscar_por_token_seguimiento',
                           params={'token': TOKEN_PUBLIC})


# ──────────────────────────────────────────────────────────────────────────────
# Integridad transversal
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log_por_cada_tool_ejecutada(db_with_seed):
    """Cada tool read-only ejecutada debe dejar rastro en audit_logs."""
    db = db_with_seed
    key = await _make_key(db, 'test_audit_r', ['*:read', 'meta:ping'])
    await execute_tool(db, api_key=key, tool_name='buscar_orden', params={'ref': ORDEN_ID_1})
    await execute_tool(db, api_key=key, tool_name='consultar_inventario', params={'q': 'TESTMCP'})

    logs_count = await db[AUDIT_COLLECTION].count_documents(
        {'source': 'mcp_agent', 'agent_id': 'test_audit_r'},
    )
    assert logs_count >= 2


@pytest.mark.asyncio
async def test_ningun_tool_devuelve_mongo_id(db_with_seed):
    """Sanity check: ninguna tool read-only filtra la clave Mongo `_id`."""
    db = db_with_seed
    key = await _make_key(db, 'test_kpi', ['*:read', 'meta:ping'])

    def _contains_mongo_id(obj) -> bool:
        if isinstance(obj, dict):
            if '_id' in obj:
                return True
            return any(_contains_mongo_id(v) for v in obj.values())
        if isinstance(obj, list):
            return any(_contains_mongo_id(it) for it in obj)
        return False

    checks = [
        ('buscar_orden', {'ref': ORDEN_ID_1}),
        ('listar_ordenes', {'cliente_id': CLIENTE_ID}),
        ('buscar_cliente', {'q': CLIENTE_ID}),
        ('obtener_historial_cliente', {'cliente_id': CLIENTE_ID}),
        ('consultar_inventario', {'q': 'TESTMCP'}),
        ('obtener_metricas', {'metrica': 'ordenes_por_estado'}),
        ('obtener_dashboard', {'periodo': 'año'}),
    ]
    for name, params in checks:
        r = await execute_tool(db, api_key=key, tool_name=name, params=params)
        assert not _contains_mongo_id(r), f'{name} filtró clave _id en su respuesta'

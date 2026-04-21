"""
Tests Fase 2 · Tools del Supervisor de Cola Operacional.

Cubre:
  - listar_ordenes_en_riesgo_sla (calcula y ordena correctamente 3 niveles)
  - marcar_orden_en_riesgo (éxito, orden inexistente, idempotencia, doble-scope)
  - abrir_incidencia (éxito, orden inexistente, anti-duplicado)
  - enviar_notificacion (preview mock, persiste traza)
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
from revix_mcp.runtime import ToolExecutionError, execute_tool
from revix_mcp.tools import supervisor_cola  # noqa: F401 — side-effect registro


ORD_CRITICA = 'test_sup_ord_critica'
ORD_ROJA = 'test_sup_ord_roja'
ORD_AMARILLA = 'test_sup_ord_amarilla'
ORD_SANA = 'test_sup_ord_sana'
ORD_ENVIADA = 'test_sup_ord_enviada'
CLI_ID = 'test_sup_cli'


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec='seconds')


@pytest_asyncio.fixture
async def db_seed():
    assert DB_NAME != 'production'
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]

    # Limpieza
    await database.ordenes.delete_many({'id': {'$regex': '^test_sup_'}})
    await database.incidencias.delete_many({'orden_id': {'$regex': '^test_sup_'}})
    await database.notificaciones.delete_many({'orden_id': {'$regex': '^test_sup_'}})
    await database[API_KEYS_COLLECTION].delete_many({'agent_id': {'$regex': '^test_sup_'}})
    await database[IDEMPOTENCY_COLLECTION].delete_many({'agent_id': {'$regex': '^test_sup_'}})
    await database[AUDIT_COLLECTION].delete_many({'agent_id': {'$regex': '^test_sup_'}})
    await database[rate_limit.USAGE_COLLECTION].delete_many({'agent_id': {'$regex': '^test_sup_'}})
    await database[rate_limit.LIMITS_COLLECTION].delete_many({'agent_id': {'$regex': '^test_sup_'}})
    rate_limit.invalidate_limits_cache()

    # Órdenes con distintos vencimientos SLA (sla_dias=5 por defecto)
    now = datetime.now(timezone.utc)
    ords = [
        {
            'id': ORD_CRITICA, 'numero_orden': 'OT-SUP-CRIT', 'cliente_id': CLI_ID,
            'estado': 'reparando',
            'dispositivo': {'marca': 'Apple', 'modelo': 'iPhone 14', 'daños': 'x'},
            'sla_dias': 5,
            'created_at': _iso(now - timedelta(days=10)),  # vencida hace 5 días
            'updated_at': _iso(now - timedelta(days=2)),
        },
        {
            'id': ORD_ROJA, 'numero_orden': 'OT-SUP-ROJO', 'cliente_id': CLI_ID,
            'estado': 'diagnosticando',
            'dispositivo': {'marca': 'Samsung', 'modelo': 'S23', 'daños': 'y'},
            'sla_dias': 5,
            'created_at': _iso(now - timedelta(hours=108)),  # 12h restantes (rojo <=24h)
            'updated_at': _iso(now),
        },
        {
            'id': ORD_AMARILLA, 'numero_orden': 'OT-SUP-AMAR', 'cliente_id': CLI_ID,
            'estado': 'recibido',
            'dispositivo': {'marca': 'Xiaomi', 'modelo': 'Mi12', 'daños': 'z'},
            'sla_dias': 5,
            'created_at': _iso(now - timedelta(hours=72)),  # 48h restantes (amarillo <=72h)
            'updated_at': _iso(now),
        },
        {
            'id': ORD_SANA, 'numero_orden': 'OT-SUP-SANA', 'cliente_id': CLI_ID,
            'estado': 'reparando',
            'dispositivo': {'marca': 'Pixel', 'modelo': '8', 'daños': 'w'},
            'sla_dias': 5,
            'created_at': _iso(now - timedelta(hours=12)),  # 108h restantes (sana)
            'updated_at': _iso(now),
        },
        {
            'id': ORD_ENVIADA, 'numero_orden': 'OT-SUP-ENV', 'cliente_id': CLI_ID,
            'estado': 'enviado',  # NO activa, se ignora aunque esté vencida
            'dispositivo': {'marca': 'Apple', 'modelo': 'X', 'daños': 'z'},
            'sla_dias': 5,
            'created_at': _iso(now - timedelta(days=20)),
            'updated_at': _iso(now),
        },
    ]
    await database.ordenes.insert_many(ords)

    yield database

    # Limpieza post
    await database.ordenes.delete_many({'id': {'$regex': '^test_sup_'}})
    await database.incidencias.delete_many({'orden_id': {'$regex': '^test_sup_'}})
    await database.notificaciones.delete_many({'orden_id': {'$regex': '^test_sup_'}})
    await database[API_KEYS_COLLECTION].delete_many({'agent_id': {'$regex': '^test_sup_'}})
    await database[IDEMPOTENCY_COLLECTION].delete_many({'agent_id': {'$regex': '^test_sup_'}})
    await database[AUDIT_COLLECTION].delete_many({'agent_id': {'$regex': '^test_sup_'}})
    await database[rate_limit.USAGE_COLLECTION].delete_many({'agent_id': {'$regex': '^test_sup_'}})
    await database[rate_limit.LIMITS_COLLECTION].delete_many({'agent_id': {'$regex': '^test_sup_'}})
    rate_limit.invalidate_limits_cache()
    client.close()


async def _make_key(db, agent_id: str, scopes: list[str]) -> str:
    plain, _ = await auth.create_api_key(
        db, agent_id=agent_id, agent_name=agent_id,
        scopes=scopes, created_by='pytest',
    )
    return plain


# ──────────────────────────────────────────────────────────────────────────────
# 1 · listar_ordenes_en_riesgo_sla
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_listar_riesgo_ordena_por_severidad(db_seed):
    key = await _make_key(db_seed, 'test_sup_sup1', [
        'orders:read', 'incidents:write', 'notifications:write', 'meta:ping',
    ])
    r = await execute_tool(db_seed, api_key=key, tool_name='listar_ordenes_en_riesgo_sla',
                           params={'limit': 500})
    # Filtrar solo nuestras órdenes test y mapear id → posición + nivel
    test_items = [o for o in r['items'] if o['id'].startswith('test_sup_')]
    positions = {o['id']: i for i, o in enumerate(test_items)}
    niveles = {o['id']: o['nivel_riesgo'] for o in test_items}
    # Las 3 deben estar presentes
    assert ORD_CRITICA in positions
    assert ORD_ROJA in positions
    assert ORD_AMARILLA in positions
    # Orden relativo correcto
    assert positions[ORD_CRITICA] < positions[ORD_ROJA] < positions[ORD_AMARILLA]
    # Niveles correctos
    assert niveles[ORD_CRITICA] == 'critico'
    assert niveles[ORD_ROJA] == 'rojo'
    assert niveles[ORD_AMARILLA] == 'amarillo'
    # ORD_SANA y ORD_ENVIADA NO deben aparecer
    assert ORD_SANA not in positions
    assert ORD_ENVIADA not in positions
    # Resumen global (incluye otras órdenes de la BD) — al menos 1 de cada
    assert r['resumen']['critico'] >= 1
    assert r['resumen']['rojo'] >= 1
    assert r['resumen']['amarillo'] >= 1


@pytest.mark.asyncio
async def test_listar_riesgo_respeta_umbral_horas(db_seed):
    key = await _make_key(db_seed, 'test_sup_sup2', ['orders:read', 'meta:ping'])
    # Umbral=24 → solo debería ver crítica y roja (no amarilla)
    r = await execute_tool(db_seed, api_key=key, tool_name='listar_ordenes_en_riesgo_sla',
                           params={'umbral_horas': 24})
    ids = [o['id'] for o in r['items']]
    assert ORD_CRITICA in ids
    assert ORD_ROJA in ids
    assert ORD_AMARILLA not in ids


# ──────────────────────────────────────────────────────────────────────────────
# 2 · marcar_orden_en_riesgo
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_marcar_riesgo_ok_y_persiste(db_seed):
    key = await _make_key(db_seed, 'test_sup_mark1', [
        'orders:read', 'incidents:write', 'meta:ping',
    ])
    r = await execute_tool(db_seed, api_key=key, tool_name='marcar_orden_en_riesgo', params={
        'order_id': ORD_CRITICA,
        'nivel_riesgo': 'critico',
        'motivo': 'Proveedor no confirma recepción, dispositivo parado.',
        '_idempotency_key': 'mark-ord-critica-test-1',
    })
    assert r['success'] is True
    assert r['nivel_riesgo_nuevo'] == 'critico'

    # Persistido en la orden
    doc = await db_seed.ordenes.find_one({'id': ORD_CRITICA}, {'_id': 0})
    assert doc['nivel_riesgo_actual'] == 'critico'
    assert doc['marcado_riesgo_motivo'].startswith('Proveedor')
    assert doc['marcado_riesgo_por'] == 'mcp:test_sup_mark1'
    assert len(doc.get('historial_riesgo', [])) == 1


@pytest.mark.asyncio
async def test_marcar_riesgo_idempotente(db_seed):
    key = await _make_key(db_seed, 'test_sup_mark2', [
        'orders:read', 'incidents:write', 'meta:ping',
    ])
    params = {
        'order_id': ORD_ROJA,
        'nivel_riesgo': 'rojo',
        'motivo': 'SLA < 24h',
        '_idempotency_key': 'dup-key-123',
    }
    r1 = await execute_tool(db_seed, api_key=key, tool_name='marcar_orden_en_riesgo', params=dict(params))
    r2 = await execute_tool(db_seed, api_key=key, tool_name='marcar_orden_en_riesgo', params=dict(params))
    assert r1 == r2
    # El historial debe tener solo 1 entrada (la 2ª llamada fue cacheada)
    doc = await db_seed.ordenes.find_one({'id': ORD_ROJA}, {'_id': 0})
    assert len(doc.get('historial_riesgo', [])) == 1


@pytest.mark.asyncio
async def test_marcar_riesgo_orden_inexistente(db_seed):
    key = await _make_key(db_seed, 'test_sup_mark3', [
        'orders:read', 'incidents:write', 'meta:ping',
    ])
    r = await execute_tool(db_seed, api_key=key, tool_name='marcar_orden_en_riesgo', params={
        'order_id': 'no-existe-xxx',
        'nivel_riesgo': 'rojo',
        'motivo': 'prueba',
        '_idempotency_key': 'noexiste-1',
    })
    assert r['success'] is False
    assert r['error'] == 'order_not_found'


@pytest.mark.asyncio
async def test_marcar_riesgo_requiere_orders_read(db_seed):
    # Agente solo con incidents:write (sin orders:read) debe fallar
    key = await _make_key(db_seed, 'test_sup_mark4', ['incidents:write', 'meta:ping'])
    with pytest.raises(ToolExecutionError, match='orders:read'):
        await execute_tool(db_seed, api_key=key, tool_name='marcar_orden_en_riesgo', params={
            'order_id': ORD_CRITICA,
            'nivel_riesgo': 'critico',
            'motivo': 'x',
            '_idempotency_key': 'x-1',
        })


# ──────────────────────────────────────────────────────────────────────────────
# 3 · abrir_incidencia
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_abrir_incidencia_ok(db_seed):
    key = await _make_key(db_seed, 'test_sup_inc1', ['incidents:write', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='abrir_incidencia', params={
        'order_id': ORD_AMARILLA,
        'tipo_incidencia': 'retraso_proveedor',
        'descripcion': 'Proveedor MobileSentrix sin confirmar pedido',
        'prioridad': 'alta',
        '_idempotency_key': 'inc-1',
    })
    assert r['success'] is True
    assert r['numero_incidencia'].startswith('INC-')

    doc = await db_seed.incidencias.find_one({'id': r['incidencia_id']}, {'_id': 0})
    assert doc['estado'] == 'abierta'
    assert doc['prioridad'] == 'alta'
    assert doc['tipo'] == 'retraso_proveedor'
    assert doc['created_by'] == 'mcp:test_sup_inc1'


@pytest.mark.asyncio
async def test_abrir_incidencia_bloquea_duplicado(db_seed):
    key = await _make_key(db_seed, 'test_sup_inc2', ['incidents:write', 'meta:ping'])
    # 1ª
    r1 = await execute_tool(db_seed, api_key=key, tool_name='abrir_incidencia', params={
        'order_id': ORD_ROJA, 'tipo_incidencia': 'material_incorrecto',
        'descripcion': 'Pantalla recibida con pixel muerto',
        'prioridad': 'media',
        '_idempotency_key': 'inc-dup-1',
    })
    assert r1['success'] is True
    # 2ª con idempotency_key DISTINTO → la lógica anti-duplicado debe rechazar
    r2 = await execute_tool(db_seed, api_key=key, tool_name='abrir_incidencia', params={
        'order_id': ORD_ROJA, 'tipo_incidencia': 'material_incorrecto',
        'descripcion': 'Otra descripción',
        'prioridad': 'alta',
        '_idempotency_key': 'inc-dup-2',
    })
    assert r2['success'] is False
    assert r2['error'] == 'incidencia_abierta_ya_existe'
    assert r2['incidencia_existente']['numero_incidencia'] == r1['numero_incidencia']


@pytest.mark.asyncio
async def test_abrir_incidencia_orden_inexistente(db_seed):
    key = await _make_key(db_seed, 'test_sup_inc3', ['incidents:write', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='abrir_incidencia', params={
        'order_id': 'no-existe-zzz', 'tipo_incidencia': 'otro',
        'descripcion': 'xxx', 'prioridad': 'baja',
        '_idempotency_key': 'inc-noexiste-1',
    })
    assert r['success'] is False
    assert r['error'] == 'order_not_found'


# ──────────────────────────────────────────────────────────────────────────────
# 4 · enviar_notificacion
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_enviar_notif_preview_interno(db_seed):
    key = await _make_key(db_seed, 'test_sup_notif1', ['notifications:write', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='enviar_notificacion', params={
        'destinatario_id': 'tecnico-abc',
        'canal': 'interno',
        'mensaje': 'Revisar pantalla de test',
        'referencia_orden': ORD_CRITICA,
    })
    assert r['success'] is True
    # Persistida
    doc = await db_seed.notificaciones.find_one({'id': r['notificacion_id']}, {'_id': 0})
    assert doc['source'] == 'mcp_agent'
    assert doc['agent_id'] == 'test_sup_notif1'
    assert '[PREVIEW]' in doc['mensaje']  # MCP_ENV=preview


@pytest.mark.asyncio
async def test_enviar_notif_preview_email_mock(db_seed):
    key = await _make_key(db_seed, 'test_sup_notif2', ['notifications:write', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='enviar_notificacion', params={
        'destinatario_id': 'tecnico-xyz',
        'canal': 'email',
        'mensaje': 'Avería urgente pendiente',
        'referencia_orden': ORD_ROJA,
    })
    assert r['success'] is True
    assert r['preview'] is True
    assert '[PREVIEW]' in r['message']
    assert r['canal_solicitado'] == 'email'


# ──────────────────────────────────────────────────────────────────────────────
# Audit transversal
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_todas_las_tools_escriben_audit(db_seed):
    key = await _make_key(db_seed, 'test_sup_audit', [
        'orders:read', 'incidents:write', 'notifications:write', 'meta:ping',
    ])
    await execute_tool(db_seed, api_key=key, tool_name='listar_ordenes_en_riesgo_sla', params={})
    await execute_tool(db_seed, api_key=key, tool_name='marcar_orden_en_riesgo', params={
        'order_id': ORD_AMARILLA, 'nivel_riesgo': 'amarillo', 'motivo': 'test',
        '_idempotency_key': 'audit-1',
    })
    await execute_tool(db_seed, api_key=key, tool_name='enviar_notificacion', params={
        'destinatario_id': 't-1', 'canal': 'interno',
        'mensaje': 'hola', 'referencia_orden': ORD_AMARILLA,
    })
    logs = await db_seed[AUDIT_COLLECTION].find(
        {'agent_id': 'test_sup_audit', 'source': 'mcp_agent'}, {'_id': 0},
    ).to_list(20)
    tools_vistas = {lg['tool'] for lg in logs if lg.get('error') is None}
    assert 'listar_ordenes_en_riesgo_sla' in tools_vistas
    assert 'marcar_orden_en_riesgo' in tools_vistas
    assert 'enviar_notificacion' in tools_vistas

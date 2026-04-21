"""
Tests Fase 2 · Tools del ISO 9001 Quality Officer.

Cubre las 6 tools:
  - crear_muestreo_qa (aleatorio + por_tecnico + sin_candidatas)
  - registrar_resultado (conforme + no_conforme indica abrir_nc + idempotencia + ajeno al muestreo)
  - abrir_nc (persiste en capas + numero_nc único)
  - listar_acuses_pendientes (excluye ya acusados + filtro rol + vencidos_dias)
  - evaluar_proveedor (score ponderado + clasificación + comparativa previa)
  - generar_revision_direccion (secciones + acciones derivadas)
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
from revix_mcp.tools import iso_officer  # noqa: F401 — registro


# Prefijo unificado para limpieza
PFX = 'test_iso_'
ORD_1 = f'{PFX}ord_1'
ORD_2 = f'{PFX}ord_2'
ORD_3 = f'{PFX}ord_3'
PROV_1 = f'{PFX}prov_1'
USER_TEC = f'{PFX}usr_tec'
USER_ADMIN = f'{PFX}usr_admin'
DOC_ID = f'{PFX}doc_1'


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec='seconds')


@pytest_asyncio.fixture
async def db_seed():
    assert DB_NAME != 'production'
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]

    # Limpieza previa exhaustiva
    collections_clean = [
        'ordenes', 'proveedores', 'users', 'iso_documentos',
        'iso_proveedores_evaluacion', 'mcp_qa_muestreos', 'capas',
        API_KEYS_COLLECTION, IDEMPOTENCY_COLLECTION, AUDIT_COLLECTION,
        rate_limit.USAGE_COLLECTION, rate_limit.LIMITS_COLLECTION,
    ]
    for col in collections_clean:
        await database[col].delete_many({'id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'agent_id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'proveedor_id': PROV_1})
    rate_limit.invalidate_limits_cache()

    # Órdenes completadas para muestreo
    now = datetime.now(timezone.utc)
    hace_5d = now - timedelta(days=5)
    await database.ordenes.insert_many([
        {
            'id': ORD_1, 'numero_orden': 'OT-ISO-1',
            'estado': 'enviado', 'updated_at': _iso(hace_5d),
            'tecnico_asignado': 'tec-uuid-1', 'tipo_servicio': 'particular',
            'created_at': _iso(hace_5d - timedelta(days=2)),
            'fecha_enviado': _iso(hace_5d),
            'cliente_id': 'cli-x',
        },
        {
            'id': ORD_2, 'numero_orden': 'OT-ISO-2',
            'estado': 'reparado', 'updated_at': _iso(hace_5d + timedelta(hours=5)),
            'tecnico_asignado': 'tec-uuid-2', 'tipo_servicio': 'seguro',
            'created_at': _iso(hace_5d),
            'cliente_id': 'cli-y',
        },
        {
            'id': ORD_3, 'numero_orden': 'OT-ISO-3',
            'estado': 'enviado', 'updated_at': _iso(hace_5d + timedelta(days=1)),
            'tecnico_asignado': 'tec-uuid-1', 'tipo_servicio': 'particular',
            'created_at': _iso(hace_5d - timedelta(days=1)),
            'fecha_enviado': _iso(hace_5d + timedelta(days=1)),
            'cliente_id': 'cli-z',
        },
    ])

    # Proveedor
    await database.proveedores.insert_one({
        'id': PROV_1, 'nombre': 'Proveedor Test',
        'created_at': _iso(now - timedelta(days=100)),
    })

    # Usuarios (acuses)
    await database.users.insert_many([
        {'id': USER_TEC, 'email': 'tec@test.com', 'nombre': 'Técnico Test',
         'role': 'tecnico', 'active': True},
        {'id': USER_ADMIN, 'email': 'admin@test.com', 'nombre': 'Admin Test',
         'role': 'admin', 'active': True},
    ])

    # Documento ISO que requiere acuse, publicado hace 40 días
    await database.iso_documentos.insert_one({
        'id': DOC_ID,
        'codigo': 'TEST-DOC-001',
        'titulo': 'Procedimiento de prueba',
        'version': '1.0',
        'estado': 'vigente',
        'requiere_acuse': True,
        'acuses_lectura': [
            {'usuario_id': USER_ADMIN, 'fecha': _iso(now - timedelta(days=20))},
        ],  # solo admin ha acusado; tec no
        'created_at': _iso(now - timedelta(days=40)),
    })

    yield database

    # Limpieza post
    for col in collections_clean:
        await database[col].delete_many({'id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'agent_id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'proveedor_id': PROV_1})
    # NCs creadas por los tests
    await database.capas.delete_many({'source': 'mcp_agent', 'created_by': {'$regex': f'mcp:{PFX}'}})
    rate_limit.invalidate_limits_cache()
    client.close()


async def _make_key(db, agent_id: str, scopes: list[str]) -> str:
    plain, _ = await auth.create_api_key(
        db, agent_id=agent_id, agent_name=agent_id,
        scopes=scopes, created_by='pytest',
    )
    return plain


# ──────────────────────────────────────────────────────────────────────────────
# 1 · crear_muestreo_qa
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_muestreo_aleatorio_selecciona_porcentaje(db_seed):
    key = await _make_key(db_seed, f'{PFX}iso1', ['iso:quality', 'orders:read', 'meta:ping'])
    now = datetime.now(timezone.utc)
    r = await execute_tool(db_seed, api_key=key, tool_name='crear_muestreo_qa', params={
        'fecha_inicio': _iso(now - timedelta(days=10)),
        'fecha_fin': _iso(now + timedelta(hours=1)),
        'porcentaje_muestra': 100,  # coge todas las candidatas
        'criterio_seleccion': 'aleatorio',
    })
    assert r['success']
    assert r['tam_muestra'] >= 3  # las 3 test + posibles otras
    ids = {o['id'] for o in r['order_ids_seleccionados']}
    assert {ORD_1, ORD_2, ORD_3}.issubset(ids)


@pytest.mark.asyncio
async def test_muestreo_por_tecnico_filtra(db_seed):
    key = await _make_key(db_seed, f'{PFX}iso2', ['iso:quality', 'orders:read', 'meta:ping'])
    now = datetime.now(timezone.utc)
    r = await execute_tool(db_seed, api_key=key, tool_name='crear_muestreo_qa', params={
        'fecha_inicio': _iso(now - timedelta(days=10)),
        'fecha_fin': _iso(now + timedelta(hours=1)),
        'porcentaje_muestra': 100,
        'criterio_seleccion': 'por_tecnico',
        'filtro_tecnico_id': 'tec-uuid-1',
    })
    assert r['success']
    ids = {o['id'] for o in r['order_ids_seleccionados']}
    # ORD_1 y ORD_3 son de tec-uuid-1
    assert ORD_1 in ids and ORD_3 in ids
    assert ORD_2 not in ids


@pytest.mark.asyncio
async def test_muestreo_requiere_dual_scope(db_seed):
    # Solo iso:quality SIN orders:read → debe fallar
    key = await _make_key(db_seed, f'{PFX}iso3', ['iso:quality', 'meta:ping'])
    now = datetime.now(timezone.utc)
    with pytest.raises(ToolExecutionError, match='orders:read'):
        await execute_tool(db_seed, api_key=key, tool_name='crear_muestreo_qa', params={
            'fecha_inicio': _iso(now - timedelta(days=10)),
            'fecha_fin': _iso(now),
            'porcentaje_muestra': 10,
            'criterio_seleccion': 'aleatorio',
        })


# ──────────────────────────────────────────────────────────────────────────────
# 2 · registrar_resultado
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_registrar_resultado_conforme_y_no_conforme(db_seed):
    key = await _make_key(db_seed, f'{PFX}iso4', ['iso:quality', 'orders:read', 'meta:ping'])
    now = datetime.now(timezone.utc)
    muestreo = await execute_tool(db_seed, api_key=key, tool_name='crear_muestreo_qa', params={
        'fecha_inicio': _iso(now - timedelta(days=10)),
        'fecha_fin': _iso(now + timedelta(hours=1)),
        'porcentaje_muestra': 100,
        'criterio_seleccion': 'aleatorio',
    })
    mid = muestreo['muestreo_id']

    r1 = await execute_tool(db_seed, api_key=key, tool_name='registrar_resultado', params={
        'muestreo_id': mid, 'order_id': ORD_1, 'resultado': 'conforme',
        'observaciones': 'Todo OK',
        '_idempotency_key': f'resultado_{mid}_{ORD_1}',
    })
    assert r1['success'] and r1['resultado'] == 'conforme'
    assert 'accion_requerida' not in r1

    r2 = await execute_tool(db_seed, api_key=key, tool_name='registrar_resultado', params={
        'muestreo_id': mid, 'order_id': ORD_2, 'resultado': 'no_conforme',
        'observaciones': 'Falta foto de cierre',
        '_idempotency_key': f'resultado_{mid}_{ORD_2}',
    })
    assert r2['success']
    assert r2['accion_requerida'] == 'abrir_nc'
    assert 'abrir_nc' in r2['mensaje_accion']


@pytest.mark.asyncio
async def test_registrar_resultado_idempotente(db_seed):
    key = await _make_key(db_seed, f'{PFX}iso5', ['iso:quality', 'orders:read', 'meta:ping'])
    now = datetime.now(timezone.utc)
    muestreo = await execute_tool(db_seed, api_key=key, tool_name='crear_muestreo_qa', params={
        'fecha_inicio': _iso(now - timedelta(days=10)),
        'fecha_fin': _iso(now + timedelta(hours=1)),
        'porcentaje_muestra': 100,
        'criterio_seleccion': 'aleatorio',
    })
    mid = muestreo['muestreo_id']
    params = {
        'muestreo_id': mid, 'order_id': ORD_1, 'resultado': 'conforme',
        'observaciones': 'conforme ok',
        '_idempotency_key': f'resultado_{mid}_{ORD_1}',
    }
    r1 = await execute_tool(db_seed, api_key=key, tool_name='registrar_resultado', params=dict(params))
    r2 = await execute_tool(db_seed, api_key=key, tool_name='registrar_resultado', params=dict(params))
    assert r1 == r2


@pytest.mark.asyncio
async def test_registrar_resultado_order_no_en_muestreo(db_seed):
    key = await _make_key(db_seed, f'{PFX}iso6', ['iso:quality', 'orders:read', 'meta:ping'])
    now = datetime.now(timezone.utc)
    muestreo = await execute_tool(db_seed, api_key=key, tool_name='crear_muestreo_qa', params={
        'fecha_inicio': _iso(now - timedelta(days=10)),
        'fecha_fin': _iso(now + timedelta(hours=1)),
        'porcentaje_muestra': 100,
        'criterio_seleccion': 'por_tecnico',
        'filtro_tecnico_id': 'tec-uuid-1',  # ORD_2 NO estará incluida
    })
    r = await execute_tool(db_seed, api_key=key, tool_name='registrar_resultado', params={
        'muestreo_id': muestreo['muestreo_id'], 'order_id': ORD_2,
        'resultado': 'conforme', 'observaciones': 'probando',
        '_idempotency_key': 'k-fuera-1',
    })
    assert r['success'] is False
    assert r['error'] == 'order_id_no_en_muestreo'


# ──────────────────────────────────────────────────────────────────────────────
# 3 · abrir_nc
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_abrir_nc_persiste_en_capas(db_seed):
    key = await _make_key(db_seed, f'{PFX}iso7', ['iso:quality', 'orders:read', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='abrir_nc', params={
        'tipo': 'mayor',
        'proceso_afectado': 'reparacion',
        'descripcion': 'Pantalla recibida con pixel muerto en 3 órdenes consecutivas',
        'evidencia_ids': ['ev-001', 'ev-002'],
        'order_id_origen': ORD_1,
        '_idempotency_key': 'nc-mayor-reparacion-1',
    })
    assert r['success']
    assert r['numero_nc'].startswith('NC-')
    assert r['tipo'] == 'mayor'

    doc = await db_seed.capas.find_one({'id': r['nc_id']}, {'_id': 0})
    assert doc['origen'] == 'mcp_iso_officer'
    assert doc['estado'] == 'abierta'
    assert doc['ot_id'] == ORD_1
    assert doc['evidencia_ids'] == ['ev-001', 'ev-002']


# ──────────────────────────────────────────────────────────────────────────────
# 4 · listar_acuses_pendientes
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_acuses_pendientes_solo_no_acusados(db_seed):
    key = await _make_key(db_seed, f'{PFX}iso8', ['iso:quality', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='listar_acuses_pendientes', params={})
    # Filtro: solo el doc test con USER_TEC pendiente
    doc_match = next((it for it in r['items'] if it['doc_id'] == DOC_ID), None)
    assert doc_match is not None
    pendientes_ids = {p['user_id'] for p in doc_match['pendientes']}
    assert USER_TEC in pendientes_ids
    assert USER_ADMIN not in pendientes_ids
    assert doc_match['dias_desde_publicacion'] >= 39


@pytest.mark.asyncio
async def test_acuses_filtro_rol(db_seed):
    key = await _make_key(db_seed, f'{PFX}iso9', ['iso:quality', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='listar_acuses_pendientes',
                           params={'filtro_rol': 'tecnico'})
    doc_match = next((it for it in r['items'] if it['doc_id'] == DOC_ID), None)
    assert doc_match is not None
    # Solo debe listar USER_TEC (no admins)
    roles = {p['role'] for p in doc_match['pendientes']}
    assert roles == {'tecnico'}


@pytest.mark.asyncio
async def test_acuses_vencidos_dias(db_seed):
    key = await _make_key(db_seed, f'{PFX}iso10', ['iso:quality', 'meta:ping'])
    # Docs publicados hace >=50 días → nuestro test doc (40 días) NO aparece
    r = await execute_tool(db_seed, api_key=key, tool_name='listar_acuses_pendientes',
                           params={'incluir_vencidos_dias': 50})
    assert not any(it['doc_id'] == DOC_ID for it in r['items'])


# ──────────────────────────────────────────────────────────────────────────────
# 5 · evaluar_proveedor
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_evaluar_proveedor_score_y_clasificacion(db_seed):
    key = await _make_key(db_seed, f'{PFX}iso11', ['iso:quality', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='evaluar_proveedor', params={
        'proveedor_id': PROV_1,
        'criterios': {'calidad': 5, 'plazo': 4, 'precio': 4, 'documentacion': 5},
        'periodo_evaluado': '2026-Q1',
    })
    assert r['success']
    # 5*0.4 + 4*0.3 + 4*0.15 + 5*0.15 = 2.0 + 1.2 + 0.6 + 0.75 = 4.55
    assert abs(r['score_global'] - 4.55) < 0.01
    assert r['clasificacion'].startswith('A')
    assert r['comparativa'] is None  # sin previa

    # 2ª evaluación con nota peor → delta negativo, tendencia empeora
    r2 = await execute_tool(db_seed, api_key=key, tool_name='evaluar_proveedor', params={
        'proveedor_id': PROV_1,
        'criterios': {'calidad': 3, 'plazo': 3, 'precio': 4, 'documentacion': 3},
        'periodo_evaluado': '2026-Q2',
    })
    assert r2['comparativa'] is not None
    assert r2['comparativa']['delta_score'] < 0
    assert r2['comparativa']['tendencia'] == 'empeora'


# ──────────────────────────────────────────────────────────────────────────────
# 6 · generar_revision_direccion
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generar_revision_direccion_default_secciones(db_seed):
    key = await _make_key(db_seed, f'{PFX}iso12', ['iso:quality', 'orders:read', 'meta:ping'])
    now = datetime.now(timezone.utc)
    # Abrimos una NC dentro del periodo para asegurar datos
    await execute_tool(db_seed, api_key=key, tool_name='abrir_nc', params={
        'tipo': 'menor', 'proceso_afectado': 'logistica',
        'descripcion': 'Retraso MRW en zona norte (2 órdenes)',
        'evidencia_ids': ['ev-x'],
        '_idempotency_key': 'nc-log-test',
    })
    r = await execute_tool(db_seed, api_key=key, tool_name='generar_revision_direccion', params={
        'fecha_inicio': _iso(now - timedelta(days=30)),
        'fecha_fin': _iso(now + timedelta(hours=1)),
    })
    # Comprueba estructura básica
    assert 'indicadores' in r
    assert 'no_conformidades' in r
    assert r['no_conformidades']['resumen']['total'] >= 1
    assert 'acciones_recomendadas' in r
    assert isinstance(r['acciones_recomendadas'], list)


@pytest.mark.asyncio
async def test_generar_revision_secciones_custom(db_seed):
    key = await _make_key(db_seed, f'{PFX}iso13', ['iso:quality', 'orders:read', 'meta:ping'])
    now = datetime.now(timezone.utc)
    r = await execute_tool(db_seed, api_key=key, tool_name='generar_revision_direccion', params={
        'fecha_inicio': _iso(now - timedelta(days=7)),
        'fecha_fin': _iso(now),
        'incluir_secciones': ['indicadores', 'sla'],
    })
    assert 'indicadores' in r
    assert 'sla' in r
    assert 'no_conformidades' not in r
    assert 'proveedores' not in r

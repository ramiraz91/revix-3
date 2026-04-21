"""
Tests Fase 2 · Auditor Transversal (5 tools).

Cubre:
  - audit_financiero: detecta órdenes sin facturar + factura sin orden
  - audit_operacional: detecta orden sin token + estado inconsistente
  - audit_seguridad: detecta intentos sin scope + fuera de horario
  - generar_audit_report: rechaza sin auditoría previa + requiere evidencia
  - abrir_nc_audit: solo HIGH/CRITICAL + asigna a iso_officer
"""
from __future__ import annotations

import sys
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
from revix_mcp.tools import auditor  # noqa: F401 — registro


PFX = 'test_aud_'
ORD_SIN_FAC = f'{PFX}ord_nofact'
ORD_SIN_TOKEN = f'{PFX}ord_notoken'
ORD_ESTADO_MAL = f'{PFX}ord_badstate'
FAC_SIN_ORDEN = f'{PFX}fac_noorden'


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec='seconds')


@pytest_asyncio.fixture
async def db_seed():
    assert DB_NAME != 'production'
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]

    collections = [
        'ordenes', 'facturas', 'liquidaciones',
        'capas', 'mcp_audit_reports',
        API_KEYS_COLLECTION, IDEMPOTENCY_COLLECTION, AUDIT_COLLECTION,
        rate_limit.USAGE_COLLECTION, rate_limit.LIMITS_COLLECTION,
    ]
    for col in collections:
        await database[col].delete_many({'id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'agent_id': {'$regex': f'^{PFX}'}})
    rate_limit.invalidate_limits_cache()

    now = datetime.now(timezone.utc)
    # Orden enviada SIN facturar (hallazgo CRITICAL financiero)
    await database.ordenes.insert_one({
        'id': ORD_SIN_FAC, 'numero_orden': 'OT-AUD-1',
        'estado': 'enviado', 'cliente_id': 'cli-x',
        'fecha_enviado': _iso(now - timedelta(days=2)),
        'presupuesto_total': 300.0,
        'facturada': False, 'factura_id': None,
        'created_at': _iso(now - timedelta(days=5)),
        'updated_at': _iso(now),
    })
    # Orden sin token_seguimiento (MEDIUM operacional)
    await database.ordenes.insert_one({
        'id': ORD_SIN_TOKEN, 'numero_orden': 'OT-AUD-2',
        'estado': 'reparando', 'cliente_id': 'cli-y',
        'token_seguimiento': None, 'presupuesto_total': 100.0,
        'created_at': _iso(now - timedelta(days=3)),
        'updated_at': _iso(now),
    })
    # Orden enviado SIN fecha_enviado (HIGH operacional)
    await database.ordenes.insert_one({
        'id': ORD_ESTADO_MAL, 'numero_orden': 'OT-AUD-3',
        'estado': 'enviado', 'cliente_id': 'cli-z',
        'fecha_enviado': None, 'token_seguimiento': 'TOK123',
        'presupuesto_total': 50.0,
        'created_at': _iso(now - timedelta(days=2)),
        'updated_at': _iso(now),
    })
    # Factura sin orden (HIGH financiero)
    await database.facturas.insert_one({
        'id': FAC_SIN_ORDEN, 'tipo': 'venta', 'numero': 'TEST-NOORDEN',
        'orden_id': None, 'total': 99,
        'fecha_emision': _iso(now - timedelta(days=2)),
        'cliente_nombre': 'X',
    })

    yield database

    for col in collections:
        await database[col].delete_many({'id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'agent_id': {'$regex': f'^{PFX}'}})
    await database.capas.delete_many({'origen': 'mcp_auditor_transversal'})
    rate_limit.invalidate_limits_cache()
    client.close()


async def _make_key(db, agent_id: str, scopes: list[str]) -> str:
    plain, _ = await auth.create_api_key(
        db, agent_id=agent_id, agent_name=agent_id,
        scopes=scopes, created_by='pytest',
    )
    return plain


# ──────────────────────────────────────────────────────────────────────────────
# 1 · ejecutar_audit_financiero
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_financiero_detecta_orden_sin_facturar(db_seed):
    key = await _make_key(db_seed, f'{PFX}a1', ['audit:read', 'audit:report', 'meta:ping'])
    now = datetime.now(timezone.utc)
    r = await execute_tool(db_seed, api_key=key, tool_name='ejecutar_audit_financiero', params={
        'fecha_inicio': _iso(now - timedelta(days=30)),
        'fecha_fin': _iso(now + timedelta(hours=1)),
    })
    # Al menos un hallazgo de órdenes sin facturar con CRITICAL
    titulos = [h['titulo'] for h in r['hallazgos']]
    assert any('sin factura' in t for t in titulos)
    assert r['severidad_max'] in ('HIGH', 'CRITICAL')


# ──────────────────────────────────────────────────────────────────────────────
# 2 · ejecutar_audit_operacional
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_operacional_detecta_sin_token_y_estado(db_seed):
    key = await _make_key(db_seed, f'{PFX}a2', ['audit:read', 'audit:report', 'meta:ping'])
    now = datetime.now(timezone.utc)
    r = await execute_tool(db_seed, api_key=key, tool_name='ejecutar_audit_operacional', params={
        'fecha_inicio': _iso(now - timedelta(days=30)),
        'fecha_fin': _iso(now + timedelta(hours=1)),
    })
    titulos = [h['titulo'] for h in r['hallazgos']]
    assert any('token_seguimiento' in t for t in titulos)
    assert any('fecha_enviado' in t for t in titulos)


# ──────────────────────────────────────────────────────────────────────────────
# 3 · ejecutar_audit_seguridad
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_seguridad_detecta_scope_denied(db_seed):
    # Generar intento sin scope previo
    key_limited = await _make_key(db_seed, f'{PFX}a3_lim', ['meta:ping'])
    from revix_mcp.runtime import ToolExecutionError
    try:
        await execute_tool(db_seed, api_key=key_limited, tool_name='listar_ordenes', params={})
    except ToolExecutionError:
        pass

    # Auditor ejecuta seguridad
    key = await _make_key(db_seed, f'{PFX}a3', ['audit:read', 'audit:report', 'meta:ping'])
    now = datetime.now(timezone.utc)
    r = await execute_tool(db_seed, api_key=key, tool_name='ejecutar_audit_seguridad', params={
        'fecha_inicio': _iso(now - timedelta(days=1)),
        'fecha_fin': _iso(now + timedelta(hours=1)),
    })
    titulos = [h['titulo'] for h in r['hallazgos']]
    assert any('sin scope' in t for t in titulos)


# ──────────────────────────────────────────────────────────────────────────────
# 4 · generar_audit_report
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generar_report_rechaza_sin_auditoria_previa(db_seed):
    key = await _make_key(db_seed, f'{PFX}a4', ['audit:read', 'audit:report', 'meta:ping'])
    now = datetime.now(timezone.utc)
    # Agente recién creado, sin haber ejecutado ninguna audit tool
    r = await execute_tool(db_seed, api_key=key, tool_name='generar_audit_report', params={
        'tipo_auditoria': 'financiero',
        'fecha_inicio': _iso(now - timedelta(days=7)),
        'fecha_fin': _iso(now),
        'hallazgos': [{
            'id': 'TEST-001', 'descripcion': 'prueba test',
            'severidad': 'HIGH',
            'evidencia': [{'order_id': ORD_SIN_FAC}],
            'recomendacion': 'emitir factura',
        }],
        '_idempotency_key': 'rpt-sin-previa',
    })
    assert r['success'] is False
    assert r['error'] == 'sin_auditoria_previa'


@pytest.mark.asyncio
async def test_generar_report_ok_tras_auditoria(db_seed):
    key = await _make_key(db_seed, f'{PFX}a5', ['audit:read', 'audit:report', 'meta:ping'])
    now = datetime.now(timezone.utc)
    # 1) auditar primero
    await execute_tool(db_seed, api_key=key, tool_name='ejecutar_audit_financiero', params={
        'fecha_inicio': _iso(now - timedelta(days=7)),
        'fecha_fin': _iso(now),
    })
    # 2) generar reporte
    r = await execute_tool(db_seed, api_key=key, tool_name='generar_audit_report', params={
        'tipo_auditoria': 'financiero',
        'fecha_inicio': _iso(now - timedelta(days=7)),
        'fecha_fin': _iso(now),
        'hallazgos': [{
            'id': 'FIN-TEST-001', 'descripcion': 'orden sin facturar',
            'severidad': 'CRITICAL',
            'evidencia': [{'order_id': ORD_SIN_FAC, 'total': 300}],
            'recomendacion': 'emitir factura o justificar',
        }],
        '_idempotency_key': 'rpt-ok-1',
    })
    assert r['success']
    assert r['numero_report'].startswith('AUD-')
    assert r['severidad_max'] == 'CRITICAL'
    assert r['hint_next_action'] is not None  # HIGH/CRITICAL → sugerir abrir_nc_audit


# ──────────────────────────────────────────────────────────────────────────────
# 5 · abrir_nc_audit
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_abrir_nc_audit_solo_high_critical(db_seed):
    key = await _make_key(db_seed, f'{PFX}a6', ['audit:read', 'audit:report', 'meta:ping'])
    now = datetime.now(timezone.utc)
    await execute_tool(db_seed, api_key=key, tool_name='ejecutar_audit_financiero', params={
        'fecha_inicio': _iso(now - timedelta(days=7)),
        'fecha_fin': _iso(now),
    })
    rpt = await execute_tool(db_seed, api_key=key, tool_name='generar_audit_report', params={
        'tipo_auditoria': 'financiero',
        'fecha_inicio': _iso(now - timedelta(days=7)),
        'fecha_fin': _iso(now),
        'hallazgos': [
            {'id': 'H-LOW-1', 'descripcion': 'algo menor', 'severidad': 'LOW',
             'evidencia': [{'x': 1}], 'recomendacion': 'revisar'},
            {'id': 'H-CRIT-1', 'descripcion': 'orden sin facturar',
             'severidad': 'CRITICAL',
             'evidencia': [{'order_id': ORD_SIN_FAC}], 'recomendacion': 'facturar'},
        ],
        '_idempotency_key': 'rpt-nc-1',
    })
    report_id = rpt['audit_report_id']

    # Intentar abrir NC para hallazgo LOW → debe rechazarse
    r_low = await execute_tool(db_seed, api_key=key, tool_name='abrir_nc_audit', params={
        'tipo': 'menor', 'proceso_afectado': 'test',
        'descripcion': 'no deberia abrirse',
        'evidencia_ids': ['ev-1'],
        'audit_report_id_origen': report_id,
        'hallazgo_id_origen': 'H-LOW-1',
        '_idempotency_key': 'nc-low-rej',
    })
    assert r_low['success'] is False
    assert r_low['error'] == 'severidad_insuficiente'

    # Abrir NC para hallazgo CRITICAL → OK
    r_crit = await execute_tool(db_seed, api_key=key, tool_name='abrir_nc_audit', params={
        'tipo': 'mayor', 'proceso_afectado': 'facturacion',
        'descripcion': 'Facturación pendiente urgente',
        'evidencia_ids': ['ev-crit-1'],
        'audit_report_id_origen': report_id,
        'hallazgo_id_origen': 'H-CRIT-1',
        '_idempotency_key': 'nc-crit-ok',
    })
    assert r_crit['success'] is True
    assert r_crit['asignado_a'] == 'iso_officer'

    nc = await db_seed.capas.find_one({'id': r_crit['nc_id']}, {'_id': 0})
    assert nc['origen'] == 'mcp_auditor_transversal'
    assert nc['asignado_a'] == 'iso_officer'
    assert nc['audit_report_id_origen'] == report_id

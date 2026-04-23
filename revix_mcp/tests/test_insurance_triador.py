"""
Tests Fase 3 · Gestor de Siniestros (5 tools) + Triador de Averías (3 tools).

Cubre:
  - listar_peticiones_pendientes (prioridad SLA)
  - crear_orden_desde_peticion (validaciones: sin contrato, tipo fuera alcance, importe)
  - actualizar_portal_insurama (mock en preview + traza)
  - subir_evidencias
  - cerrar_siniestro (validaciones: sin evidencia, portal no actualizado)
  - proponer_diagnostico (match reglas + no match)
  - sugerir_repuestos (stock OK / sin stock / priorización)
  - recomendar_tecnico (carga + especialidad + prioridad)
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
from revix_mcp.tools import insurance, triador_averias  # noqa: F401 — registro


PFX = 'test_f3_'
PET_OK = f'{PFX}peticion_ok'
PET_SIN_CONTRATO = f'{PFX}peticion_sincontrato'
PET_FUERA_ALCANCE = f'{PFX}peticion_fueraalcance'
PET_IMPORTE_EXCEDE = f'{PFX}peticion_excede'
PET_CRITICA = f'{PFX}peticion_critica'
ASEGURADORA_OK = f'{PFX}ase_ok'
ASEGURADORA_RESTRICTIVA = f'{PFX}ase_restrictiva'
ORD_SINI = f'{PFX}ord_siniestro'
TEC_A = f'{PFX}tec_a'
TEC_B = f'{PFX}tec_b'


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec='seconds')


@pytest_asyncio.fixture
async def db_seed():
    assert DB_NAME != 'production'
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]

    collections = [
        'ordenes', 'clientes', 'users', 'inventario',
        'siniestros_peticiones', 'aseguradoras_contratos',
        'siniestros_evidencias', 'mcp_insurama_updates',
        'notificaciones',
        API_KEYS_COLLECTION, IDEMPOTENCY_COLLECTION, AUDIT_COLLECTION,
        rate_limit.USAGE_COLLECTION, rate_limit.LIMITS_COLLECTION,
    ]
    for col in collections:
        await database[col].delete_many({'id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'agent_id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'peticion_id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'siniestro_id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'siniestro_id_externo': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'order_id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'order_id_revix': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'aseguradora_id': {'$regex': f'^{PFX}'}})
    rate_limit.invalidate_limits_cache()

    now = datetime.now(timezone.utc)

    # Aseguradoras
    await database.aseguradoras_contratos.insert_many([
        {
            'id': ASEGURADORA_OK, 'aseguradora_id': ASEGURADORA_OK,
            'nombre': 'Insurama Test', 'activo': True,
            'sla_horas_respuesta': 48, 'sla_dias_reparacion': 7,
            'alcance_tipos_reparacion': ['pantalla', 'bateria', 'agua'],
            'limite_importe_autorizado': 500.0,
        },
        {
            'id': ASEGURADORA_RESTRICTIVA, 'aseguradora_id': ASEGURADORA_RESTRICTIVA,
            'nombre': 'Restrictiva', 'activo': True,
            'sla_horas_respuesta': 24, 'sla_dias_reparacion': 5,
            'alcance_tipos_reparacion': ['pantalla'],
            'limite_importe_autorizado': 150.0,
        },
    ])

    # Peticiones
    await database.siniestros_peticiones.insert_many([
        {
            'id': PET_OK, 'siniestro_id_externo': 'SX-OK-001',
            'aseguradora_id': ASEGURADORA_OK, 'aseguradora_nombre': 'Insurama Test',
            'cliente_nombre': 'Cliente OK', 'cliente_email': 'cli@test.com',
            'cliente_telefono': '600111', 'numero_autorizacion': 'AUTH-OK-1',
            'dispositivo': {'marca': 'Apple', 'modelo': 'iPhone 12'},
            'importe_estimado': 200.0, 'estado': 'recibida',
            'tipo_reparacion': 'pantalla',
            'fecha_recepcion': _iso(now - timedelta(hours=2)),
        },
        {
            'id': PET_CRITICA, 'siniestro_id_externo': 'SX-CRIT-001',
            'aseguradora_id': ASEGURADORA_OK, 'aseguradora_nombre': 'Insurama Test',
            'cliente_nombre': 'Cliente Crítico',
            'dispositivo': {'marca': 'Samsung', 'modelo': 'S22'},
            'importe_estimado': 180.0, 'estado': 'recibida',
            'tipo_reparacion': 'pantalla',
            'fecha_recepcion': _iso(now - timedelta(hours=72)),  # SLA vencido
        },
        {
            'id': PET_SIN_CONTRATO, 'siniestro_id_externo': 'SX-NOCNT-001',
            'aseguradora_id': f'{PFX}inexistente', 'aseguradora_nombre': 'Fantasma',
            'cliente_nombre': 'Cliente Sin Contrato',
            'dispositivo': {'marca': 'Apple', 'modelo': 'iPhone 11'},
            'importe_estimado': 150.0, 'estado': 'recibida',
            'tipo_reparacion': 'pantalla',
            'fecha_recepcion': _iso(now - timedelta(hours=1)),
        },
        {
            'id': PET_FUERA_ALCANCE, 'siniestro_id_externo': 'SX-OUT-001',
            'aseguradora_id': ASEGURADORA_RESTRICTIVA, 'aseguradora_nombre': 'Restrictiva',
            'cliente_nombre': 'Fuera de Alcance',
            'dispositivo': {'marca': 'Apple', 'modelo': 'iPhone 12'},
            'importe_estimado': 100.0, 'estado': 'recibida',
            'tipo_reparacion': 'bateria',  # restrictiva solo permite pantalla
            'fecha_recepcion': _iso(now - timedelta(hours=1)),
        },
        {
            'id': PET_IMPORTE_EXCEDE, 'siniestro_id_externo': 'SX-CAP-001',
            'aseguradora_id': ASEGURADORA_RESTRICTIVA, 'aseguradora_nombre': 'Restrictiva',
            'cliente_nombre': 'Excede Límite',
            'dispositivo': {'marca': 'Apple', 'modelo': 'iPhone 14 Pro'},
            'importe_estimado': 400.0,  # > 150 límite
            'estado': 'recibida', 'tipo_reparacion': 'pantalla',
            'fecha_recepcion': _iso(now - timedelta(hours=1)),
        },
    ])

    # Inventario
    await database.inventario.insert_many([
        {
            'id': f'{PFX}inv_pant_stock', 'sku_corto': 'PANT-iP12',
            'nombre': 'Pantalla iPhone 12 OEM',
            'descripcion': 'Pantalla LCD iPhone 12',
            'categoria': 'pantalla', 'modelo_compatible': 'iPhone 12',
            'stock': 5, 'stock_minimo': 2,
            'precio_venta': 120.0, 'precio_compra': 60.0,
            'proveedor': 'Mobile Sentrix',
        },
        {
            'id': f'{PFX}inv_pant_sinstock', 'sku_corto': 'PANT-iP14',
            'nombre': 'Pantalla iPhone 14 OEM',
            'descripcion': 'Pantalla iPhone 14', 'categoria': 'pantalla',
            'modelo_compatible': 'iPhone 14',
            'stock': 0, 'stock_minimo': 2,
            'precio_venta': 250.0, 'precio_compra': 140.0,
            'proveedor': 'Utopya',
        },
        {
            'id': f'{PFX}inv_bat', 'sku_corto': 'BAT-iP12',
            'nombre': 'Batería iPhone 12', 'descripcion': 'Batería iPhone 12',
            'categoria': 'bateria', 'modelo_compatible': 'iPhone 12',
            'stock': 8, 'stock_minimo': 2,
            'precio_venta': 40.0, 'precio_compra': 15.0,
            'proveedor': 'Mobile Sentrix',
        },
    ])

    # Técnicos
    await database.users.insert_many([
        {
            'id': TEC_A, 'email': f'{PFX}tecA@revix.es', 'nombre': 'Técnico A',
            'rol': 'tecnico', 'activo': True,
            'especialidades': ['pantalla', 'bateria'],
        },
        {
            'id': TEC_B, 'email': f'{PFX}tecB@revix.es', 'nombre': 'Técnico B',
            'rol': 'tecnico', 'activo': True,
            'especialidades': ['agua', 'placa'],
        },
    ])
    # Carga actual: A con 1 orden, B con 0
    await database.ordenes.insert_one({
        'id': f'{PFX}ord_carga_a', 'numero_orden': 'OT-CA',
        'cliente_id': 'x', 'estado': 'en_taller',
        'tecnico_asignado': TEC_A,
        'averia_descripcion': 'pantalla rota por caída',
        'dispositivo': {'marca': 'Apple', 'modelo': 'iPhone 12'},
        'created_at': _iso(now - timedelta(days=1)),
        'updated_at': _iso(now),
    })

    yield database

    # Cleanup
    for col in collections:
        await database[col].delete_many({'id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'agent_id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'peticion_id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'siniestro_id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'siniestro_id_externo': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'order_id': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'order_id_revix': {'$regex': f'^{PFX}'}})
        await database[col].delete_many({'aseguradora_id': {'$regex': f'^{PFX}'}})
    # Órdenes creadas por la tool
    await database.ordenes.delete_many({'created_by': {'$regex': f'mcp:{PFX}'}})
    await database.ordenes.delete_many({'peticion_origen_id': {'$regex': f'^{PFX}'}})
    await database.clientes.delete_many({'source': 'mcp_gestor_siniestros',
                                         'created_at': {'$regex': '2026|2025'}})
    rate_limit.invalidate_limits_cache()
    client.close()


async def _make_key(db, agent_id: str, scopes: list[str]) -> str:
    plain, _ = await auth.create_api_key(
        db, agent_id=agent_id, agent_name=agent_id,
        scopes=scopes, created_by='pytest',
    )
    return plain


# ══════════════════════════════════════════════════════════════════════════════
# Gestor de Siniestros · 5 tools
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_listar_peticiones_prioridad_sla(db_seed):
    key = await _make_key(db_seed, f'{PFX}gs1',
                          ['orders:read', 'insurance:ops', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key,
                           tool_name='listar_peticiones_pendientes',
                           params={'estado': 'recibida'})
    ids = [p['id'] for p in r['items']]
    # La crítica (72h, SLA 48h) debe aparecer primero
    idx_crit = ids.index(PET_CRITICA)
    idx_ok = ids.index(PET_OK)
    assert idx_crit < idx_ok
    # Prioridad calculada
    crit = next(p for p in r['items'] if p['id'] == PET_CRITICA)
    assert crit['prioridad'] == 'critico'
    assert crit['horas_restantes_sla'] < 0


@pytest.mark.asyncio
async def test_crear_orden_ok(db_seed):
    key = await _make_key(db_seed, f'{PFX}gs2',
                          ['orders:read', 'orders:write', 'insurance:ops', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key,
                           tool_name='crear_orden_desde_peticion',
                           params={
                               'peticion_id': PET_OK,
                               'tecnico_id': TEC_A,
                               'fecha_estimada_entrega': (
                                   datetime.now(timezone.utc) + timedelta(days=5)
                               ).isoformat(),
                               '_idempotency_key': f'orden_siniestro_{PET_OK}',
                           })
    assert r['success'] is True
    assert r['order_id']
    assert r['numero_orden'].startswith('OT-')
    # Orden persistida
    orden = await db_seed.ordenes.find_one({'id': r['order_id']}, {'_id': 0})
    assert orden is not None
    assert orden['es_siniestro'] is True
    assert orden['aseguradora_id'] == ASEGURADORA_OK
    assert orden['tecnico_asignado'] == TEC_A
    # Petición actualizada
    pet = await db_seed.siniestros_peticiones.find_one({'id': PET_OK}, {'_id': 0})
    assert pet['estado'] == 'orden_creada'


@pytest.mark.asyncio
async def test_crear_orden_sin_contrato(db_seed):
    key = await _make_key(db_seed, f'{PFX}gs3',
                          ['orders:write', 'insurance:ops', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key,
                           tool_name='crear_orden_desde_peticion',
                           params={
                               'peticion_id': PET_SIN_CONTRATO, 'tecnico_id': TEC_A,
                               'fecha_estimada_entrega': (
                                   datetime.now(timezone.utc) + timedelta(days=5)
                               ).isoformat(),
                               '_idempotency_key': f'orden_siniestro_{PET_SIN_CONTRATO}',
                           })
    assert r['success'] is False
    assert r['error'] == 'aseguradora_sin_contrato_activo'
    # Marcada pendiente_validacion
    pet = await db_seed.siniestros_peticiones.find_one({'id': PET_SIN_CONTRATO})
    assert pet['estado'] == 'pendiente_validacion'


@pytest.mark.asyncio
async def test_crear_orden_fuera_alcance(db_seed):
    key = await _make_key(db_seed, f'{PFX}gs4',
                          ['orders:write', 'insurance:ops', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key,
                           tool_name='crear_orden_desde_peticion',
                           params={
                               'peticion_id': PET_FUERA_ALCANCE, 'tecnico_id': TEC_A,
                               'fecha_estimada_entrega': (
                                   datetime.now(timezone.utc) + timedelta(days=5)
                               ).isoformat(),
                               '_idempotency_key': f'orden_siniestro_{PET_FUERA_ALCANCE}',
                           })
    assert r['success'] is False
    assert r['error'] == 'tipo_reparacion_fuera_alcance'
    assert 'pantalla' in r['tipos_permitidos']


@pytest.mark.asyncio
async def test_crear_orden_importe_excede(db_seed):
    key = await _make_key(db_seed, f'{PFX}gs5',
                          ['orders:write', 'insurance:ops', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key,
                           tool_name='crear_orden_desde_peticion',
                           params={
                               'peticion_id': PET_IMPORTE_EXCEDE, 'tecnico_id': TEC_A,
                               'fecha_estimada_entrega': (
                                   datetime.now(timezone.utc) + timedelta(days=5)
                               ).isoformat(),
                               '_idempotency_key': f'orden_siniestro_{PET_IMPORTE_EXCEDE}',
                           })
    assert r['success'] is False
    assert r['error'] == 'importe_excede_limite_autorizado'
    assert r['limite_autorizado'] == 150.0


@pytest.mark.asyncio
async def test_actualizar_portal_insurama_preview(db_seed):
    key = await _make_key(db_seed, f'{PFX}gs6',
                          ['insurance:ops', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key,
                           tool_name='actualizar_portal_insurama',
                           params={
                               'siniestro_id_externo': 'SX-OK-001',
                               'estado_nuevo': 'reparado',
                               'order_id_revix': 'orden_ficticia',
                           })
    assert r['success'] is True
    assert r['preview'] is True
    assert 'PREVIEW' in r['message']
    # Traza
    trace = await db_seed.mcp_insurama_updates.find_one(
        {'siniestro_id_externo': 'SX-OK-001'}, {'_id': 0},
    )
    assert trace is not None
    assert trace['estado_nuevo'] == 'reparado'


@pytest.mark.asyncio
async def test_actualizar_portal_estado_invalido(db_seed):
    key = await _make_key(db_seed, f'{PFX}gs7', ['insurance:ops', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key,
                           tool_name='actualizar_portal_insurama',
                           params={
                               'siniestro_id_externo': 'SX-x',
                               'estado_nuevo': 'en_el_limbo',
                               'order_id_revix': 'x',
                           })
    assert r['success'] is False
    assert r['error'] == 'estado_invalido'


@pytest.mark.asyncio
async def test_subir_evidencias(db_seed):
    key = await _make_key(db_seed, f'{PFX}gs8', ['insurance:ops', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key,
                           tool_name='subir_evidencias',
                           params={
                               'siniestro_id': 'SX-OK-001',
                               'tipo_evidencia': 'entrega',
                               'archivo_ids': ['file_a', 'file_b'],
                           })
    assert r['success'] is True
    assert r['archivos_count'] == 2


@pytest.mark.asyncio
async def test_cerrar_siniestro_sin_evidencias(db_seed):
    """Resultado=reparado SIN evidencia de entrega → error `falta_evidencia_entrega`."""
    key = await _make_key(db_seed, f'{PFX}gs9',
                          ['orders:write', 'insurance:ops', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key,
                           tool_name='cerrar_siniestro',
                           params={
                               'siniestro_id': 'SX-NOEVI-001',
                               'order_id': 'order_noevi', 'resultado': 'reparado',
                           })
    assert r['success'] is False
    # Con resultado=reparado se exige evidencia de entrega específicamente
    assert r['error'] in ('falta_evidencia_entrega', 'sin_evidencias')


@pytest.mark.asyncio
async def test_cerrar_siniestro_portal_no_actualizado(db_seed):
    """Con evidencia pero sin update de portal, debe fallar."""
    # Primero subo evidencia de entrega
    key = await _make_key(db_seed, f'{PFX}gs10',
                          ['orders:write', 'insurance:ops', 'meta:ping'])
    await execute_tool(db_seed, api_key=key, tool_name='subir_evidencias', params={
        'siniestro_id': 'SX-CLOSE-1', 'tipo_evidencia': 'entrega',
        'archivo_ids': ['evid_1'],
    })
    # No hay mcp_insurama_updates para 'order_close_1'
    r = await execute_tool(db_seed, api_key=key, tool_name='cerrar_siniestro', params={
        'siniestro_id': 'SX-CLOSE-1', 'order_id': 'order_close_1',
        'resultado': 'reparado',
    })
    assert r['success'] is False
    assert r['error'] == 'portal_no_actualizado'


# ══════════════════════════════════════════════════════════════════════════════
# Triador de Averías · 3 tools
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_proponer_diagnostico_pantalla(db_seed):
    key = await _make_key(db_seed, f'{PFX}tr1',
                          ['orders:read', 'orders:suggest', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='proponer_diagnostico',
                           params={'sintomas': 'Se me cayó y tiene la pantalla rota',
                                   'dispositivo_marca': 'Apple',
                                   'dispositivo_modelo': 'iPhone 12'})
    assert r['success'] is True
    assert r['diagnostico_match'] is True
    assert r['tipo_reparacion_sugerido'] == 'pantalla'
    assert 'pantalla' in r['repuestos_ref']
    # Primera causa con confianza alta
    assert r['causas_probables'][0]['confianza'] >= 0.5


@pytest.mark.asyncio
async def test_proponer_diagnostico_no_match(db_seed):
    key = await _make_key(db_seed, f'{PFX}tr2',
                          ['orders:read', 'orders:suggest', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='proponer_diagnostico',
                           params={'sintomas': 'algo raro e impreciso sin pista'})
    assert r['success'] is True
    assert r['diagnostico_match'] is False
    assert r['causas_probables'] == []


@pytest.mark.asyncio
async def test_proponer_diagnostico_requiere_sintomas(db_seed):
    key = await _make_key(db_seed, f'{PFX}tr3',
                          ['orders:read', 'orders:suggest', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='proponer_diagnostico',
                           params={})
    assert r['success'] is False
    assert r['error'] == 'sintomas_requeridos'


@pytest.mark.asyncio
async def test_sugerir_repuestos_con_stock(db_seed):
    key = await _make_key(db_seed, f'{PFX}tr4',
                          ['inventory:read', 'orders:suggest', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='sugerir_repuestos',
                           params={'repuestos_ref': ['pantalla'],
                                   'dispositivo_modelo': 'iPhone 12',
                                   'cantidad_por_repuesto': 1})
    assert r['success'] is True
    sug = r['sugerencias'][0]
    assert sug['hay_stock_directo'] is True
    assert sug['mejor_opcion']['sku_corto'] == 'PANT-iP12'


@pytest.mark.asyncio
async def test_sugerir_repuestos_sin_stock(db_seed):
    key = await _make_key(db_seed, f'{PFX}tr5',
                          ['inventory:read', 'orders:suggest', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='sugerir_repuestos',
                           params={'repuestos_ref': ['pantalla'],
                                   'dispositivo_modelo': 'iPhone 14',
                                   'cantidad_por_repuesto': 1})
    assert r['success'] is True
    sug = r['sugerencias'][0]
    assert sug['hay_stock_directo'] is False
    assert 'Sin stock' in r['veredicto']


@pytest.mark.asyncio
async def test_sugerir_repuestos_multiple(db_seed):
    key = await _make_key(db_seed, f'{PFX}tr6',
                          ['inventory:read', 'orders:suggest', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='sugerir_repuestos',
                           params={'repuestos_ref': ['pantalla', 'bateria'],
                                   'dispositivo_modelo': 'iPhone 12'})
    assert r['total_repuestos_consultados'] == 2
    assert r['con_stock_inmediato'] == 2
    assert 'OK' in r['veredicto']


@pytest.mark.asyncio
async def test_recomendar_tecnico_especialista(db_seed):
    key = await _make_key(db_seed, f'{PFX}tr7',
                          ['orders:read', 'orders:suggest', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='recomendar_tecnico',
                           params={'tipo_reparacion': 'pantalla',
                                   'prioridad': 'normal'})
    assert r['success'] is True
    # TEC_A tiene carga=1 pero es especialista en pantalla
    assert r['recomendado']['id'] == TEC_A
    assert r['recomendado']['especialista_en_tipo'] is True


@pytest.mark.asyncio
async def test_recomendar_tecnico_urgente_gana_descargado(db_seed):
    """Para urgentes, el técnico con carga=0 gana por prio_bonus."""
    key = await _make_key(db_seed, f'{PFX}tr8',
                          ['orders:read', 'orders:suggest', 'meta:ping'])
    r = await execute_tool(db_seed, api_key=key, tool_name='recomendar_tecnico',
                           params={'tipo_reparacion': 'agua', 'prioridad': 'urgente'})
    # TEC_B tiene carga=0 y especialidad agua → debería ganar ampliamente
    assert r['recomendado']['id'] == TEC_B


@pytest.mark.asyncio
async def test_tool_registrada_en_registry(db_seed):
    """Verifica que las 8 tools nuevas están en el registry."""
    from revix_mcp.tools._registry import list_tools
    names = {t.name for t in list_tools()}
    # Gestor siniestros
    assert {'listar_peticiones_pendientes', 'crear_orden_desde_peticion',
            'actualizar_portal_insurama', 'subir_evidencias',
            'cerrar_siniestro'}.issubset(names)
    # Triador
    assert {'proponer_diagnostico', 'sugerir_repuestos',
            'recomendar_tecnico'}.issubset(names)

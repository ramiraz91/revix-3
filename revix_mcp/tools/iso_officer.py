"""
Revix MCP · Tools Fase 2 — Agente ISO 9001 Quality Officer.

6 tools:
  1. crear_muestreo_qa           (write · orders:read + iso:quality)
  2. registrar_resultado         (write · idempotente)
  3. abrir_nc                    (write · idempotente)
  4. listar_acuses_pendientes    (read · iso:quality)
  5. evaluar_proveedor           (write)
  6. generar_revision_direccion  (read aggregado)

Colecciones:
  - mcp_qa_muestreos            (lotes de muestreo, creación nueva)
  - qa_muestreos                (resultados por orden, se reutiliza la existente)
  - capas                       (NCs, reutilizada)
  - iso_documentos              (acuses, reutilizada)
  - iso_proveedores_evaluacion  (reutilizada)
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..auth import AgentIdentity, AuthError
from ._registry import ToolSpec, register
from ._common import validate_input


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _parse_iso(s: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def _require_dual_scope(identity: AgentIdentity, extra: str) -> None:
    """Lanza AuthError si el agente no tiene además el scope extra."""
    if not identity.has_scope(extra):
        raise AuthError(
            f'Scope requerido "{extra}" no presente en agente "{identity.agent_id}"'
        )


# ──────────────────────────────────────────────────────────────────────────────
# 1. crear_muestreo_qa
# ──────────────────────────────────────────────────────────────────────────────

class CrearMuestreoInput(BaseModel):
    fecha_inicio: str = Field(..., description='ISO date o datetime (inclusivo)')
    fecha_fin: str = Field(..., description='ISO date o datetime (inclusivo)')
    porcentaje_muestra: float = Field(..., gt=0, le=100)
    criterio_seleccion: Literal[
        'aleatorio', 'por_tecnico', 'por_tipo_reparacion', 'por_reclamacion',
    ] = 'aleatorio'
    filtro_tecnico_id: Optional[str] = None
    filtro_tipo_reparacion: Optional[str] = None

    @field_validator('fecha_inicio', 'fecha_fin')
    @classmethod
    def _valid_iso(cls, v):
        if _parse_iso(v) is None:
            raise ValueError('fecha inválida (ISO)')
        return v


async def _crear_muestreo_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require_dual_scope(identity, 'orders:read')
    p = validate_input(CrearMuestreoInput, params)
    ini = _parse_iso(p.fecha_inicio)
    fin = _parse_iso(p.fecha_fin)
    if fin < ini:
        return {'success': False, 'error': 'fecha_fin_menor_que_inicio'}

    # Pool: órdenes completadas/enviadas en el periodo
    query: dict = {
        'estado': {'$in': ['reparado', 'validacion', 'enviado']},
        'updated_at': {'$gte': ini.isoformat(), '$lte': fin.isoformat()},
    }
    if p.criterio_seleccion == 'por_tecnico' and p.filtro_tecnico_id:
        query['tecnico_asignado'] = p.filtro_tecnico_id
    if p.criterio_seleccion == 'por_tipo_reparacion' and p.filtro_tipo_reparacion:
        query['tipo_servicio'] = p.filtro_tipo_reparacion
    if p.criterio_seleccion == 'por_reclamacion':
        # Órdenes con incidencia abierta o reclamación en el periodo
        ords_reclamacion = await db.incidencias.distinct(
            'orden_id', {'created_at': {'$gte': ini.isoformat(), '$lte': fin.isoformat()}},
        )
        if not ords_reclamacion:
            return {
                'success': False, 'error': 'sin_ordenes_candidatas',
                'message': 'No hay reclamaciones en el periodo',
            }
        query['id'] = {'$in': ords_reclamacion}

    pool = await db.ordenes.find(
        query,
        {'_id': 0, 'id': 1, 'numero_orden': 1, 'tecnico_asignado': 1,
         'tipo_servicio': 1, 'updated_at': 1},
    ).to_list(20000)

    if not pool:
        return {'success': False, 'error': 'sin_ordenes_candidatas',
                'query': {k: str(v) for k, v in query.items()}}

    tam = max(1, round(len(pool) * p.porcentaje_muestra / 100))
    tam = min(tam, len(pool))
    seleccionadas = random.sample(pool, tam)

    muestreo_id = str(uuid.uuid4())
    now = _now_iso()
    await db.mcp_qa_muestreos.insert_one({
        'id': muestreo_id,
        'periodo_inicio': ini.isoformat(),
        'periodo_fin': fin.isoformat(),
        'porcentaje_muestra': p.porcentaje_muestra,
        'criterio_seleccion': p.criterio_seleccion,
        'filtro_tecnico_id': p.filtro_tecnico_id,
        'filtro_tipo_reparacion': p.filtro_tipo_reparacion,
        'total_candidatas': len(pool),
        'tam_muestra': tam,
        'order_ids_seleccionados': [o['id'] for o in seleccionadas],
        'estado': 'en_curso',
        'resultados_por_orden': {},  # se rellena con registrar_resultado
        'created_at': now,
        'created_by': f'mcp:{identity.agent_id}',
        'source': 'mcp_agent',
    })

    return {
        'success': True,
        'muestreo_id': muestreo_id,
        'total_candidatas': len(pool),
        'tam_muestra': tam,
        'criterio_seleccion': p.criterio_seleccion,
        'order_ids_seleccionados': [
            {'id': o['id'], 'numero_orden': o.get('numero_orden'),
             'tecnico_asignado': o.get('tecnico_asignado')}
            for o in seleccionadas
        ],
    }


register(ToolSpec(
    name='crear_muestreo_qa',
    description=(
        'Crea un lote de muestreo QA sobre órdenes completadas en un periodo. '
        'Criterios: aleatorio (default), por_tecnico (requiere filtro_tecnico_id), '
        'por_tipo_reparacion (requiere filtro_tipo_reparacion), por_reclamacion '
        '(solo órdenes con incidencia en el periodo). Devuelve muestreo_id y la '
        'lista de order_ids seleccionados. Requiere scopes iso:quality + orders:read.'
    ),
    required_scope='iso:quality',
    input_schema={
        'type': 'object',
        'properties': {
            'fecha_inicio': {'type': 'string', 'description': 'ISO date/datetime'},
            'fecha_fin': {'type': 'string', 'description': 'ISO date/datetime'},
            'porcentaje_muestra': {'type': 'number', 'minimum': 0.1, 'maximum': 100},
            'criterio_seleccion': {
                'type': 'string',
                'enum': ['aleatorio', 'por_tecnico', 'por_tipo_reparacion', 'por_reclamacion'],
                'default': 'aleatorio',
            },
            'filtro_tecnico_id': {'type': 'string'},
            'filtro_tipo_reparacion': {'type': 'string'},
        },
        'required': ['fecha_inicio', 'fecha_fin', 'porcentaje_muestra', 'criterio_seleccion'],
        'additionalProperties': False,
    },
    handler=_crear_muestreo_handler,
    writes=True,
))


# ──────────────────────────────────────────────────────────────────────────────
# 2. registrar_resultado
# ──────────────────────────────────────────────────────────────────────────────

class RegistrarResultadoInput(BaseModel):
    muestreo_id: str
    order_id: str
    resultado: Literal['conforme', 'no_conforme']
    observaciones: str = Field(..., min_length=3, max_length=2000)


async def _registrar_resultado_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(RegistrarResultadoInput, params)
    muestreo = await db.mcp_qa_muestreos.find_one(
        {'id': p.muestreo_id}, {'_id': 0},
    )
    if not muestreo:
        return {'success': False, 'error': 'muestreo_not_found'}
    if p.order_id not in muestreo.get('order_ids_seleccionados', []):
        return {'success': False, 'error': 'order_id_no_en_muestreo'}

    now = _now_iso()
    await db.mcp_qa_muestreos.update_one(
        {'id': p.muestreo_id},
        {'$set': {
            f'resultados_por_orden.{p.order_id}': {
                'resultado': p.resultado,
                'observaciones': p.observaciones,
                'recorded_at': now,
                'recorded_by': f'mcp:{identity.agent_id}',
            },
            'updated_at': now,
        }},
    )

    # Si todos los pendientes están resueltos → cerrar muestreo
    muestreo = await db.mcp_qa_muestreos.find_one({'id': p.muestreo_id}, {'_id': 0})
    completados = len(muestreo.get('resultados_por_orden', {}))
    if completados >= muestreo['tam_muestra']:
        await db.mcp_qa_muestreos.update_one(
            {'id': p.muestreo_id},
            {'$set': {'estado': 'completado', 'completed_at': now}},
        )

    response = {
        'success': True,
        'muestreo_id': p.muestreo_id,
        'order_id': p.order_id,
        'resultado': p.resultado,
        'completados': completados,
        'pendientes': muestreo['tam_muestra'] - completados,
    }
    if p.resultado == 'no_conforme':
        response['accion_requerida'] = 'abrir_nc'
        response['mensaje_accion'] = (
            f'⚠ Resultado NO CONFORME registrado. Debes ahora ejecutar `abrir_nc` '
            f'con tipo (menor|mayor|critica), proceso_afectado="reparacion", '
            f'descripcion basada en las observaciones, order_id_origen="{p.order_id}" '
            f'y evidencia_ids con las referencias disponibles.'
        )
    return response


register(ToolSpec(
    name='registrar_resultado',
    description=(
        'Registra el resultado (conforme|no_conforme) de una orden dentro de un '
        'lote de muestreo QA. Si no_conforme, el agente DEBE llamar después a '
        '`abrir_nc` (el resultado te lo dirá explícitamente). '
        'Idempotency_key recomendado: `resultado_{muestreo_id}_{order_id}`.'
    ),
    required_scope='iso:quality',
    input_schema={
        'type': 'object',
        'properties': {
            'muestreo_id': {'type': 'string'},
            'order_id': {'type': 'string'},
            'resultado': {'type': 'string', 'enum': ['conforme', 'no_conforme']},
            'observaciones': {'type': 'string', 'minLength': 3, 'maxLength': 2000},
            '_idempotency_key': {
                'type': 'string',
                'description': 'Obligatorio. Formato sugerido: resultado_{muestreo_id}_{order_id}',
            },
        },
        'required': ['muestreo_id', 'order_id', 'resultado', 'observaciones', '_idempotency_key'],
        'additionalProperties': False,
    },
    handler=_registrar_resultado_handler,
    writes=True,
))


# ──────────────────────────────────────────────────────────────────────────────
# 3. abrir_nc (No Conformidad)
# ──────────────────────────────────────────────────────────────────────────────

class AbrirNCInput(BaseModel):
    tipo: Literal['menor', 'mayor', 'critica']
    proceso_afectado: str = Field(..., min_length=2, max_length=100)
    descripcion: str = Field(..., min_length=5, max_length=2000)
    evidencia_ids: list[str] = Field(default_factory=list)
    order_id_origen: Optional[str] = None
    proveedor_id_origen: Optional[str] = None


async def _abrir_nc_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(AbrirNCInput, params)
    now = _now_iso()
    nc_id = str(uuid.uuid4())
    fecha_corta = datetime.now(timezone.utc).strftime('%Y%m%d')
    numero_nc = f'NC-{fecha_corta}-{str(uuid.uuid4())[:6].upper()}'

    doc = {
        'id': nc_id,
        'numero_nc': numero_nc,
        'tipo': p.tipo,
        'proceso_afectado': p.proceso_afectado,
        'descripcion': p.descripcion,
        'evidencia_ids': p.evidencia_ids,
        'ot_id': p.order_id_origen,
        'proveedor_id_origen': p.proveedor_id_origen,
        'origen': 'mcp_iso_officer',
        'estado': 'abierta',
        'motivo_apertura': 'no_conformidad',
        'problema': p.descripcion,
        'created_at': now,
        'updated_at': now,
        'created_by': f'mcp:{identity.agent_id}',
        'source': 'mcp_agent',
    }
    await db.capas.insert_one(dict(doc))

    return {
        'success': True,
        'nc_id': nc_id,
        'numero_nc': numero_nc,
        'tipo': p.tipo,
        'estado': 'abierta',
        'created_at': now,
    }


register(ToolSpec(
    name='abrir_nc',
    description=(
        'Abre una No Conformidad (NC) en el sistema ISO 9001. Se guarda en la '
        'colección `capas` (CAPA process). Tipo: menor (corrección local), '
        'mayor (acción correctiva formal), crítica (parada + revisión urgente). '
        'Devuelve nc_id + numero_nc. Requiere idempotency_key.'
    ),
    required_scope='iso:quality',
    input_schema={
        'type': 'object',
        'properties': {
            'tipo': {'type': 'string', 'enum': ['menor', 'mayor', 'critica']},
            'proceso_afectado': {'type': 'string', 'minLength': 2, 'maxLength': 100},
            'descripcion': {'type': 'string', 'minLength': 5, 'maxLength': 2000},
            'evidencia_ids': {'type': 'array', 'items': {'type': 'string'}},
            'order_id_origen': {'type': 'string'},
            'proveedor_id_origen': {'type': 'string'},
            '_idempotency_key': {'type': 'string', 'description': 'Obligatorio'},
        },
        'required': ['tipo', 'proceso_afectado', 'descripcion', 'evidencia_ids', '_idempotency_key'],
        'additionalProperties': False,
    },
    handler=_abrir_nc_handler,
    writes=True,
))


# ──────────────────────────────────────────────────────────────────────────────
# 4. listar_acuses_pendientes
# ──────────────────────────────────────────────────────────────────────────────

class ListarAcusesInput(BaseModel):
    filtro_rol: Optional[str] = Field(None, description='admin|tecnico|master — filtra usuarios')
    incluir_vencidos_dias: Optional[int] = Field(None, ge=1, le=365,
                                                 description='Solo docs publicados hace >= N días')


async def _listar_acuses_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(ListarAcusesInput, params)

    # Usuarios objetivo
    user_query: dict = {'active': {'$ne': False}}
    if p.filtro_rol:
        user_query['role'] = p.filtro_rol
    users = await db.users.find(
        user_query, {'_id': 0, 'id': 1, 'email': 1, 'nombre': 1, 'role': 1},
    ).to_list(500)
    user_index = {u['id']: u for u in users if u.get('id')}

    # Docs que requieren acuse
    doc_query = {'requiere_acuse': True, 'estado': 'vigente'}
    if p.incluir_vencidos_dias:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=p.incluir_vencidos_dias))
        doc_query['created_at'] = {'$lte': cutoff.isoformat()}
    docs = await db.iso_documentos.find(
        doc_query,
        {'_id': 0, 'id': 1, 'codigo': 1, 'titulo': 1, 'version': 1,
         'created_at': 1, 'acuses_lectura': 1, 'requiere_acuse': 1},
    ).to_list(500)

    resultados = []
    for d in docs:
        acusados_ids = {a.get('usuario_id') for a in (d.get('acuses_lectura') or [])}
        pendientes = [
            {'user_id': u['id'], 'email': u.get('email'),
             'nombre': u.get('nombre'), 'role': u.get('role')}
            for uid, u in user_index.items() if uid not in acusados_ids
        ]
        if not pendientes:
            continue
        resultados.append({
            'doc_id': d['id'],
            'codigo': d.get('codigo'),
            'titulo': d.get('titulo'),
            'version': d.get('version'),
            'publicado_en': d.get('created_at'),
            'dias_desde_publicacion': _dias_desde(d.get('created_at')),
            'total_pendientes': len(pendientes),
            'pendientes': pendientes,
        })

    # Ordenar por más antiguo primero
    resultados.sort(key=lambda r: r.get('dias_desde_publicacion') or 0, reverse=True)

    return {
        'total_documentos_con_pendientes': len(resultados),
        'total_usuarios_evaluados': len(user_index),
        'items': resultados,
    }


def _dias_desde(iso_str: Optional[str]) -> Optional[int]:
    if not iso_str:
        return None
    dt = _parse_iso(iso_str if isinstance(iso_str, str) else iso_str.isoformat())
    if not dt:
        return None
    return (datetime.now(timezone.utc) - dt).days


register(ToolSpec(
    name='listar_acuses_pendientes',
    description=(
        'Lista documentos ISO que requieren acuse de lectura y las personas que '
        'aún NO han acusado. Filtrable por rol (admin|tecnico|master) y por '
        'antigüedad (`incluir_vencidos_dias` para detectar incumplimientos). '
        'Útil para el ISO Officer antes de una auditoría.'
    ),
    required_scope='iso:quality',
    input_schema={
        'type': 'object',
        'properties': {
            'filtro_rol': {'type': 'string', 'description': 'admin|tecnico|master'},
            'incluir_vencidos_dias': {
                'type': 'integer', 'minimum': 1, 'maximum': 365,
                'description': 'Solo docs publicados hace >= N días',
            },
        },
        'additionalProperties': False,
    },
    handler=_listar_acuses_handler,
))


# ──────────────────────────────────────────────────────────────────────────────
# 5. evaluar_proveedor
# ──────────────────────────────────────────────────────────────────────────────

class CriteriosProveedorInput(BaseModel):
    calidad: int = Field(..., ge=1, le=5)
    plazo: int = Field(..., ge=1, le=5)
    precio: int = Field(..., ge=1, le=5)
    documentacion: int = Field(..., ge=1, le=5)


class EvaluarProveedorInput(BaseModel):
    proveedor_id: str = Field(..., min_length=1)
    criterios: CriteriosProveedorInput
    periodo_evaluado: str = Field(..., description='YYYY-Q[1-4] | YYYY-MM | texto libre')
    observaciones: Optional[str] = None


# Pesos por defecto (ISO 9001 · cláusula 8.4)
_PROVEEDOR_PESOS = {
    'calidad': 0.40, 'plazo': 0.30, 'precio': 0.15, 'documentacion': 0.15,
}


def _clasificar_proveedor(score_global: float) -> str:
    """Devuelve calificación A/B/C/D según score (1-5)."""
    if score_global >= 4.5:
        return 'A · preferente'
    if score_global >= 3.5:
        return 'B · aprobado'
    if score_global >= 2.5:
        return 'C · en observación'
    return 'D · a desactivar'


async def _evaluar_proveedor_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(EvaluarProveedorInput, params)

    # Resolver nombre del proveedor si existe
    prov = await db.proveedores.find_one(
        {'id': p.proveedor_id},
        {'_id': 0, 'id': 1, 'nombre': 1},
    )
    proveedor_nombre = prov.get('nombre') if prov else p.proveedor_id

    score_global = round(sum(
        getattr(p.criterios, c) * w for c, w in _PROVEEDOR_PESOS.items()
    ), 2)
    clasificacion = _clasificar_proveedor(score_global)

    # Evaluación anterior (misma proveedor_id o nombre)
    prev = await db.iso_proveedores_evaluacion.find_one(
        {'$or': [
            {'proveedor_id': p.proveedor_id},
            {'proveedor': proveedor_nombre},
        ]},
        {'_id': 0},
        sort=[('created_at', -1)],
    )

    now = _now_iso()
    doc = {
        'id': str(uuid.uuid4()),
        'proveedor_id': p.proveedor_id,
        'proveedor': proveedor_nombre,
        'periodo_evaluado': p.periodo_evaluado,
        'criterios': p.criterios.model_dump(),
        'score': score_global,
        'score_global': score_global,
        'clasificacion': clasificacion,
        'estado': 'vigente',
        'observaciones': p.observaciones,
        'created_at': now,
        'updated_at': now,
        'created_by': f'mcp:{identity.agent_id}',
        'source': 'mcp_agent',
    }
    await db.iso_proveedores_evaluacion.insert_one(dict(doc))

    comparativa = None
    if prev:
        prev_score = float(prev.get('score') or prev.get('score_global') or 0)
        delta = round(score_global - prev_score, 2)
        tendencia = 'mejora' if delta > 0.1 else ('empeora' if delta < -0.1 else 'estable')
        comparativa = {
            'evaluacion_anterior': {
                'periodo_evaluado': prev.get('periodo_evaluado'),
                'score': prev_score,
                'clasificacion': prev.get('clasificacion'),
                'created_at': prev.get('created_at'),
            },
            'delta_score': delta,
            'tendencia': tendencia,
        }

    return {
        'success': True,
        'evaluacion_id': doc['id'],
        'proveedor': proveedor_nombre,
        'score_global': score_global,
        'clasificacion': clasificacion,
        'criterios': doc['criterios'],
        'periodo_evaluado': p.periodo_evaluado,
        'comparativa': comparativa,
    }


register(ToolSpec(
    name='evaluar_proveedor',
    description=(
        'Evalúa un proveedor sobre 4 criterios (calidad, plazo, precio, documentación) '
        'puntuados 1-5. Calcula score global ponderado (ISO 9001 cláusula 8.4: '
        'calidad 40% · plazo 30% · precio 15% · documentación 15%) y clasifica en '
        'A/B/C/D. Devuelve comparativa con la evaluación anterior (delta + tendencia).'
    ),
    required_scope='iso:quality',
    input_schema={
        'type': 'object',
        'properties': {
            'proveedor_id': {'type': 'string'},
            'criterios': {
                'type': 'object',
                'properties': {
                    'calidad': {'type': 'integer', 'minimum': 1, 'maximum': 5},
                    'plazo': {'type': 'integer', 'minimum': 1, 'maximum': 5},
                    'precio': {'type': 'integer', 'minimum': 1, 'maximum': 5},
                    'documentacion': {'type': 'integer', 'minimum': 1, 'maximum': 5},
                },
                'required': ['calidad', 'plazo', 'precio', 'documentacion'],
                'additionalProperties': False,
            },
            'periodo_evaluado': {'type': 'string'},
            'observaciones': {'type': 'string'},
        },
        'required': ['proveedor_id', 'criterios', 'periodo_evaluado'],
        'additionalProperties': False,
    },
    handler=_evaluar_proveedor_handler,
    writes=True,
))


# ──────────────────────────────────────────────────────────────────────────────
# 6. generar_revision_direccion
# ──────────────────────────────────────────────────────────────────────────────

_SECCIONES_DEFAULT = [
    'indicadores', 'no_conformidades', 'acuses_pendientes',
    'proveedores', 'sla', 'acciones_recomendadas',
]


class GenerarRevisionInput(BaseModel):
    fecha_inicio: str
    fecha_fin: str
    incluir_secciones: Optional[list[str]] = None

    @field_validator('fecha_inicio', 'fecha_fin')
    @classmethod
    def _valid_iso(cls, v):
        if _parse_iso(v) is None:
            raise ValueError('fecha inválida (ISO)')
        return v


async def _generar_revision_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(GenerarRevisionInput, params)
    secciones = p.incluir_secciones or _SECCIONES_DEFAULT
    ini = _parse_iso(p.fecha_inicio).isoformat()
    fin = _parse_iso(p.fecha_fin).isoformat()
    informe: dict = {
        'periodo': {'inicio': ini, 'fin': fin},
        'generado_en': _now_iso(),
        'generado_por': identity.agent_id,
        'secciones_incluidas': secciones,
    }

    if 'indicadores' in secciones:
        total_ord = await db.ordenes.count_documents(
            {'created_at': {'$gte': ini, '$lte': fin}},
        )
        enviadas = await db.ordenes.count_documents(
            {'fecha_enviado': {'$gte': ini, '$lte': fin}},
        )
        reclam = await db.incidencias.count_documents(
            {'created_at': {'$gte': ini, '$lte': fin}},
        )
        tasa_reclam = round((100.0 * reclam / enviadas), 2) if enviadas else 0.0
        informe['indicadores'] = {
            'ordenes_creadas': total_ord,
            'ordenes_enviadas': enviadas,
            'reclamaciones': reclam,
            'tasa_reclamacion_pct': tasa_reclam,
        }

    if 'no_conformidades' in secciones:
        ncs = await db.capas.find(
            {'created_at': {'$gte': ini, '$lte': fin}},
            {'_id': 0, 'id': 1, 'numero_nc': 1, 'tipo': 1, 'estado': 1,
             'proceso_afectado': 1, 'created_at': 1},
        ).to_list(500)
        resumen_nc = {'total': len(ncs),
                      'abiertas': sum(1 for n in ncs if n.get('estado') == 'abierta'),
                      'por_tipo': {}}
        for n in ncs:
            t = n.get('tipo') or 'sin_tipo'
            resumen_nc['por_tipo'][t] = resumen_nc['por_tipo'].get(t, 0) + 1
        informe['no_conformidades'] = {'resumen': resumen_nc, 'items': ncs[:50]}

    if 'acuses_pendientes' in secciones:
        # Reutilizamos handler interno
        acuses_res = await _listar_acuses_handler(db, identity, {'incluir_vencidos_dias': 30})
        informe['acuses_pendientes'] = {
            'docs_con_pendientes': acuses_res['total_documentos_con_pendientes'],
            'muestra_top5': acuses_res['items'][:5],
        }

    if 'proveedores' in secciones:
        cursor = db.iso_proveedores_evaluacion.aggregate([
            {'$match': {'created_at': {'$gte': ini, '$lte': fin}}},
            {'$sort': {'created_at': -1}},
            {'$group': {
                '_id': {'$ifNull': ['$proveedor_id', '$proveedor']},
                'latest': {'$first': '$$ROOT'},
            }},
            {'$replaceRoot': {'newRoot': '$latest'}},
            {'$project': {
                '_id': 0, 'proveedor': 1, 'score': 1,
                'clasificacion': 1, 'periodo_evaluado': 1,
            }},
            {'$sort': {'score': 1}},
            {'$limit': 20},
        ])
        provs = [d async for d in cursor]
        informe['proveedores'] = {
            'evaluados_en_periodo': len(provs),
            'peores': [p_ for p_ in provs if (p_.get('score') or 0) < 3.5][:10],
            'top': sorted(provs, key=lambda x: -(x.get('score') or 0))[:5],
        }

    if 'sla' in secciones:
        total = await db.ordenes.count_documents(
            {'estado': 'enviado', 'fecha_enviado': {'$gte': ini, '$lte': fin}},
        )
        fuera = await db.ordenes.count_documents(
            {'estado': 'enviado', 'fecha_enviado': {'$gte': ini, '$lte': fin},
             'alerta_sla_enviada': True},
        )
        cumplimiento = round(100.0 * (total - fuera) / total, 2) if total else 0.0
        informe['sla'] = {
            'ordenes_enviadas': total,
            'fuera_sla': fuera,
            'cumplimiento_pct': cumplimiento,
        }

    if 'acciones_recomendadas' in secciones:
        acciones = []
        nc_abiertas = informe.get('no_conformidades', {}).get('resumen', {}).get('abiertas', 0)
        if nc_abiertas > 0:
            acciones.append(f'Cerrar {nc_abiertas} NCs abiertas antes del próximo comité.')
        tasa = informe.get('indicadores', {}).get('tasa_reclamacion_pct', 0)
        if tasa > 5:
            acciones.append(f'Tasa de reclamación {tasa}% > 5% umbral. Revisar causas en CAPA.')
        cumpl = informe.get('sla', {}).get('cumplimiento_pct', 100)
        if cumpl < 90:
            acciones.append(f'SLA cumplimiento {cumpl}% < 90%. Revisar proceso de reparación.')
        acuses_n = informe.get('acuses_pendientes', {}).get('docs_con_pendientes', 0)
        if acuses_n > 0:
            acciones.append(f'{acuses_n} documento(s) con acuses vencidos. Enviar recordatorio.')
        provs_malos = len(informe.get('proveedores', {}).get('peores', []))
        if provs_malos > 0:
            acciones.append(f'{provs_malos} proveedor(es) en observación. Plan de mejora o baja.')
        if not acciones:
            acciones.append('Sin acciones críticas. Mantener monitoreo rutinario.')
        informe['acciones_recomendadas'] = acciones

    return informe


register(ToolSpec(
    name='generar_revision_direccion',
    description=(
        'Genera un informe estructurado de Revisión por la Dirección (ISO 9001 §9.3) '
        'para un periodo. Secciones incluidas por defecto: indicadores, no_conformidades, '
        'acuses_pendientes, proveedores, sla, acciones_recomendadas. '
        'Útil como entrada al comité de revisión trimestral.'
    ),
    required_scope='iso:quality',
    input_schema={
        'type': 'object',
        'properties': {
            'fecha_inicio': {'type': 'string', 'description': 'ISO date/datetime'},
            'fecha_fin': {'type': 'string', 'description': 'ISO date/datetime'},
            'incluir_secciones': {
                'type': 'array',
                'items': {
                    'type': 'string',
                    'enum': _SECCIONES_DEFAULT,
                },
            },
        },
        'required': ['fecha_inicio', 'fecha_fin'],
        'additionalProperties': False,
    },
    handler=_generar_revision_handler,
))

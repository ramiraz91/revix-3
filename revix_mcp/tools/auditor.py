"""
Revix MCP · Tools Fase 2 — Auditor Transversal.

5 tools:
  1. ejecutar_audit_financiero   (audit:read)
  2. ejecutar_audit_operacional  (audit:read)
  3. ejecutar_audit_seguridad    (audit:read)
  4. generar_audit_report        (audit:report · idempotente)
  5. abrir_nc_audit              (audit:report · delegada a ISO Officer)

El agente auditor NO tiene acceso a orders:write, finance:*, customers:write, iso:*.
Todas las tools son analíticas: leen, detectan, reportan. NO modifican datos operativos.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..auth import AgentIdentity
from ._registry import ToolSpec, register
from ._common import validate_input


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _parse_iso(v) -> Optional[datetime]:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None


class _PeriodoInput(BaseModel):
    fecha_inicio: str
    fecha_fin: str

    @field_validator('fecha_inicio', 'fecha_fin')
    @classmethod
    def _valid_iso(cls, v):
        if _parse_iso(v) is None:
            raise ValueError('fecha inválida (ISO)')
        return v


# ──────────────────────────────────────────────────────────────────────────────
# 1 · ejecutar_audit_financiero
# ──────────────────────────────────────────────────────────────────────────────

class AuditFinancieroInput(_PeriodoInput):
    foco: Literal['facturas', 'liquidaciones', 'materiales', 'todo'] = 'todo'


async def _audit_financiero_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(AuditFinancieroInput, params)
    ini = _parse_iso(p.fecha_inicio).isoformat()
    fin = _parse_iso(p.fecha_fin).isoformat()

    hallazgos: list[dict] = []

    if p.foco in ('facturas', 'todo'):
        # Facturas sin orden asociada
        cursor = db.facturas.find(
            {'tipo': 'venta',
             'fecha_emision': {'$gte': ini, '$lte': fin},
             '$or': [
                 {'orden_id': None},
                 {'orden_id': ''},
             ]},
            {'_id': 0, 'id': 1, 'numero': 1, 'cliente_nombre': 1, 'total': 1},
        )
        fsin = [d async for d in cursor]
        if fsin:
            hallazgos.append({
                'id': f'FIN-001-{uuid.uuid4().hex[:6]}',
                'titulo': f'{len(fsin)} factura(s) de venta sin orden asociada',
                'severidad': 'HIGH',
                'descripcion': 'Facturas emitidas sin vínculo a una orden. Riesgo de ingresos no trazables.',
                'evidencia': [{'factura_id': f['id'], 'numero': f.get('numero'),
                               'total': f.get('total')} for f in fsin[:20]],
                'evidencia_count': len(fsin),
                'recomendacion': 'Revisar y vincular cada factura a su orden origen, o justificar el motivo.',
            })

        # Órdenes enviadas sin facturar
        ord_sin_fact = await db.ordenes.find({
            'estado': 'enviado',
            'fecha_enviado': {'$gte': ini, '$lte': fin},
            '$or': [
                {'facturada': {'$ne': True}},
                {'factura_id': None},
            ],
        }, {'_id': 0, 'id': 1, 'numero_orden': 1, 'presupuesto_total': 1,
             'cliente_id': 1}).to_list(500)
        if ord_sin_fact:
            hallazgos.append({
                'id': f'FIN-002-{uuid.uuid4().hex[:6]}',
                'titulo': f'{len(ord_sin_fact)} orden(es) enviada(s) sin factura',
                'severidad': 'CRITICAL',
                'descripcion': (
                    'Órdenes cerradas y enviadas sin factura emitida. '
                    'Pérdida potencial de ingresos facturables.'
                ),
                'evidencia': [
                    {'order_id': o['id'], 'numero_orden': o.get('numero_orden'),
                     'importe_esperado': o.get('presupuesto_total')}
                    for o in ord_sin_fact[:20]
                ],
                'evidencia_count': len(ord_sin_fact),
                'importe_total_estimado': round(sum(
                    float(o.get('presupuesto_total') or 0) for o in ord_sin_fact
                ), 2),
                'recomendacion': 'Emitir facturas pendientes o documentar justificación caso a caso.',
            })

        # Discrepancias de totales (orden.total vs factura.total)
        facturas_periodo = await db.facturas.find({
            'tipo': 'venta', 'fecha_emision': {'$gte': ini, '$lte': fin},
            'orden_id': {'$nin': [None, '']},
        }, {'_id': 0, 'id': 1, 'orden_id': 1, 'total': 1, 'numero': 1}).to_list(2000)
        discrepancias = []
        for f in facturas_periodo:
            ord_doc = await db.ordenes.find_one(
                {'id': f['orden_id']},
                {'_id': 0, 'presupuesto_total': 1, 'numero_orden': 1},
            )
            if not ord_doc:
                continue
            ord_tot = float(ord_doc.get('presupuesto_total') or 0)
            fac_tot = float(f.get('total') or 0)
            if abs(ord_tot - fac_tot) > 0.01:
                discrepancias.append({
                    'factura_id': f['id'], 'numero_factura': f.get('numero'),
                    'numero_orden': ord_doc.get('numero_orden'),
                    'total_orden': ord_tot, 'total_factura': fac_tot,
                    'delta': round(fac_tot - ord_tot, 2),
                })
        if discrepancias:
            hallazgos.append({
                'id': f'FIN-003-{uuid.uuid4().hex[:6]}',
                'titulo': f'{len(discrepancias)} discrepancia(s) entre total de orden y factura',
                'severidad': 'HIGH',
                'descripcion': 'Diferencias entre el total registrado en la orden y el total de su factura.',
                'evidencia': discrepancias[:20],
                'evidencia_count': len(discrepancias),
                'recomendacion': 'Investigar cada caso: puede haber rectificativas pendientes o errores de captura.',
            })

    if p.foco in ('liquidaciones', 'todo'):
        # Liquidaciones duplicadas (misma orden aparece en >1 liquidación)
        dup_cursor = db.liquidaciones.aggregate([
            {'$match': {'fecha_liquidacion': {'$gte': ini, '$lte': fin}}},
            {'$unwind': '$orden_ids'},
            {'$group': {'_id': '$orden_ids', 'count': {'$sum': 1},
                        'liquidaciones': {'$push': {'id': '$id', 'numero': '$numero'}}}},
            {'$match': {'count': {'$gt': 1}}},
            {'$limit': 50},
        ])
        dup = [d async for d in dup_cursor]
        if dup:
            hallazgos.append({
                'id': f'FIN-004-{uuid.uuid4().hex[:6]}',
                'titulo': f'{len(dup)} orden(es) en múltiples liquidaciones',
                'severidad': 'CRITICAL',
                'descripcion': 'Riesgo de doble-pago a técnicos / proveedores.',
                'evidencia': [{'order_id': d['_id'], 'liquidaciones': d['liquidaciones']}
                              for d in dup[:20]],
                'evidencia_count': len(dup),
                'recomendacion': 'Revisar cada caso y anular la liquidación duplicada.',
            })

    if p.foco in ('materiales', 'todo'):
        # Materiales con precio_unitario <= 0 en órdenes del periodo
        cursor = db.ordenes.find({
            'created_at': {'$gte': ini, '$lte': fin},
            'materiales.precio_unitario': {'$lte': 0},
        }, {'_id': 0, 'id': 1, 'numero_orden': 1, 'materiales': 1}).limit(200)
        ord_mat_mal = [d async for d in cursor]
        if ord_mat_mal:
            hallazgos.append({
                'id': f'FIN-005-{uuid.uuid4().hex[:6]}',
                'titulo': f'{len(ord_mat_mal)} orden(es) con materiales a precio 0 o negativo',
                'severidad': 'MEDIUM',
                'descripcion': 'Material registrado sin coste → afecta margen y valoración de inventario.',
                'evidencia': [{'order_id': o['id'], 'numero_orden': o.get('numero_orden')}
                              for o in ord_mat_mal[:20]],
                'evidencia_count': len(ord_mat_mal),
                'recomendacion': 'Actualizar precio en cada orden o marcar explícitamente como servicio sin coste.',
            })

    return {
        'tipo_auditoria': 'financiero',
        'periodo': {'inicio': ini, 'fin': fin},
        'foco': p.foco,
        'hallazgos_count': len(hallazgos),
        'severidad_max': max(
            (h['severidad'] for h in hallazgos),
            key=lambda s: {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2, 'CRITICAL': 3}.get(s, 0),
            default='NONE',
        ),
        'hallazgos': hallazgos,
        'ejecutado_en': _now_iso(),
        'ejecutado_por': identity.agent_id,
    }


register(ToolSpec(
    name='ejecutar_audit_financiero',
    description=(
        'Audita la integridad financiera en un periodo: facturas sin orden, '
        'órdenes cerradas sin facturar, discrepancias de totales orden↔factura, '
        'liquidaciones duplicadas, materiales con precio 0/negativo. Devuelve '
        'lista de hallazgos con severidad (LOW/MEDIUM/HIGH/CRITICAL) y evidencia.'
    ),
    required_scope='audit:read',
    input_schema={
        'type': 'object',
        'properties': {
            'fecha_inicio': {'type': 'string'},
            'fecha_fin': {'type': 'string'},
            'foco': {'type': 'string',
                     'enum': ['facturas', 'liquidaciones', 'materiales', 'todo'],
                     'default': 'todo'},
        },
        'required': ['fecha_inicio', 'fecha_fin'],
        'additionalProperties': False,
    },
    handler=_audit_financiero_handler,
))


# ──────────────────────────────────────────────────────────────────────────────
# 2 · ejecutar_audit_operacional
# ──────────────────────────────────────────────────────────────────────────────

class AuditOperacionalInput(_PeriodoInput):
    tecnico_id: Optional[str] = None
    tipo_reparacion: Optional[str] = None


async def _audit_operacional_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(AuditOperacionalInput, params)
    ini = _parse_iso(p.fecha_inicio).isoformat()
    fin = _parse_iso(p.fecha_fin).isoformat()

    base_filter: dict = {'created_at': {'$gte': ini, '$lte': fin}}
    if p.tecnico_id:
        base_filter['tecnico_asignado'] = p.tecnico_id
    if p.tipo_reparacion:
        base_filter['tipo_servicio'] = p.tipo_reparacion

    hallazgos: list[dict] = []

    # Órdenes sin token de seguimiento
    sin_token = await db.ordenes.count_documents({
        **base_filter,
        '$or': [{'token_seguimiento': None}, {'token_seguimiento': ''}],
    })
    if sin_token > 0:
        hallazgos.append({
            'id': f'OP-001-{uuid.uuid4().hex[:6]}',
            'titulo': f'{sin_token} orden(es) sin token_seguimiento',
            'severidad': 'MEDIUM',
            'descripcion': 'Cliente no puede consultar estado autónomamente.',
            'evidencia_count': sin_token,
            'recomendacion': 'Ejecutar migración de tokens o regenerar manualmente.',
        })

    # Estados inconsistentes: enviado sin fecha_enviado
    inconsist = await db.ordenes.find({
        **base_filter,
        'estado': 'enviado',
        '$or': [{'fecha_enviado': None}, {'fecha_enviado': ''}],
    }, {'_id': 0, 'id': 1, 'numero_orden': 1}).to_list(100)
    if inconsist:
        hallazgos.append({
            'id': f'OP-002-{uuid.uuid4().hex[:6]}',
            'titulo': f'{len(inconsist)} orden(es) "enviado" sin fecha_enviado',
            'severidad': 'HIGH',
            'descripcion': 'Campo fecha_enviado vacío en órdenes marcadas como enviadas.',
            'evidencia': [{'order_id': o['id'], 'numero_orden': o.get('numero_orden')}
                          for o in inconsist[:20]],
            'evidencia_count': len(inconsist),
            'recomendacion': 'Completar fecha_enviado o revertir estado.',
        })

    # Tiempos anómalos: reparación >30 días
    cursor = db.ordenes.find({
        **base_filter,
        'estado': {'$in': ['reparando', 'reparado', 'enviado']},
    }, {'_id': 0, 'id': 1, 'numero_orden': 1, 'created_at': 1,
         'fecha_fin_reparacion': 1, 'fecha_enviado': 1}).limit(2000)
    tiempos_anomalos = []
    async for o in cursor:
        ini_dt = _parse_iso(o.get('created_at'))
        fin_dt = _parse_iso(o.get('fecha_enviado') or o.get('fecha_fin_reparacion'))
        if not ini_dt or not fin_dt:
            continue
        horas = (fin_dt - ini_dt).total_seconds() / 3600
        if horas > 720:  # >30 días
            tiempos_anomalos.append({
                'order_id': o['id'], 'numero_orden': o.get('numero_orden'),
                'duracion_horas': round(horas, 1),
                'duracion_dias': round(horas / 24, 1),
            })
    if tiempos_anomalos:
        hallazgos.append({
            'id': f'OP-003-{uuid.uuid4().hex[:6]}',
            'titulo': f'{len(tiempos_anomalos)} orden(es) con duración >30 días',
            'severidad': 'MEDIUM',
            'descripcion': 'Reparaciones anómalamente largas. Posible bloqueo no gestionado.',
            'evidencia': tiempos_anomalos[:20],
            'evidencia_count': len(tiempos_anomalos),
            'recomendacion': 'Revisar cada caso, abrir incidencia si procede.',
        })

    # Técnicos sin actividad en el periodo
    tecnicos_activos = await db.ordenes.distinct('tecnico_asignado', base_filter)
    tecnicos_activos = {t for t in tecnicos_activos if t}
    todos_tecnicos = await db.users.find(
        {'role': 'tecnico', 'active': {'$ne': False}},
        {'_id': 0, 'id': 1, 'email': 1, 'nombre': 1},
    ).to_list(200)
    sin_actividad = [t for t in todos_tecnicos if t['id'] not in tecnicos_activos]
    if sin_actividad:
        hallazgos.append({
            'id': f'OP-004-{uuid.uuid4().hex[:6]}',
            'titulo': f'{len(sin_actividad)} técnico(s) activo(s) sin órdenes en el periodo',
            'severidad': 'LOW',
            'descripcion': 'Pueden ser vacaciones, baja, o técnico dado de alta por error.',
            'evidencia': [{'tecnico_id': t['id'], 'nombre': t.get('nombre'),
                           'email': t.get('email')} for t in sin_actividad],
            'evidencia_count': len(sin_actividad),
            'recomendacion': 'Revisar asignaciones o desactivar cuenta si procede.',
        })

    return {
        'tipo_auditoria': 'operacional',
        'periodo': {'inicio': ini, 'fin': fin},
        'filtros': {'tecnico_id': p.tecnico_id, 'tipo_reparacion': p.tipo_reparacion},
        'hallazgos_count': len(hallazgos),
        'severidad_max': max(
            (h['severidad'] for h in hallazgos),
            key=lambda s: {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2, 'CRITICAL': 3}.get(s, 0),
            default='NONE',
        ),
        'hallazgos': hallazgos,
        'ejecutado_en': _now_iso(),
        'ejecutado_por': identity.agent_id,
    }


register(ToolSpec(
    name='ejecutar_audit_operacional',
    description=(
        'Audita integridad operacional: órdenes sin token_seguimiento, estados '
        'inconsistentes (ej. enviado sin fecha_enviado), tiempos anómalos '
        '(>30 días), técnicos activos sin actividad. Filtrable por técnico y '
        'tipo de reparación.'
    ),
    required_scope='audit:read',
    input_schema={
        'type': 'object',
        'properties': {
            'fecha_inicio': {'type': 'string'},
            'fecha_fin': {'type': 'string'},
            'tecnico_id': {'type': 'string'},
            'tipo_reparacion': {'type': 'string'},
        },
        'required': ['fecha_inicio', 'fecha_fin'],
        'additionalProperties': False,
    },
    handler=_audit_operacional_handler,
))


# ──────────────────────────────────────────────────────────────────────────────
# 3 · ejecutar_audit_seguridad
# ──────────────────────────────────────────────────────────────────────────────

class AuditSeguridadInput(_PeriodoInput):
    pass


async def _audit_seguridad_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(AuditSeguridadInput, params)
    ini = _parse_iso(p.fecha_inicio).isoformat()
    fin = _parse_iso(p.fecha_fin).isoformat()

    hallazgos: list[dict] = []

    # Accesos fuera de horario laboral (06:00-22:00 UTC+1/+2 → considera 05:00-21:00 UTC)
    # Para no depender de tz del backend usamos audit_logs.timestamp como string ISO UTC
    cursor = db.audit_logs.find(
        {'source': 'mcp_agent', 'timestamp': {'$gte': ini, '$lte': fin}},
        {'_id': 0, 'agent_id': 1, 'tool': 1, 'timestamp': 1, 'error': 1},
    ).limit(10000)
    fuera_horario: dict[str, list] = {}
    volumen_por_agente: dict[str, int] = {}
    sin_scope: list[dict] = []
    async for log in cursor:
        ts = _parse_iso(log.get('timestamp'))
        if ts is None:
            continue
        agent_id = log.get('agent_id') or 'unknown'
        volumen_por_agente[agent_id] = volumen_por_agente.get(agent_id, 0) + 1

        hora = ts.hour  # UTC
        if hora < 5 or hora >= 22:
            fuera_horario.setdefault(agent_id, []).append({
                'timestamp': log.get('timestamp'),
                'tool': log.get('tool'),
                'hora_utc': hora,
            })
        if (log.get('error') or '').startswith('scope_denied'):
            sin_scope.append({
                'agent_id': agent_id, 'tool': log.get('tool'),
                'timestamp': log.get('timestamp'), 'error': log.get('error'),
            })

    if fuera_horario:
        total_fuera = sum(len(v) for v in fuera_horario.values())
        hallazgos.append({
            'id': f'SEC-001-{uuid.uuid4().hex[:6]}',
            'titulo': f'{total_fuera} acceso(s) MCP fuera de horario (22:00-05:00 UTC)',
            'severidad': 'MEDIUM',
            'descripcion': 'Actividad MCP en horario nocturno — revisar si es scheduler legítimo o uso anómalo.',
            'evidencia': [
                {'agent_id': a, 'count': len(v), 'ejemplos': v[:3]}
                for a, v in fuera_horario.items()
            ],
            'evidencia_count': total_fuera,
            'recomendacion': 'Confirmar si coincide con tareas programadas. Si no, revocar API key del agente afectado.',
        })

    # Volumen inusual (>500 llamadas/min en el periodo)
    # Usamos mcp_rate_limits como fuente de verdad (ventanas de 60s)
    vol_cursor = db.mcp_rate_limits.aggregate([
        {'$match': {'timestamp': {'$gte': _parse_iso(ini), '$lte': _parse_iso(fin)}}},
        {'$group': {
            '_id': {'agent_id': '$agent_id',
                    'minuto': {'$dateTrunc': {'date': '$timestamp', 'unit': 'minute'}}},
            'count': {'$sum': 1},
        }},
        {'$match': {'count': {'$gte': 500}}},
        {'$sort': {'count': -1}},
        {'$limit': 50},
    ])
    try:
        vol_picos = [d async for d in vol_cursor]
    except Exception:  # noqa: BLE001 — fallback si $dateTrunc no soportado
        vol_picos = []
    if vol_picos:
        hallazgos.append({
            'id': f'SEC-002-{uuid.uuid4().hex[:6]}',
            'titulo': f'{len(vol_picos)} pico(s) de volumen >500 llamadas/min',
            'severidad': 'HIGH',
            'descripcion': 'Volumen inusualmente alto — posible loop de agente o abuso de API key.',
            'evidencia': [
                {'agent_id': v['_id']['agent_id'], 'minuto': str(v['_id']['minuto']),
                 'calls': v['count']}
                for v in vol_picos
            ],
            'evidencia_count': len(vol_picos),
            'recomendacion': 'Revisar logs del agente afectado. Bajar rate limit temporalmente si procede.',
        })

    if sin_scope:
        hallazgos.append({
            'id': f'SEC-003-{uuid.uuid4().hex[:6]}',
            'titulo': f'{len(sin_scope)} intento(s) de tool sin scope',
            'severidad': 'HIGH',
            'descripcion': 'Agentes intentando invocar tools para las que no tienen permiso.',
            'evidencia': sin_scope[:20],
            'evidencia_count': len(sin_scope),
            'recomendacion': 'Revisar si es un bug del prompt del agente o un intento de escalado.',
        })

    return {
        'tipo_auditoria': 'seguridad',
        'periodo': {'inicio': ini, 'fin': fin},
        'resumen_volumen': volumen_por_agente,
        'hallazgos_count': len(hallazgos),
        'severidad_max': max(
            (h['severidad'] for h in hallazgos),
            key=lambda s: {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2, 'CRITICAL': 3}.get(s, 0),
            default='NONE',
        ),
        'hallazgos': hallazgos,
        'ejecutado_en': _now_iso(),
        'ejecutado_por': identity.agent_id,
    }


register(ToolSpec(
    name='ejecutar_audit_seguridad',
    description=(
        'Audita seguridad MCP en un periodo: accesos fuera de horario (22:00-05:00 UTC), '
        'volumen inusual por agente (>500/min), intentos de tool sin scope. Usa '
        'audit_logs + mcp_rate_limits como fuentes de verdad.'
    ),
    required_scope='audit:read',
    input_schema={
        'type': 'object',
        'properties': {
            'fecha_inicio': {'type': 'string'},
            'fecha_fin': {'type': 'string'},
        },
        'required': ['fecha_inicio', 'fecha_fin'],
        'additionalProperties': False,
    },
    handler=_audit_seguridad_handler,
))


# ──────────────────────────────────────────────────────────────────────────────
# 4 · generar_audit_report
# ──────────────────────────────────────────────────────────────────────────────

class HallazgoInput(BaseModel):
    id: str = Field(..., min_length=1)
    descripcion: str = Field(..., min_length=5)
    severidad: Literal['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    evidencia: list[dict] = Field(..., min_length=1)
    recomendacion: str = Field(..., min_length=5)


class GenerarAuditReportInput(BaseModel):
    tipo_auditoria: Literal['financiero', 'operacional', 'seguridad', 'mixto']
    fecha_inicio: str
    fecha_fin: str
    hallazgos: list[HallazgoInput] = Field(..., min_length=1)

    @field_validator('fecha_inicio', 'fecha_fin')
    @classmethod
    def _valid_iso(cls, v):
        if _parse_iso(v) is None:
            raise ValueError('fecha inválida (ISO)')
        return v


async def _generar_audit_report_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(GenerarAuditReportInput, params)

    # Validar que ha ejecutado al menos una tool de auditoría recientemente (30 min)
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    ejecutado = await db.audit_logs.find_one({
        'source': 'mcp_agent', 'agent_id': identity.agent_id,
        'tool': {'$in': ['ejecutar_audit_financiero', 'ejecutar_audit_operacional',
                         'ejecutar_audit_seguridad']},
        'timestamp': {'$gte': cutoff},
        'error': None,
    }, {'_id': 0, 'tool': 1})
    if not ejecutado:
        return {
            'success': False, 'error': 'sin_auditoria_previa',
            'message': (
                'Debes ejecutar al menos una tool de auditoría '
                '(ejecutar_audit_financiero|operacional|seguridad) en los últimos '
                '30 minutos antes de generar un reporte.'
            ),
        }

    # Validar que todos los hallazgos tienen evidencia
    for h in p.hallazgos:
        if not h.evidencia:
            return {
                'success': False, 'error': 'hallazgo_sin_evidencia',
                'message': f'Hallazgo "{h.id}" no tiene evidencia. No se permiten reportes vacíos.',
            }

    # Crear reporte
    report_id = str(uuid.uuid4())
    now = _now_iso()
    fecha_corta = datetime.now(timezone.utc).strftime('%Y%m%d')
    numero_report = f'AUD-{fecha_corta}-{uuid.uuid4().hex[:6].upper()}'

    by_sev = {}
    for h in p.hallazgos:
        by_sev[h.severidad] = by_sev.get(h.severidad, 0) + 1

    doc = {
        'id': report_id,
        'numero_report': numero_report,
        'tipo_auditoria': p.tipo_auditoria,
        'periodo': {'inicio': p.fecha_inicio, 'fin': p.fecha_fin},
        'hallazgos': [h.model_dump() for h in p.hallazgos],
        'hallazgos_count': len(p.hallazgos),
        'hallazgos_por_severidad': by_sev,
        'severidad_max': max(
            (h.severidad for h in p.hallazgos),
            key=lambda s: {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2, 'CRITICAL': 3}.get(s, 0),
        ),
        'estado': 'emitido',
        'created_at': now,
        'created_by': f'mcp:{identity.agent_id}',
        'source': 'mcp_agent',
    }
    await db.mcp_audit_reports.insert_one(dict(doc))

    return {
        'success': True,
        'audit_report_id': report_id,
        'numero_report': numero_report,
        'tipo_auditoria': p.tipo_auditoria,
        'hallazgos_count': len(p.hallazgos),
        'hallazgos_por_severidad': by_sev,
        'severidad_max': doc['severidad_max'],
        'created_at': now,
        'hint_next_action': (
            'Si hay hallazgos HIGH o CRITICAL, considera abrir NCs con abrir_nc_audit '
            'para que el ISO Officer los aborde formalmente.'
        ) if any(h.severidad in ('HIGH', 'CRITICAL') for h in p.hallazgos) else None,
    }


register(ToolSpec(
    name='generar_audit_report',
    description=(
        'Genera un reporte de auditoría oficial. REQUISITOS: (1) haber ejecutado '
        'al menos una tool de auditoría en los últimos 30 minutos, (2) al menos '
        'un hallazgo con evidencia no vacía. Persiste en `mcp_audit_reports` con '
        'numero_report auto. Idempotency_key obligatorio.'
    ),
    required_scope='audit:report',
    input_schema={
        'type': 'object',
        'properties': {
            'tipo_auditoria': {'type': 'string',
                               'enum': ['financiero', 'operacional', 'seguridad', 'mixto']},
            'fecha_inicio': {'type': 'string'},
            'fecha_fin': {'type': 'string'},
            'hallazgos': {
                'type': 'array',
                'minItems': 1,
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'string'},
                        'descripcion': {'type': 'string', 'minLength': 5},
                        'severidad': {'type': 'string',
                                      'enum': ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']},
                        'evidencia': {'type': 'array', 'minItems': 1},
                        'recomendacion': {'type': 'string', 'minLength': 5},
                    },
                    'required': ['id', 'descripcion', 'severidad', 'evidencia', 'recomendacion'],
                    'additionalProperties': True,
                },
            },
            '_idempotency_key': {'type': 'string', 'description': 'Obligatorio'},
        },
        'required': ['tipo_auditoria', 'fecha_inicio', 'fecha_fin', 'hallazgos', '_idempotency_key'],
        'additionalProperties': False,
    },
    handler=_generar_audit_report_handler,
    writes=True,
))


# ──────────────────────────────────────────────────────────────────────────────
# 5 · abrir_nc_audit (delegada; solo para HIGH/CRITICAL)
# ──────────────────────────────────────────────────────────────────────────────

class AbrirNCAuditInput(BaseModel):
    tipo: Literal['menor', 'mayor', 'critica']
    proceso_afectado: str = Field(..., min_length=2, max_length=100)
    descripcion: str = Field(..., min_length=5, max_length=2000)
    evidencia_ids: list[str] = Field(..., min_length=1)
    audit_report_id_origen: str = Field(..., min_length=1)
    hallazgo_id_origen: Optional[str] = None


async def _abrir_nc_audit_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(AbrirNCAuditInput, params)

    # Validar que el audit_report existe y pertenece a este agente
    report = await db.mcp_audit_reports.find_one(
        {'id': p.audit_report_id_origen},
        {'_id': 0, 'hallazgos': 1, 'created_by': 1, 'numero_report': 1},
    )
    if not report:
        return {'success': False, 'error': 'audit_report_no_encontrado'}

    # Validar que el hallazgo referenciado es HIGH o CRITICAL
    hallazgo = None
    if p.hallazgo_id_origen:
        hallazgo = next(
            (h for h in report.get('hallazgos', []) if h.get('id') == p.hallazgo_id_origen),
            None,
        )
        if not hallazgo:
            return {'success': False, 'error': 'hallazgo_no_encontrado_en_report'}
        if hallazgo.get('severidad') not in ('HIGH', 'CRITICAL'):
            return {
                'success': False, 'error': 'severidad_insuficiente',
                'message': f'Solo se abren NCs para hallazgos HIGH/CRITICAL. Este es {hallazgo.get("severidad")}.',
            }

    now = _now_iso()
    nc_id = str(uuid.uuid4())
    fecha_corta = datetime.now(timezone.utc).strftime('%Y%m%d')
    numero_nc = f'NC-{fecha_corta}-{uuid.uuid4().hex[:6].upper()}'

    doc = {
        'id': nc_id,
        'numero_nc': numero_nc,
        'tipo': p.tipo,
        'proceso_afectado': p.proceso_afectado,
        'descripcion': p.descripcion,
        'evidencia_ids': p.evidencia_ids,
        'audit_report_id_origen': p.audit_report_id_origen,
        'numero_audit_report': report.get('numero_report'),
        'hallazgo_id_origen': p.hallazgo_id_origen,
        'origen': 'mcp_auditor_transversal',
        'estado': 'abierta',
        'motivo_apertura': 'audit_report',
        'problema': p.descripcion,
        'asignado_a': 'iso_officer',  # delegación explícita
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
        'asignado_a': 'iso_officer',
        'audit_report_id_origen': p.audit_report_id_origen,
        'created_at': now,
    }


register(ToolSpec(
    name='abrir_nc_audit',
    description=(
        'Abre una NC a partir de un hallazgo de auditoría. SOLO permitido para '
        'hallazgos HIGH o CRITICAL referenciados por audit_report_id. La NC queda '
        'asignada al ISO Officer (asignado_a=iso_officer) para su tratamiento formal. '
        'Requiere idempotency_key.'
    ),
    required_scope='audit:report',
    input_schema={
        'type': 'object',
        'properties': {
            'tipo': {'type': 'string', 'enum': ['menor', 'mayor', 'critica']},
            'proceso_afectado': {'type': 'string', 'minLength': 2, 'maxLength': 100},
            'descripcion': {'type': 'string', 'minLength': 5, 'maxLength': 2000},
            'evidencia_ids': {'type': 'array', 'minItems': 1, 'items': {'type': 'string'}},
            'audit_report_id_origen': {'type': 'string'},
            'hallazgo_id_origen': {'type': 'string'},
            '_idempotency_key': {'type': 'string', 'description': 'Obligatorio'},
        },
        'required': ['tipo', 'proceso_afectado', 'descripcion', 'evidencia_ids',
                     'audit_report_id_origen', '_idempotency_key'],
        'additionalProperties': False,
    },
    handler=_abrir_nc_audit_handler,
    writes=True,
))

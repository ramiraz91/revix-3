"""
Revix MCP · Tools Fase 3 — Gestor de Siniestros (aseguradoras).

5 tools:
  1. listar_peticiones_pendientes      (orders:read + insurance:ops)
  2. crear_orden_desde_peticion        (orders:write + insurance:ops · idempotente)
  3. actualizar_portal_insurama        (insurance:ops · mock en preview)
  4. subir_evidencias                  (insurance:ops)
  5. cerrar_siniestro                  (orders:write + insurance:ops · valida evidencias+portal)

Colecciones:
  - siniestros_peticiones           (peticiones entrantes de aseguradoras)
  - aseguradoras_contratos          (contratos activos con SLA y límites)
  - ordenes                         (se crean órdenes siniestro desde peticion)
  - mcp_insurama_updates            (traza de llamadas al portal)
  - siniestros_evidencias           (refs a archivos subidos)
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..auth import AgentIdentity, AuthError
from ..config import MCP_ENV
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


def _require_scopes(identity: AgentIdentity, *extras: str) -> None:
    for s in extras:
        if not identity.has_scope(s):
            raise AuthError(
                f'Scope requerido "{s}" no presente en agente "{identity.agent_id}"',
            )


# ──────────────────────────────────────────────────────────────────────────────
# 1 · listar_peticiones_pendientes
# ──────────────────────────────────────────────────────────────────────────────

class ListarPeticionesInput(BaseModel):
    aseguradora_id: Optional[str] = None
    estado: Literal['recibida', 'en_proceso', 'pendiente_validacion'] = 'recibida'
    limit: int = Field(100, ge=1, le=500)


async def _listar_peticiones_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require_scopes(identity, 'orders:read')
    p = validate_input(ListarPeticionesInput, params)

    query: dict = {'estado': p.estado}
    if p.aseguradora_id:
        query['aseguradora_id'] = p.aseguradora_id

    cursor = db.siniestros_peticiones.find(query, {
        '_id': 0, 'id': 1, 'siniestro_id_externo': 1,
        'aseguradora_id': 1, 'aseguradora_nombre': 1,
        'cliente_nombre': 1, 'dispositivo': 1,
        'importe_estimado': 1, 'estado': 1,
        'tipo_reparacion': 1,
        'fecha_recepcion': 1,
    }).sort('fecha_recepcion', 1).limit(p.limit)
    peticiones = [d async for d in cursor]

    # Enriquecer con SLA de la aseguradora
    now = datetime.now(timezone.utc)
    contratos = {
        c['aseguradora_id']: c async for c in db.aseguradoras_contratos.find(
            {'activo': True}, {'_id': 0},
        )
    }
    for pet in peticiones:
        recep = _parse_iso(pet.get('fecha_recepcion'))
        contrato = contratos.get(pet.get('aseguradora_id'), {})
        sla_h = int(contrato.get('sla_horas_respuesta') or 48)
        horas_transcurridas = (now - recep).total_seconds() / 3600 if recep else 0
        horas_restantes = sla_h - horas_transcurridas
        pet['horas_restantes_sla'] = round(horas_restantes, 1)
        if horas_restantes < 0:
            pet['prioridad'] = 'critico'
        elif horas_restantes < 12:
            pet['prioridad'] = 'alta'
        elif horas_restantes < 24:
            pet['prioridad'] = 'media'
        else:
            pet['prioridad'] = 'baja'

    # Ordenar por prioridad + antigüedad
    prio_rank = {'critico': 0, 'alta': 1, 'media': 2, 'baja': 3}
    peticiones.sort(key=lambda x: (prio_rank[x['prioridad']], x.get('fecha_recepcion') or ''))

    resumen = {'critico': 0, 'alta': 0, 'media': 0, 'baja': 0}
    for p_ in peticiones:
        resumen[p_['prioridad']] += 1

    return {
        'total': len(peticiones),
        'estado_filtro': p.estado,
        'resumen_prioridad': resumen,
        'items': peticiones,
    }


register(ToolSpec(
    name='listar_peticiones_pendientes',
    description=(
        'Lista peticiones de aseguradora (estado recibida|en_proceso|pendiente_validacion). '
        'Ordenadas por prioridad SLA: crítico (SLA vencido) > alta (<12h) > media (<24h) > baja. '
        'Usa `aseguradoras_contratos.sla_horas_respuesta` para calcular.'
    ),
    required_scope='insurance:ops',
    input_schema={
        'type': 'object',
        'properties': {
            'aseguradora_id': {'type': 'string'},
            'estado': {'type': 'string',
                       'enum': ['recibida', 'en_proceso', 'pendiente_validacion'],
                       'default': 'recibida'},
            'limit': {'type': 'integer', 'minimum': 1, 'maximum': 500, 'default': 100},
        },
        'additionalProperties': False,
    },
    handler=_listar_peticiones_handler,
))


# ──────────────────────────────────────────────────────────────────────────────
# 2 · crear_orden_desde_peticion
# ──────────────────────────────────────────────────────────────────────────────

class CrearOrdenSiniestroInput(BaseModel):
    peticion_id: str
    tecnico_id: str
    fecha_estimada_entrega: str

    # Validado en handler


async def _crear_orden_desde_peticion_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require_scopes(identity, 'orders:write')
    p = validate_input(CrearOrdenSiniestroInput, params)

    if _parse_iso(p.fecha_estimada_entrega) is None:
        return {'success': False, 'error': 'fecha_estimada_entrega_invalida'}

    # Cargar petición
    peticion = await db.siniestros_peticiones.find_one(
        {'id': p.peticion_id}, {'_id': 0},
    )
    if not peticion:
        return {'success': False, 'error': 'peticion_not_found'}
    if peticion.get('estado') == 'orden_creada':
        return {
            'success': False, 'error': 'peticion_ya_procesada',
            'order_id_existente': peticion.get('order_id_revix'),
        }

    # Validación 1: contrato activo
    contrato = await db.aseguradoras_contratos.find_one(
        {'aseguradora_id': peticion.get('aseguradora_id'), 'activo': True},
        {'_id': 0},
    )
    if not contrato:
        # Registrar como pendiente_validacion + notificar
        await _marcar_pendiente_validacion(
            db, peticion, identity,
            motivo='aseguradora_sin_contrato_activo',
        )
        return {
            'success': False, 'error': 'aseguradora_sin_contrato_activo',
            'peticion_id': p.peticion_id,
            'accion': 'registrada como pendiente_validacion + notificación enviada',
        }

    # Validación 2: tipo de reparación en alcance del contrato
    tipo = peticion.get('tipo_reparacion')
    alcance = contrato.get('alcance_tipos_reparacion') or []
    if alcance and tipo not in alcance:
        await _marcar_pendiente_validacion(
            db, peticion, identity,
            motivo=f'tipo_reparacion_fuera_de_alcance:{tipo}',
        )
        return {
            'success': False, 'error': 'tipo_reparacion_fuera_alcance',
            'tipo_solicitado': tipo, 'tipos_permitidos': alcance,
            'peticion_id': p.peticion_id,
        }

    # Validación 3: importe estimado dentro del límite autorizado
    importe = float(peticion.get('importe_estimado') or 0)
    limite = float(contrato.get('limite_importe_autorizado') or 0)
    if limite > 0 and importe > limite:
        await _marcar_pendiente_validacion(
            db, peticion, identity,
            motivo=f'importe_excede_limite:{importe}>{limite}',
        )
        return {
            'success': False, 'error': 'importe_excede_limite_autorizado',
            'importe_estimado': importe, 'limite_autorizado': limite,
            'peticion_id': p.peticion_id,
        }

    # Crear orden
    now_iso = _now_iso()
    order_id = str(uuid.uuid4())
    fecha_corta = datetime.now(timezone.utc).strftime('%Y%m%d')
    numero_orden = f'OT-{fecha_corta}-{uuid.uuid4().hex[:8].upper()}'
    token = uuid.uuid4().hex[:12].upper()

    # Cliente: si no existe en `clientes`, crearlo on-the-fly desde la petición
    cliente_id = peticion.get('cliente_id')
    if not cliente_id:
        cliente_id = str(uuid.uuid4())
        await db.clientes.insert_one({
            'id': cliente_id,
            'nombre': (peticion.get('cliente_nombre') or 'Cliente').split(' ')[0],
            'apellidos': ' '.join((peticion.get('cliente_nombre') or '').split(' ')[1:]) or '',
            'email': peticion.get('cliente_email') or '',
            'telefono': peticion.get('cliente_telefono') or '',
            'tipo_cliente': 'seguro',
            'created_at': now_iso, 'updated_at': now_iso,
            'source': 'mcp_gestor_siniestros',
        })

    orden = {
        'id': order_id,
        'numero_orden': numero_orden,
        'numero_autorizacion': peticion.get('numero_autorizacion'),
        'token_seguimiento': token,
        'cliente_id': cliente_id,
        'dispositivo': peticion.get('dispositivo') or {},
        'estado': 'pendiente_recibir',
        'es_garantia': False,
        'es_siniestro': True,
        'siniestro_id_externo': peticion.get('siniestro_id_externo'),
        'aseguradora_id': peticion.get('aseguradora_id'),
        'peticion_origen_id': p.peticion_id,
        'tipo_servicio': 'seguro',
        'tipo_reparacion': tipo,
        'tecnico_asignado': p.tecnico_id,
        'fecha_estimada_entrega': p.fecha_estimada_entrega,
        'presupuesto_total': importe,
        'materiales': [],
        'sla_dias': contrato.get('sla_dias_reparacion', 7),
        'created_at': now_iso, 'updated_at': now_iso,
        'created_by': f'mcp:{identity.agent_id}',
        'source': 'mcp_agent',
    }
    await db.ordenes.insert_one(dict(orden))

    # Actualizar petición
    await db.siniestros_peticiones.update_one(
        {'id': p.peticion_id},
        {'$set': {
            'estado': 'orden_creada',
            'order_id_revix': order_id,
            'numero_orden': numero_orden,
            'updated_at': now_iso,
        }},
    )

    return {
        'success': True,
        'order_id': order_id,
        'numero_orden': numero_orden,
        'token_seguimiento': token,
        'peticion_id': p.peticion_id,
        'cliente_id': cliente_id,
        'tecnico_asignado': p.tecnico_id,
        'sla_dias': orden['sla_dias'],
    }


async def _marcar_pendiente_validacion(
    db: AsyncIOMotorDatabase, peticion: dict, identity: AgentIdentity, motivo: str,
) -> None:
    now_iso = _now_iso()
    await db.siniestros_peticiones.update_one(
        {'id': peticion['id']},
        {'$set': {
            'estado': 'pendiente_validacion',
            'motivo_pendiente': motivo,
            'updated_at': now_iso,
        }},
    )
    await db.notificaciones.insert_one({
        'id': str(uuid.uuid4()),
        'tipo': 'mcp_peticion_pendiente_validacion',
        'mensaje': (
            f'Petición siniestro {peticion.get("siniestro_id_externo") or peticion["id"]} '
            f'requiere validación manual: {motivo}'
        ),
        'peticion_id': peticion['id'],
        'destinatario_email': os.environ.get('MCP_FAILURE_NOTIFY_EMAIL', 'master@revix.es'),
        'leida': False,
        'created_at': now_iso,
        'source': 'mcp_agent',
        'agent_id': identity.agent_id,
    })


register(ToolSpec(
    name='crear_orden_desde_peticion',
    description=(
        'Crea una orden de siniestro a partir de una petición de aseguradora. '
        'Validaciones antes de crear: (1) contrato de la aseguradora activo, '
        '(2) tipo de reparación dentro del alcance del contrato, (3) importe '
        'estimado no supera límite autorizado. Si falla, la petición queda en '
        'pendiente_validacion y se notifica al responsable. Idempotency key: '
        'orden_siniestro_{peticion_id}.'
    ),
    required_scope='insurance:ops',
    input_schema={
        'type': 'object',
        'properties': {
            'peticion_id': {'type': 'string'},
            'tecnico_id': {'type': 'string'},
            'fecha_estimada_entrega': {'type': 'string'},
            '_idempotency_key': {'type': 'string',
                                 'description': 'Obligatorio. Formato: orden_siniestro_{peticion_id}'},
        },
        'required': ['peticion_id', 'tecnico_id', 'fecha_estimada_entrega', '_idempotency_key'],
        'additionalProperties': False,
    },
    handler=_crear_orden_desde_peticion_handler,
    writes=True,
))


# ──────────────────────────────────────────────────────────────────────────────
# 3 · actualizar_portal_insurama
# ──────────────────────────────────────────────────────────────────────────────

_ESTADOS_PORTAL = {
    'orden_creada', 'diagnostico_listo', 'reparando',
    'reparado', 'entregado', 'irreparable', 'cancelado',
}


class ActualizarPortalInput(BaseModel):
    siniestro_id_externo: str = Field(..., min_length=1)
    estado_nuevo: str = Field(..., min_length=1)
    order_id_revix: str = Field(..., min_length=1)
    comentario: Optional[str] = None
    fecha_estimada: Optional[str] = None


async def _actualizar_portal_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(ActualizarPortalInput, params)
    if p.estado_nuevo not in _ESTADOS_PORTAL:
        return {
            'success': False, 'error': 'estado_invalido',
            'estados_validos': sorted(_ESTADOS_PORTAL),
        }

    now_iso = _now_iso()
    preview = MCP_ENV == 'preview'

    doc = {
        'id': str(uuid.uuid4()),
        'siniestro_id_externo': p.siniestro_id_externo,
        'order_id_revix': p.order_id_revix,
        'estado_nuevo': p.estado_nuevo,
        'comentario': p.comentario,
        'fecha_estimada': p.fecha_estimada,
        'mock_preview': preview,
        'created_at': now_iso,
        'agent_id': identity.agent_id,
        'source': 'mcp_agent',
    }
    await db.mcp_insurama_updates.insert_one(dict(doc))

    if preview:
        return {
            'success': True,
            'preview': True,
            'update_id': doc['id'],
            'message': '[PREVIEW] Portal Insurama NO actualizado. Traza guardada.',
            'estado_enviado': p.estado_nuevo,
            'siniestro_id_externo': p.siniestro_id_externo,
        }

    # En production: aquí iría la integración real con el SOAP/REST de Insurama
    # Placeholder: marcar el doc como "pendiente de envío real"
    await db.mcp_insurama_updates.update_one(
        {'id': doc['id']},
        {'$set': {'estado_envio': 'pendiente_integracion_real'}},
    )
    return {
        'success': True,
        'preview': False,
        'update_id': doc['id'],
        'message': 'Actualización encolada (integración real pendiente de configurar).',
        'estado_enviado': p.estado_nuevo,
    }


register(ToolSpec(
    name='actualizar_portal_insurama',
    description=(
        'Actualiza el estado de un siniestro en el portal Insurama. En preview '
        'NO hace la llamada real (mock con traza en mcp_insurama_updates). '
        'Estados válidos: orden_creada|diagnostico_listo|reparando|reparado|'
        'entregado|irreparable|cancelado.'
    ),
    required_scope='insurance:ops',
    input_schema={
        'type': 'object',
        'properties': {
            'siniestro_id_externo': {'type': 'string'},
            'estado_nuevo': {'type': 'string'},
            'order_id_revix': {'type': 'string'},
            'comentario': {'type': 'string'},
            'fecha_estimada': {'type': 'string'},
            '_idempotency_key': {'type': 'string'},
        },
        'required': ['siniestro_id_externo', 'estado_nuevo', 'order_id_revix'],
        'additionalProperties': False,
    },
    handler=_actualizar_portal_handler,
    writes=True,
))


# ──────────────────────────────────────────────────────────────────────────────
# 4 · subir_evidencias
# ──────────────────────────────────────────────────────────────────────────────

class SubirEvidenciasInput(BaseModel):
    siniestro_id: str
    tipo_evidencia: Literal['diagnostico', 'reparacion', 'entrega']
    archivo_ids: list[str] = Field(..., min_length=1)


async def _subir_evidencias_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(SubirEvidenciasInput, params)
    now_iso = _now_iso()
    ev_id = str(uuid.uuid4())
    await db.siniestros_evidencias.insert_one({
        'id': ev_id,
        'siniestro_id': p.siniestro_id,
        'tipo_evidencia': p.tipo_evidencia,
        'archivo_ids': p.archivo_ids,
        'created_at': now_iso,
        'created_by': f'mcp:{identity.agent_id}',
        'source': 'mcp_agent',
    })
    return {
        'success': True,
        'evidencia_id': ev_id,
        'siniestro_id': p.siniestro_id,
        'tipo_evidencia': p.tipo_evidencia,
        'archivos_count': len(p.archivo_ids),
    }


register(ToolSpec(
    name='subir_evidencias',
    description=(
        'Registra evidencias (diagnostico|reparacion|entrega) asociadas a un '
        'siniestro. archivo_ids deben existir ya en el storage (Cloudinary).'
    ),
    required_scope='insurance:ops',
    input_schema={
        'type': 'object',
        'properties': {
            'siniestro_id': {'type': 'string'},
            'tipo_evidencia': {'type': 'string',
                               'enum': ['diagnostico', 'reparacion', 'entrega']},
            'archivo_ids': {'type': 'array', 'minItems': 1, 'items': {'type': 'string'}},
            '_idempotency_key': {'type': 'string'},
        },
        'required': ['siniestro_id', 'tipo_evidencia', 'archivo_ids'],
        'additionalProperties': False,
    },
    handler=_subir_evidencias_handler,
    writes=True,
))


# ──────────────────────────────────────────────────────────────────────────────
# 5 · cerrar_siniestro
# ──────────────────────────────────────────────────────────────────────────────

class CerrarSiniestroInput(BaseModel):
    siniestro_id: str
    order_id: str
    resultado: Literal['reparado', 'irreparable', 'no_cubierto']


async def _cerrar_siniestro_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require_scopes(identity, 'orders:write')
    p = validate_input(CerrarSiniestroInput, params)

    # Verificar evidencias subidas (al menos 1 de entrega si resultado=reparado)
    evidencias = await db.siniestros_evidencias.find(
        {'siniestro_id': p.siniestro_id}, {'_id': 0, 'tipo_evidencia': 1},
    ).to_list(50)
    tipos_evidencia = {e['tipo_evidencia'] for e in evidencias}
    if p.resultado == 'reparado' and 'entrega' not in tipos_evidencia:
        return {
            'success': False, 'error': 'falta_evidencia_entrega',
            'message': 'Para cerrar como reparado se requiere al menos evidencia de entrega.',
            'evidencias_actuales': sorted(tipos_evidencia),
        }
    if not evidencias:
        return {
            'success': False, 'error': 'sin_evidencias',
            'message': 'No hay ninguna evidencia subida para este siniestro.',
        }

    # Verificar actualización de portal final
    estado_portal_final = {
        'reparado': 'reparado', 'irreparable': 'irreparable', 'no_cubierto': 'cancelado',
    }[p.resultado]
    ultima_update = await db.mcp_insurama_updates.find_one(
        {'order_id_revix': p.order_id},
        {'_id': 0, 'estado_nuevo': 1}, sort=[('created_at', -1)],
    )
    if not ultima_update or ultima_update.get('estado_nuevo') != estado_portal_final:
        return {
            'success': False, 'error': 'portal_no_actualizado',
            'message': (
                f'Antes de cerrar, actualiza el portal Insurama al estado '
                f'"{estado_portal_final}". Último estado enviado: '
                f'{ultima_update.get("estado_nuevo") if ultima_update else "ninguno"}.'
            ),
        }

    now_iso = _now_iso()
    referencia_liquidacion = f'LIQ-{datetime.now(timezone.utc).strftime("%Y%m")}-{uuid.uuid4().hex[:6].upper()}'
    await db.ordenes.update_one(
        {'id': p.order_id},
        {'$set': {
            'estado': 'enviado' if p.resultado == 'reparado' else 'no_reparable',
            'siniestro_resultado': p.resultado,
            'siniestro_cerrado_en': now_iso,
            'referencia_liquidacion': referencia_liquidacion,
            'updated_at': now_iso,
        }},
    )
    # Cerrar petición
    await db.siniestros_peticiones.update_one(
        {'siniestro_id_externo': p.siniestro_id},
        {'$set': {
            'estado': 'cerrado', 'cerrada_en': now_iso,
            'resultado_final': p.resultado,
        }},
    )

    return {
        'success': True,
        'siniestro_id': p.siniestro_id,
        'order_id': p.order_id,
        'resultado': p.resultado,
        'referencia_liquidacion': referencia_liquidacion,
        'cerrado_en': now_iso,
    }


register(ToolSpec(
    name='cerrar_siniestro',
    description=(
        'Cierra un siniestro. Validaciones antes de cerrar: al menos 1 evidencia '
        'subida (y si resultado=reparado, evidencia de entrega), último portal '
        'actualizado al estado final correspondiente. Devuelve referencia de liquidación.'
    ),
    required_scope='insurance:ops',
    input_schema={
        'type': 'object',
        'properties': {
            'siniestro_id': {'type': 'string'},
            'order_id': {'type': 'string'},
            'resultado': {'type': 'string', 'enum': ['reparado', 'irreparable', 'no_cubierto']},
            '_idempotency_key': {'type': 'string'},
        },
        'required': ['siniestro_id', 'order_id', 'resultado'],
        'additionalProperties': False,
    },
    handler=_cerrar_siniestro_handler,
    writes=True,
))

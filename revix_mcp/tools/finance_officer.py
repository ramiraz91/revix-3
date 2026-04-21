"""
Revix MCP · Tools Fase 2 — Agente Finance Officer.

4 tools:
  1. listar_facturas_pendientes_cobro    (read · finance:read)
  2. emitir_factura_orden                (write · idempotente · finance:bill)
  3. enviar_recordatorio_cobro           (write · idempotente · finance:dunning)
  4. calcular_modelo_303                 (read agregado · finance:fiscal_calc)

Colecciones reutilizadas:
  - facturas                   (ya existe en el CRM)
  - contabilidad_series        (numeración por año/tipo)
  - clientes, ordenes, compras, notificaciones
  - mcp_recordatorios_cobro    (nueva, para trazabilidad dunning)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..auth import AgentIdentity
from ..config import MCP_ENV
from ._registry import ToolSpec, register
from ._common import validate_input


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat(timespec='seconds')


def _parse_iso(v) -> Optional[datetime]:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None


# ──────────────────────────────────────────────────────────────────────────────
# 1 · listar_facturas_pendientes_cobro
# ──────────────────────────────────────────────────────────────────────────────

class ListarFacturasPendientesInput(BaseModel):
    antiguedad_minima_dias: int = Field(0, ge=0, le=3650)
    cliente_id: Optional[str] = None
    canal: Optional[Literal['particular', 'seguro', 'empresa', 'otros']] = None
    limit: int = Field(100, ge=1, le=500)


async def _listar_facturas_pendientes_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(ListarFacturasPendientesInput, params)
    now = _now()

    query: dict = {
        'tipo': 'venta',
        'estado': {'$in': ['emitida', 'vencida']},
        '$or': [
            {'pagada': {'$ne': True}},
            {'pendiente_cobro': {'$gt': 0}},
        ],
    }
    if p.cliente_id:
        query['cliente_id'] = p.cliente_id

    cursor = db.facturas.find(query, {
        '_id': 0, 'id': 1, 'numero': 1, 'fecha_emision': 1,
        'cliente_id': 1, 'cliente_nombre': 1, 'cliente_email': 1,
        'orden_id': 1, 'numero_orden': 1,
        'total': 1, 'pendiente_cobro': 1, 'estado': 1,
    }).sort('fecha_emision', 1).limit(p.limit)

    items: list[dict] = []
    async for f in cursor:
        emision = _parse_iso(f.get('fecha_emision'))
        dias = (now - emision).days if emision else 0
        if dias < p.antiguedad_minima_dias:
            continue

        # Canal requiere consulta al cliente
        cliente_doc = None
        if p.canal or not f.get('cliente_email'):
            cliente_doc = await db.clientes.find_one(
                {'id': f.get('cliente_id')},
                {'_id': 0, 'nombre': 1, 'apellidos': 1, 'email': 1,
                 'telefono': 1, 'tipo_cliente': 1, 'nif': 1, 'dni': 1, 'cif_empresa': 1},
            )
            if p.canal and cliente_doc and cliente_doc.get('tipo_cliente') != p.canal:
                continue

        f['dias_antiguedad'] = dias
        f['semaforo'] = 'verde' if dias < 15 else ('amarillo' if dias < 30 else 'rojo')
        if cliente_doc:
            f['cliente_contacto'] = {
                'email': cliente_doc.get('email') or f.get('cliente_email'),
                'telefono': cliente_doc.get('telefono'),
                'tipo_cliente': cliente_doc.get('tipo_cliente'),
                'nif': cliente_doc.get('nif') or cliente_doc.get('dni') or cliente_doc.get('cif_empresa'),
            }
        items.append(f)

    # Ya vienen ordenadas por fecha_emision asc (más antiguas primero)
    items.sort(key=lambda x: -x['dias_antiguedad'])

    total_pendiente = round(sum((i.get('pendiente_cobro') or i.get('total') or 0) for i in items), 2)
    return {
        'total_facturas': len(items),
        'total_pendiente_eur': total_pendiente,
        'resumen_semaforo': {
            'verde': sum(1 for i in items if i['semaforo'] == 'verde'),
            'amarillo': sum(1 for i in items if i['semaforo'] == 'amarillo'),
            'rojo': sum(1 for i in items if i['semaforo'] == 'rojo'),
        },
        'items': items,
    }


register(ToolSpec(
    name='listar_facturas_pendientes_cobro',
    description=(
        'Lista facturas de venta pendientes de cobro (estado emitida|vencida y '
        '`pendiente_cobro>0`). Ordenadas por antigüedad descendente. Incluye '
        'semáforo (verde <15d, amarillo 15-30d, rojo >30d) y datos de contacto '
        'del cliente. Filtros: antigüedad mínima, cliente_id, canal '
        '(particular|seguro|empresa|otros).'
    ),
    required_scope='finance:read',
    input_schema={
        'type': 'object',
        'properties': {
            'antiguedad_minima_dias': {'type': 'integer', 'minimum': 0, 'maximum': 3650, 'default': 0},
            'cliente_id': {'type': 'string'},
            'canal': {'type': 'string', 'enum': ['particular', 'seguro', 'empresa', 'otros']},
            'limit': {'type': 'integer', 'minimum': 1, 'maximum': 500, 'default': 100},
        },
        'additionalProperties': False,
    },
    handler=_listar_facturas_pendientes_handler,
))


# ──────────────────────────────────────────────────────────────────────────────
# 2 · emitir_factura_orden
# ──────────────────────────────────────────────────────────────────────────────

_ESTADOS_FACTURABLES = {'enviado', 'reparado', 'completada', 'entregada'}


class EmitirFacturaInput(BaseModel):
    order_id: str = Field(..., min_length=1)
    tipo_factura: Literal['normal', 'rectificativa'] = 'normal'
    serie_facturacion: str = Field('FV', min_length=1, max_length=10)
    factura_origen_id: Optional[str] = Field(
        None, description='Obligatorio si tipo=rectificativa',
    )


async def _emitir_factura_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(EmitirFacturaInput, params)
    now = _now()

    orden = await db.ordenes.find_one({'id': p.order_id}, {'_id': 0})
    if not orden:
        return {'success': False, 'error': 'order_not_found'}

    # Validación 1: estado facturable
    estado = orden.get('estado')
    if estado not in _ESTADOS_FACTURABLES:
        return {
            'success': False, 'error': 'estado_no_facturable',
            'message': f'Orden en estado "{estado}". Debe estar en {sorted(_ESTADOS_FACTURABLES)}.',
        }

    # Validación 2: totales y materiales
    total = (orden.get('presupuesto_total')
             or orden.get('total_factura')
             or 0)
    mano_obra = orden.get('mano_obra', 0) or 0
    materiales = orden.get('materiales') or []
    if (total or 0) <= 0 or (not materiales and mano_obra <= 0):
        return {
            'success': False, 'error': 'totales_incompletos',
            'message': 'La orden no tiene materiales ni mano de obra registrada, o el total es 0. Regístralos antes de emitir.',
        }

    # Validación 3: factura normal ya existente
    if p.tipo_factura == 'normal':
        existente = await db.facturas.find_one(
            {'tipo': 'venta', 'orden_id': p.order_id,
             'subtipo': {'$ne': 'rectificativa'}},
            {'_id': 0, 'id': 1, 'numero': 1, 'estado': 1},
        )
        if existente:
            return {
                'success': False, 'error': 'factura_ya_emitida',
                'message': 'Esta orden ya está facturada. Si hay que corregir, usa tipo_factura="rectificativa".',
                'factura_existente': existente,
            }

    # Validación 4: cliente completo
    cliente = await db.clientes.find_one(
        {'id': orden.get('cliente_id')},
        {'_id': 0, 'nombre': 1, 'apellidos': 1, 'email': 1, 'telefono': 1,
         'direccion': 1, 'dni': 1, 'nif': 1, 'cif_empresa': 1, 'tipo_cliente': 1},
    )
    if not cliente:
        return {'success': False, 'error': 'cliente_no_encontrado'}
    nif = cliente.get('nif') or cliente.get('dni') or cliente.get('cif_empresa')
    faltantes = []
    if not nif:
        faltantes.append('NIF/CIF')
    if not (cliente.get('direccion') or '').strip():
        faltantes.append('direccion')
    if faltantes:
        return {
            'success': False, 'error': 'cliente_datos_incompletos',
            'message': f'Faltan los siguientes datos del cliente: {", ".join(faltantes)}.',
            'faltantes': faltantes,
        }

    # Validación 5: rectificativa requiere origen
    if p.tipo_factura == 'rectificativa':
        if not p.factura_origen_id:
            return {
                'success': False, 'error': 'rectificativa_sin_origen',
                'message': 'Indica `factura_origen_id` de la factura a rectificar.',
            }
        origen = await db.facturas.find_one(
            {'id': p.factura_origen_id, 'tipo': 'venta'}, {'_id': 0, 'id': 1, 'numero': 1},
        )
        if not origen:
            return {'success': False, 'error': 'factura_origen_no_encontrada'}

    # Numeración
    serie = p.serie_facturacion.upper()
    año = now.year
    serie_key = {'tipo': 'factura_venta', 'año': año, 'serie': serie}
    doc_serie = await db.contabilidad_series.find_one(serie_key)
    siguiente = (doc_serie.get('ultimo_numero', 0) if doc_serie else 0) + 1
    prefijo = f'{serie}R' if p.tipo_factura == 'rectificativa' else serie
    numero_factura = f'{prefijo}-{año}-{siguiente:05d}'

    factura_id = str(uuid.uuid4())

    # Líneas desde materiales + mano de obra
    lineas = []
    for mat in materiales:
        cantidad = mat.get('cantidad', 1)
        precio = mat.get('precio_unitario', 0)
        lineas.append({
            'descripcion': mat.get('nombre', 'Material'),
            'cantidad': cantidad,
            'precio_unitario': precio,
            'iva_porcentaje': mat.get('iva', 21),
            'subtotal': round(cantidad * precio, 2),
        })
    if mano_obra > 0:
        lineas.append({
            'descripcion': 'Mano de obra',
            'cantidad': 1,
            'precio_unitario': mano_obra,
            'iva_porcentaje': 21,
            'subtotal': mano_obra,
        })

    factura_doc = {
        'id': factura_id,
        'tipo': 'venta',
        'subtipo': 'rectificativa' if p.tipo_factura == 'rectificativa' else 'normal',
        'serie': serie,
        'numero': numero_factura,
        'cliente_id': orden.get('cliente_id'),
        'cliente_nombre': f"{cliente.get('nombre', '')} {cliente.get('apellidos', '')}".strip(),
        'cliente_email': cliente.get('email'),
        'cliente_nif': nif,
        'cliente_direccion': cliente.get('direccion'),
        'orden_id': p.order_id,
        'numero_orden': orden.get('numero_orden'),
        'factura_origen_id': p.factura_origen_id,
        'fecha_emision': _now_iso(),
        'lineas': lineas,
        'base_imponible': orden.get('base_imponible') or total,
        'total_iva': orden.get('total_iva', 0),
        'total': total,
        'estado': 'emitida',
        'pendiente_cobro': total if p.tipo_factura == 'normal' else 0,
        'año_fiscal': año,
        'created_at': _now_iso(),
        'created_by': f'mcp:{identity.agent_id}',
        'source': 'mcp_agent',
    }
    await db.facturas.insert_one(dict(factura_doc))

    # Actualizar serie
    await db.contabilidad_series.update_one(
        serie_key, {'$set': {'ultimo_numero': siguiente}}, upsert=True,
    )

    # Marcar orden como facturada (si es normal)
    if p.tipo_factura == 'normal':
        await db.ordenes.update_one(
            {'id': p.order_id},
            {'$set': {'facturada': True, 'factura_id': factura_id, 'updated_at': _now_iso()}},
        )

    url_pdf = f'/api/finanzas/facturas/{factura_id}/pdf'

    return {
        'success': True,
        'factura_id': factura_id,
        'numero_factura': numero_factura,
        'tipo_factura': p.tipo_factura,
        'serie': serie,
        'total': total,
        'pendiente_cobro': factura_doc['pendiente_cobro'],
        'url_pdf': url_pdf,
        'cliente': {
            'nombre': factura_doc['cliente_nombre'],
            'nif': nif,
            'email': factura_doc['cliente_email'],
        },
        'fecha_emision': factura_doc['fecha_emision'],
    }


register(ToolSpec(
    name='emitir_factura_orden',
    description=(
        'Emite una factura (normal|rectificativa) para una orden. Valida ANTES '
        'de emitir: estado facturable (enviado/reparado/completada/entregada), '
        'materiales o mano de obra con total>0, no exista factura normal previa, '
        'cliente con NIF/CIF y dirección. Si falla, devuelve success=false sin '
        'emitir. Devuelve factura_id, número y url_pdf. Idempotency_key '
        'obligatorio (formato: `factura_{order_id}`).'
    ),
    required_scope='finance:bill',
    input_schema={
        'type': 'object',
        'properties': {
            'order_id': {'type': 'string'},
            'tipo_factura': {'type': 'string', 'enum': ['normal', 'rectificativa'], 'default': 'normal'},
            'serie_facturacion': {'type': 'string', 'minLength': 1, 'maxLength': 10, 'default': 'FV'},
            'factura_origen_id': {'type': 'string', 'description': 'Obligatorio si rectificativa'},
            '_idempotency_key': {'type': 'string', 'description': 'Obligatorio. Formato: factura_{order_id}'},
        },
        'required': ['order_id', 'tipo_factura', 'serie_facturacion', '_idempotency_key'],
        'additionalProperties': False,
    },
    handler=_emitir_factura_handler,
    writes=True,
))


# ──────────────────────────────────────────────────────────────────────────────
# 3 · enviar_recordatorio_cobro
# ──────────────────────────────────────────────────────────────────────────────

_ORDEN_SEVERIDAD = {'amistoso': 1, 'formal': 2, 'ultimo_aviso': 3}


class EnviarRecordatorioInput(BaseModel):
    factura_id: str
    tipo_recordatorio: Literal['amistoso', 'formal', 'ultimo_aviso']


async def _enviar_recordatorio_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    p = validate_input(EnviarRecordatorioInput, params)
    factura = await db.facturas.find_one(
        {'id': p.factura_id, 'tipo': 'venta'}, {'_id': 0},
    )
    if not factura:
        return {'success': False, 'error': 'factura_not_found'}
    if (factura.get('pendiente_cobro') or 0) <= 0:
        return {
            'success': False, 'error': 'factura_cobrada',
            'message': 'La factura ya no tiene importe pendiente.',
        }

    # Calcular antigüedad
    emision = _parse_iso(factura.get('fecha_emision'))
    dias = (_now() - emision).days if emision else 0

    # Tipo sugerido según antigüedad + verificación coherencia
    sugerido = 'amistoso' if dias < 15 else ('formal' if dias < 30 else 'ultimo_aviso')

    # Regla: ultimo_aviso requiere que haya al menos un recordatorio previo
    if p.tipo_recordatorio == 'ultimo_aviso':
        previos = await db.mcp_recordatorios_cobro.count_documents({
            'factura_id': p.factura_id,
        })
        if previos == 0:
            return {
                'success': False, 'error': 'ultimo_aviso_sin_previos',
                'message': 'No puedes enviar un "último aviso" sin recordatorio previo. Envía primero amistoso o formal.',
                'tipo_sugerido': sugerido,
                'dias_antiguedad': dias,
            }

    # Aviso si el tipo solicitado es demasiado agresivo para la antigüedad
    warning = None
    if _ORDEN_SEVERIDAD[p.tipo_recordatorio] > _ORDEN_SEVERIDAD[sugerido]:
        warning = (
            f'El tipo "{p.tipo_recordatorio}" es más severo que el sugerido '
            f'para {dias} días ({sugerido}). Sigue adelante solo si hay contexto especial.'
        )

    preview_mode = MCP_ENV == 'preview'
    asunto = {
        'amistoso': f'Recordatorio amistoso · Factura {factura.get("numero")}',
        'formal': f'Aviso formal · Factura {factura.get("numero")} pendiente',
        'ultimo_aviso': f'ÚLTIMO AVISO · Factura {factura.get("numero")}',
    }[p.tipo_recordatorio]

    mensaje = {
        'amistoso': (
            f'Hola {factura.get("cliente_nombre", "")}, te recordamos que la '
            f'factura {factura.get("numero")} por {factura.get("total")}€ emitida '
            f'el {factura.get("fecha_emision", "")[:10]} sigue pendiente de pago. '
            f'Si ya la has abonado, ignora este mensaje. ¡Gracias!'
        ),
        'formal': (
            f'Estimado/a {factura.get("cliente_nombre", "")}, le escribimos de '
            f'forma formal para comunicarle que la factura {factura.get("numero")} '
            f'por importe de {factura.get("total")}€ está pendiente desde hace {dias} días. '
            f'Le rogamos proceder al abono en los próximos 7 días.'
        ),
        'ultimo_aviso': (
            f'Sr./Sra. {factura.get("cliente_nombre", "")}: última comunicación '
            f'sobre la factura {factura.get("numero")} ({factura.get("total")}€) '
            f'pendiente desde hace {dias} días. Si no recibimos el pago en 7 días '
            f'naturales, procederemos por vía legal. Póngase en contacto urgente.'
        ),
    }[p.tipo_recordatorio]

    if preview_mode:
        mensaje = f'[PREVIEW] {mensaje}'

    now_iso = _now_iso()
    rec_id = str(uuid.uuid4())
    await db.mcp_recordatorios_cobro.insert_one({
        'id': rec_id,
        'factura_id': p.factura_id,
        'numero_factura': factura.get('numero'),
        'tipo_recordatorio': p.tipo_recordatorio,
        'cliente_id': factura.get('cliente_id'),
        'cliente_email': factura.get('cliente_email'),
        'dias_antiguedad_al_enviar': dias,
        'importe_pendiente': factura.get('pendiente_cobro'),
        'asunto': asunto,
        'mensaje': mensaje,
        'preview_mock': preview_mode,
        'created_at': now_iso,
        'created_by': f'mcp:{identity.agent_id}',
        'source': 'mcp_agent',
    })

    # En preview creamos también una notificación interna como traza
    await db.notificaciones.insert_one({
        'id': str(uuid.uuid4()),
        'tipo': 'mcp_recordatorio_cobro',
        'mensaje': f'{asunto}: {mensaje[:120]}...',
        'orden_id': factura.get('orden_id'),
        'factura_id': p.factura_id,
        'leida': False,
        'created_at': now_iso,
        'source': 'mcp_agent',
        'agent_id': identity.agent_id,
        'preview_mock': preview_mode,
    })

    return {
        'success': True,
        'preview': preview_mode,
        'recordatorio_id': rec_id,
        'factura_id': p.factura_id,
        'numero_factura': factura.get('numero'),
        'tipo_recordatorio': p.tipo_recordatorio,
        'tipo_sugerido_por_antiguedad': sugerido,
        'dias_antiguedad': dias,
        'warning': warning,
        'asunto': asunto,
        'mensaje_enviado': mensaje if preview_mode else mensaje[:200] + '...',
        'message': (
            f'[PREVIEW] Recordatorio NO enviado realmente. Traza guardada.'
            if preview_mode else
            'Recordatorio enviado correctamente.'
        ),
    }


register(ToolSpec(
    name='enviar_recordatorio_cobro',
    description=(
        'Envía un recordatorio de cobro (amistoso|formal|ultimo_aviso) a una '
        'factura pendiente. Regla: ultimo_aviso NO permitido si no hay recordatorio '
        'previo. Tipo sugerido automático según antigüedad (<15d amistoso, 15-30d '
        'formal, >30d último_aviso). En MCP_ENV=preview solo registra traza. '
        'Idempotency_key: `recordatorio_{factura_id}_{tipo}`.'
    ),
    required_scope='finance:dunning',
    input_schema={
        'type': 'object',
        'properties': {
            'factura_id': {'type': 'string'},
            'tipo_recordatorio': {'type': 'string', 'enum': ['amistoso', 'formal', 'ultimo_aviso']},
            '_idempotency_key': {'type': 'string', 'description': 'Obligatorio. Formato: recordatorio_{factura_id}_{tipo}'},
        },
        'required': ['factura_id', 'tipo_recordatorio', '_idempotency_key'],
        'additionalProperties': False,
    },
    handler=_enviar_recordatorio_handler,
    writes=True,
))


# ──────────────────────────────────────────────────────────────────────────────
# 4 · calcular_modelo_303
# ──────────────────────────────────────────────────────────────────────────────

class CalcularModelo303Input(BaseModel):
    trimestre: int = Field(..., ge=1, le=4)
    anno: int = Field(..., ge=2000, le=2100, alias='año')

    model_config = {'populate_by_name': True}


def _rango_trimestre(anno: int, trim: int) -> tuple[str, str]:
    inicio_mes = (trim - 1) * 3 + 1
    inicio = datetime(anno, inicio_mes, 1, tzinfo=timezone.utc)
    if trim == 4:
        fin = datetime(anno + 1, 1, 1, tzinfo=timezone.utc)
    else:
        fin = datetime(anno, inicio_mes + 3, 1, tzinfo=timezone.utc)
    fin = fin - timedelta(seconds=1)
    return inicio.isoformat(), fin.isoformat()


async def _modelo_303_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    # Acepta tanto 'anno' como 'año' (alias) para retrocompatibilidad
    if 'año' in params and 'anno' not in params:
        params = dict(params)
        params['anno'] = params.pop('año')
    p = validate_input(CalcularModelo303Input, params)
    inicio, fin = _rango_trimestre(p.anno, p.trimestre)

    # IVA repercutido (ventas)
    ventas_cursor = db.facturas.aggregate([
        {'$match': {
            'tipo': 'venta',
            'estado': {'$in': ['emitida', 'cobrada', 'vencida']},
            'fecha_emision': {'$gte': inicio, '$lte': fin},
        }},
        {'$group': {
            '_id': None,
            'base': {'$sum': {'$ifNull': ['$base_imponible', 0]}},
            'iva': {'$sum': {'$ifNull': ['$total_iva', 0]}},
            'count': {'$sum': 1},
        }},
    ])
    v_docs = [d async for d in ventas_cursor]
    base_ventas = float(v_docs[0]['base']) if v_docs else 0.0
    iva_repercutido = float(v_docs[0]['iva']) if v_docs else 0.0
    n_ventas = int(v_docs[0]['count']) if v_docs else 0

    # IVA soportado deducible (compras)
    compras_cursor = db.facturas.aggregate([
        {'$match': {
            'tipo': 'compra',
            'fecha_emision': {'$gte': inicio, '$lte': fin},
        }},
        {'$group': {
            '_id': None,
            'base': {'$sum': {'$ifNull': ['$base_imponible', 0]}},
            'iva': {'$sum': {'$ifNull': ['$total_iva', 0]}},
            'count': {'$sum': 1},
        }},
    ])
    c_docs = [d async for d in compras_cursor]
    base_compras = float(c_docs[0]['base']) if c_docs else 0.0
    iva_soportado = float(c_docs[0]['iva']) if c_docs else 0.0
    n_compras = int(c_docs[0]['count']) if c_docs else 0

    resultado = round(iva_repercutido - iva_soportado, 2)
    tipo_resultado = 'a_ingresar' if resultado > 0 else ('a_devolver' if resultado < 0 else 'cero')

    return {
        'trimestre': p.trimestre,
        'año': p.anno,
        'anno': p.anno,
        'periodo': {'inicio': inicio, 'fin': fin},
        'ventas': {
            'num_facturas': n_ventas,
            'base_imponible': round(base_ventas, 2),
            'iva_repercutido': round(iva_repercutido, 2),
        },
        'compras': {
            'num_facturas': n_compras,
            'base_imponible_deducible': round(base_compras, 2),
            'iva_soportado_deducible': round(iva_soportado, 2),
        },
        'resultado': {
            'tipo': tipo_resultado,
            'importe': abs(resultado),
            'signo': 'positivo (a ingresar)' if resultado > 0 else (
                'negativo (a devolver)' if resultado < 0 else 'neutro'),
            'importe_con_signo': resultado,
        },
        'aviso_legal': (
            '⚠ Este cálculo es una estimación automática basada en las facturas '
            'registradas en el sistema. Requiere revisión y presentación por el '
            'asesor fiscal antes de su presentación ante la AEAT (Modelo 303).'
        ),
    }


register(ToolSpec(
    name='calcular_modelo_303',
    description=(
        'Calcula el Modelo 303 (IVA trimestral) a partir de las facturas '
        'registradas en el sistema. Devuelve: base imponible y cuotas de IVA '
        'repercutido (ventas) y soportado deducible (compras), y el resultado '
        '(a ingresar | a devolver | cero). SIEMPRE incluye aviso legal de que '
        'requiere revisión y presentación por el asesor fiscal.'
    ),
    required_scope='finance:fiscal_calc',
    input_schema={
        'type': 'object',
        'properties': {
            'trimestre': {'type': 'integer', 'minimum': 1, 'maximum': 4},
            'anno': {'type': 'integer', 'minimum': 2000, 'maximum': 2100,
                     'description': 'Año (usa `anno` en lugar de `año` por compatibilidad API)'},
        },
        'required': ['trimestre', 'anno'],
        'additionalProperties': False,
    },
    handler=_modelo_303_handler,
))

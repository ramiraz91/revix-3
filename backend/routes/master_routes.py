"""
Rutas de Master: métricas de técnicos, facturación, ISO, analíticas, finanzas.
Extraído de server.py durante refactorización.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime, timezone, timedelta
import csv
import io
import math
import random

from config import db, EMERGENT_LLM_KEY, logger
import config as cfg
from auth import require_auth, require_admin, require_master
from models import OrderStatus

router = APIRouter(tags=["master"])

@router.get("/master/metricas-tecnicos")
async def obtener_metricas_tecnicos(user: dict = Depends(require_master)):
    tecnicos = await db.users.find({"role": "tecnico"}, {"_id": 0, "password_hash": 0}).to_list(100)
    metricas = []
    for t in tecnicos:
        ordenes = await db.ordenes.find({"tecnico_asignado": t['id']}, {"_id": 0}).to_list(1000)
        completadas = len([o for o in ordenes if o.get('estado') == 'enviado'])
        metricas.append({"tecnico_id": t['id'], "nombre": t['nombre'], "total_ordenes": len(ordenes), "completadas": completadas, "garantias": len([o for o in ordenes if o.get('es_garantia')]), "en_proceso": len([o for o in ordenes if o.get('estado') in ['en_taller', 'reparado', 'validacion']]), "irreparables": len([o for o in ordenes if o.get('estado') == 'irreparable']), "tasa_exito": round((completadas / len(ordenes) * 100) if ordenes else 0, 1)})
    return metricas

@router.get("/master/facturacion")
async def obtener_facturacion(user: dict = Depends(require_master), fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None):
    query = {"estado": "enviado"}
    if fecha_desde:
        query["fecha_enviado"] = {"$gte": fecha_desde}
    if fecha_hasta:
        if "fecha_enviado" in query:
            query["fecha_enviado"]["$lte"] = fecha_hasta
        else:
            query["fecha_enviado"] = {"$lte": fecha_hasta}
    ordenes = await db.ordenes.find(query, {"_id": 0}).to_list(5000)
    config_empresa = await db.configuracion.find_one({"tipo": "empresa"}, {"_id": 0})
    iva_defecto = config_empresa.get("datos", {}).get("iva_por_defecto", 21.0) if config_empresa else 21.0
    total_materiales = sum(m.get('precio_unitario', 0) * m.get('cantidad', 1) for o in ordenes for m in o.get('materiales', []))
    subtotal = total_materiales
    iva = subtotal * (iva_defecto / 100)
    return {
        "periodo": {"desde": fecha_desde, "hasta": fecha_hasta},
        "ordenes_facturadas": len(ordenes),
        "desglose": {
            "materiales": round(total_materiales, 2),
            "mano_obra": 0,
            "subtotal": round(subtotal, 2),
            "iva_porcentaje": iva_defecto,
            "iva_importe": round(iva, 2),
            "total": round(subtotal + iva, 2),
        },
    }



def _parse_dt_safe(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None


@router.get("/master/iso/documentos")
async def obtener_iso_documentos(user: dict = Depends(require_master)):
    documentos = await db.iso_documentos.find({}, {"_id": 0}).sort("codigo", 1).to_list(500)
    return documentos


@router.post("/master/iso/documentos")
async def guardar_iso_documento(data: dict, user: dict = Depends(require_master)):
    codigo = (data.get("codigo") or "").strip().upper()
    titulo = (data.get("titulo") or "").strip()
    tipo = (data.get("tipo") or "").strip().lower()

    if not codigo or not titulo or tipo not in {"documento", "registro"}:
        raise HTTPException(status_code=400, detail="codigo, titulo y tipo(documento/registro) son obligatorios")

    now = datetime.now(timezone.utc).isoformat()
    existing = await db.iso_documentos.find_one({"codigo": codigo}, {"_id": 0})

    payload = {
        "codigo": codigo,
        "titulo": titulo,
        "tipo": tipo,
        "version": data.get("version") or "1.0",
        "estado": data.get("estado") or "vigente",
        "aprobado_por": data.get("aprobado_por") or user.get("email"),
        "retencion_anios": int(data.get("retencion_anios") or 3),
        "proceso": data.get("proceso") or "sgc",
        "clausulas_iso": data.get("clausulas_iso") or [],
        "observaciones": data.get("observaciones"),
        "updated_at": now,
        "updated_by": user.get("email"),
    }

    if existing:
        await db.iso_documentos.update_one({"codigo": codigo}, {"$set": payload})
    else:
        payload["created_at"] = now
        payload["created_by"] = user.get("email")
        await db.iso_documentos.insert_one(payload)

    return await db.iso_documentos.find_one({"codigo": codigo}, {"_id": 0})


@router.get("/master/iso/proveedores")
async def obtener_iso_proveedores(user: dict = Depends(require_master)):
    evaluaciones = await db.iso_proveedores_evaluacion.find({}, {"_id": 0}).sort("proveedor", 1).to_list(500)

    # Semillas mínimas para proveedores críticos ya usados por el negocio
    semillas = ["GLS", "MobileSentrix", "Utopya"]
    existentes = {e.get("proveedor") for e in evaluaciones}
    now = datetime.now(timezone.utc).isoformat()

    for nombre in semillas:
        if nombre not in existentes:
            doc = {
                "proveedor": nombre,
                "tipo": "logistica" if nombre == "GLS" else "recambios",
                "estado": "pendiente",
                "score": None,
                "ultima_evaluacion": None,
                "proxima_reevaluacion": None,
                "incidencias": 0,
                "comentarios": None,
                "created_at": now,
                "updated_at": now,
            }
            await db.iso_proveedores_evaluacion.insert_one(doc)
            evaluaciones.append(doc)

    cleaned = []
    for ev in evaluaciones:
        ev_clean = dict(ev)
        ev_clean.pop("_id", None)
        for key, value in list(ev_clean.items()):
            if isinstance(value, ObjectId):
                ev_clean[key] = str(value)
        cleaned.append(ev_clean)

    return sorted(cleaned, key=lambda x: x.get("proveedor", ""))


@router.post("/master/iso/proveedores/evaluar")
async def evaluar_iso_proveedor(data: dict, user: dict = Depends(require_master)):
    proveedor = (data.get("proveedor") or "").strip()
    if not proveedor:
        raise HTTPException(status_code=400, detail="proveedor es obligatorio")

    puntualidad = float(data.get("puntualidad") or 0)
    calidad = float(data.get("calidad") or 0)
    respuesta = float(data.get("respuesta") or 0)
    incidencias = float(data.get("incidencias") or 0)

    score = round((puntualidad + calidad + respuesta + (100 - incidencias)) / 4, 1)
    estado = "aprobado" if score >= 75 else "condicional" if score >= 60 else "bloqueado"

    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    proxima = (now_dt + timedelta(days=90)).date().isoformat()

    payload = {
        "proveedor": proveedor,
        "tipo": data.get("tipo") or "recambios",
        "puntualidad": puntualidad,
        "calidad": calidad,
        "respuesta": respuesta,
        "incidencias": incidencias,
        "score": score,
        "estado": estado,
        "ultima_evaluacion": now,
        "proxima_reevaluacion": data.get("proxima_reevaluacion") or proxima,
        "comentarios": data.get("comentarios"),
        "updated_at": now,
        "updated_by": user.get("email"),
    }

    await db.iso_proveedores_evaluacion.update_one(
        {"proveedor": proveedor},
        {"$set": payload, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return await db.iso_proveedores_evaluacion.find_one({"proveedor": proveedor}, {"_id": 0})


@router.get("/master/iso/kpis")
async def obtener_kpis_iso(user: dict = Depends(require_master)):
    ordenes = await db.ordenes.find({}, {"_id": 0}).to_list(10000)

    enviados = [o for o in ordenes if o.get("estado") == "enviado"]
    total_enviados = len(enviados)
    garantias = [o for o in ordenes if o.get("es_garantia")]
    total_garantias = len(garantias)

    retrabajo_pct = round((total_garantias / total_enviados * 100), 2) if total_enviados else 0
    reparaciones_sin_retrabajo_pct = round(100 - retrabajo_pct, 2) if total_enviados else 0

    tat_horas = []
    entregas_a_tiempo = 0
    entregas_con_sla = 0

    for o in enviados:
        created_at = _parse_dt_safe(o.get("created_at"))
        fecha_enviado = _parse_dt_safe(o.get("fecha_enviado"))
        if created_at and fecha_enviado:
            tat_horas.append((fecha_enviado - created_at).total_seconds() / 3600)

        fecha_estimada = _parse_dt_safe(o.get("fecha_estimada_entrega"))
        if fecha_estimada and fecha_enviado:
            entregas_con_sla += 1
            if fecha_enviado <= fecha_estimada:
                entregas_a_tiempo += 1

    tat_promedio_horas = round(sum(tat_horas) / len(tat_horas), 2) if tat_horas else None
    entregas_a_tiempo_pct = round((entregas_a_tiempo / entregas_con_sla) * 100, 2) if entregas_con_sla else None

    qc_fallos = len([o for o in ordenes if o.get("estado") == "validacion" and not (o.get("diagnostico_salida_realizado") and o.get("funciones_verificadas") and o.get("limpieza_realizada"))])
    first_pass_yield_pct = round(((total_enviados - total_garantias) / total_enviados) * 100, 2) if total_enviados else 0

    incidencias = await db.incidencias.find({}, {"_id": 0, "tipo": 1, "estado": 1}).to_list(5000)
    reclamaciones = [i for i in incidencias if i.get("tipo") == "reclamacion"]
    csat_proxy = round(max(0, 100 - (len(reclamaciones) / total_enviados * 100)), 2) if total_enviados else None

    proveedores = await db.iso_proveedores_evaluacion.find({}, {"_id": 0, "proveedor": 1, "score": 1, "estado": 1, "incidencias": 1}).to_list(200)

    return {
        "kpis": {
            "reparaciones_sin_retrabajo_pct": reparaciones_sin_retrabajo_pct,
            "tat_promedio_horas": tat_promedio_horas,
            "entregas_a_tiempo_pct": entregas_a_tiempo_pct,
            "qc_fallos": qc_fallos,
            "first_pass_yield_pct": first_pass_yield_pct,
            "devoluciones_garantias_pct": retrabajo_pct,
            "satisfaccion_cliente_proxy_pct": csat_proxy,
        },
        "proveedores": proveedores,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }



async def _collect_audit_pack_for_order(order_doc: dict) -> dict:
    orden_id = order_doc.get("id")
    eventos = await db.ot_event_log.find({"ot_id": orden_id}, {"_id": 0}).sort("created_at", 1).to_list(5000)
    consentimientos = await db.consentimientos_seguimiento.find({"orden_id": orden_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
    incidencias = await db.incidencias.find({"orden_id": orden_id}, {"_id": 0}).sort("created_at", -1).to_list(200)

    return {
        "ot": {
            "id": order_doc.get("id"),
            "numero_orden": order_doc.get("numero_orden"),
            "numero_autorizacion": order_doc.get("numero_autorizacion"),
            "estado": order_doc.get("estado"),
            "cliente_id": order_doc.get("cliente_id"),
            "dispositivo": order_doc.get("dispositivo"),
            "created_at": order_doc.get("created_at"),
            "updated_at": order_doc.get("updated_at"),
            "historial_estados": order_doc.get("historial_estados", []),
            "ri": {
                "obligatoria": bool(order_doc.get("ri_obligatoria")),
                "completada": bool(order_doc.get("ri_completada")),
                "resultado": order_doc.get("ri_resultado"),
                "fecha": order_doc.get("ri_fecha"),
                "usuario": order_doc.get("ri_usuario"),
                "fotos_count": len(order_doc.get("ri_fotos_recepcion", []) or []),
            },
            "qc": {
                "diagnostico_salida_realizado": bool(order_doc.get("diagnostico_salida_realizado")),
                "funciones_verificadas": bool(order_doc.get("funciones_verificadas")),
                "limpieza_realizada": bool(order_doc.get("limpieza_realizada")),
            },
            "bateria": {
                "reemplazada": bool(order_doc.get("bateria_reemplazada")),
                "almacenamiento_temporal": bool(order_doc.get("bateria_almacenamiento_temporal")),
                "residuo_pendiente": bool(order_doc.get("bateria_residuo_pendiente")),
                "gestor": order_doc.get("bateria_gestor_autorizado"),
                "fecha_entrega_gestor": order_doc.get("bateria_fecha_entrega_gestor"),
            },
            "cpi": {
                "requiere_borrado": order_doc.get("cpi_requiere_borrado"),
                "metodo": order_doc.get("cpi_metodo"),
                "resultado": order_doc.get("cpi_resultado"),
                "fecha": order_doc.get("cpi_fecha"),
            },
            "flash": {
                "aplica": order_doc.get("flash_aplica"),
                "version": order_doc.get("flash_version"),
                "herramienta": order_doc.get("flash_herramienta"),
                "resultado": order_doc.get("flash_resultado"),
            },
            "evidencias_count": len(order_doc.get("evidencias", []) or []),
            "evidencias_tecnico_count": len(order_doc.get("evidencias_tecnico", []) or []),
        },
        "event_log": eventos,
        "consentimientos": consentimientos,
        "incidencias": incidencias,
    }


@router.get("/master/iso/audit-pack/ot/{orden_id}")
async def obtener_audit_pack_ot(orden_id: str, user: dict = Depends(require_master)):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="OT no encontrada")
    pack = await _collect_audit_pack_for_order(orden)
    await _registrar_evento_seguridad(user, 'audit_pack_ot_export', {'orden_id': orden_id})
    return pack


@router.get("/master/iso/audit-pack/periodo")
async def obtener_audit_pack_periodo(
    user: dict = Depends(require_master),
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    query = {}
    if fecha_desde or fecha_hasta:
        query["created_at"] = {}
        if fecha_desde:
            query["created_at"]["$gte"] = fecha_desde
        if fecha_hasta:
            query["created_at"]["$lte"] = fecha_hasta

    ordenes = await db.ordenes.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    items = []
    for o in ordenes:
        items.append(await _collect_audit_pack_for_order(o))

    payload = {
        "periodo": {"desde": fecha_desde, "hasta": fecha_hasta},
        "total_ots": len(items),
        "items": items,
    }
    await _registrar_evento_seguridad(user, 'audit_pack_periodo_export', {'desde': fecha_desde, 'hasta': fecha_hasta, 'total_ots': len(items)})
    return payload


@router.get("/master/iso/audit-pack/periodo/csv")
async def exportar_audit_pack_csv(
    user: dict = Depends(require_master),
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    query = {}
    if fecha_desde or fecha_hasta:
        query["created_at"] = {}
        if fecha_desde:
            query["created_at"]["$gte"] = fecha_desde
        if fecha_hasta:
            query["created_at"]["$lte"] = fecha_hasta

    ordenes = await db.ordenes.find(query, {"_id": 0}).sort("created_at", -1).to_list(5000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ot_id",
        "numero_orden",
        "estado",
        "created_at",
        "ri_completada",
        "ri_resultado",
        "qc_ok",
        "consentimientos",
        "eventos_auditoria",
        "incidencias",
        "capa_abiertas",
    ])

    for o in ordenes:
        orden_id = o.get("id")
        consent_count = await db.consentimientos_seguimiento.count_documents({"orden_id": orden_id})
        event_count = await db.ot_event_log.count_documents({"ot_id": orden_id})
        incidencias = await db.incidencias.find({"orden_id": orden_id}, {"_id": 0, "capa_estado": 1}).to_list(200)
        capa_abiertas = len([i for i in incidencias if i.get("capa_estado") in {"abierta", "en_progreso", "en_seguimiento"}])
        qc_ok = bool(o.get("diagnostico_salida_realizado") and o.get("funciones_verificadas") and o.get("limpieza_realizada"))

        writer.writerow([
            orden_id,
            o.get("numero_orden"),
            o.get("estado"),
            o.get("created_at"),
            bool(o.get("ri_completada")),
            o.get("ri_resultado"),
            qc_ok,
            consent_count,
            event_count,
            len(incidencias),
            capa_abiertas,
        ])

    csv_bytes = io.BytesIO(output.getvalue().encode("utf-8"))
    await _registrar_evento_seguridad(user, 'audit_pack_periodo_csv_export', {'desde': fecha_desde, 'hasta': fecha_hasta, 'total_ots': len(ordenes)})
    headers = {"Content-Disposition": "attachment; filename=audit_pack_periodo.csv"}
    return StreamingResponse(csv_bytes, media_type="text/csv", headers=headers)






@router.get('/master/iso/capa-dashboard')
async def obtener_dashboard_capa(user: dict = Depends(require_master)):
    capas = await db.capas.find({}, {'_id': 0}).to_list(5000)
    total = len(capas)
    por_estado = {}
    por_motivo = {}
    abiertas_antiguas = 0
    limite_antiguedad = datetime.now(timezone.utc) - timedelta(days=30)

    for c in capas:
        estado = c.get('estado') or 'abierta'
        por_estado[estado] = por_estado.get(estado, 0) + 1

        motivo = c.get('motivo_apertura') or 'sin_motivo'
        por_motivo[motivo] = por_motivo.get(motivo, 0) + 1

        created_at = _parse_dt_safe(c.get('created_at'))
        if estado in {'abierta', 'en_curso', 'implementada', 'en_seguimiento'} and created_at and created_at < limite_antiguedad:
            abiertas_antiguas += 1

    return {
        'total_capas': total,
        'por_estado': por_estado,
        'por_motivo': por_motivo,
        'abiertas_antiguedad_30d': abiertas_antiguas,
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }

async def _registrar_evento_seguridad(user: dict, accion: str, detalle: dict):
    evento = {
        'id': str(uuid.uuid4()),
        'accion': accion,
        'usuario': user.get('email'),
        'role': user.get('role'),
        'detalle': detalle,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.seguridad_eventos.insert_one(evento)


@router.get("/master/iso/qa-config")
async def obtener_config_qa_iso(user: dict = Depends(require_master)):
    cfg = await db.iso_qa_config.find_one({'id': 'default'}, {'_id': 0})
    if not cfg:
        cfg = {
            'id': 'default',
            'porcentaje_diario': 10,
            'minimo_muestras': 1,
            'escalado_por_fallo_porcentaje': 20,
            'escalado_dias': 7,
            'escalado_hasta': None,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.iso_qa_config.insert_one(cfg)
    return cfg


@router.post("/master/iso/qa-config")
async def guardar_config_qa_iso(data: dict, user: dict = Depends(require_master)):
    cfg = await obtener_config_qa_iso(user)
    now = datetime.now(timezone.utc).isoformat()

    update = {
        'porcentaje_diario': int(data.get('porcentaje_diario', cfg.get('porcentaje_diario', 10))),
        'minimo_muestras': int(data.get('minimo_muestras', cfg.get('minimo_muestras', 1))),
        'escalado_por_fallo_porcentaje': int(data.get('escalado_por_fallo_porcentaje', cfg.get('escalado_por_fallo_porcentaje', 20))),
        'escalado_dias': int(data.get('escalado_dias', cfg.get('escalado_dias', 7))),
        'updated_at': now,
        'updated_by': user.get('email'),
    }

    await db.iso_qa_config.update_one({'id': 'default'}, {'$set': update}, upsert=True)
    return await db.iso_qa_config.find_one({'id': 'default'}, {'_id': 0})


@router.post("/master/iso/qa-muestreo/ejecutar")
async def ejecutar_muestreo_qa_iso(user: dict = Depends(require_master)):
    cfg = await obtener_config_qa_iso(user)
    now_dt = datetime.now(timezone.utc)
    hoy = now_dt.date().isoformat()

    porcentaje = int(cfg.get('porcentaje_diario', 10))
    escalado_hasta = cfg.get('escalado_hasta')
    if escalado_hasta:
        esc_dt = _parse_dt_safe(escalado_hasta)
        if esc_dt and esc_dt >= now_dt:
            porcentaje = int(cfg.get('escalado_por_fallo_porcentaje', 20))

    inicio_dia = f"{hoy}T00:00:00"
    ordenes = await db.ordenes.find(
        {
            'estado': {'$in': ['reparado', 'validacion', 'enviado']},
            'updated_at': {'$gte': inicio_dia},
        },
        {'_id': 0, 'id': 1, 'numero_orden': 1, 'estado': 1, 'updated_at': 1},
    ).to_list(5000)

    if not ordenes:
        return {'message': 'No hay OT candidatas hoy para muestreo QA', 'muestras': []}

    total = len(ordenes)
    minimo = max(1, int(cfg.get('minimo_muestras', 1)))
    tam_muestra = max(minimo, math.ceil((total * porcentaje) / 100))
    tam_muestra = min(tam_muestra, total)

    seleccionadas = random.sample(ordenes, tam_muestra)
    registros = []
    for o in seleccionadas:
        existente = await db.qa_muestreos.find_one({'ot_id': o.get('id'), 'fecha': hoy}, {'_id': 0})
        if existente:
            registros.append(existente)
            continue
        doc = {
            'id': str(uuid.uuid4()),
            'ot_id': o.get('id'),
            'numero_orden': o.get('numero_orden'),
            'fecha': hoy,
            'porcentaje_aplicado': porcentaje,
            'estado': 'pendiente_qa',
            'resultado': None,
            'hallazgos': None,
            'capa_id': None,
            'created_at': now_dt.isoformat(),
            'created_by': user.get('email'),
        }
        await db.qa_muestreos.insert_one(doc)
        doc.pop('_id', None)
        registros.append(doc)

    await _registrar_evento_seguridad(user, 'qa_muestreo_ejecutado', {'fecha': hoy, 'total': total, 'muestra': len(registros), 'porcentaje': porcentaje})

    return {
        'fecha': hoy,
        'total_candidatas': total,
        'tam_muestra': len(registros),
        'porcentaje_aplicado': porcentaje,
        'muestras': registros,
    }


@router.post('/master/iso/qa-muestreo/{muestreo_id}/resultado')
async def registrar_resultado_muestreo_qa(muestreo_id: str, data: dict, user: dict = Depends(require_master)):
    muestreo = await db.qa_muestreos.find_one({'id': muestreo_id}, {'_id': 0})
    if not muestreo:
        raise HTTPException(status_code=404, detail='Muestreo QA no encontrado')

    resultado = (data.get('resultado') or '').strip().lower()
    if resultado not in {'ok', 'fallo'}:
        raise HTTPException(status_code=400, detail='resultado debe ser ok o fallo')

    now_dt = datetime.now(timezone.utc)
    update = {
        'resultado': resultado,
        'estado': 'completado',
        'hallazgos': data.get('hallazgos'),
        'updated_at': now_dt.isoformat(),
        'updated_by': user.get('email'),
    }

    capa_id = None
    if resultado == 'fallo':
        cfg = await obtener_config_qa_iso(user)
        escalado_dias = int(cfg.get('escalado_dias', 7))
        escalado_hasta = (now_dt + timedelta(days=escalado_dias)).isoformat()
        await db.iso_qa_config.update_one({'id': 'default'}, {'$set': {'escalado_hasta': escalado_hasta, 'updated_at': now_dt.isoformat()}})

        capa_id = str(uuid.uuid4())
        capa_doc = {
            'id': capa_id,
            'origen': 'qa_muestreo',
            'ot_id': muestreo.get('ot_id'),
            'numero_orden': muestreo.get('numero_orden'),
            'estado': 'abierta',
            'motivo_apertura': 'fallo_qa_muestreo',
            'problema': data.get('hallazgos') or 'Fallo detectado en QA por muestreo',
            'created_at': now_dt.isoformat(),
            'updated_at': now_dt.isoformat(),
            'created_by': user.get('email'),
        }
        await db.capas.insert_one(capa_doc)
        update['capa_id'] = capa_id

    await db.qa_muestreos.update_one({'id': muestreo_id}, {'$set': update})

    await _registrar_evento_seguridad(user, 'qa_muestreo_resultado', {'muestreo_id': muestreo_id, 'resultado': resultado, 'capa_id': capa_id})

    return await db.qa_muestreos.find_one({'id': muestreo_id}, {'_id': 0})

@router.get("/master/iso/reporte-pdf")
async def exportar_reporte_iso_pdf(
    user: dict = Depends(require_master),
    orden_id: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    query = {}

    if orden_id:
        query["id"] = orden_id

    if fecha_desde or fecha_hasta:
        query["created_at"] = {}
        if fecha_desde:
            query["created_at"]["$gte"] = fecha_desde
        if fecha_hasta:
            query["created_at"]["$lte"] = fecha_hasta

    ordenes = await db.ordenes.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, "Reporte ISO 9001 - Evidencias ERP")
    y -= 18
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Generado por: {user.get('email')} | Fecha: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
    y -= 24

    if orden_id:
        pdf.drawString(40, y, f"Filtro OT: {orden_id}")
        y -= 14
    if fecha_desde or fecha_hasta:
        pdf.drawString(40, y, f"Rango: {fecha_desde or '-'} a {fecha_hasta or '-'}")
        y -= 18

    if not ordenes:
        pdf.drawString(40, y, "Sin resultados para los filtros aplicados")
    else:
        for o in ordenes:
            if y < 120:
                pdf.showPage()
                y = height - 40

            consent_count = await db.consentimientos_seguimiento.count_documents({"orden_id": o.get("id")})
            event_count = await db.ot_event_log.count_documents({"ot_id": o.get("id")})
            incidencia_nc = await db.incidencias.find_one(
                {"orden_id": o.get("id"), "$or": [{"es_no_conformidad": True}, {"tipo": {"$in": ["reclamacion", "garantia", "daño_transporte"]}}]},
                {"_id": 0, "numero_incidencia": 1, "capa_estado": 1, "capa_causa_raiz": 1, "capa_accion_correctiva": 1},
            )

            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(40, y, f"OT {o.get('numero_orden')} ({o.get('estado')})")
            y -= 14
            pdf.setFont("Helvetica", 9)
            pdf.drawString(50, y, f"Cliente ID: {o.get('cliente_id')} | Creada: {o.get('created_at')} | Enviado: {o.get('fecha_enviado')}")
            y -= 12
            pdf.drawString(50, y, f"Consentimientos seguimiento: {consent_count} | EventLog: {event_count}")
            y -= 12
            pdf.drawString(50, y, f"RI: completada={bool(o.get('ri_completada'))} resultado={o.get('ri_resultado')}")
            y -= 12
            pdf.drawString(
                50,
                y,
                "Checklist recepción/QC: "
                f"recepcion={bool(o.get('recepcion_checklist_completo'))}, "
                f"diag_final={bool(o.get('diagnostico_salida_realizado'))}, "
                f"funciones={bool(o.get('funciones_verificadas'))}, "
                f"limpieza={bool(o.get('limpieza_realizada'))}",
            )
            y -= 12
            pdf.drawString(
                50,
                y,
                "Batería: "
                f"reemplazada={bool(o.get('bateria_reemplazada'))}, "
                f"almacenamiento={bool(o.get('bateria_almacenamiento_temporal'))}, "
                f"residuo_pendiente={bool(o.get('bateria_residuo_pendiente'))}",
            )
            y -= 12

            if incidencia_nc:
                pdf.drawString(
                    50,
                    y,
                    f"NC/CAPA: {incidencia_nc.get('numero_incidencia')} estado={incidencia_nc.get('capa_estado')}",
                )
                y -= 12
            else:
                pdf.drawString(50, y, "NC/CAPA: sin incidencia NC vinculada")
                y -= 12

            y -= 6

    pdf.save()
    buffer.seek(0)
    await _registrar_evento_seguridad(user, 'iso_reporte_pdf_export', {'orden_id': orden_id, 'desde': fecha_desde, 'hasta': fecha_hasta, 'total_ots': len(ordenes)})
    headers = {"Content-Disposition": "attachment; filename=reporte_iso_evidencias.pdf"}
    return StreamingResponse(buffer, media_type="application/pdf", headers=headers)



@router.get("/master/analiticas")
async def obtener_analiticas(user: dict = Depends(require_master)):
    """Panel de analíticas completo para master"""
    ordenes = await db.ordenes.find({}, {"_id": 0}).to_list(10000)

    # === MÉTRICAS FINANCIERAS ===
    total_gastos = 0  # Coste de materiales
    total_cobrado = 0  # Precio de venta de órdenes cerradas (enviado)
    total_pendiente_cobrar = 0  # Precio de venta de órdenes completadas pero no cerradas
    gastos_pendientes = 0  # Coste de órdenes no cerradas
    
    for o in ordenes:
        # Usar campos precalculados si existen
        if o.get('presupuesto_total') is not None:
            try:
                precio_venta_orden = float(o.get('presupuesto_total', 0) or 0)
                coste_orden = float(o.get('coste_total', 0) or 0)
            except (TypeError, ValueError):
                precio_venta_orden = 0
                coste_orden = 0
        else:
            # Fallback: cálculo manual para órdenes antiguas
            materiales = o.get('materiales', [])
            try:
                coste_orden = sum(float(m.get('coste', 0) or 0) * int(m.get('cantidad', 1) or 1) for m in materiales)
                precio_venta_orden = sum(float(m.get('precio_unitario', 0) or 0) * int(m.get('cantidad', 1) or 1) for m in materiales)
            except (TypeError, ValueError):
                coste_orden = 0
                precio_venta_orden = 0
        
        if o.get('estado') == 'enviado':
            # Orden cerrada
            total_gastos += coste_orden
            total_cobrado += precio_venta_orden
        elif o.get('estado') in ['reparado', 'validacion']:
            # Orden completada pero no cerrada (pendiente de cobrar)
            total_pendiente_cobrar += precio_venta_orden
            gastos_pendientes += coste_orden
        elif o.get('estado') in ['en_taller', 'recibida']:
            # Orden en proceso
            gastos_pendientes += coste_orden
    
    margen_beneficio = total_cobrado - total_gastos
    porcentaje_margen = round((margen_beneficio / total_cobrado * 100) if total_cobrado > 0 else 0, 1)

    # Ingresos por mes
    ingresos_por_mes = {}
    gastos_por_mes = {}
    for o in ordenes:
        if o.get('estado') == 'enviado':
            try:
                fecha = datetime.fromisoformat(o['created_at']) if isinstance(o['created_at'], str) else o['created_at']
                mes = fecha.strftime('%Y-%m')
                
                # Usar campos precalculados
                if o.get('presupuesto_total') is not None:
                    try:
                        total_venta = float(o.get('presupuesto_total', 0) or 0)
                        total_coste = float(o.get('coste_total', 0) or 0)
                    except (TypeError, ValueError):
                        total_venta = 0
                        total_coste = 0
                else:
                    materiales = o.get('materiales', [])
                    try:
                        total_venta = sum(float(m.get('precio_unitario', 0) or 0) * int(m.get('cantidad', 1) or 1) for m in materiales)
                        total_coste = sum(float(m.get('coste', 0) or 0) * int(m.get('cantidad', 1) or 1) for m in materiales)
                    except (TypeError, ValueError):
                        total_venta = 0
                        total_coste = 0
                
                ingresos_por_mes[mes] = ingresos_por_mes.get(mes, 0) + total_venta
                gastos_por_mes[mes] = gastos_por_mes.get(mes, 0) + total_coste
            except Exception:
                pass

    # Tiempo medio de reparación (en horas) - MEJORADO
    tiempos_reparacion = []
    ordenes_con_tiempo = 0
    ordenes_sin_tiempo = 0
    
    for o in ordenes:
        if o.get('estado') != 'enviado':
            continue  # Solo órdenes completadas (enviadas)
            
        tiempo_calculado = False
        
        # Método 1: Usar campos específicos fecha_inicio_reparacion y fecha_fin_reparacion
        inicio = o.get('fecha_inicio_reparacion')
        fin = o.get('fecha_fin_reparacion')
        if inicio and fin:
            try:
                i = datetime.fromisoformat(inicio) if isinstance(inicio, str) else inicio
                f = datetime.fromisoformat(fin) if isinstance(fin, str) else fin
                diff_horas = (f - i).total_seconds() / 3600
                if 0 < diff_horas < 2160:  # Max 90 días
                    tiempos_reparacion.append(diff_horas)
                    tiempo_calculado = True
            except Exception:
                pass
        
        # Método 2: Usar fecha_recibida_centro hasta fecha_enviado o updated_at
        if not tiempo_calculado:
            inicio_alt = o.get('fecha_recibida_centro') or o.get('created_at')
            fin_alt = o.get('fecha_enviado') or o.get('updated_at')
            if inicio_alt and fin_alt:
                try:
                    i = datetime.fromisoformat(inicio_alt) if isinstance(inicio_alt, str) else inicio_alt
                    f = datetime.fromisoformat(fin_alt) if isinstance(fin_alt, str) else fin_alt
                    diff_horas = (f - i).total_seconds() / 3600
                    if 0 < diff_horas < 2160:  # Max 90 días
                        tiempos_reparacion.append(diff_horas)
                        tiempo_calculado = True
                except Exception:
                    pass
        
        # Método 3: Usar created_at hasta updated_at como último recurso
        if not tiempo_calculado:
            inicio_fallback = o.get('created_at')
            fin_fallback = o.get('updated_at')
            if inicio_fallback and fin_fallback:
                try:
                    i = datetime.fromisoformat(inicio_fallback) if isinstance(inicio_fallback, str) else inicio_fallback
                    f = datetime.fromisoformat(fin_fallback) if isinstance(fin_fallback, str) else fin_fallback
                    diff_horas = (f - i).total_seconds() / 3600
                    if 0 < diff_horas < 2160:  # Max 90 días
                        tiempos_reparacion.append(diff_horas)
                        tiempo_calculado = True
                except Exception:
                    pass
        
        if tiempo_calculado:
            ordenes_con_tiempo += 1
        else:
            ordenes_sin_tiempo += 1
    
    tiempo_medio_horas = round(sum(tiempos_reparacion) / len(tiempos_reparacion), 1) if tiempos_reparacion else 0
    tiempo_medio_dias = round(tiempo_medio_horas / 24, 1)

    # Ranking técnicos
    tecnicos = await db.users.find({"role": "tecnico", "activo": True}, {"_id": 0, "password_hash": 0}).to_list(100)
    ranking = []
    for t in tecnicos:
        t_ordenes = [o for o in ordenes if o.get('tecnico_asignado') == t['id']]
        completadas = len([o for o in t_ordenes if o.get('estado') == 'enviado'])
        ranking.append({"nombre": f"{t['nombre']} {t.get('apellidos', '')}", "total": len(t_ordenes), "completadas": completadas, "tasa": round((completadas / len(t_ordenes) * 100) if t_ordenes else 0, 1)})
    ranking.sort(key=lambda x: x['completadas'], reverse=True)

    # Distribución por estado
    dist_estado = {}
    for o in ordenes:
        est = o.get('estado', 'desconocido')
        dist_estado[est] = dist_estado.get(est, 0) + 1

    # Órdenes últimos 12 meses
    ordenes_por_mes = {}
    for o in ordenes:
        try:
            fecha = datetime.fromisoformat(o['created_at']) if isinstance(o['created_at'], str) else o['created_at']
            mes = fecha.strftime('%Y-%m')
            ordenes_por_mes[mes] = ordenes_por_mes.get(mes, 0) + 1
        except Exception:
            pass

    return {
        # Métricas financieras
        "finanzas": {
            "total_gastos": round(total_gastos, 2),
            "total_cobrado": round(total_cobrado, 2),
            "pendiente_cobrar": round(total_pendiente_cobrar, 2),
            "gastos_pendientes": round(gastos_pendientes, 2),
            "margen_beneficio": round(margen_beneficio, 2),
            "porcentaje_margen": porcentaje_margen,
        },
        "ingresos_por_mes": dict(sorted(ingresos_por_mes.items())[-12:]),
        "gastos_por_mes": dict(sorted(gastos_por_mes.items())[-12:]),
        "tiempo_medio_reparacion_horas": tiempo_medio_horas,
        "tiempo_medio_reparacion_dias": tiempo_medio_dias,
        "ordenes_con_tiempo": ordenes_con_tiempo,
        "ordenes_sin_tiempo": ordenes_sin_tiempo,
        "ranking_tecnicos": ranking,
        "distribucion_estado": dist_estado,
        "ordenes_por_mes": dict(sorted(ordenes_por_mes.items())[-12:]),
        "total_ordenes": len(ordenes),
        "total_completadas": len([o for o in ordenes if o.get('estado') == 'enviado']),
        "total_en_proceso": len([o for o in ordenes if o.get('estado') in ['en_taller', 'reparado', 'validacion']]),
    }


@router.get("/master/finanzas")
async def obtener_finanzas(
    periodo: str = "mes",  # mes, semana, trimestre, año, custom
    fecha_inicio: str = None,
    fecha_fin: str = None,
    user: dict = Depends(require_master)
):
    """
    Panel financiero detallado con filtros por período.
    - Total a facturar (presupuestos aceptados)
    - Desglose por semana/mes
    - Proyecciones
    - Clasificación por estado de facturación
    """
    from datetime import timedelta
    
    ahora = datetime.now(timezone.utc)
    
    # Determinar rango de fechas según período
    if fecha_inicio and fecha_fin:
        inicio = datetime.fromisoformat(fecha_inicio.replace('Z', '+00:00'))
        fin = datetime.fromisoformat(fecha_fin.replace('Z', '+00:00'))
    elif periodo == "semana":
        inicio = ahora - timedelta(days=ahora.weekday())  # Lunes de esta semana
        inicio = inicio.replace(hour=0, minute=0, second=0, microsecond=0)
        fin = ahora
    elif periodo == "mes":
        inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fin = ahora
    elif periodo == "trimestre":
        trimestre_mes = ((ahora.month - 1) // 3) * 3 + 1
        inicio = ahora.replace(month=trimestre_mes, day=1, hour=0, minute=0, second=0, microsecond=0)
        fin = ahora
    elif periodo == "año":
        inicio = ahora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        fin = ahora
    else:  # Por defecto mes actual
        inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fin = ahora
    
    # Obtener todas las órdenes del período
    ordenes = await db.ordenes.find({
        "created_at": {"$gte": inicio.isoformat(), "$lte": fin.isoformat()}
    }, {"_id": 0}).to_list(10000)
    
    # También obtener órdenes anteriores pendientes de facturar
    ordenes_pendientes_anteriores = await db.ordenes.find({
        "created_at": {"$lt": inicio.isoformat()},
        "estado": {"$in": ["reparado", "validacion", "en_taller", "recibida", "pendiente_recibir"]}
    }, {"_id": 0}).to_list(10000)
    
    # === CLASIFICACIÓN DE ÓRDENES ===
    facturado = []  # Órdenes cerradas (estado: enviado)
    pendiente_facturar = []  # Órdenes completadas pero no cerradas (reparado, validacion)
    en_proceso = []  # Órdenes en taller
    por_recibir = []  # Órdenes pendientes de recibir
    
    for o in ordenes:
        estado = o.get('estado', '')
        
        # === CALCULAR VALOR DE LA ORDEN ===
        valor_orden = 0
        coste_materiales = 0
        
        # 1. Usar campos precalculados si existen
        if o.get('presupuesto_total') is not None:
            try:
                valor_orden = float(o.get('presupuesto_total', 0) or 0)
                coste_materiales = float(o.get('coste_total', 0) or 0)
            except (TypeError, ValueError):
                valor_orden = 0
                coste_materiales = 0
        
        # 2. Si no hay presupuesto_total, buscar en datos_portal.price
        if valor_orden <= 0:
            datos_portal = o.get('datos_portal') or {}
            try:
                precio_portal = datos_portal.get('price') or datos_portal.get('claim_real_value') or 0
                valor_orden = float(precio_portal) if precio_portal else 0
            except (TypeError, ValueError):
                valor_orden = 0
        
        # 3. Buscar en presupuesto_enviado
        if valor_orden <= 0:
            presupuesto_enviado = o.get('presupuesto_enviado') or {}
            try:
                valor_orden = float(presupuesto_enviado.get('precio', 0) or 0)
            except (TypeError, ValueError):
                valor_orden = 0
        
        # 4. Fallback a suma de materiales
        if valor_orden <= 0:
            materiales = o.get('materiales', [])
            try:
                valor_orden = sum(float(m.get('precio_unitario', 0) or 0) * int(m.get('cantidad', 1) or 1) for m in materiales)
            except (TypeError, ValueError):
                valor_orden = 0
        
        # Calcular coste de materiales si no está precalculado
        if coste_materiales <= 0:
            materiales = o.get('materiales', [])
            try:
                coste_materiales = sum(float(m.get('coste', 0) or 0) * int(m.get('cantidad', 1) or 1) for m in materiales)
            except (TypeError, ValueError):
                coste_materiales = 0
        
        beneficio = valor_orden - coste_materiales
        
        dispositivo = o.get('dispositivo') or {}
        orden_data = {
            "id": o.get('id'),
            "numero_orden": o.get('numero_orden'),
            "estado": estado,
            "valor": valor_orden,
            "coste": coste_materiales,
            "beneficio": beneficio,
            "cliente": o.get('cliente_nombre', 'N/A'),
            "dispositivo": f"{dispositivo.get('marca', '')} {dispositivo.get('modelo', '')}".strip(),
            "fecha": o.get('created_at'),
            "origen": o.get('origen', 'directo')
        }
        
        if estado == 'enviado':
            facturado.append(orden_data)
        elif estado in ['reparado', 'validacion']:
            pendiente_facturar.append(orden_data)
        elif estado in ['en_taller', 'recibida']:
            en_proceso.append(orden_data)
        elif estado == 'pendiente_recibir':
            por_recibir.append(orden_data)
    
    # === TOTALES ===
    total_facturado = sum(o['valor'] for o in facturado)
    total_pendiente = sum(o['valor'] for o in pendiente_facturar)
    total_en_proceso = sum(o['valor'] for o in en_proceso)
    total_por_recibir = sum(o['valor'] for o in por_recibir)
    
    total_coste_facturado = sum(o['coste'] for o in facturado)
    total_coste_pendiente = sum(o['coste'] for o in pendiente_facturar)
    
    # === DESGLOSE POR SEMANA (últimas 4 semanas del período) ===
    semanas = {}
    for o in ordenes:
        try:
            fecha = datetime.fromisoformat(o['created_at']) if isinstance(o['created_at'], str) else o['created_at']
            semana_num = fecha.isocalendar()[1]
            semana_key = f"S{semana_num}"
            
            if semana_key not in semanas:
                semanas[semana_key] = {"ordenes": 0, "valor": 0, "facturado": 0, "pendiente": 0}
            
            # Usar campos precalculados
            if o.get('presupuesto_total') is not None:
                try:
                    precio = float(o.get('presupuesto_total', 0) or 0)
                except (TypeError, ValueError):
                    precio = 0
            else:
                materiales = o.get('materiales', [])
                pres_env = o.get('presupuesto_enviado') or {}
                try:
                    precio = float(pres_env.get('precio', 0) or 0)
                    if precio <= 0:
                        precio = sum(float(m.get('precio_unitario', 0) or 0) * int(m.get('cantidad', 1) or 1) for m in materiales)
                except (TypeError, ValueError):
                    precio = 0
            
            semanas[semana_key]["ordenes"] += 1
            semanas[semana_key]["valor"] += precio
            
            if o.get('estado') == 'enviado':
                semanas[semana_key]["facturado"] += precio
            elif o.get('estado') in ['reparado', 'validacion']:
                semanas[semana_key]["pendiente"] += precio
        except Exception:
            pass
    
    # === PROYECCIÓN ===
    dias_transcurridos = (ahora - inicio).days + 1
    
    if periodo == "mes":
        dias_totales = 30
    elif periodo == "semana":
        dias_totales = 7
    elif periodo == "trimestre":
        dias_totales = 90
    elif periodo == "año":
        dias_totales = 365
    else:
        dias_totales = dias_transcurridos
    
    # Proyección basada en ritmo actual
    ritmo_diario = (total_facturado + total_pendiente + total_en_proceso) / dias_transcurridos if dias_transcurridos > 0 else 0
    proyeccion_periodo = ritmo_diario * dias_totales
    
    # Ticket medio - calculado sobre todas las órdenes del período
    total_valor_periodo = total_facturado + total_pendiente + total_en_proceso + total_por_recibir
    ticket_medio = total_valor_periodo / len(ordenes) if ordenes else 0
    
    # === COMPARATIVA CON PERÍODO ANTERIOR ===
    duracion_periodo = fin - inicio
    inicio_anterior = inicio - duracion_periodo
    fin_anterior = inicio
    
    ordenes_anterior = await db.ordenes.find({
        "created_at": {"$gte": inicio_anterior.isoformat(), "$lt": fin_anterior.isoformat()}
    }, {"_id": 0}).to_list(10000)
    
    total_anterior = 0
    for o in ordenes_anterior:
        # Usar campos precalculados
        if o.get('presupuesto_total') is not None:
            try:
                precio = float(o.get('presupuesto_total', 0) or 0)
            except (TypeError, ValueError):
                precio = 0
        else:
            materiales = o.get('materiales', [])
            pres_env_ant = o.get('presupuesto_enviado') or {}
            try:
                precio = float(pres_env_ant.get('precio', 0) or 0)
                if precio <= 0:
                    precio = sum(float(m.get('precio_unitario', 0) or 0) * int(m.get('cantidad', 1) or 1) for m in materiales)
            except (TypeError, ValueError):
                precio = 0
        total_anterior += precio
    
    variacion_porcentaje = round(((total_facturado + total_pendiente - total_anterior) / total_anterior * 100) if total_anterior > 0 else 0, 1)
    
    return {
        "periodo": {
            "tipo": periodo,
            "inicio": inicio.isoformat(),
            "fin": fin.isoformat(),
            "dias_transcurridos": dias_transcurridos,
            "dias_totales": dias_totales
        },
        "resumen": {
            "total_ordenes": len(ordenes),
            "total_a_facturar": round(total_facturado + total_pendiente + total_en_proceso + total_por_recibir, 2),
            "ya_facturado": round(total_facturado, 2),
            "pendiente_facturar": round(total_pendiente, 2),
            "en_proceso": round(total_en_proceso, 2),
            "por_recibir": round(total_por_recibir, 2),
            "ticket_medio": round(ticket_medio, 2),
        },
        "costes": {
            "total_costes": round(total_coste_facturado + total_coste_pendiente, 2),
            "costes_facturado": round(total_coste_facturado, 2),
            "costes_pendiente": round(total_coste_pendiente, 2),
        },
        "beneficio": {
            "beneficio_facturado": round(total_facturado - total_coste_facturado, 2),
            "beneficio_estimado_pendiente": round(total_pendiente - total_coste_pendiente, 2),
            "margen_porcentaje": round(((total_facturado - total_coste_facturado) / total_facturado * 100) if total_facturado > 0 else 0, 1),
        },
        "proyeccion": {
            "ritmo_diario": round(ritmo_diario, 2),
            "proyeccion_periodo": round(proyeccion_periodo, 2),
            "proyeccion_mensual": round(ritmo_diario * 30, 2),
            "proyeccion_anual": round(ritmo_diario * 365, 2),
        },
        "comparativa": {
            "periodo_anterior": round(total_anterior, 2),
            "variacion_porcentaje": variacion_porcentaje,
            "tendencia": "alza" if variacion_porcentaje > 0 else "baja" if variacion_porcentaje < 0 else "estable"
        },
        "desglose_semanal": dict(sorted(semanas.items())),
        "clasificacion": {
            "facturado": {"count": len(facturado), "total": round(total_facturado, 2), "ordenes": facturado[:10]},
            "pendiente_facturar": {"count": len(pendiente_facturar), "total": round(total_pendiente, 2), "ordenes": pendiente_facturar[:10]},
            "en_proceso": {"count": len(en_proceso), "total": round(total_en_proceso, 2), "ordenes": en_proceso[:10]},
            "por_recibir": {"count": len(por_recibir), "total": round(total_por_recibir, 2), "ordenes": por_recibir[:10]},
        },
        "pendientes_anteriores": {
            "count": len(ordenes_pendientes_anteriores),
            "total": round(sum(
                (o.get('presupuesto_enviado') or {}).get('precio', 0) or 
                sum(m.get('precio_unitario', 0) * m.get('cantidad', 1) for m in o.get('materiales', []))
                for o in ordenes_pendientes_anteriores
            ), 2)
        }
    }



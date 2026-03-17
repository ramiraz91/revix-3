"""
GLS Routes - Complete logistics module.
Endpoints: config, shipments, pickups, labels, tracking, sync, admin panel, logs.
All GLS logic centralized here + service layer.
"""
import logging
import base64
import uuid as uuid_mod
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, validator
from typing import Optional, List
from config import db
from auth import require_auth, require_master, require_admin

from services.gls_soap_client import (
    graba_servicios, etiqueta_envio, etiqueta_recogida, get_exp_cli, anula,
    build_envio_xml, SERVICIOS_GLS, HORARIOS_GLS
)
from services.gls_state_mapper import (
    map_gls_status, is_final_state, is_incidencia, get_badge_info,
    process_state_change, GLS_STATUS_MAP, ESTADO_BADGE
)

logger = logging.getLogger("gls_routes")
router = APIRouter(prefix="/gls", tags=["gls"])

CONFIG_TIPO = "gls_config"


# ─── Helpers ──────────────────────────────────────────────

async def _get_gls_config() -> dict:
    doc = await db.configuracion.find_one({"tipo": CONFIG_TIPO}, {"_id": 0})
    return doc.get("datos", {}) if doc else {}


async def _require_active() -> dict:
    cfg = await _get_gls_config()
    if not cfg.get("activo"):
        raise HTTPException(400, "Integración GLS no activada")
    if not cfg.get("uid_cliente"):
        raise HTTPException(400, "UID cliente GLS no configurado")
    return cfg


async def _log(envio_id: str, tipo: str, detalle: str = "", error: str = "", request_data: str = "", response_data: str = ""):
    """Persist integration log."""
    await db.gls_logs.insert_one({
        "id": str(uuid_mod.uuid4()),
        "envio_id": envio_id,
        "tipo_operacion": tipo,
        "detalle": detalle[:500],
        "error": error[:500],
        "request_resumen": request_data[:2000] if request_data else "",
        "response_resumen": response_data[:2000] if response_data else "",
        "fecha": datetime.now(timezone.utc).isoformat()
    })


def _validate_required(data: dict, fields: list):
    missing = [f for f in fields if not data.get(f, "").strip()]
    if missing:
        raise HTTPException(422, f"Campos obligatorios vacíos: {', '.join(missing)}")


# ─── Config ───────────────────────────────────────────────

@router.get("/config")
async def get_config(user: dict = Depends(require_master)):
    cfg = await _get_gls_config()
    return {
        "activo": cfg.get("activo", False),
        "uid_cliente": cfg.get("uid_cliente", ""),
        "remitente": cfg.get("remitente", {
            "nombre": "revix.es", "direccion": "Julio alarcon 8, Local",
            "poblacion": "Cordoba", "cp": "14007", "telefono": "604319223", "nif": "31018296J"
        }),
        "servicio_defecto": cfg.get("servicio_defecto", "1"),
        "horario_defecto": cfg.get("horario_defecto", "18"),
        "portes_defecto": cfg.get("portes_defecto", "P"),
        "formato_etiqueta": cfg.get("formato_etiqueta", "PDF"),
        "polling_activo": cfg.get("polling_activo", False),
        "polling_intervalo_horas": cfg.get("polling_intervalo_horas", 4),
        "servicios_disponibles": SERVICIOS_GLS,
        "horarios_disponibles": HORARIOS_GLS,
        "estados_mapa": ESTADO_BADGE,
    }


class GLSConfigPayload(BaseModel):
    activo: bool = False
    uid_cliente: str = ""
    remitente: dict = {}
    servicio_defecto: str = "1"
    horario_defecto: str = "18"
    portes_defecto: str = "P"
    formato_etiqueta: str = "PDF"
    polling_activo: bool = False
    polling_intervalo_horas: int = 4


@router.post("/config")
async def save_config(payload: GLSConfigPayload, user: dict = Depends(require_master)):
    data = payload.dict()
    await db.configuracion.update_one(
        {"tipo": CONFIG_TIPO},
        {"$set": {"tipo": CONFIG_TIPO, "datos": data,
                  "updated_at": datetime.now(timezone.utc).isoformat(),
                  "updated_by": user.get("email", "sistema")}},
        upsert=True
    )
    return {"success": True, "message": "Configuración GLS guardada"}


# ─── Create Shipment ─────────────────────────────────────

class CrearEnvioPayload(BaseModel):
    orden_id: str
    entidad_tipo: str = "orden"
    nombre_dst: str
    direccion_dst: str
    poblacion_dst: str
    cp_dst: str
    telefono_dst: str = ""
    email_dst: str = ""
    nif_dst: str = ""
    observaciones: str = ""
    servicio: str = ""
    horario: str = ""
    bultos: str = "1"
    peso: str = "1"
    portes: str = ""
    reembolso: str = "0"
    pais_dst: str = "ES"


@router.post("/envio")
async def crear_envio_endpoint(payload: CrearEnvioPayload, user: dict = Depends(require_auth)):
    cfg = await _require_active()
    uid = cfg["uid_cliente"]
    rem = cfg.get("remitente", {})

    _validate_required({"nombre": payload.nombre_dst, "direccion": payload.direccion_dst,
                         "poblacion": payload.poblacion_dst, "cp": payload.cp_dst},
                        ["nombre", "direccion", "poblacion", "cp"])

    # Check duplicates
    existing = await db.gls_envios.find_one(
        {"entidad_origen_id": payload.orden_id, "tipo": "envio", "estado_interno": {"$nin": ["anulado", "cancelado"]}},
        {"_id": 0, "id": 1}
    )
    if existing:
        raise HTTPException(409, "Ya existe un envío activo para esta orden. Anúlelo primero si desea crear otro.")

    ref_interna = payload.orden_id
    servicio = payload.servicio or cfg.get("servicio_defecto", "1")
    horario = payload.horario or cfg.get("horario_defecto", "18")
    portes = payload.portes or cfg.get("portes_defecto", "P")

    destinatario = {"nombre": payload.nombre_dst, "direccion": payload.direccion_dst,
                    "poblacion": payload.poblacion_dst, "cp": payload.cp_dst,
                    "telefono": payload.telefono_dst, "email": payload.email_dst,
                    "nif": payload.nif_dst, "pais": payload.pais_dst}
    params = {"servicio": servicio, "horario": horario, "bultos": payload.bultos,
              "peso": payload.peso, "portes": portes, "reembolso": payload.reembolso,
              "observaciones": payload.observaciones, "referencia": ref_interna}

    envio_xml = build_envio_xml(rem, destinatario, params)
    result = await graba_servicios(uid, envio_xml)

    envio_id = str(uuid_mod.uuid4())

    # Persist to gls_envios collection
    envio_doc = {
        "id": envio_id,
        "tipo": "envio",
        "entidad_origen_tipo": payload.entidad_tipo,
        "entidad_origen_id": payload.orden_id,
        "cliente_id": "",
        "gls_codexp": "",
        "gls_uid": result.get("uid_envio", ""),
        "gls_codbarras": result.get("codbarras", ""),
        "referencia_interna": ref_interna,
        "servicio_gls": servicio,
        "horario_gls": horario,
        "destinatario": destinatario,
        "remitente": rem,
        "fecha_creacion": datetime.now(timezone.utc).isoformat(),
        "fecha_ultima_sync": None,
        "estado_interno": "grabado" if result["success"] else "error",
        "estado_gls_codigo": "",
        "estado_gls_texto": "",
        "tracking_json": None,
        "entrega_fecha": None,
        "entrega_receptor": None,
        "entrega_dni": None,
        "pod_url": None,
        "incidencia_codigo": None,
        "incidencia_texto": None,
        "label_generada": False,
        "label_formato": cfg.get("formato_etiqueta", "PDF"),
        "bultos": payload.bultos,
        "peso": payload.peso,
        "portes": portes,
        "observaciones": payload.observaciones,
        "reembolso": payload.reembolso,
        "raw_request": (result.get("raw_request") or "")[:3000],
        "raw_response": (result.get("raw_response") or "")[:3000],
        "sync_status": "ok" if result["success"] else "error",
        "sync_error": result.get("error", ""),
        "created_by": user.get("email", "sistema"),
        "updated_by": user.get("email", "sistema"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.gls_envios.insert_one(envio_doc)

    if result["success"]:
        # Update order
        await db.ordenes.update_one(
            {"id": payload.orden_id},
            {"$set": {"codigo_recogida_salida": result["codbarras"], "agencia_envio": "GLS",
                      "updated_at": datetime.now(timezone.utc).isoformat()},
             "$push": {"gls_envios": {"id": envio_id, "tipo": "envio", "codbarras": result["codbarras"],
                       "referencia": ref_interna, "estado_gls": "grabado",
                       "created_at": datetime.now(timezone.utc).isoformat(), "created_by": user.get("email")}}}
        )
        await _log(envio_id, "crear_envio", f"Envío creado: {result['codbarras']}")
    else:
        await _log(envio_id, "crear_envio", error=result.get("error", ""))

    # Remove raw data from response
    safe_result = {k: v for k, v in result.items() if k not in ("raw_request", "raw_response")}
    return {**safe_result, "envio_id": envio_id}


# ─── Create Pickup ───────────────────────────────────────

class CrearRecogidaPayload(BaseModel):
    orden_id: str
    entidad_tipo: str = "orden"
    nombre_org: str
    direccion_org: str
    poblacion_org: str
    cp_org: str
    telefono_org: str = ""
    observaciones: str = ""
    servicio: str = ""
    horario: str = ""
    bultos: str = "1"
    peso: str = "1"
    fecha: str = ""


@router.post("/recogida")
async def crear_recogida_endpoint(payload: CrearRecogidaPayload, user: dict = Depends(require_auth)):
    cfg = await _require_active()
    uid = cfg["uid_cliente"]
    rem = cfg.get("remitente", {})

    _validate_required({"nombre": payload.nombre_org, "direccion": payload.direccion_org,
                         "poblacion": payload.poblacion_org, "cp": payload.cp_org},
                        ["nombre", "direccion", "poblacion", "cp"])

    existing = await db.gls_envios.find_one(
        {"entidad_origen_id": payload.orden_id, "tipo": "recogida", "estado_interno": {"$nin": ["anulado", "cancelado"]}},
        {"_id": 0, "id": 1}
    )
    if existing:
        raise HTTPException(409, "Ya existe una recogida activa para esta orden.")

    ref_interna = payload.orden_id
    servicio = payload.servicio or cfg.get("servicio_defecto", "1")
    horario = payload.horario or cfg.get("horario_defecto", "18")
    fecha = payload.fecha or datetime.now(timezone.utc).strftime("%d/%m/%Y")

    # For pickup: client is sender, shop is destination
    remitente_pickup = {"nombre": payload.nombre_org, "direccion": payload.direccion_org,
                        "poblacion": payload.poblacion_org, "cp": payload.cp_org,
                        "telefono": payload.telefono_org}
    params = {"servicio": servicio, "horario": horario, "bultos": payload.bultos,
              "peso": payload.peso, "portes": "P", "reembolso": "0", "fecha": fecha,
              "observaciones": payload.observaciones, "referencia": ref_interna}

    envio_xml = build_envio_xml(remitente_pickup, rem, params)
    result = await graba_servicios(uid, envio_xml)

    envio_id = str(uuid_mod.uuid4())
    envio_doc = {
        "id": envio_id,
        "tipo": "recogida",
        "entidad_origen_tipo": payload.entidad_tipo,
        "entidad_origen_id": payload.orden_id,
        "cliente_id": "",
        "gls_codexp": "",
        "gls_uid": result.get("uid_envio", ""),
        "gls_codbarras": result.get("codbarras", ""),
        "referencia_interna": ref_interna,
        "servicio_gls": servicio,
        "horario_gls": horario,
        "destinatario": rem,
        "remitente": remitente_pickup,
        "fecha_creacion": datetime.now(timezone.utc).isoformat(),
        "fecha_ultima_sync": None,
        "estado_interno": "grabado" if result["success"] else "error",
        "estado_gls_codigo": "",
        "estado_gls_texto": "",
        "tracking_json": None,
        "entrega_fecha": None, "entrega_receptor": None, "entrega_dni": None, "pod_url": None,
        "incidencia_codigo": None, "incidencia_texto": None,
        "label_generada": False,
        "label_formato": cfg.get("formato_etiqueta", "PDF"),
        "bultos": payload.bultos, "peso": payload.peso,
        "portes": "P", "observaciones": payload.observaciones, "reembolso": "0",
        "raw_request": (result.get("raw_request") or "")[:3000],
        "raw_response": (result.get("raw_response") or "")[:3000],
        "sync_status": "ok" if result["success"] else "error",
        "sync_error": result.get("error", ""),
        "created_by": user.get("email", "sistema"),
        "updated_by": user.get("email", "sistema"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.gls_envios.insert_one(envio_doc)

    if result["success"]:
        await db.ordenes.update_one(
            {"id": payload.orden_id},
            {"$set": {"codigo_recogida_entrada": result["codbarras"], "agencia_envio": "GLS",
                      "updated_at": datetime.now(timezone.utc).isoformat()},
             "$push": {"gls_envios": {"id": envio_id, "tipo": "recogida", "codbarras": result["codbarras"],
                       "referencia": ref_interna, "estado_gls": "grabado",
                       "created_at": datetime.now(timezone.utc).isoformat(), "created_by": user.get("email")}}}
        )
        await _log(envio_id, "crear_recogida", f"Recogida creada: {result['codbarras']}")

        # Send email with pickup label
        try:
            await _enviar_email_recogida(cfg, payload.orden_id, result["codbarras"])
        except Exception as e:
            logger.error(f"Error enviando email recogida: {e}")
    else:
        await _log(envio_id, "crear_recogida", error=result.get("error", ""))

    safe_result = {k: v for k, v in result.items() if k not in ("raw_request", "raw_response")}
    return {**safe_result, "envio_id": envio_id}


# ─── Email Recogida ──────────────────────────────────────

async def _enviar_email_recogida(cfg: dict, orden_id: str, codbarras: str):
    """Send pickup instructions + label PDF to client."""
    import smtplib, ssl
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.application import MIMEApplication
    import config as app_cfg

    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        return
    cliente = orden.get("cliente") or {}
    email_dst = cliente.get("email", "")
    if not email_dst or not app_cfg.SMTP_CONFIGURED:
        return

    etiqueta_pdf = None
    try:
        label_result = await etiqueta_recogida(cfg["uid_cliente"], orden_id, "PDF")
        if label_result.get("success"):
            etiqueta_pdf = base64.b64decode(label_result["etiqueta_base64"])
    except Exception as e:
        logger.error(f"Error obteniendo etiqueta para email: {e}")

    nombre = cliente.get("nombre", "Cliente")
    num = orden.get("numero_orden", orden_id)
    disp = orden.get("dispositivo", {})
    disp_txt = f"{disp.get('marca', '')} {disp.get('modelo', '')}".strip() or "su dispositivo"

    html = f'''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:'Segoe UI',Tahoma,sans-serif;background:#f5f5f5;">
<div style="max-width:600px;margin:20px auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
<div style="background:#1a1a2e;color:#fff;padding:30px 40px;text-align:center;">
<h1 style="margin:0;font-size:22px;">Instrucciones de Envio</h1>
<p style="margin:8px 0 0;opacity:0.85;font-size:14px;">Orden {num}</p></div>
<div style="padding:30px 40px;">
<p style="font-size:16px;color:#333;">Hola <strong>{nombre}</strong>,</p>
<p style="font-size:14px;color:#555;line-height:1.6;">Hemos generado la etiqueta de recogida para su <strong>{disp_txt}</strong>. GLS pasara a recoger el paquete en la direccion indicada.</p>
<div style="background:#FFF8E1;border-left:4px solid #F9A825;padding:20px;border-radius:6px;margin:24px 0;">
<h3 style="margin:0 0 12px;color:#E65100;font-size:15px;">Antes de entregar el paquete:</h3>
<ol style="margin:0;padding-left:20px;color:#555;font-size:14px;line-height:2;">
<li><strong>Restablezca el dispositivo a valores de fabrica</strong></li>
<li><strong>Retire la tarjeta SIM</strong> y tarjeta de memoria</li>
<li><strong>No incluya accesorios</strong>: ni cargador, cable, funda ni protector</li>
<li><strong>Embale correctamente</strong>: papel burbuja y caja resistente</li>
<li><strong>Solo el dispositivo</strong> dentro del paquete</li></ol></div>
<div style="background:#E8F5E9;border-left:4px solid #43A047;padding:16px;border-radius:6px;margin:20px 0;">
<p style="margin:0;font-size:14px;color:#2E7D32;"><strong>Codigo de seguimiento:</strong>
<span style="font-family:monospace;font-size:15px;background:#fff;padding:4px 8px;border-radius:4px;">{codbarras}</span></p>
<p style="margin:8px 0 0;font-size:13px;"><a href="https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/?match={codbarras}" style="color:#1B5E20;">Seguir en GLS</a></p></div>
{"<p style='font-size:14px;color:#555;'>La <strong>etiqueta de envio</strong> esta adjunta en PDF. Imprimala y peguela visible en el paquete.</p>" if etiqueta_pdf else ""}
<div style="border-top:1px solid #eee;margin-top:24px;padding-top:16px;">
<p style="font-size:13px;color:#888;">Dudas: <a href="mailto:help@revix.es" style="color:#1a1a2e;">help@revix.es</a> | 604 319 223</p></div></div>
<div style="background:#f8f8f8;padding:16px 40px;text-align:center;border-top:1px solid #eee;">
<p style="margin:0;font-size:12px;color:#999;">revix.es - Servicio tecnico profesional</p></div></div></body></html>'''

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"Instrucciones de Envio - Orden {num}"
    msg["From"] = app_cfg.SMTP_FROM or f"Revix <{app_cfg.SMTP_USER}>"
    msg["To"] = email_dst
    msg["Reply-To"] = app_cfg.SMTP_REPLY_TO or "help@revix.es"
    msg.attach(MIMEText(html, "html", "utf-8"))

    if etiqueta_pdf:
        att = MIMEApplication(etiqueta_pdf, _subtype="pdf")
        att.add_header("Content-Disposition", "attachment", filename=f"etiqueta_recogida_{num}.pdf")
        msg.attach(att)

    context = ssl.create_default_context()
    try:
        if app_cfg.SMTP_SECURE and app_cfg.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(app_cfg.SMTP_HOST, app_cfg.SMTP_PORT, context=context, timeout=15) as s:
                s.login(app_cfg.SMTP_USER, app_cfg.SMTP_PASS); s.send_message(msg)
        else:
            with smtplib.SMTP(app_cfg.SMTP_HOST, app_cfg.SMTP_PORT, timeout=15) as s:
                s.starttls(context=context); s.login(app_cfg.SMTP_USER, app_cfg.SMTP_PASS); s.send_message(msg)
        logger.info(f"Email recogida enviado a {email_dst} para orden {num}")
    except Exception as e:
        logger.error(f"Error SMTP email recogida: {e}")


# ─── Labels ──────────────────────────────────────────────

@router.get("/etiqueta/{envio_id}")
async def descargar_etiqueta_endpoint(envio_id: str, formato: str = "PDF", user: dict = Depends(require_auth)):
    cfg = await _require_active()
    uid = cfg["uid_cliente"]

    envio = await db.gls_envios.find_one({"id": envio_id}, {"_id": 0})
    if not envio:
        # Fallback: try as referencia
        envio = await db.gls_envios.find_one({"referencia_interna": envio_id}, {"_id": 0})
    if not envio:
        raise HTTPException(404, "Envío no encontrado")

    ref = envio.get("referencia_interna") or envio.get("entidad_origen_id", "")
    is_pickup = envio.get("tipo") == "recogida"

    if is_pickup:
        result = await etiqueta_recogida(uid, ref, formato)
    else:
        result = await etiqueta_envio(uid, ref, formato)

    if not result.get("success"):
        await _log(envio.get("id", ""), "etiqueta_error", error=result.get("error", ""))
        raise HTTPException(404, result.get("error", "Error obteniendo etiqueta"))

    label_bytes = base64.b64decode(result["etiqueta_base64"])

    # Mark label as generated
    await db.gls_envios.update_one(
        {"id": envio.get("id")},
        {"$set": {"label_generada": True, "label_formato": formato.upper(),
                  "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    await _log(envio.get("id", ""), "etiqueta_descargada", f"Formato: {formato}")

    ext = formato.lower()
    codbarras = envio.get("gls_codbarras", envio_id)
    return Response(content=label_bytes, media_type=result["content_type"],
                    headers={"Content-Disposition": f"attachment; filename=etiqueta_{codbarras}.{ext}"})


# ─── Tracking ────────────────────────────────────────────

@router.get("/tracking/{envio_id}")
async def consultar_tracking_endpoint(envio_id: str, user: dict = Depends(require_auth)):
    cfg = await _require_active()
    uid = cfg["uid_cliente"]

    envio = await db.gls_envios.find_one({"id": envio_id}, {"_id": 0})
    if not envio:
        envio = await db.gls_envios.find_one({"referencia_interna": envio_id}, {"_id": 0})
    if not envio:
        raise HTTPException(404, "Envío no encontrado")

    ref = envio.get("referencia_interna") or envio.get("entidad_origen_id", "")
    result = await get_exp_cli(uid, ref)

    if result.get("success"):
        old_state = envio.get("estado_interno", "grabado")
        mapped = map_gls_status(result.get("codestado", ""))
        new_state = mapped["estado"]

        # Update gls_envios doc
        update_data = {
            "estado_interno": new_state,
            "estado_gls_codigo": result.get("codestado", ""),
            "estado_gls_texto": result.get("estado", ""),
            "tracking_json": result,
            "fecha_ultima_sync": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if result.get("incidencia"):
            update_data["incidencia_codigo"] = result.get("codestado", "")
            update_data["incidencia_texto"] = result.get("incidencia", "")
        if result.get("fecha_entrega"):
            update_data["entrega_fecha"] = result["fecha_entrega"]
        if result.get("nombre_receptor"):
            update_data["entrega_receptor"] = result["nombre_receptor"]
        if result.get("dni_receptor"):
            update_data["entrega_dni"] = result["dni_receptor"]
        if result.get("pod_url"):
            update_data["pod_url"] = result["pod_url"]

        await db.gls_envios.update_one({"id": envio["id"]}, {"$set": update_data})

        # Insert new tracking events
        for event in (result.get("tracking_list") or []):
            exists = await db.gls_tracking_events.find_one(
                {"envio_id": envio["id"], "fecha_evento": event["fecha"],
                 "codigo_evento": event.get("codigo", ""), "descripcion_evento": event.get("evento", "")},
                {"_id": 1}
            )
            if not exists:
                await db.gls_tracking_events.insert_one({
                    "id": str(uuid_mod.uuid4()),
                    "envio_id": envio["id"],
                    "fecha_evento": event.get("fecha", ""),
                    "codigo_evento": event.get("codigo", ""),
                    "descripcion_evento": event.get("evento", ""),
                    "plaza": event.get("plaza", ""),
                    "nombre_plaza": event.get("nombre_plaza", ""),
                    "raw_event": event,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })

        # Process state change business logic
        if old_state != new_state:
            await process_state_change(db, envio, old_state, new_state, result)
            # Update embedded array in order too
            await db.ordenes.update_one(
                {"gls_envios.id": envio["id"]},
                {"$set": {"gls_envios.$.estado_gls": new_state}}
            )

        await _log(envio["id"], "tracking_consulta", f"Estado: {new_state}")
    else:
        await _log(envio.get("id", ""), "tracking_error", error=result.get("error", ""))

    # Remove raw_response from client response
    safe = {k: v for k, v in result.items() if k != "raw_response"}
    safe["estado_interno"] = map_gls_status(result.get("codestado", "")) if result.get("success") else {}
    safe["badge"] = get_badge_info(safe.get("estado_interno", {}).get("estado", "desconocido")) if result.get("success") else {}
    return safe


# ─── Sync (batch polling) ────────────────────────────────

@router.post("/sync")
async def sync_tracking_batch(user: dict = Depends(require_master)):
    """Sync all non-final GLS shipments."""
    cfg = await _require_active()
    uid = cfg["uid_cliente"]

    envios = await db.gls_envios.find(
        {"estado_interno": {"$nin": list({"entregado", "entregado_parcial", "devuelto", "anulado", "cancelado", "error"})}},
        {"_id": 0, "id": 1, "referencia_interna": 1, "estado_interno": 1, "entidad_origen_id": 1}
    ).to_list(500)

    updated, errors, skipped = 0, 0, 0
    for envio in envios:
        ref = envio.get("referencia_interna") or envio.get("entidad_origen_id", "")
        if not ref:
            skipped += 1
            continue
        try:
            result = await get_exp_cli(uid, ref)
            if result.get("success"):
                old_state = envio.get("estado_interno", "grabado")
                mapped = map_gls_status(result.get("codestado", ""))
                new_state = mapped["estado"]

                up = {
                    "estado_interno": new_state,
                    "estado_gls_codigo": result.get("codestado", ""),
                    "estado_gls_texto": result.get("estado", ""),
                    "tracking_json": {k: v for k, v in result.items() if k != "raw_response"},
                    "fecha_ultima_sync": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                if result.get("entrega_fecha"):
                    up["entrega_fecha"] = result["entrega_fecha"]
                if result.get("nombre_receptor"):
                    up["entrega_receptor"] = result["nombre_receptor"]
                if result.get("dni_receptor"):
                    up["entrega_dni"] = result["dni_receptor"]
                if result.get("incidencia"):
                    up["incidencia_texto"] = result["incidencia"]

                await db.gls_envios.update_one({"id": envio["id"]}, {"$set": up})

                if old_state != new_state:
                    await process_state_change(db, envio, old_state, new_state, result)
                    await db.ordenes.update_one(
                        {"gls_envios.id": envio["id"]},
                        {"$set": {"gls_envios.$.estado_gls": new_state}}
                    )
                updated += 1
            else:
                errors += 1
        except Exception as e:
            logger.error(f"Sync error for {ref}: {e}")
            errors += 1

    await _log("batch", "sync_batch", f"Updated: {updated}, Errors: {errors}, Skipped: {skipped}")
    return {"success": True, "updated": updated, "errors": errors, "skipped": skipped, "total": len(envios)}


# ─── Cancel ──────────────────────────────────────────────

@router.post("/anular/{envio_id}")
async def anular_envio_endpoint(envio_id: str, user: dict = Depends(require_auth)):
    cfg = await _require_active()
    uid = cfg["uid_cliente"]

    envio = await db.gls_envios.find_one({"id": envio_id}, {"_id": 0})
    if not envio:
        raise HTTPException(404, "Envío no encontrado")
    if envio.get("estado_interno") in ("anulado", "cancelado", "entregado"):
        raise HTTPException(400, f"No se puede anular un envío en estado: {envio['estado_interno']}")

    ref = envio.get("referencia_interna") or envio.get("entidad_origen_id", "")
    result = await anula(uid, ref)

    if result.get("success"):
        await db.gls_envios.update_one(
            {"id": envio_id},
            {"$set": {"estado_interno": "anulado", "sync_status": "ok",
                      "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": user.get("email")}}
        )
        await db.ordenes.update_one(
            {"gls_envios.id": envio_id},
            {"$set": {"gls_envios.$.estado_gls": "anulado"}}
        )
        await _log(envio_id, "anular", "Envío anulado correctamente")
    else:
        await _log(envio_id, "anular_error", error=result.get("error", ""))

    return result


# ─── Admin Panel: List & Detail ──────────────────────────

@router.get("/envios")
async def listar_envios(
    page: int = 1, limit: int = 50, estado: str = "", tipo: str = "",
    busqueda: str = "", fecha: str = "",
    user: dict = Depends(require_auth)
):
    """List GLS shipments with filters for admin panel."""
    query = {}
    if estado:
        query["estado_interno"] = estado
    if tipo:
        query["tipo"] = tipo
    if busqueda:
        query["$or"] = [
            {"gls_codbarras": {"$regex": busqueda, "$options": "i"}},
            {"referencia_interna": {"$regex": busqueda, "$options": "i"}},
            {"entidad_origen_id": busqueda},
            {"destinatario.nombre": {"$regex": busqueda, "$options": "i"}},
            {"remitente.nombre": {"$regex": busqueda, "$options": "i"}},
        ]
    if fecha:
        query["created_at"] = {"$regex": f"^{fecha}"}

    total = await db.gls_envios.count_documents(query)
    skip = (page - 1) * limit
    envios = await db.gls_envios.find(query, {"_id": 0, "raw_request": 0, "raw_response": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    # Enrich with order number
    for e in envios:
        orden = await db.ordenes.find_one({"id": e.get("entidad_origen_id")}, {"_id": 0, "numero_orden": 1, "cliente": 1})
        if orden:
            e["numero_orden"] = orden.get("numero_orden", "")
            e["cliente_nombre"] = (orden.get("cliente") or {}).get("nombre", "")

    return {"envios": envios, "total": total, "page": page, "pages": (total + limit - 1) // limit}


@router.get("/envios/{envio_id}")
async def detalle_envio(envio_id: str, user: dict = Depends(require_auth)):
    """Get full detail of a GLS shipment including tracking events and logs."""
    envio = await db.gls_envios.find_one({"id": envio_id}, {"_id": 0})
    if not envio:
        raise HTTPException(404, "Envío no encontrado")

    # Get tracking events
    events = await db.gls_tracking_events.find(
        {"envio_id": envio_id}, {"_id": 0}
    ).sort("fecha_evento", -1).to_list(100)

    # Get logs
    logs = await db.gls_logs.find(
        {"envio_id": envio_id}, {"_id": 0}
    ).sort("fecha", -1).to_list(50)

    # Get order info
    orden = await db.ordenes.find_one(
        {"id": envio.get("entidad_origen_id")},
        {"_id": 0, "numero_orden": 1, "cliente": 1, "estado": 1, "dispositivo": 1}
    )

    envio["tracking_events"] = events
    envio["integration_logs"] = logs
    envio["orden"] = orden
    envio["badge"] = get_badge_info(envio.get("estado_interno", "desconocido"))

    return envio


# ─── Labels Search ───────────────────────────────────────

@router.get("/etiquetas")
async def listar_etiquetas(fecha: str = "", referencia: str = "", user: dict = Depends(require_auth)):
    """Search GLS labels by date or reference."""
    query = {}
    if referencia:
        query["$or"] = [
            {"gls_codbarras": {"$regex": referencia, "$options": "i"}},
            {"referencia_interna": {"$regex": referencia, "$options": "i"}},
            {"entidad_origen_id": referencia},
        ]
    elif fecha:
        query["created_at"] = {"$regex": f"^{fecha}"}
    else:
        hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        query["created_at"] = {"$regex": f"^{hoy}"}

    envios = await db.gls_envios.find(query, {"_id": 0, "raw_request": 0, "raw_response": 0}).sort("created_at", -1).to_list(100)

    etiquetas = []
    for e in envios:
        orden = await db.ordenes.find_one({"id": e.get("entidad_origen_id")}, {"_id": 0, "numero_orden": 1, "cliente": 1})
        etiquetas.append({
            "envio_id": e["id"],
            "orden_id": e.get("entidad_origen_id", ""),
            "numero_orden": (orden or {}).get("numero_orden", ""),
            "cliente_nombre": ((orden or {}).get("cliente") or {}).get("nombre", ""),
            "tipo": e.get("tipo", ""),
            "codbarras": e.get("gls_codbarras", ""),
            "estado": e.get("estado_interno", ""),
            "label_generada": e.get("label_generada", False),
            "created_at": e.get("created_at", ""),
        })

    return {"etiquetas": etiquetas, "total": len(etiquetas)}


# ─── Retry failed ────────────────────────────────────────

@router.post("/reintentar/{envio_id}")
async def reintentar_envio(envio_id: str, user: dict = Depends(require_auth)):
    """Retry a failed shipment creation."""
    cfg = await _require_active()
    envio = await db.gls_envios.find_one({"id": envio_id}, {"_id": 0})
    if not envio:
        raise HTTPException(404, "Envío no encontrado")
    if envio.get("estado_interno") != "error":
        raise HTTPException(400, "Solo se pueden reintentar envíos en estado error")

    rem = envio.get("remitente", {})
    dst = envio.get("destinatario", {})
    params = {
        "servicio": envio.get("servicio_gls", "1"), "horario": envio.get("horario_gls", "18"),
        "bultos": envio.get("bultos", "1"), "peso": envio.get("peso", "1"),
        "portes": envio.get("portes", "P"), "reembolso": envio.get("reembolso", "0"),
        "observaciones": envio.get("observaciones", ""),
        "referencia": envio.get("referencia_interna", ""),
    }

    envio_xml = build_envio_xml(rem, dst, params)
    result = await graba_servicios(cfg["uid_cliente"], envio_xml)

    if result.get("success"):
        await db.gls_envios.update_one({"id": envio_id}, {"$set": {
            "gls_codbarras": result["codbarras"], "gls_uid": result.get("uid_envio", ""),
            "estado_interno": "grabado", "sync_status": "ok", "sync_error": "",
            "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": user.get("email"),
        }})
        await _log(envio_id, "reintentar", f"Reintento exitoso: {result['codbarras']}")
    else:
        await db.gls_envios.update_one({"id": envio_id}, {"$set": {
            "sync_error": result.get("error", ""), "updated_at": datetime.now(timezone.utc).isoformat()
        }})
        await _log(envio_id, "reintentar_error", error=result.get("error", ""))

    return {k: v for k, v in result.items() if k not in ("raw_request", "raw_response")}


# ─── Maestros ────────────────────────────────────────────

@router.get("/servicios")
async def listar_servicios(user: dict = Depends(require_auth)):
    return {"servicios": SERVICIOS_GLS, "horarios": HORARIOS_GLS, "estados": ESTADO_BADGE}

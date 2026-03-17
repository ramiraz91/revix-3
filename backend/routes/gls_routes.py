"""
GLS Logistics API Routes.
Endpoints for: config, create shipments/pickups, labels, tracking, cancel.
"""
import logging
import base64
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from config import db
from auth import require_auth, require_master

from services.gls_service import (
    crear_envio, crear_recogida, obtener_etiqueta, obtener_etiqueta_recogida,
    consultar_envio, anular_envio, SERVICIOS_GLS, HORARIOS_GLS
)

logger = logging.getLogger("gls_routes")
router = APIRouter(prefix="/gls", tags=["gls"])

COLLECTION = "configuracion"
CONFIG_TIPO = "gls_config"


# ─── Helpers ──────────────────────────────────────────────

async def _get_gls_config() -> dict:
    doc = await db.configuracion.find_one({"tipo": CONFIG_TIPO}, {"_id": 0})
    return doc.get("datos", {}) if doc else {}


async def _require_gls_active():
    cfg = await _get_gls_config()
    if not cfg.get("activo"):
        raise HTTPException(status_code=400, detail="Integración GLS no está activada")
    if not cfg.get("uid_cliente"):
        raise HTTPException(status_code=400, detail="UID de cliente GLS no configurado")
    return cfg


# ─── Config endpoints ────────────────────────────────────

@router.get("/config")
async def get_gls_config(user: dict = Depends(require_master)):
    cfg = await _get_gls_config()
    return {
        "activo": cfg.get("activo", False),
        "uid_cliente": cfg.get("uid_cliente", ""),
        "remitente": cfg.get("remitente", {
            "nombre": "revix.es",
            "direccion": "Julio alarcon 8, Local",
            "poblacion": "Cordoba",
            "cp": "14007",
            "telefono": "604319223",
            "nif": "31018296J"
        }),
        "servicio_defecto": cfg.get("servicio_defecto", "1"),
        "horario_defecto": cfg.get("horario_defecto", "18"),
        "portes_defecto": cfg.get("portes_defecto", "P"),
        "formato_etiqueta": cfg.get("formato_etiqueta", "PDF"),
        "polling_activo": cfg.get("polling_activo", False),
        "polling_intervalo_horas": cfg.get("polling_intervalo_horas", 4),
        "servicios_disponibles": SERVICIOS_GLS,
        "horarios_disponibles": HORARIOS_GLS,
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
async def save_gls_config(payload: GLSConfigPayload, user: dict = Depends(require_master)):
    data = payload.dict()
    await db.configuracion.update_one(
        {"tipo": CONFIG_TIPO},
        {"$set": {
            "tipo": CONFIG_TIPO,
            "datos": data,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user.get("email", "sistema")
        }},
        upsert=True
    )
    return {"success": True, "message": "Configuración GLS guardada"}


# ─── Shipment creation ───────────────────────────────────

class CrearEnvioPayload(BaseModel):
    orden_id: str
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
async def crear_envio_gls(payload: CrearEnvioPayload, user: dict = Depends(require_auth)):
    cfg = await _require_gls_active()
    
    envio_data = payload.dict()
    envio_data["servicio"] = envio_data["servicio"] or cfg.get("servicio_defecto", "1")
    envio_data["horario"] = envio_data["horario"] or cfg.get("horario_defecto", "18")
    envio_data["portes"] = envio_data["portes"] or cfg.get("portes_defecto", "P")
    envio_data["referencia"] = payload.orden_id

    result = await crear_envio(cfg, envio_data)

    if result.get("success"):
        # Save to order
        gls_envio = {
            "id": str(uuid.uuid4()),
            "tipo": "envio",
            "codbarras": result["codbarras"],
            "uid_envio": result.get("uid_envio", ""),
            "referencia": payload.orden_id,
            "servicio": envio_data["servicio"],
            "nombre_dst": payload.nombre_dst,
            "cp_dst": payload.cp_dst,
            "estado_gls": "grabado",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": user.get("email", "sistema"),
        }
        await db.ordenes.update_one(
            {"id": payload.orden_id},
            {
                "$push": {"gls_envios": gls_envio},
                "$set": {
                    "codigo_recogida_salida": result["codbarras"],
                    "agencia_envio": "GLS",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        return {**result, "gls_envio": gls_envio}
    
    return result


class CrearRecogidaPayload(BaseModel):
    orden_id: str
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
async def crear_recogida_gls(payload: CrearRecogidaPayload, user: dict = Depends(require_auth)):
    cfg = await _require_gls_active()
    
    rec_data = payload.dict()
    rec_data["servicio"] = rec_data["servicio"] or cfg.get("servicio_defecto", "1")
    rec_data["horario"] = rec_data["horario"] or cfg.get("horario_defecto", "18")
    rec_data["referencia"] = payload.orden_id
    if not rec_data["fecha"]:
        rec_data["fecha"] = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    result = await crear_recogida(cfg, rec_data)

    if result.get("success"):
        gls_recogida = {
            "id": str(uuid.uuid4()),
            "tipo": "recogida",
            "codbarras": result["codbarras"],
            "uid_envio": result.get("uid_envio", ""),
            "referencia": payload.orden_id,
            "servicio": rec_data["servicio"],
            "nombre_org": payload.nombre_org,
            "cp_org": payload.cp_org,
            "estado_gls": "grabado",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": user.get("email", "sistema"),
        }
        await db.ordenes.update_one(
            {"id": payload.orden_id},
            {
                "$push": {"gls_envios": gls_recogida},
                "$set": {
                    "codigo_recogida_entrada": result["codbarras"],
                    "agencia_envio": "GLS",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )

        # Enviar email al cliente con etiqueta de recogida
        try:
            await _enviar_email_recogida(cfg, payload.orden_id, result["codbarras"])
        except Exception as e:
            logger.error(f"Error enviando email de recogida: {e}")

        return {**result, "gls_envio": gls_recogida}
    
    return result


# ─── Labels ──────────────────────────────────────────────

async def _enviar_email_recogida(cfg: dict, orden_id: str, codbarras: str):
    """Envía email al cliente con instrucciones de envío y etiqueta GLS adjunta."""
    import smtplib
    import ssl
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.application import MIMEApplication
    import config as app_cfg

    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        return

    cliente = orden.get("cliente") or {}
    email_dst = cliente.get("email", "")
    if not email_dst:
        logger.info(f"No se envía email de recogida: cliente sin email en orden {orden_id}")
        return

    if not app_cfg.SMTP_CONFIGURED:
        logger.warning("SMTP no configurado, no se puede enviar email de recogida")
        return

    # Obtener etiqueta PDF
    etiqueta_pdf = None
    try:
        label_result = await obtener_etiqueta_recogida(cfg["uid_cliente"], orden_id, "PDF")
        if label_result.get("success") and label_result.get("etiqueta_base64"):
            etiqueta_pdf = base64.b64decode(label_result["etiqueta_base64"])
    except Exception as e:
        logger.error(f"Error obteniendo etiqueta para email: {e}")

    nombre_cliente = cliente.get("nombre", "Cliente")
    numero_orden = orden.get("numero_orden", orden_id)
    dispositivo = orden.get("dispositivo", {})
    disp_texto = f"{dispositivo.get('marca', '')} {dispositivo.get('modelo', '')}".strip() or "su dispositivo"

    html = f'''<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:#f5f5f5;">
  <div style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:8px;overflow:hidden;margin-top:20px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
    
    <div style="background:#1a1a2e;color:#ffffff;padding:30px 40px;text-align:center;">
      <h1 style="margin:0;font-size:22px;font-weight:600;">Instrucciones de Envío</h1>
      <p style="margin:8px 0 0;opacity:0.85;font-size:14px;">Orden {numero_orden}</p>
    </div>

    <div style="padding:30px 40px;">
      <p style="font-size:16px;color:#333;">Hola <strong>{nombre_cliente}</strong>,</p>
      
      <p style="font-size:14px;color:#555;line-height:1.6;">
        Le confirmamos que hemos generado la etiqueta de recogida para su <strong>{disp_texto}</strong>.
        GLS pasará a recoger el paquete en la dirección indicada.
      </p>

      <div style="background:#FFF8E1;border-left:4px solid #F9A825;padding:20px;border-radius:6px;margin:24px 0;">
        <h3 style="margin:0 0 12px;color:#E65100;font-size:15px;">Antes de entregar el paquete, por favor:</h3>
        <ol style="margin:0;padding-left:20px;color:#555;font-size:14px;line-height:2;">
          <li><strong>Restablezca el dispositivo a valores de fábrica</strong> (borrar datos y cuentas)</li>
          <li><strong>Retire la tarjeta SIM</strong> y cualquier tarjeta de memoria</li>
          <li><strong>No incluya accesorios</strong>: ni cargador, ni cable, ni funda, ni protector</li>
          <li><strong>Embale el dispositivo correctamente</strong>: use papel burbuja o similar y una caja resistente</li>
          <li><strong>Solo el dispositivo</strong> dentro del paquete</li>
        </ol>
      </div>

      <div style="background:#E8F5E9;border-left:4px solid #43A047;padding:16px;border-radius:6px;margin:20px 0;">
        <p style="margin:0;font-size:14px;color:#2E7D32;">
          <strong>Código de seguimiento:</strong> 
          <span style="font-family:monospace;font-size:15px;background:#fff;padding:4px 8px;border-radius:4px;">{codbarras}</span>
        </p>
      </div>

      {"<p style='font-size:14px;color:#555;'>Encontrará la <strong>etiqueta de envío adjunta</strong> en formato PDF. Imprímala y péguela en el exterior del paquete de forma visible.</p>" if etiqueta_pdf else "<p style='font-size:14px;color:#888;'>La etiqueta de envío estará disponible próximamente. Le informaremos cuando pueda descargarla.</p>"}

      <div style="border-top:1px solid #eee;margin-top:24px;padding-top:16px;">
        <p style="font-size:13px;color:#888;">Si tiene alguna duda, contacte con nosotros en <a href="mailto:help@revix.es" style="color:#1a1a2e;">help@revix.es</a> o llámenos al 604 319 223.</p>
      </div>
    </div>

    <div style="background:#f8f8f8;padding:16px 40px;text-align:center;border-top:1px solid #eee;">
      <p style="margin:0;font-size:12px;color:#999;">revix.es &mdash; Servicio técnico profesional</p>
    </div>
  </div>
</body>
</html>'''

    # Construir email con adjunto
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"Instrucciones de Envío - Orden {numero_orden}"
    msg["From"] = app_cfg.SMTP_FROM or f"Revix <{app_cfg.SMTP_USER}>"
    msg["To"] = email_dst
    msg["Reply-To"] = app_cfg.SMTP_REPLY_TO or "help@revix.es"

    msg.attach(MIMEText(html, "html", "utf-8"))

    if etiqueta_pdf:
        pdf_attachment = MIMEApplication(etiqueta_pdf, _subtype="pdf")
        pdf_attachment.add_header("Content-Disposition", "attachment", filename=f"etiqueta_recogida_{numero_orden}.pdf")
        msg.attach(pdf_attachment)

    context = ssl.create_default_context()
    try:
        if app_cfg.SMTP_SECURE and app_cfg.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(app_cfg.SMTP_HOST, app_cfg.SMTP_PORT, context=context, timeout=15) as server:
                server.login(app_cfg.SMTP_USER, app_cfg.SMTP_PASS)
                server.send_message(msg)
        else:
            with smtplib.SMTP(app_cfg.SMTP_HOST, app_cfg.SMTP_PORT, timeout=15) as server:
                server.starttls(context=context)
                server.login(app_cfg.SMTP_USER, app_cfg.SMTP_PASS)
                server.send_message(msg)
        logger.info(f"Email de recogida enviado a {email_dst} para orden {numero_orden}")
    except Exception as e:
        logger.error(f"Error SMTP enviando email de recogida a {email_dst}: {e}")

@router.get("/etiqueta/{referencia}")
async def descargar_etiqueta(referencia: str, tipo: str = "PDF", user: dict = Depends(require_auth)):
    cfg = await _require_gls_active()
    result = await obtener_etiqueta(cfg["uid_cliente"], referencia, tipo)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Error obteniendo etiqueta"))
    
    label_bytes = base64.b64decode(result["etiqueta_base64"])
    ext = tipo.lower()
    return Response(
        content=label_bytes,
        media_type=result["content_type"],
        headers={"Content-Disposition": f"attachment; filename=etiqueta_{referencia}.{ext}"}
    )


@router.get("/etiqueta-recogida/{referencia}")
async def descargar_etiqueta_recogida(referencia: str, tipo: str = "PDF", user: dict = Depends(require_auth)):
    cfg = await _require_gls_active()
    result = await obtener_etiqueta_recogida(cfg["uid_cliente"], referencia, tipo)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Error obteniendo etiqueta"))
    
    label_bytes = base64.b64decode(result["etiqueta_base64"])
    ext = tipo.lower()
    return Response(
        content=label_bytes,
        media_type=result["content_type"],
        headers={"Content-Disposition": f"attachment; filename=etiqueta_recogida_{referencia}.{ext}"}
    )


# ─── Tracking ────────────────────────────────────────────

@router.get("/tracking/{referencia}")
async def consultar_tracking(referencia: str, user: dict = Depends(require_auth)):
    cfg = await _require_gls_active()
    result = await consultar_envio(cfg["uid_cliente"], referencia)
    
    if result.get("success"):
        # Update order with latest tracking
        await db.ordenes.update_one(
            {"id": referencia},
            {"$set": {
                "gls_ultimo_tracking": result,
                "gls_tracking_updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    return result


@router.post("/tracking/poll")
async def poll_tracking_all(user: dict = Depends(require_master)):
    """Poll tracking for all orders with active GLS shipments."""
    cfg = await _require_gls_active()
    uid = cfg["uid_cliente"]
    
    ordenes = await db.ordenes.find(
        {"gls_envios": {"$exists": True, "$ne": []}, "estado": {"$nin": ["entregado", "cancelado", "irreparable"]}},
        {"_id": 0, "id": 1, "gls_envios": 1, "numero_orden": 1}
    ).to_list(200)
    
    updated = 0
    errors = 0
    for orden in ordenes:
        for envio in (orden.get("gls_envios") or []):
            ref = envio.get("referencia") or orden["id"]
            try:
                result = await consultar_envio(uid, ref)
                if result.get("success"):
                    await db.ordenes.update_one(
                        {"id": orden["id"]},
                        {"$set": {
                            "gls_ultimo_tracking": result,
                            "gls_tracking_updated_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    updated += 1
            except Exception as e:
                logger.error(f"Error polling tracking {ref}: {e}")
                errors += 1
    
    return {"success": True, "updated": updated, "errors": errors, "total": len(ordenes)}


# ─── Cancel ──────────────────────────────────────────────

@router.post("/anular/{referencia}")
async def anular_envio_gls(referencia: str, user: dict = Depends(require_auth)):
    cfg = await _require_gls_active()
    result = await anular_envio(cfg["uid_cliente"], referencia)
    
    if result.get("success"):
        await db.ordenes.update_one(
            {"gls_envios.referencia": referencia},
            {"$set": {"gls_envios.$.estado_gls": "anulado"}}
        )
    return result


# ─── Maestros ─────────────────────────────────────────────

@router.get("/servicios")
async def listar_servicios(user: dict = Depends(require_auth)):
    return {"servicios": SERVICIOS_GLS, "horarios": HORARIOS_GLS}

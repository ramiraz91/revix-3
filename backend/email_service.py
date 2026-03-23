"""
email_service.py — Servicio SMTP mejorado para Revix CRM
Mejoras:
  - Carga de variables con fallback explícito y validación al arrancar
  - Reintento automático en caso de fallo de conexión
  - Soporte para puerto 587 (TLS) y 465 (SSL) correctamente diferenciados
  - Cola asíncrona para no bloquear el hilo principal
  - Diagnóstico claro en los logs cuando falla
  - Nuevas notificaciones: presupuesto, factura, bienvenida
"""

import smtplib
import ssl
import os
import logging
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass

# Carga .env desde la raíz del proyecto
load_dotenv(Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)


# ── Configuración con validación ──────────────────────────────────────────────

@dataclass
class SMTPConfig:
    host:     str
    port:     int
    user:     str
    password: str
    from_addr:str
    reply_to: str
    secure:   bool

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.user and self.password)

    def diagnostico(self) -> str:
        lineas = [
            f"  SMTP_HOST : {'✅ ' + self.host if self.host else '❌ no definido'}",
            f"  SMTP_PORT : {self.port}",
            f"  SMTP_USER : {'✅ ' + self.user if self.user else '❌ no definido'}",
            f"  SMTP_PASS : {'✅ definida' if self.password else '❌ no definida'}",
            f"  SMTP_FROM : {self.from_addr}",
            f"  Modo      : {'SSL (465)' if self.port == 465 else 'STARTTLS (587)'}",
        ]
        return "\n".join(lineas)


def _cargar_config() -> SMTPConfig:
    cfg = SMTPConfig(
        host      = os.getenv("SMTP_HOST", "").strip(),
        port      = int(os.getenv("SMTP_PORT", "465")),
        user      = os.getenv("SMTP_USER", "").strip(),
        password  = os.getenv("SMTP_PASS", "").strip(),
        from_addr = os.getenv("SMTP_FROM", "Revix <notificaciones@revix.es>").strip(),
        reply_to  = os.getenv("SMTP_REPLY_TO", "help@revix.es").strip(),
        secure    = os.getenv("SMTP_SECURE", "true").lower() == "true",
    )
    if not cfg.is_configured:
        logger.warning(
            "⚠️  SMTP no configurado correctamente. "
            "Los emails no se enviarán hasta que definas las variables.\n%s",
            cfg.diagnostico()
        )
    else:
        logger.info("📧 SMTP configurado:\n%s", cfg.diagnostico())
    return cfg


CONFIG = _cargar_config()
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://revix.es").rstrip("/")


# ── Template HTML ─────────────────────────────────────────────────────────────

def _build_html(titulo: str, contenido: str,
                link_url: Optional[str] = None,
                link_text: str = "Ver en Revix") -> str:
    boton = ""
    if link_url:
        boton = f'''
        <tr><td style="padding:20px 30px 30px;">
          <a href="{link_url}"
             style="display:inline-block;background:#2563eb;color:#fff;
                    padding:12px 28px;border-radius:6px;text-decoration:none;
                    font-weight:600;font-size:14px;">{link_text}</a>
        </td></tr>'''

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f1f5f9;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#f1f5f9;padding:20px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:8px;
                  box-shadow:0 1px 3px rgba(0,0,0,0.1);">
      <tr><td style="background:#1e40af;padding:20px 30px;border-radius:8px 8px 0 0;">
        <h1 style="margin:0;color:#fff;font-size:20px;letter-spacing:-0.5px;">Revix</h1>
      </td></tr>
      <tr><td style="padding:30px 30px 10px;">
        <h2 style="margin:0 0 15px;color:#1e293b;font-size:18px;">{titulo}</h2>
        <div style="color:#475569;font-size:14px;line-height:1.6;">{contenido}</div>
      </td></tr>
      {boton}
      <tr><td style="padding:20px 30px;border-top:1px solid #e2e8f0;">
        <p style="margin:0;color:#94a3b8;font-size:11px;">
          Correo automático de Revix CRM · No respondas a este mensaje ·
          <a href="{FRONTEND_URL}" style="color:#94a3b8;">revix.es</a>
        </p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""


# ── Envío con reintento ───────────────────────────────────────────────────────

def _enviar_smtp(msg: MIMEMultipart, intentos: int = 3) -> bool:
    """Intenta enviar el mensaje hasta `intentos` veces."""
    context = ssl.create_default_context()
    ultimo_error = None

    for intento in range(1, intentos + 1):
        try:
            if CONFIG.port == 465:
                # SSL directo — mail.privateemail.com puerto 465
                with smtplib.SMTP_SSL(
                    CONFIG.host, CONFIG.port,
                    context=context, timeout=15
                ) as server:
                    server.login(CONFIG.user, CONFIG.password)
                    server.send_message(msg)
            else:
                # STARTTLS — puerto 587
                with smtplib.SMTP(
                    CONFIG.host, CONFIG.port, timeout=15
                ) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(CONFIG.user, CONFIG.password)
                    server.send_message(msg)

            logger.info("✅ Email enviado a %s: %s", msg["To"], msg["Subject"])
            return True

        except smtplib.SMTPAuthenticationError as e:
            # Error de credenciales — no tiene sentido reintentar
            logger.error(
                "❌ Error de autenticación SMTP. "
                "Revisa SMTP_USER y SMTP_PASS en tus variables de entorno.\n"
                "  Usuario: %s\n  Error: %s", CONFIG.user, e
            )
            return False

        except smtplib.SMTPConnectError as e:
            ultimo_error = e
            logger.warning(
                "⚠️  Intento %d/%d — No se pudo conectar a %s:%d: %s",
                intento, intentos, CONFIG.host, CONFIG.port, e
            )

        except smtplib.SMTPException as e:
            ultimo_error = e
            logger.warning("⚠️  Intento %d/%d — Error SMTP: %s", intento, intentos, e)

        except Exception as e:
            ultimo_error = e
            logger.warning("⚠️  Intento %d/%d — Error inesperado: %s", intento, intentos, e)

        if intento < intentos:
            import time
            time.sleep(2 * intento)  # espera 2s, 4s entre reintentos

    logger.error(
        "❌ Email fallido tras %d intentos a %s. Último error: %s",
        intentos, msg["To"], ultimo_error
    )
    return False


def send_email(
    to: str,
    subject: str,
    titulo: str,
    contenido: str,
    link_url: Optional[str] = None,
    link_text: str = "Ver en Revix",
) -> bool:
    """Envía un email HTML. Devuelve True si tuvo éxito."""
    if not CONFIG.is_configured:
        logger.warning("📧 SMTP no configurado — email a %s omitido", to)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = CONFIG.from_addr
    msg["To"]      = to
    msg["Reply-To"]= CONFIG.reply_to

    html = _build_html(titulo, contenido, link_url, link_text)
    msg.attach(MIMEText(html, "html", "utf-8"))

    return _enviar_smtp(msg)


async def send_email_async(
    to: str,
    subject: str,
    titulo: str,
    contenido: str,
    link_url: Optional[str] = None,
    link_text: str = "Ver en Revix",
) -> bool:
    """
    Versión async — no bloquea FastAPI mientras envía.
    Úsala en los endpoints con: await send_email_async(...)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: send_email(to, subject, titulo, contenido, link_url, link_text)
    )


# ── Notificaciones específicas ────────────────────────────────────────────────

async def notificar_cambio_estado(
    to: str, orden_numero: str, auth_code: str,
    nuevo_estado: str, orden_id: str
) -> bool:
    """Notifica al cliente un cambio de estado en su orden."""
    codigo = auth_code or orden_numero
    link   = f"{FRONTEND_URL}/ordenes/{orden_id}"

    ETIQUETAS_ESTADO = {
        "pendiente_recibir": "Pendiente de recibir",
        "entrada":           "Entrada registrada",
        "recibida":          "Dispositivo recibido",
        "cuarentena":        "En cuarentena",
        "diagnostico":       "En diagnóstico",
        "esperando_ppto":    "Presupuesto enviado",
        "aprobada":          "Presupuesto aceptado",
        "en_taller":         "En reparación",
        "en_reparacion":     "En reparación",
        "re_presupuestar":   "Requiere nuevo presupuesto",
        "reparado":          "Reparación completada",
        "control_calidad":   "Control de calidad",
        "validacion":        "En validación",
        "lista":             "¡Lista para recoger!",
        "enviado":           "Enviada al cliente",
        "enviada":           "Enviada al cliente",
        "cancelado":         "Cancelada",
        "cancelada":         "Cancelada",
        "garantia":          "En garantía",
        "reemplazo":         "En proceso de reemplazo",
        "irreparable":       "Irreparable",
    }
    etiqueta = ETIQUETAS_ESTADO.get(nuevo_estado, nuevo_estado)

    contenido = f"""
    <p>Le informamos que su orden ha cambiado de estado:</p>
    <table style="margin:15px 0;border-collapse:collapse;width:100%;">
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Código</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;">{codigo}</td>
      </tr>
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Estado</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;color:#2563eb;font-weight:600;">{etiqueta}</td>
      </tr>
    </table>
    <p>Puede consultar el estado de su orden en cualquier momento a través del enlace de abajo.</p>"""

    return await send_email_async(
        to=to,
        subject=f"Revix — Su orden {codigo}: {etiqueta}",
        titulo="Actualización de su Orden",
        contenido=contenido,
        link_url=link,
        link_text="Ver Estado de mi Orden",
    )


async def notificar_material_pendiente(
    to: str, pieza: str, orden_numero: str, orden_id: str
) -> bool:
    """Notificación interna — material pendiente de aprobación."""
    link = f"{FRONTEND_URL}/ordenes/{orden_id}"
    contenido = f"""
    <p>El técnico ha solicitado material para la orden <strong>{orden_numero}</strong>:</p>
    <table style="margin:15px 0;border-collapse:collapse;width:100%;">
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Material</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;">{pieza}</td>
      </tr>
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Orden</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;">{orden_numero}</td>
      </tr>
    </table>
    <p>Accede a la orden para aprobar o rechazar el material solicitado.</p>"""

    return await send_email_async(
        to=to,
        subject=f"Revix — Material pendiente en orden {orden_numero}",
        titulo="Material Pendiente de Aprobación",
        contenido=contenido,
        link_url=link,
        link_text="Aprobar Material",
    )


async def notificar_presupuesto_enviado(
    to: str, orden_numero: str, total: float,
    orden_id: str, dias_validez: int = 15
) -> bool:
    """Notifica al cliente que tiene un presupuesto pendiente de aprobar."""
    link = f"{FRONTEND_URL}/ordenes/{orden_id}"
    contenido = f"""
    <p>Hemos preparado un presupuesto para la reparación de su dispositivo:</p>
    <table style="margin:15px 0;border-collapse:collapse;width:100%;">
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Orden</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;">{orden_numero}</td>
      </tr>
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Total</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;font-weight:600;color:#2563eb;">{total:.2f} €</td>
      </tr>
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Válido hasta</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;">{dias_validez} días desde hoy</td>
      </tr>
    </table>
    <p>Por favor, accede al enlace para aceptar o rechazar el presupuesto.</p>"""

    return await send_email_async(
        to=to,
        subject=f"Revix — Presupuesto para su orden {orden_numero}",
        titulo="Presupuesto Pendiente de Aprobación",
        contenido=contenido,
        link_url=link,
        link_text="Ver y Aprobar Presupuesto",
    )


async def notificar_orden_lista(
    to: str, orden_numero: str, auth_code: str, orden_id: str
) -> bool:
    """Avisa al cliente que su dispositivo está listo para recoger o enviar."""
    codigo = auth_code or orden_numero
    link   = f"{FRONTEND_URL}/ordenes/{orden_id}"
    contenido = f"""
    <p>¡Buenas noticias! Su dispositivo ya está reparado y listo.</p>
    <table style="margin:15px 0;border-collapse:collapse;width:100%;">
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Código</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;">{codigo}</td>
      </tr>
    </table>
    <p>En breve nos pondremos en contacto para coordinar la entrega o el envío.</p>"""

    return await send_email_async(
        to=to,
        subject=f"Revix — ¡Su dispositivo está listo! ({codigo})",
        titulo="¡Su Dispositivo Está Listo!",
        contenido=contenido,
        link_url=link,
        link_text="Ver mi Orden",
    )


async def notificar_factura_emitida(
    to: str, factura_numero: str, total: float,
    orden_numero: str, orden_id: str
) -> bool:
    """Notifica al cliente que se ha emitido su factura."""
    link = f"{FRONTEND_URL}/ordenes/{orden_id}"
    contenido = f"""
    <p>Le informamos que hemos emitido la factura correspondiente a su reparación:</p>
    <table style="margin:15px 0;border-collapse:collapse;width:100%;">
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Nº Factura</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;">{factura_numero}</td>
      </tr>
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Orden</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;">{orden_numero}</td>
      </tr>
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Total</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;font-weight:600;color:#2563eb;">{total:.2f} €</td>
      </tr>
    </table>
    <p>Puede descargar su factura accediendo al enlace de abajo.</p>"""

    return await send_email_async(
        to=to,
        subject=f"Revix — Factura {factura_numero}",
        titulo="Factura Emitida",
        contenido=contenido,
        link_url=link,
        link_text="Ver Factura",
    )


async def notificar_bienvenida(
    to: str, nombre: str
) -> bool:
    """Email de bienvenida para nuevos clientes."""
    contenido = f"""
    <p>Hola <strong>{nombre}</strong>,</p>
    <p>¡Bienvenido/a a Revix! Nos alegra tenerte como cliente.</p>
    <p>A partir de ahora podrás:</p>
    <ul style="color:#475569;padding-left:20px;">
      <li>Seguir el estado de tus reparaciones en tiempo real</li>
      <li>Recibir notificaciones cuando tu dispositivo esté listo</li>
      <li>Consultar el historial de tus órdenes y facturas</li>
    </ul>
    <p>Si tienes cualquier duda, no dudes en contactarnos.</p>
    <p>¡Gracias por confiar en nosotros!</p>"""

    return await send_email_async(
        to=to,
        subject="¡Bienvenido/a a Revix!",
        titulo=f"¡Hola {nombre}!",
        contenido=contenido,
        link_url=FRONTEND_URL,
        link_text="Visitar Revix",
    )


# ── Test de conexión ──────────────────────────────────────────────────────────

def test_conexion_smtp() -> dict:
    """
    Prueba la conexión SMTP sin enviar email.
    Útil para verificar desde /api/health o desde consola.
    """
    if not CONFIG.is_configured:
        return {"ok": False, "error": "SMTP no configurado", "config": CONFIG.diagnostico()}

    try:
        context = ssl.create_default_context()
        if CONFIG.port == 465:
            with smtplib.SMTP_SSL(CONFIG.host, CONFIG.port, context=context, timeout=10) as s:
                s.login(CONFIG.user, CONFIG.password)
        else:
            with smtplib.SMTP(CONFIG.host, CONFIG.port, timeout=10) as s:
                s.ehlo()
                s.starttls(context=context)
                s.login(CONFIG.user, CONFIG.password)
        return {"ok": True, "host": CONFIG.host, "port": CONFIG.port, "user": CONFIG.user}
    except smtplib.SMTPAuthenticationError:
        return {"ok": False, "error": "Credenciales incorrectas — revisa SMTP_USER y SMTP_PASS"}
    except smtplib.SMTPConnectError as e:
        return {"ok": False, "error": f"No se pudo conectar a {CONFIG.host}:{CONFIG.port} — {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

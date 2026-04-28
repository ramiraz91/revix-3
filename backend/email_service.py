"""
email_service.py — Servicio de emails con Resend para Revix CRM
Reemplaza la implementación SMTP anterior por la API de Resend.

Arquitectura de URLs (importante):
  · Emails para CLIENTES finales → siempre página pública /consulta?codigo={token}
    Construir con `_build_client_link(token)`.
  · Emails para STAFF interno    → /crm/... o /ordenes/... (requieren login)
    Construir con `_build_admin_link(path)`.
  · `client_safe_email_html()` valida en runtime que un email de cliente
    NO contenga URLs internas (/ordenes/, /crm/, /dashboard/).
"""

import os
import asyncio
import logging
import re
import resend
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Carga .env desde la raíz del proyecto
load_dotenv(Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)

# ── Configuración Resend ──────────────────────────────────────────────────────

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "notificaciones@revix.es").strip()

# ── FRONTEND_URL con salvaguarda anti-preview ─────────────────────────────────
# En production, si el deployment inyecta accidentalmente una URL de preview
# (o de localhost), los emails que se envíen a clientes reales llevarían links
# inservibles. Filtramos dominios no válidos y caemos al dominio oficial.
_UNSAFE_URL_PATTERNS = (
    "preview.emergentagent.com", "preview.emergent.host",
    "emergentagent.com", "emergent.host",
    "localhost", "127.0.0.1", "0.0.0.0",
    ".local", ".test",
)
_PUBLIC_FALLBACK = "https://revix.es"


def _safe_public_url(raw: Optional[str]) -> str:
    """Devuelve una URL pública segura. Filtra previews/localhost."""
    val = (raw or "").strip().rstrip("/")
    if not val:
        return _PUBLIC_FALLBACK
    low = val.lower()
    if not (low.startswith("http://") or low.startswith("https://")):
        return _PUBLIC_FALLBACK
    if any(p in low for p in _UNSAFE_URL_PATTERNS):
        logger.warning(
            "⚠️ FRONTEND_URL detectada como no-producción (%s). "
            "Usando fallback %s para links de emails.",
            val, _PUBLIC_FALLBACK,
        )
        return _PUBLIC_FALLBACK
    return val


FRONTEND_URL = _safe_public_url(os.getenv("FRONTEND_URL"))


# ── Helpers únicos para construir URLs ────────────────────────────────────────
# REGLA: cualquier email enviado a un CLIENTE final debe usar _build_client_link.
# REGLA: emails internos (admin/técnico) pueden usar _build_admin_link.

def _build_client_link(token_seguimiento: Optional[str] = None) -> str:
    """URL de la página pública de seguimiento (sin login).

    Si hay token, prerellena el código de búsqueda. Si no, lleva al portal
    público donde el cliente puede introducir su código manualmente.

    Esta es la ÚNICA función que construye URLs para emails de cliente.
    """
    base = f"{FRONTEND_URL}/consulta"
    if token_seguimiento:
        return f"{base}?codigo={token_seguimiento}"
    return base


def _build_admin_link(path: str) -> str:
    """URL para enlaces internos (CRM). Sólo para emails dirigidos a staff.

    `path` debe empezar por '/' y normalmente apunta a /crm/... o /ordenes/...
    """
    if not path.startswith("/"):
        path = "/" + path
    return f"{FRONTEND_URL}{path}"


# Patrones que NUNCA deben aparecer en un href de email de cliente.
_CLIENT_FORBIDDEN_PATHS = re.compile(
    r"href\s*=\s*['\"][^'\"]*?(/ordenes/|/crm/|/dashboard/|/inventario|/proveedores|/clientes/[a-f0-9-]{8,})",
    re.IGNORECASE,
)


def _assert_client_safe(html: str, where: str = "") -> None:
    """Valida que un HTML destinado a CLIENTE no contenga URLs internas.

    Lanza un warning crítico (y, en debug, AssertionError) si encuentra
    enlaces hacia rutas internas que requieren login.
    """
    m = _CLIENT_FORBIDDEN_PATHS.search(html)
    if m:
        msg = (
            f"🚨 [email-leak] Email de CLIENTE contiene URL interna del CRM: "
            f"'{m.group(0)[:120]}' en {where}. Debe usar /consulta?codigo=…"
        )
        logger.error(msg)
        if os.getenv("EMAIL_STRICT_CLIENT_LINKS", "1") == "1":
            raise AssertionError(msg)


# Configurar Resend
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
    logger.info("📧 Resend configurado correctamente con remitente: %s", SENDER_EMAIL)
else:
    logger.warning("⚠️ RESEND_API_KEY no configurada. Los emails no se enviarán.")


def is_configured() -> bool:
    """Verifica si Resend está configurado."""
    return bool(RESEND_API_KEY)


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
          Correo automatico de Revix CRM - No respondas a este mensaje -
          <a href="{FRONTEND_URL}" style="color:#94a3b8;">revix.es</a>
        </p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""


# ── Envio con Resend ──────────────────────────────────────────────────────────

def send_email(
    to: str,
    subject: str,
    titulo: str,
    contenido: str,
    link_url: Optional[str] = None,
    link_text: str = "Ver en Revix",
    audience: str = "client",
) -> bool:
    """Envia un email HTML usando Resend. Devuelve True si tuvo exito.

    `audience`:
      - "client" (default): valida que el HTML no contenga URLs internas del CRM.
      - "admin": permite URLs internas (/crm/, /ordenes/, etc).
    """
    if not is_configured():
        logger.warning("📧 Resend no configurado — email a %s omitido", to)
        return False

    html = _build_html(titulo, contenido, link_url, link_text)

    # Salvaguarda anti-leak: emails a cliente no pueden tener URLs internas.
    if audience == "client":
        _assert_client_safe(html, where=f"send_email(subject={subject!r})")

    params = {
        "from": f"Revix <{SENDER_EMAIL}>",
        "to": [to],
        "subject": subject,
        "html": html,
        "reply_to": "help@revix.es"
    }

    try:
        result = resend.Emails.send(params)
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, 'id', None)
        logger.info("✅ Email enviado a %s: %s (ID: %s)", to, subject, email_id)
        return True
    except Exception as e:
        logger.error("❌ Error enviando email a %s: %s", to, str(e))
        return False


async def send_email_async(
    to: str,
    subject: str,
    titulo: str,
    contenido: str,
    link_url: Optional[str] = None,
    link_text: str = "Ver en Revix",
    audience: str = "client",
) -> bool:
    """
    Version async — no bloquea FastAPI mientras envia.
    Usa asyncio.to_thread para mantener el event loop libre.
    """
    return await asyncio.to_thread(
        send_email, to, subject, titulo, contenido, link_url, link_text, audience,
    )


# ── Notificaciones especificas ────────────────────────────────────────────────

async def notificar_cambio_estado(
    to: str, orden_numero: str, auth_code: str,
    nuevo_estado: str, orden_id: str,
    token_seguimiento: Optional[str] = None,
) -> bool:
    """Notifica al cliente un cambio de estado en su orden.

    Enlaza a la página pública de seguimiento /consulta?codigo={token}.
    """
    codigo = auth_code or orden_numero
    link = _build_client_link(token_seguimiento)

    ETIQUETAS_ESTADO = {
        "pendiente_recibir": "Pendiente de recibir",
        "entrada": "Entrada registrada",
        "recibida": "Dispositivo recibido",
        "cuarentena": "En cuarentena",
        "diagnostico": "En diagnostico",
        "esperando_ppto": "Presupuesto enviado",
        "aprobada": "Presupuesto aceptado",
        "en_taller": "En reparacion",
        "en_reparacion": "En reparacion",
        "re_presupuestar": "Requiere nuevo presupuesto",
        "reparado": "Reparacion completada",
        "control_calidad": "Control de calidad",
        "validacion": "En validacion",
        "lista": "Lista para recoger!",
        "enviado": "Enviada al cliente",
        "enviada": "Enviada al cliente",
        "cancelado": "Cancelada",
        "cancelada": "Cancelada",
        "garantia": "En garantia",
        "reemplazo": "En proceso de reemplazo",
        "irreparable": "Irreparable",
    }
    etiqueta = ETIQUETAS_ESTADO.get(nuevo_estado, nuevo_estado)

    contenido = f"""
    <p>Le informamos que su orden ha cambiado de estado:</p>
    <table style="margin:15px 0;border-collapse:collapse;width:100%;">
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Codigo</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;">{codigo}</td>
      </tr>
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Estado</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;color:#2563eb;font-weight:600;">{etiqueta}</td>
      </tr>
    </table>
    <p>Puede consultar el estado de su orden en cualquier momento a traves del enlace de abajo.</p>"""

    return await send_email_async(
        to=to,
        subject=f"Revix — Su orden {codigo}: {etiqueta}",
        titulo="Actualizacion de su Orden",
        contenido=contenido,
        link_url=link,
        link_text="Ver Estado de mi Orden",
        audience="client",
    )


async def notificar_material_pendiente(
    to: str, pieza: str, orden_numero: str, orden_id: str
) -> bool:
    """Notificacion INTERNA al staff — material pendiente de aprobacion.

    Enlace al CRM (requiere login). audience='admin'.
    """
    link = _build_admin_link(f"/ordenes/{orden_id}")
    contenido = f"""
    <p>El tecnico ha solicitado material para la orden <strong>{orden_numero}</strong>:</p>
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
        titulo="Material Pendiente de Aprobacion",
        contenido=contenido,
        link_url=link,
        link_text="Aprobar Material",
        audience="admin",
    )


async def notificar_presupuesto_enviado(
    to: str, orden_numero: str, total: float,
    orden_id: str, dias_validez: int = 15,
    token_seguimiento: Optional[str] = None,
) -> bool:
    """Notifica al cliente que tiene un presupuesto pendiente de aprobar.

    Enlaza a la página pública de seguimiento donde puede aprobar el presupuesto.
    """
    link = _build_client_link(token_seguimiento)
    contenido = f"""
    <p>Hemos preparado un presupuesto para la reparacion de su dispositivo:</p>
    <table style="margin:15px 0;border-collapse:collapse;width:100%;">
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Orden</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;">{orden_numero}</td>
      </tr>
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Total</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;font-weight:600;color:#2563eb;">{total:.2f} EUR</td>
      </tr>
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Valido hasta</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;">{dias_validez} dias desde hoy</td>
      </tr>
    </table>
    <p>Por favor, accede al enlace para aceptar o rechazar el presupuesto.</p>"""

    return await send_email_async(
        to=to,
        subject=f"Revix — Presupuesto para su orden {orden_numero}",
        titulo="Presupuesto Pendiente de Aprobacion",
        contenido=contenido,
        link_url=link,
        link_text="Ver y Aprobar Presupuesto",
        audience="client",
    )


async def notificar_orden_lista(
    to: str, orden_numero: str, auth_code: str, orden_id: str,
    token_seguimiento: Optional[str] = None,
) -> bool:
    """Avisa al cliente que su dispositivo esta listo para recoger o enviar.

    Enlaza a la página pública de seguimiento /consulta?codigo={token}.
    """
    codigo = auth_code or orden_numero
    link = _build_client_link(token_seguimiento)
    contenido = f"""
    <p>Buenas noticias! Su dispositivo ya esta reparado y listo.</p>
    <table style="margin:15px 0;border-collapse:collapse;width:100%;">
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Codigo</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;">{codigo}</td>
      </tr>
    </table>
    <p>En breve nos pondremos en contacto para coordinar la entrega o el envio.</p>"""

    return await send_email_async(
        to=to,
        subject=f"Revix — Su dispositivo esta listo! ({codigo})",
        titulo="Su Dispositivo Esta Listo!",
        contenido=contenido,
        link_url=link,
        link_text="Ver mi Orden",
        audience="client",
    )


async def notificar_factura_emitida(
    to: str, factura_numero: str, total: float,
    orden_numero: str, orden_id: str,
    token_seguimiento: Optional[str] = None,
) -> bool:
    """Notifica al cliente que se ha emitido su factura.

    Enlaza a la página pública /consulta?codigo={token} desde donde podrá
    descargar la factura.
    """
    link = _build_client_link(token_seguimiento)
    contenido = f"""
    <p>Le informamos que hemos emitido la factura correspondiente a su reparacion:</p>
    <table style="margin:15px 0;border-collapse:collapse;width:100%;">
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">N Factura</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;">{factura_numero}</td>
      </tr>
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Orden</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;">{orden_numero}</td>
      </tr>
      <tr>
        <td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Total</td>
        <td style="padding:8px 15px;border:1px solid #e2e8f0;font-weight:600;color:#2563eb;">{total:.2f} EUR</td>
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
        audience="client",
    )


async def notificar_bienvenida(
    to: str, nombre: str
) -> bool:
    """Email de bienvenida para nuevos clientes."""
    contenido = f"""
    <p>Hola <strong>{nombre}</strong>,</p>
    <p>Bienvenido/a a Revix! Nos alegra tenerte como cliente.</p>
    <p>A partir de ahora podras:</p>
    <ul style="color:#475569;padding-left:20px;">
      <li>Seguir el estado de tus reparaciones en tiempo real</li>
      <li>Recibir notificaciones cuando tu dispositivo este listo</li>
      <li>Consultar el historial de tus ordenes y facturas</li>
    </ul>
    <p>Si tienes cualquier duda, no dudes en contactarnos.</p>
    <p>Gracias por confiar en nosotros!</p>"""

    return await send_email_async(
        to=to,
        subject="Bienvenido/a a Revix!",
        titulo=f"Hola {nombre}!",
        contenido=contenido,
        link_url=_build_client_link(),
        link_text="Visitar Revix",
        audience="client",
    )


# ── Test de conexion ──────────────────────────────────────────────────────────

def test_conexion_resend() -> dict:
    """
    Prueba la configuracion de Resend.
    Util para verificar desde /api/health o desde consola.
    """
    if not is_configured():
        return {"ok": False, "error": "Resend no configurado - falta RESEND_API_KEY"}
    
    return {
        "ok": True, 
        "provider": "Resend",
        "sender": SENDER_EMAIL,
        "api_key_prefix": RESEND_API_KEY[:10] + "..."
    }


# Alias para compatibilidad con codigo existente que usa test_conexion_smtp
test_conexion_smtp = test_conexion_resend

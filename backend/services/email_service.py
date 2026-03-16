"""
SMTP Email Service for Revix CRM.
Sends transactional emails: order status updates, notifications, etc.
Uses the company's own SMTP server (mail.privateemail.com).
"""
import smtplib
import ssl
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv(Path(__file__).parent.parent / '.env')

logger = logging.getLogger(__name__)

SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '465'))
SMTP_SECURE = os.environ.get('SMTP_SECURE', 'true').lower() == 'true'
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
SMTP_FROM = os.environ.get('SMTP_FROM', 'Revix <notificaciones@revix.es>')
SMTP_REPLY_TO = os.environ.get('SMTP_REPLY_TO', 'help@revix.es')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://repair-crm-dev.preview.emergentagent.com')


def _build_html_body(titulo: str, contenido: str, link_url: Optional[str] = None, link_text: str = "Ver en Revix") -> str:
    link_html = ""
    if link_url:
        link_html = f'''
        <tr>
          <td style="padding:20px 30px 30px;">
            <a href="{link_url}" style="display:inline-block;background:#2563eb;color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:600;font-size:14px;">{link_text}</a>
          </td>
        </tr>'''

    return f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:20px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
      <tr><td style="background:#1e40af;padding:20px 30px;">
        <h1 style="margin:0;color:#fff;font-size:20px;">Revix</h1>
      </td></tr>
      <tr><td style="padding:30px 30px 10px;">
        <h2 style="margin:0 0 15px;color:#1e293b;font-size:18px;">{titulo}</h2>
        <div style="color:#475569;font-size:14px;line-height:1.6;">{contenido}</div>
      </td></tr>
      {link_html}
      <tr><td style="padding:20px 30px;border-top:1px solid #e2e8f0;">
        <p style="margin:0;color:#94a3b8;font-size:11px;">Este es un correo automático de Revix CRM. No responda a este mensaje.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>'''


def send_email(to: str, subject: str, titulo: str, contenido: str,
               link_url: Optional[str] = None, link_text: str = "Ver en Revix") -> bool:
    """Send an HTML email via SMTP. Returns True on success."""
    if not SMTP_HOST or not SMTP_USER:
        logger.warning("SMTP not configured, skipping email to %s", to)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg["Reply-To"] = SMTP_REPLY_TO

    html = _build_html_body(titulo, contenido, link_url, link_text)
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        context = ssl.create_default_context()
        if SMTP_SECURE and SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=15) as server:
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)

        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Email send failed to %s: %s", to, e)
        return False


# ── Convenience helpers for common notification types ──

def send_orden_status_email(to: str, orden_numero: str, auth_code: str,
                            nuevo_estado: str, orden_id: str):
    """Notify client about order status change."""
    link = f"{FRONTEND_URL}/ordenes/{orden_id}"
    contenido = f'''
    <p>Le informamos que su orden <strong>{auth_code or orden_numero}</strong> ha cambiado de estado:</p>
    <table style="margin:15px 0;border-collapse:collapse;">
      <tr><td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Nuevo Estado</td>
          <td style="padding:8px 15px;border:1px solid #e2e8f0;">{nuevo_estado}</td></tr>
      <tr><td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Código</td>
          <td style="padding:8px 15px;border:1px solid #e2e8f0;">{auth_code or orden_numero}</td></tr>
    </table>
    <p>Puede consultar el estado de su orden en cualquier momento a través del siguiente enlace.</p>'''

    return send_email(
        to=to,
        subject=f"Revix - Actualización de su orden {auth_code or orden_numero}",
        titulo="Actualización de Estado",
        contenido=contenido,
        link_url=link,
        link_text="Ver Estado de mi Orden"
    )


def send_material_pendiente_email(to: str, pieza: str, orden_numero: str, orden_id: str):
    """Internal notification about a pending material for an order."""
    link = f"{FRONTEND_URL}/ordenes/{orden_id}"
    contenido = f'''
    <p>Se ha solicitado material para la orden <strong>{orden_numero}</strong>:</p>
    <table style="margin:15px 0;border-collapse:collapse;">
      <tr><td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Material</td>
          <td style="padding:8px 15px;border:1px solid #e2e8f0;">{pieza}</td></tr>
      <tr><td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Orden</td>
          <td style="padding:8px 15px;border:1px solid #e2e8f0;">{orden_numero}</td></tr>
    </table>
    <p>El repuesto está pendiente de llegada.</p>'''

    return send_email(
        to=to,
        subject=f"Revix - Material pendiente para {orden_numero}",
        titulo="Material Pendiente de Recepción",
        contenido=contenido,
        link_url=link,
        link_text="Ver Orden"
    )

"""
services/email_service.py — Proxy hacia backend/email_service.py
Existe para que los imports del tipo:
    from services.email_service import send_email
funcionen sin cambiar codigo en todos los routes.
"""
from email_service import *  # noqa: F401, F403
from email_service import (
    send_email,
    send_email_async,
    notificar_cambio_estado,
    notificar_material_pendiente,
    notificar_presupuesto_enviado,
    notificar_orden_lista,
    notificar_factura_emitida,
    notificar_bienvenida,
    test_conexion_smtp,
    is_configured,
    RESEND_API_KEY,
    SENDER_EMAIL,
    FRONTEND_URL,
)

"""
services/email_service.py — Proxy hacia backend/email_service.py
Existe para que los imports del tipo:
    from services.email_service import send_email
funcionen sin cambiar código en todos los routes.
"""
from email_service import *  # noqa: F401, F403
from email_service import (
    SMTPConfig,
    send_email,
    send_email_async,
    notificar_cambio_estado,
    notificar_material_pendiente,
    notificar_presupuesto_enviado,
    notificar_orden_lista,
    notificar_factura_emitida,
    notificar_bienvenida,
    test_conexion_smtp,
    CONFIG,
    FRONTEND_URL,
)

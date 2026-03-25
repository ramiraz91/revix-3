"""
services/__init__.py
Re-exporta los modulos de servicio para que los imports del tipo
`from services.email_service import ...` funcionen correctamente,
aunque los archivos reales esten en backend/ o backend/services/.
"""

# email_service esta en backend/email_service.py
# Todos los imports `from services.email_service import X` funcionaran
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
    FRONTEND_URL,
    RESEND_API_KEY,
    SENDER_EMAIL,
)

# cloudinary_service está en backend/services/cloudinary_service.py — OK
# apple_manuals_service está en backend/services/apple_manuals_service.py — OK

"""
services/__init__.py
Re-exporta los módulos de servicio para que los imports del tipo
`from services.email_service import ...` funcionen correctamente,
aunque los archivos reales estén en backend/ o backend/services/.
"""

# email_service está en backend/email_service.py
# Todos los imports `from services.email_service import X` funcionarán
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
    CONFIG,
    FRONTEND_URL,
)

# cloudinary_service está en backend/services/cloudinary_service.py — OK
# apple_manuals_service está en backend/services/apple_manuals_service.py — OK

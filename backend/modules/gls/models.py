"""
GLS Models - Pydantic models for validation and DB schema definitions.
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class GLSEntityType(str, Enum):
    """Types of internal entities that can originate a GLS shipment."""
    ORDEN = "orden"
    PEDIDO = "pedido"
    REPARACION = "reparacion"
    RMA = "rma"
    INCIDENCIA = "incidencia"
    DEVOLUCION = "devolucion"
    CLIENTE = "cliente"


class GLSShipmentType(str, Enum):
    ENVIO = "envio"
    RECOGIDA = "recogida"
    RECOGIDA_CRUZADA = "recogida_cruzada"


class GLSLabelFormat(str, Enum):
    PDF = "PDF"
    PNG = "PNG"
    JPG = "JPG"
    EPL = "EPL"
    DPL = "DPL"
    XML = "XML"
    EPL_SEPARADO = "EPL_SEPARADO"
    PDF_SEPARADO = "PDF_SEPARADO"


# ─── Request Models ──────────────────────────

class GLSConfigUpdate(BaseModel):
    activo: bool = False
    uid_cliente: str = ""
    # Datos del remitente (Revix)
    remitente_nombre: str = ""
    remitente_direccion: str = ""
    remitente_poblacion: str = ""
    remitente_provincia: str = ""
    remitente_cp: str = ""
    remitente_pais: str = "34"
    remitente_telefono: str = ""
    remitente_email: str = ""
    # Códigos de plaza y cliente (requeridos por GLS España)
    plaza_remitente: str = ""  # Código de plaza (ej: 143)
    codigo_remitente: str = ""  # Código cliente en remite (ej: 645831)
    codigo_cliente_inf: str = ""  # Código inf (ej: 42669)
    # Configuración de servicio
    servicio_defecto: str = "96"
    horario_defecto: str = "18"
    formato_etiqueta: str = "PDF"
    portes: str = "P"
    polling_activo: bool = False
    polling_intervalo_horas: int = 4
    email_recogida_activo: bool = True


class GLSCreateShipment(BaseModel):
    orden_id: str
    entidad_tipo: GLSEntityType = GLSEntityType.ORDEN
    tipo: GLSShipmentType = GLSShipmentType.ENVIO
    # Destinatario
    dest_nombre: str
    dest_direccion: str
    dest_poblacion: str
    dest_provincia: str = ""
    dest_cp: str
    dest_pais: str = "34"
    dest_telefono: str = ""
    dest_movil: str = ""
    dest_email: str = ""
    dest_contacto: str = ""
    dest_observaciones: str = ""
    # Envío
    bultos: int = 1
    peso: float = 1.0
    servicio: str = ""
    horario: str = ""
    referencia: str = ""
    reembolso: float = 0.0
    retorno: str = "0"
    pod: str = "N"
    # Etiqueta inline
    etiqueta_inline: bool = True
    formato_etiqueta: str = "PDF"
    # Recogida cruzada
    recogida_nombre: Optional[str] = None
    recogida_direccion: Optional[str] = None
    recogida_poblacion: Optional[str] = None
    recogida_cp: Optional[str] = None
    recogida_telefono: Optional[str] = None


class GLSGetLabel(BaseModel):
    codigo: str  # codbarras or referencia
    formato: GLSLabelFormat = GLSLabelFormat.PDF


class GLSTrackingQuery(BaseModel):
    codigo: str  # codbarras, referencia, codexp, or uid


# ─── DB Schema Reference (for gls_shipments collection) ──────────────────────
# Document structure stored in MongoDB:
# {
#   "id": "uuid",
#   "entidad_tipo": "orden|pedido|rma|...",
#   "entidad_id": "ref to internal entity",
#   "cliente_id": "ref to client",
#   "tipo": "envio|recogida|recogida_cruzada",
#   "gls_codexp": "174705756",
#   "gls_uid": "a94c5c8a-...",
#   "gls_codbarras": "61771001452051",
#   "referencia_interna": "ORD-2024-0001",
#   "servicio": "96",
#   "horario": "18",
#   "estado_interno": "grabado",
#   "estado_gls_codigo": -10,
#   "estado_gls_texto": "GRABADO",
#   "es_final": false,
#   "incidencia_codigo": null,
#   "incidencia_texto": null,
#   "entrega_fecha": null,
#   "entrega_receptor": null,
#   "entrega_dni": null,
#   "pod_url": null,
#   "fecha_prevista_entrega": null,
#   "label_generada": false,
#   "label_formato": "PDF",
#   "bultos": 1,
#   "peso": 1.0,
#   "reembolso": 0.0,
#   "observaciones": "",
#   "remitente": { nombre, direccion, poblacion, cp, ... },
#   "destinatario": { nombre, direccion, poblacion, cp, ... },
#   "raw_request": "xml string",
#   "raw_response": "xml string",
#   "tracking_json": null,
#   "fecha_ultima_sync": null,
#   "sync_status": "ok|error|pending",
#   "sync_error": null,
#   "created_by": "user email",
#   "updated_by": null,
#   "created_at": "ISO datetime",
#   "updated_at": "ISO datetime"
# }

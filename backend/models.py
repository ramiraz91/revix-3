from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from enum import Enum
from datetime import datetime, timezone
import uuid


# ==================== ENUMS ====================

class OrderStatus(str, Enum):
    PENDIENTE_RECIBIR = "pendiente_recibir"
    RECIBIDA = "recibida"
    CUARENTENA = "cuarentena"
    EN_TALLER = "en_taller"
    RE_PRESUPUESTAR = "re_presupuestar"
    REPARADO = "reparado"
    VALIDACION = "validacion"
    ENVIADO = "enviado"
    CANCELADO = "cancelado"
    GARANTIA = "garantia"
    REEMPLAZO = "reemplazo"
    IRREPARABLE = "irreparable"

class UserRole(str, Enum):
    MASTER = "master"
    ADMIN = "admin"
    TECNICO = "tecnico"

class PurchaseOrderStatus(str, Enum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    PEDIDA = "pedida"  # Pedido realizado al proveedor
    RECHAZADA = "rechazada"
    RECIBIDA = "recibida"  # Material llegó
    COMPLETADA = "completada"

class PurchaseOrderPriority(str, Enum):
    NORMAL = "normal"
    URGENTE = "urgente"

class TipoJornada(str, Enum):
    COMPLETA = "completa"
    PARCIAL = "parcial"
    MEDIA_JORNADA = "media_jornada"

class TipoEvento(str, Enum):
    ORDEN_ASIGNADA = "orden_asignada"
    LLEGADA_DISPOSITIVO = "llegada_dispositivo"
    LLEGADA_REPUESTO = "llegada_repuesto"
    VACACIONES = "vacaciones"
    AUSENCIA = "ausencia"
    REUNION = "reunion"
    OTRO = "otro"

class TipoIncidencia(str, Enum):
    REEMPLAZO_DISPOSITIVO = "reemplazo_dispositivo"
    RECLAMACION = "reclamacion"
    GARANTIA = "garantia"
    DAÑO_TRANSPORTE = "daño_transporte"
    OTRO = "otro"

class EstadoIncidencia(str, Enum):
    ABIERTA = "abierta"
    EN_PROCESO = "en_proceso"
    RESUELTA = "resuelta"
    CERRADA = "cerrada"

class PrioridadOrden(str, Enum):
    NORMAL = "normal"
    URGENTE = "urgente"
    EXPRESS = "express"

class TipoServicio(str, Enum):
    GARANTIA_FABRICANTE = "garantia_fabricante"
    SEGURO = "seguro"
    PARTICULAR = "particular"
    EMPRESA = "empresa"

class TipoCliente(str, Enum):
    PARTICULAR = "particular"
    EMPRESA = "empresa"

class SubestadoOrden(str, Enum):
    """Subestados internos para órdenes en espera"""
    NINGUNO = "ninguno"
    ESPERANDO_REPUESTOS = "esperando_repuestos"
    ESPERANDO_AUTORIZACION = "esperando_autorizacion"
    ESPERANDO_CLIENTE = "esperando_cliente"
    ESPERANDO_PAGO = "esperando_pago"
    EN_CONSULTA_TECNICA = "en_consulta_tecnica"
    PENDIENTE_RECOGIDA = "pendiente_recogida"
    OTRO = "otro"
    ASEGURADORA = "aseguradora"

class PreferenciaComunicacion(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    TELEFONO = "telefono"
    NINGUNO = "ninguno"

class CalidadPantalla(str, Enum):
    """Calidad de pantallas - para clasificación visual"""
    # Apple (6 niveles)
    GENUINE = "genuine"  # Original nuevo Apple
    REFURBISHED_GENUINE = "refurbished_genuine"  # Original reacondicionado
    SOFT_OLED = "soft_oled"  # OLED flexible de alta calidad
    HARD_OLED = "hard_oled"  # OLED rígido
    INCELL = "incell"  # LCD con digitalizador integrado
    # Otras marcas
    SERVICE_PACK = "service_pack"  # Original de marca (Samsung, etc.)
    OLED = "oled"  # OLED genérico
    # Sin determinar
    DESCONOCIDO = "desconocido"


# ==================== USER MODELS ====================

class HorarioTrabajo(BaseModel):
    lunes: Optional[str] = "09:00-18:00"
    martes: Optional[str] = "09:00-18:00"
    miercoles: Optional[str] = "09:00-18:00"
    jueves: Optional[str] = "09:00-18:00"
    viernes: Optional[str] = "09:00-18:00"
    sabado: Optional[str] = None
    domingo: Optional[str] = None

class VacacionesInfo(BaseModel):
    dias_totales: int = 22
    dias_usados: int = 0
    dias_pendientes: int = 22
    periodos: List[dict] = []

class FichaEmpleado(BaseModel):
    dni: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    codigo_postal: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    fecha_alta: Optional[str] = None
    numero_ss: Optional[str] = None
    cuenta_bancaria: Optional[str] = None
    contacto_emergencia: Optional[str] = None
    telefono_emergencia: Optional[str] = None

class InfoLaboral(BaseModel):
    tipo_jornada: TipoJornada = TipoJornada.COMPLETA
    horas_semanales: int = 40
    horario: HorarioTrabajo = HorarioTrabajo()
    sueldo_bruto: Optional[float] = None
    sueldo_neto: Optional[float] = None
    puesto: Optional[str] = None
    departamento: Optional[str] = None
    vacaciones: VacacionesInfo = VacacionesInfo()
    # Comisiones
    comisiones_activas: bool = False  # Por defecto desactivado
    comision_porcentaje: float = 0.0  # Porcentaje sobre el precio de reparación
    comision_fija_por_orden: float = 0.0  # Cantidad fija por orden completada


class ComisionTecnico(BaseModel):
    """Registro de comisión generada para un técnico"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tecnico_id: str
    tecnico_nombre: str
    orden_id: str
    numero_orden: str
    tipo_comision: str = "porcentaje"  # porcentaje, fija, mixta
    precio_reparacion: float = 0.0
    porcentaje_aplicado: float = 0.0
    monto_porcentaje: float = 0.0
    monto_fijo: float = 0.0
    monto_total: float = 0.0
    estado: str = "pendiente"  # pendiente, aprobada, pagada, cancelada
    periodo: str = ""  # ej: "2025-02" para febrero 2025
    notas: Optional[str] = None
    aprobada_por: Optional[str] = None
    fecha_aprobacion: Optional[datetime] = None
    pagada_fecha: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserBase(BaseModel):
    email: str
    nombre: str
    apellidos: Optional[str] = None
    role: UserRole = UserRole.TECNICO
    activo: bool = True
    ficha: FichaEmpleado = FichaEmpleado()
    info_laboral: InfoLaboral = InfoLaboral()
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    role: Optional[UserRole] = None
    activo: Optional[bool] = None
    ficha: Optional[FichaEmpleado] = None
    info_laboral: Optional[InfoLaboral] = None
    avatar_url: Optional[str] = None
    password: Optional[str] = None

class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    token: str
    user: dict


# ==================== CALENDARIO ====================

class EventoCalendario(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    titulo: str
    descripcion: Optional[str] = None
    tipo: TipoEvento
    fecha_inicio: str
    fecha_fin: Optional[str] = None
    todo_el_dia: bool = False
    usuario_id: Optional[str] = None
    orden_id: Optional[str] = None
    color: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== CLIENTES ====================

class ClienteBase(BaseModel):
    nombre: str
    apellidos: str
    dni: str
    telefono: str
    email: Optional[str] = None
    direccion: str
    planta: Optional[str] = None
    puerta: Optional[str] = None
    ciudad: Optional[str] = None
    codigo_postal: Optional[str] = None
    # Nuevos campos para mejor gestión de clientes
    tipo_cliente: Optional[str] = "particular"  # particular, empresa, aseguradora
    cif_empresa: Optional[str] = None  # Para clientes empresa
    preferencia_comunicacion: Optional[str] = "email"  # email, sms, whatsapp, telefono, ninguno
    idioma_preferido: Optional[str] = "es"  # es, ca, en
    notas_internas: Optional[str] = None  # Notas solo visibles para admin
    acepta_comunicaciones_comerciales: bool = False

class ClienteCreate(ClienteBase):
    pass

class Cliente(ClienteBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== PROVEEDORES ====================

class ProveedorBase(BaseModel):
    nombre: str
    contacto: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    web: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None

class ProveedorCreate(ProveedorBase):
    pass

class Proveedor(ProveedorBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== INVENTARIO/REPUESTOS ====================

class RepuestoBase(BaseModel):
    nombre: str
    categoria: str
    sku: Optional[str] = None
    abreviatura: Optional[str] = None
    modelo_compatible: Optional[str] = None
    precio_compra: float = 0
    precio_venta: float = 0
    stock: int = 0
    stock_minimo: int = 5
    ubicacion: Optional[str] = None
    proveedor_id: Optional[str] = None
    proveedor: Optional[str] = None  # Nombre del proveedor (ej: "MobileSentrix", "Utopya")
    sku_proveedor: Optional[str] = None  # SKU original del proveedor
    # Nuevos campos para mejor gestión de inventario
    codigo_barras: Optional[str] = None  # EAN13/UPC para escaneo rápido
    ean: Optional[str] = None  # Código EAN del producto (13 dígitos)
    url_proveedor: Optional[str] = None  # URL del producto en el sitio del proveedor
    ubicacion_fisica: Optional[str] = None  # Ej: "Estante A3, Cajón 5"
    tiempo_reposicion_dias: Optional[int] = None  # Lead time del proveedor
    es_generico: bool = False  # Si es pieza genérica compatible con múltiples modelos
    modelos_compatibles: List[str] = []  # Lista de modelos compatibles
    imagen_url: Optional[str] = None  # URL de imagen del producto
    ultima_sync: Optional[datetime] = None  # Última sincronización con proveedor
    # Calidad de pantalla (para pantallas/screens)
    calidad_pantalla: Optional[str] = None  # genuine, soft_oled, hard_oled, incell, service_pack, etc.
    es_pantalla: bool = False  # True si es un producto de pantalla/display
    # Control de IVA
    iva_compra: float = 21.0  # Porcentaje de IVA en compra (0 para exentos/ISP)
    inversion_sujeto_pasivo: bool = False  # True si el IVA no se paga en compra (compras intracomunitarias)
    iva_venta: float = 21.0  # Porcentaje de IVA en venta

class RepuestoCreate(RepuestoBase):
    pass

class Repuesto(RepuestoBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== ORDENES DE TRABAJO ====================

class MaterialOrden(BaseModel):
    model_config = ConfigDict(extra="allow")  # Permitir campos adicionales para trazabilidad
    repuesto_id: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    cantidad: int = 1
    precio_unitario: float = 0
    coste: float = 0
    iva: float = 21.0
    descuento: float = 0
    añadido_por_tecnico: bool = False
    aprobado: bool = True
    pendiente_precios: bool = False
    # Campos de trazabilidad
    estado_material: Optional[str] = None  # pendiente_compra, compra_aprobada, pedido_proveedor, recibido
    orden_compra_id: Optional[str] = None
    orden_compra_numero: Optional[str] = None
    numero_pedido: Optional[str] = None
    solicitado_por: Optional[str] = None
    fecha_solicitud: Optional[str] = None
    fecha_aprobacion: Optional[str] = None
    fecha_pedido: Optional[str] = None
    fecha_recepcion: Optional[str] = None
    aprobado_por: Optional[str] = None

class DispositivoInfo(BaseModel):
    modelo: str
    imei: Optional[str] = None
    color: Optional[str] = None
    daños: str

class OrdenTrabajoBase(BaseModel):
    cliente_id: str
    dispositivo: DispositivoInfo
    agencia_envio: Optional[str] = None
    codigo_recogida_entrada: Optional[str] = None
    codigo_recogida_salida: Optional[str] = None
    numero_autorizacion: Optional[str] = None
    materiales: List[MaterialOrden] = []
    notas: Optional[str] = None
    diagnostico_tecnico: Optional[str] = None
    tecnico_asignado: Optional[str] = None

class OrdenTrabajoCreate(OrdenTrabajoBase):
    pass

class OrdenTrabajo(OrdenTrabajoBase):
    model_config = ConfigDict(extra="allow")  # Permitir campos adicionales del portal
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    numero_orden: str = Field(default_factory=lambda: f"OT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}")
    estado: OrderStatus = OrderStatus.PENDIENTE_RECIBIR
    qr_code: Optional[str] = None
    token_seguimiento: str = Field(default_factory=lambda: str(uuid.uuid4())[:12].upper())
    evidencias: List[str] = []
    evidencias_tecnico: List[str] = []
    fotos_antes: List[str] = []  # Fotos del estado inicial del dispositivo
    fotos_despues: List[str] = []  # Fotos después de la reparación
    historial_estados: List[dict] = []
    mensajes: List[dict] = []
    requiere_aprobacion: bool = False
    bloqueada: bool = False
    garantia_meses: int = 3
    garantia_fecha_inicio: Optional[datetime] = None
    garantia_fecha_fin: Optional[datetime] = None
    orden_padre_id: Optional[str] = None
    es_garantia: bool = False
    ordenes_garantia: List[str] = []
    fecha_recogida_logistica: Optional[datetime] = None
    fecha_recibida_centro: Optional[datetime] = None
    fecha_inicio_reparacion: Optional[datetime] = None
    fecha_fin_reparacion: Optional[datetime] = None
    fecha_enviado: Optional[datetime] = None
    # Campos del portal del proveedor
    codigo_siniestro: Optional[str] = None
    fotos_portal: List[str] = []
    datos_portal: Optional[dict] = None
    # NUEVOS CAMPOS - Mejoras de trazabilidad y gestión
    prioridad: Optional[str] = "normal"  # normal, urgente, express
    tipo_servicio: Optional[str] = "seguro"  # garantia_fabricante, seguro, particular, empresa
    fecha_estimada_entrega: Optional[datetime] = None  # Compromiso con el cliente
    # Campos de presupuesto
    presupuesto_emitido: bool = False
    presupuesto_precio: Optional[float] = None
    presupuesto_fecha_emision: Optional[datetime] = None
    presupuesto_aceptado: Optional[bool] = None  # None = sin respuesta, True/False
    presupuesto_fecha_respuesta: Optional[datetime] = None
    presupuesto_motivo_rechazo: Optional[str] = None
    # Campos de SLA y alertas
    sla_dias: int = 5  # Días objetivo para completar
    alerta_sla_enviada: bool = False
    # Idempotency key para prevenir duplicados
    idempotency_key: Optional[str] = None
    # Envíos GLS creados por el módulo /api/logistica/gls/* (v2)
    gls_envios: List[dict] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== NOTIFICACIONES ====================

class Notificacion(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tipo: str
    mensaje: str
    # Categoría amplia para filtrado en la central.
    # Valores: LOGISTICA, INCIDENCIA_LOGISTICA, COMUNICACION_INTERNA,
    #          RECHAZO, MODIFICACION, INCIDENCIA, GENERAL
    categoria: Optional[str] = "GENERAL"
    # Opcional: título corto para mostrar en la central
    titulo: Optional[str] = None
    orden_id: Optional[str] = None
    usuario_destino: Optional[str] = None  # ID del usuario destinatario (para filtrar por técnico)
    leida: bool = False
    # Contexto extra (codbarras, incidencia_id, etc.)
    meta: Optional[dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MensajeOrden(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    autor: str
    autor_nombre: str
    rol: str
    mensaje: str
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    visible_tecnico: bool = True

class MensajeOrdenCreate(BaseModel):
    mensaje: str
    visible_tecnico: bool = True


# ==================== ORDENES DE COMPRA ====================

class OrdenCompraBase(BaseModel):
    nombre_pieza: str
    descripcion: Optional[str] = None
    cantidad: int = 1
    orden_trabajo_id: str
    solicitado_por: str
    repuesto_id: Optional[str] = None  # Vincula a repuesto existente si aplica
    precio_unitario: Optional[float] = None
    coste_unitario: Optional[float] = None

class OrdenCompraCreate(OrdenCompraBase):
    pass

class OrdenCompra(OrdenCompraBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    numero_oc: str = Field(default_factory=lambda: f"OC-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}")
    estado: PurchaseOrderStatus = PurchaseOrderStatus.PENDIENTE
    prioridad: PurchaseOrderPriority = PurchaseOrderPriority.URGENTE
    proveedor_id: Optional[str] = None
    precio_estimado: Optional[float] = None
    notas_admin: Optional[str] = None
    # Campos de trazabilidad
    numero_pedido_proveedor: Optional[str] = None  # Número de pedido/factura del proveedor
    fecha_pedido: Optional[str] = None  # Cuando se hizo el pedido al proveedor
    fecha_recepcion: Optional[str] = None  # Cuando llegó el material
    material_index_en_orden: Optional[int] = None  # Índice del material en la orden de trabajo
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrdenCompraUpdate(BaseModel):
    estado: Optional[str] = None
    proveedor_id: Optional[str] = None
    precio_estimado: Optional[float] = None
    precio_unitario: Optional[float] = None
    coste_unitario: Optional[float] = None
    notas_admin: Optional[str] = None
    notas: Optional[str] = None
    numero_pedido_proveedor: Optional[str] = None
    fecha_pedido: Optional[str] = None


# ==================== EMPRESA Y CONFIGURACIÓN ====================

class TipoIVA(BaseModel):
    nombre: str
    porcentaje: float
    activo: bool = True

class LogoConfig(BaseModel):
    url: Optional[str] = None
    ancho_web: int = 200
    alto_web: int = 60
    ancho_pdf: int = 150
    alto_pdf: int = 45

class TextosLegales(BaseModel):
    aceptacion_seguimiento: str = "Al acceder a este portal de seguimiento, el cliente acepta que [NOMBRE_EMPRESA] no se hace responsable de los daños externos que pueda presentar el dispositivo, tales como arañazos, abolladuras o defectos cosméticos preexistentes. La responsabilidad de la empresa se limita exclusivamente a la reparación contratada. El cliente declara haber entregado el dispositivo en el estado actual y acepta las condiciones del servicio."
    clausulas_documentos: str = "Garantía de reparación: 3 meses desde la fecha de entrega. La garantía cubre únicamente la avería reparada. Quedan excluidos de la garantía los daños por mal uso, golpes, líquidos o manipulación por terceros."
    politica_privacidad: str = "Sus datos personales serán tratados conforme al RGPD. Para más información, consulte nuestra política de privacidad completa."
    titulo_aceptacion: str = "Condiciones del Servicio"

class EmpresaConfig(BaseModel):
    nombre: str = "Mi Empresa"
    cif: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    codigo_postal: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    web: Optional[str] = None
    logo: LogoConfig = LogoConfig()
    logo_url: Optional[str] = None
    textos_legales: TextosLegales = TextosLegales()
    tipos_iva: List[TipoIVA] = [
        TipoIVA(nombre="General", porcentaje=21.0),
        TipoIVA(nombre="Reducido", porcentaje=10.0),
        TipoIVA(nombre="Superreducido", porcentaje=4.0),
        TipoIVA(nombre="Exento", porcentaje=0.0)
    ]
    iva_por_defecto: float = 21.0


# ==================== INCIDENCIAS ====================

class IncidenciaBase(BaseModel):
    cliente_id: str
    orden_id: Optional[str] = None
    tipo: TipoIncidencia = TipoIncidencia.OTRO
    titulo: str
    descripcion: str
    prioridad: str = "media"
    origen_ncm: Optional[str] = None
    severidad_ncm: Optional[str] = "media"
    disposicion_ncm: Optional[str] = None
    impacto_ncm: Optional[str] = None
    contencion_ncm: Optional[str] = None

class IncidenciaCreate(IncidenciaBase):
    pass

class Incidencia(IncidenciaBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    numero_incidencia: str = Field(default_factory=lambda: f"INC-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}")
    estado: EstadoIncidencia = EstadoIncidencia.ABIERTA
    notas_resolucion: Optional[str] = None
    resuelto_por: Optional[str] = None
    fecha_resolucion: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None


# ==================== DISPOSITIVOS DE RESTOS ====================

class DispositivoRestoBase(BaseModel):
    modelo: str
    imei: Optional[str] = None
    color: Optional[str] = None
    estado_fisico: str
    descripcion: Optional[str] = None
    piezas_aprovechables: List[str] = []
    origen_orden_id: Optional[str] = None
    ubicacion_almacen: Optional[str] = None

class DispositivoRestoCreate(DispositivoRestoBase):
    pass

class DispositivoResto(DispositivoRestoBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    codigo: str = Field(default_factory=lambda: f"RST-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}")
    fecha_ingreso: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    piezas_usadas: List[dict] = []
    activo: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== NETELIP ====================

class NetelipConfig(BaseModel):
    api_token: str
    account_id: str
    default_caller_id: Optional[str] = None
    webhook_url: Optional[str] = None
    activo: bool = True

class NetelipUsuarioExtension(BaseModel):
    usuario_id: str
    extension: str
    nombre_usuario: Optional[str] = None
    activo: bool = True

class NetelipCallAction(BaseModel):
    call_id: str
    action: str
    params: Optional[dict] = None


# ==================== MISC REQUEST MODELS ====================

class SeguimientoRequest(BaseModel):
    token: str
    telefono: str
    acepta_condiciones: Optional[bool] = False
    acepta_rgpd: Optional[bool] = False

class ConfiguracionNotificaciones(BaseModel):
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: Optional[str] = None

class DiagnosticoRequest(BaseModel):
    diagnostico: str

class AsignarOrdenRequest(BaseModel):
    orden_id: str
    tecnico_id: str
    fecha_inicio: str
    fecha_fin: Optional[str] = None

class IARequest(BaseModel):
    texto: str
    contexto: Optional[str] = None

class IAChatRequest(BaseModel):
    mensaje: str
    session_id: Optional[str] = None


# ==================== AGENTE EMAIL - ENUMS ====================

class EstadoPreRegistro(str, Enum):
    PENDIENTE_PRESUPUESTO = "pendiente_presupuesto"
    PRESUPUESTO_ENVIADO = "presupuesto_enviado"
    ACEPTADO = "aceptado"
    PENDIENTE_TRAMITAR = "pendiente_tramitar"
    RECHAZADO = "rechazado"
    ORDEN_CREADA = "orden_creada"
    ARCHIVADO = "archivado"

class TipoEventoEmail(str, Enum):
    NUEVO_SINIESTRO = "nuevo_siniestro"
    PRESUPUESTO_ACEPTADO = "presupuesto_aceptado"
    PRESUPUESTO_RECHAZADO = "presupuesto_rechazado"
    IMAGENES_FALTANTES = "imagenes_faltantes"
    DOCUMENTACION_FALTANTE = "documentacion_faltante"
    SLA_24H = "sla_24h"
    SLA_48H = "sla_48h"
    RECORDATORIO = "recordatorio"
    INCIDENCIA_PROVEEDOR = "incidencia_proveedor"
    DESCONOCIDO = "desconocido"

class SeveridadNotificacion(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class EstadoAgente(str, Enum):
    ACTIVO = "activo"
    PAUSADO = "pausado"
    ERROR = "error"


# ==================== AGENTE EMAIL - MODELOS ====================

class PreRegistro(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    codigo_siniestro: str
    email_message_id: str
    email_subject: str
    email_body: Optional[str] = None
    email_from: Optional[str] = None
    email_date: Optional[str] = None
    estado: EstadoPreRegistro = EstadoPreRegistro.PENDIENTE_PRESUPUESTO
    orden_id: Optional[str] = None
    datos_portal: Optional[dict] = None
    historial: List[dict] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class NotificacionExterna(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    codigo_siniestro: str
    orden_id: Optional[str] = None
    pre_registro_id: Optional[str] = None
    tipo: TipoEventoEmail
    severidad: SeveridadNotificacion = SeveridadNotificacion.INFO
    titulo: str
    contenido: str
    email_message_id: str
    email_subject: str
    email_date: Optional[str] = None
    leida: bool = False
    resuelta: bool = False
    resuelta_por: Optional[str] = None
    fecha_resolucion: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EventoPendiente(BaseModel):
    """Evento en ventana de consolidación (5 min)"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    codigo_siniestro: str
    tipo_evento: TipoEventoEmail
    email_message_id: str
    email_subject: str
    email_body: Optional[str] = None
    email_from: Optional[str] = None
    email_date: Optional[str] = None
    procesado: bool = False
    consolidado_en: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    procesar_despues_de: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    accion: str
    resultado: str
    nivel: str = "info"
    codigo_siniestro: Optional[str] = None
    email_id: Optional[str] = None
    error: Optional[str] = None
    detalles: Optional[dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== AUDITORÍA CENTRALIZADA ====================

class AuditLog(BaseModel):
    """Log de auditoría para rastrear todas las acciones del sistema"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entidad: str  # "orden", "cliente", "repuesto", "usuario", "orden_compra", "config"
    entidad_id: str
    accion: str  # "crear", "actualizar", "eliminar", "cambiar_estado", "autorizar", etc.
    usuario_id: Optional[str] = None
    usuario_email: Optional[str] = None
    rol: Optional[str] = None
    cambios: dict = {}  # {"campo": {"antes": X, "despues": Y}} o descripción de cambio
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== ALERTAS SLA ====================

class AlertaSLA(BaseModel):
    """Alerta cuando una orden está próxima o ha superado su SLA"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    orden_id: str
    numero_orden: str
    tipo_alerta: str  # "proximo_vencer", "vencido", "critico"
    dias_en_proceso: int
    sla_objetivo: int
    mensaje: str
    notificado_a: List[str] = []  # Lista de emails notificados
    resuelta: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== ETIQUETAS DE ENVÍO ====================

class ConfiguracionTransportista(BaseModel):
    """Configuración de integración con transportista"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str  # MRW, SEUR, Correos, DHL, etc.
    codigo: str  # mrw, seur, correos, dhl
    activo: bool = False
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    usuario: Optional[str] = None
    password: Optional[str] = None
    cliente_id: Optional[str] = None  # ID de cliente con el transportista
    centro_origen: Optional[str] = None  # Código del centro de origen
    # Configuración adicional específica del transportista
    config_extra: dict = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EtiquetaEnvio(BaseModel):
    """Etiqueta de envío generada"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    orden_id: str
    numero_orden: str
    transportista: str  # mrw, seur, correos
    tipo: str = "salida"  # salida, recogida, devolucion
    # Datos del destinatario
    destinatario_nombre: str
    destinatario_direccion: str
    destinatario_ciudad: str
    destinatario_cp: str
    destinatario_telefono: str
    destinatario_email: Optional[str] = None
    # Datos del paquete
    peso_kg: float = 0.5
    largo_cm: float = 20
    ancho_cm: float = 15
    alto_cm: float = 10
    contenido: str = "Dispositivo móvil"
    valor_declarado: Optional[float] = None
    # Respuesta del transportista
    codigo_seguimiento: Optional[str] = None
    url_seguimiento: Optional[str] = None
    etiqueta_pdf_url: Optional[str] = None
    etiqueta_base64: Optional[str] = None
    # Estado
    estado: str = "pendiente"  # pendiente, generada, enviada, entregada, error
    error_mensaje: Optional[str] = None
    # Timestamps
    fecha_envio: Optional[datetime] = None
    fecha_entrega: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PlantillaEmail(BaseModel):
    """Plantilla de email personalizable"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tipo: str  # created, recibida, en_taller, reparado, enviado, presupuesto, etc.
    nombre: str
    asunto: str
    # Contenido personalizable
    titulo: str
    subtitulo: str
    mensaje_principal: str
    mensaje_secundario: Optional[str] = None
    # Configuración visual
    color_banner: str = "#3b82f6"  # Color del banner de estado
    emoji_estado: str = "📱"
    mostrar_progreso: bool = True
    mostrar_tracking: bool = False
    # Estado
    activo: bool = True
    es_default: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))



# ==================== RESTOS / DESPIECE ====================

class TipoResto(str, Enum):
    DISPOSITIVO_REEMPLAZADO = "dispositivo_reemplazado"  # Dispositivo original tras reemplazo
    IRREPARABLE = "irreparable"  # Dispositivo irreparable para piezas
    GARANTIA = "garantia"  # Dispositivo devuelto en garantía
    DESECHO = "desecho"  # Descarte general

class EstadoResto(str, Enum):
    PENDIENTE = "pendiente"  # Pendiente de clasificar
    CLASIFICADO = "clasificado"  # Piezas identificadas
    EN_DESPIECE = "en_despiece"  # En proceso de extraer piezas
    DESPIEZADO = "despiezado"  # Completado despiece
    DESCARTADO = "descartado"  # Sin piezas útiles

class PiezaResto(BaseModel):
    """Pieza extraída de un resto"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str
    estado: str = "bueno"  # bueno, aceptable, malo
    destino: Optional[str] = None  # inventario, desecho, vendido
    codigo_inventario: Optional[str] = None  # Si se añade al inventario
    notas: Optional[str] = None

class Resto(BaseModel):
    """Dispositivo que va a restos/despiece"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    codigo_resto: str = Field(default_factory=lambda: f"RST-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}")
    # Origen
    orden_id: str  # Orden original
    numero_orden: str
    tipo: str = "dispositivo_reemplazado"  # TipoResto
    # Dispositivo
    modelo: str
    imei: Optional[str] = None
    color: Optional[str] = None
    descripcion_daños: Optional[str] = None
    # Estado y procesamiento
    estado: str = "pendiente"  # EstadoResto
    ubicacion: Optional[str] = None  # Estantería, caja, etc.
    # Piezas extraídas
    piezas: List[PiezaResto] = []
    piezas_utiles: int = 0
    valor_estimado_piezas: float = 0.0
    # Trazabilidad
    procesado_por: Optional[str] = None
    fecha_recepcion: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fecha_clasificacion: Optional[datetime] = None
    fecha_despiece: Optional[datetime] = None
    notas: Optional[str] = None
    # Fotos del dispositivo en restos
    fotos: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

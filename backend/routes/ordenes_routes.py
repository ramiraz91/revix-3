"""
Rutas de Órdenes de Trabajo
Extraído de server.py para mejorar modularidad
Incluye: CRUD, estados, materiales, evidencias, mensajes, métricas, reemplazo
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import aiofiles
import asyncio
import os

from config import db, UPLOAD_DIR, logger
from auth import require_auth, require_admin, require_master, require_tecnico
from models import (
    OrderStatus, OrdenTrabajo, OrdenTrabajoCreate, Notificacion, MensajeOrdenCreate,
    SubestadoOrden
)
from helpers import generate_barcode, send_order_notification
from utils.image_compression import compress_image, is_image

router = APIRouter()

# ==================== FUNCIÓN DE CÁLCULO DE TOTALES ====================

async def recalcular_totales_orden(orden_id: str):
    """
    Recalcula y actualiza los totales de una orden basándose en sus materiales.
    - presupuesto_total: Suma de (precio_unitario * cantidad) con IVA y descuentos
    - coste_total: Suma de (coste * cantidad)
    - beneficio_estimado: presupuesto_total - coste_total
    - mano_obra: Se mantiene el valor existente o 0
    """
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        return None
    
    materiales = orden.get('materiales', [])
    mano_obra = orden.get('mano_obra', 0) or 0
    
    subtotal_materiales = 0
    coste_total = 0
    total_iva = 0
    
    for mat in materiales:
        # Solo contar materiales aprobados
        if not mat.get('aprobado', True):
            continue
            
        cantidad = mat.get('cantidad', 1)
        precio_unitario = mat.get('precio_unitario', 0) or 0
        coste_unitario = mat.get('coste', 0) or 0
        iva_porcentaje = mat.get('iva', 21) or 21
        descuento_porcentaje = mat.get('descuento', 0) or 0
        
        # Calcular precio con descuento
        precio_con_descuento = precio_unitario * (1 - descuento_porcentaje / 100)
        subtotal_linea = precio_con_descuento * cantidad
        iva_linea = subtotal_linea * (iva_porcentaje / 100)
        
        subtotal_materiales += subtotal_linea
        total_iva += iva_linea
        coste_total += coste_unitario * cantidad
    
    # Calcular totales finales
    base_imponible = subtotal_materiales + mano_obra
    iva_mano_obra = mano_obra * 0.21  # IVA 21% sobre mano de obra
    presupuesto_total = base_imponible + total_iva + iva_mano_obra
    beneficio_estimado = presupuesto_total - coste_total - (mano_obra * 0.5)  # Asumimos ~50% coste de mano de obra
    
    # Actualizar en la base de datos
    update_data = {
        "subtotal_materiales": round(subtotal_materiales, 2),
        "total_iva": round(total_iva + iva_mano_obra, 2),
        "base_imponible": round(base_imponible, 2),
        "presupuesto_total": round(presupuesto_total, 2),
        "coste_total": round(coste_total, 2),
        "beneficio_estimado": round(beneficio_estimado, 2),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ordenes.update_one({"id": orden_id}, {"$set": update_data})
    
    return {
        "subtotal_materiales": update_data["subtotal_materiales"],
        "total_iva": update_data["total_iva"],
        "base_imponible": update_data["base_imponible"],
        "presupuesto_total": update_data["presupuesto_total"],
        "coste_total": update_data["coste_total"],
        "beneficio_estimado": update_data["beneficio_estimado"]
    }


# ==================== SUBESTADOS ====================

class CambiarSubestadoRequest(BaseModel):
    subestado: str  # SubestadoOrden value
    fecha_revision: Optional[str] = None  # ISO date string
    motivo: str

SUBESTADO_LABELS = {
    "ninguno": "Sin subestado",
    "esperando_repuestos": "Esperando repuestos",
    "esperando_autorizacion": "Esperando autorización",
    "esperando_cliente": "Esperando respuesta del cliente",
    "esperando_pago": "Esperando pago",
    "en_consulta_tecnica": "En consulta técnica",
    "pendiente_recogida": "Pendiente de recogida",
    "aseguradora": "Esperando aseguradora",
    "otro": "Otro"
}

# ==================== INSURAMA AUTO-SYNC ====================

# Mapping CRM status -> Sumbroker action type
CRM_TO_SUMBROKER_STATUS = {
    "recibida": "received",        # Solo pickup_date
    "en_taller": "in_repair",      # No action en Sumbroker
    "reparado": "repaired",        # Status 5 + repair_date
    "enviado": "shipped",          # tracking + shipping_date
    "entregado": "delivered",      # Status 6 + delivery_date
}

async def _get_sumbroker_client_safe():
    """Get Sumbroker client if credentials are configured. Returns None on failure."""
    try:
        from agent.scraper import SumbrokerClient
        config = await db.configuracion.find_one({"tipo": "sumbroker"}, {"_id": 0})
        if not config or not config.get("datos", {}).get("login"):
            login = os.environ.get("SUMBROKER_LOGIN")
            password = os.environ.get("SUMBROKER_PASSWORD")
            if not login or not password:
                return None
        else:
            login = config["datos"]["login"]
            password = config["datos"]["password"]
        return SumbrokerClient(login, password)
    except Exception as e:
        logger.error(f"Error creating Sumbroker client: {e}")
        return None

async def sync_order_status_to_insurama(orden: dict, nuevo_estado: str, codigo_envio: str = None):
    """
    Background task: sync CRM status change to Sumbroker.
    Only runs for orders with numero_autorizacion (Insurama origin).
    """
    codigo_auth = orden.get("numero_autorizacion")
    if not codigo_auth:
        return
    
    sumbroker_action = CRM_TO_SUMBROKER_STATUS.get(nuevo_estado)
    if not sumbroker_action:
        return
    
    try:
        client = await _get_sumbroker_client_safe()
        if not client:
            logger.warning("Insurama sync skipped: no credentials")
            return
        
        budget = await client.find_budget_by_service_code(codigo_auth)
        if not budget:
            logger.warning(f"Insurama sync: budget not found for {codigo_auth}")
            return
        
        budget_id = budget.get("id")
        result = None
        
        if nuevo_estado == "recibida":
            result = await client.mark_as_received(budget_id)
            # Guardar nota de recogida localmente (API no soporta POST observaciones)
            codigo_recogida = orden.get("codigo_recogida_salida") or codigo_envio
            if codigo_recogida:
                nota = f"Código de recogida: {codigo_recogida}"
                await db.ordenes.update_one(
                    {"id": orden["id"]},
                    {"$push": {"notas_insurama": {"fecha": datetime.now(timezone.utc).isoformat(), "mensaje": nota}}}
                )
        elif nuevo_estado == "en_taller":
            result = await client.mark_as_in_repair(budget_id)
        elif nuevo_estado == "reparado":
            result = await client.mark_as_repaired(budget_id)
        elif nuevo_estado == "enviado" and codigo_envio:
            transportista = orden.get("transportista")
            result = await client.mark_as_shipped(budget_id, codigo_envio, transportista)
            msg = f"Enviado con código {codigo_envio}"
            if transportista:
                msg += f", agencia: {transportista}"
            await db.ordenes.update_one(
                {"id": orden["id"]},
                {"$push": {"notas_insurama": {"fecha": datetime.now(timezone.utc).isoformat(), "mensaje": msg}}}
            )
        elif nuevo_estado == "entregado":
            result = await client.mark_as_delivered(budget_id)
        
        if result and result.get("success"):
            logger.info(f"Insurama sync OK: {codigo_auth} -> {sumbroker_action}")
            await db.ordenes.update_one(
                {"id": orden["id"]},
                {"$set": {f"insurama_sync_{nuevo_estado}": datetime.now(timezone.utc).isoformat()}}
            )
        elif result:
            logger.error(f"Insurama sync FAILED for {codigo_auth}: {result.get('error')}")
    except Exception as e:
        logger.error(f"Insurama sync exception for {codigo_auth}: {e}")

async def sync_diagnostico_to_insurama(orden: dict, diagnostico: str):
    """
    Background task: send technician diagnosis as observation to Sumbroker.
    """
    codigo_auth = orden.get("numero_autorizacion")
    if not codigo_auth or not diagnostico:
        return
    
    try:
        client = await _get_sumbroker_client_safe()
        if not client:
            return
        
        budget = await client.find_budget_by_service_code(codigo_auth)
        if not budget:
            return
        
        budget_id = budget.get("id")
        msg = f"Diagnóstico técnico: {diagnostico}"
        result = await client.send_observation(budget_id, msg, visible_to_client=False)
        
        if result and result.get("success"):
            logger.info(f"Insurama diagnosis sync OK: {codigo_auth}")
            await db.ordenes.update_one(
                {"id": orden["id"]},
                {"$set": {"insurama_diagnostico_enviado": True}}
            )
        else:
            logger.error(f"Insurama diagnosis sync FAILED for {codigo_auth}: {result.get('error', 'unknown')}")
    except Exception as e:
        logger.error(f"Insurama diagnosis sync exception: {e}")


# ==================== ALBARÁN AUTOMÁTICO ====================

async def crear_albaran_automatico(orden_id: str, user: dict):
    """
    Crear albarán automáticamente cuando una orden pasa a estado VALIDACION.
    El albarán se genera con los materiales de la orden y la mano de obra.
    """
    try:
        orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
        if not orden:
            logger.error(f"Albarán automático: Orden {orden_id} no encontrada")
            return
        
        # Verificar si ya tiene albarán
        if orden.get("albaran_id"):
            logger.info(f"Albarán automático: Orden {orden.get('numero_orden')} ya tiene albarán")
            return
        
        cliente_id = orden.get("cliente_id")
        if not cliente_id:
            logger.error(f"Albarán automático: Orden {orden.get('numero_orden')} sin cliente")
            return
        
        cliente = await db.clientes.find_one({"id": cliente_id}, {"_id": 0})
        if not cliente:
            logger.error(f"Albarán automático: Cliente {cliente_id} no encontrado")
            return
        
        # Obtener siguiente número de albarán
        año = datetime.now().year
        
        # Buscar último número del año
        ultimo = await db.contabilidad_series.find_one(
            {"tipo": "albaran", "año": año},
            {"_id": 0}
        )
        
        if ultimo:
            siguiente = ultimo.get("ultimo_numero", 0) + 1
        else:
            siguiente = 1
        
        # Actualizar serie
        await db.contabilidad_series.update_one(
            {"tipo": "albaran", "año": año},
            {"$set": {"ultimo_numero": siguiente, "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True
        )
        
        numero = f"ALB-{año}-{siguiente:05d}"
        
        # Crear líneas desde materiales de la orden
        lineas = []
        base_imponible = 0
        total_iva = 0
        
        for mat in orden.get("materiales", []):
            if not mat.get("aprobado", True):  # Solo materiales aprobados
                continue
            
            cantidad = mat.get("cantidad", 1)
            precio = mat.get("precio_unitario", 0)
            descuento = mat.get("descuento", 0)
            iva_pct = mat.get("iva", 21)
            
            subtotal = round(cantidad * precio * (1 - descuento / 100), 2)
            iva = round(subtotal * iva_pct / 100, 2)
            
            base_imponible += subtotal
            total_iva += iva
            
            lineas.append({
                "descripcion": mat.get("nombre", "Material"),
                "cantidad": cantidad,
                "precio_unitario": precio,
                "descuento": descuento,
                "tipo_iva": "general",
                "iva_porcentaje": iva_pct,
                "repuesto_id": mat.get("repuesto_id"),
                "orden_id": orden_id
            })
        
        # Añadir mano de obra si existe
        if orden.get("mano_obra", 0) > 0:
            mo = orden.get("mano_obra", 0)
            mo_iva = round(mo * 21 / 100, 2)
            base_imponible += mo
            total_iva += mo_iva
            
            lineas.append({
                "descripcion": "Mano de obra",
                "cantidad": 1,
                "precio_unitario": mo,
                "descuento": 0,
                "tipo_iva": "general",
                "iva_porcentaje": 21,
                "orden_id": orden_id
            })
        
        total = round(base_imponible + total_iva, 2)
        
        # Datos del dispositivo para el albarán
        dispositivo = orden.get("dispositivo", {})
        dispositivo_desc = f"{dispositivo.get('marca', '')} {dispositivo.get('modelo', '')}".strip()
        
        doc = {
            "id": str(uuid.uuid4()),
            "numero": numero,
            "orden_id": orden_id,
            "numero_orden": orden.get("numero_orden"),
            "numero_autorizacion": orden.get("numero_autorizacion"),
            "cliente_id": cliente_id,
            "nombre_cliente": f"{cliente.get('nombre', '')} {cliente.get('apellidos', '')}".strip(),
            "dispositivo": dispositivo_desc,
            "imei": dispositivo.get("imei"),
            "lineas": lineas,
            "base_imponible": round(base_imponible, 2),
            "total_iva": round(total_iva, 2),
            "total": total,
            "desglose_iva": {"21%": {"base": round(base_imponible, 2), "cuota": round(total_iva, 2)}},
            "notas": f"Reparación: {orden.get('descripcion_averia', '')}",
            "estado": "emitido",
            "facturado": False,
            "factura_id": None,
            # Para autofacturas (cuando paga un tercero como aseguradora)
            "pagador_tercero": orden.get("es_seguro", False) or bool(orden.get("numero_autorizacion")),
            "pagador_nombre": orden.get("aseguradora_nombre") if orden.get("es_seguro") else "Insurama",
            "pagador_nif": orden.get("aseguradora_nif") if orden.get("es_seguro") else None,
            "generado_automaticamente": True,
            "fecha_emision": datetime.now(timezone.utc).isoformat(),
            "año_fiscal": año,
            "created_by": user.get("email", "sistema"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.albaranes.insert_one(doc)
        
        # Vincular a la orden
        await db.ordenes.update_one(
            {"id": orden_id},
            {"$set": {
                "albaran_id": doc["id"],
                "albaran_numero": numero,
                "albaranado": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        logger.info(f"Albarán {numero} creado automáticamente para orden {orden.get('numero_orden')}")
        
        # Crear notificación
        await db.notificaciones.insert_one({
            "id": str(uuid.uuid4()),
            "tipo": "albaran_generado",
            "mensaje": f"📄 Albarán {numero} generado automáticamente para orden {orden.get('numero_orden')}",
            "orden_id": orden_id,
            "albaran_id": doc["id"],
            "leida": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error creando albarán automático para orden {orden_id}: {e}")


# ==================== AUDITORÍA ====================

async def registrar_auditoria(
    entidad: str,
    entidad_id: str,
    accion: str,
    usuario_id: str,
    usuario_email: str,
    rol: str,
    cambios: dict = None,
    ip_address: str = None
):
    """Registra una acción en el log de auditoría centralizado"""
    audit_doc = {
        "id": str(uuid.uuid4()),
        "entidad": entidad,
        "entidad_id": entidad_id,
        "accion": accion,
        "usuario_id": usuario_id,
        "usuario_email": usuario_email,
        "rol": rol,
        "cambios": cambios or {},
        "ip_address": ip_address,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.audit_logs.insert_one(audit_doc)


def _build_diff(before: dict, updates: dict) -> dict:
    diff = {}
    for key, new_value in updates.items():
        old_value = before.get(key)
        if old_value != new_value:
            diff[key] = {
                "before": old_value,
                "after": new_value,
            }
    return diff


async def registrar_evento_ot(
    ot_doc: dict,
    action: str,
    actor: dict,
    source: str,
    updates: Optional[dict] = None,
    before: Optional[dict] = None,
    ip_address: Optional[str] = None,
):
    before_data = before or {}
    updates_data = updates or {}
    after_data = {**before_data, **updates_data} if before else updates_data

    evento = {
        "id": str(uuid.uuid4()),
        "ot_id": ot_doc.get("id"),
        "numero_orden": ot_doc.get("numero_orden"),
        "action": action,
        "source": source,
        "actor_id": actor.get("user_id"),
        "actor_email": actor.get("email"),
        "actor_role": actor.get("role"),
        "ip_address": ip_address,
        "before": before_data,
        "updates": updates_data,
        "after": after_data,
        "diff": _build_diff(before_data, updates_data) if before else {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.ot_event_log.insert_one(evento)


# ==================== REQUEST MODELS ====================

class EnvioAuthUpdate(BaseModel):
    numero_autorizacion: Optional[str] = None
    agencia_envio: Optional[str] = None
    codigo_recogida_entrada: Optional[str] = None
    codigo_recogida_salida: Optional[str] = None
    datos_recogida: Optional[dict] = None
    datos_envio: Optional[dict] = None

class CambioEstadoRequest(BaseModel):
    nuevo_estado: OrderStatus
    usuario: str = "admin"
    mensaje: str  # OBLIGATORIO - Motivo del cambio de estado
    codigo_envio: Optional[str] = None
    forzar_sin_validacion: Optional[bool] = False  # Solo admin puede forzar


class ReceivingInspectionRequest(BaseModel):
    resultado_ri: str  # ok | sospechoso | no_conforme
    checklist_visual: dict
    fotos_recepcion: List[str]
    observaciones: Optional[str] = None
    propiedad_cliente_estado: Optional[str] = None
    propiedad_cliente_nota: Optional[str] = None


class CPINistRequest(BaseModel):
    tipo_ot: Optional[str] = None  # b2b / b2c
    requiere_borrado: bool = False
    autorizacion_cliente: Optional[bool] = None
    metodo: Optional[str] = None  # factory_reset / herramienta_validada / no_aplica_misma_unidad
    resultado: Optional[str] = None  # completado / fallido / no_aplica
    observaciones: Optional[str] = None
    # Nueva opción estructurada (3 opciones exclusivas ISO/WISE)
    opcion: Optional[str] = None  # cliente_ya_restablecio | cliente_no_autoriza | sat_realizo_restablecimiento



class PrintLogRequest(BaseModel):
    mode: str = 'full'  # full | no_prices | blank_no_prices
    output: str = 'print'  # print | pdf
    document_version: str = 'OT-PDF v1.1'

    propiedad_cliente_estado: Optional[str] = None
    propiedad_cliente_nota: Optional[str] = None


class ScanQRRequest(BaseModel):
    tipo_escaneo: str
    usuario: str = "admin"

class AñadirMaterialRequest(BaseModel):
    repuesto_id: Optional[str] = None
    nombre: Optional[str] = None
    cantidad: int = 1
    precio_unitario: Optional[float] = None
    coste: Optional[float] = None
    iva: Optional[float] = 21.0
    descuento: Optional[float] = 0
    añadido_por_tecnico: bool = False

class ActualizarMaterialRequest(BaseModel):
    precio_unitario: float
    coste: float
    iva: float = 21.0

class MaterialUpdate(BaseModel):
    nombre: Optional[str] = None
    nombre_personalizado: Optional[str] = None
    cantidad: Optional[int] = None
    precio_unitario: Optional[float] = None
    coste: Optional[float] = None
    iva: Optional[float] = None
    descuento: Optional[float] = 0

class DiagnosticoRequest(BaseModel):
    diagnostico: str

class EmitirPresupuestoRequest(BaseModel):
    """Request para emitir un presupuesto a una orden"""
    precio: float
    notas: Optional[str] = None
    validez_dias: int = 15

class AceptarPresupuestoRequest(BaseModel):
    """Request para registrar aceptación/rechazo de presupuesto"""
    aceptado: bool
    canal: str = "portal"  # portal, email, telefono
    motivo_rechazo: Optional[str] = None

class ActualizarFechaEstimadaRequest(BaseModel):
    """Request para actualizar fecha estimada de entrega"""
    fecha_estimada: str  # ISO format
    notificar_cliente: bool = True

class CrearOrdenRequest(BaseModel):
    """Request para crear orden con idempotency key"""
    idempotency_key: Optional[str] = None  # UUID para prevenir duplicados

# ==================== VALIDACIONES ====================

def validar_imei(imei: str) -> tuple[bool, str]:
    """Valida un IMEI usando el algoritmo Luhn.
    
    Returns:
        tuple: (es_valido, mensaje)
    """
    if not imei:
        return True, ""  # IMEI opcional
    
    # Limpiar IMEI
    imei_clean = ''.join(filter(str.isdigit, imei))
    
    # Verificar longitud (15 o 16 dígitos)
    if len(imei_clean) not in [15, 16]:
        return False, f"IMEI debe tener 15 o 16 dígitos, tiene {len(imei_clean)}"
    
    # Algoritmo Luhn
    def luhn_checksum(num_str):
        def digits_of(n):
            return [int(d) for d in str(n)]
        digits = digits_of(num_str)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10
    
    if luhn_checksum(imei_clean[:15]) != 0:
        return False, "IMEI no válido (falla verificación Luhn)"
    
    return True, ""


def parse_imeis(imei_field: str) -> list[str]:
    """Parsea un campo IMEI que puede contener uno o dos IMEIs separados por //
    Ejemplo: '123456789123456 // 152345678912345' → ['123456789123456', '152345678912345']
    """
    if not imei_field:
        return []
    return [s.strip() for s in imei_field.split('//') if s.strip()]


def imei_matches(imei_escaneado: str, imei_field: str) -> bool:
    """Verifica si un IMEI escaneado coincide con alguno de los IMEIs del campo (soporta IMEIs duales separados por //)."""
    if not imei_escaneado or not imei_field:
        return True  # Si no hay IMEI, no verificar
    imeis = parse_imeis(imei_field)
    escaneado_clean = ''.join(filter(str.isdigit, imei_escaneado))
    for imei in imeis:
        imei_clean = ''.join(filter(str.isdigit, imei))
        if escaneado_clean == imei_clean:
            return True
    return False


def _parse_datetime_safe(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


def _normalizar_orden_doc(orden: dict) -> dict:
    normalized = dict(orden)

    cliente_data = normalized.get("cliente") if isinstance(normalized.get("cliente"), dict) else {}
    normalized["cliente_id"] = normalized.get("cliente_id") or cliente_data.get("id") or ""

    dispositivo_raw = normalized.get("dispositivo") if isinstance(normalized.get("dispositivo"), dict) else {}
    normalized["dispositivo"] = {
        "modelo": dispositivo_raw.get("modelo") or normalized.get("dispositivo_modelo") or "",
        "imei": dispositivo_raw.get("imei") or normalized.get("dispositivo_imei") or "",
        "color": dispositivo_raw.get("color") or normalized.get("dispositivo_color") or "",
        "daños": dispositivo_raw.get("daños") or normalized.get("averia_descripcion") or normalized.get("diagnostico_tecnico") or "",
    }

    estado = normalized.get("estado")
    if estado not in {s.value for s in OrderStatus}:
        normalized["estado"] = OrderStatus.PENDIENTE_RECIBIR.value

    if normalized.get("materiales") is None:
        normalized["materiales"] = []
    if normalized.get("historial_estados") is None:
        normalized["historial_estados"] = []
    if normalized.get("mensajes") is None:
        normalized["mensajes"] = []
    if normalized.get("evidencias") is None:
        normalized["evidencias"] = []
    if normalized.get("evidencias_tecnico") is None:
        normalized["evidencias_tecnico"] = []

    normalized["created_at"] = _parse_datetime_safe(normalized.get("created_at"))
    normalized["updated_at"] = _parse_datetime_safe(normalized.get("updated_at"))
    
    # Remove nested MongoDB _id fields that may cause serialization issues
    if "ultimo_consentimiento_seguimiento" in normalized:
        consent_data = normalized["ultimo_consentimiento_seguimiento"]
        if isinstance(consent_data, dict) and "_id" in consent_data:
            del consent_data["_id"]
    
    return normalized

# ==================== CRUD ÓRDENES ====================

@router.post("/ordenes", response_model=OrdenTrabajo)
async def crear_orden(orden: OrdenTrabajoCreate, user: dict = Depends(require_auth)):
    # Verificar idempotency_key para prevenir duplicados
    idempotency_key = getattr(orden, 'idempotency_key', None)
    if idempotency_key:
        existing = await db.ordenes.find_one({"idempotency_key": idempotency_key}, {"_id": 0})
        if existing:
            logger.info(f"Orden duplicada detectada con idempotency_key: {idempotency_key}")
            return OrdenTrabajo(**existing)
    
    cliente = await db.clientes.find_one({"id": orden.cliente_id}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Resolver nombre del creador
    creator_user = await db.users.find_one({"email": user.get('email')}, {"_id": 0, "nombre": 1, "apellidos": 1})
    creator_name = user.get('email', 'sistema')
    if creator_user:
        cn = creator_user.get('nombre', '')
        ca = creator_user.get('apellidos', '')
        creator_name = f"{cn} {ca}".strip() or creator_name

    orden_obj = OrdenTrabajo(**orden.model_dump())
    orden_obj.qr_code = generate_barcode(orden_obj.numero_orden)
    orden_obj.historial_estados = [{"estado": OrderStatus.PENDIENTE_RECIBIR.value, "fecha": datetime.now(timezone.utc).isoformat(), "usuario": creator_name}]
    
    doc = orden_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['ri_obligatoria'] = True
    doc['ri_completada'] = False
    
    # Guardar idempotency_key si existe
    if idempotency_key:
        doc['idempotency_key'] = idempotency_key
    
    await db.ordenes.insert_one(doc)

    await registrar_evento_ot(
        ot_doc=doc,
        action="orden_creada",
        actor=user,
        source="api",
        updates={"estado": doc.get("estado"), "ri_obligatoria": True},
    )
    
    # Registrar en auditoría
    await registrar_auditoria(
        entidad="orden",
        entidad_id=orden_obj.id,
        accion="crear",
        usuario_id=user.get('user_id'),
        usuario_email=user.get('email'),
        rol=user.get('role'),
        cambios={"numero_orden": orden_obj.numero_orden, "cliente_id": orden.cliente_id}
    )
    
    try:
        await send_order_notification(doc, cliente, "created")
    except Exception as e:
        logger.error(f"Error enviando notificación de creación: {e}")
    return orden_obj


@router.post("/ordenes/{orden_id}/receiving-inspection")
async def registrar_receiving_inspection(orden_id: str, payload: ReceivingInspectionRequest, user: dict = Depends(require_tecnico)):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    resultado = (payload.resultado_ri or "").lower().strip()
    if resultado not in {"ok", "sospechoso", "no_conforme"}:
        raise HTTPException(status_code=400, detail="resultado_ri debe ser: ok, sospechoso o no_conforme")

    if not payload.fotos_recepcion or len(payload.fotos_recepcion) < 3:
        raise HTTPException(status_code=400, detail="Debes adjuntar al menos 3 fotos de recepción (frontal/trasera/daños)")

    now = datetime.now(timezone.utc)

    # Obtener nombre del técnico (nunca email en PDF)
    db_user_ri = await db.users.find_one({"id": user['user_id']}, {"_id": 0})
    nombre_tecnico_ri = "Nombre no configurado"
    if db_user_ri:
        nombre = db_user_ri.get('nombre', '').strip()
        apellidos = db_user_ri.get('apellidos', '').strip()
        primer_apellido = apellidos.split()[0] if apellidos else ''
        if nombre:
            nombre_tecnico_ri = f"{nombre} {primer_apellido}".strip()

    update_data = {
        "ri_completada": True,
        "ri_resultado": resultado,
        "ri_checklist_visual": payload.checklist_visual,
        "ri_fotos_recepcion": payload.fotos_recepcion,
        "ri_observaciones": payload.observaciones,
        "ri_propiedad_cliente_estado": payload.propiedad_cliente_estado,
        "ri_propiedad_cliente_nota": payload.propiedad_cliente_nota,
        "ri_usuario": user.get("email"),
        "ri_usuario_nombre": nombre_tecnico_ri,
        "ri_fecha": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    historial = orden.get("historial_estados", [])
    nuevo_estado = None
    
    if resultado in {"sospechoso", "no_conforme"} and orden.get("estado") != OrderStatus.CUARENTENA.value:
        # RI con problemas -> Cuarentena
        historial.append({"estado": OrderStatus.CUARENTENA.value, "fecha": now.isoformat(), "usuario": user.get("email", "Sistema")})
        update_data["estado"] = OrderStatus.CUARENTENA.value
        update_data["historial_estados"] = historial
        nuevo_estado = OrderStatus.CUARENTENA.value
    elif resultado == "ok" and orden.get("estado") in {OrderStatus.PENDIENTE_RECIBIR.value, OrderStatus.RECIBIDA.value}:
        # RI OK -> Automáticamente pasa a En Taller (inicia reparación)
        historial.append({"estado": OrderStatus.EN_TALLER.value, "fecha": now.isoformat(), "usuario": user.get("email", "Sistema")})
        update_data["estado"] = OrderStatus.EN_TALLER.value
        update_data["historial_estados"] = historial
        update_data["fecha_inicio_reparacion"] = now.isoformat()
        nuevo_estado = OrderStatus.EN_TALLER.value

    await db.ordenes.update_one({"id": orden_id}, {"$set": update_data})

    await registrar_evento_ot(
        ot_doc=orden,
        action="receiving_inspection",
        actor=user,
        source="api_ri",
        updates=update_data,
        before={"estado": orden.get("estado"), "ri_completada": orden.get("ri_completada")},
    )

    estado_final = nuevo_estado or orden.get("estado")
    mensaje = "Receiving Inspection registrada correctamente"
    if nuevo_estado == OrderStatus.EN_TALLER.value:
        mensaje = "RI completada — Reparación iniciada automáticamente"
    elif nuevo_estado == OrderStatus.CUARENTENA.value:
        mensaje = "RI registrada — Orden en Cuarentena por resultado sospechoso/no conforme"

    return {
        "message": mensaje,
        "estado_actual": estado_final,
        "resultado_ri": resultado,
    }


@router.get("/ordenes/{orden_id}/eventos-auditoria")
async def listar_eventos_auditoria_orden(orden_id: str, user: dict = Depends(require_auth)):
    eventos = await db.ot_event_log.find({"ot_id": orden_id}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    return eventos


# ==================== PROYECCIÓN OPTIMIZADA PARA LISTADOS ====================
# Campos mínimos para mostrar en tablas/listas (reduce payload ~90%)
LISTADO_PROJECTION = {
    "_id": 0,
    "id": 1,
    "numero_orden": 1,
    "estado": 1,
    "subestado": 1,
    "created_at": 1,
    "updated_at": 1,
    "cliente_id": 1,
    "tecnico_asignado": 1,
    "dispositivo.modelo": 1,
    "dispositivo.imei": 1,
    "dispositivo.color": 1,
    "averia_descripcion": 1,
    "presupuesto_total": 1,
    "numero_autorizacion": 1,
    "es_garantia": 1,
    "bloqueada": 1,
    "ri_completada": 1,
    "ri_resultado": 1,
    "fecha_recogida": 1,
    "fecha_entrega_estimada": 1,
    "tracking_envio": 1,
    # Fechas de proceso y historial para mostrar "desde cuándo" está en el estado actual
    "fecha_recibida_centro": 1,
    "fecha_inicio_reparacion": 1,
    "fecha_fin_reparacion": 1,
    "fecha_enviado": 1,
    "historial_estados": 1,
    # GLS v2: solo los campos mínimos que necesita el icono de la lista
    "gls_envios.codbarras": 1,
    "gls_envios.tracking_url": 1,
    "gls_envios.estado_actual": 1,
    "gls_envios.estado_codigo": 1,
    "gls_envios.incidencia": 1,
    "gls_envios.mock_preview": 1,
}

@router.get("/ordenes/v2")
async def listar_ordenes_v2(
    estado: Optional[str] = None,
    cliente_id: Optional[str] = None,
    search: Optional[str] = None,
    telefono: Optional[str] = None,
    autorizacion: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    fecha_campo: Optional[str] = "created_at",
    solo_garantias: Optional[bool] = None,
    page: int = 1,
    page_size: int = 50,
    user: dict = Depends(require_auth)
):
    """
    Endpoint optimizado de listado de órdenes con paginación.
    Devuelve solo campos necesarios para listados (reduce payload ~90%).
    """
    query = {}
    conditions = []
    
    if estado:
        conditions.append({"estado": estado})
    if cliente_id:
        conditions.append({"cliente_id": cliente_id})
    if solo_garantias:
        conditions.append({"es_garantia": True})
    if autorizacion:
        conditions.append({"numero_autorizacion": {"$regex": autorizacion, "$options": "i"}})
    if telefono:
        telefono_clean = ''.join(filter(str.isdigit, telefono))
        clientes = await db.clientes.find(
            {"telefono": {"$regex": telefono_clean, "$options": "i"}},
            {"id": 1, "_id": 0}
        ).to_list(100)
        cliente_ids = [c['id'] for c in clientes]
        if cliente_ids:
            conditions.append({"cliente_id": {"$in": cliente_ids}})
        else:
            return {"data": [], "total": 0, "page": page, "page_size": page_size, "pages": 0}
    if search:
        # Buscar también por código de barras GLS
        conditions.append({
            "$or": [
                {"numero_orden": {"$regex": search, "$options": "i"}},
                {"numero_autorizacion": {"$regex": search, "$options": "i"}},
                {"dispositivo.modelo": {"$regex": search, "$options": "i"}},
                {"dispositivo.imei": {"$regex": search, "$options": "i"}},
                {"gls_envios.codbarras": search},  # Código de barras GLS exacto
                {"codigo_recogida_entrada": search},  # Código legacy
                {"codigo_recogida_salida": search},
            ]
        })

    # Filtros de fecha — campo configurable (created_at | fecha_recibida_centro | fecha_enviado | fecha_fin_reparacion | fecha_inicio_reparacion)
    campos_fecha_validos = {"created_at", "fecha_recibida_centro", "fecha_enviado", "fecha_fin_reparacion", "fecha_inicio_reparacion"}
    campo_fecha_aplicado = fecha_campo if fecha_campo in campos_fecha_validos else "created_at"

    if fecha_desde:
        conditions.append({campo_fecha_aplicado: {"$gte": fecha_desde}})
    if fecha_hasta:
        conditions.append({campo_fecha_aplicado: {"$lte": fecha_hasta}})
    
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    
    # Paginación
    skip = (page - 1) * page_size
    
    # Count total (usar count_documents para eficiencia)
    total = await db.ordenes.count_documents(query)
    
    # Obtener datos con proyección optimizada
    ordenes = await db.ordenes.find(query, LISTADO_PROJECTION)\
        .sort(campo_fecha_aplicado, -1)\
        .skip(skip)\
        .limit(page_size)\
        .to_list(page_size)
    
    return {
        "data": ordenes,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }


# ==================== ESCANEO INTELIGENTE DASHBOARD ====================

@router.get("/ordenes/buscar")
async def buscar_orden_escaner(q: str, user: dict = Depends(require_auth)):
    """
    Busca órdenes por código/número para el escáner del Dashboard.
    - Si encuentra exactamente 1 orden en estado pendiente_recibir, la marca como recibida
    - Si la orden está en otro estado, solo devuelve los datos para navegación
    - Devuelve lista de órdenes si hay múltiples coincidencias
    """
    if not q or not q.strip():
        raise HTTPException(400, "Se requiere un término de búsqueda")
    
    codigo = q.strip().upper()
    
    # Buscar por múltiples campos
    query = {"$or": [
        {"id": codigo},
        {"numero_orden": {"$regex": codigo, "$options": "i"}},
        {"numero_autorizacion": {"$regex": codigo, "$options": "i"}},
        {"codigo_recogida_entrada": {"$regex": codigo, "$options": "i"}},
        {"gls_envios.codbarras": codigo},
        {"dispositivo.imei": {"$regex": codigo, "$options": "i"}},
    ]}
    
    ordenes = await db.ordenes.find(query, {"_id": 0}).to_list(50)
    
    if not ordenes:
        return {"ordenes": [], "accion": None, "mensaje": "No se encontraron órdenes"}
    
    # Si hay exactamente una orden
    if len(ordenes) == 1:
        orden = ordenes[0]
        
        # Si está pendiente de recibir, marcarla como recibida automáticamente
        if orden.get("estado") == OrderStatus.PENDIENTE_RECIBIR.value:
            now = datetime.now(timezone.utc)
            nuevo_estado = OrderStatus.RECIBIDA.value
            
            historial = orden.get('historial_estados', [])
            historial.append({
                "estado": nuevo_estado,
                "fecha": now.isoformat(),
                "usuario": user.get("email", "scanner")
            })
            
            update_data = {
                "estado": nuevo_estado,
                "historial_estados": historial,
                "fecha_recibida_centro": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            await db.ordenes.update_one({"id": orden["id"]}, {"$set": update_data})
            
            # Notificar
            try:
                cliente = await db.clientes.find_one({"id": orden.get('cliente_id')}, {"_id": 0})
                if cliente:
                    orden_act = orden.copy()
                    orden_act['estado'] = nuevo_estado
                    await send_order_notification(orden_act, cliente, "status_change")
            except Exception as e:
                logger.error(f"Error enviando notificación por escaneo dashboard: {e}")
            
            return {
                "ordenes": [{
                    "id": orden["id"],
                    "numero_orden": orden.get("numero_orden"),
                    "estado": nuevo_estado,
                    "dispositivo": orden.get("dispositivo")
                }],
                "accion": "recibida",
                "mensaje": f"Orden {orden.get('numero_orden')} marcada como RECIBIDA"
            }
        
        # Si no está pendiente, solo devolver para navegación
        # Enriquecer con tipo de match (codbarras GLS, autorización, etc.)
        match_type = "orden"
        match_meta = {}
        if str(orden.get("numero_autorizacion", "")).upper() == codigo:
            match_type = "autorizacion"
            match_meta["numero_autorizacion"] = orden.get("numero_autorizacion")
        else:
            # ¿Es un codbarras GLS?
            for e in (orden.get("gls_envios") or []):
                if str(e.get("codbarras", "")) == codigo:
                    match_type = "gls_codbarras"
                    try:
                        from modules.logistica.state_mapper import (
                            friendly_estado as _fe, interno_estado as _ie,
                        )
                        estado_raw = e.get("estado_actual") or e.get("estado") or ""
                        codigo_est = str(e.get("estado_codigo") or "")
                        match_meta = {
                            "codbarras": e.get("codbarras"),
                            "estado_interno": _ie(estado_raw, codigo_est, e.get("incidencia", "")),
                            "estado_cliente": _fe(estado_raw, codigo_est),
                            "tracking_url": e.get("tracking_url"),
                            "fecha_entrega": e.get("fecha_entrega", ""),
                        }
                    except Exception:
                        match_meta = {"codbarras": e.get("codbarras")}
                    break

        return {
            "ordenes": [{
                "id": orden["id"],
                "numero_orden": orden.get("numero_orden"),
                "estado": orden.get("estado"),
                "dispositivo": orden.get("dispositivo"),
                "numero_autorizacion": orden.get("numero_autorizacion"),
            }],
            "accion": "navegacion",
            "match_type": match_type,
            "match_meta": match_meta,
            "mensaje": f"Abriendo orden {orden.get('numero_orden')}"
        }
    
    # Si hay múltiples órdenes, devolver lista
    return {
        "ordenes": [{
            "id": o["id"],
            "numero_orden": o.get("numero_orden"),
            "estado": o.get("estado"),
            "dispositivo": o.get("dispositivo")
        } for o in ordenes],
        "accion": "multiple",
        "mensaje": f"Se encontraron {len(ordenes)} órdenes"
    }


@router.get("/ordenes", response_model=List[OrdenTrabajo])
async def listar_ordenes(estado: Optional[str] = None, cliente_id: Optional[str] = None, search: Optional[str] = None, telefono: Optional[str] = None, autorizacion: Optional[str] = None, fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None, fecha_campo: Optional[str] = "created_at", solo_garantias: Optional[bool] = None):
    query = {}
    conditions = []
    if estado:
        conditions.append({"estado": estado})
    if cliente_id:
        conditions.append({"cliente_id": cliente_id})
    if solo_garantias:
        conditions.append({"es_garantia": True})
    if autorizacion:
        conditions.append({"numero_autorizacion": {"$regex": autorizacion, "$options": "i"}})
    if telefono:
        telefono_clean = ''.join(filter(str.isdigit, telefono))
        clientes = await db.clientes.find({"telefono": {"$regex": telefono_clean, "$options": "i"}}, {"id": 1, "_id": 0}).to_list(100)
        cliente_ids = [c['id'] for c in clientes]
        if cliente_ids:
            conditions.append({"cliente_id": {"$in": cliente_ids}})
        else:
            return []
    if search:
        conditions.append({"$or": [{"numero_orden": {"$regex": search, "$options": "i"}}, {"numero_autorizacion": {"$regex": search, "$options": "i"}}, {"dispositivo.modelo": {"$regex": search, "$options": "i"}}, {"dispositivo.imei": {"$regex": search, "$options": "i"}}]})

    # Filtros de fecha sobre el campo elegido (created_at | fecha_recibida_centro | fecha_enviado | fecha_fin_reparacion)
    campos_fecha_validos = {"created_at", "fecha_recibida_centro", "fecha_enviado", "fecha_fin_reparacion", "fecha_inicio_reparacion"}
    campo_fecha_aplicado = fecha_campo if fecha_campo in campos_fecha_validos else "created_at"
    if fecha_desde:
        conditions.append({campo_fecha_aplicado: {"$gte": fecha_desde}})
    if fecha_hasta:
        conditions.append({campo_fecha_aplicado: {"$lte": fecha_hasta}})
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]

    ordenes = await db.ordenes.find(query, {"_id": 0}).sort(campo_fecha_aplicado, -1).to_list(1000)

    ordenes_normalizadas = []
    for orden in ordenes:
        normalized = _normalizar_orden_doc(orden)
        try:
            OrdenTrabajo(**normalized)
            ordenes_normalizadas.append(normalized)
        except Exception as e:
            logger.warning(f"Orden inválida omitida en listado ({orden.get('id', 'sin-id')}): {e}")

    return ordenes_normalizadas


@router.patch("/ordenes/{orden_id}/cpi")
async def registrar_cpi_nist(orden_id: str, payload: CPINistRequest, user: dict = Depends(require_tecnico)):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    cliente = await db.clientes.find_one({"id": orden.get("cliente_id")}, {"_id": 0}) if orden.get("cliente_id") else None
    tipo_cliente = (payload.tipo_ot or (cliente or {}).get('tipo_cliente') or 'particular').lower()
    tipo_ot = 'b2b' if tipo_cliente in {'empresa', 'b2b'} else 'b2c'

    metodo = (payload.metodo or '').strip().lower() or None
    resultado = (payload.resultado or '').strip().lower() or None

    metodos_validos = {'factory_reset', 'herramienta_validada', 'no_aplica_misma_unidad'}
    resultados_validos = {'completado', 'fallido', 'no_aplica'}

    if metodo and metodo not in metodos_validos:
        raise HTTPException(status_code=400, detail="Método CPI inválido")
    if resultado and resultado not in resultados_validos:
        raise HTTPException(status_code=400, detail="Resultado CPI inválido")

    if tipo_ot == 'b2b':
        if not metodo:
            raise HTTPException(status_code=400, detail="En OT B2B el método CPI/NIST es obligatorio")
        if not resultado:
            raise HTTPException(status_code=400, detail="En OT B2B el resultado CPI/NIST es obligatorio")

    if tipo_ot == 'b2c' and payload.requiere_borrado:
        if not payload.autorizacion_cliente:
            raise HTTPException(status_code=400, detail="En OT B2C se requiere autorización del cliente para borrado")
        if not metodo:
            raise HTTPException(status_code=400, detail="Debes indicar método de borrado para OT B2C con borrado requerido")

    # Obtener nombre del técnico (nunca email en PDF)
    db_user = await db.users.find_one({"id": user['user_id']}, {"_id": 0})
    nombre_tecnico = "Nombre no configurado"
    if db_user:
        nombre = db_user.get('nombre', '').strip()
        apellidos = db_user.get('apellidos', '').strip()
        primer_apellido = apellidos.split()[0] if apellidos else ''
        if nombre:
            nombre_tecnico = f"{nombre} {primer_apellido}".strip()

    now = datetime.now(timezone.utc).isoformat()
    update_data = {
        'cpi_tipo_ot': tipo_ot,
        'cpi_opcion': payload.opcion or None,
        'cpi_requiere_borrado': bool(payload.requiere_borrado),
        'cpi_autorizacion_cliente': bool(payload.autorizacion_cliente) if payload.autorizacion_cliente is not None else None,
        'cpi_metodo': metodo,
        'cpi_resultado': resultado,
        'cpi_observaciones': payload.observaciones,
        'cpi_usuario': user.get('email'),
        'cpi_usuario_nombre': nombre_tecnico,
        'cpi_fecha': now,
        'updated_at': now,
    }

    await db.ordenes.update_one({'id': orden_id}, {'$set': update_data})

    await registrar_evento_ot(
        ot_doc=orden,
        action='cpi_nist_registrado',
        actor=user,
        source='api_cpi',
        updates=update_data,
        before={
            'cpi_metodo': orden.get('cpi_metodo'),
            'cpi_resultado': orden.get('cpi_resultado'),
            'cpi_requiere_borrado': orden.get('cpi_requiere_borrado'),
        },
    )

    return await db.ordenes.find_one({'id': orden_id}, {'_id': 0})

@router.get("/ordenes/{orden_ref}", response_model=OrdenTrabajo)
async def obtener_orden(orden_ref: str):
    # Limpiar el código de caracteres especiales
    codigo = orden_ref.strip().upper()
    
    # Buscar por múltiples campos
    orden = await db.ordenes.find_one({"id": orden_ref}, {"_id": 0})
    if not orden:
        orden = await db.ordenes.find_one({"numero_orden": {"$regex": f"^{codigo}$", "$options": "i"}}, {"_id": 0})
    if not orden:
        orden = await db.ordenes.find_one({"numero_autorizacion": {"$regex": f"^{codigo}$", "$options": "i"}}, {"_id": 0})
    if not orden:
        orden = await db.ordenes.find_one({"codigo_recogida_entrada": codigo}, {"_id": 0})
    if not orden:
        orden = await db.ordenes.find_one({"gls_envios.codbarras": codigo}, {"_id": 0})
    if not orden:
        orden = await db.ordenes.find_one({"dispositivo.imei": codigo}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return _normalizar_orden_doc(orden)


@router.post('/ordenes/{orden_id}/registro-impresion')
async def registrar_impresion_ot(orden_id: str, payload: PrintLogRequest, user: dict = Depends(require_auth), request: Request = None):
    orden = await db.ordenes.find_one({'id': orden_id}, {'_id': 0})
    if not orden:
        raise HTTPException(status_code=404, detail='Orden no encontrada')

    mode = (payload.mode or 'full').strip().lower()
    if mode not in {'full', 'no_prices', 'blank_no_prices'}:
        raise HTTPException(status_code=400, detail='mode inválido')

    if mode == 'full' and user.get('role') not in {'admin', 'master'}:
        raise HTTPException(status_code=403, detail='Solo admin/master pueden generar ficha con precios')

    now = datetime.now(timezone.utc).isoformat()
    log = {
        'id': str(uuid.uuid4()),
        'orden_id': orden_id,
        'numero_orden': orden.get('numero_orden'),
        'mode': mode,
        'output': payload.output,
        'document_version': payload.document_version,
        'generated_by': user.get('email'),
        'generated_role': user.get('role'),
        'generated_at': now,
        'ip_address': request.client.host if request and request.client else None,
    }
    await db.ot_print_logs.insert_one(log)

    await registrar_evento_ot(
        ot_doc=orden,
        action='ot_print_generated',
        actor=user,
        source='print_view',
        updates={'print_mode': mode, 'output': payload.output, 'document_version': payload.document_version},
        before={},
        ip_address=log['ip_address'],
    )

    log.pop('_id', None)
    return log

@router.put("/ordenes/{orden_id}", response_model=OrdenTrabajo)
async def actualizar_orden(orden_id: str, orden: OrdenTrabajoCreate, user: dict = Depends(require_admin)):
    """Actualización completa de una orden - SOLO ADMIN"""
    existing = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    update_data = orden.model_dump()
    
    # ============ PROTECCIÓN DE FOTOS - NUNCA BORRAR ============
    campos_fotos_protegidos = ['evidencias', 'evidencias_tecnico', 'fotos_antes', 'fotos_despues', 'fotos_recepcion']
    for campo in campos_fotos_protegidos:
        valor_existente = existing.get(campo, []) or []
        valor_nuevo = update_data.get(campo, []) or []
        # Si el nuevo valor es vacío pero ya hay fotos, mantener las existentes
        if len(valor_nuevo) == 0 and len(valor_existente) > 0:
            update_data[campo] = valor_existente
        # Si hay valores nuevos, fusionar
        elif len(valor_nuevo) > 0:
            update_data[campo] = list(set(valor_existente + valor_nuevo))
    # ============================================================
    
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    await db.ordenes.update_one({"id": orden_id}, {"$set": update_data})
    updated = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    return _normalizar_orden_doc(updated)

@router.patch("/ordenes/{orden_id}")
async def actualizar_orden_parcial(orden_id: str, data: dict, user: dict = Depends(require_auth)):
    """Actualización parcial de una orden con control de permisos por rol."""
    existing = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # ============ PROTECCIÓN DE FOTOS - NUNCA BORRAR ============
    # Estos campos SOLO pueden añadirse, nunca sobrescribirse con arrays vacíos
    campos_fotos_protegidos = ['evidencias', 'evidencias_tecnico', 'fotos_antes', 'fotos_despues', 'fotos_recepcion']
    for campo in campos_fotos_protegidos:
        if campo in data:
            valor_nuevo = data[campo]
            valor_existente = existing.get(campo, []) or []
            # Si intentan enviar array vacío pero ya hay fotos, mantener las existentes
            if isinstance(valor_nuevo, list) and len(valor_nuevo) == 0 and len(valor_existente) > 0:
                logger.warning(f"Protección de fotos: Ignorando intento de borrar {campo} en orden {orden_id}")
                del data[campo]
            # Si envían nuevas fotos, fusionar con las existentes (no duplicar)
            elif isinstance(valor_nuevo, list) and len(valor_nuevo) > 0:
                fotos_combinadas = list(set(valor_existente + valor_nuevo))
                data[campo] = fotos_combinadas
    # ============================================================
    
    # Campos que un técnico puede actualizar en su flujo operativo
    campos_tecnico_permitidos = [
        'imei_validado', 'imei_escaneado_incorrecto', 'bloqueada', 'motivo_bloqueo',
        'diagnostico_tecnico', 'diagnostico_salida_realizado', 'funciones_verificadas',
        'limpieza_realizada', 'notas_cierre_tecnico', 'fecha_fin_reparacion',
        'recepcion_checklist_completo', 'recepcion_estado_fisico_registrado',
        'recepcion_accesorios_registrados', 'recepcion_notas', 'diagnostico_recepcion', 'bateria_reemplazada',
        'bateria_almacenamiento_temporal', 'bateria_residuo_pendiente',
        'bateria_gestor_autorizado', 'bateria_fecha_entrega_gestor',
        'ri_completada',  # El técnico puede marcar RI como completada
        # Campos de QC al cerrar reparación (TecnicoCierreReparacion)
        'bateria_nivel', 'bateria_ciclos', 'bateria_estado',
        'qc_funciones', 'qc_funciones_no_aplica', 'qc_es_smartphone',
        'qc_resultado_averia', 'qc_motivo_no_reparada',
        'garantia_resultado', 'garantia_motivo_no_procede', 'garantia_tests_omitidos',
    ]

    # Campos de diagnóstico/QC que el técnico puede modificar libremente
    # Admin puede LEER estos campos pero NO modificarlos (excepto diagnostico_tecnico e indicaciones)
    campos_diagnostico_qc_exclusivos_tecnico = [
        'notas_cierre_tecnico',
        'fecha_fin_reparacion',
        'recepcion_checklist_completo',
        'recepcion_estado_fisico_registrado',
        'recepcion_accesorios_registrados',
        'recepcion_notas',
    ]
    
    # Campos que TANTO admin como técnico pueden editar
    campos_admin_y_tecnico = [
        'diagnostico_tecnico',       # Admin puede editar/revisar el diagnóstico
        'indicaciones_tecnico',      # Admin da instrucciones al técnico
        'tecnico_asignado',          # Asignación de técnico
        'tecnico_nombre',            # Nombre del técnico asignado
    ]
    
    # Campos de QC que el admin PUEDE marcar como completados al finalizar
    campos_qc_finalizacion = [
        'diagnostico_salida_realizado',
        'funciones_verificadas',
        'limpieza_realizada',
    ]
    
    is_admin = user.get('role') in ['admin', 'master']
    if not is_admin:
        # Técnico: solo puede editar sus campos permitidos + campos compartidos
        campos_permitidos_tecnico = campos_tecnico_permitidos + campos_admin_y_tecnico
        data = {k: v for k, v in data.items() if k in campos_permitidos_tecnico}
    else:
        # Admin: puede editar casi todo EXCEPTO campos exclusivos del técnico
        intentos_restringidos = [k for k in data.keys() if k in campos_diagnostico_qc_exclusivos_tecnico]
        
        # Verificar si intenta modificar campos de QC de finalización
        intentos_qc = [k for k in data.keys() if k in campos_qc_finalizacion]
        for campo_qc in intentos_qc:
            # Solo permitir si está marcando como True (completado)
            if data.get(campo_qc) != True:
                intentos_restringidos.append(campo_qc)
        
        if intentos_restringidos:
            raise HTTPException(
                status_code=403,
                detail="Algunos campos de control de calidad solo pueden ser actualizados por el técnico",
            )
    
    if not data:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    # Campos protegidos que nunca se pueden modificar
    for campo in ['id', 'numero_orden', 'created_at']:
        data.pop(campo, None)
    
    now = datetime.now(timezone.utc)
    data['updated_at'] = now.isoformat()
    
    # Obtener info del usuario para el historial
    db_user = await db.users.find_one({"id": user['user_id']}, {"_id": 0})
    usuario_nombre = db_user.get('nombre', user.get('email', 'Sistema')) if db_user else user.get('email', 'Sistema')
    
    # Si se está bloqueando la orden, registrar en historial de bloqueos
    if data.get('bloqueada') and not existing.get('bloqueada'):
        historial_bloqueos = existing.get('historial_bloqueos', [])
        nuevo_bloqueo = {
            "id": str(uuid.uuid4()),
            "fecha": now.isoformat(),
            "motivo": data.get('motivo_bloqueo', 'Sin especificar'),
            "bloqueado_por": usuario_nombre,
            "bloqueado_por_id": user.get('user_id'),
            "bloqueado_por_rol": user.get('role'),
            "imei_escaneado": data.get('imei_escaneado_incorrecto'),
            "imei_esperado": existing.get('dispositivo', {}).get('imei'),
            "resuelto": False,
            "resuelto_por": None,
            "fecha_resolucion": None,
            "notas_resolucion": None
        }
        historial_bloqueos.append(nuevo_bloqueo)
        data['historial_bloqueos'] = historial_bloqueos
        data['bloqueo_actual_id'] = nuevo_bloqueo['id']
    
    # Si se está desbloqueando (admin aprueba), marcar el bloqueo como resuelto
    if not data.get('bloqueada', True) and existing.get('bloqueada') and is_admin:
        historial_bloqueos = existing.get('historial_bloqueos', [])
        bloqueo_actual_id = existing.get('bloqueo_actual_id')
        
        # Preparar info de actualización de IMEI si aplica
        imei_actualizado = data.get('imei_actualizado', False)
        imei_nuevo = data.get('dispositivo.imei')
        imei_anterior = data.get('imei_anterior') or existing.get('dispositivo', {}).get('imei')
        
        for bloqueo in historial_bloqueos:
            if bloqueo.get('id') == bloqueo_actual_id and not bloqueo.get('resuelto'):
                bloqueo['resuelto'] = True
                bloqueo['resuelto_por'] = usuario_nombre
                bloqueo['resuelto_por_id'] = user.get('user_id')
                bloqueo['fecha_resolucion'] = now.isoformat()
                bloqueo['notas_resolucion'] = data.get('notas_desbloqueo', 'Aprobado por administrador')
                # Registrar si se cambió el IMEI
                if imei_actualizado and imei_nuevo:
                    bloqueo['imei_corregido'] = imei_nuevo
                    bloqueo['imei_anterior'] = imei_anterior
                break
        
        data['historial_bloqueos'] = historial_bloqueos
        data['bloqueo_actual_id'] = None
        
        # Limpiar campos temporales que no deben ir a la BD
        data.pop('imei_actualizado', None)
        data.pop('imei_anterior', None)
        data.pop('notas_desbloqueo', None)
        
        # Notificar al técnico que la orden fue desbloqueada
        tecnico_id = existing.get('tecnico_asignado')
        if tecnico_id:
            mensaje_notif = f"✅ La orden {existing['numero_orden']} ha sido desbloqueada."
            if imei_actualizado:
                mensaje_notif += f" IMEI actualizado a: {imei_nuevo}"
            mensaje_notif += " Puedes continuar con la reparación."
            
            notif = Notificacion(
                tipo="orden_desbloqueada",
                mensaje=mensaje_notif,
                orden_id=orden_id,
                usuario_destino=tecnico_id
            )
            notif_doc = notif.model_dump()
            notif_doc['created_at'] = notif_doc['created_at'].isoformat()
            await db.notificaciones.insert_one(notif_doc)
    
    await db.ordenes.update_one({"id": orden_id}, {"$set": data})
    
    # Recalcular totales si la orden tiene materiales
    orden_actual = await db.ordenes.find_one({"id": orden_id}, {"_id": 0, "materiales": 1})
    if orden_actual and orden_actual.get('materiales'):
        await recalcular_totales_orden(orden_id)

    await registrar_evento_ot(
        ot_doc=existing,
        action="orden_actualizada_parcial",
        actor=user,
        source="api_patch",
        updates=data,
        before=existing,
    )
    
    # Si se bloqueó por IMEI incorrecto, crear notificación para admin
    if data.get('bloqueada') and data.get('motivo_bloqueo') == 'IMEI no coincide':
        imeis_registrados = parse_imeis(existing.get('dispositivo', {}).get('imei', ''))
        imeis_str = ' / '.join(imeis_registrados) if imeis_registrados else 'N/A'
        notif = Notificacion(
            tipo="alerta_imei",
            mensaje=f"⚠️ ALERTA: IMEI no coincide en orden {existing['numero_orden']}. Escaneado: {data.get('imei_escaneado_incorrecto', 'N/A')} | Registrado(s): {imeis_str}",
            orden_id=orden_id
        )
        notif_doc = notif.model_dump()
        notif_doc['created_at'] = notif_doc['created_at'].isoformat()
        await db.notificaciones.insert_one(notif_doc)
    
    updated = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    return _normalizar_orden_doc(updated)

@router.delete("/ordenes/{orden_id}")
async def eliminar_orden(orden_id: str, user: dict = Depends(require_admin)):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    await registrar_evento_ot(
        ot_doc=orden,
        action="orden_eliminada",
        actor=user,
        source="api_delete",
        updates={"deleted": True},
        before={"estado": orden.get("estado")},
    )

    result = await db.ordenes.delete_one({"id": orden_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return {"message": "Orden eliminada"}

# ==================== ENVÍO Y AUTORIZACIÓN ====================

@router.patch("/ordenes/{orden_id}/envio")
async def actualizar_envio_orden(orden_id: str, data: EnvioAuthUpdate):
    """Update shipping and authorization data inline."""
    existing = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    update_fields = {k: v for k, v in data.model_dump().items() if v is not None}
    update_fields['updated_at'] = datetime.now(timezone.utc).isoformat()
    await db.ordenes.update_one({"id": orden_id}, {"$set": update_fields})
    updated = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    return _normalizar_orden_doc(updated)

# ==================== TRANSICIONES DE ESTADO VÁLIDAS ====================

TRANSICIONES_VALIDAS = {
    "pendiente_recibir": ["recibida", "cancelado"],
    "recibida": ["cuarentena", "en_taller", "cancelado"],
    "cuarentena": ["recibida", "cancelado"],
    "en_taller": ["reparado", "validacion", "re_presupuestar", "irreparable", "reemplazo", "cancelado"],
    "re_presupuestar": ["en_taller", "cancelado"],
    "reparado": ["validacion", "enviado", "en_taller"],  # Admin puede enviar directamente, puede volver si falla QA
    "validacion": ["enviado", "reparado", "en_taller"],  # puede volver a taller si hay problema
    "enviado": ["garantia"],  # solo para abrir garantía
    "garantia": ["en_taller", "recibida"],
    "reemplazo": ["enviado", "validacion"],
    "irreparable": ["enviado", "cancelado"],  # permite enviar para contabilizar
    "cancelado": [],  # estado final
}

def validar_transicion(estado_actual: str, nuevo_estado: str, es_admin: bool = False, es_master: bool = False) -> tuple[bool, str]:
    """Valida si una transición de estado es permitida.
    
    Returns:
        tuple: (es_valida, mensaje_error)
    """
    # MASTER: Puede cambiar a CUALQUIER estado sin restricciones
    if es_master:
        return True, ""
    
    # Admin puede forzar ciertas transiciones
    if es_admin and nuevo_estado in ["cancelado", "re_presupuestar", "validacion", "enviado"]:
        return True, ""
    
    transiciones_permitidas = TRANSICIONES_VALIDAS.get(estado_actual, [])
    
    if nuevo_estado in transiciones_permitidas:
        return True, ""
    
    return False, f"Transición no válida: {estado_actual} → {nuevo_estado}. Transiciones permitidas: {transiciones_permitidas}"

# ==================== ESTADO Y ESCANEO ====================

@router.patch("/ordenes/{orden_id}/estado")
async def cambiar_estado_orden(orden_id: str, request: CambioEstadoRequest, user: dict = Depends(require_auth)):
    """
    Cambiar estado de una orden.
    
    REGLAS:
    - MASTER: Puede cambiar a CUALQUIER estado sin restricciones
    - Admin: Puede cambiar estados con algunas restricciones
    - Técnico: Solo puede cambiar a estados de su flujo de trabajo
    - Mensaje es OBLIGATORIO
    - Se graba quién y cuándo en historial_estados
    """
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    estado_actual = orden.get('estado', 'pendiente_recibir')
    es_admin = user.get('role') in ['admin', 'master']
    es_master = user.get('role') == 'master'
    es_tecnico = user.get('role') == 'tecnico'

    # Validar mensaje obligatorio
    if not request.mensaje or not request.mensaje.strip():
        raise HTTPException(status_code=400, detail="El mensaje/motivo del cambio de estado es obligatorio")

    # ─── MASTER: SIN RESTRICCIONES ───
    if es_master:
        # El Master puede cambiar a cualquier estado sin validaciones adicionales
        pass
    elif es_tecnico:
        # ─── RESTRICCIÓN TÉCNICO ───
        ESTADOS_TECNICO_PERMITIDOS = {'en_taller', 'reparado', 'irreparable'}
        if request.nuevo_estado.value not in ESTADOS_TECNICO_PERMITIDOS:
            raise HTTPException(
                status_code=403,
                detail=f"Como técnico, solo puedes cambiar a los estados: {', '.join(ESTADOS_TECNICO_PERMITIDOS)}. "
                       "Contacta a un administrador para otros cambios de estado."
            )
        ESTADOS_ORIGEN_TECNICO = {'recibida', 'en_taller', 'cuarentena'}
        if estado_actual not in ESTADOS_ORIGEN_TECNICO:
            raise HTTPException(
                status_code=403,
                detail=f"Como técnico, no puedes cambiar el estado desde '{estado_actual}'. "
                       "Contacta a un administrador."
            )
    elif es_admin:
        # ─── ADMIN: Algunas restricciones, pero puede solicitar cambio ───
        # Validar transición
        transicion_valida, error_msg = validar_transicion(estado_actual, request.nuevo_estado.value, es_admin, es_master)
        if not transicion_valida:
            raise HTTPException(status_code=400, detail=error_msg)

    # ─── Validaciones adicionales (excepto para Master) ───
    if not es_master:
        if orden.get('bloqueada') and request.nuevo_estado not in [OrderStatus.RE_PRESUPUESTAR, OrderStatus.CANCELADO]:
            raise HTTPException(status_code=400, detail="La orden está bloqueada pendiente de aprobación de materiales")
        
        if request.nuevo_estado == OrderStatus.EN_TALLER:
            if orden.get('ri_obligatoria') and not orden.get('ri_completada'):
                raise HTTPException(
                    status_code=400,
                    detail="Completa la Receiving Inspection (RI) antes de iniciar reparación",
                )
            if not orden.get('recepcion_checklist_completo'):
                raise HTTPException(
                    status_code=400,
                    detail="Completa el checklist de recepción antes de iniciar reparación (estado en_taller)",
                )
        
        # Validar materiales antes de marcar como REPARADO
        if request.nuevo_estado == OrderStatus.REPARADO:
            materiales = orden.get('materiales', [])
            if materiales:
                materiales_sin_validar = [m for m in materiales if not m.get('validado_tecnico')]
                if materiales_sin_validar:
                    puede_forzar = es_admin and request.forzar_sin_validacion
                    if not puede_forzar:
                        nombres_pendientes = ", ".join([m.get('nombre', 'Material')[:30] for m in materiales_sin_validar[:3]])
                        if len(materiales_sin_validar) > 3:
                            nombres_pendientes += f" y {len(materiales_sin_validar) - 3} más"
                        raise HTTPException(
                            status_code=400,
                            detail=f"Valida los materiales antes de marcar como REPARADO: {nombres_pendientes}. "
                                   "Usa el checkbox junto a cada material o marca 'forzar sin validación'."
                        )
                else:
                    # Registrar en historial que se forzó sin validación
                    logger.warning(f"Admin {user.get('email')} forzó cambio a REPARADO sin validar {len(materiales_sin_validar)} materiales en orden {orden.get('numero_orden')}")
        
        # Cuando el técnico marca como REPARADO, su trabajo termina.
        # El QC lo completará el admin al validar/enviar.
    
    now = datetime.now(timezone.utc)
    historial = orden.get('historial_estados', [])
    
    # Si se forzó, añadir nota al historial
    nota_forzado = ""
    if request.nuevo_estado == OrderStatus.REPARADO and request.forzar_sin_validacion and es_admin:
        materiales = orden.get('materiales', [])
        materiales_sin_validar = [m for m in materiales if not m.get('validado_tecnico')]
        if materiales_sin_validar:
            nota_forzado = f" (FORZADO sin validar {len(materiales_sin_validar)} materiales)"
    
    # Resolver nombre del usuario para trazabilidad (nombre, no email)
    db_user = await db.users.find_one({"email": user.get('email')}, {"_id": 0, "nombre": 1, "apellidos": 1})
    usuario_display = user.get('email', 'sistema')
    if db_user:
        nombre = db_user.get('nombre', '')
        apellidos = db_user.get('apellidos', '')
        usuario_display = f"{nombre} {apellidos}".strip() or user.get('email', 'sistema')

    historial.append({
        "estado": request.nuevo_estado.value, 
        "fecha": now.isoformat(), 
        "usuario": usuario_display,
        "usuario_email": user.get('email', ''),
        "rol": user.get('role', 'unknown'),
        "mensaje": request.mensaje.strip(),
        "nota": nota_forzado if nota_forzado else None,
    })
    update_data = {"estado": request.nuevo_estado.value, "historial_estados": historial, "updated_at": now.isoformat()}
    if request.nuevo_estado == OrderStatus.RECIBIDA:
        update_data["fecha_recibida_centro"] = now.isoformat()
    elif request.nuevo_estado == OrderStatus.EN_TALLER:
        update_data["fecha_inicio_reparacion"] = now.isoformat()
    elif request.nuevo_estado == OrderStatus.REPARADO:
        update_data["fecha_fin_reparacion"] = now.isoformat()
    elif request.nuevo_estado == OrderStatus.ENVIADO:
        update_data["fecha_enviado"] = now.isoformat()
    if request.codigo_envio:
        update_data["codigo_recogida_salida"] = request.codigo_envio
    await db.ordenes.update_one({"id": orden_id}, {"$set": update_data})

    await registrar_evento_ot(
        ot_doc=orden,
        action="cambio_estado",
        actor=user,
        source="api_estado",
        updates={"estado": request.nuevo_estado.value, "codigo_envio": request.codigo_envio, "mensaje": request.mensaje},
        before={"estado": estado_actual, "codigo_envio": orden.get("codigo_recogida_salida")},
    )
    
    # Registrar en auditoría
    await registrar_auditoria(
        entidad="orden",
        entidad_id=orden_id,
        accion="cambiar_estado",
        usuario_id=user.get('user_id'),
        usuario_email=user.get('email'),
        rol=user.get('role'),
        cambios={"estado_anterior": estado_actual, "estado_nuevo": request.nuevo_estado.value, "mensaje": request.mensaje}
    )
    
    # Notificaciones de cambio de estado:
    # - orden_reparada (GENERAL)  → la dejamos
    # - orden_estado_cambiado (MODIFICACION) → nueva, siempre
    from modules.notificaciones.helper import create_notification
    if request.nuevo_estado == OrderStatus.REPARADO and request.usuario != "admin":
        await create_notification(
            db,
            tipo="orden_reparada",
            categoria="GENERAL",
            titulo="Orden lista para validación",
            mensaje=(f"El técnico ha marcado la orden {orden['numero_orden']} "
                     f"como REPARADA. Lista para validación."),
            orden_id=orden_id,
            source=f"cambio_estado:{user.get('email','')}",
        )
    # Notificación de modificación general (cambio de estado)
    await create_notification(
        db,
        tipo="orden_estado_cambiado",
        categoria="MODIFICACION",
        titulo="Cambio de estado de orden",
        mensaje=(f"OT {orden['numero_orden']}: {estado_actual} → {request.nuevo_estado.value}"
                 + (f" · {request.mensaje}" if request.mensaje else "")),
        orden_id=orden_id,
        meta={"estado_anterior": estado_actual,
              "estado_nuevo": request.nuevo_estado.value},
        source=f"cambio_estado:{user.get('email','')}",
        skip_if_duplicate_minutes=1,  # evitar duplicados al spamear el endpoint
    )
    try:
        cliente = await db.clientes.find_one({"id": orden['cliente_id']}, {"_id": 0})
        if cliente:
            orden_act = orden.copy()
            orden_act['estado'] = request.nuevo_estado.value
            orden_act['codigo_recogida_salida'] = request.codigo_envio or orden.get('codigo_recogida_salida')
            await send_order_notification(orden_act, cliente, "status_change")
    except Exception as e:
        logger.error(f"Error enviando notificación: {e}")
    
    # Auto-sync with Insurama if order has authorization code
    if orden.get("numero_autorizacion"):
        # Pass updated order data including the new codigo_envio
        orden_updated = {**orden, "codigo_recogida_salida": request.codigo_envio or orden.get("codigo_recogida_salida")}
        asyncio.create_task(sync_order_status_to_insurama(
            orden_updated, request.nuevo_estado.value, request.codigo_envio
        ))
    
    # Crear albarán automático cuando se pasa a VALIDACION
    if request.nuevo_estado == OrderStatus.VALIDACION:
        asyncio.create_task(crear_albaran_automatico(orden_id, user))
    
    # Crear albarán automático cuando se pasa a ENVIADO (si no tiene ya uno)
    if request.nuevo_estado == OrderStatus.ENVIADO:
        orden_actual = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
        if orden_actual and not orden_actual.get("albaran_id"):
            asyncio.create_task(crear_albaran_automatico(orden_id, user))
    
    return {"message": f"Estado cambiado a {request.nuevo_estado.value}"}

@router.post("/ordenes/{orden_ref}/scan")
async def escanear_orden(orden_ref: str, request: ScanQRRequest):
    orden = await db.ordenes.find_one({"id": orden_ref}, {"_id": 0})
    if not orden:
        orden = await db.ordenes.find_one({"numero_orden": orden_ref}, {"_id": 0})
    if not orden:
        orden = await db.ordenes.find_one({"numero_autorizacion": orden_ref}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail=f"Orden no encontrada con referencia: {orden_ref}")
    if orden.get('bloqueada'):
        raise HTTPException(status_code=400, detail="La orden está bloqueada pendiente de aprobación de materiales")
    nuevo_estado = None
    update_data = {}
    now = datetime.now(timezone.utc)
    if request.tipo_escaneo == "recepcion":
        if orden['estado'] == OrderStatus.PENDIENTE_RECIBIR.value:
            nuevo_estado = OrderStatus.RECIBIDA
            update_data["fecha_recibida_centro"] = now.isoformat()
        else:
            raise HTTPException(status_code=400, detail=f"No se puede recibir una orden en estado {orden['estado']}")
    elif request.tipo_escaneo == "tecnico":
        if orden['estado'] == OrderStatus.RECIBIDA.value:
            if orden.get('ri_obligatoria') and not orden.get('ri_completada'):
                raise HTTPException(status_code=400, detail="Completa la Receiving Inspection (RI) antes de iniciar reparación")
            if not orden.get('recepcion_checklist_completo'):
                raise HTTPException(status_code=400, detail="Completa el checklist de recepción antes de iniciar reparación")
            nuevo_estado = OrderStatus.EN_TALLER
            update_data["fecha_inicio_reparacion"] = now.isoformat()
        else:
            raise HTTPException(status_code=400, detail=f"No se puede iniciar reparación de una orden en estado {orden['estado']}")
    else:
        raise HTTPException(status_code=400, detail="Tipo de escaneo no válido")
    historial = orden.get('historial_estados', [])
    historial.append({"estado": nuevo_estado.value, "fecha": now.isoformat(), "usuario": request.usuario})
    update_data.update({"estado": nuevo_estado.value, "historial_estados": historial, "updated_at": now.isoformat()})
    await db.ordenes.update_one({"id": orden['id']}, {"$set": update_data})

    await registrar_evento_ot(
        ot_doc=orden,
        action="cambio_estado_scan",
        actor={"user_id": None, "email": request.usuario, "role": "scan"},
        source=f"scan_{request.tipo_escaneo}",
        updates={"estado": nuevo_estado.value},
        before={"estado": orden.get("estado")},
    )
    try:
        cliente = await db.clientes.find_one({"id": orden['cliente_id']}, {"_id": 0})
        if cliente:
            orden_act = orden.copy()
            orden_act['estado'] = nuevo_estado.value
            await send_order_notification(orden_act, cliente, "status_change")
    except Exception as e:
        logger.error(f"Error enviando notificación por escaneo: {e}")
    
    # Auto-sync with Insurama
    if orden.get("numero_autorizacion"):
        asyncio.create_task(sync_order_status_to_insurama(orden, nuevo_estado.value))
    
    return {"message": f"Orden escaneada. Nuevo estado: {nuevo_estado.value}", "nuevo_estado": nuevo_estado.value}


# ==================== ESCANEO CÓDIGO DE BARRAS GLS ====================

class ScanGLSRequest(BaseModel):
    codigo_barras: str
    usuario_email: str
    mensaje: str = "Paquete recibido vía escaneo GLS"


@router.post("/scan-gls")
async def escanear_codigo_gls(request: ScanGLSRequest, user: dict = Depends(require_auth)):
    """
    Busca una orden por código de barras GLS y la marca como RECIBIDA.
    Solo funciona si la orden está en estado pendiente_recibir.
    Solo admin/master pueden usar esta función.
    """
    if user.get("role") not in ("admin", "master"):
        raise HTTPException(403, "Solo administradores pueden escanear paquetes GLS")
    
    codigo = request.codigo_barras.strip()
    if not codigo:
        raise HTTPException(400, "Código de barras requerido")
    
    # Buscar primero en gls_shipments
    gls_shipment = await db.gls_shipments.find_one(
        {"gls_codbarras": codigo},
        {"_id": 0, "entidad_id": 1, "tipo": 1, "estado_interno": 1}
    )
    
    orden = None
    if gls_shipment and gls_shipment.get("entidad_id"):
        orden = await db.ordenes.find_one({"id": gls_shipment["entidad_id"]}, {"_id": 0})
    
    # Si no encontramos por shipment, buscar directamente en la orden
    if not orden:
        orden = await db.ordenes.find_one(
            {"$or": [
                {"gls_envios.codbarras": codigo},
                {"codigo_recogida_entrada": codigo},
                {"codigo_recogida_salida": codigo},
            ]},
            {"_id": 0}
        )
    
    if not orden:
        raise HTTPException(404, f"No se encontró orden con código GLS: {codigo}")
    
    # Verificar estado
    estado_actual = orden.get("estado", "")
    if estado_actual != "pendiente_recibir":
        return {
            "success": False,
            "message": f"La orden {orden.get('numero_orden')} ya está en estado '{estado_actual}'. No se puede marcar como recibida.",
            "orden_id": orden.get("id"),
            "numero_orden": orden.get("numero_orden"),
            "estado_actual": estado_actual,
            "accion": "ver_orden"
        }
    
    # Marcar como RECIBIDA
    now = datetime.now(timezone.utc).isoformat()
    historial = orden.get("historial_estados", [])
    historial.append({
        "estado": "recibida",
        "fecha": now,
        "usuario": user.get("email"),
        "mensaje": request.mensaje,
        "via": "escaneo_gls",
        "codigo_gls": codigo,
    })
    
    await db.ordenes.update_one(
        {"id": orden["id"]},
        {"$set": {
            "estado": "recibida",
            "historial_estados": historial,
            "fecha_recibida_centro": now,
            "updated_at": now,
        }}
    )
    
    # Registrar evento
    await registrar_evento_ot(
        ot_doc=orden,
        action="recepcion_gls",
        actor=user,
        source="scan_gls",
        updates={"estado": "recibida", "codigo_gls": codigo},
        before={"estado": estado_actual},
    )
    
    # Actualizar estado del shipment GLS si existe
    if gls_shipment:
        await db.gls_shipments.update_one(
            {"gls_codbarras": codigo},
            {"$set": {"recepcion_confirmada": True, "recepcion_fecha": now, "recepcion_usuario": user.get("email")}}
        )
    
    # Auto-sync con Insurama si aplica
    if orden.get("numero_autorizacion"):
        asyncio.create_task(sync_order_status_to_insurama(orden, "recibida"))
    
    # Notificar al cliente
    try:
        cliente = await db.clientes.find_one({"id": orden["cliente_id"]}, {"_id": 0})
        if cliente:
            orden_actualizada = orden.copy()
            orden_actualizada["estado"] = "recibida"
            await send_order_notification(orden_actualizada, cliente, "status_change")
    except Exception as e:
        logger.error(f"Error enviando notificación tras escaneo GLS: {e}")
    
    return {
        "success": True,
        "message": f"Orden {orden.get('numero_orden')} marcada como RECIBIDA",
        "orden_id": orden.get("id"),
        "numero_orden": orden.get("numero_orden"),
        "estado_nuevo": "recibida",
        "codigo_gls": codigo,
    }


# ==================== MATERIALES ====================

@router.post("/ordenes/{orden_id}/materiales")
async def añadir_material_orden(orden_id: str, request: AñadirMaterialRequest):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if orden.get('bloqueada'):
        raise HTTPException(status_code=400, detail="La orden está bloqueada pendiente de aprobación")
    if request.repuesto_id:
        repuesto = await db.repuestos.find_one({"id": request.repuesto_id}, {"_id": 0})
        if not repuesto:
            raise HTTPException(status_code=404, detail="Repuesto no encontrado")
        material = {"repuesto_id": request.repuesto_id, "nombre": repuesto['nombre'], "sku": repuesto.get('sku', ''), "cantidad": request.cantidad, "precio_unitario": request.precio_unitario if request.precio_unitario is not None else repuesto.get('precio_venta', 0), "coste": request.coste if request.coste is not None else repuesto.get('precio_coste', 0), "iva": request.iva or 21.0, "descuento": request.descuento or 0, "añadido_por_tecnico": request.añadido_por_tecnico, "aprobado": not request.añadido_por_tecnico, "pendiente_precios": False}
        await db.repuestos.update_one({"id": request.repuesto_id}, {"$inc": {"stock": -request.cantidad}})
        # Hook stock <= mínimo tras descuento (silencioso)
        try:
            from modules.compras.helpers import trigger_alerta_stock_minimo
            r2 = await db.repuestos.find_one({"id": request.repuesto_id}, {"_id": 0})
            if r2:
                await trigger_alerta_stock_minimo(db, r2)
        except Exception:
            pass
    else:
        if not request.nombre:
            raise HTTPException(status_code=400, detail="Se requiere nombre para material personalizado")
        pendiente_precios = request.añadido_por_tecnico and (request.precio_unitario is None or request.coste is None)
        # Hook autocreate: intenta resolver/crear repuesto en inventario por nombre
        # Si falla, sigue el flujo legacy (material sin repuesto_id) — NO debe romper.
        repuesto_auto = None
        try:
            from modules.compras.helpers import get_or_create_repuesto, agregar_a_lista_compras, FUENTE_AUTO_MATERIAL
            repuesto_auto = await get_or_create_repuesto(
                db, request.nombre,
                precio_compra=float(request.coste or 0),
                precio_venta=float(request.precio_unitario or 0),
                creado_por="auto_material_ot",
            )
            # Si el técnico añadió y NO hay stock, agrega a lista compras (urgencia alta)
            if request.añadido_por_tecnico and (repuesto_auto.get("stock") or 0) < request.cantidad:
                await agregar_a_lista_compras(
                    db,
                    repuesto_id=repuesto_auto["id"],
                    cantidad=max(request.cantidad - (repuesto_auto.get("stock") or 0), 1),
                    urgencia="alta" if (repuesto_auto.get("stock") or 0) == 0 else "normal",
                    fuente=FUENTE_AUTO_MATERIAL,
                    order_id=orden_id,
                    creado_por="auto_material_ot",
                )
        except Exception as _exc:  # noqa: BLE001
            repuesto_auto = None  # fallback silencioso al flujo legacy
        material = {
            "repuesto_id": repuesto_auto["id"] if repuesto_auto else None,
            "nombre": request.nombre,
            "sku": (repuesto_auto.get("sku") if repuesto_auto else None),
            "cantidad": request.cantidad,
            "precio_unitario": request.precio_unitario or 0,
            "coste": request.coste or 0,
            "iva": request.iva or 21.0,
            "descuento": request.descuento or 0,
            "añadido_por_tecnico": request.añadido_por_tecnico,
            "aprobado": not request.añadido_por_tecnico,
            "pendiente_precios": pendiente_precios,
            "auto_creado": bool(repuesto_auto and repuesto_auto.get("auto_creado")),
        }
        # Si tenemos repuesto y hay stock disponible, descontar
        if repuesto_auto and (repuesto_auto.get("stock") or 0) >= request.cantidad:
            try:
                await db.repuestos.update_one(
                    {"id": repuesto_auto["id"]},
                    {"$inc": {"stock": -request.cantidad}},
                )
            except Exception:
                pass
    materiales = orden.get('materiales', [])
    materiales.append(material)
    update_data = {"materiales": materiales, "updated_at": datetime.now(timezone.utc).isoformat()}
    if request.añadido_por_tecnico:
        update_data["requiere_aprobacion"] = True
        update_data["bloqueada"] = True
        msg = f"El técnico ha añadido '{material['nombre']}' a la orden {orden['numero_orden']}. La orden está BLOQUEADA hasta su aprobación."
        notif = Notificacion(tipo="material_añadido", mensaje=msg, orden_id=orden_id)
        notif_doc = notif.model_dump()
        notif_doc['created_at'] = notif_doc['created_at'].isoformat()
        await db.notificaciones.insert_one(notif_doc)
    await db.ordenes.update_one({"id": orden_id}, {"$set": update_data})
    
    # Recalcular totales de la orden
    totales = await recalcular_totales_orden(orden_id)
    
    return {"message": "Material añadido", "bloqueada": request.añadido_por_tecnico, "material": material, "totales": totales}

@router.patch("/ordenes/{orden_id}/materiales/{material_index}")
async def actualizar_material_orden(orden_id: str, material_index: int, request: ActualizarMaterialRequest, user: dict = Depends(require_admin)):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    materiales = orden.get('materiales', [])
    if material_index < 0 or material_index >= len(materiales):
        raise HTTPException(status_code=400, detail="Índice de material inválido")
    materiales[material_index]['precio_unitario'] = request.precio_unitario
    materiales[material_index]['coste'] = request.coste
    materiales[material_index]['iva'] = request.iva
    materiales[material_index]['pendiente_precios'] = False
    await db.ordenes.update_one({"id": orden_id}, {"$set": {"materiales": materiales, "updated_at": datetime.now(timezone.utc).isoformat()}})
    
    # Recalcular totales de la orden
    totales = await recalcular_totales_orden(orden_id)
    
    return {"message": "Material actualizado", "material": materiales[material_index], "totales": totales}

@router.put("/ordenes/{orden_id}/materiales/{material_index}")
async def editar_material_completo(orden_id: str, material_index: int, data: MaterialUpdate, user: dict = Depends(require_admin)):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    materiales = orden.get('materiales', [])
    if material_index < 0 or material_index >= len(materiales):
        raise HTTPException(status_code=400, detail="Índice de material inválido")
    material = materiales[material_index]
    if data.nombre is not None: material['nombre'] = data.nombre
    if data.nombre_personalizado is not None: material['nombre_personalizado'] = data.nombre_personalizado
    if data.cantidad is not None: material['cantidad'] = data.cantidad
    if data.precio_unitario is not None: material['precio_unitario'] = data.precio_unitario
    if data.coste is not None: material['coste'] = data.coste
    if data.iva is not None: material['iva'] = data.iva
    if data.descuento is not None: material['descuento'] = data.descuento
    material['pendiente_precios'] = False
    materiales[material_index] = material
    await db.ordenes.update_one({"id": orden_id}, {"$set": {"materiales": materiales, "updated_at": datetime.now(timezone.utc).isoformat()}})
    
    # Recalcular totales de la orden
    totales = await recalcular_totales_orden(orden_id)
    
    return {"message": "Material actualizado", "material": material, "totales": totales}

@router.delete("/ordenes/{orden_id}/materiales/{material_index}")
async def eliminar_material_orden(orden_id: str, material_index: int, user: dict = Depends(require_admin)):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    materiales = orden.get('materiales', [])
    if material_index < 0 or material_index >= len(materiales):
        raise HTTPException(status_code=400, detail="Índice de material inválido")
    material_eliminado = materiales.pop(material_index)
    if material_eliminado.get('repuesto_id'):
        await db.repuestos.update_one({"id": material_eliminado['repuesto_id']}, {"$inc": {"stock_actual": material_eliminado.get('cantidad', 1)}})
    await db.ordenes.update_one({"id": orden_id}, {"$set": {"materiales": materiales, "updated_at": datetime.now(timezone.utc).isoformat()}})
    
    # Recalcular totales de la orden
    totales = await recalcular_totales_orden(orden_id)
    
    return {"message": "Material eliminado", "materiales_restantes": len(materiales), "totales": totales}


# ==================== MANO DE OBRA Y TOTALES ====================

class ManoObraRequest(BaseModel):
    mano_obra: float
    descripcion: Optional[str] = None

@router.patch("/ordenes/{orden_id}/mano-obra")
async def actualizar_mano_obra(orden_id: str, request: ManoObraRequest, user: dict = Depends(require_admin)):
    """Actualiza el importe de mano de obra y recalcula los totales"""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    update_data = {
        "mano_obra": request.mano_obra,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    if request.descripcion:
        update_data["mano_obra_descripcion"] = request.descripcion
    
    await db.ordenes.update_one({"id": orden_id}, {"$set": update_data})
    
    # Recalcular totales
    totales = await recalcular_totales_orden(orden_id)
    
    return {"message": "Mano de obra actualizada", "mano_obra": request.mano_obra, "totales": totales}


# ==================== NOTIFICAR (ENVIAR-WHATSAPP) ====================

@router.post("/ordenes/{orden_id}/enviar-whatsapp")
async def enviar_notificacion_orden(orden_id: str, user: dict = Depends(require_auth)):
    """Reenvía la notificación por email/SMS al cliente con el link de seguimiento."""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    cliente = await db.clientes.find_one({"id": orden.get("cliente_id")}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Ensure order has a tracking token
    token = orden.get("token_seguimiento")
    if not token:
        token = str(uuid.uuid4())[:12].upper()
        await db.ordenes.update_one({"id": orden_id}, {"$set": {"token_seguimiento": token}})
        orden["token_seguimiento"] = token
    
    try:
        results = await send_order_notification(orden, cliente, "created")
        canales = []
        if results.get("email", {}).get("success"):
            canales.append("email")
        if results.get("sms", {}).get("success"):
            canales.append("SMS")
        
        if canales:
            return {"message": f"Notificación enviada por {', '.join(canales)}"}
        else:
            return {"message": "Notificación procesada. Verifica la configuración SMTP si no llega el email."}
    except Exception as e:
        logger.error(f"Error enviando notificación manual para orden {orden_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al enviar notificación: {str(e)}")


# ==================== RE-PRESUPUESTO ====================

class RePresupuestoRequest(BaseModel):
    nuevo_importe: float
    motivo: Optional[str] = None
    notificar_cliente: bool = True

@router.post("/ordenes/{orden_id}/re-presupuesto")
async def iniciar_re_presupuesto(orden_id: str, request: RePresupuestoRequest, user: dict = Depends(require_auth)):
    """Inicia un flujo de re-presupuesto: cambia estado, registra el nuevo importe y notifica al cliente."""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    estado_actual = orden.get("estado", "pendiente_recibir")
    es_admin = user.get("role") in ["admin", "master"]
    
    # Validate transition
    transicion_valida, error_msg = validar_transicion(estado_actual, "re_presupuestar", es_admin, user.get("role") == "master")
    if not transicion_valida:
        raise HTTPException(status_code=400, detail=error_msg)
    
    now = datetime.now(timezone.utc)
    historial = orden.get("historial_estados", [])
    historial.append({
        "estado": "re_presupuestar",
        "fecha": now.isoformat(),
        "usuario": user.get("email", "admin")
    })
    
    update_data = {
        "estado": "re_presupuestar",
        "historial_estados": historial,
        "re_presupuesto_importe": request.nuevo_importe,
        "re_presupuesto_motivo": request.motivo or "Re-presupuesto solicitado",
        "re_presupuesto_fecha": now.isoformat(),
        "re_presupuesto_aprobado": None,
        "updated_at": now.isoformat()
    }
    
    await db.ordenes.update_one({"id": orden_id}, {"$set": update_data})
    
    await registrar_evento_ot(
        ot_doc=orden,
        action="re_presupuesto",
        actor=user,
        source="api",
        updates={"estado": "re_presupuestar", "nuevo_importe": request.nuevo_importe},
        before={"estado": estado_actual},
    )
    
    # Notify client
    if request.notificar_cliente:
        try:
            cliente = await db.clientes.find_one({"id": orden.get("cliente_id")}, {"_id": 0})
            if cliente and cliente.get("email"):
                from services.email_service import send_email as smtp_send
                import config as smtp_cfg
                
                token = orden.get("token_seguimiento", "")
                link = f"https://revix.es/consulta?codigo={token}"
                
                contenido = f"""
                <p>Hola {cliente.get('nombre', '')},</p>
                <p>Te informamos de que tu reparación (orden <strong>{orden.get('numero_orden', '')}</strong>) 
                necesita un nuevo presupuesto.</p>
                <div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:8px;padding:16px;margin:16px 0;">
                    <p style="font-size:14px;color:#92400e;margin-bottom:8px;"><strong>Nuevo presupuesto:</strong></p>
                    <p style="font-size:24px;font-weight:bold;color:#d97706;">{request.nuevo_importe:.2f} EUR</p>
                    {f'<p style="font-size:13px;color:#92400e;margin-top:8px;">Motivo: {request.motivo}</p>' if request.motivo else ''}
                </div>
                <p>Puedes consultar el estado de tu reparación en cualquier momento:</p>
                <p><a href="{link}" style="color:#2563eb;text-decoration:underline;">Ver estado de mi reparación</a></p>
                <p>Si tienes alguna duda, no dudes en contactarnos.</p>
                """
                
                smtp_send(
                    to=cliente["email"],
                    subject=f"Revix - Nuevo presupuesto para tu reparación ({orden.get('numero_orden', '')})",
                    titulo="Nuevo presupuesto de reparación",
                    contenido=contenido
                )
        except Exception as e:
            logger.error(f"Error notificando re-presupuesto para orden {orden_id}: {e}")
    
    # Create internal notification
    notif = Notificacion(
        tipo="re_presupuesto",
        mensaje=f"Re-presupuesto de {request.nuevo_importe:.2f}EUR para orden {orden.get('numero_orden', '')}. {request.motivo or ''}",
        orden_id=orden_id
    )
    notif_doc = notif.model_dump()
    notif_doc["created_at"] = notif_doc["created_at"].isoformat()
    await db.notificaciones.insert_one(notif_doc)
    
    return {
        "message": f"Re-presupuesto de {request.nuevo_importe:.2f}EUR registrado. Estado cambiado a 're_presupuestar'.",
        "nuevo_importe": request.nuevo_importe,
        "estado": "re_presupuestar"
    }


@router.post("/ordenes/{orden_id}/aprobar-re-presupuesto")
async def aprobar_re_presupuesto(orden_id: str, user: dict = Depends(require_auth)):
    """El admin aprueba el re-presupuesto y vuelve la orden a en_taller."""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    if orden.get("estado") != "re_presupuestar":
        raise HTTPException(status_code=400, detail="La orden no está en estado de re-presupuesto")
    
    now = datetime.now(timezone.utc)
    historial = orden.get("historial_estados", [])
    historial.append({
        "estado": "en_taller",
        "fecha": now.isoformat(),
        "usuario": user.get("email", "admin") + " (re-presupuesto aprobado)"
    })
    
    update_data = {
        "estado": "en_taller",
        "historial_estados": historial,
        "re_presupuesto_aprobado": True,
        "re_presupuesto_aprobado_fecha": now.isoformat(),
        "re_presupuesto_aprobado_por": user.get("email"),
        "updated_at": now.isoformat()
    }
    
    await db.ordenes.update_one({"id": orden_id}, {"$set": update_data})
    
    return {"message": "Re-presupuesto aprobado. Orden devuelta a en_taller.", "estado": "en_taller"}


@router.post("/ordenes/{orden_id}/recalcular-totales")
async def recalcular_totales_endpoint(orden_id: str, user: dict = Depends(require_admin)):
    """Fuerza el recálculo de los totales de una orden"""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    totales = await recalcular_totales_orden(orden_id)
    
    return {"message": "Totales recalculados", "totales": totales}


@router.post("/ordenes/recalcular-todos")
async def recalcular_todos_totales(user: dict = Depends(require_master)):
    """
    Recalcula los totales de TODAS las órdenes.
    Útil para migrar órdenes antiguas que no tienen los campos precalculados.
    """
    ordenes = await db.ordenes.find({}, {"_id": 0, "id": 1}).to_list(10000)
    
    recalculadas = 0
    errores = 0
    
    for o in ordenes:
        try:
            await recalcular_totales_orden(o['id'])
            recalculadas += 1
        except Exception as e:
            logger.error(f"Error recalculando orden {o['id']}: {e}")
            errores += 1
    
    return {
        "message": f"Proceso completado. {recalculadas} órdenes recalculadas, {errores} errores.",
        "recalculadas": recalculadas,
        "errores": errores,
        "total": len(ordenes)
    }


@router.post("/ordenes/{orden_id}/materiales/{material_index}/validar")
async def validar_material_tecnico(orden_id: str, material_index: int, user: dict = Depends(require_auth)):
    """
    El técnico valida que ha usado un material escaneando su SKU o código de barras.
    Esto confirma que el material asignado realmente fue utilizado en la reparación.
    """
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    materiales = orden.get('materiales', [])
    if material_index < 0 or material_index >= len(materiales):
        raise HTTPException(status_code=400, detail="Índice de material inválido")
    
    material = materiales[material_index]
    
    # Marcar como validado por el técnico
    material['validado_tecnico'] = True
    material['validado_por'] = user.get('email', 'unknown')
    material['validado_at'] = datetime.now(timezone.utc).isoformat()
    
    materiales[material_index] = material
    
    await db.ordenes.update_one(
        {"id": orden_id}, 
        {"$set": {"materiales": materiales, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "message": f"Material '{material.get('nombre')}' validado correctamente",
        "material": material
    }


@router.post("/ordenes/{orden_id}/materiales/validar-por-codigo")
async def validar_material_por_codigo(orden_id: str, data: dict, user: dict = Depends(require_auth)):
    """
    Valida un material escaneando su SKU o código de barras.
    Busca el material en la orden y lo marca como validado.
    """
    codigo = data.get('codigo', '').strip()
    if not codigo:
        raise HTTPException(status_code=400, detail="Código no proporcionado")
    
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    materiales = orden.get('materiales', [])
    
    # Buscar el material por SKU o código de barras
    material_encontrado = None
    material_index = -1
    
    for idx, mat in enumerate(materiales):
        # Verificar si el código coincide con SKU o código de barras del repuesto
        if mat.get('sku') == codigo or mat.get('codigo_barras') == codigo:
            material_encontrado = mat
            material_index = idx
            break
        
        # Si tiene repuesto_id, buscar en la base de datos de repuestos
        if mat.get('repuesto_id'):
            repuesto = await db.repuestos.find_one(
                {"id": mat['repuesto_id']},
                {"_id": 0, "sku": 1, "codigo_barras": 1}
            )
            if repuesto:
                if repuesto.get('sku') == codigo or repuesto.get('codigo_barras') == codigo:
                    material_encontrado = mat
                    material_index = idx
                    # Guardar el SKU en el material para futuras validaciones
                    mat['sku'] = repuesto.get('sku')
                    mat['codigo_barras'] = repuesto.get('codigo_barras')
                    break
    
    if not material_encontrado:
        raise HTTPException(
            status_code=404, 
            detail=f"No se encontró ningún material con código '{codigo}' asignado a esta orden"
        )
    
    if material_encontrado.get('validado_tecnico'):
        return {
            "message": f"Material '{material_encontrado.get('nombre')}' ya estaba validado",
            "material": material_encontrado,
            "ya_validado": True
        }
    
    # Marcar como validado
    material_encontrado['validado_tecnico'] = True
    material_encontrado['validado_por'] = user.get('email', 'unknown')
    material_encontrado['validado_at'] = datetime.now(timezone.utc).isoformat()
    
    materiales[material_index] = material_encontrado
    
    await db.ordenes.update_one(
        {"id": orden_id}, 
        {"$set": {"materiales": materiales, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Contar materiales pendientes
    pendientes = sum(1 for m in materiales if not m.get('validado_tecnico'))
    
    return {
        "message": f"Material '{material_encontrado.get('nombre')}' validado correctamente",
        "material": material_encontrado,
        "pendientes": pendientes,
        "total": len(materiales)
    }


@router.post("/ordenes/{orden_id}/aprobar-materiales")
async def aprobar_materiales(orden_id: str):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    materiales = orden.get('materiales', [])
    for m in materiales:
        m['aprobado'] = True
    await db.ordenes.update_one({"id": orden_id}, {"$set": {"materiales": materiales, "requiere_aprobacion": False, "bloqueada": False, "updated_at": datetime.now(timezone.utc).isoformat()}})
    
    # Recalcular totales después de aprobar materiales
    totales = await recalcular_totales_orden(orden_id)
    
    return {"message": "Materiales aprobados y orden desbloqueada", "totales": totales}

# ==================== MENSAJES ====================

@router.post("/ordenes/{orden_id}/mensajes")
async def añadir_mensaje(orden_id: str, mensaje: MensajeOrdenCreate, user: dict = Depends(require_auth)):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    db_user = await db.users.find_one({"id": user['user_id']}, {"_id": 0})
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    nuevo_mensaje = {"id": str(uuid.uuid4()), "autor": user.get('email', 'sistema'), "autor_nombre": db_user.get('nombre', 'Usuario'), "rol": user['role'], "mensaje": mensaje.mensaje, "fecha": datetime.now(timezone.utc).isoformat(), "visible_tecnico": mensaje.visible_tecnico if user['role'] == 'admin' else True}
    mensajes = orden.get('mensajes', [])
    mensajes.append(nuevo_mensaje)
    await db.ordenes.update_one({"id": orden_id}, {"$set": {"mensajes": mensajes, "updated_at": datetime.now(timezone.utc).isoformat()}})
    
    # Si el técnico envía un mensaje, notificar al admin
    if user['role'] == 'tecnico':
        notif = Notificacion(
            tipo="mensaje_tecnico",
            mensaje=f"💬 {db_user.get('nombre', 'Técnico')} ha enviado un mensaje en la orden {orden['numero_orden']}: \"{mensaje.mensaje[:50]}{'...' if len(mensaje.mensaje) > 50 else ''}\"",
            orden_id=orden_id
        )
        notif_doc = notif.model_dump()
        notif_doc['created_at'] = notif_doc['created_at'].isoformat()
        await db.notificaciones.insert_one(notif_doc)
    
    # Si el admin envía un mensaje al técnico, crear notificación para el técnico
    elif user['role'] in ['admin', 'master'] and mensaje.visible_tecnico:
        tecnico_id = orden.get('tecnico_asignado')
        notif = Notificacion(
            tipo="mensaje_admin",
            mensaje=f"📩 Nuevo mensaje del administrador en la orden {orden['numero_orden']}",
            orden_id=orden_id,
            usuario_destino=tecnico_id
        )
        notif_doc = notif.model_dump()
        notif_doc['created_at'] = notif_doc['created_at'].isoformat()
        await db.notificaciones.insert_one(notif_doc)
    
    return {"message": "Mensaje añadido", "mensaje": nuevo_mensaje}

@router.get("/ordenes/{orden_id}/mensajes")
async def obtener_mensajes(orden_id: str, user: dict = Depends(require_auth)):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    mensajes = orden.get('mensajes', [])
    if user['role'] == 'tecnico':
        mensajes = [m for m in mensajes if m.get('visible_tecnico', True)]
    return mensajes

# ==================== PRESUPUESTOS Y FECHAS ====================

@router.post("/ordenes/{orden_id}/presupuesto")
async def emitir_presupuesto_orden(orden_id: str, request: EmitirPresupuestoRequest, user: dict = Depends(require_admin)):
    """Emite un presupuesto para una orden de trabajo"""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    now = datetime.now(timezone.utc)
    fecha_vencimiento = now + timedelta(days=request.validez_dias)
    
    update_data = {
        "presupuesto_emitido": True,
        "presupuesto_precio": request.precio,
        "presupuesto_fecha_emision": now.isoformat(),
        "presupuesto_validez_dias": request.validez_dias,
        "presupuesto_fecha_vencimiento": fecha_vencimiento.isoformat(),
        "presupuesto_notas": request.notas,
        "presupuesto_emitido_por": user.get('email'),
        "presupuesto_aceptado": None,  # Resetear estado de aceptación
        "updated_at": now.isoformat()
    }
    
    await db.ordenes.update_one({"id": orden_id}, {"$set": update_data})
    
    # Registrar en auditoría
    await registrar_auditoria(
        entidad="orden",
        entidad_id=orden_id,
        accion="emitir_presupuesto",
        usuario_id=user.get('user_id'),
        usuario_email=user.get('email'),
        rol=user.get('role'),
        cambios={"precio": request.precio, "validez_dias": request.validez_dias}
    )
    
    # Crear notificación
    notif = Notificacion(
        tipo="presupuesto_emitido",
        mensaje=f"Presupuesto de {request.precio}€ emitido para orden {orden['numero_orden']}",
        orden_id=orden_id
    )
    notif_doc = notif.model_dump()
    notif_doc['created_at'] = notif_doc['created_at'].isoformat()
    await db.notificaciones.insert_one(notif_doc)
    
    return {
        "message": "Presupuesto emitido correctamente",
        "precio": request.precio,
        "fecha_vencimiento": fecha_vencimiento.isoformat()
    }

@router.post("/ordenes/{orden_id}/presupuesto/respuesta")
async def registrar_respuesta_presupuesto(orden_id: str, request: AceptarPresupuestoRequest, user: dict = Depends(require_admin)):
    """Registra la aceptación o rechazo del presupuesto"""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    if not orden.get('presupuesto_emitido'):
        raise HTTPException(status_code=400, detail="No hay presupuesto emitido para esta orden")
    
    now = datetime.now(timezone.utc)
    
    update_data = {
        "presupuesto_aceptado": request.aceptado,
        "presupuesto_fecha_respuesta": now.isoformat(),
        "presupuesto_canal_respuesta": request.canal,
        "updated_at": now.isoformat()
    }
    
    if not request.aceptado:
        update_data["presupuesto_motivo_rechazo"] = request.motivo_rechazo
    
    await db.ordenes.update_one({"id": orden_id}, {"$set": update_data})
    
    # Registrar en auditoría
    await registrar_auditoria(
        entidad="orden",
        entidad_id=orden_id,
        accion="respuesta_presupuesto",
        usuario_id=user.get('user_id'),
        usuario_email=user.get('email'),
        rol=user.get('role'),
        cambios={"aceptado": request.aceptado, "canal": request.canal, "motivo_rechazo": request.motivo_rechazo}
    )
    
    # Crear notificación (categoría RECHAZO si rechazado, GENERAL si aceptado)
    from modules.notificaciones.helper import create_notification
    tipo_notif = "presupuesto_aceptado" if request.aceptado else "presupuesto_rechazado"
    mensaje_notif = f"Presupuesto {'ACEPTADO' if request.aceptado else 'RECHAZADO'} para orden {orden['numero_orden']}"
    if not request.aceptado and request.motivo_rechazo:
        mensaje_notif += f" - Motivo: {request.motivo_rechazo}"

    await create_notification(
        db,
        tipo=tipo_notif,
        categoria="RECHAZO" if not request.aceptado else "GENERAL",
        titulo=("Presupuesto rechazado" if not request.aceptado else "Presupuesto aceptado"),
        mensaje=mensaje_notif,
        orden_id=orden_id,
        meta={"motivo_rechazo": request.motivo_rechazo,
              "canal": request.canal} if not request.aceptado else {"canal": request.canal},
        source=f"respuesta_presupuesto:{user.get('email','')}",
    )

    return {"message": f"Respuesta de presupuesto registrada: {'Aceptado' if request.aceptado else 'Rechazado'}"}

@router.patch("/ordenes/{orden_id}/fecha-estimada")
async def actualizar_fecha_estimada(orden_id: str, request: ActualizarFechaEstimadaRequest, user: dict = Depends(require_admin)):
    """Actualiza la fecha estimada de entrega"""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    now = datetime.now(timezone.utc)
    
    update_data = {
        "fecha_estimada_entrega": request.fecha_estimada,
        "updated_at": now.isoformat()
    }
    
    await db.ordenes.update_one({"id": orden_id}, {"$set": update_data})
    
    # Registrar en auditoría
    await registrar_auditoria(
        entidad="orden",
        entidad_id=orden_id,
        accion="actualizar_fecha_estimada",
        usuario_id=user.get('user_id'),
        usuario_email=user.get('email'),
        rol=user.get('role'),
        cambios={"fecha_estimada": request.fecha_estimada}
    )
    
    # Si se debe notificar al cliente
    if request.notificar_cliente:
        cliente = await db.clientes.find_one({"id": orden['cliente_id']}, {"_id": 0})
        if cliente:
            try:
                await send_order_notification(
                    {**orden, "fecha_estimada_entrega": request.fecha_estimada},
                    cliente,
                    "fecha_estimada"
                )
            except Exception as e:
                logger.error(f"Error notificando fecha estimada: {e}")
    
    return {"message": "Fecha estimada actualizada"}

# ==================== SUBESTADOS ====================

@router.patch("/ordenes/{orden_id}/subestado")
async def cambiar_subestado_orden(orden_id: str, request: CambiarSubestadoRequest, user: dict = Depends(require_auth)):
    """
    Cambia el subestado interno de una orden de trabajo.
    Los subestados permiten rastrear estados intermedios como "Esperando repuestos" sin cambiar el estado principal.
    """
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # Validar que el subestado sea válido
    subestados_validos = [s.value for s in SubestadoOrden]
    if request.subestado not in subestados_validos:
        raise HTTPException(status_code=400, detail=f"Subestado no válido. Opciones: {subestados_validos}")
    
    now = datetime.now(timezone.utc)
    
    # Construir entrada de historial
    historial_entry = {
        "id": str(uuid.uuid4()),
        "subestado_anterior": orden.get("subestado", "ninguno"),
        "subestado_nuevo": request.subestado,
        "motivo": request.motivo,
        "fecha_revision": request.fecha_revision,
        "cambiado_por": user.get('email', 'sistema'),
        "cambiado_por_id": user.get('user_id'),
        "fecha_cambio": now.isoformat()
    }
    
    # Obtener historial existente o crear array vacío
    historial_subestados = orden.get("historial_subestados", [])
    historial_subestados.append(historial_entry)
    
    # Preparar datos de actualización
    update_data = {
        "subestado": request.subestado,
        "motivo_subestado": request.motivo,
        "historial_subestados": historial_subestados,
        "updated_at": now.isoformat()
    }
    
    # Si hay fecha de revisión, guardarla
    if request.fecha_revision:
        update_data["fecha_revision_subestado"] = request.fecha_revision
    elif request.subestado == "ninguno":
        # Si vuelve a "ninguno", limpiar fecha de revisión
        update_data["fecha_revision_subestado"] = None
    
    await db.ordenes.update_one({"id": orden_id}, {"$set": update_data})
    
    # Registrar en auditoría
    await registrar_auditoria(
        entidad="orden",
        entidad_id=orden_id,
        accion="cambiar_subestado",
        usuario_id=user.get('user_id'),
        usuario_email=user.get('email'),
        rol=user.get('role'),
        cambios={
            "subestado_anterior": historial_entry["subestado_anterior"],
            "subestado_nuevo": request.subestado,
            "motivo": request.motivo,
            "fecha_revision": request.fecha_revision
        }
    )
    
    # Crear notificación si el subestado es relevante
    if request.subestado != "ninguno":
        label = SUBESTADO_LABELS.get(request.subestado, request.subestado)
        notif_msg = f"📌 Orden {orden['numero_orden']} marcada como '{label}'"
        if request.fecha_revision:
            notif_msg += f" - Revisar el {request.fecha_revision[:10]}"
        
        notif = Notificacion(
            tipo="subestado_cambiado",
            mensaje=notif_msg,
            orden_id=orden_id
        )
        notif_doc = notif.model_dump()
        notif_doc['created_at'] = notif_doc['created_at'].isoformat()
        await db.notificaciones.insert_one(notif_doc)
    
    return {
        "message": f"Subestado cambiado a '{SUBESTADO_LABELS.get(request.subestado, request.subestado)}'",
        "subestado": request.subestado,
        "fecha_revision": request.fecha_revision
    }


@router.get("/ordenes/{orden_id}/subestado")
async def obtener_subestado_orden(orden_id: str, user: dict = Depends(require_auth)):
    """
    Obtiene información del subestado actual y el historial de cambios.
    """
    orden = await db.ordenes.find_one(
        {"id": orden_id}, 
        {"_id": 0, "subestado": 1, "motivo_subestado": 1, "fecha_revision_subestado": 1, "historial_subestados": 1}
    )
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    return {
        "subestado": orden.get("subestado", "ninguno"),
        "motivo": orden.get("motivo_subestado"),
        "fecha_revision": orden.get("fecha_revision_subestado"),
        "historial": orden.get("historial_subestados", []),
        "labels": SUBESTADO_LABELS
    }


@router.get("/ordenes/subestados/pendientes-revision")
async def obtener_ordenes_revision_pendiente(user: dict = Depends(require_auth)):
    """
    Obtiene todas las órdenes que tienen una fecha de revisión de subestado
    que ya ha pasado o es hoy.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Buscar órdenes con subestado != ninguno y fecha de revisión <= hoy
    ordenes = await db.ordenes.find({
        "subestado": {"$ne": "ninguno", "$exists": True},
        "fecha_revision_subestado": {"$lte": today, "$ne": None},
        "estado": {"$nin": ["cancelado", "enviado"]}  # Excluir terminadas
    }, {"_id": 0, "id": 1, "numero_orden": 1, "subestado": 1, "motivo_subestado": 1, "fecha_revision_subestado": 1}).to_list(100)
    
    return {
        "ordenes_pendientes": ordenes,
        "total": len(ordenes),
        "fecha_consulta": today
    }


@router.post("/ordenes/subestados/generar-recordatorios")
async def generar_recordatorios_subestado(user: dict = Depends(require_admin)):
    """
    Genera notificaciones para las órdenes cuya fecha de revisión de subestado
    ya ha pasado y no tienen notificación reciente.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc)
    
    # Buscar órdenes con subestado y fecha vencida
    ordenes = await db.ordenes.find({
        "subestado": {"$ne": "ninguno", "$exists": True},
        "fecha_revision_subestado": {"$lte": today, "$ne": None},
        "estado": {"$nin": ["cancelado", "enviado"]}
    }, {"_id": 0}).to_list(100)
    
    notificaciones_creadas = 0
    
    for orden in ordenes:
        orden_id = orden["id"]
        
        # Verificar si ya existe una notificación reciente (últimas 24h) para esta orden y tipo
        notif_existente = await db.notificaciones.find_one({
            "orden_id": orden_id,
            "tipo": "recordatorio_subestado",
            "created_at": {"$gte": (now - timedelta(hours=24)).isoformat()}
        })
        
        if notif_existente:
            continue  # Ya hay notificación reciente
        
        label = SUBESTADO_LABELS.get(orden.get("subestado"), orden.get("subestado"))
        
        notif = Notificacion(
            tipo="recordatorio_subestado",
            mensaje=f"⏰ RECORDATORIO: Orden {orden['numero_orden']} en estado '{label}' pendiente de revisión. Motivo: {orden.get('motivo_subestado', 'Sin especificar')}",
            orden_id=orden_id
        )
        notif_doc = notif.model_dump()
        notif_doc['created_at'] = notif_doc['created_at'].isoformat()
        await db.notificaciones.insert_one(notif_doc)
        notificaciones_creadas += 1
    
    return {
        "message": f"Generados {notificaciones_creadas} recordatorios",
        "ordenes_revisadas": len(ordenes),
        "recordatorios_creados": notificaciones_creadas
    }

# ==================== EVIDENCIAS ====================

@router.post("/ordenes/{orden_id}/evidencias")
async def subir_evidencia_admin(orden_id: str, file: UploadFile = File(...), user: dict = Depends(require_admin)):
    """Subir evidencia/foto por parte del admin a Cloudinary (almacenamiento permanente)"""
    from services.cloudinary_service import upload_image
    
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # Subir a Cloudinary
    result = await upload_image(
        file=file,
        orden_id=orden_id,
        tipo="admin",
        numero_orden=orden.get('numero_orden', orden_id)
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=f"Error subiendo imagen: {result.get('error')}")
    
    # Guardar URL de Cloudinary en la orden
    evidencias = orden.get('evidencias', [])
    evidencias.append(result["url"])
    await db.ordenes.update_one({"id": orden_id}, {"$set": {"evidencias": evidencias, "updated_at": datetime.now(timezone.utc).isoformat()}})
    
    # Registrar en auditoría
    await registrar_auditoria(
        entidad="orden",
        entidad_id=orden_id,
        accion="subir_evidencia",
        usuario_id=user.get('user_id'),
        usuario_email=user.get('email'),
        rol=user.get('role'),
        cambios={"evidencia_añadida": result["url"], "cloudinary_id": result.get("public_id")}
    )
    
    return {"message": "Evidencia subida a Cloudinary", "url": result["url"], "public_id": result.get("public_id")}

@router.post("/ordenes/{orden_id}/evidencias-tecnico")
async def subir_evidencia_tecnico(
    orden_id: str, 
    file: UploadFile = File(...), 
    tipo_foto: str = "general",  # general, antes, despues
    user: dict = Depends(require_auth)
):
    """Subir evidencia/foto por parte del técnico a Cloudinary. tipo_foto puede ser: general, antes, despues"""
    from services.cloudinary_service import upload_image
    
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # Subir a Cloudinary
    result = await upload_image(
        file=file,
        orden_id=orden_id,
        tipo=tipo_foto,
        numero_orden=orden.get('numero_orden', orden_id)
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=f"Error subiendo imagen: {result.get('error')}")
    
    # Determinar en qué array guardar la URL de Cloudinary
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if tipo_foto == "antes":
        fotos_antes = orden.get('fotos_antes', [])
        fotos_antes.append(result["url"])
        update_data["fotos_antes"] = fotos_antes
    elif tipo_foto == "despues":
        fotos_despues = orden.get('fotos_despues', [])
        fotos_despues.append(result["url"])
        update_data["fotos_despues"] = fotos_despues
    else:
        # General - va a evidencias_tecnico
        evidencias_tecnico = orden.get('evidencias_tecnico', [])
        evidencias_tecnico.append(result["url"])
        update_data["evidencias_tecnico"] = evidencias_tecnico
    
    await db.ordenes.update_one({"id": orden_id}, {"$set": update_data})
    return {"message": f"Foto ({tipo_foto}) subida a Cloudinary", "url": result["url"], "tipo": tipo_foto, "public_id": result.get("public_id")}


# ==================== ELIMINAR FOTO ====================

class EliminarFotoRequest(BaseModel):
    url: str
    tipo: str  # 'admin' (evidencias) | 'tecnico' (evidencias_tecnico) | 'antes' (fotos_antes) | 'despues' (fotos_despues)


@router.delete("/ordenes/{orden_id}/fotos")
async def eliminar_foto_orden(orden_id: str, request: EliminarFotoRequest, user: dict = Depends(require_auth)):
    """Eliminar una foto/evidencia concreta de una orden por URL.

    El tipo determina de qué array MongoDB se elimina:
      - admin    -> evidencias
      - tecnico  -> evidencias_tecnico
      - antes    -> fotos_antes
      - despues  -> fotos_despues
    """
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    tipo_to_field = {
        "admin": "evidencias",
        "tecnico": "evidencias_tecnico",
        "antes": "fotos_antes",
        "despues": "fotos_despues",
    }
    field = tipo_to_field.get(request.tipo)
    if not field:
        raise HTTPException(status_code=400, detail=f"Tipo de foto no válido: {request.tipo}")

    fotos_actuales = orden.get(field, []) or []
    if request.url not in fotos_actuales:
        raise HTTPException(status_code=404, detail="Foto no encontrada en la orden")

    nuevas = [u for u in fotos_actuales if u != request.url]
    await db.ordenes.update_one(
        {"id": orden_id},
        {"$set": {field: nuevas, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )

    await registrar_auditoria(
        entidad="orden",
        entidad_id=orden_id,
        accion="eliminar_evidencia",
        usuario_id=user.get('user_id'),
        usuario_email=user.get('email'),
        rol=user.get('role'),
        cambios={"foto_eliminada": request.url, "campo": field},
    )

    return {"message": "Foto eliminada", "tipo": request.tipo, "campo": field, "restantes": len(nuevas)}



# ==================== DESCARGA ZIP DE FOTOS ====================

@router.get("/ordenes/{orden_id}/fotos-zip")
async def descargar_fotos_zip(orden_id: str, user: dict = Depends(require_auth)):
    """Descarga todas las fotos de una orden en un archivo ZIP (soporta Cloudinary y local).

    Cambios anti-corrupción de ZIP:
      - Devuelve `Response` (no StreamingResponse) para enviar Content-Length
        correcto y evitar truncamiento por chunked-encoding en proxies/CDN.
      - Sanea Content-Disposition con filename*=UTF-8'' para nombres con
        caracteres especiales (ñ, espacios, /).
      - Sanea nombres internos del ZIP (deduplica, quita caracteres
        reservados de Windows).
      - Detecta extensión correcta usando Content-Type del HTTP response.
    """
    import zipfile
    import io
    import httpx
    from fastapi.responses import Response
    from utils.zip_helper import (
        safe_inner_filename, safe_content_disposition, detect_extension,
    )

    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    # Recopilar todas las fotos
    todas_fotos = []
    for foto in (orden.get('evidencias') or []):
        todas_fotos.append(("admin", foto))
    for foto in (orden.get('evidencias_tecnico') or []):
        todas_fotos.append(("tecnico", foto))
    for foto in (orden.get('fotos_antes') or []):
        todas_fotos.append(("antes", foto))
    for foto in (orden.get('fotos_despues') or []):
        todas_fotos.append(("despues", foto))

    if not todas_fotos:
        raise HTTPException(status_code=404, detail="No hay fotos para descargar")

    zip_buffer = io.BytesIO()
    errores = []
    fotos_ok = 0
    nombres_usados: set[str] = set()

    def _make_unique(base: str) -> str:
        """Garantiza unicidad del nombre dentro del ZIP."""
        n = safe_inner_filename(base)
        if n not in nombres_usados:
            nombres_usados.add(n)
            return n
        i = 2
        while True:
            if "." in n:
                stem, ext = n.rsplit(".", 1)
                cand = f"{stem}_{i}.{ext}"
            else:
                cand = f"{n}_{i}"
            if cand not in nombres_usados:
                nombres_usados.add(cand)
                return cand
            i += 1

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for idx, (categoria, foto_ref) in enumerate(todas_fotos):
                try:
                    if foto_ref.startswith('http'):
                        content = None
                        ctype = None
                        for intento in range(3):
                            try:
                                response = await client.get(foto_ref, follow_redirects=True)
                                if response.status_code == 200:
                                    content = response.content
                                    ctype = response.headers.get("content-type")
                                    break
                                if response.status_code == 404:
                                    logger.warning(f"Foto no encontrada (404): {foto_ref}")
                                    break
                            except httpx.TimeoutException:
                                if intento < 2:
                                    await asyncio.sleep(1)
                                    continue
                                logger.error(f"Timeout descargando foto: {foto_ref}")
                            except Exception as e:
                                logger.error(f"Error intento {intento+1} descargando {foto_ref}: {e}")
                                if intento < 2:
                                    await asyncio.sleep(1)

                        if content:
                            ext = detect_extension(foto_ref, ctype)
                            zip_filename = _make_unique(f"{categoria}_{idx+1}.{ext}")
                            zip_file.writestr(zip_filename, content)
                            fotos_ok += 1
                        else:
                            errores.append(f"{categoria}_{idx+1}")
                    else:
                        file_path = UPLOAD_DIR / foto_ref
                        if file_path.exists():
                            zip_filename = _make_unique(f"{categoria}_{foto_ref}")
                            zip_file.write(file_path, zip_filename)
                            fotos_ok += 1
                        else:
                            errores.append(f"local_{foto_ref}")
                except Exception as e:
                    logger.error(f"Error procesando foto {foto_ref}: {e}")
                    errores.append(f"{categoria}_{idx+1}")
                    continue

    if fotos_ok == 0:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo descargar ninguna foto. Errores: {errores[:5]}",
        )

    zip_bytes = zip_buffer.getvalue()
    numero_orden = orden.get('numero_orden', orden_id)

    if errores:
        logger.warning(f"ZIP {numero_orden}: {fotos_ok} fotos OK, {len(errores)} errores: {errores[:5]}")

    # Response con Content-Length explícito (no StreamingResponse) para evitar
    # ZIP truncado por chunked-encoding en proxies.
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": safe_content_disposition(f"{numero_orden}_fotos.zip"),
            "Content-Length": str(len(zip_bytes)),
            "X-Fotos-OK": str(fotos_ok),
            "X-Fotos-Error": str(len(errores)),
            "Cache-Control": "no-store",
        },
    )


@router.get("/ordenes/{orden_id}/fotos-zip/{tipo}")
async def descargar_fotos_zip_por_tipo(orden_id: str, tipo: str, user: dict = Depends(require_auth)):
    """Descarga fotos de una orden filtradas por tipo: 'antes' o 'despues'."""
    import zipfile
    import io
    import httpx
    from fastapi.responses import Response

    if tipo not in ("antes", "despues"):
        raise HTTPException(status_code=400, detail="Tipo debe ser 'antes' o 'despues'")

    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    fotos = []
    if tipo == "antes":
        for f in (orden.get('evidencias') or []):
            fotos.append(f)
        for f in (orden.get('fotos_antes') or []):
            fotos.append(f)
    else:
        for f in (orden.get('fotos_despues') or []):
            fotos.append(f)

    if not fotos:
        raise HTTPException(status_code=404, detail=f"No hay fotos de '{tipo}' para descargar")

    zip_buffer = io.BytesIO()
    errores = []
    fotos_ok = 0
    nombres_usados: set[str] = set()
    from utils.zip_helper import (
        safe_inner_filename, safe_content_disposition, detect_extension,
    )

    def _make_unique(base: str) -> str:
        n = safe_inner_filename(base)
        if n not in nombres_usados:
            nombres_usados.add(n)
            return n
        i = 2
        while True:
            if "." in n:
                stem, ext = n.rsplit(".", 1)
                cand = f"{stem}_{i}.{ext}"
            else:
                cand = f"{n}_{i}"
            if cand not in nombres_usados:
                nombres_usados.add(cand)
                return cand
            i += 1

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for idx, foto_ref in enumerate(fotos):
                try:
                    if foto_ref.startswith('http'):
                        content = None
                        ctype = None
                        for intento in range(3):
                            try:
                                response = await client.get(foto_ref, follow_redirects=True)
                                if response.status_code == 200:
                                    content = response.content
                                    ctype = response.headers.get("content-type")
                                    break
                                elif response.status_code == 404:
                                    break
                            except httpx.TimeoutException:
                                if intento < 2:
                                    await asyncio.sleep(1)
                            except Exception:
                                if intento < 2:
                                    await asyncio.sleep(1)

                        if content:
                            ext = detect_extension(foto_ref, ctype)
                            zip_file.writestr(_make_unique(f"{tipo}_{idx+1}.{ext}"), content)
                            fotos_ok += 1
                        else:
                            errores.append(idx+1)
                    else:
                        file_path = UPLOAD_DIR / foto_ref
                        if file_path.exists():
                            zip_file.write(file_path, _make_unique(f"{tipo}_{foto_ref}"))
                            fotos_ok += 1
                        else:
                            errores.append(idx+1)
                except Exception as e:
                    logger.error(f"Error descargando foto {foto_ref}: {e}")
                    errores.append(idx+1)

    if fotos_ok == 0:
        raise HTTPException(status_code=500, detail=f"No se pudo descargar ninguna foto de '{tipo}'")

    zip_bytes = zip_buffer.getvalue()
    numero_orden = orden.get('numero_orden', orden_id)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": safe_content_disposition(f"{numero_orden}_fotos_{tipo}.zip"),
            "Content-Length": str(len(zip_bytes)),
            "Cache-Control": "no-store",
        },
    )


# ==================== MÉTRICAS ====================

@router.get("/ordenes/{orden_id}/metricas")
async def obtener_metricas_orden(orden_id: str):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    now = datetime.now(timezone.utc)
    def parse_date(ds):
        if not ds: return None
        if isinstance(ds, datetime): return ds
        return datetime.fromisoformat(ds.replace('Z', '+00:00'))
    def calc_hours(s, e):
        s, e = parse_date(s), parse_date(e)
        return round((e - s).total_seconds() / 3600, 2) if s and e else None
    created_at = parse_date(orden.get('created_at'))
    metricas = {"tiempo_desde_creacion_horas": None, "tiempo_logistica_horas": None, "tiempo_espera_taller_horas": None, "tiempo_reparacion_horas": None, "tiempo_total_proceso_horas": None, "dias_desde_creacion": None, "en_retraso": False, "retraso_dias": 0}
    if created_at:
        delta = now - created_at
        metricas["tiempo_desde_creacion_horas"] = round(delta.total_seconds() / 3600, 2)
        metricas["dias_desde_creacion"] = delta.days
        if orden.get('estado') != 'enviado' and delta.days > 5:
            metricas["en_retraso"] = True
            metricas["retraso_dias"] = delta.days - 5
    metricas["tiempo_logistica_horas"] = calc_hours(orden.get('created_at'), orden.get('fecha_recibida_centro'))
    metricas["tiempo_espera_taller_horas"] = calc_hours(orden.get('fecha_recibida_centro'), orden.get('fecha_inicio_reparacion'))
    metricas["tiempo_reparacion_horas"] = calc_hours(orden.get('fecha_inicio_reparacion'), orden.get('fecha_fin_reparacion'))
    metricas["tiempo_total_proceso_horas"] = calc_hours(orden.get('created_at'), orden.get('fecha_enviado'))
    metricas["timestamps"] = {"created_at": orden.get('created_at'), "fecha_recibida_centro": orden.get('fecha_recibida_centro'), "fecha_inicio_reparacion": orden.get('fecha_inicio_reparacion'), "fecha_fin_reparacion": orden.get('fecha_fin_reparacion'), "fecha_enviado": orden.get('fecha_enviado')}
    return metricas

# ==================== LINK SEGUIMIENTO ====================

@router.get("/ordenes/{orden_id}/link-seguimiento")
async def obtener_link_seguimiento(orden_id: str, user: dict = Depends(require_auth)):
    """Obtiene el token de seguimiento de una orden para compartir con el cliente."""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    cliente = await db.clientes.find_one({"id": orden.get('cliente_id')}, {"_id": 0})
    telefono_hint = ""
    if cliente and cliente.get('telefono'):
        tel = cliente['telefono']
        telefono_hint = f"***{tel[-4:]}" if len(tel) >= 4 else "****"
    token = orden.get('token_seguimiento')
    if not token:
        token = str(uuid.uuid4())[:12].upper()
        await db.ordenes.update_one({"id": orden_id}, {"$set": {"token_seguimiento": token}})
    return {
        "token": token,
        "telefono_hint": telefono_hint,
        "orden_id": orden_id,
        "numero_orden": orden.get('numero_orden')
    }


@router.post("/ordenes/{orden_id}/restablecer-seguimiento")
async def restablecer_token_seguimiento(orden_id: str, user: dict = Depends(require_admin)):
    """Genera un nuevo token de seguimiento para la orden."""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    new_token = str(uuid.uuid4())[:12].upper().replace("-", "")
    # Format as XXXX-XXXX-XXX
    new_token = f"{new_token[:4]}-{new_token[4:8]}-{new_token[8:11]}"
    
    await db.ordenes.update_one(
        {"id": orden_id},
        {"$set": {
            "token_seguimiento": new_token,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    cliente = await db.clientes.find_one({"id": orden.get('cliente_id')}, {"_id": 0})
    telefono_hint = ""
    if cliente and cliente.get('telefono'):
        tel = cliente['telefono']
        telefono_hint = f"***{tel[-4:]}" if len(tel) >= 4 else "****"
    
    return {
        "token": new_token,
        "telefono_hint": telefono_hint,
        "orden_id": orden_id,
        "numero_orden": orden.get('numero_orden'),
        "message": "Token restablecido correctamente"
    }


# ==================== DIAGNÓSTICO ====================

@router.post("/ordenes/{orden_id}/diagnostico")
async def guardar_diagnostico(orden_id: str, request: DiagnosticoRequest, user: dict = Depends(require_tecnico)):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    await db.ordenes.update_one({"id": orden_id}, {"$set": {"diagnostico_tecnico": request.diagnostico, "updated_at": datetime.now(timezone.utc).isoformat()}})
    
    # Auto-sync diagnosis to Insurama
    if orden.get("numero_autorizacion"):
        asyncio.create_task(sync_diagnostico_to_insurama(orden, request.diagnostico))
    
    return {"message": "Diagnóstico guardado", "diagnostico": request.diagnostico}

# ==================== GARANTÍAS ====================

class CrearGarantiaRequest(BaseModel):
    indicaciones_cliente: str = ""

@router.post("/ordenes/{orden_id}/crear-garantia")
async def crear_garantia_simple(orden_id: str, request: CrearGarantiaRequest = None, user: dict = Depends(require_admin)):
    """
    Crea una orden de garantía desde una orden enviada.
    También crea una incidencia de tipo 'garantia' vinculada al cliente.
    """
    # Parse request body si existe
    indicaciones = request.indicaciones_cliente if request else ""
    
    orden_padre = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden_padre:
        raise HTTPException(status_code=404, detail="Orden padre no encontrada")
    
    if orden_padre.get('estado') != 'enviado':
        raise HTTPException(status_code=400, detail="Solo se pueden abrir garantías de órdenes enviadas")
    
    if orden_padre.get('es_garantia'):
        raise HTTPException(status_code=400, detail="Esta orden ya es una garantía")
    
    now = datetime.now(timezone.utc)
    
    # Clonar dispositivo del padre y actualizar daños con las nuevas indicaciones del cliente
    dispositivo_garantia = dict(orden_padre['dispositivo']) if orden_padre.get('dispositivo') else {}
    if indicaciones:
        dispositivo_garantia['daños'] = indicaciones

    # 1. Crear la nueva orden de garantía con toda la info del dispositivo
    nueva_orden = OrdenTrabajo(
        cliente_id=orden_padre['cliente_id'],
        dispositivo=dispositivo_garantia,
        agencia_envio=orden_padre.get('agencia_envio', ''),
        codigo_recogida_entrada=orden_padre.get('codigo_recogida_entrada', ''),
        notas=f"GARANTÍA de orden {orden_padre['numero_orden']}. {indicaciones or orden_padre.get('notas', '')}".strip(),
        orden_padre_id=orden_id,
        es_garantia=True,
        tipo_servicio="garantia_fabricante"
    )
    nueva_orden.qr_code = generate_barcode(nueva_orden.numero_orden)
    nueva_orden.historial_estados = [{
        "estado": OrderStatus.PENDIENTE_RECIBIR.value,
        "fecha": now.isoformat(),
        "usuario": user.get('email', 'sistema')
    }]
    
    doc = nueva_orden.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    # Heredar campos relevantes de la orden padre
    campos_heredar = [
        'cliente_nombre', 'cliente_email', 'cliente_telefono',
        'dispositivo_marca', 'dispositivo_modelo', 'dispositivo_color',
        'numero_serie', 'imei', 'codigo_insurama', 'numero_autorizacion',
        'tipo_seguro', 'compania_seguro'
    ]
    for campo in campos_heredar:
        if orden_padre.get(campo):
            doc[campo] = orden_padre[campo]
    
    # Referencia clara a la orden padre
    doc['numero_orden_padre'] = orden_padre['numero_orden']
    
    # Indicaciones del cliente para la garantía
    if indicaciones:
        doc['indicaciones_garantia_cliente'] = indicaciones
        doc['indicaciones_tecnico'] = f"GARANTÍA: {indicaciones}"
        # Aseguramos que la avería reportada y el campo "averia_descripcion"
        # reflejen las nuevas indicaciones del cliente (no la avería del parte original)
        doc['averia_descripcion'] = indicaciones
        if isinstance(doc.get('dispositivo'), dict):
            doc['dispositivo']['daños'] = indicaciones
    
    await db.ordenes.insert_one(doc)
    doc.pop('_id', None)
    
    # 2. Vincular la garantía a la orden padre
    ordenes_garantia = orden_padre.get('ordenes_garantia', [])
    ordenes_garantia.append(nueva_orden.id)
    await db.ordenes.update_one(
        {"id": orden_id},
        {"$set": {
            "ordenes_garantia": ordenes_garantia,
            "updated_at": now.isoformat()
        }}
    )
    
    # 3. Crear incidencia de tipo garantía vinculada al cliente
    incidencia_doc = {
        "id": str(uuid.uuid4()),
        "numero_incidencia": f"INC-GAR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "cliente_id": orden_padre['cliente_id'],
        "orden_id": orden_id,
        "orden_garantia_id": nueva_orden.id,
        "tipo": "garantia",
        "titulo": f"Garantía - {orden_padre['dispositivo'].get('modelo', 'Dispositivo')}",
        "descripcion": f"Se ha abierto garantía para la orden {orden_padre['numero_orden']}. Dispositivo: {orden_padre['dispositivo'].get('modelo', '')} {orden_padre['dispositivo'].get('color', '')}",
        "estado": "abierta",
        "prioridad": "alta",
        "created_by": user.get('user_id'),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    await db.incidencias.insert_one(incidencia_doc)
    incidencia_doc.pop('_id', None)
    
    # 4. Crear notificación
    notif = Notificacion(
        tipo="garantia_abierta",
        mensaje=f"Se ha abierto garantía para orden {orden_padre['numero_orden']} → Nueva orden: {nueva_orden.numero_orden}",
        orden_id=nueva_orden.id
    )
    notif_doc = notif.model_dump()
    notif_doc['created_at'] = notif_doc['created_at'].isoformat()
    await db.notificaciones.insert_one(notif_doc)
    
    # 5. Registrar en auditoría
    await registrar_auditoria(
        entidad="orden",
        entidad_id=orden_id,
        accion="abrir_garantia",
        usuario_id=user.get('user_id'),
        usuario_email=user.get('email'),
        rol=user.get('role'),
        cambios={
            "orden_garantia_id": nueva_orden.id,
            "numero_orden_garantia": nueva_orden.numero_orden,
            "incidencia_id": incidencia_doc['id']
        }
    )
    
    return {
        "message": "Garantía creada correctamente",
        "orden_garantia": doc,
        "incidencia": incidencia_doc
    }

@router.get("/ordenes/{orden_id}/garantias")
async def obtener_garantias_orden(orden_id: str, user: dict = Depends(require_auth)):
    """Obtiene todas las órdenes de garantía asociadas a una orden padre."""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    garantia_ids = orden.get('ordenes_garantia', [])
    if not garantia_ids:
        return []
    
    garantias = await db.ordenes.find(
        {"id": {"$in": garantia_ids}},
        {"_id": 0}
    ).to_list(100)
    
    return garantias

@router.post("/ordenes/{orden_id}/garantia")
async def crear_orden_garantia(orden_id: str, data: dict, user: dict = Depends(require_admin)):
    orden_padre = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden_padre:
        raise HTTPException(status_code=404, detail="Orden padre no encontrada")
    nueva_orden = OrdenTrabajo(cliente_id=orden_padre['cliente_id'], dispositivo=orden_padre['dispositivo'], agencia_envio=data.get('agencia_envio', orden_padre.get('agencia_envio', '')), codigo_recogida_entrada=data.get('codigo_recogida_entrada', ''), notas=data.get('notas', f"Garantía de orden {orden_padre['numero_orden']}"), orden_padre_id=orden_id, es_garantia=True)
    nueva_orden.qr_code = generate_barcode(nueva_orden.numero_orden)
    nueva_orden.historial_estados = [{"estado": OrderStatus.PENDIENTE_RECIBIR.value, "fecha": datetime.now(timezone.utc).isoformat(), "usuario": user.get('email', 'sistema')}]
    doc = nueva_orden.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.ordenes.insert_one(doc)
    ordenes_garantia = orden_padre.get('ordenes_garantia', [])
    ordenes_garantia.append(nueva_orden.id)
    await db.ordenes.update_one({"id": orden_id}, {"$set": {"ordenes_garantia": ordenes_garantia, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return nueva_orden

# ==================== EXPORTAR EVIDENCIAS ====================

@router.get("/ordenes/{orden_id}/exportar-evidencias")
async def exportar_evidencias_orden(orden_id: str, user: dict = Depends(require_admin)):
    import zipfile
    import io
    from fastapi.responses import FileResponse
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    todas_evidencias = orden.get('evidencias', []) + orden.get('evidencias_tecnico', [])
    if not todas_evidencias:
        raise HTTPException(status_code=404, detail="No hay evidencias para exportar")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for i, ev in enumerate(todas_evidencias):
            file_path = UPLOAD_DIR / ev
            if file_path.exists():
                zip_file.write(file_path, f"{orden['numero_orden']}_{i+1}_{ev}")
    zip_buffer.seek(0)
    zip_path = UPLOAD_DIR / f"evidencias_{orden['numero_orden']}.zip"
    with open(zip_path, 'wb') as f:
        f.write(zip_buffer.getvalue())
    return FileResponse(str(zip_path), filename=f"evidencias_{orden['numero_orden']}.zip", media_type="application/zip")

# ==================== REGENERAR CÓDIGOS ====================

@router.post("/ordenes/{orden_id}/regenerar-codigo")
async def regenerar_codigo_barras(orden_id: str, user: dict = Depends(require_admin)):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    nuevo_codigo = generate_barcode(orden['numero_orden'])
    await db.ordenes.update_one({"id": orden_id}, {"$set": {"qr_code": nuevo_codigo, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": "Código de barras regenerado", "numero_orden": orden['numero_orden']}

@router.post("/ordenes/regenerar-todos-codigos")
async def regenerar_todos_codigos(user: dict = Depends(require_master)):
    ordenes = await db.ordenes.find({}, {"id": 1, "numero_orden": 1}).to_list(10000)
    for orden in ordenes:
        nuevo_codigo = generate_barcode(orden['numero_orden'])
        await db.ordenes.update_one({"id": orden['id']}, {"$set": {"qr_code": nuevo_codigo}})
    return {"message": f"Códigos regenerados para {len(ordenes)} órdenes"}

# ==================== REEMPLAZO DE DISPOSITIVO ====================

class SolicitudReemplazoRequest(BaseModel):
    motivo: str
    diagnostico_final: Optional[str] = None

class AutorizarReemplazoRequest(BaseModel):
    nuevo_modelo: str
    nuevo_color: str
    nuevo_imei: str
    valor_dispositivo: float
    notas: Optional[str] = None

@router.post("/ordenes/{orden_id}/solicitar-reemplazo")
async def solicitar_reemplazo(orden_id: str, request: SolicitudReemplazoRequest, user: dict = Depends(require_auth)):
    """
    Técnico solicita reemplazo cuando el dispositivo NO es reparable.
    - Bloquea la orden
    - Notifica al admin
    - Admin debe autorizar con datos del nuevo dispositivo
    """
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    if orden.get('reemplazo_solicitado'):
        raise HTTPException(status_code=400, detail="Ya se ha solicitado reemplazo para esta orden")
    
    now = datetime.now(timezone.utc)
    
    # Actualizar orden con solicitud de reemplazo
    historial = orden.get('historial_estados', [])
    historial.append({
        "estado": "reemplazo_solicitado",
        "fecha": now.isoformat(),
        "usuario": user.get('email', 'tecnico'),
        "motivo": request.motivo
    })
    
    await db.ordenes.update_one(
        {"id": orden_id},
        {"$set": {
            "reemplazo_solicitado": True,
            "reemplazo_motivo": request.motivo,
            "reemplazo_diagnostico": request.diagnostico_final,
            "reemplazo_solicitado_por": user.get('email', 'tecnico'),
            "reemplazo_fecha_solicitud": now.isoformat(),
            "bloqueada": True,
            "historial_estados": historial,
            "updated_at": now.isoformat()
        }}
    )
    
    # Crear notificación urgente para admin
    notif = Notificacion(
        tipo="reemplazo_solicitado",
        mensaje=f"⚠️ REEMPLAZO SOLICITADO: Orden {orden['numero_orden']} - Dispositivo NO reparable. Motivo: {request.motivo}",
        orden_id=orden_id
    )
    notif_doc = notif.model_dump()
    notif_doc['created_at'] = notif_doc['created_at'].isoformat()
    notif_doc['urgente'] = True
    notif_doc['popup'] = True
    await db.notificaciones.insert_one(notif_doc)
    
    return {
        "message": "Solicitud de reemplazo enviada. La orden está bloqueada hasta autorización del administrador.",
        "orden_bloqueada": True
    }

@router.post("/ordenes/{orden_id}/autorizar-reemplazo")
async def autorizar_reemplazo(orden_id: str, request: AutorizarReemplazoRequest, user: dict = Depends(require_admin)):
    """
    Admin autoriza el reemplazo:
    - Registra datos del nuevo dispositivo
    - ELIMINA todos los materiales de reparación (ya no aplican)
    - Registra solo el valor del nuevo dispositivo
    - Desbloquea la orden
    """
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    if not orden.get('reemplazo_solicitado'):
        raise HTTPException(status_code=400, detail="No hay solicitud de reemplazo pendiente")
    
    now = datetime.now(timezone.utc)
    
    # Historial
    historial = orden.get('historial_estados', [])
    historial.append({
        "estado": OrderStatus.REEMPLAZO.value,
        "fecha": now.isoformat(),
        "usuario": user.get('email', 'admin'),
        "notas": f"Reemplazo autorizado. Nuevo dispositivo: {request.nuevo_modelo}"
    })
    
    # Datos del dispositivo de reemplazo
    dispositivo_reemplazo = {
        "modelo": request.nuevo_modelo,
        "color": request.nuevo_color,
        "imei": request.nuevo_imei,
        "valor": request.valor_dispositivo,
        "autorizado_por": user.get('email', 'admin'),
        "fecha_autorizacion": now.isoformat(),
        "notas": request.notas
    }
    
    # Guardar materiales originales en histórico antes de eliminarlos
    materiales_originales = orden.get('materiales', [])
    
    await db.ordenes.update_one(
        {"id": orden_id},
        {"$set": {
            "estado": OrderStatus.REEMPLAZO.value,
            "reemplazo_autorizado": True,
            "reemplazo_autorizado_por": user.get('email', 'admin'),
            "reemplazo_fecha_autorizacion": now.isoformat(),
            "dispositivo_reemplazo": dispositivo_reemplazo,
            "materiales": [],  # Eliminar materiales de reparación
            "materiales_historico": materiales_originales,  # Guardar para auditoría
            "bloqueada": False,
            "historial_estados": historial,
            "updated_at": now.isoformat()
        }}
    )
    
    # Notificación
    notif = Notificacion(
        tipo="reemplazo_autorizado",
        mensaje=f"✅ REEMPLAZO AUTORIZADO: Orden {orden['numero_orden']} - Nuevo dispositivo: {request.nuevo_modelo} (IMEI: {request.nuevo_imei})",
        orden_id=orden_id
    )
    notif_doc = notif.model_dump()
    notif_doc['created_at'] = notif_doc['created_at'].isoformat()
    await db.notificaciones.insert_one(notif_doc)
    
    return {
        "message": "Reemplazo autorizado correctamente",
        "dispositivo_reemplazo": dispositivo_reemplazo,
        "materiales_eliminados": len(materiales_originales)
    }

@router.post("/ordenes/{orden_id}/rechazar-reemplazo")
async def rechazar_reemplazo(orden_id: str, motivo: str = "", user: dict = Depends(require_admin)):
    """Admin rechaza la solicitud de reemplazo"""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    if not orden.get('reemplazo_solicitado'):
        raise HTTPException(status_code=400, detail="No hay solicitud de reemplazo pendiente")
    
    now = datetime.now(timezone.utc)
    
    historial = orden.get('historial_estados', [])
    historial.append({
        "estado": "reemplazo_rechazado",
        "fecha": now.isoformat(),
        "usuario": user.get('email', 'admin'),
        "motivo": motivo
    })
    
    await db.ordenes.update_one(
        {"id": orden_id},
        {"$set": {
            "reemplazo_solicitado": False,
            "reemplazo_rechazado": True,
            "reemplazo_rechazo_motivo": motivo,
            "reemplazo_rechazado_por": user.get('email', 'admin'),
            "bloqueada": False,
            "historial_estados": historial,
            "updated_at": now.isoformat()
        }}
    )
    
    # Notificación al técnico
    notif = Notificacion(
        tipo="reemplazo_rechazado",
        mensaje=f"❌ Solicitud de reemplazo RECHAZADA para orden {orden['numero_orden']}. {motivo}",
        orden_id=orden_id
    )
    notif_doc = notif.model_dump()
    notif_doc['created_at'] = notif_doc['created_at'].isoformat()
    await db.notificaciones.insert_one(notif_doc)
    
    return {"message": "Solicitud de reemplazo rechazada", "orden_desbloqueada": True}



# ==================== LIQUIDACIÓN ====================

class RegistrarLiquidacionRequest(BaseModel):
    estado: str = "pendiente_cobro"
    importe: float = 0
    fecha_cierre: Optional[str] = None

@router.post("/{orden_id}/registrar-liquidacion")
async def registrar_liquidacion(
    orden_id: str,
    data: RegistrarLiquidacionRequest,
    user: dict = Depends(require_admin)
):
    """Registra una orden en el sistema de liquidaciones (para órdenes de seguro)"""
    orden = await db.ordenes.find_one({"id": orden_id})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    liquidacion = {
        "orden_id": orden_id,
        "numero_orden": orden.get("numero_orden"),
        "numero_autorizacion": orden.get("numero_autorizacion"),
        "cliente_nombre": orden.get("cliente", {}).get("nombre", "") + " " + orden.get("cliente", {}).get("apellidos", ""),
        "dispositivo": f"{orden.get('dispositivo', {}).get('marca', '')} {orden.get('dispositivo', {}).get('modelo', '')}",
        "importe": data.importe or orden.get("presupuesto_total", 0),
        "estado": data.estado,
        "fecha_cierre": data.fecha_cierre or datetime.now(timezone.utc).isoformat(),
        "origen": orden.get("origen", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "registrado_por": user.get("email")
    }
    
    # Verificar si ya existe
    existente = await db.liquidaciones.find_one({"orden_id": orden_id})
    if existente:
        await db.liquidaciones.update_one(
            {"orden_id": orden_id},
            {"$set": liquidacion}
        )
        return {"message": "Liquidación actualizada", "liquidacion": liquidacion}
    
    await db.liquidaciones.insert_one(liquidacion)
    
    # Marcar la orden como registrada en liquidación
    await db.ordenes.update_one(
        {"id": orden_id},
        {"$set": {
            "liquidacion_registrada": True,
            "liquidacion_fecha": liquidacion["fecha_cierre"]
        }}
    )
    
    return {"message": "Liquidación registrada", "liquidacion": liquidacion}



# ==================== LOGÍSTICA - INTEGRACIÓN PROFUNDA GLS ====================

async def _registrar_evento_logistica(orden_id: str, tipo_evento: str, detalle: str, usuario: str):
    """Registra un evento de logística en el historial de la OT."""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0, "historial_estados": 1})
    if not orden:
        return
    historial = orden.get("historial_estados", [])
    historial.append({
        "estado": "logistica",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "usuario": usuario,
        "tipo": "logistica",
        "subtipo": tipo_evento,
        "detalle": detalle,
    })
    await db.ordenes.update_one(
        {"id": orden_id},
        {"$set": {"historial_estados": historial, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )


async def _enviar_email_logistica(orden_id: str, tipo: str, codbarras: str):
    """Envía email al cliente cuando se genera recogida o envío."""
    try:
        orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
        if not orden:
            return
        cliente = await db.clientes.find_one({"id": orden.get("cliente_id")}, {"_id": 0})
        if not cliente or not cliente.get("email"):
            return

        from services.email_service import send_email, FRONTEND_URL

        numero = orden.get("numero_autorizacion") or orden.get("numero_orden", "")
        # URL de tracking público GLS: formato mygls oficial
        # https://mygls.gls-spain.es/e/{codexp}/{cp_destinatario}
        codexp = ""
        cp_destinatario = ""
        for env in (orden.get("gls_envios") or []):
            if env.get("codbarras") == codbarras:
                codexp = env.get("codexp", "")
                cp_destinatario = env.get("cp_destinatario") \
                    or (env.get("destinatario_snapshot") or {}).get("cp", "")
                break
        if not cp_destinatario and orden.get("cp_envio"):
            cp_destinatario = orden["cp_envio"]
        if codexp and cp_destinatario:
            tracking_url = f"https://mygls.gls-spain.es/e/{codexp}/{cp_destinatario}"
        else:
            tracking_url = f"https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/?match={codbarras}"

        if tipo == "recogida":
            subject = f"Revix - Recogida programada para su orden {numero}"
            titulo = "Recogida Programada"
            contenido = f'''
            <p>Le informamos que hemos programado la <strong>recogida</strong> de su dispositivo para la orden <strong>{numero}</strong>.</p>
            <table style="margin:15px 0;border-collapse:collapse;">
              <tr><td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Nº Seguimiento</td>
                  <td style="padding:8px 15px;border:1px solid #e2e8f0;font-family:monospace;">{codbarras}</td></tr>
              <tr><td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Transportista</td>
                  <td style="padding:8px 15px;border:1px solid #e2e8f0;">GLS</td></tr>
            </table>
            <p>Puede seguir el estado de la recogida en el siguiente enlace:</p>
            <p><a href="{tracking_url}" style="color:#2563eb;">{tracking_url}</a></p>
            <p>El transportista se pondrá en contacto con usted para coordinar la recogida.</p>'''
        else:
            subject = f"Revix - Su dispositivo ha sido enviado - Orden {numero}"
            titulo = "Dispositivo Enviado"
            contenido = f'''
            <p>Le informamos que su dispositivo reparado de la orden <strong>{numero}</strong> ha sido <strong>enviado</strong>.</p>
            <table style="margin:15px 0;border-collapse:collapse;">
              <tr><td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Nº Seguimiento</td>
                  <td style="padding:8px 15px;border:1px solid #e2e8f0;font-family:monospace;">{codbarras}</td></tr>
              <tr><td style="padding:8px 15px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600;">Transportista</td>
                  <td style="padding:8px 15px;border:1px solid #e2e8f0;">GLS</td></tr>
            </table>
            <p>Puede seguir el estado de su envío en el siguiente enlace:</p>
            <p><a href="{tracking_url}" style="color:#2563eb;">{tracking_url}</a></p>
            <p>Recibirá su dispositivo en los próximos días.</p>'''

        send_email(
            to=cliente["email"],
            subject=subject,
            titulo=titulo,
            contenido=contenido,
            link_url=tracking_url,
            link_text="Seguir mi envío en GLS"
        )
    except Exception as e:
        logger.error(f"Error enviando email logística: {e}")


class LogisticsCreateRequest(BaseModel):
    dest_nombre: str
    dest_direccion: str
    dest_poblacion: str = ""
    dest_cp: str
    dest_provincia: str = ""
    dest_telefono: str = ""
    dest_email: str = ""
    dest_observaciones: str = ""
    bultos: int = 1
    peso: float = 1.0
    referencia: str = ""
    skip_duplicate_check: bool = False
    notify_client: bool = False


PICKUP_VALID_STATES = {"pendiente_recibir", "recibida", "cuarentena", "en_taller"}
DELIVERY_VALID_STATES = {"reparado", "validacion", "enviado"}


@router.get("/ordenes/{orden_id}/logistics")
async def get_orden_logistics(orden_id: str, user: dict = Depends(require_auth)):
    """Obtiene toda la información logística de una orden: recogidas, envíos y devoluciones."""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0, "id": 1})
    if not orden:
        raise HTTPException(404, "Orden no encontrada")

    from modules.gls import shipment_service
    return await shipment_service.get_orden_logistics(db, orden_id)


@router.post("/ordenes/{orden_id}/logistics/pickup")
async def crear_recogida_logistica(orden_id: str, data: LogisticsCreateRequest, user: dict = Depends(require_auth)):
    """Genera una recogida GLS para la orden. Validaciones de estado y datos."""
    if user.get("role") not in ("admin", "master"):
        raise HTTPException(403, "Solo administradores pueden generar recogidas")

    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(404, "Orden no encontrada")

    # Validate order state
    estado = orden.get("estado", "")
    if estado not in PICKUP_VALID_STATES and user.get("role") != "master":
        raise HTTPException(400, f"No se puede crear recogida en estado '{estado}'. Estados válidos: {', '.join(PICKUP_VALID_STATES)}")

    # Validate address data
    if not data.dest_nombre or not data.dest_direccion or not data.dest_cp:
        raise HTTPException(400, "Datos de dirección incompletos: nombre, dirección y CP son obligatorios")

    if not data.dest_telefono:
        raise HTTPException(400, "El teléfono es obligatorio para el transportista")

    from modules.gls import shipment_service

    # Check for duplicates unless forced
    if not data.skip_duplicate_check:
        existing = await shipment_service.check_duplicate_shipment(db, orden_id, "recogida")
        if existing:
            raise HTTPException(409, f"Ya existe una recogida activa para esta orden (código: {existing.get('gls_codbarras', 'N/A')}). Anúlala primero o usa skip_duplicate_check=true.")

    # Build shipment data
    shipment_data = {
        "orden_id": orden_id,
        "entidad_tipo": "orden",
        "tipo": "recogida",
        "cliente_id": orden.get("cliente_id", ""),
        "dest_nombre": data.dest_nombre,
        "dest_direccion": data.dest_direccion,
        "dest_poblacion": data.dest_poblacion,
        "dest_cp": data.dest_cp,
        "dest_provincia": data.dest_provincia,
        "dest_telefono": data.dest_telefono,
        "dest_email": data.dest_email,
        "dest_observaciones": data.dest_observaciones,
        "bultos": data.bultos,
        "peso": data.peso,
        "referencia": data.referencia or orden.get("numero_orden", "")[:20],
    }

    result = await shipment_service.create_shipment(
        db, shipment_data, user.get("email", ""),
        skip_duplicate_check=True,  # Already checked above
        notify_client=data.notify_client if hasattr(data, 'notify_client') else False
    )

    if not result["success"]:
        raise HTTPException(400, result.get("error", "Error al crear recogida GLS"))

    shipment = result.get("shipment", {})
    codbarras = shipment.get("gls_codbarras", "")

    # Register event in order timeline
    await _registrar_evento_logistica(
        orden_id, "recogida_creada",
        f"Recogida GLS creada - Código: {codbarras}",
        user.get("email", "Sistema")
    )

    # Send email notification (async, don't block)
    asyncio.create_task(_enviar_email_logistica(orden_id, "recogida", codbarras))

    return {"success": True, "shipment": shipment}


@router.post("/ordenes/{orden_id}/logistics/delivery")
async def crear_envio_logistica(orden_id: str, data: LogisticsCreateRequest, user: dict = Depends(require_auth)):
    """Genera un envío GLS para la orden. Validaciones de estado y datos."""
    if user.get("role") not in ("admin", "master"):
        raise HTTPException(403, "Solo administradores pueden generar envíos")

    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(404, "Orden no encontrada")

    # Validate order state
    estado = orden.get("estado", "")
    if estado not in DELIVERY_VALID_STATES and user.get("role") != "master":
        raise HTTPException(400, f"No se puede crear envío en estado '{estado}'. Estados válidos: {', '.join(DELIVERY_VALID_STATES)}")

    # Validate address data
    if not data.dest_nombre or not data.dest_direccion or not data.dest_cp:
        raise HTTPException(400, "Datos de dirección incompletos: nombre, dirección y CP son obligatorios")

    if not data.dest_telefono:
        raise HTTPException(400, "El teléfono es obligatorio para el transportista")

    from modules.gls import shipment_service

    # Check for duplicates unless forced
    if not data.skip_duplicate_check:
        existing = await shipment_service.check_duplicate_shipment(db, orden_id, "envio")
        if existing:
            raise HTTPException(409, f"Ya existe un envío activo para esta orden (código: {existing.get('gls_codbarras', 'N/A')}). Anúlalo primero o usa skip_duplicate_check=true.")

    # Build shipment data
    shipment_data = {
        "orden_id": orden_id,
        "entidad_tipo": "orden",
        "tipo": "envio",
        "cliente_id": orden.get("cliente_id", ""),
        "dest_nombre": data.dest_nombre,
        "dest_direccion": data.dest_direccion,
        "dest_poblacion": data.dest_poblacion,
        "dest_cp": data.dest_cp,
        "dest_provincia": data.dest_provincia,
        "dest_telefono": data.dest_telefono,
        "dest_email": data.dest_email,
        "dest_observaciones": data.dest_observaciones,
        "bultos": data.bultos,
        "peso": data.peso,
        "referencia": data.referencia or orden.get("numero_orden", "")[:20],
    }

    result = await shipment_service.create_shipment(
        db, shipment_data, user.get("email", ""),
        skip_duplicate_check=True,  # Already checked above
        notify_client=data.notify_client if hasattr(data, 'notify_client') else False
    )

    if not result["success"]:
        raise HTTPException(400, result.get("error", "Error al crear envío GLS"))

    shipment = result.get("shipment", {})
    codbarras = shipment.get("gls_codbarras", "")

    # Register event in order timeline
    await _registrar_evento_logistica(
        orden_id, "envio_creado",
        f"Envío GLS creado - Código: {codbarras}",
        user.get("email", "Sistema")
    )

    # Send email notification (async, don't block)
    asyncio.create_task(_enviar_email_logistica(orden_id, "envio", codbarras))

    return {"success": True, "shipment": shipment}


@router.post("/ordenes/{orden_id}/logistics/{shipment_id}/sync")
async def sync_envio_logistica(orden_id: str, shipment_id: str, user: dict = Depends(require_auth)):
    """Sincroniza el tracking de un envío específico."""
    # Verify shipment belongs to this order
    shipment = await db.gls_shipments.find_one(
        {"id": shipment_id, "entidad_id": orden_id},
        {"_id": 0, "id": 1, "tipo": 1, "estado_interno": 1}
    )
    if not shipment:
        raise HTTPException(404, "Envío no encontrado para esta orden")

    from modules.gls import shipment_service
    old_state = shipment.get("estado_interno", "")

    result = await shipment_service.get_tracking(db, shipment_id)

    if result.get("success"):
        # Check if state changed
        updated = await db.gls_shipments.find_one({"id": shipment_id}, {"_id": 0, "estado_interno": 1, "gls_codbarras": 1})
        new_state = updated.get("estado_interno", "")
        if new_state != old_state:
            tipo_label = "Recogida" if shipment.get("tipo") == "recogida" else "Envío"
            await _registrar_evento_logistica(
                orden_id, "estado_actualizado",
                f"{tipo_label} GLS actualizado: {old_state} → {new_state} (Código: {updated.get('gls_codbarras', '')})",
                "Sistema (sync)"
            )

    return {"success": result.get("success", False), "tracking": result}


@router.get("/ordenes/{orden_id}/logistics/{shipment_id}/label")
async def descargar_etiqueta_logistica(orden_id: str, shipment_id: str, user: dict = Depends(require_auth)):
    """Descarga la etiqueta de un envío específico de esta orden."""
    import base64
    from fastapi.responses import Response as FastAPIResponse

    shipment = await db.gls_shipments.find_one(
        {"id": shipment_id, "entidad_id": orden_id},
        {"_id": 0, "id": 1}
    )
    if not shipment:
        raise HTTPException(404, "Envío no encontrado para esta orden")

    from modules.gls import shipment_service
    result = await shipment_service.get_label(db, shipment_id)

    if not result.get("success") or not result.get("labels"):
        raise HTTPException(404, result.get("error", "Etiqueta no disponible"))

    label_b64 = result["labels"][0]
    label_bytes = base64.b64decode(label_b64)

    return FastAPIResponse(
        content=label_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="etiqueta_gls_{shipment_id[:8]}.pdf"'}
    )



DEVOLUCION_VALID_STATES = {"enviado", "entregado", "incidencia", "reparado"}


@router.post("/ordenes/{orden_id}/logistics/return")
async def crear_devolucion_logistica(orden_id: str, data: LogisticsCreateRequest, user: dict = Depends(require_auth)):
    """Genera una devolución GLS para la orden. El cliente envía de vuelta al taller."""
    if user.get("role") not in ("admin", "master"):
        raise HTTPException(403, "Solo administradores pueden generar devoluciones")

    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(404, "Orden no encontrada")

    # Validate order state
    estado = orden.get("estado", "")
    if estado not in DEVOLUCION_VALID_STATES and user.get("role") != "master":
        raise HTTPException(400, f"No se puede crear devolución en estado '{estado}'. Estados válidos: {', '.join(DEVOLUCION_VALID_STATES)}")

    # Validate address data
    if not data.dest_nombre or not data.dest_direccion or not data.dest_cp:
        raise HTTPException(400, "Datos de dirección incompletos: nombre, dirección y CP son obligatorios")

    if not data.dest_telefono:
        raise HTTPException(400, "El teléfono es obligatorio para el transportista")

    from modules.gls import shipment_service

    # Check for duplicates unless forced
    if not data.skip_duplicate_check:
        existing = await shipment_service.check_duplicate_shipment(db, orden_id, "devolucion")
        if existing:
            raise HTTPException(409, f"Ya existe una devolución activa para esta orden (código: {existing.get('gls_codbarras', 'N/A')}). Anúlala primero o usa skip_duplicate_check=true.")

    # Build shipment data - for devolucion, dest is the CLIENT (from where we pickup return)
    shipment_data = {
        "orden_id": orden_id,
        "entidad_tipo": "orden",
        "tipo": "devolucion",  # Will be handled specially in shipment_service
        "cliente_id": orden.get("cliente_id", ""),
        "dest_nombre": data.dest_nombre,
        "dest_direccion": data.dest_direccion,
        "dest_poblacion": data.dest_poblacion,
        "dest_cp": data.dest_cp,
        "dest_provincia": data.dest_provincia,
        "dest_telefono": data.dest_telefono,
        "dest_email": data.dest_email,
        "dest_observaciones": data.dest_observaciones or "DEVOLUCIÓN",
        "bultos": data.bultos,
        "peso": data.peso,
        "referencia": data.referencia or f"DEV-{orden.get('numero_orden', '')[:15]}",
    }

    result = await shipment_service.create_shipment(
        db, shipment_data, user.get("email", ""),
        skip_duplicate_check=True,
        notify_client=data.notify_client
    )

    if not result["success"]:
        raise HTTPException(400, result.get("error", "Error al crear devolución GLS"))

    shipment = result.get("shipment", {})
    codbarras = shipment.get("gls_codbarras", "")

    # Register event in order timeline
    await _registrar_evento_logistica(
        orden_id, "devolucion_creada",
        f"Devolución GLS creada - Código: {codbarras}",
        user.get("email", "Sistema")
    )

    # Send email notification (async, don't block)
    asyncio.create_task(_enviar_email_logistica(orden_id, "devolucion", codbarras))

    return {"success": True, "shipment": shipment}


@router.delete("/ordenes/{orden_id}/logistics/{shipment_id}")
async def anular_envio_logistica(
    orden_id: str, 
    shipment_id: str, 
    motivo: str = "", 
    user: dict = Depends(require_auth)
):
    """Anula un envío específico de esta orden."""
    if user.get("role") not in ("admin", "master"):
        raise HTTPException(403, "Solo administradores pueden anular envíos")

    shipment = await db.gls_shipments.find_one(
        {"id": shipment_id, "entidad_id": orden_id},
        {"_id": 0, "id": 1, "tipo": 1, "gls_codbarras": 1}
    )
    if not shipment:
        raise HTTPException(404, "Envío no encontrado para esta orden")

    from modules.gls import shipment_service
    result = await shipment_service.cancel_shipment(db, shipment_id, user.get("email", ""), motivo)

    if not result["success"]:
        raise HTTPException(400, result.get("error"))

    tipo_label = {"envio": "Envío", "recogida": "Recogida", "devolucion": "Devolución"}.get(shipment.get("tipo"), "Envío")
    await _registrar_evento_logistica(
        orden_id, "envio_anulado",
        f"{tipo_label} GLS anulado - Código: {shipment.get('gls_codbarras', 'N/A')}" + (f" - Motivo: {motivo}" if motivo else ""),
        user.get("email", "Sistema")
    )

    return {"success": True, "message": "Envío anulado"}

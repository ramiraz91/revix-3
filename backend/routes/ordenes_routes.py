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
    
    orden_obj = OrdenTrabajo(**orden.model_dump())
    orden_obj.qr_code = generate_barcode(orden_obj.numero_orden)
    orden_obj.historial_estados = [{"estado": OrderStatus.PENDIENTE_RECIBIR.value, "fecha": datetime.now(timezone.utc).isoformat(), "usuario": user.get('email', 'sistema')}]
    
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
        conditions.append({
            "$or": [
                {"numero_orden": {"$regex": search, "$options": "i"}},
                {"numero_autorizacion": {"$regex": search, "$options": "i"}},
                {"dispositivo.modelo": {"$regex": search, "$options": "i"}},
                {"dispositivo.imei": {"$regex": search, "$options": "i"}}
            ]
        })
    if fecha_desde:
        conditions.append({"created_at": {"$gte": fecha_desde}})
    if fecha_hasta:
        conditions.append({"created_at": {"$lte": fecha_hasta}})
    
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    
    # Paginación
    skip = (page - 1) * page_size
    
    # Count total (usar count_documents para eficiencia)
    total = await db.ordenes.count_documents(query)
    
    # Obtener datos con proyección optimizada
    ordenes = await db.ordenes.find(query, LISTADO_PROJECTION)\
        .sort("created_at", -1)\
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


@router.get("/ordenes", response_model=List[OrdenTrabajo])
async def listar_ordenes(estado: Optional[str] = None, cliente_id: Optional[str] = None, search: Optional[str] = None, telefono: Optional[str] = None, autorizacion: Optional[str] = None, fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None, solo_garantias: Optional[bool] = None):
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
    if fecha_desde:
        conditions.append({"created_at": {"$gte": fecha_desde}})
    if fecha_hasta:
        conditions.append({"created_at": {"$lte": fecha_hasta}})
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]

    ordenes = await db.ordenes.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)

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
    orden = await db.ordenes.find_one({"id": orden_ref}, {"_id": 0})
    if not orden:
        orden = await db.ordenes.find_one({"numero_orden": orden_ref}, {"_id": 0})
    if not orden:
        orden = await db.ordenes.find_one({"numero_autorizacion": orden_ref}, {"_id": 0})
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
        'recepcion_accesorios_registrados', 'recepcion_notas', 'bateria_reemplazada',
        'bateria_almacenamiento_temporal', 'bateria_residuo_pendiente',
        'bateria_gestor_autorizado', 'bateria_fecha_entrega_gestor',
        'ri_completada',  # El técnico puede marcar RI como completada
    ]

    # Campos de diagnóstico/QC exclusivos del técnico (admin/master solo lectura)
    # EXCEPCIÓN: Admin puede marcarlos como completados al finalizar una orden
    campos_diagnostico_qc_exclusivos_tecnico = [
        'diagnostico_tecnico',
        'notas_cierre_tecnico',
        'fecha_fin_reparacion',
        'recepcion_checklist_completo',
        'recepcion_estado_fisico_registrado',
        'recepcion_accesorios_registrados',
        'recepcion_notas',
    ]
    
    # Campos de QC que el admin PUEDE marcar como completados al finalizar
    campos_qc_finalizacion = [
        'diagnostico_salida_realizado',
        'funciones_verificadas',
        'limpieza_realizada',
    ]
    
    is_admin = user.get('role') in ['admin', 'master']
    if not is_admin:
        data = {k: v for k, v in data.items() if k in campos_tecnico_permitidos}
    else:
        # Admin puede marcar campos de QC como completados (pero no modificarlos a False)
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
                detail="Diagnóstico y control de calidad solo pueden ser actualizados por el técnico",
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
    "en_taller": ["reparado", "validacion", "re_presupuestar", "irreparable", "reemplazo", "cancelado"],  # técnico puede ir directo a validación
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
    # Master puede forzar transiciones a validacion y enviado desde cualquier estado
    if es_master and nuevo_estado in ["validacion", "enviado"]:
        return True, ""
    
    # Admin puede forzar ciertas transiciones
    if es_admin and nuevo_estado in ["cancelado", "re_presupuestar"]:
        return True, ""
    
    transiciones_permitidas = TRANSICIONES_VALIDAS.get(estado_actual, [])
    
    if nuevo_estado in transiciones_permitidas:
        return True, ""
    
    return False, f"Transición no válida: {estado_actual} → {nuevo_estado}. Transiciones permitidas: {transiciones_permitidas}"

# ==================== ESTADO Y ESCANEO ====================

@router.patch("/ordenes/{orden_id}/estado")
async def cambiar_estado_orden(orden_id: str, request: CambioEstadoRequest, user: dict = Depends(require_auth)):
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    estado_actual = orden.get('estado', 'pendiente_recibir')
    es_admin = user.get('role') in ['admin', 'master']
    es_master = user.get('role') == 'master'
    es_tecnico = user.get('role') == 'tecnico'

    # ─── Transiciones técnicas: solo técnico puede ejecutarlas ───
    # EXCEPCIÓN: Master puede forzar validacion y enviado desde cualquier estado
    ESTADOS_SOLO_TECNICO = {'en_taller', 'reparado', 'validacion', 'irreparable'}
    # Resolución de cuarentena (cuarentena → recibida) también es técnica
    es_resolucion_cuarentena = (estado_actual == 'cuarentena' and request.nuevo_estado.value == 'recibida')
    if request.nuevo_estado.value in ESTADOS_SOLO_TECNICO or es_resolucion_cuarentena:
        # Master puede forzar validacion y enviado sin ser técnico
        if es_master and request.nuevo_estado.value in {'validacion', 'enviado'}:
            pass  # Master permitido
        elif not es_tecnico:
            raise HTTPException(
                status_code=403,
                detail=f"La transición a '{request.nuevo_estado.value}' es una acción técnica. "
                       "Solo el rol 'técnico' puede ejecutarla."
            )

    # Validar transición de estado
    transicion_valida, error_msg = validar_transicion(estado_actual, request.nuevo_estado.value, es_admin, es_master)
    if not transicion_valida:
        raise HTTPException(status_code=400, detail=error_msg)
    
    if orden.get('bloqueada') and request.nuevo_estado not in [OrderStatus.RE_PRESUPUESTAR, OrderStatus.CANCELADO]:
        raise HTTPException(status_code=400, detail="La orden está bloqueada pendiente de aprobación de materiales")
    if request.nuevo_estado == OrderStatus.ENVIADO and not request.codigo_envio:
        raise HTTPException(status_code=400, detail="Se requiere código de envío para marcar como enviado")

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

    # Cuando el admin envía, el QC se marca automáticamente como completado
    # (el frontend lo hace antes de llamar a este endpoint)
    
    # Validar que todos los materiales estén validados antes de marcar como REPARADO
    # Admin puede forzar con forzar_sin_validacion=True
    if request.nuevo_estado == OrderStatus.REPARADO:
        materiales = orden.get('materiales', [])
        if materiales:
            materiales_sin_validar = [m for m in materiales if not m.get('validado_tecnico')]
            if materiales_sin_validar:
                # Solo permitir forzar si es admin/master
                puede_forzar = es_admin and request.forzar_sin_validacion
                if not puede_forzar:
                    nombres_pendientes = ", ".join([m.get('nombre', 'Material')[:30] for m in materiales_sin_validar[:3]])
                    if len(materiales_sin_validar) > 3:
                        nombres_pendientes += f" y {len(materiales_sin_validar) - 3} más"
                    raise HTTPException(
                        status_code=400, 
                        detail=f"No se puede marcar como REPARADO. Hay {len(materiales_sin_validar)} material(es) sin validar: {nombres_pendientes}. El técnico debe validar todos los materiales usados."
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
    
    historial.append({"estado": request.nuevo_estado.value, "fecha": now.isoformat(), "usuario": request.usuario + nota_forzado})
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
        updates={"estado": request.nuevo_estado.value, "codigo_envio": request.codigo_envio},
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
        cambios={"estado_anterior": estado_actual, "estado_nuevo": request.nuevo_estado.value}
    )
    
    if request.nuevo_estado == OrderStatus.REPARADO and request.usuario != "admin":
        notif = Notificacion(tipo="orden_reparada", mensaje=f"El técnico ha marcado la orden {orden['numero_orden']} como REPARADA. Lista para validación.", orden_id=orden_id)
        notif_doc = notif.model_dump()
        notif_doc['created_at'] = notif_doc['created_at'].isoformat()
        await db.notificaciones.insert_one(notif_doc)
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
    else:
        if not request.nombre:
            raise HTTPException(status_code=400, detail="Se requiere nombre para material personalizado")
        pendiente_precios = request.añadido_por_tecnico and (request.precio_unitario is None or request.coste is None)
        material = {"repuesto_id": None, "nombre": request.nombre, "cantidad": request.cantidad, "precio_unitario": request.precio_unitario or 0, "coste": request.coste or 0, "iva": request.iva or 21.0, "descuento": request.descuento or 0, "añadido_por_tecnico": request.añadido_por_tecnico, "aprobado": not request.añadido_por_tecnico, "pendiente_precios": pendiente_precios}
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
                link = f"{smtp_cfg.FRONTEND_URL}/web/consulta?codigo={token}"
                
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
    return {"message": "Materiales aprobados y orden desbloqueada"}

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
    
    # Crear notificación
    tipo_notif = "presupuesto_aceptado" if request.aceptado else "presupuesto_rechazado"
    mensaje_notif = f"Presupuesto {'ACEPTADO' if request.aceptado else 'RECHAZADO'} para orden {orden['numero_orden']}"
    if not request.aceptado and request.motivo_rechazo:
        mensaje_notif += f" - Motivo: {request.motivo_rechazo}"
    
    notif = Notificacion(tipo=tipo_notif, mensaje=mensaje_notif, orden_id=orden_id)
    notif_doc = notif.model_dump()
    notif_doc['created_at'] = notif_doc['created_at'].isoformat()
    await db.notificaciones.insert_one(notif_doc)
    
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


# ==================== DESCARGA ZIP DE FOTOS ====================

@router.get("/ordenes/{orden_id}/fotos-zip")
async def descargar_fotos_zip(orden_id: str, user: dict = Depends(require_auth)):
    """Descarga todas las fotos de una orden en un archivo ZIP (soporta Cloudinary y local)"""
    import zipfile
    import io
    import httpx
    from fastapi.responses import StreamingResponse
    
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # Recopilar todas las fotos
    todas_fotos = []
    
    # Evidencias del admin
    for foto in (orden.get('evidencias') or []):
        todas_fotos.append(("admin", foto))
    
    # Evidencias del técnico
    for foto in (orden.get('evidencias_tecnico') or []):
        todas_fotos.append(("tecnico", foto))
    
    # Fotos antes
    for foto in (orden.get('fotos_antes') or []):
        todas_fotos.append(("antes", foto))
    
    # Fotos después
    for foto in (orden.get('fotos_despues') or []):
        todas_fotos.append(("despues", foto))
    
    if not todas_fotos:
        raise HTTPException(status_code=404, detail="No hay fotos para descargar")
    
    # Crear ZIP en memoria
    zip_buffer = io.BytesIO()
    async with httpx.AsyncClient() as client:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for idx, (categoria, foto_ref) in enumerate(todas_fotos):
                try:
                    # Determinar si es URL de Cloudinary o archivo local
                    if foto_ref.startswith('http'):
                        # Es URL de Cloudinary - descargar
                        response = await client.get(foto_ref, timeout=30.0)
                        if response.status_code == 200:
                            # Extraer extensión de la URL
                            ext = foto_ref.split('.')[-1].split('?')[0] if '.' in foto_ref else 'jpg'
                            zip_filename = f"{categoria}_{idx+1}.{ext}"
                            zip_file.writestr(zip_filename, response.content)
                    else:
                        # Es archivo local
                        file_path = UPLOAD_DIR / foto_ref
                        if file_path.exists():
                            zip_filename = f"{categoria}_{foto_ref}"
                            zip_file.write(file_path, zip_filename)
                except Exception as e:
                    logger.error(f"Error descargando foto {foto_ref}: {e}")
                    continue
    
    zip_buffer.seek(0)
    
    numero_orden = orden.get('numero_orden', orden_id)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={numero_orden}_fotos.zip"
        }
    )


@router.get("/ordenes/{orden_id}/fotos-zip/{tipo}")
async def descargar_fotos_zip_por_tipo(orden_id: str, tipo: str, user: dict = Depends(require_auth)):
    """Descarga fotos de una orden filtradas por tipo: 'antes' o 'despues'."""
    import zipfile
    import io
    import httpx
    from fastapi.responses import StreamingResponse

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
    async with httpx.AsyncClient() as client:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for idx, foto_ref in enumerate(fotos):
                try:
                    if foto_ref.startswith('http'):
                        response = await client.get(foto_ref, timeout=30.0)
                        if response.status_code == 200:
                            ext = foto_ref.split('.')[-1].split('?')[0] if '.' in foto_ref else 'jpg'
                            zip_file.writestr(f"{tipo}_{idx+1}.{ext}", response.content)
                    else:
                        file_path = UPLOAD_DIR / foto_ref
                        if file_path.exists():
                            zip_file.write(file_path, f"{tipo}_{foto_ref}")
                except Exception as e:
                    logger.error(f"Error descargando foto {foto_ref}: {e}")

    zip_buffer.seek(0)
    numero_orden = orden.get('numero_orden', orden_id)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={numero_orden}_fotos_{tipo}.zip"}
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

@router.post("/ordenes/{orden_id}/crear-garantia")
async def crear_garantia_simple(orden_id: str, user: dict = Depends(require_admin)):
    """
    Crea una orden de garantía desde una orden enviada.
    También crea una incidencia de tipo 'garantia' vinculada al cliente.
    """
    orden_padre = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden_padre:
        raise HTTPException(status_code=404, detail="Orden padre no encontrada")
    
    if orden_padre.get('estado') != 'enviado':
        raise HTTPException(status_code=400, detail="Solo se pueden abrir garantías de órdenes enviadas")
    
    if orden_padre.get('es_garantia'):
        raise HTTPException(status_code=400, detail="Esta orden ya es una garantía")
    
    now = datetime.now(timezone.utc)
    
    # 1. Crear la nueva orden de garantía con toda la info del dispositivo
    nueva_orden = OrdenTrabajo(
        cliente_id=orden_padre['cliente_id'],
        dispositivo=orden_padre['dispositivo'],
        agencia_envio=orden_padre.get('agencia_envio', ''),
        codigo_recogida_entrada=orden_padre.get('codigo_recogida_entrada', ''),
        notas=f"GARANTÍA de orden {orden_padre['numero_orden']}. {orden_padre.get('notas', '')}".strip(),
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


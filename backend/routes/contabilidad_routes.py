"""
Módulo de Contabilidad - NEXORA CRM
Gestión de facturas, albaranes, abonos, pagos y reporting financiero.

Características:
- Facturas de venta (a clientes) y compra (de proveedores)
- Albaranes automáticos al cerrar órdenes de trabajo
- Control de IVA e inversión del sujeto pasivo
- Abonos y devoluciones
- Control de pagos pendientes
- Recordatorios automáticos
- Informes (IVA trimestral, beneficios, etc.)
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid

from config import db, logger
from auth import require_auth, require_admin, require_master

router = APIRouter(prefix="/contabilidad", tags=["Contabilidad"])

# ==================== ENUMS ====================

class TipoFactura(str, Enum):
    VENTA = "venta"
    COMPRA = "compra"

class TipoIVA(str, Enum):
    GENERAL = "general"  # 21%
    REDUCIDO = "reducido"  # 10%
    SUPERREDUCIDO = "superreducido"  # 4%
    EXENTO = "exento"  # 0% - Inversión sujeto pasivo
    
class EstadoFactura(str, Enum):
    BORRADOR = "borrador"
    EMITIDA = "emitida"
    PAGADA = "pagada"
    PARCIAL = "parcial"  # Pago parcial
    VENCIDA = "vencida"
    ANULADA = "anulada"

class EstadoPago(str, Enum):
    PENDIENTE = "pendiente"
    COMPLETADO = "completado"
    PARCIAL = "parcial"
    DEVUELTO = "devuelto"

class MetodoPago(str, Enum):
    EFECTIVO = "efectivo"
    TARJETA = "tarjeta"
    TRANSFERENCIA = "transferencia"
    BIZUM = "bizum"
    DOMICILIACION = "domiciliacion"
    PAGARE = "pagare"

# ==================== MODELS ====================

class LineaFactura(BaseModel):
    """Línea de factura"""
    descripcion: str
    cantidad: float = 1
    precio_unitario: float
    descuento: float = 0  # Porcentaje
    tipo_iva: TipoIVA = TipoIVA.GENERAL
    iva_porcentaje: float = 21.0
    # Referencias opcionales
    repuesto_id: Optional[str] = None
    orden_id: Optional[str] = None
    albaran_id: Optional[str] = None
    
    @property
    def subtotal(self) -> float:
        return round(self.cantidad * self.precio_unitario * (1 - self.descuento / 100), 2)
    
    @property
    def importe_iva(self) -> float:
        return round(self.subtotal * self.iva_porcentaje / 100, 2)
    
    @property
    def total(self) -> float:
        return round(self.subtotal + self.importe_iva, 2)

class FacturaCreate(BaseModel):
    """Crear factura"""
    tipo: TipoFactura
    # Cliente/Proveedor
    cliente_id: Optional[str] = None
    proveedor_id: Optional[str] = None
    # Datos fiscales
    nombre_fiscal: str
    nif_cif: str
    direccion_fiscal: Optional[str] = None
    # Contenido
    lineas: List[LineaFactura] = []
    notas: Optional[str] = None
    # Fechas y pago
    fecha_emision: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    metodo_pago: MetodoPago = MetodoPago.TRANSFERENCIA
    # IVA especial
    inversion_sujeto_pasivo: bool = False  # Para compras intracomunitarias

class FacturaUpdate(BaseModel):
    """Actualizar factura"""
    estado: Optional[EstadoFactura] = None
    lineas: Optional[List[LineaFactura]] = None
    notas: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    metodo_pago: Optional[MetodoPago] = None

class PagoCreate(BaseModel):
    """Registrar pago"""
    factura_id: str
    importe: float
    metodo: MetodoPago
    fecha: Optional[str] = None
    referencia: Optional[str] = None  # Nº transferencia, etc.
    notas: Optional[str] = None

class AbonoCreate(BaseModel):
    """Crear abono/devolución"""
    factura_id: str
    motivo: str
    lineas: List[LineaFactura] = []  # Líneas a abonar (cantidad negativa)
    devolucion_completa: bool = False

class AlbaranCreate(BaseModel):
    """Crear albarán"""
    orden_id: str
    cliente_id: str
    lineas: List[LineaFactura] = []
    notas: Optional[str] = None

# ==================== HELPER FUNCTIONS ====================

async def get_next_numero(tipo: str, año: int) -> str:
    """Genera el siguiente número de documento según serie"""
    # Formato: TIPO-AÑO-NUMERO (ej: FV-2026-00001, FC-2026-00001, ALB-2026-00001)
    prefijos = {
        "factura_venta": "FV",
        "factura_compra": "FC",
        "albaran": "ALB",
        "abono": "ABN"
    }
    prefijo = prefijos.get(tipo, "DOC")
    
    # Buscar último número del año
    ultimo = await db.contabilidad_series.find_one(
        {"tipo": tipo, "año": año},
        {"_id": 0}
    )
    
    if ultimo:
        siguiente = ultimo.get("ultimo_numero", 0) + 1
    else:
        siguiente = 1
    
    # Actualizar serie
    await db.contabilidad_series.update_one(
        {"tipo": tipo, "año": año},
        {"$set": {"ultimo_numero": siguiente, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    
    return f"{prefijo}-{año}-{siguiente:05d}"

async def calcular_totales_factura(lineas: List[dict]) -> dict:
    """Calcula totales de una factura"""
    base_imponible = 0
    total_iva = 0
    desglose_iva = {}
    
    for linea in lineas:
        cantidad = linea.get("cantidad", 1)
        precio = linea.get("precio_unitario", 0)
        descuento = linea.get("descuento", 0)
        iva_pct = linea.get("iva_porcentaje", 21)
        
        subtotal = round(cantidad * precio * (1 - descuento / 100), 2)
        iva = round(subtotal * iva_pct / 100, 2)
        
        base_imponible += subtotal
        total_iva += iva
        
        # Desglose por tipo de IVA
        iva_key = f"{iva_pct}%"
        if iva_key not in desglose_iva:
            desglose_iva[iva_key] = {"base": 0, "cuota": 0}
        desglose_iva[iva_key]["base"] += subtotal
        desglose_iva[iva_key]["cuota"] += iva
    
    return {
        "base_imponible": round(base_imponible, 2),
        "total_iva": round(total_iva, 2),
        "total": round(base_imponible + total_iva, 2),
        "desglose_iva": desglose_iva
    }

async def verificar_facturas_vencidas():
    """Marca facturas vencidas y genera alertas"""
    hoy = datetime.now(timezone.utc).date()
    
    # Buscar facturas emitidas con fecha vencimiento pasada
    cursor = db.facturas.find({
        "estado": {"$in": ["emitida", "parcial"]},
        "fecha_vencimiento": {"$lt": hoy.isoformat()}
    })
    
    async for factura in cursor:
        await db.facturas.update_one(
            {"id": factura["id"]},
            {"$set": {"estado": "vencida", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Crear notificación
        await db.notificaciones.insert_one({
            "id": str(uuid.uuid4()),
            "tipo": "factura_vencida",
            "mensaje": f"Factura {factura['numero']} vencida. Importe pendiente: {factura.get('pendiente_cobro', factura['total'])}€",
            "factura_id": factura["id"],
            "leida": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

# ==================== FACTURAS ====================

@router.post("/facturas")
async def crear_factura(factura: FacturaCreate, user: dict = Depends(require_admin)):
    """Crear nueva factura (venta o compra)"""
    año = datetime.now().year
    
    tipo_serie = f"factura_{factura.tipo.value}"
    numero = await get_next_numero(tipo_serie, año)
    
    # Calcular totales
    lineas_dict = [l.model_dump() for l in factura.lineas]
    totales = await calcular_totales_factura(lineas_dict)
    
    # Fecha emisión y vencimiento
    fecha_emision = factura.fecha_emision or datetime.now(timezone.utc).isoformat()
    if not factura.fecha_vencimiento:
        # Por defecto 30 días
        fecha_venc = datetime.now(timezone.utc) + timedelta(days=30)
        fecha_vencimiento = fecha_venc.isoformat()
    else:
        fecha_vencimiento = factura.fecha_vencimiento
    
    doc = {
        "id": str(uuid.uuid4()),
        "numero": numero,
        "tipo": factura.tipo.value,
        "estado": "borrador",
        # Entidad
        "cliente_id": factura.cliente_id,
        "proveedor_id": factura.proveedor_id,
        "nombre_fiscal": factura.nombre_fiscal,
        "nif_cif": factura.nif_cif,
        "direccion_fiscal": factura.direccion_fiscal,
        # Contenido
        "lineas": lineas_dict,
        "notas": factura.notas,
        # Totales
        **totales,
        # Fechas
        "fecha_emision": fecha_emision,
        "fecha_vencimiento": fecha_vencimiento,
        "año_fiscal": año,
        # Pago
        "metodo_pago": factura.metodo_pago.value,
        "inversion_sujeto_pasivo": factura.inversion_sujeto_pasivo,
        "pagos": [],
        "total_pagado": 0,
        "pendiente_cobro": totales["total"],
        # Metadata
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.facturas.insert_one(doc)
    doc.pop("_id", None)
    
    logger.info(f"Factura {numero} creada por {user.get('email')}")
    return doc

@router.get("/facturas")
async def listar_facturas(
    tipo: Optional[str] = None,
    estado: Optional[str] = None,
    cliente_id: Optional[str] = None,
    proveedor_id: Optional[str] = None,
    año: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
    user: dict = Depends(require_auth)
):
    """Listar facturas con filtros"""
    query = {}
    
    if tipo:
        query["tipo"] = tipo
    if estado:
        query["estado"] = estado
    if cliente_id:
        query["cliente_id"] = cliente_id
    if proveedor_id:
        query["proveedor_id"] = proveedor_id
    if año:
        query["año_fiscal"] = año
    
    total = await db.facturas.count_documents(query)
    skip = (page - 1) * page_size
    
    facturas = await db.facturas.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size).to_list(page_size)
    
    return {
        "items": facturas,
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.get("/facturas/{factura_id}")
async def obtener_factura(factura_id: str, user: dict = Depends(require_auth)):
    """Obtener detalle de factura"""
    factura = await db.facturas.find_one({"id": factura_id}, {"_id": 0})
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    # Enriquecer con datos del cliente/proveedor
    if factura.get("cliente_id"):
        cliente = await db.clientes.find_one({"id": factura["cliente_id"]}, {"_id": 0, "nombre": 1, "apellidos": 1, "email": 1, "telefono": 1})
        factura["cliente"] = cliente
    
    if factura.get("proveedor_id"):
        proveedor = await db.proveedores.find_one({"id": factura["proveedor_id"]}, {"_id": 0, "nombre": 1, "email": 1, "telefono": 1})
        factura["proveedor"] = proveedor
    
    return factura

@router.patch("/facturas/{factura_id}")
async def actualizar_factura(factura_id: str, data: FacturaUpdate, user: dict = Depends(require_admin)):
    """Actualizar factura"""
    factura = await db.facturas.find_one({"id": factura_id}, {"_id": 0})
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    # No permitir editar facturas pagadas o anuladas
    if factura["estado"] in ["pagada", "anulada"]:
        raise HTTPException(status_code=400, detail=f"No se puede editar una factura {factura['estado']}")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if data.estado:
        update_data["estado"] = data.estado.value
    if data.lineas is not None:
        lineas_dict = [l.model_dump() for l in data.lineas]
        totales = await calcular_totales_factura(lineas_dict)
        update_data["lineas"] = lineas_dict
        update_data.update(totales)
        update_data["pendiente_cobro"] = totales["total"] - factura.get("total_pagado", 0)
    if data.notas is not None:
        update_data["notas"] = data.notas
    if data.fecha_vencimiento:
        update_data["fecha_vencimiento"] = data.fecha_vencimiento
    if data.metodo_pago:
        update_data["metodo_pago"] = data.metodo_pago.value
    
    await db.facturas.update_one({"id": factura_id}, {"$set": update_data})
    
    return {"message": "Factura actualizada"}

@router.post("/facturas/{factura_id}/emitir")
async def emitir_factura(factura_id: str, user: dict = Depends(require_admin)):
    """Emitir factura (cambiar de borrador a emitida)"""
    factura = await db.facturas.find_one({"id": factura_id}, {"_id": 0})
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    if factura["estado"] != "borrador":
        raise HTTPException(status_code=400, detail="Solo se pueden emitir facturas en borrador")
    
    if not factura.get("lineas"):
        raise HTTPException(status_code=400, detail="La factura debe tener al menos una línea")
    
    await db.facturas.update_one(
        {"id": factura_id},
        {"$set": {
            "estado": "emitida",
            "fecha_emision": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Factura emitida", "numero": factura["numero"]}

@router.post("/facturas/{factura_id}/anular")
async def anular_factura(factura_id: str, motivo: str, user: dict = Depends(require_master)):
    """Anular factura (solo master)"""
    factura = await db.facturas.find_one({"id": factura_id}, {"_id": 0})
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    if factura["estado"] == "anulada":
        raise HTTPException(status_code=400, detail="La factura ya está anulada")
    
    await db.facturas.update_one(
        {"id": factura_id},
        {"$set": {
            "estado": "anulada",
            "motivo_anulacion": motivo,
            "anulada_por": user.get("email"),
            "fecha_anulacion": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    logger.info(f"Factura {factura['numero']} anulada por {user.get('email')}: {motivo}")
    return {"message": "Factura anulada"}

# ==================== PAGOS ====================

@router.post("/pagos")
async def registrar_pago(pago: PagoCreate, user: dict = Depends(require_admin)):
    """Registrar pago de factura"""
    factura = await db.facturas.find_one({"id": pago.factura_id}, {"_id": 0})
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    if factura["estado"] in ["pagada", "anulada"]:
        raise HTTPException(status_code=400, detail=f"No se puede registrar pago en factura {factura['estado']}")
    
    pendiente = factura.get("pendiente_cobro", factura["total"])
    if pago.importe > pendiente:
        raise HTTPException(status_code=400, detail=f"El importe ({pago.importe}€) supera el pendiente ({pendiente}€)")
    
    pago_doc = {
        "id": str(uuid.uuid4()),
        "importe": pago.importe,
        "metodo": pago.metodo.value,
        "fecha": pago.fecha or datetime.now(timezone.utc).isoformat(),
        "referencia": pago.referencia,
        "notas": pago.notas,
        "registrado_por": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    nuevo_total_pagado = factura.get("total_pagado", 0) + pago.importe
    nuevo_pendiente = factura["total"] - nuevo_total_pagado
    
    # Determinar nuevo estado
    if nuevo_pendiente <= 0:
        nuevo_estado = "pagada"
    elif nuevo_total_pagado > 0:
        nuevo_estado = "parcial"
    else:
        nuevo_estado = factura["estado"]
    
    await db.facturas.update_one(
        {"id": pago.factura_id},
        {
            "$push": {"pagos": pago_doc},
            "$set": {
                "total_pagado": nuevo_total_pagado,
                "pendiente_cobro": nuevo_pendiente,
                "estado": nuevo_estado,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    logger.info(f"Pago de {pago.importe}€ registrado en factura {factura['numero']} por {user.get('email')}")
    return {"message": "Pago registrado", "nuevo_pendiente": nuevo_pendiente, "estado": nuevo_estado}

@router.get("/pagos")
async def listar_pagos(
    factura_id: Optional[str] = None,
    metodo: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    user: dict = Depends(require_auth)
):
    """Listar pagos registrados"""
    # Los pagos están embebidos en las facturas, hacer agregación
    pipeline = [
        {"$unwind": "$pagos"},
        {"$project": {
            "_id": 0,
            "factura_id": "$id",
            "factura_numero": "$numero",
            "tipo_factura": "$tipo",
            "cliente_id": "$cliente_id",
            "proveedor_id": "$proveedor_id",
            "nombre_fiscal": "$nombre_fiscal",
            "pago": "$pagos"
        }}
    ]
    
    # Filtros
    match_stage = {}
    if factura_id:
        match_stage["id"] = factura_id
    
    if match_stage:
        pipeline.insert(0, {"$match": match_stage})
    
    pagos = await db.facturas.aggregate(pipeline).to_list(500)
    
    # Aplanar estructura
    resultado = []
    for p in pagos:
        pago = p["pago"]
        pago["factura_id"] = p["factura_id"]
        pago["factura_numero"] = p["factura_numero"]
        pago["tipo_factura"] = p["tipo_factura"]
        pago["nombre_fiscal"] = p["nombre_fiscal"]
        resultado.append(pago)
    
    # Filtros post-agregación
    if metodo:
        resultado = [p for p in resultado if p.get("metodo") == metodo]
    if desde:
        resultado = [p for p in resultado if p.get("fecha", "") >= desde]
    if hasta:
        resultado = [p for p in resultado if p.get("fecha", "") <= hasta]
    
    return resultado

# ==================== ABONOS ====================

@router.post("/abonos")
async def crear_abono(abono: AbonoCreate, user: dict = Depends(require_admin)):
    """Crear abono/nota de crédito"""
    factura = await db.facturas.find_one({"id": abono.factura_id}, {"_id": 0})
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    if factura["estado"] not in ["emitida", "pagada", "parcial"]:
        raise HTTPException(status_code=400, detail="Solo se pueden abonar facturas emitidas o pagadas")
    
    año = datetime.now().year
    numero = await get_next_numero("abono", año)
    
    # Si es devolución completa, copiar todas las líneas con signo negativo
    if abono.devolucion_completa:
        lineas = []
        for linea in factura.get("lineas", []):
            linea_abono = linea.copy()
            linea_abono["cantidad"] = -abs(linea_abono.get("cantidad", 1))
            lineas.append(linea_abono)
    else:
        lineas = [l.model_dump() for l in abono.lineas]
    
    totales = await calcular_totales_factura(lineas)
    
    doc = {
        "id": str(uuid.uuid4()),
        "numero": numero,
        "tipo": "abono",
        "factura_origen_id": abono.factura_id,
        "factura_origen_numero": factura["numero"],
        "estado": "emitida",
        # Copiar datos fiscales de la factura original
        "cliente_id": factura.get("cliente_id"),
        "proveedor_id": factura.get("proveedor_id"),
        "nombre_fiscal": factura["nombre_fiscal"],
        "nif_cif": factura["nif_cif"],
        "direccion_fiscal": factura.get("direccion_fiscal"),
        # Contenido
        "lineas": lineas,
        "motivo": abono.motivo,
        "devolucion_completa": abono.devolucion_completa,
        # Totales (negativos)
        **totales,
        # Fechas
        "fecha_emision": datetime.now(timezone.utc).isoformat(),
        "año_fiscal": año,
        # Metadata
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.abonos.insert_one(doc)
    
    # Vincular abono a la factura original
    await db.facturas.update_one(
        {"id": abono.factura_id},
        {
            "$push": {"abonos_vinculados": {"id": doc["id"], "numero": numero}},
            "$set": {"tiene_abonos": True, "updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    doc.pop("_id", None)
    logger.info(f"Abono {numero} creado para factura {factura['numero']} por {user.get('email')}")
    return doc

@router.get("/abonos")
async def listar_abonos(
    factura_id: Optional[str] = None,
    año: Optional[int] = None,
    user: dict = Depends(require_auth)
):
    """Listar abonos"""
    query = {}
    if factura_id:
        query["factura_origen_id"] = factura_id
    if año:
        query["año_fiscal"] = año
    
    abonos = await db.abonos.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return abonos

# ==================== ALBARANES ====================

@router.post("/albaranes")
async def crear_albaran(albaran: AlbaranCreate, user: dict = Depends(require_admin)):
    """Crear albarán manualmente"""
    orden = await db.ordenes.find_one({"id": albaran.orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    cliente = await db.clientes.find_one({"id": albaran.cliente_id}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    año = datetime.now().year
    numero = await get_next_numero("albaran", año)
    
    # Si no hay líneas, crear desde los materiales de la orden
    if not albaran.lineas:
        lineas = []
        for mat in orden.get("materiales", []):
            lineas.append({
                "descripcion": mat.get("nombre", "Material"),
                "cantidad": mat.get("cantidad", 1),
                "precio_unitario": mat.get("precio_unitario", 0),
                "descuento": mat.get("descuento", 0),
                "tipo_iva": "general",
                "iva_porcentaje": mat.get("iva", 21),
                "repuesto_id": mat.get("repuesto_id"),
                "orden_id": albaran.orden_id
            })
    else:
        lineas = [l.model_dump() for l in albaran.lineas]
    
    totales = await calcular_totales_factura(lineas)
    
    doc = {
        "id": str(uuid.uuid4()),
        "numero": numero,
        "orden_id": albaran.orden_id,
        "numero_orden": orden.get("numero_orden"),
        "cliente_id": albaran.cliente_id,
        "nombre_cliente": f"{cliente.get('nombre', '')} {cliente.get('apellidos', '')}".strip(),
        "lineas": lineas,
        **totales,
        "notas": albaran.notas,
        "estado": "emitido",
        "facturado": False,
        "factura_id": None,
        "fecha_emision": datetime.now(timezone.utc).isoformat(),
        "año_fiscal": año,
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.albaranes.insert_one(doc)
    
    # Vincular a la orden
    await db.ordenes.update_one(
        {"id": albaran.orden_id},
        {"$set": {"albaran_id": doc["id"], "albaran_numero": numero, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    doc.pop("_id", None)
    logger.info(f"Albarán {numero} creado para orden {orden.get('numero_orden')} por {user.get('email')}")
    return doc

@router.post("/albaranes/desde-orden/{orden_id}")
async def crear_albaran_desde_orden(orden_id: str, user: dict = Depends(require_admin)):
    """Crear albarán automáticamente desde una orden cerrada"""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # Verificar que la orden esté en estado válido
    estados_validos = ["reparado", "enviado", "garantia", "validacion"]
    if orden.get("estado") not in estados_validos:
        raise HTTPException(status_code=400, detail=f"La orden debe estar en estado {estados_validos}")
    
    # Verificar si ya tiene albarán
    if orden.get("albaran_id"):
        raise HTTPException(status_code=400, detail="Esta orden ya tiene un albarán asociado")
    
    cliente_id = orden.get("cliente_id")
    if not cliente_id:
        raise HTTPException(status_code=400, detail="La orden no tiene cliente asociado")
    
    cliente = await db.clientes.find_one({"id": cliente_id}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    año = datetime.now().year
    numero = await get_next_numero("albaran", año)
    
    # Crear líneas desde materiales de la orden
    lineas = []
    for mat in orden.get("materiales", []):
        if not mat.get("aprobado", True):  # Solo materiales aprobados
            continue
        lineas.append({
            "descripcion": mat.get("nombre", "Material"),
            "cantidad": mat.get("cantidad", 1),
            "precio_unitario": mat.get("precio_unitario", 0),
            "descuento": mat.get("descuento", 0),
            "tipo_iva": "general",
            "iva_porcentaje": mat.get("iva", 21),
            "repuesto_id": mat.get("repuesto_id"),
            "orden_id": orden_id
        })
    
    # Añadir mano de obra si existe
    if orden.get("mano_obra", 0) > 0:
        lineas.append({
            "descripcion": "Mano de obra",
            "cantidad": 1,
            "precio_unitario": orden.get("mano_obra", 0),
            "descuento": 0,
            "tipo_iva": "general",
            "iva_porcentaje": 21,
            "orden_id": orden_id
        })
    
    totales = await calcular_totales_factura(lineas)
    
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
        **totales,
        "notas": f"Reparación: {orden.get('descripcion_averia', '')}",
        "estado": "emitido",
        "facturado": False,
        "factura_id": None,
        # Para autofacturas (cuando paga un tercero como aseguradora)
        "pagador_tercero": orden.get("es_seguro", False),
        "pagador_nombre": orden.get("aseguradora_nombre") if orden.get("es_seguro") else None,
        "pagador_nif": orden.get("aseguradora_nif") if orden.get("es_seguro") else None,
        "fecha_emision": datetime.now(timezone.utc).isoformat(),
        "año_fiscal": año,
        "created_by": user.get("email"),
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
    
    doc.pop("_id", None)
    logger.info(f"Albarán {numero} creado automáticamente para orden {orden.get('numero_orden')}")
    return doc

@router.get("/albaranes")
async def listar_albaranes(
    cliente_id: Optional[str] = None,
    facturado: Optional[bool] = None,
    año: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
    user: dict = Depends(require_auth)
):
    """Listar albaranes"""
    query = {}
    if cliente_id:
        query["cliente_id"] = cliente_id
    if facturado is not None:
        query["facturado"] = facturado
    if año:
        query["año_fiscal"] = año
    
    total = await db.albaranes.count_documents(query)
    skip = (page - 1) * page_size
    
    albaranes = await db.albaranes.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size).to_list(page_size)
    
    return {
        "items": albaranes,
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.get("/albaranes/{albaran_id}")
async def obtener_albaran(albaran_id: str, user: dict = Depends(require_auth)):
    """Obtener detalle de albarán"""
    albaran = await db.albaranes.find_one({"id": albaran_id}, {"_id": 0})
    if not albaran:
        raise HTTPException(status_code=404, detail="Albarán no encontrado")
    return albaran

@router.post("/albaranes/{albaran_id}/facturar")
async def facturar_albaran(albaran_id: str, user: dict = Depends(require_admin)):
    """Crear factura desde albarán"""
    albaran = await db.albaranes.find_one({"id": albaran_id}, {"_id": 0})
    if not albaran:
        raise HTTPException(status_code=404, detail="Albarán no encontrado")
    
    if albaran.get("facturado"):
        raise HTTPException(status_code=400, detail="Este albarán ya está facturado")
    
    cliente = await db.clientes.find_one({"id": albaran["cliente_id"]}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    año = datetime.now().year
    numero = await get_next_numero("factura_venta", año)
    
    # Usar líneas del albarán
    lineas = albaran.get("lineas", [])
    for linea in lineas:
        linea["albaran_id"] = albaran_id
    
    totales = await calcular_totales_factura(lineas)
    
    doc = {
        "id": str(uuid.uuid4()),
        "numero": numero,
        "tipo": "venta",
        "estado": "emitida",
        "cliente_id": albaran["cliente_id"],
        "nombre_fiscal": cliente.get("nombre_fiscal") or f"{cliente.get('nombre', '')} {cliente.get('apellidos', '')}".strip(),
        "nif_cif": cliente.get("dni") or cliente.get("nif") or "",
        "direccion_fiscal": cliente.get("direccion"),
        "lineas": lineas,
        **totales,
        "notas": f"Factura generada desde albarán {albaran['numero']}",
        "albaran_id": albaran_id,
        "albaran_numero": albaran["numero"],
        "orden_id": albaran.get("orden_id"),
        "fecha_emision": datetime.now(timezone.utc).isoformat(),
        "fecha_vencimiento": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "año_fiscal": año,
        "metodo_pago": "transferencia",
        "pagos": [],
        "total_pagado": 0,
        "pendiente_cobro": totales["total"],
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.facturas.insert_one(doc)
    
    # Marcar albarán como facturado
    await db.albaranes.update_one(
        {"id": albaran_id},
        {"$set": {"facturado": True, "factura_id": doc["id"], "factura_numero": numero}}
    )
    
    doc.pop("_id", None)
    logger.info(f"Factura {numero} creada desde albarán {albaran['numero']}")
    return doc

# ==================== INFORMES ====================

@router.get("/informes/resumen")
async def resumen_contabilidad(
    año: Optional[int] = None,
    trimestre: Optional[int] = None,
    user: dict = Depends(require_admin)
):
    """Resumen general de contabilidad"""
    año = año or datetime.now().year
    
    query_base = {"año_fiscal": año}
    if trimestre:
        meses = {1: [1, 2, 3], 2: [4, 5, 6], 3: [7, 8, 9], 4: [10, 11, 12]}
        # TODO: Filtrar por meses del trimestre
    
    # Facturas de venta
    ventas = await db.facturas.find(
        {**query_base, "tipo": "venta", "estado": {"$ne": "anulada"}},
        {"_id": 0, "total": 1, "base_imponible": 1, "total_iva": 1, "estado": 1, "pendiente_cobro": 1}
    ).to_list(10000)
    
    total_ventas = sum(f.get("total", 0) for f in ventas)
    base_ventas = sum(f.get("base_imponible", 0) for f in ventas)
    iva_repercutido = sum(f.get("total_iva", 0) for f in ventas)
    pendiente_cobro = sum(f.get("pendiente_cobro", 0) for f in ventas if f.get("estado") != "pagada")
    
    # Facturas de compra
    compras = await db.facturas.find(
        {**query_base, "tipo": "compra", "estado": {"$ne": "anulada"}},
        {"_id": 0, "total": 1, "base_imponible": 1, "total_iva": 1, "estado": 1, "pendiente_cobro": 1, "inversion_sujeto_pasivo": 1}
    ).to_list(10000)
    
    total_compras = sum(f.get("total", 0) for f in compras)
    base_compras = sum(f.get("base_imponible", 0) for f in compras)
    iva_soportado = sum(f.get("total_iva", 0) for f in compras if not f.get("inversion_sujeto_pasivo"))
    pendiente_pago = sum(f.get("pendiente_cobro", 0) for f in compras if f.get("estado") != "pagada")
    
    # Abonos
    abonos = await db.abonos.find(
        {"año_fiscal": año},
        {"_id": 0, "total": 1}
    ).to_list(1000)
    total_abonos = sum(abs(a.get("total", 0)) for a in abonos)
    
    return {
        "año": año,
        "trimestre": trimestre,
        "ventas": {
            "total": round(total_ventas, 2),
            "base_imponible": round(base_ventas, 2),
            "iva_repercutido": round(iva_repercutido, 2),
            "num_facturas": len(ventas),
            "pendiente_cobro": round(pendiente_cobro, 2)
        },
        "compras": {
            "total": round(total_compras, 2),
            "base_imponible": round(base_compras, 2),
            "iva_soportado": round(iva_soportado, 2),
            "num_facturas": len(compras),
            "pendiente_pago": round(pendiente_pago, 2)
        },
        "abonos": {
            "total": round(total_abonos, 2),
            "num_abonos": len(abonos)
        },
        "liquidacion_iva": {
            "iva_repercutido": round(iva_repercutido, 2),
            "iva_soportado": round(iva_soportado, 2),
            "resultado": round(iva_repercutido - iva_soportado, 2)  # Positivo = a pagar, negativo = a compensar
        },
        "beneficio_bruto": round(base_ventas - base_compras - total_abonos, 2)
    }

@router.get("/informes/iva-trimestral")
async def informe_iva_trimestral(
    año: int,
    trimestre: int,
    user: dict = Depends(require_admin)
):
    """Informe de IVA para modelo 303"""
    if trimestre not in [1, 2, 3, 4]:
        raise HTTPException(status_code=400, detail="Trimestre debe ser 1, 2, 3 o 4")
    
    meses = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
    mes_inicio, mes_fin = meses[trimestre]
    
    fecha_inicio = f"{año}-{mes_inicio:02d}-01"
    fecha_fin = f"{año}-{mes_fin:02d}-31"
    
    # Facturas emitidas (ventas)
    ventas = await db.facturas.find({
        "tipo": "venta",
        "estado": {"$ne": "anulada"},
        "fecha_emision": {"$gte": fecha_inicio, "$lte": fecha_fin}
    }, {"_id": 0}).to_list(10000)
    
    # Facturas recibidas (compras)
    compras = await db.facturas.find({
        "tipo": "compra",
        "estado": {"$ne": "anulada"},
        "fecha_emision": {"$gte": fecha_inicio, "$lte": fecha_fin}
    }, {"_id": 0}).to_list(10000)
    
    # Desglose por tipo de IVA
    iva_repercutido = {"21%": {"base": 0, "cuota": 0}, "10%": {"base": 0, "cuota": 0}, "4%": {"base": 0, "cuota": 0}}
    iva_soportado = {"21%": {"base": 0, "cuota": 0}, "10%": {"base": 0, "cuota": 0}, "4%": {"base": 0, "cuota": 0}}
    
    for f in ventas:
        desglose = f.get("desglose_iva", {})
        for tipo, datos in desglose.items():
            if tipo in iva_repercutido:
                iva_repercutido[tipo]["base"] += datos.get("base", 0)
                iva_repercutido[tipo]["cuota"] += datos.get("cuota", 0)
    
    for f in compras:
        if f.get("inversion_sujeto_pasivo"):
            continue  # No cuenta para IVA soportado
        desglose = f.get("desglose_iva", {})
        for tipo, datos in desglose.items():
            if tipo in iva_soportado:
                iva_soportado[tipo]["base"] += datos.get("base", 0)
                iva_soportado[tipo]["cuota"] += datos.get("cuota", 0)
    
    total_repercutido = sum(d["cuota"] for d in iva_repercutido.values())
    total_soportado = sum(d["cuota"] for d in iva_soportado.values())
    
    return {
        "año": año,
        "trimestre": trimestre,
        "periodo": f"{fecha_inicio} - {fecha_fin}",
        "iva_devengado": {
            "regimen_general": iva_repercutido,
            "total": round(total_repercutido, 2)
        },
        "iva_deducible": {
            "operaciones_interiores": iva_soportado,
            "total": round(total_soportado, 2)
        },
        "diferencia": round(total_repercutido - total_soportado, 2),
        "resultado": "a_ingresar" if total_repercutido > total_soportado else "a_compensar"
    }

@router.get("/informes/pendientes")
async def informe_pendientes(user: dict = Depends(require_admin)):
    """Facturas pendientes de cobro/pago"""
    # Pendientes de cobro (ventas)
    cobros = await db.facturas.find(
        {"tipo": "venta", "estado": {"$in": ["emitida", "parcial", "vencida"]}},
        {"_id": 0, "id": 1, "numero": 1, "nombre_fiscal": 1, "total": 1, "pendiente_cobro": 1, "fecha_vencimiento": 1, "estado": 1}
    ).sort("fecha_vencimiento", 1).to_list(500)
    
    # Pendientes de pago (compras)
    pagos = await db.facturas.find(
        {"tipo": "compra", "estado": {"$in": ["emitida", "parcial", "vencida"]}},
        {"_id": 0, "id": 1, "numero": 1, "nombre_fiscal": 1, "total": 1, "pendiente_cobro": 1, "fecha_vencimiento": 1, "estado": 1}
    ).sort("fecha_vencimiento", 1).to_list(500)
    
    total_cobros = sum(f.get("pendiente_cobro", 0) for f in cobros)
    total_pagos = sum(f.get("pendiente_cobro", 0) for f in pagos)
    
    return {
        "pendiente_cobro": {
            "facturas": cobros,
            "total": round(total_cobros, 2),
            "num_facturas": len(cobros)
        },
        "pendiente_pago": {
            "facturas": pagos,
            "total": round(total_pagos, 2),
            "num_facturas": len(pagos)
        },
        "balance": round(total_cobros - total_pagos, 2)
    }

# ==================== RECORDATORIOS ====================

@router.post("/recordatorios/enviar/{factura_id}")
async def enviar_recordatorio(factura_id: str, user: dict = Depends(require_admin)):
    """Enviar recordatorio de pago por email"""
    factura = await db.facturas.find_one({"id": factura_id}, {"_id": 0})
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    if factura["estado"] in ["pagada", "anulada"]:
        raise HTTPException(status_code=400, detail="Esta factura no requiere recordatorio")
    
    # Registrar recordatorio enviado
    recordatorio = {
        "id": str(uuid.uuid4()),
        "fecha": datetime.now(timezone.utc).isoformat(),
        "enviado_por": user.get("email"),
        "metodo": "email"
    }
    
    await db.facturas.update_one(
        {"id": factura_id},
        {
            "$push": {"recordatorios": recordatorio},
            "$set": {"ultimo_recordatorio": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    # TODO: Integrar con servicio de email
    logger.info(f"Recordatorio de pago enviado para factura {factura['numero']}")
    
    return {"message": "Recordatorio registrado", "factura": factura["numero"]}

# ==================== STATS ====================

@router.get("/stats")
async def estadisticas_contabilidad(user: dict = Depends(require_auth)):
    """Estadísticas generales de contabilidad"""
    año_actual = datetime.now().year
    
    # Contadores
    facturas_venta = await db.facturas.count_documents({"tipo": "venta", "año_fiscal": año_actual})
    facturas_compra = await db.facturas.count_documents({"tipo": "compra", "año_fiscal": año_actual})
    albaranes = await db.albaranes.count_documents({"año_fiscal": año_actual})
    albaranes_sin_facturar = await db.albaranes.count_documents({"año_fiscal": año_actual, "facturado": False})
    abonos = await db.abonos.count_documents({"año_fiscal": año_actual})
    
    # Pendientes
    pendiente_cobro = await db.facturas.aggregate([
        {"$match": {"tipo": "venta", "estado": {"$in": ["emitida", "parcial", "vencida"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$pendiente_cobro"}}}
    ]).to_list(1)
    
    pendiente_pago = await db.facturas.aggregate([
        {"$match": {"tipo": "compra", "estado": {"$in": ["emitida", "parcial", "vencida"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$pendiente_cobro"}}}
    ]).to_list(1)
    
    return {
        "año": año_actual,
        "facturas_venta": facturas_venta,
        "facturas_compra": facturas_compra,
        "albaranes": albaranes,
        "albaranes_sin_facturar": albaranes_sin_facturar,
        "abonos": abonos,
        "pendiente_cobro": round(pendiente_cobro[0]["total"], 2) if pendiente_cobro else 0,
        "pendiente_pago": round(pendiente_pago[0]["total"], 2) if pendiente_pago else 0
    }

# ==================== MODELO 347 ====================

@router.get("/informes/modelo-347")
async def informe_modelo_347(
    año: int,
    user: dict = Depends(require_admin)
):
    """
    Modelo 347 - Declaración anual de operaciones con terceros
    Obligatorio declarar operaciones > 3.005,06€ anuales con un mismo cliente/proveedor
    """
    try:
        LIMITE_347 = 3005.06
        
        # Obtener todas las facturas del año
        facturas = await db.facturas.find(
            {"año_fiscal": año, "estado": {"$ne": "anulada"}},
            {"_id": 0, "tipo": 1, "nombre_fiscal": 1, "nif_cif": 1, "total": 1, "base_imponible": 1, "cliente_id": 1, "proveedor_id": 1}
        ).to_list(50000)
        
        # Agrupar por NIF/CIF
        operaciones = {}
        for f in facturas:
            nif = f.get("nif_cif", "").upper().strip()
            if not nif:
                continue
                
            if nif not in operaciones:
                operaciones[nif] = {
                    "nif_cif": nif,
                    "nombre_fiscal": f.get("nombre_fiscal", ""),
                    "ventas": 0.0,
                    "compras": 0.0,
                    "total": 0.0,
                    "num_facturas": 0
                }
            
            if f.get("tipo") == "venta":
                operaciones[nif]["ventas"] += float(f.get("total", 0) or 0)
            else:
                operaciones[nif]["compras"] += float(f.get("total", 0) or 0)
            
            operaciones[nif]["total"] += float(f.get("total", 0) or 0)
            operaciones[nif]["num_facturas"] += 1
        
        # Filtrar operaciones > 3.005,06€
        declarables = [
            op for op in operaciones.values()
            if op["total"] >= LIMITE_347
        ]
        
        # Ordenar por importe total
        declarables.sort(key=lambda x: x["total"], reverse=True)
        
        # Calcular totales
        total_ventas_declarables = sum(op["ventas"] for op in declarables)
        total_compras_declarables = sum(op["compras"] for op in declarables)
        
        return {
            "año": año,
            "limite_declaracion": LIMITE_347,
            "operaciones_declarables": declarables,
            "resumen": {
                "num_terceros": len(declarables),
                "total_ventas": round(total_ventas_declarables, 2),
                "total_compras": round(total_compras_declarables, 2),
                "total_operaciones": round(total_ventas_declarables + total_compras_declarables, 2)
            },
            "operaciones_no_declarables": len(operaciones) - len(declarables)
        }
    except Exception as e:
        logger.error(f"Error en modelo 347: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== RECORDATORIOS AUTOMÁTICOS ====================

@router.get("/recordatorios/vencidas")
async def obtener_facturas_vencidas(user: dict = Depends(require_admin)):
    """Obtener facturas vencidas pendientes de recordatorio"""
    hoy = datetime.now(timezone.utc).date().isoformat()
    
    facturas = await db.facturas.find({
        "estado": {"$in": ["emitida", "parcial", "vencida"]},
        "fecha_vencimiento": {"$lt": hoy}
    }, {"_id": 0}).sort("fecha_vencimiento", 1).to_list(500)
    
    # Calcular días de retraso
    for f in facturas:
        fecha_venc = datetime.fromisoformat(f["fecha_vencimiento"].replace("Z", "+00:00")).date()
        hoy_date = datetime.now(timezone.utc).date()
        f["dias_retraso"] = (hoy_date - fecha_venc).days
        f["ultimo_recordatorio_dias"] = None
        if f.get("ultimo_recordatorio"):
            ultimo = datetime.fromisoformat(f["ultimo_recordatorio"].replace("Z", "+00:00")).date()
            f["ultimo_recordatorio_dias"] = (hoy_date - ultimo).days
    
    return facturas

@router.post("/recordatorios/verificar-vencidas")
async def verificar_y_marcar_vencidas(background_tasks: BackgroundTasks, user: dict = Depends(require_admin)):
    """Verificar facturas vencidas y marcar estado"""
    hoy = datetime.now(timezone.utc).date().isoformat()
    
    # Buscar facturas emitidas con fecha vencimiento pasada
    result = await db.facturas.update_many(
        {
            "estado": {"$in": ["emitida", "parcial"]},
            "fecha_vencimiento": {"$lt": hoy}
        },
        {
            "$set": {
                "estado": "vencida",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Crear notificaciones para las vencidas
    if result.modified_count > 0:
        facturas_vencidas = await db.facturas.find(
            {"estado": "vencida", "notificacion_vencimiento_enviada": {"$ne": True}},
            {"_id": 0, "id": 1, "numero": 1, "nombre_fiscal": 1, "pendiente_cobro": 1}
        ).to_list(100)
        
        for f in facturas_vencidas:
            await db.notificaciones.insert_one({
                "id": str(uuid.uuid4()),
                "tipo": "factura_vencida",
                "mensaje": f"⚠️ Factura {f['numero']} vencida - {f['nombre_fiscal']} - Pendiente: {f['pendiente_cobro']}€",
                "factura_id": f["id"],
                "leida": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            await db.facturas.update_one(
                {"id": f["id"]},
                {"$set": {"notificacion_vencimiento_enviada": True}}
            )
    
    return {
        "message": f"{result.modified_count} facturas marcadas como vencidas",
        "facturas_actualizadas": result.modified_count
    }

@router.post("/recordatorios/enviar-masivo")
async def enviar_recordatorios_masivos(
    dias_minimo_retraso: int = 7,
    dias_desde_ultimo: int = 7,
    user: dict = Depends(require_admin)
):
    """Enviar recordatorios masivos a facturas vencidas"""
    hoy = datetime.now(timezone.utc)
    hoy_date = hoy.date()
    fecha_limite = (hoy_date - timedelta(days=dias_minimo_retraso)).isoformat()
    
    facturas = await db.facturas.find({
        "estado": {"$in": ["emitida", "parcial", "vencida"]},
        "fecha_vencimiento": {"$lt": fecha_limite}
    }, {"_id": 0}).to_list(500)
    
    enviados = 0
    for f in facturas:
        # Verificar si ya se envió recordatorio recientemente
        if f.get("ultimo_recordatorio"):
            ultimo = datetime.fromisoformat(f["ultimo_recordatorio"].replace("Z", "+00:00")).date()
            if (hoy_date - ultimo).days < dias_desde_ultimo:
                continue
        
        # Registrar recordatorio
        recordatorio = {
            "id": str(uuid.uuid4()),
            "fecha": hoy.isoformat(),
            "enviado_por": user.get("email"),
            "metodo": "email",
            "automatico": True
        }
        
        await db.facturas.update_one(
            {"id": f["id"]},
            {
                "$push": {"recordatorios": recordatorio},
                "$set": {"ultimo_recordatorio": hoy.isoformat()}
            }
        )
        enviados += 1
        
        logger.info(f"Recordatorio enviado: Factura {f['numero']} - {f['nombre_fiscal']}")
    
    return {
        "message": f"{enviados} recordatorios enviados",
        "facturas_notificadas": enviados
    }

# ==================== CONFIGURACIÓN RECORDATORIOS ====================

@router.get("/recordatorios/config")
async def obtener_config_recordatorios(user: dict = Depends(require_admin)):
    """Obtener configuración de recordatorios automáticos"""
    config = await db.configuracion.find_one({"tipo": "recordatorios_facturas"}, {"_id": 0})
    
    if not config:
        config = {
            "tipo": "recordatorios_facturas",
            "activo": False,
            "dias_antes_vencimiento": 3,
            "dias_despues_vencimiento": [7, 14, 30],
            "enviar_email": True,
            "enviar_notificacion": True
        }
        await db.configuracion.insert_one({**config})
        # Re-fetch without _id
        config = await db.configuracion.find_one({"tipo": "recordatorios_facturas"}, {"_id": 0})
    
    return config

@router.post("/recordatorios/config")
async def guardar_config_recordatorios(config: dict, user: dict = Depends(require_master)):
    """Guardar configuración de recordatorios automáticos"""
    await db.configuracion.update_one(
        {"tipo": "recordatorios_facturas"},
        {"$set": {
            **config,
            "tipo": "recordatorios_facturas",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user.get("email")
        }},
        upsert=True
    )
    return {"message": "Configuración guardada"}

"""
Módulo de Compras - Gestión de facturas de proveedores
- Upload de facturas PDF
- Extracción automática con IA (Gemini)
- Confirmación antes de aplicar cambios
- Trazabilidad por lote
- Integración con inventario y proveedores
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid
import os
import base64
from config import db, logger, UPLOAD_DIR, EMERGENT_LLM_KEY

router = APIRouter(prefix="/compras", tags=["compras"])

# Dependencias de autenticación
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from auth import require_auth, require_admin


# ==================== MODELOS ====================

class ProductoFactura(BaseModel):
    linea: int
    descripcion: str
    codigo_referencia: Optional[str] = None
    ean: Optional[str] = None  # Código EAN / código de barras
    cantidad: int = 1
    precio_unitario: float = 0
    precio_total: float = 0
    iva: float = 21
    repuesto_id: Optional[str] = None  # Si coincide con inventario existente
    accion_sugerida: str = "crear"  # "crear", "añadir_stock", "ignorar"
    stock_actual: Optional[int] = None  # Si existe en inventario


class FacturaExtraida(BaseModel):
    proveedor_nombre: Optional[str] = None
    proveedor_cif: Optional[str] = None
    proveedor_id: Optional[str] = None  # Si coincide con proveedor existente
    numero_factura: Optional[str] = None
    fecha_factura: Optional[str] = None
    base_imponible: float = 0
    total_iva: float = 0
    total_factura: float = 0
    productos: List[ProductoFactura] = []
    confianza_extraccion: float = 0  # 0-100%
    notas_extraccion: Optional[str] = None


class CompraCreate(BaseModel):
    proveedor_id: str
    numero_factura: str
    fecha_factura: str
    productos: List[dict]  # Lista de productos confirmados
    base_imponible: float
    total_iva: float
    total_factura: float
    notas: Optional[str] = None
    archivo_factura: Optional[str] = None  # Ruta del archivo


class LoteCompra(BaseModel):
    id: str
    codigo_lote: str  # TRZ-2026-0312-001
    compra_id: str
    repuesto_id: str
    cantidad: int
    precio_unitario: float
    fecha_compra: str
    proveedor_id: str
    proveedor_nombre: str
    numero_factura: str
    unidades_disponibles: int
    created_at: str


# ==================== UTILIDADES ====================

def safe_float(value, default=0.0) -> float:
    """Convierte un valor a float de forma segura, devolviendo default si falla"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=1) -> int:
    """Convierte un valor a int de forma segura, devolviendo default si falla"""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def generar_codigo_lote() -> str:
    """Genera código de trazabilidad único: TRZ-AAAA-MMDD-NNN"""
    ahora = datetime.now(timezone.utc)
    fecha_str = ahora.strftime("%Y-%m%d")
    
    # Obtener secuencial del día (esto debería ser atómico en producción)
    # Por simplicidad, usamos timestamp
    seq = ahora.strftime("%H%M%S")[-3:]
    
    return f"TRZ-{fecha_str}-{seq}"


async def extraer_datos_factura_ia(pdf_content: bytes, filename: str) -> FacturaExtraida:
    """Usa Gemini para extraer datos de la factura PDF"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
        import tempfile
        
        prompt = """Analiza esta factura de compra de un proveedor de repuestos de móviles/electrónica.

Extrae la siguiente información en formato JSON:
{
    "proveedor_nombre": "nombre del proveedor",
    "proveedor_cif": "CIF/NIF del proveedor",
    "numero_factura": "número de factura",
    "fecha_factura": "YYYY-MM-DD",
    "base_imponible": número,
    "total_iva": número,
    "total_factura": número,
    "productos": [
        {
            "linea": 1,
            "descripcion": "descripción del producto",
            "codigo_referencia": "código SKU o referencia del proveedor si existe",
            "ean": "código EAN, código de barras, GTIN o UPC si existe (suele ser numérico de 8-13 dígitos)",
            "cantidad": número,
            "precio_unitario": número (sin IVA),
            "precio_total": número (sin IVA),
            "iva": porcentaje de IVA
        }
    ],
    "confianza_extraccion": número del 0 al 100 indicando confianza en la extracción,
    "notas_extraccion": "cualquier nota o advertencia sobre la extracción"
}

IMPORTANTE sobre códigos de producto:
- "codigo_referencia": es el código SKU o referencia interna del proveedor (puede ser alfanumérico, ej: "REP-1234", "MS-LCD-IP14")
- "ean": es el código de barras EAN/GTIN (normalmente numérico de 8-13 dígitos, ej: "8435607600123") o referencia de fabricante (ej: "661-56050")
- Si la factura muestra columnas como "Ref.", "Código", "SKU", "Part Number" → va en codigo_referencia
- Si la factura muestra "EAN", "Código de barras", "GTIN", "UPC" → va en ean
- Si solo hay un código y parece numérico de 8-13 dígitos, ponlo en ean
- Si solo hay un código alfanumérico corto, ponlo en codigo_referencia

Si no puedes leer algún dato, déjalo como null. Los precios deben ser números sin símbolos de moneda.
Responde SOLO con el JSON, sin texto adicional."""

        # Guardar PDF temporalmente para poder pasarlo como FileContentWithMimeType
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(pdf_content)
            tmp_path = tmp_file.name
        
        try:
            # Crear instancia de chat con Gemini
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"compras-{uuid.uuid4()}",
                system_message="Eres un experto en análisis de facturas. Extrae datos con precisión."
            ).with_model("gemini", "gemini-2.5-flash")
            
            # Crear archivo adjunto
            pdf_file = FileContentWithMimeType(
                file_path=tmp_path,
                mime_type="application/pdf"
            )
            
            # Crear mensaje con archivo adjunto
            user_message = UserMessage(
                text=prompt,
                file_contents=[pdf_file]
            )
            
            # Enviar mensaje y obtener respuesta
            response = await chat.send_message(user_message)
        finally:
            # Limpiar archivo temporal
            import os as temp_os
            try:
                temp_os.unlink(tmp_path)
            except:
                pass
        
        # Parsear respuesta JSON
        import json
        # Limpiar respuesta de posibles marcadores de código
        response_text = response.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        data = json.loads(response_text.strip())
        
        # Convertir a modelo
        productos = []
        for i, p in enumerate(data.get("productos", [])):
            productos.append(ProductoFactura(
                linea=p.get("linea", i + 1) if p.get("linea") is not None else i + 1,
                descripcion=p.get("descripcion") or "",
                codigo_referencia=p.get("codigo_referencia"),
                ean=p.get("ean"),
                cantidad=safe_int(p.get("cantidad"), 1),
                precio_unitario=safe_float(p.get("precio_unitario"), 0),
                precio_total=safe_float(p.get("precio_total"), 0),
                iva=safe_float(p.get("iva"), 21)
            ))
        
        return FacturaExtraida(
            proveedor_nombre=data.get("proveedor_nombre"),
            proveedor_cif=data.get("proveedor_cif"),
            numero_factura=data.get("numero_factura"),
            fecha_factura=data.get("fecha_factura"),
            base_imponible=safe_float(data.get("base_imponible"), 0),
            total_iva=safe_float(data.get("total_iva"), 0),
            total_factura=safe_float(data.get("total_factura"), 0),
            productos=productos,
            confianza_extraccion=safe_float(data.get("confianza_extraccion"), 50),
            notas_extraccion=data.get("notas_extraccion")
        )
        
    except Exception as e:
        logger.error(f"Error extrayendo datos de factura: {e}")
        return FacturaExtraida(
            confianza_extraccion=0,
            notas_extraccion=f"Error en extracción automática: {str(e)}"
        )


async def buscar_coincidencias_inventario(productos: List[ProductoFactura]) -> List[ProductoFactura]:
    """Busca productos en inventario que coincidan con los de la factura"""
    productos_actualizados = []
    
    for producto in productos:
        query = {"$or": []}
        
        if producto.codigo_referencia:
            query["$or"].append({"sku_proveedor": {"$regex": producto.codigo_referencia, "$options": "i"}})
            query["$or"].append({"codigo_barras": producto.codigo_referencia})
            query["$or"].append({"sku": {"$regex": producto.codigo_referencia, "$options": "i"}})
        
        if producto.ean:
            query["$or"].append({"ean": producto.ean})
            query["$or"].append({"codigo_barras": producto.ean})
        
        if producto.descripcion:
            palabras = producto.descripcion.split()[:3]
            for palabra in palabras:
                if len(palabra) > 3:
                    query["$or"].append({"nombre": {"$regex": palabra, "$options": "i"}})
        
        if query["$or"]:
            repuesto = await db.repuestos.find_one(query, {"_id": 0})
            if repuesto:
                producto.repuesto_id = repuesto.get("id")
                producto.stock_actual = repuesto.get("stock", 0)
                producto.accion_sugerida = "añadir_stock"
            else:
                producto.accion_sugerida = "crear"
        else:
            producto.accion_sugerida = "crear"
        
        productos_actualizados.append(producto)
    
    return productos_actualizados


async def buscar_proveedor_existente(nombre: str, cif: str) -> Optional[dict]:
    """Busca si el proveedor ya existe en la base de datos"""
    query = {"$or": []}
    
    if cif:
        query["$or"].append({"cif": cif})
        query["$or"].append({"nif": cif})
    
    if nombre:
        query["$or"].append({"nombre": {"$regex": nombre, "$options": "i"}})
    
    if query["$or"]:
        return await db.proveedores.find_one(query, {"_id": 0})
    
    return None


# ==================== ENDPOINTS ====================

@router.post("/analizar-factura")
async def analizar_factura(
    archivo: UploadFile = File(...),
    user: dict = Depends(require_admin)
):
    """
    Sube una factura PDF y extrae los datos automáticamente con IA.
    Devuelve los datos extraídos para revisión antes de confirmar.
    """
    if not archivo.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")
    
    # Leer contenido del archivo
    contenido = await archivo.read()
    
    # Guardar archivo temporalmente
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"factura_{timestamp}_{archivo.filename}"
    filepath = os.path.join(UPLOAD_DIR, "facturas", filename)
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, "wb") as f:
        f.write(contenido)
    
    # Extraer datos con IA
    datos_extraidos = await extraer_datos_factura_ia(contenido, archivo.filename)
    
    # Buscar coincidencias en inventario
    if datos_extraidos.productos:
        datos_extraidos.productos = await buscar_coincidencias_inventario(datos_extraidos.productos)
    
    # Buscar proveedor existente
    if datos_extraidos.proveedor_nombre or datos_extraidos.proveedor_cif:
        proveedor = await buscar_proveedor_existente(
            datos_extraidos.proveedor_nombre,
            datos_extraidos.proveedor_cif
        )
        if proveedor:
            datos_extraidos.proveedor_id = proveedor.get("id")
    
    return {
        "archivo_guardado": filename,
        "ruta_archivo": filepath,
        "datos_extraidos": datos_extraidos.model_dump(),
        "mensaje": "Revisa los datos extraídos y confirma para registrar la compra"
    }


@router.post("/confirmar")
async def confirmar_compra(
    compra: CompraCreate,
    user: dict = Depends(require_admin)
):
    """
    Confirma una compra después de revisar los datos extraídos.
    Actualiza el inventario y genera códigos de trazabilidad.
    """
    # Validar proveedor
    proveedor = await db.proveedores.find_one({"id": compra.proveedor_id}, {"_id": 0})
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    # Crear registro de compra
    compra_id = str(uuid.uuid4())
    ahora = datetime.now(timezone.utc)
    
    compra_doc = {
        "id": compra_id,
        "proveedor_id": compra.proveedor_id,
        "proveedor_nombre": proveedor.get("nombre"),
        "numero_factura": compra.numero_factura,
        "fecha_factura": compra.fecha_factura,
        "base_imponible": compra.base_imponible,
        "total_iva": compra.total_iva,
        "total_factura": compra.total_factura,
        "archivo_factura": compra.archivo_factura,
        "notas": compra.notas,
        "productos": [],
        "lotes_generados": [],
        "created_at": ahora.isoformat(),
        "created_by": user.get("id")
    }
    
    lotes_creados = []
    productos_actualizados = []
    productos_creados = []
    
    for producto in compra.productos:
        accion = producto.get("accion", "crear")
        repuesto_id = producto.get("repuesto_id")
        
        if accion == "ignorar":
            continue
        
        # Generar código de lote
        codigo_lote = generar_codigo_lote()
        
        if accion == "añadir_stock" and repuesto_id:
            # Actualizar stock existente
            cantidad = safe_int(producto.get("cantidad"), 1)
            
            update_fields = {
                "precio_compra": safe_float(producto.get("precio_unitario"), 0),
                "ultimo_proveedor_id": compra.proveedor_id,
                "ultima_compra": ahora.isoformat(),
                "updated_at": ahora.isoformat()
            }
            
            # Si la factura trae EAN o referencia, actualizar en el repuesto
            ean_factura = producto.get("ean")
            ref_factura = producto.get("codigo_referencia")
            if ean_factura:
                update_fields["ean"] = ean_factura
                update_fields["codigo_barras"] = ean_factura
            if ref_factura:
                update_fields["sku_proveedor"] = ref_factura
            
            await db.repuestos.update_one(
                {"id": repuesto_id},
                {
                    "$inc": {"stock": cantidad},
                    "$set": update_fields
                }
            )
            
            productos_actualizados.append({
                "repuesto_id": repuesto_id,
                "cantidad_añadida": cantidad,
                "codigo_lote": codigo_lote
            })
            
        elif accion == "crear":
            # Crear nuevo producto en inventario
            nuevo_repuesto_id = str(uuid.uuid4())
            
            # Generar SKU corto
            categoria = "Otros"
            prefijo = "REP"
            count = await db.repuestos.count_documents({})
            sku = f"{prefijo}-{count + 1:04d}"
            
            ean_factura = producto.get("ean")
            ref_factura = producto.get("codigo_referencia")
            precio_unitario = safe_float(producto.get("precio_unitario"), 0)
            
            nuevo_repuesto = {
                "id": nuevo_repuesto_id,
                "nombre": producto.get("descripcion") or "Sin nombre",
                "categoria": categoria,
                "sku": sku,
                "sku_proveedor": ref_factura or "",
                "ean": ean_factura or None,
                "codigo_barras": ean_factura or ref_factura or "",
                "precio_compra": precio_unitario,
                "precio_venta": round(precio_unitario * 1.5, 2),
                "stock": safe_int(producto.get("cantidad"), 1),
                "stock_minimo": 5,
                "proveedor_id": compra.proveedor_id,
                "ultimo_proveedor_id": compra.proveedor_id,
                "ultima_compra": ahora.isoformat(),
                "created_at": ahora.isoformat(),
                "updated_at": ahora.isoformat()
            }
            
            await db.repuestos.insert_one(nuevo_repuesto)
            repuesto_id = nuevo_repuesto_id
            
            productos_creados.append({
                "repuesto_id": nuevo_repuesto_id,
                "nombre": nuevo_repuesto["nombre"],
                "sku": sku,
                "cantidad": producto.get("cantidad", 1),
                "codigo_lote": codigo_lote
            })
        
        # Crear registro de lote para trazabilidad
        lote_doc = {
            "id": str(uuid.uuid4()),
            "codigo_lote": codigo_lote,
            "compra_id": compra_id,
            "repuesto_id": repuesto_id,
            "cantidad_original": producto.get("cantidad", 1),
            "unidades_disponibles": producto.get("cantidad", 1),
            "precio_unitario": producto.get("precio_unitario", 0),
            "fecha_compra": compra.fecha_factura,
            "proveedor_id": compra.proveedor_id,
            "proveedor_nombre": proveedor.get("nombre"),
            "numero_factura": compra.numero_factura,
            "created_at": ahora.isoformat()
        }
        
        await db.lotes_compra.insert_one(lote_doc)
        lotes_creados.append(lote_doc)
        
        compra_doc["productos"].append({
            **producto,
            "repuesto_id": repuesto_id,
            "codigo_lote": codigo_lote
        })
        compra_doc["lotes_generados"].append(codigo_lote)
    
    # Guardar compra
    await db.compras.insert_one(compra_doc)
    
    return {
        "success": True,
        "compra_id": compra_id,
        "mensaje": "Compra registrada correctamente",
        "resumen": {
            "productos_actualizados": len(productos_actualizados),
            "productos_creados": len(productos_creados),
            "lotes_generados": len(lotes_creados)
        },
        "productos_actualizados": productos_actualizados,
        "productos_creados": productos_creados,
        "lotes": [lote["codigo_lote"] for lote in lotes_creados]
    }


@router.get("")
@router.get("/")
async def listar_compras(
    page: int = 1,
    page_size: int = 20,
    proveedor_id: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Lista todas las compras con filtros opcionales"""
    query = {}
    
    if proveedor_id:
        query["proveedor_id"] = proveedor_id
    
    if fecha_desde:
        query["fecha_factura"] = {"$gte": fecha_desde}
    
    if fecha_hasta:
        if "fecha_factura" in query:
            query["fecha_factura"]["$lte"] = fecha_hasta
        else:
            query["fecha_factura"] = {"$lte": fecha_hasta}
    
    total = await db.compras.count_documents(query)
    
    compras = await db.compras.find(query, {"_id": 0}).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size).to_list(page_size)
    
    return {
        "items": compras,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/{compra_id}")
async def obtener_compra(compra_id: str, user: dict = Depends(require_admin)):
    """Obtiene el detalle de una compra específica"""
    compra = await db.compras.find_one({"id": compra_id}, {"_id": 0})
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    
    # Obtener lotes asociados
    lotes = await db.lotes_compra.find({"compra_id": compra_id}, {"_id": 0}).to_list(100)
    
    return {
        **compra,
        "lotes": lotes
    }


@router.get("/lote/{codigo_lote}")
async def obtener_lote(codigo_lote: str, user: dict = Depends(require_admin)):
    """Obtiene información de un lote específico por su código de trazabilidad"""
    lote = await db.lotes_compra.find_one({"codigo_lote": codigo_lote}, {"_id": 0})
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    
    # Obtener información del repuesto
    repuesto = await db.repuestos.find_one({"id": lote.get("repuesto_id")}, {"_id": 0})
    
    # Obtener órdenes donde se usó este lote
    ordenes_uso = await db.ordenes.find(
        {"materiales.codigo_lote": codigo_lote},
        {"_id": 0, "id": 1, "numero_orden": 1, "cliente_nombre": 1, "created_at": 1}
    ).to_list(100)
    
    return {
        "lote": lote,
        "repuesto": repuesto,
        "uso_en_ordenes": ordenes_uso
    }


@router.get("/trazabilidad/repuesto/{repuesto_id}")
async def trazabilidad_repuesto(repuesto_id: str, user: dict = Depends(require_admin)):
    """Obtiene todos los lotes de un repuesto para trazabilidad completa"""
    lotes = await db.lotes_compra.find(
        {"repuesto_id": repuesto_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Estadísticas
    total_comprado = sum(lote.get("cantidad_original", 0) for lote in lotes)
    total_disponible = sum(lote.get("unidades_disponibles", 0) for lote in lotes)
    total_usado = total_comprado - total_disponible
    
    # Proveedores únicos
    proveedores = list(set(lote.get("proveedor_nombre") for lote in lotes if lote.get("proveedor_nombre")))
    
    # Historial de precios
    historial_precios = [
        {
            "fecha": lote.get("fecha_compra"),
            "precio": lote.get("precio_unitario"),
            "proveedor": lote.get("proveedor_nombre"),
            "factura": lote.get("numero_factura")
        }
        for lote in lotes
    ]
    
    return {
        "repuesto_id": repuesto_id,
        "lotes": lotes,
        "estadisticas": {
            "total_comprado": total_comprado,
            "total_disponible": total_disponible,
            "total_usado": total_usado,
            "num_lotes": len(lotes),
            "proveedores": proveedores
        },
        "historial_precios": historial_precios
    }


@router.get("/dashboard/resumen")
async def dashboard_compras(
    periodo: str = "mes",
    user: dict = Depends(require_admin)
):
    """Dashboard de compras con métricas y estadísticas"""
    from datetime import timedelta
    
    ahora = datetime.now(timezone.utc)
    
    if periodo == "semana":
        inicio = ahora - timedelta(days=7)
    elif periodo == "mes":
        inicio = ahora.replace(day=1)
    elif periodo == "trimestre":
        trimestre_mes = ((ahora.month - 1) // 3) * 3 + 1
        inicio = ahora.replace(month=trimestre_mes, day=1)
    else:
        inicio = ahora.replace(month=1, day=1)
    
    inicio_str = inicio.strftime("%Y-%m-%d")
    
    # Total compras del período
    compras = await db.compras.find(
        {"fecha_factura": {"$gte": inicio_str}},
        {"_id": 0}
    ).to_list(1000)
    
    total_compras = len(compras)
    total_gastado = sum(c.get("total_factura", 0) for c in compras)
    total_productos = sum(len(c.get("productos", [])) for c in compras)
    
    # Gasto por proveedor
    gasto_por_proveedor = {}
    for c in compras:
        prov = c.get("proveedor_nombre", "Desconocido")
        gasto_por_proveedor[prov] = gasto_por_proveedor.get(prov, 0) + c.get("total_factura", 0)
    
    # Top proveedores
    top_proveedores = sorted(
        [{"nombre": k, "total": v} for k, v in gasto_por_proveedor.items()],
        key=lambda x: x["total"],
        reverse=True
    )[:5]
    
    # Productos más comprados
    productos_count = {}
    for c in compras:
        for p in c.get("productos", []):
            nombre = p.get("descripcion", "Sin nombre")
            productos_count[nombre] = productos_count.get(nombre, 0) + p.get("cantidad", 1)
    
    productos_top = sorted(
        [{"nombre": k, "cantidad": v} for k, v in productos_count.items()],
        key=lambda x: x["cantidad"],
        reverse=True
    )[:10]
    
    # Alertas de stock bajo
    stock_bajo = await db.repuestos.find(
        {"$expr": {"$lte": ["$stock", "$stock_minimo"]}},
        {"_id": 0, "id": 1, "nombre": 1, "sku": 1, "stock": 1, "stock_minimo": 1}
    ).to_list(20)
    
    return {
        "periodo": periodo,
        "fecha_inicio": inicio_str,
        "resumen": {
            "total_compras": total_compras,
            "total_gastado": round(total_gastado, 2),
            "total_productos": total_productos,
            "promedio_por_compra": round(total_gastado / total_compras, 2) if total_compras > 0 else 0
        },
        "top_proveedores": top_proveedores,
        "productos_mas_comprados": productos_top,
        "alertas_stock_bajo": stock_bajo
    }

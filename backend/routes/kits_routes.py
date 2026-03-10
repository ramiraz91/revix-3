"""
Módulo de Artículos Compuestos / Kits
Permite crear combinaciones de productos y servicios que se añaden como múltiples líneas.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime, timezone
import uuid

from config import db, logger
from auth import require_auth, require_admin

router = APIRouter(prefix="/kits", tags=["Artículos Compuestos"])

# ==================== MODELS ====================

class ComponenteKit(BaseModel):
    """Componente de un kit/artículo compuesto"""
    tipo: Literal["producto", "servicio", "mano_obra", "logistica", "otro"]
    # Si es producto, referencia al repuesto
    repuesto_id: Optional[str] = None
    repuesto_nombre: Optional[str] = None
    # Descripción del componente (obligatoria para servicios)
    descripcion: str
    # Cantidad y precio
    cantidad: float = 1
    precio_unitario: float = 0
    # IVA
    iva_porcentaje: float = 21
    # Descuento opcional
    descuento: float = 0
    # Si el precio es fijo o se hereda del producto
    precio_fijo: bool = True
    # Orden de aparición
    orden: int = 0

class KitCreate(BaseModel):
    """Crear un nuevo kit/artículo compuesto"""
    nombre: str
    descripcion: Optional[str] = None
    # Producto principal asociado (opcional)
    producto_principal_id: Optional[str] = None
    producto_principal_nombre: Optional[str] = None
    # Categoría del kit
    categoria: Optional[str] = None
    # Componentes del kit
    componentes: List[ComponenteKit] = []
    # Estado
    activo: bool = True
    # Tags para búsqueda
    tags: List[str] = []

class KitUpdate(BaseModel):
    """Actualizar kit"""
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    componentes: Optional[List[ComponenteKit]] = None
    activo: Optional[bool] = None
    tags: Optional[List[str]] = None

# ==================== HELPER FUNCTIONS ====================

async def calcular_totales_kit(componentes: List[dict]) -> dict:
    """Calcula totales de un kit"""
    subtotal = 0
    total_iva = 0
    
    for comp in componentes:
        cantidad = comp.get("cantidad", 1)
        precio = comp.get("precio_unitario", 0)
        descuento = comp.get("descuento", 0)
        iva_pct = comp.get("iva_porcentaje", 21)
        
        linea_subtotal = cantidad * precio * (1 - descuento / 100)
        linea_iva = linea_subtotal * iva_pct / 100
        
        subtotal += linea_subtotal
        total_iva += linea_iva
    
    return {
        "subtotal": round(subtotal, 2),
        "total_iva": round(total_iva, 2),
        "total": round(subtotal + total_iva, 2),
        "num_componentes": len(componentes)
    }

async def expandir_kit_a_lineas(kit: dict, cantidad_kit: int = 1) -> List[dict]:
    """
    Expande un kit a sus líneas individuales.
    Útil para añadir a órdenes o facturas.
    """
    lineas = []
    
    for comp in kit.get("componentes", []):
        # Si el precio no es fijo y hay repuesto, obtener precio actual
        precio = comp.get("precio_unitario", 0)
        
        if not comp.get("precio_fijo") and comp.get("repuesto_id"):
            repuesto = await db.repuestos.find_one(
                {"id": comp["repuesto_id"]},
                {"_id": 0, "precio_venta": 1}
            )
            if repuesto:
                precio = repuesto.get("precio_venta", precio)
        
        linea = {
            "tipo": comp.get("tipo", "producto"),
            "descripcion": comp.get("descripcion", ""),
            "repuesto_id": comp.get("repuesto_id"),
            "cantidad": comp.get("cantidad", 1) * cantidad_kit,
            "precio_unitario": precio,
            "descuento": comp.get("descuento", 0),
            "iva_porcentaje": comp.get("iva_porcentaje", 21),
            "kit_origen_id": kit.get("id"),
            "kit_origen_nombre": kit.get("nombre")
        }
        lineas.append(linea)
    
    return lineas

# ==================== ESTADÍSTICAS ====================

@router.get("/stats")
async def estadisticas_kits(user: dict = Depends(require_auth)):
    """Estadísticas de kits"""
    total = await db.kits.count_documents({})
    activos = await db.kits.count_documents({"activo": True})
    
    return {
        "total_kits": total,
        "kits_activos": activos,
        "kits_inactivos": total - activos
    }

# ==================== ENDPOINTS ====================

@router.post("")
async def crear_kit(kit: KitCreate, user: dict = Depends(require_admin)):
    """Crear nuevo kit/artículo compuesto"""
    
    # Validar que hay al menos un componente
    if not kit.componentes:
        raise HTTPException(status_code=400, detail="El kit debe tener al menos un componente")
    
    # Si hay producto principal, obtener su nombre
    if kit.producto_principal_id and not kit.producto_principal_nombre:
        producto = await db.repuestos.find_one(
            {"id": kit.producto_principal_id},
            {"_id": 0, "nombre": 1}
        )
        if producto:
            kit.producto_principal_nombre = producto.get("nombre")
    
    # Enriquecer componentes con nombres de productos
    componentes = []
    for idx, comp in enumerate(kit.componentes):
        comp_dict = comp.model_dump()
        comp_dict["orden"] = idx
        
        if comp.repuesto_id and not comp.repuesto_nombre:
            repuesto = await db.repuestos.find_one(
                {"id": comp.repuesto_id},
                {"_id": 0, "nombre": 1, "precio_venta": 1}
            )
            if repuesto:
                comp_dict["repuesto_nombre"] = repuesto.get("nombre")
                # Si precio no es fijo, usar precio del producto
                if not comp.precio_fijo:
                    comp_dict["precio_unitario"] = repuesto.get("precio_venta", 0)
        
        componentes.append(comp_dict)
    
    # Calcular totales
    totales = await calcular_totales_kit(componentes)
    
    doc = {
        "id": str(uuid.uuid4()),
        "nombre": kit.nombre,
        "descripcion": kit.descripcion,
        "producto_principal_id": kit.producto_principal_id,
        "producto_principal_nombre": kit.producto_principal_nombre,
        "categoria": kit.categoria,
        "componentes": componentes,
        "activo": kit.activo,
        "tags": kit.tags,
        **totales,
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.kits.insert_one(doc)
    doc.pop("_id", None)
    
    logger.info(f"Kit '{kit.nombre}' creado por {user.get('email')}")
    return doc

@router.get("")
async def listar_kits(
    activo: Optional[bool] = None,
    categoria: Optional[str] = None,
    producto_id: Optional[str] = None,
    buscar: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    user: dict = Depends(require_auth)
):
    """Listar kits con filtros"""
    query = {}
    
    if activo is not None:
        query["activo"] = activo
    if categoria:
        query["categoria"] = categoria
    if producto_id:
        query["producto_principal_id"] = producto_id
    if buscar:
        query["$or"] = [
            {"nombre": {"$regex": buscar, "$options": "i"}},
            {"descripcion": {"$regex": buscar, "$options": "i"}},
            {"tags": {"$regex": buscar, "$options": "i"}}
        ]
    
    total = await db.kits.count_documents(query)
    skip = (page - 1) * page_size
    
    kits = await db.kits.find(query, {"_id": 0}).sort("nombre", 1).skip(skip).limit(page_size).to_list(page_size)
    
    return {
        "items": kits,
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.get("/por-producto/{producto_id}")
async def obtener_kits_producto(producto_id: str, user: dict = Depends(require_auth)):
    """Obtener todos los kits asociados a un producto"""
    kits = await db.kits.find(
        {"producto_principal_id": producto_id, "activo": True},
        {"_id": 0}
    ).to_list(100)
    
    return kits

@router.get("/{kit_id}")
async def obtener_kit(kit_id: str, user: dict = Depends(require_auth)):
    """Obtener detalle de un kit"""
    kit = await db.kits.find_one({"id": kit_id}, {"_id": 0})
    if not kit:
        raise HTTPException(status_code=404, detail="Kit no encontrado")
    return kit

@router.put("/{kit_id}")
async def actualizar_kit(kit_id: str, data: KitUpdate, user: dict = Depends(require_admin)):
    """Actualizar kit"""
    kit = await db.kits.find_one({"id": kit_id}, {"_id": 0})
    if not kit:
        raise HTTPException(status_code=404, detail="Kit no encontrado")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if data.nombre is not None:
        update_data["nombre"] = data.nombre
    if data.descripcion is not None:
        update_data["descripcion"] = data.descripcion
    if data.activo is not None:
        update_data["activo"] = data.activo
    if data.tags is not None:
        update_data["tags"] = data.tags
    
    if data.componentes is not None:
        componentes = []
        for idx, comp in enumerate(data.componentes):
            comp_dict = comp.model_dump()
            comp_dict["orden"] = idx
            
            if comp.repuesto_id and not comp.repuesto_nombre:
                repuesto = await db.repuestos.find_one(
                    {"id": comp.repuesto_id},
                    {"_id": 0, "nombre": 1, "precio_venta": 1}
                )
                if repuesto:
                    comp_dict["repuesto_nombre"] = repuesto.get("nombre")
                    if not comp.precio_fijo:
                        comp_dict["precio_unitario"] = repuesto.get("precio_venta", 0)
            
            componentes.append(comp_dict)
        
        update_data["componentes"] = componentes
        totales = await calcular_totales_kit(componentes)
        update_data.update(totales)
    
    await db.kits.update_one({"id": kit_id}, {"$set": update_data})
    
    return {"message": "Kit actualizado"}

@router.delete("/{kit_id}")
async def eliminar_kit(kit_id: str, user: dict = Depends(require_admin)):
    """Eliminar kit (soft delete)"""
    result = await db.kits.update_one(
        {"id": kit_id},
        {"$set": {"activo": False, "deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Kit no encontrado")
    
    return {"message": "Kit eliminado"}

@router.post("/{kit_id}/expandir")
async def expandir_kit(kit_id: str, cantidad: int = 1, user: dict = Depends(require_auth)):
    """
    Expande un kit a sus líneas individuales.
    Útil para previsualizar antes de añadir a orden/factura.
    """
    kit = await db.kits.find_one({"id": kit_id}, {"_id": 0})
    if not kit:
        raise HTTPException(status_code=404, detail="Kit no encontrado")
    
    if not kit.get("activo", True):
        raise HTTPException(status_code=400, detail="Este kit no está activo")
    
    lineas = await expandir_kit_a_lineas(kit, cantidad)
    
    # Calcular totales de las líneas expandidas
    totales = await calcular_totales_kit(lineas)
    
    return {
        "kit_id": kit_id,
        "kit_nombre": kit.get("nombre"),
        "cantidad": cantidad,
        "lineas": lineas,
        **totales
    }

@router.get("/categorias/lista")
async def listar_categorias_kits(user: dict = Depends(require_auth)):
    """Obtener lista de categorías de kits"""
    categorias = await db.kits.distinct("categoria", {"activo": True})
    return [c for c in categorias if c]

# ==================== TIPOS DE COMPONENTES ====================

@router.get("/tipos-componente/lista")
async def listar_tipos_componente(user: dict = Depends(require_auth)):
    """Obtener tipos de componentes disponibles"""
    return [
        {"value": "producto", "label": "Producto/Repuesto", "descripcion": "Producto del inventario"},
        {"value": "mano_obra", "label": "Mano de Obra", "descripcion": "Servicio de instalación/reparación"},
        {"value": "logistica", "label": "Logística", "descripcion": "Envío, recogida, transporte"},
        {"value": "servicio", "label": "Servicio", "descripcion": "Servicio adicional"},
        {"value": "otro", "label": "Otro", "descripcion": "Concepto personalizado"}
    ]

# ==================== PLANTILLAS PREDEFINIDAS ====================

@router.get("/plantillas/lista")
async def listar_plantillas(user: dict = Depends(require_auth)):
    """Obtener plantillas predefinidas de kits comunes"""
    return [
        {
            "nombre": "Kit Reparación Pantalla",
            "descripcion": "Pantalla + Mano de obra + Logística",
            "componentes": [
                {"tipo": "producto", "descripcion": "Pantalla", "cantidad": 1, "precio_fijo": False},
                {"tipo": "mano_obra", "descripcion": "Mano de obra instalación", "cantidad": 1, "precio_unitario": 30, "precio_fijo": True},
                {"tipo": "logistica", "descripcion": "Logística", "cantidad": 1, "precio_unitario": 10, "precio_fijo": True}
            ]
        },
        {
            "nombre": "Kit Reparación Batería",
            "descripcion": "Batería + Mano de obra",
            "componentes": [
                {"tipo": "producto", "descripcion": "Batería", "cantidad": 1, "precio_fijo": False},
                {"tipo": "mano_obra", "descripcion": "Mano de obra instalación", "cantidad": 1, "precio_unitario": 20, "precio_fijo": True}
            ]
        },
        {
            "nombre": "Kit Completo Premium",
            "descripcion": "Producto + Mano de obra + Logística + Garantía extendida",
            "componentes": [
                {"tipo": "producto", "descripcion": "Repuesto principal", "cantidad": 1, "precio_fijo": False},
                {"tipo": "mano_obra", "descripcion": "Mano de obra", "cantidad": 1, "precio_unitario": 35, "precio_fijo": True},
                {"tipo": "logistica", "descripcion": "Logística express", "cantidad": 1, "precio_unitario": 15, "precio_fijo": True},
                {"tipo": "servicio", "descripcion": "Garantía extendida 12 meses", "cantidad": 1, "precio_unitario": 25, "precio_fijo": True}
            ]
        }
    ]


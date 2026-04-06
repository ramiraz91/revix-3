"""
API Routes para la gestión de proveedores e inventarios externos.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from auth import require_admin, require_auth
from config import db
from providers.gestor import get_gestor_proveedores, PROVEEDORES_DISPONIBLES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catalogo-proveedores", tags=["Catálogo Proveedores"])


# ============== MODELOS ==============

class ProveedorConfig(BaseModel):
    nombre: str
    username: Optional[str] = None
    password: Optional[str] = None
    activo: bool = True


class BusquedaRequest(BaseModel):
    query: str
    marca: Optional[str] = None
    proveedores: Optional[List[str]] = None
    solo_disponibles: bool = True
    ordenar_por: str = "precio"


class ProductoImportar(BaseModel):
    sku_proveedor: str
    nombre: str
    precio: float
    proveedor: str
    cantidad: int = 1
    tipo: str = "compatible"


# ============== ENDPOINTS ==============

@router.get("/disponibles")
async def listar_proveedores_disponibles(user: dict = Depends(require_admin)):
    """Listar todos los proveedores soportados por el sistema."""
    return {
        "proveedores": [
            {
                "id": nombre,
                "nombre": nombre.capitalize(),
                "requiere_login": clase.REQUIERE_LOGIN,
                "url": clase.URL_BASE
            }
            for nombre, clase in PROVEEDORES_DISPONIBLES.items()
        ]
    }


@router.get("/configurados")
async def listar_proveedores_configurados(user: dict = Depends(require_admin)):
    """Listar proveedores configurados con credenciales."""
    gestor = await get_gestor_proveedores(db)
    return {
        "proveedores": gestor.listar_proveedores()
    }


@router.post("/configurar")
async def configurar_proveedor(config: ProveedorConfig, user: dict = Depends(require_admin)):
    """Guardar o actualizar credenciales de un proveedor."""
    nombre = config.nombre.lower()
    
    if nombre not in PROVEEDORES_DISPONIBLES:
        raise HTTPException(
            status_code=400, 
            detail=f"Proveedor '{nombre}' no soportado. Disponibles: {list(PROVEEDORES_DISPONIBLES.keys())}"
        )
    
    # Obtener configuración actual
    cfg = await db.configuracion.find_one({"tipo": "proveedores"}, {"_id": 0})
    if not cfg:
        cfg = {"tipo": "proveedores", "datos": {"proveedores": []}}
    
    proveedores = cfg.get("datos", {}).get("proveedores", [])
    
    # Actualizar o añadir proveedor
    encontrado = False
    for i, p in enumerate(proveedores):
        if p.get("nombre", "").lower() == nombre:
            proveedores[i] = {
                "nombre": nombre,
                "username": config.username,
                "password": config.password,
                "activo": config.activo
            }
            encontrado = True
            break
    
    if not encontrado:
        proveedores.append({
            "nombre": nombre,
            "username": config.username,
            "password": config.password,
            "activo": config.activo
        })
    
    # Guardar en BD
    await db.configuracion.update_one(
        {"tipo": "proveedores"},
        {"$set": {"datos.proveedores": proveedores}},
        upsert=True
    )
    
    # Recargar gestor
    gestor = await get_gestor_proveedores(db)
    if config.activo:
        gestor.agregar_proveedor(nombre, config.username, config.password)
    
    return {"message": f"Proveedor {nombre} configurado correctamente"}


@router.delete("/configurar/{nombre}")
async def eliminar_proveedor(nombre: str, user: dict = Depends(require_admin)):
    """Eliminar configuración de un proveedor."""
    nombre = nombre.lower()
    
    cfg = await db.configuracion.find_one({"tipo": "proveedores"}, {"_id": 0})
    if not cfg:
        raise HTTPException(status_code=404, detail="No hay proveedores configurados")
    
    proveedores = cfg.get("datos", {}).get("proveedores", [])
    proveedores = [p for p in proveedores if p.get("nombre", "").lower() != nombre]
    
    await db.configuracion.update_one(
        {"tipo": "proveedores"},
        {"$set": {"datos.proveedores": proveedores}}
    )
    
    return {"message": f"Proveedor {nombre} eliminado"}


@router.post("/buscar")
async def buscar_productos(
    request: BusquedaRequest,
    user: dict = Depends(require_auth)
):
    """
    Buscar productos en los proveedores configurados.
    
    Ejemplo:
    ```json
    {
        "query": "pantalla iphone 14 pro",
        "marca": "Apple",
        "proveedores": ["mobilax", "spainsellers"],
        "solo_disponibles": true,
        "ordenar_por": "precio"
    }
    ```
    """
    gestor = await get_gestor_proveedores(db)
    
    if not gestor._proveedores:
        raise HTTPException(
            status_code=400, 
            detail="No hay proveedores configurados. Ve a Configuración > Proveedores para añadir credenciales."
        )
    
    try:
        productos = await gestor.buscar_en_todos(
            query=request.query,
            marca=request.marca,
            proveedores=request.proveedores,
            ordenar_por=request.ordenar_por,
            solo_disponibles=request.solo_disponibles
        )
        
        return {
            "query": request.query,
            "total": len(productos),
            "productos": [p.to_dict() for p in productos]
        }
        
    except Exception as e:
        logger.error(f"Error buscando productos: {e}")
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")


@router.get("/buscar")
async def buscar_productos_get(
    q: str = Query(..., description="Término de búsqueda"),
    marca: Optional[str] = Query(None, description="Filtrar por marca"),
    proveedor: Optional[str] = Query(None, description="Proveedor específico"),
    user: dict = Depends(require_auth)
):
    """Buscar productos (versión GET para pruebas rápidas)."""
    gestor = await get_gestor_proveedores(db)
    
    if not gestor._proveedores:
        raise HTTPException(status_code=400, detail="No hay proveedores configurados")
    
    proveedores = [proveedor] if proveedor else None
    
    productos = await gestor.buscar_en_todos(
        query=q,
        marca=marca,
        proveedores=proveedores,
        solo_disponibles=True
    )
    
    return {
        "query": q,
        "total": len(productos),
        "productos": [p.to_dict() for p in productos]
    }


@router.post("/comparar-precios")
async def comparar_precios(
    query: str = Query(..., description="SKU o nombre del producto"),
    user: dict = Depends(require_auth)
):
    """Comparar precios de un producto entre todos los proveedores."""
    gestor = await get_gestor_proveedores(db)
    
    if not gestor._proveedores:
        raise HTTPException(status_code=400, detail="No hay proveedores configurados")
    
    resultado = await gestor.comparar_precios(query)
    return resultado


@router.get("/buscar-compatible")
async def buscar_repuesto_compatible(
    marca: str = Query(..., description="Marca del dispositivo"),
    modelo: str = Query(..., description="Modelo del dispositivo"),
    tipo: Optional[str] = Query(None, description="Tipo de repuesto (pantalla, batería, etc.)"),
    user: dict = Depends(require_auth)
):
    """Buscar repuestos compatibles con un dispositivo específico."""
    gestor = await get_gestor_proveedores(db)
    
    if not gestor._proveedores:
        raise HTTPException(status_code=400, detail="No hay proveedores configurados")
    
    productos = await gestor.buscar_repuesto_compatible(
        marca=marca,
        modelo=modelo,
        tipo_repuesto=tipo
    )
    
    return {
        "dispositivo": f"{marca} {modelo}",
        "tipo_repuesto": tipo,
        "total": len(productos),
        "productos": [p.to_dict() for p in productos]
    }


@router.post("/importar-a-inventario")
async def importar_producto_a_inventario(
    producto: ProductoImportar,
    user: dict = Depends(require_admin)
):
    """
    Importar un producto de proveedor al inventario interno del CRM.
    
    Esto crea una entrada en el inventario con los datos del proveedor.
    """
    from datetime import datetime, timezone
    import uuid
    
    # Generar SKU interno
    sku_interno = f"IMP-{producto.proveedor[:3].upper()}-{producto.sku_proveedor[:10]}"
    
    # Verificar si ya existe
    existente = await db.inventario.find_one({"sku": sku_interno}, {"_id": 0})
    if existente:
        return {
            "message": "El producto ya existe en el inventario",
            "sku": sku_interno,
            "producto_existente": existente
        }
    
    # Crear entrada de inventario
    nuevo_producto = {
        "id": str(uuid.uuid4()),
        "sku": sku_interno,
        "nombre": producto.nombre,
        "tipo": producto.tipo,
        "precio_venta": producto.precio,
        "precio_coste": round(producto.precio * 0.7, 2),  # Estimado 30% margen
        "stock": producto.cantidad,
        "stock_minimo": 1,
        "proveedor": producto.proveedor,
        "proveedor_sku": producto.sku_proveedor,
        "origen": "importado_proveedor",
        "activo": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.get("email")
    }
    
    await db.inventario.insert_one(nuevo_producto)
    del nuevo_producto["_id"]
    
    logger.info(f"Producto importado al inventario: {sku_interno} por {user.get('email')}")
    
    return {
        "message": "Producto importado correctamente",
        "producto": nuevo_producto
    }


@router.post("/test-conexion/{nombre}")
async def test_conexion_proveedor(nombre: str, user: dict = Depends(require_admin)):
    """Probar la conexión/autenticación con un proveedor."""
    nombre = nombre.lower()
    
    gestor = await get_gestor_proveedores(db)
    
    if nombre not in gestor._proveedores:
        raise HTTPException(status_code=404, detail=f"Proveedor '{nombre}' no configurado")
    
    scraper = gestor._proveedores[nombre]
    
    try:
        resultado = await scraper.authenticate()
        return {
            "proveedor": nombre,
            "conexion_exitosa": resultado,
            "mensaje": "Autenticación exitosa" if resultado else "Error de autenticación"
        }
    except Exception as e:
        return {
            "proveedor": nombre,
            "conexion_exitosa": False,
            "mensaje": f"Error: {str(e)}"
        }

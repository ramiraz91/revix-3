"""
Rutas de Restos / Despiece.
Extraído de server.py durante refactorización.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timezone
import uuid

from config import db, logger
from auth import require_auth, require_admin
from models import Resto, PiezaResto

router = APIRouter(tags=["restos"])

@router.get("/restos")
async def listar_restos(
    estado: Optional[str] = None,
    tipo: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(require_admin)
):
    """Lista todos los dispositivos en restos/despiece"""
    query = {}
    if estado:
        query["estado"] = estado
    if tipo:
        query["tipo"] = tipo
    return await db.restos.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)

@router.get("/restos/{resto_id}")
async def obtener_resto(resto_id: str, user: dict = Depends(require_admin)):
    """Obtiene un resto específico por ID"""
    resto = await db.restos.find_one({"id": resto_id}, {"_id": 0})
    if not resto:
        raise HTTPException(status_code=404, detail="Resto no encontrado")
    # Añadir info de la orden original
    if resto.get('orden_id'):
        resto['orden_original'] = await db.ordenes.find_one({"id": resto['orden_id']}, {"_id": 0})
    return resto

@router.post("/restos")
async def crear_resto(data: dict, user: dict = Depends(require_admin)):
    """Crea un nuevo registro de resto/despiece"""
    resto = Resto(
        orden_id=data.get('orden_id', ''),
        numero_orden=data.get('numero_orden', ''),
        tipo=data.get('tipo', 'dispositivo_reemplazado'),
        modelo=data.get('modelo', ''),
        imei=data.get('imei'),
        color=data.get('color'),
        descripcion_daños=data.get('descripcion_daños'),
        ubicacion=data.get('ubicacion'),
        notas=data.get('notas'),
    )
    doc = resto.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['fecha_recepcion'] = doc['fecha_recepcion'].isoformat()
    await db.restos.insert_one(doc)
    doc.pop('_id', None)
    
    # Log de auditoría
    from routes.ordenes_routes import log_audit
    await log_audit("resto", doc['id'], user, "resto_creado", f"Creado resto {doc['codigo_resto']} desde orden {data.get('numero_orden', 'N/A')}")
    
    return doc

@router.put("/restos/{resto_id}")
async def actualizar_resto(resto_id: str, data: dict, user: dict = Depends(require_admin)):
    """Actualiza un resto existente"""
    resto = await db.restos.find_one({"id": resto_id}, {"_id": 0})
    if not resto:
        raise HTTPException(status_code=404, detail="Resto no encontrado")
    
    update_data = {k: v for k, v in data.items() if v is not None and k not in ['id', 'codigo_resto', 'created_at']}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # Si cambia a clasificado o despiezado, actualizar fechas
    if data.get('estado') == 'clasificado' and resto.get('estado') != 'clasificado':
        update_data['fecha_clasificacion'] = datetime.now(timezone.utc).isoformat()
    if data.get('estado') == 'despiezado' and resto.get('estado') != 'despiezado':
        update_data['fecha_despiece'] = datetime.now(timezone.utc).isoformat()
    
    await db.restos.update_one({"id": resto_id}, {"$set": update_data})
    return await db.restos.find_one({"id": resto_id}, {"_id": 0})

@router.post("/restos/{resto_id}/piezas")
async def añadir_pieza_resto(resto_id: str, data: dict, user: dict = Depends(require_admin)):
    """Añade una pieza extraída a un resto"""
    resto = await db.restos.find_one({"id": resto_id}, {"_id": 0})
    if not resto:
        raise HTTPException(status_code=404, detail="Resto no encontrado")
    
    pieza = PiezaResto(
        nombre=data.get('nombre', ''),
        estado=data.get('estado', 'bueno'),
        destino=data.get('destino'),
        codigo_inventario=data.get('codigo_inventario'),
        notas=data.get('notas'),
    )
    pieza_doc = pieza.model_dump()
    
    piezas_actuales = resto.get('piezas', [])
    piezas_actuales.append(pieza_doc)
    piezas_utiles = len([p for p in piezas_actuales if p.get('estado') in ['bueno', 'aceptable']])
    
    await db.restos.update_one({"id": resto_id}, {
        "$set": {
            "piezas": piezas_actuales,
            "piezas_utiles": piezas_utiles,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    })
    
    return await db.restos.find_one({"id": resto_id}, {"_id": 0})

@router.delete("/restos/{resto_id}/piezas/{pieza_id}")
async def eliminar_pieza_resto(resto_id: str, pieza_id: str, user: dict = Depends(require_admin)):
    """Elimina una pieza de un resto"""
    resto = await db.restos.find_one({"id": resto_id}, {"_id": 0})
    if not resto:
        raise HTTPException(status_code=404, detail="Resto no encontrado")
    
    piezas = [p for p in resto.get('piezas', []) if p.get('id') != pieza_id]
    piezas_utiles = len([p for p in piezas if p.get('estado') in ['bueno', 'aceptable']])
    
    await db.restos.update_one({"id": resto_id}, {
        "$set": {
            "piezas": piezas,
            "piezas_utiles": piezas_utiles,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    })
    
    return {"message": "Pieza eliminada"}

@router.post("/ordenes/{orden_id}/enviar-a-restos")
async def enviar_orden_a_restos(orden_id: str, data: dict, user: dict = Depends(require_admin)):
    """Envía el dispositivo de una orden a restos (usado cuando se reemplaza)"""
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    resto = Resto(
        orden_id=orden_id,
        numero_orden=orden['numero_orden'],
        tipo=data.get('tipo', 'dispositivo_reemplazado'),
        modelo=orden['dispositivo']['modelo'],
        imei=orden['dispositivo'].get('imei'),
        color=orden['dispositivo'].get('color'),
        descripcion_daños=orden['dispositivo'].get('daños'),
        ubicacion=data.get('ubicacion'),
        notas=data.get('notas', f"Dispositivo original de orden {orden['numero_orden']} - Reemplazado"),
    )
    doc = resto.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['fecha_recepcion'] = doc['fecha_recepcion'].isoformat()
    await db.restos.insert_one(doc)
    doc.pop('_id', None)
    
    # Actualizar la orden con referencia al resto
    await db.ordenes.update_one({"id": orden_id}, {
        "$set": {
            "resto_id": doc['id'],
            "resto_codigo": doc['codigo_resto'],
            "dispositivo_enviado_a_restos": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    })
    
    # Log de auditoría
    from routes.ordenes_routes import log_audit
    await log_audit("resto", doc['id'], user, "envio_a_restos", f"Dispositivo de orden {orden['numero_orden']} enviado a restos con código {doc['codigo_resto']}")
    
    return {
        "message": "Dispositivo enviado a restos",
        "codigo_resto": doc['codigo_resto'],
        "resto": doc
    }


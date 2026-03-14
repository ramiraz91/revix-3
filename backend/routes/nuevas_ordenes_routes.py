"""
Nuevas Órdenes - Endpoints para gestionar pre-registros aceptados pendientes de tramitar.
El tramitador revisa los datos, añade el código de recogida y confirma la creación de la orden.
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from config import db, logger
from auth import require_admin, require_auth
from models import EstadoPreRegistro

router = APIRouter(prefix="/nuevas-ordenes", tags=["nuevas-ordenes"])


class TramitarRequest(BaseModel):
    codigo_recogida: str
    agencia_envio: Optional[str] = ""
    notas: Optional[str] = ""


@router.get("/count")
async def contar_nuevas_ordenes(user: dict = Depends(require_admin)):
    """Cuenta las nuevas órdenes pendientes de tramitar (para el badge del sidebar)."""
    count = await db.pre_registros.count_documents({
        "estado": EstadoPreRegistro.PENDIENTE_TRAMITAR.value
    })
    return {"count": count}


@router.get("/")
async def listar_nuevas_ordenes(user: dict = Depends(require_admin)):
    """Lista todas las nuevas órdenes pendientes de tramitar."""
    cursor = db.pre_registros.find(
        {"estado": EstadoPreRegistro.PENDIENTE_TRAMITAR.value},
        {"_id": 0}
    ).sort("updated_at", -1)
    
    items = await cursor.to_list(100)
    return {"items": items, "total": len(items)}


@router.get("/{pre_registro_id}")
async def detalle_nueva_orden(pre_registro_id: str, user: dict = Depends(require_admin)):
    """Detalle de una nueva orden pendiente de tramitar."""
    pre_reg = await db.pre_registros.find_one({"id": pre_registro_id}, {"_id": 0})
    if not pre_reg:
        raise HTTPException(status_code=404, detail="Pre-registro no encontrado")
    return pre_reg


@router.post("/{pre_registro_id}/tramitar")
async def tramitar_nueva_orden(
    pre_registro_id: str,
    data: TramitarRequest,
    user: dict = Depends(require_admin)
):
    """
    Tramitar una nueva orden: el tramitador añade el código de recogida
    y se crea la orden de trabajo real en el sistema.
    """
    pre_reg = await db.pre_registros.find_one({"id": pre_registro_id}, {"_id": 0})
    if not pre_reg:
        raise HTTPException(status_code=404, detail="Pre-registro no encontrado")
    
    if pre_reg.get("estado") != EstadoPreRegistro.PENDIENTE_TRAMITAR.value:
        raise HTTPException(status_code=400, detail=f"Estado no válido: {pre_reg.get('estado')}")
    
    if pre_reg.get("orden_id"):
        raise HTTPException(status_code=400, detail="Ya tiene una orden creada")
    
    if not data.codigo_recogida.strip():
        raise HTTPException(status_code=400, detail="El código de recogida es obligatorio")
    
    try:
        from agent.processor import create_orden_from_pre_registro, log_agent
        
        # Enrich portal data with tramitador input
        datos_portal = pre_reg.get("datos_portal") or {}
        datos_portal["tracking_number"] = data.codigo_recogida.strip()
        if data.agencia_envio:
            datos_portal["shipping_company"] = data.agencia_envio
        
        # Create the real work order
        orden_id = await create_orden_from_pre_registro(pre_reg, datos_portal)
        
        if not orden_id:
            raise HTTPException(status_code=500, detail="Error creando la orden de trabajo")
        
        # Update the work order with the pickup code and notes
        update_orden = {
            "codigo_recogida_entrada": data.codigo_recogida.strip(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if data.agencia_envio:
            update_orden["agencia_envio"] = data.agencia_envio
        if data.notas:
            update_orden["notas_tramitador"] = data.notas
        
        await db.ordenes.update_one({"id": orden_id}, {"$set": update_orden})
        
        # Update pre_registro
        historial = pre_reg.get("historial", [])
        historial.append({
            "evento": "orden_creada_tramitador",
            "fecha": datetime.now(timezone.utc).isoformat(),
            "detalle": f"Orden {orden_id} creada por {user.get('email')}. Código recogida: {data.codigo_recogida}"
        })
        
        await db.pre_registros.update_one(
            {"id": pre_registro_id},
            {"$set": {
                "estado": EstadoPreRegistro.ORDEN_CREADA.value,
                "orden_id": orden_id,
                "codigo_recogida": data.codigo_recogida.strip(),
                "tramitado_por": user.get("email"),
                "fecha_tramitacion": datetime.now(timezone.utc).isoformat(),
                "historial": historial,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Get order details for response
        orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0, "numero_orden": 1})
        numero_orden = orden.get("numero_orden") if orden else ""
        
        # Notification
        codigo = pre_reg.get("codigo_siniestro", "")
        await db.notificaciones.insert_one({
            "id": str(import_uuid()),
            "tipo": "orden_tramitada",
            "titulo": "Orden Tramitada",
            "mensaje": f"Siniestro {codigo} tramitado → Orden {numero_orden}. Código recogida: {data.codigo_recogida}",
            "orden_id": orden_id,
            "codigo_siniestro": codigo,
            "leida": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"Nueva orden tramitada: {codigo} → {numero_orden} por {user.get('email')}")
        
        return {
            "message": "Orden de trabajo creada correctamente",
            "orden_id": orden_id,
            "numero_orden": numero_orden,
            "codigo_siniestro": codigo
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tramitando nueva orden {pre_registro_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{pre_registro_id}/rechazar")
async def rechazar_nueva_orden(
    pre_registro_id: str,
    user: dict = Depends(require_admin)
):
    """Rechazar/archivar una nueva orden sin crear orden de trabajo."""
    pre_reg = await db.pre_registros.find_one({"id": pre_registro_id}, {"_id": 0})
    if not pre_reg:
        raise HTTPException(status_code=404, detail="Pre-registro no encontrado")
    
    historial = pre_reg.get("historial", [])
    historial.append({
        "evento": "rechazado_tramitador",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "detalle": f"Rechazado/archivado por {user.get('email')}"
    })
    
    await db.pre_registros.update_one(
        {"id": pre_registro_id},
        {"$set": {
            "estado": EstadoPreRegistro.ARCHIVADO.value,
            "historial": historial,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Nueva orden archivada"}


def import_uuid():
    import uuid
    return uuid.uuid4()

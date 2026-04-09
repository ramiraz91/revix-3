"""
Nuevas Órdenes - Endpoints para gestionar pre-registros aceptados pendientes de tramitar.
El tramitador revisa los datos, añade el código de recogida y confirma la creación de la orden.
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
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


@router.get("")
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


@router.put("/{pre_registro_id}")
async def actualizar_nueva_orden(pre_registro_id: str, request: Request, user: dict = Depends(require_admin)):
    """Actualizar datos de una pre-orden (cliente, dispositivo, etc.) antes de tramitar."""
    pre_reg = await db.pre_registros.find_one({"id": pre_registro_id}, {"_id": 0})
    if not pre_reg:
        raise HTTPException(status_code=404, detail="Pre-registro no encontrado")
    if pre_reg.get("estado") not in [EstadoPreRegistro.PENDIENTE_TRAMITAR.value]:
        raise HTTPException(status_code=400, detail="Solo se pueden editar pre-órdenes pendientes de tramitar")
    
    body = await request.json()
    
    campos_editables = [
        "cliente_nombre", "cliente_email", "cliente_telefono",
        "cliente_direccion", "cliente_codigo_postal", "cliente_ciudad",
        "cliente_provincia", "cliente_dni",
        "dispositivo_modelo", "dispositivo_marca", "dispositivo_color",
        "dispositivo_imei", "numero_serie",
        "daño_descripcion", "notas",
        "tipo_servicio", "tipo_seguro", "compania_seguro",
        "agencia_envio", "codigo_recogida_sugerido"
    ]
    
    update = {}
    for campo in campos_editables:
        if campo in body:
            update[campo] = body[campo]
    
    if not update:
        return pre_reg
    
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    historial = pre_reg.get("historial", [])
    historial.append({
        "evento": "datos_editados",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "detalle": f"Datos editados por {user.get('email')}: {', '.join(update.keys())}"
    })
    update["historial"] = historial
    
    await db.pre_registros.update_one({"id": pre_registro_id}, {"$set": update})
    
    updated = await db.pre_registros.find_one({"id": pre_registro_id}, {"_id": 0})
    return updated


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


@router.delete("/{pre_registro_id}")
async def eliminar_nueva_orden(
    pre_registro_id: str,
    user: dict = Depends(require_admin)
):
    """Eliminar permanentemente una pre-orden."""
    pre_reg = await db.pre_registros.find_one({"id": pre_registro_id}, {"_id": 0})
    if not pre_reg:
        raise HTTPException(status_code=404, detail="Pre-registro no encontrado")
    
    # No permitir eliminar si ya tiene orden creada
    if pre_reg.get("orden_id"):
        raise HTTPException(status_code=400, detail="No se puede eliminar: ya tiene una orden de trabajo asociada")
    
    codigo = pre_reg.get("codigo_siniestro", "")
    await db.pre_registros.delete_one({"id": pre_registro_id})
    
    logger.info(f"Pre-registro {codigo} eliminado por {user.get('email')}")
    return {"message": f"Pre-orden {codigo} eliminada permanentemente"}


@router.post("/{pre_registro_id}/refrescar-datos")
async def refrescar_datos_portal(
    pre_registro_id: str,
    user: dict = Depends(require_admin)
):
    """Re-scrapea los datos del portal Sumbroker para enriquecer la pre-orden."""
    pre_reg = await db.pre_registros.find_one({"id": pre_registro_id}, {"_id": 0})
    if not pre_reg:
        raise HTTPException(status_code=404, detail="Pre-registro no encontrado")
    
    codigo = pre_reg.get("codigo_siniestro")
    if not codigo:
        raise HTTPException(status_code=400, detail="Código de siniestro no válido")
    
    try:
        from agent.processor import scrape_portal_data
        
        datos_portal = await scrape_portal_data(codigo)
        
        if not datos_portal:
            raise HTTPException(status_code=404, detail="No se pudieron obtener datos del portal")
        
        # Mapear datos del portal a campos del pre-registro
        update_data = {
            "datos_portal": datos_portal,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Enriquecer campos del pre-registro
        dp = datos_portal
        if dp.get("client_full_name"):
            update_data["cliente_nombre"] = dp["client_full_name"]
        if dp.get("client_phone"):
            update_data["cliente_telefono"] = dp["client_phone"]
        if dp.get("client_email"):
            update_data["cliente_email"] = dp["client_email"]
        if dp.get("client_nif"):
            update_data["cliente_dni"] = dp["client_nif"]
        if dp.get("client_address"):
            update_data["cliente_direccion"] = dp["client_address"]
        if dp.get("client_zip"):
            update_data["cliente_codigo_postal"] = dp["client_zip"]
        if dp.get("client_city"):
            update_data["cliente_ciudad"] = dp["client_city"]
        if dp.get("client_province"):
            update_data["cliente_provincia"] = dp["client_province"]
        
        # Dispositivo
        device_brand = dp.get("device_brand") or ""
        device_model = dp.get("device_model") or ""
        if device_brand or device_model:
            update_data["dispositivo_modelo"] = f"{device_brand} {device_model}".strip()
        if device_brand:
            update_data["dispositivo_marca"] = device_brand
        if dp.get("device_imei"):
            update_data["dispositivo_imei"] = dp["device_imei"]
        if dp.get("device_colour"):
            update_data["dispositivo_color"] = dp["device_colour"]
        
        # Daño y servicio
        if dp.get("damage_description"):
            update_data["daño_descripcion"] = dp["damage_description"]
        if dp.get("damage_type_text"):
            update_data["tipo_servicio"] = dp["damage_type_text"]
        
        # Tracking/envío
        if dp.get("tracking_number"):
            update_data["codigo_recogida_sugerido"] = dp["tracking_number"]
        if dp.get("shipping_company"):
            update_data["agencia_envio"] = dp["shipping_company"]
        
        # Seguro
        if dp.get("policy_number"):
            update_data["poliza"] = dp["policy_number"]
        if dp.get("insurance_company"):
            update_data["compania"] = dp["insurance_company"]
        if dp.get("product_name"):
            update_data["producto"] = dp["product_name"]
        
        # Historial
        historial = pre_reg.get("historial", [])
        historial.append({
            "evento": "datos_refrescados",
            "fecha": datetime.now(timezone.utc).isoformat(),
            "detalle": f"Datos actualizados desde portal por {user.get('email')}"
        })
        update_data["historial"] = historial
        
        await db.pre_registros.update_one({"id": pre_registro_id}, {"$set": update_data})
        
        updated = await db.pre_registros.find_one({"id": pre_registro_id}, {"_id": 0})
        return updated
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refrescando datos de {codigo}: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo datos: {str(e)}")


@router.post("/actualizar-insurama")
async def actualizar_desde_insurama(user: dict = Depends(require_admin)):
    """Fuerza una consulta inmediata a Insurama para buscar nuevos presupuestos aceptados."""
    import asyncio
    try:
        from agent.insurama_poller import poll_insurama_budgets
        # Ejecutar en background para no bloquear la request
        asyncio.create_task(poll_insurama_budgets())
        
        count = await db.pre_registros.count_documents({
            "estado": EstadoPreRegistro.PENDIENTE_TRAMITAR.value
        })
        
        return {
            "message": "Consulta a Insurama iniciada. Actualiza en unos segundos para ver resultados.",
            "pendientes_tramitar": count
        }
    except Exception as e:
        logger.error(f"Error consultando Insurama: {e}")
        raise HTTPException(status_code=500, detail=f"Error consultando Insurama: {str(e)}")


def import_uuid():
    import uuid
    return uuid.uuid4()

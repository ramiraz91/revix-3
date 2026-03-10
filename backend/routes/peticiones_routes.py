"""
Rutas para Peticiones Exteriores (Solicitudes de presupuesto de la web pública)
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from config import db, logger
from auth import require_auth, require_admin, require_master

router = APIRouter()

# ==================== MODELOS ====================

class PeticionExteriorCreate(BaseModel):
    nombre: str
    email: str
    telefono: str
    dispositivo: str  # Marca y modelo
    problema: str  # Descripción del problema
    tipo_pieza: Optional[str] = "sin_preferencia"  # original, compatible, sin_preferencia
    direccion: Optional[str] = None
    codigo_postal: Optional[str] = None
    ciudad: Optional[str] = None
    comentarios: Optional[str] = None
    origen: str = "web"  # web, telefono, email, presencial

class PeticionExteriorUpdate(BaseModel):
    estado: Optional[str] = None
    notas_internas: Optional[str] = None
    presupuesto_estimado: Optional[float] = None
    tiempo_estimado: Optional[str] = None
    asignado_a: Optional[str] = None
    fecha_llamada: Optional[str] = None
    resultado_llamada: Optional[str] = None

class ConvertirAOrdenRequest(BaseModel):
    crear_cliente: bool = True
    notas: Optional[str] = None

# ==================== ENDPOINTS ====================

@router.get("/peticiones-exteriores")
async def listar_peticiones(
    estado: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    user: dict = Depends(require_admin)
):
    """Lista todas las peticiones exteriores"""
    filtro = {}
    if estado:
        filtro["estado"] = estado
    
    peticiones = await db.peticiones_exteriores.find(
        filtro, 
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.peticiones_exteriores.count_documents(filtro)
    
    # Contar por estado
    estados_count = {}
    for est in ["pendiente", "contactado", "presupuestado", "aceptado", "rechazado", "convertido"]:
        estados_count[est] = await db.peticiones_exteriores.count_documents({"estado": est})
    
    return {
        "peticiones": peticiones,
        "total": total,
        "estados": estados_count
    }

@router.get("/peticiones-exteriores/{peticion_id}")
async def obtener_peticion(peticion_id: str, user: dict = Depends(require_admin)):
    """Obtiene una petición por ID"""
    peticion = await db.peticiones_exteriores.find_one({"id": peticion_id}, {"_id": 0})
    if not peticion:
        raise HTTPException(status_code=404, detail="Petición no encontrada")
    return peticion

@router.post("/peticiones-exteriores")
async def crear_peticion(data: PeticionExteriorCreate, request: Request):
    """Crea una nueva petición exterior (desde web pública o CRM)"""
    
    peticion_id = str(uuid.uuid4())
    numero_peticion = f"PET-{datetime.now().strftime('%Y%m%d')}-{peticion_id[:4].upper()}"
    
    peticion = {
        "id": peticion_id,
        "numero": numero_peticion,
        "nombre": data.nombre.strip(),
        "email": data.email.lower().strip(),
        "telefono": data.telefono.strip(),
        "dispositivo": data.dispositivo.strip(),
        "problema": data.problema.strip(),
        "tipo_pieza": data.tipo_pieza,
        "direccion": data.direccion,
        "codigo_postal": data.codigo_postal,
        "ciudad": data.ciudad,
        "comentarios": data.comentarios,
        "origen": data.origen,
        "estado": "pendiente",
        "notas_internas": "",
        "presupuesto_estimado": None,
        "tiempo_estimado": None,
        "asignado_a": None,
        "fecha_llamada": None,
        "resultado_llamada": None,
        "orden_id": None,  # Se llena cuando se convierte a orden
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "ip_origen": request.client.host if request.client else None
    }
    
    await db.peticiones_exteriores.insert_one(peticion)
    
    # Enviar email de confirmación al cliente
    try:
        from services.email_service import send_email
        send_email(
            to=data.email,
            subject="¡Hemos recibido tu petición! — Revix.es",
            titulo=f"¡Hola {data.nombre.split()[0]}! 👋",
            contenido=f"""
                <p style="font-size: 16px;">¡Ya hemos recibido tu petición de presupuesto!</p>
                
                <div style="background: #f0f9ff; border-left: 4px solid #0055FF; padding: 16px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                    <p style="margin: 0; font-size: 15px;">
                        <strong>📱 Dispositivo:</strong> {data.dispositivo}<br/>
                        <strong>🔧 Problema:</strong> {data.problema}
                    </p>
                </div>
                
                <p style="font-size: 15px;">
                    En breve recibirás una <strong>llamada de un técnico especializado</strong> para tu caso. 
                    Te explicaremos todo el proceso y resolveremos cualquier duda que tengas.
                </p>
                
                <p style="font-size: 14px; color: #64748b; font-style: italic;">
                    Ten paciencia, ¡somos muy rápidos pero a veces nos hacemos de rogar! 😄
                </p>
                
                <p style="font-size: 15px; margin-top: 24px;">
                    <strong>¡Gracias por confiar en Revix.es!</strong>
                </p>
            """,
            link_url="https://revix.es/consulta",
            link_text="Consultar estado"
        )
        logger.info(f"Email de confirmación enviado a {data.email}")
    except Exception as e:
        logger.warning(f"No se pudo enviar email de confirmación: {e}")
    
    return {"message": "Petición creada correctamente", "id": peticion_id, "numero": numero_peticion}

@router.put("/peticiones-exteriores/{peticion_id}")
async def actualizar_peticion(
    peticion_id: str, 
    data: PeticionExteriorUpdate, 
    user: dict = Depends(require_admin)
):
    """Actualiza una petición exterior"""
    peticion = await db.peticiones_exteriores.find_one({"id": peticion_id})
    if not peticion:
        raise HTTPException(status_code=404, detail="Petición no encontrada")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.peticiones_exteriores.update_one(
        {"id": peticion_id},
        {"$set": update_data}
    )
    
    return {"message": "Petición actualizada"}

@router.post("/peticiones-exteriores/{peticion_id}/contactar")
async def marcar_contactado(
    peticion_id: str,
    resultado: str,  # "exito", "no_contesta", "llamar_luego", "rechazado"
    notas: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Marca una petición como contactada después de llamar al cliente"""
    peticion = await db.peticiones_exteriores.find_one({"id": peticion_id}, {"_id": 0})
    if not peticion:
        raise HTTPException(status_code=404, detail="Petición no encontrada")
    
    nuevo_estado = "contactado"
    if resultado == "rechazado":
        nuevo_estado = "rechazado"
    elif resultado == "exito":
        nuevo_estado = "presupuestado"
    
    await db.peticiones_exteriores.update_one(
        {"id": peticion_id},
        {"$set": {
            "estado": nuevo_estado,
            "fecha_llamada": datetime.now(timezone.utc).isoformat(),
            "resultado_llamada": resultado,
            "notas_internas": (peticion.get("notas_internas", "") + f"\n[{datetime.now().strftime('%d/%m %H:%M')}] Llamada: {resultado}. {notas or ''}").strip(),
            "asignado_a": user.get("email"),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Estado actualizado", "nuevo_estado": nuevo_estado}

@router.post("/peticiones-exteriores/{peticion_id}/aceptar")
async def aceptar_presupuesto(
    peticion_id: str,
    presupuesto: float,
    tiempo_estimado: str,
    notas: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Marca que el cliente ha aceptado el presupuesto"""
    peticion = await db.peticiones_exteriores.find_one({"id": peticion_id}, {"_id": 0})
    if not peticion:
        raise HTTPException(status_code=404, detail="Petición no encontrada")
    
    await db.peticiones_exteriores.update_one(
        {"id": peticion_id},
        {"$set": {
            "estado": "aceptado",
            "presupuesto_estimado": presupuesto,
            "tiempo_estimado": tiempo_estimado,
            "notas_internas": (peticion.get("notas_internas", "") + f"\n[{datetime.now().strftime('%d/%m %H:%M')}] Presupuesto aceptado: {presupuesto}€. {notas or ''}").strip(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Enviar email de confirmación al cliente
    try:
        from services.email_service import send_email
        send_email(
            to=peticion["email"],
            subject="¡Presupuesto confirmado! — Revix.es",
            titulo=f"¡Genial {peticion['nombre'].split()[0]}! 🎉",
            contenido=f"""
                <p style="font-size: 16px;">Tu presupuesto ha sido confirmado. ¡Estamos listos para reparar tu dispositivo!</p>
                
                <div style="background: #f0fdf4; border-left: 4px solid #22c55e; padding: 16px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                    <p style="margin: 0; font-size: 15px;">
                        <strong>📱 Dispositivo:</strong> {peticion['dispositivo']}<br/>
                        <strong>💰 Presupuesto:</strong> {presupuesto}€<br/>
                        <strong>⏱️ Tiempo estimado:</strong> {tiempo_estimado}
                    </p>
                </div>
                
                <p style="font-size: 15px;">
                    <strong>Próximos pasos:</strong>
                </p>
                <ol style="font-size: 14px; color: #475569;">
                    <li>Coordinaremos la recogida de tu dispositivo (normalmente en 24h)</li>
                    <li>Realizaremos el diagnóstico y prepararemos las piezas</li>
                    <li>Te avisaremos cuando esté listo para la devolución</li>
                </ol>
                
                <p style="font-size: 14px; color: #64748b;">
                    Si detectamos alguna avería adicional durante el diagnóstico, te llamaremos para informarte del nuevo presupuesto antes de proceder.
                </p>
            """,
            link_url="https://revix.es/consulta",
            link_text="Seguir mi reparación"
        )
    except Exception as e:
        logger.warning(f"No se pudo enviar email de confirmación: {e}")
    
    return {"message": "Presupuesto aceptado"}

@router.post("/peticiones-exteriores/{peticion_id}/convertir")
async def convertir_a_orden(
    peticion_id: str,
    data: ConvertirAOrdenRequest,
    user: dict = Depends(require_admin)
):
    """Convierte una petición aceptada en una orden de trabajo"""
    peticion = await db.peticiones_exteriores.find_one({"id": peticion_id}, {"_id": 0})
    if not peticion:
        raise HTTPException(status_code=404, detail="Petición no encontrada")
    
    if peticion["estado"] not in ["aceptado", "presupuestado"]:
        raise HTTPException(status_code=400, detail="La petición debe estar aceptada para convertirla en orden")
    
    # Crear o buscar cliente
    cliente_id = None
    if data.crear_cliente:
        cliente_existente = await db.clientes.find_one({"email": peticion["email"]}, {"_id": 0})
        if cliente_existente:
            cliente_id = cliente_existente["id"]
        else:
            cliente_id = str(uuid.uuid4())
            nuevo_cliente = {
                "id": cliente_id,
                "nombre": peticion["nombre"],
                "email": peticion["email"],
                "telefono": peticion["telefono"],
                "direccion": peticion.get("direccion", ""),
                "ciudad": peticion.get("ciudad", ""),
                "codigo_postal": peticion.get("codigo_postal", ""),
                "notas": f"Cliente creado desde petición exterior {peticion['numero']}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "origen": "peticion_exterior"
            }
            await db.clientes.insert_one(nuevo_cliente)
    
    # Crear orden de trabajo
    from helpers import generate_barcode
    
    orden_id = str(uuid.uuid4())
    contador = await db.ordenes.count_documents({}) + 1
    numero_orden = f"ORD-{contador:06d}"
    
    # Parsear dispositivo (intentar separar marca y modelo)
    dispositivo_parts = peticion["dispositivo"].split(" ", 1)
    marca = dispositivo_parts[0] if dispositivo_parts else ""
    modelo = dispositivo_parts[1] if len(dispositivo_parts) > 1 else peticion["dispositivo"]
    
    nueva_orden = {
        "id": orden_id,
        "numero_orden": numero_orden,
        "codigo_barras": generate_barcode(),
        "cliente_id": cliente_id,
        "cliente": {
            "nombre": peticion["nombre"],
            "email": peticion["email"],
            "telefono": peticion["telefono"]
        },
        "dispositivo": {
            "tipo": "smartphone",
            "marca": marca,
            "modelo": modelo
        },
        "problema_reportado": peticion["problema"],
        "estado": "pendiente_recibir",
        "es_exterior": True,
        "peticion_origen_id": peticion_id,
        "tipo_pieza_preferida": peticion.get("tipo_pieza", "sin_preferencia"),
        "presupuesto_estimado": peticion.get("presupuesto_estimado"),
        "notas_internas": f"Origen: Petición exterior {peticion['numero']}\n{data.notas or ''}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.get("email"),
        "evidencias": [],
        "materiales": [],
        "historial": [{
            "fecha": datetime.now(timezone.utc).isoformat(),
            "accion": "Orden creada desde petición exterior",
            "usuario": user.get("email"),
            "detalles": f"Petición: {peticion['numero']}"
        }]
    }
    
    await db.ordenes.insert_one(nueva_orden)
    
    # Actualizar petición
    await db.peticiones_exteriores.update_one(
        {"id": peticion_id},
        {"$set": {
            "estado": "convertido",
            "orden_id": orden_id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "Petición convertida a orden de trabajo",
        "orden_id": orden_id,
        "numero_orden": numero_orden,
        "cliente_id": cliente_id
    }

@router.delete("/peticiones-exteriores/{peticion_id}")
async def eliminar_peticion(peticion_id: str, user: dict = Depends(require_master)):
    """Elimina una petición (solo master)"""
    result = await db.peticiones_exteriores.delete_one({"id": peticion_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Petición no encontrada")
    return {"message": "Petición eliminada"}

# ==================== ESTADÍSTICAS ====================

@router.get("/peticiones-exteriores/stats/resumen")
async def estadisticas_peticiones(user: dict = Depends(require_admin)):
    """Estadísticas de peticiones exteriores"""
    total = await db.peticiones_exteriores.count_documents({})
    
    # Por estado
    estados = {}
    for estado in ["pendiente", "contactado", "presupuestado", "aceptado", "rechazado", "convertido"]:
        estados[estado] = await db.peticiones_exteriores.count_documents({"estado": estado})
    
    # Por origen
    origenes = {}
    for origen in ["web", "telefono", "email", "presencial"]:
        origenes[origen] = await db.peticiones_exteriores.count_documents({"origen": origen})
    
    # Últimas 24h
    from datetime import timedelta
    hace_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    nuevas_24h = await db.peticiones_exteriores.count_documents({"created_at": {"$gte": hace_24h}})
    
    # Tasa de conversión
    tasa_conversion = (estados.get("convertido", 0) / total * 100) if total > 0 else 0
    
    return {
        "total": total,
        "por_estado": estados,
        "por_origen": origenes,
        "nuevas_24h": nuevas_24h,
        "tasa_conversion": round(tasa_conversion, 1),
        "pendientes_llamar": estados.get("pendiente", 0)
    }

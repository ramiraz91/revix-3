"""
Rutas de Calendario: eventos, asignación de órdenes, disponibilidad técnicos.
Extraído de server.py durante refactorización.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from config import db, logger
from auth import require_auth, require_admin

router = APIRouter(tags=["calendario"])

@router.get("/calendario/eventos")
async def listar_eventos_calendario(
    fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None,
    usuario_id: Optional[str] = None, tipo: Optional[str] = None,
    user: dict = Depends(require_auth)
):
    query = {}
    conditions = []
    if fecha_desde:
        conditions.append({"fecha_inicio": {"$gte": fecha_desde}})
    if fecha_hasta:
        conditions.append({"fecha_inicio": {"$lte": fecha_hasta}})
    if usuario_id:
        conditions.append({"usuario_id": usuario_id})
    if tipo:
        conditions.append({"tipo": tipo})
    if user.get('role') == 'tecnico':
        conditions.append({"usuario_id": user['user_id']})
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    return await db.calendario.find(query, {"_id": 0}).sort("fecha_inicio", 1).to_list(1000)

@router.post("/calendario/eventos")
async def crear_evento_calendario(evento: dict, user: dict = Depends(require_admin)):
    evento_obj = EventoCalendario(
        titulo=evento.get('titulo'), descripcion=evento.get('descripcion'),
        tipo=evento.get('tipo', TipoEvento.OTRO), fecha_inicio=evento.get('fecha_inicio'),
        fecha_fin=evento.get('fecha_fin'), todo_el_dia=evento.get('todo_el_dia', False),
        usuario_id=evento.get('usuario_id'), orden_id=evento.get('orden_id'),
        color=evento.get('color'), created_by=user['user_id']
    )
    doc = evento_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.calendario.insert_one(doc)
    doc.pop('_id', None)
    return doc

@router.put("/calendario/eventos/{evento_id}")
async def actualizar_evento_calendario(evento_id: str, evento: dict, user: dict = Depends(require_admin)):
    existing = await db.calendario.find_one({"id": evento_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    update_data = {k: v for k, v in evento.items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.calendario.update_one({"id": evento_id}, {"$set": update_data})
    return await db.calendario.find_one({"id": evento_id}, {"_id": 0})

@router.delete("/calendario/eventos/{evento_id}")
async def eliminar_evento_calendario(evento_id: str, user: dict = Depends(require_admin)):
    result = await db.calendario.delete_one({"id": evento_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return {"message": "Evento eliminado"}

class _AsignarOrdenRequest(BaseModel):
    orden_id: str
    tecnico_id: str
    fecha_estimada: str

@router.post("/calendario/asignar-orden")
async def asignar_orden_tecnico(data: _AsignarOrdenRequest, user: dict = Depends(require_admin)):
    orden = await db.ordenes.find_one({"id": data.orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    tecnico = await db.users.find_one({"id": data.tecnico_id, "role": "tecnico"}, {"_id": 0})
    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    await db.ordenes.update_one({"id": data.orden_id}, {"$set": {"tecnico_asignado": data.tecnico_id, "fecha_estimada_reparacion": data.fecha_estimada, "updated_at": datetime.now(timezone.utc).isoformat()}})
    evento = EventoCalendario(titulo=f"Reparación: {orden['numero_orden']}", descripcion=f"Dispositivo: {orden['dispositivo']['modelo']} - {orden['dispositivo']['daños']}", tipo=TipoEvento.ORDEN_ASIGNADA, fecha_inicio=data.fecha_estimada, usuario_id=data.tecnico_id, orden_id=data.orden_id, color="#3b82f6", created_by=user['user_id'])
    doc = evento.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.calendario.insert_one(doc)
    doc.pop('_id', None)
    notificacion = Notificacion(tipo="orden_asignada", mensaje=f"Se te ha asignado la orden {orden['numero_orden']} para el {data.fecha_estimada}", orden_id=data.orden_id)
    notif_doc = notificacion.model_dump()
    notif_doc['created_at'] = notif_doc['created_at'].isoformat()
    notif_doc['usuario_destino'] = data.tecnico_id
    await db.notificaciones.insert_one(notif_doc)
    return {"message": "Orden asignada al técnico", "evento_id": doc.get('id')}

@router.get("/tecnicos/disponibilidad")
async def obtener_disponibilidad_tecnicos(fecha: str, user: dict = Depends(require_admin)):
    tecnicos = await db.users.find({"role": "tecnico", "activo": True}, {"_id": 0, "password_hash": 0}).to_list(100)
    resultado = []
    for tecnico in tecnicos:
        ordenes_asignadas = await db.calendario.count_documents({"usuario_id": tecnico['id'], "tipo": "orden_asignada", "fecha_inicio": {"$regex": f"^{fecha}"}})
        tiene_ausencia = await db.calendario.find_one({"usuario_id": tecnico['id'], "tipo": {"$in": ["vacaciones", "ausencia"]}, "fecha_inicio": {"$lte": fecha}, "fecha_fin": {"$gte": fecha}})
        resultado.append({"tecnico": {"id": tecnico['id'], "nombre": tecnico['nombre'], "apellidos": tecnico.get('apellidos', ''), "avatar_url": tecnico.get('avatar_url')}, "ordenes_asignadas": ordenes_asignadas, "disponible": not tiene_ausencia, "motivo_no_disponible": tiene_ausencia['tipo'] if tiene_ausencia else None})
    return resultado

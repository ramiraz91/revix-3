"""
Admin routes - Auditoría, SLA, Comisiones, Etiquetas de envío, Plantillas de email
Refactorizado desde server.py
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from config import db, logger
from auth import require_admin, require_master

router = APIRouter(tags=["admin"])

# ==================== AUDITORÍA ====================

@router.get("/auditoria")
async def listar_auditoria(
    entidad: Optional[str] = None,
    entidad_id: Optional[str] = None,
    usuario_email: Optional[str] = None,
    accion: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    user: dict = Depends(require_admin)
):
    """Lista logs de auditoría con filtros"""
    query = {}
    conditions = []
    
    if entidad:
        conditions.append({"entidad": entidad})
    if entidad_id:
        conditions.append({"entidad_id": entidad_id})
    if usuario_email:
        conditions.append({"usuario_email": {"$regex": usuario_email, "$options": "i"}})
    if accion:
        conditions.append({"accion": accion})
    if fecha_desde:
        conditions.append({"created_at": {"$gte": fecha_desde}})
    if fecha_hasta:
        conditions.append({"created_at": {"$lte": fecha_hasta}})
    
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    
    total = await db.audit_logs.count_documents(query)
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return {
        "total": total,
        "limit": limit,
        "skip": skip,
        "data": logs
    }

@router.get("/auditoria/entidad/{entidad}/{entidad_id}")
async def obtener_auditoria_entidad(entidad: str, entidad_id: str, user: dict = Depends(require_admin)):
    """Obtiene el historial de auditoría de una entidad específica"""
    logs = await db.audit_logs.find(
        {"entidad": entidad, "entidad_id": entidad_id}, 
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    return logs

# ==================== ALERTAS SLA ====================

@router.get("/alertas-sla")
async def listar_alertas_sla(
    tipo: Optional[str] = None,
    resuelta: Optional[bool] = None,
    limit: int = 50,
    user: dict = Depends(require_admin)
):
    """Lista alertas de SLA activas"""
    query = {}
    conditions = []
    
    if tipo:
        conditions.append({"tipo_alerta": tipo})
    if resuelta is not None:
        conditions.append({"resuelta": resuelta})
    
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    
    return await db.alertas_sla.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)

@router.post("/alertas-sla/verificar")
async def verificar_sla_ordenes(user: dict = Depends(require_admin)):
    """Verifica órdenes y genera alertas de SLA si corresponde"""
    now = datetime.now(timezone.utc)
    alertas_generadas = []
    
    estados_activos = ["pendiente_recibir", "recibida", "en_taller", "re_presupuestar", "reparado", "validacion"]
    ordenes = await db.ordenes.find(
        {"estado": {"$in": estados_activos}},
        {"_id": 0, "id": 1, "numero_orden": 1, "created_at": 1, "sla_dias": 1, "alerta_sla_enviada": 1}
    ).to_list(1000)
    
    for orden in ordenes:
        try:
            created_at = orden.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            dias_en_proceso = (now - created_at).days
            sla_objetivo = orden.get('sla_dias', 5)
            
            tipo_alerta = None
            if dias_en_proceso >= sla_objetivo * 2:
                tipo_alerta = "critico"
            elif dias_en_proceso >= sla_objetivo:
                tipo_alerta = "vencido"
            elif dias_en_proceso >= sla_objetivo - 1:
                tipo_alerta = "proximo_vencer"
            
            if tipo_alerta and not orden.get('alerta_sla_enviada'):
                alerta = {
                    "id": str(uuid.uuid4()),
                    "orden_id": orden['id'],
                    "numero_orden": orden['numero_orden'],
                    "tipo_alerta": tipo_alerta,
                    "dias_en_proceso": dias_en_proceso,
                    "sla_objetivo": sla_objetivo,
                    "mensaje": f"Orden {orden['numero_orden']}: {dias_en_proceso} días en proceso (SLA: {sla_objetivo} días)",
                    "resuelta": False,
                    "created_at": now.isoformat()
                }
                await db.alertas_sla.insert_one(alerta)
                await db.ordenes.update_one({"id": orden['id']}, {"$set": {"alerta_sla_enviada": True}})
                alertas_generadas.append(alerta)
        except Exception as e:
            logger.error(f"Error procesando SLA para orden {orden.get('id')}: {e}")
    
    return {"alertas_generadas": len(alertas_generadas), "alertas": alertas_generadas}

@router.patch("/alertas-sla/{alerta_id}/resolver")
async def resolver_alerta_sla(alerta_id: str, user: dict = Depends(require_admin)):
    """Marca una alerta SLA como resuelta"""
    result = await db.alertas_sla.update_one(
        {"id": alerta_id},
        {"$set": {"resuelta": True, "resuelta_por": user.get('email'), "fecha_resolucion": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return {"message": "Alerta marcada como resuelta"}

# ==================== COMISIONES DE TÉCNICOS ====================

@router.get("/comisiones")
async def listar_comisiones(
    tecnico_id: Optional[str] = None,
    estado: Optional[str] = None,
    periodo: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(require_admin)
):
    """Lista las comisiones de técnicos con filtros"""
    query = {}
    conditions = []
    
    if tecnico_id:
        conditions.append({"tecnico_id": tecnico_id})
    if estado:
        conditions.append({"estado": estado})
    if periodo:
        conditions.append({"periodo": periodo})
    
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    
    comisiones = await db.comisiones.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    total_pendiente = sum(c.get('monto_total', 0) for c in comisiones if c.get('estado') == 'pendiente')
    total_aprobadas = sum(c.get('monto_total', 0) for c in comisiones if c.get('estado') == 'aprobada')
    total_pagadas = sum(c.get('monto_total', 0) for c in comisiones if c.get('estado') == 'pagada')
    
    return {
        "comisiones": comisiones,
        "totales": {
            "pendiente": total_pendiente,
            "aprobadas": total_aprobadas,
            "pagadas": total_pagadas
        }
    }

@router.get("/comisiones/resumen")
async def resumen_comisiones(periodo: Optional[str] = None, user: dict = Depends(require_admin)):
    """Resumen de comisiones por técnico"""
    query = {}
    if periodo:
        query["periodo"] = periodo
    
    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": "$tecnico_id",
            "tecnico_nombre": {"$first": "$tecnico_nombre"},
            "total_ordenes": {"$sum": 1},
            "total_monto": {"$sum": "$monto_total"},
            "pendiente": {"$sum": {"$cond": [{"$eq": ["$estado", "pendiente"]}, "$monto_total", 0]}},
            "aprobada": {"$sum": {"$cond": [{"$eq": ["$estado", "aprobada"]}, "$monto_total", 0]}},
            "pagada": {"$sum": {"$cond": [{"$eq": ["$estado", "pagada"]}, "$monto_total", 0]}}
        }},
        {"$sort": {"total_monto": -1}}
    ]
    
    result = await db.comisiones.aggregate(pipeline).to_list(100)
    return result

@router.post("/comisiones/{comision_id}/aprobar")
async def aprobar_comision(comision_id: str, user: dict = Depends(require_admin)):
    """Aprueba una comisión pendiente"""
    result = await db.comisiones.update_one(
        {"id": comision_id, "estado": "pendiente"},
        {"$set": {
            "estado": "aprobada",
            "aprobada_por": user.get('email'),
            "fecha_aprobacion": datetime.now(timezone.utc).isoformat()
        }}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Comisión no encontrada o ya aprobada")
    return {"message": "Comisión aprobada"}

@router.post("/comisiones/{comision_id}/pagar")
async def marcar_comision_pagada(comision_id: str, user: dict = Depends(require_admin)):
    """Marca una comisión como pagada"""
    result = await db.comisiones.update_one(
        {"id": comision_id, "estado": "aprobada"},
        {"$set": {
            "estado": "pagada",
            "pagada_fecha": datetime.now(timezone.utc).isoformat()
        }}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Comisión no encontrada o no está aprobada")
    return {"message": "Comisión marcada como pagada"}

@router.get("/comisiones/config")
async def obtener_config_comisiones(user: dict = Depends(require_admin)):
    """Obtiene la configuración global de comisiones"""
    config = await db.configuracion.find_one({"tipo": "comisiones"}, {"_id": 0})
    if not config:
        config = {
            "tipo": "comisiones",
            "datos": {
                "sistema_activo": False,
                "porcentaje_default": 5.0,
                "fijo_default": 0.0,
                "aplicar_a_garantias": False,
                "aplicar_a_seguros": True,
                "aplicar_a_particulares": True
            }
        }
    return config.get('datos', {})

@router.put("/comisiones/config")
async def actualizar_config_comisiones(config: dict, user: dict = Depends(require_admin)):
    """Actualiza la configuración global de comisiones"""
    await db.configuracion.update_one(
        {"tipo": "comisiones"},
        {"$set": {"datos": config, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    return {"message": "Configuración actualizada"}

# ==================== ETIQUETAS DE ENVÍO ====================

@router.get("/transportistas")
async def listar_transportistas(user: dict = Depends(require_admin)):
    """Lista los transportistas configurados"""
    transportistas = await db.transportistas.find({}, {"_id": 0, "api_key": 0, "api_secret": 0, "password": 0}).to_list(20)
    
    if not transportistas:
        transportistas = [
            {"id": "mrw", "nombre": "MRW", "codigo": "mrw", "activo": False, "config_extra": {}},
            {"id": "seur", "nombre": "SEUR", "codigo": "seur", "activo": False, "config_extra": {}},
            {"id": "correos", "nombre": "Correos Express", "codigo": "correos", "activo": False, "config_extra": {}},
            {"id": "dhl", "nombre": "DHL", "codigo": "dhl", "activo": False, "config_extra": {}},
            {"id": "ups", "nombre": "UPS", "codigo": "ups", "activo": False, "config_extra": {}},
            {"id": "gls", "nombre": "GLS", "codigo": "gls", "activo": False, "config_extra": {}},
        ]
    return transportistas

@router.get("/transportistas/{codigo}")
async def obtener_transportista(codigo: str, user: dict = Depends(require_admin)):
    """Obtiene la configuración de un transportista"""
    transportista = await db.transportistas.find_one({"codigo": codigo}, {"_id": 0})
    if not transportista:
        raise HTTPException(status_code=404, detail="Transportista no encontrado")
    if 'api_key' in transportista:
        transportista['api_key'] = '***' if transportista['api_key'] else None
    if 'api_secret' in transportista:
        transportista['api_secret'] = '***' if transportista['api_secret'] else None
    if 'password' in transportista:
        transportista['password'] = '***' if transportista['password'] else None
    return transportista

@router.put("/transportistas/{codigo}")
async def actualizar_transportista(codigo: str, data: dict, user: dict = Depends(require_admin)):
    """Actualiza la configuración de un transportista"""
    if data.get('api_key') == '***':
        del data['api_key']
    if data.get('api_secret') == '***':
        del data['api_secret']
    if data.get('password') == '***':
        del data['password']
    
    data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.transportistas.update_one(
        {"codigo": codigo},
        {"$set": data},
        upsert=True
    )
    return {"message": "Transportista actualizado"}

@router.get("/etiquetas-envio")
async def listar_etiquetas(
    orden_id: Optional[str] = None,
    estado: Optional[str] = None,
    transportista: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(require_admin)
):
    """Lista las etiquetas de envío"""
    query = {}
    conditions = []
    
    if orden_id:
        conditions.append({"orden_id": orden_id})
    if estado:
        conditions.append({"estado": estado})
    if transportista:
        conditions.append({"transportista": transportista})
    
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    
    return await db.etiquetas_envio.find(query, {"_id": 0, "etiqueta_base64": 0}).sort("created_at", -1).to_list(limit)

@router.post("/etiquetas-envio")
async def crear_etiqueta_envio(data: dict, user: dict = Depends(require_admin)):
    """Crea una etiqueta de envío (preparada para integración con API)"""
    orden_id = data.get('orden_id')
    if not orden_id:
        raise HTTPException(status_code=400, detail="orden_id es requerido")
    
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    cliente = await db.clientes.find_one({"id": orden.get('cliente_id')}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    transportista_codigo = data.get('transportista', 'mrw')
    transportista = await db.transportistas.find_one({"codigo": transportista_codigo}, {"_id": 0})
    
    etiqueta = {
        "id": str(uuid.uuid4()),
        "orden_id": orden_id,
        "numero_orden": orden.get('numero_orden'),
        "transportista": transportista_codigo,
        "tipo": data.get('tipo', 'salida'),
        "destinatario_nombre": f"{cliente.get('nombre', '')} {cliente.get('apellidos', '')}".strip(),
        "destinatario_direccion": cliente.get('direccion', ''),
        "destinatario_ciudad": cliente.get('ciudad', ''),
        "destinatario_cp": cliente.get('codigo_postal', ''),
        "destinatario_telefono": cliente.get('telefono', ''),
        "destinatario_email": cliente.get('email'),
        "peso_kg": data.get('peso_kg', 0.5),
        "largo_cm": data.get('largo_cm', 20),
        "ancho_cm": data.get('ancho_cm', 15),
        "alto_cm": data.get('alto_cm', 10),
        "contenido": data.get('contenido', 'Dispositivo móvil'),
        "valor_declarado": data.get('valor_declarado'),
        "estado": "pendiente",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    if transportista and transportista.get('activo') and transportista.get('api_url'):
        etiqueta['estado'] = 'pendiente_api'
        etiqueta['error_mensaje'] = 'Integración con API pendiente de configuración'
    
    await db.etiquetas_envio.insert_one(etiqueta)
    
    return {"message": "Etiqueta creada", "etiqueta": etiqueta}

@router.get("/etiquetas-envio/{etiqueta_id}")
async def obtener_etiqueta(etiqueta_id: str, user: dict = Depends(require_admin)):
    """Obtiene una etiqueta específica"""
    etiqueta = await db.etiquetas_envio.find_one({"id": etiqueta_id}, {"_id": 0})
    if not etiqueta:
        raise HTTPException(status_code=404, detail="Etiqueta no encontrada")
    return etiqueta

@router.delete("/etiquetas-envio/{etiqueta_id}")
async def eliminar_etiqueta(etiqueta_id: str, user: dict = Depends(require_admin)):
    """Elimina una etiqueta"""
    result = await db.etiquetas_envio.delete_one({"id": etiqueta_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Etiqueta no encontrada")
    return {"message": "Etiqueta eliminada"}

# ==================== PLANTILLAS DE EMAIL ====================

PLANTILLAS_DEFAULT = [
    {
        "tipo": "created",
        "nombre": "Nueva Orden",
        "asunto": "✨ Nueva Orden de Reparación - {numero_orden}",
        "titulo": "¡Orden Registrada!",
        "subtitulo": "Hemos recibido tu solicitud de reparación",
        "mensaje_principal": "Tu orden de reparación ha sido registrada correctamente. Te mantendremos informado sobre el progreso de tu dispositivo.",
        "color_banner": "#3b82f6",
        "emoji_estado": "📱",
        "mostrar_progreso": True,
        "mostrar_tracking": False,
        "activo": True,
        "es_default": True
    },
    {
        "tipo": "recibida",
        "nombre": "Dispositivo Recibido",
        "asunto": "✅ Dispositivo Recibido - {numero_orden}",
        "titulo": "Dispositivo Recibido",
        "subtitulo": "Tu dispositivo llegó a nuestro centro",
        "mensaje_principal": "¡Buenas noticias! Hemos recibido tu dispositivo en nuestras instalaciones.",
        "color_banner": "#10b981",
        "emoji_estado": "✅",
        "mostrar_progreso": True,
        "mostrar_tracking": False,
        "activo": True,
        "es_default": True
    },
    {
        "tipo": "en_taller",
        "nombre": "En Reparación",
        "asunto": "🔧 En Reparación - {numero_orden}",
        "titulo": "En Reparación",
        "subtitulo": "Nuestro técnico está trabajando en tu dispositivo",
        "mensaje_principal": "Tu dispositivo ya está en manos de nuestros especialistas.",
        "color_banner": "#f59e0b",
        "emoji_estado": "🔧",
        "mostrar_progreso": True,
        "mostrar_tracking": False,
        "activo": True,
        "es_default": True
    },
    {
        "tipo": "reparado",
        "nombre": "Reparación Completada",
        "asunto": "✨ ¡Reparación Completada! - {numero_orden}",
        "titulo": "¡Reparación Completada!",
        "subtitulo": "Tu dispositivo está listo",
        "mensaje_principal": "¡Excelentes noticias! La reparación ha sido completada con éxito.",
        "color_banner": "#8b5cf6",
        "emoji_estado": "✨",
        "mostrar_progreso": True,
        "mostrar_tracking": False,
        "activo": True,
        "es_default": True
    },
    {
        "tipo": "enviado",
        "nombre": "Dispositivo Enviado",
        "asunto": "🚀 ¡Tu dispositivo está en camino! - {numero_orden}",
        "titulo": "¡En Camino!",
        "subtitulo": "Tu dispositivo reparado va hacia ti",
        "mensaje_principal": "Tu dispositivo reparado ya está en camino.",
        "color_banner": "#06b6d4",
        "emoji_estado": "🚀",
        "mostrar_progreso": True,
        "mostrar_tracking": True,
        "activo": True,
        "es_default": True
    }
]

@router.get("/plantillas-email")
async def listar_plantillas_email(user: dict = Depends(require_admin)):
    """Lista todas las plantillas de email"""
    plantillas = await db.plantillas_email.find({}, {"_id": 0}).sort("tipo", 1).to_list(50)
    
    if not plantillas:
        for p in PLANTILLAS_DEFAULT:
            p_copy = p.copy()
            p_copy['id'] = str(uuid.uuid4())
            p_copy['created_at'] = datetime.now(timezone.utc).isoformat()
            p_copy['updated_at'] = datetime.now(timezone.utc).isoformat()
            await db.plantillas_email.insert_one(p_copy)
        
        plantillas = await db.plantillas_email.find({}, {"_id": 0}).to_list(50)
    
    return plantillas

@router.get("/plantillas-email/{tipo}")
async def obtener_plantilla_email(tipo: str, user: dict = Depends(require_admin)):
    """Obtiene una plantilla específica por tipo"""
    plantilla = await db.plantillas_email.find_one({"tipo": tipo, "activo": True}, {"_id": 0})
    if not plantilla:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return plantilla

@router.put("/plantillas-email/{plantilla_id}")
async def actualizar_plantilla_email(plantilla_id: str, data: dict, user: dict = Depends(require_admin)):
    """Actualiza una plantilla de email"""
    data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.plantillas_email.update_one(
        {"id": plantilla_id},
        {"$set": data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    
    return {"message": "Plantilla actualizada"}

@router.post("/plantillas-email/{plantilla_id}/reset")
async def resetear_plantilla_email(plantilla_id: str, user: dict = Depends(require_admin)):
    """Resetea una plantilla a sus valores por defecto"""
    plantilla = await db.plantillas_email.find_one({"id": plantilla_id}, {"_id": 0})
    if not plantilla:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    
    tipo = plantilla.get('tipo')
    default = next((p for p in PLANTILLAS_DEFAULT if p['tipo'] == tipo), None)
    
    if default:
        reset_data = {
            "asunto": default['asunto'],
            "nombre": default['nombre'],
            "titulo": default['titulo'],
            "subtitulo": default['subtitulo'],
            "mensaje_principal": default['mensaje_principal'],
            "mensaje_secundario": default.get('mensaje_secundario', ''),
            "color_banner": default['color_banner'],
            "emoji_estado": default['emoji_estado'],
            "mostrar_progreso": default.get('mostrar_progreso', True),
            "mostrar_tracking": default.get('mostrar_tracking', False),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.plantillas_email.update_one({"id": plantilla_id}, {"$set": reset_data})
    
    return {"message": "Plantilla reseteada a valores por defecto"}

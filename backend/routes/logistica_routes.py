"""
Rutas de Control de Logística
Gestión de recogidas y envíos con alertas de retrasos
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from config import db, logger
from auth import require_auth, require_admin

router = APIRouter()


# ==================== MODELOS ====================

class LogisticaItem(BaseModel):
    orden_id: str
    numero_orden: str
    numero_autorizacion: Optional[str] = None
    cliente_nombre: str
    cliente_telefono: Optional[str] = None
    dispositivo_modelo: str
    estado: str
    tipo: str  # 'recogida' o 'envio'
    codigo_tracking: Optional[str] = None
    fecha_solicitud: Optional[str] = None
    fecha_completado: Optional[str] = None
    horas_transcurridas: Optional[float] = None
    en_retraso: bool = False
    direccion: Optional[str] = None
    ciudad: Optional[str] = None


class LogisticaResumen(BaseModel):
    total_recogidas_pendientes: int = 0
    total_envios_pendientes: int = 0
    recogidas_en_retraso: int = 0
    envios_en_retraso: int = 0
    completados_hoy: int = 0


# ==================== ENDPOINTS ====================

@router.get("/logistica/resumen")
async def obtener_resumen_logistica(user: dict = Depends(require_admin)):
    """Obtiene resumen de estado de logística"""
    try:
        now = datetime.now(timezone.utc)
        hace_48h = now - timedelta(hours=48)
        hoy_inicio = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Recogidas pendientes (sin codigo_recogida_entrada y no canceladas)
        recogidas_pendientes = await db.ordenes.count_documents({
            "estado": {"$nin": ["cancelado", "irreparable"]},
            "$or": [
                {"codigo_recogida_entrada": {"$exists": False}},
                {"codigo_recogida_entrada": None},
                {"codigo_recogida_entrada": ""}
            ],
            "fecha_recibida_centro": None
        })
        
        # Envíos pendientes (reparado/validación sin código salida)
        envios_pendientes = await db.ordenes.count_documents({
            "estado": {"$in": ["reparado", "validacion"]},
            "$or": [
                {"codigo_recogida_salida": {"$exists": False}},
                {"codigo_recogida_salida": None},
                {"codigo_recogida_salida": ""}
            ]
        })
        
        # Recogidas en retraso (>48h sin recibir)
        recogidas_retraso = await db.ordenes.count_documents({
            "estado": "pendiente_recibir",
            "created_at": {"$lt": hace_48h.isoformat()}
        })
        
        # Envíos en retraso (>48h en estado reparado/validación sin enviar)
        pipeline_envios_retraso = [
            {
                "$match": {
                    "estado": {"$in": ["reparado", "validacion"]},
                    "$or": [
                        {"fecha_enviado": None},
                        {"fecha_enviado": {"$exists": False}}
                    ]
                }
            },
            {
                "$addFields": {
                    "fecha_fin": {
                        "$cond": {
                            "if": {"$ne": ["$fecha_fin_reparacion", None]},
                            "then": "$fecha_fin_reparacion",
                            "else": "$updated_at"
                        }
                    }
                }
            }
        ]
        envios_retraso_cursor = db.ordenes.aggregate(pipeline_envios_retraso)
        envios_retraso = 0
        async for orden in envios_retraso_cursor:
            fecha_fin = orden.get("fecha_fin")
            if fecha_fin:
                try:
                    if isinstance(fecha_fin, str):
                        fecha_fin = datetime.fromisoformat(fecha_fin.replace('Z', '+00:00'))
                    if fecha_fin < hace_48h:
                        envios_retraso += 1
                except:
                    pass
        
        # Completados hoy (recibidos o enviados hoy)
        completados_hoy = await db.ordenes.count_documents({
            "$or": [
                {"fecha_recibida_centro": {"$gte": hoy_inicio.isoformat()}},
                {"fecha_enviado": {"$gte": hoy_inicio.isoformat()}}
            ]
        })
        
        return {
            "total_recogidas_pendientes": recogidas_pendientes,
            "total_envios_pendientes": envios_pendientes,
            "recogidas_en_retraso": recogidas_retraso,
            "envios_en_retraso": envios_retraso,
            "completados_hoy": completados_hoy
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo resumen logística: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logistica/recogidas")
async def listar_recogidas(
    estado: Optional[str] = Query(None, description="pendiente, completada, retraso"),
    busqueda: Optional[str] = Query(None, description="Buscar por número orden o autorización"),
    limit: int = Query(50, le=200),
    user: dict = Depends(require_admin)
):
    """Lista recogidas pendientes y completadas"""
    try:
        now = datetime.now(timezone.utc)
        hace_48h = now - timedelta(hours=48)
        
        # Base query
        query = {"estado": {"$nin": ["cancelado", "irreparable"]}}
        
        # Filtro por estado
        if estado == "pendiente":
            query["$and"] = [
                {"$or": [
                    {"fecha_recibida_centro": None},
                    {"fecha_recibida_centro": {"$exists": False}}
                ]},
                {"estado": "pendiente_recibir"}
            ]
        elif estado == "completada":
            query["fecha_recibida_centro"] = {"$ne": None, "$exists": True}
        elif estado == "retraso":
            query["$and"] = [
                {"estado": "pendiente_recibir"},
                {"created_at": {"$lt": hace_48h.isoformat()}}
            ]
        
        # Búsqueda
        if busqueda:
            query["$or"] = [
                {"numero_orden": {"$regex": busqueda, "$options": "i"}},
                {"numero_autorizacion": {"$regex": busqueda, "$options": "i"}}
            ]
        
        ordenes = await db.ordenes.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        # Obtener clientes
        cliente_ids = [o.get("cliente_id") for o in ordenes if o.get("cliente_id")]
        clientes = {}
        if cliente_ids:
            clientes_docs = await db.clientes.find(
                {"id": {"$in": cliente_ids}},
                {"_id": 0, "id": 1, "nombre": 1, "apellidos": 1, "telefono": 1, "direccion": 1, "ciudad": 1, "codigo_postal": 1}
            ).to_list(len(cliente_ids))
            clientes = {c["id"]: c for c in clientes_docs}
        
        # Construir resultado
        items = []
        for orden in ordenes:
            cliente = clientes.get(orden.get("cliente_id"), {})
            
            # Calcular horas transcurridas
            horas = None
            en_retraso = False
            created_at = orden.get("created_at")
            fecha_recibida = orden.get("fecha_recibida_centro")
            
            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        created_dt = created_at
                    
                    if fecha_recibida:
                        if isinstance(fecha_recibida, str):
                            recibida_dt = datetime.fromisoformat(fecha_recibida.replace('Z', '+00:00'))
                        else:
                            recibida_dt = fecha_recibida
                        horas = (recibida_dt - created_dt).total_seconds() / 3600
                    else:
                        horas = (now - created_dt).total_seconds() / 3600
                        en_retraso = horas > 48
                except:
                    pass
            
            items.append({
                "orden_id": orden.get("id"),
                "numero_orden": orden.get("numero_orden"),
                "numero_autorizacion": orden.get("numero_autorizacion"),
                "cliente_nombre": f"{cliente.get('nombre', '')} {cliente.get('apellidos', '')}".strip() or "Sin cliente",
                "cliente_telefono": cliente.get("telefono"),
                "dispositivo_modelo": orden.get("dispositivo", {}).get("modelo", "N/A"),
                "estado": "completada" if fecha_recibida else "pendiente",
                "tipo": "recogida",
                "codigo_tracking": orden.get("codigo_recogida_entrada"),
                "fecha_solicitud": created_at,
                "fecha_completado": fecha_recibida,
                "horas_transcurridas": round(horas, 1) if horas else None,
                "en_retraso": en_retraso,
                "direccion": cliente.get("direccion"),
                "ciudad": f"{cliente.get('codigo_postal', '')} {cliente.get('ciudad', '')}".strip()
            })
        
        return items
        
    except Exception as e:
        logger.error(f"Error listando recogidas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logistica/envios")
async def listar_envios(
    estado: Optional[str] = Query(None, description="pendiente, completado, retraso"),
    busqueda: Optional[str] = Query(None, description="Buscar por número orden o autorización"),
    limit: int = Query(50, le=200),
    user: dict = Depends(require_admin)
):
    """Lista envíos pendientes y completados"""
    try:
        now = datetime.now(timezone.utc)
        hace_48h = now - timedelta(hours=48)
        
        # Base query - solo órdenes que han sido reparadas
        query = {
            "$or": [
                {"estado": {"$in": ["reparado", "validacion", "enviado"]}},
                {"fecha_fin_reparacion": {"$ne": None, "$exists": True}}
            ]
        }
        
        # Filtro por estado
        if estado == "pendiente":
            query["estado"] = {"$in": ["reparado", "validacion"]}
            query["$and"] = query.get("$and", []) + [
                {"$or": [
                    {"fecha_enviado": None},
                    {"fecha_enviado": {"$exists": False}}
                ]}
            ]
        elif estado == "completado":
            query["fecha_enviado"] = {"$ne": None, "$exists": True}
        elif estado == "retraso":
            # Envíos en retraso se calculan después
            pass
        
        # Búsqueda
        if busqueda:
            if "$or" not in query:
                query["$or"] = []
            else:
                # Mover el $or existente a $and
                existing_or = query.pop("$or")
                query["$and"] = query.get("$and", []) + [{"$or": existing_or}]
            
            query["$and"] = query.get("$and", []) + [
                {"$or": [
                    {"numero_orden": {"$regex": busqueda, "$options": "i"}},
                    {"numero_autorizacion": {"$regex": busqueda, "$options": "i"}}
                ]}
            ]
        
        ordenes = await db.ordenes.find(
            query,
            {"_id": 0}
        ).sort("fecha_fin_reparacion", -1).limit(limit).to_list(limit)
        
        # Obtener clientes
        cliente_ids = [o.get("cliente_id") for o in ordenes if o.get("cliente_id")]
        clientes = {}
        if cliente_ids:
            clientes_docs = await db.clientes.find(
                {"id": {"$in": cliente_ids}},
                {"_id": 0, "id": 1, "nombre": 1, "apellidos": 1, "telefono": 1, "direccion": 1, "ciudad": 1, "codigo_postal": 1}
            ).to_list(len(cliente_ids))
            clientes = {c["id"]: c for c in clientes_docs}
        
        # Construir resultado
        items = []
        for orden in ordenes:
            cliente = clientes.get(orden.get("cliente_id"), {})
            
            # Calcular horas transcurridas desde fin reparación
            horas = None
            en_retraso = False
            fecha_fin_rep = orden.get("fecha_fin_reparacion")
            fecha_enviado = orden.get("fecha_enviado")
            
            if fecha_fin_rep:
                try:
                    if isinstance(fecha_fin_rep, str):
                        fin_dt = datetime.fromisoformat(fecha_fin_rep.replace('Z', '+00:00'))
                    else:
                        fin_dt = fecha_fin_rep
                    
                    if fecha_enviado:
                        if isinstance(fecha_enviado, str):
                            enviado_dt = datetime.fromisoformat(fecha_enviado.replace('Z', '+00:00'))
                        else:
                            enviado_dt = fecha_enviado
                        horas = (enviado_dt - fin_dt).total_seconds() / 3600
                    else:
                        horas = (now - fin_dt).total_seconds() / 3600
                        en_retraso = horas > 48
                except:
                    pass
            
            # Filtrar por retraso si se solicita
            if estado == "retraso" and not en_retraso:
                continue
            
            items.append({
                "orden_id": orden.get("id"),
                "numero_orden": orden.get("numero_orden"),
                "numero_autorizacion": orden.get("numero_autorizacion"),
                "cliente_nombre": f"{cliente.get('nombre', '')} {cliente.get('apellidos', '')}".strip() or "Sin cliente",
                "cliente_telefono": cliente.get("telefono"),
                "dispositivo_modelo": orden.get("dispositivo", {}).get("modelo", "N/A"),
                "estado": "completado" if fecha_enviado else "pendiente",
                "tipo": "envio",
                "codigo_tracking": orden.get("codigo_recogida_salida") or orden.get("codigo_envio"),
                "fecha_solicitud": fecha_fin_rep,
                "fecha_completado": fecha_enviado,
                "horas_transcurridas": round(horas, 1) if horas else None,
                "en_retraso": en_retraso,
                "direccion": cliente.get("direccion"),
                "ciudad": f"{cliente.get('codigo_postal', '')} {cliente.get('ciudad', '')}".strip()
            })
        
        return items
        
    except Exception as e:
        logger.error(f"Error listando envíos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logistica/orden/{orden_id}")
async def obtener_logistica_orden(orden_id: str, user: dict = Depends(require_auth)):
    """Obtiene información de logística de una orden específica"""
    try:
        orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
        if not orden:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
        
        cliente = None
        if orden.get("cliente_id"):
            cliente = await db.clientes.find_one(
                {"id": orden["cliente_id"]},
                {"_id": 0}
            )
        
        now = datetime.now(timezone.utc)
        
        # Info de recogida
        recogida = {
            "codigo": orden.get("codigo_recogida_entrada"),
            "fecha_solicitud": orden.get("created_at"),
            "fecha_completado": orden.get("fecha_recibida_centro"),
            "estado": "completada" if orden.get("fecha_recibida_centro") else "pendiente",
            "datos": orden.get("datos_recogida"),
            "horas_transcurridas": None,
            "en_retraso": False
        }
        
        if recogida["fecha_solicitud"] and not recogida["fecha_completado"]:
            try:
                created_dt = datetime.fromisoformat(recogida["fecha_solicitud"].replace('Z', '+00:00'))
                horas = (now - created_dt).total_seconds() / 3600
                recogida["horas_transcurridas"] = round(horas, 1)
                recogida["en_retraso"] = horas > 48
            except:
                pass
        
        # Info de envío
        envio = {
            "codigo": orden.get("codigo_recogida_salida") or orden.get("codigo_envio"),
            "fecha_solicitud": orden.get("fecha_fin_reparacion"),
            "fecha_completado": orden.get("fecha_enviado"),
            "estado": "completado" if orden.get("fecha_enviado") else ("pendiente" if orden.get("fecha_fin_reparacion") else "no_aplica"),
            "datos": orden.get("datos_envio"),
            "horas_transcurridas": None,
            "en_retraso": False
        }
        
        if envio["fecha_solicitud"] and not envio["fecha_completado"]:
            try:
                fin_dt = datetime.fromisoformat(envio["fecha_solicitud"].replace('Z', '+00:00'))
                horas = (now - fin_dt).total_seconds() / 3600
                envio["horas_transcurridas"] = round(horas, 1)
                envio["en_retraso"] = horas > 48
            except:
                pass
        
        return {
            "orden": {
                "id": orden.get("id"),
                "numero_orden": orden.get("numero_orden"),
                "numero_autorizacion": orden.get("numero_autorizacion"),
                "estado": orden.get("estado"),
                "dispositivo": orden.get("dispositivo", {}).get("modelo")
            },
            "cliente": {
                "nombre": f"{cliente.get('nombre', '')} {cliente.get('apellidos', '')}".strip() if cliente else "Sin cliente",
                "telefono": cliente.get("telefono") if cliente else None,
                "direccion": cliente.get("direccion") if cliente else None,
                "ciudad": f"{cliente.get('codigo_postal', '')} {cliente.get('ciudad', '')}".strip() if cliente else None
            },
            "recogida": recogida,
            "envio": envio
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo logística orden: {e}")
        raise HTTPException(status_code=500, detail=str(e))

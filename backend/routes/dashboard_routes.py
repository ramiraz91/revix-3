"""
Rutas de Dashboard: estadísticas, métricas avanzadas, alertas, operativo, técnico.
Extraído de server.py durante refactorización.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timezone, timedelta

from config import db, logger
from auth import require_auth, require_admin

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard/stats")
async def obtener_estadisticas():
    """Dashboard stats - OPTIMIZADO con aggregation pipeline"""
    now = datetime.now(timezone.utc)
    hace_30_dias = now - timedelta(days=30)
    hace_7_dias = now - timedelta(days=7)
    
    # Pipeline de agregación para obtener todo en una sola query
    pipeline = [
        {
            "$facet": {
                "por_estado": [
                    {"$group": {"_id": "$estado", "count": {"$sum": 1}}}
                ],
                "totales": [
                    {"$count": "total"}
                ],
                "ultimo_mes": [
                    {"$match": {"created_at": {"$gte": hace_30_dias.isoformat()}}},
                    {"$count": "count"}
                ],
                "ultima_semana": [
                    {"$match": {"created_at": {"$gte": hace_7_dias.isoformat()}}},
                    {"$count": "count"}
                ],
                "bloqueadas": [
                    {"$match": {"bloqueada": True}},
                    {"$count": "count"}
                ]
            }
        }
    ]
    
    result = await db.ordenes.aggregate(pipeline).to_list(1)
    data = result[0] if result else {}
    
    # Procesar resultados
    ordenes_por_estado = {}
    for item in data.get("por_estado", []):
        ordenes_por_estado[item["_id"] or "unknown"] = item["count"]
    
    # Manejo seguro de listas vacías (MongoDB $count devuelve [] si no hay documentos)
    totales_list = data.get("totales", [])
    total_ordenes = totales_list[0].get("total", 0) if totales_list else 0
    
    ultimo_mes_list = data.get("ultimo_mes", [])
    ordenes_ultimo_mes = ultimo_mes_list[0].get("count", 0) if ultimo_mes_list else 0
    
    ultima_semana_list = data.get("ultima_semana", [])
    ordenes_ultima_semana = ultima_semana_list[0].get("count", 0) if ultima_semana_list else 0
    
    bloqueadas_list = data.get("bloqueadas", [])
    ordenes_bloqueadas = bloqueadas_list[0].get("count", 0) if bloqueadas_list else 0
    
    # Conteos simples en paralelo (son rápidos)
    total_clientes = await db.clientes.count_documents({})
    total_repuestos = await db.repuestos.count_documents({})
    notificaciones_pendientes = await db.notificaciones.count_documents({"leida": False})
    repuestos_bajo_stock = await db.repuestos.count_documents({"$expr": {"$lte": ["$stock", "$stock_minimo"]}})
    
    ordenes_completadas = ordenes_por_estado.get("enviado", 0)
    ordenes_canceladas = ordenes_por_estado.get("cancelado", 0)
    tasa_completado = round((ordenes_completadas / total_ordenes * 100) if total_ordenes > 0 else 0, 1)
    
    return {
        "total_ordenes": total_ordenes,
        "ordenes_por_estado": ordenes_por_estado,
        "total_clientes": total_clientes,
        "total_repuestos": total_repuestos,
        "notificaciones_pendientes": notificaciones_pendientes,
        "ordenes_ultimo_mes": ordenes_ultimo_mes,
        "ordenes_ultima_semana": ordenes_ultima_semana,
        "tasa_completado": tasa_completado,
        "ordenes_canceladas": ordenes_canceladas,
        "ordenes_garantia_activas": 0,
        "repuestos_bajo_stock": repuestos_bajo_stock,
        "ordenes_bloqueadas": ordenes_bloqueadas
    }

@router.get("/dashboard/metricas-avanzadas")
async def obtener_metricas_avanzadas(user: dict = Depends(require_admin)):
    """Métricas avanzadas - OPTIMIZADO con aggregation pipelines"""
    from collections import defaultdict
    now = datetime.now(timezone.utc)
    hace_30_dias = now - timedelta(days=30)
    hace_7_dias = now - timedelta(days=7)
    
    # Pipeline optimizado para obtener métricas sin cargar todas las órdenes
    pipeline = [
        {
            "$facet": {
                # Órdenes por día (últimos 30 días)
                "ordenes_por_dia": [
                    {"$match": {"created_at": {"$gte": hace_30_dias.isoformat()}}},
                    {"$addFields": {
                        "fecha": {"$substr": ["$created_at", 0, 10]}
                    }},
                    {"$group": {"_id": "$fecha", "ordenes": {"$sum": 1}}},
                    {"$sort": {"_id": 1}},
                    {"$project": {"fecha": "$_id", "ordenes": 1, "_id": 0}}
                ],
                # Órdenes por estado
                "ordenes_por_estado": [
                    {"$group": {"_id": "$estado", "cantidad": {"$sum": 1}}},
                    {"$project": {"estado": "$_id", "cantidad": 1, "_id": 0}}
                ],
                # Totales
                "totales": [
                    {"$group": {
                        "_id": None,
                        "total": {"$sum": 1},
                        "completadas": {"$sum": {"$cond": [{"$eq": ["$estado", "enviado"]}, 1, 0]}},
                        "canceladas": {"$sum": {"$cond": [{"$eq": ["$estado", "cancelado"]}, 1, 0]}},
                        "garantias": {"$sum": {"$cond": ["$es_garantia", 1, 0]}}
                    }}
                ],
                # Últimos 7 días
                "ultimos_7": [
                    {"$match": {"created_at": {"$gte": hace_7_dias.isoformat()}}},
                    {"$count": "count"}
                ],
                # Últimos 30 días
                "ultimos_30": [
                    {"$match": {"created_at": {"$gte": hace_30_dias.isoformat()}}},
                    {"$count": "count"}
                ],
                # Top repuestos (de las últimas 100 órdenes con materiales)
                "top_repuestos": [
                    {"$match": {"materiales": {"$exists": True, "$ne": []}}},
                    {"$sort": {"created_at": -1}},
                    {"$limit": 100},
                    {"$unwind": "$materiales"},
                    {"$group": {
                        "_id": "$materiales.nombre",
                        "cantidad": {"$sum": {"$ifNull": ["$materiales.cantidad", 1]}}
                    }},
                    {"$sort": {"cantidad": -1}},
                    {"$limit": 5},
                    {"$project": {"nombre": "$_id", "cantidad": 1, "_id": 0}}
                ]
            }
        }
    ]
    
    result = await db.ordenes.aggregate(pipeline).to_list(1)
    data = result[0] if result else {}
    
    totales = data.get("totales", [{}])[0] if data.get("totales") else {}
    total = totales.get("total", 0)
    completadas = totales.get("completadas", 0)
    canceladas = totales.get("canceladas", 0)
    garantias = totales.get("garantias", 0)
    en_proceso = total - completadas - canceladas
    
    # Manejo seguro de listas vacías
    ultimos_7_list = data.get("ultimos_7", [])
    ultimos_7 = ultimos_7_list[0].get("count", 0) if ultimos_7_list else 0
    
    ultimos_30_list = data.get("ultimos_30", [])
    ultimos_30 = ultimos_30_list[0].get("count", 0) if ultimos_30_list else 0
    
    return {
        "ordenes_por_dia": data.get("ordenes_por_dia", []),
        "ordenes_por_estado": data.get("ordenes_por_estado", []),
        "ratios": {
            "total": total,
            "completadas": completadas,
            "canceladas": canceladas,
            "en_proceso": en_proceso,
            "garantias": garantias,
            "ratio_cancelacion": round((canceladas / total * 100) if total > 0 else 0, 1),
            "ratio_completado": round((completadas / total * 100) if total > 0 else 0, 1)
        },
        "tiempos": {
            "promedio_reparacion_horas": 0,
            "promedio_total_horas": 0,
            "promedio_reparacion_dias": 0,
            "promedio_total_dias": 0
        },
        "comparativa": {
            "ultimos_7_dias": ultimos_7,
            "total_30_dias": ultimos_30
        },
        "top_repuestos": data.get("top_repuestos", [])
    }

@router.get("/dashboard/alertas-stock")
async def obtener_alertas_stock(user: dict = Depends(require_admin)):
    repuestos = await db.repuestos.find({}, {"_id": 0}).to_list(1000)
    alertas = []
    for rep in repuestos:
        stock = rep.get('stock', 0)
        stock_minimo = rep.get('stock_minimo', 5)
        if stock <= stock_minimo:
            alertas.append({"id": rep.get('id'), "nombre": rep.get('nombre'), "stock": stock, "stock_minimo": stock_minimo, "nivel": "critico" if stock == 0 else "bajo", "proveedor_id": rep.get('proveedor_id')})
    alertas.sort(key=lambda x: (0 if x['nivel'] == 'critico' else 1, x['stock']))
    return {"alertas": alertas, "total_critico": len([a for a in alertas if a['nivel'] == 'critico']), "total_bajo": len([a for a in alertas if a['nivel'] == 'bajo'])}

@router.get("/dashboard/ordenes-compra-urgentes")
async def obtener_ordenes_compra_urgentes(user: dict = Depends(require_admin)):
    ordenes = await db.ordenes_compra.find({"estado": {"$in": ["pendiente", "aprobada"]}}, {"_id": 0}).sort("created_at", -1).to_list(50)
    for oc in ordenes:
        orden_trabajo = await db.ordenes.find_one({"id": oc.get('orden_trabajo_id')}, {"_id": 0, "numero_orden": 1, "dispositivo": 1})
        oc['orden_trabajo'] = {"numero_orden": orden_trabajo.get('numero_orden', 'N/A') if orden_trabajo else 'N/A', "dispositivo": orden_trabajo.get('dispositivo', {}).get('modelo', 'N/A') if orden_trabajo else 'N/A'}
    return {"total_pendientes": len([o for o in ordenes if o['estado'] == 'pendiente']), "ordenes": ordenes}


@router.get("/dashboard/operativo")
async def obtener_dashboard_operativo(user: dict = Depends(require_auth)):
    """
    Dashboard operativo completo con:
    - Órdenes en taller por subestado
    - Órdenes con demora (4+ días sin cambio)
    - Últimos reparados
    - Últimos enviados
    - Órdenes por recibir
    - Actividad reciente (cambios hoy/ayer)
    - KPIs de tiempo y eficiencia
    """
    now = datetime.now(timezone.utc)
    hoy = now.replace(hour=0, minute=0, second=0, microsecond=0)
    ayer = hoy - timedelta(days=1)
    hace_4_dias = now - timedelta(days=4)
    hace_7_dias = now - timedelta(days=7)
    hace_30_dias = now - timedelta(days=30)
    
    # Estados considerados "en taller" (trabajo activo)
    ESTADOS_EN_TALLER = ["recibida", "en_taller", "re_presupuestar", "validacion"]
    ESTADOS_PENDIENTES = ["pendiente_recibir"]
    ESTADOS_FINALIZADOS = ["reparado", "enviado"]
    
    # Pipeline principal para obtener todas las métricas
    pipeline = [
        {
            "$facet": {
                # Órdenes en taller por estado
                "en_taller_por_estado": [
                    {"$match": {"estado": {"$in": ESTADOS_EN_TALLER}}},
                    {"$group": {"_id": "$estado", "count": {"$sum": 1}}}
                ],
                
                # Órdenes pendientes de recibir
                "pendientes_recibir": [
                    {"$match": {"estado": "pendiente_recibir"}},
                    {"$sort": {"created_at": -1}},
                    {"$limit": 10},
                    {"$project": {
                        "_id": 0, "id": 1, "numero_orden": 1, "dispositivo": 1,
                        "created_at": 1, "agencia_envio": 1, "codigo_recogida_entrada": 1
                    }}
                ],
                
                # Órdenes con demora (4+ días sin cambio de estado)
                "con_demora": [
                    {"$match": {
                        "estado": {"$in": ESTADOS_EN_TALLER},
                        "updated_at": {"$lte": hace_4_dias.isoformat()}
                    }},
                    {"$sort": {"updated_at": 1}},
                    {"$limit": 15},
                    {"$project": {
                        "_id": 0, "id": 1, "numero_orden": 1, "estado": 1,
                        "dispositivo": 1, "created_at": 1, "updated_at": 1
                    }}
                ],
                
                # Últimos reparados (últimos 10)
                "ultimos_reparados": [
                    {"$match": {"estado": "reparado"}},
                    {"$sort": {"updated_at": -1}},
                    {"$limit": 10},
                    {"$project": {
                        "_id": 0, "id": 1, "numero_orden": 1, "dispositivo": 1,
                        "updated_at": 1, "created_at": 1
                    }}
                ],
                
                # Últimos enviados (últimos 10)
                "ultimos_enviados": [
                    {"$match": {"estado": "enviado"}},
                    {"$sort": {"updated_at": -1}},
                    {"$limit": 10},
                    {"$project": {
                        "_id": 0, "id": 1, "numero_orden": 1, "dispositivo": 1,
                        "updated_at": 1, "agencia_envio": 1, "codigo_seguimiento_salida": 1
                    }}
                ],
                
                # Cambios de hoy
                "cambios_hoy": [
                    {"$match": {"updated_at": {"$gte": hoy.isoformat()}}},
                    {"$count": "total"}
                ],
                
                # Cambios de ayer
                "cambios_ayer": [
                    {"$match": {
                        "updated_at": {"$gte": ayer.isoformat(), "$lt": hoy.isoformat()}
                    }},
                    {"$count": "total"}
                ],
                
                # Totales por estado (para gráfico)
                "totales_por_estado": [
                    {"$group": {"_id": "$estado", "count": {"$sum": 1}}}
                ],
                
                # Métricas de tiempo (TODAS las órdenes completadas - enviadas)
                "metricas_tiempo": [
                    {"$match": {
                        "estado": "enviado"
                    }},
                    {"$sort": {"updated_at": -1}},
                    {"$limit": 1000},
                    {"$project": {
                        "_id": 0,
                        "created_at": 1,
                        "updated_at": 1,
                        "fecha_recibida_centro": 1,
                        "fecha_inicio_reparacion": 1,
                        "fecha_fin_reparacion": 1,
                        "fecha_enviado": 1,
                        "historial_estados": 1
                    }}
                ],
                
                # Órdenes creadas últimos 7 días por día
                "ordenes_semana": [
                    {"$match": {"created_at": {"$gte": hace_7_dias.isoformat()}}},
                    {"$addFields": {"fecha": {"$substr": ["$created_at", 0, 10]}}},
                    {"$group": {"_id": "$fecha", "total": {"$sum": 1}}},
                    {"$sort": {"_id": 1}}
                ],
                
                # Total en taller
                "total_en_taller": [
                    {"$match": {"estado": {"$in": ESTADOS_EN_TALLER}}},
                    {"$count": "total"}
                ],
                
                # Total pendientes
                "total_pendientes": [
                    {"$match": {"estado": {"$in": ESTADOS_PENDIENTES}}},
                    {"$count": "total"}
                ],
                
                # Total reparados (listos para enviar)
                "total_reparados": [
                    {"$match": {"estado": "reparado"}},
                    {"$count": "total"}
                ],
                
                # Garantías activas
                "garantias_activas": [
                    {"$match": {"estado": "garantia"}},
                    {"$count": "total"}
                ],
                
                # Total general de órdenes
                "total_general": [
                    {"$count": "total"}
                ],
                
                # Total enviados
                "total_enviados": [
                    {"$match": {"estado": "enviado"}},
                    {"$count": "total"}
                ]
            }
        }
    ]
    
    result = await db.ordenes.aggregate(pipeline).to_list(1)
    data = result[0] if result else {}
    
    # Procesar subestados en taller
    en_taller_estados = {}
    total_en_taller = 0
    for item in data.get("en_taller_por_estado", []):
        estado = item["_id"]
        count = item["count"]
        en_taller_estados[estado] = count
        total_en_taller += count
    
    # Procesar totales por estado
    totales_estado = {}
    for item in data.get("totales_por_estado", []):
        totales_estado[item["_id"] or "desconocido"] = item["count"]
    
    # Calcular tiempos promedio de reparación
    # Usar TODAS las órdenes enviadas con cualquier dato de fecha disponible
    tiempos = data.get("metricas_tiempo", [])
    tiempos_reparacion = []
    tiempos_totales = []  # Desde creación hasta envío
    
    for orden in tiempos:
        try:
            historial = orden.get("historial_estados", [])
            fecha_inicio = None
            fecha_reparado = None
            fecha_creacion = None
            fecha_envio = None
            
            # 1. Intentar obtener fecha_creacion
            if orden.get("created_at"):
                try:
                    fecha_creacion = datetime.fromisoformat(orden["created_at"].replace("Z", "+00:00"))
                except Exception:
                    pass
            
            # 2. Intentar obtener fecha de envío (fin del proceso)
            if orden.get("fecha_enviado"):
                try:
                    fecha_envio = datetime.fromisoformat(orden["fecha_enviado"].replace("Z", "+00:00"))
                except Exception:
                    pass
            elif orden.get("updated_at"):
                try:
                    fecha_envio = datetime.fromisoformat(orden["updated_at"].replace("Z", "+00:00"))
                except Exception:
                    pass
            
            # 3. Buscar en historial
            for h in historial:
                estado = h.get("estado")
                fecha_str = h.get("fecha", "")
                if not fecha_str:
                    continue
                
                try:
                    fecha_parsed = datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
                except Exception:
                    continue
                
                # Fecha de inicio = primer estado de trabajo
                if not fecha_inicio and estado in ["recibida", "en_taller", "en_reparacion", "re_presupuestar", "validacion"]:
                    fecha_inicio = fecha_parsed
                
                # Fecha de reparado (última ocurrencia)
                if estado == "reparado":
                    fecha_reparado = fecha_parsed
                
                # Fecha de envío si no la tenemos
                if estado == "enviado" and not fecha_envio:
                    fecha_envio = fecha_parsed
            
            # 4. Alternativas para fecha_inicio
            if not fecha_inicio and orden.get("fecha_recibida_centro"):
                try:
                    fecha_inicio = datetime.fromisoformat(orden["fecha_recibida_centro"].replace("Z", "+00:00"))
                except Exception:
                    pass
            
            if not fecha_inicio and orden.get("fecha_inicio_reparacion"):
                try:
                    fecha_inicio = datetime.fromisoformat(orden["fecha_inicio_reparacion"].replace("Z", "+00:00"))
                except Exception:
                    pass
            
            # 5. Si no hay fecha_inicio, usar fecha_creacion
            if not fecha_inicio and fecha_creacion:
                fecha_inicio = fecha_creacion
            
            # 6. Calcular tiempo de reparación (inicio → reparado o envío)
            fecha_fin = fecha_reparado or fecha_envio
            if fecha_inicio and fecha_fin:
                diff_horas = (fecha_fin - fecha_inicio).total_seconds() / 3600
                if 0 < diff_horas < 2160:  # Máximo 90 días, mínimo 0
                    tiempos_reparacion.append(diff_horas)
            
            # 7. Calcular tiempo total (creación → envío)
            if fecha_creacion and fecha_envio:
                diff_total = (fecha_envio - fecha_creacion).total_seconds() / 3600
                if 0 < diff_total < 2160:  # Máximo 90 días
                    tiempos_totales.append(diff_total)
                    
        except Exception as e:
            pass
    
    # Usar tiempos_totales si hay más datos, sino tiempos_reparacion
    tiempos_usar = tiempos_totales if len(tiempos_totales) > len(tiempos_reparacion) else tiempos_reparacion
    promedio_horas = sum(tiempos_usar) / len(tiempos_usar) if tiempos_usar else 0
    promedio_dias = promedio_horas / 24
    
    # Helper para extraer conteo seguro
    def safe_count(key):
        lst = data.get(key, [])
        return lst[0].get("total", 0) if lst else 0
    
    # Calcular días de demora para órdenes con demora
    ordenes_demora = data.get("con_demora", [])
    for orden in ordenes_demora:
        try:
            updated = datetime.fromisoformat(orden.get("updated_at", "").replace("Z", "+00:00"))
            dias_sin_cambio = (now - updated).days
            orden["dias_demora"] = dias_sin_cambio
        except Exception:
            orden["dias_demora"] = 0
    
    return {
        # KPIs principales
        "kpis": {
            "total_ordenes": safe_count("total_general"),
            "total_enviados": safe_count("total_enviados"),
            "total_en_taller": total_en_taller,
            "total_pendientes_recibir": safe_count("total_pendientes"),
            "total_reparados": safe_count("total_reparados"),
            "garantias_activas": safe_count("garantias_activas"),
            "con_demora": len(ordenes_demora),
            "cambios_hoy": safe_count("cambios_hoy"),
            "cambios_ayer": safe_count("cambios_ayer")
        },
        
        # Desglose de órdenes en taller
        "en_taller": {
            "total": total_en_taller,
            "por_estado": en_taller_estados,
            "detalle": {
                "recibidas": en_taller_estados.get("recibida", 0),
                "en_reparacion": en_taller_estados.get("en_taller", 0),
                "re_presupuestar": en_taller_estados.get("re_presupuestar", 0),
                "validacion": en_taller_estados.get("validacion", 0)
            }
        },
        
        # Listas de órdenes
        "ordenes": {
            "pendientes_recibir": data.get("pendientes_recibir", []),
            "con_demora": ordenes_demora,
            "ultimos_reparados": data.get("ultimos_reparados", []),
            "ultimos_enviados": data.get("ultimos_enviados", [])
        },
        
        # Métricas de tiempo
        "tiempos": {
            "promedio_total_horas": round(promedio_horas, 1),
            "promedio_total_dias": round(promedio_dias, 1),
            "ordenes_analizadas": len(tiempos_usar),
            "total_enviadas": len(tiempos),
            "con_datos_tiempo": len(tiempos_usar),
            "sin_datos_tiempo": len(tiempos) - len(tiempos_usar)
        },
        
        # Datos para gráficos
        "graficos": {
            "por_estado": totales_estado,
            "ordenes_semana": [
                {"fecha": item["_id"], "total": item["total"]} 
                for item in data.get("ordenes_semana", [])
            ]
        },
        
        # Timestamp
        "generado_at": now.isoformat()
    }


# ==================== DASHBOARD TÉCNICO ====================

@router.get("/dashboard/tecnico")
async def obtener_dashboard_tecnico(user: dict = Depends(require_auth)):
    """
    Dashboard específico para técnicos con:
    - Sus últimas órdenes reparadas
    - Órdenes asignadas actualmente
    - Métricas de tiempo personales
    """
    tecnico_email = user.get("email", "")
    now = datetime.now(timezone.utc)
    hace_30_dias = now - timedelta(days=30)
    
    # Pipeline para métricas del técnico
    pipeline = [
        {
            "$facet": {
                # Órdenes reparadas por este técnico (últimas 20)
                "mis_reparados": [
                    {"$match": {
                        "tecnico_asignado": tecnico_email,
                        "estado": {"$in": ["reparado", "enviado"]}
                    }},
                    {"$sort": {"updated_at": -1}},
                    {"$limit": 20},
                    {"$project": {
                        "_id": 0, "id": 1, "numero_orden": 1, "dispositivo": 1,
                        "estado": 1, "updated_at": 1, "created_at": 1,
                        "historial_estados": 1
                    }}
                ],
                
                # Órdenes asignadas actualmente (en taller)
                "mis_asignadas": [
                    {"$match": {
                        "tecnico_asignado": tecnico_email,
                        "estado": {"$in": ["recibida", "en_taller", "re_presupuestar", "validacion"]}
                    }},
                    {"$sort": {"created_at": -1}},
                    {"$project": {
                        "_id": 0, "id": 1, "numero_orden": 1, "dispositivo": 1,
                        "estado": 1, "updated_at": 1, "created_at": 1
                    }}
                ],
                
                # Total reparadas este mes
                "total_reparadas_mes": [
                    {"$match": {
                        "tecnico_asignado": tecnico_email,
                        "estado": {"$in": ["reparado", "enviado"]},
                        "updated_at": {"$gte": hace_30_dias.isoformat()}
                    }},
                    {"$count": "total"}
                ],
                
                # Métricas de tiempo (últimas 50 órdenes completadas)
                "metricas_tiempo": [
                    {"$match": {
                        "tecnico_asignado": tecnico_email,
                        "estado": {"$in": ["reparado", "enviado"]},
                        "historial_estados": {"$exists": True, "$ne": []}
                    }},
                    {"$sort": {"updated_at": -1}},
                    {"$limit": 50},
                    {"$project": {
                        "_id": 0,
                        "created_at": 1,
                        "updated_at": 1,
                        "historial_estados": 1
                    }}
                ]
            }
        }
    ]
    
    result = await db.ordenes.aggregate(pipeline).to_list(1)
    data = result[0] if result else {}
    
    # Calcular tiempo promedio de reparación
    tiempos_reparacion = []
    for orden in data.get("metricas_tiempo", []):
        try:
            historial = orden.get("historial_estados", [])
            fecha_recibida = None
            fecha_reparado = None
            for h in historial:
                fecha_str = h.get("fecha", "")
                if not fecha_str:
                    continue
                if h.get("estado") == "recibida" and not fecha_recibida:
                    fecha_recibida = datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
                if h.get("estado") == "reparado" and not fecha_reparado:
                    fecha_reparado = datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
            if fecha_recibida and fecha_reparado:
                diff = (fecha_reparado - fecha_recibida).total_seconds() / 3600
                # Solo incluir si es positivo y razonable (menos de 30 días = 720 horas)
                if 0 < diff < 720:
                    tiempos_reparacion.append(diff)
        except Exception:
            pass
    
    promedio_horas = sum(tiempos_reparacion) / len(tiempos_reparacion) if tiempos_reparacion else 0
    promedio_dias = promedio_horas / 24
    
    def safe_count(key):
        lst = data.get(key, [])
        return lst[0].get("total", 0) if lst else 0
    
    return {
        "tecnico": {
            "email": tecnico_email,
            "nombre": user.get("nombre", tecnico_email)
        },
        "kpis": {
            "total_reparadas_mes": safe_count("total_reparadas_mes"),
            "asignadas_actualmente": len(data.get("mis_asignadas", [])),
            "promedio_horas": round(promedio_horas, 1),
            "promedio_dias": round(promedio_dias, 1)
        },
        "ordenes": {
            "asignadas": data.get("mis_asignadas", []),
            "ultimos_reparados": data.get("mis_reparados", [])
        },
        "generado_at": now.isoformat()
    }



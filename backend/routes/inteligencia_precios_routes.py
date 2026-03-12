"""
Rutas para el Sistema de Inteligencia de Precios
Captura automática de datos de mercado y recomendaciones de precios
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
import re

from config import db, logger
from auth import require_admin

router = APIRouter(prefix="/inteligencia-precios", tags=["inteligencia-precios"])


# ==================== MODELOS ====================

class RegistroMercado(BaseModel):
    codigo_siniestro: str
    dispositivo_marca: Optional[str] = None
    dispositivo_modelo: Optional[str] = None
    tipo_reparacion: Optional[str] = None
    fecha_cierre: Optional[str] = None
    resultado: str  # "ganado", "perdido", "cancelado_cliente", "cancelado_otros"
    
    mi_precio: Optional[float] = None
    precio_ganador: Optional[float] = None
    ganador_nombre: Optional[str] = None
    
    num_competidores: int = 0
    precio_minimo: Optional[float] = None
    precio_maximo: Optional[float] = None
    precio_medio: Optional[float] = None
    
    competidores: List[dict] = []  # [{nombre, precio, posicion}]
    
    # Metadata
    mi_tiempo_respuesta_horas: Optional[float] = None
    

# ==================== CAPTURA DE DATOS ====================

@router.post("/registrar-resultado")
async def registrar_resultado_mercado(data: RegistroMercado, user: dict = Depends(require_admin)):
    """
    Registra el resultado de un presupuesto cerrado.
    Se llama automáticamente cuando se detecta un cambio de estado.
    """
    try:
        # Verificar si ya existe registro para este siniestro
        existente = await db.historial_mercado.find_one(
            {"codigo_siniestro": data.codigo_siniestro},
            {"_id": 0}
        )
        
        registro = {
            "codigo_siniestro": data.codigo_siniestro,
            "dispositivo_marca": data.dispositivo_marca,
            "dispositivo_modelo": data.dispositivo_modelo,
            "dispositivo_key": f"{data.dispositivo_marca or ''} {data.dispositivo_modelo or ''}".strip().upper(),
            "tipo_reparacion": data.tipo_reparacion,
            "tipo_reparacion_key": normalizar_tipo_reparacion(data.tipo_reparacion),
            "fecha_cierre": data.fecha_cierre or datetime.now(timezone.utc).isoformat(),
            "resultado": data.resultado,
            
            "mi_precio": data.mi_precio,
            "precio_ganador": data.precio_ganador,
            "ganador_nombre": data.ganador_nombre,
            "ganador_nombre_key": (data.ganador_nombre or "").upper(),
            
            "num_competidores": data.num_competidores,
            "precio_minimo": data.precio_minimo,
            "precio_maximo": data.precio_maximo,
            "precio_medio": data.precio_medio,
            
            "competidores": data.competidores,
            "mi_tiempo_respuesta_horas": data.mi_tiempo_respuesta_horas,
            
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if existente:
            await db.historial_mercado.update_one(
                {"codigo_siniestro": data.codigo_siniestro},
                {"$set": registro}
            )
            return {"message": "Registro actualizado", "codigo": data.codigo_siniestro}
        else:
            registro["created_at"] = datetime.now(timezone.utc).isoformat()
            await db.historial_mercado.insert_one(registro)
            return {"message": "Registro creado", "codigo": data.codigo_siniestro}
            
    except Exception as e:
        logger.error(f"Error registrando resultado: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def normalizar_tipo_reparacion(tipo: Optional[str]) -> str:
    """Normaliza el tipo de reparación para búsquedas consistentes"""
    if not tipo:
        return "OTROS"
    
    tipo_upper = tipo.upper()
    
    # Mapeo de palabras clave a categorías
    if any(x in tipo_upper for x in ["PANTALLA", "LCD", "DISPLAY", "OLED", "INCELL"]):
        return "PANTALLA"
    if any(x in tipo_upper for x in ["BATERIA", "BATTERY"]):
        return "BATERIA"
    if any(x in tipo_upper for x in ["CAMARA", "CAMERA", "TRASERA", "FRONTAL"]):
        return "CAMARA"
    if any(x in tipo_upper for x in ["TAPA", "BACK", "COVER", "CARCASA"]):
        return "TAPA_TRASERA"
    if any(x in tipo_upper for x in ["CONECTOR", "CARGA", "CHARGING", "PUERTO"]):
        return "CONECTOR_CARGA"
    if any(x in tipo_upper for x in ["PLACA", "BOARD", "MOTHER"]):
        return "PLACA_BASE"
    if any(x in tipo_upper for x in ["ALTAVOZ", "SPEAKER", "AURICULAR"]):
        return "AUDIO"
    if any(x in tipo_upper for x in ["BOTON", "BUTTON", "POWER", "VOLUMEN"]):
        return "BOTONES"
    
    return "OTROS"


# ==================== ANALYTICS / DASHBOARD ====================

@router.get("/dashboard")
async def obtener_dashboard(user: dict = Depends(require_admin)):
    """Obtiene todos los datos para el dashboard de inteligencia - MEJORADO con métricas reales del CRM"""
    try:
        # Fechas para filtros
        ahora = datetime.now(timezone.utc)
        hace_30_dias = (ahora - timedelta(days=30)).isoformat()
        hace_90_dias = (ahora - timedelta(days=90)).isoformat()
        
        # =============== MÉTRICAS REALES DEL CRM (ÓRDENES INSURAMA) ===============
        
        # Total de órdenes de Insurama
        total_ordenes_insurama = await db.ordenes.count_documents({"origen": "insurama"})
        ordenes_insurama_30d = await db.ordenes.count_documents({
            "origen": "insurama",
            "created_at": {"$gte": hace_30_dias}
        })
        
        # Órdenes por estado
        ordenes_cerradas = await db.ordenes.count_documents({"origen": "insurama", "estado": "enviado"})
        ordenes_en_proceso = await db.ordenes.count_documents({
            "origen": "insurama", 
            "estado": {"$in": ["recibida", "en_taller", "reparado", "validacion"]}
        })
        ordenes_pendientes = await db.ordenes.count_documents({
            "origen": "insurama", 
            "estado": "pendiente_recibir"
        })
        
        # Calcular ingresos, gastos y beneficios de órdenes Insurama
        pipeline_financiero = [
            {"$match": {"origen": "insurama"}},
            {"$project": {
                "estado": 1,
                "materiales": 1,
                "datos_portal": 1,
                "presupuesto_enviado": 1
            }},
            {"$addFields": {
                "ingresos": {
                    "$sum": {
                        "$map": {
                            "input": {"$ifNull": ["$materiales", []]},
                            "as": "m",
                            "in": {"$multiply": [
                                {"$ifNull": ["$$m.precio_unitario", 0]},
                                {"$ifNull": ["$$m.cantidad", 1]}
                            ]}
                        }
                    }
                },
                "gastos": {
                    "$sum": {
                        "$map": {
                            "input": {"$ifNull": ["$materiales", []]},
                            "as": "m",
                            "in": {"$multiply": [
                                {"$ifNull": ["$$m.coste", 0]},
                                {"$ifNull": ["$$m.cantidad", 1]}
                            ]}
                        }
                    }
                },
                "precio_presupuesto": {"$ifNull": ["$presupuesto_enviado.precio", "$datos_portal.price"]}
            }},
            {"$group": {
                "_id": None,
                "total_ingresos_cerradas": {
                    "$sum": {"$cond": [{"$eq": ["$estado", "enviado"]}, "$ingresos", 0]}
                },
                "total_gastos_cerradas": {
                    "$sum": {"$cond": [{"$eq": ["$estado", "enviado"]}, "$gastos", 0]}
                },
                "ingresos_en_proceso": {
                    "$sum": {"$cond": [
                        {"$in": ["$estado", ["recibida", "en_taller", "reparado", "validacion"]]},
                        "$ingresos", 0
                    ]}
                },
                "gastos_en_proceso": {
                    "$sum": {"$cond": [
                        {"$in": ["$estado", ["recibida", "en_taller", "reparado", "validacion"]]},
                        "$gastos", 0
                    ]}
                },
                "precios_presupuestos": {
                    "$push": {"$cond": [{"$gt": ["$precio_presupuesto", 0]}, "$precio_presupuesto", "$$REMOVE"]}
                }
            }}
        ]
        
        financiero_result = await db.ordenes.aggregate(pipeline_financiero).to_list(1)
        financiero = financiero_result[0] if financiero_result else {}
        
        total_ingresos = financiero.get("total_ingresos_cerradas", 0)
        total_gastos = financiero.get("total_gastos_cerradas", 0)
        beneficio_cerradas = total_ingresos - total_gastos
        
        ingresos_pendientes = financiero.get("ingresos_en_proceso", 0)
        gastos_pendientes = financiero.get("gastos_en_proceso", 0)
        
        precios_presupuestos = financiero.get("precios_presupuestos", [])
        ticket_medio = round(sum(precios_presupuestos) / len(precios_presupuestos), 2) if precios_presupuestos else 0
        
        # Ratio de aceptación (basado en estado de presupuesto en datos_portal)
        # Status 3 = Aceptado en Sumbroker
        ordenes_con_datos = await db.ordenes.find(
            {"origen": "insurama", "datos_portal.status": {"$exists": True}},
            {"_id": 0, "datos_portal.status": 1}
        ).to_list(1000)
        
        total_con_status = len(ordenes_con_datos)
        aceptados = sum(1 for o in ordenes_con_datos if o.get("datos_portal", {}).get("status") == 3)
        ratio_aceptacion = round((aceptados / total_con_status * 100), 1) if total_con_status > 0 else 0
        
        # =============== MÉTRICAS DE COMPETENCIA (historial_mercado) ===============
        
        total_registros = await db.historial_mercado.count_documents({})
        registros_30d = await db.historial_mercado.count_documents({"fecha_cierre": {"$gte": hace_30_dias}})
        
        ganados = await db.historial_mercado.count_documents({"resultado": "ganado"})
        ganados_30d = await db.historial_mercado.count_documents({
            "resultado": "ganado",
            "fecha_cierre": {"$gte": hace_30_dias}
        })
        
        perdidos = await db.historial_mercado.count_documents({"resultado": "perdido"})
        perdidos_30d = await db.historial_mercado.count_documents({
            "resultado": "perdido", 
            "fecha_cierre": {"$gte": hace_30_dias}
        })
        
        # Tasa de éxito en competencia
        total_competidos = ganados + perdidos
        total_competidos_30d = ganados_30d + perdidos_30d
        tasa_exito = round((ganados / total_competidos * 100), 1) if total_competidos > 0 else 0
        tasa_exito_30d = round((ganados_30d / total_competidos_30d * 100), 1) if total_competidos_30d > 0 else 0
        
        # Precio promedio y margen
        pipeline_precios = [
            {"$match": {"mi_precio": {"$gt": 0}, "precio_ganador": {"$gt": 0}}},
            {"$group": {
                "_id": None,
                "mi_precio_promedio": {"$avg": "$mi_precio"},
                "precio_ganador_promedio": {"$avg": "$precio_ganador"},
                "diferencia_promedio": {"$avg": {"$subtract": ["$mi_precio", "$precio_ganador"]}}
            }}
        ]
        precios_stats = await db.historial_mercado.aggregate(pipeline_precios).to_list(1)
        precios_data = precios_stats[0] if precios_stats else {}
        
        # Top competidores que nos ganan
        pipeline_competidores = [
            {"$match": {"resultado": "perdido", "ganador_nombre": {"$ne": None}}},
            {"$group": {
                "_id": "$ganador_nombre_key",
                "nombre": {"$first": "$ganador_nombre"},
                "veces_ganado": {"$sum": 1},
                "precio_promedio": {"$avg": "$precio_ganador"},
                "diferencia_promedio": {"$avg": {"$subtract": ["$precio_ganador", "$mi_precio"]}}
            }},
            {"$sort": {"veces_ganado": -1}},
            {"$limit": 10}
        ]
        top_competidores = await db.historial_mercado.aggregate(pipeline_competidores).to_list(10)
        
        # Dispositivos más rentables (mayor tasa de éxito)
        pipeline_dispositivos = [
            {"$match": {"dispositivo_key": {"$ne": ""}}},
            {"$group": {
                "_id": "$dispositivo_key",
                "total": {"$sum": 1},
                "ganados": {"$sum": {"$cond": [{"$eq": ["$resultado", "ganado"]}, 1, 0]}},
                "perdidos": {"$sum": {"$cond": [{"$eq": ["$resultado", "perdido"]}, 1, 0]}},
                "precio_promedio_ganado": {"$avg": {
                    "$cond": [{"$eq": ["$resultado", "ganado"]}, "$mi_precio", None]
                }}
            }},
            {"$match": {"total": {"$gte": 2}}},
            {"$addFields": {
                "tasa_exito": {
                    "$cond": [
                        {"$gt": [{"$add": ["$ganados", "$perdidos"]}, 0]},
                        {"$multiply": [
                            {"$divide": ["$ganados", {"$add": ["$ganados", "$perdidos"]}]},
                            100
                        ]},
                        0
                    ]
                }
            }},
            {"$sort": {"tasa_exito": -1, "total": -1}},
            {"$limit": 10}
        ]
        dispositivos_rentables = await db.historial_mercado.aggregate(pipeline_dispositivos).to_list(10)
        
        # Tipos de reparación más comunes
        pipeline_tipos = [
            {"$group": {
                "_id": "$tipo_reparacion_key",
                "total": {"$sum": 1},
                "ganados": {"$sum": {"$cond": [{"$eq": ["$resultado", "ganado"]}, 1, 0]}},
                "precio_promedio": {"$avg": "$mi_precio"}
            }},
            {"$sort": {"total": -1}},
            {"$limit": 8}
        ]
        tipos_reparacion = await db.historial_mercado.aggregate(pipeline_tipos).to_list(8)
        
        # Evolución mensual
        pipeline_mensual = [
            {"$match": {"fecha_cierre": {"$gte": hace_90_dias}}},
            {"$addFields": {
                "mes": {"$substr": ["$fecha_cierre", 0, 7]}
            }},
            {"$group": {
                "_id": "$mes",
                "total": {"$sum": 1},
                "ganados": {"$sum": {"$cond": [{"$eq": ["$resultado", "ganado"]}, 1, 0]}},
                "perdidos": {"$sum": {"$cond": [{"$eq": ["$resultado", "perdido"]}, 1, 0]}}
            }},
            {"$sort": {"_id": 1}}
        ]
        evolucion_mensual = await db.historial_mercado.aggregate(pipeline_mensual).to_list(12)
        
        return {
            # NUEVAS MÉTRICAS REALES DEL NEGOCIO
            "negocio": {
                "total_ordenes_insurama": total_ordenes_insurama,
                "ordenes_30d": ordenes_insurama_30d,
                "ordenes_cerradas": ordenes_cerradas,
                "ordenes_en_proceso": ordenes_en_proceso,
                "ordenes_pendientes": ordenes_pendientes,
                "ratio_aceptacion": ratio_aceptacion,
                "ticket_medio": ticket_medio,
                "total_ingresos": round(total_ingresos, 2),
                "total_gastos": round(total_gastos, 2),
                "beneficio": round(beneficio_cerradas, 2),
                "margen_porcentaje": round((beneficio_cerradas / total_ingresos * 100), 1) if total_ingresos > 0 else 0,
                "ingresos_pendientes": round(ingresos_pendientes, 2),
                "gastos_pendientes": round(gastos_pendientes, 2),
            },
            # MÉTRICAS DE COMPETENCIA
            "kpis": {
                "total_registros": total_registros,
                "registros_30d": registros_30d,
                "ganados": ganados,
                "ganados_30d": ganados_30d,
                "perdidos": perdidos,
                "perdidos_30d": perdidos_30d,
                "tasa_exito": tasa_exito,
                "tasa_exito_30d": tasa_exito_30d,
                "mi_precio_promedio": round(precios_data.get("mi_precio_promedio", 0), 2),
                "precio_ganador_promedio": round(precios_data.get("precio_ganador_promedio", 0), 2),
                "diferencia_promedio": round(precios_data.get("diferencia_promedio", 0), 2)
            },
            "top_competidores": top_competidores,
            "dispositivos_rentables": dispositivos_rentables,
            "tipos_reparacion": tipos_reparacion,
            "evolucion_mensual": evolucion_mensual
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== RECOMENDACIONES ====================

@router.get("/recomendar-precio")
async def recomendar_precio(
    dispositivo: Optional[str] = None,
    tipo_reparacion: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """
    Recomienda un precio basado en historial de casos similares.
    Busca por dispositivo y/o tipo de reparación.
    """
    try:
        filtros = {}
        
        if dispositivo:
            # Buscar dispositivos similares
            dispositivo_key = dispositivo.upper()
            filtros["dispositivo_key"] = {"$regex": dispositivo_key, "$options": "i"}
        
        if tipo_reparacion:
            tipo_key = normalizar_tipo_reparacion(tipo_reparacion)
            filtros["tipo_reparacion_key"] = tipo_key
        
        if not filtros:
            # Sin filtros, dar estadísticas generales
            filtros = {"mi_precio": {"$gt": 0}}
        
        # Obtener casos similares
        casos = await db.historial_mercado.find(
            filtros,
            {"_id": 0}
        ).sort("fecha_cierre", -1).limit(50).to_list(50)
        
        if not casos:
            return {
                "tiene_datos": False,
                "mensaje": "No hay datos históricos suficientes para este tipo de reparación"
            }
        
        # Calcular estadísticas
        precios_ganados = [c["mi_precio"] for c in casos if c.get("resultado") == "ganado" and c.get("mi_precio")]
        precios_perdidos = [c["mi_precio"] for c in casos if c.get("resultado") == "perdido" and c.get("mi_precio")]
        precios_ganadores = [c["precio_ganador"] for c in casos if c.get("precio_ganador")]
        
        total_casos = len(casos)
        casos_ganados = len([c for c in casos if c.get("resultado") == "ganado"])
        casos_perdidos = len([c for c in casos if c.get("resultado") == "perdido"])
        
        # Precio recomendado: promedio de precios ganadores - pequeño margen
        if precios_ganadores:
            precio_ganador_promedio = sum(precios_ganadores) / len(precios_ganadores)
            precio_recomendado = round(precio_ganador_promedio * 0.98, 2)  # 2% menos que el promedio ganador
        elif precios_ganados:
            precio_recomendado = round(sum(precios_ganados) / len(precios_ganados), 2)
        else:
            precio_recomendado = None
        
        # Rango de precios
        todos_precios = precios_ganados + precios_perdidos
        precio_minimo = min(todos_precios) if todos_precios else None
        precio_maximo = max(todos_precios) if todos_precios else None
        
        # Tasa de éxito
        tasa_exito = round((casos_ganados / (casos_ganados + casos_perdidos) * 100), 1) if (casos_ganados + casos_perdidos) > 0 else 0
        
        # Competidores frecuentes en este tipo
        competidores_frecuentes = {}
        for caso in casos:
            if caso.get("resultado") == "perdido" and caso.get("ganador_nombre"):
                nombre = caso["ganador_nombre"]
                if nombre not in competidores_frecuentes:
                    competidores_frecuentes[nombre] = {"veces": 0, "precio_promedio": []}
                competidores_frecuentes[nombre]["veces"] += 1
                if caso.get("precio_ganador"):
                    competidores_frecuentes[nombre]["precio_promedio"].append(caso["precio_ganador"])
        
        # Top 3 competidores peligrosos
        competidores_peligrosos = []
        for nombre, data in sorted(competidores_frecuentes.items(), key=lambda x: x[1]["veces"], reverse=True)[:3]:
            precio_prom = sum(data["precio_promedio"]) / len(data["precio_promedio"]) if data["precio_promedio"] else 0
            competidores_peligrosos.append({
                "nombre": nombre,
                "veces_ganado": data["veces"],
                "precio_promedio": round(precio_prom, 2)
            })
        
        # Últimos 5 casos para contexto
        ultimos_casos = []
        for caso in casos[:5]:
            ultimos_casos.append({
                "codigo": caso.get("codigo_siniestro"),
                "dispositivo": caso.get("dispositivo_key"),
                "resultado": caso.get("resultado"),
                "mi_precio": caso.get("mi_precio"),
                "precio_ganador": caso.get("precio_ganador"),
                "ganador": caso.get("ganador_nombre"),
                "fecha": caso.get("fecha_cierre", "")[:10]
            })
        
        return {
            "tiene_datos": True,
            "total_casos_analizados": total_casos,
            "casos_ganados": casos_ganados,
            "casos_perdidos": casos_perdidos,
            "tasa_exito": tasa_exito,
            
            "precio_recomendado": precio_recomendado,
            "precio_minimo_historico": precio_minimo,
            "precio_maximo_historico": precio_maximo,
            "precio_ganador_promedio": round(sum(precios_ganadores) / len(precios_ganadores), 2) if precios_ganadores else None,
            
            "competidores_peligrosos": competidores_peligrosos,
            "ultimos_casos": ultimos_casos,
            
            "consejos": generar_consejos(tasa_exito, precio_recomendado, competidores_peligrosos)
        }
        
    except Exception as e:
        logger.error(f"Error recomendando precio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def generar_consejos(tasa_exito: float, precio_recomendado: Optional[float], competidores: list) -> list:
    """Genera consejos inteligentes basados en los datos"""
    consejos = []
    
    if tasa_exito >= 70:
        consejos.append({
            "tipo": "success",
            "mensaje": f"Tu tasa de éxito es excelente ({tasa_exito}%). Mantén tu estrategia actual."
        })
    elif tasa_exito >= 50:
        consejos.append({
            "tipo": "info",
            "mensaje": f"Tu tasa de éxito es buena ({tasa_exito}%). Considera ajustar precios en casos competitivos."
        })
    else:
        consejos.append({
            "tipo": "warning",
            "mensaje": f"Tu tasa de éxito es baja ({tasa_exito}%). Revisa tu estrategia de precios."
        })
    
    if competidores:
        top = competidores[0]
        consejos.append({
            "tipo": "alert",
            "mensaje": f"⚠️ {top['nombre']} es tu competidor más agresivo. Suele ganar con precios ~{top['precio_promedio']}€"
        })
    
    if precio_recomendado:
        consejos.append({
            "tipo": "recommendation",
            "mensaje": f"💡 Precio sugerido: {precio_recomendado}€ para maximizar probabilidad de ganar"
        })
    
    return consejos


# ==================== HISTORIAL ====================

@router.get("/historial")
async def obtener_historial(
    skip: int = 0,
    limit: int = 50,
    resultado: Optional[str] = None,
    dispositivo: Optional[str] = None,
    competidor: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Obtiene el historial de mercado con filtros"""
    try:
        filtros = {}
        
        if resultado:
            filtros["resultado"] = resultado
        if dispositivo:
            filtros["dispositivo_key"] = {"$regex": dispositivo.upper(), "$options": "i"}
        if competidor:
            filtros["ganador_nombre_key"] = {"$regex": competidor.upper(), "$options": "i"}
        if fecha_desde:
            filtros["fecha_cierre"] = {"$gte": fecha_desde}
        if fecha_hasta:
            if "fecha_cierre" in filtros:
                filtros["fecha_cierre"]["$lte"] = fecha_hasta
            else:
                filtros["fecha_cierre"] = {"$lte": fecha_hasta}
        
        total = await db.historial_mercado.count_documents(filtros)
        
        registros = await db.historial_mercado.find(
            filtros,
            {"_id": 0}
        ).sort("fecha_cierre", -1).skip(skip).limit(limit).to_list(limit)
        
        return {
            "total": total,
            "registros": registros,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CAPTURA AUTOMÁTICA ====================

@router.post("/capturar-desde-competidores/{codigo}")
async def capturar_desde_competidores(codigo: str, user: dict = Depends(require_admin)):
    """
    Captura los datos de mercado desde el endpoint de competidores existente.
    Útil para capturar manualmente o llamar desde el frontend.
    """
    try:
        from routes.insurama_routes import obtener_competidores_presupuesto
        from agent.scraper import SumbrokerClient
        from routes.insurama_routes import get_sumbroker_client
        
        # Obtener datos del presupuesto directamente del cliente
        client = await get_sumbroker_client()
        budget = await client.find_budget_by_service_code(codigo)
        
        if not budget:
            return {"capturado": False, "error": f"No se encontró presupuesto con código {codigo}"}
        
        presupuesto_data = budget
        
        # Obtener datos de competidores
        competidores_data = await obtener_competidores_presupuesto(codigo, user)
        
        if not competidores_data or not competidores_data.get("mi_presupuesto"):
            return {"capturado": False, "error": "No se encontraron datos de competidores"}
        
        mi_presupuesto = competidores_data["mi_presupuesto"]
        competidores = competidores_data.get("competidores", [])
        estadisticas = competidores_data.get("estadisticas", {})
        
        # Determinar resultado
        mi_estado = mi_presupuesto.get("estado_codigo")
        resultado = "pendiente"
        precio_ganador = None
        ganador_nombre = None
        
        # Estado 3 = Aceptado (ganamos)
        if mi_estado == 3:
            resultado = "ganado"
            precio_ganador = float(mi_presupuesto.get("precio", 0) or 0)
            ganador_nombre = mi_presupuesto.get("tienda_nombre")
        # Estado 7 = Cancelado
        elif mi_estado == 7:
            # Buscar si algún competidor tiene estado 3 (Aceptado)
            ganador = None
            for comp in competidores:
                if comp.get("estado_codigo") == 3:
                    ganador = comp
                    break
            
            if ganador:
                resultado = "perdido"
                precio_ganador = float(ganador.get("precio", 0) or 0)
                ganador_nombre = ganador.get("tienda_nombre")
            else:
                resultado = "cancelado_cliente"
        
        # Extraer datos del dispositivo
        dispositivo_marca = presupuesto_data.get("device_brand", "")
        dispositivo_modelo = presupuesto_data.get("device_model", "")
        tipo_reparacion = presupuesto_data.get("damage_description", "")
        
        # Preparar lista de competidores
        competidores_lista = []
        for i, comp in enumerate(competidores):
            competidores_lista.append({
                "nombre": comp.get("tienda_nombre"),
                "precio": float(comp.get("precio", 0) or 0),
                "posicion": i + 1,
                "estado": comp.get("estado")
            })
        
        # Crear registro
        registro = RegistroMercado(
            codigo_siniestro=codigo,
            dispositivo_marca=dispositivo_marca,
            dispositivo_modelo=dispositivo_modelo,
            tipo_reparacion=tipo_reparacion,
            fecha_cierre=datetime.now(timezone.utc).isoformat(),
            resultado=resultado,
            mi_precio=float(mi_presupuesto.get("precio", 0) or 0),
            precio_ganador=precio_ganador,
            ganador_nombre=ganador_nombre,
            num_competidores=len(competidores),
            precio_minimo=estadisticas.get("precio_minimo"),
            precio_maximo=estadisticas.get("precio_maximo"),
            precio_medio=estadisticas.get("precio_medio"),
            competidores=competidores_lista
        )
        
        # Guardar
        result = await registrar_resultado_mercado(registro, user)
        
        return {
            "capturado": True,
            "resultado": resultado,
            "mi_precio": registro.mi_precio,
            "precio_ganador": precio_ganador,
            "ganador": ganador_nombre,
            "registro": result
        }
        
    except Exception as e:
        logger.error(f"Error capturando datos de mercado: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ANÁLISIS DE COMPETIDOR ====================

@router.get("/analisis-competidor/{nombre}")
async def analisis_competidor(nombre: str, user: dict = Depends(require_admin)):
    """Análisis detallado de un competidor específico"""
    try:
        nombre_key = nombre.upper()
        
        # Buscar casos donde este competidor ganó
        casos_ganados = await db.historial_mercado.find(
            {"ganador_nombre_key": {"$regex": nombre_key, "$options": "i"}},
            {"_id": 0}
        ).to_list(100)
        
        # Buscar casos donde aparece como competidor
        casos_compitio = await db.historial_mercado.find(
            {"competidores.nombre": {"$regex": nombre, "$options": "i"}},
            {"_id": 0}
        ).to_list(100)
        
        if not casos_ganados and not casos_compitio:
            return {"tiene_datos": False, "mensaje": "No hay datos de este competidor"}
        
        # Estadísticas
        veces_ganado = len(casos_ganados)
        veces_compitio = len(casos_compitio)
        
        # Precios cuando ganó
        precios_victoria = [c["precio_ganador"] for c in casos_ganados if c.get("precio_ganador")]
        precio_promedio_victoria = round(sum(precios_victoria) / len(precios_victoria), 2) if precios_victoria else 0
        
        # Diferencia con nuestros precios
        diferencias = [c["mi_precio"] - c["precio_ganador"] for c in casos_ganados 
                       if c.get("mi_precio") and c.get("precio_ganador")]
        diferencia_promedio = round(sum(diferencias) / len(diferencias), 2) if diferencias else 0
        
        # Dispositivos donde más compite
        dispositivos = {}
        for caso in casos_ganados:
            disp = caso.get("dispositivo_key", "OTROS")
            if disp not in dispositivos:
                dispositivos[disp] = 0
            dispositivos[disp] += 1
        
        dispositivos_top = sorted(dispositivos.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "tiene_datos": True,
            "nombre": nombre,
            "veces_nos_gano": veces_ganado,
            "veces_compitio_con_nosotros": veces_compitio,
            "precio_promedio_victoria": precio_promedio_victoria,
            "diferencia_promedio_con_nosotros": diferencia_promedio,
            "dispositivos_especialidad": [{"dispositivo": d[0], "veces": d[1]} for d in dispositivos_top],
            "ultimos_casos": casos_ganados[:10]
        }
        
    except Exception as e:
        logger.error(f"Error analizando competidor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

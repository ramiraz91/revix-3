"""
Rutas para integración con Insurama/Sumbroker
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
import os
import re
import asyncio

from config import db, logger
from auth import require_admin, require_auth
from agent.scraper import SumbrokerClient

router = APIRouter(prefix="/insurama", tags=["insurama"])

# Flag para evitar sincronizaciones simultáneas
_sync_in_progress = False
CACHE_TTL_MINUTES = 10  # Caché válida por 10 minutos

# Credenciales de Sumbroker (se configuran en .env o en DB)
async def get_sumbroker_client():
    """Obtiene cliente de Sumbroker con credenciales configuradas"""
    config = await db.configuracion.find_one({"tipo": "sumbroker"}, {"_id": 0})
    
    if not config or not config.get("datos", {}).get("login"):
        # Intentar desde env
        login = os.environ.get("SUMBROKER_LOGIN")
        password = os.environ.get("SUMBROKER_PASSWORD")
        if not login or not password:
            raise HTTPException(
                status_code=400, 
                detail="Credenciales de Sumbroker no configuradas. Ve a Configuración > Insurama"
            )
    else:
        login = config["datos"]["login"]
        password = config["datos"]["password"]
    
    return SumbrokerClient(login, password)

# ==================== MODELOS ====================

class SumbrokerCredentials(BaseModel):
    login: str
    password: str

class EnviarPresupuestoRequest(BaseModel):
    precio: float
    descripcion: str
    tiempo_reparacion: str = "24-48h"
    garantia_meses: int = 12
    # Campos adicionales requeridos por Sumbroker
    disponibilidad_recambios: Optional[str] = None  # "inmediata", "24h", "48h", "7dias", "sin_stock"
    tiempo_horas: Optional[float] = None  # Tiempo estimado en horas de trabajo
    tipo_recambio: Optional[str] = None  # "original", "compatible", "reacondicionado", "no_aplica"
    tipo_garantia: Optional[str] = None  # "fabricante", "taller", "sin_garantia"

class ActualizarEstadoRequest(BaseModel):
    estado: str  # recibido, en_reparacion, reparado, enviado
    tracking_number: Optional[str] = None
    transportista: Optional[str] = None
    notas: Optional[str] = None

class EnviarObservacionRequest(BaseModel):
    mensaje: str
    visible_cliente: bool = False

# ==================== CONFIGURACIÓN ====================

@router.get("/config")
async def obtener_config_insurama(user: dict = Depends(require_admin)):
    """Obtiene la configuración actual de Insurama/Sumbroker"""
    config = await db.configuracion.find_one({"tipo": "sumbroker"}, {"_id": 0})
    agent_config = await db.configuracion.find_one({"tipo": "agent_config"}, {"_id": 0})
    
    # Verificar estado del agente de polling
    agent_activo = False
    try:
        from agent.scheduler import is_agent_running
        agent_activo = is_agent_running()
    except:
        pass
    
    if not config:
        return {
            "configurado": False,
            "login": None,
            "conexion_ok": False,
            "agente_activo": agent_activo
        }
    
    return {
        "configurado": True,
        "login": config.get("datos", {}).get("login"),
        "conexion_ok": config.get("datos", {}).get("conexion_ok", False),
        "ultima_verificacion": config.get("datos", {}).get("ultima_verificacion"),
        "agente_activo": agent_activo,
        "poll_interval": agent_config.get("datos", {}).get("poll_interval", 1800) if agent_config else 1800,
        "auto_create_orders": agent_config.get("datos", {}).get("auto_create_orders", True) if agent_config else True
    }

@router.post("/config")
async def guardar_config_insurama(credentials: SumbrokerCredentials, user: dict = Depends(require_admin)):
    """Guarda las credenciales de Insurama/Sumbroker y activa el agente de polling"""
    # Probar conexión primero
    client = SumbrokerClient(credentials.login, credentials.password)
    test_result = await client.test_connection()
    
    config_data = {
        "login": credentials.login,
        "password": credentials.password,
        "conexion_ok": test_result.get("success", False),
        "ultima_verificacion": datetime.now(timezone.utc).isoformat(),
        "user_name": test_result.get("user"),
        "user_role": test_result.get("role"),
        "total_presupuestos": test_result.get("store_budgets_total", 0)
    }
    
    await db.configuracion.update_one(
        {"tipo": "sumbroker"},
        {"$set": {"datos": config_data, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    
    if not test_result.get("success"):
        raise HTTPException(status_code=400, detail=f"Error de conexión: {test_result.get('error')}")
    
    # Activar el agente de polling si la conexión es exitosa
    try:
        # Crear/actualizar agent_config para activar el polling
        await db.configuracion.update_one(
            {"tipo": "agent_config"},
            {"$set": {
                "datos.estado": "activo",
                "datos.poll_interval": 1800,  # 30 minutos
                "datos.auto_create_orders": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
        
        # Iniciar el agente de polling
        from agent.scheduler import start_agent, is_agent_running
        if not is_agent_running():
            start_agent()
            logger.info("Agente de polling Insurama iniciado")
    except Exception as e:
        logger.error(f"Error iniciando agente de polling: {e}")
    
    return {
        "message": "Credenciales guardadas y verificadas. Agente de polling activado.",
        "conexion": test_result
    }

@router.post("/test-conexion")
async def test_conexion_insurama(user: dict = Depends(require_admin)):
    """Prueba la conexión con Insurama/Sumbroker"""
    try:
        client = await get_sumbroker_client()
        result = await client.test_connection()
        
        # Actualizar estado en config
        await db.configuracion.update_one(
            {"tipo": "sumbroker"},
            {"$set": {
                "datos.conexion_ok": result.get("success", False),
                "datos.ultima_verificacion": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/debug-budgets/{codigo}")
async def debug_budgets_por_codigo(codigo: str, user: dict = Depends(require_admin)):
    """
    DEBUG: Muestra TODOS los presupuestos encontrados para un código de autorización.
    Útil para verificar que se están obteniendo ambos presupuestos cuando existen múltiples.
    """
    try:
        client = await get_sumbroker_client()
        
        # Usar el método con retry del cliente
        if not await client._ensure_auth():
            return {"error": "Authentication failed"}
        
        try:
            resp = await client._request_with_retry(
                "get", f"https://api.sumbroker.es/api/v2/store-budget",
                params={"search": codigo, "limit": 50})
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}
        
        if resp.status_code != 200:
            return {"error": f"API error: {resp.status_code}", "raw": resp.text[:500]}
            
            data = resp.json()
            all_budgets = data.get("store_budgets", [])
            total = data.get("total", 0)
            
            # Filtrar por coincidencia exacta
            exact_matches = []
            for b in all_budgets:
                claim = b.get("claim_budget") or {}
                prc = claim.get("policy_risk_claim") or {}
                identifier = prc.get("identifier")
                
                # Status puede venir como string o int
                status_raw = b.get("status")
                status = int(status_raw) if status_raw is not None else None
                
                budget_info = {
                    "budget_id": b.get("id"),
                    "identifier": identifier,
                    "matches_code": identifier == codigo,
                    "status": status,
                    "status_text": b.get("status_text"),
                    "price": b.get("price"),
                    "accepted_date": b.get("accepted_date"),
                    "created_at": b.get("created_at"),
                }
                
                if identifier == codigo:
                    exact_matches.append(budget_info)
            
            # Determinar cuál se seleccionaría con la lógica actual
            selected = None
            selection_reason = None
            
            if exact_matches:
                # Priority 1: Accepted (status 3)
                for b in exact_matches:
                    if b["status"] == 3:
                        selected = b
                        selection_reason = "ACCEPTED (status=3)"
                        break
                
                # Priority 2: Not cancelled
                if not selected:
                    for b in exact_matches:
                        if b["status"] != 7:
                            selected = b
                            selection_reason = f"ACTIVE (status={b['status']}, not cancelled)"
                            break
                
                # Priority 3: First
                if not selected and exact_matches:
                    selected = exact_matches[0]
                    selection_reason = "FALLBACK (first match, all cancelled)"
            
            return {
                "codigo_buscado": codigo,
                "total_en_api": total,
                "budgets_devueltos": len(all_budgets),
                "coincidencias_exactas": len(exact_matches),
                "todos_budgets_exactos": exact_matches,
                "presupuesto_seleccionado": selected,
                "razon_seleccion": selection_reason
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Debug budgets error: {e}")
        return {"error": str(e)}

@router.get("/debug-competidores-raw/{codigo}")
async def debug_competidores_raw(codigo: str, user: dict = Depends(require_admin)):
    """
    DEBUG: Muestra la estructura RAW de los presupuestos de competidores.
    Para identificar qué campos contienen los comentarios/observaciones.
    """
    try:
        client = await get_sumbroker_client()
        budget = await client.find_budget_by_service_code(codigo)
        
        if not budget:
            return {"error": f"No se encontró presupuesto con código {codigo}"}
        
        claim_budget_id = budget.get("claim_budget_id")
        
        if not claim_budget_id:
            return {"error": "No se pudo obtener claim_budget_id"}
        
        all_budgets = await client.get_claim_store_budgets(claim_budget_id)
        
        if not all_budgets:
            return {"error": "No se pudieron obtener los presupuestos de competidores"}
        
        # Extraer TODAS las claves de cada presupuesto para análisis
        budget_keys_analysis = []
        for i, b in enumerate(all_budgets[:3]):  # Solo primeros 3 para no saturar
            # Filtrar campos vacíos y mostrar estructura
            non_empty_fields = {k: v for k, v in b.items() if v and v != 0 and k != 'store'}
            store_info = b.get("store", {})
            budget_keys_analysis.append({
                "index": i,
                "tienda": store_info.get("name", "N/A"),
                "precio": b.get("price"),
                "campos_con_valor": list(non_empty_fields.keys()),
                "muestra_campos": {
                    "observation": b.get("observation"),
                    "observations": b.get("observations"),
                    "description": b.get("description"),
                    "repair_description": b.get("repair_description"),
                    "comment": b.get("comment"),
                    "comments": b.get("comments"),
                    "notes": b.get("notes"),
                    "message": b.get("message"),
                    "text": b.get("text"),
                    "budget_text": b.get("budget_text"),
                    "details": b.get("details"),
                }
            })
        
        return {
            "codigo": codigo,
            "claim_budget_id": claim_budget_id,
            "total_competidores": len(all_budgets),
            "analisis_campos": budget_keys_analysis,
            "primer_budget_completo": all_budgets[0] if all_budgets else None
        }
        
    except Exception as e:
        logger.error(f"Debug competidores raw error: {e}")
        return {"error": str(e)}

# ==================== CONSULTAS ====================

def _format_budget_for_ui(b):
    """Formatea un presupuesto raw de Sumbroker para la UI"""
    try:
        claim = b.get("claim_budget") or {}
        prc = claim.get("policy_risk_claim") or {}
        policy = claim.get("policy") or {}
        
        client_name = policy.get("complete_name") or f"{policy.get('name', '')} {policy.get('last_name_1', '')}".strip()
        client_phone = policy.get("phone_number") or prc.get("phone_number")
        
        terminals = policy.get("mobile_terminals_active") or policy.get("mobile_terminals") or []
        if terminals:
            t = terminals[0]
            device_str = f"{t.get('brand', '')} {t.get('model', '')}".strip()
        else:
            device_str = f"{b.get('brand', '')} {b.get('model', '')}".strip()
        device_str = device_str.replace("None", "").strip() or "N/A"
        
        return {
            "id": b.get("id"),
            "codigo_siniestro": prc.get("identifier"),
            "cliente_nombre": client_name,
            "cliente_telefono": client_phone,
            "dispositivo": device_str,
            "daño": (prc.get("description") or "")[:100],
            "estado": b.get("status_text"),
            "precio": b.get("price"),
            "reserve_value": prc.get("reserve_value"),
            "claim_real_value": prc.get("claim_real_value"),
            "product_name": b.get("product_name"),
            "repair_time_text": b.get("repair_time_text"),
            "fecha_creacion": b.get("created_at"),
            "fecha_aceptacion": b.get("accepted_date"),
            "tracking": b.get("tracking_number")
        }
    except Exception as e:
        logger.warning(f"Error formateando presupuesto {b.get('id')}: {e}")
        return None

async def _sync_presupuestos_cache(limit: int = 50):
    """Sincroniza presupuestos de Sumbroker a caché MongoDB en background"""
    global _sync_in_progress
    if _sync_in_progress:
        logger.info("Sync already in progress, skipping")
        return
    
    _sync_in_progress = True
    try:
        config = await db.configuracion.find_one({"tipo": "sumbroker"}, {"_id": 0})
        if not config or not config.get("datos", {}).get("login"):
            return
        
        datos = config["datos"]
        client = SumbrokerClient(login=datos["login"], password=datos["password"])
        
        budgets = await client.list_store_budgets(limit=limit)
        if not budgets:
            return
        
        resultado = []
        for b in budgets:
            formatted = _format_budget_for_ui(b)
            if formatted:
                resultado.append(formatted)
        
        # Guardar en caché
        await db.insurama_cache.update_one(
            {"tipo": "presupuestos_lista"},
            {"$set": {
                "tipo": "presupuestos_lista",
                "datos": resultado,
                "total": len(resultado),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True
        )
        logger.info(f"Cache actualizada: {len(resultado)} presupuestos")
        
        # Alimentar historial de mercado con los datos de competidores
        await _alimentar_historial_mercado(client, resultado)
    except Exception as e:
        logger.error(f"Error syncing presupuestos cache: {e}")
    finally:
        _sync_in_progress = False

async def _alimentar_historial_mercado(client, presupuestos):
    """Captura datos de mercado automáticamente para alimentar el dashboard de inteligencia"""
    try:
        for p in presupuestos[:10]:  # Procesar los 10 más recientes
            codigo = p.get("codigo_siniestro")
            if not codigo:
                continue
            
            # Verificar si ya tenemos datos recientes para este código
            existente = await db.historial_mercado.find_one(
                {"codigo_siniestro": codigo}, {"_id": 0, "updated_at": 1}
            )
            if existente and existente.get("updated_at"):
                try:
                    last_update = datetime.fromisoformat(existente["updated_at"])
                    if (datetime.now(timezone.utc) - last_update) < timedelta(hours=6):
                        continue  # Ya actualizado recientemente
                except:
                    pass
            
            try:
                # Obtener competidores
                comp_data = await _fetch_competidores(codigo)
                if not comp_data:
                    continue
                
                mi = comp_data.get("mi_presupuesto")
                if not mi or not isinstance(mi, dict):
                    continue
                
                comps = comp_data.get("competidores") or []
                stats = comp_data.get("estadisticas") or {}
                
                # Determinar resultado
                mi_estado = str(mi.get("estado_codigo", ""))
                resultado = "pendiente"
                precio_ganador = None
                ganador_nombre = None
                
                if mi_estado == "3":
                    resultado = "ganado"
                    precio_ganador = mi.get("precio_num", 0)
                    ganador_nombre = mi.get("tienda_nombre")
                elif mi_estado == "7":
                    ganador = next((c for c in comps if str(c.get("estado_codigo")) == "3"), None)
                    if ganador:
                        resultado = "perdido"
                        precio_ganador = ganador.get("precio_num", 0)
                        ganador_nombre = ganador.get("tienda_nombre")
                    else:
                        resultado = "cancelado_otros"
                
                # Guardar en historial
                competidores_lista = [
                    {"nombre": c.get("tienda_nombre"), "precio": c.get("precio_num", 0), "posicion": i+1, "estado": c.get("estado")}
                    for i, c in enumerate(comps)
                ]
                
                registro = {
                    "codigo_siniestro": codigo,
                    "dispositivo_marca": p.get("dispositivo", "").split(" ")[0] if p.get("dispositivo") else "",
                    "dispositivo_modelo": " ".join(p.get("dispositivo", "").split(" ")[1:]) if p.get("dispositivo") else "",
                    "dispositivo_key": (p.get("dispositivo") or "").upper(),
                    "tipo_reparacion": p.get("daño", ""),
                    "tipo_reparacion_key": _normalizar_tipo(p.get("daño", "")),
                    "fecha_cierre": datetime.now(timezone.utc).isoformat(),
                    "resultado": resultado,
                    "mi_precio": mi.get("precio_num", 0),
                    "precio_ganador": precio_ganador,
                    "ganador_nombre": ganador_nombre,
                    "ganador_nombre_key": (ganador_nombre or "").upper(),
                    "num_competidores": len(comps),
                    "precio_minimo": stats.get("precio_minimo"),
                    "precio_maximo": stats.get("precio_maximo"),
                    "precio_medio": stats.get("precio_medio"),
                    "competidores": competidores_lista,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                await db.historial_mercado.update_one(
                    {"codigo_siniestro": codigo},
                    {"$set": registro, "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}},
                    upsert=True
                )
                logger.info(f"Historial mercado actualizado: {codigo} ({resultado})")
                
                # También actualizar caché de competidores
                cache_key = f"competidores_{codigo.upper()}"
                await db.insurama_cache.update_one(
                    {"tipo": cache_key},
                    {"$set": {"tipo": cache_key, "datos": comp_data, "updated_at": datetime.now(timezone.utc).isoformat()}},
                    upsert=True
                )
            except Exception as e:
                logger.warning(f"Error procesando mercado para {codigo}: {e}")
                continue
        
        logger.info("Historial de mercado alimentado correctamente")
    except Exception as e:
        logger.error(f"Error alimentando historial de mercado: {e}")

def _normalizar_tipo(tipo):
    if not tipo:
        return "OTROS"
    t = tipo.upper()
    if any(x in t for x in ["PANTALLA", "LCD", "DISPLAY", "OLED", "INCELL"]):
        return "PANTALLA"
    if any(x in t for x in ["BATERIA", "BATTERY"]):
        return "BATERIA"
    if any(x in t for x in ["CAMARA", "CAMERA"]):
        return "CAMARA"
    if any(x in t for x in ["TAPA", "BACK", "COVER"]):
        return "TAPA_TRASERA"
    if any(x in t for x in ["CONECTOR", "CARGA"]):
        return "CONECTOR_CARGA"
    return "OTROS"

@router.get("/presupuestos")
async def listar_presupuestos_insurama(
    limit: int = 20,
    background_tasks: BackgroundTasks = None,
    user: dict = Depends(require_admin)
):
    """Lista los últimos presupuestos - sirve caché primero, sincroniza en background"""
    try:
        # 1. Intentar servir desde caché
        cache = await db.insurama_cache.find_one({"tipo": "presupuestos_lista"}, {"_id": 0})
        
        if cache and cache.get("datos"):
            cache_age = datetime.now(timezone.utc) - datetime.fromisoformat(cache["updated_at"])
            datos = cache["datos"][:limit]
            
            # Si la caché es antigua, sincronizar en background
            if cache_age > timedelta(minutes=CACHE_TTL_MINUTES) and background_tasks:
                background_tasks.add_task(_sync_presupuestos_cache, limit)
            
            return {
                "presupuestos": datos,
                "total": len(datos),
                "from_cache": True,
                "cache_age_seconds": int(cache_age.total_seconds()),
            }
        
        # 2. Sin caché - hacer petición directa pero también guardar en caché
        client = await get_sumbroker_client()
        budgets = await client.list_store_budgets(limit=limit)
        
        if budgets is None:
            return {"presupuestos": [], "total": 0, "error": "No se pudieron obtener los presupuestos"}
        
        resultado = []
        for b in budgets:
            formatted = _format_budget_for_ui(b)
            if formatted:
                resultado.append(formatted)
        
        # Guardar en caché para la próxima vez
        await db.insurama_cache.update_one(
            {"tipo": "presupuestos_lista"},
            {"$set": {
                "tipo": "presupuestos_lista",
                "datos": resultado,
                "total": len(resultado),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True
        )
        
        return {"presupuestos": resultado, "total": len(resultado), "from_cache": False}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listando presupuestos Insurama: {e}")
        # Última opción: servir caché aunque sea vieja
        cache = await db.insurama_cache.find_one({"tipo": "presupuestos_lista"}, {"_id": 0})
        if cache and cache.get("datos"):
            return {"presupuestos": cache["datos"][:limit], "total": len(cache["datos"][:limit]), "from_cache": True, "stale": True}
        return {"presupuestos": [], "total": 0, "error": str(e)}

@router.post("/sync")
async def forzar_sincronizacion(background_tasks: BackgroundTasks, user: dict = Depends(require_admin)):
    """Fuerza una sincronización de presupuestos y activa el polling si no está activo"""
    # Sincronizar presupuestos
    background_tasks.add_task(_sync_presupuestos_cache, 50)
    
    # Verificar y activar el agente si no está corriendo
    agente_iniciado = False
    try:
        from agent.scheduler import start_agent, is_agent_running
        if not is_agent_running():
            # Asegurar que agent_config existe y está activo
            await db.configuracion.update_one(
                {"tipo": "agent_config"},
                {"$set": {
                    "datos.estado": "activo",
                    "datos.poll_interval": 1800,
                    "datos.auto_create_orders": True,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }},
                upsert=True
            )
            start_agent()
            agente_iniciado = True
            logger.info("Agente de polling iniciado tras sincronización forzada")
    except Exception as e:
        logger.error(f"Error iniciando agente: {e}")
    
    return {
        "message": "Sincronización iniciada en background",
        "agente_iniciado": agente_iniciado
    }

@router.get("/presupuesto/{codigo}")
async def obtener_presupuesto_insurama(
    codigo: str, 
    background_tasks: BackgroundTasks = None,
    user: dict = Depends(require_admin)
):
    """Obtiene los detalles completos de un presupuesto por código de siniestro - con caché"""
    try:
        cache_key = f"presupuesto_detalle_{codigo.upper()}"
        
        # 1. Intentar servir desde caché
        cache = await db.insurama_cache.find_one({"tipo": cache_key}, {"_id": 0})
        if cache and cache.get("datos"):
            cache_age = datetime.now(timezone.utc) - datetime.fromisoformat(cache["updated_at"])
            if cache_age < timedelta(minutes=CACHE_TTL_MINUTES):
                return cache["datos"]
            # Caché vieja: servir pero actualizar en background
            if background_tasks:
                background_tasks.add_task(_sync_presupuesto_detalle, codigo)
            return cache["datos"]
        
        # 2. Sin caché - petición directa
        client = await get_sumbroker_client()
        data = await client.extract_service_data(codigo)
        
        if not data:
            raise HTTPException(status_code=404, detail=f"No se encontró presupuesto con código {codigo}")
        
        # Guardar en caché
        await db.insurama_cache.update_one(
            {"tipo": cache_key},
            {"$set": {"tipo": cache_key, "datos": data, "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True
        )
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo presupuesto {codigo}: {e}")
        # Fallback a caché vieja
        cache = await db.insurama_cache.find_one({"tipo": f"presupuesto_detalle_{codigo.upper()}"}, {"_id": 0})
        if cache and cache.get("datos"):
            return cache["datos"]
        raise HTTPException(status_code=500, detail=str(e))

async def _sync_presupuesto_detalle(codigo: str):
    """Actualiza caché de detalle de presupuesto en background"""
    try:
        client = await get_sumbroker_client()
        data = await client.extract_service_data(codigo)
        if data:
            cache_key = f"presupuesto_detalle_{codigo.upper()}"
            await db.insurama_cache.update_one(
                {"tipo": cache_key},
                {"$set": {"tipo": cache_key, "datos": data, "updated_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True
            )
    except Exception as e:
        logger.error(f"Error syncing presupuesto detalle {codigo}: {e}")


# ==================== BÚSQUEDA MÚLTIPLE ====================

class BusquedaMultipleRequest(BaseModel):
    codigos: list[str]

@router.post("/busqueda-multiple")
async def busqueda_multiple_presupuestos(data: BusquedaMultipleRequest, user: dict = Depends(require_admin)):
    """
    Busca múltiples códigos de siniestro de forma secuencial optimizada.
    Usa una sola sesión HTTP para evitar saturar la API.
    Pre-carga datos de mercado para navegación inmediata.
    Máximo 10 códigos.
    """
    
    # Validar límite
    codigos = list(set([c.strip().upper() for c in data.codigos if c.strip()]))[:10]
    
    if not codigos:
        raise HTTPException(status_code=400, detail="No se proporcionaron códigos válidos")
    
    try:
        client = await get_sumbroker_client()
        resultados_finales = []
        
        for codigo in codigos:
            resultado = {
                "codigo": codigo,
                "status": "loading",
                "presupuesto": None,
                "competidores": None,
                "error": None
            }
            
            try:
                # Buscar el presupuesto
                budget = await client.find_budget_by_service_code(codigo)
                
                if not budget:
                    resultado["status"] = "not_found"
                    resultado["error"] = "No encontrado en Sumbroker"
                    resultados_finales.append(resultado)
                    continue
                
                # Extraer datos básicos del presupuesto encontrado
                claim = budget.get("claim_budget") or {}
                prc = claim.get("policy_risk_claim") or {}
                policy = claim.get("policy") or {}
                
                # Datos básicos del presupuesto (versión simplificada)
                resultado["presupuesto"] = {
                    "budget_id": budget.get("id"),
                    "claim_budget_id": budget.get("claim_budget_id"),
                    "claim_identifier": codigo,
                    "device_brand": budget.get("brand") or (policy.get("mobile_terminals_active", [{}])[0].get("brand") if policy.get("mobile_terminals_active") else ""),
                    "device_model": budget.get("model") or (policy.get("mobile_terminals_active", [{}])[0].get("model") if policy.get("mobile_terminals_active") else ""),
                    "device_imei": budget.get("imei") or (policy.get("mobile_terminals_active", [{}])[0].get("imei") if policy.get("mobile_terminals_active") else ""),
                    "damage_type_text": prc.get("description", "")[:100] if prc.get("description") else "",
                    "damage_description": prc.get("description", ""),
                    "client_full_name": policy.get("complete_name") or f"{policy.get('name', '')} {policy.get('last_name_1', '')}".strip(),
                    "client_phone": policy.get("phone_number"),
                    "status": budget.get("status"),
                    "status_text": budget.get("status_text"),
                    "price": budget.get("price"),
                    "reserve_value": prc.get("reserve_value"),
                    "claim_real_value": prc.get("claim_real_value"),
                    "product_name": budget.get("product_name"),
                    "internal_status_text": prc.get("internal_status_text"),
                    "external_status_text": prc.get("external_status_text"),
                    "repair_time_text": budget.get("repair_time_text"),
                    "warranty_type_text": budget.get("warranty_type_text"),
                    "device_purchase_date": (policy.get("mobile_terminals_active", [{}])[0].get("purchase_date") if policy.get("mobile_terminals_active") else None),
                    "device_purchase_price": (policy.get("mobile_terminals_active", [{}])[0].get("purchase_price") if policy.get("mobile_terminals_active") else None),
                }
                
                # Obtener competidores/mercado si tenemos claim_budget_id
                claim_budget_id = budget.get("claim_budget_id")
                my_budget_id = budget.get("id")
                
                if claim_budget_id:
                    try:
                        all_budgets = await client.get_claim_store_budgets(claim_budget_id)
                        
                        if all_budgets:
                            # Procesar competidores
                            competidores = []
                            mi_presupuesto = None
                            precios_validos = []
                            
                            for b in all_budgets:
                                store = b.get("store", {})
                                precio = float(b.get("price", 0) or 0)
                                budget_id = b.get("id")
                                
                                budget_info = {
                                    "id": budget_id,
                                    "tienda_nombre": store.get("name", "N/A"),
                                    "tienda_ciudad": store.get("city", ""),
                                    "precio": b.get("price"),
                                    "precio_num": precio,
                                    "estado": b.get("status_text"),
                                    "estado_codigo": b.get("status"),
                                    "es_mio": budget_id == my_budget_id
                                }
                                
                                if b.get("id") == my_budget_id:
                                    mi_presupuesto = budget_info
                                else:
                                    competidores.append(budget_info)
                                
                                if precio > 0:
                                    precios_validos.append(precio)
                            
                            # Ordenar competidores por precio
                            competidores.sort(key=lambda x: (x["precio_num"] == 0, x["precio_num"]))
                            
                            # Calcular estadísticas
                            estadisticas = None
                            if precios_validos:
                                mi_precio = float(mi_presupuesto.get("precio", 0) or 0) if mi_presupuesto else 0
                                mi_posicion = sum(1 for p in precios_validos if p < mi_precio) + 1 if mi_precio > 0 else None
                                
                                estadisticas = {
                                    "total_participantes": len(all_budgets),
                                    "con_precio": len(precios_validos),
                                    "precio_minimo": min(precios_validos),
                                    "precio_maximo": max(precios_validos),
                                    "precio_medio": round(sum(precios_validos) / len(precios_validos), 2),
                                    "mi_posicion": mi_posicion
                                }
                            
                            resultado["competidores"] = {
                                "mi_presupuesto": mi_presupuesto,
                                "competidores": competidores[:10],
                                "estadisticas": estadisticas
                            }
                    except Exception as comp_err:
                        logger.warning(f"Error obteniendo competidores para {codigo}: {comp_err}")
                
                resultado["status"] = "success"
                
            except Exception as e:
                resultado["status"] = "error"
                resultado["error"] = str(e)
            
            resultados_finales.append(resultado)
        
        # Estadísticas generales
        encontrados = sum(1 for r in resultados_finales if r["status"] == "success")
        no_encontrados = sum(1 for r in resultados_finales if r["status"] == "not_found")
        errores = sum(1 for r in resultados_finales if r["status"] == "error")
        
        return {
            "total_buscados": len(codigos),
            "encontrados": encontrados,
            "no_encontrados": no_encontrados,
            "errores": errores,
            "resultados": resultados_finales
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en búsqueda múltiple: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/presupuesto/{codigo}/competidores")
async def obtener_competidores_presupuesto(
    codigo: str, 
    background_tasks: BackgroundTasks = None,
    user: dict = Depends(require_admin)
):
    """Obtiene todos los presupuestos de competidores - con caché"""
    try:
        # 1. Intentar servir desde caché
        cache_key = f"competidores_{codigo.upper()}"
        cache = await db.insurama_cache.find_one({"tipo": cache_key}, {"_id": 0})
        
        if cache and cache.get("datos"):
            cache_age = datetime.now(timezone.utc) - datetime.fromisoformat(cache["updated_at"])
            # Si caché es reciente (< 10 min), servir directamente
            if cache_age < timedelta(minutes=CACHE_TTL_MINUTES):
                return cache["datos"]
            # Si es vieja, servir pero actualizar en background
            if background_tasks:
                background_tasks.add_task(_sync_competidores_cache, codigo)
            return cache["datos"]
        
        # 2. Sin caché - petición directa
        result = await _fetch_competidores(codigo)
        
        # Guardar en caché
        await db.insurama_cache.update_one(
            {"tipo": cache_key},
            {"$set": {"tipo": cache_key, "datos": result, "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo competidores para {codigo}: {e}")
        # Intentar caché vieja como fallback
        cache = await db.insurama_cache.find_one({"tipo": f"competidores_{codigo.upper()}"}, {"_id": 0})
        if cache and cache.get("datos"):
            return cache["datos"]
        raise HTTPException(status_code=500, detail=str(e))

async def _sync_competidores_cache(codigo: str):
    """Sincroniza competidores de un siniestro en background"""
    try:
        result = await _fetch_competidores(codigo)
        cache_key = f"competidores_{codigo.upper()}"
        await db.insurama_cache.update_one(
            {"tipo": cache_key},
            {"$set": {"tipo": cache_key, "datos": result, "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error syncing competidores cache for {codigo}: {e}")

async def _fetch_competidores(codigo: str) -> dict:
    """Fetch competidores from Sumbroker API"""
    try:
        client = await get_sumbroker_client()
        budget = await client.find_budget_by_service_code(codigo)
        
        if not budget:
            raise HTTPException(status_code=404, detail=f"No se encontró presupuesto con código {codigo}")
        
        claim_budget_id = budget.get("claim_budget_id")
        my_budget_id = budget.get("id")
        
        if not claim_budget_id:
            return {
                "mi_presupuesto": {
                    "id": my_budget_id,
                    "precio": budget.get("price"),
                    "estado": budget.get("status_text")
                },
                "competidores": [],
                "estadisticas": None,
                "error": "No se pudo obtener el claim_budget_id"
            }
        
        # Obtener todos los presupuestos del siniestro
        all_budgets = await client.get_claim_store_budgets(claim_budget_id)
        
        if not all_budgets:
            return {
                "mi_presupuesto": {
                    "id": my_budget_id,
                    "precio": budget.get("price"),
                    "estado": budget.get("status_text")
                },
                "competidores": [],
                "estadisticas": None,
                "error": f"No se pudieron obtener los presupuestos de competidores"
            }
        
        # Obtener observaciones del siniestro UNA sola vez (son por siniestro, no por presupuesto)
        all_observations = []
        try:
            # Usar el primer budget para obtener las observaciones del siniestro
            any_budget_id = all_budgets[0].get("id") if all_budgets else None
            if any_budget_id:
                all_observations = await client.get_observations(any_budget_id)
        except Exception as e:
            logger.warning(f"Error getting observations: {e}")
        
        # Indexar observaciones por nombre de tienda que las escribió
        observaciones_por_tienda = {}
        mi_tienda_nombre = None
        
        # Primero, identificar el nombre de mi tienda
        for b in all_budgets:
            if b.get("id") == my_budget_id:
                mi_tienda_nombre = (b.get("store", {}).get("name") or "").upper()
                break
        
        # Agrupar observaciones por tienda que las escribió
        for obs in all_observations:
            user_name = (obs.get("user_name") or "").upper()
            obs_text = obs.get("observations") or obs.get("observation") or ""
            if user_name and obs_text:
                if user_name not in observaciones_por_tienda:
                    observaciones_por_tienda[user_name] = []
                observaciones_por_tienda[user_name].append(obs_text.strip())
        
        # Procesar presupuestos
        competidores = []
        mi_presupuesto = None
        precios_validos = []
        
        for b in all_budgets:
            store = b.get("store", {})
            precio = float(b.get("price", 0) or 0)
            budget_id = b.get("id")
            tienda_nombre = (store.get("name") or "").upper()
            es_mi_presupuesto = budget_id == my_budget_id
            es_mi_tienda = mi_tienda_nombre and (
                tienda_nombre == mi_tienda_nombre or
                tienda_nombre in mi_tienda_nombre or
                mi_tienda_nombre in tienda_nombre
            )
            
            # Buscar comentarios de esta tienda
            comentario = ""
            
            # Solo mostrar comentarios si:
            # 1. Es mi presupuesto principal (siempre mostrar mis comentarios)
            # 2. Es un competidor que NO es de mi tienda (mostrar sus comentarios)
            if es_mi_presupuesto or not es_mi_tienda:
                # Buscar en las observaciones indexadas
                for user_key, obs_list in observaciones_por_tienda.items():
                    # Matching flexible: la tienda puede tener variaciones de nombre
                    if tienda_nombre and (
                        tienda_nombre in user_key or 
                        user_key in tienda_nombre or
                        (user_key.split()[0] if user_key else "") in tienda_nombre
                    ):
                        comentario = " | ".join(obs_list[:2])
                        break
            
            budget_info = {
                "id": budget_id,
                "tienda_nombre": store.get("name", "N/A"),
                "tienda_ciudad": store.get("city", ""),
                "tienda_provincia": store.get("province", ""),
                "precio": b.get("price"),
                "precio_num": precio,
                "estado": b.get("status_text"),
                "estado_codigo": b.get("status"),
                "tiempo_reparacion": b.get("repair_time_text"),
                "disponibilidad": b.get("part_available_text"),
                "distancia_km": b.get("km"),
                "fecha": b.get("created_at"),
                "es_mio": budget_id == my_budget_id,
                "comentario": comentario
            }
            
            if b.get("id") == my_budget_id:
                mi_presupuesto = budget_info
            else:
                competidores.append(budget_info)
            
            if precio > 0:
                precios_validos.append(precio)
        
        # Ordenar competidores por precio (los que tienen precio primero)
        competidores.sort(key=lambda x: (x["precio_num"] == 0, x["precio_num"]))
        
        # Calcular estadísticas
        estadisticas = None
        if precios_validos:
            mi_precio = float(mi_presupuesto.get("precio", 0) or 0) if mi_presupuesto else 0
            mi_posicion = sum(1 for p in precios_validos if p < mi_precio) + 1 if mi_precio > 0 else None
            
            estadisticas = {
                "total_participantes": len(all_budgets),
                "con_precio": len(precios_validos),
                "sin_precio": len(all_budgets) - len(precios_validos),
                "precio_minimo": min(precios_validos),
                "precio_maximo": max(precios_validos),
                "precio_medio": round(sum(precios_validos) / len(precios_validos), 2),
                "mi_posicion": mi_posicion,
                "mi_precio": mi_precio
            }
        
        return {
            "codigo_siniestro": codigo,
            "mi_presupuesto": mi_presupuesto,
            "competidores": competidores,
            "estadisticas": estadisticas
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo competidores para {codigo}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/presupuesto/{codigo}/fotos")
async def obtener_fotos_presupuesto(codigo: str, user: dict = Depends(require_admin)):
    """Obtiene las fotos/documentos de un siniestro"""
    try:
        client = await get_sumbroker_client()
        data = await client.extract_service_data(codigo)
        
        if not data:
            raise HTTPException(status_code=404, detail=f"No se encontró presupuesto con código {codigo}")
        
        return {"docs": data.get("docs", []), "codigo": codigo}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/presupuesto/{codigo}/descargar-fotos")
async def descargar_fotos_presupuesto(codigo: str, user: dict = Depends(require_admin)):
    """Descarga todas las fotos de un siniestro al servidor"""
    try:
        client = await get_sumbroker_client()
        data = await client.extract_service_data(codigo)
        
        if not data:
            raise HTTPException(status_code=404, detail=f"No se encontró presupuesto con código {codigo}")
        
        docs = data.get("docs", [])
        saved = await client.download_and_save_photos(docs, codigo)
        
        return {
            "message": f"Descargadas {len(saved)} fotos",
            "archivos": saved
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/presupuesto/{codigo}/observaciones")
async def obtener_observaciones_presupuesto(codigo: str, user: dict = Depends(require_admin)):
    """Obtiene las observaciones/mensajes de un siniestro"""
    try:
        client = await get_sumbroker_client()
        budget = await client.find_budget_by_service_code(codigo)
        
        if not budget:
            raise HTTPException(status_code=404, detail=f"No se encontró presupuesto con código {codigo}")
        
        budget_id = budget.get("id")
        observations = await client.get_observations(budget_id)
        
        return {"observaciones": observations, "codigo": codigo}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== IMPORTAR A CRM ====================

@router.post("/presupuesto/{codigo}/importar")
async def importar_presupuesto_a_crm(codigo: str, user: dict = Depends(require_admin)):
    """Importa un presupuesto de Insurama como orden en el CRM"""
    try:
        client = await get_sumbroker_client()
        data = await client.extract_service_data(codigo)
        
        if not data:
            raise HTTPException(status_code=404, detail=f"No se encontró presupuesto con código {codigo}")
        
        # Verificar si ya existe
        existing = await db.ordenes.find_one({"numero_autorizacion": codigo}, {"_id": 0})
        if existing:
            raise HTTPException(status_code=400, detail=f"Ya existe una orden con autorización {codigo}")
        
        # Crear o buscar cliente
        cliente_existente = None
        if data.get("client_phone"):
            cliente_existente = await db.clientes.find_one(
                {"telefono": {"$regex": data["client_phone"][-9:]}},
                {"_id": 0}
            )
        
        if not cliente_existente:
            import uuid
            cliente_id = str(uuid.uuid4())
            nuevo_cliente = {
                "id": cliente_id,
                "nombre": data.get("client_name", ""),
                "apellidos": f"{data.get('client_last_name_1', '')} {data.get('client_last_name_2', '')}".strip(),
                "telefono": data.get("client_phone", ""),
                "email": data.get("client_email", ""),
                "dni": data.get("client_nif", ""),
                "direccion": data.get("client_address", ""),
                "ciudad": data.get("client_city", ""),
                "provincia": data.get("client_province", ""),
                "codigo_postal": data.get("client_zip", ""),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.clientes.insert_one(nuevo_cliente)
        else:
            cliente_id = cliente_existente["id"]
        
        # Crear orden
        import uuid
        from helpers import generate_barcode
        
        orden_id = str(uuid.uuid4())
        fecha_hoy = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_suffix = uuid.uuid4().hex[:8].upper()
        numero_orden = f"OT-{fecha_hoy}-{random_suffix}"
        
        nueva_orden = {
            "id": orden_id,
            "numero_orden": numero_orden,
            "numero_autorizacion": codigo,
            "cliente_id": cliente_id,
            "estado": "pendiente_recibir",
            "dispositivo": {
                "modelo": f"{data.get('device_brand') or ''} {data.get('device_model') or ''}".strip() or "Pendiente datos",
                "color": data.get("device_colour") or "",
                "imei": data.get("device_imei") or "",
                "daños": data.get("damage_description") or ""
            },
            "datos_portal": data,
            "origen": "insurama",
            "qr_code": generate_barcode(numero_orden),
            "historial_estados": [{
                "estado": "pendiente_recibir",
                "fecha": datetime.now(timezone.utc).isoformat(),
                "usuario": user.get("email", "sistema")
            }],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.ordenes.insert_one(nueva_orden)
        
        # Descargar fotos si hay
        docs = data.get("docs", [])
        fotos_guardadas = []
        if docs:
            # Ahora retorna URLs de Cloudinary directamente
            fotos_guardadas = await client.download_and_save_photos(docs, codigo, numero_orden)
            if fotos_guardadas:
                # Las URLs ya son de Cloudinary, guardarlas directamente
                fotos_orden = [{"src": url, "tipo": "portal"} for url in fotos_guardadas]
                await db.ordenes.update_one(
                    {"id": orden_id},
                    {"$set": {"fotos": fotos_orden}}
                )
        
        return {
            "message": "Presupuesto importado correctamente",
            "orden_id": orden_id,
            "numero_orden": numero_orden,
            "cliente_id": cliente_id,
            "fotos_descargadas": len(fotos_guardadas)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importando presupuesto {codigo}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== SINCRONIZACIÓN ====================

@router.post("/sincronizar")
async def sincronizar_con_insurama(user: dict = Depends(require_admin)):
    """Sincroniza estados entre CRM e Insurama"""
    try:
        client = await get_sumbroker_client()
        
        # Obtener órdenes con número de autorización (vienen de Insurama)
        ordenes_insurama = await db.ordenes.find(
            {"numero_autorizacion": {"$exists": True, "$ne": None}},
            {"_id": 0}
        ).to_list(500)
        
        actualizadas = 0
        errores = []
        
        for orden in ordenes_insurama:
            try:
                codigo = orden.get("numero_autorizacion")
                if not codigo:
                    continue
                
                # Obtener datos actuales de Insurama
                data = await client.extract_service_data(codigo)
                if not data:
                    continue
                
                # Actualizar datos del portal
                await db.ordenes.update_one(
                    {"id": orden["id"]},
                    {"$set": {
                        "datos_portal": data,
                        "datos_portal_sync": datetime.now(timezone.utc).isoformat()
                    }}
                )
                actualizadas += 1
                
            except Exception as e:
                errores.append({"codigo": orden.get("numero_autorizacion"), "error": str(e)})
        
        return {
            "message": "Sincronización completada",
            "ordenes_actualizadas": actualizadas,
            "errores": errores
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ACCIONES DE ESCRITURA ====================

@router.post("/presupuesto/{codigo}/observacion")
async def enviar_observacion(codigo: str, data: EnviarObservacionRequest, user: dict = Depends(require_admin)):
    """Envía una observación/mensaje al portal de Insurama"""
    try:
        client = await get_sumbroker_client()
        budget = await client.find_budget_by_service_code(codigo)
        
        if not budget:
            raise HTTPException(status_code=404, detail=f"No se encontró presupuesto con código {codigo}")
        
        budget_id = budget.get("id")
        result = await client.send_observation(budget_id, data.mensaje, data.visible_cliente)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Error al enviar observación"))
        
        # Guardar en historial local
        await db.ordenes.update_one(
            {"numero_autorizacion": codigo},
            {"$push": {
                "observaciones_enviadas": {
                    "mensaje": data.mensaje,
                    "visible_cliente": data.visible_cliente,
                    "fecha": datetime.now(timezone.utc).isoformat(),
                    "usuario": user.get("email")
                }
            }}
        )
        
        return {"message": "Observación enviada correctamente", "data": result.get("data")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enviando observación: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/presupuesto/{codigo}/enviar-presupuesto")
async def enviar_presupuesto_precio(codigo: str, data: EnviarPresupuestoRequest, user: dict = Depends(require_admin)):
    """Envía el presupuesto (precio y descripción) al portal de Insurama"""
    try:
        client = await get_sumbroker_client()
        budget = await client.find_budget_by_service_code(codigo)
        
        if not budget:
            raise HTTPException(status_code=404, detail=f"No se encontró presupuesto con código {codigo}")
        
        budget_id = budget.get("id")
        result = await client.submit_budget(
            budget_id, 
            data.precio, 
            data.descripcion,
            data.tiempo_reparacion,
            data.garantia_meses,
            disponibilidad_recambios=data.disponibilidad_recambios,
            tiempo_horas=data.tiempo_horas,
            tipo_recambio=data.tipo_recambio,
            tipo_garantia=data.tipo_garantia
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Error al enviar presupuesto"))
        
        # Actualizar orden local con todos los campos
        await db.ordenes.update_one(
            {"numero_autorizacion": codigo},
            {"$set": {
                "presupuesto_enviado": {
                    "precio": data.precio,
                    "descripcion": data.descripcion,
                    "tiempo_reparacion": data.tiempo_reparacion,
                    "garantia_meses": data.garantia_meses,
                    "disponibilidad_recambios": data.disponibilidad_recambios,
                    "tiempo_horas": data.tiempo_horas,
                    "tipo_recambio": data.tipo_recambio,
                    "tipo_garantia": data.tipo_garantia,
                    "fecha_envio": datetime.now(timezone.utc).isoformat(),
                    "usuario": user.get("email")
                }
            }}
        )
        
        return {"message": "Presupuesto enviado correctamente", "data": result.get("data")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enviando presupuesto: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/presupuesto/{codigo}/estado")
async def actualizar_estado_insurama(codigo: str, data: ActualizarEstadoRequest, user: dict = Depends(require_admin)):
    """Actualiza el estado del presupuesto en Insurama"""
    try:
        client = await get_sumbroker_client()
        budget = await client.find_budget_by_service_code(codigo)
        
        if not budget:
            raise HTTPException(status_code=404, detail=f"No se encontró presupuesto con código {codigo}")
        
        budget_id = budget.get("id")
        result = None
        
        # Mapear estados
        if data.estado == "recibido":
            result = await client.mark_as_received(budget_id)
        elif data.estado == "en_reparacion":
            result = await client.mark_as_in_repair(budget_id)
        elif data.estado == "reparado":
            result = await client.mark_as_repaired(budget_id)
        elif data.estado == "enviado":
            if not data.tracking_number:
                raise HTTPException(status_code=400, detail="Se requiere número de tracking para marcar como enviado")
            result = await client.mark_as_shipped(budget_id, data.tracking_number, data.transportista)
        else:
            raise HTTPException(status_code=400, detail=f"Estado no válido: {data.estado}")
        
        if not result or not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Error al actualizar estado"))
        
        # Enviar observación si hay notas
        if data.notas:
            await client.send_observation(budget_id, data.notas, visible_to_client=False)
        
        return {"message": f"Estado actualizado a '{data.estado}'", "data": result.get("data")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando estado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/presupuesto/{codigo}/tracking")
async def enviar_tracking(codigo: str, tracking_number: str, transportista: str = None, user: dict = Depends(require_admin)):
    """Envía el número de tracking al portal de Insurama"""
    try:
        client = await get_sumbroker_client()
        budget = await client.find_budget_by_service_code(codigo)
        
        if not budget:
            raise HTTPException(status_code=404, detail=f"No se encontró presupuesto con código {codigo}")
        
        budget_id = budget.get("id")
        result = await client.update_tracking(budget_id, tracking_number, transportista)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Error al enviar tracking"))
        
        # Actualizar orden local
        await db.ordenes.update_one(
            {"numero_autorizacion": codigo},
            {"$set": {
                "tracking_insurama": {
                    "numero": tracking_number,
                    "transportista": transportista,
                    "fecha_envio": datetime.now(timezone.utc).isoformat()
                }
            }}
        )
        
        return {"message": "Tracking enviado correctamente", "data": result.get("data")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enviando tracking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SUBIR FOTOS ====================

class SubirFotoRequest(BaseModel):
    tipo: str = "repair"  # before, after, repair, damage

@router.post("/presupuesto/{codigo}/fotos/subir")
async def subir_foto_insurama(
    codigo: str, 
    tipo: str = "repair",
    file: bytes = None,
    user: dict = Depends(require_admin)
):
    """
    Sube una foto al portal de Insurama/Sumbroker.
    Tipos: before (antes), after (después), repair (reparación), damage (daño)
    
    NOTA: La API de Sumbroker puede no soportar subida de fotos directamente.
    En ese caso, se guardarán localmente y se mostrará instrucciones para el portal web.
    """
    try:
        client = await get_sumbroker_client()
        budget = await client.find_budget_by_service_code(codigo)
        
        if not budget:
            raise HTTPException(status_code=404, detail=f"No se encontró presupuesto con código {codigo}")
        
        # Por ahora retornamos info sobre la limitación
        # La subida real requiere inspeccionar el tráfico del portal web
        return {
            "message": "La subida de fotos via API está en investigación",
            "info": "Por ahora, sube las fotos directamente desde el portal web de Sumbroker",
            "portal_url": "https://distribuidor.sumbroker.es",
            "codigo": codigo,
            "tipo_solicitado": tipo
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subiendo foto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/presupuesto/{codigo}/fotos/subir-desde-orden")
async def subir_fotos_desde_orden(codigo: str, user: dict = Depends(require_admin)):
    """
    Intenta subir las fotos ya guardadas en la orden al portal de Insurama.
    Busca fotos en evidencias y evidencias_tecnico de la orden.
    """
    try:
        client = await get_sumbroker_client()
        budget = await client.find_budget_by_service_code(codigo)
        
        if not budget:
            raise HTTPException(status_code=404, detail=f"No se encontró presupuesto con código {codigo}")
        
        budget_id = budget.get("id")
        
        # Buscar orden por numero_autorizacion
        orden = await db.ordenes.find_one({"numero_autorizacion": codigo}, {"_id": 0})
        if not orden:
            raise HTTPException(status_code=404, detail=f"No hay orden asociada al código {codigo}")
        
        # Recopilar fotos
        fotos_a_subir = []
        
        # Evidencias de admin (fotos ANTES típicamente)
        for ev in (orden.get("evidencias") or []):
            if isinstance(ev, str) and ev:
                fotos_a_subir.append({"path": ev, "tipo": "before"})
        
        # Evidencias de técnico (fotos DESPUÉS típicamente)
        for ev in (orden.get("evidencias_tecnico") or []):
            if isinstance(ev, str) and ev:
                fotos_a_subir.append({"path": ev, "tipo": "after"})
        
        if not fotos_a_subir:
            return {
                "message": "No hay fotos en la orden para subir",
                "codigo": codigo
            }
        
        # Intentar subir
        import os
        UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
        
        resultados = {"subidas": [], "fallidas": [], "no_soportado": False}
        
        for foto in fotos_a_subir:
            filepath = os.path.join(UPLOAD_DIR, foto["path"])
            if os.path.exists(filepath):
                result = await client.upload_photo(budget_id, filepath, foto["tipo"])
                if result.get("success"):
                    resultados["subidas"].append(foto["path"])
                elif "not supported" in result.get("error", "").lower() or "portal" in result.get("error", "").lower():
                    resultados["no_soportado"] = True
                    resultados["fallidas"].append({"archivo": foto["path"], "error": result.get("error")})
                else:
                    resultados["fallidas"].append({"archivo": foto["path"], "error": result.get("error")})
        
        if resultados["no_soportado"]:
            return {
                "message": "La subida de fotos via API no está soportada por Sumbroker",
                "info": "Debes subir las fotos manualmente desde el portal web",
                "portal_url": "https://distribuidor.sumbroker.es",
                "fotos_locales": len(fotos_a_subir),
                "codigo": codigo
            }
        
        return {
            "message": f"Proceso completado: {len(resultados['subidas'])} subidas, {len(resultados['fallidas'])} fallidas",
            "resultados": resultados
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subiendo fotos desde orden: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== RECHAZAR PRESUPUESTO ====================

class RechazarPresupuestoRequest(BaseModel):
    motivo: str
    diagnostico: Optional[str] = None

@router.post("/presupuesto/{codigo}/rechazar")
async def rechazar_presupuesto(codigo: str, data: RechazarPresupuestoRequest, user: dict = Depends(require_admin)):
    """
    Rechaza un presupuesto indicando que la reparación no es viable.
    Envía el motivo como observación al portal de Insurama.
    
    NOTA: La mayoría de portales de seguros no permiten a los talleres rechazar directamente.
    Esta acción envía una observación explicando el rechazo para que la aseguradora tome acción.
    """
    try:
        client = await get_sumbroker_client()
        budget = await client.find_budget_by_service_code(codigo)
        
        if not budget:
            raise HTTPException(status_code=404, detail=f"No se encontró presupuesto con código {codigo}")
        
        budget_id = budget.get("id")
        
        # Intentar rechazar via API
        result = await client.reject_budget(budget_id, data.motivo)
        
        # Guardar en historial local
        mensaje_rechazo = f"RECHAZO DE REPARACIÓN\nMotivo: {data.motivo}"
        if data.diagnostico:
            mensaje_rechazo += f"\nDiagnóstico: {data.diagnostico}"
        
        await db.ordenes.update_one(
            {"numero_autorizacion": codigo},
            {
                "$set": {
                    "rechazo_taller": {
                        "motivo": data.motivo,
                        "diagnostico": data.diagnostico,
                        "fecha": datetime.now(timezone.utc).isoformat(),
                        "usuario": user.get("email"),
                        "enviado_sumbroker": result.get("success", False)
                    }
                },
                "$push": {
                    "notas_insurama": {
                        "fecha": datetime.now(timezone.utc).isoformat(),
                        "mensaje": mensaje_rechazo
                    }
                }
            }
        )
        
        if not result.get("success"):
            # API no soporta rechazo directo, pero guardamos localmente
            return {
                "message": "Rechazo registrado localmente",
                "info": result.get("error", "El rechazo directo no está soportado por la API"),
                "observation_sent": result.get("observation_sent", False),
                "accion_requerida": "Comunica el rechazo manualmente desde el portal web de Sumbroker",
                "portal_url": "https://distribuidor.sumbroker.es"
            }
        
        return {
            "message": "Presupuesto rechazado correctamente",
            "data": result.get("data")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rechazando presupuesto: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ==================== CARGA MASIVA ====================

from fastapi import UploadFile, File
import pandas as pd
from io import BytesIO
import uuid

class CargaMasivaResponse(BaseModel):
    total_procesados: int
    creados: int
    actualizados: int
    errores: int
    detalles: list


def _safe_text(value, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if text.lower() == "nan":
        return default
    return text


async def _upsert_cliente_desde_sumbroker(datos_sumbroker: dict) -> str:
    dni = _safe_text(datos_sumbroker.get("client_nif"))
    email = _safe_text(datos_sumbroker.get("client_email"))
    telefono = _safe_text(datos_sumbroker.get("client_phone"))

    filtros = []
    if dni:
        filtros.append({"dni": dni})
        filtros.append({"nif": dni})
    if email:
        filtros.append({"email": email})
    if telefono:
        filtros.append({"telefono": telefono})

    existente = await db.clientes.find_one({"$or": filtros}, {"_id": 0}) if filtros else None

    nombre = _safe_text(datos_sumbroker.get("client_name"))
    apellidos = f"{_safe_text(datos_sumbroker.get('client_last_name_1'))} {_safe_text(datos_sumbroker.get('client_last_name_2'))}".strip()

    cliente_data = {
        "nombre": nombre,
        "apellidos": apellidos,
        "dni": dni,
        "telefono": telefono,
        "email": email,
        "direccion": _safe_text(datos_sumbroker.get("client_address")),
        "ciudad": _safe_text(datos_sumbroker.get("client_city")),
        "codigo_postal": _safe_text(datos_sumbroker.get("client_zip")),
        "preferencia_comunicacion": "email",
        "tipo_cliente": "particular",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if existente:
        await db.clientes.update_one({"id": existente["id"]}, {"$set": cliente_data})
        return existente["id"]

    cliente_id = str(uuid.uuid4())
    cliente_data.update({
        "id": cliente_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "idioma_preferido": "es",
        "acepta_comunicaciones_comerciales": False,
    })
    await db.clientes.insert_one(cliente_data)
    return cliente_id


def _build_dispositivo_desde_sumbroker(datos_sumbroker: dict) -> dict:
    danos = _safe_text(datos_sumbroker.get("damage_type_text"))
    if not danos:
        danos = _safe_text(datos_sumbroker.get("damage_description"))[:100]

    return {
        "marca": _safe_text(datos_sumbroker.get("device_brand")),
        "modelo": _safe_text(datos_sumbroker.get("device_model")),
        "imei": _safe_text(datos_sumbroker.get("device_imei")),
        "color": _safe_text(datos_sumbroker.get("device_colour")),
        "daños": danos,
    }


def _analizar_archivo_carga_masiva(content: bytes) -> dict:
    df = pd.read_excel(BytesIO(content))

    posibles_columnas = [
        "Numero de siniestro",
        "numero_siniestro",
        "codigo_siniestro",
        "Código",
        "codigo",
        "Siniestro",
        "siniestro",
        "claim_identifier",
    ]

    columna_codigo = next((col for col in posibles_columnas if col in df.columns), None)
    if not columna_codigo:
        raise HTTPException(
            status_code=400,
            detail=f"No se encontró columna de código de siniestro. Columnas disponibles: {list(df.columns)}",
        )

    patron_codigo = re.compile(r"^[A-Za-z0-9-]{6,}$")
    codigos_unicos = []
    codigos_set = set()
    detalles = []

    vacios = 0
    duplicados = 0
    formato_invalido = 0

    for idx, row in df.iterrows():
        fila = int(idx) + 2
        codigo = _safe_text(row[columna_codigo])

        if not codigo:
            vacios += 1
            detalles.append({
                "fila": fila,
                "codigo": "",
                "status": "vacio",
                "mensaje": "Fila sin código de siniestro",
            })
            continue

        if not patron_codigo.match(codigo):
            formato_invalido += 1
            detalles.append({
                "fila": fila,
                "codigo": codigo,
                "status": "formato_invalido",
                "mensaje": "Formato inválido (mínimo 6 caracteres alfanuméricos)",
            })
            continue

        if codigo in codigos_set:
            duplicados += 1
            detalles.append({
                "fila": fila,
                "codigo": codigo,
                "status": "duplicado",
                "mensaje": "Código duplicado en el archivo",
            })
            continue

        codigos_set.add(codigo)
        codigos_unicos.append(codigo)
        detalles.append({
            "fila": fila,
            "codigo": codigo,
            "status": "listo",
            "mensaje": "Código válido para procesamiento",
        })

    return {
        "columna_codigo": columna_codigo,
        "codigos_listos": codigos_unicos,
        "detalles": detalles,
        "resumen": {
            "total_filas": int(len(df)),
            "validos_unicos": len(codigos_unicos),
            "vacios": vacios,
            "duplicados": duplicados,
            "formato_invalido": formato_invalido,
            "existentes_en_crm": 0,
            "nuevos_estimados": len(codigos_unicos),
            "actualizaciones_estimadas": 0,
            "listos_para_procesar": len(codigos_unicos),
        },
    }


@router.post("/carga-masiva/precheck")
async def precheck_carga_masiva_siniestros(
    file: UploadFile = File(...),
    user: dict = Depends(require_admin),
):
    if not (file.filename or "").endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")

    content = await file.read()
    analisis = _analizar_archivo_carga_masiva(content)

    codigos_listos = analisis.get("codigos_listos", [])
    existentes = set()
    if codigos_listos:
        docs_existentes = await db.ordenes.find(
            {"numero_autorizacion": {"$in": codigos_listos}},
            {"_id": 0, "numero_autorizacion": 1},
        ).to_list(5000)
        existentes = {doc.get("numero_autorizacion") for doc in docs_existentes if doc.get("numero_autorizacion")}

    for detalle in analisis["detalles"]:
        if detalle["status"] == "listo":
            if detalle["codigo"] in existentes:
                detalle["status"] = "existente"
                detalle["mensaje"] = "Ya existe en CRM (se actualizará)"
            else:
                detalle["status"] = "nuevo"
                detalle["mensaje"] = "Nuevo en CRM (se creará)"

    resumen = analisis["resumen"]
    resumen["existentes_en_crm"] = len(existentes)
    resumen["actualizaciones_estimadas"] = len(existentes)
    resumen["nuevos_estimados"] = resumen["validos_unicos"] - len(existentes)

    return {
        "archivo": file.filename,
        "columna_codigo": analisis["columna_codigo"],
        "resumen": resumen,
        "detalles": analisis["detalles"],
    }


@router.post("/carga-masiva")
async def carga_masiva_siniestros(
    file: UploadFile = File(...),
    user: dict = Depends(require_admin)
):
    """
    Carga masiva de siniestros desde Excel.
    Lee los códigos de siniestro, consulta Sumbroker para obtener datos completos,
    y crea las órdenes de trabajo.
    """
    if not (file.filename or "").endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")
    
    try:
        # Obtener cliente de Sumbroker
        client = await get_sumbroker_client()
        
        # Leer Excel y analizar códigos
        content = await file.read()
        analisis = _analizar_archivo_carga_masiva(content)
        codigos = analisis.get("codigos_listos", [])

        resultados = {
            "total_procesados": len(codigos),
            "creados": 0,
            "actualizados": 0,
            "errores": 0,
            "detalles": []
        }

        for codigo in codigos:
            try:
                # Verificar si ya existe
                existente = await db.ordenes.find_one({"numero_autorizacion": codigo})
                
                # Consultar datos de Sumbroker
                logger.info(f"Consultando Sumbroker para código: {codigo}")
                datos_sumbroker = await client.extract_service_data(codigo)
                
                if not datos_sumbroker:
                    resultados["errores"] += 1
                    resultados["detalles"].append({
                        "codigo": codigo,
                        "status": "error",
                        "mensaje": "No encontrado en Sumbroker"
                    })
                    continue
                
                # Mapear estado de Sumbroker a estado CRM
                status_sumbroker = datos_sumbroker.get("status")
                estado_crm = mapear_estado_sumbroker(status_sumbroker)
                
                # Crear/actualizar cliente en CRM para mantener referencia consistente
                cliente_id = await _upsert_cliente_desde_sumbroker(datos_sumbroker)

                # Crear estructura de dispositivo
                dispositivo = _build_dispositivo_desde_sumbroker(datos_sumbroker)
                
                if existente:
                    # Actualizar orden existente
                    await db.ordenes.update_one(
                        {"_id": existente["_id"]},
                        {"$set": {
                            "estado": estado_crm,
                            "cliente_id": cliente_id,
                            "dispositivo": dispositivo,
                            "datos_sumbroker": datos_sumbroker,
                            "presupuesto_total": datos_sumbroker.get("price") or 0,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    resultados["actualizados"] += 1
                    resultados["detalles"].append({
                        "codigo": codigo,
                        "status": "actualizado",
                        "mensaje": f"Actualizado: {dispositivo['marca']} {dispositivo['modelo']}"
                    })
                else:
                    # Crear nueva orden
                    orden_id = str(uuid.uuid4())
                    nueva_orden = {
                        "id": orden_id,
                        "numero_orden": f"INS-{codigo[-6:]}",
                        "numero_autorizacion": codigo,
                        "estado": estado_crm,
                        "prioridad": "normal",
                        "tipo_servicio": "seguro",
                        "origen": "insurama",

                        # Campos mínimos del esquema de orden
                        "cliente_id": cliente_id,
                        "dispositivo": dispositivo,
                        "materiales": [],
                        "token_seguimiento": str(uuid.uuid4())[:12].upper(),
                        "evidencias": [],
                        "evidencias_tecnico": [],
                        "fotos_antes": [],
                        "fotos_despues": [],
                        "mensajes": [],
                        "historial_estados": [{
                            "estado": estado_crm,
                            "fecha": datetime.now(timezone.utc).isoformat(),
                            "usuario": user.get("email", "Sistema"),
                            "notas": f"Importado desde carga masiva - Estado Sumbroker: {datos_sumbroker.get('status_text')}"
                        }],

                        # Datos de negocio de Insurama
                        "poliza": _safe_text(datos_sumbroker.get("policy_number")),
                        "presupuesto_total": float(datos_sumbroker.get("price") or 0),
                        "coste_materiales": 0,
                        "coste_mano_obra": float(datos_sumbroker.get("price") or 0),
                        "cliente_nombre": _safe_text(datos_sumbroker.get("client_full_name")),
                        "cliente_telefono": _safe_text(datos_sumbroker.get("client_phone")),
                        "cliente_email": _safe_text(datos_sumbroker.get("client_email")),
                        "dispositivo_marca": dispositivo["marca"],
                        "dispositivo_modelo": dispositivo["modelo"],
                        "dispositivo_imei": dispositivo["imei"],
                        "averia_tipo": _safe_text(datos_sumbroker.get("damage_type_text")),
                        "averia_descripcion": _safe_text(datos_sumbroker.get("damage_description")),
                        "datos_sumbroker": datos_sumbroker,
                        "insurama_status": _safe_text(datos_sumbroker.get("status_text")),
                        "cobertura": _safe_text(datos_sumbroker.get("product_name")),
                        "garantia_tipo": _safe_text(datos_sumbroker.get("warranty_type_text")),
                        "notas_internas": f"Importado desde Sumbroker. Estado original: {datos_sumbroker.get('status_text')}",

                        # Fechas
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "fecha_entrada": datetime.now(timezone.utc).isoformat(),
                    }
                    
                    await db.ordenes.insert_one(nueva_orden)
                    resultados["creados"] += 1
                    resultados["detalles"].append({
                        "codigo": codigo,
                        "status": "creado",
                        "mensaje": f"Creado: {dispositivo['marca']} {dispositivo['modelo']} - {datos_sumbroker.get('client_full_name')}"
                    })
                    
            except Exception as e:
                logger.error(f"Error procesando código {codigo}: {e}")
                resultados["errores"] += 1
                resultados["detalles"].append({
                    "codigo": codigo,
                    "status": "error",
                    "mensaje": str(e)
                })
        
        return resultados
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en carga masiva: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def mapear_estado_sumbroker(status) -> str:
    """
    Mapea estado de Sumbroker a estado del CRM.
    Sumbroker: 1=Pending, 2=Sent, 3=Accepted, 4=Modified, 5=Repaired, 6=Delivered, 7=Cancelled
    """
    if status is None:
        return "pendiente_recibir"
    
    try:
        status = int(status)
    except (TypeError, ValueError):
        return "pendiente_recibir"
    
    mapping = {
        1: "pendiente_recibir",  # Pending
        2: "pendiente_recibir",  # Sent (presupuesto enviado)
        3: "recibida",           # Accepted (presupuesto aceptado)
        4: "en_taller",          # Modified
        5: "validacion",         # Repaired
        6: "enviado",            # Delivered en portal => enviado en CRM
        7: "cancelado",          # Cancelled
    }
    
    return mapping.get(status, "pendiente_recibir")

"""
Scheduler para sincronización automática de proveedores.
Ejecuta sincronizaciones de MobileSentrix y Utopya de forma programada.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
import threading
import time

from config import db, logger

# Estado global del scheduler
scheduler_state = {
    "running": False,
    "last_check": None,
    "next_sync": None,
    "mobilesentrix_last_auto_sync": None,
    "utopya_last_auto_sync": None
}

async def get_scheduler_config():
    """Obtener configuración del scheduler"""
    config = await db.configuracion.find_one({"tipo": "sync_scheduler"}, {"_id": 0})
    if not config:
        # Configuración por defecto
        config = {
            "tipo": "sync_scheduler",
            "enabled": False,
            "interval_days": 7,  # Semanal por defecto
            "sync_mobilesentrix": True,
            "sync_utopya": True,
            "preferred_hour": 3,  # 3 AM
            "last_auto_sync": None
        }
        await db.configuracion.insert_one(config)
    return config

async def save_scheduler_config(config: dict):
    """Guardar configuración del scheduler"""
    config["tipo"] = "sync_scheduler"
    await db.configuracion.update_one(
        {"tipo": "sync_scheduler"},
        {"$set": config},
        upsert=True
    )

async def should_run_sync() -> bool:
    """Verificar si es momento de ejecutar sincronización"""
    config = await get_scheduler_config()
    
    if not config.get("enabled"):
        return False
    
    last_sync = config.get("last_auto_sync")
    interval_days = config.get("interval_days", 7)
    
    if not last_sync:
        return True
    
    try:
        last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
        next_sync_dt = last_sync_dt + timedelta(days=interval_days)
        scheduler_state["next_sync"] = next_sync_dt.isoformat()
        
        return datetime.now(timezone.utc) >= next_sync_dt
    except:
        return True

async def run_auto_sync():
    """Ejecutar sincronización automática de proveedores"""
    from routes.mobilesentrix_routes import sync_catalogo_task, get_mobilesentrix_config
    from routes.utopya_routes import scrape_utopya_products, get_utopya_config
    
    config = await get_scheduler_config()
    logger.info("=== INICIANDO SINCRONIZACIÓN AUTOMÁTICA ===")
    
    # Sincronizar MobileSentrix
    if config.get("sync_mobilesentrix", True):
        try:
            logger.info("Auto-sync: Iniciando MobileSentrix...")
            ms_config = await get_mobilesentrix_config()
            
            if ms_config.get("sync_products") and ms_config.get("access_token"):
                selected_cats = ms_config.get("selected_categories", [])
                
                # Obtener margen
                margenes_config = await db.configuracion.find_one({"tipo": "margenes_proveedores"}, {"_id": 0})
                margen = 27.0
                if margenes_config and margenes_config.get("proveedores", {}).get("MobileSentrix"):
                    margen = margenes_config["proveedores"]["MobileSentrix"].get("margen", 27.0)
                
                await sync_catalogo_task(margen, selected_cats)
                scheduler_state["mobilesentrix_last_auto_sync"] = datetime.now(timezone.utc).isoformat()
                logger.info("Auto-sync: MobileSentrix completado")
            else:
                logger.warning("Auto-sync: MobileSentrix no configurado o sin permisos")
        except Exception as e:
            logger.error(f"Auto-sync: Error en MobileSentrix: {e}")
    
    # Sincronizar Utopya
    if config.get("sync_utopya", True):
        try:
            logger.info("Auto-sync: Iniciando Utopya...")
            uto_config = await get_utopya_config()
            
            email = uto_config.get("email")
            password = uto_config.get("password")
            selected_cats = uto_config.get("categorias_seleccionadas", [])
            
            if email and password and selected_cats:
                # Obtener margen
                margenes_config = await db.configuracion.find_one({"tipo": "margenes_proveedores"}, {"_id": 0})
                margen = 25.0
                if margenes_config and margenes_config.get("proveedores", {}).get("Utopya"):
                    margen = margenes_config["proveedores"]["Utopya"].get("margen", 25.0)
                
                await scrape_utopya_products(email, password, selected_cats, margen)
                scheduler_state["utopya_last_auto_sync"] = datetime.now(timezone.utc).isoformat()
                logger.info("Auto-sync: Utopya completado")
            else:
                logger.warning("Auto-sync: Utopya no configurado (faltan credenciales o categorías)")
        except Exception as e:
            logger.error(f"Auto-sync: Error en Utopya: {e}")
    
    # Actualizar timestamp de última sincronización
    config["last_auto_sync"] = datetime.now(timezone.utc).isoformat()
    await save_scheduler_config(config)
    
    logger.info("=== SINCRONIZACIÓN AUTOMÁTICA COMPLETADA ===")

async def scheduler_loop():
    """Loop principal del scheduler"""
    global scheduler_state
    
    logger.info("Scheduler: Iniciando loop de sincronización automática")
    
    while scheduler_state["running"]:
        try:
            scheduler_state["last_check"] = datetime.now(timezone.utc).isoformat()
            
            if await should_run_sync():
                logger.info("Scheduler: Es momento de sincronizar")
                await run_auto_sync()
            
            # Esperar 1 hora antes de verificar de nuevo
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            await asyncio.sleep(60)  # Esperar 1 minuto en caso de error

def start_scheduler():
    """Iniciar el scheduler en un thread separado"""
    global scheduler_state
    
    if scheduler_state["running"]:
        return False
    
    scheduler_state["running"] = True
    
    def run_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scheduler_loop())
    
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    
    logger.info("Scheduler iniciado")
    return True

def stop_scheduler():
    """Detener el scheduler"""
    global scheduler_state
    scheduler_state["running"] = False
    logger.info("Scheduler detenido")

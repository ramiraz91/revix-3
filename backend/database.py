"""
database.py — Configuración de conexión MongoDB

Configuración con fallback de seguridad a la BD privada del cliente.
- Primero intenta usar variables de entorno (para Kubernetes/Emergent)
- Si no existen, usa la BD privada de Revix como fallback
"""

import os
import sys
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

# Cargar .env solo si las variables no están ya definidas (Kubernetes las define)
load_dotenv(override=False)

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE BASE DE DATOS CON FALLBACK DE SEGURIDAD
# ══════════════════════════════════════════════════════════════════════════════
# Prioridad:
# 1. Variables de entorno (MONGO_URL, DB_NAME) - para Kubernetes/Emergent
# 2. Fallback: BD privada de Revix en MongoDB Atlas
# ══════════════════════════════════════════════════════════════════════════════

# Fallback de seguridad - BD privada de Revix
_FALLBACK_MONGO_URL = "mongodb+srv://revix_app:xTGydIpZKsgfTtuV@revix.d7soggd.mongodb.net/production?retryWrites=true&w=majority&appName=Revix"
_FALLBACK_DB_NAME = "production"

# Usar variable de entorno SI existe, sino usar el fallback
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URL") or _FALLBACK_MONGO_URL
DB_NAME = os.getenv("DB_NAME") or _FALLBACK_DB_NAME

# Log de la conexión (sin exponer credenciales)
_using_fallback = (MONGO_URL == _FALLBACK_MONGO_URL)
if _using_fallback:
    logger.info("📦 Usando BD de fallback (Revix Atlas privado)")
else:
    logger.info("📦 Usando BD desde variables de entorno")

# ── Clientes ──────────────────────────────────────────────────────────────────

async_client: AsyncIOMotorClient = None
async_db = None

sync_client: MongoClient = None
sync_db = None


# ── Inicialización async (FastAPI) ────────────────────────────────────────────

async def connect_db():
    """Conecta a MongoDB de forma asíncrona (para FastAPI)"""
    global async_client, async_db
    try:
        async_client = AsyncIOMotorClient(
            MONGO_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
            maxPoolSize=10,
            retryWrites=True,
        )
        await async_client.admin.command("ping")
        async_db = async_client[DB_NAME]
        logger.info(f"✅ MongoDB conectado — base de datos: '{DB_NAME}'")
        return async_db
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.critical(f"❌ No se pudo conectar a MongoDB: {e}")
        sys.exit(1)


async def disconnect_db():
    """Desconecta de MongoDB"""
    global async_client
    if async_client:
        async_client.close()
        logger.info("🔌 MongoDB desconectado")


def get_db():
    """Obtiene la instancia de la base de datos async"""
    if async_db is None:
        raise RuntimeError("Base de datos no inicializada. ¿Llamaste a connect_db()?")
    return async_db


# ── Inicialización sync (tests / scripts) ────────────────────────────────────

def connect_db_sync():
    """Conecta a MongoDB de forma síncrona (para tests y scripts)"""
    global sync_client, sync_db
    try:
        sync_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        sync_client.admin.command("ping")
        sync_db = sync_client[DB_NAME]
        logger.info(f"✅ MongoDB (sync) conectado — base de datos: '{DB_NAME}'")
        return sync_db
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.critical(f"❌ No se pudo conectar a MongoDB (sync): {e}")
        raise


def get_db_sync():
    """Obtiene la instancia de la base de datos sync"""
    if sync_db is None:
        return connect_db_sync()
    return sync_db


# ── Colecciones ───────────────────────────────────────────────────────────────

class Collections:
    """Acceso centralizado a las colecciones de la base de datos"""
    
    @staticmethod
    def clientes(db):
        return db["clientes"]
    
    @staticmethod
    def proveedores(db):
        return db["proveedores"]
    
    @staticmethod
    def repuestos(db):
        return db["repuestos"]
    
    @staticmethod
    def ordenes(db):
        return db["ordenes"]
    
    @staticmethod
    def users(db):
        return db["users"]
    
    @staticmethod
    def presupuestos(db):
        return db["presupuestos"]
    
    @staticmethod
    def facturas(db):
        return db["facturas"]
    
    @staticmethod
    def notificaciones(db):
        return db["notificaciones"]
    
    @staticmethod
    def movimientos_stock(db):
        return db["movimientos_stock"]
    
    @staticmethod
    def pre_registros(db):
        return db["pre_registros"]
    
    @staticmethod
    def incidencias(db):
        return db["incidencias"]


# ── Índices ───────────────────────────────────────────────────────────────────

async def crear_indices():
    """Crea los índices necesarios en MongoDB"""
    db = get_db()
    try:
        # Clientes
        await db["clientes"].create_index("dni", unique=True, sparse=True)
        await db["clientes"].create_index("email", unique=True, sparse=True)
        await db["clientes"].create_index("telefono")
        
        # Usuarios
        await db["users"].create_index("email", unique=True)
        
        # Órdenes
        await db["ordenes"].create_index("numero_orden", unique=True, sparse=True)
        await db["ordenes"].create_index("cliente_id")
        await db["ordenes"].create_index("estado")
        await db["ordenes"].create_index("created_at")
        await db["ordenes"].create_index("tecnico_asignado")
        
        # Repuestos
        await db["repuestos"].create_index("nombre")
        await db["repuestos"].create_index("categoria")
        await db["repuestos"].create_index("sku", unique=True, sparse=True)
        await db["repuestos"].create_index([("stock", 1), ("stock_minimo", 1)])
        
        # Presupuestos y Facturas
        await db["presupuestos"].create_index("numero", unique=True, sparse=True)
        await db["presupuestos"].create_index("orden_id")
        await db["facturas"].create_index("numero", unique=True, sparse=True)
        await db["facturas"].create_index("orden_id")
        
        # Pre-registros (Insurama)
        await db["pre_registros"].create_index("siniestro", unique=True, sparse=True)
        await db["pre_registros"].create_index("estado")
        
        logger.info("✅ Índices MongoDB creados/verificados")
    except Exception as e:
        logger.warning(f"⚠️ Error creando índices: {e}")


# ── Health check ──────────────────────────────────────────────────────────────

async def health_check() -> dict:
    """Verifica el estado de la conexión a MongoDB"""
    try:
        await async_client.admin.command("ping")
        info = await async_client.server_info()
        return {
            "status": "ok",
            "database": DB_NAME,
            "mongo_version": info.get("version", "?"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ── Utilidades ────────────────────────────────────────────────────────────────

async def test_connection() -> bool:
    """Prueba la conexión a MongoDB"""
    try:
        client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=3000)
        await client.admin.command("ping")
        client.close()
        return True
    except Exception:
        return False

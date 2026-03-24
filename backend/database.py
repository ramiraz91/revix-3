"""
database.py — Configuración de conexión MongoDB
⚠️  BASE DE DATOS DE PRODUCCIÓN - NO MODIFICAR ⚠️

IMPORTANTE: Este archivo está configurado para usar EXCLUSIVAMENTE
la base de datos privada del cliente en MongoDB Atlas.
NO cambiar MONGO_URL ni DB_NAME bajo ninguna circunstancia.
"""

import os
import sys
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# ⚠️  CONFIGURACIÓN FIJA DE BASE DE DATOS - NO MODIFICAR ⚠️
# ══════════════════════════════════════════════════════════════════════════════
# 
# Base de datos: MongoDB Atlas (Cluster privado del cliente)
# Host: revix.d7soggd.mongodb.net
# Database: production
#
# NUNCA usar otra base de datos. NUNCA cambiar estos valores.
# ══════════════════════════════════════════════════════════════════════════════

# URL FIJA - Solo se puede sobrescribir con variable de entorno
_FIXED_MONGO_URL = "mongodb+srv://revix_app:xTGydIpZKsgfTtuV@revix.d7soggd.mongodb.net/production?retryWrites=true&w=majority&appName=Revix"
_FIXED_DB_NAME = "production"

# Usar variable de entorno SI existe, sino usar la fija
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URL") or _FIXED_MONGO_URL
DB_NAME = os.getenv("DB_NAME") or _FIXED_DB_NAME

# Validación: Asegurar que siempre apunte al cluster correcto
if "revix.d7soggd.mongodb.net" not in MONGO_URL:
    logger.critical("⛔ ERROR CRÍTICO: MONGO_URL no apunta al cluster correcto (revix.d7soggd.mongodb.net)")
    logger.critical(f"⛔ URL detectada: {MONGO_URL[:50]}...")
    logger.critical("⛔ Usando URL fija de seguridad")
    MONGO_URL = _FIXED_MONGO_URL

if DB_NAME != "production":
    logger.warning(f"⚠️  DB_NAME no es 'production', es '{DB_NAME}'. Corrigiendo...")
    DB_NAME = "production"

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

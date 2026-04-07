"""
config.py — Configuración central de Revix CRM
- Carga variables de entorno
- Importa la conexión de database.py (sin duplicar cliente)
- Expone `db` como alias global para compatibilidad con todos los routes
"""

from fastapi.security import HTTPBearer
from pathlib import Path
from urllib.parse import urlparse
import os
import logging
import sys

# ── Cargar variables de entorno ───────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
from dotenv import load_dotenv
# override=True para que .env tenga prioridad en PREVIEW
# En producción, las System Keys de Emergent se inyectan DESPUÉS del arranque
load_dotenv(ROOT_DIR / '.env', override=True)

# ── Base de datos: usar SIEMPRE database.py como fuente única ─────────────────
from database import (
    MONGO_URL, DB_NAME,
    async_client, async_db,
    connect_db, disconnect_db, get_db,
    connect_db_sync, get_db_sync,
    crear_indices, health_check, test_connection,
    Collections
)

# Alias global `db` para compatibilidad con todos los routes existentes
# Se inicializa en el startup — aquí solo exponemos el cliente para acceso directo
from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = MONGO_URL
db_name   = DB_NAME

_safe_host = urlparse(mongo_url).hostname or mongo_url[:40]
print(f"📦 MongoDB → {_safe_host} / {db_name}")

# Cliente único — compartido con database.py
client = AsyncIOMotorClient(
    mongo_url,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
    socketTimeoutMS=30000,
    maxPoolSize=10,
    retryWrites=True,
)
db = client[db_name]

# ── JWT ───────────────────────────────────────────────────────────────────────
JWT_SECRET    = os.environ.get('JWT_SECRET', 'techrepair-secret-key-2026')
JWT_ALGORITHM = "HS256"

if JWT_SECRET == 'techrepair-secret-key-2026':
    import warnings
    warnings.warn(
        "⚠️ SEGURIDAD: JWT_SECRET usa el valor por defecto. "
        "Define JWT_SECRET en .env para producción.",
        UserWarning
    )

# ── Servicios externos ────────────────────────────────────────────────────────
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

TWILIO_ACCOUNT_SID  = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN   = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

SENDGRID_API_KEY    = os.environ.get('SENDGRID_API_KEY')
SENDGRID_FROM_EMAIL = os.environ.get('SENDGRID_FROM_EMAIL', 'help@revix.es')

# ── Resend (Email) ─────────────────────────────────────────────────────────────
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'notificaciones@revix.es')
RESEND_CONFIGURED = bool(RESEND_API_KEY)

# ── URLs ──────────────────────────────────────────────────────────────────────
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://revix.es')

# ── Directorios ───────────────────────────────────────────────────────────────
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# ── Seguridad ─────────────────────────────────────────────────────────────────
security = HTTPBearer(auto_error=False)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# ── Clientes mutables (se inicializan en startup) ─────────────────────────────
twilio_client   = None
sendgrid_client = None

from dotenv import load_dotenv
from fastapi.security import HTTPBearer
from pathlib import Path
from urllib.parse import urlparse
import os
import logging
import sys

# ── Cargar variables de entorno ───────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env', override=True)

# ── Importar módulo de base de datos mejorado ─────────────────────────────────
from database import (
    MONGO_URL, DB_NAME,
    async_client, async_db,
    connect_db, disconnect_db, get_db,
    connect_db_sync, get_db_sync,
    crear_indices, health_check, test_connection,
    Collections
)

# Compatibilidad: mantener 'db' como alias global para código existente
from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = MONGO_URL
db_name = DB_NAME

print(f"MongoDB -> {urlparse(mongo_url).hostname or mongo_url[:40]}")
print(f"DB: {db_name}")

# Cliente y DB (inicialización inmediata para compatibilidad)
client = AsyncIOMotorClient(
    mongo_url,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
    socketTimeoutMS=30000,
    maxPoolSize=10,
    retryWrites=True,
)
db = client[db_name]

# JWT
JWT_SECRET = os.environ.get('JWT_SECRET', 'techrepair-secret-key-2026')
JWT_ALGORITHM = "HS256"

# Advertencia de seguridad para producción
if JWT_SECRET == 'techrepair-secret-key-2026':
    import warnings
    warnings.warn(
        "⚠️ SEGURIDAD: JWT_SECRET está usando el valor por defecto. "
        "Configura JWT_SECRET en .env para producción.",
        UserWarning
    )

# LLM
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Twilio
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

# SendGrid (legacy, kept for reference)
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
SENDGRID_FROM_EMAIL = os.environ.get('SENDGRID_FROM_EMAIL', 'help@revix.es')

# SMTP (primary email)
SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '465'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
SMTP_FROM = os.environ.get('SMTP_FROM', '')
SMTP_REPLY_TO = os.environ.get('SMTP_REPLY_TO', '')
SMTP_SECURE = os.environ.get('SMTP_SECURE', 'true').lower() == 'true'
SMTP_CONFIGURED = bool(SMTP_HOST and SMTP_USER)

# URLs
FRONTEND_URL = os.environ.get('FRONTEND_URL')

# Upload directory
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Security
security = HTTPBearer(auto_error=False)

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mutable clients (set on startup)
twilio_client = None
sendgrid_client = None

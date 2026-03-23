from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.security import HTTPBearer
from pathlib import Path
from urllib.parse import urlparse
import os
import logging
import sys

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# ==================== MONGODB - CONFIGURACIÓN CON PRIORIDAD CUSTOM ====================
#
# Emergent sobreescribe MONGO_URL y DB_NAME en cada deploy.
# Para usar tu propia BD Atlas, configura en Secrets de Emergent:
#   CUSTOM_MONGO_URL = tu connection string de Atlas
#   CUSTOM_DB_NAME = tu nombre de base de datos
# Estas variables tienen PRIORIDAD sobre MONGO_URL y DB_NAME.
#

mongo_url = os.environ.get('CUSTOM_MONGO_URL') or os.environ.get('MONGO_URL', 'mongodb://localhost:27017')

# Detectar si es localhost (entorno de desarrollo/preview)
is_localhost = 'localhost' in mongo_url or '127.0.0.1' in mongo_url
is_atlas = 'mongodb.net' in mongo_url or 'mongodb+srv' in mongo_url
is_custom = bool(os.environ.get('CUSTOM_MONGO_URL'))

if is_custom:
    parsed = urlparse(mongo_url)
    host_display = parsed.hostname or "MongoDB Atlas"
    print(f"CUSTOM MongoDB conectado a: {host_display}")
elif is_atlas:
    parsed = urlparse(mongo_url)
    host_display = parsed.hostname or "MongoDB Atlas"
    print(f"MongoDB PRODUCCION conectado a: {host_display}")
elif is_localhost:
    print("MongoDB LOCAL (preview/desarrollo)")
else:
    print(f"MongoDB conectado a: {mongo_url[:50]}...")

client = AsyncIOMotorClient(
    mongo_url,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
    socketTimeoutMS=30000,
)

db_name = os.environ.get('CUSTOM_DB_NAME') or os.environ.get('DB_NAME', 'production')
db = client[db_name]
print(f"Base de datos: {db_name}{' (CUSTOM)' if os.environ.get('CUSTOM_DB_NAME') else ''}")

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

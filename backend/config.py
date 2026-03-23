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

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'production')

import socket
def _is_local_mongo():
    try:
        s = socket.create_connection(("localhost", 27017), timeout=1)
        s.close()
        return True
    except:
        return False

if _is_local_mongo() and 'localhost' not in mongo_url:
    mongo_url = 'mongodb://localhost:27017'
    db_name = 'production'
    print(f"MongoDB -> localhost (preview)")
else:
    print(f"MongoDB -> {urlparse(mongo_url).hostname or mongo_url[:40]}")
print(f"DB: {db_name}")

client = AsyncIOMotorClient(
    mongo_url,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
    socketTimeoutMS=30000,
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

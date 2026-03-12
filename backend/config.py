from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.security import HTTPBearer
from pathlib import Path
from urllib.parse import urlparse
import os
import logging

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB - with connection options for both local and Atlas
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(
    mongo_url,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
    socketTimeoutMS=30000,
)

db_name = os.environ.get('DB_NAME', 'production')
db = client[db_name]
print(f"[CONFIG] Base de datos: {db_name}")

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
SMTP_CONFIGURED = bool(SMTP_HOST and SMTP_USER)

# URLs
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://repair-workshop-crm.preview.emergentagent.com')

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

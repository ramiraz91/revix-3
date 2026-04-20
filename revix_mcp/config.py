"""
Revix MCP Server — Configuración central.

Lee variables de entorno; usa defaults seguros cuando tiene sentido,
aborta en arranque si falta algo crítico.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Prioridad de carga de env:
# 1. .env del MCP si existe (para desarrollo local)
# 2. Variables ya presentes en el entorno (para despliegue)
load_dotenv(BASE_DIR / '.env', override=False)

# También toma credenciales del backend si compartimos pod
load_dotenv(BASE_DIR.parent / 'backend' / '.env', override=False)


def _required(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        print(f'❌ MCP config: falta variable de entorno requerida: {name}', file=sys.stderr)
        sys.exit(2)
    return v


# ── Mongo ─────────────────────────────────────────────────────────────────────
MONGO_URL = _required('MONGO_URL')
DB_NAME = _required('DB_NAME')

# ── Entorno ───────────────────────────────────────────────────────────────────
# preview | production
# En preview los side effects (emails, webhooks, GLS) se mockean.
MCP_ENV = os.environ.get('MCP_ENV', 'preview').lower()
assert MCP_ENV in ('preview', 'production'), f'MCP_ENV inválido: {MCP_ENV}'

# ── Backend Revix ─────────────────────────────────────────────────────────────
# URL interna al backend para que tools hagan HTTP calls si lo necesitan.
REVIX_BACKEND_URL = os.environ.get('REVIX_BACKEND_URL', 'http://localhost:8001')

# ── Transporte ────────────────────────────────────────────────────────────────
# stdio | http
MCP_TRANSPORT = os.environ.get('MCP_TRANSPORT', 'stdio').lower()
MCP_HTTP_HOST = os.environ.get('MCP_HTTP_HOST', '127.0.0.1')
MCP_HTTP_PORT = int(os.environ.get('MCP_HTTP_PORT', '8765'))

# ── Audit ─────────────────────────────────────────────────────────────────────
AUDIT_COLLECTION = 'audit_logs'
API_KEYS_COLLECTION = 'mcp_api_keys'
IDEMPOTENCY_COLLECTION = 'mcp_idempotency'

# ── Rate limit por defecto (si no está en la API key) ─────────────────────────
DEFAULT_RATE_LIMIT_PER_MIN = 120

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get('MCP_LOG_LEVEL', 'INFO').upper()


def info_banner() -> str:
    return (
        f'Revix MCP · db={DB_NAME} · env={MCP_ENV} · transport={MCP_TRANSPORT}'
    )

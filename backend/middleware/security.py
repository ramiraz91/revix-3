"""
Middleware de seguridad para el CRM Revix.
- Rate limiting por IP y por usuario
- Sanitizacion de inputs MongoDB
- Logs de seguridad
"""
import re
import time
import logging
from datetime import datetime, timezone
from collections import defaultdict
from typing import Optional

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("security")

# ═══════════════════════════════════════════════════════
#  RATE LIMITER (en memoria, por IP)
# ═══════════════════════════════════════════════════════

class RateLimitStore:
    """Almacena contadores de peticiones por IP con ventana deslizante."""

    def __init__(self):
        self._requests = defaultdict(list)  # ip -> [timestamps]
        self._login_attempts = defaultdict(list)  # ip -> [timestamps]

    def _clean(self, entries, window):
        now = time.time()
        return [t for t in entries if now - t < window]

    def check_rate(self, ip: str, limit: int, window: int) -> bool:
        """Retorna True si la peticion esta permitida."""
        self._requests[ip] = self._clean(self._requests[ip], window)
        if len(self._requests[ip]) >= limit:
            return False
        self._requests[ip].append(time.time())
        return True

    def check_login(self, ip: str, limit: int = 5, window: int = 900) -> bool:
        """Rate limit especifico para login (5 intentos en 15 min)."""
        self._login_attempts[ip] = self._clean(self._login_attempts[ip], window)
        if len(self._login_attempts[ip]) >= limit:
            return False
        self._login_attempts[ip].append(time.time())
        return True

    def get_login_remaining(self, ip: str, limit: int = 5, window: int = 900) -> int:
        self._login_attempts[ip] = self._clean(self._login_attempts[ip], window)
        return max(0, limit - len(self._login_attempts[ip]))


rate_store = RateLimitStore()

# Configuracion de limites por tipo de endpoint
RATE_LIMITS = {
    "login":    {"limit": 5,   "window": 900},    # 5 intentos / 15 min
    "public":   {"limit": 30,  "window": 60},     # 30 req / min
    "api":      {"limit": 200, "window": 60},     # 200 req / min
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.client.host
        path = request.url.path

        # Login rate limit (mas estricto)
        if path == "/api/auth/login" and request.method == "POST":
            cfg = RATE_LIMITS["login"]
            if not rate_store.check_login(ip, cfg["limit"], cfg["window"]):
                remaining = rate_store.get_login_remaining(ip)
                logger.warning(f"RATE_LIMIT login bloqueado: IP={ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Demasiados intentos de inicio de sesion. Espere 15 minutos.",
                        "retry_after": 900,
                    },
                    headers={"Retry-After": "900"},
                )

        # Endpoints publicos (seguimiento, contacto, web)
        elif any(path.startswith(p) for p in ["/api/seguimiento", "/api/web/", "/api/contacto"]):
            cfg = RATE_LIMITS["public"]
            if not rate_store.check_rate(f"pub:{ip}", cfg["limit"], cfg["window"]):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Demasiadas peticiones. Intente de nuevo en un minuto."},
                    headers={"Retry-After": "60"},
                )

        # API general (autenticada)
        elif path.startswith("/api/"):
            cfg = RATE_LIMITS["api"]
            if not rate_store.check_rate(f"api:{ip}", cfg["limit"], cfg["window"]):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Limite de peticiones excedido."},
                    headers={"Retry-After": "60"},
                )

        response = await call_next(request)
        return response


# ═══════════════════════════════════════════════════════
#  SANITIZACION NOSQL
# ═══════════════════════════════════════════════════════

# Operadores MongoDB peligrosos
NOSQL_OPERATORS = re.compile(r'\$(?:gt|gte|lt|lte|ne|in|nin|or|and|not|nor|regex|where|exists|type|expr|jsonSchema|mod|text|all|elemMatch|size)')


def sanitize_value(value):
    """Elimina operadores MongoDB de un valor de entrada."""
    if isinstance(value, str):
        if NOSQL_OPERATORS.search(value):
            return re.sub(r'\$', '', value)
        # Limitar longitud
        return value[:10000]
    elif isinstance(value, dict):
        # Bloquear claves que empiecen con $
        return {
            k: sanitize_value(v)
            for k, v in value.items()
            if not k.startswith('$')
        }
    elif isinstance(value, list):
        return [sanitize_value(v) for v in value[:1000]]
    return value


def sanitize_query_params(params: dict) -> dict:
    """Sanitiza parametros de query string."""
    return {k: sanitize_value(v) for k, v in params.items()}


# ═══════════════════════════════════════════════════════
#  LOGS DE SEGURIDAD
# ═══════════════════════════════════════════════════════

class SecurityLogger:
    """Registra eventos de seguridad."""

    def __init__(self):
        self._failed_logins = defaultdict(int)

    def log_failed_login(self, ip: str, email: str):
        self._failed_logins[ip] += 1
        count = self._failed_logins[ip]
        logger.warning(
            f"LOGIN_FALLIDO #{count}: IP={ip} email={email}"
        )
        if count >= 5:
            logger.error(
                f"ALERTA: {count} intentos fallidos desde IP={ip}"
            )

    def log_successful_login(self, ip: str, email: str):
        if ip in self._failed_logins:
            del self._failed_logins[ip]
        logger.info(f"LOGIN_OK: IP={ip} email={email}")

    def log_suspicious_activity(self, ip: str, detail: str):
        logger.error(f"SOSPECHOSO: IP={ip} {detail}")


security_logger = SecurityLogger()

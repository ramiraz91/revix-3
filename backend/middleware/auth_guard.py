"""
Middleware de autenticación con whitelist explícita.

Cualquier endpoint bajo /api/* requiere JWT excepto los listados como públicos.
Esto cierra de un golpe la fuga histórica donde varios routers (data_routes,
dashboard_routes, notificaciones_routes) exponían CRUDs sin Depends(require_auth).

NOTA: este middleware NO sustituye a Depends(require_*) — permite que los
endpoints sigan validando rol (admin/master/tecnico). Solo bloquea peticiones
sin token a rutas que NO están explícitamente en la whitelist.
"""
import logging
import re
from typing import Iterable

import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("security.auth_guard")


# ── Whitelist de rutas públicas (sin token) ─────────────────────────────────
# Patrones EXACTOS o prefijos terminados en "/" (deben ser sub-rutas, no toda /api/).
PUBLIC_PREFIXES: tuple[str, ...] = (
    # Auth (login + recuperación)
    "/api/auth/login",
    "/api/auth/register",            # registro (si el flujo lo permite)
    "/api/auth/recuperar-password",
    "/api/auth/reset-password",
    "/api/auth/verificar-token-reset",
    "/api/auth/emergency-access",    # protegido por EMERGENCY_ACCESS_KEY
    # Web pública (revix.es)
    "/api/web/",                     # chatbot, lead, contacto, presupuesto
    # Agentes públicos (chat por token, widget)
    "/api/public/",                  # /api/public/agents/seguimiento/chat
    # FAQs y configuración pública
    "/api/faqs/public",
    "/api/configuracion/empresa/publica",
    # Catálogo de manuales Apple (recurso documental)
    "/api/apple-manuals/",
    # OAuth callback (token + verifier llegan vía redirect del navegador)
    "/api/mobilesentrix/oauth/callback",
    # Seguimiento público con token
    "/api/seguimiento/",
    # Tracking/portal-cliente público (presentación con token)
    "/api/orden-token/",
    "/api/track/",
)

# Endpoints exactos públicos (precisión quirúrgica, sin prefix-match).
PUBLIC_EXACT: frozenset[tuple[str, str]] = frozenset({
    # Health / meta — exactos para que /api/clientes NO pase como público.
    ("GET", "/api/"),
    ("GET", "/api/health"),
    # POST público para que el formulario web cree peticiones exteriores
    ("POST", "/api/peticiones-exteriores"),
})


# Paths que aceptan token por query string (?token=...).
# Son endpoints que devuelven binarios y se abren en pestaña nueva donde el
# navegador no puede enviar el header Authorization. Restringido al mínimo.
QUERY_TOKEN_PATHS: tuple[str, ...] = (
    "/api/logistica/gls/etiqueta/",
    "/api/gls/etiqueta/",
)


def _is_public(method: str, path: str, prefixes: Iterable[str], exact) -> bool:
    if (method, path) in exact:
        return True
    for p in prefixes:
        if path == p or path.startswith(p):
            return True
    return False


def _allows_query_token(path: str) -> bool:
    return any(path.startswith(p) for p in QUERY_TOKEN_PATHS)


class AuthGuardMiddleware(BaseHTTPMiddleware):
    """Bloquea cualquier /api/* sin Authorization válida salvo whitelist."""

    def __init__(self, app, jwt_secret: str, jwt_algorithm: str = "HS256"):
        super().__init__(app)
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method.upper()

        # Sólo aplicamos a /api/*
        if not path.startswith("/api/"):
            return await call_next(request)

        # OPTIONS (preflight CORS) siempre se permite
        if method == "OPTIONS":
            return await call_next(request)

        # Whitelist
        if _is_public(method, path, PUBLIC_PREFIXES, PUBLIC_EXACT):
            return await call_next(request)

        # Verificar Authorization Bearer
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            # Fallback: token por query string SOLO en paths whitelisted que
            # devuelven binarios (PDFs) y se abren en pestaña nueva, donde el
            # navegador no puede enviar el header Authorization.
            if _allows_query_token(path):
                qs_token = request.query_params.get("token", "")
                if qs_token:
                    auth = f"Bearer {qs_token}"
            if not auth.startswith("Bearer "):
                logger.info(f"[auth-guard] 401 sin token: {method} {path}")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Autenticación requerida"},
                )
        token = auth[7:]
        try:
            jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token expirado"},
            )
        except jwt.InvalidTokenError:
            logger.warning(f"[auth-guard] 401 token inválido: {method} {path}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Token inválido"},
            )

        return await call_next(request)

"""
Endpoints públicos del Widget Embeddable de revix.es.

Conecta visitantes anónimos con el agente `presupuestador_publico` (Fase 4 MCP).

Endpoints (sin auth, prefijo /api/public/widget):
  GET  /health           — health-check
  POST /chat             — turno conversacional con presupuestador_publico
  POST /lead             — crea pre_registro (lead capture: nombre+email+telefono)

Salvaguardas:
  - Rate limit por IP: 30 req/min para chat, 10 req/min para lead
  - En MCP_ENV=preview: /lead devuelve mock (no escribe en BD real)
  - Disclaimer obligatorio en respuestas del LLM (lo añade el system prompt; aquí
    además garantizamos que SIEMPRE acompaña la respuesta del endpoint).
  - Validación estricta de email/telefono.
"""
from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from config import db

# Importar MCP runtime
_APP_ROOT = Path(__file__).resolve().parents[2]
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from revix_mcp.runtime import ToolRateLimitError  # noqa: E402
from modules.agents.agent_defs import get_agent  # noqa: E402
from modules.agents.engine import run_agent_turn  # noqa: E402

logger = logging.getLogger("revix.widget")

router = APIRouter(prefix="/public/widget", tags=["widget-publico"])

DISCLAIMER = (
    "Este presupuesto es orientativo y puede variar tras diagnóstico presencial. "
    "No constituye compromiso de precio ni plazo."
)

AGENT_MESSAGES_COLL = "agent_messages"


def _is_preview() -> bool:
    return os.environ.get("MCP_ENV", "").lower() == "preview"


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Rate limit en memoria por IP ────────────────────────────────────────────
_RATE_BUCKETS: dict[str, deque] = defaultdict(deque)


def _check_rate_limit(key: str, limit_per_min: int) -> None:
    now = time.time()
    window = 60.0
    bucket = _RATE_BUCKETS[key]
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    if len(bucket) >= limit_per_min:
        raise HTTPException(
            status_code=429,
            detail="Demasiadas solicitudes. Espera un momento e intenta de nuevo.",
        )
    bucket.append(now)


# ══════════════════════════════════════════════════════════════════════════════
# /health
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/health")
async def widget_health() -> dict:
    return {
        "ok": True,
        "service": "revix-widget",
        "agent": "presupuestador_publico",
        "preview": _is_preview(),
        "version": "1.0.0",
    }


# ══════════════════════════════════════════════════════════════════════════════
# /chat — conversación con presupuestador_publico
# ══════════════════════════════════════════════════════════════════════════════

class WidgetChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = Field(None, max_length=64)


@router.post("/chat")
async def widget_chat(body: WidgetChatRequest, request: Request) -> dict:
    ip = _client_ip(request)
    _check_rate_limit(f"chat:{ip}", limit_per_min=30)

    agent = get_agent("presupuestador_publico")
    if not agent:
        raise HTTPException(status_code=500, detail="Agente no configurado")

    session_id = body.session_id or str(uuid.uuid4())

    # Historial de la sesión (cap 40 turnos)
    cursor = db[AGENT_MESSAGES_COLL].find(
        {"session_id": session_id},
        {"_id": 0, "role": 1, "content": 1, "tool_calls": 1,
         "tool_call_id": 1, "name": 1, "seq": 1},
    ).sort("seq", 1).limit(40)
    history = [m async for m in cursor]
    history_for_llm = []
    for m in history:
        entry = {"role": m["role"], "content": m.get("content") or ""}
        if m.get("tool_calls"):
            entry["tool_calls"] = m["tool_calls"]
        if m.get("tool_call_id"):
            entry["tool_call_id"] = m["tool_call_id"]
        if m.get("name"):
            entry["name"] = m["name"]
        history_for_llm.append(entry)

    try:
        result = await run_agent_turn(db, agent, history_for_llm, body.message)
    except ToolRateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail="Estamos recibiendo muchas consultas. Inténtalo en un momento.",
        ) from e
    except Exception:  # noqa: BLE001
        logger.exception("widget chat turn failed")
        raise HTTPException(
            status_code=500,
            detail="Fallo del asistente. Inténtalo de nuevo.",
        )

    # Persistir mensajes nuevos
    base_seq = len(history)
    full_new = result["messages"][len(history_for_llm):]
    docs = []
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for i, m in enumerate(full_new):
        docs.append({
            "session_id": session_id,
            "agent_id": "presupuestador_publico",
            "seq": base_seq + i,
            "role": m.get("role"),
            "content": m.get("content"),
            "tool_calls": m.get("tool_calls"),
            "tool_call_id": m.get("tool_call_id"),
            "name": m.get("name"),
            "created_at": now_iso,
            "public": True,
            "source": "widget",
            "ip": ip,
        })
    if docs:
        await db[AGENT_MESSAGES_COLL].insert_many(docs)

    return {
        "session_id": session_id,
        "reply": result["reply"],
        "duration_ms": result["duration_ms"],
        "disclaimer": DISCLAIMER,
    }


# ══════════════════════════════════════════════════════════════════════════════
# /lead — captura de lead (nombre, email, teléfono) → pre_registro
# ══════════════════════════════════════════════════════════════════════════════

class WidgetLeadRequest(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    telefono: Optional[str] = Field(None, max_length=30)
    tipo_dispositivo: Optional[str] = Field(None, max_length=50)
    modelo: Optional[str] = Field(None, max_length=80)
    descripcion_averia: Optional[str] = Field(None, max_length=1000)
    session_id: Optional[str] = Field(None, max_length=64)
    consent: bool = Field(False, description="Consentimiento RGPD")


@router.post("/lead")
async def widget_lead(body: WidgetLeadRequest, request: Request) -> dict:
    ip = _client_ip(request)
    _check_rate_limit(f"lead:{ip}", limit_per_min=10)

    if not body.consent:
        raise HTTPException(
            status_code=400,
            detail="Se requiere consentimiento RGPD para procesar tus datos.",
        )

    # Idempotency por (email + session_id) en una ventana razonable
    idem_key = f"widget-{body.email}-{body.session_id or 'no-session'}"

    # Modo preview: NO persiste, devuelve mock
    if _is_preview():
        logger.info(f"[widget-lead PREVIEW MOCK] {body.email}")
        return {
            "ok": True,
            "preview": True,
            "mock": True,
            "pre_registro_id": f"preview-mock-{uuid.uuid4().hex[:8]}",
            "disclaimer": DISCLAIMER,
            "mensaje": "Recibido (modo preview, no se ha persistido).",
        }

    # Producción: usa la tool MCP `crear_presupuesto_publico` para mantener
    # el mismo flujo (idempotencia, notificación admins, audit) que el agente.
    try:
        import revix_mcp.tools  # noqa: F401  - asegura registro
        from revix_mcp.tools._registry import get_tool
        from revix_mcp.auth import AgentIdentity

        identity = AgentIdentity(
            key_id=f"widget-{ip}",
            agent_name="widget_publico",
            rate_limit_per_min=60,
            agent_id="presupuestador_publico",
            scopes=["catalog:read", "quotes:write_public", "meta:ping"],
        )
        tool = get_tool("crear_presupuesto_publico")
        if tool is None:
            raise RuntimeError("Tool crear_presupuesto_publico no registrada")

        result = await tool.handler(db, identity, {
            "nombre_visitante": body.nombre,
            "email": body.email,
            "telefono": body.telefono,
            "tipo_dispositivo": body.tipo_dispositivo or "no-especificado",
            "modelo": body.modelo or "no-especificado",
            "descripcion_averia": body.descripcion_averia or "Solicitud desde widget",
            "idempotency_key": idem_key,
        })
        return {
            "ok": True,
            "preview": False,
            "pre_registro_id": result.get("pre_registro_id"),
            "deduped": result.get("deduped", False),
            "disclaimer": DISCLAIMER,
            "mensaje": "Recibimos tu solicitud. Te contactaremos en horario laboral.",
        }
    except Exception:  # noqa: BLE001
        logger.exception("widget lead failed")
        raise HTTPException(
            status_code=500,
            detail="No pudimos registrar tu solicitud. Intenta de nuevo más tarde.",
        )

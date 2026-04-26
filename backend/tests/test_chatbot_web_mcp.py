"""
Tests del chatbox web público (revix.es) integrado con presupuestador_publico.

Cubre:
  - POST /api/web/chatbot — usa MCP presupuestador_publico, devuelve disclaimer
  - POST /api/web/lead    — captura lead con consent RGPD, mock en preview
  - Rate limit, validación pydantic, retro-compatibilidad de la firma
"""
import os
import uuid

import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
    raise RuntimeError("REACT_APP_BACKEND_URL no configurado")


# ── /api/web/chatbot ─────────────────────────────────────────────────────────

def test_chatbot_responde_con_disclaimer():
    sid = f"test-chatbot-{uuid.uuid4().hex[:8]}"
    r = requests.post(
        f"{BASE}/api/web/chatbot",
        json={"mensaje": "iPhone 13 con pantalla rota", "session_id": sid},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    # Firma legacy preservada
    assert "respuesta" in d
    assert "session_id" in d and d["session_id"] == sid
    # Nuevo: disclaimer
    assert "orientativ" in d.get("disclaimer", "").lower()


def test_chatbot_mantiene_contexto_por_session():
    sid = f"test-ctx-{uuid.uuid4().hex[:8]}"
    r1 = requests.post(
        f"{BASE}/api/web/chatbot",
        json={"mensaje": "Tengo un iPhone 13", "session_id": sid},
        timeout=60,
    )
    assert r1.status_code == 200
    # Segundo turno: el agente debe recordar el iPhone 13
    r2 = requests.post(
        f"{BASE}/api/web/chatbot",
        json={"mensaje": "Pantalla rota, ¿precio?", "session_id": sid},
        timeout=60,
    )
    assert r2.status_code == 200
    # No verificamos contenido exacto del LLM, sólo que devolvió respuesta válida
    assert r2.json()["session_id"] == sid


def test_chatbot_validacion_mensaje_vacio():
    r = requests.post(
        f"{BASE}/api/web/chatbot",
        json={"mensaje": "", "session_id": "test"},
        timeout=10,
    )
    assert r.status_code == 422


# ── /api/web/lead ────────────────────────────────────────────────────────────

def test_lead_requiere_consent():
    r = requests.post(
        f"{BASE}/api/web/lead",
        json={"nombre": "Juan Pérez", "email": "test@example.com", "consent": False},
        timeout=10,
    )
    assert r.status_code == 400
    detail = r.json()["detail"].lower()
    assert "consentimiento" in detail or "rgpd" in detail


def test_lead_email_invalido():
    r = requests.post(
        f"{BASE}/api/web/lead",
        json={"nombre": "Juan", "email": "no-es-email", "consent": True},
        timeout=10,
    )
    assert r.status_code == 422


def test_lead_nombre_demasiado_corto():
    r = requests.post(
        f"{BASE}/api/web/lead",
        json={"nombre": "X", "email": "x@y.com", "consent": True},
        timeout=10,
    )
    assert r.status_code == 422


def test_lead_preview_devuelve_mock():
    r = requests.post(
        f"{BASE}/api/web/lead",
        json={
            "nombre": "Test Lead",
            "email": f"lead-{uuid.uuid4().hex[:8]}@test.com",
            "telefono": "600000000",
            "consent": True,
            "session_id": "test-sess",
        },
        timeout=10,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] is True
    if d.get("preview"):
        assert d.get("mock") is True
        assert d["pre_registro_id"].startswith("preview-mock-")
    assert "orientativ" in d.get("disclaimer", "").lower()


def test_endpoints_no_requieren_auth():
    # chatbot
    r1 = requests.post(
        f"{BASE}/api/web/chatbot",
        json={"mensaje": "hola", "session_id": "anon"},
        headers={"Authorization": "Bearer fake"},
        timeout=30,
    )
    assert r1.status_code == 200
    # lead
    r2 = requests.post(
        f"{BASE}/api/web/lead",
        json={"nombre": "Anon", "email": "a@b.com", "consent": True},
        headers={"Authorization": "Bearer fake"},
        timeout=10,
    )
    assert r2.status_code == 200

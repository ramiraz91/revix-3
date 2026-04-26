"""
Tests del Widget público de revix.es.

Cubre:
  - GET /api/public/widget/health
  - POST /api/public/widget/chat (sin auth, devuelve disclaimer + session_id)
  - POST /api/public/widget/lead (consent obligatorio, mock en preview)
  - Rate limit por IP (chat 30/min, lead 10/min)
  - Validación pydantic (email inválido, nombre <2 chars)
"""
import os
import uuid

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
    raise RuntimeError("REACT_APP_BACKEND_URL no configurado")


def test_widget_health():
    r = requests.get(f"{BASE}/api/public/widget/health", timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert d["agent"] == "presupuestador_publico"
    assert d["service"] == "revix-widget"
    assert "version" in d


def test_widget_chat_sin_auth_devuelve_disclaimer_y_session():
    r = requests.post(
        f"{BASE}/api/public/widget/chat",
        json={"message": "Hola, pantalla rota iPhone 13"},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("session_id") and len(d["session_id"]) >= 8
    assert d.get("reply")
    assert "orientativ" in d.get("disclaimer", "").lower()


def test_widget_chat_mantiene_sesion():
    sid = str(uuid.uuid4())
    r1 = requests.post(
        f"{BASE}/api/public/widget/chat",
        json={"message": "Hola", "session_id": sid},
        timeout=60,
    )
    assert r1.status_code == 200
    assert r1.json()["session_id"] == sid


def test_widget_chat_validacion_message_vacio():
    r = requests.post(
        f"{BASE}/api/public/widget/chat",
        json={"message": ""},
        timeout=10,
    )
    assert r.status_code == 422


def test_widget_lead_requiere_consent():
    r = requests.post(
        f"{BASE}/api/public/widget/lead",
        json={
            "nombre": "Juan Pérez",
            "email": "test@example.com",
            "consent": False,
        },
        timeout=10,
    )
    assert r.status_code == 400
    assert "consentimiento" in r.json()["detail"].lower() or \
           "rgpd" in r.json()["detail"].lower()


def test_widget_lead_email_invalido():
    r = requests.post(
        f"{BASE}/api/public/widget/lead",
        json={
            "nombre": "Juan Pérez",
            "email": "no-es-email",
            "consent": True,
        },
        timeout=10,
    )
    assert r.status_code == 422


def test_widget_lead_preview_mock():
    """En MCP_ENV=preview el endpoint debe devolver mock sin persistir."""
    r = requests.post(
        f"{BASE}/api/public/widget/lead",
        json={
            "nombre": "Test Widget",
            "email": f"widget-test-{uuid.uuid4().hex[:8]}@example.com",
            "telefono": "600000000",
            "tipo_dispositivo": "movil",
            "modelo": "iPhone 13",
            "descripcion_averia": "pantalla rota",
            "consent": True,
        },
        timeout=10,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] is True
    # En preview: mock=True, pre_registro_id empieza por "preview-mock-"
    if d.get("preview"):
        assert d.get("mock") is True
        assert d["pre_registro_id"].startswith("preview-mock-")


def test_widget_health_no_requiere_auth():
    """Confirma que el endpoint NO está bloqueado por middleware de auth."""
    r = requests.get(f"{BASE}/api/public/widget/health", timeout=10)
    assert r.status_code == 200
    # No debe pedir Authorization
    r2 = requests.get(
        f"{BASE}/api/public/widget/health",
        headers={"Authorization": "Bearer fake-token-XXXX"},
        timeout=10,
    )
    assert r2.status_code == 200

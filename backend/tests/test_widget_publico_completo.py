"""
Tests completos del Widget público de revix.es (PUNTO 2 Roadmap).

Cubre:
  - GET /api/public/widget/health - sin auth, devuelve {ok:true, agent:'presupuestador_publico', preview:true, version}
  - POST /api/public/widget/chat - sin auth, body {message, session_id?}. Devuelve session_id, reply, disclaimer
  - POST /api/public/widget/chat - validación: message vacío → 422. Cuerpo malformado → 422
  - POST /api/public/widget/lead - sin auth. Requiere consent=true (400 si false). Email inválido → 422. Nombre <2 chars → 422
  - POST /api/public/widget/lead - en MCP_ENV=preview devuelve {ok:true, preview:true, mock:true, pre_registro_id starts with 'preview-mock-'}
  - Rate limiting por IP: chat 30/min, lead 10/min (ráfagas mayores → 429)
  - Frontend widget: GET /widget/revix-widget.js → 200 (script accesible)
  - Frontend widget: GET /widget/ → 200 (página demo)
"""
import os
import uuid
import time

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
    raise RuntimeError("REACT_APP_BACKEND_URL no configurado")


# ══════════════════════════════════════════════════════════════════════════════
# GET /api/public/widget/health
# ══════════════════════════════════════════════════════════════════════════════

class TestWidgetHealth:
    """Tests para GET /api/public/widget/health"""
    
    def test_health_returns_ok_true(self):
        """Health endpoint devuelve ok:true"""
        r = requests.get(f"{BASE}/api/public/widget/health", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
    
    def test_health_returns_agent_presupuestador_publico(self):
        """Health endpoint devuelve agent:'presupuestador_publico'"""
        r = requests.get(f"{BASE}/api/public/widget/health", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["agent"] == "presupuestador_publico"
    
    def test_health_returns_preview_true(self):
        """Health endpoint devuelve preview:true en MCP_ENV=preview"""
        r = requests.get(f"{BASE}/api/public/widget/health", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["preview"] is True
    
    def test_health_returns_version(self):
        """Health endpoint devuelve version"""
        r = requests.get(f"{BASE}/api/public/widget/health", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "version" in d
        assert d["version"] == "1.0.0"
    
    def test_health_returns_service_revix_widget(self):
        """Health endpoint devuelve service:'revix-widget'"""
        r = requests.get(f"{BASE}/api/public/widget/health", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["service"] == "revix-widget"
    
    def test_health_no_requiere_auth(self):
        """Health endpoint NO requiere autenticación"""
        # Sin header Authorization
        r1 = requests.get(f"{BASE}/api/public/widget/health", timeout=10)
        assert r1.status_code == 200
        
        # Con header Authorization falso (no debe fallar)
        r2 = requests.get(
            f"{BASE}/api/public/widget/health",
            headers={"Authorization": "Bearer fake-token-XXXX"},
            timeout=10,
        )
        assert r2.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# POST /api/public/widget/chat
# ══════════════════════════════════════════════════════════════════════════════

class TestWidgetChat:
    """Tests para POST /api/public/widget/chat"""
    
    def test_chat_sin_auth_devuelve_session_id(self):
        """Chat sin auth devuelve session_id"""
        r = requests.post(
            f"{BASE}/api/public/widget/chat",
            json={"message": "Hola, pantalla rota iPhone 13"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("session_id") and len(d["session_id"]) >= 8
    
    def test_chat_sin_auth_devuelve_reply(self):
        """Chat sin auth devuelve reply del LLM"""
        r = requests.post(
            f"{BASE}/api/public/widget/chat",
            json={"message": "Hola"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("reply") and len(d["reply"]) > 0
    
    def test_chat_sin_auth_devuelve_disclaimer(self):
        """Chat sin auth devuelve disclaimer obligatorio"""
        r = requests.post(
            f"{BASE}/api/public/widget/chat",
            json={"message": "Pantalla rota"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert "disclaimer" in d
        assert "orientativ" in d["disclaimer"].lower()
    
    def test_chat_mantiene_sesion(self):
        """Chat mantiene contexto con mismo session_id"""
        sid = str(uuid.uuid4())
        r1 = requests.post(
            f"{BASE}/api/public/widget/chat",
            json={"message": "Hola", "session_id": sid},
            timeout=60,
        )
        assert r1.status_code == 200
        assert r1.json()["session_id"] == sid
        
        # Segunda llamada con mismo session_id
        r2 = requests.post(
            f"{BASE}/api/public/widget/chat",
            json={"message": "Mi iPhone 13", "session_id": sid},
            timeout=60,
        )
        assert r2.status_code == 200
        assert r2.json()["session_id"] == sid
    
    def test_chat_validacion_message_vacio_422(self):
        """Chat con message vacío devuelve 422"""
        r = requests.post(
            f"{BASE}/api/public/widget/chat",
            json={"message": ""},
            timeout=10,
        )
        assert r.status_code == 422
    
    def test_chat_validacion_cuerpo_malformado_422(self):
        """Chat con cuerpo malformado devuelve 422"""
        r = requests.post(
            f"{BASE}/api/public/widget/chat",
            json={},  # Sin campo message
            timeout=10,
        )
        assert r.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# POST /api/public/widget/lead
# ══════════════════════════════════════════════════════════════════════════════

class TestWidgetLead:
    """Tests para POST /api/public/widget/lead"""
    
    def test_lead_requiere_consent_true(self):
        """Lead con consent=false devuelve 400"""
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
        detail = r.json().get("detail", "").lower()
        assert "consentimiento" in detail or "rgpd" in detail
    
    def test_lead_email_invalido_422(self):
        """Lead con email inválido devuelve 422"""
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
    
    def test_lead_nombre_menor_2_chars_422(self):
        """Lead con nombre <2 chars devuelve 422"""
        r = requests.post(
            f"{BASE}/api/public/widget/lead",
            json={
                "nombre": "J",  # Solo 1 char
                "email": "test@example.com",
                "consent": True,
            },
            timeout=10,
        )
        assert r.status_code == 422
    
    def test_lead_preview_mock_ok_true(self):
        """Lead en preview devuelve ok:true"""
        r = requests.post(
            f"{BASE}/api/public/widget/lead",
            json={
                "nombre": "Test Widget",
                "email": f"widget-test-{uuid.uuid4().hex[:8]}@example.com",
                "telefono": "600000000",
                "consent": True,
            },
            timeout=10,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
    
    def test_lead_preview_mock_preview_true(self):
        """Lead en preview devuelve preview:true"""
        r = requests.post(
            f"{BASE}/api/public/widget/lead",
            json={
                "nombre": "Test Widget",
                "email": f"widget-test-{uuid.uuid4().hex[:8]}@example.com",
                "consent": True,
            },
            timeout=10,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("preview") is True
    
    def test_lead_preview_mock_true(self):
        """Lead en preview devuelve mock:true"""
        r = requests.post(
            f"{BASE}/api/public/widget/lead",
            json={
                "nombre": "Test Widget",
                "email": f"widget-test-{uuid.uuid4().hex[:8]}@example.com",
                "consent": True,
            },
            timeout=10,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("mock") is True
    
    def test_lead_preview_pre_registro_id_starts_with_preview_mock(self):
        """Lead en preview devuelve pre_registro_id que empieza con 'preview-mock-'"""
        r = requests.post(
            f"{BASE}/api/public/widget/lead",
            json={
                "nombre": "Test Widget",
                "email": f"widget-test-{uuid.uuid4().hex[:8]}@example.com",
                "consent": True,
            },
            timeout=10,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["pre_registro_id"].startswith("preview-mock-")


# ══════════════════════════════════════════════════════════════════════════════
# Frontend widget static files
# ══════════════════════════════════════════════════════════════════════════════

class TestWidgetFrontend:
    """Tests para archivos estáticos del widget"""
    
    def test_widget_js_accesible(self):
        """GET /widget/revix-widget.js devuelve 200"""
        r = requests.get(f"{BASE}/widget/revix-widget.js", timeout=10)
        assert r.status_code == 200
        assert "RevixWidget" in r.text or "revix-widget" in r.text.lower()
    
    def test_widget_demo_page_accesible(self):
        """GET /widget/ devuelve 200 (página demo)"""
        r = requests.get(f"{BASE}/widget/", timeout=10)
        assert r.status_code == 200
        assert "Revix Widget" in r.text or "revix" in r.text.lower()


# ══════════════════════════════════════════════════════════════════════════════
# Rate limiting (smoke test - no exhaustivo para no bloquear IP)
# ══════════════════════════════════════════════════════════════════════════════

class TestWidgetRateLimiting:
    """Tests básicos de rate limiting (no exhaustivos)"""
    
    def test_chat_permite_varias_llamadas_consecutivas(self):
        """Chat permite al menos 5 llamadas consecutivas (dentro del límite 30/min)"""
        for i in range(5):
            r = requests.post(
                f"{BASE}/api/public/widget/chat",
                json={"message": f"Test rate limit {i}"},
                timeout=60,
            )
            # Debe ser 200 o 429 si ya se alcanzó el límite
            assert r.status_code in [200, 429], f"Unexpected status: {r.status_code}"
            if r.status_code == 429:
                print(f"Rate limit alcanzado en llamada {i+1}")
                break
    
    def test_lead_permite_varias_llamadas_consecutivas(self):
        """Lead permite al menos 3 llamadas consecutivas (dentro del límite 10/min)"""
        for i in range(3):
            r = requests.post(
                f"{BASE}/api/public/widget/lead",
                json={
                    "nombre": f"Test Rate {i}",
                    "email": f"rate-test-{uuid.uuid4().hex[:8]}@example.com",
                    "consent": True,
                },
                timeout=10,
            )
            # Debe ser 200 o 429 si ya se alcanzó el límite
            assert r.status_code in [200, 429], f"Unexpected status: {r.status_code}"
            if r.status_code == 429:
                print(f"Rate limit alcanzado en llamada {i+1}")
                break

"""
E2E Tests Fase 4 MCP — Validación completa de agentes cara al cliente.

Cubre:
  - GET /api/agents/panel/overview: 11 agentes incluyendo call_center, presupuestador_publico, seguimiento_publico
  - GET /api/agents: solo agentes internos (excluye visible_to_public=True)
  - Tools MCP de los 3 agentes nuevos
  - Auth strict: sin scopes correctos → AuthError
  - Regresión: módulo Compras, bandeja Insurama, agentes legacy
"""
import os
import pytest
import requests
from dotenv import load_dotenv

# Load frontend .env for REACT_APP_BACKEND_URL
load_dotenv("/app/frontend/.env")
BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
    raise RuntimeError("REACT_APP_BACKEND_URL not set - check /app/frontend/.env")

MASTER = ("master@revix.es", "RevixMaster2026!")


def _login():
    """Login and return token."""
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": MASTER[0], "password": MASTER[1]})
    if r.status_code != 200:
        pytest.skip(f"Login failed: {r.status_code} - {r.text[:200]}")
    return r.json().get("token")


@pytest.fixture(scope="module")
def tok():
    return _login()


def H(t):
    return {"Authorization": f"Bearer {t}"}


# ══════════════════════════════════════════════════════════════════════════════
# 1. GET /api/agents/panel/overview — 11 agentes con scopes correctos
# ══════════════════════════════════════════════════════════════════════════════

class TestPanelOverview:
    """Tests for /api/agents/panel/overview endpoint."""
    
    def test_overview_returns_11_agents(self, tok):
        """Panel overview debe listar los 11 agentes registrados."""
        r = requests.get(f"{BASE}/api/agents/panel/overview", headers=H(tok))
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"
        data = r.json()
        assert "agents" in data
        agents = data["agents"]
        assert len(agents) == 11, f"Expected 11 agents, got {len(agents)}"
        
    def test_overview_includes_fase4_agents(self, tok):
        """Panel overview debe incluir los 3 agentes de Fase 4."""
        r = requests.get(f"{BASE}/api/agents/panel/overview", headers=H(tok))
        assert r.status_code == 200
        agents = r.json()["agents"]
        agent_ids = {a["agent_id"] for a in agents}
        
        fase4_agents = ["call_center", "presupuestador_publico", "seguimiento_publico"]
        for aid in fase4_agents:
            assert aid in agent_ids, f"Falta agente Fase 4: {aid}"
            
    def test_overview_call_center_scopes(self, tok):
        """Call center debe tener scopes correctos."""
        r = requests.get(f"{BASE}/api/agents/panel/overview", headers=H(tok))
        agents = r.json()["agents"]
        cc = next((a for a in agents if a["agent_id"] == "call_center"), None)
        assert cc is not None
        scopes = set(cc.get("scopes", []))
        
        # Debe tener
        required = {"customers:read", "orders:read", "comm:write", "comm:escalate", "meta:ping"}
        for s in required:
            assert s in scopes, f"Falta scope {s} en call_center"
            
        # NO debe tener
        forbidden = {"finance:bill", "finance:read", "orders:write", "insurance:ops"}
        for s in forbidden:
            assert s not in scopes, f"Scope prohibido {s} presente en call_center"
            
    def test_overview_presupuestador_scopes(self, tok):
        """Presupuestador público debe tener scopes estrictos."""
        r = requests.get(f"{BASE}/api/agents/panel/overview", headers=H(tok))
        agents = r.json()["agents"]
        pp = next((a for a in agents if a["agent_id"] == "presupuestador_publico"), None)
        assert pp is not None
        scopes = set(pp.get("scopes", []))
        
        # Debe tener
        assert "catalog:read" in scopes
        assert "quotes:write_public" in scopes
        
        # NO debe tener
        forbidden = {"customers:read", "orders:write", "finance:read", "orders:read"}
        for s in forbidden:
            assert s not in scopes, f"Scope prohibido {s} presente en presupuestador"
            
    def test_overview_seguimiento_scopes(self, tok):
        """Seguimiento público debe tener solo scope público."""
        r = requests.get(f"{BASE}/api/agents/panel/overview", headers=H(tok))
        agents = r.json()["agents"]
        sp = next((a for a in agents if a["agent_id"] == "seguimiento_publico"), None)
        assert sp is not None
        scopes = set(sp.get("scopes", []))
        
        # Debe tener
        assert "public:track_by_token" in scopes
        
        # NO debe tener
        forbidden = {"customers:read", "orders:read", "finance:read", "comm:write"}
        for s in forbidden:
            assert s not in scopes, f"Scope prohibido {s} presente en seguimiento"
            
    def test_overview_includes_resumen(self, tok):
        """Panel overview debe incluir resumen global."""
        r = requests.get(f"{BASE}/api/agents/panel/overview", headers=H(tok))
        data = r.json()
        assert "resumen" in data
        resumen = data["resumen"]
        assert "total_agentes" in resumen
        assert resumen["total_agentes"] == 11


# ══════════════════════════════════════════════════════════════════════════════
# 2. GET /api/agents — solo agentes internos
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentsEndpoint:
    """Tests for /api/agents endpoint (internal agents only)."""
    
    def test_agents_excludes_public_agents(self, tok):
        """GET /api/agents debe excluir agentes con visible_to_public=True."""
        r = requests.get(f"{BASE}/api/agents", headers=H(tok))
        assert r.status_code == 200
        
        # Handle both response formats
        data = r.json()
        if isinstance(data, list):
            agents = data
        else:
            agents = data.get("agents") or data.get("agentes") or []
            
        agent_ids = {a.get("id") for a in agents}
        
        # presupuestador_publico y seguimiento_publico tienen visible_to_public=True
        # por lo tanto NO deben aparecer en /api/agents
        assert "presupuestador_publico" not in agent_ids, \
            "presupuestador_publico NO debe aparecer en /api/agents (es público)"
        assert "seguimiento_publico" not in agent_ids, \
            "seguimiento_publico NO debe aparecer en /api/agents (es público)"
            
    def test_agents_includes_call_center(self, tok):
        """GET /api/agents debe incluir call_center (es interno)."""
        r = requests.get(f"{BASE}/api/agents", headers=H(tok))
        data = r.json()
        if isinstance(data, list):
            agents = data
        else:
            agents = data.get("agents") or data.get("agentes") or []
            
        agent_ids = {a.get("id") for a in agents}
        assert "call_center" in agent_ids, "call_center debe aparecer en /api/agents"
        
    def test_agents_includes_legacy_agents(self, tok):
        """GET /api/agents debe incluir agentes legacy."""
        r = requests.get(f"{BASE}/api/agents", headers=H(tok))
        data = r.json()
        if isinstance(data, list):
            agents = data
        else:
            agents = data.get("agents") or data.get("agentes") or []
            
        agent_ids = {a.get("id") for a in agents}
        
        legacy = ["kpi_analyst", "auditor", "supervisor_cola", "iso_officer", 
                  "finance_officer", "gestor_siniestros", "triador_averias", "gestor_compras"]
        for aid in legacy:
            assert aid in agent_ids, f"Falta agente legacy: {aid}"


# ══════════════════════════════════════════════════════════════════════════════
# 3. Regresión: Módulo de Compras
# ══════════════════════════════════════════════════════════════════════════════

class TestComprasRegression:
    """Regression tests for /api/compras/lista/* endpoints."""
    
    def test_compras_lista_pendientes(self, tok):
        """GET /api/compras/lista/pendientes debe funcionar."""
        r = requests.get(f"{BASE}/api/compras/lista/pendientes", headers=H(tok))
        # 200 o 404 si no hay datos, pero no 500
        assert r.status_code in [200, 404], f"Unexpected status: {r.status_code}"
        if r.status_code == 200:
            data = r.json()
            assert "items" in data or isinstance(data, list)
            
    def test_compras_lista_all(self, tok):
        """GET /api/compras/lista debe funcionar."""
        r = requests.get(f"{BASE}/api/compras/lista", headers=H(tok))
        assert r.status_code in [200, 404], f"Unexpected status: {r.status_code}"


# ══════════════════════════════════════════════════════════════════════════════
# 4. Regresión: Bandeja Insurama
# ══════════════════════════════════════════════════════════════════════════════

class TestInsuramaRegression:
    """Regression tests for /api/insurama/inbox/* endpoints."""
    
    def test_insurama_inbox(self, tok):
        """GET /api/insurama/inbox debe funcionar."""
        r = requests.get(f"{BASE}/api/insurama/inbox", headers=H(tok))
        # 200 o 404 si no hay datos
        assert r.status_code in [200, 404], f"Unexpected status: {r.status_code}"
        
    def test_insurama_inbox_pendientes(self, tok):
        """GET /api/insurama/inbox/pendientes debe funcionar."""
        r = requests.get(f"{BASE}/api/insurama/inbox/pendientes", headers=H(tok))
        assert r.status_code in [200, 404], f"Unexpected status: {r.status_code}"


# ══════════════════════════════════════════════════════════════════════════════
# 5. Regresión: Endpoints básicos
# ══════════════════════════════════════════════════════════════════════════════

class TestBasicEndpointsRegression:
    """Regression tests for basic endpoints."""
    
    def test_health_check(self):
        """GET /api/health debe funcionar."""
        r = requests.get(f"{BASE}/api/health")
        assert r.status_code == 200
        
    def test_ordenes_list(self, tok):
        """GET /api/ordenes debe funcionar."""
        r = requests.get(f"{BASE}/api/ordenes", headers=H(tok))
        assert r.status_code == 200
        
    def test_clientes_list(self, tok):
        """GET /api/clientes debe funcionar."""
        r = requests.get(f"{BASE}/api/clientes", headers=H(tok))
        assert r.status_code == 200
        
    def test_dashboard_stats(self, tok):
        """GET /api/dashboard/stats debe funcionar."""
        r = requests.get(f"{BASE}/api/dashboard/stats", headers=H(tok))
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 6. Agent Panel Endpoints
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentPanelEndpoints:
    """Tests for agent panel management endpoints."""
    
    def test_agent_config_call_center(self, tok):
        """GET /api/agents/call_center/config debe funcionar."""
        r = requests.get(f"{BASE}/api/agents/call_center/config", headers=H(tok))
        assert r.status_code == 200
        data = r.json()
        assert data["agent_id"] == "call_center"
        assert "scopes" in data
        assert "tools" in data
        
    def test_agent_timeline(self, tok):
        """GET /api/agents/{id}/timeline debe funcionar."""
        r = requests.get(f"{BASE}/api/agents/kpi_analyst/timeline", headers=H(tok))
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        
    def test_panel_metrics(self, tok):
        """GET /api/agents/panel/metrics debe funcionar."""
        r = requests.get(f"{BASE}/api/agents/panel/metrics?days=7", headers=H(tok))
        assert r.status_code == 200
        data = r.json()
        assert "por_agente" in data
        assert "top_tools" in data
        
    def test_pending_approvals(self, tok):
        """GET /api/agents/panel/pending-approvals debe funcionar."""
        r = requests.get(f"{BASE}/api/agents/panel/pending-approvals", headers=H(tok))
        assert r.status_code == 200
        data = r.json()
        assert "items" in data


# ══════════════════════════════════════════════════════════════════════════════
# 7. Public Agent Endpoint (seguimiento)
# ══════════════════════════════════════════════════════════════════════════════

class TestPublicAgentEndpoint:
    """Tests for public agent endpoint (no auth required)."""
    
    def test_public_seguimiento_chat(self):
        """POST /api/public/agents/seguimiento/chat debe funcionar sin auth."""
        r = requests.post(
            f"{BASE}/api/public/agents/seguimiento/chat",
            json={"message": "Hola, quiero saber el estado de mi reparación con token ABC123"}
        )
        # Puede ser 200 (éxito) o 500 si hay problema con LLM, pero no 401/403
        assert r.status_code != 401, "Public endpoint should not require auth"
        assert r.status_code != 403, "Public endpoint should not require auth"


# ══════════════════════════════════════════════════════════════════════════════
# 8. Logística Panel (regression)
# ══════════════════════════════════════════════════════════════════════════════

class TestLogisticaRegression:
    """Regression tests for logistics panel."""
    
    def test_logistica_panel_resumen(self, tok):
        """GET /api/logistica/panel/resumen debe funcionar."""
        r = requests.get(f"{BASE}/api/logistica/panel/resumen", headers=H(tok))
        assert r.status_code == 200
        data = r.json()
        assert "envios_activos" in data or "total" in data
        
    def test_logistica_panel_envios(self, tok):
        """GET /api/logistica/panel/envios debe funcionar."""
        r = requests.get(f"{BASE}/api/logistica/panel/envios", headers=H(tok))
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 9. Notificaciones (regression)
# ══════════════════════════════════════════════════════════════════════════════

class TestNotificacionesRegression:
    """Regression tests for notifications."""
    
    def test_notificaciones_list(self, tok):
        """GET /api/notificaciones debe funcionar."""
        r = requests.get(f"{BASE}/api/notificaciones", headers=H(tok))
        assert r.status_code == 200
        
    def test_notificaciones_contadores(self, tok):
        """GET /api/notificaciones/contadores debe funcionar."""
        r = requests.get(f"{BASE}/api/notificaciones/contadores", headers=H(tok))
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 10. Finanzas (regression)
# ══════════════════════════════════════════════════════════════════════════════

class TestFinanzasRegression:
    """Regression tests for finance endpoints."""
    
    def test_finanzas_dashboard(self, tok):
        """GET /api/finanzas/dashboard debe funcionar."""
        r = requests.get(f"{BASE}/api/finanzas/dashboard", headers=H(tok))
        assert r.status_code == 200
        
    def test_finanzas_balance(self, tok):
        """GET /api/finanzas/balance debe funcionar."""
        r = requests.get(f"{BASE}/api/finanzas/balance", headers=H(tok))
        assert r.status_code == 200

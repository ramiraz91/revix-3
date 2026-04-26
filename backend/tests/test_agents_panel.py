"""
Test suite for Agents Panel endpoints (/api/agents/panel/*)
Tests the new advanced agent management panel for /crm/agentes

Endpoints tested:
- GET /api/agents/panel/overview - List all 8 agents with stats
- POST /api/agents/{id}/pause - Pause agent (master/admin only)
- POST /api/agents/{id}/activate - Activate agent
- GET /api/agents/{id}/timeline - Agent activity timeline
- GET /api/agents/{id}/config - Agent configuration
- POST /api/agents/{id}/config - Update rate limits and system prompt
- GET /api/agents/panel/metrics - Global metrics
- GET /api/agents/panel/pending-approvals - Approval queue
- POST /api/agents/panel/pending-approvals/{id}/decide - Approve/reject
"""

import pytest
import requests
import os
import uuid
from dotenv import load_dotenv

# Load frontend .env for REACT_APP_BACKEND_URL
load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL not set - check /app/frontend/.env")

# Test credentials
MASTER_EMAIL = "master@revix.es"
MASTER_PASSWORD = "RevixMaster2026!"
TECNICO_EMAIL = "tecnico1@revix.es"
TECNICO_PASSWORD = "Tecnico1Demo!"


@pytest.fixture(scope="module")
def master_token():
    """Get master user auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MASTER_EMAIL,
        "password": MASTER_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Master login failed: {response.status_code} - {response.text}")
    return response.json().get("token")


@pytest.fixture(scope="module")
def tecnico_token():
    """Get tecnico user auth token (non-master)"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TECNICO_EMAIL,
        "password": TECNICO_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Tecnico login failed: {response.status_code}")
    return response.json().get("token")


@pytest.fixture
def master_headers(master_token):
    return {"Authorization": f"Bearer {master_token}", "Content-Type": "application/json"}


@pytest.fixture
def tecnico_headers(tecnico_token):
    return {"Authorization": f"Bearer {tecnico_token}", "Content-Type": "application/json"}


class TestAgentsPanelOverview:
    """Tests for GET /api/agents/panel/overview"""
    
    def test_overview_returns_11_agents(self, master_headers):
        """Overview should return list of 11 agents with stats (8 legacy + 3 Fase 4)"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/overview", headers=master_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "agents" in data, "Response should have 'agents' key"
        assert "resumen" in data, "Response should have 'resumen' key"
        
        agents = data["agents"]
        assert len(agents) == 11, f"Expected 11 agents, got {len(agents)}"
        
        # Verify agent structure
        for agent in agents:
            assert "agent_id" in agent
            assert "nombre" in agent
            assert "descripcion" in agent
            assert "emoji" in agent
            assert "estado" in agent  # activo/pausado/error
            assert "tools_count" in agent
            assert "acciones_hoy" in agent
            assert "tasa_exito_7d" in agent
    
    def test_overview_resumen_structure(self, master_headers):
        """Overview resumen should have global stats"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/overview", headers=master_headers)
        assert response.status_code == 200
        
        resumen = response.json()["resumen"]
        assert "total_agentes" in resumen
        assert "acciones_hoy" in resumen
        assert "errores_24h" in resumen
        assert "agente_mas_activo" in resumen
        assert "aprobaciones_pendientes" in resumen
        assert "tareas_proximas_24h" in resumen
        
        assert resumen["total_agentes"] == 11
    
    def test_overview_requires_auth(self):
        """Overview should require authentication"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/overview")
        assert response.status_code in [401, 403]


class TestAgentPauseActivate:
    """Tests for POST /api/agents/{id}/pause and /activate"""
    
    def test_pause_agent_as_master(self, master_headers):
        """Master can pause an agent"""
        agent_id = "kpi_analyst"
        response = requests.post(f"{BASE_URL}/api/agents/{agent_id}/pause", headers=master_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["ok"] == True
        assert data["agent_id"] == agent_id
        assert data["estado"] == "pausado"
    
    def test_activate_agent_as_master(self, master_headers):
        """Master can activate a paused agent"""
        agent_id = "kpi_analyst"
        response = requests.post(f"{BASE_URL}/api/agents/{agent_id}/activate", headers=master_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["ok"] == True
        assert data["agent_id"] == agent_id
        assert data["estado"] == "activo"
    
    def test_pause_persists_in_agent_states(self, master_headers):
        """Pause should persist in agent_states collection"""
        agent_id = "auditor"
        
        # Pause
        response = requests.post(f"{BASE_URL}/api/agents/{agent_id}/pause", headers=master_headers)
        assert response.status_code == 200
        
        # Verify via overview
        overview = requests.get(f"{BASE_URL}/api/agents/panel/overview", headers=master_headers)
        agents = overview.json()["agents"]
        auditor = next((a for a in agents if a["agent_id"] == agent_id), None)
        assert auditor is not None
        assert auditor["estado"] == "pausado"
        
        # Cleanup - reactivate
        requests.post(f"{BASE_URL}/api/agents/{agent_id}/activate", headers=master_headers)
    
    def test_pause_nonexistent_agent_returns_404(self, master_headers):
        """Pausing non-existent agent should return 404"""
        response = requests.post(f"{BASE_URL}/api/agents/fake_agent_xyz/pause", headers=master_headers)
        assert response.status_code == 404
    
    def test_pause_requires_master_or_admin(self, tecnico_headers):
        """Non-master/admin cannot pause agents (403)"""
        agent_id = "kpi_analyst"
        response = requests.post(f"{BASE_URL}/api/agents/{agent_id}/pause", headers=tecnico_headers)
        assert response.status_code == 403, f"Expected 403 for tecnico, got {response.status_code}"


class TestAgentTimeline:
    """Tests for GET /api/agents/{id}/timeline"""
    
    def test_timeline_returns_items(self, master_headers):
        """Timeline should return audit log items"""
        agent_id = "triador_averias"  # Known to have activity
        response = requests.get(f"{BASE_URL}/api/agents/{agent_id}/timeline", headers=master_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
    
    def test_timeline_filter_by_tool(self, master_headers):
        """Timeline can filter by tool name"""
        agent_id = "triador_averias"
        response = requests.get(
            f"{BASE_URL}/api/agents/{agent_id}/timeline?tool=proponer_diagnostico",
            headers=master_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        # All items should have the filtered tool (if any)
        for item in data["items"]:
            assert item.get("tool") == "proponer_diagnostico"
    
    def test_timeline_filter_by_resultado(self, master_headers):
        """Timeline can filter by resultado (ok/error)"""
        agent_id = "triador_averias"
        
        # Filter errors only
        response = requests.get(
            f"{BASE_URL}/api/agents/{agent_id}/timeline?resultado=error",
            headers=master_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        for item in data["items"]:
            assert item.get("error") is not None
    
    def test_timeline_nonexistent_agent_returns_404(self, master_headers):
        """Timeline for non-existent agent should return 404"""
        response = requests.get(f"{BASE_URL}/api/agents/fake_agent/timeline", headers=master_headers)
        assert response.status_code == 404


class TestAgentConfig:
    """Tests for GET/POST /api/agents/{id}/config"""
    
    def test_get_config_returns_structure(self, master_headers):
        """Config should return rate limits, prompt, tools, scopes"""
        agent_id = "kpi_analyst"
        response = requests.get(f"{BASE_URL}/api/agents/{agent_id}/config", headers=master_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["agent_id"] == agent_id
        assert "rate_limit_soft" in data
        assert "rate_limit_hard" in data
        assert "system_prompt_default" in data
        assert "system_prompt_effective" in data
        assert "system_prompt_override" in data
        assert "scopes" in data
        assert "tools" in data
    
    def test_update_rate_limits(self, master_headers):
        """Master can update rate limits"""
        agent_id = "kpi_analyst"
        
        # Get current config
        current = requests.get(f"{BASE_URL}/api/agents/{agent_id}/config", headers=master_headers).json()
        original_soft = current["rate_limit_soft"]
        original_hard = current["rate_limit_hard"]
        
        # Update
        new_soft = 150
        new_hard = 700
        response = requests.post(
            f"{BASE_URL}/api/agents/{agent_id}/config",
            headers=master_headers,
            json={"rate_limit_soft": new_soft, "rate_limit_hard": new_hard}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["ok"] == True
        assert "rate limits" in str(data.get("changes", []))
        
        # Verify persistence
        updated = requests.get(f"{BASE_URL}/api/agents/{agent_id}/config", headers=master_headers).json()
        assert updated["rate_limit_soft"] == new_soft
        assert updated["rate_limit_hard"] == new_hard
        
        # Restore original
        requests.post(
            f"{BASE_URL}/api/agents/{agent_id}/config",
            headers=master_headers,
            json={"rate_limit_soft": original_soft, "rate_limit_hard": original_hard}
        )
    
    def test_update_rate_limits_validates_hard_gte_soft(self, master_headers):
        """hard_limit must be >= soft_limit"""
        agent_id = "kpi_analyst"
        response = requests.post(
            f"{BASE_URL}/api/agents/{agent_id}/config",
            headers=master_headers,
            json={"rate_limit_soft": 500, "rate_limit_hard": 100}  # Invalid: hard < soft
        )
        assert response.status_code == 400
    
    def test_update_system_prompt_persists_with_history(self, master_headers):
        """System prompt update should persist in agent_overrides with history"""
        agent_id = "auditor"
        
        # Get original
        original = requests.get(f"{BASE_URL}/api/agents/{agent_id}/config", headers=master_headers).json()
        original_prompt = original["system_prompt_effective"]
        
        # Update prompt
        test_prompt = f"TEST PROMPT {uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/agents/{agent_id}/config",
            headers=master_headers,
            json={"system_prompt": test_prompt}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["ok"] == True
        assert "system_prompt" in str(data.get("changes", []))
        
        # Verify persistence
        updated = requests.get(f"{BASE_URL}/api/agents/{agent_id}/config", headers=master_headers).json()
        assert updated["system_prompt_effective"] == test_prompt
        assert updated["system_prompt_override"] == True
        assert len(updated.get("history", [])) > 0
        
        # Restore original (or default)
        requests.post(
            f"{BASE_URL}/api/agents/{agent_id}/config",
            headers=master_headers,
            json={"system_prompt": original_prompt}
        )
    
    def test_config_nonexistent_agent_returns_404(self, master_headers):
        """Config for non-existent agent should return 404"""
        response = requests.get(f"{BASE_URL}/api/agents/fake_agent/config", headers=master_headers)
        assert response.status_code == 404


class TestAgentMetrics:
    """Tests for GET /api/agents/panel/metrics"""
    
    def test_metrics_returns_structure(self, master_headers):
        """Metrics should return por_agente, top_tools, por_dia, top_errors"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/metrics?days=7", headers=master_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "desde" in data
        assert "dias" in data
        assert "por_agente" in data
        assert "top_tools" in data
        assert "por_dia" in data
        assert "top_errors" in data
        
        assert data["dias"] == 7
    
    def test_metrics_por_agente_structure(self, master_headers):
        """por_agente should have agent stats"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/metrics?days=7", headers=master_headers)
        data = response.json()
        
        for agent_stat in data["por_agente"]:
            assert "agent_id" in agent_stat
            assert "total" in agent_stat
            assert "errores" in agent_stat
            assert "tasa_exito" in agent_stat
    
    def test_metrics_top_tools_structure(self, master_headers):
        """top_tools should have tool usage stats"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/metrics?days=7", headers=master_headers)
        data = response.json()
        
        for tool_stat in data["top_tools"]:
            assert "agent_id" in tool_stat
            assert "tool" in tool_stat
            assert "total" in tool_stat
    
    def test_metrics_different_days(self, master_headers):
        """Metrics should accept different day ranges"""
        for days in [1, 7, 30]:
            response = requests.get(f"{BASE_URL}/api/agents/panel/metrics?days={days}", headers=master_headers)
            assert response.status_code == 200
            assert response.json()["dias"] == days


class TestPendingApprovals:
    """Tests for GET/POST /api/agents/panel/pending-approvals"""
    
    def test_list_pending_approvals(self, master_headers):
        """Should return list of pending approvals (may be empty)"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/pending-approvals", headers=master_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
    
    def test_decide_nonexistent_approval_returns_404(self, master_headers):
        """Deciding on non-existent approval should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/agents/panel/pending-approvals/fake_approval_id/decide",
            headers=master_headers,
            json={"decision": "aprobar"}
        )
        assert response.status_code == 404
    
    def test_decide_requires_valid_decision(self, master_headers):
        """Decision must be aprobar/rechazar/modificar"""
        response = requests.post(
            f"{BASE_URL}/api/agents/panel/pending-approvals/any_id/decide",
            headers=master_headers,
            json={"decision": "invalid_decision"}
        )
        # Should fail validation (422) or not found (404)
        assert response.status_code in [404, 422]


class TestRegressionLogisticaAjustes:
    """Regression tests for /crm/logistica and /crm/ajustes/gls"""
    
    def test_logistica_panel_resumen(self, master_headers):
        """Logistica panel resumen should still work"""
        response = requests.get(f"{BASE_URL}/api/logistica/panel/resumen", headers=master_headers)
        assert response.status_code == 200, f"Logistica panel broken: {response.status_code}"
        
        data = response.json()
        assert "envios_activos" in data
        assert "total_envios_mes" in data
    
    def test_gls_config(self, master_headers):
        """GLS config should still work"""
        response = requests.get(f"{BASE_URL}/api/logistica/config/gls", headers=master_headers)
        assert response.status_code == 200, f"GLS config broken: {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

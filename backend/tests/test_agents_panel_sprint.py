"""
Test suite for Agents Panel Sprint - PUNTO 1 del roadmap
Tests all new endpoints for /crm/agentes panel avanzado

Endpoints tested:
- GET /api/agents/panel/overview - 11 agentes con tools array [NUEVO]
- POST /api/agents/{id}/pause - master/admin only (403 para otros)
- POST /api/agents/{id}/activate - master/admin only
- GET /api/agents/{id}/timeline - filtros tool, resultado, desde/hasta
- GET /api/agents/{id}/config - system_prompt_default/effective/override, rate limits, history, scopes, tools
- POST /api/agents/{id}/config - master/admin only, validación hard >= soft
- GET /api/agents/panel/metrics?days=N - por_agente, top_tools, por_dia, top_errors
- GET /api/agents/panel/pending-approvals - items con estado=pendiente
- POST /api/agents/panel/pending-approvals/{id}/decide - aprobar/rechazar/modificar
- GET /api/agents/scheduled-tasks?agent_id=X - lista tareas filtradas
- POST /api/agents/scheduled-tasks/{task_id}/run-now - ejecuta inmediato
- PATCH /api/agents/scheduled-tasks/{task_id} - activo: true/false
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

# Load env
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL not set")

# Test credentials from /app/memory/test_credentials.md
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


# ══════════════════════════════════════════════════════════════════════════════
# 1. GET /api/agents/panel/overview - 11 agentes con tools array
# ══════════════════════════════════════════════════════════════════════════════

class TestPanelOverview:
    """Tests for GET /api/agents/panel/overview"""
    
    def test_overview_returns_11_agents(self, master_headers):
        """Overview should return 11 agents (8 legacy + 3 Fase 4)"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/overview", headers=master_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "agents" in data
        assert "resumen" in data
        
        agents = data["agents"]
        assert len(agents) == 11, f"Expected 11 agents, got {len(agents)}: {[a['agent_id'] for a in agents]}"
    
    def test_overview_agent_has_tools_array(self, master_headers):
        """Each agent should have tools array (not just tools_count)"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/overview", headers=master_headers)
        assert response.status_code == 200
        
        agents = response.json()["agents"]
        for agent in agents:
            assert "agent_id" in agent
            assert "nombre" in agent
            assert "descripcion" in agent
            assert "emoji" in agent
            assert "color" in agent
            assert "estado" in agent
            assert "tools_count" in agent
            assert "tools" in agent, f"Agent {agent['agent_id']} missing 'tools' array"
            assert isinstance(agent["tools"], list), f"Agent {agent['agent_id']} tools should be list"
            assert "scopes" in agent
            assert "acciones_hoy" in agent
            assert "tasa_exito_7d" in agent
            assert "errores_24h" in agent
            assert "ultima_accion" in agent
    
    def test_overview_resumen_structure(self, master_headers):
        """Resumen should have all required fields"""
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
    
    def test_overview_all_11_agents_present(self, master_headers):
        """All 11 agents should be present"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/overview", headers=master_headers)
        assert response.status_code == 200
        
        agent_ids = {a["agent_id"] for a in response.json()["agents"]}
        expected = {
            "kpi_analyst", "auditor", "supervisor_cola", "iso_officer",
            "finance_officer", "gestor_siniestros", "triador_averias", "gestor_compras",
            "call_center", "presupuestador_publico", "seguimiento_publico"
        }
        assert agent_ids == expected, f"Missing agents: {expected - agent_ids}"


# ══════════════════════════════════════════════════════════════════════════════
# 2. POST /api/agents/{id}/pause and /activate - master/admin only
# ══════════════════════════════════════════════════════════════════════════════

class TestPauseActivate:
    """Tests for pause/activate endpoints"""
    
    def test_pause_agent_as_master(self, master_headers):
        """Master can pause an agent"""
        agent_id = "iso_officer"
        response = requests.post(f"{BASE_URL}/api/agents/{agent_id}/pause", headers=master_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["ok"] == True
        assert data["agent_id"] == agent_id
        assert data["estado"] == "pausado"
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/agents/{agent_id}/activate", headers=master_headers)
    
    def test_activate_agent_as_master(self, master_headers):
        """Master can activate a paused agent"""
        agent_id = "iso_officer"
        # First pause
        requests.post(f"{BASE_URL}/api/agents/{agent_id}/pause", headers=master_headers)
        
        # Then activate
        response = requests.post(f"{BASE_URL}/api/agents/{agent_id}/activate", headers=master_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["ok"] == True
        assert data["estado"] == "activo"
    
    def test_pause_idempotent(self, master_headers):
        """Pausing already paused agent should succeed (idempotent)"""
        agent_id = "finance_officer"
        # Pause twice
        r1 = requests.post(f"{BASE_URL}/api/agents/{agent_id}/pause", headers=master_headers)
        r2 = requests.post(f"{BASE_URL}/api/agents/{agent_id}/pause", headers=master_headers)
        
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r2.json()["estado"] == "pausado"
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/agents/{agent_id}/activate", headers=master_headers)
    
    def test_pause_persists_in_agent_states(self, master_headers):
        """Pause should persist and show in overview"""
        agent_id = "gestor_compras"
        
        # Pause
        requests.post(f"{BASE_URL}/api/agents/{agent_id}/pause", headers=master_headers)
        
        # Verify via overview
        overview = requests.get(f"{BASE_URL}/api/agents/panel/overview", headers=master_headers)
        agents = overview.json()["agents"]
        agent = next((a for a in agents if a["agent_id"] == agent_id), None)
        assert agent is not None
        assert agent["estado"] == "pausado"
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/agents/{agent_id}/activate", headers=master_headers)
    
    def test_pause_nonexistent_agent_returns_404(self, master_headers):
        """Pausing non-existent agent should return 404"""
        response = requests.post(f"{BASE_URL}/api/agents/fake_agent_xyz/pause", headers=master_headers)
        assert response.status_code == 404
    
    def test_pause_requires_master_or_admin_403(self, tecnico_headers):
        """Non-master/admin (tecnico) cannot pause agents - should get 403"""
        agent_id = "kpi_analyst"
        response = requests.post(f"{BASE_URL}/api/agents/{agent_id}/pause", headers=tecnico_headers)
        assert response.status_code == 403, f"Expected 403 for tecnico, got {response.status_code}"
    
    def test_activate_requires_master_or_admin_403(self, tecnico_headers):
        """Non-master/admin cannot activate agents - should get 403"""
        agent_id = "kpi_analyst"
        response = requests.post(f"{BASE_URL}/api/agents/{agent_id}/activate", headers=tecnico_headers)
        assert response.status_code == 403, f"Expected 403 for tecnico, got {response.status_code}"


# ══════════════════════════════════════════════════════════════════════════════
# 3. GET /api/agents/{id}/timeline - filtros
# ══════════════════════════════════════════════════════════════════════════════

class TestTimeline:
    """Tests for GET /api/agents/{id}/timeline"""
    
    def test_timeline_returns_items(self, master_headers):
        """Timeline should return audit log items"""
        agent_id = "kpi_analyst"
        response = requests.get(f"{BASE_URL}/api/agents/{agent_id}/timeline", headers=master_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
    
    def test_timeline_filter_by_tool(self, master_headers):
        """Timeline can filter by tool name"""
        agent_id = "kpi_analyst"
        response = requests.get(
            f"{BASE_URL}/api/agents/{agent_id}/timeline?tool=obtener_dashboard",
            headers=master_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        for item in data["items"]:
            assert item.get("tool") == "obtener_dashboard"
    
    def test_timeline_filter_by_resultado_error(self, master_headers):
        """Timeline can filter by resultado=error"""
        agent_id = "kpi_analyst"
        response = requests.get(
            f"{BASE_URL}/api/agents/{agent_id}/timeline?resultado=error",
            headers=master_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        for item in data["items"]:
            assert item.get("error") is not None
    
    def test_timeline_filter_by_resultado_ok(self, master_headers):
        """Timeline can filter by resultado=ok"""
        agent_id = "kpi_analyst"
        response = requests.get(
            f"{BASE_URL}/api/agents/{agent_id}/timeline?resultado=ok",
            headers=master_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        for item in data["items"]:
            assert item.get("error") is None
    
    def test_timeline_filter_by_desde_hasta(self, master_headers):
        """Timeline can filter by desde/hasta dates"""
        agent_id = "kpi_analyst"
        desde = "2025-01-01T00:00:00"
        hasta = "2026-12-31T23:59:59"
        response = requests.get(
            f"{BASE_URL}/api/agents/{agent_id}/timeline?desde={desde}&hasta={hasta}",
            headers=master_headers
        )
        assert response.status_code == 200
    
    def test_timeline_limit_parameter(self, master_headers):
        """Timeline respects limit parameter"""
        agent_id = "kpi_analyst"
        response = requests.get(
            f"{BASE_URL}/api/agents/{agent_id}/timeline?limit=5",
            headers=master_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) <= 5
    
    def test_timeline_nonexistent_agent_returns_404(self, master_headers):
        """Timeline for non-existent agent should return 404"""
        response = requests.get(f"{BASE_URL}/api/agents/fake_agent/timeline", headers=master_headers)
        assert response.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# 4. GET/POST /api/agents/{id}/config
# ══════════════════════════════════════════════════════════════════════════════

class TestConfig:
    """Tests for GET/POST /api/agents/{id}/config"""
    
    def test_get_config_returns_all_fields(self, master_headers):
        """Config should return all required fields"""
        agent_id = "kpi_analyst"
        response = requests.get(f"{BASE_URL}/api/agents/{agent_id}/config", headers=master_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["agent_id"] == agent_id
        assert "system_prompt_default" in data
        assert "system_prompt_effective" in data
        assert "system_prompt_override" in data
        assert "rate_limit_soft" in data
        assert "rate_limit_hard" in data
        assert "history" in data
        assert "scopes" in data
        assert "tools" in data
        
        assert isinstance(data["scopes"], list)
        assert isinstance(data["tools"], list)
        assert isinstance(data["history"], list)
    
    def test_update_rate_limits_as_master(self, master_headers):
        """Master can update rate limits"""
        agent_id = "auditor"
        
        # Get current
        current = requests.get(f"{BASE_URL}/api/agents/{agent_id}/config", headers=master_headers).json()
        original_soft = current["rate_limit_soft"]
        original_hard = current["rate_limit_hard"]
        
        # Update
        new_soft = 200
        new_hard = 800
        response = requests.post(
            f"{BASE_URL}/api/agents/{agent_id}/config",
            headers=master_headers,
            json={"rate_limit_soft": new_soft, "rate_limit_hard": new_hard}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["ok"] == True
        
        # Verify persistence
        updated = requests.get(f"{BASE_URL}/api/agents/{agent_id}/config", headers=master_headers).json()
        assert updated["rate_limit_soft"] == new_soft
        assert updated["rate_limit_hard"] == new_hard
        
        # Restore
        requests.post(
            f"{BASE_URL}/api/agents/{agent_id}/config",
            headers=master_headers,
            json={"rate_limit_soft": original_soft, "rate_limit_hard": original_hard}
        )
    
    def test_update_rate_limits_validates_hard_gte_soft(self, master_headers):
        """hard_limit must be >= soft_limit (400 if not)"""
        agent_id = "auditor"
        response = requests.post(
            f"{BASE_URL}/api/agents/{agent_id}/config",
            headers=master_headers,
            json={"rate_limit_soft": 500, "rate_limit_hard": 100}  # Invalid
        )
        assert response.status_code == 400
    
    def test_update_system_prompt_persists_with_history(self, master_headers):
        """System prompt update should persist with history entry"""
        agent_id = "supervisor_cola"
        
        # Get original
        original = requests.get(f"{BASE_URL}/api/agents/{agent_id}/config", headers=master_headers).json()
        original_prompt = original["system_prompt_effective"]
        original_history_len = len(original.get("history", []))
        
        # Update
        test_prompt = f"TEST PROMPT {uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/agents/{agent_id}/config",
            headers=master_headers,
            json={"system_prompt": test_prompt}
        )
        assert response.status_code == 200
        
        # Verify
        updated = requests.get(f"{BASE_URL}/api/agents/{agent_id}/config", headers=master_headers).json()
        assert updated["system_prompt_effective"] == test_prompt
        assert updated["system_prompt_override"] == True
        assert len(updated.get("history", [])) > original_history_len
        
        # Restore
        requests.post(
            f"{BASE_URL}/api/agents/{agent_id}/config",
            headers=master_headers,
            json={"system_prompt": original_prompt}
        )
    
    def test_config_creates_audit_log_entry(self, master_headers):
        """Config update should create audit_log entry with tool='_config_update'"""
        agent_id = "triador_averias"
        
        # Update something
        response = requests.post(
            f"{BASE_URL}/api/agents/{agent_id}/config",
            headers=master_headers,
            json={"rate_limit_soft": 130, "rate_limit_hard": 650}
        )
        assert response.status_code == 200
        
        # Check timeline for _config_update
        timeline = requests.get(
            f"{BASE_URL}/api/agents/{agent_id}/timeline?tool=_config_update&limit=5",
            headers=master_headers
        )
        assert timeline.status_code == 200
        items = timeline.json()["items"]
        # Should have at least one _config_update entry
        assert any(i.get("tool") == "_config_update" for i in items)
    
    def test_config_requires_master_or_admin_403(self, tecnico_headers):
        """Non-master/admin cannot update config - should get 403"""
        agent_id = "kpi_analyst"
        response = requests.post(
            f"{BASE_URL}/api/agents/{agent_id}/config",
            headers=tecnico_headers,
            json={"rate_limit_soft": 100}
        )
        assert response.status_code == 403
    
    def test_config_nonexistent_agent_returns_404(self, master_headers):
        """Config for non-existent agent should return 404"""
        response = requests.get(f"{BASE_URL}/api/agents/fake_agent/config", headers=master_headers)
        assert response.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# 5. GET /api/agents/panel/metrics?days=N
# ══════════════════════════════════════════════════════════════════════════════

class TestMetrics:
    """Tests for GET /api/agents/panel/metrics"""
    
    def test_metrics_returns_structure(self, master_headers):
        """Metrics should return por_agente, top_tools, por_dia, top_errors"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/metrics?days=7", headers=master_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "desde" in data
        assert "dias" in data
        assert "por_agente" in data
        assert "top_tools" in data
        assert "por_dia" in data
        assert "top_errors" in data
        
        assert data["dias"] == 7
    
    def test_metrics_days_1(self, master_headers):
        """Metrics with days=1"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/metrics?days=1", headers=master_headers)
        assert response.status_code == 200
        assert response.json()["dias"] == 1
    
    def test_metrics_days_30(self, master_headers):
        """Metrics with days=30"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/metrics?days=30", headers=master_headers)
        assert response.status_code == 200
        assert response.json()["dias"] == 30
    
    def test_metrics_por_agente_structure(self, master_headers):
        """por_agente should have correct structure"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/metrics?days=7", headers=master_headers)
        data = response.json()
        
        for agent_stat in data["por_agente"]:
            assert "agent_id" in agent_stat
            assert "total" in agent_stat
            assert "errores" in agent_stat
            assert "tasa_exito" in agent_stat
    
    def test_metrics_top_tools_structure(self, master_headers):
        """top_tools should have correct structure"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/metrics?days=7", headers=master_headers)
        data = response.json()
        
        for tool_stat in data["top_tools"]:
            assert "agent_id" in tool_stat
            assert "tool" in tool_stat
            assert "total" in tool_stat


# ══════════════════════════════════════════════════════════════════════════════
# 6. GET/POST /api/agents/panel/pending-approvals
# ══════════════════════════════════════════════════════════════════════════════

class TestPendingApprovals:
    """Tests for pending approvals endpoints"""
    
    def test_list_pending_approvals(self, master_headers):
        """Should return list of pending approvals"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/pending-approvals", headers=master_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        
        # All items should have estado=pendiente
        for item in data["items"]:
            assert item.get("estado") == "pendiente"
    
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
    
    def test_decide_requires_master_or_admin_403(self, tecnico_headers):
        """Non-master/admin cannot decide - should get 403"""
        response = requests.post(
            f"{BASE_URL}/api/agents/panel/pending-approvals/any_id/decide",
            headers=tecnico_headers,
            json={"decision": "aprobar"}
        )
        assert response.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# 7. GET/POST/PATCH /api/agents/scheduled-tasks
# ══════════════════════════════════════════════════════════════════════════════

class TestScheduledTasks:
    """Tests for scheduled tasks endpoints"""
    
    def test_list_scheduled_tasks(self, master_headers):
        """Should return list of scheduled tasks"""
        response = requests.get(f"{BASE_URL}/api/agents/scheduled-tasks", headers=master_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "tasks" in data
        assert "count" in data
        assert isinstance(data["tasks"], list)
    
    def test_list_scheduled_tasks_filter_by_agent(self, master_headers):
        """Should filter tasks by agent_id"""
        agent_id = "kpi_analyst"
        response = requests.get(
            f"{BASE_URL}/api/agents/scheduled-tasks?agent_id={agent_id}",
            headers=master_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        for task in data["tasks"]:
            assert task.get("agent_id") == agent_id
    
    def test_run_now_nonexistent_task_returns_404(self, master_headers):
        """Run-now on non-existent task should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/agents/scheduled-tasks/fake_task_id/run-now",
            headers=master_headers
        )
        assert response.status_code == 404
    
    def test_patch_task_activo_toggle(self, master_headers):
        """PATCH should accept activo: true/false"""
        # First get a task if any exist
        tasks_resp = requests.get(f"{BASE_URL}/api/agents/scheduled-tasks", headers=master_headers)
        tasks = tasks_resp.json().get("tasks", [])
        
        if not tasks:
            pytest.skip("No scheduled tasks to test PATCH")
        
        task = tasks[0]
        task_id = task["id"]
        original_activo = task.get("activo", True)
        
        # Toggle
        new_activo = not original_activo
        response = requests.patch(
            f"{BASE_URL}/api/agents/scheduled-tasks/{task_id}",
            headers=master_headers,
            json={"activo": new_activo}
        )
        assert response.status_code == 200
        
        # Verify
        updated_tasks = requests.get(f"{BASE_URL}/api/agents/scheduled-tasks", headers=master_headers).json()["tasks"]
        updated_task = next((t for t in updated_tasks if t["id"] == task_id), None)
        assert updated_task is not None
        assert updated_task.get("activo") == new_activo
        
        # Restore
        requests.patch(
            f"{BASE_URL}/api/agents/scheduled-tasks/{task_id}",
            headers=master_headers,
            json={"activo": original_activo}
        )
    
    def test_patch_nonexistent_task_returns_404(self, master_headers):
        """PATCH on non-existent task should return 404"""
        response = requests.patch(
            f"{BASE_URL}/api/agents/scheduled-tasks/fake_task_id",
            headers=master_headers,
            json={"activo": False}
        )
        assert response.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# 8. Regression tests - Fase 4 MCP still works
# ══════════════════════════════════════════════════════════════════════════════

class TestRegressionFase4:
    """Regression tests to ensure Fase 4 MCP still works"""
    
    def test_all_11_agents_have_correct_scopes(self, master_headers):
        """All 11 agents should have their expected scopes"""
        response = requests.get(f"{BASE_URL}/api/agents/panel/overview", headers=master_headers)
        agents = {a["agent_id"]: a for a in response.json()["agents"]}
        
        # Check call_center scopes
        cc = agents.get("call_center")
        assert cc is not None
        cc_scopes = set(cc.get("scopes", []))
        assert "customers:read" in cc_scopes
        assert "orders:read" in cc_scopes
        assert "comm:write" in cc_scopes
        assert "comm:escalate" in cc_scopes
        
        # Check presupuestador_publico scopes
        pp = agents.get("presupuestador_publico")
        assert pp is not None
        pp_scopes = set(pp.get("scopes", []))
        assert "catalog:read" in pp_scopes
        assert "quotes:write_public" in pp_scopes
        
        # Check seguimiento_publico scopes
        sp = agents.get("seguimiento_publico")
        assert sp is not None
        sp_scopes = set(sp.get("scopes", []))
        assert "public:track_by_token" in sp_scopes
    
    def test_basic_endpoints_still_work(self, master_headers):
        """Basic endpoints should still work"""
        # Health
        r = requests.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        
        # Dashboard
        r = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=master_headers)
        assert r.status_code == 200
        
        # Ordenes
        r = requests.get(f"{BASE_URL}/api/ordenes", headers=master_headers)
        assert r.status_code == 200
        
        # Clientes
        r = requests.get(f"{BASE_URL}/api/clientes", headers=master_headers)
        assert r.status_code == 200
    
    def test_logistica_panel_still_works(self, master_headers):
        """Logistica panel should still work"""
        r = requests.get(f"{BASE_URL}/api/logistica/panel/resumen", headers=master_headers)
        assert r.status_code == 200
    
    def test_finanzas_dashboard_still_works(self, master_headers):
        """Finanzas dashboard should still work"""
        r = requests.get(f"{BASE_URL}/api/finanzas/dashboard", headers=master_headers)
        assert r.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

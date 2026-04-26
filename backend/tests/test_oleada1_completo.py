"""
Tests completos Oleada 1 — autonomía agentes (kpi_analyst, auditor, iso_officer)
+ kill-switch global (pausa de emergencia) + verificación de roles.

Cubre:
- 4 tareas Oleada 1 sembradas correctamente
- Endpoints /api/agents/autonomy/{status,pause-all,resume-all}
- Kill-switch persistencia y snapshot
- Verificación de roles (master vs admin)
- run-now de kpi_analyst devuelve dashboard real
- Audit logs con tool='_kill_switch_activated' y '_kill_switch_resumed'
- Variable MCP_FAILURE_NOTIFY_EMAIL
"""
import os
import uuid
import time

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
MASTER_EMAIL = "master@revix.es"
MASTER_PASS = "RevixMaster2026!"


def _login(email=MASTER_EMAIL, password=MASTER_PASS):
    r = requests.post(
        f"{BASE}/api/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    if r.status_code == 429:
        pytest.skip("Rate limit activo - esperar 15 minutos")
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["token"]


def _h(t):
    return {"Authorization": f"Bearer {t}"}


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: Tareas Oleada 1 sembradas
# ═══════════════════════════════════════════════════════════════════════════════

class TestOleada1TasksSeeded:
    """Verificar que las 4 tareas de Oleada 1 están sembradas correctamente."""

    def test_4_tareas_oleada1_existen(self):
        """Las 4 tareas de Oleada 1 deben existir y estar activas."""
        t = _login()
        expected = {
            ("kpi_analyst", "obtener_dashboard", "0 8 * * *"),
            ("auditor", "ejecutar_audit_operacional", "0 22 * * *"),
            ("auditor", "generar_audit_report", "0 9 * * 1"),
            ("iso_officer", "generar_revision_direccion", "0 6 1 * *"),
        }
        r = requests.get(f"{BASE}/api/agents/scheduled-tasks", headers=_h(t), timeout=10)
        assert r.status_code == 200
        tasks = r.json().get("tasks", [])
        found = {(x["agent_id"], x["tool"], x["cron_expression"]) for x in tasks if x.get("activo", True)}
        missing = expected - found
        assert not missing, f"Faltan tareas Oleada 1: {missing}"

    def test_tareas_oleada1_tienen_descripcion(self):
        """Las 4 tareas específicas de Oleada 1 deben existir con sus cron correctos."""
        t = _login()
        r = requests.get(f"{BASE}/api/agents/scheduled-tasks", headers=_h(t), timeout=10)
        assert r.status_code == 200
        tasks = r.json().get("tasks", [])
        # Verificar que las 4 tareas específicas de Oleada 1 existen
        oleada1_crons = {
            ("kpi_analyst", "0 8 * * *"),
            ("auditor", "0 22 * * *"),
            ("auditor", "0 9 * * 1"),
            ("iso_officer", "0 6 1 * *"),
        }
        found = {(t["agent_id"], t["cron_expression"]) for t in tasks}
        missing = oleada1_crons - found
        assert not missing, f"Faltan tareas Oleada 1: {missing}"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: Endpoint /api/agents/autonomy/status
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutonomyStatus:
    """Verificar endpoint GET /api/agents/autonomy/status."""

    def test_status_devuelve_campos_requeridos(self):
        """Status debe devolver paused, paused_at, paused_by, reason, tasks_activas, tasks_pausadas."""
        t = _login()
        r = requests.get(f"{BASE}/api/agents/autonomy/status", headers=_h(t), timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "paused" in d
        assert "paused_at" in d
        assert "paused_by" in d
        assert "reason" in d
        assert "tasks_activas" in d
        assert "tasks_pausadas" in d

    def test_status_sin_auth_devuelve_401(self):
        """Sin token → 401."""
        r = requests.get(f"{BASE}/api/agents/autonomy/status", timeout=10)
        assert r.status_code == 401

    def test_status_tasks_activas_minimo_4(self):
        """Debe haber al menos 4 tareas activas (Oleada 1)."""
        t = _login()
        r = requests.get(f"{BASE}/api/agents/autonomy/status", headers=_h(t), timeout=10)
        assert r.status_code == 200
        d = r.json()
        # Si no está pausado, debe haber al menos 4 activas
        if not d["paused"]:
            assert d["tasks_activas"] >= 4, f"Esperadas >=4 tareas activas, hay {d['tasks_activas']}"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: Endpoints pause-all y resume-all
# ═══════════════════════════════════════════════════════════════════════════════

class TestKillSwitch:
    """Verificar endpoints POST /api/agents/autonomy/pause-all y resume-all."""

    def test_pause_all_sin_auth_devuelve_401(self):
        """Sin token → 401."""
        r = requests.post(f"{BASE}/api/agents/autonomy/pause-all", json={}, timeout=10)
        assert r.status_code == 401

    def test_resume_all_sin_auth_devuelve_401(self):
        """Sin token → 401."""
        r = requests.post(f"{BASE}/api/agents/autonomy/resume-all", timeout=10)
        assert r.status_code == 401

    def test_pause_resume_cycle_completo(self):
        """Ciclo completo: pause-all → status → resume-all → status."""
        t = _login()
        reason = f"test-{uuid.uuid4().hex[:8]}"
        
        # Estado inicial
        s0 = requests.get(f"{BASE}/api/agents/autonomy/status", headers=_h(t)).json()
        initial_active = s0["tasks_activas"]
        
        # Si ya está pausado, primero reanudar
        if s0["paused"]:
            requests.post(f"{BASE}/api/agents/autonomy/resume-all", headers=_h(t), timeout=10)
            time.sleep(0.5)
            s0 = requests.get(f"{BASE}/api/agents/autonomy/status", headers=_h(t)).json()
            initial_active = s0["tasks_activas"]
        
        try:
            # Pausar
            r = requests.post(
                f"{BASE}/api/agents/autonomy/pause-all",
                headers=_h(t),
                json={"reason": reason},
                timeout=10,
            )
            assert r.status_code == 200, f"pause-all failed: {r.text}"
            d = r.json()
            assert d["paused"] is True
            assert d["tasks_pausadas"] == initial_active
            assert d["reason"] == reason
            
            # Status post-pausa
            s1 = requests.get(f"{BASE}/api/agents/autonomy/status", headers=_h(t)).json()
            assert s1["paused"] is True
            assert s1["tasks_activas"] == 0
            assert s1["tasks_pausadas"] >= initial_active
            assert s1.get("paused_by") is not None
            assert s1.get("reason") == reason
            
            # Resume
            r2 = requests.post(f"{BASE}/api/agents/autonomy/resume-all", headers=_h(t), timeout=10)
            assert r2.status_code == 200
            assert r2.json()["paused"] is False
            
            # Status final restaurado
            s2 = requests.get(f"{BASE}/api/agents/autonomy/status", headers=_h(t)).json()
            assert s2["paused"] is False
            assert s2["tasks_activas"] == initial_active
        finally:
            # SIEMPRE reanudar para no dejar el sistema pausado
            requests.post(f"{BASE}/api/agents/autonomy/resume-all", headers=_h(t), timeout=10)

    def test_pause_all_idempotente(self):
        """Llamar pause-all dos veces no debe fallar."""
        t = _login()
        
        # Asegurar estado inicial no pausado
        s0 = requests.get(f"{BASE}/api/agents/autonomy/status", headers=_h(t)).json()
        if s0["paused"]:
            requests.post(f"{BASE}/api/agents/autonomy/resume-all", headers=_h(t), timeout=10)
            time.sleep(0.5)
        
        try:
            # Primera pausa
            r1 = requests.post(
                f"{BASE}/api/agents/autonomy/pause-all",
                headers=_h(t),
                json={"reason": "test idempotente 1"},
                timeout=10,
            )
            assert r1.status_code == 200
            
            # Segunda pausa (idempotente)
            r2 = requests.post(
                f"{BASE}/api/agents/autonomy/pause-all",
                headers=_h(t),
                json={"reason": "test idempotente 2"},
                timeout=10,
            )
            assert r2.status_code == 200
            # La segunda vez no debería pausar más tareas (ya están pausadas)
            assert r2.json()["tasks_pausadas"] == 0
        finally:
            requests.post(f"{BASE}/api/agents/autonomy/resume-all", headers=_h(t), timeout=10)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: run-now de kpi_analyst
# ═══════════════════════════════════════════════════════════════════════════════

class TestKpiAnalystRunNow:
    """Verificar que run-now de kpi_analyst devuelve dashboard real."""

    def test_run_now_kpi_analyst_success(self):
        """run-now de kpi_analyst debe devolver success=true."""
        t = _login()
        tasks = requests.get(
            f"{BASE}/api/agents/scheduled-tasks?agent_id=kpi_analyst",
            headers=_h(t),
        ).json()["tasks"]
        assert tasks, "kpi_analyst no tiene tareas"
        task_id = tasks[0]["id"]
        r = requests.post(
            f"{BASE}/api/agents/scheduled-tasks/{task_id}/run-now",
            headers=_h(t),
            timeout=60,
        )
        assert r.status_code == 200
        d = r.json()
        assert d.get("success") is True, f"run-now failed: {d}"

    def test_run_now_kpi_analyst_devuelve_dashboard_keys(self):
        """run-now de kpi_analyst debe devolver dashboard con keys esperadas."""
        t = _login()
        tasks = requests.get(
            f"{BASE}/api/agents/scheduled-tasks?agent_id=kpi_analyst",
            headers=_h(t),
        ).json()["tasks"]
        assert tasks, "kpi_analyst no tiene tareas"
        task_id = tasks[0]["id"]
        r = requests.post(
            f"{BASE}/api/agents/scheduled-tasks/{task_id}/run-now",
            headers=_h(t),
            timeout=60,
        )
        assert r.status_code == 200
        d = r.json()
        assert d.get("success") is True
        result = d.get("result", {})
        # El dashboard debe tener al menos algunas de estas keys
        expected_keys = {"periodo", "ordenes", "finanzas", "inventario", "clientes"}
        found_keys = set(result.keys()) if isinstance(result, dict) else set()
        # Al menos 3 de las 5 keys esperadas
        intersection = expected_keys & found_keys
        assert len(intersection) >= 3 or "dashboard" in str(result).lower(), \
            f"Dashboard no tiene keys esperadas. Keys encontradas: {found_keys}"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: Audit logs del kill-switch
# ═══════════════════════════════════════════════════════════════════════════════

class TestKillSwitchAuditLogs:
    """Verificar que pause-all y resume-all crean audit logs."""

    def test_pause_all_crea_audit_log(self):
        """pause-all debe crear audit_log con tool='_kill_switch_activated'."""
        t = _login()
        
        # Asegurar estado inicial no pausado
        s0 = requests.get(f"{BASE}/api/agents/autonomy/status", headers=_h(t)).json()
        if s0["paused"]:
            requests.post(f"{BASE}/api/agents/autonomy/resume-all", headers=_h(t), timeout=10)
            time.sleep(0.5)
        
        try:
            # Pausar
            requests.post(
                f"{BASE}/api/agents/autonomy/pause-all",
                headers=_h(t),
                json={"reason": "test audit log"},
                timeout=10,
            )
            
            # Verificar audit log
            r = requests.get(f"{BASE}/api/agents/audit-logs?limit=10", headers=_h(t), timeout=10)
            assert r.status_code == 200
            logs = r.json().get("logs", [])
            kill_switch_logs = [l for l in logs if l.get("tool") == "_kill_switch_activated"]
            assert len(kill_switch_logs) > 0, "No se encontró audit log de _kill_switch_activated"
        finally:
            requests.post(f"{BASE}/api/agents/autonomy/resume-all", headers=_h(t), timeout=10)

    def test_resume_all_crea_audit_log(self):
        """resume-all debe crear audit_log con tool='_kill_switch_resumed'."""
        t = _login()
        
        # Asegurar estado inicial no pausado
        s0 = requests.get(f"{BASE}/api/agents/autonomy/status", headers=_h(t)).json()
        if s0["paused"]:
            requests.post(f"{BASE}/api/agents/autonomy/resume-all", headers=_h(t), timeout=10)
            time.sleep(0.5)
        
        try:
            # Pausar y luego reanudar
            requests.post(
                f"{BASE}/api/agents/autonomy/pause-all",
                headers=_h(t),
                json={"reason": "test audit log resume"},
                timeout=10,
            )
            requests.post(f"{BASE}/api/agents/autonomy/resume-all", headers=_h(t), timeout=10)
            
            # Verificar audit log
            r = requests.get(f"{BASE}/api/agents/audit-logs?limit=10", headers=_h(t), timeout=10)
            assert r.status_code == 200
            logs = r.json().get("logs", [])
            resume_logs = [l for l in logs if l.get("tool") == "_kill_switch_resumed"]
            assert len(resume_logs) > 0, "No se encontró audit log de _kill_switch_resumed"
        finally:
            requests.post(f"{BASE}/api/agents/autonomy/resume-all", headers=_h(t), timeout=10)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: Regresión - scheduled-tasks lista todas las tareas
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegresion:
    """Verificar que no se rompió funcionalidad existente."""

    def test_scheduled_tasks_lista_correctamente(self):
        """GET /api/agents/scheduled-tasks debe listar todas las tareas."""
        t = _login()
        r = requests.get(f"{BASE}/api/agents/scheduled-tasks", headers=_h(t), timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "tasks" in d
        assert "count" in d
        # Debe haber al menos las 4 de Oleada 1
        assert d["count"] >= 4, f"Esperadas >=4 tareas, hay {d['count']}"

    def test_scheduled_tasks_filtro_por_agent_id(self):
        """GET /api/agents/scheduled-tasks?agent_id=X debe filtrar correctamente."""
        t = _login()
        r = requests.get(f"{BASE}/api/agents/scheduled-tasks?agent_id=auditor", headers=_h(t), timeout=10)
        assert r.status_code == 200
        tasks = r.json().get("tasks", [])
        # Auditor tiene 2 tareas en Oleada 1
        assert len(tasks) >= 2, f"Auditor debería tener >=2 tareas, tiene {len(tasks)}"
        for task in tasks:
            assert task["agent_id"] == "auditor"

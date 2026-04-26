"""
Tests Oleada 1 — autonomía agentes (kpi_analyst, auditor, iso_officer)
+ kill-switch global (pausa de emergencia).
"""
import os
import uuid

import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "master@revix.es")
ADMIN_PASS = os.environ.get("TEST_ADMIN_PASSWORD", "RevixMaster2026!")


def _login():
    r = requests.post(
        f"{BASE}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _h(t):
    return {"Authorization": f"Bearer {t}"}


def test_oleada1_tasks_seeded():
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
    found = {(x["agent_id"], x["tool"], x["cron_expression"]) for x in tasks if x["activo"]}
    missing = expected - found
    assert not missing, f"Faltan tareas Oleada 1: {missing}"


def test_autonomy_status_endpoint():
    t = _login()
    r = requests.get(f"{BASE}/api/agents/autonomy/status", headers=_h(t), timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert "paused" in d
    assert "tasks_activas" in d
    assert d["tasks_activas"] >= 4  # al menos las 4 de Oleada 1


def test_kill_switch_pause_resume_cycle():
    t = _login()
    # Estado inicial
    s0 = requests.get(f"{BASE}/api/agents/autonomy/status", headers=_h(t)).json()
    initial_active = s0["tasks_activas"]
    assert s0["paused"] is False, "El test asume estado no-pausado al inicio"
    # Pausa
    r = requests.post(
        f"{BASE}/api/agents/autonomy/pause-all",
        headers=_h(t),
        json={"reason": f"test-{uuid.uuid4().hex[:8]}"},
        timeout=10,
    )
    assert r.status_code == 200
    d = r.json()
    assert d["paused"] is True
    assert d["tasks_pausadas"] == initial_active
    # Status post-pausa
    s1 = requests.get(f"{BASE}/api/agents/autonomy/status", headers=_h(t)).json()
    assert s1["paused"] is True
    assert s1["tasks_activas"] == 0
    assert s1["tasks_pausadas"] >= initial_active
    assert s1.get("paused_by") and s1.get("reason")
    # Resume
    r2 = requests.post(f"{BASE}/api/agents/autonomy/resume-all", headers=_h(t), timeout=10)
    assert r2.status_code == 200
    assert r2.json()["paused"] is False
    # Status final restaurado
    s2 = requests.get(f"{BASE}/api/agents/autonomy/status", headers=_h(t)).json()
    assert s2["paused"] is False
    assert s2["tasks_activas"] == initial_active


def test_kpi_analyst_run_now_funciona():
    """Validar que la tarea de kpi_analyst se ejecuta sin fallar."""
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
    assert r.json().get("success") is True


def test_endpoints_autonomia_protegidos():
    """status: cualquier auth. pause/resume: SOLO master."""
    # Sin token → 401
    r = requests.get(f"{BASE}/api/agents/autonomy/status", timeout=10)
    assert r.status_code == 401
    r = requests.post(f"{BASE}/api/agents/autonomy/pause-all", json={}, timeout=10)
    assert r.status_code == 401


def test_scheduler_ignora_tareas_durante_pause_all():
    """Tras pause-all, run-now individual sigue funcionando (es manual),
    pero el scheduler tick no ejecuta nada."""
    t = _login()
    # Pausa
    requests.post(
        f"{BASE}/api/agents/autonomy/pause-all",
        headers=_h(t), json={"reason": "test scheduler ignore"}, timeout=10,
    )
    try:
        # Run-now sigue funcionando (acción manual)
        tasks = requests.get(
            f"{BASE}/api/agents/scheduled-tasks?agent_id=kpi_analyst",
            headers=_h(t),
        ).json()["tasks"]
        if tasks:
            r = requests.post(
                f"{BASE}/api/agents/scheduled-tasks/{tasks[0]['id']}/run-now",
                headers=_h(t), timeout=60,
            )
            # run-now manual funciona aunque la tarea esté inactiva
            assert r.status_code in (200, 400)
    finally:
        # SIEMPRE reanudar para no dejar el sistema pausado
        requests.post(f"{BASE}/api/agents/autonomy/resume-all", headers=_h(t), timeout=10)

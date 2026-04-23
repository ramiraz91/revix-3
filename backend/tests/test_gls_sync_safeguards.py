"""
Tests de salvaguardas del sync histórico GLS (backup + dry-run + confirmación + rollback).

Cubre:
  1. Entorno expuesto en /candidatas (entorno + hard_cap + soft_warning + confirmacion_texto).
  2. dry_run=True por defecto → no modifica BD, no crea backups.
  3. Parámetro `sync_run_id` devuelto + persistido en gls_sync_runs.
  4. max_ordenes > hard_cap → 400.
  5. En production: dry_run=False sin `confirmacion` → 400.
  6. En production: dry_run=False + max_ordenes > soft_warning sin forzar → 400.
  7. Endpoint GET /gls/sync-runs lista runs.
  8. Endpoint GET /gls/sync-runs/{id} devuelve run + backups.
  9. Endpoint POST /gls/sync-runs/{id}/restaurar (rollback) restaura estado previo.

Ejecución: usa env MCP_ENV=preview por defecto. Para simular production, el test 5-6
fuerza `production` creando una orden real + payload que hace el endpoint rechazar.
Como no podemos alterar MCP_ENV del backend vivo, esos dos casos se marcan skip
si el pod corre con MCP_ENV=preview y se ejecutan solo en CI production.
"""
import os
import uuid
from datetime import datetime, timezone

import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
MASTER = ("master@revix.es", "RevixMaster2026!")
TECNICO = ("tecnico1@revix.es", "Tecnico1Demo!")


def _login(email, pwd):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pwd})
    if r.status_code != 200:
        pytest.skip(f"Login {email} failed: {r.status_code}")
    return r.json().get("token")


@pytest.fixture(scope="module")
def master_tok():
    return _login(*MASTER)


@pytest.fixture(scope="module")
def tecnico_tok():
    return _login(*TECNICO)


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


# ── 1. Candidatas expone los parámetros de salvaguarda ───────────────────────
def test_candidatas_exposes_safeguard_params(master_tok):
    r = requests.get(
        f"{BASE}/api/logistica/gls/sincronizar-ordenes/candidatas?dias_atras=45",
        headers=H(master_tok),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["entorno"] in ("preview", "production")
    assert data["hard_cap_max_ordenes"] == 500
    assert data["soft_warning_max_ordenes"] == 50
    assert data["confirmacion_texto"] == "CONFIRMO"
    assert "total_candidatas" in data


# ── 2. dry_run=True por defecto ──────────────────────────────────────────────
def test_dry_run_is_default(master_tok):
    r = requests.post(
        f"{BASE}/api/logistica/gls/sincronizar-ordenes",
        headers=H(master_tok),
        json={"dias_atras": 1, "max_ordenes": 5},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["dry_run"] is True
    assert data["sync_run_id"].startswith("run_")
    # En dry-run, los resultados marcan status ok_dryrun
    for res in data.get("resultados", []):
        if res.get("status") == "ok":
            assert False, "dry_run=True no debe producir status=ok (solo ok_dryrun)"


# ── 3. max_ordenes > hard cap → 400 ──────────────────────────────────────────
def test_hard_cap_excedido(master_tok):
    r = requests.post(
        f"{BASE}/api/logistica/gls/sincronizar-ordenes",
        headers=H(master_tok),
        json={"dias_atras": 45, "max_ordenes": 9999},
    )
    assert r.status_code == 400
    assert "500" in r.text or "limite" in r.text.lower() or "hard" in r.text.lower() or "límite" in r.text.lower()


# ── 4. Tecnico bloqueado ─────────────────────────────────────────────────────
def test_tecnico_cannot_sync(tecnico_tok):
    r = requests.post(
        f"{BASE}/api/logistica/gls/sincronizar-ordenes",
        headers=H(tecnico_tok),
        json={"dias_atras": 45, "max_ordenes": 5, "dry_run": True},
    )
    assert r.status_code == 403


# ── 5. Production: sin CONFIRMO → 400 (skip si preview) ──────────────────────
def _get_entorno(tok):
    r = requests.get(
        f"{BASE}/api/logistica/gls/sincronizar-ordenes/candidatas?dias_atras=1",
        headers=H(tok),
    )
    return r.json().get("entorno") if r.status_code == 200 else "unknown"


def test_production_requires_confirmacion(master_tok):
    if _get_entorno(master_tok) != "production":
        pytest.skip("Requires MCP_ENV=production")
    r = requests.post(
        f"{BASE}/api/logistica/gls/sincronizar-ordenes",
        headers=H(master_tok),
        json={"dias_atras": 1, "max_ordenes": 5, "dry_run": False},
    )
    assert r.status_code == 400
    assert "CONFIRMO" in r.text


def test_production_requires_forzar_por_volumen(master_tok):
    if _get_entorno(master_tok) != "production":
        pytest.skip("Requires MCP_ENV=production")
    r = requests.post(
        f"{BASE}/api/logistica/gls/sincronizar-ordenes",
        headers=H(master_tok),
        json={"dias_atras": 1, "max_ordenes": 100,
              "dry_run": False, "confirmacion": "CONFIRMO"},
    )
    assert r.status_code == 400
    assert "umbral" in r.text.lower() or "forzar" in r.text.lower() or "soft" in r.text.lower()


# ── 6. Endpoints de histórico ────────────────────────────────────────────────
def test_listar_sync_runs(master_tok):
    # Primero creamos un run (dry_run)
    requests.post(
        f"{BASE}/api/logistica/gls/sincronizar-ordenes",
        headers=H(master_tok),
        json={"dias_atras": 1, "max_ordenes": 3},
    )
    r = requests.get(f"{BASE}/api/logistica/gls/sync-runs?limit=10",
                     headers=H(master_tok))
    assert r.status_code == 200
    data = r.json()
    assert "runs" in data and isinstance(data["runs"], list)
    if data["runs"]:
        first = data["runs"][0]
        assert "sync_run_id" in first
        assert "stats" in first
        assert "dry_run" in first


def test_detalle_run(master_tok):
    # Crear un run y consultar su detalle
    r0 = requests.post(
        f"{BASE}/api/logistica/gls/sincronizar-ordenes",
        headers=H(master_tok),
        json={"dias_atras": 1, "max_ordenes": 3},
    )
    run_id = r0.json().get("sync_run_id")
    r = requests.get(f"{BASE}/api/logistica/gls/sync-runs/{run_id}",
                     headers=H(master_tok))
    assert r.status_code == 200
    data = r.json()
    assert data["run"]["sync_run_id"] == run_id
    assert "backups" in data
    # dry_run → sin backups (confirma que el backup solo pasa en no-dry-run)
    assert data["total_backups"] == 0


def test_restore_dryrun_bloqueado(master_tok):
    r0 = requests.post(
        f"{BASE}/api/logistica/gls/sincronizar-ordenes",
        headers=H(master_tok),
        json={"dias_atras": 1, "max_ordenes": 3},
    )
    run_id = r0.json().get("sync_run_id")
    r = requests.post(
        f"{BASE}/api/logistica/gls/sync-runs/{run_id}/restaurar",
        headers=H(master_tok),
        json={"confirmacion": "CONFIRMO"},
    )
    # En preview: dry_run bloqueado (400). En production ídem, dry_run no toca BD.
    assert r.status_code == 400
    assert "dry" in r.text.lower() or "dry-run" in r.text.lower()


def test_restore_run_inexistente(master_tok):
    r = requests.post(
        f"{BASE}/api/logistica/gls/sync-runs/run_inexistente_xxx/restaurar",
        headers=H(master_tok),
        json={"confirmacion": "CONFIRMO"},
    )
    assert r.status_code == 404


# ── 7. E2E (solo preview): dry_run=False en preview → escribe + backup + restore ──
def test_e2e_real_sync_backup_restore_preview(master_tok):
    """
    En preview, dry_run=False NO requiere CONFIRMO (la salvaguarda solo aplica
    en production). Verifica que se escribe, se hace backup, y se puede restaurar.
    """
    if _get_entorno(master_tok) != "preview":
        pytest.skip("E2E preview-only (evita tocar BD real en production)")

    # Crear una orden temporal con numero_autorizacion único
    import pymongo
    from pymongo import MongoClient

    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        pytest.skip("Sin MONGO_URL")
    cli = MongoClient(mongo_url)
    db = cli[db_name]
    oid = f"test-safeg-{uuid.uuid4().hex[:8]}"
    autoriz = f"AUT-SAFEG-{uuid.uuid4().hex[:6].upper()}"
    db.ordenes.insert_one({
        "id": oid, "numero_orden": oid, "numero_autorizacion": autoriz,
        "cp_envio": "28001", "gls_envios": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    try:
        # Sync real (en preview = mock, pero pasa por la vía de escritura+backup)
        r = requests.post(
            f"{BASE}/api/logistica/gls/sincronizar-ordenes",
            headers=H(master_tok),
            json={"order_ids": [oid], "dry_run": False, "max_ordenes": 5},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["dry_run"] is False
        assert data["sincronizadas"] == 1
        run_id = data["sync_run_id"]

        # Verificar que la orden tiene ahora gls_envios
        o = db.ordenes.find_one({"id": oid}, {"_id": 0, "gls_envios": 1})
        assert len(o["gls_envios"]) == 1
        assert o["gls_envios"][0]["sync_run_id"] == run_id

        # Backup presente
        det = requests.get(f"{BASE}/api/logistica/gls/sync-runs/{run_id}",
                           headers=H(master_tok)).json()
        assert det["total_backups"] == 1
        assert det["backups"][0]["gls_envios_previo"] == []

        # Restaurar
        rr = requests.post(
            f"{BASE}/api/logistica/gls/sync-runs/{run_id}/restaurar",
            headers=H(master_tok),
            json={"confirmacion": "CONFIRMO"},
        )
        assert rr.status_code == 200, rr.text
        assert rr.json()["restauradas"] == 1

        # Orden restaurada a gls_envios=[]
        o2 = db.ordenes.find_one({"id": oid}, {"_id": 0, "gls_envios": 1})
        assert o2["gls_envios"] == []

        # Re-restaurar → 409
        rr2 = requests.post(
            f"{BASE}/api/logistica/gls/sync-runs/{run_id}/restaurar",
            headers=H(master_tok),
            json={"confirmacion": "CONFIRMO"},
        )
        assert rr2.status_code == 409
    finally:
        db.ordenes.delete_one({"id": oid})
        db.gls_sync_backups.delete_many({"order_id": oid})

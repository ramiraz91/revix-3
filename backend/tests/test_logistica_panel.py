"""
Tests unitarios para el panel de Logística y Ajustes GLS.

Requiere MongoDB corriendo (MCP_ENV=preview).

Ejecutar:
    cd /app/backend && python -m pytest tests/test_logistica_panel.py -v
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
os.environ.setdefault("MCP_ENV", "preview")
os.environ.setdefault("JWT_SECRET", os.environ.get("JWT_SECRET", "test-secret-panel-logistica"))
sys.path.insert(0, "/app/backend")


@pytest.fixture(scope="module")
def sync_db():
    """Cliente síncrono a la misma BD para seeding (evita conflictos de loop)."""
    mc = MongoClient(os.environ["MONGO_URL"])
    db_name = os.environ["DB_NAME"]
    yield mc[db_name]
    mc.close()


@pytest.fixture(scope="module")
def client():
    from server import app  # noqa: WPS433
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def admin_token(client):
    resp = client.post("/api/auth/login", json={
        "email": "master@revix.es", "password": "RevixMaster2026!",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return data.get("token") or data.get("access_token")


@pytest.fixture(scope="module")
def headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module", autouse=True)
def seed_and_cleanup(sync_db):
    # Limpieza previa
    sync_db.ordenes.delete_many({"id": {"$regex": "^test_mcp_panel_"}})
    sync_db.clientes.delete_many({"id": "test_mcp_panel_cliente"})

    now = datetime.now(timezone.utc)
    creado = (now - timedelta(minutes=5)).isoformat(timespec="seconds")
    fixtures = [
        ("TMP-001", "9000000000001", "EN REPARTO", "6", ""),
        ("TMP-002", "9000000000002", "ENTREGADO", "7", ""),
        ("TMP-003", "9000000000003", "INCIDENCIA DIRECCION ERRONEA", "8",
         "DIRECCION ERRONEA"),
    ]
    for (numero_orden, cod, estado, codigo, incid) in fixtures:
        sync_db.ordenes.update_one(
            {"numero_orden": numero_orden},
            {"$set": {
                "numero_orden": numero_orden,
                "id": f"test_mcp_panel_{numero_orden}",
                "estado": "reparado",
                "cliente_id": "test_mcp_panel_cliente",
                "updated_at": creado,
                "gls_envios": [{
                    "codbarras": cod, "uid": "uid-" + cod,
                    "referencia": "REF-" + cod, "peso_kg": 0.5,
                    "estado_actual": estado, "estado_codigo": codigo,
                    "incidencia": incid,
                    "creado_en": creado, "ultima_actualizacion": creado,
                    "tracking_url": f"https://example/{cod}",
                    "mock_preview": True, "eventos": [],
                }],
            }},
            upsert=True,
        )
    sync_db.clientes.update_one(
        {"id": "test_mcp_panel_cliente"},
        {"$set": {
            "id": "test_mcp_panel_cliente",
            "nombre": "Test Panel", "apellidos": "Cliente",
            "telefono": "600000999",
        }},
        upsert=True,
    )

    yield

    # Cleanup
    sync_db.ordenes.delete_many({"id": {"$regex": "^test_mcp_panel_"}})
    sync_db.clientes.delete_many({"id": "test_mcp_panel_cliente"})
    sync_db.configuracion.delete_one({"tipo": "gls"})


# ── Panel ────────────────────────────────────────────────────────────────────

def test_panel_resumen(client, headers):
    r = client.get("/api/logistica/panel/resumen", headers=headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["envios_activos"] >= 2
    assert d["incidencias_activas"] >= 1
    assert d["recogidas_pendientes"] == 0
    assert d["total_envios_mes"] >= 3


def test_panel_envios_listado(client, headers):
    r = client.get("/api/logistica/panel/envios?page=1&page_size=100", headers=headers)
    assert r.status_code == 200
    d = r.json()
    cods = {i["codbarras"] for i in d["items"]}
    assert "9000000000001" in cods
    fila = next(i for i in d["items"] if i["codbarras"] == "9000000000001")
    assert "Test Panel" in fila["cliente_nombre"]
    assert fila["transportista"] == "GLS"


def test_panel_envios_filtro_solo_incidencias(client, headers):
    r = client.get("/api/logistica/panel/envios?solo_incidencias=true", headers=headers)
    assert r.status_code == 200
    for it in r.json()["items"]:
        assert it["tiene_incidencia"] is True or it["incidencia"]


def test_panel_envios_filtro_entregado(client, headers):
    r = client.get("/api/logistica/panel/envios?estado=ENTREGADO", headers=headers)
    assert r.status_code == 200
    cods = {i["codbarras"] for i in r.json()["items"]}
    assert "9000000000002" in cods
    assert "9000000000001" not in cods


def test_panel_export_csv(client, headers):
    r = client.get("/api/logistica/panel/export-csv", headers=headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    body = r.content.decode("utf-8-sig")
    assert "codbarras" in body
    assert "9000000000001" in body


def test_panel_actualizar_todos(client, headers):
    r = client.post("/api/logistica/panel/actualizar-todos", headers=headers)
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert d["preview"] is True


def test_panel_requiere_auth(client):
    r = client.get("/api/logistica/panel/resumen")
    assert r.status_code in (401, 403)


# ── Config GLS ───────────────────────────────────────────────────────────────

def test_config_gls_get(client, headers):
    r = client.get("/api/logistica/config/gls", headers=headers)
    assert r.status_code == 200
    d = r.json()
    assert d["entorno"] in ("preview", "production")
    assert "uid_cliente_masked" in d
    assert "remitente" in d
    assert "polling_hours" in d
    if d["uid_cliente_set"] and len(d["uid_cliente_masked"]) > 8:
        assert "•" in d["uid_cliente_masked"]


def test_config_gls_guardar_remitente(client, headers):
    payload = {
        "nombre": "TEST_REMITENTE", "direccion": "Test 1", "poblacion": "Test",
        "provincia": "Test", "cp": "12345", "telefono": "600000000", "pais": "34",
    }
    r = client.post("/api/logistica/config/gls/remitente", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["remitente"]["nombre"] == "TEST_REMITENTE"
    assert d["remitente_source"]["nombre"] == "bd"


def test_config_gls_polling_set(client, headers):
    r = client.post("/api/logistica/config/gls/polling",
                    json={"polling_hours": 2.5}, headers=headers)
    assert r.status_code == 200
    assert r.json()["polling_hours"] == 2.5


def test_config_gls_polling_invalid(client, headers):
    r = client.post("/api/logistica/config/gls/polling",
                    json={"polling_hours": 0.01}, headers=headers)
    assert r.status_code == 422


def test_config_gls_verify_preview(client, headers):
    r = client.post("/api/logistica/config/gls/verify", headers=headers)
    assert r.status_code == 200
    d = r.json()
    assert d["preview"] is True
    assert d["ok"] is True


def test_config_gls_requiere_admin(client):
    r = client.get("/api/logistica/config/gls")
    assert r.status_code in (401, 403)


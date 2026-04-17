"""
Tests de regresion para flujos criticos del CRM Revix.
Ejecutar: pytest tests/test_critical_flows.py -v
"""
import os
import sys
import pytest
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

API_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
MASTER_EMAIL = os.environ.get("TEST_MASTER_EMAIL", "master@revix.es")
MASTER_PASS = os.environ.get("TEST_MASTER_PASSWORD", "RevixMaster2026!")


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=API_URL, timeout=15) as c:
        yield c


@pytest.fixture(scope="module")
def auth_token(client):
    res = client.post("/api/auth/login", json={"email": MASTER_EMAIL, "password": MASTER_PASS})
    assert res.status_code == 200, f"Login failed: {res.text}"
    data = res.json()
    assert "token" in data, "No token in login response"
    return data["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ═══════════════════════════════════════════════════════
#  1. AUTENTICACION
# ═══════════════════════════════════════════════════════

class TestAuth:
    def test_login_correcto(self, client):
        res = client.post("/api/auth/login", json={"email": MASTER_EMAIL, "password": MASTER_PASS})
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert data["user"]["email"] == MASTER_EMAIL

    def test_login_password_incorrecta(self, client):
        res = client.post("/api/auth/login", json={"email": "test_wrong_pw@fake.com", "password": "wrong"})
        assert res.status_code in (401, 403, 429)

    def test_login_email_inexistente(self, client):
        res = client.post("/api/auth/login", json={"email": "noexiste_test@fake.com", "password": "x"})
        assert res.status_code in (401, 404, 429)

    def test_endpoint_protegido_sin_token(self, client):
        res = client.get("/api/liquidaciones/pendientes")
        assert res.status_code in (401, 403, 422)

    def test_token_invalido(self, client):
        res = client.get("/api/liquidaciones/pendientes", headers={"Authorization": "Bearer invalidtoken123"})
        assert res.status_code in (401, 403)


# ═══════════════════════════════════════════════════════
#  2. ORDENES
# ═══════════════════════════════════════════════════════

class TestOrdenes:
    def test_listar_ordenes(self, client, auth_headers):
        res = client.get("/api/ordenes?page=1&limit=5", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, (list, dict))

    def test_orden_detalle(self, client, auth_headers):
        # Get first order
        res = client.get("/api/ordenes?page=1&limit=1", headers=auth_headers)
        data = res.json()
        ordenes = data if isinstance(data, list) else data.get("ordenes", [data])
        if ordenes:
            orden_id = ordenes[0]["id"]
            res2 = client.get(f"/api/ordenes/{orden_id}", headers=auth_headers)
            assert res2.status_code == 200

    def test_orden_inexistente(self, client, auth_headers):
        res = client.get("/api/ordenes/id-que-no-existe-99999", headers=auth_headers)
        assert res.status_code == 404

    def test_link_seguimiento(self, client, auth_headers):
        res = client.get("/api/ordenes?page=1&limit=1", headers=auth_headers)
        data = res.json()
        ordenes = data if isinstance(data, list) else data.get("ordenes", [data])
        if ordenes:
            oid = ordenes[0]["id"]
            res2 = client.get(f"/api/ordenes/{oid}/link-seguimiento", headers=auth_headers)
            assert res2.status_code == 200
            link = res2.json()
            assert "token" in link
            assert link["token"]  # Not empty


# ═══════════════════════════════════════════════════════
#  3. DASHBOARD Y METRICAS
# ═══════════════════════════════════════════════════════

class TestDashboard:
    def test_dashboard_stats(self, client, auth_headers):
        res = client.get("/api/dashboard/stats", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "total_ordenes" in data
        assert data["total_ordenes"] >= 0

    def test_analiticas(self, client, auth_headers):
        res = client.get("/api/master/analiticas?periodo=30d", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "total_ordenes" in data


# ═══════════════════════════════════════════════════════
#  4. CLIENTES
# ═══════════════════════════════════════════════════════

class TestClientes:
    def test_listar_clientes(self, client, auth_headers):
        res = client.get("/api/clientes", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)

    def test_buscar_cliente(self, client, auth_headers):
        res = client.get("/api/clientes?search=a", headers=auth_headers)
        assert res.status_code == 200


# ═══════════════════════════════════════════════════════
#  5. LIQUIDACIONES
# ═══════════════════════════════════════════════════════

class TestLiquidaciones:
    def test_pendientes(self, client, auth_headers):
        res = client.get("/api/liquidaciones/pendientes", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "pendientes" in data
        assert "resumen" in data
        assert "total_pendientes" in data["resumen"]

    def test_no_duplicados_autorizacion(self, client, auth_headers):
        res = client.get("/api/liquidaciones/pendientes", headers=auth_headers)
        data = res.json()
        all_items = data["pendientes"] + data.get("pagados", []) + data.get("garantias_abiertas", [])
        codigos = [i["codigo_siniestro"] for i in all_items]
        assert len(codigos) == len(set(codigos)), f"Duplicados encontrados: {[c for c in codigos if codigos.count(c) > 1]}"


# ═══════════════════════════════════════════════════════
#  6. IMPRESION
# ═══════════════════════════════════════════════════════

class TestPrint:
    def test_print_status(self, client, auth_headers):
        res = client.get("/api/print/status", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "ok" in data
        assert "agent_connected" in data

    def test_print_send(self, client, auth_headers):
        res = client.post("/api/print/send", headers=auth_headers, json={
            "template": "ot_barcode_minimal",
            "data": {"barcodeValue": "TEST-PYTEST", "orderNumber": "OT-TEST", "deviceModel": "Test"},
        })
        assert res.status_code == 200
        data = res.json()
        assert data["ok"]
        assert "job_id" in data

    def test_print_agent_download(self, client):
        res = client.get("/api/print/agent/download")
        assert res.status_code == 200
        assert res.headers.get("content-type", "").startswith("application/")

    def test_print_pending_auth(self, client):
        # Sin agent_key debe fallar
        res = client.get("/api/print/pending?agent_key=wrong&agent_id=test")
        assert res.status_code == 403


# ═══════════════════════════════════════════════════════
#  7. SEGUIMIENTO PUBLICO
# ═══════════════════════════════════════════════════════

class TestSeguimiento:
    def test_verificar_token_invalido(self, client):
        res = client.post("/api/seguimiento/verificar", json={"token": "NOEXISTE", "telefono": "000000"})
        assert res.status_code in (401, 404)

    def test_verificar_telefono_incorrecto(self, client):
        res = client.post("/api/seguimiento/verificar", json={"token": "008D7E46-FD6", "telefono": "000000"})
        # Token exists but phone wrong
        assert res.status_code in (401, 404)


# ═══════════════════════════════════════════════════════
#  8. URLS DE PRODUCCION
# ═══════════════════════════════════════════════════════

class TestURLs:
    """Verifica que ningun email/link apunte a preview."""

    def test_frontend_url_config(self):
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
        import config as cfg
        assert "preview" not in cfg.FRONTEND_URL, f"FRONTEND_URL apunta a preview: {cfg.FRONTEND_URL}"
        assert "emergentagent" not in cfg.FRONTEND_URL, f"FRONTEND_URL apunta a emergentagent: {cfg.FRONTEND_URL}"
        assert "revix.es" in cfg.FRONTEND_URL

    def test_no_preview_urls_in_helpers(self):
        helpers_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "helpers.py")
        with open(helpers_path) as f:
            content = f.read()
        assert "preview.emergentagent" not in content, "helpers.py contiene URL de preview"

    def test_no_preview_urls_in_routes(self):
        routes_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "routes")
        for fname in os.listdir(routes_dir):
            if fname.endswith(".py"):
                with open(os.path.join(routes_dir, fname)) as f:
                    content = f.read()
                # Skip test files and mobilesentrix (uses REACT_APP_BACKEND_URL for OAuth callback)
                if "test" in fname or "mobilesentrix" in fname:
                    continue
                assert "preview.emergentagent" not in content, f"{fname} contiene URL de preview"

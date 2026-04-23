"""
Tests for GLS tracking URL update, MRW integration, and Triador UI endpoint.

Features tested:
- GLS tracking URL format: https://mygls.gls-spain.es/e/{codexp}/{codplaza_dst}
- MRW endpoints: crear-envio, tracking, recogida, config
- Triador diagnostico endpoint: /api/ordenes/{id}/triador-diagnostico
- Panel resumen counts GLS + MRW
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_EMAIL = "master@revix.es"
TEST_PASSWORD = "RevixMaster2026!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user."""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    })
    if resp.status_code != 200:
        pytest.skip(f"Auth failed: {resp.status_code} - {resp.text[:200]}")
    return resp.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


# ═══════════════════════════════════════════════════════════════════════════════
# GLS Tracking URL Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestGLSTrackingURL:
    """Test GLS tracking URL format: mygls.gls-spain.es/e/{codexp}/{codplaza_dst}"""

    def test_gls_crear_envio_returns_mygls_url(self, auth_headers):
        """POST /api/logistica/gls/crear-envio returns tracking_url with mygls format."""
        # First get an order to create envio for
        resp = requests.get(f"{BASE_URL}/api/ordenes", headers=auth_headers, params={"page_size": 5})
        assert resp.status_code == 200
        data = resp.json()
        ordenes = data if isinstance(data, list) else data.get("items") or data.get("ordenes") or []
        if not ordenes:
            pytest.skip("No orders available for testing")
        
        # Find an order without GLS envio or use force_duplicate
        orden = ordenes[0]
        order_id = orden.get("id")
        
        # Create GLS envio with force_duplicate
        resp = requests.post(f"{BASE_URL}/api/logistica/gls/crear-envio", headers=auth_headers, json={
            "order_id": order_id,
            "peso_kg": 0.5,
            "force_duplicate": True,
            "dest_direccion": "Calle Test 123",
            "dest_cp": "28001",
        })
        
        if resp.status_code == 400 and "incompleto" in resp.text.lower():
            pytest.skip("Order missing required destination data")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        
        # Verify response structure
        assert data.get("success") is True
        assert "codbarras" in data
        assert "tracking_url" in data
        
        # Verify tracking URL format is mygls
        tracking_url = data["tracking_url"]
        assert "mygls.gls-spain.es/e/" in tracking_url, f"Expected mygls format, got: {tracking_url}"
        
        # URL should have format: https://mygls.gls-spain.es/e/{codexp}/{codplaza_dst}
        parts = tracking_url.split("/e/")
        assert len(parts) == 2, f"Invalid mygls URL format: {tracking_url}"
        path_parts = parts[1].split("/")
        assert len(path_parts) >= 2, f"Missing codexp/codplaza in URL: {tracking_url}"

    def test_gls_orden_detail_returns_mygls_url(self, auth_headers):
        """GET /api/logistica/gls/orden/{id} returns tracking_url with mygls format for new envios."""
        # Get orders with GLS envios
        resp = requests.get(f"{BASE_URL}/api/ordenes", headers=auth_headers, params={"page_size": 20})
        assert resp.status_code == 200
        data = resp.json()
        ordenes = data if isinstance(data, list) else data.get("items") or data.get("ordenes") or []
        
        # Find order with gls_envios
        orden_with_gls = None
        for o in ordenes:
            if o.get("gls_envios"):
                orden_with_gls = o
                break
        
        if not orden_with_gls:
            pytest.skip("No orders with GLS envios found")
        
        order_id = orden_with_gls["id"]
        resp = requests.get(f"{BASE_URL}/api/logistica/gls/orden/{order_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        
        assert "envios" in data
        if data["envios"]:
            envio = data["envios"][-1]  # Latest envio
            tracking_url = envio.get("tracking_url", "")
            # New envios should have mygls format
            if envio.get("codexp") and envio.get("codplaza_dst"):
                assert "mygls.gls-spain.es/e/" in tracking_url, f"Expected mygls format: {tracking_url}"


# ═══════════════════════════════════════════════════════════════════════════════
# MRW Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestMRWConfig:
    """Test MRW configuration endpoints."""

    def test_mrw_config_get(self, auth_headers):
        """GET /api/logistica/config/mrw returns config with preview/production status."""
        resp = requests.get(f"{BASE_URL}/api/logistica/config/mrw", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        
        # Verify response structure
        assert "entorno" in data
        assert data["entorno"] in ("preview", "production")
        assert "franquicia_masked" in data
        assert "abonado_masked" in data
        assert "usuario_masked" in data
        assert "credenciales_set" in data
        assert "remitente" in data
        assert "remitente_source" in data
        assert "stats_mes" in data
        assert "ultimo_envio" in data

    def test_mrw_config_remitente_save(self, auth_headers):
        """POST /api/logistica/config/mrw/remitente persists in BD and marks source=bd."""
        remitente_data = {
            "nombre": "TEST REVIX MRW",
            "direccion": "Calle Test MRW 123",
            "poblacion": "Madrid",
            "provincia": "Madrid",
            "cp": "28001",
            "telefono": "912345678",
        }
        resp = requests.post(f"{BASE_URL}/api/logistica/config/mrw/remitente", 
                            headers=auth_headers, json=remitente_data)
        assert resp.status_code == 200
        data = resp.json()
        
        # Verify remitente was saved
        assert data["remitente"]["nombre"] == "TEST REVIX MRW"
        assert data["remitente"]["direccion"] == "Calle Test MRW 123"
        
        # Verify source is marked as 'bd'
        assert data["remitente_source"]["nombre"] == "bd"
        assert data["remitente_source"]["direccion"] == "bd"

    def test_mrw_config_verify_preview(self, auth_headers):
        """POST /api/logistica/config/mrw/verify in preview returns ok=true."""
        resp = requests.post(f"{BASE_URL}/api/logistica/config/mrw/verify", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        
        # In preview mode, should return ok=true
        assert "ok" in data
        assert "preview" in data
        assert "mensaje" in data
        
        if data["preview"]:
            assert data["ok"] is True


class TestMRWEnvio:
    """Test MRW envio creation and tracking."""

    def test_mrw_crear_envio_preview(self, auth_headers):
        """POST /api/logistica/mrw/crear-envio in preview generates M+12 digits num_envio."""
        # Get an order
        resp = requests.get(f"{BASE_URL}/api/ordenes", headers=auth_headers, params={"page_size": 5})
        assert resp.status_code == 200
        data = resp.json()
        ordenes = data if isinstance(data, list) else data.get("items") or data.get("ordenes") or []
        if not ordenes:
            pytest.skip("No orders available")
        
        order_id = ordenes[0]["id"]
        
        resp = requests.post(f"{BASE_URL}/api/logistica/mrw/crear-envio", headers=auth_headers, json={
            "order_id": order_id,
            "peso_kg": 0.5,
            "observaciones": "Test MRW envio",
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        
        # Verify response
        assert data.get("success") is True
        assert "num_envio" in data
        
        # num_envio should start with M and have 12 chars total
        num_envio = data["num_envio"]
        assert num_envio.startswith("M"), f"num_envio should start with M: {num_envio}"
        assert len(num_envio) == 12, f"num_envio should be 12 chars: {num_envio}"
        
        # Verify tracking URL format
        tracking_url = data.get("tracking_url", "")
        assert "mrw.es/seguimiento_envios/Tracking.asp" in tracking_url
        assert f"numeroEnvio={num_envio}" in tracking_url
        
        # Verify mock_preview flag
        assert data.get("mock_preview") is True

    def test_mrw_orden_detail(self, auth_headers):
        """GET /api/logistica/mrw/orden/{id} lists MRW envios with estado_actual, tracking_url."""
        # Get orders with MRW envios
        resp = requests.get(f"{BASE_URL}/api/ordenes", headers=auth_headers, params={"page_size": 20})
        assert resp.status_code == 200
        data = resp.json()
        ordenes = data if isinstance(data, list) else data.get("items") or data.get("ordenes") or []
        
        orden_with_mrw = None
        for o in ordenes:
            if o.get("mrw_envios"):
                orden_with_mrw = o
                break
        
        if not orden_with_mrw:
            pytest.skip("No orders with MRW envios found")
        
        order_id = orden_with_mrw["id"]
        resp = requests.get(f"{BASE_URL}/api/logistica/mrw/orden/{order_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        
        assert "envios" in data
        assert len(data["envios"]) > 0
        
        envio = data["envios"][0]
        assert "num_envio" in envio
        assert "estado" in envio or "estado_actual" in envio
        assert "tracking_url" in envio

    def test_mrw_actualizar_tracking_preview(self, auth_headers):
        """POST /api/logistica/mrw/actualizar-tracking/{num_envio} updates estado in preview."""
        # First create an envio to get a num_envio
        resp = requests.get(f"{BASE_URL}/api/ordenes", headers=auth_headers, params={"page_size": 5})
        data = resp.json()
        ordenes = data if isinstance(data, list) else data.get("items") or data.get("ordenes") or []
        if not ordenes:
            pytest.skip("No orders available")
        
        # Find order with MRW envio
        num_envio = None
        for o in ordenes:
            for env in (o.get("mrw_envios") or []):
                if env.get("num_envio"):
                    num_envio = env["num_envio"]
                    break
            if num_envio:
                break
        
        if not num_envio:
            pytest.skip("No MRW envios found")
        
        resp = requests.post(f"{BASE_URL}/api/logistica/mrw/actualizar-tracking/{num_envio}", 
                            headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        
        assert data.get("success") is True
        assert data.get("num_envio") == num_envio
        assert "estado_actual" in data
        assert "estado_codigo" in data


class TestMRWRecogida:
    """Test MRW recogida (pickup) functionality."""

    def test_mrw_solicitar_recogida(self, auth_headers):
        """POST /api/logistica/mrw/solicitar-recogida creates doc with estado=pendiente."""
        resp = requests.post(f"{BASE_URL}/api/logistica/mrw/solicitar-recogida", headers=auth_headers, json={
            "fecha_recogida": "2026-01-25",
            "peso_total_kg": 2.5,
            "num_bultos": 3,
            "observaciones": "Test recogida MRW",
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        
        assert data.get("success") is True
        assert "num_recogida" in data
        
        # num_recogida should start with R
        num_recogida = data["num_recogida"]
        assert num_recogida.startswith("R"), f"num_recogida should start with R: {num_recogida}"
        
        assert data.get("fecha_recogida") == "2026-01-25"
        assert "tracking_url" in data


# ═══════════════════════════════════════════════════════════════════════════════
# Panel Resumen Tests (GLS + MRW counts)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPanelResumen:
    """Test panel resumen counts GLS + MRW correctly."""

    def test_panel_resumen_counts_both_transportistas(self, auth_headers):
        """GET /api/logistica/panel/resumen counts envíos GLS + MRW + recogidas_pendientes."""
        resp = requests.get(f"{BASE_URL}/api/logistica/panel/resumen", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        
        # Verify all expected fields
        assert "envios_activos" in data
        assert "entregados_hoy" in data
        assert "incidencias_activas" in data
        assert "recogidas_pendientes" in data
        assert "total_envios_mes" in data
        
        # Values should be integers >= 0
        assert isinstance(data["envios_activos"], int)
        assert isinstance(data["total_envios_mes"], int)
        assert isinstance(data["recogidas_pendientes"], int)

    def test_panel_envios_filter_mrw(self, auth_headers):
        """GET /api/logistica/panel/envios?transportista=MRW filters only MRW."""
        resp = requests.get(f"{BASE_URL}/api/logistica/panel/envios", headers=auth_headers, 
                           params={"transportista": "MRW"})
        assert resp.status_code == 200
        data = resp.json()
        
        assert "items" in data
        # All items should be MRW
        for item in data["items"]:
            assert item.get("transportista") == "MRW", f"Expected MRW, got {item.get('transportista')}"

    def test_panel_envios_filter_gls(self, auth_headers):
        """GET /api/logistica/panel/envios?transportista=GLS filters only GLS."""
        resp = requests.get(f"{BASE_URL}/api/logistica/panel/envios", headers=auth_headers, 
                           params={"transportista": "GLS"})
        assert resp.status_code == 200
        data = resp.json()
        
        assert "items" in data
        # All items should be GLS
        for item in data["items"]:
            assert item.get("transportista") == "GLS", f"Expected GLS, got {item.get('transportista')}"


# ═══════════════════════════════════════════════════════════════════════════════
# Triador Diagnostico Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestTriadorDiagnostico:
    """Test triador-diagnostico endpoint that chains 3 tools."""

    def test_triador_sin_averia_returns_error(self, auth_headers):
        """POST /api/ordenes/{id}/triador-diagnostico without averia returns success=false."""
        # Get an order without averia_descripcion
        resp = requests.get(f"{BASE_URL}/api/ordenes", headers=auth_headers, params={"page_size": 20})
        assert resp.status_code == 200
        data = resp.json()
        ordenes = data if isinstance(data, list) else data.get("items") or data.get("ordenes") or []
        
        orden_sin_averia = None
        for o in ordenes:
            if not o.get("averia_descripcion") and not o.get("problema_reportado") and not o.get("diagnostico_tecnico"):
                orden_sin_averia = o
                break
        
        if not orden_sin_averia:
            pytest.skip("All orders have averia descriptions")
        
        order_id = orden_sin_averia["id"]
        resp = requests.post(f"{BASE_URL}/api/ordenes/{order_id}/triador-diagnostico", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        
        assert "diagnostico" in data
        assert data["diagnostico"].get("success") is False
        assert data["diagnostico"].get("error") == "sin_averia_descripcion"

    def test_triador_con_averia_returns_diagnostico(self, auth_headers):
        """POST /api/ordenes/{id}/triador-diagnostico with averia returns full diagnostico."""
        # Get an order with averia_descripcion
        resp = requests.get(f"{BASE_URL}/api/ordenes", headers=auth_headers, params={"page_size": 20})
        assert resp.status_code == 200
        data = resp.json()
        ordenes = data if isinstance(data, list) else data.get("items") or data.get("ordenes") or []
        
        orden_con_averia = None
        for o in ordenes:
            averia = o.get("averia_descripcion") or o.get("problema_reportado") or o.get("diagnostico_tecnico")
            if averia and len(averia) > 5:
                orden_con_averia = o
                break
        
        if not orden_con_averia:
            pytest.skip("No orders with averia descriptions found")
        
        order_id = orden_con_averia["id"]
        resp = requests.post(f"{BASE_URL}/api/ordenes/{order_id}/triador-diagnostico", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        
        # Verify response structure
        assert "order_id" in data
        assert "numero_orden" in data
        assert "diagnostico" in data
        assert "preview" in data
        
        diag = data["diagnostico"]
        assert "success" in diag
        
        if diag.get("diagnostico_match"):
            # If match found, verify full structure
            assert "causas_probables" in diag
            assert "tipo_reparacion_sugerido" in diag
            assert "confianza_global" in diag
            assert diag["confianza_global"] >= 0
            
            # Should also have repuestos and tecnico sections
            if data.get("repuestos"):
                assert "sugerencias" in data["repuestos"]
                assert "veredicto" in data["repuestos"]
            
            if data.get("tecnico"):
                assert "recomendado" in data["tecnico"]
                assert "ranking" in data["tecnico"]

    def test_triador_pantalla_rota_high_confidence(self, auth_headers):
        """Test triador with 'pantalla rota' returns high confidence match."""
        # Find order with pantalla-related averia or update one
        resp = requests.get(f"{BASE_URL}/api/ordenes", headers=auth_headers, params={"page_size": 20})
        data = resp.json()
        ordenes = data if isinstance(data, list) else data.get("items") or data.get("ordenes") or []
        
        orden_pantalla = None
        for o in ordenes:
            averia = (o.get("averia_descripcion") or "").lower()
            if "pantalla" in averia:
                orden_pantalla = o
                break
        
        if not orden_pantalla:
            pytest.skip("No orders with 'pantalla' in averia found")
        
        order_id = orden_pantalla["id"]
        resp = requests.post(f"{BASE_URL}/api/ordenes/{order_id}/triador-diagnostico", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        
        diag = data["diagnostico"]
        if diag.get("diagnostico_match"):
            # Pantalla should have high confidence
            assert diag.get("confianza_global", 0) >= 0.5
            assert diag.get("tipo_reparacion_sugerido") == "pantalla"


# ═══════════════════════════════════════════════════════════════════════════════
# Email Tracking URL Test (ordenes_routes.py line 3703)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmailTrackingURL:
    """Test that email uses mygls URL when codexp/codplaza available."""

    def test_gls_envio_stores_codexp_codplaza(self, auth_headers):
        """Verify GLS envio stores codexp and codplaza_dst in BD."""
        # Get orders with GLS envios
        resp = requests.get(f"{BASE_URL}/api/ordenes", headers=auth_headers, params={"page_size": 20})
        data = resp.json()
        ordenes = data if isinstance(data, list) else data.get("items") or data.get("ordenes") or []
        
        for o in ordenes:
            for env in (o.get("gls_envios") or []):
                if env.get("codexp") and env.get("codplaza_dst"):
                    # Found envio with both fields
                    assert len(env["codexp"]) > 0
                    assert len(env["codplaza_dst"]) > 0
                    
                    # Verify tracking_url uses mygls format
                    tracking_url = env.get("tracking_url", "")
                    if tracking_url:
                        assert "mygls.gls-spain.es/e/" in tracking_url
                    return
        
        pytest.skip("No GLS envios with codexp/codplaza_dst found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

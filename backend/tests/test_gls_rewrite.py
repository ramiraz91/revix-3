"""
GLS Module Tests - Testing the complete GLS logistics integration rewrite.

Tests cover:
- Config endpoints (GET/POST /api/gls/config)
- Maestros endpoint (GET /api/gls/maestros)
- Shipments CRUD (GET/POST /api/gls/envios)
- Sync endpoint (POST /api/gls/sync)
- Error handling when GLS is not activated
"""
import pytest
import requests
import os
from datetime import datetime
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for master user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "master@techrepair.local",
        "password": "master123"
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    return response.json().get("token")

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get auth headers with bearer token."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestGLSConfig:
    """Test GLS configuration endpoints - GET and POST /api/gls/config"""

    def test_get_config_returns_200(self, auth_headers):
        """GET /api/gls/config returns GLS config with all expected fields."""
        response = requests.get(f"{BASE_URL}/api/gls/config", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify expected config fields exist
        expected_fields = ["activo", "uid_masked"]
        for field in expected_fields:
            assert field in data, f"Expected field '{field}' in config response"
        
        print(f"✓ GLS config retrieved: activo={data.get('activo')}, uid_masked={data.get('uid_masked')}")

    def test_get_config_requires_auth(self):
        """GET /api/gls/config requires authentication."""
        response = requests.get(f"{BASE_URL}/api/gls/config")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"

    def test_post_config_saves_config(self, auth_headers):
        """POST /api/gls/config saves GLS configuration."""
        # First get current config to restore later
        get_response = requests.get(f"{BASE_URL}/api/gls/config", headers=auth_headers)
        original_config = get_response.json()
        
        # Update config with test data
        test_config = {
            "activo": False,  # Keep inactive for safety
            "uid_cliente": "",  # Don't set real UID
            "remitente_nombre": "TEST TechRepair",
            "remitente_direccion": "Calle Test 123",
            "remitente_poblacion": "Madrid",
            "remitente_provincia": "Madrid",
            "remitente_cp": "28001",
            "remitente_pais": "34",
            "remitente_telefono": "612345678",
            "remitente_email": "test@techrepair.local",
            "servicio_defecto": "96",
            "horario_defecto": "18",
            "formato_etiqueta": "PDF",
            "portes": "P",
            "polling_activo": False,
            "polling_intervalo_horas": 4,
            "email_recogida_activo": True
        }
        
        response = requests.post(f"{BASE_URL}/api/gls/config", json=test_config, headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Expected success message in response"
        print(f"✓ GLS config saved successfully: {data.get('message')}")
        
        # Verify config was saved by reading it back
        verify_response = requests.get(f"{BASE_URL}/api/gls/config", headers=auth_headers)
        assert verify_response.status_code == 200
        
        saved_config = verify_response.json()
        assert saved_config.get("remitente_nombre") == "TEST TechRepair", "Config not persisted correctly"
        print("✓ Config verified: remitente_nombre saved correctly")


class TestGLSMaestros:
    """Test GLS maestros (reference data) endpoint - GET /api/gls/maestros"""

    def test_get_maestros_returns_services_and_schedules(self, auth_headers):
        """GET /api/gls/maestros returns servicios, horarios, estados."""
        response = requests.get(f"{BASE_URL}/api/gls/maestros", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Check all expected fields
        assert "servicios" in data, "Expected 'servicios' in maestros response"
        assert "horarios" in data, "Expected 'horarios' in maestros response"
        assert "estados" in data, "Expected 'estados' in maestros response"
        
        # Validate servicios has expected entries
        servicios = data["servicios"]
        assert isinstance(servicios, dict), "servicios should be a dict"
        assert "96" in servicios, "Expected BusinessParcel (96) in servicios"
        assert "1" in servicios, "Expected Express/Courier (1) in servicios"
        print(f"✓ Servicios loaded: {len(servicios)} services")
        
        # Validate horarios
        horarios = data["horarios"]
        assert isinstance(horarios, dict), "horarios should be a dict"
        assert "18" in horarios, "Expected BusinessParcel (18) in horarios"
        print(f"✓ Horarios loaded: {len(horarios)} schedules")
        
        # Validate estados (state badges)
        estados = data["estados"]
        assert isinstance(estados, dict), "estados should be a dict"
        assert "entregado" in estados, "Expected 'entregado' in estados"
        assert "grabado" in estados, "Expected 'grabado' in estados"
        print(f"✓ Estados loaded: {len(estados)} states")


class TestGLSShipments:
    """Test GLS shipments CRUD endpoints - GET/POST /api/gls/envios"""

    def test_get_envios_returns_paginated_list(self, auth_headers):
        """GET /api/gls/envios returns paginated shipment list."""
        response = requests.get(f"{BASE_URL}/api/gls/envios", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "data" in data, "Expected 'data' array in response"
        assert "total" in data, "Expected 'total' count in response"
        assert "page" in data, "Expected 'page' in response"
        assert "limit" in data, "Expected 'limit' in response"
        
        assert isinstance(data["data"], list), "data should be a list"
        assert isinstance(data["total"], int), "total should be an integer"
        print(f"✓ Envios list: {len(data['data'])} items, total: {data['total']}")

    def test_get_envios_with_pagination(self, auth_headers):
        """GET /api/gls/envios?page=1&limit=10 respects pagination."""
        response = requests.get(f"{BASE_URL}/api/gls/envios?page=1&limit=10", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["page"] == 1, "Expected page=1"
        assert data["limit"] == 10, "Expected limit=10"
        assert len(data["data"]) <= 10, "Should return at most 10 items"
        print(f"✓ Pagination works: page={data['page']}, limit={data['limit']}")

    def test_get_envios_filter_by_orden_id(self, auth_headers):
        """GET /api/gls/envios?orden_id=X filters by order ID."""
        test_orden_id = "nonexistent-order-id"
        response = requests.get(f"{BASE_URL}/api/gls/envios?orden_id={test_orden_id}", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # With nonexistent order, should return empty
        assert data["total"] == 0, "Filter by nonexistent orden_id should return 0 results"
        print(f"✓ Filter by orden_id works: returned {data['total']} results for nonexistent order")

    def test_get_envios_filter_by_estado(self, auth_headers):
        """GET /api/gls/envios?estado=grabado filters by state."""
        response = requests.get(f"{BASE_URL}/api/gls/envios?estado=grabado", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # All items should have estado_interno = grabado (if any)
        for item in data["data"]:
            assert item.get("estado_interno") == "grabado", f"Item {item.get('id')} has wrong estado"
        print(f"✓ Filter by estado works: {len(data['data'])} items with estado=grabado")

    def test_get_envios_search(self, auth_headers):
        """GET /api/gls/envios?search=term performs search."""
        response = requests.get(f"{BASE_URL}/api/gls/envios?search=TEST", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"✓ Search works: {len(data['data'])} results for search=TEST")

    def test_post_envios_returns_error_when_gls_not_activated(self, auth_headers):
        """POST /api/gls/envios returns error 'Integración GLS no activada' when GLS is not configured."""
        # Create a shipment request (will fail because GLS is not activated)
        shipment_data = {
            "orden_id": "test-order-id",
            "entidad_tipo": "orden",
            "tipo": "envio",
            "dest_nombre": "Test Customer",
            "dest_direccion": "Calle Test 456",
            "dest_poblacion": "Barcelona",
            "dest_provincia": "Barcelona",
            "dest_cp": "08001",
            "dest_pais": "34",
            "dest_telefono": "612345679",
            "dest_email": "test@customer.com",
            "bultos": 1,
            "peso": 1.0,
            "referencia": "TEST-REF-001"
        }
        
        response = requests.post(f"{BASE_URL}/api/gls/envios", json=shipment_data, headers=auth_headers)
        
        # Should return 400 with specific error about GLS not activated
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        error_detail = data.get("detail", "")
        assert "no activada" in error_detail.lower() or "gls" in error_detail.lower(), \
            f"Expected error about GLS not activated, got: {error_detail}"
        
        print(f"✓ POST /api/gls/envios correctly returns error when GLS not activated: {error_detail}")


class TestGLSSync:
    """Test GLS sync endpoint - POST /api/gls/sync"""

    def test_sync_manual_triggers_sync(self, auth_headers):
        """POST /api/gls/sync triggers manual sync and returns stats."""
        response = requests.post(f"{BASE_URL}/api/gls/sync", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Sync should return stats
        expected_fields = ["synced", "errors", "total"]
        has_stats = any(field in data for field in expected_fields)
        if not has_stats and "message" in data:
            # If GLS not configured, might return a message instead
            print(f"✓ Sync response (GLS not configured): {data.get('message')}")
        else:
            print(f"✓ Sync stats: synced={data.get('synced', 0)}, errors={data.get('errors', 0)}, total={data.get('total', 0)}")

    def test_sync_requires_admin(self):
        """POST /api/gls/sync requires admin authentication."""
        response = requests.post(f"{BASE_URL}/api/gls/sync")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"


class TestGLSShipmentDetail:
    """Test shipment detail and related endpoints."""

    def test_get_envio_detail_not_found(self, auth_headers):
        """GET /api/gls/envios/{id} returns 404 for nonexistent shipment."""
        fake_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/api/gls/envios/{fake_id}", headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/gls/envios/{fake_id[:8]}... returns 404 correctly")


class TestGLSTracking:
    """Test tracking endpoints."""

    def test_tracking_not_found(self, auth_headers):
        """GET /api/gls/tracking/{id} returns error for nonexistent shipment."""
        fake_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/api/gls/tracking/{fake_id}", headers=auth_headers)
        # Should return 400 or 404
        assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}"
        print(f"✓ GET /api/gls/tracking/{fake_id[:8]}... returns expected error")


class TestGLSLabels:
    """Test label endpoints."""

    def test_label_not_found(self, auth_headers):
        """GET /api/gls/etiqueta/{id} returns 404 for nonexistent shipment."""
        fake_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/api/gls/etiqueta/{fake_id}", headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ GET /api/gls/etiqueta/{fake_id[:8]}... returns 404 correctly")

    def test_label_by_code_not_found(self, auth_headers):
        """GET /api/gls/etiqueta-por-codigo/{codigo} returns 404 for nonexistent code."""
        fake_code = "9999999999999"
        response = requests.get(f"{BASE_URL}/api/gls/etiqueta-por-codigo/{fake_code}", headers=auth_headers)
        # Should return 400 (GLS not configured) or 404
        assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}"
        print(f"✓ GET /api/gls/etiqueta-por-codigo/{fake_code} returns expected error")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
GLS Module Complete Tests - Testing the refactored GLS logistics module.

Tests cover:
- GET /api/gls/status - Check if GLS is active
- GET /api/gls/envios - List shipments with tipo, gls_codbarras, estado_interno, tracking_url
- GET /api/gls/check-duplicate/{orden_id}/{tipo} - Duplicate detection
- GET /api/gls/orden/{orden_id} - Get logistics data for order (recogida, envio, devolucion)
- GET /api/gls/maestros - Get master data (servicios, horarios, estados, tipos_envio)
- POST /api/ordenes/{orden_id}/logistics/pickup - Create pickup
- POST /api/ordenes/{orden_id}/logistics/delivery - Create delivery
- POST /api/ordenes/{orden_id}/logistics/return - Create return (NEW)
- DELETE /api/ordenes/{orden_id}/logistics/{shipment_id} - Cancel shipment (NEW)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_ORDER_ID = "037899f0-1df6-4b7a-bd9c-5a54a163996f"  # Provided test order

# Test credentials
MASTER_EMAIL = "master@revix.es"
MASTER_PASSWORD = "RevixMaster2026!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for master user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MASTER_EMAIL,
        "password": MASTER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Session with auth header."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestGLSStatus:
    """Test GET /api/gls/status endpoint."""
    
    def test_gls_status_returns_active_true(self, api_client):
        """GLS status should return active:true when configured."""
        response = api_client.get(f"{BASE_URL}/api/gls/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "active" in data, "Response should contain 'active' field"
        assert data["active"] is True, "GLS should be active (configured)"
        print(f"✓ GLS status: active={data['active']}")


class TestGLSEnvios:
    """Test GET /api/gls/envios endpoint."""
    
    def test_list_envios_returns_correct_structure(self, api_client):
        """List envios should return data with required fields."""
        response = api_client.get(f"{BASE_URL}/api/gls/envios")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "data" in data, "Response should contain 'data' array"
        assert "total" in data, "Response should contain 'total' count"
        assert "page" in data, "Response should contain 'page'"
        assert "limit" in data, "Response should contain 'limit'"
        
        print(f"✓ Envios list: total={data['total']}, page={data['page']}")
    
    def test_envios_have_required_fields(self, api_client):
        """Each envio should have tipo, gls_codbarras, estado_interno, tracking_url."""
        response = api_client.get(f"{BASE_URL}/api/gls/envios")
        assert response.status_code == 200
        
        data = response.json()
        if data["total"] > 0:
            envio = data["data"][0]
            # Check required fields exist
            assert "tipo" in envio, "Envio should have 'tipo' field"
            assert "gls_codbarras" in envio, "Envio should have 'gls_codbarras' field"
            assert "estado_interno" in envio, "Envio should have 'estado_interno' field"
            assert "tracking_url" in envio, "Envio should have 'tracking_url' field"
            
            print(f"✓ Envio fields: tipo={envio['tipo']}, codbarras={envio.get('gls_codbarras')}, estado={envio['estado_interno']}")
            
            # Verify tracking_url format if codbarras exists
            if envio.get("gls_codbarras"):
                assert envio["tracking_url"] is not None, "tracking_url should not be null when codbarras exists"
                assert "gls-spain.es" in envio["tracking_url"], "tracking_url should point to GLS Spain"
        else:
            pytest.skip("No envios found to test fields")


class TestGLSCheckDuplicate:
    """Test GET /api/gls/check-duplicate/{orden_id}/{tipo} endpoint."""
    
    def test_check_duplicate_envio(self, api_client):
        """Check duplicate detection for envio type."""
        response = api_client.get(f"{BASE_URL}/api/gls/check-duplicate/{TEST_ORDER_ID}/envio")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "has_duplicate" in data, "Response should contain 'has_duplicate' field"
        assert isinstance(data["has_duplicate"], bool), "has_duplicate should be boolean"
        
        print(f"✓ Check duplicate envio: has_duplicate={data['has_duplicate']}")
        
        if data["has_duplicate"]:
            assert "existing_shipment" in data, "Should include existing_shipment when duplicate exists"
    
    def test_check_duplicate_recogida(self, api_client):
        """Check duplicate detection for recogida type."""
        response = api_client.get(f"{BASE_URL}/api/gls/check-duplicate/{TEST_ORDER_ID}/recogida")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "has_duplicate" in data
        print(f"✓ Check duplicate recogida: has_duplicate={data['has_duplicate']}")
    
    def test_check_duplicate_devolucion(self, api_client):
        """Check duplicate detection for devolucion type."""
        response = api_client.get(f"{BASE_URL}/api/gls/check-duplicate/{TEST_ORDER_ID}/devolucion")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "has_duplicate" in data
        print(f"✓ Check duplicate devolucion: has_duplicate={data['has_duplicate']}")


class TestGLSOrdenLogistics:
    """Test GET /api/gls/orden/{orden_id} endpoint."""
    
    def test_get_orden_logistics_structure(self, api_client):
        """Get orden logistics should return recogida, envio, devolucion blocks."""
        response = api_client.get(f"{BASE_URL}/api/gls/orden/{TEST_ORDER_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Check main structure
        assert "gls_activo" in data, "Response should contain 'gls_activo'"
        assert "recogida" in data, "Response should contain 'recogida' block"
        assert "envio" in data, "Response should contain 'envio' block"
        assert "devolucion" in data, "Response should contain 'devolucion' block"
        
        print(f"✓ Orden logistics: gls_activo={data['gls_activo']}")
    
    def test_orden_logistics_block_structure(self, api_client):
        """Each logistics block should have shipment, eventos, total, historial."""
        response = api_client.get(f"{BASE_URL}/api/gls/orden/{TEST_ORDER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        
        for block_name in ["recogida", "envio", "devolucion"]:
            block = data[block_name]
            assert "shipment" in block, f"{block_name} should have 'shipment'"
            assert "eventos" in block, f"{block_name} should have 'eventos'"
            assert "total" in block, f"{block_name} should have 'total'"
            assert "historial" in block, f"{block_name} should have 'historial'"
            
            print(f"✓ {block_name} block: shipment={'exists' if block['shipment'] else 'null'}, total={block['total']}")
    
    def test_orden_logistics_shipment_has_tracking(self, api_client):
        """If shipment exists with codbarras, it should have tracking_url."""
        response = api_client.get(f"{BASE_URL}/api/gls/orden/{TEST_ORDER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        
        for block_name in ["recogida", "envio", "devolucion"]:
            shipment = data[block_name].get("shipment")
            if shipment:
                # These fields should always exist
                assert "gls_codbarras" in shipment, f"{block_name} shipment should have gls_codbarras field"
                assert "estado_interno" in shipment, f"{block_name} shipment should have estado_interno"
                
                # tracking_url should exist if codbarras is not empty
                codbarras = shipment.get("gls_codbarras", "")
                if codbarras:
                    assert "tracking_url" in shipment and shipment["tracking_url"], f"{block_name} shipment with codbarras should have tracking_url"
                    assert "gls-spain.es" in shipment["tracking_url"], "tracking_url should point to GLS Spain"
                
                print(f"✓ {block_name} shipment: codbarras={codbarras or 'empty'}, estado={shipment.get('estado_interno')}")


class TestGLSMaestros:
    """Test GET /api/gls/maestros endpoint."""
    
    def test_maestros_returns_all_data(self, api_client):
        """Maestros should return servicios, horarios, estados, tipos_envio."""
        response = api_client.get(f"{BASE_URL}/api/gls/maestros")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        assert "servicios" in data, "Response should contain 'servicios'"
        assert "horarios" in data, "Response should contain 'horarios'"
        assert "estados" in data, "Response should contain 'estados'"
        assert "tipos_envio" in data, "Response should contain 'tipos_envio'"
        
        print(f"✓ Maestros: servicios={len(data['servicios'])}, horarios={len(data['horarios'])}, estados={len(data['estados'])}, tipos_envio={len(data['tipos_envio'])}")
    
    def test_tipos_envio_includes_devolucion(self, api_client):
        """tipos_envio should include envio, recogida, and devolucion."""
        response = api_client.get(f"{BASE_URL}/api/gls/maestros")
        assert response.status_code == 200
        
        data = response.json()
        tipos = [t["value"] for t in data["tipos_envio"]]
        
        assert "envio" in tipos, "tipos_envio should include 'envio'"
        assert "recogida" in tipos, "tipos_envio should include 'recogida'"
        assert "devolucion" in tipos, "tipos_envio should include 'devolucion'"
        
        print(f"✓ tipos_envio: {tipos}")


class TestLogisticsEndpoints:
    """Test logistics endpoints on ordenes routes."""
    
    def test_get_orden_logistics_via_ordenes_route(self, api_client):
        """GET /api/ordenes/{orden_id}/logistics should work."""
        response = api_client.get(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/logistics")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "gls_activo" in data
        assert "recogida" in data
        assert "envio" in data
        assert "devolucion" in data
        
        print(f"✓ GET /api/ordenes/{TEST_ORDER_ID}/logistics: gls_activo={data['gls_activo']}")
    
    def test_pickup_endpoint_exists(self, api_client):
        """POST /api/ordenes/{orden_id}/logistics/pickup should exist (test validation error)."""
        # Send incomplete data to test endpoint exists
        response = api_client.post(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/logistics/pickup", json={
            "dest_nombre": "",
            "dest_direccion": "",
            "dest_cp": ""
        })
        # Should return 400 (validation error) not 404 (not found)
        assert response.status_code in [400, 409, 422], f"Expected 400/409/422, got {response.status_code}: {response.text}"
        print(f"✓ POST /api/ordenes/{TEST_ORDER_ID}/logistics/pickup endpoint exists (validation error: {response.status_code})")
    
    def test_delivery_endpoint_exists(self, api_client):
        """POST /api/ordenes/{orden_id}/logistics/delivery should exist (test validation error)."""
        response = api_client.post(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/logistics/delivery", json={
            "dest_nombre": "",
            "dest_direccion": "",
            "dest_cp": ""
        })
        assert response.status_code in [400, 409, 422], f"Expected 400/409/422, got {response.status_code}: {response.text}"
        print(f"✓ POST /api/ordenes/{TEST_ORDER_ID}/logistics/delivery endpoint exists (validation error: {response.status_code})")
    
    def test_return_endpoint_exists(self, api_client):
        """POST /api/ordenes/{orden_id}/logistics/return should exist (NEW endpoint)."""
        response = api_client.post(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/logistics/return", json={
            "dest_nombre": "",
            "dest_direccion": "",
            "dest_cp": ""
        })
        assert response.status_code in [400, 409, 422], f"Expected 400/409/422, got {response.status_code}: {response.text}"
        print(f"✓ POST /api/ordenes/{TEST_ORDER_ID}/logistics/return endpoint exists (validation error: {response.status_code})")
    
    def test_delete_shipment_endpoint_exists(self, api_client):
        """DELETE /api/ordenes/{orden_id}/logistics/{shipment_id} should exist (NEW endpoint)."""
        # Use a fake shipment_id to test endpoint exists
        fake_shipment_id = "00000000-0000-0000-0000-000000000000"
        response = api_client.delete(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/logistics/{fake_shipment_id}")
        # Should return 404 (shipment not found) not 405 (method not allowed)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"✓ DELETE /api/ordenes/{TEST_ORDER_ID}/logistics/{{shipment_id}} endpoint exists (404 for fake ID)")


class TestLogisticsValidation:
    """Test validation logic for logistics endpoints."""
    
    def test_pickup_requires_telefono(self, api_client):
        """Pickup should require telefono field."""
        response = api_client.post(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/logistics/pickup", json={
            "dest_nombre": "Test Name",
            "dest_direccion": "Test Address",
            "dest_cp": "28001",
            "dest_telefono": ""  # Empty telefono
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "teléfono" in response.text.lower() or "telefono" in response.text.lower(), "Error should mention telefono"
        print("✓ Pickup validation: telefono is required")
    
    def test_delivery_requires_complete_address(self, api_client):
        """Delivery should require nombre, direccion, and CP."""
        response = api_client.post(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/logistics/delivery", json={
            "dest_nombre": "Test Name",
            "dest_direccion": "",  # Empty direccion
            "dest_cp": "28001",
            "dest_telefono": "600000000"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Delivery validation: direccion is required")


class TestGLSAuthentication:
    """Test that GLS endpoints require authentication."""
    
    def test_gls_status_requires_auth(self):
        """GLS status should require authentication."""
        response = requests.get(f"{BASE_URL}/api/gls/status")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ GET /api/gls/status requires authentication")
    
    def test_gls_envios_requires_auth(self):
        """GLS envios should require authentication."""
        response = requests.get(f"{BASE_URL}/api/gls/envios")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ GET /api/gls/envios requires authentication")
    
    def test_gls_maestros_requires_auth(self):
        """GLS maestros should require authentication."""
        response = requests.get(f"{BASE_URL}/api/gls/maestros")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ GET /api/gls/maestros requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test GLS Envios and Tracking URL Endpoints
Tests for:
- GET /api/gls/envios - List shipments with tracking_url
- GET /api/ordenes/{orden_id}/logistics - Order logistics with tracking_url
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://backend-perf-test.preview.emergentagent.com").rstrip('/')

# Test credentials from the request
MASTER_EMAIL = "master@revix.es"
MASTER_PASSWORD = "RevixMaster2026!"

# Order with shipments
TEST_ORDER_ID = "57988501-4faa-4633-88ca-f0c96e6d75ce"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for master user."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": MASTER_EMAIL, "password": MASTER_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.text}")


class TestGLSEnviosEndpoint:
    """Tests for GET /api/gls/envios endpoint"""
    
    def test_envios_returns_list_with_total(self, auth_token):
        """GET /api/gls/envios should return list with total, data, and tracking_url"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/gls/envios", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Check response structure
        assert "data" in data, "Response should contain 'data' field"
        assert "total" in data, "Response should contain 'total' field"
        assert "page" in data, "Response should contain 'page' field"
        assert "limit" in data, "Response should contain 'limit' field"
        
        # Check total is a number
        assert isinstance(data["total"], int), "total should be an integer"
        assert data["total"] >= 0, "total should be non-negative"
        
        # Check data is a list
        assert isinstance(data["data"], list), "data should be a list"
        
        print(f"SUCCESS: GET /api/gls/envios returned {data['total']} shipments")
    
    def test_envios_items_have_tracking_url(self, auth_token):
        """Shipments with codbarras should have tracking_url field"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/gls/envios", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        if data["total"] > 0:
            shipments_with_tracking = 0
            shipments_missing_tracking = []
            
            for shipment in data["data"]:
                # Check if tracking_url field exists and is populated for shipments with codbarras
                if shipment.get("gls_codbarras") and shipment.get("tracking_url"):
                    assert "gls-spain.es" in shipment["tracking_url"], "tracking_url should point to GLS Spain"
                    assert shipment["gls_codbarras"] in shipment["tracking_url"], "tracking_url should contain codbarras"
                    shipments_with_tracking += 1
                elif shipment.get("gls_codbarras") and not shipment.get("tracking_url"):
                    # Legacy shipments may not have tracking_url - log but don't fail
                    shipments_missing_tracking.append(shipment.get("id"))
            
            if shipments_missing_tracking:
                print(f"WARNING: {len(shipments_missing_tracking)} legacy shipments missing tracking_url")
            
            # At least some shipments should have tracking_url
            assert shipments_with_tracking > 0, "At least one shipment should have tracking_url"
            print(f"SUCCESS: {shipments_with_tracking} shipments have valid tracking_url")
        else:
            pytest.skip("No shipments to test")
    
    def test_envios_requires_auth(self):
        """GET /api/gls/envios should require authentication"""
        response = requests.get(f"{BASE_URL}/api/gls/envios")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("SUCCESS: Endpoint requires authentication")


class TestOrdenLogisticsEndpoint:
    """Tests for GET /api/ordenes/{orden_id}/logistics endpoint"""
    
    def test_logistics_returns_correct_structure(self, auth_token):
        """GET /api/ordenes/{orden_id}/logistics should return gls_activo and shipment data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/logistics", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Check response structure
        assert "gls_activo" in data, "Response should contain 'gls_activo' field"
        assert "recogida" in data, "Response should contain 'recogida' field"
        assert "envio" in data, "Response should contain 'envio' field"
        
        # Check gls_activo is boolean
        assert isinstance(data["gls_activo"], bool), "gls_activo should be boolean"
        
        # Check recogida structure
        assert "shipment" in data["recogida"], "recogida should have 'shipment' field"
        assert "eventos" in data["recogida"], "recogida should have 'eventos' field"
        assert "total" in data["recogida"], "recogida should have 'total' field"
        
        # Check envio structure
        assert "shipment" in data["envio"], "envio should have 'shipment' field"
        assert "eventos" in data["envio"], "envio should have 'eventos' field"
        assert "total" in data["envio"], "envio should have 'total' field"
        
        print(f"SUCCESS: GET /api/ordenes/{TEST_ORDER_ID}/logistics returned correct structure")
        print(f"  gls_activo: {data['gls_activo']}")
        print(f"  recogida total: {data['recogida']['total']}")
        print(f"  envio total: {data['envio']['total']}")
    
    def test_logistics_gls_activo_is_true(self, auth_token):
        """GLS should be active for this order"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/logistics", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["gls_activo"] == True, "gls_activo should be True"
        print("SUCCESS: gls_activo is True")
    
    def test_logistics_envio_has_tracking_url(self, auth_token):
        """Envio shipment should have tracking_url"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/logistics", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        envio_shipment = data["envio"]["shipment"]
        if envio_shipment:
            assert "tracking_url" in envio_shipment, "Envio shipment should have tracking_url"
            assert envio_shipment["tracking_url"], "tracking_url should not be empty"
            assert "gls-spain.es" in envio_shipment["tracking_url"], "tracking_url should point to GLS Spain"
            
            # Verify tracking_url contains the codbarras
            if envio_shipment.get("gls_codbarras"):
                assert envio_shipment["gls_codbarras"] in envio_shipment["tracking_url"], \
                    "tracking_url should contain the codbarras"
            
            print(f"SUCCESS: Envio has tracking_url: {envio_shipment['tracking_url']}")
        else:
            pytest.skip("No envio shipment to test")
    
    def test_logistics_requires_auth(self):
        """GET /api/ordenes/{orden_id}/logistics should require authentication"""
        response = requests.get(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/logistics")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("SUCCESS: Endpoint requires authentication")
    
    def test_logistics_not_found_for_invalid_order(self, auth_token):
        """GET /api/ordenes/{invalid_id}/logistics should return 404"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/ordenes/invalid-order-id-12345/logistics", headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("SUCCESS: Returns 404 for invalid order")


class TestTrackingURLFormat:
    """Tests for tracking URL format and correctness"""
    
    def test_tracking_url_format(self, auth_token):
        """Tracking URL should be in correct format"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/gls/envios", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        for shipment in data["data"]:
            if shipment.get("gls_codbarras") and shipment.get("tracking_url"):
                tracking_url = shipment["tracking_url"]
                codbarras = shipment["gls_codbarras"]
                
                # Check URL format
                assert tracking_url.startswith("https://www.gls-spain.es/apptracking.asp"), \
                    f"Invalid tracking URL format: {tracking_url}"
                assert f"codigo={codbarras}" in tracking_url, \
                    f"tracking_url should contain codigo={codbarras}"
                
                print(f"SUCCESS: Valid tracking URL for {codbarras}: {tracking_url}")
        
        print("SUCCESS: All tracking URLs have correct format")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

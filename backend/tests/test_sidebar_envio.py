"""
Test suite for CRM Revix.es iteration 21 features:
- PATCH /api/ordenes/{id}/envio endpoint
- Orders list API (autorizacion field)
- Sidebar groups and navigation
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MASTER_EMAIL = "master@techrepair.local"
MASTER_PASSWORD = "master123"
TEST_ORDER_ID = "6f05f8e9-452b-4562-97ad-b4b2890903f9"
TEST_AUTH_CODE = "26BE000774"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for master user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MASTER_EMAIL,
        "password": MASTER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed")


@pytest.fixture
def api_client(auth_token):
    """Create session with auth headers"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestEnvioEndpoint:
    """Tests for PATCH /api/ordenes/{id}/envio endpoint"""
    
    def test_get_order_has_auth_code(self, api_client):
        """Verify test order has authorization code"""
        response = api_client.get(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}")
        assert response.status_code == 200, f"Failed to get order: {response.text}"
        
        data = response.json()
        assert data.get("numero_autorizacion") == TEST_AUTH_CODE, \
            f"Expected auth code {TEST_AUTH_CODE}, got {data.get('numero_autorizacion')}"
        print(f"✅ Order {TEST_ORDER_ID} has auth code: {data.get('numero_autorizacion')}")
    
    def test_patch_envio_agencia_only(self, api_client):
        """Test partial update - only agencia field"""
        # First get current value
        get_response = api_client.get(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}")
        original_data = get_response.json()
        original_agencia = original_data.get("agencia_envio", "")
        
        # Update only agencia
        new_agencia = "TEST_AGENCIA_UPDATE"
        response = api_client.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/envio",
            json={"agencia_envio": new_agencia}
        )
        assert response.status_code == 200, f"PATCH failed: {response.text}"
        
        data = response.json()
        assert data.get("agencia_envio") == new_agencia
        # Other fields should remain unchanged
        assert data.get("numero_autorizacion") == original_data.get("numero_autorizacion")
        print(f"✅ PATCH agencia_envio successful: {new_agencia}")
        
        # Restore original
        api_client.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/envio",
            json={"agencia_envio": original_agencia}
        )
    
    def test_patch_envio_tracking_entrada(self, api_client):
        """Test partial update - tracking entrada field"""
        # First get current value
        get_response = api_client.get(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}")
        original_data = get_response.json()
        original_tracking = original_data.get("codigo_recogida_entrada", "")
        
        # Update tracking
        new_tracking = "TEST_TRACK_12345"
        response = api_client.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/envio",
            json={"codigo_recogida_entrada": new_tracking}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("codigo_recogida_entrada") == new_tracking
        print(f"✅ PATCH codigo_recogida_entrada successful: {new_tracking}")
        
        # Restore original
        api_client.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/envio",
            json={"codigo_recogida_entrada": original_tracking}
        )
    
    def test_patch_envio_tracking_salida(self, api_client):
        """Test partial update - tracking salida field"""
        new_tracking = "SALIDA_TEST_789"
        response = api_client.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/envio",
            json={"codigo_recogida_salida": new_tracking}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("codigo_recogida_salida") == new_tracking
        print(f"✅ PATCH codigo_recogida_salida successful: {new_tracking}")
        
        # Clear test value
        api_client.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/envio",
            json={"codigo_recogida_salida": ""}
        )
    
    def test_patch_envio_multiple_fields(self, api_client):
        """Test updating multiple fields at once"""
        # Get original values
        get_response = api_client.get(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}")
        original_data = get_response.json()
        
        # Update multiple fields
        updates = {
            "agencia_envio": "MULTI_TEST_AGENCY",
            "codigo_recogida_entrada": "MULTI_ENTRADA",
            "codigo_recogida_salida": "MULTI_SALIDA"
        }
        
        response = api_client.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/envio",
            json=updates
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("agencia_envio") == "MULTI_TEST_AGENCY"
        assert data.get("codigo_recogida_entrada") == "MULTI_ENTRADA"
        assert data.get("codigo_recogida_salida") == "MULTI_SALIDA"
        # Auth code should remain unchanged
        assert data.get("numero_autorizacion") == TEST_AUTH_CODE
        print("✅ PATCH multiple fields successful")
        
        # Restore original values
        api_client.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/envio",
            json={
                "agencia_envio": original_data.get("agencia_envio", ""),
                "codigo_recogida_entrada": original_data.get("codigo_recogida_entrada", ""),
                "codigo_recogida_salida": original_data.get("codigo_recogida_salida", "")
            }
        )
    
    def test_patch_envio_auth_code_update(self, api_client):
        """Test updating authorization code"""
        # Get original value
        get_response = api_client.get(f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}")
        original_data = get_response.json()
        original_auth = original_data.get("numero_autorizacion", "")
        
        # Update auth code
        new_auth = "TEST_AUTH_99999"
        response = api_client.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/envio",
            json={"numero_autorizacion": new_auth}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("numero_autorizacion") == new_auth
        print(f"✅ PATCH numero_autorizacion successful: {new_auth}")
        
        # Restore original
        api_client.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/envio",
            json={"numero_autorizacion": original_auth}
        )
    
    def test_patch_envio_invalid_order(self, api_client):
        """Test PATCH with non-existent order ID"""
        response = api_client.patch(
            f"{BASE_URL}/api/ordenes/nonexistent-order-id/envio",
            json={"agencia_envio": "Test"}
        )
        assert response.status_code == 404
        print("✅ PATCH returns 404 for invalid order ID")


class TestOrdersListAuthorizacion:
    """Tests for orders list filtering by authorization code"""
    
    def test_list_orders_has_autorizacion_field(self, api_client):
        """Verify orders list includes numero_autorizacion field"""
        response = api_client.get(f"{BASE_URL}/api/ordenes")
        assert response.status_code == 200
        
        orders = response.json()
        assert len(orders) > 0, "No orders found"
        
        # Check that at least one order has numero_autorizacion
        orders_with_auth = [o for o in orders if o.get("numero_autorizacion")]
        assert len(orders_with_auth) > 0, "No orders with authorization code found"
        print(f"✅ Found {len(orders_with_auth)} orders with authorization codes")
    
    def test_filter_orders_by_autorizacion(self, api_client):
        """Test filtering orders by authorization code"""
        response = api_client.get(
            f"{BASE_URL}/api/ordenes",
            params={"autorizacion": TEST_AUTH_CODE}
        )
        assert response.status_code == 200
        
        orders = response.json()
        assert len(orders) > 0, f"No orders found for auth code {TEST_AUTH_CODE}"
        
        # All returned orders should have the auth code
        for order in orders:
            assert TEST_AUTH_CODE in order.get("numero_autorizacion", ""), \
                f"Order {order.get('id')} doesn't match auth code filter"
        print(f"✅ Filter by autorizacion works: found {len(orders)} orders")
    
    def test_filter_orders_partial_autorizacion(self, api_client):
        """Test partial match on authorization code"""
        partial_code = "26BE"  # Partial match
        response = api_client.get(
            f"{BASE_URL}/api/ordenes",
            params={"autorizacion": partial_code}
        )
        assert response.status_code == 200
        
        orders = response.json()
        for order in orders:
            auth = order.get("numero_autorizacion", "")
            assert partial_code.lower() in auth.lower(), \
                f"Order auth code {auth} doesn't contain {partial_code}"
        print(f"✅ Partial auth code filter works: found {len(orders)} orders")


class TestAPIStatus:
    """Basic API health checks"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        print("✅ API root accessible")
    
    def test_dashboard_stats(self, api_client):
        """Test dashboard stats endpoint"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_ordenes" in data
        assert "ordenes_por_estado" in data
        print(f"✅ Dashboard stats: {data.get('total_ordenes')} total orders")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

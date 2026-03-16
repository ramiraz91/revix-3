"""
Test cases for new endpoints:
- POST /api/ordenes/{id}/enviar-whatsapp
- POST /api/ordenes/{id}/re-presupuesto
- POST /api/ordenes/{id}/aprobar-re-presupuesto

These endpoints were added for CRM/ERP functionality for repair workshop (Revix).
"""
import pytest
import requests
import os
import sys

# Add backend to path for token generation
sys.path.insert(0, '/app/backend')
from auth import create_token

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Generate JWT token for testing
TEST_TOKEN = create_token('test-id', 'master@revix.es', 'master')

@pytest.fixture
def auth_headers():
    """Auth headers with valid JWT token"""
    return {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }

@pytest.fixture
def session(auth_headers):
    """Requests session with auth headers"""
    s = requests.Session()
    s.headers.update(auth_headers)
    return s


class TestEnviarWhatsAppEndpoint:
    """Test POST /api/ordenes/{id}/enviar-whatsapp"""
    
    def test_enviar_whatsapp_returns_404_for_missing_order(self, session):
        """
        Test that enviar-whatsapp returns 404 (not 405) for non-existent order.
        This validates the endpoint exists and handles missing orders correctly.
        """
        fake_order_id = "non-existent-order-id-12345"
        response = session.post(f"{BASE_URL}/api/ordenes/{fake_order_id}/enviar-whatsapp")
        
        # Should be 404 (order not found), NOT 405 (method not allowed)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        
        # Verify error message mentions order not found
        data = response.json()
        assert "detail" in data
        assert "no encontrada" in data["detail"].lower() or "not found" in data["detail"].lower()
        print(f"✓ enviar-whatsapp returns 404 for missing order: {data['detail']}")
    
    def test_enviar_whatsapp_endpoint_exists(self, session):
        """
        Verify the endpoint exists by checking it doesn't return 405.
        """
        response = session.post(f"{BASE_URL}/api/ordenes/test-id/enviar-whatsapp")
        
        # Should NOT be 405 (method not allowed) - endpoint should exist
        assert response.status_code != 405, "Endpoint POST /ordenes/{id}/enviar-whatsapp doesn't exist (405)"
        print(f"✓ enviar-whatsapp endpoint exists (status: {response.status_code})")


class TestRePresupuestoEndpoint:
    """Test POST /api/ordenes/{id}/re-presupuesto"""
    
    def test_re_presupuesto_returns_404_for_missing_order(self, session):
        """
        Test that re-presupuesto returns 404 for non-existent order.
        """
        fake_order_id = "non-existent-order-id-12345"
        payload = {
            "nuevo_importe": 150.00,
            "motivo": "Testing re-presupuesto"
        }
        response = session.post(
            f"{BASE_URL}/api/ordenes/{fake_order_id}/re-presupuesto",
            json=payload
        )
        
        # Should be 404 (order not found)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data
        assert "no encontrada" in data["detail"].lower() or "not found" in data["detail"].lower()
        print(f"✓ re-presupuesto returns 404 for missing order: {data['detail']}")
    
    def test_re_presupuesto_endpoint_exists(self, session):
        """
        Verify the endpoint exists by checking it doesn't return 405.
        """
        payload = {
            "nuevo_importe": 100.00,
            "motivo": "Test"
        }
        response = session.post(
            f"{BASE_URL}/api/ordenes/test-id/re-presupuesto",
            json=payload
        )
        
        # Should NOT be 405 (method not allowed) - endpoint should exist
        assert response.status_code != 405, "Endpoint POST /ordenes/{id}/re-presupuesto doesn't exist (405)"
        print(f"✓ re-presupuesto endpoint exists (status: {response.status_code})")
    
    def test_re_presupuesto_accepts_required_fields(self, session):
        """
        Verify the endpoint accepts nuevo_importe and motivo fields.
        """
        payload = {
            "nuevo_importe": 250.50,
            "motivo": "Additional parts needed"
        }
        response = session.post(
            f"{BASE_URL}/api/ordenes/test-order/re-presupuesto",
            json=payload
        )
        
        # Should be 404 (no order), but NOT 422 (validation error)
        # This confirms the payload structure is correct
        assert response.status_code != 422, f"Payload rejected (422): {response.text}"
        print(f"✓ re-presupuesto accepts nuevo_importe and motivo fields (status: {response.status_code})")


class TestAprobarRePresupuestoEndpoint:
    """Test POST /api/ordenes/{id}/aprobar-re-presupuesto"""
    
    def test_aprobar_re_presupuesto_returns_404_for_missing_order(self, session):
        """
        Test that aprobar-re-presupuesto returns 404 for non-existent order.
        """
        fake_order_id = "non-existent-order-id-12345"
        response = session.post(f"{BASE_URL}/api/ordenes/{fake_order_id}/aprobar-re-presupuesto")
        
        # Should be 404 (order not found)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data
        assert "no encontrada" in data["detail"].lower() or "not found" in data["detail"].lower()
        print(f"✓ aprobar-re-presupuesto returns 404 for missing order: {data['detail']}")
    
    def test_aprobar_re_presupuesto_endpoint_exists(self, session):
        """
        Verify the endpoint exists by checking it doesn't return 405.
        """
        response = session.post(f"{BASE_URL}/api/ordenes/test-id/aprobar-re-presupuesto")
        
        # Should NOT be 405 (method not allowed) - endpoint should exist
        assert response.status_code != 405, "Endpoint POST /ordenes/{id}/aprobar-re-presupuesto doesn't exist (405)"
        print(f"✓ aprobar-re-presupuesto endpoint exists (status: {response.status_code})")


class TestApiIntegration:
    """Integration tests for API methods in frontend api.js"""
    
    def test_ordenes_api_re_presupuesto_method(self, session):
        """
        Verify the API method for re-presupuesto is correctly routed.
        Frontend calls: ordenesAPI.rePresupuesto(id, data)
        Backend expects: POST /api/ordenes/{id}/re-presupuesto
        """
        # Test the exact URL pattern used by frontend
        response = session.post(
            f"{BASE_URL}/api/ordenes/any-order-id/re-presupuesto",
            json={"nuevo_importe": 100.00, "motivo": "test", "notificar_cliente": False}
        )
        
        # Endpoint should exist (not 405) and return 404 for missing order
        assert response.status_code in [404, 400], f"Unexpected status: {response.status_code}"
        print(f"✓ API route for rePresupuesto works correctly")
    
    def test_ordenes_api_aprobar_re_presupuesto_method(self, session):
        """
        Verify the API method for aprobar-re-presupuesto is correctly routed.
        Frontend calls: ordenesAPI.aprobarRePresupuesto(id)
        Backend expects: POST /api/ordenes/{id}/aprobar-re-presupuesto
        """
        response = session.post(f"{BASE_URL}/api/ordenes/any-order-id/aprobar-re-presupuesto")
        
        # Endpoint should exist (not 405) and return 404 for missing order
        assert response.status_code in [404, 400], f"Unexpected status: {response.status_code}"
        print(f"✓ API route for aprobarRePresupuesto works correctly")
    
    def test_ordenes_api_enviar_whatsapp_method(self, session):
        """
        Verify the API method for enviar-whatsapp is correctly routed.
        Frontend calls: ordenesAPI.enviarWhatsApp(id)
        Backend expects: POST /api/ordenes/{id}/enviar-whatsapp
        """
        response = session.post(f"{BASE_URL}/api/ordenes/any-order-id/enviar-whatsapp")
        
        # Endpoint should exist (not 405) and return 404 for missing order
        assert response.status_code in [404, 500], f"Unexpected status: {response.status_code}"
        print(f"✓ API route for enviarWhatsApp works correctly")


class TestAuthenticationRequirements:
    """Test that endpoints require authentication"""
    
    def test_enviar_whatsapp_requires_auth(self):
        """Verify enviar-whatsapp requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/ordenes/test-id/enviar-whatsapp",
            headers={"Content-Type": "application/json"}
        )
        
        # Should be 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print(f"✓ enviar-whatsapp requires authentication")
    
    def test_re_presupuesto_requires_auth(self):
        """Verify re-presupuesto requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/ordenes/test-id/re-presupuesto",
            headers={"Content-Type": "application/json"},
            json={"nuevo_importe": 100.00}
        )
        
        # Should be 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print(f"✓ re-presupuesto requires authentication")
    
    def test_aprobar_re_presupuesto_requires_auth(self):
        """Verify aprobar-re-presupuesto requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/ordenes/test-id/aprobar-re-presupuesto",
            headers={"Content-Type": "application/json"}
        )
        
        # Should be 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print(f"✓ aprobar-re-presupuesto requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

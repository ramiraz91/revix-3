"""
Iteration 39: P0/P1 Fixes Testing
=================================
Tests for validating fixes to backend endpoints that were crashing due to
legacy documents with missing/invalid fields (dni, datetime, etc.)

P0 (Critical):
- GET /api/clientes - Should not return 500 with legacy documents
- GET /api/clientes/{id} - Should return normalized fields
- GET /api/ordenes - Should remain stable (no validation crash)
- GET /api/incidencias - Should respond 200

P1 (Important):
- POST /api/insurama/carga-masiva - Should return 400 for non-Excel files
"""

import pytest
import requests
import os

# Get the preview URL from frontend/.env
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Fallback if env not set - read from file
if not BASE_URL:
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    BASE_URL = line.split('=', 1)[1].strip().rstrip('/')
                    break
    except:
        pass

assert BASE_URL, "BASE_URL not configured - check REACT_APP_BACKEND_URL in frontend/.env"


class TestP0ClientesEndpoint:
    """Tests for GET /api/clientes - P0 Critical fix for ResponseValidationError"""
    
    def test_clientes_list_returns_200(self):
        """GET /api/clientes should return 200, not 500 (ResponseValidationError)"""
        response = requests.get(f"{BASE_URL}/api/clientes", timeout=30)
        
        # Must not be 500 - this was the original bug
        assert response.status_code != 500, f"Endpoint returned 500 (bug not fixed): {response.text[:500]}"
        
        # Should be 200 OK
        assert response.status_code == 200, f"Unexpected status {response.status_code}: {response.text[:500]}"
        
        # Should return a list
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ GET /api/clientes returned 200 with {len(data)} clients")
    
    def test_clientes_list_with_search(self):
        """GET /api/clientes?search=... should handle search without crashing"""
        response = requests.get(f"{BASE_URL}/api/clientes", params={"search": "test"}, timeout=30)
        
        assert response.status_code != 500, f"Search query caused 500 error: {response.text[:500]}"
        assert response.status_code == 200, f"Unexpected status {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/clientes?search=test returned 200 with {len(data)} results")
    
    def test_clientes_normalized_fields(self):
        """Verify that clients have normalized fields (dni, telefono, etc.)"""
        response = requests.get(f"{BASE_URL}/api/clientes", timeout=30)
        assert response.status_code == 200
        
        clients = response.json()
        if len(clients) == 0:
            pytest.skip("No clients in database to validate")
        
        # Check first few clients for normalized fields
        for client in clients[:5]:
            # These fields should exist and be strings (not None)
            assert "nombre" in client, f"Missing 'nombre' field in client {client.get('id')}"
            assert "apellidos" in client, f"Missing 'apellidos' field in client {client.get('id')}"
            assert "dni" in client, f"Missing 'dni' field in client {client.get('id')}"
            assert "telefono" in client, f"Missing 'telefono' field in client {client.get('id')}"
            
            # Fields should be strings, not None
            assert isinstance(client.get("nombre"), str), f"'nombre' should be string in client {client.get('id')}"
            assert isinstance(client.get("dni"), str), f"'dni' should be string in client {client.get('id')}"
            
        print(f"✓ Verified {min(5, len(clients))} clients have normalized fields")


class TestP0ClienteByIdEndpoint:
    """Tests for GET /api/clientes/{id} - Should return normalized document"""
    
    def test_cliente_by_id_endpoint_works(self):
        """GET /api/clientes/{id} should work for an existing client"""
        # First get list of clients to find a valid ID
        list_response = requests.get(f"{BASE_URL}/api/clientes", timeout=30)
        assert list_response.status_code == 200
        
        clients = list_response.json()
        if len(clients) == 0:
            pytest.skip("No clients in database to test")
        
        # Get first client by ID
        client_id = clients[0].get("id")
        assert client_id, "Client doesn't have 'id' field"
        
        response = requests.get(f"{BASE_URL}/api/clientes/{client_id}", timeout=30)
        
        # Should not return 500
        assert response.status_code != 500, f"GET by ID returned 500: {response.text[:500]}"
        assert response.status_code == 200, f"Unexpected status {response.status_code}"
        
        client = response.json()
        # Verify normalized fields
        assert "dni" in client
        assert isinstance(client.get("dni"), str)
        assert "nombre" in client
        assert isinstance(client.get("nombre"), str)
        
        print(f"✓ GET /api/clientes/{client_id} returned 200 with normalized fields")
    
    def test_cliente_specific_test_id(self):
        """GET /api/clientes/test-cliente-001 should return normalized fields"""
        # This tests a specific client ID if it exists
        response = requests.get(f"{BASE_URL}/api/clientes/test-cliente-001", timeout=30)
        
        # Can be 404 if not exists, but should NOT be 500
        assert response.status_code != 500, f"Endpoint returned 500: {response.text[:500]}"
        
        if response.status_code == 200:
            client = response.json()
            assert "dni" in client
            assert isinstance(client.get("dni"), str)
            print(f"✓ GET /api/clientes/test-cliente-001 returned normalized client")
        elif response.status_code == 404:
            print(f"✓ GET /api/clientes/test-cliente-001 returned 404 (client doesn't exist, but no 500 error)")
        else:
            pytest.fail(f"Unexpected status: {response.status_code}")


class TestP0OrdenesEndpoint:
    """Tests for GET /api/ordenes - Should remain stable"""
    
    def test_ordenes_list_returns_200(self):
        """GET /api/ordenes should return 200 without validation crash"""
        response = requests.get(f"{BASE_URL}/api/ordenes", timeout=30)
        
        # Must not crash with 500
        assert response.status_code != 500, f"Endpoint returned 500: {response.text[:500]}"
        assert response.status_code == 200, f"Unexpected status {response.status_code}: {response.text[:500]}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ GET /api/ordenes returned 200 with {len(data)} orders")
    
    def test_ordenes_with_filters(self):
        """GET /api/ordenes with various filters should work"""
        # Test with estado filter
        response = requests.get(f"{BASE_URL}/api/ordenes", params={"estado": "pendiente_recibir"}, timeout=30)
        assert response.status_code != 500, f"Filter 'estado' caused 500: {response.text[:500]}"
        assert response.status_code == 200
        
        # Test with search filter
        response = requests.get(f"{BASE_URL}/api/ordenes", params={"search": "test"}, timeout=30)
        assert response.status_code != 500, f"Filter 'search' caused 500: {response.text[:500]}"
        assert response.status_code == 200
        
        print(f"✓ GET /api/ordenes with filters works correctly")
    
    def test_orden_by_ref(self):
        """GET /api/ordenes/{orden_ref} should work for existing orders"""
        # Get list first
        list_response = requests.get(f"{BASE_URL}/api/ordenes", timeout=30)
        assert list_response.status_code == 200
        
        orders = list_response.json()
        if len(orders) == 0:
            pytest.skip("No orders in database to test")
        
        # Test with first order's ID
        order_id = orders[0].get("id")
        if order_id:
            response = requests.get(f"{BASE_URL}/api/ordenes/{order_id}", timeout=30)
            assert response.status_code != 500, f"GET order by ID returned 500: {response.text[:500]}"
            assert response.status_code == 200
            
            order = response.json()
            # Verify key fields exist
            assert "estado" in order
            assert "dispositivo" in order
            assert "materiales" in order
            assert "historial_estados" in order
            
            print(f"✓ GET /api/ordenes/{order_id} returned 200 with normalized fields")


class TestP0IncidenciasEndpoint:
    """Tests for GET /api/incidencias - Should respond 200"""
    
    def test_incidencias_returns_200(self):
        """GET /api/incidencias should return 200 (requires auth)"""
        # Note: This endpoint requires authentication
        # First login to get a token
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "ramiraz91@gmail.com", "password": "temp123"},
            timeout=30
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"Could not login to test authenticated endpoint: {login_response.status_code}")
        
        token = login_response.json().get("access_token") or login_response.json().get("token")
        if not token:
            pytest.skip("No token received from login")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/incidencias", headers=headers, timeout=30)
        
        # Should not return 500
        assert response.status_code != 500, f"Endpoint returned 500: {response.text[:500]}"
        assert response.status_code == 200, f"Unexpected status {response.status_code}: {response.text[:500]}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ GET /api/incidencias returned 200 with {len(data)} incidencias")


class TestP1InsuramaEndpoint:
    """Tests for POST /api/insurama/carga-masiva - P1 fix for file validation"""
    
    def test_carga_masiva_rejects_non_excel(self):
        """POST /api/insurama/carga-masiva should return 400 for non-Excel files"""
        # Login first
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "ramiraz91@gmail.com", "password": "temp123"},
            timeout=30
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"Could not login: {login_response.status_code}")
        
        token = login_response.json().get("access_token") or login_response.json().get("token")
        if not token:
            pytest.skip("No token received from login")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a fake text file (not Excel)
        fake_content = b"This is not an Excel file"
        files = {"file": ("test.txt", fake_content, "text/plain")}
        
        response = requests.post(
            f"{BASE_URL}/api/insurama/carga-masiva",
            headers=headers,
            files=files,
            timeout=30
        )
        
        # Should return 400 (Bad Request) for non-Excel files
        assert response.status_code == 400, f"Expected 400 for non-Excel, got {response.status_code}: {response.text[:500]}"
        
        # Check error message mentions Excel requirement
        error_detail = response.json().get("detail", "")
        assert "excel" in error_detail.lower() or "xlsx" in error_detail.lower() or "xls" in error_detail.lower(), \
            f"Error message should mention Excel format: {error_detail}"
        
        print(f"✓ POST /api/insurama/carga-masiva correctly returns 400 for non-Excel files")
    
    def test_carga_masiva_endpoint_exists(self):
        """POST /api/insurama/carga-masiva endpoint should exist and not return 404"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "ramiraz91@gmail.com", "password": "temp123"},
            timeout=30
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"Could not login: {login_response.status_code}")
        
        token = login_response.json().get("access_token") or login_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Send request without file to test endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/insurama/carga-masiva",
            headers=headers,
            timeout=30
        )
        
        # Should not be 404 or 405
        assert response.status_code not in [404, 405], \
            f"Endpoint not found: {response.status_code}"
        
        # Could be 422 (validation error) or 400 if file is required - both are acceptable
        print(f"✓ POST /api/insurama/carga-masiva endpoint exists (status: {response.status_code})")


class TestHealthAndBasics:
    """Basic health checks"""
    
    def test_api_root(self):
        """Basic API root check"""
        response = requests.get(f"{BASE_URL}/api/", timeout=10)
        
        # API root endpoint should return 200
        assert response.status_code == 200, f"API root check failed: {response.status_code}"
        print(f"✓ API root check passed")
    
    def test_base_url_accessible(self):
        """Verify BASE_URL is accessible"""
        response = requests.get(BASE_URL, timeout=10)
        
        # Should get some response (frontend or redirect)
        assert response.status_code < 500, f"Server error: {response.status_code}"
        print(f"✓ Base URL accessible: {BASE_URL}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

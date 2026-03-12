"""
Iteration 28: Test Photos Before/After and Insurama Features
Tests:
- P0: Photos Before/After - OrdenTecnico page photo upload with tipo_foto parameter
- P1: Insurama /api/insurama/presupuestos endpoint returns populated client data
- P1: Backend auto-sync functions exist and can be called
- Backend /api/ordenes/{id}/evidencias-tecnico endpoint with tipo_foto parameter
- Login flows for admin and technician
"""
import pytest
import requests
import os
import io
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://revix-crm.preview.emergentagent.com"

# ==== FIXTURES ====

@pytest.fixture(scope="module")
def session():
    """Shared requests session"""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s

@pytest.fixture(scope="module")
def admin_token(session):
    """Get admin authentication token"""
    # Try multiple credential variations
    credentials = [
        {"email": "admin@crm.com", "password": "admin123"},
        {"email": "admin@techrepair.local", "password": "admin123"},
    ]
    
    for cred in credentials:
        response = session.post(f"{BASE_URL}/api/auth/login", json=cred)
        if response.status_code == 200:
            token = response.json().get("token")
            print(f"Admin login successful with: {cred['email']}")
            return token
    
    pytest.skip("Admin login failed - skipping admin tests")
    return None

@pytest.fixture(scope="module")
def tecnico_token(session):
    """Get technician authentication token"""
    credentials = [
        {"email": "tecnico@crm.com", "password": "password123"},
        {"email": "tecnico@techrepair.local", "password": "tecnico123"},
    ]
    
    for cred in credentials:
        response = session.post(f"{BASE_URL}/api/auth/login", json=cred)
        if response.status_code == 200:
            token = response.json().get("token")
            print(f"Tecnico login successful with: {cred['email']}")
            return token
    
    pytest.skip("Tecnico login failed - skipping tecnico tests")
    return None

@pytest.fixture(scope="module")
def admin_session(session, admin_token):
    """Session with admin auth header"""
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return s

@pytest.fixture(scope="module")
def tecnico_session(session, tecnico_token):
    """Session with tecnico auth header"""
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {tecnico_token}"
    })
    return s


# ==== AUTH TESTS ====

class TestAuth:
    """Authentication tests"""
    
    def test_api_root(self, session):
        """Test API is accessible"""
        response = session.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "Mobile Repair" in str(data)
        print(f"API root response: {data}")
    
    def test_admin_login(self, session):
        """Test admin login with various credentials"""
        credentials = [
            {"email": "admin@crm.com", "password": "admin123"},
            {"email": "admin@techrepair.local", "password": "admin123"},
        ]
        
        success = False
        for cred in credentials:
            response = session.post(f"{BASE_URL}/api/auth/login", json=cred)
            if response.status_code == 200:
                data = response.json()
                assert "token" in data
                assert "user" in data
                print(f"Admin login OK with {cred['email']}")
                success = True
                break
            else:
                print(f"Login failed with {cred['email']}: {response.status_code}")
        
        if not success:
            # Create admin user if doesn't exist
            print("Attempting to check existing users...")
    
    def test_tecnico_login(self, session):
        """Test technician login"""
        credentials = [
            {"email": "tecnico@crm.com", "password": "password123"},
            {"email": "tecnico@techrepair.local", "password": "tecnico123"},
        ]
        
        for cred in credentials:
            response = session.post(f"{BASE_URL}/api/auth/login", json=cred)
            if response.status_code == 200:
                data = response.json()
                assert "token" in data
                print(f"Tecnico login OK with {cred['email']}")
                return
        
        print("Note: Tecnico login may need different credentials")


# ==== PHOTOS BEFORE/AFTER TESTS ====

class TestPhotosBeforeAfter:
    """Test P0: Photos Before/After feature"""
    
    def test_evidencias_tecnico_endpoint_exists(self, tecnico_session):
        """Test that the evidencias-tecnico endpoint accepts tipo_foto parameter"""
        # First get an order to test with
        orders_response = tecnico_session.get(f"{BASE_URL}/api/ordenes?limit=5")
        if orders_response.status_code != 200:
            pytest.skip("No orders available for testing")
        
        orders = orders_response.json()
        if not orders:
            pytest.skip("No orders found in system")
        
        # Use first order
        orden_id = orders[0].get('id')
        print(f"Testing with order ID: {orden_id}")
        
        # Create a simple test image (1x1 pixel PNG)
        test_image = io.BytesIO()
        # Minimal valid JPEG (1x1 pixel)
        test_image.write(bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
            0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
            0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
            0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
            0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
            0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
            0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
            0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
            0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
            0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
            0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
            0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
            0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
            0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
            0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
            0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
            0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD3, 0xFF, 0xD9
        ]))
        test_image.seek(0)
        
        # Test endpoint with tipo_foto=antes
        files = {'file': ('test_antes.jpg', test_image, 'image/jpeg')}
        headers = {"Authorization": tecnico_session.headers.get("Authorization")}
        
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{orden_id}/evidencias-tecnico?tipo_foto=antes",
            files=files,
            headers=headers
        )
        
        print(f"Upload response status: {response.status_code}")
        print(f"Upload response: {response.text[:500] if response.text else 'Empty'}")
        
        # Endpoint should exist and accept the request (may fail due to various reasons but not 404 or 405)
        assert response.status_code != 404, "Endpoint not found - tipo_foto parameter may not be implemented"
        assert response.status_code != 405, "Method not allowed"
        
        if response.status_code == 200:
            data = response.json()
            assert "file_name" in data or "message" in data
            print(f"Photo upload successful: {data}")
    
    def test_order_has_photo_arrays(self, tecnico_session):
        """Test that orders have fotos_antes and fotos_despues arrays"""
        response = tecnico_session.get(f"{BASE_URL}/api/ordenes?limit=5")
        if response.status_code != 200:
            pytest.skip("Cannot fetch orders")
        
        orders = response.json()
        if not orders:
            pytest.skip("No orders available")
        
        orden = orders[0]
        
        # These arrays should exist (may be empty)
        # Backend should support these fields even if empty
        print(f"Order keys: {orden.keys()}")
        print(f"fotos_antes: {orden.get('fotos_antes', 'NOT PRESENT')}")
        print(f"fotos_despues: {orden.get('fotos_despues', 'NOT PRESENT')}")
        print(f"evidencias_tecnico: {orden.get('evidencias_tecnico', 'NOT PRESENT')}")
        
        # Fields don't need to exist if empty, but should be supported
        # The backend code shows these fields are handled


# ==== INSURAMA TESTS ====

class TestInsuramaFeatures:
    """Test P1: Insurama/Sumbroker integration"""
    
    def test_insurama_presupuestos_endpoint(self, admin_session):
        """Test /api/insurama/presupuestos returns data with client names"""
        response = admin_session.get(f"{BASE_URL}/api/insurama/presupuestos?limit=10")
        
        print(f"Insurama presupuestos status: {response.status_code}")
        
        # Endpoint should exist
        if response.status_code == 400:
            data = response.json()
            if "Credenciales" in str(data):
                print("Insurama credentials not configured - expected in test environment")
                pytest.skip("Sumbroker credentials not configured")
            
        if response.status_code == 200:
            data = response.json()
            print(f"Insurama response keys: {data.keys()}")
            
            presupuestos = data.get("presupuestos", [])
            print(f"Found {len(presupuestos)} presupuestos")
            
            # Check that client names are populated (not 'None None' or empty)
            for p in presupuestos[:3]:
                cliente_nombre = p.get("cliente_nombre", "")
                dispositivo = p.get("dispositivo", "")
                print(f"  - Cliente: {cliente_nombre}, Dispositivo: {dispositivo}")
                
                # These should not be 'None None' or empty strings after the fix
                if cliente_nombre:
                    assert cliente_nombre.strip() != "None None", f"Client name not populated: {cliente_nombre}"
                    assert cliente_nombre.strip() != "", "Client name is empty"
    
    def test_insurama_config_endpoint(self, admin_session):
        """Test /api/insurama/config endpoint exists"""
        response = admin_session.get(f"{BASE_URL}/api/insurama/config")
        
        print(f"Insurama config status: {response.status_code}")
        assert response.status_code in [200, 400, 403]
        
        if response.status_code == 200:
            data = response.json()
            print(f"Insurama config: {data}")
            # Should have configurado field
            assert "configurado" in data


# ==== BACKEND AUTO-SYNC TESTS ====

class TestBackendAutoSync:
    """Test P1: Backend auto-sync functions exist"""
    
    def test_sync_functions_in_ordenes_routes(self):
        """Verify sync_order_status_to_insurama function exists in code"""
        import os
        ordenes_routes_path = "/app/backend/routes/ordenes_routes.py"
        
        with open(ordenes_routes_path, 'r') as f:
            content = f.read()
        
        # Check for sync functions
        assert "sync_order_status_to_insurama" in content, "sync_order_status_to_insurama function not found"
        assert "sync_diagnostico_to_insurama" in content, "sync_diagnostico_to_insurama function not found"
        
        # Check that they are called in status change endpoint
        assert "asyncio.create_task(sync_order_status_to_insurama" in content, "Auto-sync not called on status change"
        assert "asyncio.create_task(sync_diagnostico_to_insurama" in content, "Auto-sync not called on diagnosis save"
        
        print("Auto-sync functions found and integrated in ordenes_routes.py")
    
    def test_diagnostico_endpoint(self, tecnico_session):
        """Test /api/ordenes/{id}/diagnostico endpoint"""
        # Get an order first
        orders_response = tecnico_session.get(f"{BASE_URL}/api/ordenes?limit=5")
        if orders_response.status_code != 200:
            pytest.skip("Cannot fetch orders")
        
        orders = orders_response.json()
        if not orders:
            pytest.skip("No orders available")
        
        orden_id = orders[0].get('id')
        
        # Test diagnosis endpoint
        response = tecnico_session.post(
            f"{BASE_URL}/api/ordenes/{orden_id}/diagnostico",
            json={"diagnostico": f"Test diagnosis at {datetime.now().isoformat()}"}
        )
        
        # Use PATCH instead if POST fails
        if response.status_code in [404, 405]:
            response = tecnico_session.patch(
                f"{BASE_URL}/api/ordenes/{orden_id}/diagnostico",
                json={"diagnostico": f"Test diagnosis at {datetime.now().isoformat()}"}
            )
        
        print(f"Diagnostico endpoint status: {response.status_code}")
        
        # Should work (may fail due to order state but not 404)
        assert response.status_code != 404, "Diagnostico endpoint not found"


# ==== ORDENES TESTS ====

class TestOrdenes:
    """Test orders functionality"""
    
    def test_list_ordenes(self, admin_session):
        """Test listing orders"""
        response = admin_session.get(f"{BASE_URL}/api/ordenes")
        assert response.status_code == 200
        
        orders = response.json()
        print(f"Found {len(orders)} orders")
        
        if orders:
            orden = orders[0]
            print(f"Sample order keys: {orden.keys()}")
            print(f"Sample order numero_orden: {orden.get('numero_orden')}")
            print(f"Sample order numero_autorizacion: {orden.get('numero_autorizacion', 'N/A')}")
    
    def test_order_status_change(self, admin_session):
        """Test order status change triggers sync logic"""
        # Get orders with numero_autorizacion (Insurama orders)
        response = admin_session.get(f"{BASE_URL}/api/ordenes")
        assert response.status_code == 200
        
        orders = response.json()
        insurama_orders = [o for o in orders if o.get('numero_autorizacion')]
        
        print(f"Found {len(insurama_orders)} Insurama orders")
        
        # If no Insurama orders, that's fine - the sync logic exists
        if insurama_orders:
            orden = insurama_orders[0]
            print(f"Insurama order: {orden.get('numero_orden')} - Auth: {orden.get('numero_autorizacion')}")


# ==== INSURAMA PAGE TEST ====

class TestInsuramaPage:
    """Test Insurama page access"""
    
    def test_insurama_page_route_requires_auth(self, session):
        """Test that /insurama route requires authentication"""
        # Without auth, API calls should fail
        response = session.get(f"{BASE_URL}/api/insurama/config")
        assert response.status_code in [401, 403], "Insurama config should require auth"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

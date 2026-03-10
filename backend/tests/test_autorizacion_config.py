"""
Test suite for numero_autorizacion feature and Configuracion page
Tests:
- P0: numero_autorizacion - crear orden con número de autorización y verificar que se guarda y muestra correctamente
- P0: numero_autorizacion - búsqueda por número de autorización en lista de órdenes
- P0: numero_autorizacion - visualización del número de autorización en página de detalle de orden
- P1: Página de Configuración - verificar que carga correctamente y muestra estado de integraciones
- P1: API de configuración - GET /api/configuracion/notificaciones devuelve estado de Twilio y SendGrid
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestNumeroAutorizacion:
    """Tests for numero_autorizacion feature in orders"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Store created resources for cleanup
        self.created_cliente_id = None
        self.created_orden_id = None
        
        yield
        
        # Cleanup
        if self.created_orden_id:
            try:
                self.session.delete(f"{BASE_URL}/api/ordenes/{self.created_orden_id}")
            except:
                pass
        if self.created_cliente_id:
            try:
                self.session.delete(f"{BASE_URL}/api/clientes/{self.created_cliente_id}")
            except:
                pass
    
    def test_create_order_with_numero_autorizacion(self):
        """P0: Create order with numero_autorizacion and verify it's saved correctly"""
        # First create a test client
        unique_id = str(uuid.uuid4())[:8]
        cliente_data = {
            "nombre": f"TEST_Cliente_{unique_id}",
            "apellidos": "Autorizacion",
            "dni": f"TEST{unique_id}",
            "telefono": "600123456",
            "email": f"test_{unique_id}@test.com",
            "direccion": "Calle Test 123"
        }
        
        cliente_response = self.session.post(f"{BASE_URL}/api/clientes", json=cliente_data)
        assert cliente_response.status_code == 200, f"Failed to create client: {cliente_response.text}"
        cliente = cliente_response.json()
        self.created_cliente_id = cliente["id"]
        
        # Create order with numero_autorizacion
        test_auth_number = f"AUTH-TEST-{unique_id}"
        orden_data = {
            "cliente_id": cliente["id"],
            "dispositivo": {
                "modelo": "iPhone 15 Pro Test",
                "imei": "123456789012345",
                "color": "Negro",
                "daños": "Pantalla rota - Test autorización"
            },
            "agencia_envio": "SEUR",
            "codigo_recogida_entrada": f"SEUR{unique_id}",
            "numero_autorizacion": test_auth_number,
            "materiales": [],
            "notas": "Test order for numero_autorizacion"
        }
        
        orden_response = self.session.post(f"{BASE_URL}/api/ordenes", json=orden_data)
        assert orden_response.status_code == 200, f"Failed to create order: {orden_response.text}"
        orden = orden_response.json()
        self.created_orden_id = orden["id"]
        
        # Verify numero_autorizacion is saved
        assert orden.get("numero_autorizacion") == test_auth_number, \
            f"numero_autorizacion not saved correctly. Expected: {test_auth_number}, Got: {orden.get('numero_autorizacion')}"
        
        print(f"SUCCESS: Order created with numero_autorizacion: {test_auth_number}")
        print(f"Order ID: {orden['id']}, Numero Orden: {orden['numero_orden']}")
        
        # Verify by fetching the order again
        get_response = self.session.get(f"{BASE_URL}/api/ordenes/{orden['id']}")
        assert get_response.status_code == 200
        fetched_orden = get_response.json()
        assert fetched_orden.get("numero_autorizacion") == test_auth_number, \
            "numero_autorizacion not persisted correctly in database"
        
        print("SUCCESS: numero_autorizacion persisted and retrieved correctly")
    
    def test_search_order_by_numero_autorizacion(self):
        """P0: Search orders by numero_autorizacion"""
        # First create a test client and order with unique auth number
        unique_id = str(uuid.uuid4())[:8]
        cliente_data = {
            "nombre": f"TEST_Search_{unique_id}",
            "apellidos": "Busqueda",
            "dni": f"SRCH{unique_id}",
            "telefono": "600654321",
            "email": f"search_{unique_id}@test.com",
            "direccion": "Calle Busqueda 456"
        }
        
        cliente_response = self.session.post(f"{BASE_URL}/api/clientes", json=cliente_data)
        assert cliente_response.status_code == 200
        cliente = cliente_response.json()
        self.created_cliente_id = cliente["id"]
        
        # Create order with unique numero_autorizacion
        unique_auth = f"SEARCH-AUTH-{unique_id}"
        orden_data = {
            "cliente_id": cliente["id"],
            "dispositivo": {
                "modelo": "Samsung Galaxy S24",
                "imei": "987654321098765",
                "color": "Azul",
                "daños": "Batería defectuosa"
            },
            "agencia_envio": "MRW",
            "codigo_recogida_entrada": f"MRW{unique_id}",
            "numero_autorizacion": unique_auth,
            "materiales": [],
            "notas": "Test order for search by autorizacion"
        }
        
        orden_response = self.session.post(f"{BASE_URL}/api/ordenes", json=orden_data)
        assert orden_response.status_code == 200
        orden = orden_response.json()
        self.created_orden_id = orden["id"]
        
        # Search by numero_autorizacion using the autorizacion parameter
        search_response = self.session.get(f"{BASE_URL}/api/ordenes", params={"autorizacion": unique_auth})
        assert search_response.status_code == 200, f"Search failed: {search_response.text}"
        
        results = search_response.json()
        assert len(results) >= 1, f"Expected at least 1 result, got {len(results)}"
        
        # Verify our order is in the results
        found = False
        for result in results:
            if result.get("numero_autorizacion") == unique_auth:
                found = True
                break
        
        assert found, f"Order with numero_autorizacion '{unique_auth}' not found in search results"
        print(f"SUCCESS: Search by numero_autorizacion '{unique_auth}' returned {len(results)} result(s)")
        
        # Also test general search includes numero_autorizacion
        general_search_response = self.session.get(f"{BASE_URL}/api/ordenes", params={"search": unique_auth})
        assert general_search_response.status_code == 200
        general_results = general_search_response.json()
        
        found_in_general = any(r.get("numero_autorizacion") == unique_auth for r in general_results)
        assert found_in_general, "numero_autorizacion not found in general search"
        print(f"SUCCESS: General search also finds order by numero_autorizacion")
    
    def test_order_detail_shows_numero_autorizacion(self):
        """P0: Verify numero_autorizacion is visible in order detail"""
        # Create test client and order
        unique_id = str(uuid.uuid4())[:8]
        cliente_data = {
            "nombre": f"TEST_Detail_{unique_id}",
            "apellidos": "Detalle",
            "dni": f"DTL{unique_id}",
            "telefono": "600111222",
            "email": f"detail_{unique_id}@test.com",
            "direccion": "Calle Detalle 789"
        }
        
        cliente_response = self.session.post(f"{BASE_URL}/api/clientes", json=cliente_data)
        assert cliente_response.status_code == 200
        cliente = cliente_response.json()
        self.created_cliente_id = cliente["id"]
        
        # Create order with numero_autorizacion
        detail_auth = f"DETAIL-AUTH-{unique_id}"
        orden_data = {
            "cliente_id": cliente["id"],
            "dispositivo": {
                "modelo": "Google Pixel 8",
                "imei": "111222333444555",
                "color": "Verde",
                "daños": "Cámara no funciona"
            },
            "agencia_envio": "GLS",
            "codigo_recogida_entrada": f"GLS{unique_id}",
            "numero_autorizacion": detail_auth,
            "materiales": [],
            "notas": "Test order for detail view"
        }
        
        orden_response = self.session.post(f"{BASE_URL}/api/ordenes", json=orden_data)
        assert orden_response.status_code == 200
        orden = orden_response.json()
        self.created_orden_id = orden["id"]
        
        # Get order detail
        detail_response = self.session.get(f"{BASE_URL}/api/ordenes/{orden['id']}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        
        # Verify all expected fields are present
        assert "numero_autorizacion" in detail, "numero_autorizacion field missing from order detail"
        assert detail["numero_autorizacion"] == detail_auth, \
            f"numero_autorizacion mismatch. Expected: {detail_auth}, Got: {detail['numero_autorizacion']}"
        
        # Verify other important fields
        assert detail.get("numero_orden") is not None, "numero_orden missing"
        assert detail.get("estado") is not None, "estado missing"
        assert detail.get("dispositivo") is not None, "dispositivo missing"
        
        print(f"SUCCESS: Order detail contains numero_autorizacion: {detail['numero_autorizacion']}")
        print(f"Order fields verified: numero_orden={detail['numero_orden']}, estado={detail['estado']}")


class TestConfiguracionPage:
    """Tests for Configuracion page and API"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_get_configuracion_notificaciones(self):
        """P1: GET /api/configuracion/notificaciones returns Twilio and SendGrid status"""
        response = self.session.get(f"{BASE_URL}/api/configuracion/notificaciones")
        assert response.status_code == 200, f"Failed to get config: {response.text}"
        
        config = response.json()
        
        # Verify structure
        assert "twilio" in config, "twilio section missing from config"
        assert "sendgrid" in config, "sendgrid section missing from config"
        
        # Verify Twilio fields
        twilio = config["twilio"]
        assert "configurado" in twilio, "twilio.configurado field missing"
        assert "account_sid" in twilio, "twilio.account_sid field missing"
        assert "phone_number" in twilio, "twilio.phone_number field missing"
        
        # Verify SendGrid fields
        sendgrid = config["sendgrid"]
        assert "configurado" in sendgrid, "sendgrid.configurado field missing"
        assert "api_key" in sendgrid, "sendgrid.api_key field missing"
        assert "from_email" in sendgrid, "sendgrid.from_email field missing"
        
        print(f"SUCCESS: Configuration API returns correct structure")
        print(f"Twilio configured: {twilio['configurado']}")
        print(f"SendGrid configured: {sendgrid['configurado']}")
        
        # Based on backend/.env, both should be configured
        if twilio['configurado']:
            print(f"Twilio Account SID (masked): {twilio['account_sid']}")
            print(f"Twilio Phone: {twilio['phone_number']}")
        
        if sendgrid['configurado']:
            print(f"SendGrid API Key (masked): {sendgrid['api_key']}")
            print(f"SendGrid From Email: {sendgrid['from_email']}")
    
    def test_configuracion_requires_admin(self):
        """P1: Verify configuracion endpoint requires admin role"""
        # Try without auth
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.get(f"{BASE_URL}/api/configuracion/notificaciones")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("SUCCESS: Endpoint correctly requires authentication")
        
        # Try with tecnico (non-admin)
        tecnico_login = no_auth_session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "tecnico",
            "password": "tecnico123"
        })
        
        if tecnico_login.status_code == 200:
            tecnico_token = tecnico_login.json()["token"]
            no_auth_session.headers.update({"Authorization": f"Bearer {tecnico_token}"})
            
            response = no_auth_session.get(f"{BASE_URL}/api/configuracion/notificaciones")
            assert response.status_code == 403, f"Expected 403 for tecnico, got {response.status_code}"
            print("SUCCESS: Endpoint correctly requires admin role")


class TestExistingOrderWithAutorizacion:
    """Test the existing order mentioned in the context"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        self.token = login_response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_search_existing_order_by_auth_number(self):
        """Search for the existing order with AUTH-2025-001"""
        # Search by the auth number mentioned in context
        search_response = self.session.get(f"{BASE_URL}/api/ordenes", params={"autorizacion": "AUTH-2025-001"})
        assert search_response.status_code == 200
        
        results = search_response.json()
        print(f"Search for AUTH-2025-001 returned {len(results)} result(s)")
        
        if len(results) > 0:
            for orden in results:
                print(f"  - Order: {orden.get('numero_orden')}, Auth: {orden.get('numero_autorizacion')}")
        else:
            print("  No orders found with AUTH-2025-001 (may have been cleaned up)")
    
    def test_list_all_orders_with_autorizacion(self):
        """List all orders and check which have numero_autorizacion"""
        response = self.session.get(f"{BASE_URL}/api/ordenes")
        assert response.status_code == 200
        
        ordenes = response.json()
        orders_with_auth = [o for o in ordenes if o.get("numero_autorizacion")]
        
        print(f"Total orders: {len(ordenes)}")
        print(f"Orders with numero_autorizacion: {len(orders_with_auth)}")
        
        for orden in orders_with_auth[:5]:  # Show first 5
            print(f"  - {orden.get('numero_orden')}: Auth={orden.get('numero_autorizacion')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

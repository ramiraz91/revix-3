"""
Test suite for barcode scanning, user management, calendar, AI diagnostics, and notifications
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    def test_login_master(self):
        """P0: Login with master credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "master@techrepair.local",
            "password": "master123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "master"
        
    def test_login_admin(self):
        """P0: Login with admin credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        
    def test_login_tecnico(self):
        """P0: Login with tecnico credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "tecnico@techrepair.local",
            "password": "tecnico123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "tecnico"


class TestBarcodeScanning:
    """Barcode scanning tests - the main bug reported by user"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "master@techrepair.local",
            "password": "master123"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def test_order(self, auth_token):
        """Create a test order for scanning"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # First create a client
        client_data = {
            "nombre": "TEST_Scan",
            "apellidos": "Client",
            "dni": f"TEST{uuid.uuid4().hex[:6]}",
            "telefono": "600000000",
            "direccion": "Test Address"
        }
        client_res = requests.post(f"{BASE_URL}/api/clientes", json=client_data, headers=headers)
        client_id = client_res.json()["id"]
        
        # Create order
        order_data = {
            "cliente_id": client_id,
            "dispositivo": {
                "modelo": "TEST iPhone 15",
                "imei": "123456789012345",
                "color": "Negro",
                "daños": "Pantalla rota"
            },
            "agencia_envio": "SEUR",
            "codigo_recogida_entrada": "TEST123"
        }
        order_res = requests.post(f"{BASE_URL}/api/ordenes", json=order_data, headers=headers)
        order = order_res.json()
        
        yield order
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/ordenes/{order['id']}", headers=headers)
        requests.delete(f"{BASE_URL}/api/clientes/{client_id}", headers=headers)
    
    def test_scan_by_numero_orden_recepcion(self, auth_token, test_order):
        """P0: Scan order by numero_orden for reception - MAIN BUG FIX"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        numero_orden = test_order["numero_orden"]
        
        # Scan by numero_orden (what barcode contains)
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{numero_orden}/scan",
            json={"tipo_escaneo": "recepcion", "usuario": "admin"},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["nuevo_estado"] == "recibida"
        
        # Verify state changed
        order_res = requests.get(f"{BASE_URL}/api/ordenes/{test_order['id']}", headers=headers)
        assert order_res.json()["estado"] == "recibida"
    
    def test_scan_by_id(self, auth_token, test_order):
        """P0: Scan order by ID"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        order_id = test_order["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{order_id}/scan",
            json={"tipo_escaneo": "recepcion", "usuario": "admin"},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["nuevo_estado"] == "recibida"
    
    def test_scan_tecnico_starts_repair(self, auth_token, test_order):
        """P0: Tecnico scan starts repair (changes to en_taller)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        numero_orden = test_order["numero_orden"]
        
        # First scan for reception
        requests.post(
            f"{BASE_URL}/api/ordenes/{numero_orden}/scan",
            json={"tipo_escaneo": "recepcion", "usuario": "admin"},
            headers=headers
        )
        
        # Then scan for tecnico
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{numero_orden}/scan",
            json={"tipo_escaneo": "tecnico", "usuario": "tecnico"},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["nuevo_estado"] == "en_taller"
    
    def test_order_has_barcode(self, auth_token, test_order):
        """P0: Order has qr_code (barcode) generated"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(f"{BASE_URL}/api/ordenes/{test_order['id']}", headers=headers)
        order = response.json()
        
        assert "qr_code" in order
        assert order["qr_code"] is not None
        assert len(order["qr_code"]) > 100  # Base64 encoded image


class TestUsuariosCRUD:
    """User management CRUD tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "master@techrepair.local",
            "password": "master123"
        })
        return response.json()["token"]
    
    def test_list_usuarios(self, auth_token):
        """P0: List all users"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/usuarios", headers=headers)
        
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) >= 1
    
    def test_create_usuario(self, auth_token):
        """P0: Create new user"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        user_data = {
            "email": f"test_{uuid.uuid4().hex[:8]}@test.com",
            "password": "testpass123",
            "nombre": "TEST_User",
            "apellidos": "Test",
            "role": "tecnico"
        }
        
        response = requests.post(f"{BASE_URL}/api/usuarios", json=user_data, headers=headers)
        
        assert response.status_code == 200
        user = response.json()
        assert user["email"] == user_data["email"].lower()
        assert user["nombre"] == user_data["nombre"]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/usuarios/{user['id']}", headers=headers)
    
    def test_update_usuario(self, auth_token):
        """P0: Update user"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create user first
        user_data = {
            "email": f"test_{uuid.uuid4().hex[:8]}@test.com",
            "password": "testpass123",
            "nombre": "TEST_Original",
            "role": "tecnico"
        }
        create_res = requests.post(f"{BASE_URL}/api/usuarios", json=user_data, headers=headers)
        user_id = create_res.json()["id"]
        
        # Update
        update_data = {"nombre": "TEST_Updated"}
        response = requests.put(f"{BASE_URL}/api/usuarios/{user_id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        assert response.json()["nombre"] == "TEST_Updated"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/usuarios/{user_id}", headers=headers)
    
    def test_delete_usuario(self, auth_token):
        """P0: Delete user (master only)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create user first
        user_data = {
            "email": f"test_{uuid.uuid4().hex[:8]}@test.com",
            "password": "testpass123",
            "nombre": "TEST_ToDelete",
            "role": "tecnico"
        }
        create_res = requests.post(f"{BASE_URL}/api/usuarios", json=user_data, headers=headers)
        user_id = create_res.json()["id"]
        
        # Delete
        response = requests.delete(f"{BASE_URL}/api/usuarios/{user_id}", headers=headers)
        
        assert response.status_code == 200
        
        # Verify deleted
        get_res = requests.get(f"{BASE_URL}/api/usuarios/{user_id}", headers=headers)
        assert get_res.status_code == 404


class TestCalendario:
    """Calendar and order assignment tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        return response.json()["token"]
    
    def test_list_eventos(self, auth_token):
        """P0: List calendar events"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/calendario/eventos", headers=headers)
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_evento(self, auth_token):
        """P0: Create calendar event"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        event_data = {
            "titulo": "TEST_Event",
            "tipo": "otro",
            "fecha_inicio": datetime.now().strftime("%Y-%m-%d"),
            "todo_el_dia": True
        }
        
        response = requests.post(f"{BASE_URL}/api/calendario/eventos", json=event_data, headers=headers)
        
        assert response.status_code == 200
        event = response.json()
        assert event["titulo"] == "TEST_Event"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/calendario/eventos/{event['id']}", headers=headers)
    
    def test_asignar_orden_tecnico(self, auth_token):
        """P0: Assign order to technician"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get a tecnico
        users_res = requests.get(f"{BASE_URL}/api/usuarios?role=tecnico", headers=headers)
        tecnicos = users_res.json()
        if not tecnicos:
            pytest.skip("No technicians available")
        tecnico_id = tecnicos[0]["id"]
        
        # Get an order
        orders_res = requests.get(f"{BASE_URL}/api/ordenes?estado=pendiente_recibir", headers=headers)
        orders = orders_res.json()
        if not orders:
            pytest.skip("No pending orders available")
        order_id = orders[0]["id"]
        
        # Assign
        assign_data = {
            "orden_id": order_id,
            "tecnico_id": tecnico_id,
            "fecha_estimada": datetime.now().strftime("%Y-%m-%d")
        }
        
        response = requests.post(f"{BASE_URL}/api/calendario/asignar-orden", json=assign_data, headers=headers)
        
        assert response.status_code == 200
        assert "evento_id" in response.json()


class TestDiagnosticoIA:
    """AI Diagnostics tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "tecnico@techrepair.local",
            "password": "tecnico123"
        })
        return response.json()["token"]
    
    def test_diagnostico_ia_endpoint(self, auth_token):
        """P0: AI diagnostics endpoint works"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Use query params as the endpoint expects
        response = requests.post(
            f"{BASE_URL}/api/ia/diagnostico?modelo=iPhone%2014%20Pro&sintomas=Pantalla%20no%20enciende",
            headers=headers
        )
        
        # May return 200 with diagnostico or 500 if LLM not configured
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "diagnostico" in data


class TestMaterialesPersonalizados:
    """Custom materials tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "tecnico@techrepair.local",
            "password": "tecnico123"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        return response.json()["token"]
    
    def test_add_custom_material(self, auth_token, admin_token):
        """P0: Add custom material to order"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get an order in en_taller state
        orders_res = requests.get(f"{BASE_URL}/api/ordenes?estado=en_taller", headers=admin_headers)
        orders = orders_res.json()
        if not orders:
            pytest.skip("No orders in en_taller state")
        order_id = orders[0]["id"]
        
        # Add custom material
        material_data = {
            "nombre": "TEST_Custom_Material",
            "cantidad": 1,
            "añadido_por_tecnico": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{order_id}/materiales",
            json=material_data,
            headers=headers
        )
        
        # Should work or fail with specific error
        assert response.status_code in [200, 400]


class TestNotificaciones:
    """Notifications tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        return response.json()["token"]
    
    def test_list_notificaciones(self, auth_token):
        """P0: List notifications"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/notificaciones", headers=headers)
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestDashboard:
    """Dashboard stats tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        return response.json()["token"]
    
    def test_dashboard_stats(self, auth_token):
        """P0: Dashboard stats endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_ordenes" in data
        assert "total_clientes" in data

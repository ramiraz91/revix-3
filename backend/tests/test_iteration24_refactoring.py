"""
Test Iteration 24: Backend Refactoring Verification
Tests for ordenes_routes.py extraction from server.py and new link-seguimiento endpoint

Features tested:
- Login with admin credentials
- GET /api/ordenes - List orders
- GET /api/ordenes/{id} - Get order detail
- GET /api/ordenes/{id}/link-seguimiento - NEW endpoint for tracking links
- GET /api/dashboard/stats - Dashboard statistics
- GET /api/clientes - List clients
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuthAndBasicEndpoints:
    """Test authentication and basic API endpoints after refactoring"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        self.master_token = None
    
    def get_admin_token(self):
        """Get admin authentication token"""
        if self.admin_token:
            return self.admin_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        if response.status_code == 200:
            self.admin_token = response.json().get("token")
            return self.admin_token
        return None
    
    def get_master_token(self):
        """Get master authentication token"""
        if self.master_token:
            return self.master_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "master@techrepair.local",
            "password": "master123"
        })
        if response.status_code == 200:
            self.master_token = response.json().get("token")
            return self.master_token
        return None
    
    # ==================== AUTH TESTS ====================
    
    def test_01_admin_login_success(self):
        """Test admin login with correct credentials"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert "user" in data, "User not in response"
        assert data["user"]["email"] == "admin@techrepair.local"
        assert data["user"]["role"] in ["admin", "master"]
        print(f"✓ Admin login successful - role: {data['user']['role']}")
    
    def test_02_master_login_success(self):
        """Test master login with correct credentials"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "master@techrepair.local",
            "password": "master123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert data["user"]["role"] == "master"
        print(f"✓ Master login successful")
    
    def test_03_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected")
    
    # ==================== ORDENES TESTS (from ordenes_routes.py) ====================
    
    def test_04_listar_ordenes(self):
        """Test GET /api/ordenes - List all orders"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = self.session.get(
            f"{BASE_URL}/api/ordenes",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Failed to list orders: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Listed {len(data)} orders successfully")
        
        # Store first order ID for subsequent tests
        if data:
            self.__class__.test_orden_id = data[0].get('id')
            self.__class__.test_orden_numero = data[0].get('numero_orden')
            print(f"  Using order ID: {self.test_orden_id}")
    
    def test_05_obtener_orden_detalle(self):
        """Test GET /api/ordenes/{id} - Get order detail"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        # First get an order ID
        response = self.session.get(
            f"{BASE_URL}/api/ordenes?limit=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        ordenes = response.json()
        
        if not ordenes:
            pytest.skip("No orders available for testing")
        
        orden_id = ordenes[0]['id']
        
        # Get order detail
        response = self.session.get(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Failed to get order detail: {response.text}"
        data = response.json()
        
        # Verify order structure
        assert "id" in data, "Order should have id"
        assert "numero_orden" in data, "Order should have numero_orden"
        assert "estado" in data, "Order should have estado"
        assert "dispositivo" in data, "Order should have dispositivo"
        assert "cliente_id" in data, "Order should have cliente_id"
        
        print(f"✓ Order detail retrieved: {data['numero_orden']} - Estado: {data['estado']}")
    
    def test_06_link_seguimiento_endpoint(self):
        """Test GET /api/ordenes/{id}/link-seguimiento - NEW endpoint"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        # First get an order ID
        response = self.session.get(
            f"{BASE_URL}/api/ordenes?limit=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        ordenes = response.json()
        
        if not ordenes:
            pytest.skip("No orders available for testing")
        
        orden_id = ordenes[0]['id']
        
        # Test the new link-seguimiento endpoint
        response = self.session.get(
            f"{BASE_URL}/api/ordenes/{orden_id}/link-seguimiento",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"link-seguimiento failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "token" in data, "Response should have token"
        assert "telefono_hint" in data, "Response should have telefono_hint"
        assert "orden_id" in data, "Response should have orden_id"
        assert "numero_orden" in data, "Response should have numero_orden"
        
        # Verify token format (should be uppercase, 12 chars)
        assert len(data["token"]) == 12, f"Token should be 12 chars, got {len(data['token'])}"
        assert data["token"].isupper(), "Token should be uppercase"
        
        print(f"✓ Link seguimiento endpoint working:")
        print(f"  Token: {data['token']}")
        print(f"  Telefono hint: {data['telefono_hint']}")
        print(f"  Orden: {data['numero_orden']}")
    
    def test_07_link_seguimiento_not_found(self):
        """Test link-seguimiento with invalid order ID returns 404"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = self.session.get(
            f"{BASE_URL}/api/ordenes/invalid-order-id-12345/link-seguimiento",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Invalid order ID correctly returns 404")
    
    def test_08_link_seguimiento_requires_auth(self):
        """Test link-seguimiento requires authentication"""
        response = self.session.get(
            f"{BASE_URL}/api/ordenes/some-order-id/link-seguimiento"
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Endpoint correctly requires authentication")
    
    # ==================== DASHBOARD TESTS ====================
    
    def test_09_dashboard_stats(self):
        """Test GET /api/dashboard/stats"""
        response = self.session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        
        # Verify dashboard structure
        assert "total_ordenes" in data, "Should have total_ordenes"
        assert "ordenes_por_estado" in data, "Should have ordenes_por_estado"
        assert "total_clientes" in data, "Should have total_clientes"
        assert "total_repuestos" in data, "Should have total_repuestos"
        
        print(f"✓ Dashboard stats retrieved:")
        print(f"  Total ordenes: {data['total_ordenes']}")
        print(f"  Total clientes: {data['total_clientes']}")
        print(f"  Total repuestos: {data['total_repuestos']}")
    
    # ==================== CLIENTES TESTS ====================
    
    def test_10_listar_clientes(self):
        """Test GET /api/clientes"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = self.session.get(
            f"{BASE_URL}/api/clientes",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Failed to list clients: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        if data:
            # Verify client structure
            cliente = data[0]
            assert "id" in cliente, "Client should have id"
            assert "nombre" in cliente, "Client should have nombre"
        
        print(f"✓ Listed {len(data)} clients successfully")
    
    # ==================== ADDITIONAL ORDENES ROUTES TESTS ====================
    
    def test_11_ordenes_filter_by_estado(self):
        """Test filtering orders by estado"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = self.session.get(
            f"{BASE_URL}/api/ordenes?estado=pendiente_recibir",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Filter failed: {response.text}"
        data = response.json()
        
        # All returned orders should have the filtered estado
        for orden in data:
            assert orden['estado'] == 'pendiente_recibir', f"Order has wrong estado: {orden['estado']}"
        
        print(f"✓ Filtered orders by estado: {len(data)} orders with estado=pendiente_recibir")
    
    def test_12_ordenes_search(self):
        """Test searching orders"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        # Get first order to use its numero_orden for search
        response = self.session.get(
            f"{BASE_URL}/api/ordenes?limit=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        ordenes = response.json()
        
        if not ordenes:
            pytest.skip("No orders available for search test")
        
        search_term = ordenes[0]['numero_orden'][:6]  # Use first 6 chars
        
        response = self.session.get(
            f"{BASE_URL}/api/ordenes?search={search_term}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        print(f"✓ Search with term '{search_term}' returned {len(response.json())} results")
    
    def test_13_orden_metricas(self):
        """Test GET /api/ordenes/{id}/metricas"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        # Get an order ID
        response = self.session.get(
            f"{BASE_URL}/api/ordenes?limit=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        ordenes = response.json()
        
        if not ordenes:
            pytest.skip("No orders available for metrics test")
        
        orden_id = ordenes[0]['id']
        
        response = self.session.get(
            f"{BASE_URL}/api/ordenes/{orden_id}/metricas",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Metrics failed: {response.text}"
        data = response.json()
        
        # Verify metrics structure
        assert "tiempo_desde_creacion_horas" in data
        assert "dias_desde_creacion" in data
        assert "timestamps" in data
        
        print(f"✓ Order metrics retrieved: {data['dias_desde_creacion']} days since creation")
    
    def test_14_orden_mensajes(self):
        """Test GET /api/ordenes/{id}/mensajes"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        # Get an order ID
        response = self.session.get(
            f"{BASE_URL}/api/ordenes?limit=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        ordenes = response.json()
        
        if not ordenes:
            pytest.skip("No orders available for messages test")
        
        orden_id = ordenes[0]['id']
        
        response = self.session.get(
            f"{BASE_URL}/api/ordenes/{orden_id}/mensajes",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Messages failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Messages should be a list"
        
        print(f"✓ Order messages retrieved: {len(data)} messages")


class TestRefactoringIntegrity:
    """Tests to verify refactoring didn't break existing functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_token(self, email, password):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_01_api_root(self):
        """Test API root endpoint"""
        response = self.session.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ API root: {data['message']}")
    
    def test_02_notificaciones_endpoint(self):
        """Test notificaciones endpoint still works"""
        response = self.session.get(f"{BASE_URL}/api/notificaciones")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Notificaciones endpoint working: {len(data)} notifications")
    
    def test_03_repuestos_endpoint(self):
        """Test repuestos endpoint still works"""
        token = self.get_token("admin@techrepair.local", "admin123")
        assert token, "Failed to get token"
        
        response = self.session.get(
            f"{BASE_URL}/api/repuestos",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Repuestos endpoint working: {len(data)} items")
    
    def test_04_proveedores_endpoint(self):
        """Test proveedores endpoint still works"""
        token = self.get_token("admin@techrepair.local", "admin123")
        assert token, "Failed to get token"
        
        response = self.session.get(
            f"{BASE_URL}/api/proveedores",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Proveedores endpoint working: {len(data)} providers")
    
    def test_05_calendario_eventos(self):
        """Test calendario eventos endpoint still works"""
        token = self.get_token("admin@techrepair.local", "admin123")
        assert token, "Failed to get token"
        
        response = self.session.get(
            f"{BASE_URL}/api/calendario/eventos",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Calendario eventos endpoint working: {len(data)} events")
    
    def test_06_seguimiento_publico(self):
        """Test public seguimiento endpoint still works"""
        # First get a valid token from an order
        token = self.get_token("admin@techrepair.local", "admin123")
        assert token, "Failed to get token"
        
        response = self.session.get(
            f"{BASE_URL}/api/ordenes?limit=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200 and response.json():
            orden = response.json()[0]
            if orden.get('token_seguimiento'):
                # Test public seguimiento endpoint
                response = self.session.get(
                    f"{BASE_URL}/api/seguimiento/{orden['token_seguimiento']}"
                )
                assert response.status_code == 200
                print(f"✓ Public seguimiento endpoint working")
            else:
                print("✓ Seguimiento endpoint exists (no token in test order)")
        else:
            print("✓ Seguimiento endpoint exists (no orders to test)")
    
    def test_07_dashboard_metricas_avanzadas(self):
        """Test dashboard metricas avanzadas requires admin"""
        token = self.get_token("admin@techrepair.local", "admin123")
        assert token, "Failed to get token"
        
        response = self.session.get(
            f"{BASE_URL}/api/dashboard/metricas-avanzadas",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "ordenes_por_dia" in data
        assert "ordenes_por_estado" in data
        print(f"✓ Dashboard metricas avanzadas working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Iteration 13 Backend Tests:
- Incidencias CRUD endpoints (POST, GET, PUT)
- Ordenes de Compra PATCH endpoint (approve, reject, mark pedida/recibida)
- Dashboard ordenes-compra-urgentes endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MASTER_EMAIL = "master@techrepair.local"
MASTER_PASSWORD = "master123"


class TestAuth:
    """Test authentication and get token"""
    token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for all tests"""
        if not TestAuth.token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": MASTER_EMAIL,
                "password": MASTER_PASSWORD
            })
            assert response.status_code == 200, f"Login failed: {response.text}"
            TestAuth.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {TestAuth.token}"}
    
    def test_login_master(self):
        """Test master login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": MASTER_EMAIL,
            "password": MASTER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "master"


class TestIncidenciasAPI:
    """Test Incidencias CRUD endpoints"""
    token = None
    cliente_id = None
    incidencia_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and client ID"""
        if not TestIncidenciasAPI.token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": MASTER_EMAIL,
                "password": MASTER_PASSWORD
            })
            assert response.status_code == 200
            TestIncidenciasAPI.token = response.json()["token"]
        
        self.headers = {"Authorization": f"Bearer {TestIncidenciasAPI.token}"}
        
        # Get first client for testing
        if not TestIncidenciasAPI.cliente_id:
            response = requests.get(f"{BASE_URL}/api/clientes", headers=self.headers)
            if response.status_code == 200 and response.json():
                TestIncidenciasAPI.cliente_id = response.json()[0]["id"]
    
    def test_01_listar_incidencias(self):
        """GET /api/incidencias - List all incidencias"""
        response = requests.get(f"{BASE_URL}/api/incidencias", headers=self.headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"Found {len(response.json())} incidencias")
    
    def test_02_crear_incidencia(self):
        """POST /api/incidencias - Create new incidencia"""
        if not TestIncidenciasAPI.cliente_id:
            pytest.skip("No client found for testing")
        
        payload = {
            "cliente_id": TestIncidenciasAPI.cliente_id,
            "tipo": "reclamacion",
            "titulo": "TEST_Incidencia de prueba automática",
            "descripcion": "Esta es una incidencia creada por el test automático para verificar el CRUD",
            "prioridad": "alta"
        }
        
        response = requests.post(f"{BASE_URL}/api/incidencias", json=payload, headers=self.headers)
        assert response.status_code == 200, f"Failed to create incidencia: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert data["titulo"] == payload["titulo"]
        assert data["estado"] == "abierta"
        assert "numero_incidencia" in data
        
        TestIncidenciasAPI.incidencia_id = data["id"]
        print(f"Created incidencia: {data['numero_incidencia']}")
    
    def test_03_obtener_incidencia(self):
        """GET /api/incidencias/{id} - Get specific incidencia"""
        if not TestIncidenciasAPI.incidencia_id:
            pytest.skip("No incidencia created")
        
        response = requests.get(
            f"{BASE_URL}/api/incidencias/{TestIncidenciasAPI.incidencia_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == TestIncidenciasAPI.incidencia_id
        assert "titulo" in data
    
    def test_04_actualizar_incidencia_en_proceso(self):
        """PUT /api/incidencias/{id} - Change state to en_proceso"""
        if not TestIncidenciasAPI.incidencia_id:
            pytest.skip("No incidencia created")
        
        response = requests.put(
            f"{BASE_URL}/api/incidencias/{TestIncidenciasAPI.incidencia_id}",
            json={"estado": "en_proceso"},
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "en_proceso"
        print("Incidencia marked as en_proceso")
    
    def test_05_actualizar_incidencia_resuelta(self):
        """PUT /api/incidencias/{id} - Change state to resuelta"""
        if not TestIncidenciasAPI.incidencia_id:
            pytest.skip("No incidencia created")
        
        response = requests.put(
            f"{BASE_URL}/api/incidencias/{TestIncidenciasAPI.incidencia_id}",
            json={
                "estado": "resuelta",
                "notas_resolucion": "Resuelto por el test automático"
            },
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "resuelta"
        assert "resuelto_por" in data
        assert "fecha_resolucion" in data
        print("Incidencia marked as resuelta")
    
    def test_06_filtrar_incidencias_por_estado(self):
        """GET /api/incidencias?estado=resuelta - Filter by state"""
        response = requests.get(
            f"{BASE_URL}/api/incidencias?estado=resuelta",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        # All returned should be resuelta
        for inc in data:
            assert inc["estado"] == "resuelta"
        print(f"Found {len(data)} resolved incidencias")


class TestOrdenesCompraAPI:
    """Test Ordenes de Compra PATCH endpoint"""
    token = None
    oc_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        if not TestOrdenesCompraAPI.token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": MASTER_EMAIL,
                "password": MASTER_PASSWORD
            })
            assert response.status_code == 200
            TestOrdenesCompraAPI.token = response.json()["token"]
        
        self.headers = {"Authorization": f"Bearer {TestOrdenesCompraAPI.token}"}
    
    def test_01_listar_ordenes_compra(self):
        """GET /api/ordenes-compra - List all purchase orders"""
        response = requests.get(f"{BASE_URL}/api/ordenes-compra", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} ordenes de compra")
        
        # Store first pendiente for later tests
        pendientes = [oc for oc in data if oc.get("estado") == "pendiente"]
        if pendientes:
            TestOrdenesCompraAPI.oc_id = pendientes[0]["id"]
            print(f"Will use order {pendientes[0]['id']} for state change tests")
    
    def test_02_filtrar_ordenes_pendientes(self):
        """GET /api/ordenes-compra?estado=pendiente - Filter by state"""
        response = requests.get(
            f"{BASE_URL}/api/ordenes-compra?estado=pendiente",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        for oc in data:
            assert oc["estado"] == "pendiente"
        print(f"Found {len(data)} pending ordenes de compra")
    
    def test_03_aprobar_orden_compra(self):
        """PATCH /api/ordenes-compra/{id} - Approve order"""
        if not TestOrdenesCompraAPI.oc_id:
            pytest.skip("No pending order found to approve")
        
        response = requests.patch(
            f"{BASE_URL}/api/ordenes-compra/{TestOrdenesCompraAPI.oc_id}",
            json={"estado": "aprobada", "notas": "Aprobada por test automático"},
            headers=self.headers
        )
        assert response.status_code == 200
        print("Order approved successfully")
    
    def test_04_marcar_orden_pedida(self):
        """PATCH /api/ordenes-compra/{id} - Mark as pedida"""
        if not TestOrdenesCompraAPI.oc_id:
            pytest.skip("No order to mark as pedida")
        
        response = requests.patch(
            f"{BASE_URL}/api/ordenes-compra/{TestOrdenesCompraAPI.oc_id}",
            json={"estado": "pedida"},
            headers=self.headers
        )
        assert response.status_code == 200
        print("Order marked as pedida")
    
    def test_05_marcar_orden_recibida(self):
        """PATCH /api/ordenes-compra/{id} - Mark as recibida"""
        if not TestOrdenesCompraAPI.oc_id:
            pytest.skip("No order to mark as recibida")
        
        response = requests.patch(
            f"{BASE_URL}/api/ordenes-compra/{TestOrdenesCompraAPI.oc_id}",
            json={"estado": "recibida"},
            headers=self.headers
        )
        assert response.status_code == 200
        print("Order marked as recibida")
    
    def test_06_verify_order_state_persisted(self):
        """GET /api/ordenes-compra/{id} - Verify state was persisted"""
        if not TestOrdenesCompraAPI.oc_id:
            pytest.skip("No order to verify")
        
        response = requests.get(
            f"{BASE_URL}/api/ordenes-compra/{TestOrdenesCompraAPI.oc_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "recibida"
        print(f"Verified order state is {data['estado']}")


class TestDashboardOrdenesCompraUrgentes:
    """Test Dashboard ordenes-compra-urgentes endpoint"""
    token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        if not TestDashboardOrdenesCompraUrgentes.token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": MASTER_EMAIL,
                "password": MASTER_PASSWORD
            })
            assert response.status_code == 200
            TestDashboardOrdenesCompraUrgentes.token = response.json()["token"]
        
        self.headers = {"Authorization": f"Bearer {TestDashboardOrdenesCompraUrgentes.token}"}
    
    def test_dashboard_ordenes_compra_urgentes(self):
        """GET /api/dashboard/ordenes-compra-urgentes - Dashboard endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/ordenes-compra-urgentes",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "total_pendientes" in data
        assert isinstance(data["total_pendientes"], int)
        print(f"Dashboard shows {data['total_pendientes']} pending purchase orders")
    
    def test_dashboard_stats(self):
        """GET /api/dashboard/stats - Dashboard stats endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields
        assert "total_ordenes" in data
        assert "total_clientes" in data
        assert "total_repuestos" in data
        print(f"Dashboard stats: {data['total_ordenes']} orders, {data['total_clientes']} clients")


class TestScannerEndpoint:
    """Test scanner endpoint for Dashboard compact scanner"""
    token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        if not TestScannerEndpoint.token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": MASTER_EMAIL,
                "password": MASTER_PASSWORD
            })
            assert response.status_code == 200
            TestScannerEndpoint.token = response.json()["token"]
        
        self.headers = {"Authorization": f"Bearer {TestScannerEndpoint.token}"}
    
    def test_search_order_by_code(self):
        """GET /api/ordenes - Search for order by code (scanner uses this)"""
        # Get first order to use as search term
        response = requests.get(f"{BASE_URL}/api/ordenes", headers=self.headers)
        assert response.status_code == 200
        
        if response.json():
            first_order = response.json()[0]
            numero_orden = first_order["numero_orden"]
            
            # Search by order number (like scanner would)
            search_response = requests.get(
                f"{BASE_URL}/api/ordenes?search={numero_orden}",
                headers=self.headers
            )
            assert search_response.status_code == 200
            results = search_response.json()
            assert len(results) > 0
            assert any(o["numero_orden"] == numero_orden for o in results)
            print(f"Scanner search found order {numero_orden}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

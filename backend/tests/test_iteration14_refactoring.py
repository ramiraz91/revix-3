"""
Iteration 14 Backend Tests
Tests for:
1. Backend refactoring verification - all routes still work after split
2. Login with 3 accounts (master, admin, tecnico)
3. Dashboard stats and metricas-avanzadas
4. Ordenes CRUD
5. Clientes CRUD
6. Master-only /master/analiticas endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')
if not BASE_URL:
    BASE_URL = "https://workshop-manager-75.preview.emergentagent.com"

# Test credentials
MASTER_CREDS = {"email": "master@techrepair.local", "password": "master123"}
ADMIN_CREDS = {"email": "admin@techrepair.local", "password": "admin123"}
TECNICO_CREDS = {"email": "tecnico@techrepair.local", "password": "tecnico123"}


class TestBackendRefactoring:
    """Test that basic API is working after refactoring"""
    
    def test_api_root_accessible(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"API root accessible: {data}")
    
    def test_health_check(self):
        """Test basic connectivity"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200


class TestAuthentication:
    """Test login with all 3 user types"""
    
    def test_login_master(self):
        """Test master login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MASTER_CREDS)
        assert response.status_code == 200, f"Master login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "master"
        assert data["user"]["email"] == MASTER_CREDS["email"]
        print(f"Master login successful: {data['user']['nombre']}")
        
    def test_login_admin(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "admin"
        assert data["user"]["email"] == ADMIN_CREDS["email"]
        print(f"Admin login successful: {data['user']['nombre']}")
        
    def test_login_tecnico(self):
        """Test tecnico login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TECNICO_CREDS)
        assert response.status_code == 200, f"Tecnico login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "tecnico"
        assert data["user"]["email"] == TECNICO_CREDS["email"]
        print(f"Tecnico login successful: {data['user']['nombre']}")
    
    def test_login_invalid_credentials(self):
        """Test invalid login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrong"
        })
        assert response.status_code == 401


class TestDashboardEndpoints:
    """Test dashboard stats and metricas"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        # Get master token for all tests
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MASTER_CREDS)
        self.master_token = response.json()["token"]
        self.master_headers = {"Authorization": f"Bearer {self.master_token}"}
        
        # Get admin token
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        self.admin_token = response.json()["token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_dashboard_stats(self):
        """Test /dashboard/stats endpoint returns correct data"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=self.master_headers)
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "total_ordenes" in data
        assert "ordenes_por_estado" in data
        assert "total_clientes" in data
        assert "total_repuestos" in data
        assert "notificaciones_pendientes" in data
        
        print(f"Dashboard stats: ordenes={data['total_ordenes']}, clientes={data['total_clientes']}, repuestos={data['total_repuestos']}")
    
    def test_dashboard_metricas_avanzadas_admin(self):
        """Test /dashboard/metricas-avanzadas with admin - should work"""
        response = requests.get(f"{BASE_URL}/api/dashboard/metricas-avanzadas", headers=self.admin_headers)
        assert response.status_code == 200, f"Metricas avanzadas failed: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "ordenes_por_dia" in data
        assert "ordenes_por_estado" in data
        assert "ratios" in data
        assert "tiempos" in data
        assert "comparativa" in data
        
        # Verify ratios structure
        assert "total" in data["ratios"]
        assert "completadas" in data["ratios"]
        assert "canceladas" in data["ratios"]
        assert "ratio_completado" in data["ratios"]
        
        # Verify tiempos structure
        assert "promedio_reparacion_horas" in data["tiempos"]
        assert "promedio_total_horas" in data["tiempos"]
        
        print(f"Metricas avanzadas: ratios={data['ratios']}, tiempos={data['tiempos']}")


class TestOrdenesAPI:
    """Test ordenes CRUD endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        # Get admin token
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        self.admin_token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_listar_ordenes(self):
        """Test GET /ordenes"""
        response = requests.get(f"{BASE_URL}/api/ordenes", headers=self.headers)
        assert response.status_code == 200, f"Listar ordenes failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Total ordenes: {len(data)}")
        
        if data:
            # Verify order structure
            orden = data[0]
            assert "id" in orden
            assert "numero_orden" in orden
            assert "estado" in orden
            assert "cliente_id" in orden
    
    def test_crear_y_obtener_orden(self):
        """Test POST /ordenes and GET /ordenes/{id}"""
        # First get a cliente
        clientes_resp = requests.get(f"{BASE_URL}/api/clientes", headers=self.headers)
        if clientes_resp.status_code != 200 or not clientes_resp.json():
            pytest.skip("No clientes available for testing")
        
        cliente_id = clientes_resp.json()[0]["id"]
        
        # Create order
        orden_data = {
            "cliente_id": cliente_id,
            "dispositivo": {
                "modelo": "TEST iPhone 14 Pro",
                "imei": "123456789012345",
                "color": "Space Black",
                "daños": "Pantalla rota"
            },
            "agencia_envio": "MRW",
            "codigo_recogida_entrada": "TEST-123",
            "notas": "Orden de prueba iteration 14"
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=self.headers)
        assert create_resp.status_code == 200, f"Create orden failed: {create_resp.text}"
        created = create_resp.json()
        
        assert "id" in created
        assert "numero_orden" in created
        assert created["dispositivo"]["modelo"] == "TEST iPhone 14 Pro"
        
        orden_id = created["id"]
        print(f"Created orden: {created['numero_orden']}")
        
        # Get order by id
        get_resp = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=self.headers)
        assert get_resp.status_code == 200, f"Get orden failed: {get_resp.text}"
        fetched = get_resp.json()
        
        assert fetched["id"] == orden_id
        assert fetched["numero_orden"] == created["numero_orden"]
        
        # Clean up - delete order
        del_resp = requests.delete(f"{BASE_URL}/api/ordenes/{orden_id}", headers=self.headers)
        assert del_resp.status_code == 200
        print(f"Deleted test orden: {created['numero_orden']}")


class TestClientesAPI:
    """Test clientes CRUD endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        self.admin_token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_listar_clientes(self):
        """Test GET /clientes"""
        response = requests.get(f"{BASE_URL}/api/clientes", headers=self.headers)
        assert response.status_code == 200, f"Listar clientes failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Total clientes: {len(data)}")
        
        if data:
            cliente = data[0]
            assert "id" in cliente
            assert "nombre" in cliente
            assert "telefono" in cliente
    
    def test_crear_y_eliminar_cliente(self):
        """Test POST /clientes and DELETE"""
        cliente_data = {
            "nombre": "TEST",
            "apellidos": "Cliente Prueba",
            "dni": "TEST12345X",
            "telefono": "600000000",
            "email": "test_iter14@test.com",
            "direccion": "Calle Test 123"
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/clientes", json=cliente_data, headers=self.headers)
        assert create_resp.status_code == 200, f"Create cliente failed: {create_resp.text}"
        created = create_resp.json()
        
        assert "id" in created
        assert created["nombre"] == "TEST"
        
        cliente_id = created["id"]
        print(f"Created cliente: {created['nombre']} {created['apellidos']}")
        
        # Delete
        del_resp = requests.delete(f"{BASE_URL}/api/clientes/{cliente_id}", headers=self.headers)
        assert del_resp.status_code == 200
        print(f"Deleted test cliente")


class TestMasterOnlyEndpoints:
    """Test endpoints that require master role"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        # Get master token
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MASTER_CREDS)
        self.master_token = response.json()["token"]
        self.master_headers = {"Authorization": f"Bearer {self.master_token}"}
        
        # Get admin token
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        self.admin_token = response.json()["token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Get tecnico token
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TECNICO_CREDS)
        self.tecnico_token = response.json()["token"]
        self.tecnico_headers = {"Authorization": f"Bearer {self.tecnico_token}"}
    
    def test_master_analiticas_with_master(self):
        """Test /master/analiticas with master - should succeed"""
        response = requests.get(f"{BASE_URL}/api/master/analiticas", headers=self.master_headers)
        assert response.status_code == 200, f"Master analiticas failed: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "ingresos_por_mes" in data
        assert "tiempo_medio_reparacion_horas" in data
        assert "ranking_tecnicos" in data
        assert "distribucion_estado" in data
        assert "ordenes_por_mes" in data
        assert "total_ordenes" in data
        assert "total_completadas" in data
        assert "total_en_proceso" in data
        
        print(f"Master analiticas: total={data['total_ordenes']}, completadas={data['total_completadas']}")
    
    def test_master_analiticas_with_admin_denied(self):
        """Test /master/analiticas with admin - should be denied"""
        response = requests.get(f"{BASE_URL}/api/master/analiticas", headers=self.admin_headers)
        assert response.status_code == 403, f"Admin should be denied access to master/analiticas, got: {response.status_code}"
        print("Admin correctly denied access to /master/analiticas")
    
    def test_master_analiticas_with_tecnico_denied(self):
        """Test /master/analiticas with tecnico - should be denied"""
        response = requests.get(f"{BASE_URL}/api/master/analiticas", headers=self.tecnico_headers)
        assert response.status_code == 403, f"Tecnico should be denied access to master/analiticas, got: {response.status_code}"
        print("Tecnico correctly denied access to /master/analiticas")
    
    def test_configuracion_notificaciones_master_only(self):
        """Test /configuracion/notificaciones with master"""
        response = requests.get(f"{BASE_URL}/api/configuracion/notificaciones", headers=self.master_headers)
        assert response.status_code == 200, f"Config notificaciones failed: {response.text}"
        print("Master can access configuracion notificaciones")
    
    def test_configuracion_notificaciones_admin_denied(self):
        """Test /configuracion/notificaciones with admin - should be denied"""
        response = requests.get(f"{BASE_URL}/api/configuracion/notificaciones", headers=self.admin_headers)
        assert response.status_code == 403, f"Admin should be denied, got: {response.status_code}"
        print("Admin correctly denied access to /configuracion/notificaciones")


class TestRouteIntegrity:
    """Verify key routes still work after refactoring"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MASTER_CREDS)
        self.master_token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.master_token}"}
    
    def test_usuarios_endpoint(self):
        """Test /usuarios (moved to auth_routes)"""
        response = requests.get(f"{BASE_URL}/api/usuarios", headers=self.headers)
        assert response.status_code == 200, f"Usuarios failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Total usuarios: {len(data)}")
    
    def test_repuestos_endpoint(self):
        """Test /repuestos (moved to data_routes)"""
        response = requests.get(f"{BASE_URL}/api/repuestos", headers=self.headers)
        assert response.status_code == 200, f"Repuestos failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Total repuestos: {len(data)}")
    
    def test_proveedores_endpoint(self):
        """Test /proveedores (moved to data_routes)"""
        response = requests.get(f"{BASE_URL}/api/proveedores", headers=self.headers)
        assert response.status_code == 200, f"Proveedores failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Total proveedores: {len(data)}")
    
    def test_incidencias_endpoint(self):
        """Test /incidencias (moved to data_routes)"""
        response = requests.get(f"{BASE_URL}/api/incidencias", headers=self.headers)
        assert response.status_code == 200, f"Incidencias failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Total incidencias: {len(data)}")
    
    def test_ordenes_compra_endpoint(self):
        """Test /ordenes-compra (moved to data_routes)"""
        response = requests.get(f"{BASE_URL}/api/ordenes-compra", headers=self.headers)
        assert response.status_code == 200, f"Ordenes compra failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Total ordenes compra: {len(data)}")
    
    def test_notificaciones_endpoint(self):
        """Test /notificaciones (still in server.py)"""
        response = requests.get(f"{BASE_URL}/api/notificaciones", headers=self.headers)
        assert response.status_code == 200, f"Notificaciones failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Total notificaciones: {len(data)}")
    
    def test_calendario_eventos(self):
        """Test /calendario/eventos (still in server.py)"""
        response = requests.get(f"{BASE_URL}/api/calendario/eventos", headers=self.headers)
        assert response.status_code == 200, f"Calendario failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Total eventos calendario: {len(data)}")
    
    def test_dashboard_alertas_stock(self):
        """Test /dashboard/alertas-stock (still in server.py)"""
        response = requests.get(f"{BASE_URL}/api/dashboard/alertas-stock", headers=self.headers)
        assert response.status_code == 200, f"Alertas stock failed: {response.text}"
        data = response.json()
        assert "alertas" in data
        print(f"Stock alertas: critico={data.get('total_critico', 0)}, bajo={data.get('total_bajo', 0)}")
    
    def test_dashboard_ordenes_compra_urgentes(self):
        """Test /dashboard/ordenes-compra-urgentes (still in server.py)"""
        response = requests.get(f"{BASE_URL}/api/dashboard/ordenes-compra-urgentes", headers=self.headers)
        assert response.status_code == 200, f"OC urgentes failed: {response.text}"
        data = response.json()
        assert "total_pendientes" in data
        assert "ordenes" in data
        print(f"Ordenes compra pendientes: {data['total_pendientes']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

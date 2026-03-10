"""
Test suite for new CRM/ERP features:
- Diagnóstico del técnico
- Rol Master con métricas y facturación
- Configuración de empresa e IVA
- Gestión de dispositivos de restos
- Nuevos estados: reemplazo e irreparable
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests for all roles"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful, role: {data['user']['role']}")
    
    def test_tecnico_login(self):
        """Test tecnico login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "tecnico",
            "password": "tecnico123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "tecnico"
        print(f"✓ Tecnico login successful, role: {data['user']['role']}")
    
    def test_master_login(self):
        """Test master login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "master",
            "password": "master123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "master"
        print(f"✓ Master login successful, role: {data['user']['role']}")


class TestDiagnosticoTecnico:
    """Tests for technician diagnostic feature"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def tecnico_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "tecnico",
            "password": "tecnico123"
        })
        return response.json()["token"]
    
    def test_get_existing_order_with_diagnostico(self, admin_token):
        """Test getting an existing order that may have diagnostico"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/ordenes", headers=headers)
        assert response.status_code == 200
        ordenes = response.json()
        if ordenes:
            orden = ordenes[0]
            print(f"✓ Found order: {orden.get('numero_orden')}")
            print(f"  Diagnostico: {orden.get('diagnostico_tecnico', 'No diagnostico')}")
    
    def test_save_diagnostico_as_tecnico(self, tecnico_token):
        """Test saving diagnostic as technician"""
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        
        # Get an order first
        response = requests.get(f"{BASE_URL}/api/ordenes", headers=headers)
        assert response.status_code == 200
        ordenes = response.json()
        
        if ordenes:
            orden_id = ordenes[0]["id"]
            test_diagnostico = f"TEST_DIAGNOSTICO_{uuid.uuid4().hex[:8]}: Pantalla dañada, se requiere reemplazo completo."
            
            # Save diagnostic
            response = requests.patch(
                f"{BASE_URL}/api/ordenes/{orden_id}/diagnostico",
                json={"diagnostico": test_diagnostico},
                headers=headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["diagnostico"] == test_diagnostico
            print(f"✓ Diagnostico saved successfully for order {ordenes[0]['numero_orden']}")
            
            # Verify it was saved
            response = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=headers)
            assert response.status_code == 200
            orden = response.json()
            assert orden["diagnostico_tecnico"] == test_diagnostico
            print(f"✓ Diagnostico verified in order data")
        else:
            pytest.skip("No orders available for testing")


class TestMasterPanel:
    """Tests for Master panel features"""
    
    @pytest.fixture
    def master_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "master",
            "password": "master123"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def tecnico_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "tecnico",
            "password": "tecnico123"
        })
        return response.json()["token"]
    
    def test_metricas_tecnicos_as_master(self, master_token):
        """Test getting technician metrics as master"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.get(f"{BASE_URL}/api/master/metricas-tecnicos", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Metricas tecnicos returned {len(data)} technicians")
        for tech in data:
            print(f"  - {tech.get('nombre')}: {tech.get('total_ordenes')} orders, {tech.get('tasa_exito')}% success")
    
    def test_metricas_tecnicos_denied_for_admin(self, admin_token):
        """Test that admin cannot access master metrics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/master/metricas-tecnicos", headers=headers)
        assert response.status_code == 403
        print("✓ Admin correctly denied access to master metrics")
    
    def test_metricas_tecnicos_denied_for_tecnico(self, tecnico_token):
        """Test that tecnico cannot access master metrics"""
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        response = requests.get(f"{BASE_URL}/api/master/metricas-tecnicos", headers=headers)
        assert response.status_code == 403
        print("✓ Tecnico correctly denied access to master metrics")
    
    def test_facturacion_as_master(self, master_token):
        """Test getting billing data as master"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.get(f"{BASE_URL}/api/master/facturacion", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "desglose" in data
        assert "ordenes_facturadas" in data
        assert "periodo" in data
        print(f"✓ Facturacion data retrieved:")
        print(f"  - Total: {data['desglose']['total']}€")
        print(f"  - Materiales: {data['desglose']['materiales']}€")
        print(f"  - Mano de obra: {data['desglose']['mano_obra']}€")
        print(f"  - IVA ({data['desglose']['iva_porcentaje']}%): {data['desglose']['iva_importe']}€")
    
    def test_facturacion_with_date_filter(self, master_token):
        """Test billing data with date filter"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.get(
            f"{BASE_URL}/api/master/facturacion?fecha_desde=2025-01-01&fecha_hasta=2026-12-31",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["periodo"]["desde"] == "2025-01-01"
        assert data["periodo"]["hasta"] == "2026-12-31"
        print(f"✓ Facturacion with date filter works correctly")


class TestEmpresaConfig:
    """Tests for company configuration"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def tecnico_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "tecnico",
            "password": "tecnico123"
        })
        return response.json()["token"]
    
    def test_get_empresa_config(self, admin_token):
        """Test getting company configuration"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Empresa config retrieved: {data.get('nombre', 'No name set')}")
    
    def test_save_empresa_config(self, admin_token):
        """Test saving company configuration"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        config = {
            "nombre": "TEST_TechRepair S.L.",
            "cif": "B12345678",
            "direccion": "Calle Test 123",
            "ciudad": "Madrid",
            "codigo_postal": "28001",
            "telefono": "+34 912 345 678",
            "email": "test@techrepair.es",
            "web": "https://techrepair.es",
            "tipos_iva": [
                {"nombre": "General", "porcentaje": 21.0, "activo": True},
                {"nombre": "Reducido", "porcentaje": 10.0, "activo": True},
                {"nombre": "Superreducido", "porcentaje": 4.0, "activo": True},
                {"nombre": "Exento", "porcentaje": 0.0, "activo": True}
            ],
            "iva_por_defecto": 21.0
        }
        response = requests.post(
            f"{BASE_URL}/api/configuracion/empresa",
            json=config,
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ Empresa config saved successfully")
        
        # Verify it was saved
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa", headers=headers)
        assert response.status_code == 200
        saved = response.json()
        assert saved.get("nombre") == "TEST_TechRepair S.L."
        print(f"✓ Empresa config verified: {saved.get('nombre')}")
    
    def test_empresa_config_denied_for_tecnico(self, tecnico_token):
        """Test that tecnico cannot access empresa config"""
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa", headers=headers)
        assert response.status_code == 403
        print("✓ Tecnico correctly denied access to empresa config")


class TestRestos:
    """Tests for leftover devices management"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        return response.json()["token"]
    
    def test_create_resto(self, admin_token):
        """Test creating a leftover device"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resto_data = {
            "modelo": f"TEST_iPhone 12 Pro_{uuid.uuid4().hex[:6]}",
            "imei": "123456789012345",
            "color": "Negro",
            "estado_fisico": "regular",
            "descripcion": "Dispositivo de prueba para testing",
            "piezas_aprovechables": ["Pantalla", "Batería", "Cámara trasera"],
            "ubicacion_almacen": "Estante A-1"
        }
        response = requests.post(
            f"{BASE_URL}/api/restos",
            json=resto_data,
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "codigo" in data
        assert data["modelo"] == resto_data["modelo"]
        print(f"✓ Resto created: {data['codigo']} - {data['modelo']}")
        return data["id"]
    
    def test_list_restos(self, admin_token):
        """Test listing leftover devices"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/restos", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} restos")
        for resto in data[:3]:
            print(f"  - {resto.get('codigo')}: {resto.get('modelo')} ({resto.get('estado_fisico')})")
    
    def test_search_restos(self, admin_token):
        """Test searching leftover devices"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/restos?search=TEST_", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Search returned {len(data)} results")
    
    def test_delete_resto(self, admin_token):
        """Test deleting (deactivating) a leftover device"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First create one to delete
        resto_data = {
            "modelo": f"TEST_DELETE_{uuid.uuid4().hex[:6]}",
            "estado_fisico": "malo",
            "piezas_aprovechables": []
        }
        create_response = requests.post(
            f"{BASE_URL}/api/restos",
            json=resto_data,
            headers=headers
        )
        assert create_response.status_code == 200
        resto_id = create_response.json()["id"]
        
        # Now delete it
        response = requests.delete(f"{BASE_URL}/api/restos/{resto_id}", headers=headers)
        assert response.status_code == 200
        print(f"✓ Resto deleted (deactivated) successfully")


class TestNewOrderStates:
    """Tests for new order states: reemplazo and irreparable"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        return response.json()["token"]
    
    def test_change_to_reemplazo_state(self, admin_token):
        """Test changing order to reemplazo state"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get an order
        response = requests.get(f"{BASE_URL}/api/ordenes", headers=headers)
        assert response.status_code == 200
        ordenes = response.json()
        
        if ordenes:
            orden_id = ordenes[0]["id"]
            original_state = ordenes[0]["estado"]
            
            # Change to reemplazo
            response = requests.patch(
                f"{BASE_URL}/api/ordenes/{orden_id}/estado",
                json={"nuevo_estado": "reemplazo", "usuario": "admin_test"},
                headers=headers
            )
            assert response.status_code == 200
            print(f"✓ Order changed to 'reemplazo' state")
            
            # Verify
            response = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=headers)
            assert response.status_code == 200
            orden = response.json()
            assert orden["estado"] == "reemplazo"
            print(f"✓ State verified as 'reemplazo'")
            
            # Restore original state
            requests.patch(
                f"{BASE_URL}/api/ordenes/{orden_id}/estado",
                json={"nuevo_estado": original_state, "usuario": "admin_test"},
                headers=headers
            )
        else:
            pytest.skip("No orders available for testing")
    
    def test_change_to_irreparable_state(self, admin_token):
        """Test changing order to irreparable state"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get an order
        response = requests.get(f"{BASE_URL}/api/ordenes", headers=headers)
        assert response.status_code == 200
        ordenes = response.json()
        
        if ordenes:
            orden_id = ordenes[0]["id"]
            original_state = ordenes[0]["estado"]
            
            # Change to irreparable
            response = requests.patch(
                f"{BASE_URL}/api/ordenes/{orden_id}/estado",
                json={"nuevo_estado": "irreparable", "usuario": "admin_test"},
                headers=headers
            )
            assert response.status_code == 200
            print(f"✓ Order changed to 'irreparable' state")
            
            # Verify
            response = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=headers)
            assert response.status_code == 200
            orden = response.json()
            assert orden["estado"] == "irreparable"
            print(f"✓ State verified as 'irreparable'")
            
            # Restore original state
            requests.patch(
                f"{BASE_URL}/api/ordenes/{orden_id}/estado",
                json={"nuevo_estado": original_state, "usuario": "admin_test"},
                headers=headers
            )
        else:
            pytest.skip("No orders available for testing")


class TestTecnicoDashboardBugFix:
    """Test that technician orders open correctly from dashboard"""
    
    @pytest.fixture
    def tecnico_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "tecnico",
            "password": "tecnico123"
        })
        return response.json()["token"]
    
    def test_tecnico_can_access_order(self, tecnico_token):
        """Test that technician can access order details"""
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        
        # Get orders
        response = requests.get(f"{BASE_URL}/api/ordenes", headers=headers)
        assert response.status_code == 200
        ordenes = response.json()
        
        if ordenes:
            orden_id = ordenes[0]["id"]
            
            # Access order detail
            response = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=headers)
            assert response.status_code == 200
            orden = response.json()
            assert orden["id"] == orden_id
            print(f"✓ Tecnico can access order: {orden['numero_orden']}")
        else:
            pytest.skip("No orders available for testing")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

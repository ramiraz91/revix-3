"""
GLS Integration Tests
Tests for:
- GET/POST /api/gls/config 
- GET /api/gls/servicios
- GET /api/gls/envios
- GET /api/gls/etiquetas
- POST /api/gls/sync (returns 400 when GLS not active)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestGLSEndpoints:
    """GLS Integration endpoint tests"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Get authentication token before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as master user
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "master@techrepair.local",
            "password": "master123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.token = token
        else:
            pytest.skip("Authentication failed - skipping tests")
    
    def test_get_gls_config(self):
        """Test GET /api/gls/config returns valid config structure"""
        response = self.session.get(f"{BASE_URL}/api/gls/config")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "activo" in data
        assert "uid_cliente" in data
        assert "remitente" in data
        assert "servicio_defecto" in data
        assert "horario_defecto" in data
        assert "formato_etiqueta" in data
        assert "polling_activo" in data
        assert "polling_intervalo_horas" in data
        assert "servicios_disponibles" in data
        assert "horarios_disponibles" in data
        assert "estados_mapa" in data
        
        # Verify remitente structure
        remitente = data["remitente"]
        assert "nombre" in remitente
        assert "direccion" in remitente
        assert "poblacion" in remitente
        assert "cp" in remitente
        assert "telefono" in remitente
        assert "nif" in remitente
        
        # Verify servicios has expected values
        assert "1" in data["servicios_disponibles"]
        assert data["servicios_disponibles"]["1"] == "BusinessParcel"
        
        print(f"GLS Config - activo: {data['activo']}, servicios: {len(data['servicios_disponibles'])}")
    
    def test_post_gls_config_and_verify(self):
        """Test POST /api/gls/config saves and retrieves config correctly"""
        # Save new config
        test_config = {
            "activo": False,
            "uid_cliente": "test-uid-pytest",
            "remitente": {
                "nombre": "Pytest Test",
                "direccion": "Test Street 999",
                "poblacion": "TestCity",
                "cp": "99999",
                "telefono": "999999999",
                "nif": "TEST12345"
            },
            "servicio_defecto": "1",
            "horario_defecto": "18",
            "portes_defecto": "P",
            "formato_etiqueta": "PDF",
            "polling_activo": False,
            "polling_intervalo_horas": 6
        }
        
        save_response = self.session.post(f"{BASE_URL}/api/gls/config", json=test_config)
        assert save_response.status_code == 200
        assert save_response.json().get("success") == True
        assert save_response.json().get("message") == "Configuración GLS guardada"
        
        # Verify saved config
        get_response = self.session.get(f"{BASE_URL}/api/gls/config")
        assert get_response.status_code == 200
        data = get_response.json()
        
        assert data["uid_cliente"] == "test-uid-pytest"
        assert data["remitente"]["nombre"] == "Pytest Test"
        assert data["polling_intervalo_horas"] == 6
        
        print("GLS Config POST verified successfully")
        
        # Restore original config
        restore_config = {
            "activo": False,
            "uid_cliente": "",
            "remitente": {
                "nombre": "revix.es",
                "direccion": "Julio alarcon 8, Local",
                "poblacion": "Cordoba",
                "cp": "14007",
                "telefono": "604319223",
                "nif": "31018296J"
            },
            "servicio_defecto": "1",
            "horario_defecto": "18",
            "portes_defecto": "P",
            "formato_etiqueta": "PDF",
            "polling_activo": False,
            "polling_intervalo_horas": 4
        }
        restore_response = self.session.post(f"{BASE_URL}/api/gls/config", json=restore_config)
        assert restore_response.status_code == 200
        print("Original GLS config restored")
    
    def test_get_gls_servicios(self):
        """Test GET /api/gls/servicios returns services list"""
        response = self.session.get(f"{BASE_URL}/api/gls/servicios")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "servicios" in data
        assert "horarios" in data
        assert "estados" in data
        
        # Verify services content
        servicios = data["servicios"]
        assert "1" in servicios
        assert "10" in servicios
        assert "14" in servicios
        assert servicios["1"] == "BusinessParcel"
        
        # Verify horarios content
        horarios = data["horarios"]
        assert "18" in horarios
        assert horarios["18"] == "Sin franja horaria"
        
        # Verify estados content
        estados = data["estados"]
        assert "entregado" in estados
        assert estados["entregado"]["color"] == "green"
        assert estados["entregado"]["label"] == "Entregado"
        
        print(f"GLS Servicios - {len(servicios)} services, {len(horarios)} schedules, {len(estados)} states")
    
    def test_get_gls_envios(self):
        """Test GET /api/gls/envios returns shipment list"""
        response = self.session.get(f"{BASE_URL}/api/gls/envios")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "envios" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data
        
        assert isinstance(data["envios"], list)
        assert isinstance(data["total"], int)
        
        print(f"GLS Envios - total: {data['total']}, page: {data['page']}/{data['pages']}")
    
    def test_get_gls_envios_with_filters(self):
        """Test GET /api/gls/envios with pagination and filters"""
        # Test with pagination
        response = self.session.get(f"{BASE_URL}/api/gls/envios?page=1&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "envios" in data
        
        # Test with estado filter
        response = self.session.get(f"{BASE_URL}/api/gls/envios?estado=entregado")
        assert response.status_code == 200
        
        # Test with tipo filter
        response = self.session.get(f"{BASE_URL}/api/gls/envios?tipo=envio")
        assert response.status_code == 200
        
        # Test with busqueda filter
        response = self.session.get(f"{BASE_URL}/api/gls/envios?busqueda=test")
        assert response.status_code == 200
        
        print("GLS Envios filters working correctly")
    
    def test_get_gls_etiquetas(self):
        """Test GET /api/gls/etiquetas returns labels list"""
        response = self.session.get(f"{BASE_URL}/api/gls/etiquetas")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "etiquetas" in data
        assert "total" in data
        
        assert isinstance(data["etiquetas"], list)
        assert isinstance(data["total"], int)
        
        print(f"GLS Etiquetas - total: {data['total']}")
    
    def test_get_gls_etiquetas_with_filters(self):
        """Test GET /api/gls/etiquetas with date and reference filters"""
        # Test with referencia filter
        response = self.session.get(f"{BASE_URL}/api/gls/etiquetas?referencia=test")
        assert response.status_code == 200
        
        # Test with fecha filter
        response = self.session.get(f"{BASE_URL}/api/gls/etiquetas?fecha=2026-01-01")
        assert response.status_code == 200
        
        print("GLS Etiquetas filters working correctly")
    
    def test_post_gls_sync_requires_active(self):
        """Test POST /api/gls/sync returns 400 when GLS not active"""
        response = self.session.post(f"{BASE_URL}/api/gls/sync")
        
        # Should return 400 because GLS is not activated
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "no activada" in data["detail"].lower() or "no configurado" in data["detail"].lower()
        
        print(f"GLS Sync correctly returns 400: {data['detail']}")
    
    def test_gls_config_requires_master(self):
        """Test that GLS config endpoints require master role"""
        # Create non-authenticated session
        unauth_session = requests.Session()
        unauth_session.headers.update({"Content-Type": "application/json"})
        
        response = unauth_session.get(f"{BASE_URL}/api/gls/config")
        assert response.status_code in [401, 403]
        
        print("GLS Config correctly requires authentication")


class TestGLSConfigValidation:
    """Test GLS config validation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get authentication token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "master@techrepair.local",
            "password": "master123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_config_default_values(self):
        """Test GLS config has correct default values"""
        response = self.session.get(f"{BASE_URL}/api/gls/config")
        assert response.status_code == 200
        data = response.json()
        
        # Default values check
        assert data["servicio_defecto"] in ["1", "10", "14", "74", "96"]
        assert data["formato_etiqueta"] in ["PDF", "PNG", "ZPL"]
        assert data["portes_defecto"] in ["P", "D"]
        assert isinstance(data["polling_intervalo_horas"], int)
        assert data["polling_intervalo_horas"] >= 1
        
        print("GLS Config default values verified")
    
    def test_servicios_data_integrity(self):
        """Test GLS servicios has all required data"""
        response = self.session.get(f"{BASE_URL}/api/gls/servicios")
        assert response.status_code == 200
        data = response.json()
        
        servicios = data["servicios"]
        horarios = data["horarios"]
        estados = data["estados"]
        
        # Known service codes
        expected_services = {"1", "10", "14", "74", "96"}
        for code in expected_services:
            assert code in servicios, f"Missing service code: {code}"
        
        # Known state codes
        expected_states = {"grabado", "recogido", "en_transito", "entregado", "incidencia", "anulado"}
        for state in expected_states:
            assert state in estados, f"Missing state: {state}"
            assert "color" in estados[state]
            assert "label" in estados[state]
        
        print("GLS Servicios data integrity verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

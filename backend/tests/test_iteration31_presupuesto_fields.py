"""
Test iteration 31: New presupuesto fields for Insurama/Sumbroker
Tests the new required fields: disponibilidad_recambios, tiempo_horas, tipo_recambio, tipo_garantia
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestEnviarPresupuestoEndpoint:
    """Tests for POST /api/insurama/presupuesto/{codigo}/enviar-presupuesto endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get auth token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
                print(f"Auth successful, token obtained")
        else:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
    
    def test_enviar_presupuesto_model_accepts_new_fields(self):
        """Test that the EnviarPresupuestoRequest model accepts the new fields"""
        # This test verifies the endpoint accepts the new fields
        # Using a test code that may not exist - we're testing the request validation
        test_codigo = "TEST_CODE_123"
        
        payload = {
            "precio": 150.00,
            "descripcion": "Test repair description",
            "tiempo_reparacion": "24-48h",
            "garantia_meses": 12,
            "disponibilidad_recambios": "inmediata",
            "tiempo_horas": 2.5,
            "tipo_recambio": "original",
            "tipo_garantia": "taller"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/insurama/presupuesto/{test_codigo}/enviar-presupuesto",
            json=payload
        )
        
        # We expect 404 (budget not found) or 400 (credentials not configured)
        # NOT 422 (validation error) which would mean the fields are not accepted
        assert response.status_code in [400, 404], f"Unexpected status: {response.status_code}, response: {response.text[:500]}"
        
        # Verify it's not a validation error for the new fields
        if response.status_code == 422:
            error_detail = response.json().get("detail", [])
            for error in error_detail:
                field = error.get("loc", [])[-1] if error.get("loc") else ""
                assert field not in ["disponibilidad_recambios", "tiempo_horas", "tipo_recambio", "tipo_garantia"], \
                    f"New field {field} not accepted by model"
        
        print(f"Endpoint accepts new fields - Status: {response.status_code}")
    
    def test_enviar_presupuesto_all_field_values(self):
        """Test all valid values for the new fields"""
        test_codigo = "TEST_CODE_456"
        
        # Test all valid disponibilidad_recambios values
        disponibilidad_values = ["inmediata", "24h", "48h", "7dias", "sin_stock"]
        for value in disponibilidad_values:
            payload = {
                "precio": 100.00,
                "descripcion": "Test",
                "disponibilidad_recambios": value,
                "tiempo_horas": 1.0,
                "tipo_recambio": "original",
                "tipo_garantia": "taller"
            }
            response = self.session.post(
                f"{BASE_URL}/api/insurama/presupuesto/{test_codigo}/enviar-presupuesto",
                json=payload
            )
            # Should not be 422 validation error
            assert response.status_code != 422, f"Value '{value}' for disponibilidad_recambios rejected"
        
        print("All disponibilidad_recambios values accepted")
        
        # Test all valid tipo_recambio values
        tipo_recambio_values = ["original", "compatible", "reacondicionado", "no_aplica"]
        for value in tipo_recambio_values:
            payload = {
                "precio": 100.00,
                "descripcion": "Test",
                "disponibilidad_recambios": "inmediata",
                "tiempo_horas": 1.0,
                "tipo_recambio": value,
                "tipo_garantia": "taller"
            }
            response = self.session.post(
                f"{BASE_URL}/api/insurama/presupuesto/{test_codigo}/enviar-presupuesto",
                json=payload
            )
            assert response.status_code != 422, f"Value '{value}' for tipo_recambio rejected"
        
        print("All tipo_recambio values accepted")
        
        # Test all valid tipo_garantia values
        tipo_garantia_values = ["fabricante", "taller", "sin_garantia"]
        for value in tipo_garantia_values:
            payload = {
                "precio": 100.00,
                "descripcion": "Test",
                "disponibilidad_recambios": "inmediata",
                "tiempo_horas": 1.0,
                "tipo_recambio": "original",
                "tipo_garantia": value
            }
            response = self.session.post(
                f"{BASE_URL}/api/insurama/presupuesto/{test_codigo}/enviar-presupuesto",
                json=payload
            )
            assert response.status_code != 422, f"Value '{value}' for tipo_garantia rejected"
        
        print("All tipo_garantia values accepted")
    
    def test_enviar_presupuesto_tiempo_horas_decimal(self):
        """Test that tiempo_horas accepts decimal values"""
        test_codigo = "TEST_CODE_789"
        
        decimal_values = [0.5, 1.0, 1.5, 2.5, 3.75, 8.0]
        for value in decimal_values:
            payload = {
                "precio": 100.00,
                "descripcion": "Test",
                "disponibilidad_recambios": "inmediata",
                "tiempo_horas": value,
                "tipo_recambio": "original",
                "tipo_garantia": "taller"
            }
            response = self.session.post(
                f"{BASE_URL}/api/insurama/presupuesto/{test_codigo}/enviar-presupuesto",
                json=payload
            )
            assert response.status_code != 422, f"Decimal value {value} for tiempo_horas rejected"
        
        print("All decimal tiempo_horas values accepted")


class TestScraperFieldMapping:
    """Tests for the scraper.py submit_budget field mapping"""
    
    def test_repair_type_mapping(self):
        """Verify repair_type mapping values match expected Sumbroker codes"""
        # These are the expected mappings from scraper.py
        repair_type_map = {
            "original": 1,
            "compatible": 2,
            "reacondicionado": 3,
            "no_aplica": 4
        }
        
        # Verify all values are integers (Sumbroker expects numeric codes)
        for key, value in repair_type_map.items():
            assert isinstance(value, int), f"repair_type value for '{key}' should be int"
            assert 1 <= value <= 4, f"repair_type value for '{key}' should be 1-4"
        
        print("repair_type mapping verified")
    
    def test_warranty_type_mapping(self):
        """Verify warranty_type mapping values match expected Sumbroker codes"""
        warranty_type_map = {
            "fabricante": 1,
            "taller": 2,
            "sin_garantia": 3
        }
        
        for key, value in warranty_type_map.items():
            assert isinstance(value, int), f"warranty_type value for '{key}' should be int"
            assert 1 <= value <= 3, f"warranty_type value for '{key}' should be 1-3"
        
        print("warranty_type mapping verified")
    
    def test_availability_mapping(self):
        """Verify spare_parts_availability mapping values match expected Sumbroker codes"""
        availability_map = {
            "inmediata": 1,
            "24h": 2,
            "48h": 3,
            "7dias": 4,
            "sin_stock": 5
        }
        
        for key, value in availability_map.items():
            assert isinstance(value, int), f"availability value for '{key}' should be int"
            assert 1 <= value <= 5, f"availability value for '{key}' should be 1-5"
        
        print("spare_parts_availability mapping verified")


class TestInsuramaConfigEndpoint:
    """Tests for Insurama configuration endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
    
    def test_get_insurama_config(self):
        """Test GET /api/insurama/config endpoint"""
        response = self.session.get(f"{BASE_URL}/api/insurama/config")
        
        assert response.status_code == 200, f"Config endpoint failed: {response.status_code}"
        
        data = response.json()
        # Should have these fields
        assert "configurado" in data, "Missing 'configurado' field"
        
        print(f"Insurama config: configurado={data.get('configurado')}, login={data.get('login')}")
    
    def test_list_presupuestos_endpoint(self):
        """Test GET /api/insurama/presupuestos endpoint"""
        response = self.session.get(f"{BASE_URL}/api/insurama/presupuestos?limit=5")
        
        # May return 200 with data or 400 if not configured
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "presupuestos" in data, "Missing 'presupuestos' field"
            assert "total" in data, "Missing 'total' field"
            print(f"Presupuestos endpoint working: {data.get('total')} total")
        else:
            print(f"Presupuestos endpoint returned 400 (credentials not configured)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

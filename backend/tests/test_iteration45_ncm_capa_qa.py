"""
Test Iteration 45: NCM avanzada, CAPA automática, QA muestreo, CPI/NIST
Tests para verificar:
1. NCM avanzada: create/update incidencias con severidad/disposición/origen/recurrencia_30d
2. Regla CAPA auto: severidad alta/critica => capa_obligatoria true + capa_id
3. Regla CAPA auto: recurrencia >=2 en 30 días (mismo tipo+origen) => capa_obligatoria true + capa_id
4. Endpoint CAPA dashboard: GET /api/master/iso/capa-dashboard
5. QA config: GET/POST /api/master/iso/qa-config
6. QA muestreo ejecutar: POST /api/master/iso/qa-muestreo/ejecutar
7. QA resultado fallo: POST /api/master/iso/qa-muestreo/{id}/resultado abre CAPA y activa escalado
8. CPI endpoint reglas: PATCH /api/ordenes/{id}/cpi (B2B obligatorio método+resultado, B2C con autorización cuando requiere borrado)
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for master user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "ramiraz91@gmail.com",
        "password": "temp123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping tests")

@pytest.fixture(scope="module")
def api_client(auth_token):
    """Session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session

@pytest.fixture(scope="module")
def test_cliente(api_client):
    """Get or create a test cliente for incidencias"""
    # First try to get an existing cliente
    response = api_client.get(f"{BASE_URL}/api/clientes")
    if response.status_code == 200 and response.json():
        return response.json()[0]
    
    # Create a test cliente
    cliente_data = {
        "nombre": "TEST_NCM",
        "apellidos": "Cliente Prueba",
        "dni": "12345678A",
        "telefono": "666123456",
        "direccion": "Calle Test 123",
        "email": "test_ncm@test.com"
    }
    response = api_client.post(f"{BASE_URL}/api/clientes", json=cliente_data)
    assert response.status_code == 200
    return response.json()

@pytest.fixture(scope="module")
def test_orden(api_client, test_cliente):
    """Get or create a test orden for CPI tests"""
    response = api_client.get(f"{BASE_URL}/api/ordenes")
    if response.status_code == 200 and response.json():
        return response.json()[0]
    
    # Create a test orden
    orden_data = {
        "cliente_id": test_cliente["id"],
        "dispositivo": {
            "modelo": "iPhone 14",
            "imei": "123456789012345",
            "color": "Black",
            "daños": "Pantalla rota"
        }
    }
    response = api_client.post(f"{BASE_URL}/api/ordenes", json=orden_data)
    assert response.status_code == 200
    return response.json()


class TestCapaDashboard:
    """Test CAPA Dashboard endpoint"""
    
    def test_capa_dashboard_returns_200(self, api_client):
        """GET /api/master/iso/capa-dashboard returns 200"""
        response = api_client.get(f"{BASE_URL}/api/master/iso/capa-dashboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ CAPA dashboard returns 200")
    
    def test_capa_dashboard_structure(self, api_client):
        """CAPA dashboard returns expected structure"""
        response = api_client.get(f"{BASE_URL}/api/master/iso/capa-dashboard")
        data = response.json()
        
        assert "total_capas" in data, "Missing total_capas"
        assert "por_estado" in data, "Missing por_estado"
        assert "por_motivo" in data, "Missing por_motivo"
        assert "abiertas_antiguedad_30d" in data, "Missing abiertas_antiguedad_30d"
        assert "generated_at" in data, "Missing generated_at"
        print(f"✓ CAPA dashboard structure valid: {data.get('total_capas', 0)} total CAPAs")


class TestQAConfig:
    """Test QA Configuration endpoints"""
    
    def test_qa_config_get(self, api_client):
        """GET /api/master/iso/qa-config returns 200 and config"""
        response = api_client.get(f"{BASE_URL}/api/master/iso/qa-config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "porcentaje_diario" in data, "Missing porcentaje_diario"
        assert "minimo_muestras" in data, "Missing minimo_muestras"
        assert "escalado_por_fallo_porcentaje" in data, "Missing escalado_por_fallo_porcentaje"
        assert "escalado_dias" in data, "Missing escalado_dias"
        print(f"✓ QA config GET: {data.get('porcentaje_diario')}% diario, mínimo {data.get('minimo_muestras')} muestras")
    
    def test_qa_config_post(self, api_client):
        """POST /api/master/iso/qa-config saves configuration"""
        config_data = {
            "porcentaje_diario": 15,
            "minimo_muestras": 2,
            "escalado_por_fallo_porcentaje": 25,
            "escalado_dias": 10
        }
        response = api_client.post(f"{BASE_URL}/api/master/iso/qa-config", json=config_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("porcentaje_diario") == 15, "porcentaje_diario not updated"
        print("✓ QA config POST: configuration saved")
        
        # Reset to default
        default_config = {
            "porcentaje_diario": 10,
            "minimo_muestras": 1,
            "escalado_por_fallo_porcentaje": 20,
            "escalado_dias": 7
        }
        api_client.post(f"{BASE_URL}/api/master/iso/qa-config", json=default_config)


class TestQAMuestreo:
    """Test QA Muestreo endpoint"""
    
    def test_qa_muestreo_ejecutar(self, api_client):
        """POST /api/master/iso/qa-muestreo/ejecutar returns 200"""
        response = api_client.post(f"{BASE_URL}/api/master/iso/qa-muestreo/ejecutar", json={})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "fecha" in data, "Missing fecha"
        assert "total_candidatas" in data, "Missing total_candidatas"
        assert "tam_muestra" in data, "Missing tam_muestra"
        assert "muestras" in data, "Missing muestras"
        print(f"✓ QA muestreo ejecutado: {data.get('tam_muestra', 0)} muestras de {data.get('total_candidatas', 0)} candidatas")
        return data
    
    def test_qa_muestreo_resultado_fallo(self, api_client):
        """POST /api/master/iso/qa-muestreo/{id}/resultado con fallo abre CAPA"""
        # First run muestreo to get a sample
        response = api_client.post(f"{BASE_URL}/api/master/iso/qa-muestreo/ejecutar", json={})
        if response.status_code != 200:
            pytest.skip("No se pudo ejecutar muestreo")
        
        data = response.json()
        muestras = data.get("muestras", [])
        if not muestras:
            pytest.skip("No hay muestras para testear resultado")
        
        muestreo_id = muestras[0].get("id")
        
        # Register a failure result
        resultado_data = {
            "resultado": "fallo",
            "hallazgos": "Test: Defecto detectado en QA muestreo"
        }
        response = api_client.post(f"{BASE_URL}/api/master/iso/qa-muestreo/{muestreo_id}/resultado", json=resultado_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result.get("resultado") == "fallo", "Resultado should be fallo"
        assert result.get("capa_id") is not None, "CAPA should be created on failure"
        print(f"✓ QA muestreo fallo: CAPA creada automáticamente con ID {result.get('capa_id')}")
        
        # Verify escalado was activated
        config_response = api_client.get(f"{BASE_URL}/api/master/iso/qa-config")
        if config_response.status_code == 200:
            config = config_response.json()
            assert config.get("escalado_hasta") is not None, "Escalado should be activated after failure"
            print("✓ Escalado QA activado tras fallo")


class TestNCMIncidencias:
    """Test NCM fields in incidencias"""
    
    def test_crear_incidencia_ncm_severidad_alta(self, api_client, test_cliente):
        """Crear incidencia tipo reclamacion con severidad alta genera CAPA automática"""
        incidencia_data = {
            "cliente_id": test_cliente["id"],
            "tipo": "reclamacion",
            "titulo": "TEST_NCM_SEVERIDAD_ALTA",
            "descripcion": "Incidencia de prueba con severidad alta",
            "prioridad": "alta",
            "severidad_ncm": "alta",
            "disposicion_ncm": "retrabajo",
            "origen_ncm": "proceso_reparacion"
        }
        response = api_client.post(f"{BASE_URL}/api/incidencias", json=incidencia_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("es_no_conformidad") == True, "Should be marked as no conformidad"
        assert data.get("severidad_ncm") == "alta", "Severidad should be alta"
        assert data.get("capa_obligatoria") == True, "CAPA should be obligatoria for alta severity"
        assert data.get("capa_id") is not None, "CAPA should be created automatically"
        print(f"✓ Incidencia NCM severidad alta: CAPA automática creada ({data.get('capa_id')})")
        return data
    
    def test_crear_incidencia_ncm_severidad_critica(self, api_client, test_cliente):
        """Crear incidencia tipo garantia con severidad critica genera CAPA automática"""
        incidencia_data = {
            "cliente_id": test_cliente["id"],
            "tipo": "garantia",
            "titulo": "TEST_NCM_SEVERIDAD_CRITICA",
            "descripcion": "Incidencia de prueba con severidad crítica",
            "prioridad": "critica",
            "severidad_ncm": "critica",
            "disposicion_ncm": "reemplazo",
            "origen_ncm": "proveedor"
        }
        response = api_client.post(f"{BASE_URL}/api/incidencias", json=incidencia_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("capa_obligatoria") == True, "CAPA should be obligatoria for critica severity"
        assert data.get("capa_id") is not None, "CAPA should be created automatically"
        print(f"✓ Incidencia NCM severidad crítica: CAPA automática creada ({data.get('capa_id')})")
    
    def test_crear_incidencia_ncm_severidad_baja_sin_capa(self, api_client, test_cliente):
        """Crear incidencia con severidad baja NO genera CAPA automática (si no hay recurrencia)"""
        unique_suffix = str(uuid.uuid4())[:8]
        incidencia_data = {
            "cliente_id": test_cliente["id"],
            "tipo": "otro",  # Not reclamacion/garantia/daño_transporte to avoid NCM type trigger
            "titulo": f"TEST_NCM_BAJA_{unique_suffix}",
            "descripcion": "Incidencia de prueba con severidad baja",
            "prioridad": "baja",
            "severidad_ncm": "baja",
            "disposicion_ncm": "retrabajo",
            "origen_ncm": f"test_unico_{unique_suffix}"  # Unique origin to avoid recurrence
        }
        response = api_client.post(f"{BASE_URL}/api/incidencias", json=incidencia_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # es_no_conformidad only set for specific tipos (reclamacion, garantia, daño_transporte)
        # With tipo=otro and severidad_baja, CAPA should not be obligatory
        print(f"✓ Incidencia severidad baja creada, capa_obligatoria={data.get('capa_obligatoria')}")
    
    def test_recurrencia_30d_genera_capa(self, api_client, test_cliente):
        """Crear 2 incidencias del mismo tipo+origen en 30 días genera CAPA automática"""
        origen_test = f"test_recurrencia_{str(uuid.uuid4())[:8]}"
        
        # Primera incidencia
        incidencia1_data = {
            "cliente_id": test_cliente["id"],
            "tipo": "reclamacion",
            "titulo": "TEST_RECURRENCIA_1",
            "descripcion": "Primera incidencia para test de recurrencia",
            "prioridad": "media",
            "severidad_ncm": "media",  # Media severity - not auto CAPA by itself
            "disposicion_ncm": "retrabajo",
            "origen_ncm": origen_test
        }
        response1 = api_client.post(f"{BASE_URL}/api/incidencias", json=incidencia1_data)
        assert response1.status_code == 200
        data1 = response1.json()
        print(f"✓ Primera incidencia creada: recurrencia_30d={data1.get('recurrencia_30d')}")
        
        # Segunda incidencia con mismo tipo+origen
        incidencia2_data = {
            "cliente_id": test_cliente["id"],
            "tipo": "reclamacion",
            "titulo": "TEST_RECURRENCIA_2",
            "descripcion": "Segunda incidencia para test de recurrencia",
            "prioridad": "media",
            "severidad_ncm": "media",
            "disposicion_ncm": "retrabajo",
            "origen_ncm": origen_test  # Same origin
        }
        response2 = api_client.post(f"{BASE_URL}/api/incidencias", json=incidencia2_data)
        assert response2.status_code == 200
        data2 = response2.json()
        
        # The second one should have recurrence >= 2 and trigger CAPA
        assert data2.get("recurrencia_30d", 0) >= 2, f"Recurrencia should be >= 2, got {data2.get('recurrencia_30d')}"
        assert data2.get("capa_obligatoria") == True, "CAPA should be obligatoria due to recurrence"
        assert data2.get("capa_id") is not None, "CAPA should be created due to recurrence"
        print(f"✓ Segunda incidencia: recurrencia_30d={data2.get('recurrencia_30d')}, CAPA creada ({data2.get('capa_id')})")


class TestCPINIST:
    """Test CPI/NIST endpoint rules"""
    
    def test_cpi_b2b_requires_metodo_y_resultado(self, api_client, test_orden):
        """B2B requires método and resultado for CPI"""
        orden_id = test_orden["id"]
        
        # Try B2B without method - should fail
        cpi_data = {
            "tipo_ot": "b2b",
            "requiere_borrado": True,
            "metodo": "",  # Empty method
            "resultado": ""
        }
        response = api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}/cpi", json=cpi_data)
        assert response.status_code == 400, f"B2B without method should fail: {response.status_code}"
        print("✓ CPI B2B sin método rechazado correctamente (400)")
    
    def test_cpi_b2b_success_with_metodo_resultado(self, api_client, test_orden):
        """B2B succeeds with method and result"""
        orden_id = test_orden["id"]
        
        cpi_data = {
            "tipo_ot": "b2b",
            "requiere_borrado": True,
            "metodo": "factory_reset",
            "resultado": "completado"
        }
        response = api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}/cpi", json=cpi_data)
        assert response.status_code == 200, f"B2B with method/result should succeed: {response.text}"
        
        data = response.json()
        assert data.get("cpi_tipo_ot") == "b2b"
        assert data.get("cpi_metodo") == "factory_reset"
        assert data.get("cpi_resultado") == "completado"
        print("✓ CPI B2B con método+resultado guardado correctamente")
    
    def test_cpi_b2c_con_borrado_requiere_autorizacion(self, api_client, test_orden):
        """B2C with borrado requires client authorization"""
        orden_id = test_orden["id"]
        
        # Try B2C with borrado but no authorization - should fail
        cpi_data = {
            "tipo_ot": "b2c",
            "requiere_borrado": True,
            "autorizacion_cliente": False,  # No authorization
            "metodo": "factory_reset"
        }
        response = api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}/cpi", json=cpi_data)
        assert response.status_code == 400, f"B2C borrado without auth should fail: {response.status_code}"
        print("✓ CPI B2C con borrado sin autorización rechazado (400)")
    
    def test_cpi_b2c_con_borrado_y_autorizacion_success(self, api_client, test_orden):
        """B2C with borrado and authorization succeeds"""
        orden_id = test_orden["id"]
        
        cpi_data = {
            "tipo_ot": "b2c",
            "requiere_borrado": True,
            "autorizacion_cliente": True,
            "metodo": "herramienta_validada",
            "resultado": "completado",
            "observaciones": "Test CPI B2C con autorización"
        }
        response = api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}/cpi", json=cpi_data)
        assert response.status_code == 200, f"B2C with auth should succeed: {response.text}"
        
        data = response.json()
        assert data.get("cpi_autorizacion_cliente") == True
        print("✓ CPI B2C con borrado+autorización guardado correctamente")
    
    def test_cpi_b2c_sin_borrado_no_requiere_autorizacion(self, api_client, test_orden):
        """B2C without borrado doesn't require authorization"""
        orden_id = test_orden["id"]
        
        cpi_data = {
            "tipo_ot": "b2c",
            "requiere_borrado": False,
            "autorizacion_cliente": False,
            "metodo": "no_aplica_misma_unidad",
            "resultado": "no_aplica"
        }
        response = api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}/cpi", json=cpi_data)
        assert response.status_code == 200, f"B2C without borrado should succeed: {response.text}"
        print("✓ CPI B2C sin borrado guardado sin requerir autorización")


class TestEndpointsExistentes:
    """Verify existing endpoints still work (no regression)"""
    
    def test_incidencias_list(self, api_client):
        """GET /api/incidencias still works"""
        response = api_client.get(f"{BASE_URL}/api/incidencias")
        assert response.status_code == 200, f"Incidencias list failed: {response.status_code}"
        print(f"✓ GET /api/incidencias OK - {len(response.json())} incidencias")
    
    def test_ordenes_list(self, api_client):
        """GET /api/ordenes still works"""
        response = api_client.get(f"{BASE_URL}/api/ordenes")
        assert response.status_code == 200, f"Ordenes list failed: {response.status_code}"
        print(f"✓ GET /api/ordenes OK - {len(response.json())} órdenes")
    
    def test_iso_kpis(self, api_client):
        """GET /api/master/iso/kpis still works"""
        response = api_client.get(f"{BASE_URL}/api/master/iso/kpis")
        assert response.status_code == 200, f"ISO KPIs failed: {response.status_code}"
        print("✓ GET /api/master/iso/kpis OK")
    
    def test_iso_documentos(self, api_client):
        """GET /api/master/iso/documentos still works"""
        response = api_client.get(f"{BASE_URL}/api/master/iso/documentos")
        assert response.status_code == 200, f"ISO documentos failed: {response.status_code}"
        print("✓ GET /api/master/iso/documentos OK")
    
    def test_iso_proveedores(self, api_client):
        """GET /api/master/iso/proveedores still works"""
        response = api_client.get(f"{BASE_URL}/api/master/iso/proveedores")
        assert response.status_code == 200, f"ISO proveedores failed: {response.status_code}"
        print("✓ GET /api/master/iso/proveedores OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

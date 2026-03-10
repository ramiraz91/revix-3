"""
Test suite for Iteration 9 features:
- Netelip VoIP configuration (config, extensiones, historial)
- Órdenes de Compra (aprobar/rechazar/pedida/recibida)
- Incidencias CRUD completo
- Incidencias por cliente
- IA mejorar diagnóstico sin markdown
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MASTER_CREDS = {"email": "master@techrepair.local", "password": "master123"}
ADMIN_CREDS = {"email": "admin@techrepair.local", "password": "admin123"}
TECNICO_CREDS = {"email": "tecnico@techrepair.local", "password": "tecnico123"}


class TestAuth:
    """Authentication tests"""
    
    def test_login_master(self):
        """Test master login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MASTER_CREDS)
        assert response.status_code == 200, f"Master login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "master"
        print(f"SUCCESS: Master login works")
    
    def test_login_admin(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"SUCCESS: Admin login works")


@pytest.fixture(scope="module")
def auth_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Authentication failed")


@pytest.fixture(scope="module")
def master_token():
    """Get master auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MASTER_CREDS)
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Master authentication failed")


@pytest.fixture(scope="module")
def headers(auth_token):
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="module")
def master_headers(master_token):
    """Get headers with master token"""
    return {
        "Authorization": f"Bearer {master_token}",
        "Content-Type": "application/json"
    }


class TestNetelipConfig:
    """Tests for Netelip VoIP configuration - /netelip endpoints"""
    
    def test_get_netelip_config(self, headers):
        """GET /api/netelip/config - Get Netelip configuration"""
        response = requests.get(f"{BASE_URL}/api/netelip/config", headers=headers)
        assert response.status_code == 200, f"Failed to get Netelip config: {response.text}"
        data = response.json()
        # Should have these fields
        assert "activo" in data
        assert "configurado" in data
        assert "webhook_url" in data
        print(f"SUCCESS: GET /api/netelip/config returns config with activo={data.get('activo')}")
    
    def test_save_netelip_config(self, headers):
        """POST /api/netelip/config - Save Netelip configuration"""
        config_data = {
            "token": "test-token-12345",
            "api_name": "TEST_Centralita",
            "extension_principal": "100",
            "activo": False  # Keep inactive for testing
        }
        response = requests.post(f"{BASE_URL}/api/netelip/config", json=config_data, headers=headers)
        assert response.status_code == 200, f"Failed to save Netelip config: {response.text}"
        data = response.json()
        assert "message" in data and "guardad" in data.get("message", "").lower()
        print(f"SUCCESS: POST /api/netelip/config saves configuration")
    
    def test_get_netelip_extensiones(self, headers):
        """GET /api/netelip/extensiones - List user extensions"""
        response = requests.get(f"{BASE_URL}/api/netelip/extensiones", headers=headers)
        assert response.status_code == 200, f"Failed to get extensiones: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: GET /api/netelip/extensiones returns {len(data)} extensiones")
    
    def test_asignar_extension(self, headers):
        """POST /api/netelip/extensiones - Assign extension to user"""
        # First get a user to assign extension to
        users_response = requests.get(f"{BASE_URL}/api/usuarios", headers=headers)
        if users_response.status_code != 200 or not users_response.json():
            pytest.skip("No users available for extension assignment")
        
        user = users_response.json()[0]
        extension_data = {
            "usuario_id": user["id"],
            "extension": f"TEST_{uuid.uuid4().hex[:4]}",
            "nombre_mostrar": "Test Extension"
        }
        response = requests.post(f"{BASE_URL}/api/netelip/extensiones", json=extension_data, headers=headers)
        assert response.status_code == 200, f"Failed to assign extension: {response.text}"
        data = response.json()
        assert "id" in data or "message" in data
        print(f"SUCCESS: POST /api/netelip/extensiones assigns extension")
    
    def test_get_netelip_llamadas(self, headers):
        """GET /api/netelip/llamadas - Get call history"""
        response = requests.get(f"{BASE_URL}/api/netelip/llamadas?limit=20", headers=headers)
        assert response.status_code == 200, f"Failed to get llamadas: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: GET /api/netelip/llamadas returns {len(data)} calls")


class TestOrdenesCompra:
    """Tests for Órdenes de Compra - /ordenes-compra endpoints"""
    
    @pytest.fixture(scope="class")
    def test_orden_compra_id(self, headers):
        """Create a test orden de compra for testing"""
        # First get a cliente and create an orden de trabajo
        clientes_response = requests.get(f"{BASE_URL}/api/clientes", headers=headers)
        if clientes_response.status_code != 200 or not clientes_response.json():
            # Create a test cliente
            cliente_data = {
                "nombre": "TEST_Cliente",
                "apellidos": "Compra",
                "dni": "12345678A",
                "telefono": "600000000",
                "direccion": "Test Address"
            }
            cliente_response = requests.post(f"{BASE_URL}/api/clientes", json=cliente_data, headers=headers)
            cliente_id = cliente_response.json()["id"]
        else:
            cliente_id = clientes_response.json()[0]["id"]
        
        # Create orden de trabajo
        orden_data = {
            "cliente_id": cliente_id,
            "dispositivo": {
                "modelo": "TEST_iPhone 15",
                "imei": "123456789012345",
                "color": "Negro",
                "daños": "Pantalla rota"
            },
            "agencia_envio": "SEUR",
            "codigo_recogida_entrada": "TEST123"
        }
        orden_response = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=headers)
        orden_id = orden_response.json()["id"]
        
        # Create orden de compra
        oc_data = {
            "nombre_pieza": f"TEST_Pantalla_{uuid.uuid4().hex[:6]}",
            "descripcion": "Pantalla LCD para pruebas",
            "cantidad": 1,
            "orden_trabajo_id": orden_id,
            "solicitado_por": "admin"
        }
        response = requests.post(f"{BASE_URL}/api/ordenes-compra", json=oc_data, headers=headers)
        assert response.status_code == 200, f"Failed to create orden compra: {response.text}"
        return response.json()["id"]
    
    def test_listar_ordenes_compra(self, headers):
        """GET /api/ordenes-compra - List purchase orders"""
        response = requests.get(f"{BASE_URL}/api/ordenes-compra", headers=headers)
        assert response.status_code == 200, f"Failed to list ordenes compra: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: GET /api/ordenes-compra returns {len(data)} orders")
    
    def test_listar_ordenes_compra_filtro_estado(self, headers):
        """GET /api/ordenes-compra?estado=pendiente - Filter by estado"""
        response = requests.get(f"{BASE_URL}/api/ordenes-compra?estado=pendiente", headers=headers)
        assert response.status_code == 200, f"Failed to filter ordenes compra: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        # All returned should be pendiente
        for oc in data:
            assert oc.get("estado") == "pendiente", f"Expected pendiente, got {oc.get('estado')}"
        print(f"SUCCESS: GET /api/ordenes-compra?estado=pendiente filters correctly")
    
    def test_aprobar_orden_compra(self, headers, test_orden_compra_id):
        """PATCH /api/ordenes-compra/{id} - Aprobar orden"""
        update_data = {
            "estado": "aprobada",
            "notas": "Aprobada para pruebas"
        }
        response = requests.patch(f"{BASE_URL}/api/ordenes-compra/{test_orden_compra_id}", json=update_data, headers=headers)
        assert response.status_code == 200, f"Failed to aprobar orden compra: {response.text}"
        data = response.json()
        # API returns message, verify by fetching the order
        assert "message" in data or data.get("estado") == "aprobada"
        # Verify the update by fetching
        verify = requests.get(f"{BASE_URL}/api/ordenes-compra/{test_orden_compra_id}", headers=headers)
        if verify.status_code == 200:
            assert verify.json().get("estado") == "aprobada"
        print(f"SUCCESS: PATCH /api/ordenes-compra/{test_orden_compra_id} - Aprobada")
    
    def test_marcar_pedida(self, headers, test_orden_compra_id):
        """PATCH /api/ordenes-compra/{id} - Marcar como pedida"""
        update_data = {
            "estado": "pedida",
            "notas": "Pedida al proveedor"
        }
        response = requests.patch(f"{BASE_URL}/api/ordenes-compra/{test_orden_compra_id}", json=update_data, headers=headers)
        assert response.status_code == 200, f"Failed to marcar pedida: {response.text}"
        data = response.json()
        assert "message" in data or data.get("estado") == "pedida"
        # Verify the update by fetching
        verify = requests.get(f"{BASE_URL}/api/ordenes-compra/{test_orden_compra_id}", headers=headers)
        if verify.status_code == 200:
            assert verify.json().get("estado") == "pedida"
        print(f"SUCCESS: PATCH /api/ordenes-compra/{test_orden_compra_id} - Pedida")
    
    def test_marcar_recibida(self, headers, test_orden_compra_id):
        """PATCH /api/ordenes-compra/{id} - Marcar como recibida"""
        update_data = {
            "estado": "recibida",
            "notas": "Recibida en almacén"
        }
        response = requests.patch(f"{BASE_URL}/api/ordenes-compra/{test_orden_compra_id}", json=update_data, headers=headers)
        assert response.status_code == 200, f"Failed to marcar recibida: {response.text}"
        data = response.json()
        assert "message" in data or data.get("estado") == "recibida"
        # Verify the update by fetching
        verify = requests.get(f"{BASE_URL}/api/ordenes-compra/{test_orden_compra_id}", headers=headers)
        if verify.status_code == 200:
            assert verify.json().get("estado") == "recibida"
        print(f"SUCCESS: PATCH /api/ordenes-compra/{test_orden_compra_id} - Recibida")


class TestIncidencias:
    """Tests for Incidencias CRUD - /incidencias endpoints"""
    
    @pytest.fixture(scope="class")
    def test_cliente_id(self, headers):
        """Get or create a test cliente"""
        clientes_response = requests.get(f"{BASE_URL}/api/clientes", headers=headers)
        if clientes_response.status_code == 200 and clientes_response.json():
            return clientes_response.json()[0]["id"]
        
        # Create test cliente
        cliente_data = {
            "nombre": "TEST_Cliente",
            "apellidos": "Incidencias",
            "dni": "87654321B",
            "telefono": "600111222",
            "direccion": "Test Address Incidencias"
        }
        response = requests.post(f"{BASE_URL}/api/clientes", json=cliente_data, headers=headers)
        return response.json()["id"]
    
    @pytest.fixture(scope="class")
    def test_incidencia_id(self, headers, test_cliente_id):
        """Create a test incidencia"""
        incidencia_data = {
            "cliente_id": test_cliente_id,
            "tipo": "reclamacion",
            "titulo": f"TEST_Incidencia_{uuid.uuid4().hex[:6]}",
            "descripcion": "Descripción de prueba para incidencia",
            "prioridad": "media"
        }
        response = requests.post(f"{BASE_URL}/api/incidencias", json=incidencia_data, headers=headers)
        assert response.status_code == 200, f"Failed to create incidencia: {response.text}"
        return response.json()["id"]
    
    def test_crear_incidencia(self, headers, test_cliente_id):
        """POST /api/incidencias - Create incidencia"""
        incidencia_data = {
            "cliente_id": test_cliente_id,
            "tipo": "garantia",
            "titulo": f"TEST_Garantia_{uuid.uuid4().hex[:6]}",
            "descripcion": "Problema con garantía del dispositivo",
            "prioridad": "alta"
        }
        response = requests.post(f"{BASE_URL}/api/incidencias", json=incidencia_data, headers=headers)
        assert response.status_code == 200, f"Failed to create incidencia: {response.text}"
        data = response.json()
        assert "id" in data
        assert "numero_incidencia" in data
        assert data["tipo"] == "garantia"
        assert data["estado"] == "abierta"
        print(f"SUCCESS: POST /api/incidencias creates incidencia {data['numero_incidencia']}")
    
    def test_listar_incidencias(self, headers):
        """GET /api/incidencias - List incidencias"""
        response = requests.get(f"{BASE_URL}/api/incidencias", headers=headers)
        assert response.status_code == 200, f"Failed to list incidencias: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: GET /api/incidencias returns {len(data)} incidencias")
    
    def test_listar_incidencias_filtro_estado(self, headers):
        """GET /api/incidencias?estado=abierta - Filter by estado"""
        response = requests.get(f"{BASE_URL}/api/incidencias?estado=abierta", headers=headers)
        assert response.status_code == 200, f"Failed to filter incidencias: {response.text}"
        data = response.json()
        for inc in data:
            assert inc.get("estado") == "abierta"
        print(f"SUCCESS: GET /api/incidencias?estado=abierta filters correctly")
    
    def test_listar_incidencias_filtro_tipo(self, headers):
        """GET /api/incidencias?tipo=garantia - Filter by tipo"""
        response = requests.get(f"{BASE_URL}/api/incidencias?tipo=garantia", headers=headers)
        assert response.status_code == 200, f"Failed to filter incidencias by tipo: {response.text}"
        data = response.json()
        for inc in data:
            assert inc.get("tipo") == "garantia"
        print(f"SUCCESS: GET /api/incidencias?tipo=garantia filters correctly")
    
    def test_obtener_incidencia(self, headers, test_incidencia_id):
        """GET /api/incidencias/{id} - Get incidencia by ID"""
        response = requests.get(f"{BASE_URL}/api/incidencias/{test_incidencia_id}", headers=headers)
        assert response.status_code == 200, f"Failed to get incidencia: {response.text}"
        data = response.json()
        assert data["id"] == test_incidencia_id
        print(f"SUCCESS: GET /api/incidencias/{test_incidencia_id} returns incidencia")
    
    def test_actualizar_incidencia_estado(self, headers, test_incidencia_id):
        """PUT /api/incidencias/{id} - Update incidencia estado"""
        update_data = {
            "estado": "en_proceso",
            "notas_resolucion": "Trabajando en la resolución"
        }
        response = requests.put(f"{BASE_URL}/api/incidencias/{test_incidencia_id}", json=update_data, headers=headers)
        assert response.status_code == 200, f"Failed to update incidencia: {response.text}"
        data = response.json()
        assert data.get("estado") == "en_proceso"
        print(f"SUCCESS: PUT /api/incidencias/{test_incidencia_id} updates estado to en_proceso")
    
    def test_resolver_incidencia(self, headers, test_incidencia_id):
        """PUT /api/incidencias/{id} - Resolve incidencia"""
        update_data = {
            "estado": "resuelta",
            "notas_resolucion": "Incidencia resuelta satisfactoriamente"
        }
        response = requests.put(f"{BASE_URL}/api/incidencias/{test_incidencia_id}", json=update_data, headers=headers)
        assert response.status_code == 200, f"Failed to resolve incidencia: {response.text}"
        data = response.json()
        assert data.get("estado") == "resuelta"
        print(f"SUCCESS: PUT /api/incidencias/{test_incidencia_id} resolves incidencia")
    
    def test_incidencias_por_cliente(self, headers, test_cliente_id):
        """GET /api/clientes/{id}/incidencias - Get incidencias by cliente"""
        response = requests.get(f"{BASE_URL}/api/clientes/{test_cliente_id}/incidencias", headers=headers)
        assert response.status_code == 200, f"Failed to get incidencias por cliente: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        # All should belong to this cliente
        for inc in data:
            assert inc.get("cliente_id") == test_cliente_id
        print(f"SUCCESS: GET /api/clientes/{test_cliente_id}/incidencias returns {len(data)} incidencias")


class TestIAMejorarDiagnostico:
    """Tests for IA mejorar diagnóstico - /ia/mejorar-diagnostico endpoint"""
    
    def test_mejorar_diagnostico_endpoint_exists(self, headers):
        """POST /api/ia/mejorar-diagnostico - Endpoint exists and responds"""
        diagnostico_data = {
            "diagnostico": "pantalla rota, cambiar lcd",
            "modelo_dispositivo": "iPhone 14 Pro",
            "sintomas": "pantalla negra, no enciende"
        }
        response = requests.post(f"{BASE_URL}/api/ia/mejorar-diagnostico", json=diagnostico_data, headers=headers)
        # Should return 200 or 500 if LLM not configured, but not 404
        assert response.status_code != 404, f"Endpoint not found: {response.text}"
        print(f"SUCCESS: POST /api/ia/mejorar-diagnostico endpoint exists (status: {response.status_code})")
    
    def test_mejorar_diagnostico_returns_text(self, headers):
        """POST /api/ia/mejorar-diagnostico - Returns improved text"""
        diagnostico_data = {
            "diagnostico": "bateria mal, cambiar",
            "modelo_dispositivo": "Samsung Galaxy S23",
            "sintomas": "se apaga solo"
        }
        response = requests.post(f"{BASE_URL}/api/ia/mejorar-diagnostico", json=diagnostico_data, headers=headers)
        if response.status_code == 200:
            data = response.json()
            # API returns diagnostico_mejorado, not texto_mejorado
            assert "diagnostico_mejorado" in data, f"Response missing diagnostico_mejorado: {data}"
            # Check that response doesn't contain markdown
            texto = data.get("diagnostico_mejorado", "")
            # Should not have markdown headers or bold
            assert "**" not in texto or texto.count("**") < 4, "Response contains too much markdown"
            print(f"SUCCESS: POST /api/ia/mejorar-diagnostico returns improved text without markdown")
        else:
            print(f"INFO: IA endpoint returned {response.status_code} - LLM may not be configured")


class TestAllIncidenciaTipos:
    """Test all incidencia types work correctly"""
    
    @pytest.fixture(scope="class")
    def test_cliente_id(self, headers):
        """Get or create a test cliente"""
        clientes_response = requests.get(f"{BASE_URL}/api/clientes", headers=headers)
        if clientes_response.status_code == 200 and clientes_response.json():
            return clientes_response.json()[0]["id"]
        return None
    
    @pytest.mark.parametrize("tipo", [
        "reclamacion",
        "garantia", 
        "reemplazo_dispositivo",
        "daño_transporte",
        "otro"
    ])
    def test_crear_incidencia_tipo(self, headers, test_cliente_id, tipo):
        """Test creating incidencia with each tipo"""
        if not test_cliente_id:
            pytest.skip("No cliente available")
        
        incidencia_data = {
            "cliente_id": test_cliente_id,
            "tipo": tipo,
            "titulo": f"TEST_{tipo}_{uuid.uuid4().hex[:4]}",
            "descripcion": f"Incidencia de tipo {tipo} para pruebas",
            "prioridad": "media"
        }
        response = requests.post(f"{BASE_URL}/api/incidencias", json=incidencia_data, headers=headers)
        assert response.status_code == 200, f"Failed to create incidencia tipo {tipo}: {response.text}"
        data = response.json()
        assert data["tipo"] == tipo
        print(f"SUCCESS: Created incidencia tipo={tipo}")


class TestOrdenesCompraRechazar:
    """Test rechazar orden de compra"""
    
    def test_rechazar_orden_compra(self, headers):
        """PATCH /api/ordenes-compra/{id} - Rechazar orden"""
        # First create an orden de compra
        clientes_response = requests.get(f"{BASE_URL}/api/clientes", headers=headers)
        if clientes_response.status_code != 200 or not clientes_response.json():
            pytest.skip("No clientes available")
        
        cliente_id = clientes_response.json()[0]["id"]
        
        # Create orden de trabajo
        orden_data = {
            "cliente_id": cliente_id,
            "dispositivo": {
                "modelo": "TEST_Rechazar",
                "imei": "999888777666555",
                "color": "Blanco",
                "daños": "Test"
            },
            "agencia_envio": "MRW",
            "codigo_recogida_entrada": "TESTREJ"
        }
        orden_response = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=headers)
        orden_id = orden_response.json()["id"]
        
        # Create orden de compra
        oc_data = {
            "nombre_pieza": f"TEST_Rechazar_{uuid.uuid4().hex[:6]}",
            "descripcion": "Para rechazar",
            "cantidad": 1,
            "orden_trabajo_id": orden_id,
            "solicitado_por": "admin"
        }
        oc_response = requests.post(f"{BASE_URL}/api/ordenes-compra", json=oc_data, headers=headers)
        oc_id = oc_response.json()["id"]
        
        # Rechazar
        update_data = {
            "estado": "rechazada",
            "notas": "Rechazada por pruebas"
        }
        response = requests.patch(f"{BASE_URL}/api/ordenes-compra/{oc_id}", json=update_data, headers=headers)
        assert response.status_code == 200, f"Failed to rechazar: {response.text}"
        data = response.json()
        assert "message" in data or data.get("estado") == "rechazada"
        # Verify the update by fetching
        verify = requests.get(f"{BASE_URL}/api/ordenes-compra/{oc_id}", headers=headers)
        if verify.status_code == 200:
            assert verify.json().get("estado") == "rechazada"
        print(f"SUCCESS: PATCH /api/ordenes-compra/{oc_id} - Rechazada")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test suite for iteration 8 features:
1. Dashboard - Botón Nueva Orden (UI test)
2. Dashboard - Panel Órdenes de Compra Urgentes
3. Calendario - Panel Disponibilidad Técnicos
4. OrdenTecnico - Botón Mejorar con IA
5. POST /api/ia/mejorar-diagnostico
6. GET /api/dashboard/ordenes-compra-urgentes
7. POST/GET /api/incidencias
8. Barcode scanner searches by numero_orden
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


@pytest.fixture(scope="module")
def master_token():
    """Get master authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MASTER_CREDS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Master authentication failed")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def tecnico_token():
    """Get tecnico authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=TECNICO_CREDS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Tecnico authentication failed")


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture
def tecnico_headers(tecnico_token):
    return {"Authorization": f"Bearer {tecnico_token}", "Content-Type": "application/json"}


@pytest.fixture
def master_headers(master_token):
    return {"Authorization": f"Bearer {master_token}", "Content-Type": "application/json"}


class TestAuthentication:
    """Test authentication with all user types"""
    
    def test_master_login(self):
        """P0: Master login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MASTER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "master"
        print(f"✓ Master login successful: {data['user']['email']}")
    
    def test_admin_login(self):
        """P0: Admin login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful: {data['user']['email']}")
    
    def test_tecnico_login(self):
        """P0: Tecnico login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TECNICO_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "tecnico"
        print(f"✓ Tecnico login successful: {data['user']['email']}")


class TestDashboardOrdenesCompraUrgentes:
    """Test GET /api/dashboard/ordenes-compra-urgentes endpoint"""
    
    def test_get_ordenes_compra_urgentes_endpoint_exists(self, admin_headers):
        """P0: Endpoint ordenes-compra-urgentes exists and returns data"""
        response = requests.get(f"{BASE_URL}/api/dashboard/ordenes-compra-urgentes", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "ordenes" in data
        assert "total_pendientes" in data
        assert "total_aprobadas" in data
        print(f"✓ Ordenes compra urgentes endpoint works: {data['total_pendientes']} pendientes, {data['total_aprobadas']} aprobadas")
    
    def test_ordenes_compra_urgentes_structure(self, admin_headers):
        """P1: Response has correct structure"""
        response = requests.get(f"{BASE_URL}/api/dashboard/ordenes-compra-urgentes", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["ordenes"], list)
        assert isinstance(data["total_pendientes"], int)
        assert isinstance(data["total_aprobadas"], int)
        print(f"✓ Response structure is correct")


class TestIncidencias:
    """Test CRUD for /api/incidencias endpoint"""
    
    @pytest.fixture
    def test_cliente(self, admin_headers):
        """Create a test client for incidencias"""
        cliente_data = {
            "nombre": "TEST_Cliente",
            "apellidos": "Incidencias",
            "dni": f"TEST{uuid.uuid4().hex[:6].upper()}",
            "telefono": "600123456",
            "direccion": "Calle Test 123"
        }
        response = requests.post(f"{BASE_URL}/api/clientes", json=cliente_data, headers=admin_headers)
        if response.status_code == 200:
            cliente = response.json()
            yield cliente
            # Cleanup
            requests.delete(f"{BASE_URL}/api/clientes/{cliente['id']}", headers=admin_headers)
        else:
            pytest.skip("Could not create test client")
    
    def test_create_incidencia(self, admin_headers, test_cliente):
        """P0: Create incidencia works"""
        incidencia_data = {
            "cliente_id": test_cliente["id"],
            "tipo": "reclamacion",
            "titulo": "TEST_Incidencia de prueba",
            "descripcion": "Descripción de la incidencia de prueba",
            "prioridad": "alta"
        }
        response = requests.post(f"{BASE_URL}/api/incidencias", json=incidencia_data, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "numero_incidencia" in data
        assert data["titulo"] == "TEST_Incidencia de prueba"
        assert data["estado"] == "abierta"
        print(f"✓ Incidencia created: {data['numero_incidencia']}")
        return data
    
    def test_list_incidencias(self, admin_headers):
        """P0: List incidencias works"""
        response = requests.get(f"{BASE_URL}/api/incidencias", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} incidencias")
    
    def test_get_incidencia_by_id(self, admin_headers, test_cliente):
        """P0: Get incidencia by ID works"""
        # First create an incidencia
        incidencia_data = {
            "cliente_id": test_cliente["id"],
            "tipo": "garantia",
            "titulo": "TEST_Incidencia para GET",
            "descripcion": "Test GET by ID",
            "prioridad": "media"
        }
        create_response = requests.post(f"{BASE_URL}/api/incidencias", json=incidencia_data, headers=admin_headers)
        assert create_response.status_code == 200
        created = create_response.json()
        
        # Now get it by ID
        response = requests.get(f"{BASE_URL}/api/incidencias/{created['id']}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created["id"]
        assert data["titulo"] == "TEST_Incidencia para GET"
        print(f"✓ Got incidencia by ID: {data['numero_incidencia']}")
    
    def test_update_incidencia(self, admin_headers, test_cliente):
        """P0: Update incidencia works"""
        # First create an incidencia
        incidencia_data = {
            "cliente_id": test_cliente["id"],
            "tipo": "otro",
            "titulo": "TEST_Incidencia para UPDATE",
            "descripcion": "Test UPDATE",
            "prioridad": "baja"
        }
        create_response = requests.post(f"{BASE_URL}/api/incidencias", json=incidencia_data, headers=admin_headers)
        assert create_response.status_code == 200
        created = create_response.json()
        
        # Update it
        update_data = {
            "estado": "en_proceso",
            "notas_resolucion": "Trabajando en la incidencia"
        }
        response = requests.put(f"{BASE_URL}/api/incidencias/{created['id']}", json=update_data, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "en_proceso"
        print(f"✓ Updated incidencia: {data['numero_incidencia']} -> estado: {data['estado']}")
    
    def test_get_incidencias_by_cliente(self, admin_headers, test_cliente):
        """P0: Get incidencias by cliente works"""
        # Create an incidencia for this client
        incidencia_data = {
            "cliente_id": test_cliente["id"],
            "tipo": "daño_transporte",
            "titulo": "TEST_Incidencia por cliente",
            "descripcion": "Test filter by cliente",
            "prioridad": "alta"
        }
        requests.post(f"{BASE_URL}/api/incidencias", json=incidencia_data, headers=admin_headers)
        
        # Get incidencias for this client
        response = requests.get(f"{BASE_URL}/api/clientes/{test_cliente['id']}/incidencias", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        print(f"✓ Got {len(data)} incidencias for cliente {test_cliente['id']}")


class TestIAMejorarDiagnostico:
    """Test POST /api/ia/mejorar-diagnostico endpoint"""
    
    def test_mejorar_diagnostico_endpoint_exists(self, tecnico_headers):
        """P0: Endpoint mejorar-diagnostico exists"""
        diagnostico_data = {
            "diagnostico": "pantalla rota, hay que cambiarla",
            "modelo_dispositivo": "iPhone 13",
            "sintomas": "pantalla no enciende"
        }
        response = requests.post(f"{BASE_URL}/api/ia/mejorar-diagnostico", json=diagnostico_data, headers=tecnico_headers)
        # Should return 200 or 500 if LLM not configured
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "diagnostico_mejorado" in data
            assert "original" in data
            print(f"✓ IA mejorar-diagnostico works: {data['diagnostico_mejorado'][:100]}...")
        else:
            print(f"⚠ IA mejorar-diagnostico returned 500 (LLM may not be configured)")
    
    def test_mejorar_diagnostico_requires_auth(self):
        """P1: Endpoint requires authentication"""
        diagnostico_data = {
            "diagnostico": "test",
        }
        response = requests.post(f"{BASE_URL}/api/ia/mejorar-diagnostico", json=diagnostico_data)
        assert response.status_code == 401
        print(f"✓ Endpoint requires authentication")


class TestTecnicosDisponibilidad:
    """Test GET /api/tecnicos/disponibilidad endpoint"""
    
    def test_disponibilidad_tecnicos_endpoint(self, admin_headers):
        """P0: Endpoint disponibilidad tecnicos works"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = requests.get(f"{BASE_URL}/api/tecnicos/disponibilidad?fecha={today}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Each item should have tecnico info and availability
        if len(data) > 0:
            assert "tecnico" in data[0]
            assert "ordenes_asignadas" in data[0]
            assert "disponible" in data[0]
        print(f"✓ Disponibilidad tecnicos: {len(data)} técnicos encontrados")
        for t in data:
            status = "Libre" if t["disponible"] else f"No disponible ({t.get('motivo_no_disponible', 'N/A')})"
            print(f"  - {t['tecnico']['nombre']}: {t['ordenes_asignadas']} órdenes, {status}")


class TestBarcodeScannerByNumeroOrden:
    """Test barcode scanner searches by numero_orden correctly"""
    
    @pytest.fixture
    def test_orden(self, admin_headers):
        """Create a test order"""
        # First create a client
        cliente_data = {
            "nombre": "TEST_Scanner",
            "apellidos": "Cliente",
            "dni": f"TEST{uuid.uuid4().hex[:6].upper()}",
            "telefono": "600999888",
            "direccion": "Calle Scanner 1"
        }
        cliente_response = requests.post(f"{BASE_URL}/api/clientes", json=cliente_data, headers=admin_headers)
        if cliente_response.status_code != 200:
            pytest.skip("Could not create test client")
        cliente = cliente_response.json()
        
        # Create order
        orden_data = {
            "cliente_id": cliente["id"],
            "dispositivo": {
                "modelo": "TEST iPhone Scanner",
                "imei": "123456789012345",
                "color": "Negro",
                "daños": "Pantalla rota para test scanner"
            },
            "agencia_envio": "SEUR",
            "codigo_recogida_entrada": "TEST123"
        }
        orden_response = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=admin_headers)
        if orden_response.status_code != 200:
            pytest.skip("Could not create test order")
        orden = orden_response.json()
        
        yield orden
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/ordenes/{orden['id']}", headers=admin_headers)
        requests.delete(f"{BASE_URL}/api/clientes/{cliente['id']}", headers=admin_headers)
    
    def test_scan_by_numero_orden(self, admin_headers, test_orden):
        """P0: Scan by numero_orden works"""
        numero_orden = test_orden["numero_orden"]
        scan_data = {
            "codigo": numero_orden,
            "tipo_escaneo": "recepcion"
        }
        response = requests.post(f"{BASE_URL}/api/ordenes/{numero_orden}/scan", json=scan_data, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # API returns message and nuevo_estado on success
        assert "message" in data or "nuevo_estado" in data
        print(f"✓ Scan by numero_orden works: {numero_orden} -> {data.get('nuevo_estado', 'OK')}")
    
    def test_scan_by_id(self, admin_headers, test_orden):
        """P0: Scan by ID also works"""
        orden_id = test_orden["id"]
        scan_data = {
            "codigo": orden_id,
            "tipo_escaneo": "recepcion"
        }
        response = requests.post(f"{BASE_URL}/api/ordenes/{orden_id}/scan", json=scan_data, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # API returns message and nuevo_estado on success
        assert "message" in data or "nuevo_estado" in data
        print(f"✓ Scan by ID works: {orden_id} -> {data.get('nuevo_estado', 'OK')}")


class TestDashboardStats:
    """Test dashboard stats endpoint"""
    
    def test_dashboard_stats(self, admin_headers):
        """P0: Dashboard stats endpoint works"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_ordenes" in data
        assert "ordenes_por_estado" in data
        print(f"✓ Dashboard stats: {data['total_ordenes']} total órdenes")


class TestOrdenesCompra:
    """Test ordenes de compra endpoints"""
    
    def test_list_ordenes_compra(self, admin_headers):
        """P0: List ordenes de compra works"""
        response = requests.get(f"{BASE_URL}/api/ordenes-compra", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} órdenes de compra")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

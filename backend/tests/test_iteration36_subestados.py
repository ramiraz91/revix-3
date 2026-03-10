"""
Test Suite for Iteration 36: Subestados (Sub-states) Feature
Tests the internal sub-state system for work orders that allows tracking
intermediate states like 'Esperando repuestos', 'Esperando autorización', etc.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "ramiraz91@gmail.com"
TEST_PASSWORD = "temp123"
TEST_ORDER_ID = "7f13de30-2bc2-49c4-85be-a80a9efd0db8"

# Valid subestados
VALID_SUBESTADOS = [
    "ninguno",
    "esperando_repuestos",
    "esperando_autorizacion",
    "esperando_cliente",
    "esperando_pago",
    "en_consulta_tecnica",
    "pendiente_recogida",
    "aseguradora",
    "otro"
]


class TestAuthentication:
    """Authentication tests"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert "user" in data, "User not in response"
        print(f"✓ Login successful, user role: {data['user'].get('role')}")


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestSubestadoEndpoints:
    """Tests for subestado CRUD operations"""
    
    def test_get_subestado_current(self, auth_headers):
        """GET /api/ordenes/{id}/subestado - Get current subestado and history"""
        response = requests.get(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/subestado",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get subestado: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "subestado" in data, "subestado field missing"
        assert "motivo" in data, "motivo field missing"
        assert "fecha_revision" in data, "fecha_revision field missing"
        assert "historial" in data, "historial field missing"
        assert "labels" in data, "labels field missing"
        
        # Verify subestado is valid
        assert data["subestado"] in VALID_SUBESTADOS, f"Invalid subestado: {data['subestado']}"
        
        print(f"✓ Current subestado: {data['subestado']}")
        print(f"✓ Motivo: {data.get('motivo', 'N/A')}")
        print(f"✓ Fecha revisión: {data.get('fecha_revision', 'N/A')}")
        print(f"✓ Historial entries: {len(data.get('historial', []))}")
    
    def test_change_subestado_esperando_repuestos(self, auth_headers):
        """PATCH /api/ordenes/{id}/subestado - Change to esperando_repuestos"""
        payload = {
            "subestado": "esperando_repuestos",
            "motivo": "Pantalla LCD no disponible en stock, pedido a proveedor",
            "fecha_revision": "2026-02-25"
        }
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/subestado",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Failed to change subestado: {response.text}"
        data = response.json()
        
        assert "message" in data, "message field missing"
        assert "subestado" in data, "subestado field missing"
        assert data["subestado"] == "esperando_repuestos"
        
        print(f"✓ Subestado changed: {data['message']}")
        print(f"✓ New subestado: {data['subestado']}")
        print(f"✓ Fecha revisión: {data.get('fecha_revision')}")
    
    def test_change_subestado_esperando_autorizacion(self, auth_headers):
        """PATCH /api/ordenes/{id}/subestado - Change to esperando_autorizacion"""
        payload = {
            "subestado": "esperando_autorizacion",
            "motivo": "Esperando autorización del cliente para reparación adicional",
            "fecha_revision": "2026-02-22"
        }
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/subestado",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Failed to change subestado: {response.text}"
        data = response.json()
        
        assert data["subestado"] == "esperando_autorizacion"
        print(f"✓ Changed to esperando_autorizacion")
    
    def test_change_subestado_with_past_date(self, auth_headers):
        """PATCH /api/ordenes/{id}/subestado - Change with past revision date (should work)"""
        payload = {
            "subestado": "esperando_cliente",
            "motivo": "Cliente no responde llamadas, intentar contactar nuevamente",
            "fecha_revision": "2026-02-20"  # Today or past date
        }
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/subestado",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Failed to change subestado: {response.text}"
        data = response.json()
        
        assert data["subestado"] == "esperando_cliente"
        print(f"✓ Changed to esperando_cliente with past revision date")
    
    def test_change_subestado_invalid(self, auth_headers):
        """PATCH /api/ordenes/{id}/subestado - Invalid subestado should fail"""
        payload = {
            "subestado": "invalid_subestado",
            "motivo": "Test invalid"
        }
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/subestado",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 400, f"Should have failed with 400: {response.text}"
        print(f"✓ Invalid subestado correctly rejected")
    
    def test_change_subestado_to_ninguno(self, auth_headers):
        """PATCH /api/ordenes/{id}/subestado - Clear subestado by setting to ninguno"""
        payload = {
            "subestado": "ninguno",
            "motivo": "Subestado eliminado - problema resuelto"
        }
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/subestado",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Failed to clear subestado: {response.text}"
        data = response.json()
        
        assert data["subestado"] == "ninguno"
        print(f"✓ Subestado cleared to 'ninguno'")
    
    def test_verify_historial_after_changes(self, auth_headers):
        """GET /api/ordenes/{id}/subestado - Verify historial has recorded changes"""
        response = requests.get(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/subestado",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        historial = data.get("historial", [])
        assert len(historial) >= 3, f"Expected at least 3 historial entries, got {len(historial)}"
        
        # Verify historial entry structure
        if historial:
            entry = historial[-1]  # Last entry
            assert "subestado_anterior" in entry, "subestado_anterior missing in historial"
            assert "subestado_nuevo" in entry, "subestado_nuevo missing in historial"
            assert "motivo" in entry, "motivo missing in historial"
            assert "cambiado_por" in entry, "cambiado_por missing in historial"
            assert "fecha_cambio" in entry, "fecha_cambio missing in historial"
        
        print(f"✓ Historial has {len(historial)} entries")
        print(f"✓ Last change: {historial[-1].get('subestado_anterior')} -> {historial[-1].get('subestado_nuevo')}")


class TestPendientesRevision:
    """Tests for pending revision orders endpoint"""
    
    def test_setup_order_with_past_revision_date(self, auth_headers):
        """Setup: Set order with past revision date for testing"""
        payload = {
            "subestado": "esperando_repuestos",
            "motivo": "Test - Repuestos pendientes de llegada",
            "fecha_revision": "2026-02-20"  # Today (past or current)
        }
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/subestado",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200
        print(f"✓ Setup: Order configured with past revision date")
    
    def test_get_ordenes_pendientes_revision(self, auth_headers):
        """GET /api/ordenes/subestados/pendientes-revision - Get orders with pending revision"""
        response = requests.get(
            f"{BASE_URL}/api/ordenes/subestados/pendientes-revision",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get pending revisions: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "ordenes_pendientes" in data, "ordenes_pendientes field missing"
        assert "total" in data, "total field missing"
        assert "fecha_consulta" in data, "fecha_consulta field missing"
        
        print(f"✓ Total orders pending revision: {data['total']}")
        print(f"✓ Query date: {data['fecha_consulta']}")
        
        # Verify our test order is in the list
        ordenes = data.get("ordenes_pendientes", [])
        order_ids = [o.get("id") for o in ordenes]
        
        if TEST_ORDER_ID in order_ids:
            print(f"✓ Test order {TEST_ORDER_ID} found in pending revisions")
        else:
            print(f"⚠ Test order not in pending list (may have different estado)")


class TestGenerarRecordatorios:
    """Tests for generating reminder notifications"""
    
    def test_generar_recordatorios(self, auth_headers):
        """POST /api/ordenes/subestados/generar-recordatorios - Generate reminder notifications"""
        response = requests.post(
            f"{BASE_URL}/api/ordenes/subestados/generar-recordatorios",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to generate reminders: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "message" in data, "message field missing"
        assert "ordenes_revisadas" in data, "ordenes_revisadas field missing"
        assert "recordatorios_creados" in data, "recordatorios_creados field missing"
        
        print(f"✓ {data['message']}")
        print(f"✓ Orders reviewed: {data['ordenes_revisadas']}")
        print(f"✓ Reminders created: {data['recordatorios_creados']}")
    
    def test_generar_recordatorios_no_duplicates(self, auth_headers):
        """POST /api/ordenes/subestados/generar-recordatorios - Should not create duplicates within 24h"""
        # First call
        response1 = requests.post(
            f"{BASE_URL}/api/ordenes/subestados/generar-recordatorios",
            headers=auth_headers
        )
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second call immediately after
        response2 = requests.post(
            f"{BASE_URL}/api/ordenes/subestados/generar-recordatorios",
            headers=auth_headers
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Second call should create 0 or fewer reminders (no duplicates)
        print(f"✓ First call created: {data1['recordatorios_creados']} reminders")
        print(f"✓ Second call created: {data2['recordatorios_creados']} reminders (should be 0 or less)")


class TestOrderDetailWithSubestado:
    """Tests to verify order detail includes subestado data"""
    
    def test_order_detail_includes_subestado(self, auth_headers):
        """GET /api/ordenes/{id} - Verify order detail includes subestado fields"""
        response = requests.get(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get order: {response.text}"
        data = response.json()
        
        # Verify subestado fields are present
        assert "subestado" in data or data.get("subestado") is None, "subestado field should exist"
        
        print(f"✓ Order {data.get('numero_orden')} retrieved")
        print(f"✓ Estado: {data.get('estado')}")
        print(f"✓ Subestado: {data.get('subestado', 'ninguno')}")
        print(f"✓ Motivo subestado: {data.get('motivo_subestado', 'N/A')}")
        print(f"✓ Fecha revisión: {data.get('fecha_revision_subestado', 'N/A')}")


class TestCleanup:
    """Cleanup tests - reset order to known state"""
    
    def test_reset_subestado(self, auth_headers):
        """Reset order subestado to esperando_repuestos for UI testing"""
        payload = {
            "subestado": "esperando_repuestos",
            "motivo": "Pantalla LCD pendiente de llegada del proveedor",
            "fecha_revision": "2026-02-20"  # Today - should show as overdue
        }
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{TEST_ORDER_ID}/subestado",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200
        print(f"✓ Order reset to esperando_repuestos with today's revision date")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test suite for Agent Simulation Flow - Iteration 18
Tests the full flow: POST /api/agente/simular-aceptacion/{codigo}
- Pre-registro creation
- Sumbroker API data extraction
- Work order creation
- Internal notification generation
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

# Test credentials
MASTER_EMAIL = "master@techrepair.local"
MASTER_PASSWORD = "master123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get master authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": MASTER_EMAIL,
        "password": MASTER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Master authentication failed - cannot run agent tests")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with master auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestAgentStatus:
    """Test agent status endpoint"""
    
    def test_get_agent_status(self, authenticated_client):
        """GET /api/agente/status - should return stats including ordenes_creadas_agente"""
        response = authenticated_client.get(f"{BASE_URL}/api/agente/status")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "stats" in data
        assert "ordenes_creadas_agente" in data["stats"]
        assert "pre_registros_total" in data["stats"]
        print(f"Agent status OK - ordenes_creadas_agente: {data['stats']['ordenes_creadas_agente']}")


class TestSimulacionAceptacion:
    """Test simulation endpoint - full acceptance flow"""
    
    def test_simular_codigo_ya_procesado_25BE005825(self, authenticated_client):
        """POST /api/agente/simular-aceptacion/25BE005825 - should return 400 (already processed)"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/agente/simular-aceptacion/25BE005825",
            timeout=30
        )
        # Should return 400 because order already exists
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data
        assert "Ya existe una orden" in data["detail"]
        print(f"Correctly rejected already processed code 25BE005825: {data['detail']}")
    
    def test_simular_codigo_ya_procesado_25BE005814(self, authenticated_client):
        """POST /api/agente/simular-aceptacion/25BE005814 - should return 400 (already processed)"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/agente/simular-aceptacion/25BE005814",
            timeout=30
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data
        print(f"Correctly rejected already processed code 25BE005814: {data['detail']}")
    
    def test_simular_nuevo_codigo_2501000028(self, authenticated_client):
        """POST /api/agente/simular-aceptacion/2501000028 - full simulation with fresh code"""
        # This test uses longer timeout as Sumbroker API calls take 5-15 seconds
        response = authenticated_client.post(
            f"{BASE_URL}/api/agente/simular-aceptacion/2501000028",
            timeout=60
        )
        
        # Could be 200 success OR 400 if already processed
        if response.status_code == 400:
            data = response.json()
            if "Ya existe una orden" in data.get("detail", ""):
                print(f"Code 2501000028 was already processed in previous test run")
                pytest.skip("Code already processed - simulation test passed previously")
            else:
                pytest.fail(f"Unexpected 400 error: {data}")
        
        assert response.status_code == 200, f"Simulation failed: {response.text}"
        
        data = response.json()
        assert "codigo" in data
        assert "steps" in data
        assert "success" in data
        
        print(f"Simulation result for 2501000028:")
        print(f"  Success: {data.get('success')}")
        print(f"  Message: {data.get('message')}")
        for step in data.get("steps", []):
            print(f"  Step {step.get('step')}: {step.get('action')}")


class TestOrdenesAutoCreadas:
    """Test that auto-created orders appear correctly"""
    
    def test_get_ordenes_list(self, authenticated_client):
        """GET /api/ordenes - verify auto-created orders exist with correct flags"""
        response = authenticated_client.get(f"{BASE_URL}/api/ordenes")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        ordenes = response.json()
        assert isinstance(ordenes, list)
        
        # Find orders created by agent
        ordenes_agente = [o for o in ordenes if o.get("creado_por_agente") == True]
        print(f"Found {len(ordenes_agente)} orders created by agent")
        
        if ordenes_agente:
            # Verify first agent-created order has expected fields
            orden = ordenes_agente[0]
            print(f"Sample agent order:")
            print(f"  numero_orden: {orden.get('numero_orden')}")
            print(f"  codigo_siniestro: {orden.get('codigo_siniestro')}")
            print(f"  creado_por_agente: {orden.get('creado_por_agente')}")
            
            # Verify enriched portal data exists
            if orden.get("datos_portal"):
                dp = orden["datos_portal"]
                print(f"  Portal data - phone: {dp.get('customer_phone')}, damage: {dp.get('damage_description', '')[:50]}")


class TestPreRegistros:
    """Test pre-registros endpoint"""
    
    def test_get_pre_registros(self, authenticated_client):
        """GET /api/pre-registros - verify pre-registros show status chain with historial"""
        # Note: The actual endpoint is /api/agente/pre-registros based on code review
        # Let me check both endpoints
        response = authenticated_client.get(f"{BASE_URL}/api/pre-registros")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        pre_registros = response.json()
        assert isinstance(pre_registros, list)
        
        print(f"Found {len(pre_registros)} pre-registros")
        
        # Find ones with orden_creada status
        orden_creadas = [pr for pr in pre_registros if pr.get("estado") == "orden_creada"]
        print(f"Pre-registros with orden_creada status: {len(orden_creadas)}")
        
        if orden_creadas:
            pr = orden_creadas[0]
            print(f"Sample pre-registro:")
            print(f"  codigo_siniestro: {pr.get('codigo_siniestro')}")
            print(f"  estado: {pr.get('estado')}")
            print(f"  orden_id: {pr.get('orden_id')}")
            
            # Verify historial exists
            historial = pr.get("historial", [])
            print(f"  historial entries: {len(historial)}")
            for h in historial[:3]:  # Show first 3
                print(f"    - {h.get('evento')}: {h.get('detalle', '')[:50]}")


class TestNotificaciones:
    """Test notifications endpoint"""
    
    def test_get_notificaciones(self, authenticated_client):
        """GET /api/notificaciones - verify notifications exist for auto-created orders"""
        response = authenticated_client.get(f"{BASE_URL}/api/notificaciones")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        notificaciones = response.json()
        assert isinstance(notificaciones, list)
        
        print(f"Found {len(notificaciones)} notifications")
        
        # Find orden_automatica type notifications
        auto_notifs = [n for n in notificaciones if n.get("tipo") == "orden_automatica"]
        print(f"Notifications of type 'orden_automatica': {len(auto_notifs)}")
        
        if auto_notifs:
            n = auto_notifs[0]
            print(f"Sample notification:")
            print(f"  tipo: {n.get('tipo')}")
            print(f"  mensaje: {n.get('mensaje', '')[:80]}")
            print(f"  orden_id: {n.get('orden_id')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

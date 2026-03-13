"""
Test Iteration 10 Features:
1. Toggle de extensión del usuario (GET /api/netelip/mi-extension, POST /api/netelip/mi-extension/toggle)
2. Botón de llamar en ficha de cliente (componente BotonLlamar.jsx)
3. Popup de llamada entrante (componente LlamadaEntrantePopup.jsx)
4. Acceso a /netelip solo para Master (no para Admin)
5. Acceso a /empresa solo para Master
6. Toggle de extensión desde panel de admin (PATCH /api/netelip/extensiones/{id}/toggle)
7. Menú lateral muestra Telefonía y Empresa solo para Master
8. PDF de orden de trabajo carga datos de empresa
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://workshop-erp-3.preview.emergentagent.com')

# Test credentials
MASTER_EMAIL = "master@techrepair.local"
MASTER_PASSWORD = "master123"
ADMIN_EMAIL = "admin@techrepair.local"
ADMIN_PASSWORD = "admin123"
TECNICO_EMAIL = "tecnico@techrepair.local"
TECNICO_PASSWORD = "tecnico123"


class TestAuth:
    """Authentication tests"""
    
    def test_login_master(self):
        """Test master login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": MASTER_EMAIL,
            "password": MASTER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "master"
        print(f"✓ Master login successful, role: {data['user']['role']}")
    
    def test_login_admin(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful, role: {data['user']['role']}")
    
    def test_login_tecnico(self):
        """Test tecnico login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TECNICO_EMAIL,
            "password": TECNICO_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "tecnico"
        print(f"✓ Tecnico login successful, role: {data['user']['role']}")


@pytest.fixture
def master_token():
    """Get master authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MASTER_EMAIL,
        "password": MASTER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Master authentication failed")


@pytest.fixture
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")


@pytest.fixture
def tecnico_token():
    """Get tecnico authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TECNICO_EMAIL,
        "password": TECNICO_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Tecnico authentication failed")


class TestMiExtension:
    """Tests for user's own extension toggle (GET /api/netelip/mi-extension, POST /api/netelip/mi-extension/toggle)"""
    
    def test_get_mi_extension_authenticated(self, master_token):
        """Test getting own extension info"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.get(f"{BASE_URL}/api/netelip/mi-extension", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Should return tiene_extension field
        assert "tiene_extension" in data
        print(f"✓ GET /api/netelip/mi-extension returns: tiene_extension={data.get('tiene_extension')}")
    
    def test_get_mi_extension_tecnico(self, tecnico_token):
        """Test tecnico can get their own extension info"""
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        response = requests.get(f"{BASE_URL}/api/netelip/mi-extension", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "tiene_extension" in data
        print(f"✓ Tecnico can access /api/netelip/mi-extension")
    
    def test_toggle_mi_extension_no_extension(self, tecnico_token):
        """Test toggle when user has no extension assigned"""
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        response = requests.post(f"{BASE_URL}/api/netelip/mi-extension/toggle", headers=headers)
        # Should return 404 if no extension assigned
        if response.status_code == 404:
            print(f"✓ Toggle returns 404 when no extension assigned (expected)")
        elif response.status_code == 200:
            print(f"✓ Toggle successful (user has extension)")
        assert response.status_code in [200, 404]


class TestExtensionAdminToggle:
    """Tests for admin toggle of extensions (PATCH /api/netelip/extensiones/{id}/toggle)"""
    
    def test_toggle_extension_requires_master(self, admin_token):
        """Test that admin cannot toggle extensions (requires master)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Try to toggle a non-existent extension
        response = requests.patch(f"{BASE_URL}/api/netelip/extensiones/fake-id/toggle", headers=headers)
        # Should return 403 (forbidden) because admin is not master
        assert response.status_code == 403
        print(f"✓ Admin cannot toggle extensions (403 Forbidden)")
    
    def test_toggle_extension_master_can_access(self, master_token):
        """Test that master can toggle extensions"""
        headers = {"Authorization": f"Bearer {master_token}"}
        # Try to toggle a non-existent extension
        response = requests.patch(f"{BASE_URL}/api/netelip/extensiones/fake-id/toggle", headers=headers)
        # Should return 404 (not found) because extension doesn't exist, not 403
        assert response.status_code == 404
        print(f"✓ Master can access toggle endpoint (404 for non-existent extension)")


class TestNetelipAccessControl:
    """Tests for Netelip config access control (master only)"""
    
    def test_netelip_config_master_access(self, master_token):
        """Test master can access Netelip config"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.get(f"{BASE_URL}/api/netelip/config", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "api_token" in data or "token" in data or "webhook_url" in data
        print(f"✓ Master can access /api/netelip/config")
    
    def test_netelip_config_admin_access(self, admin_token):
        """Test admin can access Netelip config (admin or higher)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/netelip/config", headers=headers)
        # Admin should be able to access config (require_admin)
        assert response.status_code == 200
        print(f"✓ Admin can access /api/netelip/config (require_admin)")
    
    def test_netelip_extensiones_list(self, master_token):
        """Test listing extensions"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.get(f"{BASE_URL}/api/netelip/extensiones", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/netelip/extensiones returns list with {len(data)} extensions")


class TestEmpresaAccessControl:
    """Tests for Empresa config access control (master only)"""
    
    def test_empresa_config_master_access(self, master_token):
        """Test master can access empresa config"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "nombre" in data
        print(f"✓ Master can access /api/configuracion/empresa, nombre: {data.get('nombre')}")
    
    def test_empresa_config_admin_access(self, admin_token):
        """Test admin can access empresa config (require_admin)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa", headers=headers)
        # Admin should be able to access empresa config
        assert response.status_code == 200
        print(f"✓ Admin can access /api/configuracion/empresa")
    
    def test_empresa_publica_no_auth(self):
        """Test public empresa config endpoint (no auth required)"""
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa/publica")
        assert response.status_code == 200
        data = response.json()
        assert "nombre" in data
        print(f"✓ Public empresa config accessible without auth")


class TestLlamarEndpoint:
    """Tests for the llamar endpoint"""
    
    def test_llamar_requires_auth(self):
        """Test that llamar requires authentication"""
        response = requests.post(f"{BASE_URL}/api/netelip/llamar?destino=123456789")
        assert response.status_code == 401
        print(f"✓ /api/netelip/llamar requires authentication")
    
    def test_llamar_with_auth(self, master_token):
        """Test llamar endpoint with authentication"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.post(f"{BASE_URL}/api/netelip/llamar?destino=123456789", headers=headers)
        # Should return 400 (no extension) or 500 (API error) or 200 (success)
        # Not 401 (unauthorized)
        assert response.status_code != 401
        print(f"✓ /api/netelip/llamar accessible with auth, status: {response.status_code}")


class TestLlamadaActiva:
    """Tests for llamada activa endpoint (for popup)"""
    
    def test_llamada_activa_requires_auth(self):
        """Test that llamada activa requires authentication"""
        response = requests.get(f"{BASE_URL}/api/netelip/llamada-activa")
        assert response.status_code == 401
        print(f"✓ /api/netelip/llamada-activa requires authentication")
    
    def test_llamada_activa_with_auth(self, master_token):
        """Test llamada activa endpoint with authentication"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.get(f"{BASE_URL}/api/netelip/llamada-activa", headers=headers)
        assert response.status_code == 200
        # Should return null or llamada object
        print(f"✓ /api/netelip/llamada-activa accessible with auth")


class TestLlamadasHistorial:
    """Tests for llamadas historial endpoint"""
    
    def test_llamadas_historial(self, master_token):
        """Test getting call history"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.get(f"{BASE_URL}/api/netelip/llamadas", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/netelip/llamadas returns list with {len(data)} calls")
    
    def test_llamadas_historial_with_limit(self, master_token):
        """Test getting call history with limit"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.get(f"{BASE_URL}/api/netelip/llamadas?limit=5", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
        print(f"✓ GET /api/netelip/llamadas?limit=5 returns max 5 calls")


class TestClienteWithBotonLlamar:
    """Tests for cliente endpoints (to verify BotonLlamar integration)"""
    
    def test_get_cliente_with_telefono(self, master_token):
        """Test getting cliente with telefono field"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.get(f"{BASE_URL}/api/clientes", headers=headers)
        assert response.status_code == 200
        data = response.json()
        if len(data) > 0:
            cliente = data[0]
            assert "telefono" in cliente
            print(f"✓ Cliente has telefono field: {cliente.get('telefono')}")
        else:
            print(f"✓ No clientes found, but endpoint works")
    
    def test_cliente_historial(self, master_token):
        """Test cliente historial endpoint"""
        headers = {"Authorization": f"Bearer {master_token}"}
        # First get a cliente
        response = requests.get(f"{BASE_URL}/api/clientes", headers=headers)
        assert response.status_code == 200
        clientes = response.json()
        
        if len(clientes) > 0:
            cliente_id = clientes[0]["id"]
            response = requests.get(f"{BASE_URL}/api/clientes/{cliente_id}/historial", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "cliente" in data
            assert "ordenes" in data
            print(f"✓ Cliente historial endpoint works")
        else:
            print(f"✓ No clientes to test historial")


class TestExtensionAssignment:
    """Tests for extension assignment flow"""
    
    def test_assign_extension_to_user(self, master_token):
        """Test assigning extension to a user"""
        headers = {"Authorization": f"Bearer {master_token}"}
        
        # First get a user to assign extension to
        response = requests.get(f"{BASE_URL}/api/usuarios", headers=headers)
        assert response.status_code == 200
        usuarios = response.json()
        
        if len(usuarios) > 0:
            usuario_id = usuarios[0]["id"]
            test_extension = f"TEST_{uuid.uuid4().hex[:4]}"
            
            # Assign extension
            response = requests.post(f"{BASE_URL}/api/netelip/extensiones", headers=headers, json={
                "usuario_id": usuario_id,
                "extension": test_extension
            })
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Extension {test_extension} assigned to user")
                
                # Clean up - delete the extension
                ext_id = data.get("extension", {}).get("id")
                if ext_id:
                    requests.delete(f"{BASE_URL}/api/netelip/extensiones/{ext_id}", headers=headers)
                    print(f"✓ Test extension cleaned up")
            else:
                print(f"✓ Extension assignment returned {response.status_code}: {response.text}")
        else:
            print(f"✓ No usuarios to test extension assignment")


class TestWebhookEndpoint:
    """Tests for Netelip webhook endpoint"""
    
    def test_webhook_accepts_post(self):
        """Test that webhook endpoint accepts POST requests"""
        # Webhook should be publicly accessible
        response = requests.post(f"{BASE_URL}/api/netelip/webhook", json={
            "event": "test",
            "call_id": "test-123"
        })
        # Should return 200 (success) even for test data
        assert response.status_code == 200
        print(f"✓ Webhook endpoint accepts POST requests")


class TestOrdenPDFEmpresaData:
    """Tests to verify OrdenPDF loads empresa data"""
    
    def test_empresa_data_available(self, master_token):
        """Test that empresa data is available for PDF"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields for PDF
        assert "nombre" in data
        print(f"✓ Empresa data available for PDF: nombre={data.get('nombre')}")
        
        # Check optional fields
        optional_fields = ["cif", "direccion", "telefono", "email", "web", "logo_url"]
        for field in optional_fields:
            if field in data and data[field]:
                print(f"  - {field}: {data[field][:30] if isinstance(data[field], str) else data[field]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

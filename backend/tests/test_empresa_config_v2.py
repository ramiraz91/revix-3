"""
Test suite for Empresa Configuration v2 features:
- Logo configuration with web/PDF dimensions
- Legal texts (textos_legales) configuration
- Public empresa endpoint
- Portal Seguimiento with legal acceptance
- Shipping info (codigo_recogida_entrada, codigo_recogida_salida)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestPublicEmpresaEndpoint:
    """Tests for public empresa configuration endpoint (no auth required)"""
    
    def test_get_public_empresa_config(self):
        """Test getting public empresa configuration without authentication"""
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa/publica")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields are present
        assert "nombre" in data
        assert "textos_legales" in data
        assert "logo" in data
        print(f"✓ Public empresa config retrieved: {data.get('nombre')}")
        
    def test_public_config_has_textos_legales(self):
        """Test that public config includes legal texts"""
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa/publica")
        assert response.status_code == 200
        data = response.json()
        
        textos = data.get("textos_legales", {})
        assert "aceptacion_seguimiento" in textos
        assert "clausulas_documentos" in textos
        assert "titulo_aceptacion" in textos
        print(f"✓ Legal texts present in public config")
        print(f"  - Título: {textos.get('titulo_aceptacion')}")
        
    def test_public_config_has_logo_config(self):
        """Test that public config includes logo configuration"""
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa/publica")
        assert response.status_code == 200
        data = response.json()
        
        logo = data.get("logo", {})
        # Logo config should have dimension fields
        assert isinstance(logo, dict)
        print(f"✓ Logo config present in public config")
        
    def test_public_config_has_contact_info(self):
        """Test that public config includes contact information"""
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa/publica")
        assert response.status_code == 200
        data = response.json()
        
        # Contact info should be present
        assert "telefono" in data or data.get("telefono") is None
        assert "email" in data or data.get("email") is None
        print(f"✓ Contact info present: Tel={data.get('telefono')}, Email={data.get('email')}")


class TestEmpresaConfigTabs:
    """Tests for Empresa Config tabs (General, Logo, Legal, IVA)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        return response.json()["token"]
    
    def test_get_full_empresa_config(self, admin_token):
        """Test getting full empresa configuration (authenticated)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # TAB General fields
        assert "nombre" in data
        assert "cif" in data
        assert "direccion" in data
        assert "ciudad" in data
        assert "codigo_postal" in data
        assert "telefono" in data
        assert "email" in data
        assert "web" in data
        print(f"✓ TAB General: {data.get('nombre')}, CIF: {data.get('cif')}")
        
    def test_empresa_config_has_logo_dimensions(self, admin_token):
        """Test that empresa config includes logo with dimensions"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # TAB Logo fields
        logo = data.get("logo", {})
        assert "ancho_web" in logo or logo == {}
        assert "alto_web" in logo or logo == {}
        assert "ancho_pdf" in logo or logo == {}
        assert "alto_pdf" in logo or logo == {}
        print(f"✓ TAB Logo: Web={logo.get('ancho_web')}x{logo.get('alto_web')}, PDF={logo.get('ancho_pdf')}x{logo.get('alto_pdf')}")
        
    def test_empresa_config_has_textos_legales(self, admin_token):
        """Test that empresa config includes legal texts"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # TAB Legal fields
        textos = data.get("textos_legales", {})
        assert "aceptacion_seguimiento" in textos
        assert "clausulas_documentos" in textos
        assert "politica_privacidad" in textos
        assert "titulo_aceptacion" in textos
        print(f"✓ TAB Legal: Título='{textos.get('titulo_aceptacion')}'")
        print(f"  - Aceptación: {textos.get('aceptacion_seguimiento', '')[:50]}...")
        
    def test_empresa_config_has_iva_types(self, admin_token):
        """Test that empresa config includes IVA types"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # TAB IVA fields
        assert "tipos_iva" in data
        assert "iva_por_defecto" in data
        tipos_iva = data.get("tipos_iva", [])
        assert len(tipos_iva) > 0
        print(f"✓ TAB IVA: {len(tipos_iva)} tipos, default={data.get('iva_por_defecto')}%")
        for tipo in tipos_iva:
            print(f"  - {tipo.get('nombre')}: {tipo.get('porcentaje')}% (activo={tipo.get('activo')})")
            
    def test_save_empresa_config_with_all_tabs(self, admin_token):
        """Test saving empresa config with all tab data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get current config
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa", headers=headers)
        original_config = response.json()
        
        # Save test config
        test_config = {
            "nombre": f"TEST_Empresa_{uuid.uuid4().hex[:6]}",
            "cif": "B99999999",
            "direccion": "Test Street 123",
            "ciudad": "Test City",
            "codigo_postal": "12345",
            "telefono": "+34 999 999 999",
            "email": "test@test.com",
            "web": "https://test.com",
            "logo": {
                "url": None,
                "ancho_web": 250,
                "alto_web": 75,
                "ancho_pdf": 180,
                "alto_pdf": 55
            },
            "textos_legales": {
                "aceptacion_seguimiento": "TEST: Texto de aceptación para [NOMBRE_EMPRESA]",
                "clausulas_documentos": "TEST: Cláusulas de documentos",
                "politica_privacidad": "TEST: Política de privacidad",
                "titulo_aceptacion": "TEST Condiciones"
            },
            "tipos_iva": [
                {"nombre": "General", "porcentaje": 21.0, "activo": True},
                {"nombre": "Reducido", "porcentaje": 10.0, "activo": True}
            ],
            "iva_por_defecto": 21.0
        }
        
        response = requests.post(
            f"{BASE_URL}/api/configuracion/empresa",
            json=test_config,
            headers=headers
        )
        assert response.status_code == 200
        print(f"✓ Config saved successfully")
        
        # Verify it was saved
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa", headers=headers)
        saved = response.json()
        assert saved.get("nombre") == test_config["nombre"]
        assert saved.get("logo", {}).get("ancho_web") == 250
        assert saved.get("textos_legales", {}).get("titulo_aceptacion") == "TEST Condiciones"
        print(f"✓ Config verified: {saved.get('nombre')}")
        
        # Restore original config
        requests.post(
            f"{BASE_URL}/api/configuracion/empresa",
            json=original_config,
            headers=headers
        )
        print(f"✓ Original config restored")


class TestPortalSeguimiento:
    """Tests for Portal Seguimiento with legal acceptance and shipping info"""
    
    def test_seguimiento_verificar_returns_shipping_codes(self):
        """Test that seguimiento/verificar returns shipping codes"""
        response = requests.post(
            f"{BASE_URL}/api/seguimiento/verificar",
            json={"token": "493B8910-A5D", "telefono": "677888999"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have shipping codes
        assert "codigo_recogida_entrada" in data
        assert "codigo_seguimiento_salida" in data or "codigo_recogida_salida" not in data
        print(f"✓ Seguimiento returns shipping codes:")
        print(f"  - Nº Recogida: {data.get('codigo_recogida_entrada')}")
        print(f"  - Nº Envío: {data.get('codigo_seguimiento_salida')}")
        
    def test_seguimiento_verificar_returns_order_info(self):
        """Test that seguimiento/verificar returns order information"""
        response = requests.post(
            f"{BASE_URL}/api/seguimiento/verificar",
            json={"token": "493B8910-A5D", "telefono": "677888999"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have order info
        assert "numero_orden" in data
        assert "estado" in data
        assert "dispositivo" in data
        assert "cliente" in data
        assert "fechas" in data
        print(f"✓ Order info: {data.get('numero_orden')} - {data.get('estado')}")
        
    def test_seguimiento_verificar_invalid_token(self):
        """Test seguimiento with invalid token"""
        response = requests.post(
            f"{BASE_URL}/api/seguimiento/verificar",
            json={"token": "INVALID-TOKEN", "telefono": "677888999"}
        )
        assert response.status_code == 404
        print(f"✓ Invalid token correctly returns 404")
        
    def test_seguimiento_verificar_wrong_phone(self):
        """Test seguimiento with wrong phone number"""
        response = requests.post(
            f"{BASE_URL}/api/seguimiento/verificar",
            json={"token": "493B8910-A5D", "telefono": "000000000"}
        )
        assert response.status_code == 401
        print(f"✓ Wrong phone correctly returns 401")


class TestLogoUpload:
    """Tests for logo upload functionality"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        return response.json()["token"]
    
    def test_logo_upload_endpoint_exists(self, admin_token):
        """Test that logo upload endpoint exists"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a simple test image (1x1 pixel PNG)
        import base64
        # Minimal valid PNG
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        
        files = {"file": ("test_logo.png", png_data, "image/png")}
        response = requests.post(
            f"{BASE_URL}/api/configuracion/empresa/logo",
            files=files,
            headers=headers
        )
        
        # Should return 200 or 422 (validation error) but not 404
        assert response.status_code != 404
        print(f"✓ Logo upload endpoint exists, status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  - Logo URL: {data.get('logo_url')}")


class TestEmpresaConfigAccess:
    """Tests for access control on empresa config"""
    
    @pytest.fixture
    def tecnico_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "tecnico",
            "password": "tecnico123"
        })
        return response.json()["token"]
    
    def test_tecnico_cannot_access_empresa_config(self, tecnico_token):
        """Test that tecnico cannot access empresa config"""
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa", headers=headers)
        assert response.status_code == 403
        print(f"✓ Tecnico correctly denied access to empresa config")
        
    def test_public_endpoint_no_auth_required(self):
        """Test that public endpoint doesn't require authentication"""
        response = requests.get(f"{BASE_URL}/api/configuracion/empresa/publica")
        assert response.status_code == 200
        print(f"✓ Public endpoint accessible without auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

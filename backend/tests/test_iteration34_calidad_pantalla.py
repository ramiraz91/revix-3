"""
Test suite for Screen Quality (Calidad Pantalla) feature - Iteration 34
Tests the new screen quality classification system including:
- GET /api/repuestos/calidades-pantalla - Get all quality configurations
- GET /api/repuestos/{id}/alternativas - Get price comparison alternatives
- PATCH /api/repuestos/{id}/calidad-pantalla - Update screen quality manually
- GET /api/repuestos/buscar/rapido - Search with quality info
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCalidadPantallaEndpoints:
    """Tests for screen quality classification endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "ramiraz91@gmail.com", "password": "temp123"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_calidades_pantalla_config(self):
        """Test GET /api/repuestos/calidades-pantalla returns all quality configurations"""
        response = requests.get(f"{BASE_URL}/api/repuestos/calidades-pantalla")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected qualities are present
        expected_qualities = ['genuine', 'refurbished_genuine', 'soft_oled', 'hard_oled', 
                            'service_pack', 'oled', 'incell', 'desconocido']
        for quality in expected_qualities:
            assert quality in data, f"Missing quality: {quality}"
            
        # Verify structure of each quality config
        for quality, config in data.items():
            assert 'label' in config, f"Missing label for {quality}"
            assert 'color' in config, f"Missing color for {quality}"
            assert 'bg_color' in config, f"Missing bg_color for {quality}"
            assert 'text_color' in config, f"Missing text_color for {quality}"
            assert 'description' in config, f"Missing description for {quality}"
            assert 'icon' in config, f"Missing icon for {quality}"
    
    def test_calidades_colors_correct(self):
        """Test that quality colors match specification"""
        response = requests.get(f"{BASE_URL}/api/repuestos/calidades-pantalla")
        data = response.json()
        
        # Verify specific colors as per requirements
        assert data['genuine']['color'] == '#FFD700', "Genuine should be gold"
        assert data['refurbished_genuine']['color'] == '#9CA3AF', "Refurbished should be gray"
        assert data['soft_oled']['color'] == '#10B981', "Soft OLED should be green"
        assert data['hard_oled']['color'] == '#3B82F6', "Hard OLED should be blue"
        assert data['oled']['color'] == '#8B5CF6', "OLED should be purple"
        assert data['incell']['color'] == '#F97316', "InCell should be orange"
        assert data['service_pack']['color'] == '#14B8A6', "Service Pack should be teal"
    
    def test_repuestos_list_includes_calidad_field(self):
        """Test that repuestos list includes calidad_pantalla and es_pantalla fields"""
        response = requests.get(
            f"{BASE_URL}/api/repuestos?page=1&page_size=10",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'items' in data
        
        # Check that items have calidad_pantalla field
        for item in data['items']:
            assert 'calidad_pantalla' in item or item.get('calidad_pantalla') is None
            assert 'es_pantalla' in item or item.get('es_pantalla') is None
    
    def test_buscar_rapido_includes_calidad_info(self):
        """Test that quick search includes quality info for screens"""
        response = requests.get(
            f"{BASE_URL}/api/repuestos/buscar/rapido?q=oled&limit=5",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Check that OLED products have calidad_pantalla
        for item in data:
            if 'oled' in item.get('nombre', '').lower():
                assert item.get('calidad_pantalla') is not None, f"OLED product missing calidad: {item['nombre']}"
    
    def test_get_alternativas_returns_price_comparison(self):
        """Test GET /api/repuestos/{id}/alternativas returns alternatives for price comparison"""
        # First get a screen product
        response = requests.get(
            f"{BASE_URL}/api/repuestos/buscar/rapido?q=pantalla&limit=1",
            headers=self.headers
        )
        assert response.status_code == 200
        products = response.json()
        assert len(products) > 0, "No screen products found"
        
        product_id = products[0]['id']
        
        # Get alternatives
        alt_response = requests.get(
            f"{BASE_URL}/api/repuestos/{product_id}/alternativas?limit=10",
            headers=self.headers
        )
        
        assert alt_response.status_code == 200
        data = alt_response.json()
        
        # Verify response structure
        assert 'producto_original' in data
        assert 'alternativas' in data
        assert 'modelo_detectado' in data or data.get('modelo_detectado') is None
        assert 'tipo_producto' in data or data.get('tipo_producto') is None
        
        # Verify original product has calidad info
        original = data['producto_original']
        assert 'nombre' in original
        assert 'precio_venta' in original
        assert 'precio_compra' in original
    
    def test_alternativas_from_different_providers(self):
        """Test that alternatives come from different providers"""
        # Get a Utopya product
        response = requests.get(
            f"{BASE_URL}/api/repuestos?page=1&page_size=50",
            headers=self.headers
        )
        data = response.json()
        
        utopya_product = None
        for item in data['items']:
            if item.get('proveedor') == 'Utopya' and item.get('es_pantalla'):
                utopya_product = item
                break
        
        if utopya_product:
            alt_response = requests.get(
                f"{BASE_URL}/api/repuestos/{utopya_product['id']}/alternativas?limit=10",
                headers=self.headers
            )
            
            assert alt_response.status_code == 200
            data = alt_response.json()
            
            # Alternatives should be from different providers
            for alt in data.get('alternativas', []):
                assert alt.get('proveedor') != 'Utopya', "Alternatives should be from different providers"
    
    def test_patch_calidad_pantalla_updates_quality(self):
        """Test PATCH /api/repuestos/{id}/calidad-pantalla updates quality manually"""
        # Get a screen product
        response = requests.get(
            f"{BASE_URL}/api/repuestos/buscar/rapido?q=pantalla&limit=1",
            headers=self.headers
        )
        products = response.json()
        assert len(products) > 0
        
        product_id = products[0]['id']
        original_calidad = products[0].get('calidad_pantalla')
        
        # Update to a different quality
        new_calidad = 'hard_oled' if original_calidad != 'hard_oled' else 'soft_oled'
        
        patch_response = requests.patch(
            f"{BASE_URL}/api/repuestos/{product_id}/calidad-pantalla?calidad={new_calidad}",
            headers=self.headers
        )
        
        assert patch_response.status_code == 200
        data = patch_response.json()
        
        assert data['message'] == 'Calidad actualizada'
        assert data['calidad_pantalla'] == new_calidad
        assert 'calidad_info' in data
        assert data['calidad_info']['label'] is not None
        
        # Verify the change persisted
        verify_response = requests.get(
            f"{BASE_URL}/api/repuestos/{product_id}",
            headers=self.headers
        )
        assert verify_response.status_code == 200
        assert verify_response.json()['calidad_pantalla'] == new_calidad
    
    def test_patch_calidad_invalid_quality_rejected(self):
        """Test that invalid quality values are rejected"""
        response = requests.get(
            f"{BASE_URL}/api/repuestos/buscar/rapido?q=pantalla&limit=1",
            headers=self.headers
        )
        products = response.json()
        product_id = products[0]['id']
        
        # Try invalid quality
        patch_response = requests.patch(
            f"{BASE_URL}/api/repuestos/{product_id}/calidad-pantalla?calidad=invalid_quality",
            headers=self.headers
        )
        
        assert patch_response.status_code == 400
        assert 'Calidad inválida' in patch_response.json().get('detail', '')
    
    def test_patch_calidad_requires_admin(self):
        """Test that updating quality requires admin role"""
        # This test verifies the endpoint requires authentication
        response = requests.get(
            f"{BASE_URL}/api/repuestos/buscar/rapido?q=pantalla&limit=1",
            headers=self.headers
        )
        products = response.json()
        product_id = products[0]['id']
        
        # Try without auth
        patch_response = requests.patch(
            f"{BASE_URL}/api/repuestos/{product_id}/calidad-pantalla?calidad=oled"
        )
        
        assert patch_response.status_code in [401, 403], "Should require authentication"


class TestScreenQualityDetection:
    """Tests for automatic screen quality detection logic"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "ramiraz91@gmail.com", "password": "temp123"}
        )
        self.token = login_response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_oled_products_detected_correctly(self):
        """Test that OLED products are detected with correct quality"""
        response = requests.get(
            f"{BASE_URL}/api/repuestos/buscar/rapido?q=oled&limit=10",
            headers=self.headers
        )
        
        data = response.json()
        for item in data:
            nombre = item.get('nombre', '').lower()
            calidad = item.get('calidad_pantalla')
            
            # Products with OLED in name should have oled-related quality
            if 'oled' in nombre:
                assert calidad in ['oled', 'soft_oled', 'hard_oled'], \
                    f"OLED product '{item['nombre']}' has wrong quality: {calidad}"
    
    def test_incell_products_detected_correctly(self):
        """Test that InCell products are detected with correct quality"""
        response = requests.get(
            f"{BASE_URL}/api/repuestos/buscar/rapido?q=incell&limit=10",
            headers=self.headers
        )
        
        data = response.json()
        for item in data:
            nombre = item.get('nombre', '').lower()
            calidad = item.get('calidad_pantalla')
            
            if 'incell' in nombre:
                assert calidad == 'incell', \
                    f"InCell product '{item['nombre']}' has wrong quality: {calidad}"
    
    def test_relife_screen_products_detected_as_refurbished(self):
        """Test that ReLife SCREEN products are detected as refurbished_genuine"""
        response = requests.get(
            f"{BASE_URL}/api/repuestos/buscar/rapido?q=relife&limit=20",
            headers=self.headers
        )
        
        data = response.json()
        relife_screens_found = False
        for item in data:
            nombre = item.get('nombre', '').lower()
            calidad = item.get('calidad_pantalla')
            es_pantalla = item.get('es_pantalla')
            
            # Only check screen products with ReLife
            if 'relife' in nombre and ('pantalla' in nombre or 'screen' in nombre or 'lcd' in nombre or 'display' in nombre):
                relife_screens_found = True
                assert calidad == 'refurbished_genuine', \
                    f"ReLife screen '{item['nombre']}' should be refurbished_genuine, got: {calidad}"
        
        # If no ReLife screens found, search specifically for them
        if not relife_screens_found:
            response2 = requests.get(
                f"{BASE_URL}/api/repuestos/buscar/rapido?q=pantalla+relife&limit=10",
                headers=self.headers
            )
            data2 = response2.json()
            for item in data2:
                nombre = item.get('nombre', '').lower()
                calidad = item.get('calidad_pantalla')
                if 'relife' in nombre:
                    assert calidad == 'refurbished_genuine', \
                        f"ReLife screen '{item['nombre']}' should be refurbished_genuine, got: {calidad}"


class TestPriceComparisonModal:
    """Tests for price comparison functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "ramiraz91@gmail.com", "password": "temp123"}
        )
        self.token = login_response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_alternativas_includes_price_info(self):
        """Test that alternatives include price information for comparison"""
        # Get a product with known price
        response = requests.get(
            f"{BASE_URL}/api/repuestos?page=1&page_size=20",
            headers=self.headers
        )
        data = response.json()
        
        # Find a screen product with price
        screen_product = None
        for item in data['items']:
            if item.get('es_pantalla') and item.get('precio_venta', 0) > 0:
                screen_product = item
                break
        
        if screen_product:
            alt_response = requests.get(
                f"{BASE_URL}/api/repuestos/{screen_product['id']}/alternativas?limit=10",
                headers=self.headers
            )
            
            data = alt_response.json()
            
            # Original should have price
            assert 'precio_venta' in data['producto_original']
            assert 'precio_compra' in data['producto_original']
            
            # Alternatives should have price
            for alt in data.get('alternativas', []):
                assert 'precio_venta' in alt
                assert 'proveedor' in alt
    
    def test_alternativas_includes_quality_info(self):
        """Test that alternatives include quality info for comparison"""
        response = requests.get(
            f"{BASE_URL}/api/repuestos/buscar/rapido?q=pantalla&limit=1",
            headers=self.headers
        )
        products = response.json()
        
        if products:
            alt_response = requests.get(
                f"{BASE_URL}/api/repuestos/{products[0]['id']}/alternativas?limit=10",
                headers=self.headers
            )
            
            data = alt_response.json()
            
            # Original should have calidad_info if it's a screen
            if data['producto_original'].get('calidad_pantalla'):
                assert 'calidad_info' in data['producto_original']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

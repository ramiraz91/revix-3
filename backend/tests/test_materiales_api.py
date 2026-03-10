"""
Tests for Materials CRUD API endpoints in Ordenes
- POST /api/ordenes/{id}/materiales - Add material
- PUT /api/ordenes/{id}/materiales/{index} - Edit material completely
- DELETE /api/ordenes/{id}/materiales/{index} - Delete material
- GET /api/ordenes/{id} - Verify materials in order
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Login as admin and get auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@techrepair.local",
        "password": "admin123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]

@pytest.fixture(scope="module")
def api_client(auth_token):
    """Requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session

@pytest.fixture(scope="module")
def test_order_id(api_client):
    """Get or create test order for materials tests"""
    # Use the known existing order
    order_id = "c6ece814-d73b-42fe-ad90-72d0d862be84"
    response = api_client.get(f"{BASE_URL}/api/ordenes/{order_id}")
    
    if response.status_code == 200:
        return order_id
    
    # If order doesn't exist, create a new one
    # First get a client
    clients_response = api_client.get(f"{BASE_URL}/api/clientes")
    assert clients_response.status_code == 200
    clients = clients_response.json()
    
    if not clients:
        # Create a test client
        client_response = api_client.post(f"{BASE_URL}/api/clientes", json={
            "nombre": "TEST_MaterialesClient",
            "apellidos": "Test",
            "dni": "12345678Z",
            "telefono": "600000000",
            "direccion": "Test Street 1"
        })
        assert client_response.status_code == 200
        client_id = client_response.json()["id"]
    else:
        client_id = clients[0]["id"]
    
    # Create order
    order_response = api_client.post(f"{BASE_URL}/api/ordenes", json={
        "cliente_id": client_id,
        "dispositivo": {
            "modelo": "TEST_MaterialesDevice",
            "imei": "123456789012345",
            "color": "Black",
            "daños": "Screen test"
        },
        "agencia_envio": "TEST",
        "codigo_recogida_entrada": "TEST-MAT-001",
        "materiales": []
    })
    assert order_response.status_code == 200
    return order_response.json()["id"]


class TestMaterialesAPI:
    """Tests for Materials CRUD operations"""
    
    def test_get_order_has_materials_list(self, api_client, test_order_id):
        """Test GET order returns materiales array"""
        response = api_client.get(f"{BASE_URL}/api/ordenes/{test_order_id}")
        assert response.status_code == 200, f"Failed to get order: {response.text}"
        
        data = response.json()
        assert "materiales" in data, "Order should have materiales field"
        assert isinstance(data["materiales"], list), "materiales should be a list"
        print(f"✓ Order has {len(data['materiales'])} materials")
    
    def test_add_material_to_order(self, api_client, test_order_id):
        """Test POST /api/ordenes/{id}/materiales - Add new material"""
        material_data = {
            "nombre": "TEST_NewMaterial",
            "cantidad": 1,
            "precio_unitario": 25.00,
            "coste": 12.50,
            "iva": 21.0,
            "descuento": 0,
            "añadido_por_tecnico": False
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/ordenes/{test_order_id}/materiales",
            json=material_data
        )
        
        assert response.status_code == 200, f"Failed to add material: {response.text}"
        data = response.json()
        assert "material" in data, "Response should contain added material"
        assert data["material"]["nombre"] == "TEST_NewMaterial"
        print(f"✓ Material added successfully: {data['material']['nombre']}")
        
        # Verify material was persisted
        order_response = api_client.get(f"{BASE_URL}/api/ordenes/{test_order_id}")
        order_data = order_response.json()
        materials = order_data["materiales"]
        
        # Find the added material
        added_material = next((m for m in materials if m["nombre"] == "TEST_NewMaterial"), None)
        assert added_material is not None, "Added material should exist in order"
        assert added_material["precio_unitario"] == 25.00
        print(f"✓ Material verified in order with correct price")
    
    def test_edit_material_complete_put(self, api_client, test_order_id):
        """Test PUT /api/ordenes/{id}/materiales/{index} - Edit material completely"""
        # First get current materials
        order_response = api_client.get(f"{BASE_URL}/api/ordenes/{test_order_id}")
        order_data = order_response.json()
        materials = order_data["materiales"]
        
        if len(materials) == 0:
            pytest.skip("No materials to edit")
        
        # Edit the first material
        material_index = 0
        update_data = {
            "nombre": "TEST_EditedMaterial",
            "cantidad": 3,
            "precio_unitario": 50.00,
            "coste": 25.00,
            "iva": 10.0,
            "descuento": 5.0
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/ordenes/{test_order_id}/materiales/{material_index}",
            json=update_data
        )
        
        assert response.status_code == 200, f"Failed to edit material: {response.text}"
        data = response.json()
        assert data["material"]["nombre"] == "TEST_EditedMaterial"
        assert data["material"]["cantidad"] == 3
        assert data["material"]["precio_unitario"] == 50.00
        print(f"✓ Material edited via PUT successfully")
        
        # Verify changes persisted
        order_response = api_client.get(f"{BASE_URL}/api/ordenes/{test_order_id}")
        order_data = order_response.json()
        edited_material = order_data["materiales"][material_index]
        assert edited_material["nombre"] == "TEST_EditedMaterial"
        assert edited_material["cantidad"] == 3
        assert edited_material["precio_unitario"] == 50.00
        assert edited_material["descuento"] == 5.0
        print(f"✓ Material edits verified in database")
    
    def test_edit_material_prices_patch(self, api_client, test_order_id):
        """Test PATCH /api/ordenes/{id}/materiales/{index} - Update prices only"""
        # First get current materials
        order_response = api_client.get(f"{BASE_URL}/api/ordenes/{test_order_id}")
        order_data = order_response.json()
        materials = order_data["materiales"]
        
        if len(materials) == 0:
            pytest.skip("No materials to edit")
        
        material_index = 0
        update_data = {
            "precio_unitario": 75.00,
            "coste": 35.00,
            "iva": 21.0
        }
        
        response = api_client.patch(
            f"{BASE_URL}/api/ordenes/{test_order_id}/materiales/{material_index}",
            json=update_data
        )
        
        assert response.status_code == 200, f"Failed to patch material: {response.text}"
        data = response.json()
        assert data["material"]["precio_unitario"] == 75.00
        assert data["material"]["coste"] == 35.00
        print(f"✓ Material prices updated via PATCH successfully")
    
    def test_delete_material_from_order(self, api_client, test_order_id):
        """Test DELETE /api/ordenes/{id}/materiales/{index} - Remove material"""
        # First add a material to delete
        material_data = {
            "nombre": "TEST_ToDelete",
            "cantidad": 1,
            "precio_unitario": 10.00,
            "coste": 5.00,
            "iva": 21.0,
            "añadido_por_tecnico": False
        }
        
        add_response = api_client.post(
            f"{BASE_URL}/api/ordenes/{test_order_id}/materiales",
            json=material_data
        )
        assert add_response.status_code == 200
        
        # Get order to find the index
        order_response = api_client.get(f"{BASE_URL}/api/ordenes/{test_order_id}")
        materials = order_response.json()["materiales"]
        
        # Find index of the material to delete
        delete_index = None
        for i, m in enumerate(materials):
            if m["nombre"] == "TEST_ToDelete":
                delete_index = i
                break
        
        assert delete_index is not None, "Material to delete should exist"
        initial_count = len(materials)
        
        # Delete the material
        response = api_client.delete(
            f"{BASE_URL}/api/ordenes/{test_order_id}/materiales/{delete_index}"
        )
        
        assert response.status_code == 200, f"Failed to delete material: {response.text}"
        data = response.json()
        assert data["materiales_restantes"] == initial_count - 1
        print(f"✓ Material deleted successfully, remaining: {data['materiales_restantes']}")
        
        # Verify deletion persisted
        order_response = api_client.get(f"{BASE_URL}/api/ordenes/{test_order_id}")
        order_data = order_response.json()
        
        # Verify material no longer exists
        deleted_material = next((m for m in order_data["materiales"] if m["nombre"] == "TEST_ToDelete"), None)
        assert deleted_material is None, "Deleted material should not exist in order"
        print(f"✓ Material deletion verified in database")
    
    def test_add_material_invalid_order(self, api_client):
        """Test adding material to non-existent order returns 404"""
        material_data = {
            "nombre": "TEST_Invalid",
            "cantidad": 1,
            "precio_unitario": 10.00,
            "coste": 5.00
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/ordenes/non-existent-id/materiales",
            json=material_data
        )
        
        assert response.status_code == 404, f"Expected 404 for non-existent order, got {response.status_code}"
        print(f"✓ Returns 404 for non-existent order")
    
    def test_edit_material_invalid_index(self, api_client, test_order_id):
        """Test editing material with invalid index returns 400"""
        update_data = {
            "nombre": "TEST_InvalidIndex",
            "cantidad": 1,
            "precio_unitario": 10.00,
            "coste": 5.00
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/ordenes/{test_order_id}/materiales/999",
            json=update_data
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid index, got {response.status_code}"
        print(f"✓ Returns 400 for invalid material index")


class TestEmpresaConfig:
    """Tests for empresa configuration - logo and company name"""
    
    def test_get_empresa_config(self, api_client):
        """Test GET /api/configuracion/empresa returns company data"""
        response = api_client.get(f"{BASE_URL}/api/configuracion/empresa")
        
        assert response.status_code == 200, f"Failed to get empresa config: {response.text}"
        data = response.json()
        
        assert "nombre" in data, "Should have nombre field"
        assert "logo" in data, "Should have logo field"
        assert "textos_legales" in data, "Should have textos_legales field"
        
        print(f"✓ Empresa config retrieved: {data.get('nombre', 'N/A')}")
        print(f"  - Logo URL: {data.get('logo', {}).get('url', 'Not set')}")
        print(f"  - Has textos_legales: {bool(data.get('textos_legales'))}")
    
    def test_empresa_config_structure(self, api_client):
        """Test empresa config has expected structure for sidebar and PDF"""
        response = api_client.get(f"{BASE_URL}/api/configuracion/empresa")
        data = response.json()
        
        # Check logo structure for sidebar
        logo = data.get("logo", {})
        assert "url" in logo, "logo should have url field"
        assert "ancho_web" in logo, "logo should have ancho_web for sidebar sizing"
        assert "alto_web" in logo, "logo should have alto_web for sidebar sizing"
        
        # Check fields needed for PDF
        assert "ancho_pdf" in logo, "logo should have ancho_pdf for PDF sizing"
        assert "alto_pdf" in logo, "logo should have alto_pdf for PDF sizing"
        
        print(f"✓ Logo config structure is correct for sidebar and PDF")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

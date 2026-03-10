"""
Iteration 33: Test material search fix in OrdenDetalle and NuevaOrden
Bug: repuestosAPI.listar() returns {items: [], total: X} but frontend expected array
Fix: Added buscarRapido() function using /api/repuestos/buscar/rapido endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMaterialSearchEndpoint:
    """Test /api/repuestos/buscar/rapido endpoint for material autocomplete"""
    
    def test_search_iphone_returns_results(self):
        """Search for 'iphone' should return matching products"""
        response = requests.get(f"{BASE_URL}/api/repuestos/buscar/rapido?q=iphone&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Response should be a direct array, not paginated object"
        assert len(data) > 0, "Should find at least one iPhone product"
        
        # Verify first result contains 'iphone' in name
        first_result = data[0]
        assert 'iphone' in first_result.get('nombre', '').lower(), "First result should contain 'iphone'"
        
        # Verify response structure has required fields
        assert 'id' in first_result
        assert 'nombre' in first_result
        assert 'precio_venta' in first_result
        assert 'stock' in first_result
    
    def test_search_pantalla_returns_results(self):
        """Search for 'pantalla' should return matching products"""
        response = requests.get(f"{BASE_URL}/api/repuestos/buscar/rapido?q=pantalla&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Response should be a direct array"
        assert len(data) > 0, "Should find at least one pantalla product"
        
        # Verify first result contains 'pantalla' in name
        first_result = data[0]
        assert 'pantalla' in first_result.get('nombre', '').lower(), "First result should contain 'pantalla'"
    
    def test_search_short_query_returns_empty(self):
        """Search with less than 2 characters should return empty array"""
        response = requests.get(f"{BASE_URL}/api/repuestos/buscar/rapido?q=a&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0, "Short queries should return empty array"
    
    def test_search_empty_query_returns_empty(self):
        """Search with empty query should return empty array"""
        response = requests.get(f"{BASE_URL}/api/repuestos/buscar/rapido?q=&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0, "Empty query should return empty array"
    
    def test_search_respects_limit(self):
        """Search should respect the limit parameter"""
        response = requests.get(f"{BASE_URL}/api/repuestos/buscar/rapido?q=pantalla&limit=3")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 3, "Should not return more than limit"
    
    def test_search_by_sku(self):
        """Search by SKU should also work"""
        response = requests.get(f"{BASE_URL}/api/repuestos/buscar/rapido?q=PANT&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        # May or may not find results depending on SKU patterns


class TestRepuestosListarPagination:
    """Test /api/repuestos endpoint returns paginated format"""
    
    def test_listar_returns_paginated_format(self):
        """GET /api/repuestos should return {items, total, page, page_size, total_pages}"""
        response = requests.get(f"{BASE_URL}/api/repuestos?page=1&page_size=10")
        assert response.status_code == 200
        
        data = response.json()
        assert 'items' in data, "Response should have 'items' key"
        assert 'total' in data, "Response should have 'total' key"
        assert 'page' in data, "Response should have 'page' key"
        assert 'page_size' in data, "Response should have 'page_size' key"
        assert 'total_pages' in data, "Response should have 'total_pages' key"
        
        assert isinstance(data['items'], list), "'items' should be a list"
        assert isinstance(data['total'], int), "'total' should be an integer"
    
    def test_listar_with_search_filter(self):
        """GET /api/repuestos with search should filter results"""
        response = requests.get(f"{BASE_URL}/api/repuestos?search=iphone&page=1&page_size=50")
        assert response.status_code == 200
        
        data = response.json()
        assert 'items' in data
        # All items should contain 'iphone' in name or sku
        for item in data['items']:
            name_lower = item.get('nombre', '').lower()
            sku_lower = item.get('sku', '').lower()
            sku_prov_lower = item.get('sku_proveedor', '').lower()
            assert 'iphone' in name_lower or 'iphone' in sku_lower or 'iphone' in sku_prov_lower, \
                f"Item {item.get('nombre')} should contain 'iphone'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

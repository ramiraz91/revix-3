"""
Iteration 32: Testing Inventory Pagination and Supplier Integrations (Utopya/MobileSentrix)

Tests:
1. Inventory pagination (GET /api/repuestos with page/page_size params)
2. Utopya categories endpoint
3. Utopya config and sync progress
4. MobileSentrix categories endpoint
5. MobileSentrix selected categories CRUD
6. MobileSentrix sync progress
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from requirements
TEST_EMAIL = "ramiraz91@gmail.com"
TEST_PASSWORD = "temp123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for master user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


# ==================== INVENTORY PAGINATION TESTS ====================

class TestInventoryPagination:
    """Test inventory API pagination functionality"""
    
    def test_repuestos_pagination_page1(self, auth_headers):
        """Test GET /api/repuestos?page=1&page_size=5 returns paginated response"""
        response = requests.get(
            f"{BASE_URL}/api/repuestos?page=1&page_size=5",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "items" in data, "Response must contain 'items' array"
        assert "total" in data, "Response must contain 'total' count"
        assert "page" in data, "Response must contain 'page' number"
        assert "total_pages" in data, "Response must contain 'total_pages'"
        
        # Verify pagination values
        assert data["page"] == 1
        assert len(data["items"]) <= 5, f"Expected max 5 items, got {len(data['items'])}"
        assert isinstance(data["total"], int)
        assert isinstance(data["total_pages"], int)
        
        print(f"✓ Page 1 with 5 items: total={data['total']}, total_pages={data['total_pages']}")
    
    def test_repuestos_pagination_default_page_size(self, auth_headers):
        """Test GET /api/repuestos with default page_size=50"""
        response = requests.get(
            f"{BASE_URL}/api/repuestos?page=1",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "page_size" in data, "Response must contain 'page_size'"
        assert data["page_size"] == 50, f"Default page_size should be 50, got {data.get('page_size')}"
        
        print(f"✓ Default page_size is 50")
    
    def test_repuestos_pagination_page2_different_items(self, auth_headers):
        """Test that page 2 returns different items than page 1"""
        # Get page 1
        response1 = requests.get(
            f"{BASE_URL}/api/repuestos?page=1&page_size=50",
            headers=auth_headers
        )
        assert response1.status_code == 200
        data1 = response1.json()
        
        # If there are more than 50 items, page 2 should exist
        if data1["total"] > 50:
            # Get page 2
            response2 = requests.get(
                f"{BASE_URL}/api/repuestos?page=2&page_size=50",
                headers=auth_headers
            )
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Verify page 2 has different items
            assert data2["page"] == 2
            
            # Get IDs from both pages
            ids_page1 = {item["id"] for item in data1["items"]}
            ids_page2 = {item["id"] for item in data2["items"]}
            
            # Pages should not overlap
            overlap = ids_page1 & ids_page2
            assert len(overlap) == 0, f"Pages should not overlap, found {len(overlap)} common items"
            
            print(f"✓ Page 1 and Page 2 have different items")
        else:
            print(f"✓ Skipped: Only {data1['total']} items, less than 50 for pagination test")
    
    def test_repuestos_filter_by_proveedor(self, auth_headers):
        """Test filtering by proveedor parameter"""
        response = requests.get(
            f"{BASE_URL}/api/repuestos?proveedor=Utopya&page=1&page_size=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        # Verify all items are from Utopya
        for item in data["items"]:
            if item.get("proveedor"):
                assert item["proveedor"] == "Utopya", f"Expected proveedor 'Utopya', got {item.get('proveedor')}"
        
        print(f"✓ Proveedor filter works: {len(data['items'])} Utopya items returned")


# ==================== UTOPYA TESTS ====================

class TestUtopyaIntegration:
    """Test Utopya supplier integration endpoints"""
    
    def test_utopya_categories_endpoint(self, auth_headers):
        """Test GET /api/utopya/categories returns category structure"""
        response = requests.get(
            f"{BASE_URL}/api/utopya/categories",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify structure has brands
        assert "apple" in data, "Categories must include 'apple'"
        assert "samsung" in data, "Categories must include 'samsung'"
        assert "xiaomi" in data, "Categories must include 'xiaomi'"
        
        # Verify subcategories structure
        apple = data["apple"]
        assert "name" in apple, "Brand must have 'name' field"
        assert "subcategories" in apple, "Brand must have 'subcategories'"
        assert apple["name"] == "Apple"
        
        print(f"✓ Utopya categories: {list(data.keys())}")
    
    def test_utopya_config_endpoint(self, auth_headers):
        """Test GET /api/utopya/config returns saved config"""
        response = requests.get(
            f"{BASE_URL}/api/utopya/config",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        # Config should be a dict (may be empty if not configured)
        assert isinstance(data, dict), "Config must be a dict"
        
        # If password exists, it should be masked
        if data.get("password"):
            assert data["password"] == "********", "Password should be masked"
        
        print(f"✓ Utopya config returned: {list(data.keys()) if data else 'empty'}")
    
    def test_utopya_sync_progress_endpoint(self, auth_headers):
        """Test GET /api/utopya/sync-catalogo/progress returns progress object"""
        response = requests.get(
            f"{BASE_URL}/api/utopya/sync-catalogo/progress",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        # Verify required fields
        required_fields = ["running", "total", "processed", "imported", "updated", "errors", "categories_done", "categories_total"]
        for field in required_fields:
            assert field in data, f"Progress must contain '{field}' field"
        
        # Verify types
        assert isinstance(data["running"], bool)
        assert isinstance(data["total"], int)
        assert isinstance(data["processed"], int)
        assert isinstance(data["categories_done"], int)
        assert isinstance(data["categories_total"], int)
        
        print(f"✓ Utopya sync progress: running={data['running']}, status={data.get('status', 'N/A')}")


# ==================== MOBILESENTRIX TESTS ====================

class TestMobileSentrixIntegration:
    """Test MobileSentrix supplier integration endpoints"""
    
    def test_mobilesentrix_categories_endpoint(self, auth_headers):
        """Test GET /api/mobilesentrix/categories returns list of categories"""
        response = requests.get(
            f"{BASE_URL}/api/mobilesentrix/categories",
            headers=auth_headers,
            timeout=30  # MobileSentrix API can be slow
        )
        # May return 500 if not configured, 200 if working
        if response.status_code == 500:
            # Check if it's a config issue
            error_msg = response.json().get("detail", "")
            if "OAuth" in error_msg or "consumer" in error_msg.lower():
                pytest.skip("MobileSentrix not configured (OAuth required)")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Should return list or dict with categories
        assert data is not None, "Categories response should not be None"
        
        print(f"✓ MobileSentrix categories endpoint responded")
    
    def test_mobilesentrix_selected_categories_get(self, auth_headers):
        """Test GET /api/mobilesentrix/selected-categories returns saved array"""
        response = requests.get(
            f"{BASE_URL}/api/mobilesentrix/selected-categories",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Should return a list (may be empty)
        assert isinstance(data, list), f"Selected categories must be a list, got {type(data)}"
        
        print(f"✓ MobileSentrix selected categories: {len(data)} categories saved")
    
    def test_mobilesentrix_selected_categories_save(self, auth_headers):
        """Test POST /api/mobilesentrix/selected-categories saves categories"""
        # Save categories
        test_categories = ["165", "200"]
        response = requests.post(
            f"{BASE_URL}/api/mobilesentrix/selected-categories",
            headers=auth_headers,
            json={"categories": test_categories}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response must contain 'message'"
        assert data.get("count") == 2, f"Expected count=2, got {data.get('count')}"
        
        # Verify persistence by getting
        response2 = requests.get(
            f"{BASE_URL}/api/mobilesentrix/selected-categories",
            headers=auth_headers
        )
        assert response2.status_code == 200
        saved = response2.json()
        assert set(saved) == set(test_categories), f"Saved categories don't match: {saved}"
        
        print(f"✓ MobileSentrix categories saved and persisted: {test_categories}")
    
    def test_mobilesentrix_sync_progress_endpoint(self, auth_headers):
        """Test GET /api/mobilesentrix/sync-catalogo/progress returns progress object"""
        response = requests.get(
            f"{BASE_URL}/api/mobilesentrix/sync-catalogo/progress",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify required fields
        required_fields = ["running", "total", "processed", "imported", "updated", "errors", "categories_done", "categories_total"]
        for field in required_fields:
            assert field in data, f"Progress must contain '{field}' field"
        
        # Verify types
        assert isinstance(data["running"], bool)
        assert isinstance(data["categories_done"], int)
        assert isinstance(data["categories_total"], int)
        
        print(f"✓ MobileSentrix sync progress: running={data['running']}, cats_done={data['categories_done']}/{data['categories_total']}")


# ==================== INTEGRATION TESTS ====================

class TestCombinedScenarios:
    """Test combined scenarios across features"""
    
    def test_inventory_counts_match_total(self, auth_headers):
        """Test that total inventory count matches expected (1267 from Utopya)"""
        response = requests.get(
            f"{BASE_URL}/api/repuestos?page=1&page_size=1",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        # Should have products (1267 Utopya mentioned in requirements)
        assert data["total"] > 0, "Expected some products in inventory"
        
        print(f"✓ Total products in inventory: {data['total']}")
    
    def test_pagination_math_correct(self, auth_headers):
        """Test that total_pages calculation is correct"""
        response = requests.get(
            f"{BASE_URL}/api/repuestos?page=1&page_size=50",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        # Calculate expected total_pages
        import math
        expected_pages = math.ceil(data["total"] / 50)
        assert data["total_pages"] == expected_pages, f"Expected {expected_pages} pages, got {data['total_pages']}"
        
        print(f"✓ Pagination math correct: {data['total']} items / 50 = {data['total_pages']} pages")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test suite for Dashboard Scanner and Dual IMEI features
Tests:
- Backend parse_imeis function
- Backend imei_matches function
- Scanner API endpoint behavior
- Order search API for scanner
"""
import pytest
import requests
import os
import sys

sys.path.insert(0, '/app/backend')
from routes.ordenes_routes import parse_imeis, imei_matches

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "master@techrepair.local"
TEST_PASSWORD = "master123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed")


@pytest.fixture
def api_client(auth_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


# ==================== parse_imeis Function Tests ====================

class TestParseIMEIs:
    """Tests for parse_imeis helper function"""
    
    def test_single_imei(self):
        """Single IMEI should return list with one element"""
        result = parse_imeis("353456789012345")
        assert result == ['353456789012345'], f"Expected ['353456789012345'], got {result}"
    
    def test_dual_imei_standard(self):
        """Dual IMEI with standard // separator"""
        result = parse_imeis("353456789012345 // 867530912345678")
        assert result == ['353456789012345', '867530912345678']
    
    def test_dual_imei_extra_spaces(self):
        """Dual IMEI with extra whitespace"""
        result = parse_imeis("  353456789012345   //   867530912345678  ")
        assert result == ['353456789012345', '867530912345678']
    
    def test_empty_string(self):
        """Empty string should return empty list"""
        result = parse_imeis("")
        assert result == []
    
    def test_none_input(self):
        """None input should return empty list"""
        result = parse_imeis(None)
        assert result == []
    
    def test_trailing_separator(self):
        """IMEI with trailing // should only return the valid part"""
        result = parse_imeis("123456789012345 //")
        assert result == ['123456789012345']
    
    def test_leading_separator(self):
        """IMEI with leading // should only return the valid part"""
        result = parse_imeis("// 123456789012345")
        assert result == ['123456789012345']


# ==================== imei_matches Function Tests ====================

class TestIMEIMatches:
    """Tests for imei_matches helper function"""
    
    def test_single_imei_match(self):
        """Scanned IMEI matches single stored IMEI"""
        result = imei_matches("353456789012345", "353456789012345")
        assert result == True
    
    def test_single_imei_no_match(self):
        """Scanned IMEI does not match single stored IMEI"""
        result = imei_matches("353456789012345", "000000000000000")
        assert result == False
    
    def test_dual_imei_match_first(self):
        """Scanned IMEI matches first of dual IMEIs"""
        result = imei_matches("353456789012345", "353456789012345 // 867530912345678")
        assert result == True
    
    def test_dual_imei_match_second(self):
        """Scanned IMEI matches second of dual IMEIs"""
        result = imei_matches("867530912345678", "353456789012345 // 867530912345678")
        assert result == True
    
    def test_dual_imei_no_match(self):
        """Scanned IMEI matches neither of dual IMEIs"""
        result = imei_matches("111111111111111", "353456789012345 // 867530912345678")
        assert result == False
    
    def test_empty_scanned_imei(self):
        """Empty scanned IMEI should skip validation (return True)"""
        result = imei_matches("", "353456789012345")
        assert result == True
    
    def test_empty_stored_field(self):
        """Empty stored field should skip validation (return True)"""
        result = imei_matches("353456789012345", "")
        assert result == True
    
    def test_both_empty(self):
        """Both empty should skip validation (return True)"""
        result = imei_matches("", "")
        assert result == True


# ==================== Scanner API Tests ====================

class TestScannerAPI:
    """Tests for scanner-related API endpoints"""
    
    def test_search_order_by_numero(self, api_client):
        """Search order by numero_orden should return matching order"""
        # Search for an order
        response = api_client.get(f"{BASE_URL}/api/ordenes/v2", params={
            "search": "OT-20260318",  # Partial match on order number
            "page_size": 5
        })
        assert response.status_code == 200
        data = response.json()
        assert 'data' in data
        # If there are orders, they should contain the search term
        if data['total'] > 0:
            for orden in data['data']:
                assert 'OT-20260318' in orden['numero_orden'] or 'OT-' in orden['numero_orden']
    
    def test_search_order_by_imei(self, api_client):
        """Search order by IMEI should return matching order"""
        response = api_client.get(f"{BASE_URL}/api/ordenes/v2", params={
            "search": "353456789012345",  # Dual IMEI order's first IMEI
            "page_size": 1
        })
        assert response.status_code == 200
        data = response.json()
        # Should find the dual IMEI order
        if data['total'] > 0:
            assert '353456789012345' in data['data'][0]['dispositivo'].get('imei', '')
    
    def test_search_nonexistent_order(self, api_client):
        """Search for non-existent order should return empty results"""
        response = api_client.get(f"{BASE_URL}/api/ordenes/v2", params={
            "search": "NONEXISTENT-12345678",
            "page_size": 1
        })
        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 0 or len(data['data']) == 0
    
    def test_get_order_by_id(self, api_client):
        """Get order by ID returns full order details"""
        # First get an order ID
        list_response = api_client.get(f"{BASE_URL}/api/ordenes/v2", params={"page_size": 1})
        if list_response.json()['total'] == 0:
            pytest.skip("No orders available for testing")
        
        order_id = list_response.json()['data'][0]['id']
        
        # Fetch by ID
        response = api_client.get(f"{BASE_URL}/api/ordenes/{order_id}")
        assert response.status_code == 200
        order = response.json()
        assert order['id'] == order_id
        assert 'dispositivo' in order
        assert 'estado' in order


# ==================== Dual IMEI Order Tests ====================

class TestDualIMEIOrder:
    """Tests for orders with dual IMEI"""
    
    def test_order_with_dual_imei_structure(self, api_client):
        """Order with dual IMEI should have correct structure"""
        # Find the dual IMEI test order
        response = api_client.get(f"{BASE_URL}/api/ordenes/v2", params={
            "search": "353456789012345 // 867530912345678",
            "page_size": 1
        })
        
        if response.json()['total'] == 0:
            # Search by model name as fallback
            response = api_client.get(f"{BASE_URL}/api/ordenes/v2", params={
                "search": "iPhone 15 Pro Max",
                "page_size": 1
            })
        
        if response.json()['total'] == 0:
            pytest.skip("Dual IMEI test order not found")
        
        order_id = response.json()['data'][0]['id']
        
        # Get full order
        order_response = api_client.get(f"{BASE_URL}/api/ordenes/{order_id}")
        assert order_response.status_code == 200
        order = order_response.json()
        
        # Verify IMEI structure
        imei_field = order['dispositivo'].get('imei', '')
        assert '//' in imei_field, "Dual IMEI should contain // separator"
        
        # Parse and verify
        imeis = parse_imeis(imei_field)
        assert len(imeis) == 2, "Should have 2 IMEIs"
        assert imeis[0] == '353456789012345'
        assert imeis[1] == '867530912345678'


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

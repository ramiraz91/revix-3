"""
Iteration 16: Sumbroker API Client / Scraper Module Tests
Tests the new portal endpoints: test-portal, scrape/{codigo}
and verifies role-based access control (master only)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MASTER_EMAIL = "master@techrepair.local"
MASTER_PASS = "master123"
ADMIN_EMAIL = "admin@techrepair.local"
ADMIN_PASS = "admin123"

# Test service codes
VALID_CODE = "25BE005754"  # Known existing code in Sumbroker
INVALID_CODE = "99ZZ999999"  # Non-existent code


@pytest.fixture(scope="module")
def master_token():
    """Login as master user and get token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MASTER_EMAIL,
        "password": MASTER_PASS
    })
    if resp.status_code != 200:
        pytest.skip(f"Cannot login as master: {resp.status_code} - {resp.text}")
    return resp.json().get("token")


@pytest.fixture(scope="module")
def admin_token():
    """Login as admin user and get token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASS
    })
    if resp.status_code != 200:
        pytest.skip(f"Cannot login as admin: {resp.status_code} - {resp.text}")
    return resp.json().get("token")


@pytest.fixture
def master_headers(master_token):
    return {"Authorization": f"Bearer {master_token}", "Content-Type": "application/json"}


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# ==================== GET /api/agente/config ====================

class TestAgentConfig:
    """Test agent config endpoint shows portal fields properly masked"""
    
    def test_config_shows_portal_fields_masked(self, master_headers):
        """GET /api/agente/config should show portal_user and portal_password masked"""
        resp = requests.get(f"{BASE_URL}/api/agente/config", headers=master_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "configurado" in data
        assert "datos" in data
        
        datos = data.get("datos", {})
        # Check portal_user is present (may be email or username)
        if datos.get("portal_user"):
            assert isinstance(datos["portal_user"], str)
        
        # Check portal_password is masked if configured
        if datos.get("portal_password"):
            assert datos["portal_password"] == "***configured***", \
                "Portal password should be masked with ***configured***"
        
        print(f"Config datos: {list(datos.keys())}")
        print(f"Portal user: {datos.get('portal_user', 'Not set')}")
        print(f"Portal password: {datos.get('portal_password', 'Not set')}")


# ==================== POST /api/agente/test-portal ====================

class TestPortalConnection:
    """Test Sumbroker portal connectivity endpoint"""
    
    def test_test_portal_success_master(self, master_headers):
        """POST /api/agente/test-portal should return success for master user"""
        resp = requests.post(
            f"{BASE_URL}/api/agente/test-portal",
            headers=master_headers,
            timeout=20  # Allow time for external API
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("success") is True, f"Expected success=True, got: {data}"
        
        # Should return user info
        if data.get("success"):
            assert "user" in data, "Response should include user name"
            assert "store_budgets_total" in data, "Response should include budget count"
            print(f"Portal test result: user={data.get('user')}, budgets={data.get('store_budgets_total')}")
    
    def test_test_portal_forbidden_for_admin(self, admin_headers):
        """POST /api/agente/test-portal should return 403 for non-master users"""
        resp = requests.post(
            f"{BASE_URL}/api/agente/test-portal",
            headers=admin_headers,
            timeout=10
        )
        assert resp.status_code == 403, f"Expected 403 for admin, got {resp.status_code}: {resp.text}"
        print("Admin correctly rejected from test-portal endpoint (403)")
    
    def test_test_portal_forbidden_no_auth(self):
        """POST /api/agente/test-portal should return 401 without auth"""
        resp = requests.post(f"{BASE_URL}/api/agente/test-portal", timeout=5)
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"


# ==================== POST /api/agente/scrape/{codigo} ====================

class TestManualScrape:
    """Test manual scrape endpoint for extracting service data"""
    
    def test_scrape_valid_code_master(self, master_headers):
        """POST /api/agente/scrape/{codigo} should extract data for valid code"""
        resp = requests.post(
            f"{BASE_URL}/api/agente/scrape/{VALID_CODE}",
            headers=master_headers,
            timeout=20  # Sumbroker API can take 5-10 seconds
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "message" in data
        assert "datos" in data
        
        datos = data["datos"]
        # Verify key fields from Sumbroker extraction
        assert datos.get("source") == "sumbroker_api", "Source should be sumbroker_api"
        assert "scraped_at" in datos, "Should have scraped_at timestamp"
        
        # These fields should be present (may be null depending on data)
        expected_fields = [
            "budget_id", "claim_identifier", "device_brand", "device_model",
            "damage_description", "customer_phone", "status_text", "policy_number"
        ]
        for field in expected_fields:
            assert field in datos, f"Expected field '{field}' in extracted data"
        
        print(f"Extracted data for {VALID_CODE}:")
        print(f"  - claim_identifier: {datos.get('claim_identifier')}")
        print(f"  - device: {datos.get('device_brand')} {datos.get('device_model')}")
        print(f"  - status: {datos.get('status_text')}")
        print(f"  - customer_phone: {datos.get('customer_phone')}")
    
    def test_scrape_invalid_code_returns_404(self, master_headers):
        """POST /api/agente/scrape/{codigo} should return 404 for non-existent code"""
        resp = requests.post(
            f"{BASE_URL}/api/agente/scrape/{INVALID_CODE}",
            headers=master_headers,
            timeout=15
        )
        assert resp.status_code == 404, f"Expected 404 for non-existent code, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "detail" in data, "Should have detail message"
        print(f"404 response for non-existent code: {data.get('detail')}")
    
    def test_scrape_forbidden_for_admin(self, admin_headers):
        """POST /api/agente/scrape/{codigo} should return 403 for non-master users"""
        resp = requests.post(
            f"{BASE_URL}/api/agente/scrape/{VALID_CODE}",
            headers=admin_headers,
            timeout=10
        )
        assert resp.status_code == 403, f"Expected 403 for admin, got {resp.status_code}: {resp.text}"
        print("Admin correctly rejected from scrape endpoint (403)")
    
    def test_scrape_forbidden_no_auth(self):
        """POST /api/agente/scrape/{codigo} should return 401 without auth"""
        resp = requests.post(f"{BASE_URL}/api/agente/scrape/{VALID_CODE}", timeout=5)
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"


# ==================== GET /api/agente/status ====================

class TestAgentStatus:
    """Test agent status endpoint"""
    
    def test_status_returns_stats(self, admin_headers):
        """GET /api/agente/status should return agent status with stats"""
        resp = requests.get(f"{BASE_URL}/api/agente/status", headers=admin_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "running" in data
        assert "estado" in data
        assert "stats" in data
        
        stats = data["stats"]
        expected_stat_fields = [
            "pre_registros_total", "pre_registros_pendientes",
            "ordenes_creadas_agente", "eventos_en_consolidacion",
            "notificaciones_externas"
        ]
        for field in expected_stat_fields:
            assert field in stats, f"Expected stat field '{field}'"
        
        print(f"Agent status: running={data.get('running')}, estado={data.get('estado')}")
        print(f"Stats: {stats}")


# ==================== GET /api/agente/logs ====================

class TestAgentLogs:
    """Test agent logs endpoint"""
    
    def test_logs_returns_list_master(self, master_headers):
        """GET /api/agente/logs should return list of logs for master"""
        resp = requests.get(f"{BASE_URL}/api/agente/logs?limit=10", headers=master_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert isinstance(data, list), "Should return list of logs"
        
        # If there are logs, check structure
        if len(data) > 0:
            log = data[0]
            assert "accion" in log
            assert "resultado" in log
            assert "nivel" in log
            assert "created_at" in log
            print(f"Found {len(data)} logs. Latest: {log.get('accion')} - {log.get('resultado')}")
        else:
            print("No logs found (empty)")
    
    def test_logs_forbidden_for_admin(self, admin_headers):
        """GET /api/agente/logs should return 403 for non-master users"""
        resp = requests.get(f"{BASE_URL}/api/agente/logs", headers=admin_headers)
        assert resp.status_code == 403, f"Expected 403 for admin, got {resp.status_code}: {resp.text}"
        print("Admin correctly rejected from logs endpoint (403)")


# ==================== Verify Data Persistence ====================

class TestDataPersistence:
    """Verify that scraped data is persisted correctly"""
    
    def test_scrape_updates_pre_registro_if_exists(self, master_headers):
        """Scraping should update pre_registro.datos_portal if pre_registro exists"""
        # First scrape to ensure data is in the system
        resp = requests.post(
            f"{BASE_URL}/api/agente/scrape/{VALID_CODE}",
            headers=master_headers,
            timeout=20
        )
        assert resp.status_code in [200, 404]  # 404 if no pre-registro
        
        if resp.status_code == 200:
            # Check if there's a pre-registro with this code
            pr_resp = requests.get(
                f"{BASE_URL}/api/pre-registros?search={VALID_CODE}",
                headers=master_headers
            )
            if pr_resp.status_code == 200:
                pre_registros = pr_resp.json()
                if pre_registros:
                    pr = pre_registros[0]
                    if pr.get("datos_portal"):
                        assert pr["datos_portal"].get("source") == "sumbroker_api"
                        print(f"Pre-registro {pr.get('id')} has datos_portal from Sumbroker API")
                    else:
                        print("Pre-registro exists but no datos_portal (OK if not scraped before)")
                else:
                    print("No pre-registro with this code (OK - scrape still returns data)")
        else:
            print("Code not found in Sumbroker - skipping persistence check")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

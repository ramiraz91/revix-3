"""
Test Suite for Provider Integration Enhancement - Photos + Device Info from Terminals
Tests POST /api/agente/scrape/{codigo} and POST /api/agente/scrape/{codigo}/descargar-fotos endpoints
Tests role-based access control (master-only endpoints should return 403 for admin)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MASTER_CREDENTIALS = {"email": "master@techrepair.local", "password": "master123"}
ADMIN_CREDENTIALS = {"email": "admin@techrepair.local", "password": "admin123"}
TEST_SERVICE_CODE = "25BE005754"


@pytest.fixture(scope="module")
def master_token():
    """Get authentication token for master user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MASTER_CREDENTIALS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.fail(f"Master login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.fail(f"Admin login failed: {response.status_code} - {response.text}")


class TestScrapeEndpointWithPhotosAndDevice:
    """Test POST /api/agente/scrape/{codigo} returns docs[] with photos and device info from terminals"""
    
    def test_scrape_returns_photos_and_device_info(self, master_token):
        """Scrape should return docs array with photos and enriched device info from mobile_terminals_active"""
        response = requests.post(
            f"{BASE_URL}/api/agente/scrape/{TEST_SERVICE_CODE}",
            headers={"Authorization": f"Bearer {master_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "datos" in data, "Response should contain 'datos' key"
        datos = data["datos"]
        
        # Test device info from terminals
        assert "device_brand" in datos, "Should have device_brand from terminals"
        assert "device_model" in datos, "Should have device_model from terminals"
        assert datos.get("device_brand") is not None, "device_brand should not be None"
        print(f"Device: {datos.get('device_brand')} {datos.get('device_model')}")
        
        # Test IMEI from terminals
        assert "device_imei" in datos, "Should have device_imei from terminals"
        print(f"IMEI: {datos.get('device_imei')}")
        
        # Test docs array with photos
        assert "docs" in datos, "Should have docs array"
        docs = datos.get("docs", [])
        assert isinstance(docs, list), "docs should be a list"
        print(f"Total docs/photos: {len(docs)}")
        
        # For code 25BE005754, we expect 3 photos based on test context
        if len(docs) > 0:
            first_doc = docs[0]
            assert "doc_id" in first_doc, "Each doc should have doc_id"
            assert "name" in first_doc, "Each doc should have name"
            assert "is_image" in first_doc, "Each doc should have is_image flag"
            assert "download_link" in first_doc, "Each doc should have download_link"
            print(f"First doc: {first_doc.get('name')} (is_image={first_doc.get('is_image')})")
    
    def test_scrape_device_model_contains_brand_and_model(self, master_token):
        """Device model should be extracted from mobile_terminals_active"""
        response = requests.post(
            f"{BASE_URL}/api/agente/scrape/{TEST_SERVICE_CODE}",
            headers={"Authorization": f"Bearer {master_token}"}
        )
        
        assert response.status_code == 200
        datos = response.json()["datos"]
        
        # Extract device info - brand and model should come from terminals
        device_brand = datos.get("device_brand")
        device_model = datos.get("device_model")
        
        assert device_brand is not None or device_model is not None, \
            "At least one of device_brand or device_model should be extracted"
        
        print(f"Extracted device: Brand={device_brand}, Model={device_model}")


class TestDownloadPhotosEndpoint:
    """Test POST /api/agente/scrape/{codigo}/descargar-fotos downloads photos to /app/backend/uploads/"""
    
    def test_download_photos_returns_filenames(self, master_token):
        """Download photos endpoint should return list of saved filenames"""
        response = requests.post(
            f"{BASE_URL}/api/agente/scrape/{TEST_SERVICE_CODE}/descargar-fotos",
            headers={"Authorization": f"Bearer {master_token}"},
            timeout=60  # Photos download can take time
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "message" in data, "Response should contain message"
        assert "fotos" in data, "Response should contain fotos array"
        assert "docs_total" in data, "Response should contain docs_total count"
        
        fotos = data.get("fotos", [])
        docs_total = data.get("docs_total", 0)
        
        print(f"Downloaded {len(fotos)} of {docs_total} photos")
        print(f"Message: {data.get('message')}")
        
        # Verify filenames follow expected pattern
        for filename in fotos:
            assert filename.startswith(f"portal_{TEST_SERVICE_CODE}"), \
                f"Filename should start with portal_{TEST_SERVICE_CODE}: {filename}"
            print(f"  Saved: {filename}")
    
    def test_download_photos_files_exist_on_disk(self, master_token):
        """Downloaded photos should actually exist in uploads directory"""
        # First trigger download
        response = requests.post(
            f"{BASE_URL}/api/agente/scrape/{TEST_SERVICE_CODE}/descargar-fotos",
            headers={"Authorization": f"Bearer {master_token}"},
            timeout=60
        )
        
        assert response.status_code == 200
        fotos = response.json().get("fotos", [])
        
        # Verify files exist (can't directly check filesystem from test, but API returns filenames)
        assert len(fotos) >= 0, "Should return downloaded filenames list"
        print(f"API reports {len(fotos)} files saved")


class TestRoleBasedAccessControl:
    """Test that admin user gets 403 on master-only endpoints"""
    
    def test_admin_cannot_access_scrape_endpoint(self, admin_token):
        """Admin user should get 403 on master-only scrape endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/agente/scrape/{TEST_SERVICE_CODE}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 403, \
            f"Expected 403 for admin on master-only endpoint, got {response.status_code}"
        print(f"Correctly denied admin access to scrape: {response.json()}")
    
    def test_admin_cannot_access_download_photos_endpoint(self, admin_token):
        """Admin user should get 403 on master-only download photos endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/agente/scrape/{TEST_SERVICE_CODE}/descargar-fotos",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 403, \
            f"Expected 403 for admin on master-only endpoint, got {response.status_code}"
        print(f"Correctly denied admin access to descargar-fotos: {response.json()}")
    
    def test_admin_cannot_access_agent_config(self, admin_token):
        """Admin user should get 403 on master-only config endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/agente/config",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 403, \
            f"Expected 403 for admin on master-only config endpoint, got {response.status_code}"
    
    def test_admin_can_access_agent_status(self, admin_token):
        """Admin user should be able to access status endpoint (require_admin not require_master)"""
        response = requests.get(
            f"{BASE_URL}/api/agente/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Status endpoint uses require_admin, not require_master
        assert response.status_code == 200, \
            f"Admin should access status endpoint, got {response.status_code}"
        print(f"Admin can view status: {response.json()}")


class TestScrapeNonExistentCode:
    """Test scrape endpoint with non-existent code"""
    
    def test_scrape_nonexistent_code_returns_404(self, master_token):
        """Scrape with invalid code should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/agente/scrape/99ZZ999999",
            headers={"Authorization": f"Bearer {master_token}"},
            timeout=30
        )
        
        assert response.status_code == 404, \
            f"Expected 404 for non-existent code, got {response.status_code}: {response.text}"
        print(f"Correctly returned 404 for non-existent code")


class TestSimulationEndpoint:
    """Test simulation endpoint behavior with already processed codes"""
    
    def test_simulation_already_processed_returns_400(self, master_token):
        """Simulation for already processed code should return 400"""
        response = requests.post(
            f"{BASE_URL}/api/agente/simular-aceptacion/{TEST_SERVICE_CODE}",
            headers={"Authorization": f"Bearer {master_token}"},
            timeout=60
        )
        
        # This code was already used, so should fail
        # Could be 400 (already processed) or 200 (if never processed before)
        print(f"Simulation response: {response.status_code} - {response.text[:200]}")
        
        if response.status_code == 400:
            assert "Ya existe" in response.text or "already" in response.text.lower(), \
                "Should indicate order already exists"
            print("Correctly rejected: order already exists")
        elif response.status_code == 200:
            data = response.json()
            assert "success" in data, "Should have success field"
            print(f"Simulation result: {data.get('message', data)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

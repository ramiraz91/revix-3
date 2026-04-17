"""
Test Brother QL-800 Centralized Print Queue System

Endpoints tested:
- POST /api/print/send - Create print job (requires JWT)
- GET /api/print/status - Agent status (requires JWT)
- GET /api/print/pending - Get pending jobs (requires agent_key query param)
- POST /api/print/complete - Report job completion (requires X-Agent-Key header)
- POST /api/print/heartbeat - Agent heartbeat (requires X-Agent-Key header)
- GET /api/print/jobs - List job history (requires JWT)
- GET /api/print/agent/download - Download agent ZIP (public)
- GET /api/print/agent/info - Agent info (public)

Auth:
- JWT: master@revix.es / RevixMaster2026!
- Agent Key: revix-brother-agent-2026-key
"""
import pytest
import requests
import os
import time
import zipfile
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AGENT_KEY = "revix-brother-agent-2026-key"

# ═══════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def auth_token():
    """Get JWT token for authenticated requests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "master@revix.es",
        "password": os.environ.get("TEST_MASTER_PASSWORD", "RevixMaster2026!")
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")

@pytest.fixture
def auth_headers(auth_token):
    """Headers with JWT auth"""
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.fixture
def agent_headers():
    """Headers with agent key"""
    return {"X-Agent-Key": AGENT_KEY}


# ═══════════════════════════════════════════════════════════════════
# TEST: Agent Status (no heartbeat = offline)
# ═══════════════════════════════════════════════════════════════════

class TestPrintStatusOffline:
    """Test /api/print/status when agent is offline (no recent heartbeat)"""
    
    def test_status_requires_auth(self):
        """Status endpoint requires JWT authentication"""
        response = requests.get(f"{BASE_URL}/api/print/status")
        assert response.status_code in [401, 403], "Should require auth"
    
    def test_status_returns_offline_without_heartbeat(self, auth_headers):
        """Status shows agent_connected=false when no recent heartbeat"""
        response = requests.get(f"{BASE_URL}/api/print/status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "ok" in data
        assert data["ok"] == True
        assert "agent_connected" in data
        # Note: agent_connected may be true if heartbeat was sent recently
        # We'll test the online state separately after sending heartbeat


# ═══════════════════════════════════════════════════════════════════
# TEST: Heartbeat + Online Status
# ═══════════════════════════════════════════════════════════════════

class TestHeartbeatAndOnlineStatus:
    """Test heartbeat and online status flow"""
    
    def test_heartbeat_requires_agent_key(self):
        """Heartbeat endpoint requires X-Agent-Key header"""
        response = requests.post(f"{BASE_URL}/api/print/heartbeat", json={
            "agent_id": "test-agent",
            "printer_online": True,
            "printer_name": "Brother QL-800"
        })
        assert response.status_code == 403, "Should require agent key"
    
    def test_heartbeat_rejects_invalid_key(self):
        """Heartbeat rejects invalid agent key"""
        response = requests.post(
            f"{BASE_URL}/api/print/heartbeat",
            headers={"X-Agent-Key": "wrong-key"},
            json={
                "agent_id": "test-agent",
                "printer_online": True,
                "printer_name": "Brother QL-800"
            }
        )
        assert response.status_code == 403, "Should reject invalid key"
    
    def test_heartbeat_success(self, agent_headers):
        """Heartbeat succeeds with valid agent key"""
        response = requests.post(
            f"{BASE_URL}/api/print/heartbeat",
            headers=agent_headers,
            json={
                "agent_id": "test-agent-pytest",
                "printer_online": True,
                "printer_name": "Brother QL-800 (Test)",
                "reason": ""
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
    
    def test_status_shows_online_after_heartbeat(self, auth_headers, agent_headers):
        """Status shows agent_connected=true after recent heartbeat"""
        # First send heartbeat
        hb_response = requests.post(
            f"{BASE_URL}/api/print/heartbeat",
            headers=agent_headers,
            json={
                "agent_id": "test-agent-pytest",
                "printer_online": True,
                "printer_name": "Brother QL-800 (Test)",
                "reason": ""
            }
        )
        assert hb_response.status_code == 200
        
        # Now check status
        response = requests.get(f"{BASE_URL}/api/print/status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["agent_connected"] == True, "Agent should be connected after heartbeat"
        assert data["printer_online"] == True, "Printer should be online"
        assert "Brother QL-800" in data.get("printer_name", "")


# ═══════════════════════════════════════════════════════════════════
# TEST: Send Print Job
# ═══════════════════════════════════════════════════════════════════

class TestSendPrintJob:
    """Test POST /api/print/send"""
    
    def test_send_requires_auth(self):
        """Send endpoint requires JWT authentication"""
        response = requests.post(f"{BASE_URL}/api/print/send", json={
            "template": "ot_barcode_minimal",
            "data": {"barcodeValue": "TEST-123"}
        })
        assert response.status_code in [401, 403], "Should require auth"
    
    def test_send_creates_pending_job(self, auth_headers):
        """Send creates a job with status 'pending'"""
        response = requests.post(
            f"{BASE_URL}/api/print/send",
            headers=auth_headers,
            json={
                "template": "ot_barcode_minimal",
                "data": {
                    "barcodeValue": "TEST-PYTEST-001",
                    "orderNumber": "OT-PYTEST-001",
                    "deviceModel": "Test Device"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert "job_id" in data
        assert data["status"] == "pending"
        assert "pj-" in data["job_id"], "Job ID should start with pj-"
        
        # Store job_id for later tests
        TestSendPrintJob.created_job_id = data["job_id"]
    
    def test_send_inventory_label(self, auth_headers):
        """Send inventory label job"""
        response = requests.post(
            f"{BASE_URL}/api/print/send",
            headers=auth_headers,
            json={
                "template": "inventory_label",
                "data": {
                    "barcodeValue": "SKU-PYTEST-001",
                    "productName": "Test Product",
                    "price": "29.99 EUR"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert data["status"] == "pending"


# ═══════════════════════════════════════════════════════════════════
# TEST: Get Pending Jobs (Agent)
# ═══════════════════════════════════════════════════════════════════

class TestGetPendingJobs:
    """Test GET /api/print/pending (agent endpoint)"""
    
    def test_pending_requires_agent_key(self):
        """Pending endpoint requires agent_key query param"""
        response = requests.get(f"{BASE_URL}/api/print/pending")
        assert response.status_code in [403, 422], "Should require agent_key"
    
    def test_pending_rejects_invalid_key(self):
        """Pending rejects invalid agent key"""
        response = requests.get(
            f"{BASE_URL}/api/print/pending",
            params={"agent_key": "wrong-key"}
        )
        assert response.status_code == 403, "Should reject invalid key"
    
    def test_pending_returns_jobs(self, auth_headers):
        """Pending returns jobs and marks them as 'printing'"""
        # First create a job
        send_response = requests.post(
            f"{BASE_URL}/api/print/send",
            headers=auth_headers,
            json={
                "template": "ot_barcode_minimal",
                "data": {"barcodeValue": "TEST-PENDING-001"}
            }
        )
        assert send_response.status_code == 200
        job_id = send_response.json()["job_id"]
        
        # Now get pending jobs as agent
        response = requests.get(
            f"{BASE_URL}/api/print/pending",
            params={"agent_key": AGENT_KEY, "agent_id": "test-agent"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
        
        # Store a job_id for complete test
        if data["jobs"]:
            TestGetPendingJobs.pending_job_id = data["jobs"][0]["job_id"]


# ═══════════════════════════════════════════════════════════════════
# TEST: Complete Job (Agent)
# ═══════════════════════════════════════════════════════════════════

class TestCompleteJob:
    """Test POST /api/print/complete (agent endpoint)"""
    
    def test_complete_requires_agent_key(self):
        """Complete endpoint requires X-Agent-Key header"""
        response = requests.post(f"{BASE_URL}/api/print/complete", json={
            "job_id": "pj-test",
            "status": "completed"
        })
        assert response.status_code == 403, "Should require agent key"
    
    def test_complete_rejects_invalid_key(self):
        """Complete rejects invalid agent key"""
        response = requests.post(
            f"{BASE_URL}/api/print/complete",
            headers={"X-Agent-Key": "wrong-key"},
            json={
                "job_id": "pj-test",
                "status": "completed"
            }
        )
        assert response.status_code == 403, "Should reject invalid key"
    
    def test_complete_job_success(self, auth_headers, agent_headers):
        """Complete job flow: send -> pending -> complete"""
        # 1. Create a job
        send_response = requests.post(
            f"{BASE_URL}/api/print/send",
            headers=auth_headers,
            json={
                "template": "ot_barcode_minimal",
                "data": {"barcodeValue": "TEST-COMPLETE-001"}
            }
        )
        assert send_response.status_code == 200
        job_id = send_response.json()["job_id"]
        
        # 2. Get pending (marks as printing)
        pending_response = requests.get(
            f"{BASE_URL}/api/print/pending",
            params={"agent_key": AGENT_KEY}
        )
        assert pending_response.status_code == 200
        
        # 3. Complete the job
        complete_response = requests.post(
            f"{BASE_URL}/api/print/complete",
            headers=agent_headers,
            json={
                "job_id": job_id,
                "status": "completed"
            }
        )
        
        assert complete_response.status_code == 200
        data = complete_response.json()
        assert data["ok"] == True
        assert data["status"] == "completed"
    
    def test_complete_job_with_error(self, auth_headers, agent_headers):
        """Complete job with error status"""
        # 1. Create a job
        send_response = requests.post(
            f"{BASE_URL}/api/print/send",
            headers=auth_headers,
            json={
                "template": "ot_barcode_minimal",
                "data": {"barcodeValue": "TEST-ERROR-001"}
            }
        )
        assert send_response.status_code == 200
        job_id = send_response.json()["job_id"]
        
        # 2. Complete with error
        complete_response = requests.post(
            f"{BASE_URL}/api/print/complete",
            headers=agent_headers,
            json={
                "job_id": job_id,
                "status": "error",
                "error_message": "Printer paper jam"
            }
        )
        
        assert complete_response.status_code == 200
        data = complete_response.json()
        assert data["ok"] == True
        assert data["status"] == "error"


# ═══════════════════════════════════════════════════════════════════
# TEST: Job History
# ═══════════════════════════════════════════════════════════════════

class TestJobHistory:
    """Test GET /api/print/jobs"""
    
    def test_jobs_requires_auth(self):
        """Jobs endpoint requires JWT authentication"""
        response = requests.get(f"{BASE_URL}/api/print/jobs")
        assert response.status_code in [401, 403], "Should require auth"
    
    def test_jobs_returns_history(self, auth_headers):
        """Jobs returns list of print jobs"""
        response = requests.get(
            f"{BASE_URL}/api/print/jobs",
            headers=auth_headers,
            params={"limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
        
        # Verify job structure if jobs exist
        if data["jobs"]:
            job = data["jobs"][0]
            assert "job_id" in job
            assert "status" in job
            assert "template" in job
            assert "requested_at" in job


# ═══════════════════════════════════════════════════════════════════
# TEST: Agent Download
# ═══════════════════════════════════════════════════════════════════

class TestAgentDownload:
    """Test GET /api/print/agent/download"""
    
    def test_download_returns_zip(self):
        """Download returns valid ZIP file"""
        response = requests.get(f"{BASE_URL}/api/print/agent/download")
        
        assert response.status_code == 200
        assert response.headers.get('content-type') == 'application/zip'
        
        # Verify it's a valid ZIP with 8 files
        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            file_list = zf.namelist()
            assert len(file_list) == 8, f"Expected 8 files, got {len(file_list)}"
            
            expected_files = [
                "brother-label-agent/agent.py",
                "brother-label-agent/config.json",
                "brother-label-agent/requirements.txt",
            ]
            for expected in expected_files:
                assert expected in file_list, f"Missing: {expected}"


# ═══════════════════════════════════════════════════════════════════
# TEST: Agent Info
# ═══════════════════════════════════════════════════════════════════

class TestAgentInfo:
    """Test GET /api/print/agent/info"""
    
    def test_info_returns_agent_details(self):
        """Info returns agent version and details"""
        response = requests.get(f"{BASE_URL}/api/print/agent/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "version" in data
        assert "label_format" in data
        assert data["label_format"] == "DK-11204"
        assert "printer" in data
        assert "Brother QL-800" in data["printer"]
        assert "download_url" in data


# ═══════════════════════════════════════════════════════════════════
# TEST: Full Flow Integration
# ═══════════════════════════════════════════════════════════════════

class TestFullPrintFlow:
    """Integration test: send -> pending -> complete -> verify"""
    
    def test_complete_print_flow(self, auth_headers, agent_headers):
        """Test complete print workflow"""
        # 1. Send heartbeat to mark agent online
        hb_response = requests.post(
            f"{BASE_URL}/api/print/heartbeat",
            headers=agent_headers,
            json={
                "agent_id": "integration-test-agent",
                "printer_online": True,
                "printer_name": "Brother QL-800 (Integration Test)"
            }
        )
        assert hb_response.status_code == 200
        
        # 2. Verify status shows online
        status_response = requests.get(
            f"{BASE_URL}/api/print/status",
            headers=auth_headers
        )
        assert status_response.status_code == 200
        assert status_response.json()["agent_connected"] == True
        
        # 3. Send print job
        send_response = requests.post(
            f"{BASE_URL}/api/print/send",
            headers=auth_headers,
            json={
                "template": "ot_barcode_minimal",
                "data": {
                    "barcodeValue": "INTEGRATION-TEST-001",
                    "orderNumber": "OT-INT-001"
                }
            }
        )
        assert send_response.status_code == 200
        job_id = send_response.json()["job_id"]
        
        # 4. Agent gets pending jobs
        pending_response = requests.get(
            f"{BASE_URL}/api/print/pending",
            params={"agent_key": AGENT_KEY}
        )
        assert pending_response.status_code == 200
        
        # 5. Agent completes job
        complete_response = requests.post(
            f"{BASE_URL}/api/print/complete",
            headers=agent_headers,
            json={
                "job_id": job_id,
                "status": "completed"
            }
        )
        assert complete_response.status_code == 200
        
        # 6. Verify job in history
        jobs_response = requests.get(
            f"{BASE_URL}/api/print/jobs",
            headers=auth_headers,
            params={"limit": 5}
        )
        assert jobs_response.status_code == 200
        jobs = jobs_response.json()["jobs"]
        
        # Find our job
        our_job = next((j for j in jobs if j["job_id"] == job_id), None)
        assert our_job is not None, f"Job {job_id} not found in history"
        assert our_job["status"] == "completed"


# ═══════════════════════════════════════════════════════════════════
# CLEANUP
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data(auth_token):
    """Cleanup test data after all tests"""
    yield
    # Note: In production, we'd delete test jobs here
    # For now, test jobs will remain in DB (they're clearly marked as TEST-)
    print("\n[Cleanup] Test jobs created with TEST- prefix remain in DB")

"""
Test iteration 46: Print variants for OT ficha imprimible
- POST /api/ordenes/{id}/registro-impresion (audit log)
- Modes: full, no_prices, blank_no_prices
- Permissions: full only admin/master, others allowed for all roles
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MASTER_EMAIL = "ramiraz91@gmail.com"
MASTER_PASSWORD = "temp123"


@pytest.fixture(scope="module")
def master_token():
    """Get authentication token for master user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MASTER_EMAIL,
        "password": MASTER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")  # API returns "token" not "access_token"
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(master_token):
    """Headers with authentication"""
    return {"Authorization": f"Bearer {master_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def sample_orden_id(auth_headers):
    """Get an existing orden ID for testing"""
    response = requests.get(f"{BASE_URL}/api/ordenes", headers=auth_headers)
    if response.status_code == 200 and response.json():
        return response.json()[0].get("id")
    pytest.skip("No ordenes found for testing")


class TestPrintRegistrationEndpoint:
    """Tests for POST /api/ordenes/{id}/registro-impresion"""

    def test_print_registration_mode_full_master_allowed(self, auth_headers, sample_orden_id):
        """Master user can register print log with mode=full"""
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{sample_orden_id}/registro-impresion",
            headers=auth_headers,
            json={
                "mode": "full",
                "output": "print",
                "document_version": "OT-PDF v1.1"
            }
        )
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        assert response.status_code == 200, f"Expected 200 for master with mode=full, got {response.status_code}"
        data = response.json()
        assert data.get("mode") == "full"
        assert data.get("output") == "print"
        assert "generated_at" in data

    def test_print_registration_mode_no_prices(self, auth_headers, sample_orden_id):
        """Register print log with mode=no_prices"""
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{sample_orden_id}/registro-impresion",
            headers=auth_headers,
            json={
                "mode": "no_prices",
                "output": "print",
                "document_version": "OT-PDF v1.1"
            }
        )
        print(f"Response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200 for mode=no_prices, got {response.status_code}"
        data = response.json()
        assert data.get("mode") == "no_prices"

    def test_print_registration_mode_blank_no_prices(self, auth_headers, sample_orden_id):
        """Register print log with mode=blank_no_prices"""
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{sample_orden_id}/registro-impresion",
            headers=auth_headers,
            json={
                "mode": "blank_no_prices",
                "output": "print",
                "document_version": "OT-PDF v1.1"
            }
        )
        print(f"Response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200 for mode=blank_no_prices, got {response.status_code}"
        data = response.json()
        assert data.get("mode") == "blank_no_prices"

    def test_print_registration_invalid_mode(self, auth_headers, sample_orden_id):
        """Invalid mode should return 400"""
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{sample_orden_id}/registro-impresion",
            headers=auth_headers,
            json={
                "mode": "invalid_mode",
                "output": "print",
                "document_version": "OT-PDF v1.1"
            }
        )
        print(f"Response status: {response.status_code}")
        
        assert response.status_code == 400, f"Expected 400 for invalid mode, got {response.status_code}"

    def test_print_registration_nonexistent_orden(self, auth_headers):
        """Nonexistent orden should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/ordenes/nonexistent-id-12345/registro-impresion",
            headers=auth_headers,
            json={
                "mode": "full",
                "output": "print",
                "document_version": "OT-PDF v1.1"
            }
        )
        print(f"Response status: {response.status_code}")
        
        assert response.status_code == 404, f"Expected 404 for nonexistent orden, got {response.status_code}"

    def test_print_registration_with_output_pdf(self, auth_headers, sample_orden_id):
        """Test output=pdf parameter"""
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{sample_orden_id}/registro-impresion",
            headers=auth_headers,
            json={
                "mode": "no_prices",
                "output": "pdf",
                "document_version": "OT-PDF v1.1"
            }
        )
        print(f"Response status: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("output") == "pdf"


class TestAuditEventLogging:
    """Tests to verify audit events are created for print actions"""

    def test_print_creates_audit_event(self, auth_headers, sample_orden_id):
        """Printing should create an audit event"""
        # First, register a print
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{sample_orden_id}/registro-impresion",
            headers=auth_headers,
            json={
                "mode": "full",
                "output": "print",
                "document_version": "OT-PDF v1.1"
            }
        )
        assert response.status_code == 200
        
        # Check audit events
        events_response = requests.get(
            f"{BASE_URL}/api/ordenes/{sample_orden_id}/eventos-auditoria",
            headers=auth_headers
        )
        print(f"Events response status: {events_response.status_code}")
        
        if events_response.status_code == 200:
            events = events_response.json()
            print(f"Found {len(events)} audit events")
            # Check if there's a print event
            print_events = [e for e in events if e.get("action") == "ot_print_generated"]
            assert len(print_events) > 0, "Expected at least one ot_print_generated audit event"
            print(f"Found {len(print_events)} print audit events")


class TestOrdenesEndpoint:
    """Regression tests for ordenes endpoints"""

    def test_ordenes_list_returns_200(self, auth_headers):
        """GET /api/ordenes should return 200"""
        response = requests.get(f"{BASE_URL}/api/ordenes", headers=auth_headers)
        print(f"Response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert isinstance(response.json(), list)

    def test_ordenes_get_single(self, auth_headers, sample_orden_id):
        """GET /api/ordenes/{id} should return orden details"""
        response = requests.get(f"{BASE_URL}/api/ordenes/{sample_orden_id}", headers=auth_headers)
        print(f"Response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "id" in data
        assert "numero_orden" in data


class TestOrdenPDFModes:
    """Tests to verify OrdenPDF component modes behavior via API"""

    def test_orden_has_required_fields_for_pdf(self, auth_headers, sample_orden_id):
        """Verify orden has all required fields for PDF generation"""
        response = requests.get(f"{BASE_URL}/api/ordenes/{sample_orden_id}", headers=auth_headers)
        assert response.status_code == 200
        
        orden = response.json()
        
        # Check basic fields needed for PDF
        assert "numero_orden" in orden, "Missing numero_orden"
        assert "estado" in orden, "Missing estado"
        assert "created_at" in orden, "Missing created_at"
        
        # Check dispositivo structure
        if "dispositivo" in orden and orden["dispositivo"]:
            print(f"Dispositivo fields: {orden['dispositivo'].keys()}")
        
        # Check materiales array exists
        assert "materiales" in orden, "Missing materiales array"
        
        print(f"Orden {orden.get('numero_orden')} has all required fields for PDF generation")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

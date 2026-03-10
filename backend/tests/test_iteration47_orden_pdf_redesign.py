"""
Iteration 47: Tests for OrdenPDF redesign - photo annex, 3 modes, permissions
Tests: POST /api/ordenes/{id}/registro-impresion with all 3 modes and permission checks
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test OT IDs
OT_WITH_PHOTOS = 'f38a7850-320a-4d59-8bd7-5d063660aaa3'  # TEST-001, 2 photos
OT_WITHOUT_PHOTOS = 'c8adc9dc-dce4-401e-ad96-7e790763e2d7'

# Credentials
MASTER_EMAIL = 'ramiraz91@gmail.com'
MASTER_PASSWORD = 'temp123'
ADMIN_EMAIL = 'admin@techrepair.local'
ADMIN_PASSWORD = 'Admin2026!'


@pytest.fixture(scope='module')
def master_token():
    """Get master user auth token"""
    resp = requests.post(f'{BASE_URL}/api/auth/login', json={
        'email': MASTER_EMAIL,
        'password': MASTER_PASSWORD
    })
    if resp.status_code == 200:
        return resp.json().get('token')
    pytest.skip(f"Master auth failed: {resp.status_code} - {resp.text[:100]}")


@pytest.fixture(scope='module')
def admin_token():
    """Get admin user auth token"""
    resp = requests.post(f'{BASE_URL}/api/auth/login', json={
        'email': ADMIN_EMAIL,
        'password': ADMIN_PASSWORD
    })
    if resp.status_code == 200:
        return resp.json().get('token')
    pytest.skip(f"Admin auth failed: {resp.status_code}")


@pytest.fixture
def master_headers(master_token):
    return {'Authorization': f'Bearer {master_token}', 'Content-Type': 'application/json'}


@pytest.fixture
def admin_headers(admin_token):
    return {'Authorization': f'Bearer {admin_token}', 'Content-Type': 'application/json'}


class TestRegistroImpresionEndpoint:
    """Test POST /api/ordenes/{id}/registro-impresion with all 3 modes"""
    
    def test_registro_impresion_full_mode_master(self, master_headers):
        """Master can register full mode print"""
        resp = requests.post(
            f'{BASE_URL}/api/ordenes/{OT_WITH_PHOTOS}/registro-impresion',
            json={'mode': 'full', 'output': 'print', 'document_version': 'OT-PDF v2.0'},
            headers=master_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert data['mode'] == 'full'
        assert data['orden_id'] == OT_WITH_PHOTOS
        assert data['generated_by'] == MASTER_EMAIL
        print(f"PASS: Full mode print log created: {data['id']}")
    
    def test_registro_impresion_no_prices_mode(self, master_headers):
        """Master can register no_prices mode print"""
        resp = requests.post(
            f'{BASE_URL}/api/ordenes/{OT_WITH_PHOTOS}/registro-impresion',
            json={'mode': 'no_prices', 'output': 'print', 'document_version': 'OT-PDF v2.0'},
            headers=master_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert data['mode'] == 'no_prices'
        print("PASS: no_prices mode print log created")
    
    def test_registro_impresion_blank_no_prices_mode(self, master_headers):
        """Master can register blank_no_prices mode print"""
        resp = requests.post(
            f'{BASE_URL}/api/ordenes/{OT_WITH_PHOTOS}/registro-impresion',
            json={'mode': 'blank_no_prices', 'output': 'print', 'document_version': 'OT-PDF v2.0'},
            headers=master_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert data['mode'] == 'blank_no_prices'
        print("PASS: blank_no_prices mode print log created")
    
    def test_registro_impresion_full_mode_admin(self, admin_headers):
        """Admin can also register full mode print (canPrintWithPrices=true)"""
        resp = requests.post(
            f'{BASE_URL}/api/ordenes/{OT_WITHOUT_PHOTOS}/registro-impresion',
            json={'mode': 'full', 'output': 'print', 'document_version': 'OT-PDF v2.0'},
            headers=admin_headers
        )
        assert resp.status_code == 200, f"Admin should be able to use full mode, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert data['mode'] == 'full'
        print("PASS: Admin can use full mode print")
    
    def test_registro_impresion_invalid_mode(self, master_headers):
        """Invalid mode returns 400"""
        resp = requests.post(
            f'{BASE_URL}/api/ordenes/{OT_WITH_PHOTOS}/registro-impresion',
            json={'mode': 'invalid_mode', 'output': 'print'},
            headers=master_headers
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text[:200]}"
        print("PASS: Invalid mode returns 400")
    
    def test_registro_impresion_nonexistent_orden(self, master_headers):
        """Non-existent orden returns 404"""
        resp = requests.post(
            f'{BASE_URL}/api/ordenes/00000000-0000-0000-0000-000000000000/registro-impresion',
            json={'mode': 'full', 'output': 'print'},
            headers=master_headers
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("PASS: Non-existent orden returns 404")


class TestOrdenDetailsForPDF:
    """Verify the OT with photos has the expected structure for PDF generation"""
    
    def test_ot_with_photos_has_evidencias(self, master_headers):
        """TEST-001 OT should have 2 photos (evidencias)"""
        resp = requests.get(
            f'{BASE_URL}/api/ordenes/{OT_WITH_PHOTOS}',
            headers=master_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        
        total_fotos = len(data.get('evidencias', [])) + len(data.get('evidencias_tecnico', []))
        print(f"OT photos: evidencias={len(data.get('evidencias', []))}, evidencias_tecnico={len(data.get('evidencias_tecnico', []))}, total={total_fotos}")
        
        assert total_fotos >= 2, f"TEST-001 should have at least 2 photos, found {total_fotos}"
        print(f"PASS: OT TEST-001 has {total_fotos} photos (expected >= 2)")
    
    def test_ot_has_required_pdf_fields(self, master_headers):
        """OT should have required fields for PDF generation"""
        resp = requests.get(
            f'{BASE_URL}/api/ordenes/{OT_WITH_PHOTOS}',
            headers=master_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Check required fields
        assert data.get('numero_orden'), "numero_orden should be present"
        assert data.get('estado'), "estado should be present"
        assert data.get('created_at'), "created_at should be present"
        print(f"PASS: OT has required fields - numero_orden: {data['numero_orden']}, estado: {data['estado']}")
    
    def test_ot_without_photos_exists(self, master_headers):
        """OT without photos should also be accessible"""
        resp = requests.get(
            f'{BASE_URL}/api/ordenes/{OT_WITHOUT_PHOTOS}',
            headers=master_headers
        )
        assert resp.status_code == 200, f"OT without photos should exist, got {resp.status_code}"
        data = resp.json()
        total_fotos = len(data.get('evidencias', [])) + len(data.get('evidencias_tecnico', []))
        print(f"PASS: OT without photos exists - {data.get('numero_orden')}, photos: {total_fotos}")


class TestPrintPermissions:
    """Verify print permissions are correct"""
    
    def test_no_prices_mode_works_for_admin(self, admin_headers):
        """no_prices mode should work for admin"""
        resp = requests.post(
            f'{BASE_URL}/api/ordenes/{OT_WITHOUT_PHOTOS}/registro-impresion',
            json={'mode': 'no_prices', 'output': 'print'},
            headers=admin_headers
        )
        assert resp.status_code == 200, f"no_prices should work for admin, got {resp.status_code}"
        print("PASS: Admin can use no_prices mode")
    
    def test_blank_no_prices_mode_works_for_admin(self, admin_headers):
        """blank_no_prices mode should work for admin"""
        resp = requests.post(
            f'{BASE_URL}/api/ordenes/{OT_WITHOUT_PHOTOS}/registro-impresion',
            json={'mode': 'blank_no_prices', 'output': 'print'},
            headers=admin_headers
        )
        assert resp.status_code == 200, f"blank_no_prices should work for admin, got {resp.status_code}"
        print("PASS: Admin can use blank_no_prices mode")

    def test_print_log_response_structure(self, master_headers):
        """Print log response should have correct structure"""
        resp = requests.post(
            f'{BASE_URL}/api/ordenes/{OT_WITH_PHOTOS}/registro-impresion',
            json={'mode': 'full', 'output': 'pdf', 'document_version': 'OT-PDF v2.0'},
            headers=master_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Verify response structure
        assert 'id' in data, "Response should have 'id'"
        assert 'orden_id' in data, "Response should have 'orden_id'"
        assert 'mode' in data, "Response should have 'mode'"
        assert 'generated_by' in data, "Response should have 'generated_by'"
        assert 'generated_at' in data, "Response should have 'generated_at'"
        assert '_id' not in data, "Response should NOT have '_id' (MongoDB ObjectId)"
        print(f"PASS: Print log response structure correct - id: {data['id'][:8]}...")

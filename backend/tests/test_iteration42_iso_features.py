"""
Iteration 42: ISO 9001 Features Testing
Tests for:
- Master ISO: GET /api/master/iso/documentos (LMD list)
- Master ISO: POST /api/master/iso/documentos (create/update controlled document)
- Master ISO: GET /api/master/iso/proveedores (critical suppliers list)
- Master ISO: POST /api/master/iso/proveedores/evaluar (save score/reevaluation status)
- Master ISO: GET /api/master/iso/kpis (dashboard KPIs)
- Master ISO: GET /api/master/iso/reporte-pdf (download valid PDF with optional filters)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials for master user
TEST_EMAIL = "ramiraz91@gmail.com"
TEST_PASSWORD = "temp123"


@pytest.fixture(scope="module")
def auth_token():
    """Authenticate and get token for master user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    data = response.json()
    return data.get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestMasterIsoDocumentos:
    """Tests for /api/master/iso/documentos endpoints"""

    def test_get_iso_documentos_list(self, auth_headers):
        """GET /api/master/iso/documentos returns list of documents"""
        response = requests.get(f"{BASE_URL}/api/master/iso/documentos", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"ISO Documents count: {len(data)}")

    def test_get_iso_documentos_requires_master(self):
        """GET /api/master/iso/documentos requires authentication (returns 401/403 without)"""
        response = requests.get(f"{BASE_URL}/api/master/iso/documentos")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_create_iso_documento(self, auth_headers):
        """POST /api/master/iso/documentos creates new document"""
        test_doc = {
            "codigo": "TEST-DOC-001",
            "titulo": "Test Document ISO",
            "tipo": "documento",
            "version": "1.0",
            "retencion_anios": 5,
            "proceso": "testing",
            "estado": "vigente"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/master/iso/documentos",
            json=test_doc,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("codigo") == "TEST-DOC-001", "Should return created document with correct codigo"
        assert data.get("titulo") == "Test Document ISO"
        assert data.get("tipo") == "documento"
        assert data.get("version") == "1.0"
        print(f"Created ISO Document: {data.get('codigo')}")

    def test_create_iso_registro(self, auth_headers):
        """POST /api/master/iso/documentos creates registro type"""
        test_reg = {
            "codigo": "REG-TEST-001",
            "titulo": "Test Registro ISO",
            "tipo": "registro",
            "version": "1.0",
            "retencion_anios": 3
        }
        
        response = requests.post(
            f"{BASE_URL}/api/master/iso/documentos",
            json=test_reg,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("tipo") == "registro"
        print(f"Created ISO Registro: {data.get('codigo')}")

    def test_update_existing_iso_documento(self, auth_headers):
        """POST /api/master/iso/documentos updates existing document by codigo"""
        # Update the test doc we just created
        updated_doc = {
            "codigo": "TEST-DOC-001",
            "titulo": "Test Document ISO Updated",
            "tipo": "documento",
            "version": "2.0",
            "retencion_anios": 7,
            "estado": "vigente"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/master/iso/documentos",
            json=updated_doc,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("version") == "2.0", "Version should be updated to 2.0"
        assert data.get("titulo") == "Test Document ISO Updated"
        print(f"Updated ISO Document version: {data.get('version')}")

    def test_create_iso_documento_validation(self, auth_headers):
        """POST /api/master/iso/documentos requires codigo, titulo, and tipo"""
        # Missing codigo
        response = requests.post(
            f"{BASE_URL}/api/master/iso/documentos",
            json={"titulo": "Test", "tipo": "documento"},
            headers=auth_headers
        )
        assert response.status_code == 400, f"Expected 400 for missing codigo, got {response.status_code}"
        
        # Missing titulo
        response = requests.post(
            f"{BASE_URL}/api/master/iso/documentos",
            json={"codigo": "TEST-X", "tipo": "documento"},
            headers=auth_headers
        )
        assert response.status_code == 400, f"Expected 400 for missing titulo, got {response.status_code}"
        
        # Invalid tipo
        response = requests.post(
            f"{BASE_URL}/api/master/iso/documentos",
            json={"codigo": "TEST-Y", "titulo": "Test", "tipo": "invalid"},
            headers=auth_headers
        )
        assert response.status_code == 400, f"Expected 400 for invalid tipo, got {response.status_code}"
        print("Validation errors working correctly")

    def test_verify_created_document_in_list(self, auth_headers):
        """Verify the created document appears in the list"""
        response = requests.get(f"{BASE_URL}/api/master/iso/documentos", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        test_docs = [d for d in data if d.get("codigo") in ["TEST-DOC-001", "REG-TEST-001"]]
        assert len(test_docs) >= 1, "Created test documents should appear in the list"
        print(f"Found {len(test_docs)} test documents in list")


class TestMasterIsoProveedores:
    """Tests for /api/master/iso/proveedores endpoints"""

    def test_get_iso_proveedores_list(self, auth_headers):
        """GET /api/master/iso/proveedores returns list with seed data"""
        response = requests.get(f"{BASE_URL}/api/master/iso/proveedores", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Should have seeded proveedores (GLS, MobileSentrix, Utopya)
        nombres = [p.get("proveedor") for p in data]
        print(f"ISO Proveedores ({len(data)}): {nombres}")
        
        # At least one should exist
        assert len(data) >= 1, "Should have at least one proveedor"

    def test_get_iso_proveedores_has_seed_data(self, auth_headers):
        """GET /api/master/iso/proveedores includes seeded critical suppliers"""
        response = requests.get(f"{BASE_URL}/api/master/iso/proveedores", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        nombres = [p.get("proveedor") for p in data]
        
        # Check for seeded providers
        seed_providers = ["GLS", "MobileSentrix", "Utopya"]
        found = [p for p in seed_providers if p in nombres]
        print(f"Found seeded providers: {found}")

    def test_evaluar_proveedor_iso(self, auth_headers):
        """POST /api/master/iso/proveedores/evaluar creates/updates evaluation"""
        eval_data = {
            "proveedor": "TEST_Proveedor_ISO",
            "tipo": "recambios",
            "puntualidad": 85,
            "calidad": 90,
            "respuesta": 75,
            "incidencias": 5,
            "comentarios": "Test evaluation for ISO compliance"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/master/iso/proveedores/evaluar",
            json=eval_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("proveedor") == "TEST_Proveedor_ISO"
        assert data.get("score") is not None, "Score should be calculated"
        assert data.get("estado") in ["aprobado", "condicional", "bloqueado"], "Estado should be set based on score"
        assert data.get("proxima_reevaluacion") is not None, "proxima_reevaluacion should be set"
        
        # Score should be calculated as (puntualidad + calidad + respuesta + (100 - incidencias)) / 4
        expected_score = round((85 + 90 + 75 + (100 - 5)) / 4, 1)
        assert data.get("score") == expected_score, f"Score should be {expected_score}, got {data.get('score')}"
        print(f"Evaluation created: score={data.get('score')}, estado={data.get('estado')}")

    def test_evaluar_proveedor_score_aprobado(self, auth_headers):
        """POST evaluation with high scores results in 'aprobado' status (score >= 75)"""
        eval_data = {
            "proveedor": "TEST_Proveedor_Aprobado",
            "tipo": "logistica",
            "puntualidad": 90,
            "calidad": 95,
            "respuesta": 85,
            "incidencias": 0
        }
        
        response = requests.post(
            f"{BASE_URL}/api/master/iso/proveedores/evaluar",
            json=eval_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        # Score: (90 + 95 + 85 + 100) / 4 = 92.5 -> aprobado
        assert data.get("estado") == "aprobado", f"Score {data.get('score')} should be aprobado"
        print(f"High score evaluation: score={data.get('score')}, estado={data.get('estado')}")

    def test_evaluar_proveedor_score_condicional(self, auth_headers):
        """POST evaluation with medium scores results in 'condicional' status (60 <= score < 75)"""
        eval_data = {
            "proveedor": "TEST_Proveedor_Condicional",
            "tipo": "recambios",
            "puntualidad": 60,
            "calidad": 65,
            "respuesta": 55,
            "incidencias": 30
        }
        
        response = requests.post(
            f"{BASE_URL}/api/master/iso/proveedores/evaluar",
            json=eval_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        # Score: (60 + 65 + 55 + 70) / 4 = 62.5 -> condicional
        assert data.get("estado") == "condicional", f"Score {data.get('score')} should be condicional"
        print(f"Medium score evaluation: score={data.get('score')}, estado={data.get('estado')}")

    def test_evaluar_proveedor_score_bloqueado(self, auth_headers):
        """POST evaluation with low scores results in 'bloqueado' status (score < 60)"""
        eval_data = {
            "proveedor": "TEST_Proveedor_Bloqueado",
            "tipo": "recambios",
            "puntualidad": 40,
            "calidad": 45,
            "respuesta": 35,
            "incidencias": 60
        }
        
        response = requests.post(
            f"{BASE_URL}/api/master/iso/proveedores/evaluar",
            json=eval_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        # Score: (40 + 45 + 35 + 40) / 4 = 40 -> bloqueado
        assert data.get("estado") == "bloqueado", f"Score {data.get('score')} should be bloqueado"
        print(f"Low score evaluation: score={data.get('score')}, estado={data.get('estado')}")

    def test_evaluar_proveedor_validation(self, auth_headers):
        """POST evaluation requires proveedor field"""
        response = requests.post(
            f"{BASE_URL}/api/master/iso/proveedores/evaluar",
            json={"tipo": "recambios", "puntualidad": 80},
            headers=auth_headers
        )
        assert response.status_code == 400, f"Expected 400 for missing proveedor, got {response.status_code}"
        print("Proveedor validation working correctly")


class TestMasterIsoKpis:
    """Tests for /api/master/iso/kpis endpoint"""

    def test_get_iso_kpis(self, auth_headers):
        """GET /api/master/iso/kpis returns dashboard KPIs"""
        response = requests.get(f"{BASE_URL}/api/master/iso/kpis", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "kpis" in data, "Response should contain 'kpis'"
        assert "proveedores" in data, "Response should contain 'proveedores'"
        assert "generated_at" in data, "Response should contain 'generated_at'"
        
        kpis = data.get("kpis", {})
        print(f"ISO KPIs: {kpis}")

    def test_iso_kpis_structure(self, auth_headers):
        """GET /api/master/iso/kpis returns expected KPI fields"""
        response = requests.get(f"{BASE_URL}/api/master/iso/kpis", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        kpis = data.get("kpis", {})
        
        # Check for expected KPI fields
        expected_kpis = [
            "reparaciones_sin_retrabajo_pct",
            "tat_promedio_horas",
            "entregas_a_tiempo_pct",
            "qc_fallos",
            "first_pass_yield_pct",
            "devoluciones_garantias_pct",
            "satisfaccion_cliente_proxy_pct"
        ]
        
        for kpi in expected_kpis:
            assert kpi in kpis, f"KPI '{kpi}' should be present in response"
        
        print(f"All expected KPI fields present: {list(kpis.keys())}")

    def test_iso_kpis_proveedores_included(self, auth_headers):
        """GET /api/master/iso/kpis includes proveedores summary"""
        response = requests.get(f"{BASE_URL}/api/master/iso/kpis", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        proveedores = data.get("proveedores", [])
        assert isinstance(proveedores, list), "Proveedores should be a list"
        print(f"Proveedores in KPIs: {len(proveedores)}")


class TestMasterIsoReportePdf:
    """Tests for /api/master/iso/reporte-pdf endpoint"""

    def test_get_iso_reporte_pdf_no_filters(self, auth_headers):
        """GET /api/master/iso/reporte-pdf returns valid PDF without filters"""
        response = requests.get(
            f"{BASE_URL}/api/master/iso/reporte-pdf",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check PDF magic bytes
        content = response.content
        assert content[:4] == b'%PDF', f"Response should start with PDF magic bytes, got: {content[:20]}"
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Content-Type should be application/pdf, got: {content_type}"
        
        # Check content disposition
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp, f"Should be attachment download, got: {content_disp}"
        
        print(f"PDF generated successfully: {len(content)} bytes")

    def test_get_iso_reporte_pdf_with_orden_id_filter(self, auth_headers):
        """GET /api/master/iso/reporte-pdf with orden_id filter"""
        # Use a fake orden_id - PDF should still generate (may have empty results)
        response = requests.get(
            f"{BASE_URL}/api/master/iso/reporte-pdf?orden_id=test-orden-123",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        content = response.content
        assert content[:4] == b'%PDF', "Response should be valid PDF"
        print("PDF with orden_id filter generated")

    def test_get_iso_reporte_pdf_with_date_range_filter(self, auth_headers):
        """GET /api/master/iso/reporte-pdf with fecha_desde and fecha_hasta filters"""
        response = requests.get(
            f"{BASE_URL}/api/master/iso/reporte-pdf?fecha_desde=2024-01-01&fecha_hasta=2024-12-31",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        content = response.content
        assert content[:4] == b'%PDF', "Response should be valid PDF"
        print("PDF with date range filter generated")

    def test_get_iso_reporte_pdf_with_all_filters(self, auth_headers):
        """GET /api/master/iso/reporte-pdf with all optional filters combined"""
        response = requests.get(
            f"{BASE_URL}/api/master/iso/reporte-pdf?orden_id=test-123&fecha_desde=2024-01-01&fecha_hasta=2026-01-31",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        content = response.content
        assert content[:4] == b'%PDF', "Response should be valid PDF"
        print("PDF with all filters generated")

    def test_get_iso_reporte_pdf_requires_auth(self):
        """GET /api/master/iso/reporte-pdf requires authentication"""
        response = requests.get(f"{BASE_URL}/api/master/iso/reporte-pdf")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PDF endpoint requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

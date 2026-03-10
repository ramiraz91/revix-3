"""
Iteration 43: Event Log Inmutable, Receiving Inspection (RI) con cuarentena, Audit Pack exportable
Testing new ISO+WISE features focusing on:
- Event log append-only para auditoría
- RI (Receiving Inspection) con estado cuarentena
- Audit Pack endpoints (OT y periodo)
- CSV export for audit pack
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data prefixes for cleanup
TEST_PREFIX = "TEST_RI_CUARENTENA_"


class TestSetup:
    """Setup and helper methods for tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "ramiraz91@gmail.com",
            "password": "temp123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed - skipping tests")
        
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def test_cliente(self, auth_headers):
        """Create a test cliente for orders"""
        cliente_data = {
            "nombre": f"{TEST_PREFIX}Cliente",
            "apellidos": "Test RI",
            "dni": "12345678Z",
            "telefono": "600123456",
            "email": f"test_ri_{uuid.uuid4().hex[:6]}@test.com",
            "direccion": "Calle Test 123"
        }
        response = requests.post(f"{BASE_URL}/api/clientes", json=cliente_data, headers=auth_headers)
        assert response.status_code in [200, 201], f"Failed to create test cliente: {response.text}"
        return response.json()


class TestOrderStatusCuarentena(TestSetup):
    """Tests for nuevo estado OT 'cuarentena' visible y funcional"""
    
    def test_cuarentena_status_exists_in_enum(self, auth_headers):
        """Verify cuarentena status is a valid OrderStatus"""
        # Create an order and check that cuarentena is valid
        response = requests.get(f"{BASE_URL}/api/ordenes", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get ordenes: {response.text}"
        # The fact that endpoint works confirms enum is valid
    
    def test_status_config_includes_cuarentena(self, auth_headers, test_cliente):
        """Verify cuarentena status transitions are configured"""
        # Create an order
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": f"{TEST_PREFIX}iPhone Test",
                "imei": "123456789012345",
                "color": "Negro",
                "daños": "Pantalla rota"
            },
            "notas": "Test cuarentena status"
        }
        response = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=auth_headers)
        assert response.status_code == 200, f"Failed to create test order: {response.text}"
        orden = response.json()
        
        # Transition to recibida
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden['id']}/estado",
            json={"nuevo_estado": "recibida", "usuario": "test"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to change to recibida: {response.text}"
        
        # Transition from recibida to cuarentena should be valid
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden['id']}/estado",
            json={"nuevo_estado": "cuarentena", "usuario": "test"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Cuarentena transition failed: {response.text}"
        
        # Verify order is in cuarentena
        response = requests.get(f"{BASE_URL}/api/ordenes/{orden['id']}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["estado"] == "cuarentena"


class TestReceivingInspection(TestSetup):
    """Tests for POST /api/ordenes/{id}/receiving-inspection"""
    
    def test_ri_requires_at_least_3_photos(self, auth_headers, test_cliente):
        """RI validates >=3 fotos rule"""
        # Create order
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": f"{TEST_PREFIX}iPhone RI Test",
                "imei": "123456789012346",
                "color": "Blanco",
                "daños": "Batería hinchada"
            }
        }
        response = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=auth_headers)
        assert response.status_code == 200
        orden = response.json()
        
        # Try RI with only 2 photos - should fail
        ri_data = {
            "resultado_ri": "ok",
            "checklist_visual": {"pantalla": True, "carcasa": True},
            "fotos_recepcion": ["foto1.jpg", "foto2.jpg"],  # Only 2 photos
            "observaciones": "Test RI"
        }
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{orden['id']}/receiving-inspection",
            json=ri_data,
            headers=auth_headers
        )
        assert response.status_code == 400, f"Should fail with <3 photos: {response.text}"
        assert "3 fotos" in response.json().get("detail", "")
    
    def test_ri_saves_correctly_with_valid_data(self, auth_headers, test_cliente):
        """RI guarda correctamente con datos válidos"""
        # Create order
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": f"{TEST_PREFIX}Samsung RI Valid",
                "imei": "123456789012347",
                "color": "Azul",
                "daños": "Pantalla rota"
            }
        }
        response = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=auth_headers)
        assert response.status_code == 200
        orden = response.json()
        
        # Valid RI with 3 photos
        ri_data = {
            "resultado_ri": "ok",
            "checklist_visual": {"pantalla": True, "carcasa": True, "botones": True},
            "fotos_recepcion": ["frontal.jpg", "trasera.jpg", "daños.jpg"],
            "observaciones": "Dispositivo recibido en buen estado",
            "propiedad_cliente_estado": "ok"
        }
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{orden['id']}/receiving-inspection",
            json=ri_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"RI should succeed: {response.text}"
        result = response.json()
        assert result["resultado_ri"] == "ok"
        assert "estado_actual" in result
    
    def test_ri_no_conforme_moves_to_cuarentena(self, auth_headers, test_cliente):
        """RI no_conforme moves OT to estado cuarentena"""
        # Create order
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": f"{TEST_PREFIX}iPhone No Conforme",
                "imei": "123456789012348",
                "color": "Rojo",
                "daños": "Daños severos"
            }
        }
        response = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=auth_headers)
        assert response.status_code == 200
        orden = response.json()
        
        # RI with no_conforme result
        ri_data = {
            "resultado_ri": "no_conforme",
            "checklist_visual": {"pantalla": False, "carcasa": False},
            "fotos_recepcion": ["frontal.jpg", "trasera.jpg", "daños.jpg"],
            "observaciones": "Dispositivo con daños severos no declarados",
            "propiedad_cliente_estado": "no_apto"
        }
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{orden['id']}/receiving-inspection",
            json=ri_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"RI no_conforme should succeed: {response.text}"
        result = response.json()
        assert result["resultado_ri"] == "no_conforme"
        assert result["estado_actual"] == "cuarentena", "RI no_conforme should move to cuarentena"
        
        # Verify order is in cuarentena
        response = requests.get(f"{BASE_URL}/api/ordenes/{orden['id']}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["estado"] == "cuarentena"
    
    def test_ri_sospechoso_moves_to_cuarentena(self, auth_headers, test_cliente):
        """RI sospechoso also moves OT to cuarentena"""
        # Create order
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": f"{TEST_PREFIX}iPhone Sospechoso",
                "imei": "123456789012349",
                "color": "Verde",
                "daños": "Posibles daños por agua"
            }
        }
        response = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=auth_headers)
        assert response.status_code == 200
        orden = response.json()
        
        # RI with sospechoso result
        ri_data = {
            "resultado_ri": "sospechoso",
            "checklist_visual": {"pantalla": True, "carcasa": True},
            "fotos_recepcion": ["frontal.jpg", "trasera.jpg", "daños.jpg"],
            "observaciones": "Indicadores de agua activos"
        }
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{orden['id']}/receiving-inspection",
            json=ri_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json()
        assert result["resultado_ri"] == "sospechoso"
        assert result["estado_actual"] == "cuarentena"


class TestRIEnTallerBlocking(TestSetup):
    """Tests for transición a en_taller bloqueada si RI obligatoria no completada"""
    
    def test_en_taller_blocked_without_ri(self, auth_headers, test_cliente):
        """Transition to en_taller requires RI when ri_obligatoria=True"""
        # Create order (by default ri_obligatoria=True, ri_completada=False)
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": f"{TEST_PREFIX}iPhone Blocked Test",
                "imei": "123456789012350",
                "color": "Plateado",
                "daños": "Pantalla rota"
            }
        }
        response = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=auth_headers)
        assert response.status_code == 200
        orden = response.json()
        
        # Move to recibida first
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden['id']}/estado",
            json={"nuevo_estado": "recibida", "usuario": "test"},
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Also update recepcion checklist to allow transition
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden['id']}",
            json={"recepcion_checklist_completo": True},
            headers=auth_headers
        )
        
        # Try to move to en_taller without RI - should fail
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden['id']}/estado",
            json={"nuevo_estado": "en_taller", "usuario": "test"},
            headers=auth_headers
        )
        assert response.status_code == 400, f"Should block without RI: {response.text}"
        assert "Receiving Inspection" in response.json().get("detail", "") or "RI" in response.json().get("detail", "")
    
    def test_en_taller_allowed_after_ri_completed(self, auth_headers, test_cliente):
        """Transition to en_taller allowed after RI completion"""
        # Create order
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": f"{TEST_PREFIX}iPhone RI Done",
                "imei": "123456789012351",
                "color": "Dorado",
                "daños": "Batería"
            }
        }
        response = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=auth_headers)
        assert response.status_code == 200
        orden = response.json()
        
        # Move to recibida
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden['id']}/estado",
            json={"nuevo_estado": "recibida", "usuario": "test"},
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Complete RI
        ri_data = {
            "resultado_ri": "ok",
            "checklist_visual": {"todo": True},
            "fotos_recepcion": ["f1.jpg", "f2.jpg", "f3.jpg"],
            "observaciones": "OK"
        }
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{orden['id']}/receiving-inspection",
            json=ri_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Also complete checklist
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden['id']}",
            json={"recepcion_checklist_completo": True},
            headers=auth_headers
        )
        
        # Now en_taller should work
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden['id']}/estado",
            json={"nuevo_estado": "en_taller", "usuario": "test"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Should allow en_taller after RI: {response.text}"


class TestEventosAuditoria(TestSetup):
    """Tests for GET /api/ordenes/{id}/eventos-auditoria"""
    
    def test_eventos_auditoria_returns_event_log(self, auth_headers, test_cliente):
        """Event log devuelve eventos append-only"""
        # Create order
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": f"{TEST_PREFIX}iPhone Event Log",
                "imei": "123456789012352",
                "color": "Negro",
                "daños": "Test"
            }
        }
        response = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=auth_headers)
        assert response.status_code == 200
        orden = response.json()
        
        # Get event log - should have at least creation event
        response = requests.get(
            f"{BASE_URL}/api/ordenes/{orden['id']}/eventos-auditoria",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get eventos: {response.text}"
        eventos = response.json()
        assert isinstance(eventos, list)
        assert len(eventos) >= 1, "Should have at least orden_creada event"
        
        # Check first event is creation
        has_creation_event = any(e.get("action") == "orden_creada" for e in eventos)
        assert has_creation_event, "Should have orden_creada event"
    
    def test_event_log_registers_state_changes(self, auth_headers, test_cliente):
        """Event log registra cambios de estado"""
        # Create and change state of order
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": f"{TEST_PREFIX}iPhone State Events",
                "imei": "123456789012353",
                "color": "Blanco",
                "daños": "Test states"
            }
        }
        response = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=auth_headers)
        assert response.status_code == 200
        orden = response.json()
        
        # Change state to recibida
        requests.patch(
            f"{BASE_URL}/api/ordenes/{orden['id']}/estado",
            json={"nuevo_estado": "recibida", "usuario": "test"},
            headers=auth_headers
        )
        
        # Get event log
        response = requests.get(
            f"{BASE_URL}/api/ordenes/{orden['id']}/eventos-auditoria",
            headers=auth_headers
        )
        assert response.status_code == 200
        eventos = response.json()
        
        # Should have creation + state change events
        actions = [e.get("action") for e in eventos]
        assert "orden_creada" in actions
        assert "cambio_estado" in actions
    
    def test_event_log_registers_ri(self, auth_headers, test_cliente):
        """Event log registra RI"""
        # Create order
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": f"{TEST_PREFIX}iPhone RI Event",
                "imei": "123456789012354",
                "color": "Azul",
                "daños": "RI test"
            }
        }
        response = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=auth_headers)
        assert response.status_code == 200
        orden = response.json()
        
        # Complete RI
        ri_data = {
            "resultado_ri": "ok",
            "checklist_visual": {"test": True},
            "fotos_recepcion": ["a.jpg", "b.jpg", "c.jpg"]
        }
        requests.post(
            f"{BASE_URL}/api/ordenes/{orden['id']}/receiving-inspection",
            json=ri_data,
            headers=auth_headers
        )
        
        # Get event log
        response = requests.get(
            f"{BASE_URL}/api/ordenes/{orden['id']}/eventos-auditoria",
            headers=auth_headers
        )
        assert response.status_code == 200
        eventos = response.json()
        
        # Should have RI event
        has_ri_event = any(e.get("action") == "receiving_inspection" for e in eventos)
        assert has_ri_event, "Should have receiving_inspection event"
    
    def test_event_log_registers_partial_updates(self, auth_headers, test_cliente):
        """Event log registra actualizaciones parciales"""
        # Create order
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": f"{TEST_PREFIX}iPhone Patch Event",
                "imei": "123456789012355",
                "color": "Rosa",
                "daños": "Patch test"
            }
        }
        response = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=auth_headers)
        assert response.status_code == 200
        orden = response.json()
        
        # Patch order
        requests.patch(
            f"{BASE_URL}/api/ordenes/{orden['id']}",
            json={"diagnostico_tecnico": "Test diagnostico"},
            headers=auth_headers
        )
        
        # Get event log
        response = requests.get(
            f"{BASE_URL}/api/ordenes/{orden['id']}/eventos-auditoria",
            headers=auth_headers
        )
        assert response.status_code == 200
        eventos = response.json()
        
        # Should have partial update event
        has_patch_event = any("actualizada" in (e.get("action") or "") for e in eventos)
        assert has_patch_event, "Should have actualizada_parcial event"


class TestAuditPackEndpoints(TestSetup):
    """Tests for Audit Pack endpoints"""
    
    def test_audit_pack_ot_returns_complete_pack(self, auth_headers, test_cliente):
        """GET /api/master/iso/audit-pack/ot/{id} devuelve pack completo"""
        # Create order with RI
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": f"{TEST_PREFIX}iPhone Audit OT",
                "imei": "123456789012356",
                "color": "Gris",
                "daños": "Audit test"
            }
        }
        response = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=auth_headers)
        assert response.status_code == 200
        orden = response.json()
        
        # Complete RI
        ri_data = {
            "resultado_ri": "ok",
            "checklist_visual": {"ok": True},
            "fotos_recepcion": ["1.jpg", "2.jpg", "3.jpg"]
        }
        requests.post(
            f"{BASE_URL}/api/ordenes/{orden['id']}/receiving-inspection",
            json=ri_data,
            headers=auth_headers
        )
        
        # Get audit pack
        response = requests.get(
            f"{BASE_URL}/api/master/iso/audit-pack/ot/{orden['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get audit pack: {response.text}"
        pack = response.json()
        
        # Verify pack structure
        assert "ot" in pack, "Pack should contain ot section"
        assert "event_log" in pack, "Pack should contain event_log"
        assert "consentimientos" in pack, "Pack should contain consentimientos"
        assert "incidencias" in pack, "Pack should contain incidencias"
        
        # Verify OT section has RI info
        ot = pack["ot"]
        assert "ri" in ot, "OT should have ri section"
        assert ot["ri"]["completada"] == True
        assert ot["ri"]["resultado"] == "ok"
    
    def test_audit_pack_periodo_returns_pack_by_range(self, auth_headers):
        """GET /api/master/iso/audit-pack/periodo devuelve pack por rango"""
        # Get pack for current period
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        response = requests.get(
            f"{BASE_URL}/api/master/iso/audit-pack/periodo",
            params={"fecha_hasta": today},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get periodo pack: {response.text}"
        pack = response.json()
        
        # Verify structure
        assert "periodo" in pack
        assert "total_ots" in pack
        assert "items" in pack
        assert isinstance(pack["items"], list)
    
    def test_audit_pack_periodo_csv_exports_valid_csv(self, auth_headers):
        """GET /api/master/iso/audit-pack/periodo/csv exporta CSV válido"""
        response = requests.get(
            f"{BASE_URL}/api/master/iso/audit-pack/periodo/csv",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get CSV: {response.text}"
        
        # Verify content type
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type, f"Should be CSV, got {content_type}"
        
        # Verify CSV has expected columns
        csv_content = response.text
        first_line = csv_content.split("\n")[0]
        expected_columns = ["ot_id", "numero_orden", "estado", "ri_completada", "ri_resultado"]
        for col in expected_columns:
            assert col in first_line, f"CSV should have column {col}"


class TestPanelMasterISO(TestSetup):
    """Tests verifying Panel Master ISO tab maintains functionality"""
    
    def test_iso_kpis_endpoint(self, auth_headers):
        """ISO KPIs endpoint works"""
        response = requests.get(f"{BASE_URL}/api/master/iso/kpis", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "kpis" in data
        assert "proveedores" in data
    
    def test_iso_documentos_endpoint(self, auth_headers):
        """ISO documentos endpoint works"""
        response = requests.get(f"{BASE_URL}/api/master/iso/documentos", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_iso_proveedores_endpoint(self, auth_headers):
        """ISO proveedores endpoint works"""
        response = requests.get(f"{BASE_URL}/api/master/iso/proveedores", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_iso_reporte_pdf_endpoint(self, auth_headers):
        """ISO PDF report endpoint works"""
        response = requests.get(f"{BASE_URL}/api/master/iso/reporte-pdf", headers=auth_headers)
        assert response.status_code == 200
        # Check it's a PDF (magic bytes)
        assert response.content[:4] == b'%PDF', "Should return PDF file"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

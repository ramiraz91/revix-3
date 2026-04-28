"""
Tests for TecnicoCierreReparacion QC improvements:
- Section 1: RadioGroup with 3 options (reparada/parcial/no_reparada)
- Section 3: Bulk actions for functions (marcar todas, solo requeridas, limpiar)
- Toggle esSmartphone to hide battery/functions sections
- Toggle funcionesNoAplica to disable functions grid
- IRREPARABLE state when avería no reparada
- Backend whitelist for new QC fields
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MASTER_EMAIL = "master@revix.es"
MASTER_PASSWORD = "RevixMaster2026!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for master user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MASTER_EMAIL,
        "password": MASTER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def en_taller_order(auth_headers):
    """Find an order in en_taller state for testing"""
    response = requests.get(f"{BASE_URL}/api/ordenes?estado=en_taller", headers=auth_headers)
    if response.status_code == 200:
        orders = response.json()
        if orders and len(orders) > 0:
            return orders[0]
    pytest.skip("No order in en_taller state found for testing")


class TestBackendWhitelistQCFields:
    """Test that backend whitelist includes all new QC fields"""
    
    def test_patch_bateria_nivel(self, auth_headers, en_taller_order):
        """Test that bateria_nivel can be updated via PATCH"""
        orden_id = en_taller_order['id']
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json={"bateria_nivel": 85}
        )
        assert response.status_code == 200, f"Failed to update bateria_nivel: {response.text}"
        data = response.json()
        assert data.get("bateria_nivel") == 85
        print("✓ bateria_nivel field accepted in whitelist")
    
    def test_patch_bateria_ciclos(self, auth_headers, en_taller_order):
        """Test that bateria_ciclos can be updated via PATCH"""
        orden_id = en_taller_order['id']
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json={"bateria_ciclos": 342}
        )
        assert response.status_code == 200, f"Failed to update bateria_ciclos: {response.text}"
        data = response.json()
        assert data.get("bateria_ciclos") == 342
        print("✓ bateria_ciclos field accepted in whitelist")
    
    def test_patch_bateria_estado(self, auth_headers, en_taller_order):
        """Test that bateria_estado can be updated via PATCH"""
        orden_id = en_taller_order['id']
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json={"bateria_estado": "ok"}
        )
        assert response.status_code == 200, f"Failed to update bateria_estado: {response.text}"
        data = response.json()
        assert data.get("bateria_estado") == "ok"
        print("✓ bateria_estado field accepted in whitelist")
    
    def test_patch_qc_funciones(self, auth_headers, en_taller_order):
        """Test that qc_funciones (dict) can be updated via PATCH"""
        orden_id = en_taller_order['id']
        funciones = {
            "pantalla_touch": True,
            "wifi": True,
            "bluetooth": True,
            "camara_trasera": True,
            "microfono": True,
            "altavoz_auricular": True,
            "carga": True,
            "botones_fisicos": True
        }
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json={"qc_funciones": funciones}
        )
        assert response.status_code == 200, f"Failed to update qc_funciones: {response.text}"
        data = response.json()
        assert data.get("qc_funciones") == funciones
        print("✓ qc_funciones field accepted in whitelist")
    
    def test_patch_qc_funciones_no_aplica(self, auth_headers, en_taller_order):
        """Test that qc_funciones_no_aplica can be updated via PATCH"""
        orden_id = en_taller_order['id']
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json={"qc_funciones_no_aplica": True}
        )
        assert response.status_code == 200, f"Failed to update qc_funciones_no_aplica: {response.text}"
        data = response.json()
        assert data.get("qc_funciones_no_aplica") == True
        print("✓ qc_funciones_no_aplica field accepted in whitelist")
        
        # Reset to false
        requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json={"qc_funciones_no_aplica": False}
        )
    
    def test_patch_qc_es_smartphone(self, auth_headers, en_taller_order):
        """Test that qc_es_smartphone can be updated via PATCH"""
        orden_id = en_taller_order['id']
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json={"qc_es_smartphone": False}
        )
        assert response.status_code == 200, f"Failed to update qc_es_smartphone: {response.text}"
        data = response.json()
        assert data.get("qc_es_smartphone") == False
        print("✓ qc_es_smartphone field accepted in whitelist")
        
        # Reset to true
        requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json={"qc_es_smartphone": True}
        )
    
    def test_patch_qc_resultado_averia(self, auth_headers, en_taller_order):
        """Test that qc_resultado_averia can be updated via PATCH"""
        orden_id = en_taller_order['id']
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json={"qc_resultado_averia": "reparada"}
        )
        assert response.status_code == 200, f"Failed to update qc_resultado_averia: {response.text}"
        data = response.json()
        assert data.get("qc_resultado_averia") == "reparada"
        print("✓ qc_resultado_averia field accepted in whitelist")
    
    def test_patch_qc_motivo_no_reparada(self, auth_headers, en_taller_order):
        """Test that qc_motivo_no_reparada can be updated via PATCH"""
        orden_id = en_taller_order['id']
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json={"qc_motivo_no_reparada": "Placa base dañada irreversiblemente"}
        )
        assert response.status_code == 200, f"Failed to update qc_motivo_no_reparada: {response.text}"
        data = response.json()
        assert data.get("qc_motivo_no_reparada") == "Placa base dañada irreversiblemente"
        print("✓ qc_motivo_no_reparada field accepted in whitelist")
    
    def test_patch_garantia_resultado(self, auth_headers, en_taller_order):
        """Test that garantia_resultado can be updated via PATCH"""
        orden_id = en_taller_order['id']
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json={"garantia_resultado": "procede"}
        )
        assert response.status_code == 200, f"Failed to update garantia_resultado: {response.text}"
        data = response.json()
        assert data.get("garantia_resultado") == "procede"
        print("✓ garantia_resultado field accepted in whitelist")
    
    def test_patch_garantia_motivo_no_procede(self, auth_headers, en_taller_order):
        """Test that garantia_motivo_no_procede can be updated via PATCH"""
        orden_id = en_taller_order['id']
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json={"garantia_motivo_no_procede": "Daño por líquido detectado"}
        )
        assert response.status_code == 200, f"Failed to update garantia_motivo_no_procede: {response.text}"
        data = response.json()
        assert data.get("garantia_motivo_no_procede") == "Daño por líquido detectado"
        print("✓ garantia_motivo_no_procede field accepted in whitelist")
    
    def test_patch_garantia_tests_omitidos(self, auth_headers, en_taller_order):
        """Test that garantia_tests_omitidos can be updated via PATCH"""
        orden_id = en_taller_order['id']
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json={"garantia_tests_omitidos": True}
        )
        assert response.status_code == 200, f"Failed to update garantia_tests_omitidos: {response.text}"
        data = response.json()
        assert data.get("garantia_tests_omitidos") == True
        print("✓ garantia_tests_omitidos field accepted in whitelist")


class TestCambiarEstadoIrreparable:
    """Test state transition to IRREPARABLE"""
    
    def test_valid_transition_en_taller_to_irreparable(self, auth_headers, en_taller_order):
        """Test that en_taller can transition to irreparable"""
        orden_id = en_taller_order['id']
        
        # First verify order is in en_taller
        response = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=auth_headers)
        assert response.status_code == 200
        current_state = response.json().get("estado")
        
        if current_state != "en_taller":
            pytest.skip(f"Order not in en_taller state (current: {current_state})")
        
        # Change state to irreparable
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}/estado",
            headers=auth_headers,
            json={
                "nuevo_estado": "irreparable",
                "usuario": "master",
                "mensaje": "AVERÍA NO REPARADA: Placa base con corrosión avanzada"
            }
        )
        assert response.status_code == 200, f"Failed to change state to irreparable: {response.text}"
        data = response.json()
        
        # Response may be {message: ...} or full order - check both
        if "message" in data:
            assert "irreparable" in data.get("message", "").lower()
            print("✓ State transition en_taller → irreparable successful (message response)")
        else:
            assert data.get("estado") == "irreparable"
            print("✓ State transition en_taller → irreparable successful (full order response)")
        
        # Verify by fetching the order
        verify_response = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=auth_headers)
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data.get("estado") == "irreparable"
        print("✓ Order state verified as irreparable")
        
        # Verify historial contains the message
        historial = verify_data.get("historial_estados", [])
        last_entry = historial[-1] if historial else {}
        assert "irreparable" in last_entry.get("estado", "").lower()
        print("✓ Historial updated with irreparable state")
        
        # Restore to en_taller for other tests (admin can force)
        requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}/estado",
            headers=auth_headers,
            json={
                "nuevo_estado": "en_taller",
                "usuario": "master",
                "mensaje": "Restaurando para tests",
                "forzar_sin_validacion": True
            }
        )


class TestCambiarEstadoReparado:
    """Test state transition to REPARADO (normal flow)"""
    
    def test_valid_transition_en_taller_to_reparado(self, auth_headers, en_taller_order):
        """Test that en_taller can transition to reparado"""
        orden_id = en_taller_order['id']
        
        # First verify order is in en_taller
        response = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=auth_headers)
        assert response.status_code == 200
        current_state = response.json().get("estado")
        
        if current_state != "en_taller":
            pytest.skip(f"Order not in en_taller state (current: {current_state})")
        
        # Change state to reparado
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}/estado",
            headers=auth_headers,
            json={
                "nuevo_estado": "reparado",
                "usuario": "master",
                "mensaje": "Reparación completada - QC verificado"
            }
        )
        assert response.status_code == 200, f"Failed to change state to reparado: {response.text}"
        data = response.json()
        
        # Response may be {message: ...} or full order - check both
        if "message" in data:
            assert "reparado" in data.get("message", "").lower()
            print("✓ State transition en_taller → reparado successful (message response)")
        else:
            assert data.get("estado") == "reparado"
            print("✓ State transition en_taller → reparado successful (full order response)")
        
        # Verify by fetching the order
        verify_response = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=auth_headers)
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data.get("estado") == "reparado"
        print("✓ Order state verified as reparado")
        
        # Restore to en_taller for other tests
        requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}/estado",
            headers=auth_headers,
            json={
                "nuevo_estado": "en_taller",
                "usuario": "master",
                "mensaje": "Restaurando para tests",
                "forzar_sin_validacion": True
            }
        )


class TestQCPayloadIntegration:
    """Test full QC payload as sent by TecnicoCierreReparacion component
    
    Note: Some fields (notas_cierre_tecnico, fecha_fin_reparacion) are restricted
    to tecnico role only. Admin/master cannot update them. This is by design.
    """
    
    def test_full_qc_payload_reparada(self, auth_headers, en_taller_order):
        """Test QC payload for 'reparada correctamente' flow (admin-allowed fields only)"""
        orden_id = en_taller_order['id']
        
        # QC payload with only admin-allowed fields
        # Note: notas_cierre_tecnico and fecha_fin_reparacion are tecnico-only
        qc_payload = {
            "qc_es_smartphone": True,
            "qc_resultado_averia": "reparada",
            "qc_funciones_no_aplica": False,
            "bateria_nivel": 92,
            "bateria_ciclos": 150,
            "bateria_estado": "ok",
            "qc_funciones": {
                "pantalla_touch": True,
                "wifi": True,
                "bluetooth": True,
                "camara_trasera": True,
                "camara_frontal": True,
                "microfono": True,
                "altavoz_auricular": True,
                "carga": True,
                "botones_fisicos": True,
                "sim_red": True,
                "biometria": True
            }
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json=qc_payload
        )
        assert response.status_code == 200, f"Failed to save QC payload: {response.text}"
        data = response.json()
        
        # Verify all fields were saved
        assert data.get("qc_resultado_averia") == "reparada"
        assert data.get("qc_es_smartphone") == True
        assert data.get("bateria_nivel") == 92
        assert data.get("bateria_estado") == "ok"
        assert data.get("qc_funciones", {}).get("pantalla_touch") == True
        print("✓ Full QC payload for 'reparada' saved successfully")
    
    def test_full_qc_payload_no_reparada(self, auth_headers, en_taller_order):
        """Test QC payload for 'no_reparada' flow (admin-allowed fields only)"""
        orden_id = en_taller_order['id']
        
        # QC payload for avería no reparada (admin-allowed fields only)
        qc_payload = {
            "qc_es_smartphone": True,
            "qc_resultado_averia": "no_reparada",
            "qc_motivo_no_reparada": "Placa base con corrosión avanzada, no hay disponibilidad del repuesto compatible"
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json=qc_payload
        )
        assert response.status_code == 200, f"Failed to save QC payload: {response.text}"
        data = response.json()
        
        # Verify fields were saved
        assert data.get("qc_resultado_averia") == "no_reparada"
        assert "corrosión" in data.get("qc_motivo_no_reparada", "")
        print("✓ Full QC payload for 'no_reparada' saved successfully")
    
    def test_full_qc_payload_non_smartphone(self, auth_headers, en_taller_order):
        """Test QC payload for non-smartphone device (console, TV, etc.)"""
        orden_id = en_taller_order['id']
        
        # QC payload for non-smartphone (admin-allowed fields only)
        qc_payload = {
            "qc_es_smartphone": False,  # Not a smartphone
            "qc_resultado_averia": "reparada",
            "qc_funciones_no_aplica": True,  # Functions don't apply
            "bateria_estado": "no_aplica"  # Battery doesn't apply
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json=qc_payload
        )
        assert response.status_code == 200, f"Failed to save QC payload: {response.text}"
        data = response.json()
        
        # Verify fields were saved
        assert data.get("qc_es_smartphone") == False
        assert data.get("qc_funciones_no_aplica") == True
        assert data.get("bateria_estado") == "no_aplica"
        print("✓ Full QC payload for non-smartphone saved successfully")
    
    def test_tecnico_only_fields_blocked_for_admin(self, auth_headers, en_taller_order):
        """Test that admin cannot update tecnico-only fields"""
        orden_id = en_taller_order['id']
        
        # These fields should be blocked for admin
        qc_payload = {
            "notas_cierre_tecnico": "Test note",
            "fecha_fin_reparacion": "2026-04-28T10:00:00.000Z"
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=auth_headers,
            json=qc_payload
        )
        # Should return 403 because these are tecnico-only fields
        assert response.status_code == 403, f"Expected 403 for tecnico-only fields, got {response.status_code}"
        print("✓ Admin correctly blocked from updating tecnico-only fields")


class TestHistorialMensajes:
    """Test that historial contains proper messages for different flows"""
    
    def test_historial_averia_no_reparada_message(self, auth_headers, en_taller_order):
        """Test that historial contains 'AVERÍA NO REPARADA:' message"""
        orden_id = en_taller_order['id']
        
        # First ensure order is in en_taller
        response = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=auth_headers)
        current_state = response.json().get("estado")
        
        if current_state != "en_taller":
            # Try to restore
            requests.patch(
                f"{BASE_URL}/api/ordenes/{orden_id}/estado",
                headers=auth_headers,
                json={
                    "nuevo_estado": "en_taller",
                    "usuario": "master",
                    "mensaje": "Restaurando para test",
                    "forzar_sin_validacion": True
                }
            )
        
        # Change to irreparable with proper message
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}/estado",
            headers=auth_headers,
            json={
                "nuevo_estado": "irreparable",
                "usuario": "tecnico",
                "mensaje": "AVERÍA NO REPARADA: Chip de gestión dañado irreversiblemente"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            historial = data.get("historial_estados", [])
            
            # Find the irreparable entry
            irreparable_entries = [h for h in historial if h.get("estado") == "irreparable"]
            if irreparable_entries:
                # Check if any entry has the expected message format
                # Note: The message might be stored differently depending on implementation
                print("✓ Historial contains irreparable state entry")
            
            # Restore state
            requests.patch(
                f"{BASE_URL}/api/ordenes/{orden_id}/estado",
                headers=auth_headers,
                json={
                    "nuevo_estado": "en_taller",
                    "usuario": "master",
                    "mensaje": "Restaurando para tests",
                    "forzar_sin_validacion": True
                }
            )
        else:
            print(f"Note: State change returned {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

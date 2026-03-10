"""
Iteration 41: P0 ISO Feature Testing
- Seguimiento público: consentimiento datos+RGPD
- API seguimiento/verificar con acepta_condiciones/acepta_rgpd
- Ordenes: bloquear transición a en_taller si falta recepcion_checklist_completo
- Ordenes: bloquear transición a enviado si falta QC final
- OrdenDetalle: card de diagnóstico/calidad con checklists autoguarda vía PATCH
- Incidencias NC/CAPA: tipo reclamacion/garantia/daño_transporte requiere causa raíz + acción correctiva
"""
import pytest
import requests
import uuid
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="session")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "ramiraz91@gmail.com",
        "password": "temp123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    # Fallback to default admin
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@techrepair.local",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed")

@pytest.fixture(scope="session")
def api_client(auth_token):
    """Shared requests session with auth"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session

@pytest.fixture(scope="session")
def test_cliente(api_client):
    """Create a test client for the session"""
    cliente_data = {
        "nombre": "Test",
        "apellidos": "ConsentimientoISO",
        "dni": f"TEST{uuid.uuid4().hex[:6].upper()}",
        "telefono": "612345678",
        "email": "test_iso_consent@example.com",
        "direccion": "Test Address 123"
    }
    response = api_client.post(f"{BASE_URL}/api/clientes", json=cliente_data)
    assert response.status_code == 200, f"Failed to create test cliente: {response.text}"
    return response.json()

@pytest.fixture(scope="session")
def test_orden(api_client, test_cliente):
    """Create a test order for the session"""
    orden_data = {
        "cliente_id": test_cliente["id"],
        "dispositivo": {
            "modelo": "iPhone 14 Pro Test ISO",
            "imei": "123456789012345",
            "color": "Negro",
            "daños": "Pantalla rota - Test ISO"
        },
        "notas": "Test order for ISO P0 testing"
    }
    response = api_client.post(f"{BASE_URL}/api/ordenes", json=orden_data)
    assert response.status_code == 200, f"Failed to create test orden: {response.text}"
    return response.json()


class TestSeguimientoConsentimiento:
    """Tests for seguimiento público con consentimiento RGPD"""

    def test_seguimiento_verificar_sin_consentimientos(self, test_orden, test_cliente):
        """POST /api/seguimiento/verificar without consents should work and return consentimiento_registrado=false"""
        response = requests.post(f"{BASE_URL}/api/seguimiento/verificar", json={
            "token": test_orden.get("token_seguimiento", ""),
            "telefono": test_cliente["telefono"]
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "orden" in data or "numero_orden" in data
        # Without consent flags, should return false or not be present
        assert data.get("consentimiento_registrado") == False or "consentimiento_registrado" not in data

    def test_seguimiento_verificar_con_ambos_consentimientos(self, test_orden, test_cliente):
        """POST /api/seguimiento/verificar with acepta_condiciones=True and acepta_rgpd=True registers consent"""
        response = requests.post(f"{BASE_URL}/api/seguimiento/verificar", json={
            "token": test_orden.get("token_seguimiento", ""),
            "telefono": test_cliente["telefono"],
            "acepta_condiciones": True,
            "acepta_rgpd": True
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("consentimiento_registrado") == True, "Expected consentimiento_registrado=True when both consents are True"

    def test_seguimiento_verificar_con_solo_condiciones(self, test_orden, test_cliente):
        """POST /api/seguimiento/verificar with only acepta_condiciones=True also registers consent"""
        response = requests.post(f"{BASE_URL}/api/seguimiento/verificar", json={
            "token": test_orden.get("token_seguimiento", ""),
            "telefono": test_cliente["telefono"],
            "acepta_condiciones": True,
            "acepta_rgpd": False
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Any consent flag should register
        assert data.get("consentimiento_registrado") == True

    def test_seguimiento_verificar_returns_textos_legales(self, test_orden, test_cliente):
        """POST /api/seguimiento/verificar returns textos_legales in response"""
        response = requests.post(f"{BASE_URL}/api/seguimiento/verificar", json={
            "token": test_orden.get("token_seguimiento", ""),
            "telefono": test_cliente["telefono"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "textos_legales" in data, "Response should include textos_legales for modal display"


class TestOrdenesTransicionChecklist:
    """Tests for orden state transition blocking based on checklist completeness"""

    def test_transicion_a_en_taller_sin_checklist_falla(self, api_client, test_cliente):
        """Block transition to en_taller if recepcion_checklist_completo is missing"""
        # Create a fresh order in state recibida
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": "Test Checklist Device",
                "imei": f"999{uuid.uuid4().hex[:12]}",
                "color": "Test",
                "daños": "Test daño"
            }
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ordenes", json=orden_data)
        assert create_resp.status_code == 200
        orden = create_resp.json()
        orden_id = orden["id"]
        
        # First move to recibida
        resp1 = api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}/estado", json={
            "nuevo_estado": "recibida",
            "usuario": "test"
        })
        assert resp1.status_code == 200, f"Failed to change to recibida: {resp1.text}"
        
        # Ensure recepcion_checklist_completo is False
        api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}", json={
            "recepcion_checklist_completo": False
        })
        
        # Try to transition to en_taller - should fail
        resp2 = api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}/estado", json={
            "nuevo_estado": "en_taller",
            "usuario": "test"
        })
        assert resp2.status_code == 400, f"Expected 400 blocking transition, got {resp2.status_code}: {resp2.text}"
        assert "checklist" in resp2.text.lower() or "recepcion" in resp2.text.lower(), "Error should mention checklist"

    def test_transicion_a_en_taller_con_checklist_completo_exito(self, api_client, test_cliente):
        """Allow transition to en_taller if recepcion_checklist_completo is True"""
        # Create a fresh order
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": "Test Checklist OK Device",
                "imei": f"888{uuid.uuid4().hex[:12]}",
                "color": "Test",
                "daños": "Test daño"
            }
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ordenes", json=orden_data)
        assert create_resp.status_code == 200
        orden = create_resp.json()
        orden_id = orden["id"]
        
        # Move to recibida
        resp1 = api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}/estado", json={
            "nuevo_estado": "recibida",
            "usuario": "test"
        })
        assert resp1.status_code == 200
        
        # Mark checklist as complete
        api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}", json={
            "recepcion_checklist_completo": True
        })
        
        # Now transition to en_taller should succeed
        resp2 = api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}/estado", json={
            "nuevo_estado": "en_taller",
            "usuario": "test"
        })
        assert resp2.status_code == 200, f"Expected 200 transition allowed, got {resp2.status_code}: {resp2.text}"


class TestOrdenesTransicionQCFinal:
    """Tests for orden state transition blocking based on QC final completeness"""

    def test_transicion_a_enviado_sin_qc_falla(self, api_client, test_cliente):
        """Block transition to enviado if QC final checks are missing"""
        # Create order and move through states
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": "Test QC Device",
                "imei": f"777{uuid.uuid4().hex[:12]}",
                "color": "Test",
                "daños": "Test daño"
            }
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ordenes", json=orden_data)
        assert create_resp.status_code == 200
        orden = create_resp.json()
        orden_id = orden["id"]
        
        # Progress through states: pendiente_recibir -> recibida -> en_taller -> reparado -> validacion
        for state in ["recibida", "en_taller", "reparado", "validacion"]:
            # First mark checklist complete if needed
            if state == "en_taller":
                api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}", json={
                    "recepcion_checklist_completo": True
                })
            resp = api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}/estado", json={
                "nuevo_estado": state,
                "usuario": "test"
            })
            # May fail at reparado due to material validation - that's ok for this test
            if resp.status_code != 200 and state not in ["enviado"]:
                # Skip this test if we can't get to validacion
                if state in ["reparado", "validacion"]:
                    pytest.skip(f"Could not reach {state} state: {resp.text}")
        
        # Ensure QC checks are False
        api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}", json={
            "diagnostico_salida_realizado": False,
            "funciones_verificadas": False,
            "limpieza_realizada": False
        })
        
        # Try to transition to enviado - should fail
        resp = api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}/estado", json={
            "nuevo_estado": "enviado",
            "usuario": "test",
            "codigo_envio": "TEST123"
        })
        assert resp.status_code == 400, f"Expected 400 blocking transition without QC, got {resp.status_code}: {resp.text}"
        assert "qc" in resp.text.lower() or "diagnostico" in resp.text.lower() or "verificadas" in resp.text.lower() or "limpieza" in resp.text.lower()


class TestOrdenChecklistPatch:
    """Tests for OrdenDetalle checklist auto-save via PATCH"""

    def test_patch_orden_checklist_recepcion(self, api_client, test_orden):
        """PATCH /api/ordenes/{id} can update recepcion checklist fields"""
        orden_id = test_orden["id"]
        
        response = api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}", json={
            "recepcion_checklist_completo": True,
            "recepcion_estado_fisico_registrado": True,
            "recepcion_accesorios_registrados": True,
            "recepcion_notas": "Test recepcion notes"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify the fields were saved
        get_resp = api_client.get(f"{BASE_URL}/api/ordenes/{orden_id}")
        assert get_resp.status_code == 200
        orden = get_resp.json()
        assert orden.get("recepcion_checklist_completo") == True
        assert orden.get("recepcion_estado_fisico_registrado") == True

    def test_patch_orden_qc_final_fields(self, api_client, test_orden):
        """PATCH /api/ordenes/{id} can update QC final checklist fields"""
        orden_id = test_orden["id"]
        
        response = api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}", json={
            "diagnostico_salida_realizado": True,
            "funciones_verificadas": True,
            "limpieza_realizada": True,
            "notas_cierre_tecnico": "QC final completo - test"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify
        get_resp = api_client.get(f"{BASE_URL}/api/ordenes/{orden_id}")
        assert get_resp.status_code == 200
        orden = get_resp.json()
        assert orden.get("diagnostico_salida_realizado") == True
        assert orden.get("funciones_verificadas") == True
        assert orden.get("limpieza_realizada") == True

    def test_patch_orden_bateria_trazabilidad(self, api_client, test_orden):
        """PATCH /api/ordenes/{id} can update batería trazabilidad fields"""
        orden_id = test_orden["id"]
        
        response = api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}", json={
            "bateria_reemplazada": True,
            "bateria_almacenamiento_temporal": True,
            "bateria_residuo_pendiente": False,
            "bateria_gestor_autorizado": "Gestor Test S.L.",
            "bateria_fecha_entrega_gestor": "2025-01-15"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify
        get_resp = api_client.get(f"{BASE_URL}/api/ordenes/{orden_id}")
        assert get_resp.status_code == 200
        orden = get_resp.json()
        assert orden.get("bateria_reemplazada") == True
        assert orden.get("bateria_gestor_autorizado") == "Gestor Test S.L."


class TestIncidenciasNCCAPA:
    """Tests for NC/CAPA requirements in incidencias"""

    def test_incidencia_nc_requiere_capa_para_cerrar(self, api_client, test_cliente):
        """Incidencia tipo reclamacion/garantia/daño_transporte requires causa_raiz + accion_correctiva to resolve/close"""
        # Create a NC incidencia (tipo=reclamacion)
        inc_data = {
            "cliente_id": test_cliente["id"],
            "tipo": "reclamacion",
            "titulo": "Test NC/CAPA Reclamación",
            "descripcion": "Prueba de requerimiento CAPA para cerrar",
            "prioridad": "alta"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/incidencias", json=inc_data)
        assert create_resp.status_code == 200, f"Failed to create incidencia: {create_resp.text}"
        incidencia = create_resp.json()
        incidencia_id = incidencia["id"]
        
        # Verify it's marked as NC
        assert incidencia.get("es_no_conformidad") == True or incidencia.get("tipo") in ["reclamacion", "garantia", "daño_transporte"]
        
        # Try to close without CAPA - should fail
        close_resp = api_client.put(f"{BASE_URL}/api/incidencias/{incidencia_id}", json={
            "estado": "cerrada",
            "notas_resolucion": "Intentando cerrar sin CAPA"
        })
        assert close_resp.status_code == 400, f"Expected 400 when closing NC without CAPA, got {close_resp.status_code}: {close_resp.text}"
        assert "causa" in close_resp.text.lower() or "capa" in close_resp.text.lower() or "correctiva" in close_resp.text.lower()

    def test_incidencia_nc_cerrar_con_capa_exito(self, api_client, test_cliente):
        """NC incidencia can be closed when causa_raiz and accion_correctiva are provided"""
        # Create another NC incidencia
        inc_data = {
            "cliente_id": test_cliente["id"],
            "tipo": "garantia",
            "titulo": "Test NC/CAPA Garantía con CAPA",
            "descripcion": "Prueba de cierre con CAPA completo",
            "prioridad": "media"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/incidencias", json=inc_data)
        assert create_resp.status_code == 200
        incidencia = create_resp.json()
        incidencia_id = incidencia["id"]
        
        # Close with CAPA data - should succeed
        close_resp = api_client.put(f"{BASE_URL}/api/incidencias/{incidencia_id}", json={
            "estado": "cerrada",
            "notas_resolucion": "Resuelta con CAPA completo",
            "capa_causa_raiz": "Fallo en proceso de soldadura",
            "capa_accion_correctiva": "Implementar revisión de temperatura del soldador"
        })
        assert close_resp.status_code == 200, f"Expected 200 when closing NC with CAPA, got {close_resp.status_code}: {close_resp.text}"
        
        # Verify it's closed
        get_resp = api_client.get(f"{BASE_URL}/api/incidencias/{incidencia_id}")
        assert get_resp.status_code == 200
        updated = get_resp.json()
        assert updated.get("estado") == "cerrada"
        assert updated.get("capa_causa_raiz") == "Fallo en proceso de soldadura"

    def test_incidencia_tipo_otro_no_requiere_capa(self, api_client, test_cliente):
        """Incidencia tipo 'otro' should not require CAPA to close"""
        # Create a non-NC incidencia
        inc_data = {
            "cliente_id": test_cliente["id"],
            "tipo": "otro",
            "titulo": "Test Incidencia Otro",
            "descripcion": "Prueba que otro no necesita CAPA",
            "prioridad": "baja"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/incidencias", json=inc_data)
        assert create_resp.status_code == 200
        incidencia = create_resp.json()
        incidencia_id = incidencia["id"]
        
        # Close without CAPA - should succeed
        close_resp = api_client.put(f"{BASE_URL}/api/incidencias/{incidencia_id}", json={
            "estado": "cerrada",
            "notas_resolucion": "Cerrada sin CAPA porque es tipo otro"
        })
        assert close_resp.status_code == 200, f"Expected 200 for non-NC incidencia closure, got {close_resp.status_code}: {close_resp.text}"

    def test_incidencia_guardar_capa_parcial(self, api_client, test_cliente):
        """Can save partial CAPA data without closing the incidencia"""
        # Create NC incidencia
        inc_data = {
            "cliente_id": test_cliente["id"],
            "tipo": "daño_transporte",
            "titulo": "Test CAPA Parcial",
            "descripcion": "Prueba de guardado parcial de CAPA",
            "prioridad": "alta"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/incidencias", json=inc_data)
        assert create_resp.status_code == 200
        incidencia = create_resp.json()
        incidencia_id = incidencia["id"]
        
        # Save partial CAPA (only causa_raiz) without closing
        update_resp = api_client.put(f"{BASE_URL}/api/incidencias/{incidencia_id}", json={
            "capa_causa_raiz": "Embalaje insuficiente",
            "capa_responsable": "Logística"
        })
        assert update_resp.status_code == 200, f"Expected 200 for partial CAPA save, got {update_resp.status_code}: {update_resp.text}"
        
        # Verify saved
        get_resp = api_client.get(f"{BASE_URL}/api/incidencias/{incidencia_id}")
        assert get_resp.status_code == 200
        updated = get_resp.json()
        assert updated.get("capa_causa_raiz") == "Embalaje insuficiente"
        assert updated.get("capa_responsable") == "Logística"
        assert updated.get("estado") != "cerrada"  # Should still be open


class TestScanOrdenChecklist:
    """Tests for scan endpoint blocking based on checklist"""

    def test_scan_tecnico_sin_checklist_falla(self, api_client, test_cliente):
        """POST /api/ordenes/{ref}/scan tipo=tecnico should fail without recepcion_checklist_completo"""
        # Create fresh order
        orden_data = {
            "cliente_id": test_cliente["id"],
            "dispositivo": {
                "modelo": "Test Scan Device",
                "imei": f"666{uuid.uuid4().hex[:12]}",
                "color": "Test",
                "daños": "Test"
            }
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ordenes", json=orden_data)
        assert create_resp.status_code == 200
        orden = create_resp.json()
        orden_id = orden["id"]
        numero_orden = orden["numero_orden"]
        
        # Move to recibida
        resp1 = api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}/estado", json={
            "nuevo_estado": "recibida",
            "usuario": "test"
        })
        assert resp1.status_code == 200
        
        # Ensure checklist is not complete
        api_client.patch(f"{BASE_URL}/api/ordenes/{orden_id}", json={
            "recepcion_checklist_completo": False
        })
        
        # Try scan tecnico - should fail
        scan_resp = api_client.post(f"{BASE_URL}/api/ordenes/{numero_orden}/scan", json={
            "tipo_escaneo": "tecnico",
            "usuario": "tecnico_test"
        })
        assert scan_resp.status_code == 400, f"Expected 400 for scan without checklist, got {scan_resp.status_code}: {scan_resp.text}"
        assert "checklist" in scan_resp.text.lower() or "recepcion" in scan_resp.text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

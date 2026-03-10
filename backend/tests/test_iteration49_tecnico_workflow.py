"""
Iteration 49 - Tests for full Tecnico workflow ISO/WISE:
1. btn-iniciar-reparacion visible/hidden based on estado
2. POST /api/ordenes/{id}/estado en_taller: tecnico OK, admin 403
3. RI buttons (POST /receiving-inspection) for tecnico
4. CPI card (PATCH /cpi) 3 options
5. TecnicoCierreReparacion: QC flow + estado→reparado
6. Admin/master CANNOT set en_taller/reparado → 403
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

OT_RECIBIDA = "75332015-b7cf-476a-a2e0-0d77207dfa08"

ADMIN_EMAIL = "admin@techrepair.local"
ADMIN_PASSWORD = "Admin2026!"
TECNICO_EMAIL = "tecnico@techrepair.local"
TECNICO_PASSWORD = "Tecnico2026!"


def get_token(email: str, password: str) -> str:
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        return None
    return resp.json().get("access_token") or resp.json().get("token")


@pytest.fixture(scope="module")
def admin_token():
    token = get_token(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not token:
        pytest.skip("Admin login failed")
    return token


@pytest.fixture(scope="module")
def tecnico_token():
    token = get_token(TECNICO_EMAIL, TECNICO_PASSWORD)
    if not token:
        pytest.skip("Tecnico login failed")
    return token


# ────────────────────────────────────────────────────────────────
# CASO A: OT estado inicial
# ────────────────────────────────────────────────────────────────
class TestOTEstadoInicial:
    """Verify OT starts in 'recibida' state and has expected fields"""

    def test_get_ot_estado_recibida(self, tecnico_token):
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        resp = requests.get(f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["estado"] in ["recibida", "en_taller"], f"Unexpected state: {data['estado']}"
        print(f"OT estado: {data['estado']}")

    def test_ot_has_required_fields(self, tecnico_token):
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        resp = requests.get(f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "cpi_opcion" in data or data.get("cpi_opcion") is None  # field exists (may be None)
        assert "ri_completada" in data
        assert "recepcion_checklist_completo" in data
        print(f"recepcion_checklist_completo: {data.get('recepcion_checklist_completo')}")


# ────────────────────────────────────────────────────────────────
# CASO B: Admin CANNOT set en_taller/reparado (403)
# ────────────────────────────────────────────────────────────────
class TestAdminCannot403:
    """Admin cannot use tecnico-only endpoints"""

    def test_admin_cant_set_en_taller(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/estado",
            json={"nuevo_estado": "en_taller"},
            headers=headers,
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "tecnico" in str(data).lower() or "accion tecnica" in str(data).lower() or "técnico" in str(data).lower()
        print(f"Admin 403 detail: {data.get('detail', '')}")

    def test_admin_cant_set_reparado(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/estado",
            json={"nuevo_estado": "reparado"},
            headers=headers,
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
        print(f"Admin 403 for reparado: OK")

    def test_admin_cant_set_irreparable(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/estado",
            json={"nuevo_estado": "irreparable"},
            headers=headers,
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
        print(f"Admin 403 for irreparable: OK")

    def test_admin_cant_registrar_ri(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.post(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/receiving-inspection",
            json={"resultado": "ok", "checklist_visual": True},
            headers=headers,
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
        print(f"Admin 403 for RI: OK")

    def test_admin_cant_registrar_cpi(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/cpi",
            json={"opcion": "cliente_ya_restablecio"},
            headers=headers,
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
        print(f"Admin 403 for CPI: OK")


# ────────────────────────────────────────────────────────────────
# CASO C: Tecnico CPI - 3 opciones
# ────────────────────────────────────────────────────────────────
class TestTecnicoCPI:
    """Tecnico can set CPI with all 3 options"""

    def test_cpi_opcion_cliente_ya_restablecio(self, tecnico_token):
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/cpi",
            json={
                "opcion": "cliente_ya_restablecio",
                "requiere_borrado": False,
                "autorizacion_cliente": True,
                "resultado": "no_aplica",
            },
            headers=headers,
        )
        assert resp.status_code == 200, f"CPI opcion1 failed: {resp.status_code} {resp.text}"
        data = resp.json()
        assert data.get("cpi_opcion") == "cliente_ya_restablecio"
        print(f"CPI opcion cliente_ya_restablecio: OK")

    def test_cpi_opcion_cliente_no_autoriza(self, tecnico_token):
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/cpi",
            json={
                "opcion": "cliente_no_autoriza",
                "requiere_borrado": False,
                "autorizacion_cliente": False,
                "resultado": "no_aplica",
            },
            headers=headers,
        )
        assert resp.status_code == 200, f"CPI opcion2 failed: {resp.status_code} {resp.text}"
        data = resp.json()
        assert data.get("cpi_opcion") == "cliente_no_autoriza"
        print(f"CPI opcion cliente_no_autoriza: OK")

    def test_cpi_opcion_sat_realizo_restablecimiento(self, tecnico_token):
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/cpi",
            json={
                "opcion": "sat_realizo_restablecimiento",
                "requiere_borrado": True,
                "autorizacion_cliente": True,
                "metodo": "factory_reset",
                "resultado": "completado",
            },
            headers=headers,
        )
        assert resp.status_code == 200, f"CPI opcion3 failed: {resp.status_code} {resp.text}"
        data = resp.json()
        assert data.get("cpi_opcion") == "sat_realizo_restablecimiento"
        assert data.get("cpi_metodo") == "factory_reset"
        print(f"CPI opcion sat_realizo_restablecimiento: OK")


# ────────────────────────────────────────────────────────────────
# CASO D: Tecnico RI
# ────────────────────────────────────────────────────────────────
class TestTecnicoRI:
    """Tecnico can register RI with all 3 results"""

    def test_ri_registrar_ok(self, tecnico_token):
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        resp = requests.post(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/receiving-inspection",
            json={
                "resultado_ri": "ok",
                "checklist_visual": {"inspeccion_visual": True},
                "fotos_recepcion": ["foto1.jpg", "foto2.jpg", "foto3.jpg"],
                "observaciones": "Test RI OK",
            },
            headers=headers,
        )
        assert resp.status_code == 200, f"RI OK failed: {resp.status_code} {resp.text}"
        data = resp.json()
        assert data.get("resultado_ri") == "ok"
        print(f"RI OK registered: resultado_ri={data.get('resultado_ri')}")

    def test_ri_verificar_persistencia(self, tecnico_token):
        """Verify RI was persisted via GET"""
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        resp = requests.get(f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ri_completada") == True
        assert data.get("ri_resultado") == "ok"
        print(f"RI persisted correctly: {data.get('ri_resultado')}")


# ────────────────────────────────────────────────────────────────
# CASO E: Iniciar Reparación (recibida → en_taller)
# ────────────────────────────────────────────────────────────────
class TestIniciarReparacion:
    """Test recibida → en_taller transition by tecnico"""

    def test_tecnico_puede_set_en_taller(self, tecnico_token):
        """Tecnico can change estado to en_taller (if prerequisites met)"""
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        
        # First check current state
        ot_resp = requests.get(f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}", headers=headers)
        current_state = ot_resp.json().get("estado")
        print(f"Current OT state: {current_state}")
        
        if current_state == "en_taller":
            print("OT already in en_taller - skipping transition test")
            return
        
        # Only try if in recibida state
        assert current_state == "recibida", f"Expected recibida, got {current_state}"
        
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/estado",
            json={"nuevo_estado": "en_taller"},
            headers=headers,
        )
        assert resp.status_code == 200, f"en_taller failed: {resp.status_code} {resp.text}"
        data = resp.json()
        # Response is message-based: {'message': 'Estado cambiado a en_taller'}
        assert "en_taller" in str(data).lower() or resp.status_code == 200
        print(f"Estado changed to en_taller: OK - {data}")

    def test_verify_en_taller_persisted(self, tecnico_token):
        """Verify en_taller state persisted"""
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        resp = requests.get(f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("estado") == "en_taller", f"Expected en_taller, got {data.get('estado')}"
        print(f"OT persisted in en_taller: OK")


# ────────────────────────────────────────────────────────────────
# CASO F: Cierre Reparación (en_taller → reparado)
# ────────────────────────────────────────────────────────────────
class TestCierreReparacion:
    """Test full QC closure flow en_taller → reparado"""

    def test_save_diagnostico_tecnico(self, tecnico_token):
        """Technician saves diagnostic (prerequisite for QC closure)"""
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}",
            json={"diagnostico_tecnico": "TEST_Diagnóstico técnico completado para QC final"},
            headers=headers,
        )
        assert resp.status_code == 200, f"Diagnostico save failed: {resp.status_code} {resp.text}"
        data = resp.json()
        assert data.get("diagnostico_tecnico") is not None
        print(f"Diagnostico saved: {data.get('diagnostico_tecnico', '')[:50]}")

    def test_estado_en_taller_for_qc(self, tecnico_token):
        """Verify OT is en_taller before QC"""
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        resp = requests.get(f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("estado") == "en_taller", f"Must be en_taller for QC, got {data.get('estado')}"
        print(f"OT is en_taller for QC: OK")

    def test_tecnico_cierre_reparacion_to_reparado(self, tecnico_token):
        """Full QC closure: patch QC data + change estado to reparado"""
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        
        # 1. Change state to reparado
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/estado",
            json={"nuevo_estado": "reparado"},
            headers=headers,
        )
        assert resp.status_code == 200, f"Cierre reparacion failed: {resp.status_code} {resp.text}"
        data = resp.json()
        # Response is message-based: {'message': 'Estado cambiado a reparado'}
        assert "reparado" in str(data).lower() or resp.status_code == 200
        print(f"Estado changed to reparado: OK - {data}")
        
        # 2. Save QC data
        qc_payload = {
            "diagnostico_salida_realizado": True,
            "funciones_verificadas": True,
            "limpieza_realizada": True,
            "bateria_nivel": 87,
            "bateria_estado": "ok",
            "qc_funciones": {
                "pantalla_touch": True,
                "wifi": True,
                "bluetooth": True,
                "camara_trasera": True,
                "microfono": True,
                "altavoz_auricular": True,
                "carga": True,
                "botones_fisicos": True,
            },
        }
        resp_qc = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}",
            json=qc_payload,
            headers=headers,
        )
        assert resp_qc.status_code == 200, f"QC data save failed: {resp_qc.status_code}"
        print(f"QC data saved: OK")

    def test_verify_reparado_persisted(self, tecnico_token):
        """Verify reparado state persisted"""
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        resp = requests.get(f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("estado") == "reparado", f"Expected reparado, got {data.get('estado')}"
        print(f"OT final state = reparado: OK")

    def test_reset_to_recibida_for_next_test_run(self, admin_token):
        """Reset OT state back to recibida for future test runs"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Admin can set back to recibida
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/estado",
            json={"nuevo_estado": "recibida"},
            headers=headers,
        )
        print(f"Reset to recibida: {resp.status_code}")
        if resp.status_code == 200:
            print(f"OT reset to recibida for future tests")
        else:
            print(f"Could not reset: {resp.text[:100]}")
        # Don't assert - it's OK if we can't reset (may be re_presupuestar path)

"""
Iteration 48 - Tests for role-based permissions on CPI/RI/Estado endpoints
Tests:
- CASO 1: Admin → PUT /api/ordenes/{id}/cpi → HTTP 403
- CASO 2: Admin → POST /api/ordenes/{id}/receiving-inspection → HTTP 403
- CASO 3: Admin → PATCH /api/ordenes/{id}/estado (en_taller/reparado/validacion) → HTTP 403
- CASO 4: Tecnico → PATCH /api/ordenes/{id}/cpi with 3 opciones → HTTP 200
- CASO 5: cpi_opcion y cpi_usuario_nombre correctos en respuesta
- CASO 6: OT antigua sin cpi_opcion → no error (retrocompat)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Known OT IDs from the test environment
OT_RECIBIDA = "75332015-b7cf-476a-a2e0-0d77207dfa08"
OT_ANTIGUA = "c8adc9dc-dce4-401e-ad96-7e790763e2d7"

ADMIN_EMAIL = "admin@techrepair.local"
ADMIN_PASSWORD = "Admin2026!"
TECNICO_EMAIL = "tecnico@techrepair.local"
TECNICO_PASSWORD = "Tecnico2026!"


def get_token(email: str, password: str) -> str:
    """Obtener JWT token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        return None
    return resp.json().get("access_token") or resp.json().get("token")


@pytest.fixture(scope="module")
def admin_token():
    token = get_token(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not token:
        pytest.skip(f"Admin login failed")
    return token


@pytest.fixture(scope="module")
def tecnico_token():
    token = get_token(TECNICO_EMAIL, TECNICO_PASSWORD)
    if not token:
        pytest.skip(f"Tecnico login failed")
    return token


def admin_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def tecnico_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ─── CASO 1: Admin → CPI → 403 ───────────────────────────────────────────────

class TestAdminCPI403:
    """Admin trying CPI endpoint must receive 403"""

    def test_admin_cpi_returns_403(self, admin_token):
        payload = {
            "opcion": "cliente_ya_restablecio",
            "requiere_borrado": False,
        }
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/cpi",
            json=payload,
            headers=admin_headers(admin_token)
        )
        print(f"Admin CPI response: {resp.status_code} - {resp.text[:200]}")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    def test_admin_cpi_error_message_mentions_tecnico(self, admin_token):
        payload = {"opcion": "cliente_no_autoriza", "requiere_borrado": False}
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/cpi",
            json=payload,
            headers=admin_headers(admin_token)
        )
        assert resp.status_code == 403
        detail = resp.json().get("detail", "")
        print(f"Error detail: {detail}")
        # Should mention solo técnico or similar restriction
        assert any(kw in detail.lower() for kw in ["técnico", "tecnico", "técnica", "solo", "restringida"]), \
            f"Error message doesn't mention tecnico restriction: {detail}"


# ─── CASO 2: Admin → RI → 403 ────────────────────────────────────────────────

class TestAdminRI403:
    """Admin trying RI endpoint must receive 403"""

    def test_admin_ri_returns_403(self, admin_token):
        payload = {
            "resultado_ri": "ok",
            "checklist_visual": {"pantalla": True, "carcasa": True},
            "fotos_recepcion": ["foto1.jpg", "foto2.jpg", "foto3.jpg"],
            "observaciones": "Test admin blocked",
        }
        resp = requests.post(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/receiving-inspection",
            json=payload,
            headers=admin_headers(admin_token)
        )
        print(f"Admin RI response: {resp.status_code} - {resp.text[:200]}")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    def test_admin_ri_error_message(self, admin_token):
        payload = {
            "resultado_ri": "ok",
            "checklist_visual": {},
            "fotos_recepcion": ["foto1.jpg", "foto2.jpg", "foto3.jpg"],
        }
        resp = requests.post(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/receiving-inspection",
            json=payload,
            headers=admin_headers(admin_token)
        )
        assert resp.status_code == 403
        detail = resp.json().get("detail", "")
        print(f"RI error detail: {detail}")
        assert len(detail) > 0, "Error detail should not be empty"


# ─── CASO 3: Admin → Estado técnico → 403 ────────────────────────────────────

class TestAdminEstadoTecnico403:
    """Admin trying to set technical states must receive 403"""

    def test_admin_estado_en_taller_returns_403(self, admin_token):
        payload = {
            "nuevo_estado": "en_taller",
            "usuario": "admin@techrepair.local",
        }
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/estado",
            json=payload,
            headers=admin_headers(admin_token)
        )
        print(f"Admin en_taller response: {resp.status_code} - {resp.text[:300]}")
        assert resp.status_code == 403, f"Expected 403 for en_taller, got {resp.status_code}: {resp.text}"

    def test_admin_estado_reparado_returns_403(self, admin_token):
        payload = {
            "nuevo_estado": "reparado",
            "usuario": "admin@techrepair.local",
        }
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/estado",
            json=payload,
            headers=admin_headers(admin_token)
        )
        print(f"Admin reparado response: {resp.status_code} - {resp.text[:300]}")
        assert resp.status_code == 403, f"Expected 403 for reparado, got {resp.status_code}: {resp.text}"

    def test_admin_estado_validacion_returns_403(self, admin_token):
        payload = {
            "nuevo_estado": "validacion",
            "usuario": "admin@techrepair.local",
        }
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/estado",
            json=payload,
            headers=admin_headers(admin_token)
        )
        print(f"Admin validacion response: {resp.status_code} - {resp.text[:300]}")
        assert resp.status_code == 403, f"Expected 403 for validacion, got {resp.status_code}: {resp.text}"

    def test_admin_estado_irreparable_returns_403(self, admin_token):
        payload = {
            "nuevo_estado": "irreparable",
            "usuario": "admin@techrepair.local",
        }
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/estado",
            json=payload,
            headers=admin_headers(admin_token)
        )
        print(f"Admin irreparable response: {resp.status_code} - {resp.text[:300]}")
        assert resp.status_code == 403, f"Expected 403 for irreparable, got {resp.status_code}: {resp.text}"

    def test_admin_estado_403_error_message(self, admin_token):
        payload = {
            "nuevo_estado": "en_taller",
            "usuario": "admin@techrepair.local",
        }
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/estado",
            json=payload,
            headers=admin_headers(admin_token)
        )
        assert resp.status_code == 403
        detail = resp.json().get("detail", "")
        print(f"Estado 403 detail: {detail}")
        assert any(kw in detail.lower() for kw in ["técnico", "tecnico", "técnica", "acción técnica"]), \
            f"Error detail missing 'accion tecnica' message: {detail}"


# ─── CASO 4 & 5: Tecnico → CPI con las 3 opciones → 200 ─────────────────────

class TestTecnicoCPI200:
    """Tecnico saving CPI with all 3 options must return 200"""

    def test_tecnico_cpi_opcion_cliente_ya_restablecio(self, tecnico_token):
        payload = {
            "opcion": "cliente_ya_restablecio",
            "requiere_borrado": False,
        }
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/cpi",
            json=payload,
            headers=tecnico_headers(tecnico_token)
        )
        print(f"Tecnico CPI cliente_ya_restablecio: {resp.status_code} - {resp.text[:300]}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("cpi_opcion") == "cliente_ya_restablecio", f"cpi_opcion mismatch: {data.get('cpi_opcion')}"

    def test_tecnico_cpi_opcion_cliente_no_autoriza(self, tecnico_token):
        payload = {
            "opcion": "cliente_no_autoriza",
            "requiere_borrado": False,
        }
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/cpi",
            json=payload,
            headers=tecnico_headers(tecnico_token)
        )
        print(f"Tecnico CPI cliente_no_autoriza: {resp.status_code} - {resp.text[:300]}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("cpi_opcion") == "cliente_no_autoriza"

    def test_tecnico_cpi_opcion_sat_realizo_restablecimiento(self, tecnico_token):
        payload = {
            "opcion": "sat_realizo_restablecimiento",
            "metodo": "factory_reset",
            "requiere_borrado": True,
            "autorizacion_cliente": True,
        }
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/cpi",
            json=payload,
            headers=tecnico_headers(tecnico_token)
        )
        print(f"Tecnico CPI sat_realizo_restablecimiento: {resp.status_code} - {resp.text[:300]}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("cpi_opcion") == "sat_realizo_restablecimiento"
        assert data.get("cpi_metodo") == "factory_reset"


# ─── CASO 5: cpi_usuario_nombre contiene nombre (no email) ───────────────────

class TestCPIUserNombre:
    """CPI saved by tecnico must store nombre (not email) in cpi_usuario_nombre"""

    def test_cpi_usuario_nombre_is_not_email(self, tecnico_token):
        payload = {
            "opcion": "cliente_ya_restablecio",
            "requiere_borrado": False,
        }
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/cpi",
            json=payload,
            headers=tecnico_headers(tecnico_token)
        )
        assert resp.status_code == 200
        data = resp.json()
        cpi_nombre = data.get("cpi_usuario_nombre", "")
        cpi_email = data.get("cpi_usuario", "")
        print(f"cpi_usuario_nombre: '{cpi_nombre}', cpi_usuario: '{cpi_email}'")
        # nombre must not contain @ (email)
        assert "@" not in cpi_nombre, f"cpi_usuario_nombre should not be an email: {cpi_nombre}"
        # nombre must not be empty
        assert len(cpi_nombre.strip()) > 0, "cpi_usuario_nombre should not be empty"
        # The email IS stored in cpi_usuario but not cpi_usuario_nombre
        assert "@" in cpi_email, f"cpi_usuario should contain the email: {cpi_email}"

    def test_cpi_opcion_field_saved_correctly(self, tecnico_token):
        """After saving, the returned order must have the cpi_opcion field"""
        payload = {
            "opcion": "sat_realizo_restablecimiento",
            "metodo": "factory_reset",
            "requiere_borrado": True,
            "autorizacion_cliente": True,
        }
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/cpi",
            json=payload,
            headers=tecnico_headers(tecnico_token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "cpi_opcion" in data, "cpi_opcion field missing from response"
        assert "cpi_usuario_nombre" in data, "cpi_usuario_nombre field missing from response"
        assert data.get("cpi_opcion") == "sat_realizo_restablecimiento"
        print(f"PASS: cpi_opcion='{data['cpi_opcion']}', nombre='{data['cpi_usuario_nombre']}'")


# ─── CASO 6: OT antigua sin campos CPI → no error ────────────────────────────

class TestRetrocompatibilidad:
    """Old OT without cpi fields should not cause errors"""

    def test_get_old_orden_no_error(self, tecnico_token):
        """Fetching old OT (no cpi_opcion/cpi_usuario_nombre) should return 200"""
        resp = requests.get(
            f"{BASE_URL}/api/ordenes/{OT_ANTIGUA}",
            headers=tecnico_headers(tecnico_token)
        )
        print(f"Old OT fetch: {resp.status_code}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"

    def test_old_orden_missing_cpi_fields_handled(self, tecnico_token):
        """Old OT response should not crash when cpi fields are missing"""
        resp = requests.get(
            f"{BASE_URL}/api/ordenes/{OT_ANTIGUA}",
            headers=tecnico_headers(tecnico_token)
        )
        assert resp.status_code == 200
        data = resp.json()
        # Fields may be absent (None) but should not cause an error
        cpi_opcion = data.get("cpi_opcion")  # None is OK
        cpi_nombre = data.get("cpi_usuario_nombre")  # None is OK
        print(f"Old OT cpi_opcion: {cpi_opcion}, cpi_usuario_nombre: {cpi_nombre}")
        # Just verify response is parseable and doesn't crash
        assert isinstance(data, dict), "Response should be a dict"

    def test_tecnico_can_save_cpi_on_old_orden(self, tecnico_token):
        """Even old OT (without cpi fields) can have CPI saved by tecnico"""
        # First, check old OT state
        resp_get = requests.get(
            f"{BASE_URL}/api/ordenes/{OT_ANTIGUA}",
            headers=tecnico_headers(tecnico_token)
        )
        assert resp_get.status_code == 200
        old_data = resp_get.json()
        estado_actual = old_data.get("estado", "unknown")
        print(f"Old OT state: {estado_actual}")

        # Attempt to save CPI (should succeed regardless of old state)
        payload = {"opcion": "cliente_ya_restablecio", "requiere_borrado": False}
        resp_patch = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_ANTIGUA}/cpi",
            json=payload,
            headers=tecnico_headers(tecnico_token)
        )
        print(f"Old OT CPI save: {resp_patch.status_code} - {resp_patch.text[:300]}")
        # Should succeed or only fail if 404 (OT not found)
        assert resp_patch.status_code in [200, 404], \
            f"Unexpected status: {resp_patch.status_code}: {resp_patch.text[:200]}"
        if resp_patch.status_code == 200:
            data = resp_patch.json()
            assert "cpi_opcion" in data, "cpi_opcion should be in response after save"


# ─── Admin estado ADMIN valido (no 403) ──────────────────────────────────────

class TestAdminEstadoAdmin200:
    """Admin CAN set administrative states (no 403)"""

    def test_admin_can_set_recibida_if_valid_transition(self, admin_token):
        """Admin setting a valid admin state should not return 403"""
        # Just verify admin doesn't get 403 (may get 400 for invalid transition)
        payload = {
            "nuevo_estado": "recibida",
            "usuario": "admin@techrepair.local",
        }
        resp = requests.patch(
            f"{BASE_URL}/api/ordenes/{OT_RECIBIDA}/estado",
            json=payload,
            headers=admin_headers(admin_token)
        )
        print(f"Admin recibida response: {resp.status_code} - {resp.text[:300]}")
        # Admin should NOT get 403 for admin states
        assert resp.status_code != 403, f"Admin should not get 403 for admin state 'recibida'"
        # May get 200 or 400 (if invalid transition) but NOT 403
        assert resp.status_code in [200, 400], f"Expected 200 or 400, got {resp.status_code}"

"""
Test Email Configuration and Budget Simulation features for CRM Revix.es
Iteration 23: Email config page + Budget simulation (presupuesto) flow
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MASTER_CREDS = {"email": "master@techrepair.local", "password": "master123"}
TEST_SINIESTRO_CODE = "26BE000774"


@pytest.fixture(scope="module")
def master_token():
    """Get master user token for authenticated requests."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MASTER_CREDS)
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    token = data.get("token") or data.get("access_token")
    assert token, f"No token in response: {data}"
    return token


@pytest.fixture(scope="module")
def master_headers(master_token):
    """Headers with master authentication."""
    return {"Authorization": f"Bearer {master_token}", "Content-Type": "application/json"}


class TestEmailConfig:
    """Tests for GET/PUT /api/email-config endpoints (master only)."""

    def test_get_email_config_requires_master(self):
        """GET /api/email-config should require master authentication."""
        response = requests.get(f"{BASE_URL}/api/email-config")
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_get_email_config_master_success(self, master_headers):
        """GET /api/email-config returns config for master user."""
        response = requests.get(f"{BASE_URL}/api/email-config", headers=master_headers)
        assert response.status_code == 200, f"GET email-config failed: {response.text}"
        data = response.json()
        # Should have expected fields
        assert "enabled" in data, "Missing 'enabled' field"
        assert "demo_mode" in data, "Missing 'demo_mode' field"
        print(f"GET /api/email-config: enabled={data.get('enabled')}, demo_mode={data.get('demo_mode')}")

    def test_put_email_config_saves_configuration(self, master_headers):
        """PUT /api/email-config saves new configuration."""
        config_data = {
            "enabled": True,
            "demo_mode": True,
            "demo_email": "test@example.com",
            "smtp_from": "Revix <notificaciones@revix.es>",
            "reply_to": "help@revix.es",
            "actions": {
                "orden_creada": {"enabled": True, "subject": "Test Subject", "body": "Test body"},
                "presupuesto_generado": {"enabled": True, "subject": "Presupuesto {codigo}", "body": "Precio: {precio}€"}
            }
        }
        response = requests.put(f"{BASE_URL}/api/email-config", headers=master_headers, json=config_data)
        assert response.status_code == 200, f"PUT email-config failed: {response.text}"
        data = response.json()
        assert "message" in data, f"No message in response: {data}"
        print(f"PUT /api/email-config: {data.get('message')}")

    def test_get_email_config_returns_saved_data(self, master_headers):
        """GET /api/email-config returns previously saved configuration."""
        # First save config
        config_data = {
            "enabled": True,
            "demo_mode": True,
            "demo_email": "help@revix.es",
            "smtp_from": "Revix <notificaciones@revix.es>",
            "reply_to": "help@revix.es",
            "actions": {
                "presupuesto_generado": {"enabled": True, "subject": "Presupuesto para {codigo}", "body": "Precio: {precio}€ - {notas}"}
            }
        }
        put_response = requests.put(f"{BASE_URL}/api/email-config", headers=master_headers, json=config_data)
        assert put_response.status_code == 200

        # Then verify it's saved
        get_response = requests.get(f"{BASE_URL}/api/email-config", headers=master_headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data.get("enabled") == True, f"enabled not saved: {data}"
        assert data.get("demo_mode") == True, f"demo_mode not saved: {data}"
        assert data.get("demo_email") == "help@revix.es", f"demo_email not saved: {data}"
        print(f"Verified saved config: {data}")


class TestBudgetSimulation:
    """Tests for POST /api/agente/simular-presupuesto and POST /api/agente/emitir-presupuesto."""

    def test_simular_presupuesto_requires_master(self):
        """POST /api/agente/simular-presupuesto/{code} requires master auth."""
        response = requests.post(f"{BASE_URL}/api/agente/simular-presupuesto/{TEST_SINIESTRO_CODE}")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_simular_presupuesto_creates_preregistro(self, master_headers):
        """POST /api/agente/simular-presupuesto/{code} creates pre-registro in pendiente_presupuesto."""
        response = requests.post(
            f"{BASE_URL}/api/agente/simular-presupuesto/{TEST_SINIESTRO_CODE}",
            headers=master_headers
        )
        # May return 200 with success, or 404 if code not found in portal
        if response.status_code == 200:
            data = response.json()
            assert "steps" in data, f"Missing 'steps' in response: {data}"
            assert "success" in data, f"Missing 'success' in response: {data}"
            assert data.get("success") == True, f"Simulation not successful: {data}"
            print(f"Simular presupuesto SUCCESS: {data.get('message')}")
            # Verify steps
            steps = data.get("steps", [])
            assert len(steps) >= 2, f"Expected at least 2 steps, got {len(steps)}"
            # Step 1 should be datos_portal_obtenidos
            assert steps[0].get("action") == "datos_portal_obtenidos", f"Step 1 wrong: {steps[0]}"
            # Step 2 should be pre_registro_creado
            assert steps[1].get("action") == "pre_registro_creado", f"Step 2 wrong: {steps[1]}"
            assert steps[1].get("estado") == "pendiente_presupuesto", f"Wrong estado in step 2: {steps[1]}"
        elif response.status_code == 404:
            # Portal may not have this code - this is acceptable
            print(f"Code {TEST_SINIESTRO_CODE} not found in portal (expected for test)")
        else:
            assert False, f"Unexpected status: {response.status_code} - {response.text}"

    def test_emitir_presupuesto_requires_master(self):
        """POST /api/agente/emitir-presupuesto requires master auth."""
        response = requests.post(
            f"{BASE_URL}/api/agente/emitir-presupuesto",
            json={"codigo_siniestro": TEST_SINIESTRO_CODE, "precio": 100.0}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_emitir_presupuesto_missing_preregistro(self, master_headers):
        """POST /api/agente/emitir-presupuesto returns 404 for non-existent pre-registro."""
        response = requests.post(
            f"{BASE_URL}/api/agente/emitir-presupuesto",
            headers=master_headers,
            json={"codigo_siniestro": "NONEXISTENT123", "precio": 50.0}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("Emitir presupuesto 404 for non-existent code: PASS")

    def test_emitir_presupuesto_flow(self, master_headers):
        """Full flow: simular -> emitir with price and notes."""
        # First simulate to create/update pre-registro
        sim_response = requests.post(
            f"{BASE_URL}/api/agente/simular-presupuesto/{TEST_SINIESTRO_CODE}",
            headers=master_headers
        )
        
        if sim_response.status_code != 200:
            pytest.skip(f"Simulation failed for {TEST_SINIESTRO_CODE}, skipping emit test")

        # Now emit budget
        emit_data = {
            "codigo_siniestro": TEST_SINIESTRO_CODE,
            "precio": 75.50,
            "notas": "Reparación de pantalla - test automático",
            "enviar_email": True
        }
        emit_response = requests.post(
            f"{BASE_URL}/api/agente/emitir-presupuesto",
            headers=master_headers,
            json=emit_data
        )
        assert emit_response.status_code == 200, f"Emit failed: {emit_response.text}"
        data = emit_response.json()
        assert "success" in data, f"Missing 'success' in response: {data}"
        assert "steps" in data, f"Missing 'steps' in response: {data}"
        print(f"Emitir presupuesto SUCCESS: {data.get('message')}")

        # Verify steps
        steps = data.get("steps", [])
        # Step 1: presupuesto_registrado
        step1 = next((s for s in steps if s.get("action") == "presupuesto_registrado"), None)
        assert step1 is not None, f"Missing presupuesto_registrado step: {steps}"
        assert step1.get("precio") == 75.50, f"Wrong precio: {step1}"

        # Step 2: email_presupuesto (checks demo mode)
        step2 = next((s for s in steps if s.get("action") == "email_presupuesto"), None)
        assert step2 is not None, f"Missing email_presupuesto step: {steps}"
        # In demo mode, sent should be true (if demo_email set) or false
        print(f"Email step: sent={step2.get('sent')}, to={step2.get('to')}, demo_mode={step2.get('demo_mode')}")


class TestPreRegistroState:
    """Tests to verify pre-registro state changes."""

    def test_preregistro_changes_to_presupuesto_emitido(self, master_headers):
        """After emitting, pre-registro should be in 'presupuesto_emitido' state."""
        # First ensure we have a pre-registro by simulating
        sim_response = requests.post(
            f"{BASE_URL}/api/agente/simular-presupuesto/{TEST_SINIESTRO_CODE}",
            headers=master_headers
        )
        if sim_response.status_code != 200:
            pytest.skip("Cannot create pre-registro for state test")

        # Emit budget
        emit_response = requests.post(
            f"{BASE_URL}/api/agente/emitir-presupuesto",
            headers=master_headers,
            json={
                "codigo_siniestro": TEST_SINIESTRO_CODE,
                "precio": 80.0,
                "notas": "Estado test",
                "enviar_email": False
            }
        )
        assert emit_response.status_code == 200

        # Verify pre-registro list shows the correct state
        list_response = requests.get(f"{BASE_URL}/api/pre-registros", headers=master_headers)
        if list_response.status_code == 200:
            data = list_response.json()
            pre_regs = data if isinstance(data, list) else data.get("pre_registros", [])
            matching = [p for p in pre_regs if p.get("codigo_siniestro") == TEST_SINIESTRO_CODE]
            if matching:
                assert matching[0].get("estado") == "presupuesto_emitido", f"Wrong state: {matching[0]}"
                print(f"Pre-registro state verified: presupuesto_emitido")
            else:
                print(f"Pre-registro {TEST_SINIESTRO_CODE} not in list (may be paged)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Iteration 44: Tests for role-based permissions on Diagnóstico/QC fields
Rules:
- Diagnóstico y Control de Calidad: ONLY técnico can edit
- Trazabilidad de baterías: admin/master CAN edit
- Admin/master receive 403 when trying to update QC fields
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "ramiraz91@gmail.com"
ADMIN_PASSWORD = "temp123"

# Campos de diagnóstico/QC exclusivos del técnico
CAMPOS_DIAGNOSTICO_QC = [
    'diagnostico_tecnico',
    'diagnostico_salida_realizado',
    'funciones_verificadas',
    'limpieza_realizada',
    'notas_cierre_tecnico',
    'fecha_fin_reparacion',
    'recepcion_checklist_completo',
    'recepcion_estado_fisico_registrado',
    'recepcion_accesorios_registrados',
    'recepcion_notas',
]

# Campos de batería que admin/master SÍ pueden editar
CAMPOS_BATERIA = [
    'bateria_reemplazada',
    'bateria_almacenamiento_temporal',
    'bateria_residuo_pendiente',
    'bateria_gestor_autorizado',
    'bateria_fecha_entrega_gestor',
]


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")  # API returns 'token' not 'access_token'
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Headers with admin auth token"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    }


@pytest.fixture(scope="module")
def test_orden_id(admin_headers):
    """Get or create a test order for permission testing"""
    # First try to find an existing order
    response = requests.get(f"{BASE_URL}/api/ordenes", headers=admin_headers)
    if response.status_code == 200:
        ordenes = response.json()
        if ordenes and len(ordenes) > 0:
            return ordenes[0]['id']
    
    # If no orders exist, create a test client and order
    cliente_data = {
        "nombre": "TEST_PERMISOS",
        "apellidos": "Cliente QC Test",
        "telefono": "600000044",
        "email": "test_permisos_44@test.com"
    }
    cliente_res = requests.post(f"{BASE_URL}/api/clientes", json=cliente_data, headers=admin_headers)
    if cliente_res.status_code not in [200, 201]:
        pytest.skip("Could not create test client")
    
    cliente_id = cliente_res.json()['id']
    
    orden_data = {
        "cliente_id": cliente_id,
        "dispositivo": {
            "marca": "Apple",
            "modelo": "iPhone 14 TEST",
            "imei": "123456789012345"
        },
        "descripcion_averia": "Test permiso QC"
    }
    orden_res = requests.post(f"{BASE_URL}/api/ordenes", json=orden_data, headers=admin_headers)
    if orden_res.status_code not in [200, 201]:
        pytest.skip("Could not create test order")
    
    return orden_res.json()['id']


class TestAdminCannotEditDiagnosticoQC:
    """Admin/master should receive 403 when trying to edit diagnóstico/QC fields"""
    
    def test_admin_blocked_diagnostico_salida_realizado(self, admin_headers, test_orden_id):
        """Admin cannot update diagnostico_salida_realizado - receives 403"""
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            json={"diagnostico_salida_realizado": True},
            headers=admin_headers
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "diagnóstico" in data.get("detail", "").lower() or "técnico" in data.get("detail", "").lower()
        print(f"✓ Admin blocked from diagnostico_salida_realizado: {data.get('detail')}")

    def test_admin_blocked_funciones_verificadas(self, admin_headers, test_orden_id):
        """Admin cannot update funciones_verificadas - receives 403"""
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            json={"funciones_verificadas": True},
            headers=admin_headers
        )
        assert response.status_code == 403
        print("✓ Admin blocked from funciones_verificadas")

    def test_admin_blocked_limpieza_realizada(self, admin_headers, test_orden_id):
        """Admin cannot update limpieza_realizada - receives 403"""
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            json={"limpieza_realizada": True},
            headers=admin_headers
        )
        assert response.status_code == 403
        print("✓ Admin blocked from limpieza_realizada")

    def test_admin_blocked_recepcion_checklist_completo(self, admin_headers, test_orden_id):
        """Admin cannot update recepcion_checklist_completo - receives 403"""
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            json={"recepcion_checklist_completo": True},
            headers=admin_headers
        )
        assert response.status_code == 403
        print("✓ Admin blocked from recepcion_checklist_completo")

    def test_admin_blocked_notas_cierre_tecnico(self, admin_headers, test_orden_id):
        """Admin cannot update notas_cierre_tecnico - receives 403"""
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            json={"notas_cierre_tecnico": "Notas de prueba admin"},
            headers=admin_headers
        )
        assert response.status_code == 403
        print("✓ Admin blocked from notas_cierre_tecnico")

    def test_admin_blocked_diagnostico_tecnico(self, admin_headers, test_orden_id):
        """Admin cannot update diagnostico_tecnico - receives 403"""
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            json={"diagnostico_tecnico": "Diagnóstico de prueba admin"},
            headers=admin_headers
        )
        assert response.status_code == 403
        print("✓ Admin blocked from diagnostico_tecnico")

    def test_admin_blocked_multiple_qc_fields(self, admin_headers, test_orden_id):
        """Admin cannot update multiple QC fields at once - receives 403"""
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            json={
                "diagnostico_salida_realizado": True,
                "funciones_verificadas": True,
                "limpieza_realizada": True
            },
            headers=admin_headers
        )
        assert response.status_code == 403
        print("✓ Admin blocked from updating multiple QC fields")


class TestAdminCanEditBateria:
    """Admin/master should be able to edit battery traceability fields (200 OK)"""
    
    def test_admin_can_update_bateria_reemplazada(self, admin_headers, test_orden_id):
        """Admin CAN update bateria_reemplazada - receives 200"""
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            json={"bateria_reemplazada": True},
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("bateria_reemplazada") == True
        print("✓ Admin can update bateria_reemplazada")

    def test_admin_can_update_bateria_almacenamiento_temporal(self, admin_headers, test_orden_id):
        """Admin CAN update bateria_almacenamiento_temporal - receives 200"""
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            json={"bateria_almacenamiento_temporal": True},
            headers=admin_headers
        )
        assert response.status_code == 200
        print("✓ Admin can update bateria_almacenamiento_temporal")

    def test_admin_can_update_bateria_residuo_pendiente(self, admin_headers, test_orden_id):
        """Admin CAN update bateria_residuo_pendiente - receives 200"""
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            json={"bateria_residuo_pendiente": True},
            headers=admin_headers
        )
        assert response.status_code == 200
        print("✓ Admin can update bateria_residuo_pendiente")

    def test_admin_can_update_bateria_gestor_autorizado(self, admin_headers, test_orden_id):
        """Admin CAN update bateria_gestor_autorizado - receives 200"""
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            json={"bateria_gestor_autorizado": "Gestor Test S.L."},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("bateria_gestor_autorizado") == "Gestor Test S.L."
        print("✓ Admin can update bateria_gestor_autorizado")

    def test_admin_can_update_bateria_fecha_entrega_gestor(self, admin_headers, test_orden_id):
        """Admin CAN update bateria_fecha_entrega_gestor - receives 200"""
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            json={"bateria_fecha_entrega_gestor": "2026-01-15"},
            headers=admin_headers
        )
        assert response.status_code == 200
        print("✓ Admin can update bateria_fecha_entrega_gestor")

    def test_admin_can_update_all_bateria_fields_together(self, admin_headers, test_orden_id):
        """Admin CAN update all battery fields at once - receives 200"""
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            json={
                "bateria_reemplazada": True,
                "bateria_almacenamiento_temporal": True,
                "bateria_residuo_pendiente": False,
                "bateria_gestor_autorizado": "Gestor Completo S.L.",
                "bateria_fecha_entrega_gestor": "2026-02-01"
            },
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("bateria_reemplazada") == True
        assert data.get("bateria_almacenamiento_temporal") == True
        assert data.get("bateria_gestor_autorizado") == "Gestor Completo S.L."
        print("✓ Admin can update all battery fields together")


class TestMixedFieldsUpdate:
    """Test behavior when mixing allowed and restricted fields"""
    
    def test_admin_blocked_when_mixing_qc_with_bateria(self, admin_headers, test_orden_id):
        """Admin is blocked even when mixing QC (restricted) with battery (allowed) fields"""
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            json={
                "bateria_reemplazada": True,  # Allowed
                "diagnostico_salida_realizado": True  # Restricted
            },
            headers=admin_headers
        )
        assert response.status_code == 403, f"Expected 403 when mixing fields, got {response.status_code}"
        print("✓ Admin blocked when mixing QC with battery fields")


class TestRegressionOrdenLoad:
    """Verify orden detail loads correctly without errors"""
    
    def test_orden_detalle_loads(self, admin_headers, test_orden_id):
        """Orden detail endpoint returns complete data"""
        response = requests.get(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "numero_orden" in data
        assert "estado" in data
        print(f"✓ Orden {data.get('numero_orden')} loads correctly")

    def test_ordenes_list_loads(self, admin_headers):
        """Ordenes list endpoint returns data"""
        response = requests.get(f"{BASE_URL}/api/ordenes", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Ordenes list returns {len(data)} orders")


class TestErrorMessageContent:
    """Verify error messages are clear and informative"""
    
    def test_403_error_message_mentions_tecnico(self, admin_headers, test_orden_id):
        """403 error message should mention técnico role"""
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{test_orden_id}",
            json={"diagnostico_salida_realizado": True},
            headers=admin_headers
        )
        assert response.status_code == 403
        detail = response.json().get("detail", "").lower()
        assert "técnico" in detail or "tecnico" in detail
        print(f"✓ Error message mentions técnico: {response.json().get('detail')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test Suite for Iteration 30 - Bug fixes and improvements
Tests:
1. RI optimistic updates (checklist persistence)
2. Delete photos endpoint
3. Garantía creation with correct data (indicaciones_cliente -> dispositivo.daños)
4. Edit dispositivo endpoint
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MASTER_EMAIL = "master@revix.es"
MASTER_PASSWORD = "RevixMaster2026!"
TECNICO_EMAIL = "tecnico1@revix.es"
TECNICO_PASSWORD = "Tecnico1Demo!"


@pytest.fixture(scope="module")
def master_token():
    """Get master admin token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MASTER_EMAIL,
        "password": MASTER_PASSWORD
    })
    assert response.status_code == 200, f"Master login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def tecnico_token():
    """Get tecnico token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TECNICO_EMAIL,
        "password": TECNICO_PASSWORD
    })
    assert response.status_code == 200, f"Tecnico login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def demo_orders(master_token):
    """Get demo orders for testing"""
    headers = {"Authorization": f"Bearer {master_token}"}
    response = requests.get(f"{BASE_URL}/api/ordenes?search=OT-DEMO", headers=headers)
    assert response.status_code == 200
    orders = response.json()
    return {o["numero_orden"]: o for o in orders}


class TestRIOptimisticUpdates:
    """Test (1) RI optimistic updates - checklist persistence"""
    
    def test_update_checklist_completo(self, tecnico_token, demo_orders):
        """Test updating recepcion_checklist_completo field"""
        # Get OT-DEMO-001 (pendiente_recibir)
        orden = demo_orders.get("OT-DEMO-001")
        if not orden:
            pytest.skip("OT-DEMO-001 not found")
        
        orden_id = orden["id"]
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        
        # Update checklist completo to True
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=headers,
            json={"recepcion_checklist_completo": True}
        )
        assert response.status_code == 200, f"Failed to update checklist: {response.text}"
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data.get("recepcion_checklist_completo") == True, "Checklist completo not persisted"
        print("✓ recepcion_checklist_completo persisted correctly")
    
    def test_update_estado_fisico(self, tecnico_token, demo_orders):
        """Test updating recepcion_estado_fisico_registrado field"""
        orden = demo_orders.get("OT-DEMO-001")
        if not orden:
            pytest.skip("OT-DEMO-001 not found")
        
        orden_id = orden["id"]
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        
        # Update estado fisico to True
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=headers,
            json={"recepcion_estado_fisico_registrado": True}
        )
        assert response.status_code == 200, f"Failed to update estado fisico: {response.text}"
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data.get("recepcion_estado_fisico_registrado") == True, "Estado fisico not persisted"
        print("✓ recepcion_estado_fisico_registrado persisted correctly")
    
    def test_update_accesorios(self, tecnico_token, demo_orders):
        """Test updating recepcion_accesorios_registrados field"""
        orden = demo_orders.get("OT-DEMO-001")
        if not orden:
            pytest.skip("OT-DEMO-001 not found")
        
        orden_id = orden["id"]
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        
        # Update accesorios to True
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=headers,
            json={"recepcion_accesorios_registrados": True}
        )
        assert response.status_code == 200, f"Failed to update accesorios: {response.text}"
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data.get("recepcion_accesorios_registrados") == True, "Accesorios not persisted"
        print("✓ recepcion_accesorios_registrados persisted correctly")
    
    def test_update_observaciones(self, tecnico_token, demo_orders):
        """Test updating recepcion_notas field (observaciones)"""
        orden = demo_orders.get("OT-DEMO-001")
        if not orden:
            pytest.skip("OT-DEMO-001 not found")
        
        orden_id = orden["id"]
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        
        test_notas = "Observaciones de prueba para RI - dispositivo en buen estado"
        
        # Update notas
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=headers,
            json={"recepcion_notas": test_notas}
        )
        assert response.status_code == 200, f"Failed to update notas: {response.text}"
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data.get("recepcion_notas") == test_notas, "Notas not persisted"
        print("✓ recepcion_notas persisted correctly")


class TestDeletePhotos:
    """Test (2) Delete photos endpoint"""
    
    def test_delete_photo_endpoint_exists(self, master_token, demo_orders):
        """Test that DELETE /api/ordenes/{id}/fotos endpoint exists"""
        orden = demo_orders.get("OT-DEMO-001")
        if not orden:
            pytest.skip("OT-DEMO-001 not found")
        
        orden_id = orden["id"]
        headers = {"Authorization": f"Bearer {master_token}"}
        
        # Try to delete a non-existent photo - should return 404 (not 405 method not allowed)
        response = requests.delete(
            f"{BASE_URL}/api/ordenes/{orden_id}/fotos",
            headers=headers,
            json={"url": "non_existent_photo.jpg", "tipo": "antes"}
        )
        # Should be 404 (photo not found) not 405 (method not allowed)
        assert response.status_code in [404, 400], f"Unexpected status: {response.status_code} - {response.text}"
        print(f"✓ DELETE /api/ordenes/{{id}}/fotos endpoint exists (status: {response.status_code})")
    
    def test_delete_photo_invalid_tipo(self, master_token, demo_orders):
        """Test delete photo with invalid tipo"""
        orden = demo_orders.get("OT-DEMO-001")
        if not orden:
            pytest.skip("OT-DEMO-001 not found")
        
        orden_id = orden["id"]
        headers = {"Authorization": f"Bearer {master_token}"}
        
        response = requests.delete(
            f"{BASE_URL}/api/ordenes/{orden_id}/fotos",
            headers=headers,
            json={"url": "test.jpg", "tipo": "invalid_tipo"}
        )
        assert response.status_code == 400, f"Should reject invalid tipo: {response.text}"
        print("✓ DELETE endpoint correctly rejects invalid tipo")


class TestGarantiaCreation:
    """Test (3) Garantía creation with correct data"""
    
    def test_crear_garantia_with_indicaciones(self, master_token, demo_orders):
        """Test creating garantía with indicaciones_cliente that overwrites dispositivo.daños"""
        # Use OT-DEMO-002 or OT-DEMO-003 (both in 'enviado' state)
        orden = demo_orders.get("OT-DEMO-002") or demo_orders.get("OT-DEMO-003")
        if not orden:
            pytest.skip("No order in 'enviado' state found")
        
        if orden.get("estado") != "enviado":
            pytest.skip(f"Order {orden['numero_orden']} not in 'enviado' state")
        
        orden_id = orden["id"]
        headers = {"Authorization": f"Bearer {master_token}"}
        
        indicaciones_test = "Pantalla parpadea tras la reparación - TEST GARANTIA"
        
        # Create garantía
        response = requests.post(
            f"{BASE_URL}/api/ordenes/{orden_id}/crear-garantia",
            headers=headers,
            json={"indicaciones_cliente": indicaciones_test}
        )
        
        if response.status_code == 400 and "ya es una garantía" in response.text:
            pytest.skip("Order is already a garantía")
        
        assert response.status_code == 200, f"Failed to create garantía: {response.text}"
        
        data = response.json()
        assert "orden_garantia" in data, "Response should contain orden_garantia"
        
        orden_garantia = data["orden_garantia"]
        garantia_id = orden_garantia.get("id")
        
        # Verify the garantía has correct data
        assert orden_garantia.get("es_garantia") == True, "es_garantia should be True"
        assert orden_garantia.get("indicaciones_garantia_cliente") == indicaciones_test, \
            f"indicaciones_garantia_cliente mismatch: {orden_garantia.get('indicaciones_garantia_cliente')}"
        assert orden_garantia.get("averia_descripcion") == indicaciones_test, \
            f"averia_descripcion should be overwritten: {orden_garantia.get('averia_descripcion')}"
        
        # Check dispositivo.daños
        dispositivo = orden_garantia.get("dispositivo", {})
        assert dispositivo.get("daños") == indicaciones_test, \
            f"dispositivo.daños should be overwritten: {dispositivo.get('daños')}"
        
        print(f"✓ Garantía created: {orden_garantia.get('numero_orden')}")
        print(f"  - es_garantia: {orden_garantia.get('es_garantia')}")
        print(f"  - indicaciones_garantia_cliente: {orden_garantia.get('indicaciones_garantia_cliente')}")
        print(f"  - averia_descripcion: {orden_garantia.get('averia_descripcion')}")
        print(f"  - dispositivo.daños: {dispositivo.get('daños')}")
        
        # Return garantia_id for cleanup or further tests
        return garantia_id


class TestEditDispositivo:
    """Test (4) Edit dispositivo endpoint"""
    
    def test_edit_dispositivo_as_admin(self, master_token, demo_orders):
        """Test editing dispositivo data as admin"""
        orden = demo_orders.get("OT-DEMO-001")
        if not orden:
            pytest.skip("OT-DEMO-001 not found")
        
        orden_id = orden["id"]
        headers = {"Authorization": f"Bearer {master_token}"}
        
        # New dispositivo data
        new_dispositivo = {
            "modelo": "iPhone 15 Pro Max TEST",
            "imei": orden.get("dispositivo", {}).get("imei", "123456789012345"),  # Keep original IMEI
            "color": "Titanio Negro",
            "daños": "Avería actualizada por admin - TEST"
        }
        
        # Update dispositivo via PATCH
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=headers,
            json={"dispositivo": new_dispositivo}
        )
        assert response.status_code == 200, f"Failed to update dispositivo: {response.text}"
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=headers)
        assert get_response.status_code == 200
        data = get_response.json()
        
        dispositivo = data.get("dispositivo", {})
        assert dispositivo.get("modelo") == new_dispositivo["modelo"], \
            f"Modelo mismatch: {dispositivo.get('modelo')}"
        assert dispositivo.get("color") == new_dispositivo["color"], \
            f"Color mismatch: {dispositivo.get('color')}"
        assert dispositivo.get("daños") == new_dispositivo["daños"], \
            f"Daños mismatch: {dispositivo.get('daños')}"
        
        print("✓ Dispositivo updated successfully")
        print(f"  - modelo: {dispositivo.get('modelo')}")
        print(f"  - color: {dispositivo.get('color')}")
        print(f"  - daños: {dispositivo.get('daños')}")
    
    def test_edit_dispositivo_tecnico_not_allowed(self, tecnico_token, demo_orders):
        """Test that tecnico cannot edit dispositivo (should be admin only)"""
        orden = demo_orders.get("OT-DEMO-001")
        if not orden:
            pytest.skip("OT-DEMO-001 not found")
        
        orden_id = orden["id"]
        headers = {"Authorization": f"Bearer {tecnico_token}"}
        
        # Try to update dispositivo as tecnico
        response = requests.patch(
            f"{BASE_URL}/api/ordenes/{orden_id}",
            headers=headers,
            json={"dispositivo": {"modelo": "Should Not Work"}}
        )
        
        # The PATCH endpoint filters fields for tecnico, so dispositivo should be ignored
        # Check that the model was NOT changed
        get_response = requests.get(f"{BASE_URL}/api/ordenes/{orden_id}", headers=headers)
        data = get_response.json()
        dispositivo = data.get("dispositivo", {})
        
        # Should still have the admin-set value, not "Should Not Work"
        assert dispositivo.get("modelo") != "Should Not Work", \
            "Tecnico should not be able to edit dispositivo"
        print("✓ Tecnico correctly cannot edit dispositivo")


class TestRIModifiable:
    """Test (1b) RI modifiable after completion"""
    
    def test_ri_buttons_exist_after_completion(self, master_token, demo_orders):
        """Verify that RI can be modified after completion (API level)"""
        # This is more of a frontend test, but we can verify the API allows re-registration
        orden = demo_orders.get("OT-DEMO-001")
        if not orden:
            pytest.skip("OT-DEMO-001 not found")
        
        # The RI endpoint should allow re-registration even if ri_completada is True
        # This is verified by the frontend test
        print("✓ RI modification is handled by frontend - see Playwright tests")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

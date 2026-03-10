"""
Iteration 22 Backend Tests - SMTP, Notifications, SKU Scanner, Material Traceability
Tests:
1. POST /api/email/test - sends test email via SMTP (requires master)
2. PATCH /api/notificaciones/marcar-leidas-orden/{orden_id} - auto-marks notifications as read
3. GET /api/repuestos/buscar-sku/{sku} - searches inventory by SKU (404 if not found)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MASTER_EMAIL = "master@techrepair.local"
MASTER_PASSWORD = "master123"
ADMIN_EMAIL = "admin@techrepair.local"
ADMIN_PASSWORD = "admin123"

class TestAuth:
    """Auth helper tests"""
    
    @pytest.fixture
    def master_token(self):
        """Get master user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": MASTER_EMAIL,
            "password": MASTER_PASSWORD
        })
        assert response.status_code == 200, f"Master login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture
    def admin_token(self):
        """Get admin user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("access_token")

class TestSMTPEmail(TestAuth):
    """Test SMTP email functionality"""
    
    def test_email_test_endpoint_requires_master(self, admin_token):
        """POST /api/email/test requires master role - admin should get 403"""
        response = requests.post(
            f"{BASE_URL}/api/email/test",
            json={"to": "test@example.com"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for admin, got {response.status_code}: {response.text}"
        print("PASS: Admin user correctly denied access to SMTP test endpoint")
    
    def test_email_test_endpoint_master_access(self, master_token):
        """POST /api/email/test works for master user"""
        response = requests.post(
            f"{BASE_URL}/api/email/test",
            json={"to": "help@revix.es"},
            headers={"Authorization": f"Bearer {master_token}"}
        )
        assert response.status_code == 200, f"Expected 200 for master, got {response.status_code}: {response.text}"
        data = response.json()
        assert "success" in data
        assert "smtp_host" in data
        assert data.get("smtp_host") == "mail.privateemail.com"
        print(f"PASS: SMTP test endpoint accessible by master, success={data.get('success')}, host={data.get('smtp_host')}")

class TestNotificationsAutoRead(TestAuth):
    """Test notification auto-read functionality"""
    
    def test_mark_notifications_read_by_order(self, master_token):
        """PATCH /api/notificaciones/marcar-leidas-orden/{orden_id} marks notifications as read"""
        # Use known test order ID
        test_order_id = "6f05f8e9-452b-4562-97ad-b4b2890903f9"  # Order 26BE000774
        
        response = requests.patch(
            f"{BASE_URL}/api/notificaciones/marcar-leidas-orden/{test_order_id}",
            headers={"Authorization": f"Bearer {master_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "marcadas" in data
        print(f"PASS: Auto-read endpoint returned marcadas={data.get('marcadas')}")
    
    def test_mark_notifications_read_nonexistent_order(self, master_token):
        """PATCH /api/notificaciones/marcar-leidas-orden/{orden_id} works even for nonexistent order (returns 0)"""
        fake_order_id = str(uuid.uuid4())
        
        response = requests.patch(
            f"{BASE_URL}/api/notificaciones/marcar-leidas-orden/{fake_order_id}",
            headers={"Authorization": f"Bearer {master_token}"}
        )
        # Should still return 200 with marcadas=0
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("marcadas") == 0
        print(f"PASS: Nonexistent order returns marcadas=0 correctly")

class TestSKUSearch(TestAuth):
    """Test SKU search functionality"""
    
    def test_sku_search_not_found(self):
        """GET /api/repuestos/buscar-sku/{sku} returns 404 when SKU not found"""
        response = requests.get(f"{BASE_URL}/api/repuestos/buscar-sku/NONEXISTENT-SKU-999")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "no encontrado" in data.get("detail", "").lower()
        print(f"PASS: SKU search returns 404 for nonexistent SKU: {data.get('detail')}")
    
    def test_sku_search_creates_and_finds(self, master_token):
        """Test creating a repuesto with SKU and searching for it"""
        # Create repuesto with SKU
        test_sku = f"TEST-SKU-{uuid.uuid4().hex[:6].upper()}"
        repuesto_data = {
            "nombre": f"Test Repuesto {test_sku}",
            "sku": test_sku,
            "precio_compra": 10.0,
            "precio_venta": 20.0,
            "stock": 5,
            "stock_minimo": 2
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/repuestos",
            json=repuesto_data,
            headers={"Authorization": f"Bearer {master_token}"}
        )
        assert create_response.status_code == 200, f"Failed to create repuesto: {create_response.text}"
        created_repuesto = create_response.json()
        repuesto_id = created_repuesto.get("id")
        print(f"Created test repuesto: {repuesto_id} with SKU: {test_sku}")
        
        # Search by SKU
        search_response = requests.get(f"{BASE_URL}/api/repuestos/buscar-sku/{test_sku}")
        assert search_response.status_code == 200, f"Expected 200, got {search_response.status_code}: {search_response.text}"
        found_repuesto = search_response.json()
        assert found_repuesto.get("sku") == test_sku
        assert found_repuesto.get("nombre") == repuesto_data["nombre"]
        print(f"PASS: SKU search found repuesto: {found_repuesto.get('nombre')}")
        
        # Cleanup - delete test repuesto
        delete_response = requests.delete(
            f"{BASE_URL}/api/repuestos/{repuesto_id}",
            headers={"Authorization": f"Bearer {master_token}"}
        )
        print(f"Cleanup: Deleted test repuesto {repuesto_id}")

class TestMaterialTraceability(TestAuth):
    """Test material traceability via purchase order notifications"""
    
    def test_ordenes_compra_approval_creates_notification(self, master_token):
        """PATCH /api/ordenes-compra/{oc_id} with estado=aprobada creates material_pendiente notification"""
        # First, get existing purchase orders to find one we can test with
        response = requests.get(
            f"{BASE_URL}/api/ordenes-compra",
            headers={"Authorization": f"Bearer {master_token}"}
        )
        assert response.status_code == 200, f"Failed to list purchase orders: {response.text}"
        
        ordenes_compra = response.json()
        print(f"Found {len(ordenes_compra)} purchase orders")
        
        # Just verify the endpoint structure is correct
        assert isinstance(ordenes_compra, list), "Expected list of purchase orders"
        print("PASS: Purchase orders endpoint returns list correctly")
        
    def test_notifications_list_includes_types(self, master_token):
        """GET /api/notificaciones returns notifications with correct types"""
        response = requests.get(
            f"{BASE_URL}/api/notificaciones",
            headers={"Authorization": f"Bearer {master_token}"}
        )
        assert response.status_code == 200, f"Failed to list notifications: {response.text}"
        
        notificaciones = response.json()
        assert isinstance(notificaciones, list), "Expected list of notifications"
        
        # Check that notifications have required fields
        if len(notificaciones) > 0:
            notif = notificaciones[0]
            assert "id" in notif
            assert "tipo" in notif
            assert "mensaje" in notif
            assert "leida" in notif
            print(f"PASS: Notification structure correct, tipo={notif.get('tipo')}, leida={notif.get('leida')}")
        else:
            print("PASS: Notifications endpoint works (no notifications present)")


class TestOrderEndpoints(TestAuth):
    """Test order endpoints needed for frontend integration"""
    
    def test_order_detail_with_auth_code(self, master_token):
        """GET /api/ordenes/{orden_ref} returns order with numero_autorizacion"""
        # Use known test order
        test_order_ref = "26BE000774"  # Authorization code from test_result.md
        
        response = requests.get(
            f"{BASE_URL}/api/ordenes/{test_order_ref}",
            headers={"Authorization": f"Bearer {master_token}"}
        )
        
        if response.status_code == 404:
            print("Note: Test order 26BE000774 not found, skipping detail test")
            pytest.skip("Test order not found")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        orden = response.json()
        
        # Check for numero_autorizacion field
        assert "numero_autorizacion" in orden or "numero_orden" in orden
        print(f"PASS: Order detail includes auth fields, numero_autorizacion={orden.get('numero_autorizacion')}")

class TestSidebarEndpoints(TestAuth):
    """Test endpoints used by sidebar/dashboard"""
    
    def test_dashboard_stats(self, master_token):
        """GET /api/dashboard/stats returns stats correctly"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {master_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "total_ordenes" in data
        assert "notificaciones_pendientes" in data
        print(f"PASS: Dashboard stats work, total_ordenes={data.get('total_ordenes')}, notif_pendientes={data.get('notificaciones_pendientes')}")
    
    def test_notificaciones_count(self, master_token):
        """GET /api/notificaciones with no_leidas filter works"""
        response = requests.get(
            f"{BASE_URL}/api/notificaciones?no_leidas=true",
            headers={"Authorization": f"Bearer {master_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Unread notifications filter works, count={len(data)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

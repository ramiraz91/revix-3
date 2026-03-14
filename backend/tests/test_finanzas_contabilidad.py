"""
Test Suite for Finanzas and Contabilidad APIs
Tests financial dashboard, invoices, and accounting endpoints

Revix CRM v1.2.0 - Financial Module Consolidation
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@techrepair.local"
TEST_PASSWORD = "Admin2026!"


@pytest.fixture(scope="module")
def auth_token():
    """Authenticate and get JWT token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in response"
    return data["token"]


@pytest.fixture
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


# ==================== FINANZAS DASHBOARD ====================

class TestFinanzasDashboard:
    """Test financial dashboard endpoints"""

    def test_dashboard_returns_data(self, auth_headers):
        """GET /api/finanzas/dashboard returns financial summary"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/dashboard?periodo=mes",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "periodo" in data
        assert "resumen" in data
        assert "ingresos" in data
        assert "gastos" in data
        assert "inventario" in data
        
        # Verify resumen fields
        resumen = data["resumen"]
        assert "total_ingresos" in resumen
        assert "total_gastos" in resumen
        assert "beneficio_bruto" in resumen
        assert "margen_porcentaje" in resumen
        
        # Verify ingresos structure
        ingresos = data["ingresos"]
        assert "ordenes_enviadas" in ingresos
        assert "facturas_venta" in ingresos
        assert "pendientes" in ingresos

    def test_dashboard_different_periods(self, auth_headers):
        """Test dashboard with different period values"""
        periods = ["dia", "semana", "mes", "trimestre", "año"]
        
        for period in periods:
            response = requests.get(
                f"{BASE_URL}/api/finanzas/dashboard?periodo={period}",
                headers=auth_headers
            )
            assert response.status_code == 200, f"Failed for period: {period}"
            data = response.json()
            assert data["periodo"]["tipo"] == period

    def test_evolucion_returns_monthly_data(self, auth_headers):
        """GET /api/finanzas/evolucion returns monthly evolution"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/evolucion?meses=6",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "meses" in data
        assert "datos" in data
        assert "totales" in data
        assert len(data["datos"]) == 6
        
        # Check each month has required fields
        for mes in data["datos"]:
            assert "mes" in mes
            assert "nombre_mes" in mes
            assert "ingresos" in mes
            assert "gastos" in mes
            assert "beneficio" in mes
            assert "ordenes_enviadas" in mes

    def test_valor_inventario(self, auth_headers):
        """GET /api/finanzas/inventario/valor returns inventory value"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/inventario/valor",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "resumen" in data
        resumen = data["resumen"]
        assert "total_referencias" in resumen
        assert "con_stock" in resumen
        assert "valor_coste" in resumen
        assert "valor_venta" in resumen
        assert "margen_potencial" in resumen

    def test_gastos_detalle(self, auth_headers):
        """GET /api/finanzas/gastos/detalle returns expense breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/gastos/detalle?periodo=mes",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "periodo" in data
        assert "compras_por_proveedor" in data
        assert "top_materiales_consumidos" in data
        assert "totales" in data


# ==================== CONTABILIDAD STATS ====================

class TestContabilidadStats:
    """Test accounting statistics endpoint"""

    def test_stats_returns_counts(self, auth_headers):
        """GET /api/contabilidad/stats returns statistics"""
        response = requests.get(
            f"{BASE_URL}/api/contabilidad/stats",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields
        assert "año" in data
        assert "facturas_venta" in data
        assert "facturas_compra" in data
        assert "albaranes" in data
        assert "albaranes_sin_facturar" in data
        assert "pendiente_cobro" in data
        assert "pendiente_pago" in data
        
        # Verify values match expected test data
        assert data["facturas_venta"] == 1, "Should have 1 sales invoice (FV-2026-00001)"
        assert data["pendiente_cobro"] == 229.89, f"Pending collection should be 229.89€, got {data['pendiente_cobro']}"


# ==================== FACTURAS ====================

class TestFacturas:
    """Test invoice endpoints"""

    def test_listar_facturas(self, auth_headers):
        """GET /api/contabilidad/facturas returns invoice list"""
        response = requests.get(
            f"{BASE_URL}/api/contabilidad/facturas",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert data["total"] >= 1, "Should have at least 1 invoice"

    def test_factura_fv_2026_00001_exists(self, auth_headers):
        """Verify invoice FV-2026-00001 exists with correct data"""
        response = requests.get(
            f"{BASE_URL}/api/contabilidad/facturas",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find the specific invoice
        invoice = None
        for item in data["items"]:
            if item.get("numero") == "FV-2026-00001":
                invoice = item
                break
        
        assert invoice is not None, "Invoice FV-2026-00001 not found"
        assert invoice["tipo"] == "venta"
        assert invoice["total"] == 229.89
        assert invoice["estado"] == "emitida"
        assert invoice["pendiente_cobro"] == 229.89

    def test_facturas_filter_by_type(self, auth_headers):
        """Test filtering invoices by type"""
        response = requests.get(
            f"{BASE_URL}/api/contabilidad/facturas?tipo=venta",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for item in data["items"]:
            assert item["tipo"] == "venta"


# ==================== PENDIENTES ====================

class TestPendientes:
    """Test pending invoices endpoint"""

    def test_pendientes_cobro_pago(self, auth_headers):
        """GET /api/contabilidad/informes/pendientes returns pending amounts"""
        response = requests.get(
            f"{BASE_URL}/api/contabilidad/informes/pendientes",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "pendiente_cobro" in data
        assert "pendiente_pago" in data
        assert "balance" in data
        
        # Verify pendiente_cobro structure
        cobro = data["pendiente_cobro"]
        assert "facturas" in cobro
        assert "total" in cobro
        assert "num_facturas" in cobro
        
        # Verify the expected pending amount
        assert cobro["total"] == 229.89, f"Expected 229.89€ pending, got {cobro['total']}"
        assert cobro["num_facturas"] == 1


# ==================== AUTH REQUIRED ====================

class TestAuthRequired:
    """Test endpoints require authentication"""

    def test_finanzas_dashboard_requires_auth(self):
        """Dashboard should require authentication"""
        response = requests.get(f"{BASE_URL}/api/finanzas/dashboard")
        assert response.status_code == 401

    def test_contabilidad_stats_requires_auth(self):
        """Stats should require authentication"""
        response = requests.get(f"{BASE_URL}/api/contabilidad/stats")
        assert response.status_code == 401

    def test_facturas_requires_auth(self):
        """Facturas should require authentication"""
        response = requests.get(f"{BASE_URL}/api/contabilidad/facturas")
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

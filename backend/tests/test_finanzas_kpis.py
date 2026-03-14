"""
Test suite for Finanzas Dashboard KPIs - Revix CRM
Tests the new KPI cards (7 metrics) added to the finance dashboard.
KPIs are GLOBAL metrics that should NOT change with periodo parameter.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestFinanzasKPIs:
    """Test the new kpis_ordenes section in /api/finanzas/dashboard"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token for all tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@techrepair.local", "password": "Admin2026!"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_dashboard_returns_kpis_ordenes_section(self):
        """Test that /api/finanzas/dashboard returns kpis_ordenes section"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/dashboard?periodo=mes",
            headers=self.headers
        )
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        
        # Verify kpis_ordenes section exists
        assert "kpis_ordenes" in data, "kpis_ordenes section missing from dashboard response"
        kpis = data["kpis_ordenes"]
        print(f"✓ kpis_ordenes section found: {kpis}")
    
    def test_kpis_ordenes_has_all_7_metrics(self):
        """Test that kpis_ordenes contains all 7 required metrics"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/dashboard?periodo=mes",
            headers=self.headers
        )
        assert response.status_code == 200
        kpis = response.json()["kpis_ordenes"]
        
        required_metrics = [
            "ordenes_totales",
            "ordenes_enviadas",
            "ordenes_pendientes",
            "valor_enviadas",
            "valor_pendientes",
            "coste_promedio_orden",
            "ticket_medio"
        ]
        
        for metric in required_metrics:
            assert metric in kpis, f"Missing metric: {metric}"
            print(f"✓ {metric}: {kpis[metric]}")
    
    def test_kpis_are_numeric(self):
        """Test that all KPI values are numeric"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/dashboard?periodo=mes",
            headers=self.headers
        )
        assert response.status_code == 200
        kpis = response.json()["kpis_ordenes"]
        
        for key, value in kpis.items():
            assert isinstance(value, (int, float)), f"{key} is not numeric: {type(value)}"
            print(f"✓ {key} is numeric ({type(value).__name__}): {value}")
    
    def test_kpis_global_not_filtered_by_periodo(self):
        """Test that KPIs are GLOBAL and don't change with periodo parameter"""
        periods = ["dia", "semana", "mes", "trimestre"]
        kpis_by_period = {}
        
        for period in periods:
            response = requests.get(
                f"{BASE_URL}/api/finanzas/dashboard?periodo={period}",
                headers=self.headers
            )
            assert response.status_code == 200, f"Failed for period {period}"
            kpis_by_period[period] = response.json()["kpis_ordenes"]
        
        # All KPIs should be identical across periods
        reference = kpis_by_period["dia"]
        for period, kpis in kpis_by_period.items():
            for metric in reference:
                assert kpis[metric] == reference[metric], \
                    f"KPI {metric} differs for period {period}: {kpis[metric]} vs {reference[metric]}"
        
        print(f"✓ KPIs are global (same across all periods): {reference}")
    
    def test_division_by_zero_handled(self):
        """Test that division by zero is handled correctly (coste_promedio, ticket_medio)"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/dashboard?periodo=mes",
            headers=self.headers
        )
        assert response.status_code == 200
        kpis = response.json()["kpis_ordenes"]
        
        # These should be 0 or valid numbers, never None or errors
        assert kpis.get("coste_promedio_orden") is not None, "coste_promedio_orden is None"
        assert kpis.get("ticket_medio") is not None, "ticket_medio is None"
        assert isinstance(kpis["coste_promedio_orden"], (int, float)), "coste_promedio_orden not numeric"
        assert isinstance(kpis["ticket_medio"], (int, float)), "ticket_medio not numeric"
        
        print(f"✓ coste_promedio_orden: {kpis['coste_promedio_orden']}")
        print(f"✓ ticket_medio: {kpis['ticket_medio']}")
    
    def test_dashboard_other_fields_unchanged(self):
        """Test that existing dashboard fields (resumen, ingresos, gastos, inventario) still exist"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/dashboard?periodo=mes",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        existing_fields = ["periodo", "resumen", "ingresos", "gastos", "inventario"]
        for field in existing_fields:
            assert field in data, f"Missing existing field: {field}"
            print(f"✓ {field} exists")
        
        # Verify resumen has key metrics
        resumen = data["resumen"]
        assert "total_ingresos" in resumen
        assert "total_gastos" in resumen
        assert "beneficio_bruto" in resumen
        assert "margen_porcentaje" in resumen
        print(f"✓ resumen: {resumen}")
    
    def test_periodo_selector_works(self):
        """Test that periodo selector still filters other dashboard data"""
        response_dia = requests.get(
            f"{BASE_URL}/api/finanzas/dashboard?periodo=dia",
            headers=self.headers
        )
        response_año = requests.get(
            f"{BASE_URL}/api/finanzas/dashboard?periodo=año",
            headers=self.headers
        )
        
        assert response_dia.status_code == 200
        assert response_año.status_code == 200
        
        data_dia = response_dia.json()
        data_año = response_año.json()
        
        # Period info should differ
        assert data_dia["periodo"]["tipo"] == "dia"
        assert data_año["periodo"]["tipo"] == "año"
        
        print(f"✓ periodo dia: {data_dia['periodo']}")
        print(f"✓ periodo año: {data_año['periodo']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

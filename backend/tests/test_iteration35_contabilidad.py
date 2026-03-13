"""
Iteration 35: NEXORA CRM/ERP - Contabilidad Module Testing
Tests for: Facturas, Albaranes, Pagos, Abonos, Informes IVA, Modelo 347
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://workshop-erp-3.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "ramiraz91@gmail.com"
TEST_PASSWORD = "temp123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Shared requests session with auth"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestAuthentication:
    """Test login and authentication"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401


class TestDashboard:
    """Test dashboard statistics"""
    
    def test_dashboard_stats(self, api_client):
        """Test dashboard stats endpoint"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_ordenes" in data
        assert "ordenes_por_estado" in data
        assert "total_clientes" in data
        assert "total_repuestos" in data


class TestClientes:
    """Test CRUD operations for clients"""
    
    def test_listar_clientes(self, api_client):
        """Test listing clients"""
        response = api_client.get(f"{BASE_URL}/api/clientes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_crear_cliente(self, api_client):
        """Test creating a new client"""
        cliente_data = {
            "nombre": "TEST_Cliente_Contabilidad",
            "apellidos": "Prueba",
            "telefono": "600123456",
            "email": "test_contabilidad@example.com",
            "dni": "12345678Z",
            "direccion": "Calle Test 123"
        }
        response = api_client.post(f"{BASE_URL}/api/clientes", json=cliente_data)
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == cliente_data["nombre"]
        assert "id" in data
        return data["id"]


class TestOrdenes:
    """Test CRUD operations for work orders"""
    
    def test_listar_ordenes(self, api_client):
        """Test listing orders"""
        response = api_client.get(f"{BASE_URL}/api/ordenes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_filtrar_ordenes_por_estado(self, api_client):
        """Test filtering orders by status"""
        response = api_client.get(f"{BASE_URL}/api/ordenes?estado=pendiente_recibir")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestInventario:
    """Test inventory operations"""
    
    def test_listar_repuestos(self, api_client):
        """Test listing inventory items"""
        response = api_client.get(f"{BASE_URL}/api/repuestos")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    def test_filtrar_repuestos_por_proveedor(self, api_client):
        """Test filtering inventory by provider"""
        response = api_client.get(f"{BASE_URL}/api/repuestos?proveedor=Utopya")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_busqueda_rapida_repuestos(self, api_client):
        """Test quick search for inventory"""
        response = api_client.get(f"{BASE_URL}/api/repuestos/buscar/rapido?q=pantalla&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestContabilidadStats:
    """Test contabilidad statistics endpoint"""
    
    def test_contabilidad_stats(self, api_client):
        """Test contabilidad stats endpoint"""
        response = api_client.get(f"{BASE_URL}/api/contabilidad/stats")
        assert response.status_code == 200
        data = response.json()
        assert "año" in data
        assert "facturas_venta" in data
        assert "facturas_compra" in data
        assert "albaranes" in data
        assert "pendiente_cobro" in data
        assert "pendiente_pago" in data


class TestContabilidadFacturas:
    """Test facturas (invoices) CRUD operations"""
    
    @pytest.fixture(scope="class")
    def test_cliente_id(self, api_client):
        """Create a test client for invoice tests"""
        cliente_data = {
            "nombre": "TEST_Factura_Cliente",
            "apellidos": "Contabilidad",
            "telefono": "600111222",
            "email": "factura_test@example.com",
            "dni": "87654321X",
            "direccion": "Calle Factura 456"
        }
        response = api_client.post(f"{BASE_URL}/api/clientes", json=cliente_data)
        if response.status_code == 200:
            return response.json()["id"]
        # If client exists, search for it
        response = api_client.get(f"{BASE_URL}/api/clientes?search=TEST_Factura_Cliente")
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]["id"]
        pytest.skip("Could not create test client")
    
    def test_crear_factura_venta(self, api_client, test_cliente_id):
        """Test creating a sales invoice"""
        factura_data = {
            "tipo": "venta",
            "cliente_id": test_cliente_id,
            "nombre_fiscal": "TEST_Empresa Prueba S.L.",
            "nif_cif": "B12345678",
            "direccion_fiscal": "Calle Test 123, Madrid",
            "lineas": [
                {
                    "descripcion": "Reparación pantalla iPhone 15",
                    "cantidad": 1,
                    "precio_unitario": 150.00,
                    "descuento": 0,
                    "tipo_iva": "general",
                    "iva_porcentaje": 21
                }
            ],
            "notas": "Factura de prueba",
            "metodo_pago": "transferencia"
        }
        response = api_client.post(f"{BASE_URL}/api/contabilidad/facturas", json=factura_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "numero" in data
        assert data["tipo"] == "venta"
        assert data["estado"] == "borrador"
        assert data["nombre_fiscal"] == "TEST_Empresa Prueba S.L."
        # Verify totals calculated correctly
        assert data["base_imponible"] == 150.00
        assert data["total_iva"] == 31.50  # 21% of 150
        assert data["total"] == 181.50
        return data["id"]
    
    def test_listar_facturas(self, api_client):
        """Test listing invoices"""
        response = api_client.get(f"{BASE_URL}/api/contabilidad/facturas")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
    
    def test_filtrar_facturas_por_tipo(self, api_client):
        """Test filtering invoices by type"""
        response = api_client.get(f"{BASE_URL}/api/contabilidad/facturas?tipo=venta")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        # All items should be type 'venta'
        for item in data["items"]:
            assert item["tipo"] == "venta"
    
    def test_filtrar_facturas_por_estado(self, api_client):
        """Test filtering invoices by status"""
        response = api_client.get(f"{BASE_URL}/api/contabilidad/facturas?estado=borrador")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestContabilidadEmitirFactura:
    """Test emitting invoices"""
    
    @pytest.fixture(scope="class")
    def factura_borrador_id(self, api_client):
        """Create a draft invoice for testing"""
        factura_data = {
            "tipo": "venta",
            "nombre_fiscal": "TEST_Emitir Factura S.L.",
            "nif_cif": "B99999999",
            "direccion_fiscal": "Calle Emitir 789",
            "lineas": [
                {
                    "descripcion": "Servicio de prueba",
                    "cantidad": 2,
                    "precio_unitario": 50.00,
                    "descuento": 10,
                    "tipo_iva": "general",
                    "iva_porcentaje": 21
                }
            ],
            "metodo_pago": "efectivo"
        }
        response = api_client.post(f"{BASE_URL}/api/contabilidad/facturas", json=factura_data)
        if response.status_code == 200:
            return response.json()["id"]
        pytest.skip("Could not create draft invoice")
    
    def test_emitir_factura(self, api_client, factura_borrador_id):
        """Test emitting a draft invoice"""
        response = api_client.post(f"{BASE_URL}/api/contabilidad/facturas/{factura_borrador_id}/emitir")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "numero" in data
        
        # Verify invoice is now emitted
        response = api_client.get(f"{BASE_URL}/api/contabilidad/facturas/{factura_borrador_id}")
        assert response.status_code == 200
        factura = response.json()
        assert factura["estado"] == "emitida"


class TestContabilidadPagos:
    """Test payment registration"""
    
    @pytest.fixture(scope="class")
    def factura_emitida_id(self, api_client):
        """Create and emit an invoice for payment testing"""
        # Create invoice
        factura_data = {
            "tipo": "venta",
            "nombre_fiscal": "TEST_Pago Cliente S.L.",
            "nif_cif": "B88888888",
            "direccion_fiscal": "Calle Pago 321",
            "lineas": [
                {
                    "descripcion": "Producto para pago",
                    "cantidad": 1,
                    "precio_unitario": 100.00,
                    "descuento": 0,
                    "tipo_iva": "general",
                    "iva_porcentaje": 21
                }
            ],
            "metodo_pago": "transferencia"
        }
        response = api_client.post(f"{BASE_URL}/api/contabilidad/facturas", json=factura_data)
        if response.status_code != 200:
            pytest.skip("Could not create invoice for payment test")
        factura_id = response.json()["id"]
        
        # Emit invoice
        response = api_client.post(f"{BASE_URL}/api/contabilidad/facturas/{factura_id}/emitir")
        if response.status_code != 200:
            pytest.skip("Could not emit invoice for payment test")
        
        return factura_id
    
    def test_registrar_pago_completo(self, api_client, factura_emitida_id):
        """Test registering a full payment"""
        pago_data = {
            "factura_id": factura_emitida_id,
            "importe": 121.00,  # Total with IVA
            "metodo": "transferencia",
            "referencia": "TEST_TRANSFER_001"
        }
        response = api_client.post(f"{BASE_URL}/api/contabilidad/pagos", json=pago_data)
        assert response.status_code == 200
        data = response.json()
        assert data["nuevo_pendiente"] == 0
        assert data["estado"] == "pagada"
    
    def test_registrar_pago_parcial(self, api_client):
        """Test registering a partial payment"""
        # Create and emit a new invoice
        factura_data = {
            "tipo": "venta",
            "nombre_fiscal": "TEST_Pago Parcial S.L.",
            "nif_cif": "B77777777",
            "lineas": [
                {
                    "descripcion": "Producto parcial",
                    "cantidad": 1,
                    "precio_unitario": 200.00,
                    "descuento": 0,
                    "tipo_iva": "general",
                    "iva_porcentaje": 21
                }
            ],
            "metodo_pago": "transferencia"
        }
        response = api_client.post(f"{BASE_URL}/api/contabilidad/facturas", json=factura_data)
        assert response.status_code == 200
        factura_id = response.json()["id"]
        
        # Emit
        response = api_client.post(f"{BASE_URL}/api/contabilidad/facturas/{factura_id}/emitir")
        assert response.status_code == 200
        
        # Register partial payment (100 of 242)
        pago_data = {
            "factura_id": factura_id,
            "importe": 100.00,
            "metodo": "efectivo",
            "referencia": "TEST_PARTIAL_001"
        }
        response = api_client.post(f"{BASE_URL}/api/contabilidad/pagos", json=pago_data)
        assert response.status_code == 200
        data = response.json()
        assert data["nuevo_pendiente"] == 142.00  # 242 - 100
        assert data["estado"] == "parcial"


class TestContabilidadAlbaranes:
    """Test delivery notes (albaranes)"""
    
    def test_listar_albaranes(self, api_client):
        """Test listing delivery notes"""
        response = api_client.get(f"{BASE_URL}/api/contabilidad/albaranes")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    def test_filtrar_albaranes_sin_facturar(self, api_client):
        """Test filtering unfactured delivery notes"""
        response = api_client.get(f"{BASE_URL}/api/contabilidad/albaranes?facturado=false")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestContabilidadInformes:
    """Test accounting reports"""
    
    def test_informe_resumen(self, api_client):
        """Test summary report"""
        response = api_client.get(f"{BASE_URL}/api/contabilidad/informes/resumen")
        assert response.status_code == 200
        data = response.json()
        assert "año" in data
        assert "ventas" in data
        assert "compras" in data
        assert "liquidacion_iva" in data
        assert "beneficio_bruto" in data
        
        # Verify ventas structure
        assert "total" in data["ventas"]
        assert "base_imponible" in data["ventas"]
        assert "iva_repercutido" in data["ventas"]
        assert "pendiente_cobro" in data["ventas"]
        
        # Verify compras structure
        assert "total" in data["compras"]
        assert "base_imponible" in data["compras"]
        assert "iva_soportado" in data["compras"]
        assert "pendiente_pago" in data["compras"]
    
    def test_informe_pendientes(self, api_client):
        """Test pending invoices report"""
        response = api_client.get(f"{BASE_URL}/api/contabilidad/informes/pendientes")
        assert response.status_code == 200
        data = response.json()
        assert "pendiente_cobro" in data
        assert "pendiente_pago" in data
        assert "balance" in data
        
        # Verify structure
        assert "facturas" in data["pendiente_cobro"]
        assert "total" in data["pendiente_cobro"]
        assert "facturas" in data["pendiente_pago"]
        assert "total" in data["pendiente_pago"]
    
    def test_informe_iva_trimestral(self, api_client):
        """Test quarterly VAT report"""
        año = datetime.now().year
        response = api_client.get(f"{BASE_URL}/api/contabilidad/informes/iva-trimestral?año={año}&trimestre=1")
        assert response.status_code == 200
        data = response.json()
        assert "año" in data
        assert "trimestre" in data
        assert "iva_devengado" in data
        assert "iva_deducible" in data
        assert "diferencia" in data
        assert "resultado" in data
    
    def test_informe_modelo_347(self, api_client):
        """Test modelo 347 report (operations with third parties)"""
        año = datetime.now().year
        response = api_client.get(f"{BASE_URL}/api/contabilidad/informes/modelo-347?año={año}")
        assert response.status_code == 200
        data = response.json()
        assert "año" in data
        assert "limite_declaracion" in data
        assert data["limite_declaracion"] == 3005.06
        assert "operaciones_declarables" in data
        assert "resumen" in data
        assert "num_terceros" in data["resumen"]


class TestContabilidadRecordatorios:
    """Test payment reminders"""
    
    def test_obtener_facturas_vencidas(self, api_client):
        """Test getting overdue invoices"""
        response = api_client.get(f"{BASE_URL}/api/contabilidad/recordatorios/vencidas")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_verificar_facturas_vencidas(self, api_client):
        """Test marking overdue invoices"""
        response = api_client.post(f"{BASE_URL}/api/contabilidad/recordatorios/verificar-vencidas")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "facturas_actualizadas" in data
    
    def test_obtener_config_recordatorios(self, api_client):
        """Test getting reminder configuration"""
        response = api_client.get(f"{BASE_URL}/api/contabilidad/recordatorios/config")
        assert response.status_code == 200
        data = response.json()
        assert "tipo" in data
        assert data["tipo"] == "recordatorios_facturas"


class TestNavigation:
    """Test navigation between sections"""
    
    def test_api_root(self, api_client):
        """Test API root endpoint"""
        response = api_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_all_main_endpoints_accessible(self, api_client):
        """Test all main endpoints are accessible"""
        endpoints = [
            "/api/dashboard/stats",
            "/api/ordenes",
            "/api/clientes",
            "/api/repuestos",
            "/api/contabilidad/stats",
            "/api/contabilidad/facturas",
            "/api/contabilidad/albaranes",
            "/api/contabilidad/informes/resumen",
            "/api/contabilidad/informes/pendientes",
        ]
        
        for endpoint in endpoints:
            response = api_client.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200, f"Endpoint {endpoint} failed with status {response.status_code}"


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_facturas(self, api_client):
        """Clean up test invoices (mark as anulada)"""
        # Get all invoices with TEST_ prefix
        response = api_client.get(f"{BASE_URL}/api/contabilidad/facturas?page_size=100")
        if response.status_code == 200:
            facturas = response.json().get("items", [])
            for factura in facturas:
                if "TEST_" in factura.get("nombre_fiscal", ""):
                    # Try to anular if not already
                    if factura.get("estado") != "anulada":
                        api_client.post(
                            f"{BASE_URL}/api/contabilidad/facturas/{factura['id']}/anular",
                            json={"motivo": "Test cleanup"}
                        )
        assert True  # Cleanup is best-effort
    
    def test_cleanup_test_clientes(self, api_client):
        """Clean up test clients"""
        response = api_client.get(f"{BASE_URL}/api/clientes?search=TEST_")
        if response.status_code == 200:
            clientes = response.json()
            for cliente in clientes:
                if cliente.get("nombre", "").startswith("TEST_"):
                    api_client.delete(f"{BASE_URL}/api/clientes/{cliente['id']}")
        assert True  # Cleanup is best-effort

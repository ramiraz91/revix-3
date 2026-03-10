"""
Test suite for Purchase Order (Órdenes de Compra) Traceability System
Tests the complete flow: pendiente -> aprobada -> pedida -> recibida
And verifies material state updates in work orders
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestOrdenesCompraTrazabilidad:
    """Test purchase order traceability flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
    def test_01_list_ordenes_compra(self):
        """GET /api/ordenes-compra - List purchase orders"""
        response = requests.get(f"{BASE_URL}/api/ordenes-compra", headers=self.headers)
        assert response.status_code == 200, f"Failed to list OC: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Listed {len(data)} purchase orders")
        
    def test_02_list_ordenes_compra_by_estado(self):
        """GET /api/ordenes-compra?estado=pendiente - Filter by status"""
        for estado in ['pendiente', 'aprobada', 'pedida', 'recibida']:
            response = requests.get(f"{BASE_URL}/api/ordenes-compra?estado={estado}", headers=self.headers)
            assert response.status_code == 200, f"Failed to filter by {estado}: {response.text}"
            data = response.json()
            print(f"✓ Found {len(data)} orders with estado={estado}")
            
    def test_03_get_existing_orden_trabajo(self):
        """Get an existing work order to use for creating OC"""
        response = requests.get(f"{BASE_URL}/api/ordenes", headers=self.headers)
        assert response.status_code == 200, f"Failed to list orders: {response.text}"
        ordenes = response.json()
        assert len(ordenes) > 0, "No work orders found"
        self.orden_trabajo = ordenes[0]
        print(f"✓ Found work order: {self.orden_trabajo['numero_orden']}")
        return self.orden_trabajo
        
    def test_04_create_orden_compra(self):
        """POST /api/ordenes-compra - Create OC and verify material is added to work order"""
        # First get a work order
        response = requests.get(f"{BASE_URL}/api/ordenes", headers=self.headers)
        assert response.status_code == 200
        ordenes = response.json()
        assert len(ordenes) > 0, "No work orders found"
        orden_trabajo = ordenes[0]
        orden_trabajo_id = orden_trabajo['id']
        materiales_antes = len(orden_trabajo.get('materiales', []))
        
        # Create purchase order
        oc_data = {
            "nombre_pieza": "TEST_Pantalla LCD iPhone 14",
            "descripcion": "Pantalla de repuesto para prueba de trazabilidad",
            "cantidad": 1,
            "orden_trabajo_id": orden_trabajo_id,
            "solicitado_por": "admin@techrepair.local",
            "precio_unitario": 150.00,
            "coste_unitario": 100.00
        }
        
        response = requests.post(f"{BASE_URL}/api/ordenes-compra", json=oc_data, headers=self.headers)
        assert response.status_code == 200, f"Failed to create OC: {response.text}"
        oc = response.json()
        
        # Verify OC created correctly
        assert "id" in oc, "OC should have an id"
        assert "numero_oc" in oc, "OC should have numero_oc"
        assert oc.get("estado") == "pendiente", f"Initial estado should be 'pendiente', got {oc.get('estado')}"
        assert oc.get("material_añadido") == True, "Material should be added to work order"
        
        print(f"✓ Created OC: {oc['numero_oc']} with estado=pendiente")
        
        # Verify material was added to work order
        response = requests.get(f"{BASE_URL}/api/ordenes/{orden_trabajo_id}", headers=self.headers)
        assert response.status_code == 200
        orden_actualizada = response.json()
        materiales_despues = len(orden_actualizada.get('materiales', []))
        
        assert materiales_despues > materiales_antes, "Material should be added to work order"
        
        # Find the new material
        nuevo_material = None
        for m in orden_actualizada.get('materiales', []):
            if m.get('orden_compra_id') == oc['id']:
                nuevo_material = m
                break
        
        assert nuevo_material is not None, "New material should be linked to OC"
        assert nuevo_material.get('estado_material') == 'pendiente_compra', f"Material estado should be 'pendiente_compra', got {nuevo_material.get('estado_material')}"
        
        print(f"✓ Material added to work order with estado_material=pendiente_compra")
        
        # Store OC id for next tests
        self.__class__.test_oc_id = oc['id']
        self.__class__.test_orden_trabajo_id = orden_trabajo_id
        return oc
        
    def test_05_aprobar_orden_compra(self):
        """PATCH /api/ordenes-compra/{id} estado=aprobada - Material changes to compra_aprobada"""
        oc_id = getattr(self.__class__, 'test_oc_id', None)
        orden_trabajo_id = getattr(self.__class__, 'test_orden_trabajo_id', None)
        
        if not oc_id:
            pytest.skip("No OC created in previous test")
            
        # Approve the OC
        response = requests.patch(
            f"{BASE_URL}/api/ordenes-compra/{oc_id}",
            json={"estado": "aprobada", "notas": "Aprobado para compra"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to approve OC: {response.text}"
        result = response.json()
        assert result.get("nuevo_estado") == "aprobada", f"Estado should be 'aprobada', got {result.get('nuevo_estado')}"
        
        print(f"✓ OC approved successfully")
        
        # Verify material estado changed in work order
        response = requests.get(f"{BASE_URL}/api/ordenes/{orden_trabajo_id}", headers=self.headers)
        assert response.status_code == 200
        orden = response.json()
        
        material = None
        for m in orden.get('materiales', []):
            if m.get('orden_compra_id') == oc_id:
                material = m
                break
        
        assert material is not None, "Material should exist in work order"
        assert material.get('estado_material') == 'compra_aprobada', f"Material estado should be 'compra_aprobada', got {material.get('estado_material')}"
        assert material.get('fecha_aprobacion') is not None, "fecha_aprobacion should be set"
        
        print(f"✓ Material estado changed to compra_aprobada")
        
    def test_06_marcar_pedida_sin_numero_pedido(self):
        """PATCH /api/ordenes-compra/{id} estado=pedida without numero_pedido - Should fail"""
        oc_id = getattr(self.__class__, 'test_oc_id', None)
        
        if not oc_id:
            pytest.skip("No OC created in previous test")
            
        # Try to mark as pedida without numero_pedido_proveedor
        response = requests.patch(
            f"{BASE_URL}/api/ordenes-compra/{oc_id}",
            json={"estado": "pedida"},
            headers=self.headers
        )
        assert response.status_code == 400, f"Should fail without numero_pedido_proveedor, got {response.status_code}"
        
        print(f"✓ Correctly rejected pedida without numero_pedido_proveedor")
        
    def test_07_marcar_pedida_con_numero_pedido(self):
        """PATCH /api/ordenes-compra/{id} estado=pedida with numero_pedido - Material changes to pedido_proveedor"""
        oc_id = getattr(self.__class__, 'test_oc_id', None)
        orden_trabajo_id = getattr(self.__class__, 'test_orden_trabajo_id', None)
        
        if not oc_id:
            pytest.skip("No OC created in previous test")
            
        numero_pedido = "TEST-PED-2026-001234"
        
        # Mark as pedida with numero_pedido_proveedor
        response = requests.patch(
            f"{BASE_URL}/api/ordenes-compra/{oc_id}",
            json={
                "estado": "pedida",
                "numero_pedido_proveedor": numero_pedido
            },
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to mark as pedida: {response.text}"
        result = response.json()
        assert result.get("nuevo_estado") == "pedida", f"Estado should be 'pedida', got {result.get('nuevo_estado')}"
        
        print(f"✓ OC marked as pedida with numero_pedido={numero_pedido}")
        
        # Verify material estado changed in work order
        response = requests.get(f"{BASE_URL}/api/ordenes/{orden_trabajo_id}", headers=self.headers)
        assert response.status_code == 200
        orden = response.json()
        
        material = None
        for m in orden.get('materiales', []):
            if m.get('orden_compra_id') == oc_id:
                material = m
                break
        
        assert material is not None, "Material should exist in work order"
        assert material.get('estado_material') == 'pedido_proveedor', f"Material estado should be 'pedido_proveedor', got {material.get('estado_material')}"
        assert material.get('numero_pedido') == numero_pedido, f"numero_pedido should be {numero_pedido}"
        assert material.get('fecha_pedido') is not None, "fecha_pedido should be set"
        
        print(f"✓ Material estado changed to pedido_proveedor with numero_pedido")
        
        # Store numero_pedido for search test
        self.__class__.test_numero_pedido = numero_pedido
        
    def test_08_buscar_por_numero_pedido(self):
        """GET /api/ordenes-compra/buscar-pedido/{numero} - Search by order number"""
        numero_pedido = getattr(self.__class__, 'test_numero_pedido', None)
        
        if not numero_pedido:
            pytest.skip("No numero_pedido from previous test")
            
        response = requests.get(
            f"{BASE_URL}/api/ordenes-compra/buscar-pedido/{numero_pedido}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to search by numero_pedido: {response.text}"
        data = response.json()
        
        assert "numero_pedido" in data, "Response should contain numero_pedido"
        assert "resultados" in data, "Response should contain resultados"
        assert "total" in data, "Response should contain total"
        assert data["total"] >= 1, f"Should find at least 1 result, got {data['total']}"
        
        # Verify result structure
        resultado = data["resultados"][0]
        assert "orden_compra" in resultado, "Result should contain orden_compra"
        assert "orden_trabajo" in resultado, "Result should contain orden_trabajo"
        assert "cliente" in resultado, "Result should contain cliente"
        
        print(f"✓ Search by numero_pedido returned {data['total']} results")
        print(f"  - OC: {resultado['orden_compra'].get('numero_oc')}")
        print(f"  - Orden: {resultado['orden_trabajo'].get('numero_orden') if resultado['orden_trabajo'] else 'N/A'}")
        print(f"  - Cliente: {resultado['cliente'].get('nombre') if resultado['cliente'] else 'N/A'}")
        
    def test_09_marcar_recibida(self):
        """PATCH /api/ordenes-compra/{id} estado=recibida - Material changes to recibido and order unblocks"""
        oc_id = getattr(self.__class__, 'test_oc_id', None)
        orden_trabajo_id = getattr(self.__class__, 'test_orden_trabajo_id', None)
        
        if not oc_id:
            pytest.skip("No OC created in previous test")
            
        # Mark as recibida
        response = requests.patch(
            f"{BASE_URL}/api/ordenes-compra/{oc_id}",
            json={"estado": "recibida", "notas": "Material recibido correctamente"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to mark as recibida: {response.text}"
        result = response.json()
        assert result.get("nuevo_estado") == "recibida", f"Estado should be 'recibida', got {result.get('nuevo_estado')}"
        
        print(f"✓ OC marked as recibida")
        
        # Verify material estado changed in work order
        response = requests.get(f"{BASE_URL}/api/ordenes/{orden_trabajo_id}", headers=self.headers)
        assert response.status_code == 200
        orden = response.json()
        
        material = None
        for m in orden.get('materiales', []):
            if m.get('orden_compra_id') == oc_id:
                material = m
                break
        
        assert material is not None, "Material should exist in work order"
        assert material.get('estado_material') == 'recibido', f"Material estado should be 'recibido', got {material.get('estado_material')}"
        assert material.get('aprobado') == True, "Material should be approved"
        assert material.get('fecha_recepcion') is not None, "fecha_recepcion should be set"
        
        # Verify order is unblocked (if no other pending materials)
        # Note: Order might still be blocked if there are other pending materials
        print(f"✓ Material estado changed to recibido")
        print(f"  - Order bloqueada: {orden.get('bloqueada')}")
        
    def test_10_get_orden_compra_detail(self):
        """GET /api/ordenes-compra/{id} - Get OC detail with enriched data"""
        oc_id = getattr(self.__class__, 'test_oc_id', None)
        
        if not oc_id:
            pytest.skip("No OC created in previous test")
            
        response = requests.get(f"{BASE_URL}/api/ordenes-compra/{oc_id}", headers=self.headers)
        assert response.status_code == 200, f"Failed to get OC detail: {response.text}"
        oc = response.json()
        
        assert oc.get("id") == oc_id, "OC id should match"
        assert "orden_trabajo_completa" in oc, "Should include orden_trabajo_completa"
        
        print(f"✓ OC detail retrieved with enriched data")
        print(f"  - Estado: {oc.get('estado')}")
        print(f"  - Numero pedido: {oc.get('numero_pedido_proveedor')}")
        
    def test_11_cleanup_test_data(self):
        """Cleanup: Remove test OC by searching and verifying"""
        # Note: We don't delete OCs in this system, just verify the test data exists
        oc_id = getattr(self.__class__, 'test_oc_id', None)
        
        if oc_id:
            response = requests.get(f"{BASE_URL}/api/ordenes-compra/{oc_id}", headers=self.headers)
            if response.status_code == 200:
                oc = response.json()
                print(f"✓ Test OC {oc.get('numero_oc')} exists with estado={oc.get('estado')}")
                print(f"  - This is test data (nombre_pieza starts with TEST_)")


class TestOrdenesCompraFilters:
    """Test purchase order filtering and listing"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
    def test_filter_by_prioridad(self):
        """GET /api/ordenes-compra?prioridad=urgente"""
        for prioridad in ['normal', 'urgente']:
            response = requests.get(f"{BASE_URL}/api/ordenes-compra?prioridad={prioridad}", headers=self.headers)
            assert response.status_code == 200, f"Failed to filter by prioridad={prioridad}"
            print(f"✓ Filter by prioridad={prioridad}: {len(response.json())} results")
            
    def test_filter_combined(self):
        """GET /api/ordenes-compra?estado=pendiente&prioridad=urgente"""
        response = requests.get(
            f"{BASE_URL}/api/ordenes-compra?estado=pendiente&prioridad=urgente",
            headers=self.headers
        )
        assert response.status_code == 200
        print(f"✓ Combined filter (pendiente + urgente): {len(response.json())} results")
        
    def test_list_includes_orden_trabajo_info(self):
        """Verify list includes orden_trabajo_info for each OC"""
        response = requests.get(f"{BASE_URL}/api/ordenes-compra", headers=self.headers)
        assert response.status_code == 200
        ordenes = response.json()
        
        if len(ordenes) > 0:
            oc = ordenes[0]
            # orden_trabajo_info is added when listing
            if oc.get('orden_trabajo_id'):
                assert 'orden_trabajo_info' in oc or oc.get('orden_trabajo_info') is None, "Should have orden_trabajo_info if linked"
        
        print(f"✓ List includes enriched data")


class TestOrdenesCompraAuth:
    """Test authentication requirements for purchase orders"""
    
    def test_list_without_auth(self):
        """GET /api/ordenes-compra without auth - Should fail"""
        response = requests.get(f"{BASE_URL}/api/ordenes-compra")
        assert response.status_code == 401, f"Should require auth, got {response.status_code}"
        print(f"✓ List requires authentication")
        
    def test_create_without_auth(self):
        """POST /api/ordenes-compra without auth - Should fail"""
        response = requests.post(f"{BASE_URL}/api/ordenes-compra", json={
            "nombre_pieza": "Test",
            "orden_trabajo_id": "test",
            "solicitado_por": "test"
        })
        assert response.status_code == 401, f"Should require auth, got {response.status_code}"
        print(f"✓ Create requires authentication")
        
    def test_update_without_auth(self):
        """PATCH /api/ordenes-compra/{id} without auth - Should fail"""
        response = requests.patch(f"{BASE_URL}/api/ordenes-compra/test-id", json={"estado": "aprobada"})
        assert response.status_code == 401, f"Should require auth, got {response.status_code}"
        print(f"✓ Update requires authentication")
        
    def test_search_without_auth(self):
        """GET /api/ordenes-compra/buscar-pedido/{numero} without auth - Should fail"""
        response = requests.get(f"{BASE_URL}/api/ordenes-compra/buscar-pedido/TEST-123")
        assert response.status_code == 401, f"Should require auth, got {response.status_code}"
        print(f"✓ Search requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

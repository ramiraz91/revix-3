"""
Iteration 15: Email Agent Feature Tests
- Tests for /api/agente/* endpoints
- Tests for /api/pre-registros endpoints  
- Tests for /api/notificaciones-externas endpoints
- Role-based access control (master vs admin)
- Classifier unit tests
"""
import pytest
import requests
import os
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MASTER_CREDENTIALS = {"email": "master@techrepair.local", "password": "master123"}
ADMIN_CREDENTIALS = {"email": "admin@techrepair.local", "password": "admin123"}


@pytest.fixture(scope="module")
def master_token():
    """Get master authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MASTER_CREDENTIALS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.fail(f"Master login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.fail(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture
def master_client(master_token):
    """Requests session with master auth"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {master_token}"
    })
    return session


@pytest.fixture
def admin_client(admin_token):
    """Requests session with admin auth"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return session


class TestAgentStatus:
    """Test /api/agente/status endpoint"""
    
    def test_status_returns_running_and_stats(self, admin_client):
        """GET /api/agente/status should return running status, estado, and stats"""
        response = admin_client.get(f"{BASE_URL}/api/agente/status")
        assert response.status_code == 200, f"Status failed: {response.text}"
        
        data = response.json()
        assert "running" in data, "Missing 'running' field"
        assert "estado" in data, "Missing 'estado' field"
        assert "stats" in data, "Missing 'stats' field"
        
        # Verify stats structure
        stats = data["stats"]
        assert "pre_registros_total" in stats
        assert "pre_registros_pendientes" in stats
        assert "ordenes_creadas_agente" in stats
        assert "eventos_en_consolidacion" in stats
        assert "notificaciones_externas" in stats
        assert "notif_ext_no_leidas" in stats
        print(f"Agent status: running={data['running']}, estado={data['estado']}")
        
    def test_status_requires_auth(self):
        """GET /api/agente/status requires authentication"""
        response = requests.get(f"{BASE_URL}/api/agente/status")
        assert response.status_code == 401


class TestAgentConfig:
    """Test /api/agente/config endpoint - master only"""
    
    def test_config_get_master(self, master_client):
        """GET /api/agente/config by master should work"""
        response = master_client.get(f"{BASE_URL}/api/agente/config")
        assert response.status_code == 200, f"Config GET failed: {response.text}"
        
        data = response.json()
        # First time may not be configured
        assert "configurado" in data or "datos" in data
        print(f"Config response: configurado={data.get('configurado')}")
        
    def test_config_post_master(self, master_client):
        """POST /api/agente/config by master should save config with masked passwords"""
        config_data = {
            "imap_host": "mail.test.local",
            "imap_port": 993,
            "imap_user": "test@test.local",
            "imap_password": "test_password_123",
            "imap_ssl": True,
            "imap_folder": "INBOX",
            "poll_interval": 180,
            "estado": "pausado"
        }
        
        response = master_client.post(f"{BASE_URL}/api/agente/config", json=config_data)
        assert response.status_code == 200, f"Config POST failed: {response.text}"
        assert "message" in response.json()
        
        # Verify GET returns masked password
        get_response = master_client.get(f"{BASE_URL}/api/agente/config")
        assert get_response.status_code == 200
        datos = get_response.json().get("datos", {})
        
        # Password should be masked
        if datos.get("imap_password"):
            assert datos["imap_password"] == "***configured***", "Password not masked"
            print("Password correctly masked as ***configured***")
        
        assert datos.get("imap_host") == "mail.test.local"
        assert datos.get("poll_interval") == 180
        
    def test_config_admin_forbidden(self, admin_client):
        """POST /api/agente/config by admin should return 403"""
        config_data = {"imap_host": "hacked.server.com"}
        response = admin_client.post(f"{BASE_URL}/api/agente/config", json=config_data)
        assert response.status_code == 403, f"Expected 403 for admin, got {response.status_code}"
        print("Admin correctly denied access to config POST")
        
    def test_config_get_admin_forbidden(self, admin_client):
        """GET /api/agente/config by admin should return 403 (master only)"""
        response = admin_client.get(f"{BASE_URL}/api/agente/config")
        assert response.status_code == 403, f"Expected 403 for admin GET config, got {response.status_code}"


class TestAgentControls:
    """Test /api/agente/start, /api/agente/stop, /api/agente/poll-now"""
    
    def test_start_agent_master(self, master_client):
        """POST /api/agente/start by master should work"""
        response = master_client.post(f"{BASE_URL}/api/agente/start")
        assert response.status_code == 200, f"Start failed: {response.text}"
        data = response.json()
        assert "message" in data
        assert "running" in data
        print(f"Agent start response: {data['message']}")
        
    def test_stop_agent_master(self, master_client):
        """POST /api/agente/stop by master should work"""
        response = master_client.post(f"{BASE_URL}/api/agente/stop")
        assert response.status_code == 200, f"Stop failed: {response.text}"
        data = response.json()
        assert "message" in data
        assert data["running"] == False
        print(f"Agent stop response: {data['message']}")
        
    def test_poll_now_master(self, master_client):
        """POST /api/agente/poll-now by master executes poll cycle"""
        # First stop agent to ensure clean state
        master_client.post(f"{BASE_URL}/api/agente/stop")
        
        response = master_client.post(f"{BASE_URL}/api/agente/poll-now")
        # This may succeed or fail depending on IMAP config
        # But it should not return 403 for master
        assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            print("Poll cycle executed successfully")
        else:
            print(f"Poll cycle failed (expected - no real IMAP): {response.json().get('detail')}")
            
    def test_controls_admin_forbidden(self, admin_client):
        """Agent controls should return 403 for admin"""
        # Start
        response = admin_client.post(f"{BASE_URL}/api/agente/start")
        assert response.status_code == 403, f"Start should be forbidden for admin"
        
        # Stop
        response = admin_client.post(f"{BASE_URL}/api/agente/stop")
        assert response.status_code == 403, f"Stop should be forbidden for admin"
        
        # Poll-now
        response = admin_client.post(f"{BASE_URL}/api/agente/poll-now")
        assert response.status_code == 403, f"Poll-now should be forbidden for admin"
        
        print("Admin correctly denied access to all agent controls")


class TestPreRegistros:
    """Test /api/pre-registros endpoints"""
    
    def test_list_pre_registros_empty(self, admin_client):
        """GET /api/pre-registros should return empty list (DB was cleaned)"""
        response = admin_client.get(f"{BASE_URL}/api/pre-registros")
        assert response.status_code == 200, f"List failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list response"
        print(f"Pre-registros count: {len(data)}")
        
    def test_list_with_estado_filter(self, admin_client):
        """GET /api/pre-registros?estado=pendiente_presupuesto should filter by estado"""
        response = admin_client.get(f"{BASE_URL}/api/pre-registros", 
                                     params={"estado": "pendiente_presupuesto"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned items should have the filtered estado
        for item in data:
            assert item.get("estado") == "pendiente_presupuesto"
            
    def test_list_with_search_filter(self, admin_client):
        """GET /api/pre-registros?search=XYZ should filter by search"""
        response = admin_client.get(f"{BASE_URL}/api/pre-registros", 
                                     params={"search": "26BE000001"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Results should match the search term in codigo or subject
        for item in data:
            matches = ("26BE000001" in item.get("codigo_siniestro", "") or 
                      "26BE000001" in item.get("email_subject", ""))
            assert matches or len(data) == 0  # Either matches or empty results


class TestNotificacionesExternas:
    """Test /api/notificaciones-externas endpoints"""
    
    def test_list_notificaciones(self, admin_client):
        """GET /api/notificaciones-externas should return list"""
        response = admin_client.get(f"{BASE_URL}/api/notificaciones-externas")
        assert response.status_code == 200, f"List failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Notificaciones externas count: {len(data)}")
        
    def test_list_with_severidad_filter(self, admin_client):
        """GET /api/notificaciones-externas?severidad=critical should filter"""
        response = admin_client.get(f"{BASE_URL}/api/notificaciones-externas",
                                     params={"severidad": "critical"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for item in data:
            assert item.get("severidad") == "critical"
            
    def test_list_with_orden_id_filter(self, admin_client):
        """GET /api/notificaciones-externas?orden_id=xxx should filter by orden"""
        response = admin_client.get(f"{BASE_URL}/api/notificaciones-externas",
                                     params={"orden_id": "nonexistent-id"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0  # No notifications for nonexistent order
        
    def test_resumen_notificaciones(self, admin_client):
        """GET /api/notificaciones-externas/resumen should return count by severidad"""
        response = admin_client.get(f"{BASE_URL}/api/notificaciones-externas/resumen")
        assert response.status_code == 200, f"Resumen failed: {response.text}"
        data = response.json()
        
        # Should have counts for each severity
        assert "info" in data, "Missing 'info' count"
        assert "warning" in data, "Missing 'warning' count"
        assert "critical" in data, "Missing 'critical' count"
        assert "total" in data, "Missing 'total' count"
        
        # Counts should be non-negative integers
        assert isinstance(data["info"], int) and data["info"] >= 0
        assert isinstance(data["warning"], int) and data["warning"] >= 0
        assert isinstance(data["critical"], int) and data["critical"] >= 0
        assert isinstance(data["total"], int) and data["total"] >= 0
        
        print(f"Resumen: info={data['info']}, warning={data['warning']}, "
              f"critical={data['critical']}, total={data['total']}")


class TestClassifierUnit:
    """Unit tests for email classifier (9 email types)"""
    
    def test_classify_nuevo_siniestro(self):
        """Test classification of nuevo siniestro emails"""
        # Import the classifier
        import sys
        sys.path.insert(0, '/app/backend')
        from agent.classifier import classify_email, TipoEventoEmail
        
        # Test subject with "nuevo siniestro"
        tipo, severidad = classify_email("Nuevo Siniestro 26BE000001", "Se ha creado un nuevo siniestro")
        assert tipo == TipoEventoEmail.NUEVO_SINIESTRO, f"Expected NUEVO_SINIESTRO, got {tipo}"
        print("✓ nuevo siniestro classification correct")
        
    def test_classify_presupuesto_aceptado(self):
        """Test classification of accepted quotation emails"""
        import sys
        sys.path.insert(0, '/app/backend')
        from agent.classifier import classify_email, TipoEventoEmail
        
        tipo, severidad = classify_email("Presupuesto Aceptado", "El presupuesto ha sido aceptado")
        assert tipo == TipoEventoEmail.PRESUPUESTO_ACEPTADO, f"Expected PRESUPUESTO_ACEPTADO, got {tipo}"
        print("✓ presupuesto aceptado classification correct")
        
    def test_classify_presupuesto_rechazado(self):
        """Test classification of rejected quotation emails"""
        import sys
        sys.path.insert(0, '/app/backend')
        from agent.classifier import classify_email, TipoEventoEmail
        
        tipo, severidad = classify_email("Presupuesto Rechazado", "El presupuesto ha sido rechazado")
        assert tipo == TipoEventoEmail.PRESUPUESTO_RECHAZADO, f"Expected PRESUPUESTO_RECHAZADO, got {tipo}"
        print("✓ presupuesto rechazado classification correct")
        
    def test_classify_imagenes_faltantes(self):
        """Test classification of missing images emails"""
        import sys
        sys.path.insert(0, '/app/backend')
        from agent.classifier import classify_email, TipoEventoEmail, SeveridadNotificacion
        
        tipo, severidad = classify_email("Imágenes faltantes", "Necesitamos las fotos del dispositivo")
        assert tipo == TipoEventoEmail.IMAGENES_FALTANTES, f"Expected IMAGENES_FALTANTES, got {tipo}"
        assert severidad == SeveridadNotificacion.WARNING, f"Expected WARNING severity"
        print("✓ imagenes faltantes classification correct")
        
    def test_classify_documentacion_faltante(self):
        """Test classification of missing documentation emails"""
        import sys
        sys.path.insert(0, '/app/backend')
        from agent.classifier import classify_email, TipoEventoEmail
        
        tipo, severidad = classify_email("Documentación pendiente", "Falta documentación para procesar")
        assert tipo == TipoEventoEmail.DOCUMENTACION_FALTANTE, f"Expected DOCUMENTACION_FALTANTE, got {tipo}"
        print("✓ documentacion faltante classification correct")
        
    def test_classify_sla_24h(self):
        """Test classification of 24h SLA warning emails"""
        import sys
        sys.path.insert(0, '/app/backend')
        from agent.classifier import classify_email, TipoEventoEmail, SeveridadNotificacion
        
        tipo, severidad = classify_email("Aviso 24h", "Tiene 24 horas para responder")
        assert tipo == TipoEventoEmail.SLA_24H, f"Expected SLA_24H, got {tipo}"
        assert severidad == SeveridadNotificacion.WARNING
        print("✓ sla_24h classification correct")
        
    def test_classify_sla_48h(self):
        """Test classification of 48h SLA critical emails"""
        import sys
        sys.path.insert(0, '/app/backend')
        from agent.classifier import classify_email, TipoEventoEmail, SeveridadNotificacion
        
        tipo, severidad = classify_email("Último aviso 48h", "Solo tiene 48 horas, urgente")
        assert tipo == TipoEventoEmail.SLA_48H, f"Expected SLA_48H, got {tipo}"
        assert severidad == SeveridadNotificacion.CRITICAL
        print("✓ sla_48h classification correct")
        
    def test_classify_recordatorio(self):
        """Test classification of reminder emails"""
        import sys
        sys.path.insert(0, '/app/backend')
        from agent.classifier import classify_email, TipoEventoEmail
        
        tipo, severidad = classify_email("Recordatorio", "Le recordamos que tiene acciones pendientes")
        assert tipo == TipoEventoEmail.RECORDATORIO, f"Expected RECORDATORIO, got {tipo}"
        print("✓ recordatorio classification correct")
        
    def test_classify_incidencia_proveedor(self):
        """Test classification of provider incident emails"""
        import sys
        sys.path.insert(0, '/app/backend')
        from agent.classifier import classify_email, TipoEventoEmail, SeveridadNotificacion
        
        tipo, severidad = classify_email("Incidencia en servicio", "Se ha detectado una incidencia")
        assert tipo == TipoEventoEmail.INCIDENCIA_PROVEEDOR, f"Expected INCIDENCIA_PROVEEDOR, got {tipo}"
        assert severidad == SeveridadNotificacion.CRITICAL
        print("✓ incidencia proveedor classification correct")
        
    def test_extract_codigo_siniestro(self):
        """Test extraction of codigo_siniestro from email text"""
        import sys
        sys.path.insert(0, '/app/backend')
        from agent.classifier import extract_codigo_siniestro
        
        # Test default pattern (e.g., 26BE000534)
        text = "Nuevo siniestro 26BE000534 ha sido creado"
        codigo = extract_codigo_siniestro(text)
        assert codigo == "26BE000534", f"Expected 26BE000534, got {codigo}"
        
        # Test no match
        text = "Email sin código"
        codigo = extract_codigo_siniestro(text)
        assert codigo is None
        
        print("✓ codigo_siniestro extraction correct")


class TestImapConnection:
    """Test IMAP test endpoint (expected to fail without real server)"""
    
    def test_imap_test_no_config(self, master_client):
        """POST /api/agente/test-imap should fail gracefully without config"""
        # First ensure config has no valid IMAP server
        master_client.post(f"{BASE_URL}/api/agente/config", json={
            "imap_host": "",
            "imap_user": "",
            "estado": "pausado"
        })
        
        response = master_client.post(f"{BASE_URL}/api/agente/test-imap")
        # Should return 400 (not configured) or connection error
        assert response.status_code in [400, 500], f"Unexpected status: {response.status_code}"
        print(f"IMAP test correctly failed (expected): {response.json()}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

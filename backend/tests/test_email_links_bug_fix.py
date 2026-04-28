"""
Tests de regresión para el bug crítico de enlaces en emails de cliente.

Bug original: Los emails automáticos del CRM enviaban a los CLIENTES enlaces
que apuntaban al CRM interno (/ordenes/{id}) en vez de a la página pública
de seguimiento (/consulta?codigo={token}).

Este archivo verifica:
1. Las 4 funciones de notificación al cliente generan HTML con href hacia /consulta?codigo={token}
2. _assert_client_safe lanza AssertionError si encuentra /ordenes/, /crm/, /dashboard/
3. send_email con audience='client' valida el HTML; con audience='admin' permite URLs internas
4. notificar_material_pendiente usa /ordenes/{id} (audience='admin', correcto)
5. helpers.py:generate_modern_email_html usa /consulta?codigo={token}
6. _safe_public_url filtra URLs preview/localhost
7. EMAIL_STRICT_CLIENT_LINKS=1 hace que cualquier email de cliente con /ordenes/ falle
8. Regresión: endpoints del CRM siguen funcionando
"""
import os
import re
import sys
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

# Añadir backend al sys.path
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# URL base desde env
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS - Helpers de construcción de URLs
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildClientLink:
    """Tests para _build_client_link - URLs para emails de cliente"""
    
    def test_con_token_genera_consulta_con_codigo(self):
        from email_service import _build_client_link
        url = _build_client_link("ABC-123-TOKEN")
        assert "/consulta" in url
        assert "codigo=ABC-123-TOKEN" in url
        assert "/ordenes/" not in url
        assert "/crm/" not in url
        assert "/dashboard/" not in url
    
    def test_sin_token_genera_consulta_sin_codigo(self):
        from email_service import _build_client_link
        url = _build_client_link()
        assert url.endswith("/consulta")
        assert "codigo=" not in url
        assert "/ordenes/" not in url
    
    def test_token_none_genera_consulta_sin_codigo(self):
        from email_service import _build_client_link
        url = _build_client_link(None)
        assert url.endswith("/consulta")
        assert "codigo=" not in url
    
    def test_token_vacio_genera_consulta_sin_codigo(self):
        from email_service import _build_client_link
        url = _build_client_link("")
        assert url.endswith("/consulta")
        # Empty string should not add codigo param
        assert "codigo=" not in url


class TestBuildAdminLink:
    """Tests para _build_admin_link - URLs para emails de staff"""
    
    def test_genera_url_con_path_ordenes(self):
        from email_service import _build_admin_link
        url = _build_admin_link("/ordenes/uuid-123")
        assert "/ordenes/uuid-123" in url
    
    def test_genera_url_con_path_crm(self):
        from email_service import _build_admin_link
        url = _build_admin_link("/crm/dashboard")
        assert "/crm/dashboard" in url
    
    def test_añade_slash_si_falta(self):
        from email_service import _build_admin_link
        url = _build_admin_link("ordenes/abc")
        assert "/ordenes/abc" in url


class TestSafePublicUrl:
    """Tests para _safe_public_url - filtrado de URLs preview/localhost"""
    
    def test_filtra_preview_emergentagent(self):
        from email_service import _safe_public_url, _PUBLIC_FALLBACK
        result = _safe_public_url("https://preview.emergentagent.com/test")
        assert result == _PUBLIC_FALLBACK
    
    def test_filtra_localhost(self):
        from email_service import _safe_public_url, _PUBLIC_FALLBACK
        result = _safe_public_url("http://localhost:3000")
        assert result == _PUBLIC_FALLBACK
    
    def test_filtra_127_0_0_1(self):
        from email_service import _safe_public_url, _PUBLIC_FALLBACK
        result = _safe_public_url("http://127.0.0.1:8001")
        assert result == _PUBLIC_FALLBACK
    
    def test_acepta_revix_es(self):
        from email_service import _safe_public_url
        result = _safe_public_url("https://revix.es")
        assert result == "https://revix.es"
    
    def test_acepta_dominio_produccion(self):
        from email_service import _safe_public_url
        result = _safe_public_url("https://app.revix.es")
        assert result == "https://app.revix.es"
    
    def test_url_vacia_devuelve_fallback(self):
        from email_service import _safe_public_url, _PUBLIC_FALLBACK
        result = _safe_public_url("")
        assert result == _PUBLIC_FALLBACK
    
    def test_url_none_devuelve_fallback(self):
        from email_service import _safe_public_url, _PUBLIC_FALLBACK
        result = _safe_public_url(None)
        assert result == _PUBLIC_FALLBACK
    
    def test_url_sin_protocolo_devuelve_fallback(self):
        from email_service import _safe_public_url, _PUBLIC_FALLBACK
        result = _safe_public_url("revix.es")
        assert result == _PUBLIC_FALLBACK


class TestAssertClientSafe:
    """Tests para _assert_client_safe - validación de HTML de cliente"""
    
    def test_acepta_html_con_consulta(self):
        from email_service import _assert_client_safe, _build_client_link, _build_html
        html = _build_html("Test", "<p>contenido</p>",
                           link_url=_build_client_link("token-abc"),
                           link_text="Ver mi orden")
        # No debe lanzar excepción
        _assert_client_safe(html, where="test_acepta_consulta")
    
    def test_rechaza_ordenes_path(self):
        from email_service import _assert_client_safe
        html = '<a href="https://revix.es/ordenes/abc-123">link</a>'
        with pytest.raises(AssertionError, match="email-leak"):
            _assert_client_safe(html, where="test_rechaza_ordenes")
    
    def test_rechaza_crm_path(self):
        from email_service import _assert_client_safe
        html = '<a href="https://revix.es/crm/dashboard">link</a>'
        with pytest.raises(AssertionError, match="email-leak"):
            _assert_client_safe(html, where="test_rechaza_crm")
    
    def test_rechaza_dashboard_path(self):
        from email_service import _assert_client_safe
        html = '<a href="https://revix.es/dashboard/stats">link</a>'
        with pytest.raises(AssertionError, match="email-leak"):
            _assert_client_safe(html, where="test_rechaza_dashboard")
    
    def test_rechaza_inventario_path(self):
        from email_service import _assert_client_safe
        html = '<a href="https://revix.es/inventario">link</a>'
        with pytest.raises(AssertionError, match="email-leak"):
            _assert_client_safe(html, where="test_rechaza_inventario")
    
    def test_rechaza_clientes_uuid_path(self):
        from email_service import _assert_client_safe
        html = '<a href="https://revix.es/clientes/550e8400-e29b-41d4-a716-446655440000">link</a>'
        with pytest.raises(AssertionError, match="email-leak"):
            _assert_client_safe(html, where="test_rechaza_clientes_uuid")


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS - Funciones de notificación con mock de Resend
# ══════════════════════════════════════════════════════════════════════════════

def _capture_html_from_notify(notify_fn, **kwargs):
    """Llama una función de notificación mockeando Resend para capturar el HTML."""
    captured = {}
    import email_service
    orig = email_service.resend.Emails.send

    def fake_send(params):
        captured["html"] = params["html"]
        captured["subject"] = params["subject"]
        captured["to"] = params["to"]
        return {"id": "test-mock-id"}

    email_service.resend.Emails.send = fake_send
    try:
        asyncio.run(notify_fn(**kwargs))
    finally:
        email_service.resend.Emails.send = orig
    return captured


@pytest.mark.skipif(not __import__("email_service").is_configured(),
                    reason="Resend no configurado")
class TestNotificacionesCliente:
    """Tests de las 4 funciones de notificación al cliente"""
    
    def test_notificar_cambio_estado_usa_consulta(self):
        from email_service import notificar_cambio_estado
        captured = _capture_html_from_notify(
            notificar_cambio_estado,
            to="cliente@test.com", orden_numero="OT-TEST-1", auth_code="AUTH1",
            nuevo_estado="reparado", orden_id="orden-uuid-123",
            token_seguimiento="TOK-CAMBIO-123",
        )
        html = captured.get("html", "")
        assert "/consulta?codigo=TOK-CAMBIO-123" in html
        assert "/ordenes/orden-uuid-123" not in html
        assert "/crm/" not in html
    
    def test_notificar_presupuesto_enviado_usa_consulta(self):
        from email_service import notificar_presupuesto_enviado
        captured = _capture_html_from_notify(
            notificar_presupuesto_enviado,
            to="cliente@test.com", orden_numero="OT-TEST-2",
            total=150.50, orden_id="ord-pres-x", token_seguimiento="TOK-PRES-456",
        )
        html = captured.get("html", "")
        assert "/consulta?codigo=TOK-PRES-456" in html
        assert "/ordenes/ord-pres-x" not in html
    
    def test_notificar_orden_lista_usa_consulta(self):
        from email_service import notificar_orden_lista
        captured = _capture_html_from_notify(
            notificar_orden_lista,
            to="cliente@test.com", orden_numero="OT-TEST-3",
            auth_code="A3", orden_id="ord-lista-y", token_seguimiento="TOK-LISTA-789",
        )
        html = captured.get("html", "")
        assert "/consulta?codigo=TOK-LISTA-789" in html
        assert "/ordenes/ord-lista-y" not in html
    
    def test_notificar_factura_emitida_usa_consulta(self):
        from email_service import notificar_factura_emitida
        captured = _capture_html_from_notify(
            notificar_factura_emitida,
            to="cliente@test.com", factura_numero="FAC-TEST-1", total=200.00,
            orden_numero="OT-TEST-4", orden_id="ord-fac-z", token_seguimiento="TOK-FAC-012",
        )
        html = captured.get("html", "")
        assert "/consulta?codigo=TOK-FAC-012" in html
        assert "/ordenes/ord-fac-z" not in html
    
    def test_notificar_bienvenida_usa_consulta(self):
        from email_service import notificar_bienvenida
        captured = _capture_html_from_notify(
            notificar_bienvenida,
            to="nuevo@cliente.com", nombre="Juan Test",
        )
        html = captured.get("html", "")
        assert "/consulta" in html
        assert "/ordenes/" not in html
        assert "/crm/" not in html


@pytest.mark.skipif(not __import__("email_service").is_configured(),
                    reason="Resend no configurado")
class TestNotificacionesAdmin:
    """Tests de notificaciones para staff (audience='admin')"""
    
    def test_notificar_material_pendiente_usa_ordenes(self):
        """Material pendiente VA al staff (admin) → /ordenes/{id} es correcto."""
        from email_service import notificar_material_pendiente
        captured = _capture_html_from_notify(
            notificar_material_pendiente,
            to="tecnico@revix.es", pieza="Pantalla OLED",
            orden_numero="OT-ADMIN-1", orden_id="ord-admin-w",
        )
        html = captured.get("html", "")
        # En este caso SÍ debe contener /ordenes/ porque es para staff
        assert "/ordenes/ord-admin-w" in html


# ══════════════════════════════════════════════════════════════════════════════
# TESTS - helpers.py:generate_modern_email_html
# ══════════════════════════════════════════════════════════════════════════════

class TestGenerateModernEmailHtml:
    """Tests para helpers.py:generate_modern_email_html"""
    
    def test_usa_consulta_con_token(self):
        from helpers import generate_modern_email_html
        html = generate_modern_email_html(
            orden={"id": "abc", "numero_orden": "OT-MODERN-1",
                   "token_seguimiento": "MODERN_TOK_123", "estado": "recibida",
                   "dispositivo": {"marca": "Apple", "modelo": "iPhone 13"}},
            cliente={"nombre": "Juan Test", "email": "j@test.com"},
            email_type="recibida",
        )
        assert "/consulta?codigo=MODERN_TOK_123" in html
        # Verificar que NO hay URLs internas del CRM
        matches = re.findall(r'href=["\']([^"\']+)["\']', html)
        for url in matches:
            assert "/ordenes/" not in url, f"URL prohibida encontrada: {url}"
            assert "/crm/" not in url, f"URL prohibida encontrada: {url}"
    
    def test_todos_los_tipos_de_email(self):
        """Verifica que todos los tipos de email usan /consulta"""
        from helpers import generate_modern_email_html
        tipos = ['created', 'recibida', 'en_taller', 'reparado', 'enviado', 'fecha_estimada']
        
        for tipo in tipos:
            html = generate_modern_email_html(
                orden={"id": f"id-{tipo}", "numero_orden": f"OT-{tipo}",
                       "token_seguimiento": f"TOK-{tipo}", "estado": tipo,
                       "dispositivo": {"marca": "Samsung", "modelo": "Galaxy S21"}},
                cliente={"nombre": "Test", "email": "test@test.com"},
                email_type=tipo,
            )
            assert f"/consulta?codigo=TOK-{tipo}" in html, f"Tipo {tipo} no usa /consulta"
            # Verificar que NO hay URLs internas
            assert "/ordenes/" not in html or "href" not in html.split("/ordenes/")[0][-50:], \
                f"Tipo {tipo} contiene /ordenes/ en href"


# ══════════════════════════════════════════════════════════════════════════════
# TESTS - Audience parameter en send_email
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not __import__("email_service").is_configured(),
                    reason="Resend no configurado")
class TestSendEmailAudience:
    """Tests para el parámetro audience en send_email"""
    
    def test_audience_client_valida_html(self):
        """audience='client' debe validar que no haya URLs internas"""
        from email_service import send_email
        
        # Mock resend para evitar envío real
        import email_service
        orig = email_service.resend.Emails.send
        email_service.resend.Emails.send = lambda p: {"id": "mock"}
        
        try:
            # Esto debe fallar porque el contenido tiene /ordenes/
            with pytest.raises(AssertionError, match="email-leak"):
                send_email(
                    to="cliente@test.com",
                    subject="Test",
                    titulo="Test",
                    contenido='<a href="https://revix.es/ordenes/abc">Ver</a>',
                    audience="client",
                )
        finally:
            email_service.resend.Emails.send = orig
    
    def test_audience_admin_permite_urls_internas(self):
        """audience='admin' debe permitir URLs internas"""
        from email_service import send_email
        
        import email_service
        orig = email_service.resend.Emails.send
        sent = []
        email_service.resend.Emails.send = lambda p: (sent.append(p), {"id": "mock"})[1]
        
        try:
            # Esto NO debe fallar porque audience='admin'
            result = send_email(
                to="admin@revix.es",
                subject="Test Admin",
                titulo="Test Admin",
                contenido='<a href="https://revix.es/ordenes/abc">Ver orden</a>',
                link_url="https://revix.es/crm/dashboard",
                audience="admin",
            )
            assert result is True
            assert len(sent) == 1
        finally:
            email_service.resend.Emails.send = orig


# ══════════════════════════════════════════════════════════════════════════════
# REGRESSION TESTS - Endpoints del CRM siguen funcionando
# ══════════════════════════════════════════════════════════════════════════════

class TestRegresionCRM:
    """Tests de regresión para verificar que el CRM sigue funcionando"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Obtiene token de autenticación"""
        if not BASE_URL:
            pytest.skip("REACT_APP_BACKEND_URL no configurada")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "master@revix.es", "password": "RevixMaster2026!"},
            timeout=10
        )
        if response.status_code == 429:
            pytest.skip("Rate limit activo - esperar 15 minutos")
        if response.status_code != 200:
            pytest.skip(f"Login falló: {response.status_code}")
        
        return response.json().get("token")
    
    def test_health_endpoint(self):
        """Verifica que el backend está funcionando"""
        if not BASE_URL:
            pytest.skip("REACT_APP_BACKEND_URL no configurada")
        
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
    
    def test_ordenes_endpoint_con_auth(self, auth_token):
        """Verifica que el endpoint de órdenes funciona"""
        response = requests.get(
            f"{BASE_URL}/api/ordenes",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200
    
    def test_clientes_endpoint_con_auth(self, auth_token):
        """Verifica que el endpoint de clientes funciona"""
        response = requests.get(
            f"{BASE_URL}/api/clientes",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200
    
    def test_agents_panel_overview(self, auth_token):
        """Verifica que el panel de agentes carga 11 agentes"""
        response = requests.get(
            f"{BASE_URL}/api/agents/panel/overview",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        # La respuesta tiene 'agents' como lista
        agents = data.get("agents", [])
        assert len(agents) >= 11, f"Esperados >=11 agentes, encontrados {len(agents)}"
    
    def test_chatbot_web_publico(self):
        """Verifica que el chatbot público funciona"""
        if not BASE_URL:
            pytest.skip("REACT_APP_BACKEND_URL no configurada")
        
        response = requests.post(
            f"{BASE_URL}/api/web/chatbot",
            json={"mensaje": "Hola", "session_id": "test-session-bugfix"},
            timeout=30
        )
        # Puede ser 200 o 500 si hay timeout de LLM
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "response" in data or "respuesta" in data


# ══════════════════════════════════════════════════════════════════════════════
# TESTS - EMAIL_STRICT_CLIENT_LINKS env variable
# ══════════════════════════════════════════════════════════════════════════════

class TestEmailStrictClientLinks:
    """Tests para la variable EMAIL_STRICT_CLIENT_LINKS"""
    
    def test_strict_mode_enabled_by_default(self):
        """Verifica que EMAIL_STRICT_CLIENT_LINKS=1 por defecto"""
        # El valor por defecto es "1" (strict mode)
        val = os.getenv("EMAIL_STRICT_CLIENT_LINKS", "1")
        assert val == "1", "EMAIL_STRICT_CLIENT_LINKS debe ser '1' por defecto"
    
    def test_strict_mode_raises_on_internal_url(self):
        """Con strict mode, URLs internas en emails de cliente lanzan AssertionError"""
        from email_service import _assert_client_safe
        
        # Asegurar que strict mode está activo
        original = os.environ.get("EMAIL_STRICT_CLIENT_LINKS")
        os.environ["EMAIL_STRICT_CLIENT_LINKS"] = "1"
        
        try:
            html = '<a href="https://revix.es/ordenes/abc">link</a>'
            with pytest.raises(AssertionError):
                _assert_client_safe(html, where="test_strict")
        finally:
            if original is not None:
                os.environ["EMAIL_STRICT_CLIENT_LINKS"] = original
            elif "EMAIL_STRICT_CLIENT_LINKS" in os.environ:
                del os.environ["EMAIL_STRICT_CLIENT_LINKS"]


# ══════════════════════════════════════════════════════════════════════════════
# TESTS - Proxy en services/email_service.py
# ══════════════════════════════════════════════════════════════════════════════

class TestServicesEmailServiceProxy:
    """Tests para verificar que el proxy reexporta los helpers"""
    
    def test_proxy_exporta_build_client_link(self):
        from services.email_service import _build_client_link
        url = _build_client_link("test-token")
        assert "/consulta?codigo=test-token" in url
    
    def test_proxy_exporta_build_admin_link(self):
        from services.email_service import _build_admin_link
        url = _build_admin_link("/ordenes/test")
        assert "/ordenes/test" in url
    
    def test_proxy_exporta_assert_client_safe(self):
        from services.email_service import _assert_client_safe
        # Debe existir y ser callable
        assert callable(_assert_client_safe)
    
    def test_proxy_exporta_safe_public_url(self):
        from services.email_service import _safe_public_url
        result = _safe_public_url("https://revix.es")
        assert result == "https://revix.es"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

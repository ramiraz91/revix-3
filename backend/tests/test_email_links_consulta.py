"""
Tests de regresión — enlaces de emails al cliente apuntan SIEMPRE a /consulta.

Contexto del bug original:
  email_service.py construía links a `{FRONTEND_URL}/ordenes/{orden_id}` para
  emails al cliente. Esa ruta es del CRM interno (login). Lo correcto es la
  página pública /consulta?codigo={token_seguimiento}.

Estos tests bloquean cualquier reincidencia futura.
"""
import re
import sys
from pathlib import Path

import pytest

# Hack: añadir backend al sys.path para imports directos
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from email_service import (  # noqa: E402
    _build_client_link,
    _build_admin_link,
    _build_html,
    _assert_client_safe,
    FRONTEND_URL,
)


# ── _build_client_link ───────────────────────────────────────────────────────

def test_client_link_con_token():
    url = _build_client_link("abc-123-token")
    assert "/consulta" in url
    assert "codigo=abc-123-token" in url
    assert "/ordenes/" not in url
    assert "/crm/" not in url


def test_client_link_sin_token():
    url = _build_client_link()
    assert url.endswith("/consulta")
    assert "/ordenes/" not in url
    assert "/crm/" not in url


def test_client_link_usa_frontend_url():
    """No debe filtrar URLs preview/localhost."""
    assert FRONTEND_URL.startswith("http")
    url = _build_client_link("xyz")
    assert url.startswith(FRONTEND_URL)


# ── _build_admin_link ────────────────────────────────────────────────────────

def test_admin_link_para_staff():
    url = _build_admin_link("/ordenes/uuid-123")
    assert "/ordenes/uuid-123" in url
    assert url.startswith(FRONTEND_URL)


# ── _assert_client_safe ──────────────────────────────────────────────────────

def test_assert_client_safe_acepta_consulta():
    html = _build_html("Test", "<p>contenido</p>",
                       link_url=_build_client_link("token-abc"),
                       link_text="Ver mi orden")
    # No debe lanzar
    _assert_client_safe(html, where="test_acepta_consulta")


def test_assert_client_safe_rechaza_ordenes_path():
    html = '<a href="https://revix.es/ordenes/abc-123">link</a>'
    with pytest.raises(AssertionError, match="email-leak"):
        _assert_client_safe(html, where="test_rechaza_ordenes")


def test_assert_client_safe_rechaza_crm_path():
    html = '<a href="https://revix.es/crm/dashboard">link</a>'
    with pytest.raises(AssertionError, match="email-leak"):
        _assert_client_safe(html, where="test_rechaza_crm")


# ── Verificación de las 4 funciones de notificación al cliente ──────────────
#    (inspección estática del HTML que generarían)

def _capture_html_from_notify(notify_fn, **kwargs):
    """Llama send_email mockeando Resend para capturar el HTML enviado."""
    captured = {}
    import email_service
    orig = email_service.resend.Emails.send

    def fake_send(params):
        captured["html"] = params["html"]
        captured["subject"] = params["subject"]
        return {"id": "test-mock"}

    email_service.resend.Emails.send = fake_send
    try:
        import asyncio
        asyncio.run(notify_fn(**kwargs))
    finally:
        email_service.resend.Emails.send = orig
    return captured.get("html", "")


@pytest.mark.skipif(not __import__("email_service").is_configured(),
                    reason="Resend no configurado")
def test_notificar_cambio_estado_usa_consulta():
    from email_service import notificar_cambio_estado
    html = _capture_html_from_notify(
        notificar_cambio_estado,
        to="cliente@test.com", orden_numero="OT-1", auth_code="AUTH1",
        nuevo_estado="reparado", orden_id="orden-uuid",
        token_seguimiento="TOK123",
    )
    assert "/consulta?codigo=TOK123" in html
    assert "/ordenes/orden-uuid" not in html


@pytest.mark.skipif(not __import__("email_service").is_configured(),
                    reason="Resend no configurado")
def test_notificar_presupuesto_enviado_usa_consulta():
    from email_service import notificar_presupuesto_enviado
    html = _capture_html_from_notify(
        notificar_presupuesto_enviado,
        to="cliente@test.com", orden_numero="OT-2",
        total=99.5, orden_id="ord-x", token_seguimiento="TOKPRES",
    )
    assert "/consulta?codigo=TOKPRES" in html
    assert "/ordenes/ord-x" not in html


@pytest.mark.skipif(not __import__("email_service").is_configured(),
                    reason="Resend no configurado")
def test_notificar_orden_lista_usa_consulta():
    from email_service import notificar_orden_lista
    html = _capture_html_from_notify(
        notificar_orden_lista,
        to="cliente@test.com", orden_numero="OT-3",
        auth_code="A3", orden_id="ord-y", token_seguimiento="TOKLIS",
    )
    assert "/consulta?codigo=TOKLIS" in html
    assert "/ordenes/ord-y" not in html


@pytest.mark.skipif(not __import__("email_service").is_configured(),
                    reason="Resend no configurado")
def test_notificar_factura_emitida_usa_consulta():
    from email_service import notificar_factura_emitida
    html = _capture_html_from_notify(
        notificar_factura_emitida,
        to="cliente@test.com", factura_numero="FAC-1", total=120.0,
        orden_numero="OT-4", orden_id="ord-z", token_seguimiento="TOKFAC",
    )
    assert "/consulta?codigo=TOKFAC" in html
    assert "/ordenes/ord-z" not in html


@pytest.mark.skipif(not __import__("email_service").is_configured(),
                    reason="Resend no configurado")
def test_notificar_material_pendiente_usa_admin_link():
    """Material pendiente VA al staff (admin) → /ordenes/{id} es correcto."""
    from email_service import notificar_material_pendiente
    html = _capture_html_from_notify(
        notificar_material_pendiente,
        to="tecnico@revix.es", pieza="Pantalla",
        orden_numero="OT-5", orden_id="ord-w",
    )
    # En este caso SÍ debe contener /ordenes/ porque es para staff
    assert "/ordenes/ord-w" in html


# ── helpers.py:generate_modern_email_html ───────────────────────────────────

def test_generate_modern_email_html_usa_consulta():
    from helpers import generate_modern_email_html
    html = generate_modern_email_html(
        orden={"id": "abc", "numero_orden": "OT-99",
               "token_seguimiento": "MODERN_TOK", "estado": "recibida",
               "dispositivo": {"marca": "Apple", "modelo": "iPhone 13"}},
        cliente={"nombre": "Juan", "email": "j@x.com"},
        email_type="recibida",
    )
    assert "/consulta?codigo=MODERN_TOK" in html
    # No debe contener URLs internas del CRM
    matches = re.findall(r'href=["\']([^"\']+)["\']', html)
    for url in matches:
        assert "/ordenes/" not in url, f"URL prohibida encontrada: {url}"
        assert "/crm/" not in url, f"URL prohibida encontrada: {url}"

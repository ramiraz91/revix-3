"""
Tests del filtro anti-preview en enlaces de emails.

Caso de uso: en production, si la variable FRONTEND_URL está envenenada
(apunta a preview.emergentagent.com, localhost, etc.), los emails a clientes
reales saldrían con enlaces rotos. `email_service._safe_public_url` debe
filtrar esos casos y caer al dominio oficial `https://revix.es`.
"""
import os
import sys

sys.path.insert(0, "/app/backend")

import email_service  # noqa: E402


def test_url_ok_revix_es():
    assert email_service._safe_public_url("https://revix.es") == "https://revix.es"


def test_url_ok_otros_dominios_reales():
    assert email_service._safe_public_url("https://crm.revix.es") == "https://crm.revix.es"
    assert email_service._safe_public_url("https://app.mi-taller.com") == "https://app.mi-taller.com"


def test_url_trailing_slash():
    assert email_service._safe_public_url("https://revix.es/") == "https://revix.es"


def test_url_preview_emergentagent_filtrado():
    out = email_service._safe_public_url("https://backend-perf-test.preview.emergentagent.com")
    assert out == "https://revix.es"


def test_url_emergent_host_filtrado():
    assert email_service._safe_public_url("https://algo.preview.emergent.host") == "https://revix.es"


def test_url_localhost_filtrado():
    assert email_service._safe_public_url("http://localhost:3000") == "https://revix.es"
    assert email_service._safe_public_url("http://127.0.0.1:3000") == "https://revix.es"
    assert email_service._safe_public_url("http://0.0.0.0:3000") == "https://revix.es"


def test_url_vacia_o_none():
    assert email_service._safe_public_url(None) == "https://revix.es"
    assert email_service._safe_public_url("") == "https://revix.es"
    assert email_service._safe_public_url("   ") == "https://revix.es"


def test_url_sin_esquema():
    # Sin http:// o https:// → fallback (protección contra inputs rotos)
    assert email_service._safe_public_url("revix.es") == "https://revix.es"
    assert email_service._safe_public_url("www.revix.es") == "https://revix.es"


def test_url_mayusculas_tambien_filtradas():
    assert email_service._safe_public_url("https://FOO.PREVIEW.EMERGENTAGENT.COM") == "https://revix.es"


def test_frontend_url_modulo_resuelve_a_valor_seguro():
    """Sanity: el valor exportado por el módulo es seguro."""
    assert not any(p in email_service.FRONTEND_URL.lower()
                   for p in email_service._UNSAFE_URL_PATTERNS)
    assert email_service.FRONTEND_URL.startswith("https://")


def test_links_notificaciones_ordenes_usan_frontend_url():
    """
    Los 5 helpers de notificaciones construyen el link usando f"{FRONTEND_URL}/ordenes/{id}".
    Esto se valida en código leyendo el source para asegurar que ninguno salta el filtro.
    """
    src = open("/app/backend/email_service.py").read()
    # Ningún link debe interpolar os.environ/os.getenv directamente
    import re
    bad = re.findall(r"link\s*=\s*f[\"']\{?os\.(environ|getenv)", src)
    assert not bad, f"Links que saltan el filtro: {bad}"
    # Los 5 helpers deben usar FRONTEND_URL
    assert src.count('link = f"{FRONTEND_URL}/ordenes/') >= 5

"""
Tests del módulo nuevo /app/backend/modules/logistica/gls.py.

Cubre:
  - preview: crear_envio devuelve codbarras determinista + PDF base64 válido
  - preview: tracking devuelve eventos mock
  - parseo ok de response real simulada
  - manejo error GLS (return != 0)
  - manejo XML malformado
  - manejo HTML en vez de XML (auth fail)
  - manejo HTTP != 200
  - pre-validación (uid_cliente vacío en modo prod)

No requieren Mongo ni red. Ejecutar:
    /app/revix_mcp/.venv/bin/pytest /app/backend/tests/test_gls_logistica.py -v
"""
from __future__ import annotations

import asyncio
import base64
import sys

import pytest
import httpx

sys.path.insert(0, "/app/backend")

from modules.logistica.gls import (  # noqa: E402
    Destinatario, GLSClient, GLSError, Remitente,
)


REMITENTE = Remitente(
    nombre="REVIX TALLER", direccion="Calle Falsa 123",
    poblacion="Madrid", provincia="Madrid", cp="28001",
    telefono="910000000",
)

DESTINATARIO = Destinatario(
    nombre="Juan Cliente", direccion="Av. Diagonal 100",
    poblacion="Barcelona", provincia="Barcelona", cp="08001",
    telefono="600000000", movil="600000000", email="juan@example.com",
    observaciones="OT TEST-001",
)


# ──────────────────────────────────────────────────────────────────────────────
# Preview mode
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_preview_crear_envio_determinista():
    client = GLSClient(uid_cliente="", remitente=REMITENTE, mcp_env="preview")
    r1 = await client.crear_envio("OT-001", DESTINATARIO, peso=2.5)
    r2 = await client.crear_envio("OT-001", DESTINATARIO, peso=2.5)

    assert r1.success is True
    assert r1.codbarras == r2.codbarras, "Debe ser determinista"
    assert len(r1.codbarras) == 14
    assert r1.uid  # uuid5 determinista
    assert r1.uid == r2.uid
    assert r1.referencia == "OT-001"

    # PDF base64 válido
    pdf = base64.b64decode(r1.etiqueta_pdf_base64)
    assert pdf.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf


@pytest.mark.asyncio
async def test_preview_tracking():
    client = GLSClient(uid_cliente="", remitente=REMITENTE, mcp_env="preview")
    t = await client.obtener_tracking("91234567890000")
    assert t.success is True
    assert t.codbarras == "91234567890000"
    assert t.estado_actual == "EN REPARTO"
    assert len(t.eventos) == 2
    assert t.eventos[0].estado == "ADMITIDO EN CENTRO"


@pytest.mark.asyncio
async def test_preview_no_requiere_uid():
    """En preview, un uid_cliente vacío NO debe fallar."""
    client = GLSClient(uid_cliente="", remitente=REMITENTE, mcp_env="preview")
    r = await client.crear_envio("OT-X", DESTINATARIO, peso=1.0)
    assert r.success


# ──────────────────────────────────────────────────────────────────────────────
# Parseo de response real simulada
# ──────────────────────────────────────────────────────────────────────────────

_RESPONSE_OK = '''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
<soap:Body>
<GrabaServiciosResponse xmlns="http://www.asmred.com/">
<GrabaServiciosResult>
<Servicios>
<Envio codbarras="61143283984788" uid="146234b1-aca6-4595-9b5a-4c414a803435">
<Resultado return="0" result="OK"/>
<Codexp>CODEXP-001</Codexp>
<Etiquetas>
<Etiqueta tipo="PDF">JVBERi0xLjQKJWFiY2Q=</Etiqueta>
</Etiquetas>
</Envio>
</Servicios>
</GrabaServiciosResult>
</GrabaServiciosResponse>
</soap:Body>
</soap:Envelope>'''


_RESPONSE_ERROR = '''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
<soap:Body>
<GrabaServiciosResponse xmlns="http://www.asmred.com/">
<GrabaServiciosResult>
<Servicios>
<Envio codbarras="" uid="">
<Resultado return="1" result="ERROR"/>
<Errores>Codigo postal invalido para la provincia</Errores>
</Envio>
</Servicios>
</GrabaServiciosResult>
</GrabaServiciosResponse>
</soap:Body>
</soap:Envelope>'''


_RESPONSE_TRACKING_OK = '''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
<soap:Body>
<GetExpCliResponse xmlns="http://www.asmred.com/">
<GetExpCliResult>
<Expediciones>
<exp>
<expedicion>12345</expedicion>
<codbar>61143283984788</codbar>
<estado>ENTREGADO</estado>
<codestado>10</codestado>
<FPEntrega>20/02/2026 11:30</FPEntrega>
<fecha>20/02/2026</fecha>
<incidencia></incidencia>
<tracking>
<fecha>19/02/2026 08:00</fecha>
<tipo>TRAMOS</tipo>
<evento>ADMITIDO EN CENTRO</evento>
<plaza>28</plaza>
<nombreplaza>MADRID</nombreplaza>
<codigo>1</codigo>
</tracking>
<tracking>
<fecha>20/02/2026 11:30</fecha>
<tipo>TRAMOS</tipo>
<evento>ENTREGADO</evento>
<plaza>08</plaza>
<nombreplaza>BARCELONA</nombreplaza>
<codigo>10</codigo>
</tracking>
</exp>
</Expediciones>
</GetExpCliResult>
</GetExpCliResponse>
</soap:Body>
</soap:Envelope>'''


def _mock_httpx_client(response_text: str, status_code: int = 200) -> httpx.AsyncClient:
    """Construye un AsyncClient con un MockTransport devolviendo texto fijo."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=response_text)
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport, timeout=5)


@pytest.mark.asyncio
async def test_crear_envio_parseo_ok():
    http = _mock_httpx_client(_RESPONSE_OK)
    client = GLSClient(
        uid_cliente="TEST-UID", remitente=REMITENTE,
        mcp_env="production", http_client=http,
    )
    r = await client.crear_envio("OT-100", DESTINATARIO, peso=1.5)
    await http.aclose()

    assert r.success is True
    assert r.codbarras == "61143283984788"
    assert r.uid == "146234b1-aca6-4595-9b5a-4c414a803435"
    assert r.etiqueta_pdf_base64 == "JVBERi0xLjQKJWFiY2Q="
    assert r.referencia == "OT-100"


@pytest.mark.asyncio
async def test_crear_envio_error_return_1():
    http = _mock_httpx_client(_RESPONSE_ERROR)
    client = GLSClient(
        uid_cliente="TEST-UID", remitente=REMITENTE,
        mcp_env="production", http_client=http,
    )
    with pytest.raises(GLSError) as exc_info:
        await client.crear_envio("OT-200", DESTINATARIO, peso=1.0)
    await http.aclose()
    assert exc_info.value.code == "1"
    assert "postal" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_crear_envio_xml_malformado():
    http = _mock_httpx_client("<<< not xml >>>")
    client = GLSClient(
        uid_cliente="TEST-UID", remitente=REMITENTE,
        mcp_env="production", http_client=http,
    )
    with pytest.raises(GLSError) as exc_info:
        await client.crear_envio("OT-300", DESTINATARIO, peso=1.0)
    await http.aclose()
    assert "XML" in str(exc_info.value) or "inválida" in str(exc_info.value)


@pytest.mark.asyncio
async def test_crear_envio_html_en_vez_de_xml():
    """GLS devuelve HTML de error (auth fail, endpoint mal)."""
    http = _mock_httpx_client("<html><body>401 Unauthorized</body></html>")
    client = GLSClient(
        uid_cliente="TEST-UID", remitente=REMITENTE,
        mcp_env="production", http_client=http,
    )
    with pytest.raises(GLSError) as exc_info:
        await client.crear_envio("OT-400", DESTINATARIO, peso=1.0)
    await http.aclose()
    assert "inválida" in str(exc_info.value) or "XML" in str(exc_info.value)


@pytest.mark.asyncio
async def test_crear_envio_http_500():
    http = _mock_httpx_client("Internal server error", status_code=500)
    client = GLSClient(
        uid_cliente="TEST-UID", remitente=REMITENTE,
        mcp_env="production", http_client=http,
    )
    with pytest.raises(GLSError) as exc_info:
        await client.crear_envio("OT-500", DESTINATARIO, peso=1.0)
    await http.aclose()
    assert "500" in str(exc_info.value)


@pytest.mark.asyncio
async def test_production_requiere_uid():
    """En production, sin uid_cliente debe lanzar GLSError."""
    client = GLSClient(uid_cliente="", remitente=REMITENTE, mcp_env="production")
    with pytest.raises(GLSError) as exc_info:
        await client.crear_envio("OT-X", DESTINATARIO, peso=1.0)
    assert "UID_CLIENTE" in str(exc_info.value)


@pytest.mark.asyncio
async def test_tracking_parseo_ok():
    http = _mock_httpx_client(_RESPONSE_TRACKING_OK)
    client = GLSClient(
        uid_cliente="TEST-UID", remitente=REMITENTE,
        mcp_env="production", http_client=http,
    )
    t = await client.obtener_tracking("61143283984788")
    await http.aclose()

    assert t.success is True
    assert t.estado_actual == "ENTREGADO"
    assert t.estado_codigo == "10"
    assert t.fecha_entrega == "20/02/2026 11:30"
    assert len(t.eventos) == 2
    assert t.eventos[0].estado == "ADMITIDO EN CENTRO"
    assert t.eventos[0].plaza == "MADRID"
    assert t.eventos[1].estado == "ENTREGADO"


# ──────────────────────────────────────────────────────────────────────────────
# Construcción XML
# ──────────────────────────────────────────────────────────────────────────────

def test_xml_contiene_cdata_y_uid():
    client = GLSClient(
        uid_cliente="MY-UID-1234", remitente=REMITENTE, mcp_env="production",
    )
    xml = client._build_graba_servicios_xml(DESTINATARIO, peso=2.5, referencia="OT-X")
    assert 'uidcliente="MY-UID-1234"' in xml
    assert "<![CDATA[Juan Cliente]]>" in xml
    assert "<![CDATA[Av. Diagonal 100]]>" in xml
    assert "<Peso>2,50</Peso>" in xml  # coma decimal
    assert "<Servicio>96</Servicio>" in xml
    assert "<Horario>18</Horario>" in xml


def test_soap12_envelope_header():
    client = GLSClient(
        uid_cliente="MY-UID-1234", remitente=REMITENTE, mcp_env="production",
    )
    body = client._build_graba_servicios_xml(DESTINATARIO, peso=1.0, referencia="R1")
    env = client._wrap_soap12(body)
    assert "soap12:Envelope" in env
    assert "www.w3.org/2003/05/soap-envelope" in env


if __name__ == "__main__":
    # Permite ejecutar en forma standalone
    asyncio.run(test_preview_crear_envio_determinista())
    print("ok smoke")

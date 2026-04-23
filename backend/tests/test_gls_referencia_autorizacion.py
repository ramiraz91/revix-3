"""
Tests de flujo referencia = código autorización + duplicados.

Ejecutar con:
    /usr/local/bin/python3 -m pytest /app/backend/tests/test_gls_referencia_autorizacion.py -v
"""
from __future__ import annotations

import sys

import pytest
import httpx

sys.path.insert(0, "/app/backend")

from modules.logistica.gls import (  # noqa: E402
    Destinatario, GLSClient, Remitente,
)


REMITENTE = Remitente(
    nombre="REVIX", direccion="Calle X 1", cp="14007",
    poblacion="CORDOBA", provincia="CORDOBA", telefono="+34600000000",
)
DESTINATARIO = Destinatario(
    nombre="Juan", direccion="Av Y 10", cp="08001",
    poblacion="BCN", provincia="BCN",
    telefono="600", movil="600", email="a@a.com", observaciones="",
)


def test_build_xml_usa_referencia_explicita():
    """La referencia pasada al XML es EXACTAMENTE la que se pase al método."""
    client = GLSClient(
        uid_cliente="UID-1", remitente=REMITENTE, mcp_env="production",
    )
    xml = client._build_graba_servicios_xml(
        destinatario=DESTINATARIO, peso=0.5,
        referencia="AUTH-INSUR-99887",
    )
    # El valor de la autorización debe estar en el CDATA de la Referencia
    assert "<![CDATA[AUTH-INSUR-99887]]>" in xml
    # No debe aparecer el numero_orden por ningún lado
    assert "OT-DEMO" not in xml
    # Es una referencia tipo C (cliente)
    assert 'Referencia tipo="C"' in xml


def test_build_xml_referencia_numero_ot_fallback():
    """Si sólo se pasa el numero_orden como referencia, el XML lo refleja."""
    client = GLSClient(
        uid_cliente="UID-1", remitente=REMITENTE, mcp_env="production",
    )
    xml = client._build_graba_servicios_xml(
        destinatario=DESTINATARIO, peso=0.5,
        referencia="OT-DEMO-002",
    )
    assert "<![CDATA[OT-DEMO-002]]>" in xml


@pytest.mark.asyncio
async def test_preview_mantiene_referencia_en_resultado():
    """En modo preview, el objeto resultado expone la referencia pasada."""
    client = GLSClient(
        uid_cliente="UID-1", remitente=REMITENTE, mcp_env="preview",
    )
    r = await client.crear_envio(
        order_id="OT-X", destinatario=DESTINATARIO, peso=0.5,
        referencia="AUTH-INSUR-99887",
    )
    assert r.referencia == "AUTH-INSUR-99887"
    assert r.success is True


def _mock_httpx_client(text, status=200):
    def handler(request):
        return httpx.Response(status, text=text)
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5)


_OK_RESPONSE = '''<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"><soap:Body>
<GrabaServiciosResponse xmlns="http://www.asmred.com/"><GrabaServiciosResult>
<Servicios><Envio codbarras="61000000000001" uid="uuid-x">
<Resultado return="0"/>
<Etiquetas><Etiqueta tipo="PDF">JVBERi0=</Etiqueta></Etiquetas>
</Envio></Servicios></GrabaServiciosResult></GrabaServiciosResponse>
</soap:Body></soap:Envelope>'''


@pytest.mark.asyncio
async def test_production_envia_autorizacion_al_servicio():
    """En production, el XML transmitido a GLS contiene la autorización."""
    capturado = {}

    def handler(request):
        capturado["body"] = request.content.decode("utf-8")
        return httpx.Response(200, text=_OK_RESPONSE)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5) as http:
        client = GLSClient(
            uid_cliente="UID-1", remitente=REMITENTE,
            mcp_env="production", http_client=http,
        )
        r = await client.crear_envio(
            order_id="OT-1", destinatario=DESTINATARIO, peso=0.5,
            referencia="AUTH-SINI-12345",
        )

    assert r.success
    assert "AUTH-SINI-12345" in capturado["body"]
    assert 'Referencia tipo="C"' in capturado["body"]

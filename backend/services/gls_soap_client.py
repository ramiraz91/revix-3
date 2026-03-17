"""
GLS Spain SOAP Web Service Client.
Raw SOAP communication layer - no business logic here.
Methods: GrabaServicios, EtiquetaEnvioV2, EtiquetaEnvioRecogidas, GetExpCli, Anula
"""
import logging
import base64
import httpx
from xml.etree import ElementTree as ET

logger = logging.getLogger("gls_soap")

GLS_URL = "https://ws-customer.gls-spain.es/b2b.asmx"
GLS_LABEL_URL = "https://wsclientes.asmred.com/b2b.asmx"
GLS_NS = "http://www.asmred.com/"

SERVICIOS_GLS = {
    "1": "BusinessParcel",
    "10": "10:00 Service",
    "14": "14:00 Service",
    "74": "EuroBusiness Parcel",
    "96": "EconomyParcel",
}

HORARIOS_GLS = {
    "3": "Business Parcel (sin hora)",
    "10": "Entrega antes 10:00",
    "14": "Entrega antes 14:00",
    "18": "Sin franja horaria",
}


def _escape_xml(val):
    if not val:
        return ""
    return str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


async def _soap_call(url: str, body_xml: str, timeout: float = 30.0) -> tuple:
    """Execute SOAP 1.2 call. Returns (response_text, raw_request, raw_response)."""
    envelope = f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    {body_xml}
  </soap12:Body>
</soap12:Envelope>'''

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            url,
            content=envelope.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=UTF-8"}
        )
        response.raise_for_status()
        return response.text, envelope, response.text


def _parse_xml(text: str) -> ET.Element:
    """Parse SOAP response stripping namespaces."""
    root = ET.fromstring(text)
    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]
    return root


def _text(elem, tag, default=""):
    child = elem.find(tag)
    return (child.text or default) if child is not None else default


async def graba_servicios(uid_cliente: str, envio_xml_inner: str) -> dict:
    """
    GrabaServicios - Create shipment/pickup.
    envio_xml_inner: the <Envio>...</Envio> XML block.
    Returns: {success, codbarras, uid_envio, raw_request, raw_response, error}
    """
    body = f'''<GrabaServicios xmlns="{GLS_NS}">
      <docIn>
        <Servicios uidcliente="{_escape_xml(uid_cliente)}" xmlns="{GLS_NS}">
          {envio_xml_inner}
        </Servicios>
      </docIn>
    </GrabaServicios>'''

    try:
        resp_text, raw_req, raw_resp = await _soap_call(GLS_URL, body)
        root = _parse_xml(resp_text)

        envio_elem = root.find(".//Envio")
        if envio_elem is None:
            return {"success": False, "error": "Respuesta sin nodo Envio", "raw_request": raw_req, "raw_response": raw_resp}

        codbarras = envio_elem.get("codbarras", "")
        uid_envio = envio_elem.get("uid", "")
        resultado = envio_elem.find(".//Resultado")
        ret_val = resultado.get("return", "") if resultado is not None else ""

        if ret_val and ret_val != "0":
            error_text = resultado.text if resultado is not None and resultado.text else f"Code {ret_val}"
            return {"success": False, "error": error_text, "codbarras": codbarras, "uid_envio": uid_envio,
                    "raw_request": raw_req, "raw_response": raw_resp}

        return {"success": True, "codbarras": codbarras, "uid_envio": uid_envio,
                "raw_request": raw_req, "raw_response": raw_resp}
    except httpx.TimeoutException:
        return {"success": False, "error": "Timeout conectando con GLS (30s)"}
    except Exception as e:
        logger.error(f"SOAP GrabaServicios error: {e}")
        return {"success": False, "error": str(e)}


async def etiqueta_envio(uid_cliente: str, referencia: str, formato: str = "PDF") -> dict:
    """EtiquetaEnvioV2 - Get shipment label."""
    body = f'''<EtiquetaEnvioV2 xmlns="{GLS_NS}">
      <uidcliente>{_escape_xml(uid_cliente)}</uidcliente>
      <codigo>{_escape_xml(referencia)}</codigo>
      <tipoEtiqueta>{_escape_xml(formato.upper())}</tipoEtiqueta>
    </EtiquetaEnvioV2>'''

    try:
        resp_text, raw_req, raw_resp = await _soap_call(GLS_LABEL_URL, body)
        root = _parse_xml(resp_text)
        etiquetas = root.findall(".//Etiqueta")
        if not etiquetas or not etiquetas[0].text:
            return {"success": False, "error": "Sin etiquetas en respuesta"}

        content_types = {"PDF": "application/pdf", "PNG": "image/png", "JPG": "image/jpeg",
                         "ZPL": "text/plain", "EPL": "text/plain", "DPL": "text/plain"}
        return {"success": True, "etiqueta_base64": etiquetas[0].text,
                "content_type": content_types.get(formato.upper(), "application/pdf"), "formato": formato.upper()}
    except Exception as e:
        logger.error(f"SOAP EtiquetaEnvioV2 error: {e}")
        return {"success": False, "error": str(e)}


async def etiqueta_recogida(uid_cliente: str, referencia: str, formato: str = "PDF") -> dict:
    """EtiquetaEnvioRecogidas - Get pickup label."""
    body = f'''<EtiquetaEnvioRecogidas xmlns="{GLS_NS}">
      <uidCliente>{_escape_xml(uid_cliente)}</uidCliente>
      <codigo>{_escape_xml(referencia)}</codigo>
      <tipoEtiqueta>{_escape_xml(formato.upper())}</tipoEtiqueta>
    </EtiquetaEnvioRecogidas>'''

    try:
        resp_text, raw_req, raw_resp = await _soap_call(GLS_LABEL_URL, body)
        root = _parse_xml(resp_text)
        etiquetas = root.findall(".//Etiqueta")
        if not etiquetas or not etiquetas[0].text:
            return {"success": False, "error": "Sin etiquetas de recogida en respuesta"}

        content_types = {"PDF": "application/pdf", "PNG": "image/png", "JPG": "image/jpeg"}
        return {"success": True, "etiqueta_base64": etiquetas[0].text,
                "content_type": content_types.get(formato.upper(), "application/pdf"), "formato": formato.upper()}
    except Exception as e:
        logger.error(f"SOAP EtiquetaRecogidas error: {e}")
        return {"success": False, "error": str(e)}


async def get_exp_cli(uid_cliente: str, referencia: str) -> dict:
    """GetExpCli - Get full expedition tracking."""
    body = f'''<GetExpCli xmlns="{GLS_NS}">
      <codigo>{_escape_xml(referencia)}</codigo>
      <uid>{_escape_xml(uid_cliente)}</uid>
    </GetExpCli>'''

    try:
        resp_text, raw_req, raw_resp = await _soap_call(GLS_URL, body, timeout=20.0)
        root = _parse_xml(resp_text)

        exps = root.findall(".//exp")
        if not exps:
            return {"success": False, "error": "Expedición no encontrada", "raw_response": raw_resp}

        exp = exps[0]
        result = {
            "success": True,
            "expedicion": _text(exp, "expedicion"),
            "codexp": _text(exp, "codexp"),
            "codbarras": _text(exp, "codbar"),
            "uid_envio": _text(exp, "uidExp"),
            "albaran": _text(exp, "albaran"),
            "fecha": _text(exp, "fecha"),
            "fecha_entrega_prevista": _text(exp, "FPEntrega"),
            "nombre_org": _text(exp, "nombre_org"),
            "nombre_dst": _text(exp, "nombre_dst"),
            "calle_dst": _text(exp, "calle_dst"),
            "localidad_dst": _text(exp, "localidad_dst"),
            "cp_dst": _text(exp, "cp_dst"),
            "servicio": _text(exp, "servicio"),
            "bultos": _text(exp, "bultos"),
            "kgs": _text(exp, "kgs"),
            "codestado": _text(exp, "codestado"),
            "estado": _text(exp, "estado"),
            "incidencia": _text(exp, "incidencia"),
            "nombre_receptor": _text(exp, "nombre_rec"),
            "dni_receptor": _text(exp, "dni_rec"),
            "fecha_entrega": _text(exp, "fecha_entrega"),
            "hora_entrega": _text(exp, "hora_entrega"),
            "pod_url": _text(exp, "pod"),
            "borrado": _text(exp, "borrado"),
            "raw_response": raw_resp,
        }

        tracking_list = []
        for trk in exp.findall(".//tracking_list/tracking"):
            tracking_list.append({
                "fecha": _text(trk, "fecha"),
                "tipo": _text(trk, "tipo"),
                "codigo": _text(trk, "codigo"),
                "evento": _text(trk, "evento"),
                "plaza": _text(trk, "plaza"),
                "nombre_plaza": _text(trk, "nombreplaza"),
            })
        result["tracking_list"] = tracking_list
        return result
    except httpx.TimeoutException:
        return {"success": False, "error": "Timeout consultando tracking GLS"}
    except Exception as e:
        logger.error(f"SOAP GetExpCli error: {e}")
        return {"success": False, "error": str(e)}


async def anula(uid_cliente: str, referencia: str) -> dict:
    """Anula - Cancel a shipment."""
    body = f'''<Anula xmlns="{GLS_NS}">
      <docIn>
        <Servicios uidcliente="{_escape_xml(uid_cliente)}" xmlns="{GLS_NS}">
          <Envio>
            <Referencias>
              <Referencia tipo="C">{_escape_xml(referencia)}</Referencia>
            </Referencias>
          </Envio>
        </Servicios>
      </docIn>
    </Anula>'''

    try:
        resp_text, raw_req, raw_resp = await _soap_call(GLS_URL, body)
        root = _parse_xml(resp_text)
        resultado = root.find(".//Resultado")
        ret_val = resultado.get("return", "") if resultado is not None else ""

        if ret_val == "0":
            return {"success": True, "raw_request": raw_req, "raw_response": raw_resp}
        return {"success": False, "error": f"Error anulando: code {ret_val}",
                "raw_request": raw_req, "raw_response": raw_resp}
    except Exception as e:
        logger.error(f"SOAP Anula error: {e}")
        return {"success": False, "error": str(e)}


def build_envio_xml(remitente: dict, destinatario: dict, params: dict) -> str:
    """Build the <Envio> XML block for GrabaServicios."""
    from datetime import datetime, timezone
    fecha = params.get("fecha") or datetime.now(timezone.utc).strftime("%d/%m/%Y")

    return f'''<Envio>
        <Fecha>{_escape_xml(fecha)}</Fecha>
        <Servicio>{_escape_xml(params.get("servicio", "1"))}</Servicio>
        <Horario>{_escape_xml(params.get("horario", "18"))}</Horario>
        <Bultos>{_escape_xml(params.get("bultos", "1"))}</Bultos>
        <Peso>{_escape_xml(params.get("peso", "1"))}</Peso>
        <Portes>{_escape_xml(params.get("portes", "P"))}</Portes>
        <Importes>
          <Reembolso>{_escape_xml(params.get("reembolso", "0"))}</Reembolso>
        </Importes>
        <Remite>
          <Nombre>{_escape_xml(remitente.get("nombre", ""))}</Nombre>
          <Direccion>{_escape_xml(remitente.get("direccion", ""))}</Direccion>
          <Poblacion>{_escape_xml(remitente.get("poblacion", ""))}</Poblacion>
          <Pais>ES</Pais>
          <CP>{_escape_xml(remitente.get("cp", ""))}</CP>
          <Telefono>{_escape_xml(remitente.get("telefono", ""))}</Telefono>
          <NIF>{_escape_xml(remitente.get("nif", ""))}</NIF>
        </Remite>
        <Destinatario>
          <Nombre>{_escape_xml(destinatario.get("nombre", ""))}</Nombre>
          <Direccion>{_escape_xml(destinatario.get("direccion", ""))}</Direccion>
          <Poblacion>{_escape_xml(destinatario.get("poblacion", ""))}</Poblacion>
          <Pais>{_escape_xml(destinatario.get("pais", "ES"))}</Pais>
          <CP>{_escape_xml(destinatario.get("cp", ""))}</CP>
          <Telefono>{_escape_xml(destinatario.get("telefono", ""))}</Telefono>
          <Email>{_escape_xml(destinatario.get("email", ""))}</Email>
          <NIF>{_escape_xml(destinatario.get("nif", ""))}</NIF>
          <Observaciones>{_escape_xml(params.get("observaciones", ""))}</Observaciones>
        </Destinatario>
        <Referencias>
          <Referencia tipo="C">{_escape_xml(params.get("referencia", ""))}</Referencia>
        </Referencias>
      </Envio>'''

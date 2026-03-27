"""
GLS SOAP Client - Raw communication with GLS web service.
Endpoint: https://ws-customer.gls-spain.es/b2b.asmx
Methods: GrabaServicios, EtiquetaEnvioV2, GetExp, GetExpCli
WSDL: offline b2b.wsdl (as per GLS docs, do NOT use the online version)

IMPORTANT: GLS Spain requires SOAP 1.1 (not 1.2) and NO CDATA sections.
"""
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional
from html import escape as html_escape
import httpx

logger = logging.getLogger("gls.soap")

GLS_ENDPOINT = "https://ws-customer.gls-spain.es/b2b.asmx"
GLS_NAMESPACE = "http://www.asmred.com/"
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"  # SOAP 1.1 namespace
TIMEOUT = 30


def _escape_xml(text: str) -> str:
    """Escape text for XML (no CDATA, GLS doesn't like it)."""
    if not text:
        return ""
    return html_escape(str(text), quote=False)


def _soap_envelope(body_xml: str) -> str:
    """Wrap body XML in SOAP 1.1 envelope (required by GLS Spain)."""
    return f'''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns:xsd="http://www.w3.org/2001/XMLSchema"
  xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    {body_xml}
  </soap:Body>
</soap:Envelope>'''


async def _soap_call(action: str, body_xml: str) -> str:
    """Execute SOAP call and return response body text."""
    envelope = _soap_envelope(body_xml)
    
    # El WSDL de GLS España requiere el header SOAPAction
    soap_action = f"http://www.asmred.com/{action}"
    
    # GLS España usa SOAP 1.1 que requiere text/xml (no application/soap+xml)
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": soap_action,
    }
    
    logger.debug(f"GLS SOAP Request to {action}:")
    logger.debug(f"Headers: {headers}")
    logger.debug(f"Body (truncated): {envelope[:500]}...")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(GLS_ENDPOINT, content=envelope, headers=headers)
        
        logger.debug(f"GLS SOAP Response status: {resp.status_code}")
        logger.debug(f"GLS SOAP Response (truncated): {resp.text[:500] if resp.text else 'empty'}...")
        
        if resp.status_code != 200:
            logger.error(f"GLS SOAP Error {resp.status_code}: {resp.text[:1000]}")
        
        resp.raise_for_status()
        return resp.text


def _extract_result(response_text: str, result_tag: str) -> str:
    """Extract the result content from a SOAP response."""
    try:
        root = ET.fromstring(response_text)
        
        # Buscar el elemento resultado por nombre (sin namespace específico)
        for elem in root.iter():
            tag_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag_name == result_tag:
                # Si tiene hijos, serializar todo el contenido XML
                if len(elem) > 0:
                    # Buscar el elemento Servicios dentro
                    for child in elem:
                        child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                        if child_tag == "Servicios":
                            return ET.tostring(child, encoding='unicode')
                    # Si no encuentra Servicios, devolver el contenido como string
                    return ET.tostring(elem, encoding='unicode')
                # Si es texto directo
                elif elem.text:
                    return elem.text.strip()
        
        logger.warning(f"Could not find {result_tag} in response")
        logger.debug(f"Response structure: {response_text[:500]}")
    except ET.ParseError as e:
        logger.error(f"XML parse error in _extract_result: {e}")
    return ""


def _parse_shipment_response(xml_text: str) -> dict:
    """Parse GrabaServicios response XML into structured dict."""
    result = {"success": False, "envios": [], "errors": []}
    if not xml_text:
        result["errors"].append("Empty response from GLS")
        return result

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        result["errors"].append(f"XML parse error: {e}")
        return result

    for envio_el in root.iter("Envio"):
        envio = {
            "codbarras": envio_el.get("codbarras", ""),
            "uid": envio_el.get("uid", ""),
        }
        resultado = envio_el.find("Resultado")
        if resultado is not None:
            envio["return_code"] = resultado.get("return", "")
            envio["result"] = resultado.get("result", "")
            envio["success"] = envio["return_code"] == "0"
        else:
            envio["success"] = bool(envio["codbarras"])

        errores = envio_el.find("Errores")
        if errores is not None and errores.text:
            envio["error_text"] = errores.text.strip()
        elif errores is not None:
            err_items = [e.text for e in errores if e.text]
            if err_items:
                envio["error_text"] = "; ".join(err_items)

        ref_el = envio_el.find(".//Referencia")
        if ref_el is not None:
            envio["referencia"] = ref_el.text or ""

        # Extract label if returned inline
        etiqueta_el = envio_el.find(".//Etiqueta")
        if etiqueta_el is not None and etiqueta_el.text:
            envio["label_base64"] = etiqueta_el.text

        # Extract codexp from response
        codexp_el = envio_el.find("Codexp")
        if codexp_el is not None and codexp_el.text:
            envio["codexp"] = codexp_el.text

        result["envios"].append(envio)

    result["success"] = any(e.get("success") for e in result["envios"])
    return result


def _parse_tracking_response(xml_text: str) -> dict:
    """Parse GetExp/GetExpCli response into structured tracking data."""
    result = {"success": False, "expediciones": []}
    if not xml_text:
        return result

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return result

    for exp_el in root.iter("exp"):
        exp = {}
        simple_tags = [
            "expedicion", "albaran", "fecha", "FPEntrega", "servicio", "horario",
            "codServicio", "codHorario", "tipo_portes",
            "nombre_org", "calle_org", "localidad_org", "cp_org", "tfno_org", "codpais_org",
            "nombre_dst", "calle_dst", "localidad_dst", "cp_dst", "tfno_dst", "codpais_dst",
            "email_dst", "bultos", "kgs", "vol",
            "codestado", "estado", "pod", "tipopod", "nmtipopod",
            "firma", "DniEntrega", "NombreEntrega", "incidencia", "Observacion",
            "codexp", "codbar", "uidExp",
            "dac", "retorno", "Reembolso",
            "refC", "refX", "refS", "refZ", "refGlsG", "refGlsN",
        ]
        for tag in simple_tags:
            el = exp_el.find(tag)
            exp[tag] = el.text.strip() if el is not None and el.text else ""

        # Parse tracking list
        tracking_list = []
        for t_el in exp_el.iter("tracking"):
            track = {}
            for tag in ["fecha", "tipo", "plaza", "evento", "prioridad", "codigo", "nombreplaza"]:
                el = t_el.find(tag)
                track[tag] = el.text.strip() if el is not None and el.text else ""
            tracking_list.append(track)
        exp["tracking_list"] = tracking_list

        # Parse digitalizaciones (POD, signatures, etc.)
        digitalizaciones = []
        for d_el in exp_el.iter("digitalizacion"):
            dig = {}
            for tag in ["codtipo", "tipo", "fecha", "imagen", "observaciones"]:
                el = d_el.find(tag)
                dig[tag] = el.text.strip() if el is not None and el.text else ""
            digitalizaciones.append(dig)
        exp["digitalizaciones"] = digitalizaciones

        result["expediciones"].append(exp)

    result["success"] = len(result["expediciones"]) > 0
    return result


# ─── PUBLIC API ──────────────────────────

def build_shipment_xml(uid_cliente: str, config: dict, data: dict) -> str:
    """Build GrabaServicios XML from structured data.
    
    data keys: tipo, dest_*, bultos, peso, servicio, horario, referencia,
               reembolso, retorno, pod, etiqueta_inline, formato_etiqueta,
               recogida_* (for cross-pickup)
    config keys: remitente_*
    """
    fecha = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    tipo = data.get("tipo", "envio")

    servicio = data.get("servicio") or config.get("servicio_defecto", "96")
    horario = data.get("horario") or config.get("horario_defecto", "18")
    portes = config.get("portes", "P")
    
    # Datos del remitente desde config (incluyendo plaza y código cliente)
    plaza_remitente = config.get("plaza_remitente", "")
    codigo_remitente = config.get("codigo_remitente", "")

    remitente_xml = f'''<Remite>
      <Plaza>{plaza_remitente}</Plaza>
      <Codigo>{codigo_remitente}</Codigo>
      <Nombre>{_escape_xml(config.get("remitente_nombre", ""))}</Nombre>
      <Direccion>{_escape_xml(config.get("remitente_direccion", ""))}</Direccion>
      <Poblacion>{_escape_xml(config.get("remitente_poblacion", ""))}</Poblacion>
      <Provincia>{_escape_xml(config.get("remitente_provincia", ""))}</Provincia>
      <Pais>{config.get("remitente_pais", "34")}</Pais>
      <CP>{config.get("remitente_cp", "")}</CP>
      <Telefono>{_escape_xml(config.get("remitente_telefono", ""))}</Telefono>
      <Movil></Movil>
      <Email>{_escape_xml(config.get("remitente_email", ""))}</Email>
      <Observaciones></Observaciones>
    </Remite>'''

    dest_xml = f'''<Destinatario>
      <Codigo></Codigo>
      <Plaza></Plaza>
      <Nombre>{_escape_xml(data.get("dest_nombre", ""))}</Nombre>
      <Direccion>{_escape_xml(data.get("dest_direccion", ""))}</Direccion>
      <Poblacion>{_escape_xml(data.get("dest_poblacion", ""))}</Poblacion>
      <Provincia>{_escape_xml(data.get("dest_provincia", ""))}</Provincia>
      <Pais>{data.get("dest_pais", "34")}</Pais>
      <CP>{data.get("dest_cp", "")}</CP>
      <Telefono>{_escape_xml(data.get("dest_telefono", ""))}</Telefono>
      <Movil>{_escape_xml(data.get("dest_movil", ""))}</Movil>
      <Email>{_escape_xml(data.get("dest_email", ""))}</Email>
      <Observaciones>{_escape_xml(data.get("dest_observaciones", ""))}</Observaciones>
      <ATT>{_escape_xml(data.get("dest_contacto", ""))}</ATT>
    </Destinatario>'''

    ref = data.get("referencia", "")
    ref_xml = f'''<Referencias>
      <Referencia tipo="C">{_escape_xml(ref)}</Referencia>
    </Referencias>'''

    reembolso = data.get("reembolso", 0)
    importes_xml = f'''<Importes>
      <Reembolso>{str(reembolso).replace(".", ",")}</Reembolso>
    </Importes>''' if reembolso else ""

    adicionales_xml = ""
    if data.get("etiqueta_inline"):
        fmt = data.get("formato_etiqueta", "PDF")
        adicionales_xml = f'''<DevuelveAdicionales>
      <Etiqueta tipo="{fmt}"></Etiqueta>
    </DevuelveAdicionales>'''

    if tipo == "recogida":
        # Para recogida: Remite=cliente (de quien recogemos), Destinatario=nosotros (Revix)
        envio_xml = f'''<Recogida codbarras="">
    <Fecha>{fecha}</Fecha>
    <Portes>{portes}</Portes>
    <Servicio>7</Servicio>
    <Horario>3</Horario>
    <Bultos>{data.get("bultos", 1)}</Bultos>
    <Peso>{data.get("peso", 1)}</Peso>
    <Retorno>{data.get("retorno", "0")}</Retorno>
    <Pod>{data.get("pod", "N")}</Pod>
    {dest_xml.replace("<Destinatario>", "<Remite>").replace("</Destinatario>", "</Remite>")}
    <Destinatario>
      <Plaza>{plaza_remitente}</Plaza>
      <Codigo>{codigo_remitente}</Codigo>
      <Nombre>{_escape_xml(config.get("remitente_nombre", ""))}</Nombre>
      <Direccion>{_escape_xml(config.get("remitente_direccion", ""))}</Direccion>
      <Poblacion>{_escape_xml(config.get("remitente_poblacion", ""))}</Poblacion>
      <Provincia>{_escape_xml(config.get("remitente_provincia", ""))}</Provincia>
      <Pais>{config.get("remitente_pais", "34")}</Pais>
      <CP>{config.get("remitente_cp", "")}</CP>
      <Telefono>{_escape_xml(config.get("remitente_telefono", ""))}</Telefono>
      <Movil></Movil>
      <Email>{_escape_xml(config.get("remitente_email", ""))}</Email>
      <Observaciones></Observaciones>
    </Destinatario>
    {ref_xml}
    {importes_xml}
    {adicionales_xml}
  </Recogida>'''
    else:
        envio_xml = f'''<Envio codbarras="">
    <Fecha>{fecha}</Fecha>
    <Portes>{portes}</Portes>
    <Servicio>{servicio}</Servicio>
    <Horario>{horario}</Horario>
    <Bultos>{data.get("bultos", 1)}</Bultos>
    <Peso>{data.get("peso", 1)}</Peso>
    <Retorno>{data.get("retorno", "0")}</Retorno>
    <Pod>{data.get("pod", "N")}</Pod>
    {remitente_xml}
    {dest_xml}
    {ref_xml}
    {importes_xml}
    {adicionales_xml}
  </Envio>'''

    return f'''<Servicios uidcliente="{uid_cliente}" xmlns="http://www.asmred.com/">
  {envio_xml}
</Servicios>'''


async def graba_servicios(uid_cliente: str, config: dict, data: dict) -> dict:
    """Call GrabaServicios to create a shipment/pickup."""
    xml_in = build_shipment_xml(uid_cliente, config, data)
    # GLS España NO acepta CDATA - el XML debe ir directo dentro de docIn
    body = f'''<GrabaServicios xmlns="{GLS_NAMESPACE}">
      <docIn>{xml_in}</docIn>
    </GrabaServicios>'''

    try:
        response = await _soap_call("GrabaServicios", body)
        result_xml = _extract_result(response, "GrabaServiciosResult")
        parsed = _parse_shipment_response(result_xml)
        parsed["raw_request"] = xml_in
        parsed["raw_response"] = result_xml
        return parsed
    except httpx.HTTPStatusError as e:
        return {"success": False, "errors": [f"HTTP {e.response.status_code}"], "raw_request": xml_in, "raw_response": str(e)}
    except Exception as e:
        return {"success": False, "errors": [str(e)], "raw_request": xml_in, "raw_response": ""}


async def etiqueta_envio_v2(uid_cliente: str, codigo: str, tipo_etiqueta: str = "PDF") -> dict:
    """Call EtiquetaEnvioV2 to get a label."""
    body = f'''<EtiquetaEnvioV2 xmlns="{GLS_NAMESPACE}">
      <uidcliente>{uid_cliente}</uidcliente>
      <codigo>{codigo}</codigo>
      <tipoEtiqueta>{tipo_etiqueta}</tipoEtiqueta>
    </EtiquetaEnvioV2>'''

    try:
        response = await _soap_call("EtiquetaEnvioV2", body)
        # Extract base64 labels
        root = ET.fromstring(response)
        labels = []
        for el in root.iter():
            if "base64Binary" in el.tag and el.text:
                labels.append(el.text)
        # Also try direct result extraction
        if not labels:
            result_xml = _extract_result(response, "EtiquetaEnvioV2Result")
            if result_xml:
                labels = [result_xml]
        return {"success": len(labels) > 0, "labels": labels, "formato": tipo_etiqueta}
    except Exception as e:
        return {"success": False, "labels": [], "error": str(e)}


async def get_exp(uid_exp: str) -> dict:
    """Call GetExp to get tracking by expedition UID."""
    body = f'''<GetExp xmlns="{GLS_NAMESPACE}">
      <uid>{uid_exp}</uid>
    </GetExp>'''

    try:
        response = await _soap_call("GetExp", body)
        result_xml = _extract_result(response, "GetExpResult")
        return _parse_tracking_response(result_xml)
    except Exception as e:
        return {"success": False, "expediciones": [], "error": str(e)}


async def get_exp_cli(uid_cliente: str, codigo: str) -> dict:
    """Call GetExpCli to get tracking by client UID + code (barcode/reference/codexp)."""
    body = f'''<GetExpCli xmlns="{GLS_NAMESPACE}">
      <codigo>{codigo}</codigo>
      <uid>{uid_cliente}</uid>
    </GetExpCli>'''

    try:
        response = await _soap_call("GetExpCli", body)
        result_xml = _extract_result(response, "GetExpCliResult")
        return _parse_tracking_response(result_xml)
    except Exception as e:
        return {"success": False, "expediciones": [], "error": str(e)}

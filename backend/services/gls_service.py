"""
GLS Spain SOAP Web Service Integration.
Handles: shipment creation, label generation, tracking, cancellation.
WSDL: https://ws-customer.gls-spain.es/b2b.asmx?wsdl (or local fallback)
"""
import logging
import httpx
import base64
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

logger = logging.getLogger("gls_service")

GLS_URL = "https://ws-customer.gls-spain.es/b2b.asmx"
GLS_LABEL_URL = "https://wsclientes.asmred.com/b2b.asmx"
GLS_NS = "http://www.asmred.com/"

SERVICIOS_GLS = {
    "1": "BusinessParcel",
    "10": "10:00 Service",
    "14": "14:00 Service",
    "74": "EuroBusinessParcel",
    "96": "EconomyParcel",
}

HORARIOS_GLS = {
    "3": "Business Parcel (sin hora)",
    "10": "Entrega antes 10:00",
    "14": "Entrega antes 14:00",
    "18": "Sin franja horaria",
}


async def _soap_call(url: str, action: str, body_xml: str) -> str:
    """Execute raw SOAP 1.2 call and return response body text."""
    envelope = f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    {body_xml}
  </soap12:Body>
</soap12:Envelope>'''

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            content=envelope.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=UTF-8"}
        )
        response.raise_for_status()
        return response.text


def _parse_xml_response(text: str, ns_prefix: str = "asm") -> ET.Element:
    """Parse SOAP response, return root element."""
    root = ET.fromstring(text)
    # Strip namespaces for easier parsing
    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]
    return root


async def crear_envio(config: dict, envio_data: dict) -> dict:
    """
    Create a GLS shipment via GrabaServicios.
    config: {uid_cliente, remitente: {nombre, direccion, poblacion, cp, telefono, nif}}
    envio_data: {nombre_dst, direccion_dst, poblacion_dst, cp_dst, telefono_dst, email_dst,
                 referencia, observaciones, servicio, horario, bultos, peso, portes}
    Returns: {success, codbarras, uid_envio, error}
    """
    uid = config.get("uid_cliente", "")
    rem = config.get("remitente", {})
    
    fecha = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    servicio = envio_data.get("servicio", "1")
    horario = envio_data.get("horario", "18")
    bultos = envio_data.get("bultos", "1")
    peso = envio_data.get("peso", "1")
    portes = envio_data.get("portes", "P")  # P=Pagados, D=Debidos
    reembolso = envio_data.get("reembolso", "0")
    ref = envio_data.get("referencia", "")
    
    body = f'''<GrabaServicios xmlns="{GLS_NS}">
      <docIn>
        <Servicios uidcliente="{uid}" xmlns="{GLS_NS}">
          <Envio>
            <Fecha>{fecha}</Fecha>
            <Servicio>{servicio}</Servicio>
            <Horario>{horario}</Horario>
            <Bultos>{bultos}</Bultos>
            <Peso>{peso}</Peso>
            <Portes>{portes}</Portes>
            <Importes>
              <Reembolso>{reembolso}</Reembolso>
            </Importes>
            <Remite>
              <Nombre>{rem.get("nombre", "")}</Nombre>
              <Direccion>{rem.get("direccion", "")}</Direccion>
              <Poblacion>{rem.get("poblacion", "")}</Poblacion>
              <Pais>ES</Pais>
              <CP>{rem.get("cp", "")}</CP>
              <Telefono>{rem.get("telefono", "")}</Telefono>
            </Remite>
            <Destinatario>
              <Nombre>{envio_data.get("nombre_dst", "")}</Nombre>
              <Direccion>{envio_data.get("direccion_dst", "")}</Direccion>
              <Poblacion>{envio_data.get("poblacion_dst", "")}</Poblacion>
              <Pais>{envio_data.get("pais_dst", "ES")}</Pais>
              <CP>{envio_data.get("cp_dst", "")}</CP>
              <Telefono>{envio_data.get("telefono_dst", "")}</Telefono>
              <Email>{envio_data.get("email_dst", "")}</Email>
              <NIF>{envio_data.get("nif_dst", "")}</NIF>
              <Observaciones>{envio_data.get("observaciones", "")}</Observaciones>
            </Destinatario>
            <Referencias>
              <Referencia tipo="C">{ref}</Referencia>
            </Referencias>
          </Envio>
        </Servicios>
      </docIn>
    </GrabaServicios>'''

    try:
        resp_text = await _soap_call(GLS_URL, "GrabaServicios", body)
        root = _parse_xml_response(resp_text)
        
        envio_elem = root.find(".//Envio")
        if envio_elem is None:
            return {"success": False, "error": "Respuesta inesperada de GLS"}
        
        resultado = envio_elem.find(".//Resultado")
        ret_val = resultado.get("return", "") if resultado is not None else ""
        
        codbarras = envio_elem.get("codbarras", "")
        uid_envio = envio_elem.get("uid", "")
        
        if ret_val and ret_val != "0":
            return {"success": False, "error": f"GLS error code: {ret_val}", "codbarras": codbarras, "uid_envio": uid_envio}
        
        return {"success": True, "codbarras": codbarras, "uid_envio": uid_envio, "referencia": ref}
    except Exception as e:
        logger.error(f"Error creando envío GLS: {e}")
        return {"success": False, "error": str(e)}


async def crear_recogida(config: dict, recogida_data: dict) -> dict:
    """
    Create a GLS pickup (recogida) - same as envio but origin/destination swapped.
    The customer is the sender, the shop is the destination.
    """
    uid = config.get("uid_cliente", "")
    rem = config.get("remitente", {})
    
    fecha = recogida_data.get("fecha", datetime.now(timezone.utc).strftime("%d/%m/%Y"))
    servicio = recogida_data.get("servicio", "1")
    horario = recogida_data.get("horario", "18")
    ref = recogida_data.get("referencia", "")
    
    body = f'''<GrabaServicios xmlns="{GLS_NS}">
      <docIn>
        <Servicios uidcliente="{uid}" xmlns="{GLS_NS}">
          <Envio>
            <Fecha>{fecha}</Fecha>
            <Servicio>{servicio}</Servicio>
            <Horario>{horario}</Horario>
            <Bultos>{recogida_data.get("bultos", "1")}</Bultos>
            <Peso>{recogida_data.get("peso", "1")}</Peso>
            <Portes>P</Portes>
            <Importes><Reembolso>0</Reembolso></Importes>
            <Remite>
              <Nombre>{recogida_data.get("nombre_org", "")}</Nombre>
              <Direccion>{recogida_data.get("direccion_org", "")}</Direccion>
              <Poblacion>{recogida_data.get("poblacion_org", "")}</Poblacion>
              <Pais>ES</Pais>
              <CP>{recogida_data.get("cp_org", "")}</CP>
              <Telefono>{recogida_data.get("telefono_org", "")}</Telefono>
            </Remite>
            <Destinatario>
              <Nombre>{rem.get("nombre", "")}</Nombre>
              <Direccion>{rem.get("direccion", "")}</Direccion>
              <Poblacion>{rem.get("poblacion", "")}</Poblacion>
              <Pais>ES</Pais>
              <CP>{rem.get("cp", "")}</CP>
              <Telefono>{rem.get("telefono", "")}</Telefono>
              <Observaciones>{recogida_data.get("observaciones", "")}</Observaciones>
            </Destinatario>
            <Referencias>
              <Referencia tipo="C">{ref}</Referencia>
            </Referencias>
          </Envio>
        </Servicios>
      </docIn>
    </GrabaServicios>'''

    try:
        resp_text = await _soap_call(GLS_URL, "GrabaServicios", body)
        root = _parse_xml_response(resp_text)
        envio_elem = root.find(".//Envio")
        if envio_elem is None:
            return {"success": False, "error": "Respuesta inesperada de GLS"}
        
        codbarras = envio_elem.get("codbarras", "")
        uid_envio = envio_elem.get("uid", "")
        resultado = envio_elem.find(".//Resultado")
        ret_val = resultado.get("return", "") if resultado is not None else ""
        
        if ret_val and ret_val != "0":
            return {"success": False, "error": f"GLS error code: {ret_val}", "codbarras": codbarras}
        
        return {"success": True, "codbarras": codbarras, "uid_envio": uid_envio, "referencia": ref, "tipo": "recogida"}
    except Exception as e:
        logger.error(f"Error creando recogida GLS: {e}")
        return {"success": False, "error": str(e)}


async def obtener_etiqueta(uid_cliente: str, referencia: str, tipo: str = "PDF") -> dict:
    """
    Get shipment label via EtiquetaEnvioV2.
    tipo: PDF, PNG, JPG, ZPL
    Returns: {success, etiqueta_base64, content_type}
    """
    body = f'''<EtiquetaEnvioV2 xmlns="{GLS_NS}">
      <uidcliente>{uid_cliente}</uidcliente>
      <codigo>{referencia}</codigo>
      <tipoEtiqueta>{tipo.upper()}</tipoEtiqueta>
    </EtiquetaEnvioV2>'''

    try:
        resp_text = await _soap_call(GLS_LABEL_URL, "EtiquetaEnvioV2", body)
        root = _parse_xml_response(resp_text)
        
        etiquetas = root.findall(".//Etiqueta")
        if not etiquetas:
            return {"success": False, "error": "No se encontraron etiquetas"}
        
        label_b64 = etiquetas[0].text or ""
        content_types = {"PDF": "application/pdf", "PNG": "image/png", "JPG": "image/jpeg", "ZPL": "text/plain"}
        
        return {"success": True, "etiqueta_base64": label_b64, "content_type": content_types.get(tipo.upper(), "application/pdf")}
    except Exception as e:
        logger.error(f"Error obteniendo etiqueta GLS: {e}")
        return {"success": False, "error": str(e)}


async def obtener_etiqueta_recogida(uid_cliente: str, referencia: str, tipo: str = "PDF") -> dict:
    """Get pickup label via EtiquetaEnvioRecogidas."""
    body = f'''<EtiquetaEnvioRecogidas xmlns="{GLS_NS}">
      <uidCliente>{uid_cliente}</uidCliente>
      <codigo>{referencia}</codigo>
      <tipoEtiqueta>{tipo.upper()}</tipoEtiqueta>
    </EtiquetaEnvioRecogidas>'''

    try:
        resp_text = await _soap_call(GLS_LABEL_URL, "EtiquetaEnvioRecogidas", body)
        root = _parse_xml_response(resp_text)
        
        etiquetas = root.findall(".//Etiqueta")
        if not etiquetas:
            return {"success": False, "error": "No se encontraron etiquetas de recogida"}
        
        label_b64 = etiquetas[0].text or ""
        content_types = {"PDF": "application/pdf", "PNG": "image/png", "JPG": "image/jpeg"}
        return {"success": True, "etiqueta_base64": label_b64, "content_type": content_types.get(tipo.upper(), "application/pdf")}
    except Exception as e:
        logger.error(f"Error obteniendo etiqueta recogida GLS: {e}")
        return {"success": False, "error": str(e)}


async def consultar_envio(uid_cliente: str, referencia: str) -> dict:
    """
    Get shipment details + tracking via GetExpCli.
    Returns: {success, expedicion, tracking_list, estado, ...}
    """
    body = f'''<GetExpCli xmlns="{GLS_NS}">
      <codigo>{referencia}</codigo>
      <uid>{uid_cliente}</uid>
    </GetExpCli>'''

    try:
        resp_text = await _soap_call(GLS_URL, "GetExpCli", body)
        root = _parse_xml_response(resp_text)
        
        exps = root.findall(".//exp")
        if not exps:
            return {"success": False, "error": "No se encontró el envío"}
        
        exp = exps[0]
        result = {
            "success": True,
            "expedicion": _text(exp, "expedicion"),
            "albaran": _text(exp, "albaran"),
            "codexp": _text(exp, "codexp"),
            "codbarras": _text(exp, "codbar"),
            "uid_envio": _text(exp, "uidExp"),
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
            "borrado": _text(exp, "borrado"),
        }
        
        # Parse tracking list
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
    except Exception as e:
        logger.error(f"Error consultando envío GLS: {e}")
        return {"success": False, "error": str(e)}


async def anular_envio(uid_cliente: str, referencia: str) -> dict:
    """Cancel a GLS shipment via Anula."""
    body = f'''<Anula xmlns="{GLS_NS}">
      <docIn>
        <Servicios uidcliente="{uid_cliente}" xmlns="{GLS_NS}">
          <Envio>
            <Referencias>
              <Referencia tipo="C">{referencia}</Referencia>
            </Referencias>
          </Envio>
        </Servicios>
      </docIn>
    </Anula>'''

    try:
        resp_text = await _soap_call(GLS_URL, "Anula", body)
        root = _parse_xml_response(resp_text)
        resultado = root.find(".//Resultado")
        ret_val = resultado.get("return", "") if resultado is not None else ""
        
        if ret_val == "0":
            return {"success": True, "message": "Envío anulado correctamente"}
        return {"success": False, "error": f"Error anulando: code {ret_val}"}
    except Exception as e:
        logger.error(f"Error anulando envío GLS: {e}")
        return {"success": False, "error": str(e)}


def _text(elem, tag, default=""):
    """Safely get text from XML element."""
    child = elem.find(tag)
    return (child.text or default) if child is not None else default

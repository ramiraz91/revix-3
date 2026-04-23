"""
GLS Spain — Cliente SOAP 1.2 (b2b.asmx).

Endpoint prod : https://ws-customer.gls-spain.es/b2b.asmx
Protocolo     : SOAP 1.2, text/xml; charset=UTF-8
Autenticación : uidcliente (UUID) dentro del XML
Namespace     : http://www.asmred.com/

Operaciones:
  - GrabaServicios → crear envío y obtener etiqueta PDF base64
  - GetExpCli      → tracking por referencia cliente (RefC) o codbarras

Modo preview (MCP_ENV=preview): NUNCA llama a GLS. Devuelve mock determinista
con un PDF mínimo válido en base64.

Construcción: httpx async + xml.etree.ElementTree (sin zeep/suds).
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger("gls.logistica")


# ──────────────────────────────────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────────────────────────────────

GLS_URL_DEFAULT = "https://ws-customer.gls-spain.es/b2b.asmx"
GLS_NAMESPACE = "http://www.asmred.com/"
SOAP12_NS = "http://www.w3.org/2003/05/soap-envelope"
TIMEOUT_SECONDS = 30

# PDF mock: 1 página A6 con texto "MOCK GLS LABEL {codbarras}". Es un PDF válido
# de ~900 bytes que cualquier visor abre. Generado estáticamente (no necesita
# dependencias como reportlab).
_MOCK_PDF_TEMPLATE = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 297 419]"
    b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 90>>stream\n"
    b"BT /F1 14 Tf 20 380 Td (MOCK GLS LABEL) Tj "
    b"0 -20 Td /F1 10 Tf (codbarras: __CODBARRAS__) Tj ET\n"
    b"endstream endobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"xref\n0 6\n0000000000 65535 f \n"
    b"0000000009 00000 n \n0000000052 00000 n \n0000000097 00000 n \n"
    b"0000000187 00000 n \n0000000320 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n385\n%%EOF\n"
)


# ──────────────────────────────────────────────────────────────────────────────
# Excepciones y tipos
# ──────────────────────────────────────────────────────────────────────────────

class GLSError(Exception):
    """Error devuelto por GLS o de transporte."""

    def __init__(self, message: str, *, code: str = "", raw: str = ""):
        super().__init__(message)
        self.code = code
        self.raw = raw


@dataclass
class Destinatario:
    nombre: str
    direccion: str
    cp: str
    poblacion: str = ""
    provincia: str = ""
    telefono: str = ""
    movil: str = ""
    email: str = ""
    observaciones: str = ""


@dataclass
class Remitente:
    nombre: str
    direccion: str
    cp: str
    poblacion: str = ""
    provincia: str = ""
    telefono: str = ""
    pais: str = "34"


@dataclass
class ResultadoEnvio:
    success: bool
    codbarras: str
    uid: str
    etiqueta_pdf_base64: str
    referencia: str
    raw_request: str = ""
    raw_response: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "codbarras": self.codbarras,
            "uid": self.uid,
            "etiqueta_pdf_base64": self.etiqueta_pdf_base64,
            "referencia": self.referencia,
        }


@dataclass
class EventoTracking:
    fecha: str
    estado: str
    plaza: str
    codigo: str

    def to_dict(self) -> dict:
        return {"fecha": self.fecha, "estado": self.estado,
                "plaza": self.plaza, "codigo": self.codigo}


@dataclass
class ResultadoTracking:
    success: bool
    codbarras: str
    estado_actual: str
    estado_codigo: str
    fecha_entrega: str
    eventos: list[EventoTracking]
    incidencia: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "codbarras": self.codbarras,
            "estado_actual": self.estado_actual,
            "estado_codigo": self.estado_codigo,
            "fecha_entrega": self.fecha_entrega,
            "incidencia": self.incidencia,
            "eventos": [e.to_dict() for e in self.eventos],
        }


# ──────────────────────────────────────────────────────────────────────────────
# Cliente GLS
# ──────────────────────────────────────────────────────────────────────────────

class GLSClient:
    """
    Cliente para la API SOAP 1.2 de GLS Spain.

    Uso:
        client = GLSClient(uid_cliente="UUID", remitente=Remitente(...))
        resultado = await client.crear_envio(order_id="OT-123", destinatario=..., peso=2.5)
        tracking  = await client.obtener_tracking(codbarras="...")

    En MCP_ENV=preview devuelve mocks deterministas sin llamar a GLS.
    """

    def __init__(
        self,
        uid_cliente: str,
        remitente: Remitente,
        *,
        url: Optional[str] = None,
        mcp_env: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.uid_cliente = uid_cliente
        self.remitente = remitente
        self.url = url or os.environ.get("GLS_URL") or GLS_URL_DEFAULT
        self.mcp_env = (mcp_env or os.environ.get("MCP_ENV") or "production").lower()
        self._http = http_client  # Inyectable para tests

    # ──────────────────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────────────────

    async def crear_envio(
        self,
        order_id: str,
        destinatario: Destinatario,
        peso: float,
        *,
        referencia: Optional[str] = None,
    ) -> ResultadoEnvio:
        """
        Crea un envío en GLS y devuelve codbarras + uid + etiqueta PDF base64.

        Lanza GLSError si GLS devuelve Resultado return != "0".
        """
        ref = referencia or order_id
        if self.mcp_env == "preview":
            return self._mock_crear_envio(order_id=order_id, referencia=ref)

        self._ensure_configured()
        xml_request = self._build_graba_servicios_xml(
            destinatario=destinatario, peso=peso, referencia=ref,
        )
        response_text = await self._soap_call(
            action="GrabaServicios", body_xml=xml_request,
        )
        return self._parse_graba_servicios_response(
            response_text, referencia=ref, raw_request=xml_request,
        )

    async def obtener_tracking(self, codbarras: str) -> ResultadoTracking:
        """
        Consulta el estado de un envío por codbarras (o referencia cliente).

        En preview devuelve un estado simulado "EN_REPARTO" con 2 eventos.
        """
        if self.mcp_env == "preview":
            return self._mock_tracking(codbarras)

        self._ensure_configured()
        xml_body = self._build_get_exp_cli_xml(codigo=codbarras)
        response_text = await self._soap_call(
            action="GetExpCli", body_xml=xml_body,
        )
        return self._parse_get_exp_cli_response(response_text, codbarras)

    # ──────────────────────────────────────────────────────────────────────
    # Construcción de XML (SOAP 1.2 + CDATA, según spec del usuario)
    # ──────────────────────────────────────────────────────────────────────

    def _build_graba_servicios_xml(
        self, destinatario: Destinatario, peso: float, referencia: str,
    ) -> str:
        fecha = datetime.now(timezone.utc).strftime("%d/%m/%Y")
        r = self.remitente
        d = destinatario

        # Peso con coma decimal (formato español) para GLS.
        peso_str = f"{float(peso):.2f}".replace(".", ",")

        return f'''<GrabaServicios xmlns="{GLS_NAMESPACE}">
<docIn>
  <Servicios uidcliente="{self.uid_cliente}" xmlns="{GLS_NAMESPACE}">
  <Envio codbarras="">
    <Fecha>{fecha}</Fecha>
    <Portes>P</Portes>
    <Servicio>96</Servicio>
    <Horario>18</Horario>
    <Bultos>1</Bultos>
    <Peso>{peso_str}</Peso>
    <Retorno>0</Retorno>
    <Pod>N</Pod>
    <Remite>
      <Nombre><![CDATA[{r.nombre}]]></Nombre>
      <Direccion><![CDATA[{r.direccion}]]></Direccion>
      <Poblacion><![CDATA[{r.poblacion}]]></Poblacion>
      <Provincia><![CDATA[{r.provincia}]]></Provincia>
      <Pais>{r.pais}</Pais>
      <CP>{r.cp}</CP>
      <Telefono><![CDATA[{r.telefono}]]></Telefono>
    </Remite>
    <Destinatario>
      <Nombre><![CDATA[{d.nombre}]]></Nombre>
      <Direccion><![CDATA[{d.direccion}]]></Direccion>
      <Poblacion><![CDATA[{d.poblacion}]]></Poblacion>
      <Provincia><![CDATA[{d.provincia}]]></Provincia>
      <Pais>34</Pais>
      <CP>{d.cp}</CP>
      <Telefono><![CDATA[{d.telefono}]]></Telefono>
      <Movil><![CDATA[{d.movil}]]></Movil>
      <Email><![CDATA[{d.email}]]></Email>
      <Observaciones><![CDATA[{d.observaciones}]]></Observaciones>
    </Destinatario>
    <Referencias>
      <Referencia tipo="C"><![CDATA[{referencia}]]></Referencia>
    </Referencias>
    <DevuelveAdicionales>
      <Etiqueta tipo="PDF"></Etiqueta>
    </DevuelveAdicionales>
  </Envio>
  </Servicios>
</docIn>
</GrabaServicios>'''

    def _build_get_exp_cli_xml(self, codigo: str) -> str:
        return f'''<GetExpCli xmlns="{GLS_NAMESPACE}">
  <codigo>{codigo}</codigo>
  <uid>{self.uid_cliente}</uid>
</GetExpCli>'''

    def _wrap_soap12(self, body_xml: str) -> str:
        return f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xmlns:xsd="http://www.w3.org/2001/XMLSchema" \
xmlns:soap12="{SOAP12_NS}">
<soap12:Body>
{body_xml}
</soap12:Body>
</soap12:Envelope>'''

    # ──────────────────────────────────────────────────────────────────────
    # Transporte SOAP
    # ──────────────────────────────────────────────────────────────────────

    async def _soap_call(self, action: str, body_xml: str) -> str:
        envelope = self._wrap_soap12(body_xml)
        # En SOAP 1.2 el action va codificado en el Content-Type con action=...
        headers = {
            "Content-Type": (
                f'application/soap+xml; charset=utf-8; '
                f'action="{GLS_NAMESPACE}{action}"'
            ),
        }
        logger.debug("GLS → %s (%d bytes)", action, len(envelope))

        close_after = False
        client = self._http
        if client is None:
            client = httpx.AsyncClient(timeout=TIMEOUT_SECONDS)
            close_after = True
        try:
            resp = await client.post(self.url, content=envelope, headers=headers)
        except httpx.TimeoutException as exc:
            raise GLSError(f"Timeout llamando a GLS: {exc}") from exc
        except httpx.HTTPError as exc:
            raise GLSError(f"Error HTTP llamando a GLS: {exc}") from exc
        finally:
            if close_after:
                await client.aclose()

        if resp.status_code != 200:
            raise GLSError(
                f"GLS devolvió HTTP {resp.status_code}",
                code=str(resp.status_code),
                raw=resp.text[:2000],
            )
        text = resp.text or ""
        # Sanidad: si GLS devuelve HTML (por error de auth/endpoint), cortocircuitar
        if text.lstrip().lower().startswith("<html") or not text.lstrip().startswith("<"):
            raise GLSError(
                "Respuesta inválida de GLS (no es XML). Verifica endpoint y credenciales.",
                raw=text[:500],
            )
        return text

    # ──────────────────────────────────────────────────────────────────────
    # Parseo de respuestas
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _localname(tag: str) -> str:
        return tag.split("}", 1)[1] if "}" in tag else tag

    @classmethod
    def _find_by_localname(cls, root: ET.Element, name: str) -> Optional[ET.Element]:
        for el in root.iter():
            if cls._localname(el.tag) == name:
                return el
        return None

    @classmethod
    def _findall_by_localname(cls, root: ET.Element, name: str) -> list[ET.Element]:
        return [el for el in root.iter() if cls._localname(el.tag) == name]

    def _parse_graba_servicios_response(
        self, response_text: str, *, referencia: str, raw_request: str,
    ) -> ResultadoEnvio:
        try:
            root = ET.fromstring(response_text)
        except ET.ParseError as exc:
            raise GLSError(
                f"XML malformado de GLS: {exc}", raw=response_text[:1000],
            ) from exc

        envio_el = self._find_by_localname(root, "Envio")
        if envio_el is None:
            raise GLSError(
                "Respuesta de GLS sin nodo <Envio>",
                raw=response_text[:1000],
            )

        codbarras = envio_el.get("codbarras", "")
        uid = envio_el.get("uid", "")

        # Resultado / error code
        resultado_el = self._find_by_localname(envio_el, "Resultado")
        return_code = resultado_el.get("return", "") if resultado_el is not None else ""
        if return_code and return_code != "0":
            # Intentar extraer mensaje legible
            err_text = ""
            errores_el = self._find_by_localname(envio_el, "Errores")
            if errores_el is not None:
                if errores_el.text and errores_el.text.strip():
                    err_text = errores_el.text.strip()
                else:
                    err_text = "; ".join(
                        (e.text or "").strip() for e in errores_el if e.text
                    )
            if not err_text and resultado_el is not None:
                err_text = (resultado_el.get("result")
                            or resultado_el.text or "Error desconocido")
            raise GLSError(
                f"GLS rechazó el envío (return={return_code}): {err_text}",
                code=return_code,
                raw=response_text[:2000],
            )

        if not codbarras:
            raise GLSError(
                "GLS no devolvió codbarras",
                raw=response_text[:1000],
            )

        # Etiqueta PDF en base64
        etiqueta_b64 = ""
        etiqueta_el = self._find_by_localname(envio_el, "Etiqueta")
        if etiqueta_el is not None and etiqueta_el.text and etiqueta_el.text.strip():
            etiqueta_b64 = etiqueta_el.text.strip()
        else:
            # A veces viene dentro de <Etiquetas><Etiqueta>...
            for el in self._findall_by_localname(root, "Etiqueta"):
                if el.text and el.text.strip():
                    etiqueta_b64 = el.text.strip()
                    break

        return ResultadoEnvio(
            success=True,
            codbarras=codbarras,
            uid=uid,
            etiqueta_pdf_base64=etiqueta_b64,
            referencia=referencia,
            raw_request=raw_request,
            raw_response=response_text[:5000],
        )

    def _parse_get_exp_cli_response(
        self, response_text: str, codbarras: str,
    ) -> ResultadoTracking:
        try:
            root = ET.fromstring(response_text)
        except ET.ParseError as exc:
            raise GLSError(
                f"XML malformado de GLS: {exc}", raw=response_text[:1000],
            ) from exc

        exp_el = self._find_by_localname(root, "exp")
        if exp_el is None:
            return ResultadoTracking(
                success=False, codbarras=codbarras, estado_actual="",
                estado_codigo="", fecha_entrega="", eventos=[], incidencia="",
            )

        def _txt(parent: ET.Element, name: str) -> str:
            el = self._find_by_localname(parent, name)
            return (el.text or "").strip() if el is not None and el.text else ""

        estado_actual = _txt(exp_el, "estado")
        estado_codigo = _txt(exp_el, "codestado")
        fecha_entrega = _txt(exp_el, "FPEntrega") or _txt(exp_el, "fecha")
        incidencia = _txt(exp_el, "incidencia")

        eventos: list[EventoTracking] = []
        for t_el in self._findall_by_localname(exp_el, "tracking"):
            eventos.append(EventoTracking(
                fecha=_txt(t_el, "fecha"),
                estado=_txt(t_el, "evento"),
                plaza=_txt(t_el, "nombreplaza") or _txt(t_el, "plaza"),
                codigo=_txt(t_el, "codigo"),
            ))

        return ResultadoTracking(
            success=True,
            codbarras=codbarras,
            estado_actual=estado_actual,
            estado_codigo=estado_codigo,
            fecha_entrega=fecha_entrega,
            eventos=eventos,
            incidencia=incidencia,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Mocks preview
    # ──────────────────────────────────────────────────────────────────────

    def _mock_crear_envio(self, order_id: str, referencia: str) -> ResultadoEnvio:
        # Codbarras determinista: 14 dígitos derivados del order_id
        digest = hashlib.sha1(order_id.encode("utf-8")).hexdigest()
        codbarras = ("9" + "".join(c for c in digest if c.isdigit()))[:14]
        while len(codbarras) < 14:
            codbarras += "0"
        uid_env = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"gls-preview-{order_id}"))
        pdf_bytes = _MOCK_PDF_TEMPLATE.replace(
            b"__CODBARRAS__", codbarras.encode("ascii"),
        )
        pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
        logger.info("GLS[preview] crear_envio order=%s → codbarras=%s",
                    order_id, codbarras)
        return ResultadoEnvio(
            success=True,
            codbarras=codbarras,
            uid=uid_env,
            etiqueta_pdf_base64=pdf_b64,
            referencia=referencia,
            raw_request="<preview-mode/>",
            raw_response="<preview-mode/>",
        )

    def _mock_tracking(self, codbarras: str) -> ResultadoTracking:
        now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        eventos = [
            EventoTracking(
                fecha=now, estado="ADMITIDO EN CENTRO",
                plaza="MADRID", codigo="1",
            ),
            EventoTracking(
                fecha=now, estado="EN REPARTO",
                plaza="MADRID", codigo="6",
            ),
        ]
        return ResultadoTracking(
            success=True,
            codbarras=codbarras,
            estado_actual="EN REPARTO",
            estado_codigo="6",
            fecha_entrega="",
            eventos=eventos,
            incidencia="",
        )

    # ──────────────────────────────────────────────────────────────────────
    # Guards
    # ──────────────────────────────────────────────────────────────────────

    def _ensure_configured(self) -> None:
        if not self.uid_cliente:
            raise GLSError(
                "GLS_UID_CLIENTE no configurado. Define la variable de entorno "
                "o activa MCP_ENV=preview para usar mocks.",
            )
        if not self.remitente or not self.remitente.nombre or not self.remitente.cp:
            raise GLSError("Remitente GLS sin configurar (nombre y CP requeridos).")

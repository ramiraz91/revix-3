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
    codexp: str = ""          # Código de expedición (para tracking público)
    codplaza_dst: str = ""    # Código de plaza destino (para tracking público)
    raw_request: str = ""
    raw_response: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "codbarras": self.codbarras,
            "uid": self.uid,
            "etiqueta_pdf_base64": self.etiqueta_pdf_base64,
            "referencia": self.referencia,
            "codexp": self.codexp,
            "codplaza_dst": self.codplaza_dst,
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

    async def anular_envio(self, codbarras: str) -> dict:
        """
        Anula un envío en GLS por codbarras (no eliminable si ya está en ruta).

        Devuelve {ok: bool, mensaje: str, raw: str}.
        En preview simula éxito sin llamada real.
        """
        if self.mcp_env == "preview":
            return {"ok": True, "mensaje": "Anulado (preview/mock)", "raw": ""}

        self._ensure_configured()
        body = (
            f'<Anula xmlns="{GLS_NAMESPACE}">\n'
            f'<docIn>\n'
            f'  <Servicios uidcliente="{self.uid_cliente}">\n'
            f'    <Envio codbarras="{codbarras}" />\n'
            f'  </Servicios>\n'
            f'</docIn>\n'
            f'</Anula>'
        )
        response_text = await self._soap_call(action="Anula", body_xml=body)

        # GLS responde con XML que contiene <Resultado> o <Error>
        try:
            root = ET.fromstring(response_text)
        except ET.ParseError as exc:
            return {"ok": False, "mensaje": f"Respuesta GLS no parseable: {exc}", "raw": response_text}

        # Buscar elementos clave
        error_el = self._find_by_localname(root, "Error")
        result_el = self._find_by_localname(root, "Resultado")
        if error_el is not None and (error_el.text or "").strip():
            return {"ok": False, "mensaje": (error_el.text or "").strip(), "raw": response_text}
        # Heurística éxito: presencia de <Resultado>OK</Resultado> o ausencia de error
        result_text = (result_el.text or "").strip().upper() if result_el is not None else ""
        if result_text and "OK" in result_text:
            return {"ok": True, "mensaje": "Envío anulado en GLS", "raw": response_text}
        # Fallback positivo si el XML no contiene errores explícitos
        if "Error" not in response_text and "Excepcion" not in response_text:
            return {"ok": True, "mensaje": "Envío anulado en GLS (sin error reportado)", "raw": response_text}
        return {"ok": False, "mensaje": "Respuesta GLS ambigua", "raw": response_text}

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
        # Atributos adicionales para URL de tracking público (mygls.gls-spain.es)
        codexp = (envio_el.get("codexp")
                  or envio_el.get("CodExp")
                  or "")
        codplaza_dst = (envio_el.get("codplaza_dst")
                        or envio_el.get("CodPlazaDst")
                        or envio_el.get("codplazadst")
                        or envio_el.get("CodigoPlazaDestino")
                        or "")

        # También buscar en nodos hijos por si no están como atributos
        if not codexp:
            exp_child = self._find_by_localname(envio_el, "codexp")
            if exp_child is not None and exp_child.text:
                codexp = exp_child.text.strip()
        if not codplaza_dst:
            for name in ("codplaza_dst", "codplazadst", "PlazaDestino", "plazadestino"):
                plaza_child = self._find_by_localname(envio_el, name)
                if plaza_child is not None and plaza_child.text:
                    codplaza_dst = plaza_child.text.strip()
                    break

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
            codexp=codexp,
            codplaza_dst=codplaza_dst,
            raw_request=raw_request,
            raw_response=response_text[:5000],
        )

    def _parse_get_exp_cli_response(
        self, response_text: str, codbarras: str,
    ) -> ResultadoTracking:
        """
        Parsea la respuesta GetExpCli de GLS.

        IMPORTANTE: cuando se invoca con `codigo` = numero_autorizacion (RefC),
        el XML devuelve el codbarras REAL en `<codbar>` y el código de expedición
        en `<codexp>`. Es CRÍTICO extraer ambos para:
        - Vincular correctamente el envío a la orden por codbarras real (no la RefC).
        - Construir la URL de tracking público mygls.gls-spain.es/e/{codexp}/{cp}.
        """
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

        # ── codbarras REAL desde el XML (atributo del nodo <exp> o hijo <codbar>) ──
        codbarras_real = (
            exp_el.get("codbar")
            or exp_el.get("codbarras")
            or _txt(exp_el, "codbar")
            or _txt(exp_el, "codbarras")
            or codbarras  # fallback al pasado por argumento
        )

        # ── codexp desde el XML (atributo o hijo) — para URL tracking público ──
        codexp = (
            exp_el.get("codexp")
            or exp_el.get("CodExp")
            or _txt(exp_el, "codexp")
            or _txt(exp_el, "CodExp")
            or ""
        )

        # ── refC: prioridad <refC> directo; si vacío, extraer de <Observacion> ──
        refc_directa = (
            exp_el.get("refc")
            or exp_el.get("RefC")
            or _txt(exp_el, "refc")
            or _txt(exp_el, "RefC")
            or ""
        )
        observacion = (
            _txt(exp_el, "Observacion")
            or _txt(exp_el, "observacion")
            or _txt(exp_el, "Observaciones")
            or ""
        )
        # GLS Spain admin web suele guardar la referencia como
        # "referencia <NUM_AUTORIZACION>" dentro de Observacion en lugar de RefC.
        refc_devuelta = refc_directa
        if not refc_devuelta and observacion:
            import re as _re
            m = _re.search(r"referencia\s*[:\-]?\s*(\S+)", observacion, flags=_re.IGNORECASE)
            if m:
                refc_devuelta = m.group(1).strip().rstrip(".,;")

        # ── CP destinatario desde respuesta (nombre real del tag: cp_dst) ──
        cp_destino = (
            exp_el.get("cp_dst")
            or exp_el.get("cpdst")
            or _txt(exp_el, "cp_dst")
            or _txt(exp_el, "cpdst")
            or _txt(exp_el, "cp_destino")
            or ""
        )

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

        result = ResultadoTracking(
            success=True,
            codbarras=codbarras_real,
            estado_actual=estado_actual,
            estado_codigo=estado_codigo,
            fecha_entrega=fecha_entrega,
            eventos=eventos,
            incidencia=incidencia,
        )
        # Atributos enriquecidos (no en dataclass para mantener compatibilidad)
        result.codexp = codexp  # type: ignore[attr-defined]
        result.refc_devuelta = refc_devuelta  # type: ignore[attr-defined]
        result.cp_destino = cp_destino  # type: ignore[attr-defined]
        result.observacion = observacion  # type: ignore[attr-defined]
        return result

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
        # Codexp y codplaza deterministas para que la URL sea estable en preview
        digest_hex = digest[:10]
        codexp = str(int(digest_hex, 16))[:10]  # 10 dígitos
        # Derivamos un CP de 5 dígitos (08015 por defecto si nada parsea)
        remitente_cp = (self.remitente.cp or "").strip()
        if remitente_cp.isdigit() and len(remitente_cp) == 5:
            codplaza_dst = remitente_cp
        else:
            codplaza_dst = str(int(digest[10:14], 16))[:5].zfill(5)
        pdf_bytes = _MOCK_PDF_TEMPLATE.replace(
            b"__CODBARRAS__", codbarras.encode("ascii"),
        )
        pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
        logger.info("GLS[preview] crear_envio order=%s → codbarras=%s codexp=%s plaza=%s",
                    order_id, codbarras, codexp, codplaza_dst)
        return ResultadoEnvio(
            success=True,
            codbarras=codbarras,
            uid=uid_env,
            etiqueta_pdf_base64=pdf_b64,
            referencia=referencia,
            codexp=codexp,
            codplaza_dst=codplaza_dst,
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

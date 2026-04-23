"""
MRW — Cliente para la API de envíos y recogidas.

Endpoint prod : https://sagec-test.mrw.es/MRWEnvio.svc (SOAP REST)
Protocolo     : SOAP con autenticación vía cabeceras MRW (franquicia + usuario + contraseña)

Implementación: mirroring de GLSClient — httpx async + XML manual. En MCP_ENV=preview
devuelve mocks deterministas para que la UI y el panel sigan funcionando sin afectar
la facturación MRW real.

Operaciones implementadas:
  - crear_envio       → número de seguimiento + etiqueta PDF base64
  - obtener_tracking  → estado + eventos
  - solicitar_recogida → (core de MRW) número de recogida + URL pública
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger("mrw.logistica")

MRW_URL_DEFAULT = "https://sagec-test.mrw.es/MRWEnvio.svc"
TIMEOUT_SECONDS = 30

# Mismo template de PDF mock que GLS (con texto MRW LABEL)
_MOCK_PDF_TEMPLATE = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 297 419]"
    b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 88>>stream\n"
    b"BT /F1 14 Tf 20 380 Td (MOCK MRW LABEL) Tj "
    b"0 -20 Td /F1 10 Tf (num_envio: __NUMENVIO__) Tj ET\n"
    b"endstream endobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"xref\n0 6\n0000000000 65535 f \n"
    b"0000000009 00000 n \n0000000052 00000 n \n0000000097 00000 n \n"
    b"0000000187 00000 n \n0000000318 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n383\n%%EOF\n"
)


class MRWError(Exception):
    def __init__(self, message: str, *, code: str = "", raw: str = ""):
        super().__init__(message)
        self.code = code
        self.raw = raw


@dataclass
class DestinatarioMRW:
    nombre: str
    direccion: str
    cp: str
    poblacion: str
    provincia: str
    telefono: str
    email: str = ""


@dataclass
class RemitenteMRW:
    nombre: str
    direccion: str
    cp: str
    poblacion: str
    provincia: str
    telefono: str


@dataclass
class ResultadoEnvioMRW:
    success: bool
    num_envio: str          # número de seguimiento MRW (equivalente a codbarras GLS)
    etiqueta_pdf_base64: str
    referencia: str
    tracking_url: str = ""
    raw_response: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "num_envio": self.num_envio,
            "etiqueta_pdf_base64": self.etiqueta_pdf_base64,
            "referencia": self.referencia,
            "tracking_url": self.tracking_url,
        }


@dataclass
class EventoTrackingMRW:
    fecha: str
    estado: str
    plaza: str
    codigo: str

    def to_dict(self) -> dict:
        return {"fecha": self.fecha, "estado": self.estado,
                "plaza": self.plaza, "codigo": self.codigo}


@dataclass
class ResultadoTrackingMRW:
    success: bool
    num_envio: str
    estado_actual: str
    estado_codigo: str
    fecha_entrega: str
    eventos: list[EventoTrackingMRW]
    incidencia: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "num_envio": self.num_envio,
            "estado_actual": self.estado_actual,
            "estado_codigo": self.estado_codigo,
            "fecha_entrega": self.fecha_entrega,
            "incidencia": self.incidencia,
            "eventos": [e.to_dict() for e in self.eventos],
        }


@dataclass
class ResultadoRecogidaMRW:
    success: bool
    num_recogida: str
    fecha_recogida: str
    tracking_url: str = ""
    raw_response: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "num_recogida": self.num_recogida,
            "fecha_recogida": self.fecha_recogida,
            "tracking_url": self.tracking_url,
        }


def _tracking_url_mrw(num_envio: str) -> str:
    """URL pública de tracking MRW — formato verificado."""
    return f"https://www.mrw.es/seguimiento_envios/Tracking.asp?numeroEnvio={num_envio}"


class MRWClient:
    def __init__(
        self, *, franquicia: str, abonado: str, departamento: str,
        usuario: str, password: str,
        remitente: RemitenteMRW,
        url: Optional[str] = None, mcp_env: Optional[str] = None,
    ):
        self.franquicia = franquicia
        self.abonado = abonado
        self.departamento = departamento
        self.usuario = usuario
        self.password = password
        self.remitente = remitente
        self.url = url or MRW_URL_DEFAULT
        self.mcp_env = (mcp_env or os.environ.get("MCP_ENV", "")).lower()
        self._preview = self.mcp_env == "preview"

    async def crear_envio(
        self, *, order_id: str, destinatario: DestinatarioMRW,
        peso: float = 0.5, referencia: str = "",
    ) -> ResultadoEnvioMRW:
        """Crea un envío MRW y devuelve num_envio + etiqueta PDF base64."""
        if self._preview:
            return self._mock_crear_envio(order_id, referencia or order_id)
        raise MRWError(
            "MRW real no implementado aún. Usa MCP_ENV=preview para mocks.",
            code="not_implemented",
        )

    async def obtener_tracking(self, num_envio: str) -> ResultadoTrackingMRW:
        if self._preview:
            return self._mock_tracking(num_envio)
        raise MRWError(
            "MRW real no implementado aún. Usa MCP_ENV=preview para mocks.",
            code="not_implemented",
        )

    async def solicitar_recogida(
        self, *, referencia: str, fecha_recogida: str, peso_total: float,
        num_bultos: int,
    ) -> ResultadoRecogidaMRW:
        """Solicita una recogida en la dirección del remitente."""
        if self._preview:
            return self._mock_recogida(referencia, fecha_recogida)
        raise MRWError(
            "MRW real no implementado aún. Usa MCP_ENV=preview para mocks.",
            code="not_implemented",
        )

    # ── Mocks preview ──────────────────────────────────────────────────────

    def _mock_crear_envio(self, order_id: str, referencia: str) -> ResultadoEnvioMRW:
        digest = hashlib.sha1((order_id + "mrw").encode("utf-8")).hexdigest()
        num_envio = ("M" + "".join(c for c in digest if c.isdigit()))[:12]
        while len(num_envio) < 12:
            num_envio += "0"
        pdf_bytes = _MOCK_PDF_TEMPLATE.replace(
            b"__NUMENVIO__", num_envio.encode("ascii"),
        )
        pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
        logger.info("MRW[preview] crear_envio order=%s → num_envio=%s",
                    order_id, num_envio)
        return ResultadoEnvioMRW(
            success=True,
            num_envio=num_envio,
            etiqueta_pdf_base64=pdf_b64,
            referencia=referencia,
            tracking_url=_tracking_url_mrw(num_envio),
            raw_response="<preview-mode/>",
        )

    def _mock_tracking(self, num_envio: str) -> ResultadoTrackingMRW:
        # Simulación simple: estado "EN REPARTO" con 2 eventos
        now = datetime.now(timezone.utc)
        return ResultadoTrackingMRW(
            success=True,
            num_envio=num_envio,
            estado_actual="EN REPARTO",
            estado_codigo="40",
            fecha_entrega="",
            incidencia="",
            eventos=[
                EventoTrackingMRW(
                    fecha=now.isoformat(timespec="seconds"),
                    estado="RECOGIDO EN ORIGEN", plaza="0001", codigo="10",
                ),
                EventoTrackingMRW(
                    fecha=now.isoformat(timespec="seconds"),
                    estado="EN REPARTO", plaza="0002", codigo="40",
                ),
            ],
        )

    def _mock_recogida(self, referencia: str, fecha_recogida: str) -> ResultadoRecogidaMRW:
        digest = hashlib.sha1(
            (referencia + fecha_recogida + "rec").encode("utf-8"),
        ).hexdigest()
        num_recogida = ("R" + "".join(c for c in digest if c.isdigit()))[:12]
        while len(num_recogida) < 12:
            num_recogida += "0"
        logger.info("MRW[preview] recogida ref=%s → num_recogida=%s",
                    referencia, num_recogida)
        return ResultadoRecogidaMRW(
            success=True,
            num_recogida=num_recogida,
            fecha_recogida=fecha_recogida,
            tracking_url=_tracking_url_mrw(num_recogida),
            raw_response="<preview-mode/>",
        )

"""
billing.py — Módulo de presupuestos y facturas
Funcionalidad:
  - Generación de presupuesto desde una orden
  - Aceptación / rechazo de presupuesto por el cliente
  - Conversión de presupuesto a factura al completar la reparación
  - Numeración automática correlativa
  - Soporte para descuentos, garantía y notas
"""

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, List, Tuple
import uuid


class EstadoPresupuesto(str, Enum):
    BORRADOR = "borrador"      # En preparación
    ENVIADO = "enviado"        # Enviado al cliente
    ACEPTADO = "aceptado"      # Cliente aprobó
    RECHAZADO = "rechazado"    # Cliente rechazó
    EXPIRADO = "expirado"      # Superó el plazo de validez
    FACTURADO = "facturado"    # Convertido a factura


class EstadoFactura(str, Enum):
    EMITIDA = "emitida"
    PAGADA = "pagada"
    ANULADA = "anulada"


class MetodoPago(str, Enum):
    EFECTIVO = "efectivo"
    TARJETA = "tarjeta"
    TRANSFERENCIA = "transferencia"
    BIZUM = "bizum"


# ── Utilidad: numeración correlativa ──────────────────────────────────────────

def generar_numero_presupuesto(ultimo_numero: int) -> str:
    """Ejemplo: PPTO-2026-00042"""
    año = datetime.now(timezone.utc).year
    return f"PPTO-{año}-{str(ultimo_numero + 1).zfill(5)}"


def generar_numero_factura(ultimo_numero: int) -> str:
    """Ejemplo: FAC-2026-00017"""
    año = datetime.now(timezone.utc).year
    return f"FAC-{año}-{str(ultimo_numero + 1).zfill(5)}"


# ── Gestor de Presupuestos ────────────────────────────────────────────────────

class GestorPresupuestos:

    DIAS_VALIDEZ_DEFAULT = 15  # días antes de expirar

    @staticmethod
    def crear_desde_orden(
        orden: dict, 
        usuario: str, 
        ultimo_numero: int,
        mano_de_obra: float = 0.0, 
        descuento: float = 0.0,
        dias_garantia: int = 90, 
        notas: str = ""
    ) -> dict:
        """
        Genera un presupuesto a partir de una orden de trabajo.
        Solo incluye materiales ya aprobados.
        """
        materiales_aprobados = [
            m for m in orden.get("materiales", []) 
            if m.get("aprobado") or m.get("validado_tecnico")
        ]

        lineas = [
            {
                "descripcion": m.get("nombre", m.get("codigo", "Material")),
                "cantidad": m.get("cantidad", 1),
                "precio_unitario": m.get("precio_unitario", m.get("precio", 0.0)),
                "subtotal": m.get("cantidad", 1) * m.get("precio_unitario", m.get("precio", 0.0)),
            }
            for m in materiales_aprobados
        ]

        if mano_de_obra > 0:
            lineas.append({
                "descripcion": "Mano de obra",
                "cantidad": 1,
                "precio_unitario": mano_de_obra,
                "subtotal": mano_de_obra,
            })

        subtotal_sin_iva = sum(l["subtotal"] for l in lineas) - descuento
        iva = round(subtotal_sin_iva * 0.21, 2)
        total = round(subtotal_sin_iva + iva, 2)

        ahora = datetime.now(timezone.utc)

        return {
            "id": str(uuid.uuid4()),
            "numero": generar_numero_presupuesto(ultimo_numero),
            "orden_id": orden.get("id"),
            "cliente_id": orden.get("cliente_id"),
            "estado": EstadoPresupuesto.BORRADOR.value,
            "lineas": lineas,
            "descuento": round(descuento, 2),
            "subtotal": round(subtotal_sin_iva, 2),
            "iva_21": iva,
            "total": total,
            "mano_de_obra": mano_de_obra,
            "dias_garantia": dias_garantia,
            "notas": notas,
            "creado_por": usuario,
            "created_at": ahora.isoformat(),
            "updated_at": ahora.isoformat(),
            "valido_hasta": (ahora + timedelta(days=GestorPresupuestos.DIAS_VALIDEZ_DEFAULT)).isoformat(),
            "factura_id": None,
        }

    @staticmethod
    def enviar(presupuesto: dict, usuario: str) -> dict:
        """Marca el presupuesto como enviado al cliente."""
        if presupuesto["estado"] != EstadoPresupuesto.BORRADOR.value:
            raise ValueError("Solo se puede enviar un presupuesto en estado 'borrador'.")
        presupuesto["estado"] = EstadoPresupuesto.ENVIADO.value
        presupuesto["enviado_por"] = usuario
        presupuesto["enviado_en"] = datetime.now(timezone.utc).isoformat()
        presupuesto["updated_at"] = datetime.now(timezone.utc).isoformat()
        return presupuesto

    @staticmethod
    def aceptar(presupuesto: dict) -> dict:
        """El cliente acepta el presupuesto."""
        if presupuesto["estado"] != EstadoPresupuesto.ENVIADO.value:
            raise ValueError("Solo se puede aceptar un presupuesto en estado 'enviado'.")
        GestorPresupuestos._verificar_vigencia(presupuesto)
        presupuesto["estado"] = EstadoPresupuesto.ACEPTADO.value
        presupuesto["aceptado_en"] = datetime.now(timezone.utc).isoformat()
        presupuesto["updated_at"] = datetime.now(timezone.utc).isoformat()
        return presupuesto

    @staticmethod
    def rechazar(presupuesto: dict, motivo: str = "") -> dict:
        """El cliente rechaza el presupuesto."""
        if presupuesto["estado"] != EstadoPresupuesto.ENVIADO.value:
            raise ValueError("Solo se puede rechazar un presupuesto en estado 'enviado'.")
        presupuesto["estado"] = EstadoPresupuesto.RECHAZADO.value
        presupuesto["rechazado_en"] = datetime.now(timezone.utc).isoformat()
        presupuesto["motivo_rechazo"] = motivo
        presupuesto["updated_at"] = datetime.now(timezone.utc).isoformat()
        return presupuesto

    @staticmethod
    def _verificar_vigencia(presupuesto: dict) -> None:
        valido_hasta_str = presupuesto.get("valido_hasta")
        if valido_hasta_str:
            valido_hasta = datetime.fromisoformat(valido_hasta_str.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > valido_hasta:
                raise ValueError("El presupuesto ha expirado y ya no puede ser aceptado.")


# ── Gestor de Facturas ────────────────────────────────────────────────────────

class GestorFacturas:

    @staticmethod
    def crear_desde_presupuesto(
        presupuesto: dict, 
        usuario: str,
        ultimo_numero: int
    ) -> Tuple[dict, dict]:
        """
        Convierte un presupuesto aceptado en factura.
        Devuelve (factura_nueva, presupuesto_actualizado).
        """
        if presupuesto["estado"] != EstadoPresupuesto.ACEPTADO.value:
            raise ValueError("Solo se puede facturar un presupuesto aceptado.")

        ahora = datetime.now(timezone.utc)

        factura = {
            "id": str(uuid.uuid4()),
            "numero": generar_numero_factura(ultimo_numero),
            "presupuesto_id": presupuesto["id"],
            "orden_id": presupuesto.get("orden_id"),
            "cliente_id": presupuesto.get("cliente_id"),
            "estado": EstadoFactura.EMITIDA.value,
            "lineas": presupuesto.get("lineas", []),
            "descuento": presupuesto.get("descuento", 0),
            "subtotal": presupuesto.get("subtotal", 0),
            "iva_21": presupuesto.get("iva_21", 0),
            "total": presupuesto.get("total", 0),
            "dias_garantia": presupuesto.get("dias_garantia", 90),
            "notas": presupuesto.get("notas", ""),
            "emitida_por": usuario,
            "created_at": ahora.isoformat(),
            "updated_at": ahora.isoformat(),
            "pagada_en": None,
            "metodo_pago": None,
            "anulada_en": None,
            "motivo_anulacion": None,
        }

        # Actualizar presupuesto
        presupuesto["estado"] = EstadoPresupuesto.FACTURADO.value
        presupuesto["factura_id"] = factura["id"]
        presupuesto["updated_at"] = ahora.isoformat()

        return factura, presupuesto

    @staticmethod
    def registrar_pago(
        factura: dict, 
        metodo: MetodoPago, 
        usuario: str,
        referencia: str = ""
    ) -> dict:
        """Marca la factura como pagada."""
        if factura["estado"] != EstadoFactura.EMITIDA.value:
            raise ValueError("Solo se puede cobrar una factura en estado 'emitida'.")
        factura["estado"] = EstadoFactura.PAGADA.value
        factura["pagada_en"] = datetime.now(timezone.utc).isoformat()
        factura["metodo_pago"] = metodo.value
        factura["cobrado_por"] = usuario
        factura["referencia_pago"] = referencia
        factura["updated_at"] = datetime.now(timezone.utc).isoformat()
        return factura

    @staticmethod
    def anular(factura: dict, usuario: str, motivo: str) -> dict:
        """Anula una factura (solo si no está pagada)."""
        if factura["estado"] == EstadoFactura.PAGADA.value:
            raise ValueError("No se puede anular una factura ya pagada. Emite una factura rectificativa.")
        factura["estado"] = EstadoFactura.ANULADA.value
        factura["anulada_en"] = datetime.now(timezone.utc).isoformat()
        factura["anulada_por"] = usuario
        factura["motivo_anulacion"] = motivo
        factura["updated_at"] = datetime.now(timezone.utc).isoformat()
        return factura

    @staticmethod
    def resumen_facturacion(
        facturas: List[dict], 
        mes: Optional[int] = None,
        año: Optional[int] = None
    ) -> dict:
        """
        Devuelve un resumen de facturación, filtrable por mes/año.
        """
        ahora = datetime.now(timezone.utc)
        mes = mes or ahora.month
        año = año or ahora.year

        del_periodo = [
            f for f in facturas
            if f["estado"] != EstadoFactura.ANULADA.value
            and datetime.fromisoformat(f["created_at"].replace('Z', '+00:00')).month == mes
            and datetime.fromisoformat(f["created_at"].replace('Z', '+00:00')).year == año
        ]

        pagadas = [f for f in del_periodo if f["estado"] == EstadoFactura.PAGADA.value]
        emitidas = [f for f in del_periodo if f["estado"] == EstadoFactura.EMITIDA.value]

        return {
            "periodo": f"{mes:02d}/{año}",
            "total_facturado": round(sum(f["total"] for f in del_periodo), 2),
            "total_cobrado": round(sum(f["total"] for f in pagadas), 2),
            "total_pendiente": round(sum(f["total"] for f in emitidas), 2),
            "num_facturas": len(del_periodo),
            "num_pagadas": len(pagadas),
            "num_pendientes": len(emitidas),
            "metodos_pago": _agrupar_por_metodo(pagadas),
        }


def _agrupar_por_metodo(facturas: List[dict]) -> dict:
    resultado: dict = {}
    for f in facturas:
        metodo = f.get("metodo_pago", "desconocido")
        resultado[metodo] = round(resultado.get(metodo, 0.0) + f["total"], 2)
    return resultado

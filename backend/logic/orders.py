"""
orders.py — Lógica de órdenes de trabajo mejorada
Mejoras incluidas:
  - Máquina de estados explícita con transiciones válidas
  - Historial de cambios de estado
  - Validaciones de negocio antes de cada transición
  - Cálculo automático de coste total (mano de obra + materiales)
  - Tiempo estimado y alertas de retraso
  - Bloqueo de materiales mejorado con motivo
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from dataclasses import dataclass, field


# ── Máquina de estados ─────────────────────────────────────────────────────────

class EstadoOrden(str, Enum):
    # Estados principales del CRM Revix
    PENDIENTE_RECIBIR = "pendiente_recibir"  # Orden creada, esperando dispositivo
    RECIBIDA = "recibida"                     # Dispositivo recibido en taller
    CUARENTENA = "cuarentena"                 # En cuarentena por protocolo
    EN_TALLER = "en_taller"                   # Técnico trabajando
    RE_PRESUPUESTAR = "re_presupuestar"       # Requiere nuevo presupuesto
    REPARADO = "reparado"                     # Reparación completada
    VALIDACION = "validacion"                 # Control de calidad
    ENVIADO = "enviado"                       # Devuelto al cliente
    CANCELADO = "cancelado"                   # Cancelada
    GARANTIA = "garantia"                     # En período de garantía
    REEMPLAZO = "reemplazo"                   # Dispositivo de reemplazo
    IRREPARABLE = "irreparable"               # No se puede reparar


# Transiciones permitidas: {estado_actual: [estados_siguientes_válidos]}
TRANSICIONES_VALIDAS: dict = {
    EstadoOrden.PENDIENTE_RECIBIR: [EstadoOrden.RECIBIDA, EstadoOrden.CANCELADO],
    EstadoOrden.RECIBIDA: [EstadoOrden.CUARENTENA, EstadoOrden.EN_TALLER, EstadoOrden.CANCELADO],
    EstadoOrden.CUARENTENA: [EstadoOrden.EN_TALLER, EstadoOrden.CANCELADO],
    EstadoOrden.EN_TALLER: [EstadoOrden.RE_PRESUPUESTAR, EstadoOrden.REPARADO, EstadoOrden.IRREPARABLE, EstadoOrden.CANCELADO],
    EstadoOrden.RE_PRESUPUESTAR: [EstadoOrden.EN_TALLER, EstadoOrden.CANCELADO],
    EstadoOrden.REPARADO: [EstadoOrden.VALIDACION, EstadoOrden.EN_TALLER],
    EstadoOrden.VALIDACION: [EstadoOrden.ENVIADO, EstadoOrden.EN_TALLER],
    EstadoOrden.ENVIADO: [EstadoOrden.GARANTIA],
    EstadoOrden.CANCELADO: [],  # estado final
    EstadoOrden.GARANTIA: [EstadoOrden.RECIBIDA, EstadoOrden.REEMPLAZO],
    EstadoOrden.REEMPLAZO: [EstadoOrden.ENVIADO],
    EstadoOrden.IRREPARABLE: [EstadoOrden.ENVIADO, EstadoOrden.CANCELADO],
}

# Tiempo máximo esperado por estado (en horas) — para alertas de retraso
TIEMPO_MAXIMO_POR_ESTADO: dict = {
    EstadoOrden.PENDIENTE_RECIBIR: 72,   # 3 días para recibir
    EstadoOrden.RECIBIDA: 4,              # 4 horas para procesar
    EstadoOrden.CUARENTENA: 24,           # 1 día en cuarentena
    EstadoOrden.EN_TALLER: 48,            # 2 días para reparar
    EstadoOrden.RE_PRESUPUESTAR: 24,      # 1 día para re-presupuestar
    EstadoOrden.REPARADO: 4,              # 4 horas para validar
    EstadoOrden.VALIDACION: 8,            # 8 horas en control de calidad
}


@dataclass
class EntradaHistorial:
    estado_anterior: Optional[str]
    estado_nuevo: str
    usuario: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    motivo: str = ""


class GestorOrdenes:
    """
    Encapsula toda la lógica de negocio de las órdenes.
    El backend llama a estos métodos en vez de manipular el estado directamente.
    """

    # ── Transiciones de estado ─────────────────────────────────────────────────

    @staticmethod
    def validar_transicion(estado_actual: str, estado_nuevo: str) -> None:
        """Lanza ValueError si la transición no es válida."""
        try:
            estado_actual_enum = EstadoOrden(estado_actual)
            estado_nuevo_enum = EstadoOrden(estado_nuevo)
        except ValueError:
            # Si el estado no está en el enum, permitir la transición (compatibilidad)
            return

        permitidos = TRANSICIONES_VALIDAS.get(estado_actual_enum, [])
        if estado_nuevo_enum not in permitidos:
            raise ValueError(
                f"Transición no permitida: {estado_actual} → {estado_nuevo}. "
                f"Desde '{estado_actual}' solo se puede ir a: "
                f"{[e.value for e in permitidos] or 'ningún estado (final)'}."
            )

    @staticmethod
    def cambiar_estado(orden: dict, nuevo_estado: str, usuario: str, motivo: str = "", validar: bool = True) -> dict:
        """
        Cambia el estado de una orden aplicando todas las validaciones.
        Devuelve la orden actualizada.
        """
        estado_actual = orden.get("estado", "pendiente_recibir")

        # Validar transición si está habilitado
        if validar:
            GestorOrdenes.validar_transicion(estado_actual, nuevo_estado)

        # Validaciones específicas por destino
        try:
            estado_nuevo_enum = EstadoOrden(nuevo_estado)
            
            if estado_nuevo_enum == EstadoOrden.EN_TALLER:
                if not orden.get("tecnico_id") and not orden.get("tecnico_asignado"):
                    # Solo advertencia, no bloqueo
                    pass

            if estado_nuevo_enum == EstadoOrden.ENVIADO:
                materiales_pendientes = [
                    m for m in orden.get("materiales", [])
                    if m.get("añadido_por_tecnico") and not m.get("aprobado") and not m.get("validado_tecnico")
                ]
                if materiales_pendientes:
                    raise ValueError(
                        f"Hay {len(materiales_pendientes)} material(es) pendiente(s) de aprobación."
                    )
        except ValueError as e:
            if "is not a valid" not in str(e):
                raise

        # Aplicar cambio
        entrada = EntradaHistorial(
            estado_anterior=estado_actual,
            estado_nuevo=nuevo_estado,
            usuario=usuario,
            motivo=motivo,
        )
        
        historial_entry = {
            "estado_anterior": entrada.estado_anterior,
            "estado_nuevo": entrada.estado_nuevo,
            "usuario": entrada.usuario,
            "timestamp": entrada.timestamp.isoformat(),
            "motivo": entrada.motivo,
        }
        
        orden["estado"] = nuevo_estado
        orden["historial_estados"] = orden.get("historial_estados", []) + [historial_entry]
        orden["updated_at"] = datetime.now(timezone.utc).isoformat()

        return orden

    # ── QR Scanning ───────────────────────────────────────────────────────────

    @staticmethod
    def procesar_escaneo_qr(orden: dict, tipo_escaneo: str, usuario: str) -> dict:
        """
        Mapea el tipo de escaneo al siguiente estado y aplica el cambio.
        tipo_escaneo: 'entrada_taller' | 'tecnico' | 'control_calidad' | 'salida'
        """
        MAPA_ESCANEO: dict = {
            "entrada_taller": EstadoOrden.RECIBIDA.value,
            "tecnico": EstadoOrden.EN_TALLER.value,
            "control_calidad": EstadoOrden.VALIDACION.value,
            "salida": EstadoOrden.ENVIADO.value,
        }
        if tipo_escaneo not in MAPA_ESCANEO:
            raise ValueError(f"Tipo de escaneo desconocido: '{tipo_escaneo}'")

        nuevo_estado = MAPA_ESCANEO[tipo_escaneo]
        return GestorOrdenes.cambiar_estado(
            orden, nuevo_estado, usuario, motivo=f"Escaneo QR — {tipo_escaneo}", validar=False
        )

    # ── Materiales ────────────────────────────────────────────────────────────

    @staticmethod
    def añadir_material(orden: dict, material: dict, usuario: str, es_tecnico: bool) -> dict:
        """
        Añade un material a la orden.
        Si lo añade un técnico, bloquea la orden y registra el motivo.
        """
        material["añadido_por_tecnico"] = es_tecnico
        material["aprobado"] = not es_tecnico  # admin añade ya aprobado
        material["validado_tecnico"] = not es_tecnico
        material["añadido_por"] = usuario
        material["timestamp"] = datetime.now(timezone.utc).isoformat()

        orden.setdefault("materiales", []).append(material)

        if es_tecnico:
            orden["bloqueada"] = True
            orden["motivo_bloqueo"] = f"Materiales pendientes de aprobación — añadidos por {usuario}"
            orden["bloqueada_desde"] = datetime.now(timezone.utc).isoformat()

        orden["updated_at"] = datetime.now(timezone.utc).isoformat()
        return orden

    @staticmethod
    def aprobar_materiales(orden: dict, admin_usuario: str) -> dict:
        """Aprueba todos los materiales pendientes y desbloquea la orden."""
        pendientes = [
            m for m in orden.get("materiales", [])
            if m.get("añadido_por_tecnico") and not m.get("aprobado") and not m.get("validado_tecnico")
        ]
        if not pendientes:
            raise ValueError("No hay materiales pendientes de aprobación.")

        for m in pendientes:
            m["aprobado"] = True
            m["validado_tecnico"] = True
            m["aprobado_por"] = admin_usuario
            m["aprobado_en"] = datetime.now(timezone.utc).isoformat()

        orden["bloqueada"] = False
        orden["motivo_bloqueo"] = None
        orden["updated_at"] = datetime.now(timezone.utc).isoformat()
        return orden

    @staticmethod
    def rechazar_materiales(orden: dict, admin_usuario: str, motivo: str) -> dict:
        """Rechaza materiales pendientes y los elimina de la orden."""
        rechazados = [
            m for m in orden.get("materiales", [])
            if m.get("añadido_por_tecnico") and not m.get("aprobado") and not m.get("validado_tecnico")
        ]
        if not rechazados:
            raise ValueError("No hay materiales pendientes de rechazar.")

        orden["materiales"] = [
            m for m in orden.get("materiales", [])
            if not (m.get("añadido_por_tecnico") and not m.get("aprobado") and not m.get("validado_tecnico"))
        ]
        orden["bloqueada"] = False
        orden["motivo_bloqueo"] = None
        orden["rechazo_info"] = {
            "rechazado_por": admin_usuario,
            "motivo": motivo,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "materiales_rechazados": len(rechazados),
        }
        orden["updated_at"] = datetime.now(timezone.utc).isoformat()
        return orden

    # ── Costes ────────────────────────────────────────────────────────────────

    @staticmethod
    def calcular_coste_total(orden: dict) -> dict:
        """
        Calcula y añade el desglose de costes a la orden.
        """
        materiales_aprobados = [
            m for m in orden.get("materiales", []) 
            if m.get("aprobado") or m.get("validado_tecnico")
        ]
        coste_materiales = sum(
            m.get("cantidad", 1) * m.get("precio_unitario", m.get("precio", 0.0))
            for m in materiales_aprobados
        )
        mano_de_obra = orden.get("mano_de_obra", 0.0)
        descuento = orden.get("descuento", 0.0)
        subtotal = coste_materiales + mano_de_obra
        total = max(subtotal - descuento, 0.0)
        iva = round(total * 0.21, 2)

        orden["coste_desglose"] = {
            "materiales": round(coste_materiales, 2),
            "mano_de_obra": round(mano_de_obra, 2),
            "descuento": round(descuento, 2),
            "subtotal": round(subtotal, 2),
            "iva_21": iva,
            "total": round(total + iva, 2),
        }
        return orden

    # ── Alertas de retraso ────────────────────────────────────────────────────

    @staticmethod
    def calcular_alerta_retraso(orden: dict) -> Optional[str]:
        """
        Devuelve un mensaje de alerta si la orden lleva demasiado tiempo
        en el estado actual, o None si está dentro del plazo.
        """
        estado_str = orden.get("estado", "pendiente_recibir")
        
        try:
            estado = EstadoOrden(estado_str)
        except ValueError:
            return None
            
        if estado in (EstadoOrden.ENVIADO, EstadoOrden.CANCELADO, EstadoOrden.GARANTIA):
            return None

        max_horas = TIEMPO_MAXIMO_POR_ESTADO.get(estado)
        if not max_horas:
            return None

        updated_at_str = orden.get("updated_at") or orden.get("created_at")
        if not updated_at_str:
            return None

        try:
            if isinstance(updated_at_str, str):
                updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
            else:
                updated_at = updated_at_str
                
            horas_en_estado = (datetime.now(timezone.utc) - updated_at).total_seconds() / 3600

            if horas_en_estado > max_horas:
                horas_retraso = round(horas_en_estado - max_horas, 1)
                return (
                    f"Orden lleva {horas_retraso}h de retraso en estado '{estado.value}' "
                    f"(máximo: {max_horas}h)."
                )
        except Exception:
            pass
            
        return None

    # ── Obtener órdenes con alertas ───────────────────────────────────────────

    @staticmethod
    def obtener_ordenes_retrasadas(ordenes: List[dict]) -> List[dict]:
        """
        Filtra y devuelve las órdenes que tienen alertas de retraso.
        """
        retrasadas = []
        for orden in ordenes:
            alerta = GestorOrdenes.calcular_alerta_retraso(orden)
            if alerta:
                retrasadas.append({
                    "orden_id": orden.get("id"),
                    "numero_orden": orden.get("numero_orden"),
                    "estado": orden.get("estado"),
                    "alerta": alerta,
                    "updated_at": orden.get("updated_at"),
                })
        return retrasadas

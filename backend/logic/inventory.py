"""
inventory.py — Lógica de inventario y stock mejorada
Mejoras incluidas:
  - Movimientos de stock con trazabilidad completa
  - Alertas de stock mínimo con niveles configurables
  - Reserva de stock para órdenes pendientes
  - Valoración de inventario (FIFO simplificado)
  - Reposición automática sugerida
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List


class TipoMovimiento(str, Enum):
    ENTRADA = "entrada"           # Compra a proveedor
    SALIDA = "salida"             # Usado en reparación
    AJUSTE_MAS = "ajuste_mas"     # Ajuste manual positivo
    AJUSTE_MENOS = "ajuste_menos" # Ajuste manual negativo
    RESERVA = "reserva"           # Reservado para orden pendiente
    LIBERACION = "liberacion"     # Reserva cancelada (orden cancelada)
    DEVOLUCION = "devolucion"     # Repuesto devuelto de una orden


class GestorInventario:
    """
    Encapsula toda la lógica de negocio del inventario.
    El backend llama a estos métodos en vez de manipular el stock directamente.
    """

    # ── Movimientos de stock ──────────────────────────────────────────────────

    @staticmethod
    def registrar_movimiento(
        repuesto: dict,
        tipo: TipoMovimiento,
        cantidad: int,
        usuario: str,
        referencia: str = "",   # número de orden, albarán, etc.
        notas: str = "",
    ) -> dict:
        """
        Aplica un movimiento de stock con validaciones y trazabilidad.
        Devuelve el repuesto actualizado.
        """
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser un número positivo.")

        stock_actual = repuesto.get("stock", 0)
        stock_reservado = repuesto.get("stock_reservado", 0)
        nuevo_reservado = stock_reservado

        # Calcular nuevo stock según tipo
        if tipo in (TipoMovimiento.ENTRADA, TipoMovimiento.AJUSTE_MAS, TipoMovimiento.DEVOLUCION):
            nuevo_stock = stock_actual + cantidad

        elif tipo == TipoMovimiento.LIBERACION:
            nuevo_stock = stock_actual + cantidad
            nuevo_reservado = max(stock_reservado - cantidad, 0)

        elif tipo in (TipoMovimiento.SALIDA, TipoMovimiento.AJUSTE_MENOS):
            stock_disponible = stock_actual - stock_reservado
            if cantidad > stock_disponible:
                raise ValueError(
                    f"Stock insuficiente. Disponible: {stock_disponible} "
                    f"(total {stock_actual} - reservado {stock_reservado})."
                )
            nuevo_stock = stock_actual - cantidad

        elif tipo == TipoMovimiento.RESERVA:
            stock_disponible = stock_actual - stock_reservado
            if cantidad > stock_disponible:
                raise ValueError(
                    f"No hay suficiente stock para reservar. Disponible: {stock_disponible}."
                )
            nuevo_stock = stock_actual  # el stock total no cambia
            nuevo_reservado = stock_reservado + cantidad

        else:
            raise ValueError(f"Tipo de movimiento desconocido: {tipo}")

        # Registrar movimiento en el historial
        movimiento = {
            "tipo": tipo.value,
            "cantidad": cantidad,
            "stock_antes": stock_actual,
            "stock_despues": nuevo_stock,
            "usuario": usuario,
            "referencia": referencia,
            "notas": notas,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        repuesto["stock"] = nuevo_stock
        repuesto["stock_reservado"] = nuevo_reservado
        repuesto["movimientos"] = repuesto.get("movimientos", []) + [movimiento]
        repuesto["updated_at"] = datetime.now(timezone.utc).isoformat()

        return repuesto

    # ── Stock disponible real ─────────────────────────────────────────────────

    @staticmethod
    def stock_disponible(repuesto: dict) -> int:
        """Stock total menos el reservado para órdenes en curso."""
        return repuesto.get("stock", 0) - repuesto.get("stock_reservado", 0)

    # ── Alertas ───────────────────────────────────────────────────────────────

    @staticmethod
    def nivel_alerta(repuesto: dict) -> Optional[str]:
        """
        Devuelve el nivel de alerta del repuesto:
        'critico' | 'bajo' | None
        """
        stock = repuesto.get("stock", 0)
        minimo = repuesto.get("stock_minimo", 0)
        disponible = GestorInventario.stock_disponible(repuesto)

        if disponible <= 0:
            return "critico"
        if stock <= minimo:
            return "bajo"
        return None

    @staticmethod
    def generar_alertas_inventario(repuestos: List[dict]) -> List[dict]:
        """
        Devuelve la lista de repuestos que necesitan atención,
        ordenados por urgencia.
        """
        alertas = []
        for r in repuestos:
            nivel = GestorInventario.nivel_alerta(r)
            if nivel:
                alertas.append({
                    "repuesto_id": r.get("id"),
                    "nombre": r.get("nombre"),
                    "sku": r.get("sku"),
                    "stock": r.get("stock", 0),
                    "stock_reservado": r.get("stock_reservado", 0),
                    "stock_disponible": GestorInventario.stock_disponible(r),
                    "stock_minimo": r.get("stock_minimo", 0),
                    "nivel": nivel,
                    "proveedor_id": r.get("proveedor_id"),
                })

        # Críticos primero, luego por stock disponible
        return sorted(alertas, key=lambda x: (x["nivel"] != "critico", x["stock_disponible"]))

    # ── Sugerencia de reposición ──────────────────────────────────────────────

    @staticmethod
    def sugerir_reposicion(repuesto: dict, meses_cobertura: int = 2) -> dict:
        """
        Calcula la cantidad sugerida a pedir basándose en el consumo
        histórico de los últimos 90 días.
        """
        movimientos = repuesto.get("movimientos", [])
        hace_90_dias = datetime.now(timezone.utc).timestamp() - (90 * 86400)

        salidas_recientes = sum(
            m["cantidad"]
            for m in movimientos
            if m["tipo"] == TipoMovimiento.SALIDA.value
            and datetime.fromisoformat(m["timestamp"].replace('Z', '+00:00')).timestamp() >= hace_90_dias
        )

        consumo_mensual = salidas_recientes / 3 if salidas_recientes > 0 else 0
        stock_actual = repuesto.get("stock", 0)
        stock_minimo = repuesto.get("stock_minimo", 0)
        stock_objetivo = max(consumo_mensual * meses_cobertura, stock_minimo * 2)
        cantidad_sugerida = max(int(stock_objetivo - stock_actual), 0)

        return {
            "repuesto_id": repuesto.get("id"),
            "nombre": repuesto.get("nombre"),
            "sku": repuesto.get("sku"),
            "stock_actual": stock_actual,
            "consumo_mensual": round(consumo_mensual, 1),
            "stock_objetivo": round(stock_objetivo, 1),
            "cantidad_sugerida": cantidad_sugerida,
            "proveedor_id": repuesto.get("proveedor_id"),
        }

    # ── Valoración de inventario ──────────────────────────────────────────────

    @staticmethod
    def valorar_inventario(repuestos: List[dict]) -> dict:
        """
        Calcula el valor total del inventario a precio de coste y a PVP.
        """
        valor_coste = sum(
            r.get("stock", 0) * r.get("precio_compra", 0.0)
            for r in repuestos
        )
        valor_pvp = sum(
            r.get("stock", 0) * r.get("precio_venta", 0.0)
            for r in repuestos
        )
        margen_potencial = valor_pvp - valor_coste

        return {
            "total_unidades": sum(r.get("stock", 0) for r in repuestos),
            "total_referencias": len(repuestos),
            "valor_coste": round(valor_coste, 2),
            "valor_pvp": round(valor_pvp, 2),
            "margen_potencial": round(margen_potencial, 2),
            "margen_porcentaje": round((margen_potencial / valor_coste * 100) if valor_coste else 0, 1),
            "calculado_en": datetime.now(timezone.utc).isoformat(),
        }

    # ── Historial de movimientos ──────────────────────────────────────────────

    @staticmethod
    def obtener_historial(repuesto: dict, limite: int = 50) -> List[dict]:
        """
        Devuelve los últimos movimientos del repuesto.
        """
        movimientos = repuesto.get("movimientos", [])
        return sorted(movimientos, key=lambda x: x.get("timestamp", ""), reverse=True)[:limite]

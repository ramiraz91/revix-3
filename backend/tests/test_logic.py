#!/usr/bin/env python3
"""
test_logic.py — Suite de tests unitarios para la lógica de negocio
Cubre: órdenes, inventario, presupuestos y facturas
Ejecutar con: python -m pytest tests/test_logic.py -v
"""

import pytest
from datetime import datetime, timezone, timedelta
import sys
import os

# Añadir el directorio padre al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.orders import GestorOrdenes, EstadoOrden, TRANSICIONES_VALIDAS
from logic.inventory import GestorInventario, TipoMovimiento
from logic.billing import (
    GestorPresupuestos, GestorFacturas,
    EstadoPresupuesto, EstadoFactura, MetodoPago
)


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def orden_base():
    return {
        "id": "orden-001",
        "numero_orden": "ORD-2026-00001",
        "estado": EstadoOrden.RECIBIDA.value,
        "cliente_id": "cliente-001",
        "tecnico_id": "tecnico-001",
        "tecnico_asignado": "Juan Técnico",
        "materiales": [],
        "bloqueada": False,
        "mano_de_obra": 50.0,
        "descuento": 0.0,
        "codigo_recogida_salida": None,
        "historial_estados": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def repuesto_base():
    return {
        "id": "rep-001",
        "nombre": "Pantalla iPhone 15 Pro",
        "sku": "PAN-IPH15P-001",
        "stock": 10,
        "stock_reservado": 0,
        "stock_minimo": 3,
        "precio_compra": 150.0,
        "precio_venta": 250.0,
        "proveedor_id": "prov-001",
        "movimientos": [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def presupuesto_base(orden_base):
    return GestorPresupuestos.crear_desde_orden(
        orden={
            **orden_base,
            "materiales": [
                {
                    "nombre": "Pantalla",
                    "cantidad": 1,
                    "precio_unitario": 150.0,
                    "aprobado": True,
                }
            ],
        },
        usuario="admin",
        ultimo_numero=0,
        mano_de_obra=50.0,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Tests — Máquina de estados de órdenes
# ══════════════════════════════════════════════════════════════════════════════

class TestMaquinaEstados:

    def test_transicion_valida(self, orden_base):
        """Transición válida de RECIBIDA a EN_TALLER"""
        orden = GestorOrdenes.cambiar_estado(
            orden_base, EstadoOrden.EN_TALLER.value, "admin"
        )
        assert orden["estado"] == EstadoOrden.EN_TALLER.value

    def test_transicion_invalida_lanza_error(self, orden_base):
        """No se puede saltar de RECIBIDA a ENVIADO"""
        with pytest.raises(ValueError, match="Transición no permitida"):
            GestorOrdenes.cambiar_estado(
                orden_base, EstadoOrden.ENVIADO.value, "admin"
            )

    def test_estado_final_no_permite_transicion(self, orden_base):
        """Desde CANCELADO no se puede ir a ningún lado"""
        orden_base["estado"] = EstadoOrden.CANCELADO.value
        with pytest.raises(ValueError):
            GestorOrdenes.cambiar_estado(
                orden_base, EstadoOrden.EN_TALLER.value, "admin"
            )

    def test_historial_se_registra(self, orden_base):
        """El historial guarda cada cambio de estado"""
        orden = GestorOrdenes.cambiar_estado(
            orden_base, EstadoOrden.EN_TALLER.value, "tecnico-01", motivo="Inicio reparación"
        )
        assert len(orden["historial_estados"]) == 1
        entrada = orden["historial_estados"][0]
        assert entrada["estado_anterior"] == EstadoOrden.RECIBIDA.value
        assert entrada["estado_nuevo"] == EstadoOrden.EN_TALLER.value
        assert entrada["usuario"] == "tecnico-01"
        assert entrada["motivo"] == "Inicio reparación"

    def test_cobertura_completa_de_transiciones(self):
        """Todos los estados tienen su entrada en TRANSICIONES_VALIDAS."""
        for estado in EstadoOrden:
            assert estado in TRANSICIONES_VALIDAS


# ══════════════════════════════════════════════════════════════════════════════
# Tests — Materiales y bloqueo de órdenes
# ══════════════════════════════════════════════════════════════════════════════

class TestMateriales:

    def test_tecnico_añade_material_bloquea_orden(self, orden_base):
        """Cuando técnico añade material, la orden se bloquea"""
        orden = GestorOrdenes.añadir_material(
            orden_base,
            {"repuesto_id": "rep-001", "cantidad": 1, "precio_unitario": 100.0, "nombre": "Pantalla"},
            "tecnico-01",
            es_tecnico=True,
        )
        assert orden["bloqueada"] is True
        assert orden["materiales"][0]["aprobado"] is False

    def test_admin_añade_material_no_bloquea(self, orden_base):
        """Cuando admin añade material, ya viene aprobado"""
        orden = GestorOrdenes.añadir_material(
            orden_base,
            {"repuesto_id": "rep-001", "cantidad": 1, "precio_unitario": 100.0, "nombre": "Pantalla"},
            "admin",
            es_tecnico=False,
        )
        assert orden["bloqueada"] is False
        assert orden["materiales"][0]["aprobado"] is True

    def test_aprobar_materiales_desbloquea_orden(self, orden_base):
        """Al aprobar materiales, la orden se desbloquea"""
        orden = GestorOrdenes.añadir_material(
            orden_base,
            {"repuesto_id": "rep-001", "cantidad": 1, "precio_unitario": 100.0, "nombre": "Pantalla"},
            "tecnico-01",
            es_tecnico=True,
        )
        orden = GestorOrdenes.aprobar_materiales(orden, "admin")
        assert orden["bloqueada"] is False
        assert orden["materiales"][0]["aprobado"] is True

    def test_aprobar_sin_pendientes_lanza_error(self, orden_base):
        """Error si no hay materiales pendientes de aprobación"""
        with pytest.raises(ValueError, match="No hay materiales pendientes"):
            GestorOrdenes.aprobar_materiales(orden_base, "admin")

    def test_rechazar_materiales_los_elimina(self, orden_base):
        """Rechazar materiales los elimina de la orden"""
        orden = GestorOrdenes.añadir_material(
            orden_base,
            {"repuesto_id": "rep-001", "cantidad": 1, "precio_unitario": 100.0, "nombre": "Pantalla"},
            "tecnico-01",
            es_tecnico=True,
        )
        orden = GestorOrdenes.rechazar_materiales(orden, "admin", motivo="Precio incorrecto")
        assert len(orden["materiales"]) == 0
        assert orden["bloqueada"] is False
        assert orden["rechazo_info"]["motivo"] == "Precio incorrecto"

    def test_calcular_coste_total(self, orden_base):
        """Cálculo correcto de costes con IVA"""
        orden_base["materiales"] = [
            {"cantidad": 1, "precio_unitario": 150.0, "aprobado": True},
            {"cantidad": 2, "precio_unitario": 20.0, "aprobado": True},
            {"cantidad": 1, "precio_unitario": 50.0, "aprobado": False},  # no aprobado
        ]
        orden_base["mano_de_obra"] = 60.0
        orden = GestorOrdenes.calcular_coste_total(orden_base)
        desglose = orden["coste_desglose"]
        assert desglose["materiales"] == 190.0   # 150 + 40
        assert desglose["mano_de_obra"] == 60.0
        assert desglose["subtotal"] == 250.0
        assert desglose["iva_21"] == round(250.0 * 0.21, 2)
        assert desglose["total"] == round(250.0 * 1.21, 2)


# ══════════════════════════════════════════════════════════════════════════════
# Tests — Inventario
# ══════════════════════════════════════════════════════════════════════════════

class TestInventario:

    def test_entrada_incrementa_stock(self, repuesto_base):
        """Movimiento de entrada aumenta el stock"""
        r = GestorInventario.registrar_movimiento(
            repuesto_base, TipoMovimiento.ENTRADA, 5, "admin", "ALBARAN-001"
        )
        assert r["stock"] == 15

    def test_salida_decrementa_stock(self, repuesto_base):
        """Movimiento de salida reduce el stock"""
        r = GestorInventario.registrar_movimiento(
            repuesto_base, TipoMovimiento.SALIDA, 3, "admin", "ORDEN-001"
        )
        assert r["stock"] == 7

    def test_salida_sin_stock_lanza_error(self, repuesto_base):
        """Error si no hay stock suficiente para salida"""
        repuesto_base["stock"] = 2
        with pytest.raises(ValueError, match="Stock insuficiente"):
            GestorInventario.registrar_movimiento(
                repuesto_base, TipoMovimiento.SALIDA, 5, "admin"
            )

    def test_reserva_no_modifica_stock_total(self, repuesto_base):
        """Reservar no cambia el stock total, solo el reservado"""
        r = GestorInventario.registrar_movimiento(
            repuesto_base, TipoMovimiento.RESERVA, 3, "sistema", "ORDEN-002"
        )
        assert r["stock"] == 10              # no cambia
        assert r["stock_reservado"] == 3

    def test_reserva_sin_disponible_lanza_error(self, repuesto_base):
        """Error si no hay stock disponible para reservar"""
        repuesto_base["stock_reservado"] = 9
        with pytest.raises(ValueError, match="para reservar"):
            GestorInventario.registrar_movimiento(
                repuesto_base, TipoMovimiento.RESERVA, 5, "sistema"
            )

    def test_historial_de_movimientos(self, repuesto_base):
        """Los movimientos se registran en el historial"""
        r = GestorInventario.registrar_movimiento(
            repuesto_base, TipoMovimiento.ENTRADA, 2, "admin"
        )
        r = GestorInventario.registrar_movimiento(
            r, TipoMovimiento.SALIDA, 1, "admin"
        )
        assert len(r["movimientos"]) == 2
        assert r["movimientos"][0]["tipo"] == "entrada"
        assert r["movimientos"][1]["tipo"] == "salida"

    def test_alerta_critica_cuando_sin_disponible(self, repuesto_base):
        """Alerta crítica cuando stock disponible es 0"""
        repuesto_base["stock"] = 3
        repuesto_base["stock_reservado"] = 3
        assert GestorInventario.nivel_alerta(repuesto_base) == "critico"

    def test_alerta_baja_cuando_por_debajo_minimo(self, repuesto_base):
        """Alerta baja cuando stock está por debajo del mínimo"""
        repuesto_base["stock"] = 2
        repuesto_base["stock_minimo"] = 3
        assert GestorInventario.nivel_alerta(repuesto_base) == "bajo"

    def test_sin_alerta_cuando_stock_suficiente(self, repuesto_base):
        """Sin alerta cuando hay stock suficiente"""
        assert GestorInventario.nivel_alerta(repuesto_base) is None

    def test_valoracion_inventario(self, repuesto_base):
        """Valoración correcta del inventario"""
        repuestos = [repuesto_base, {**repuesto_base, "id": "rep-002", "stock": 5}]
        val = GestorInventario.valorar_inventario(repuestos)
        assert val["total_unidades"] == 15
        assert val["valor_coste"] == round((10 + 5) * 150.0, 2)
        assert val["valor_pvp"] == round((10 + 5) * 250.0, 2)

    def test_stock_disponible(self, repuesto_base):
        """Cálculo correcto del stock disponible"""
        repuesto_base["stock_reservado"] = 3
        assert GestorInventario.stock_disponible(repuesto_base) == 7


# ══════════════════════════════════════════════════════════════════════════════
# Tests — Presupuestos y Facturas
# ══════════════════════════════════════════════════════════════════════════════

class TestPresupuestos:

    def test_crear_presupuesto_calcula_totales(self, presupuesto_base):
        """Presupuesto calcula correctamente los totales"""
        p = presupuesto_base
        assert p["subtotal"] == 200.0  # 150 material + 50 mano de obra
        assert p["iva_21"] == round(200.0 * 0.21, 2)
        assert p["total"] == round(200.0 * 1.21, 2)
        assert p["estado"] == EstadoPresupuesto.BORRADOR.value

    def test_numeracion_correlativa(self):
        """Numeración correlativa de presupuestos"""
        p0 = GestorPresupuestos.crear_desde_orden({
            "id": "o1", "cliente_id": "c1", "materiales": []
        }, "admin", ultimo_numero=41)
        assert "PPTO-" in p0["numero"]
        assert "-00042" in p0["numero"]

    def test_enviar_desde_borrador(self, presupuesto_base):
        """Se puede enviar un presupuesto en borrador"""
        p = GestorPresupuestos.enviar(presupuesto_base, "admin")
        assert p["estado"] == EstadoPresupuesto.ENVIADO.value

    def test_no_se_puede_enviar_dos_veces(self, presupuesto_base):
        """Error al enviar un presupuesto ya enviado"""
        p = GestorPresupuestos.enviar(presupuesto_base, "admin")
        with pytest.raises(ValueError):
            GestorPresupuestos.enviar(p, "admin")

    def test_aceptar_presupuesto(self, presupuesto_base):
        """Cliente puede aceptar presupuesto enviado"""
        p = GestorPresupuestos.enviar(presupuesto_base, "admin")
        p = GestorPresupuestos.aceptar(p)
        assert p["estado"] == EstadoPresupuesto.ACEPTADO.value

    def test_rechazar_presupuesto(self, presupuesto_base):
        """Cliente puede rechazar presupuesto enviado"""
        p = GestorPresupuestos.enviar(presupuesto_base, "admin")
        p = GestorPresupuestos.rechazar(p, motivo="Precio demasiado alto")
        assert p["estado"] == EstadoPresupuesto.RECHAZADO.value
        assert "motivo_rechazo" in p

    def test_no_se_puede_aceptar_expirado(self, presupuesto_base):
        """No se puede aceptar un presupuesto expirado"""
        presupuesto_base["estado"] = EstadoPresupuesto.ENVIADO.value
        presupuesto_base["valido_hasta"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        with pytest.raises(ValueError, match="expirado"):
            GestorPresupuestos.aceptar(presupuesto_base)


class TestFacturas:

    def test_crear_factura_desde_presupuesto_aceptado(self, presupuesto_base):
        """Se puede crear factura desde presupuesto aceptado"""
        p = GestorPresupuestos.enviar(presupuesto_base, "admin")
        p = GestorPresupuestos.aceptar(p)
        factura, p_actualizado = GestorFacturas.crear_desde_presupuesto(p, "admin", ultimo_numero=16)
        assert factura["estado"] == EstadoFactura.EMITIDA.value
        assert "FAC-" in factura["numero"]
        assert "-00017" in factura["numero"]
        assert factura["total"] == p["total"]
        assert p_actualizado["estado"] == EstadoPresupuesto.FACTURADO.value
        assert p_actualizado["factura_id"] == factura["id"]

    def test_no_facturar_presupuesto_no_aceptado(self, presupuesto_base):
        """Error al facturar presupuesto no aceptado"""
        with pytest.raises(ValueError, match="aceptado"):
            GestorFacturas.crear_desde_presupuesto(presupuesto_base, "admin", 0)

    def test_registrar_pago(self, presupuesto_base):
        """Se puede registrar pago de factura emitida"""
        p = GestorPresupuestos.enviar(presupuesto_base, "admin")
        p = GestorPresupuestos.aceptar(p)
        factura, _ = GestorFacturas.crear_desde_presupuesto(p, "admin", 0)
        factura = GestorFacturas.registrar_pago(factura, MetodoPago.TARJETA, "admin")
        assert factura["estado"] == EstadoFactura.PAGADA.value
        assert factura["metodo_pago"] == "tarjeta"

    def test_no_se_puede_pagar_dos_veces(self, presupuesto_base):
        """Error al pagar factura ya pagada"""
        p = GestorPresupuestos.enviar(presupuesto_base, "admin")
        p = GestorPresupuestos.aceptar(p)
        factura, _ = GestorFacturas.crear_desde_presupuesto(p, "admin", 0)
        factura = GestorFacturas.registrar_pago(factura, MetodoPago.EFECTIVO, "admin")
        with pytest.raises(ValueError):
            GestorFacturas.registrar_pago(factura, MetodoPago.EFECTIVO, "admin")

    def test_anular_factura_emitida(self, presupuesto_base):
        """Se puede anular factura emitida"""
        p = GestorPresupuestos.enviar(presupuesto_base, "admin")
        p = GestorPresupuestos.aceptar(p)
        factura, _ = GestorFacturas.crear_desde_presupuesto(p, "admin", 0)
        factura = GestorFacturas.anular(factura, "admin", "Error de datos")
        assert factura["estado"] == EstadoFactura.ANULADA.value

    def test_no_se_puede_anular_factura_pagada(self, presupuesto_base):
        """Error al anular factura ya pagada"""
        p = GestorPresupuestos.enviar(presupuesto_base, "admin")
        p = GestorPresupuestos.aceptar(p)
        factura, _ = GestorFacturas.crear_desde_presupuesto(p, "admin", 0)
        factura = GestorFacturas.registrar_pago(factura, MetodoPago.BIZUM, "admin")
        with pytest.raises(ValueError, match="rectificativa"):
            GestorFacturas.anular(factura, "admin", "Error")


# ══════════════════════════════════════════════════════════════════════════════
# Tests — Alertas de retraso
# ══════════════════════════════════════════════════════════════════════════════

class TestAlertasRetraso:

    def test_sin_alerta_orden_reciente(self, orden_base):
        """Sin alerta para orden actualizada recientemente"""
        alerta = GestorOrdenes.calcular_alerta_retraso(orden_base)
        assert alerta is None

    def test_alerta_orden_retrasada(self, orden_base):
        """Alerta para orden que lleva mucho tiempo en un estado"""
        # Simular orden antigua
        orden_base["updated_at"] = (datetime.now(timezone.utc) - timedelta(hours=50)).isoformat()
        orden_base["estado"] = EstadoOrden.EN_TALLER.value
        alerta = GestorOrdenes.calcular_alerta_retraso(orden_base)
        assert alerta is not None
        assert "retraso" in alerta.lower()

    def test_sin_alerta_estado_final(self, orden_base):
        """Sin alerta para estados finales"""
        orden_base["estado"] = EstadoOrden.ENVIADO.value
        orden_base["updated_at"] = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        alerta = GestorOrdenes.calcular_alerta_retraso(orden_base)
        assert alerta is None


# ══════════════════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

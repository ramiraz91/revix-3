"""
Sistema de Finanzas Centralizado - Revix CRM v1.1.0
====================================================
Este módulo centraliza TODA la información financiera del negocio:
- Ingresos de órdenes (enviadas/completadas)
- Gastos de compras (facturas de proveedores)
- Valor del inventario
- Materiales usados en órdenes
- Balance general y P&L

Autor: Revix Team
Fecha: 2026-03-14
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
from config import db, logger
from auth import require_auth, require_admin, require_master

router = APIRouter(prefix="/finanzas", tags=["Finanzas"])


# ==================== MODELOS ====================

class PeriodoFinanciero(str, Enum):
    DIA = "dia"
    SEMANA = "semana"
    MES = "mes"
    TRIMESTRE = "trimestre"
    AÑO = "año"


class CategoriaGasto(str, Enum):
    COMPRA_MATERIAL = "compra_material"
    MATERIAL_USADO = "material_usado"
    MANO_OBRA = "mano_obra"
    ENVIO = "envio"
    OTROS = "otros"


class MovimientoFinanciero(BaseModel):
    """Registro de movimiento financiero"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tipo: str  # "ingreso" o "gasto"
    categoria: str
    descripcion: str
    monto: float
    fecha: str
    referencia_tipo: Optional[str] = None  # "orden", "compra", "factura"
    referencia_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ==================== DASHBOARD PRINCIPAL ====================

@router.get("/dashboard")
async def dashboard_financiero(
    periodo: PeriodoFinanciero = PeriodoFinanciero.MES,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """
    Dashboard financiero centralizado.
    Muestra resumen completo de ingresos, gastos, inventario y balance.
    """
    # Calcular fechas del periodo
    now = datetime.now(timezone.utc)
    
    if fecha_inicio and fecha_fin:
        start_date = datetime.fromisoformat(fecha_inicio.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(fecha_fin.replace('Z', '+00:00'))
    else:
        if periodo == PeriodoFinanciero.DIA:
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif periodo == PeriodoFinanciero.SEMANA:
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif periodo == PeriodoFinanciero.MES:
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif periodo == PeriodoFinanciero.TRIMESTRE:
            quarter_month = ((now.month - 1) // 3) * 3 + 1
            start_date = now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # AÑO
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    
    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()
    
    # ===== 1. INGRESOS DE ÓRDENES =====
    ordenes_enviadas = await db.ordenes.find({
        "estado": "enviado",
        "fecha_enviado": {"$gte": start_iso, "$lte": end_iso}
    }, {"_id": 0, "presupuesto_total": 1, "coste_total": 1, "beneficio_estimado": 1, 
        "numero_orden": 1, "materiales": 1, "mano_obra": 1}).to_list(10000)
    
    ingresos_ordenes = sum(o.get("presupuesto_total", 0) or 0 for o in ordenes_enviadas)
    costes_ordenes = sum(o.get("coste_total", 0) or 0 for o in ordenes_enviadas)
    beneficio_ordenes = sum(o.get("beneficio_estimado", 0) or 0 for o in ordenes_enviadas)
    
    # Calcular materiales usados en órdenes
    materiales_usados = 0
    for orden in ordenes_enviadas:
        for mat in orden.get("materiales", []):
            cantidad = mat.get("cantidad", 0) or 0
            coste = mat.get("coste", 0) or 0
            materiales_usados += cantidad * coste
    
    mano_obra_total = sum(o.get("mano_obra", 0) or 0 for o in ordenes_enviadas)
    
    # ===== 2. COMPRAS (GASTOS) =====
    compras = await db.compras.find({
        "created_at": {"$gte": start_iso, "$lte": end_iso}
    }, {"_id": 0, "total_factura": 1, "base_imponible": 1, "total_iva": 1}).to_list(10000)
    
    total_compras = sum(c.get("total_factura", 0) or 0 for c in compras)
    base_compras = sum(c.get("base_imponible", 0) or 0 for c in compras)
    iva_compras = sum(c.get("total_iva", 0) or 0 for c in compras)
    
    # ===== 3. VALOR DEL INVENTARIO =====
    inventario = await db.repuestos.find(
        {"stock": {"$gt": 0}},
        {"_id": 0, "stock": 1, "precio_compra": 1, "precio_venta": 1, "nombre": 1}
    ).to_list(50000)
    
    valor_inventario_coste = sum(
        (r.get("stock", 0) or 0) * (r.get("precio_compra", 0) or 0) 
        for r in inventario
    )
    valor_inventario_venta = sum(
        (r.get("stock", 0) or 0) * (r.get("precio_venta", 0) or 0) 
        for r in inventario
    )
    total_items_stock = sum(r.get("stock", 0) or 0 for r in inventario)
    
    # ===== 4. FACTURAS DE VENTA (CONTABILIDAD) =====
    facturas_venta = await db.facturas.find({
        "tipo": "venta",
        "estado": {"$ne": "anulada"},
        "created_at": {"$gte": start_iso, "$lte": end_iso}
    }, {"_id": 0, "total": 1, "base_imponible": 1, "total_iva": 1, "estado": 1, "pendiente_cobro": 1}).to_list(10000)
    
    total_facturado = sum(f.get("total", 0) or 0 for f in facturas_venta)
    pendiente_cobro = sum(f.get("pendiente_cobro", 0) or 0 for f in facturas_venta if f.get("estado") != "pagada")
    
    # ===== 5. ÓRDENES EN PROCESO (INGRESOS PENDIENTES) =====
    ordenes_en_proceso = await db.ordenes.find({
        "estado": {"$in": ["recibida", "en_taller", "reparado", "validacion"]}
    }, {"_id": 0, "presupuesto_total": 1, "coste_total": 1}).to_list(10000)
    
    ingresos_pendientes = sum(o.get("presupuesto_total", 0) or 0 for o in ordenes_en_proceso)
    costes_pendientes = sum(o.get("coste_total", 0) or 0 for o in ordenes_en_proceso)
    
    # ===== 6. CÁLCULOS FINALES =====
    total_ingresos = ingresos_ordenes + total_facturado
    total_gastos = total_compras + materiales_usados
    beneficio_bruto = total_ingresos - total_gastos
    margen_porcentaje = round((beneficio_bruto / total_ingresos * 100), 1) if total_ingresos > 0 else 0
    
    return {
        "periodo": {
            "tipo": periodo.value,
            "inicio": start_iso,
            "fin": end_iso
        },
        "resumen": {
            "total_ingresos": round(total_ingresos, 2),
            "total_gastos": round(total_gastos, 2),
            "beneficio_bruto": round(beneficio_bruto, 2),
            "margen_porcentaje": margen_porcentaje
        },
        "ingresos": {
            "ordenes_enviadas": {
                "cantidad": len(ordenes_enviadas),
                "total": round(ingresos_ordenes, 2),
                "coste": round(costes_ordenes, 2),
                "beneficio": round(beneficio_ordenes, 2)
            },
            "facturas_venta": {
                "cantidad": len(facturas_venta),
                "total": round(total_facturado, 2),
                "pendiente_cobro": round(pendiente_cobro, 2)
            },
            "pendientes": {
                "ordenes_en_proceso": len(ordenes_en_proceso),
                "ingresos_estimados": round(ingresos_pendientes, 2),
                "costes_estimados": round(costes_pendientes, 2)
            }
        },
        "gastos": {
            "compras": {
                "cantidad": len(compras),
                "total": round(total_compras, 2),
                "base_imponible": round(base_compras, 2),
                "iva": round(iva_compras, 2)
            },
            "materiales_usados": {
                "total": round(materiales_usados, 2),
                "descripcion": "Coste de materiales utilizados en órdenes enviadas"
            },
            "mano_obra": {
                "total": round(mano_obra_total, 2),
                "descripcion": "Total facturado por mano de obra"
            }
        },
        "inventario": {
            "items_con_stock": len([r for r in inventario if r.get("stock", 0) > 0]),
            "unidades_totales": total_items_stock,
            "valor_coste": round(valor_inventario_coste, 2),
            "valor_venta": round(valor_inventario_venta, 2),
            "margen_potencial": round(valor_inventario_venta - valor_inventario_coste, 2)
        }
    }


# ==================== EVOLUCIÓN MENSUAL ====================

@router.get("/evolucion")
async def evolucion_financiera(
    meses: int = 6,
    user: dict = Depends(require_admin)
):
    """
    Evolución financiera mes a mes para gráficos.
    Devuelve datos de los últimos N meses.
    """
    now = datetime.now(timezone.utc)
    resultados = []
    
    for i in range(meses - 1, -1, -1):
        # Calcular mes
        month = now.month - i
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        
        # Primer y último día del mes
        start_date = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
        
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()
        
        # Ingresos (órdenes enviadas)
        ordenes = await db.ordenes.find({
            "estado": "enviado",
            "fecha_enviado": {"$gte": start_iso, "$lte": end_iso}
        }, {"_id": 0, "presupuesto_total": 1, "coste_total": 1}).to_list(10000)
        
        ingresos = sum(o.get("presupuesto_total", 0) or 0 for o in ordenes)
        costes = sum(o.get("coste_total", 0) or 0 for o in ordenes)
        
        # Compras
        compras = await db.compras.find({
            "created_at": {"$gte": start_iso, "$lte": end_iso}
        }, {"_id": 0, "total_factura": 1}).to_list(10000)
        
        gastos_compras = sum(c.get("total_factura", 0) or 0 for c in compras)
        
        # Calcular beneficio
        total_gastos = gastos_compras + costes
        beneficio = ingresos - total_gastos
        
        resultados.append({
            "mes": f"{year}-{month:02d}",
            "nombre_mes": start_date.strftime("%b %Y"),
            "ingresos": round(ingresos, 2),
            "gastos": round(total_gastos, 2),
            "beneficio": round(beneficio, 2),
            "ordenes_enviadas": len(ordenes),
            "compras_realizadas": len(compras)
        })
    
    return {
        "meses": meses,
        "datos": resultados,
        "totales": {
            "ingresos": round(sum(r["ingresos"] for r in resultados), 2),
            "gastos": round(sum(r["gastos"] for r in resultados), 2),
            "beneficio": round(sum(r["beneficio"] for r in resultados), 2)
        }
    }


# ==================== DETALLE DE GASTOS ====================

@router.get("/gastos/detalle")
async def detalle_gastos(
    periodo: PeriodoFinanciero = PeriodoFinanciero.MES,
    user: dict = Depends(require_admin)
):
    """
    Detalle de gastos por categoría.
    """
    now = datetime.now(timezone.utc)
    
    if periodo == PeriodoFinanciero.MES:
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif periodo == PeriodoFinanciero.TRIMESTRE:
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        start_date = now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    start_iso = start_date.isoformat()
    
    # Compras por proveedor
    compras = await db.compras.find({
        "created_at": {"$gte": start_iso}
    }, {"_id": 0}).to_list(10000)
    
    por_proveedor = {}
    for c in compras:
        prov = c.get("proveedor_nombre", "Sin proveedor")
        if prov not in por_proveedor:
            por_proveedor[prov] = {"cantidad": 0, "total": 0}
        por_proveedor[prov]["cantidad"] += 1
        por_proveedor[prov]["total"] += c.get("total_factura", 0) or 0
    
    # Materiales más usados en órdenes
    ordenes = await db.ordenes.find({
        "estado": "enviado",
        "fecha_enviado": {"$gte": start_iso}
    }, {"_id": 0, "materiales": 1}).to_list(10000)
    
    materiales_consumo = {}
    for o in ordenes:
        for mat in o.get("materiales", []):
            nombre = mat.get("nombre", "Sin nombre")
            if nombre not in materiales_consumo:
                materiales_consumo[nombre] = {"cantidad": 0, "coste_total": 0}
            cantidad = mat.get("cantidad", 0) or 0
            coste = mat.get("coste", 0) or 0
            materiales_consumo[nombre]["cantidad"] += cantidad
            materiales_consumo[nombre]["coste_total"] += cantidad * coste
    
    # Ordenar por coste
    top_materiales = sorted(
        [{"nombre": k, **v} for k, v in materiales_consumo.items()],
        key=lambda x: x["coste_total"],
        reverse=True
    )[:10]
    
    return {
        "periodo": periodo.value,
        "compras_por_proveedor": [
            {"proveedor": k, **v} for k, v in sorted(
                por_proveedor.items(), 
                key=lambda x: x[1]["total"], 
                reverse=True
            )
        ],
        "top_materiales_consumidos": top_materiales,
        "totales": {
            "compras": round(sum(c.get("total_factura", 0) or 0 for c in compras), 2),
            "materiales_consumidos": round(sum(m["coste_total"] for m in top_materiales), 2)
        }
    }


# ==================== VALOR DEL INVENTARIO ====================

@router.get("/inventario/valor")
async def valor_inventario(user: dict = Depends(require_admin)):
    """
    Análisis detallado del valor del inventario.
    """
    # Todos los repuestos con stock
    repuestos = await db.repuestos.find(
        {},
        {"_id": 0, "id": 1, "nombre": 1, "sku": 1, "stock": 1, 
         "precio_compra": 1, "precio_venta": 1, "categoria": 1, "proveedor": 1}
    ).to_list(50000)
    
    # Calcular valores
    con_stock = [r for r in repuestos if (r.get("stock") or 0) > 0]
    sin_stock = [r for r in repuestos if (r.get("stock") or 0) <= 0]
    
    valor_total_coste = 0
    valor_total_venta = 0
    por_categoria = {}
    por_proveedor = {}
    
    for r in con_stock:
        stock = r.get("stock", 0) or 0
        coste = r.get("precio_compra", 0) or 0
        venta = r.get("precio_venta", 0) or 0
        
        valor_coste = stock * coste
        valor_venta = stock * venta
        
        valor_total_coste += valor_coste
        valor_total_venta += valor_venta
        
        # Por categoría
        cat = r.get("categoria", "Sin categoría")
        if cat not in por_categoria:
            por_categoria[cat] = {"items": 0, "unidades": 0, "valor_coste": 0, "valor_venta": 0}
        por_categoria[cat]["items"] += 1
        por_categoria[cat]["unidades"] += stock
        por_categoria[cat]["valor_coste"] += valor_coste
        por_categoria[cat]["valor_venta"] += valor_venta
        
        # Por proveedor
        prov = r.get("proveedor", "Sin proveedor")
        if prov not in por_proveedor:
            por_proveedor[prov] = {"items": 0, "unidades": 0, "valor_coste": 0, "valor_venta": 0}
        por_proveedor[prov]["items"] += 1
        por_proveedor[prov]["unidades"] += stock
        por_proveedor[prov]["valor_coste"] += valor_coste
        por_proveedor[prov]["valor_venta"] += valor_venta
    
    # Top 10 productos más valiosos
    productos_valor = sorted(con_stock, key=lambda x: (x.get("stock", 0) or 0) * (x.get("precio_compra", 0) or 0), reverse=True)[:10]
    top_productos = [
        {
            "nombre": p.get("nombre"),
            "sku": p.get("sku"),
            "stock": p.get("stock", 0),
            "precio_compra": p.get("precio_compra", 0),
            "valor_total": round((p.get("stock", 0) or 0) * (p.get("precio_compra", 0) or 0), 2)
        }
        for p in productos_valor
    ]
    
    return {
        "resumen": {
            "total_referencias": len(repuestos),
            "con_stock": len(con_stock),
            "sin_stock": len(sin_stock),
            "unidades_totales": sum(r.get("stock", 0) or 0 for r in con_stock),
            "valor_coste": round(valor_total_coste, 2),
            "valor_venta": round(valor_total_venta, 2),
            "margen_potencial": round(valor_total_venta - valor_total_coste, 2),
            "margen_porcentaje": round((valor_total_venta - valor_total_coste) / valor_total_coste * 100, 1) if valor_total_coste > 0 else 0
        },
        "por_categoria": [
            {"categoria": k, **{kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()}} 
            for k, v in sorted(por_categoria.items(), key=lambda x: x[1]["valor_coste"], reverse=True)
        ],
        "por_proveedor": [
            {"proveedor": k, **{kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()}} 
            for k, v in sorted(por_proveedor.items(), key=lambda x: x[1]["valor_coste"], reverse=True)
        ],
        "top_productos_valor": top_productos
    }


# ==================== REGISTRAR COMPRA EN CONTABILIDAD ====================

@router.post("/registrar-compra/{compra_id}")
async def registrar_compra_contabilidad(
    compra_id: str,
    user: dict = Depends(require_admin)
):
    """
    Registra una compra como factura de compra en contabilidad.
    Esto conecta el módulo de compras con contabilidad.
    """
    compra = await db.compras.find_one({"id": compra_id}, {"_id": 0})
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    
    # Verificar si ya está registrada
    factura_existente = await db.facturas.find_one({
        "tipo": "compra",
        "referencia_compra_id": compra_id
    }, {"_id": 0})
    
    if factura_existente:
        return {"message": "Esta compra ya está registrada en contabilidad", "factura_id": factura_existente.get("id")}
    
    # Crear factura de compra
    now = datetime.now(timezone.utc)
    factura_id = str(uuid.uuid4())
    
    # Generar número de factura de compra
    año = now.year
    ultimo = await db.contabilidad_series.find_one({"tipo": "factura_compra", "año": año})
    siguiente_num = (ultimo.get("ultimo_numero", 0) if ultimo else 0) + 1
    numero_factura = f"FC-{año}-{siguiente_num:05d}"
    
    # Crear líneas de factura desde productos de la compra
    lineas = []
    for prod in compra.get("productos", []):
        lineas.append({
            "descripcion": prod.get("descripcion", ""),
            "cantidad": prod.get("cantidad", 1),
            "precio_unitario": prod.get("precio_unitario", 0),
            "iva_porcentaje": prod.get("iva", 21),
            "subtotal": prod.get("precio_total", 0)
        })
    
    factura_doc = {
        "id": factura_id,
        "tipo": "compra",
        "numero": numero_factura,
        "numero_factura_proveedor": compra.get("numero_factura"),
        "proveedor_id": compra.get("proveedor_id"),
        "proveedor_nombre": compra.get("proveedor_nombre"),
        "fecha_factura": compra.get("fecha_factura"),
        "fecha_emision": now.isoformat(),
        "lineas": lineas,
        "base_imponible": compra.get("base_imponible", 0),
        "total_iva": compra.get("total_iva", 0),
        "total": compra.get("total_factura", 0),
        "estado": "emitida",
        "pendiente_cobro": compra.get("total_factura", 0),
        "año_fiscal": año,
        "referencia_compra_id": compra_id,
        "created_at": now.isoformat(),
        "created_by": user.get("email")
    }
    
    await db.facturas.insert_one(factura_doc)
    
    # Actualizar serie
    await db.contabilidad_series.update_one(
        {"tipo": "factura_compra", "año": año},
        {"$set": {"ultimo_numero": siguiente_num}},
        upsert=True
    )
    
    # Marcar compra como contabilizada
    await db.compras.update_one(
        {"id": compra_id},
        {"$set": {"contabilizada": True, "factura_id": factura_id, "updated_at": now.isoformat()}}
    )
    
    logger.info(f"Compra {compra_id} registrada en contabilidad como factura {numero_factura}")
    
    return {
        "message": "Compra registrada en contabilidad",
        "factura_id": factura_id,
        "numero_factura": numero_factura
    }


# ==================== REGISTRAR ORDEN COMO INGRESO ====================

@router.post("/registrar-orden/{orden_id}")
async def registrar_orden_ingreso(
    orden_id: str,
    user: dict = Depends(require_admin)
):
    """
    Registra una orden enviada como factura de venta.
    Solo funciona con órdenes en estado 'enviado'.
    """
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    if orden.get("estado") != "enviado":
        raise HTTPException(status_code=400, detail="Solo se pueden facturar órdenes enviadas")
    
    # Verificar si ya está facturada
    factura_existente = await db.facturas.find_one({
        "tipo": "venta",
        "orden_id": orden_id
    }, {"_id": 0})
    
    if factura_existente:
        return {"message": "Esta orden ya está facturada", "factura_id": factura_existente.get("id")}
    
    # Obtener cliente
    cliente = await db.clientes.find_one({"id": orden.get("cliente_id")}, {"_id": 0})
    
    now = datetime.now(timezone.utc)
    factura_id = str(uuid.uuid4())
    
    # Generar número de factura
    año = now.year
    ultimo = await db.contabilidad_series.find_one({"tipo": "factura_venta", "año": año})
    siguiente_num = (ultimo.get("ultimo_numero", 0) if ultimo else 0) + 1
    numero_factura = f"FV-{año}-{siguiente_num:05d}"
    
    # Crear líneas desde materiales
    lineas = []
    for mat in orden.get("materiales", []):
        lineas.append({
            "descripcion": mat.get("nombre", "Material"),
            "cantidad": mat.get("cantidad", 1),
            "precio_unitario": mat.get("precio_unitario", 0),
            "iva_porcentaje": mat.get("iva", 21),
            "subtotal": mat.get("cantidad", 1) * mat.get("precio_unitario", 0)
        })
    
    # Añadir mano de obra si existe
    if orden.get("mano_obra", 0) > 0:
        lineas.append({
            "descripcion": "Mano de obra",
            "cantidad": 1,
            "precio_unitario": orden.get("mano_obra", 0),
            "iva_porcentaje": 21,
            "subtotal": orden.get("mano_obra", 0)
        })
    
    factura_doc = {
        "id": factura_id,
        "tipo": "venta",
        "numero": numero_factura,
        "cliente_id": orden.get("cliente_id"),
        "cliente_nombre": f"{cliente.get('nombre', '')} {cliente.get('apellidos', '')}".strip() if cliente else "Cliente",
        "cliente_email": cliente.get("email") if cliente else None,
        "orden_id": orden_id,
        "numero_orden": orden.get("numero_orden"),
        "fecha_emision": now.isoformat(),
        "lineas": lineas,
        "base_imponible": orden.get("base_imponible", 0) or orden.get("presupuesto_total", 0),
        "total_iva": orden.get("total_iva", 0),
        "total": orden.get("presupuesto_total", 0),
        "estado": "emitida",
        "pendiente_cobro": orden.get("presupuesto_total", 0),
        "año_fiscal": año,
        "created_at": now.isoformat(),
        "created_by": user.get("email")
    }
    
    await db.facturas.insert_one(factura_doc)
    
    # Actualizar serie
    await db.contabilidad_series.update_one(
        {"tipo": "factura_venta", "año": año},
        {"$set": {"ultimo_numero": siguiente_num}},
        upsert=True
    )
    
    # Marcar orden como facturada
    await db.ordenes.update_one(
        {"id": orden_id},
        {"$set": {"facturada": True, "factura_id": factura_id, "updated_at": now.isoformat()}}
    )
    
    logger.info(f"Orden {orden.get('numero_orden')} facturada como {numero_factura}")
    
    return {
        "message": "Orden facturada correctamente",
        "factura_id": factura_id,
        "numero_factura": numero_factura
    }


# ==================== BALANCE GENERAL ====================

@router.get("/balance")
async def balance_general(
    año: int = None,
    user: dict = Depends(require_master)
):
    """
    Balance general del negocio.
    """
    año = año or datetime.now().year
    start_date = datetime(año, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(año, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    
    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()
    
    # Ingresos totales
    ordenes = await db.ordenes.find({
        "estado": "enviado",
        "fecha_enviado": {"$gte": start_iso, "$lte": end_iso}
    }, {"_id": 0, "presupuesto_total": 1, "coste_total": 1}).to_list(100000)
    
    ingresos_ordenes = sum(o.get("presupuesto_total", 0) or 0 for o in ordenes)
    costes_ordenes = sum(o.get("coste_total", 0) or 0 for o in ordenes)
    
    # Compras totales
    compras = await db.compras.find({
        "created_at": {"$gte": start_iso, "$lte": end_iso}
    }, {"_id": 0, "total_factura": 1}).to_list(100000)
    
    total_compras = sum(c.get("total_factura", 0) or 0 for c in compras)
    
    # Valor del inventario actual
    inventario = await db.repuestos.find(
        {"stock": {"$gt": 0}},
        {"_id": 0, "stock": 1, "precio_compra": 1, "precio_venta": 1}
    ).to_list(50000)
    
    valor_inventario = sum((r.get("stock", 0) or 0) * (r.get("precio_compra", 0) or 0) for r in inventario)
    
    # Cuentas por cobrar
    facturas_pendientes = await db.facturas.find({
        "tipo": "venta",
        "estado": {"$in": ["emitida", "parcial", "vencida"]},
        "año_fiscal": año
    }, {"_id": 0, "pendiente_cobro": 1}).to_list(10000)
    
    por_cobrar = sum(f.get("pendiente_cobro", 0) or 0 for f in facturas_pendientes)
    
    # Cuentas por pagar
    facturas_por_pagar = await db.facturas.find({
        "tipo": "compra",
        "estado": {"$in": ["emitida", "parcial", "vencida"]},
        "año_fiscal": año
    }, {"_id": 0, "pendiente_cobro": 1}).to_list(10000)
    
    por_pagar = sum(f.get("pendiente_cobro", 0) or 0 for f in facturas_por_pagar)
    
    # Beneficio neto
    beneficio_operativo = ingresos_ordenes - costes_ordenes - total_compras
    
    return {
        "año": año,
        "activos": {
            "inventario": round(valor_inventario, 2),
            "cuentas_por_cobrar": round(por_cobrar, 2),
            "total_activos": round(valor_inventario + por_cobrar, 2)
        },
        "pasivos": {
            "cuentas_por_pagar": round(por_pagar, 2),
            "total_pasivos": round(por_pagar, 2)
        },
        "resultados": {
            "ingresos_brutos": round(ingresos_ordenes, 2),
            "costes_directos": round(costes_ordenes, 2),
            "compras": round(total_compras, 2),
            "beneficio_operativo": round(beneficio_operativo, 2),
            "margen_operativo": round(beneficio_operativo / ingresos_ordenes * 100, 1) if ingresos_ordenes > 0 else 0
        },
        "metricas": {
            "ordenes_completadas": len(ordenes),
            "compras_realizadas": len(compras),
            "ticket_medio": round(ingresos_ordenes / len(ordenes), 2) if ordenes else 0
        }
    }

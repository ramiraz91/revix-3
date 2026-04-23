"""
Endpoint de asistencia al triador: ejecuta las 3 tools del agente `triador_averias`
de forma encadenada y devuelve un informe completo para mostrar en un popup.

Flujo:
  1. proponer_diagnostico (síntomas de la OT + dispositivo)
  2. sugerir_repuestos (si hay diagnóstico match)
  3. recomendar_tecnico (si hay tipo_reparacion sugerido)

NO modifica la orden. Solo lectura + sugerencia. Requiere rol admin o técnico.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import db
from auth import require_auth

logger = logging.getLogger("revix.triador")

router = APIRouter(prefix="/ordenes", tags=["Triador de Averías · UI"])


class TriadorDiagnosticoResponse(BaseModel):
    order_id: str
    numero_orden: str
    diagnostico: dict
    repuestos: Optional[dict] = None
    tecnico: Optional[dict] = None
    preview: bool = True


@router.post("/{order_id}/triador-diagnostico", response_model=TriadorDiagnosticoResponse)
async def ejecutar_triador_diagnostico(
    order_id: str, user: dict = Depends(require_auth),
):
    """Encadena las 3 tools del triador para la OT indicada."""
    orden = await db.ordenes.find_one(
        {"$or": [{"id": order_id}, {"numero_orden": order_id}]},
        {"_id": 0},
    )
    if not orden:
        raise HTTPException(404, "Orden no encontrada")

    # ── 1. proponer_diagnostico ──────────────────────────────────────────────
    # Llamada directa al handler de la tool (sin pasar por LLM) — más rápido
    # y determinístico para UI. Usa el mismo código de catálogo heurístico.
    import sys
    sys.path.insert(0, "/app")
    from revix_mcp.tools.triador_averias import (
        _match_rule, _SYMPTOM_RULES,  # noqa: F401  (uso directo)
    )

    sintomas = (
        orden.get("averia_descripcion")
        or orden.get("problema_reportado")
        or orden.get("diagnostico_tecnico")
        or orden.get("descripcion")
        or ""
    )
    dispositivo = orden.get("dispositivo") or {}
    marca = dispositivo.get("marca", "")
    modelo = dispositivo.get("modelo", "")

    if not sintomas.strip():
        return TriadorDiagnosticoResponse(
            order_id=orden["id"],
            numero_orden=orden.get("numero_orden", ""),
            diagnostico={
                "success": False, "error": "sin_averia_descripcion",
                "mensaje": "La orden no tiene descripción de avería para analizar.",
            },
        )

    rule = _match_rule(sintomas)
    if not rule:
        diagnostico = {
            "success": True,
            "diagnostico_match": False,
            "sintomas_analizados": sintomas,
            "dispositivo": {"marca": marca, "modelo": modelo},
            "causas_probables": [],
            "repuestos_ref": [],
            "tipo_reparacion_sugerido": None,
            "confianza_global": 0.0,
            "mensaje": (
                "Sin coincidencias automáticas en el catálogo heurístico. "
                "Recomienda escalar a diagnóstico manual del técnico."
            ),
        }
        return TriadorDiagnosticoResponse(
            order_id=orden["id"],
            numero_orden=orden.get("numero_orden", ""),
            diagnostico=diagnostico,
            preview=True,
        )

    causas = [
        {"causa": c, "confianza": round(cf, 2)} for (c, cf) in rule["causas"]
    ]
    confianza_global = round(max(c["confianza"] for c in causas), 2)
    diagnostico = {
        "success": True,
        "diagnostico_match": True,
        "sintomas_analizados": sintomas,
        "dispositivo": {"marca": marca, "modelo": modelo},
        "causas_probables": causas,
        "repuestos_ref": rule["repuestos_ref"],
        "tipo_reparacion_sugerido": rule["tipo_reparacion"],
        "confianza_global": confianza_global,
    }

    # ── 2. sugerir_repuestos ────────────────────────────────────────────────
    repuestos_ref = rule["repuestos_ref"]
    sugerencias: list[dict] = []
    for ref in repuestos_ref:
        query = {
            "$or": [
                {"nombre": {"$regex": ref, "$options": "i"}},
                {"descripcion": {"$regex": ref, "$options": "i"}},
                {"categoria": {"$regex": ref, "$options": "i"}},
            ],
        }
        if modelo:
            query = {"$and": [query, {"$or": [
                {"modelo_compatible": {"$regex": modelo, "$options": "i"}},
                {"nombre": {"$regex": modelo, "$options": "i"}},
            ]}]}
        items = await db.inventario.find(
            query,
            {"_id": 0, "id": 1, "sku_corto": 1, "nombre": 1, "stock": 1,
             "precio_venta": 1, "proveedor": 1, "ubicacion": 1, "categoria": 1},
        ).limit(8).to_list(8)
        items.sort(key=lambda it: (0 if (it.get("stock") or 0) >= 1 else 1,
                                   float(it.get("precio_venta") or 0)))
        sugerencias.append({
            "repuesto_ref": ref,
            "encontrados": len(items),
            "mejor_opcion": items[0] if items else None,
            "alternativas": items[1:4],
            "hay_stock_directo": bool(items and (items[0].get("stock") or 0) >= 1),
        })
    con_stock = sum(1 for s in sugerencias if s["hay_stock_directo"])
    repuestos = {
        "success": True,
        "total_repuestos_consultados": len(repuestos_ref),
        "con_stock_inmediato": con_stock,
        "sugerencias": sugerencias,
        "veredicto": (
            "OK para arrancar: stock disponible en todos."
            if con_stock == len(repuestos_ref)
            else (
                "Parcial: falta stock en algunos repuestos."
                if con_stock > 0 else "Sin stock directo. Consultar proveedor."
            )
        ),
    }

    # ── 3. recomendar_tecnico ───────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    hace_30 = (now - timedelta(days=30)).isoformat()
    tecnicos = await db.users.find(
        {"$or": [{"rol": "tecnico"}, {"rol": "admin"}], "activo": {"$ne": False}},
        {"_id": 0, "id": 1, "email": 1, "nombre": 1,
         "especialidades": 1, "rol": 1},
    ).to_list(100)
    ranking: list[dict] = []
    tipo_reparacion = rule["tipo_reparacion"]
    for t in tecnicos:
        ident = t.get("id") or t.get("email")
        carga = await db.ordenes.count_documents({
            "tecnico_asignado": ident,
            "estado": {"$in": ["recibida", "en_taller", "re_presupuestar", "validacion"]},
        })
        reparadas = await db.ordenes.count_documents({
            "tecnico_asignado": ident,
            "estado": {"$in": ["reparado", "enviado"]},
            "updated_at": {"$gte": hace_30},
        })
        especialista = tipo_reparacion.lower() in [
            str(x).lower() for x in (t.get("especialidades") or [])
        ]
        score = (50 - carga * 5) + (reparadas * 0.5) + (20 if especialista else 0)
        ranking.append({
            "id": ident, "email": t.get("email"),
            "nombre": t.get("nombre") or t.get("email"),
            "carga_actual": carga, "reparadas_30d": reparadas,
            "especialista_en_tipo": especialista,
            "especialidades": [str(e).lower() for e in (t.get("especialidades") or [])],
            "score": round(score, 2),
        })
    ranking.sort(key=lambda r: r["score"], reverse=True)
    tecnico = None
    if ranking:
        top = ranking[0]
        tecnico = {
            "success": True,
            "tipo_reparacion": tipo_reparacion,
            "recomendado": top,
            "ranking": ranking[:5],
            "razon": (
                f'Recomendado {top["nombre"]}: {top["carga_actual"]} en curso, '
                f'{top["reparadas_30d"]} reparadas/30d'
                + (', especialista en este tipo' if top["especialista_en_tipo"] else '')
                + '.'
            ),
        }

    return TriadorDiagnosticoResponse(
        order_id=orden["id"],
        numero_orden=orden.get("numero_orden", ""),
        diagnostico=diagnostico,
        repuestos=repuestos,
        tecnico=tecnico,
        preview=True,
    )

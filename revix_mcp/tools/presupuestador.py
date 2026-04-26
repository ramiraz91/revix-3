"""
Tools del agente `presupuestador_publico` (Fase 4 · Cara al cliente).

Tools registradas:
  1. consultar_catalogo_servicios    (catalog:read)
  2. estimar_precio_reparacion       (catalog:read)
  3. crear_presupuesto_publico       (quotes:write_public)

Reglas de seguridad:
  - SIN scopes: customers:read, orders:write, finance:*
  - Escribe SOLO en `pre_registros`, NUNCA en `ordenes`.
  - Disclaimer obligatorio en toda respuesta.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

from ..auth import AgentIdentity, AuthError
from ._common import validate_input
from ._registry import ToolSpec, register


def _require(identity: AgentIdentity, *scopes: str) -> None:
    for s in scopes:
        if not identity.has_scope(s):
            raise AuthError(
                f'Scope requerido "{s}" no presente en agente "{identity.agent_id}"',
            )


DISCLAIMER = (
    "Este presupuesto es orientativo y puede variar tras diagnóstico presencial. "
    "No constituye compromiso de precio ni plazo."
)


# ══════════════════════════════════════════════════════════════════════════════
# 1 · consultar_catalogo_servicios
# ══════════════════════════════════════════════════════════════════════════════

class ConsultarCatalogoInput(BaseModel):
    tipo_dispositivo: Optional[str] = None
    tipo_reparacion: Optional[str] = None


async def _consultar_catalogo_servicios_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require(identity, "catalog:read")
    p = validate_input(ConsultarCatalogoInput, params)

    q: dict = {"activo": {"$ne": False}}
    if p.tipo_dispositivo:
        q["tipo_dispositivo"] = {"$regex": p.tipo_dispositivo, "$options": "i"}
    if p.tipo_reparacion:
        q["tipo_reparacion"] = {"$regex": p.tipo_reparacion, "$options": "i"}

    items = await db.catalogo_servicios.find(q, {"_id": 0}).limit(60).to_list(60)
    if not items:
        # Fallback: agrupar a partir de repuestos del catálogo
        agrup: dict = {}
        async for r in db.repuestos.find(
            {"es_catalogo_referencia": True}, {"_id": 0},
        ):
            cat = r.get("categoria") or "Otros"
            modelo = r.get("modelo_compatible") or r.get("nombre", "")
            key = (cat, modelo[:50])
            if key not in agrup:
                agrup[key] = {
                    "tipo_dispositivo": cat,
                    "modelo": modelo,
                    "tipo_reparacion": "Sustitución pantalla",
                    "precios": [],
                    "repuestos_referencia": [],
                }
            agrup[key]["precios"].append(float(r.get("precio_venta") or 0))
            agrup[key]["repuestos_referencia"].append(r.get("sku"))
        for v in agrup.values():
            ps = [p for p in v["precios"] if p > 0]
            v["precio_min"] = min(ps) if ps else 0
            v["precio_max"] = max(ps) if ps else 0
            v["tiempo_estimado"] = "1-2 días laborables"
            v.pop("precios")
        items = list(agrup.values())[:60]

    return {"success": True, "total": len(items), "servicios": items,
            "disclaimer": DISCLAIMER}


register(ToolSpec(
    name="consultar_catalogo_servicios",
    description="Lista servicios de reparación disponibles con rangos de precio orientativos.",
    required_scope="catalog:read",
    input_schema={
        "type": "object",
        "properties": {
            "tipo_dispositivo": {"type": "string"},
            "tipo_reparacion": {"type": "string"},
        },
        "additionalProperties": False,
    },
    handler=_consultar_catalogo_servicios_handler,
))


# ══════════════════════════════════════════════════════════════════════════════
# 2 · estimar_precio_reparacion
# ══════════════════════════════════════════════════════════════════════════════

class EstimarPrecioInput(BaseModel):
    tipo_dispositivo: str = Field(..., min_length=2, max_length=40)
    marca: Optional[str] = None
    modelo: str = Field(..., min_length=1, max_length=80)
    descripcion_averia: str = Field(..., min_length=4, max_length=500)


# Multiplicadores orientativos por tipo de avería detectada
AVERIA_KEYWORDS = {
    "pantalla": ("pantalla", 1.0, "Sustitución pantalla"),
    "bateria":  ("batería",   0.45, "Sustitución batería"),
    "carga":    ("conector de carga", 0.55, "Reparación conector carga"),
    "altavoz":  ("altavoz",   0.40, "Reparación altavoz"),
    "auricular": ("auricular", 0.45, "Reparación auricular"),
    "agua":     ("daño líquido", 1.20, "Limpieza tras daño líquido"),
    "no enciende": ("placa base", 1.50, "Diagnóstico/reparación placa"),
    "camara":   ("cámara",    0.60, "Sustitución cámara"),
    "cristal":  ("pantalla",  1.0,  "Sustitución pantalla"),
}

MIN_PRECIO_DIAGNOSTICO = 25.0  # diagnóstico mínimo si no hay match


async def _estimar_precio_reparacion_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require(identity, "catalog:read")
    p = validate_input(EstimarPrecioInput, params)
    descr = (p.descripcion_averia or "").lower()

    # Detectar tipo avería
    tipo_averia = None
    factor = 1.0
    label = "Reparación general"
    for k, (lbl, f, label_full) in AVERIA_KEYWORDS.items():
        if k in descr:
            tipo_averia = lbl
            factor = f
            label = label_full
            break

    # Buscar repuestos del catálogo que casen con modelo
    modelo_q = p.modelo.strip()
    repuestos = await db.repuestos.find(
        {
            "$or": [
                {"modelo_compatible": {"$regex": modelo_q, "$options": "i"}},
                {"nombre": {"$regex": modelo_q, "$options": "i"}},
            ],
        },
        {"_id": 0, "nombre": 1, "sku": 1, "precio_venta": 1, "precio_compra": 1},
    ).limit(20).to_list(20)

    precios_pantalla = [
        float(r.get("precio_venta") or 0) for r in repuestos
        if (r.get("precio_venta") or 0) > 0
    ]

    if precios_pantalla:
        base_min = min(precios_pantalla) * factor
        base_max = max(precios_pantalla) * factor
        # Margen mano de obra +25-50€
        precio_min = round(base_min + 25.0, 2)
        precio_max = round(base_max + 50.0, 2)
        partidas = [
            {"concepto": label, "min": round(base_min, 2), "max": round(base_max, 2)},
            {"concepto": "Mano de obra", "min": 25.0, "max": 50.0},
        ]
        confianza = "alta" if len(precios_pantalla) >= 3 else "media"
    else:
        # Sin match, estimación conservadora
        precio_min = round(MIN_PRECIO_DIAGNOSTICO + 30.0, 2)
        precio_max = round(MIN_PRECIO_DIAGNOSTICO + 200.0, 2)
        partidas = [
            {"concepto": "Diagnóstico", "min": MIN_PRECIO_DIAGNOSTICO, "max": MIN_PRECIO_DIAGNOSTICO},
            {"concepto": "Reparación estimada", "min": 30.0, "max": 200.0},
        ]
        confianza = "baja"

    return {
        "success": True,
        "tipo_dispositivo": p.tipo_dispositivo,
        "marca": p.marca,
        "modelo": p.modelo,
        "tipo_averia_detectada": tipo_averia or "no clasificada",
        "rango_precio": {
            "min_eur": precio_min,
            "max_eur": precio_max,
            "moneda": "EUR",
        },
        "partidas": partidas,
        "tiempo_estimado": "1-2 días laborables tras recepción",
        "repuestos_referencia": [r.get("sku") for r in repuestos[:5]],
        "confianza": confianza,
        "disclaimer": DISCLAIMER,
    }


register(ToolSpec(
    name="estimar_precio_reparacion",
    description=(
        "Estima un rango de precio (min-max) para una reparación. SIEMPRE devuelve "
        "rango, nunca precio fijo. Adjunta disclaimer obligatorio."
    ),
    required_scope="catalog:read",
    input_schema={
        "type": "object",
        "properties": {
            "tipo_dispositivo": {"type": "string"},
            "marca": {"type": "string"},
            "modelo": {"type": "string"},
            "descripcion_averia": {"type": "string"},
        },
        "required": ["tipo_dispositivo", "modelo", "descripcion_averia"],
        "additionalProperties": False,
    },
    handler=_estimar_precio_reparacion_handler,
))


# ══════════════════════════════════════════════════════════════════════════════
# 3 · crear_presupuesto_publico
# ══════════════════════════════════════════════════════════════════════════════

class CrearPresupuestoPublicoInput(BaseModel):
    nombre_visitante: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    telefono: Optional[str] = Field(None, max_length=30)
    tipo_dispositivo: str
    marca: Optional[str] = None
    modelo: str
    descripcion_averia: str = Field(..., min_length=4, max_length=1000)
    estimacion_precio: Optional[dict] = None  # {min_eur, max_eur} ya calculado
    idempotency_key: str = Field(..., min_length=8, max_length=64)


async def _crear_presupuesto_publico_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require(identity, "quotes:write_public")
    p = validate_input(CrearPresupuestoPublicoInput, params)

    # Idempotencia
    existing = await db.pre_registros.find_one(
        {"idempotency_key": p.idempotency_key}, {"_id": 0, "id": 1},
    )
    if existing:
        return {"success": True, "deduped": True, "pre_registro_id": existing["id"],
                "disclaimer": DISCLAIMER}

    doc = {
        "id": str(uuid.uuid4()),
        "fuente": "presupuestador_publico",
        "nombre": p.nombre_visitante,
        "email": p.email,
        "telefono": p.telefono,
        "tipo_dispositivo": p.tipo_dispositivo,
        "marca": p.marca,
        "modelo": p.modelo,
        "descripcion_averia": p.descripcion_averia,
        "estimacion_precio": p.estimacion_precio,
        "estado": "pendiente",  # admin lo revisará y convertirá a OT si procede
        "idempotency_key": p.idempotency_key,
        "agente_origen": identity.agent_id,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "disclaimer": DISCLAIMER,
    }
    await db.pre_registros.insert_one(doc)

    # Notificar admins (categoría GENERAL para no llenar inbox Insurama)
    try:
        from modules.notificaciones.helper import create_notification
        admins = [u async for u in db.users.find(
            {"role": {"$in": ["master", "admin"]}, "is_active": {"$ne": False}},
            {"_id": 0, "id": 1},
        )]
        for adm in admins:
            await create_notification(
                db,
                categoria="GENERAL",
                tipo="presupuesto_publico_recibido",
                titulo="Nuevo presupuesto desde web",
                mensaje=(
                    f"{p.nombre_visitante} solicitó presupuesto para "
                    f"{p.tipo_dispositivo} {p.modelo} — {p.descripcion_averia[:80]}"
                ),
                user_id=adm.get("id"),
                source="agent:presupuestador",
                meta={"pre_registro_id": doc["id"], "email": p.email,
                      "telefono": p.telefono},
            )
    except Exception:
        pass

    return {
        "success": True,
        "deduped": False,
        "pre_registro_id": doc["id"],
        "estado": "pendiente",
        "disclaimer": DISCLAIMER,
    }


register(ToolSpec(
    name="crear_presupuesto_publico",
    description=(
        "Crea una entrada en pre_registros con el presupuesto solicitado. NO crea "
        "OT. Requiere idempotency_key. Disclaimer obligatorio incluido."
    ),
    required_scope="quotes:write_public",
    input_schema={
        "type": "object",
        "properties": {
            "nombre_visitante": {"type": "string"},
            "email": {"type": "string"},
            "telefono": {"type": "string"},
            "tipo_dispositivo": {"type": "string"},
            "marca": {"type": "string"},
            "modelo": {"type": "string"},
            "descripcion_averia": {"type": "string"},
            "estimacion_precio": {"type": "object"},
            "idempotency_key": {"type": "string"},
        },
        "required": ["nombre_visitante", "email", "tipo_dispositivo",
                     "modelo", "descripcion_averia", "idempotency_key"],
        "additionalProperties": False,
    },
    handler=_crear_presupuesto_publico_handler,
))

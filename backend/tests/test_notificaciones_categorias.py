"""
Tests del sistema de categorías de notificaciones.

Ejecutar con:
    /usr/local/bin/python3 -m pytest /app/backend/tests/test_notificaciones_categorias.py -v
"""
from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/app/backend")

from modules.notificaciones.helper import (  # noqa: E402
    CATEGORIAS, TIPO_A_CATEGORIA, categoria_from_tipo, create_notification,
)


def test_categorias_oficiales():
    """Las 7 categorías oficiales están definidas."""
    esperadas = {
        "LOGISTICA", "INCIDENCIA_LOGISTICA", "COMUNICACION_INTERNA",
        "RECHAZO", "MODIFICACION", "INCIDENCIA", "GENERAL",
    }
    assert set(CATEGORIAS) == esperadas


@pytest.mark.parametrize("tipo, cat_esperada", [
    ("gls_tracking_update",   "LOGISTICA"),
    ("gls_entregado",         "LOGISTICA"),
    ("gls_incidencia",        "INCIDENCIA_LOGISTICA"),
    ("presupuesto_rechazado", "RECHAZO"),
    ("orden_rechazada",       "RECHAZO"),
    ("aseguradora_rechazo",   "RECHAZO"),
    ("orden_estado_cambiado", "MODIFICACION"),
    ("orden_reasignada",      "MODIFICACION"),
    ("mensaje_admin",         "COMUNICACION_INTERNA"),
    ("incidencia_abierta",    "INCIDENCIA"),
    ("incidencia_agente",     "INCIDENCIA"),
    ("orden_reparada",        "GENERAL"),
    ("tipo_inexistente",      "GENERAL"),  # fallback
])
def test_categoria_from_tipo(tipo, cat_esperada):
    assert categoria_from_tipo(tipo) == cat_esperada


def test_tipo_categoria_map_cubre_todos_los_tipos_principales():
    """Asegura que los tipos críticos están mapeados."""
    tipos_criticos = [
        "gls_tracking_update", "gls_incidencia", "gls_entregado",
        "presupuesto_rechazado", "orden_estado_cambiado",
        "mensaje_admin", "incidencia_abierta",
    ]
    for t in tipos_criticos:
        assert t in TIPO_A_CATEGORIA, f"Falta mapeo para '{t}'"


# ──────────────────────────────────────────────────────────────────────────────
# create_notification con fake DB
# ──────────────────────────────────────────────────────────────────────────────

class FakeColl:
    def __init__(self):
        self.docs = []
    async def insert_one(self, doc):
        self.docs.append(dict(doc))
        return type("R", (), {"inserted_id": doc.get("id")})()
    async def find_one(self, query, projection=None):
        for d in self.docs:
            match = True
            for k, v in query.items():
                if k == "created_at" and isinstance(v, dict) and "$gte" in v:
                    if d.get("created_at", "") < v["$gte"]:
                        match = False; break
                elif d.get(k) != v:
                    match = False; break
            if match:
                return {"id": d["id"]}
        return None


class FakeDB:
    def __init__(self):
        self.notificaciones = FakeColl()


@pytest.mark.asyncio
async def test_create_notification_asigna_categoria_desde_tipo():
    db = FakeDB()
    await create_notification(db, tipo="gls_tracking_update", mensaje="test")
    assert len(db.notificaciones.docs) == 1
    doc = db.notificaciones.docs[0]
    assert doc["categoria"] == "LOGISTICA"
    assert doc["tipo"] == "gls_tracking_update"
    assert doc["leida"] is False


@pytest.mark.asyncio
async def test_create_notification_categoria_explicita_override():
    db = FakeDB()
    await create_notification(
        db, tipo="orden_reparada", mensaje="x",
        categoria="MODIFICACION",  # forzar distinta
    )
    assert db.notificaciones.docs[0]["categoria"] == "MODIFICACION"


@pytest.mark.asyncio
async def test_create_notification_categoria_desconocida_fallback_general():
    db = FakeDB()
    await create_notification(
        db, tipo="algo", mensaje="x", categoria="NO_EXISTE_XYZ",
    )
    assert db.notificaciones.docs[0]["categoria"] == "GENERAL"


@pytest.mark.asyncio
async def test_create_notification_dedupe_minutos():
    db = FakeDB()
    nid1 = await create_notification(
        db, tipo="orden_estado_cambiado", mensaje="cambio",
        orden_id="O1", skip_if_duplicate_minutes=5,
    )
    nid2 = await create_notification(
        db, tipo="orden_estado_cambiado", mensaje="cambio",
        orden_id="O1", skip_if_duplicate_minutes=5,
    )
    assert nid1 == nid2  # deduplica
    assert len(db.notificaciones.docs) == 1


@pytest.mark.asyncio
async def test_create_notification_meta_y_titulo_se_persisten():
    db = FakeDB()
    await create_notification(
        db, tipo="gls_incidencia", mensaje="x",
        titulo="Incidencia envío", meta={"codbarras": "ABC123"},
    )
    d = db.notificaciones.docs[0]
    assert d["titulo"] == "Incidencia envío"
    assert d["meta"] == {"codbarras": "ABC123"}
    assert d["categoria"] == "INCIDENCIA_LOGISTICA"

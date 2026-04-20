"""
Utilidades compartidas por todos los tools.
"""
from __future__ import annotations

from typing import Any


def strip_mongo_id(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    doc.pop('_id', None)
    return doc


def strip_many(docs: list[dict]) -> list[dict]:
    for d in docs:
        d.pop('_id', None)
    return docs


def validate_input(schema_cls, params: dict) -> Any:
    """Valida params con pydantic; devuelve instancia del modelo."""
    return schema_cls(**(params or {}))


# Proyecciones Mongo reutilizables: campos NO sensibles / útiles
ORDEN_PROJECTION = {
    '_id': 0,
    'password_hash': 0,
    'datos_portal.credenciales': 0,
}

CLIENTE_PROJECTION_PUBLIC = {
    '_id': 0,
    'notas_internas': 0,
}

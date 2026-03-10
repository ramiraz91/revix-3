"""
Rutas para acceso a manuales de reparación de Apple
"""
from fastapi import APIRouter, Query
from typing import Optional

from services.apple_manuals_service import (
    get_apple_documentation,
    get_all_supported_models,
    find_model_info,
    detect_repair_type
)

router = APIRouter(prefix="/api/apple-manuals", tags=["Apple Manuals"])


@router.get("/lookup")
async def lookup_model(
    model: str = Query(..., description="Nombre del modelo (ej: iPhone 15 Pro)"),
    problem: Optional[str] = Query(None, description="Descripción del problema (ej: pantalla rota)")
):
    """
    Busca documentación de Apple para un modelo específico.
    Opcionalmente detecta secciones relevantes basadas en el problema.
    """
    result = get_apple_documentation(model, problem)
    return result


@router.get("/models")
async def list_models():
    """Lista todos los modelos de iPhone soportados con sus URLs de documentación"""
    models = get_all_supported_models()
    return {
        "total": len(models),
        "models": models
    }


@router.get("/detect-repair-type")
async def detect_repair(
    problem: str = Query(..., description="Descripción del problema")
):
    """
    Detecta el tipo de reparación basándose en la descripción del problema.
    Útil para sugerir secciones del manual relevantes.
    """
    sections = detect_repair_type(problem)
    return {
        "problem": problem,
        "detected_sections": sections
    }

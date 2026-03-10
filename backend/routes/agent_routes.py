"""
Rutas API para el Agente ARIA (Asistente Revix de Inteligencia Artificial)
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from config import db, logger
from auth import require_auth, require_admin, require_master
from agent.agent_core import revix_agent

router = APIRouter(prefix="/agent", tags=["Agente IA"])

# ==================== MODELOS ====================

class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    functions_executed: List[dict] = []
    alerts: List[dict] = []
    timestamp: str

# ==================== ENDPOINTS ====================

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(data: ChatMessage, user: dict = Depends(require_admin)):
    """
    Envía un mensaje al agente ARIA y recibe una respuesta.
    El agente puede ejecutar acciones y consultar el sistema.
    """
    # Crear o recuperar conversación
    conversation_id = data.conversation_id or str(uuid.uuid4())
    
    # Cargar historial de conversación
    conversation = await db.agent_conversations.find_one({"id": conversation_id})
    history = conversation.get("messages", []) if conversation else []
    
    # Agregar mensaje del usuario al historial
    user_msg = {
        "role": "user",
        "content": data.message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    history.append(user_msg)
    
    # Procesar con el agente
    result = await revix_agent.process_message(
        user_message=data.message,
        user_info={"email": user.get("email"), "role": user.get("role")},
        conversation_history=history
    )
    
    # Agregar respuesta al historial
    assistant_msg = {
        "role": "assistant",
        "content": result["response"],
        "functions_executed": result.get("functions_executed", []),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    history.append(assistant_msg)
    
    # Guardar conversación
    await db.agent_conversations.update_one(
        {"id": conversation_id},
        {"$set": {
            "id": conversation_id,
            "user_email": user.get("email"),
            "messages": history,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    # Obtener alertas proactivas
    alerts = await revix_agent.get_proactive_alerts()
    
    return ChatResponse(
        response=result["response"],
        conversation_id=conversation_id,
        functions_executed=result.get("functions_executed", []),
        alerts=alerts[:5],  # Máximo 5 alertas
        timestamp=datetime.now(timezone.utc).isoformat()
    )

@router.get("/summary")
async def get_system_summary(user: dict = Depends(require_admin)):
    """
    Obtiene un resumen del estado actual del sistema.
    Incluye: peticiones pendientes, órdenes, alertas SLA.
    """
    summary = await revix_agent.get_daily_summary()
    alerts = await revix_agent.get_proactive_alerts()
    
    return {
        "summary": summary,
        "alerts": alerts,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/alerts")
async def get_active_alerts(user: dict = Depends(require_admin)):
    """
    Obtiene las alertas activas del sistema (SLA, pendientes, etc.)
    """
    alerts = await revix_agent.get_proactive_alerts()
    return {
        "alerts": alerts,
        "total": len(alerts),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/conversations")
async def list_conversations(user: dict = Depends(require_admin)):
    """
    Lista las conversaciones del usuario con el agente.
    """
    conversations = await db.agent_conversations.find(
        {"user_email": user.get("email")},
        {"_id": 0, "id": 1, "updated_at": 1, "messages": {"$slice": -1}}
    ).sort("updated_at", -1).limit(20).to_list(20)
    
    return {"conversations": conversations}

@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, user: dict = Depends(require_admin)):
    """
    Obtiene una conversación específica.
    """
    conversation = await db.agent_conversations.find_one(
        {"id": conversation_id},
        {"_id": 0}
    )
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    return conversation

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user: dict = Depends(require_admin)):
    """
    Elimina una conversación.
    """
    result = await db.agent_conversations.delete_one({"id": conversation_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return {"message": "Conversación eliminada"}

# ==================== ACCIONES RÁPIDAS ====================

@router.post("/quick-action/call-pending")
async def quick_action_list_pending_calls(user: dict = Depends(require_admin)):
    """
    Acción rápida: Lista peticiones pendientes de llamar.
    """
    from agent.revix_agent import fn_listar_peticiones_pendientes
    result = await fn_listar_peticiones_pendientes()
    return result

@router.post("/quick-action/validation-pending")
async def quick_action_list_validation_pending(user: dict = Depends(require_admin)):
    """
    Acción rápida: Lista órdenes pendientes de validación.
    """
    from agent.revix_agent import fn_listar_ordenes_validacion
    result = await fn_listar_ordenes_validacion()
    return result

@router.post("/quick-action/stats/{periodo}")
async def quick_action_stats(periodo: str, user: dict = Depends(require_admin)):
    """
    Acción rápida: Obtiene estadísticas del periodo (hoy, semana, mes).
    """
    from agent.revix_agent import fn_obtener_estadisticas
    result = await fn_obtener_estadisticas(periodo)
    return result

"""
Rutas de IA: mejorar texto, diagnósticos, consultas, historial.
Extraído de server.py durante refactorización.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

from config import db, EMERGENT_LLM_KEY, logger
import config as cfg
from auth import require_auth
from models import DiagnosticoRequest, IARequest, IAChatRequest

try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
except ImportError:
    LlmChat = None
    UserMessage = None

class MejorarDiagnosticoRequest(BaseModel):
    diagnostico: str
    modelo_dispositivo: Optional[str] = None
    sintomas: Optional[str] = None

router = APIRouter(prefix="/ia", tags=["ia"])

@router.post("/mejorar-texto")
async def ia_mejorar_texto(request: IARequest, user: dict = Depends(require_auth)):
    if not EMERGENT_LLM_KEY or not LlmChat:
        raise HTTPException(status_code=500, detail="LLM no configurado")
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"mejorar-{user['user_id']}-{uuid.uuid4()}", system_message="Eres un asistente de redacción para un servicio técnico de reparación de móviles. Mejora textos haciéndolos más claros y profesionales. IMPORTANTE: Escribe en texto plano, sin markdown, sin asteriscos, sin negritas. Responde SOLO con el texto mejorado en español.").with_model("gemini", "gemini-2.5-flash")
        prompt = f"Mejora el siguiente texto:\n\n{request.texto}"
        if request.contexto:
            prompt = f"Contexto: {request.contexto}\n\n{prompt}"
        response = await chat.send_message(UserMessage(text=prompt))
        return {"texto_mejorado": response, "original": request.texto}
    except Exception as e:
        logger.error(f"Error IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mejorar-diagnostico")
async def ia_mejorar_diagnostico(request: MejorarDiagnosticoRequest, user: dict = Depends(require_auth)):
    if not EMERGENT_LLM_KEY or not LlmChat:
        raise HTTPException(status_code=500, detail="LLM no configurado")
    try:
        # System message enfocado SOLO en mejorar el texto técnico
        system_msg = """Eres un técnico experto en reparación de dispositivos móviles. Tu ÚNICA tarea es mejorar el texto de diagnóstico que te proporcionen.

REGLAS ESTRICTAS:
1. SOLO mejora el texto del diagnóstico técnico proporcionado
2. NO incluyas información de clientes (nombres, teléfonos, direcciones, etc.)
3. NO inventes información que no esté en el texto original
4. Haz el texto más claro, profesional y técnicamente preciso
5. Usa terminología técnica correcta
6. Corrige errores ortográficos y gramaticales
7. Mantén la esencia del diagnóstico original
8. Responde SOLO con el diagnóstico mejorado, sin explicaciones adicionales
9. Texto plano, sin markdown ni formato especial
10. Responde siempre en español"""

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY, 
            session_id=f"diag-{user['user_id']}-{uuid.uuid4()}", 
            system_message=system_msg
        ).with_model("gemini", "gemini-2.5-flash")
        
        # Solo enviamos el diagnóstico a mejorar, sin contexto de cliente
        prompt = f"Mejora el siguiente diagnóstico técnico:\n\n{request.diagnostico}"
        
        # Opcionalmente añadir info del dispositivo (no del cliente)
        if request.modelo_dispositivo:
            prompt = f"Dispositivo: {request.modelo_dispositivo}\n\n{prompt}"
        
        response = await chat.send_message(UserMessage(text=prompt))
        return {"diagnostico_mejorado": response, "original": request.diagnostico}
    except Exception as e:
        logger.error(f"Error IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/consulta")
async def ia_consulta(request: IAChatRequest, user: dict = Depends(require_auth)):
    if not EMERGENT_LLM_KEY or not LlmChat:
        raise HTTPException(status_code=500, detail="LLM no configurado")
    try:
        historial = await db.ia_chat_history.find({"session_id": request.session_id, "user_id": user['user_id']}).sort("created_at", 1).to_list(20)
        ctx = "\n".join([f"{'Usuario' if m['role']=='user' else 'Asistente'}: {m['content']}" for m in historial[-10:]])
        
        # System prompt completo del sistema NEXORA
        system_prompt = """Eres el asistente IA de NEXORA, un sistema CRM/ERP completo para servicios técnicos de reparación de telefonía móvil.

MÓDULOS DEL SISTEMA:
1. ÓRDENES DE TRABAJO (/ordenes): Crear, gestionar y seguir reparaciones. Estados: pendiente_recibir, recibida, en_taller, re_presupuestar, reparado, validacion, enviado, garantia, cancelado, reemplazo, irreparable.
2. CLIENTES (/clientes): Base de datos de clientes con historial de órdenes.
3. INVENTARIO (/inventario): Gestión de repuestos, stock y etiquetas con código de barras.
4. INSURAMA (/insurama): Integración con seguros vía Sumbroker. Polling automático cada 30 min para detectar nuevos siniestros.
5. PRE-REGISTROS (/pre-registros): Siniestros de Insurama pendientes de convertir en órdenes.
6. LOGÍSTICA (/logistica): Control de recogidas y envíos con alertas de retraso +48h.
7. PROVEEDORES (/proveedores): Gestión de proveedores de piezas.
8. ÓRDENES DE COMPRA (/ordenes-compra): Registro de compras de material.
9. USUARIOS (/usuarios): Roles: master, admin, tecnico.
10. NOTIFICACIONES: Sistema en tiempo real con WebSocket y popups.
11. SCANNER (/scanner): Lectura de QR/códigos de barras para cambio rápido de estado.
12. CALENDARIO (/calendario): Vista de órdenes por fecha.

FUNCIONES DE IA DISPONIBLES:
- Diagnósticos inteligentes basados en síntomas
- Mejora de textos y diagnósticos
- Consultas sobre el sistema

ACCESO A DATOS:
Puedo ayudarte a entender cómo usar cualquier módulo, explicar flujos de trabajo y responder preguntas sobre el sistema.

FORMATO: Responde siempre en español, texto plano sin markdown.

Historial de conversación:
""" + ctx
        
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"consulta-{user['user_id']}-{request.session_id}", system_message=system_prompt).with_model("gemini", "gemini-2.5-flash")
        response = await chat.send_message(UserMessage(text=request.mensaje))
        now = datetime.now(timezone.utc).isoformat()
        await db.ia_chat_history.insert_many([{"session_id": request.session_id, "user_id": user['user_id'], "role": "user", "content": request.mensaje, "created_at": now}, {"session_id": request.session_id, "user_id": user['user_id'], "role": "assistant", "content": response, "created_at": now}])
        return {"respuesta": response, "session_id": request.session_id}
    except Exception as e:
        logger.error(f"Error IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/historial/{session_id}")
async def ia_historial(session_id: str, user: dict = Depends(require_auth)):
    return await db.ia_chat_history.find({"session_id": session_id, "user_id": user['user_id']}, {"_id": 0}).sort("created_at", 1).to_list(100)

@router.delete("/historial/{session_id}")
async def ia_limpiar_historial(session_id: str, user: dict = Depends(require_auth)):
    await db.ia_chat_history.delete_many({"session_id": session_id, "user_id": user['user_id']})
    return {"message": "Historial limpiado"}

@router.post("/diagnostico")
async def ia_diagnostico(modelo: str, sintomas: str, user: dict = Depends(require_auth)):
    if not EMERGENT_LLM_KEY or not LlmChat:
        raise HTTPException(status_code=500, detail="LLM no configurado")
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"diagnostico-{user['user_id']}-{uuid.uuid4()}", system_message="Eres un técnico experto en reparación de móviles. Proporciona diagnósticos basados en síntomas. FORMATO: Texto plano, sin markdown. Español.").with_model("gemini", "gemini-2.5-flash")
        response = await chat.send_message(UserMessage(text=f"Dispositivo: {modelo}\nSíntomas: {sintomas}\n\nProporciona diagnóstico."))
        return {"diagnostico": response, "modelo": modelo, "sintomas": sintomas}
    except Exception as e:
        logger.error(f"Error IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== RESTOS / DESPIECE ====================

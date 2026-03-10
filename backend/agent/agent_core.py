"""
REVIX AI AGENT - Core del Agente Conversacional Avanzado
Usa Gemini Flash para entender y responder, con ejecución de funciones.
"""
import os
import json
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from config import db, logger, EMERGENT_LLM_KEY
from agent.revix_agent import (
    SYSTEM_KNOWLEDGE, 
    AVAILABLE_FUNCTIONS, 
    FUNCTION_MAP,
    fn_detectar_alertas_sla,
    fn_obtener_resumen_sistema
)

# Intentar importar LlmChat de emergentintegrations
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    LLM_AVAILABLE = True
    logger.info("✅ emergentintegrations.llm.chat importado correctamente")
except ImportError as e:
    LLM_AVAILABLE = False
    logger.warning(f"emergentintegrations.llm.chat no disponible: {e}")

# ==================== SYSTEM PROMPT ====================

def build_system_prompt():
    """Construye el prompt del sistema con funciones disponibles"""
    functions_description = "\n".join([
        f"- **{name}**: {info['description']}\n  Parámetros: {json.dumps(info['parameters'], ensure_ascii=False) if info['parameters'] else 'ninguno'}"
        for name, info in AVAILABLE_FUNCTIONS.items()
    ])
    
    return f"""Eres ARIA (Asistente Revix de Inteligencia Artificial), el agente inteligente del sistema CRM de Revix.es.

## Tu Personalidad
- Profesional pero cercano y amable
- Hablas SIEMPRE en español
- Eres proactivo: si detectas problemas, los mencionas
- Ofreces ayuda adicional y sugerencias
- Respondes de forma clara y estructurada
- Usas emojis apropiados para hacer las respuestas más visuales

## Conocimiento del Sistema
{SYSTEM_KNOWLEDGE}

## Funciones Disponibles
Puedes ejecutar estas funciones para consultar datos o realizar acciones:

{functions_description}

## Cómo Ejecutar Funciones
Cuando necesites datos del sistema o realizar una acción, usa este formato EXACTO:
[FUNCTION: nombre_funcion(param1="valor1", param2="valor2")]

Ejemplos correctos:
- [FUNCTION: obtener_resumen_sistema()]
- [FUNCTION: buscar_orden(busqueda="OT-20250115-12345678")]
- [FUNCTION: listar_peticiones_pendientes()]
- [FUNCTION: actualizar_estado_orden(orden_id="OT-20250115-12345678", nuevo_estado="reparado", notas="Reparación completada")]
- [FUNCTION: obtener_estadisticas(periodo="semana")]

## Reglas Importantes
1. Si el usuario pregunta por datos del sistema, SIEMPRE usa la función apropiada primero
2. Interpreta los resultados y presenta la información de forma clara y amigable
3. Si detectas alertas o problemas, menciónalos aunque el usuario no pregunte
4. Cuando muestres listas, usa formato estructurado (tablas, viñetas, numeración)
5. Si una acción tiene consecuencias importantes, confirma antes de ejecutar
6. Nunca inventes datos - si no tienes información, dilo claramente

## Formato de Respuesta
- Usa **negrita** para destacar información importante
- Usa emojis relevantes: ✅ éxito, ⚠️ alerta, 🔴 crítico, 📊 datos, 📋 lista
- Organiza la información con encabezados cuando sea apropiado
- Sé conciso pero completo
"""

AGENT_SYSTEM_PROMPT = build_system_prompt()

# ==================== EJECUTOR DE FUNCIONES ====================

async def execute_function(function_name: str, parameters: dict = None) -> dict:
    """Ejecuta una función del agente"""
    if function_name not in FUNCTION_MAP:
        return {"error": f"Función no encontrada: {function_name}. Funciones disponibles: {list(FUNCTION_MAP.keys())}"}
    
    try:
        func = FUNCTION_MAP[function_name]
        if parameters:
            # Filtrar parámetros vacíos
            params = {k: v for k, v in parameters.items() if v is not None and v != ""}
            result = await func(**params)
        else:
            result = await func()
        return result
    except TypeError as e:
        logger.error(f"Error de parámetros en {function_name}: {e}")
        return {"error": f"Parámetros incorrectos para {function_name}: {str(e)}"}
    except Exception as e:
        logger.error(f"Error ejecutando función {function_name}: {e}")
        return {"error": str(e)}

# ==================== CLASE PRINCIPAL DEL AGENTE ====================

class RevixAgent:
    def __init__(self):
        self.api_key = EMERGENT_LLM_KEY
        self.available = LLM_AVAILABLE and bool(self.api_key)
        if self.available:
            logger.info("✅ RevixAgent inicializado correctamente")
        else:
            logger.warning("⚠️ RevixAgent: LLM no disponible")
    
    def _create_chat(self, session_id: str) -> Optional[Any]:
        """Crea una nueva instancia de chat"""
        if not self.available:
            return None
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=AGENT_SYSTEM_PROMPT
            ).with_model("gemini", "gemini-2.0-flash")
            return chat
        except Exception as e:
            logger.error(f"Error creando chat: {e}")
            return None
    
    async def process_message(self, user_message: str, user_info: dict = None, conversation_history: List[dict] = None) -> dict:
        """
        Procesa un mensaje del usuario y genera una respuesta.
        Ejecuta funciones si es necesario (hasta 3 iteraciones).
        """
        if not self.available:
            return {
                "response": "⚠️ Lo siento, el servicio de IA no está disponible en este momento. Por favor, contacta al administrador.",
                "functions_executed": [],
                "error": "LLM no configurado"
            }
        
        # Construir contexto
        user_email = user_info.get('email', 'desconocido') if user_info else 'desconocido'
        user_role = user_info.get('role', 'desconocido') if user_info else 'desconocido'
        
        context = f"""## Contexto de la Conversación
- **Usuario actual**: {user_email} (Rol: {user_role})
- **Fecha/Hora**: {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
        
        # Historial de conversación (últimos 6 mensajes)
        history_text = ""
        if conversation_history:
            recent_history = conversation_history[-6:]
            for msg in recent_history:
                role = "Usuario" if msg.get("role") == "user" else "ARIA"
                content = msg.get('content', '')[:500]  # Limitar longitud
                history_text += f"\n{role}: {content}"
            history_text = f"\n## Conversación Reciente{history_text}"
        
        # Crear sesión de chat única
        import uuid
        session_id = f"aria-{uuid.uuid4()}"
        
        # Prompt con contexto
        full_message = f"""{context}
{history_text}

## Mensaje del Usuario
{user_message}

Responde de forma útil. Si necesitas datos del sistema, usa las funciones disponibles."""

        functions_executed = []
        max_iterations = 3
        
        try:
            for iteration in range(max_iterations):
                # Crear nueva instancia de chat para esta iteración
                chat = self._create_chat(f"{session_id}-{iteration}")
                if not chat:
                    return {
                        "response": "⚠️ Error al inicializar el servicio de IA.",
                        "functions_executed": functions_executed,
                        "error": "No se pudo crear instancia de chat"
                    }
                
                # Enviar mensaje
                user_msg = UserMessage(text=full_message)
                response_text = await chat.send_message(user_msg)
                
                # Detectar llamadas a funciones
                function_pattern = r'\[FUNCTION:\s*(\w+)\((.*?)\)\]'
                matches = re.findall(function_pattern, response_text)
                
                if not matches:
                    # No hay más funciones que ejecutar
                    # Limpiar cualquier tag residual
                    final_response = re.sub(function_pattern, '', response_text).strip()
                    return {
                        "response": final_response,
                        "functions_executed": functions_executed,
                        "error": None
                    }
                
                # Ejecutar funciones encontradas
                iteration_results = []
                for func_name, params_str in matches:
                    # Parsear parámetros
                    params = {}
                    if params_str.strip():
                        # Parsear "key=value" o "key=\"value\""
                        param_pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\s\)]+))'
                        param_matches = re.findall(param_pattern, params_str)
                        for match in param_matches:
                            key = match[0]
                            value = match[1] or match[2] or match[3]  # Tomar el valor no vacío
                            params[key] = value
                    
                    # Ejecutar función
                    logger.info(f"Ejecutando función: {func_name}({params})")
                    result = await execute_function(func_name, params)
                    
                    functions_executed.append({
                        "function": func_name,
                        "params": params,
                        "result": result,
                        "iteration": iteration + 1
                    })
                    
                    iteration_results.append({
                        "function": func_name,
                        "result": result
                    })
                
                # Construir prompt con resultados
                results_json = json.dumps(iteration_results, ensure_ascii=False, indent=2, default=str)
                
                full_message = f"""{context}

## Resultados de Funciones Ejecutadas
```json
{results_json}
```

## Mensaje Original del Usuario
{user_message}

## Instrucciones
Ahora interpreta estos resultados y responde al usuario de forma clara y amigable.
- NO incluyas los tags [FUNCTION:...] en tu respuesta final
- Formatea los datos de forma legible (usa listas, emojis, estructura clara)
- Si los datos muestran alertas o problemas, destácalos
- Si el usuario necesita más información, ofrece ayuda adicional
- Si necesitas más datos, puedes llamar a otra función"""
            
            # Si llegamos aquí, se agotaron las iteraciones
            final_response = re.sub(function_pattern, '', response_text).strip()
            return {
                "response": final_response,
                "functions_executed": functions_executed,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error en RevixAgent.process_message: {e}")
            return {
                "response": f"❌ Ha ocurrido un error procesando tu mensaje. Por favor, intenta de nuevo.\n\nDetalle: {str(e)}",
                "functions_executed": functions_executed,
                "error": str(e)
            }
    
    async def get_proactive_alerts(self) -> List[dict]:
        """Obtiene alertas proactivas del sistema"""
        try:
            result = await fn_detectar_alertas_sla()
            return result.get("alertas", [])
        except Exception as e:
            logger.error(f"Error obteniendo alertas: {e}")
            return []
    
    async def get_daily_summary(self) -> dict:
        """Obtiene el resumen del sistema"""
        try:
            return await fn_obtener_resumen_sistema()
        except Exception as e:
            logger.error(f"Error obteniendo resumen: {e}")
            return {"error": str(e)}

# Instancia global del agente
revix_agent = RevixAgent()

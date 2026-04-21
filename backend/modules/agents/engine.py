"""
Revix · Motor de agentes IA.

Implementa el bucle de tool-calling con Claude (vía litellm + Emergent LLM Key):
  1. Construye mensajes (system + historial + user).
  2. Manda al LLM con la lista de tools permitidas (formato OpenAI function-calling).
  3. Si el LLM devuelve tool_calls → ejecuta cada tool a través del MCP runtime
     (`execute_tool_internal`, que aplica scopes + audit_log).
  4. Añade los resultados como mensajes `role: tool` y vuelve a llamar.
  5. Termina cuando el LLM devuelve un mensaje sin tool_calls (respuesta final).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import litellm
from emergentintegrations.llm.utils import get_integration_proxy_url

# Permitir importar el paquete revix_mcp (ubicado en /app/revix_mcp/)
_APP_ROOT = Path(__file__).resolve().parents[3]  # /app
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

# NOTA: importamos solo runtime/auth/tools (NO server.py), para evitar cargar
# el SDK `mcp` oficial (que degradaría starlette).
from revix_mcp.auth import AgentIdentity
from revix_mcp.runtime import ToolExecutionError, execute_tool_internal
from revix_mcp.tools import _registry as _mcp_registry
from revix_mcp.tools import clients, inventory, metrics, orders, tracking, meta  # noqa: F401 side-effect

from .agent_defs import AgentDef

logger = logging.getLogger('revix.agents.engine')


# ──────────────────────────────────────────────────────────────────────────────
# Adaptador MCP tool → OpenAI function schema (que Claude entiende vía litellm)
# ──────────────────────────────────────────────────────────────────────────────

def _mcp_tool_to_openai_schema(tool_name: str) -> dict | None:
    spec = _mcp_registry.get_tool(tool_name)
    if not spec:
        return None
    return {
        'type': 'function',
        'function': {
            'name': spec.name,
            'description': spec.description,
            'parameters': spec.input_schema,
        },
    }


def build_tool_schemas(agent: AgentDef) -> list[dict]:
    schemas = []
    for name in agent.tools:
        sch = _mcp_tool_to_openai_schema(name)
        if sch:
            schemas.append(sch)
        else:
            logger.warning(f'Tool "{name}" declarada en agente {agent.id} no está en el registry MCP')
    return schemas


# ──────────────────────────────────────────────────────────────────────────────
# Agent turn — un intercambio (user → agent) con posibles tool calls
# ──────────────────────────────────────────────────────────────────────────────

MAX_TOOL_ITERATIONS = 8


def _identity_for(agent: AgentDef) -> AgentIdentity:
    """Identidad interna del agente (sin API key física)."""
    return AgentIdentity(
        key_id=f'internal:{agent.id}',
        agent_id=agent.id,
        agent_name=agent.nombre,
        scopes=list(agent.scopes),
        rate_limit_per_min=0,  # sin rate limit para agentes internos
        key_prefix='internal',
    )


def _llm_params(model: str, messages: list, tools: list[dict] | None) -> dict:
    """Construye los parámetros de litellm.completion() usando el proxy Emergent."""
    api_key = os.environ.get('EMERGENT_LLM_KEY', '').strip()
    if not api_key:
        raise RuntimeError('EMERGENT_LLM_KEY no configurada en .env')
    proxy_url = get_integration_proxy_url()
    params = {
        'model': model,
        'messages': messages,
        'api_key': api_key,
        'api_base': proxy_url + '/llm',
        'custom_llm_provider': 'openai',  # fuerza al proxy a hablar formato OpenAI
        'temperature': 0.2,
        'max_tokens': 2048,
    }
    if tools:
        params['tools'] = tools
        params['tool_choice'] = 'auto'
    return params


async def run_agent_turn(
    db,
    agent: AgentDef,
    history: list[dict],
    user_message: str,
) -> dict:
    """Ejecuta un turno completo del agente.

    Args:
        db: Motor database.
        agent: definición del agente.
        history: lista de mensajes previos en formato OpenAI (excluye el system).
        user_message: nuevo texto del usuario.

    Returns:
        dict con:
          · reply (str): texto final al usuario.
          · tool_calls (list): trazabilidad de tools ejecutadas.
          · messages (list): historial actualizado (incluye el turno nuevo).
          · usage (dict | None): tokens si los devuelve litellm.
          · duration_ms (int)
    """
    started = time.perf_counter()
    identity = _identity_for(agent)
    tools_schema = build_tool_schemas(agent)

    messages: list[dict] = [{'role': 'system', 'content': agent.system_prompt}]
    messages.extend(history)
    messages.append({'role': 'user', 'content': user_message})

    tool_trace: list[dict] = []
    usage_final = None

    for iteration in range(MAX_TOOL_ITERATIONS):
        params = _llm_params(agent.model, messages, tools_schema)
        try:
            response = await asyncio.to_thread(litellm.completion, **params)
        except Exception as e:  # noqa: BLE001
            logger.exception('LLM call failed')
            raise RuntimeError(f'Fallo llamando al LLM: {e}') from e

        choice = response.choices[0]
        msg = choice.message
        finish_reason = getattr(choice, 'finish_reason', None)

        # litellm puede dar message como objeto o dict
        assistant_content = getattr(msg, 'content', None) or ''
        tool_calls = getattr(msg, 'tool_calls', None) or []

        try:
            usage_final = response.usage.model_dump() if hasattr(response, 'usage') and response.usage else None
        except Exception:  # noqa: BLE001
            usage_final = None

        if tool_calls:
            # Añadir mensaje del assistant con las tool_calls
            messages.append({
                'role': 'assistant',
                'content': assistant_content,
                'tool_calls': [
                    {
                        'id': tc.id,
                        'type': 'function',
                        'function': {
                            'name': tc.function.name,
                            'arguments': tc.function.arguments,
                        },
                    } for tc in tool_calls
                ],
            })

            # Ejecutar cada tool
            for tc in tool_calls:
                tname = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or '{}')
                except json.JSONDecodeError:
                    args = {}

                t_started = time.perf_counter()
                result: Any
                error: str | None = None
                try:
                    result = await execute_tool_internal(
                        db, identity=identity, tool_name=tname, params=args,
                    )
                except ToolExecutionError as e:
                    result = {'error': str(e)}
                    error = str(e)
                except Exception as e:  # noqa: BLE001
                    logger.exception(f'Tool {tname} crashed')
                    result = {'error': f'internal: {e}'}
                    error = str(e)
                t_ms = int((time.perf_counter() - t_started) * 1000)

                tool_trace.append({
                    'tool': tname, 'args': args, 'error': error,
                    'duration_ms': t_ms,
                })

                messages.append({
                    'role': 'tool',
                    'tool_call_id': tc.id,
                    'name': tname,
                    'content': json.dumps(result, default=str, ensure_ascii=False),
                })
            # Siguiente iteración: el LLM ve los resultados
            continue

        # Sin tool calls → respuesta final
        messages.append({'role': 'assistant', 'content': assistant_content})
        return {
            'reply': assistant_content,
            'tool_calls': tool_trace,
            'messages': messages[1:],  # sin el system
            'usage': usage_final,
            'duration_ms': int((time.perf_counter() - started) * 1000),
            'iterations': iteration + 1,
            'finish_reason': finish_reason,
        }

    # Si superamos el max de iteraciones
    return {
        'reply': '[Límite de iteraciones alcanzado. Reformula la pregunta.]',
        'tool_calls': tool_trace,
        'messages': messages[1:],
        'usage': usage_final,
        'duration_ms': int((time.perf_counter() - started) * 1000),
        'iterations': MAX_TOOL_ITERATIONS,
        'finish_reason': 'max_iterations',
    }

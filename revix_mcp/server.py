"""
Revix MCP Server — entrypoint.

Arranca un servidor MCP (stdio por defecto) que expone las tools registradas.

Uso:
  # Desarrollo local (stdio):
  python -m revix_mcp.server
  # con variable de entorno:
  MCP_TRANSPORT=stdio python -m revix_mcp.server

Auth:
  El protocolo MCP stdio no tiene noción nativa de "API key en request header".
  Trabajamos con una API key por proceso: la leemos de la variable de entorno
  MCP_API_KEY en el arranque. Para múltiples agentes ⇒ varios procesos.

  En el futuro (HTTP/SSE) la key vendrá en header `X-API-Key`.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

# Importar para registrar tools (side effect)
from . import tools  # noqa: F401
from .tools import (  # noqa: F401 — registra tools en _REGISTRY
    meta, orders, clients, inventory, metrics, tracking, supervisor_cola,
)
from .config import (
    DB_NAME, LOG_LEVEL, MCP_TRANSPORT, MONGO_URL, info_banner,
)
from .tools._registry import list_tools as list_tool_specs
from .runtime import ToolExecutionError, execute_tool


logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s %(levelname)s %(name)s · %(message)s',
    stream=sys.stderr,
)
logger = logging.getLogger('revix-mcp')


def _get_api_key() -> str:
    key = os.environ.get('MCP_API_KEY', '').strip()
    if not key:
        logger.error('❌ MCP_API_KEY no definida. Cada proceso MCP necesita su propia key.')
        sys.exit(2)
    return key


async def _run_stdio() -> None:
    """Arranque con transporte stdio usando SDK oficial mcp."""
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    api_key = _get_api_key()
    client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=10000)
    db = client[DB_NAME]

    # Validación temprana: si la key no es válida, abortamos antes de exponer nada
    from .auth import verify_api_key
    try:
        identity = await verify_api_key(db, api_key)
    except Exception as e:  # noqa: BLE001
        logger.error(f'❌ MCP_API_KEY inválida: {e}')
        sys.exit(3)

    logger.info(info_banner())
    logger.info(
        f'🔓 Agente "{identity.agent_id}" ({identity.agent_name}) · '
        f'{len(identity.scopes)} scopes'
    )

    server: Server = Server('revix-mcp')

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        tools_visible = [
            t for t in list_tool_specs()
            if identity.has_scope(t.required_scope)
        ]
        return [
            Tool(
                name=t.name,
                description=t.description,
                inputSchema=t.input_schema,
            )
            for t in tools_visible
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict | None) -> list[TextContent]:
        try:
            result = await execute_tool(
                db, api_key=api_key, tool_name=name, params=arguments or {},
            )
            payload = _json_dumps(result)
        except ToolExecutionError as e:
            payload = _json_dumps({'error': str(e)})
        except Exception as e:  # noqa: BLE001
            logger.exception('Tool handler crashed')
            payload = _json_dumps({'error': f'internal: {e}'})
        return [TextContent(type='text', text=payload)]

    # Arrancar stdio loop
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def _json_dumps(obj: Any) -> str:
    import json
    try:
        return json.dumps(obj, default=str, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        return json.dumps({'error': 'no-json-serializable'})


def main() -> None:
    if MCP_TRANSPORT == 'stdio':
        asyncio.run(_run_stdio())
    else:
        logger.error(f'❌ Transporte "{MCP_TRANSPORT}" todavía no implementado. Usa stdio.')
        sys.exit(4)


if __name__ == '__main__':
    main()

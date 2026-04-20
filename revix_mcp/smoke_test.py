"""
Smoke test end-to-end del servidor MCP vía stdio.

Usa el SDK oficial `mcp` como cliente para:
  1. Lanzar el servidor como subproceso (arranque stdio).
  2. Pedir list_tools — debe incluir "ping".
  3. Invocar ping — debe responder {"pong": true, ...}.

Requiere que exista una API key válida y que se pase por env MCP_API_KEY.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main(api_key: str) -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=['-m', 'revix_mcp.server'],
        env={
            **os.environ,
            'MCP_API_KEY': api_key,
            'MCP_ENV': 'preview',
            'MCP_TRANSPORT': 'stdio',
        },
        cwd='/app',
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. list_tools
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f'📋 tools disponibles: {tool_names}')
            assert 'ping' in tool_names, 'ping no aparece en list_tools'

            # 2. call ping
            result = await session.call_tool('ping', {})
            content = result.content[0].text
            data = json.loads(content)
            print(f'🏓 ping → {data}')
            assert data.get('pong') is True
            assert data.get('env') == 'preview'
            assert data.get('agent_id') == 'kpi_analyst'

            print('✅ Smoke test OK')


if __name__ == '__main__':
    key = os.environ.get('MCP_API_KEY') or (sys.argv[1] if len(sys.argv) > 1 else '')
    if not key:
        print('Uso: python smoke_test.py <API_KEY>', file=sys.stderr)
        sys.exit(2)
    asyncio.run(main(key))

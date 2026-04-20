"""
Tool meta: `ping`.

Único propósito: validar end-to-end que el MCP server está vivo y que los
mecanismos de auth + audit + scopes funcionan. Útil para smoke tests desde
Rowboat antes de probar tools reales.
"""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..auth import AgentIdentity
from ..config import MCP_ENV, info_banner
from ._registry import ToolSpec, register


async def _ping_handler(
    db: AsyncIOMotorDatabase,
    identity: AgentIdentity,
    params: dict,
) -> dict:
    return {
        'pong': True,
        'env': MCP_ENV,
        'banner': info_banner(),
        'agent_id': identity.agent_id,
        'scopes_count': len(identity.scopes),
    }


register(ToolSpec(
    name='ping',
    description='Comprueba que el MCP server responde. Útil para validar conectividad y scopes.',
    required_scope='meta:ping',
    input_schema={
        'type': 'object',
        'properties': {},
        'additionalProperties': False,
    },
    handler=_ping_handler,
    writes=False,
    sandbox_skip=False,
))

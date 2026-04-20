"""
Revix MCP · Registry de tools.

Cada tool es una función async que recibe (db, identity, params) y devuelve un dict.
Al registrarla se indican:
  - name (identificador MCP, ej: "buscar_orden")
  - description (para el LLM cliente)
  - required_scope (scope mínimo para ejecutarla)
  - input_schema (JSON Schema de params)
  - writes (bool, afecta a idempotencia y sandbox)
  - sandbox_skip (bool, si en preview debe devolver mock en vez de ejecutar)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..auth import AgentIdentity

ToolHandler = Callable[[AsyncIOMotorDatabase, AgentIdentity, dict], Awaitable[Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    required_scope: str
    input_schema: dict
    handler: ToolHandler
    writes: bool = False
    sandbox_skip: bool = False


_REGISTRY: dict[str, ToolSpec] = {}


def register(spec: ToolSpec) -> None:
    if spec.name in _REGISTRY:
        raise ValueError(f'Tool duplicada: {spec.name}')
    _REGISTRY[spec.name] = spec


def get_tool(name: str) -> Optional[ToolSpec]:
    return _REGISTRY.get(name)


def list_tools() -> list[ToolSpec]:
    return list(_REGISTRY.values())


def all_tools_for_identity(identity: AgentIdentity) -> list[ToolSpec]:
    """Lista tools que el agente PUEDE ejecutar según sus scopes."""
    return [t for t in _REGISTRY.values() if identity.has_scope(t.required_scope)]


def clear_registry_for_tests() -> None:
    """Solo se usa en tests unitarios."""
    _REGISTRY.clear()

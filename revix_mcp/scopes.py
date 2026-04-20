"""
Revix MCP · Scopes de permisos.

Cada scope representa una capacidad concreta. Un agente tiene una lista de scopes.
Las tools declaran qué scopes requieren; el runtime valida antes de ejecutar.

Convenciones:
  - formato:        <dominio>:<accion>
  - `*:read`         lectura transversal (solo KPI Analyst / Auditor)
  - `domain:read`    lectura en un dominio concreto
  - `domain:write`   mutación en un dominio concreto
  - Otros verbos más específicos: suggest, bill, dunning, ops, track_by_token…
"""
from __future__ import annotations
from typing import FrozenSet

# Catálogo completo — si un agente pide un scope fuera de esta lista, se rechaza.
SCOPES_CATALOG: FrozenSet[str] = frozenset({
    # Meta
    'meta:ping',
    # Órdenes
    'orders:read', 'orders:write', 'orders:suggest',
    # Clientes
    'customers:read', 'customers:write',
    # Inventario
    'inventory:read', 'inventory:write',
    # Finanzas
    'finance:read', 'finance:bill', 'finance:dunning', 'finance:fiscal_calc',
    # Aseguradoras
    'insurance:ops',
    # Calidad ISO
    'iso:quality',
    # Auditoría
    'audit:read', 'audit:report',
    # Web pública
    'catalog:read', 'quotes:write_public', 'public:track_by_token',
    # Comunicaciones
    'comm:write', 'comm:escalate',
    # Observabilidad / KPIs
    'metrics:read', 'dashboard:read',
    # Operativa interna
    'incidents:write', 'notifications:write',
    # Superpoderes: lectura universal (solo KPI Analyst / Auditor)
    '*:read',
})


def is_known_scope(scope: str) -> bool:
    return scope in SCOPES_CATALOG


def has_scope(agent_scopes: list[str] | tuple[str, ...], required: str) -> bool:
    """True si `agent_scopes` satisface `required`.

    Reglas:
      - Coincidencia exacta.
      - `*:read` satisface cualquier `*:read` (ej. orders:read, metrics:read).
    """
    if required in agent_scopes:
        return True
    if required.endswith(':read') and '*:read' in agent_scopes:
        return True
    return False


def validate_scopes(scopes: list[str]) -> list[str]:
    """Valida que todos los scopes de una API key existan en el catálogo.

    Devuelve la lista limpia (sin duplicados, ordenada). Aborta con ValueError si
    alguno es desconocido.
    """
    unknown = [s for s in scopes if not is_known_scope(s)]
    if unknown:
        raise ValueError(f'Scopes desconocidos: {unknown}')
    return sorted(set(scopes))


# ── Perfiles preconfigurados por agente ───────────────────────────────────────
# Útil al crear API keys desde CLI: `--profile auditor`.
AGENT_PROFILES: dict[str, list[str]] = {
    'kpi_analyst': ['*:read', 'meta:ping'],
    'supervisor_cola': ['orders:read', 'incidents:write', 'notifications:write', 'meta:ping'],
    'triador': ['orders:read', 'orders:suggest', 'inventory:read', 'customers:read', 'meta:ping'],
    'finance_officer': ['finance:read', 'finance:bill', 'finance:dunning', 'finance:fiscal_calc', 'orders:read', 'customers:read', 'meta:ping'],
    'gestor_siniestros': ['orders:read', 'orders:write', 'insurance:ops', 'customers:write', 'notifications:write', 'meta:ping'],
    'call_center': ['customers:read', 'orders:read', 'comm:write', 'comm:escalate', 'meta:ping'],
    'presupuestador_publico': ['catalog:read', 'quotes:write_public', 'meta:ping'],
    'seguimiento_publico': ['public:track_by_token', 'meta:ping'],
    'iso_officer': ['iso:quality', 'orders:read', 'notifications:write', 'meta:ping'],
    'auditor': ['audit:read', 'audit:report', '*:read', 'meta:ping'],
}

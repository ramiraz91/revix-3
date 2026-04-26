"""
Seed de Oleada 1 — autonomía agentes (kpi_analyst, auditor, iso_officer).

Idempotente: si la tarea ya existe (mismo agent_id + tool + cron) la actualiza.

Uso:
    python -m backend.scripts.seed_oleada_1
o:
    cd /app && python backend/scripts/seed_oleada_1.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Path setup
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(_ROOT / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient

from revix_mcp.scheduler import (
    crear_tarea,
    compute_next_run,
    TASKS_COLLECTION,
)


# Definición Oleada 1 — solo lectura, riesgo bajo
OLEADA_1: list[dict] = [
    # ── kpi_analyst ────────────────────────────────────────────────────────
    {
        "agent_id": "kpi_analyst",
        "tool": "obtener_dashboard",
        "cron_expression": "0 8 * * *",
        "params": {},
        "descripcion": "[Oleada 1] KPIs diarios 08:00 UTC",
    },
    # ── auditor ────────────────────────────────────────────────────────────
    {
        "agent_id": "auditor",
        "tool": "ejecutar_audit_operacional",
        "cron_expression": "0 22 * * *",
        "params": {"desde": "auto_7d"},
        "descripcion": "[Oleada 1] Audit operacional diario 22:00 UTC",
    },
    {
        "agent_id": "auditor",
        "tool": "generar_audit_report",
        "cron_expression": "0 9 * * 1",
        "params": {"desde": "auto_7d", "hasta": "auto_now"},
        "descripcion": "[Oleada 1] Audit report semanal lunes 09:00 UTC",
    },
    # ── iso_officer ────────────────────────────────────────────────────────
    {
        "agent_id": "iso_officer",
        "tool": "generar_revision_direccion",
        "cron_expression": "0 6 1 * *",
        "params": {},
        "descripcion": "[Oleada 1] ISO revisión dirección mensual día 1 06:00 UTC",
    },
]


async def upsert_tarea(db, *, agent_id: str, tool: str, cron_expression: str,
                       params: dict, descripcion: str) -> str:
    """Crea o actualiza si ya existe (match por agent_id+tool+cron)."""
    existing = await db[TASKS_COLLECTION].find_one({
        "agent_id": agent_id, "tool": tool, "cron_expression": cron_expression,
    }, {"_id": 0})
    if existing:
        # Actualizar params/desc/activo si cambia, mantener id
        await db[TASKS_COLLECTION].update_one(
            {"id": existing["id"]},
            {"$set": {
                "params": params,
                "descripcion": descripcion,
                "activo": True,
                "proxima_ejecucion": compute_next_run(cron_expression).isoformat(),
            }},
        )
        return f"  ↻ updated  {existing['id'][:8]}  {agent_id}.{tool}  {cron_expression}"
    doc = await crear_tarea(
        db,
        agent_id=agent_id,
        tool=tool,
        cron_expression=cron_expression,
        params=params,
        descripcion=descripcion,
        created_by="seed_oleada_1",
    )
    return f"  + created  {doc['id'][:8]}  {agent_id}.{tool}  {cron_expression}"


async def main() -> None:
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "revix_preview")
    if not mongo_url:
        raise SystemExit("MONGO_URL no configurado")

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    print(f"DB: {db_name}")
    print(f"Notificaciones de fallo (3 fallos consecutivos): "
          f"{os.environ.get('MCP_FAILURE_NOTIFY_EMAIL', 'master@revix.es')}")
    print()
    print(f"Sembrando {len(OLEADA_1)} tareas Oleada 1:")
    for cfg in OLEADA_1:
        msg = await upsert_tarea(db, **cfg)
        print(msg)
    print()

    # Resumen
    total = await db[TASKS_COLLECTION].count_documents({"activo": True})
    print(f"Total tareas activas en BD: {total}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())

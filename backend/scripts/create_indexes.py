"""
Script de creacion de indices MongoDB para produccion.
Idempotente — verifica existencia antes de crear.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "production")


async def safe_index(col, keys, **kwargs):
    """Crea indice si no existe. Ignora errores de duplicado."""
    name = kwargs.get("name", str(keys))
    try:
        await col.create_index(keys, **kwargs)
        return True
    except Exception as e:
        if "already exists" in str(e) or "IndexOptionsConflict" in str(e):
            return False  # Ya existe con otro nombre
        print(f"  WARN {name}: {e}")
        return False


async def create_indexes():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    created = 0

    print("Creando indices en MongoDB...")

    # ── ORDENES ──
    o = db.ordenes
    if await safe_index(o, "id", unique=True, name="idx_ordenes_id"): created += 1
    if await safe_index(o, "numero_autorizacion", name="idx_ordenes_auth", sparse=True): created += 1
    if await safe_index(o, "origen", name="idx_ordenes_origen", sparse=True): created += 1
    if await safe_index(o, "created_at", name="idx_ordenes_created"): created += 1
    if await safe_index(o, "tecnico_asignado", name="idx_ordenes_tecnico", sparse=True): created += 1
    if await safe_index(o, [("estado", 1), ("numero_autorizacion", 1)], name="idx_ordenes_estado_auth", sparse=True): created += 1
    if await safe_index(o, [("estado", 1), ("created_at", -1)], name="idx_ordenes_estado_fecha"): created += 1
    print(f"  ordenes: +{created}")

    # ── CLIENTES ──
    c = db.clientes
    n = 0
    if await safe_index(c, "id", unique=True, name="idx_clientes_id"): n += 1
    if await safe_index(c, "email", name="idx_clientes_email", sparse=True): n += 1
    if await safe_index(c, "nombre", name="idx_clientes_nombre"): n += 1
    created += n
    print(f"  clientes: +{n}")

    # ── USERS ──
    u = db.users
    n = 0
    if await safe_index(u, "id", unique=True, name="idx_users_id"): n += 1
    if await safe_index(u, "email", unique=True, name="idx_users_email"): n += 1
    if await safe_index(u, "role", name="idx_users_role"): n += 1
    created += n
    print(f"  users: +{n}")

    # ── REPUESTOS ──
    r = db.repuestos
    n = 0
    if await safe_index(r, "id", unique=True, name="idx_repuestos_id"): n += 1
    if await safe_index(r, "sku", name="idx_repuestos_sku", sparse=True): n += 1
    if await safe_index(r, "categoria", name="idx_repuestos_cat"): n += 1
    created += n
    print(f"  repuestos: +{n}")

    # ── LIQUIDACIONES ──
    l = db.liquidaciones
    n = 0
    if await safe_index(l, "codigo_siniestro", name="idx_liq_codigo", sparse=True): n += 1
    if await safe_index(l, "estado", name="idx_liq_estado"): n += 1
    created += n
    print(f"  liquidaciones: +{n}")

    # ── PRINT JOBS ──
    pj = db.print_jobs
    n = 0
    if await safe_index(pj, "job_id", unique=True, name="idx_pj_jobid"): n += 1
    if await safe_index(pj, "status", name="idx_pj_status"): n += 1
    if await safe_index(pj, "requested_at", name="idx_pj_date"): n += 1
    created += n
    print(f"  print_jobs: +{n}")

    # ── PRINT AGENTS ──
    if await safe_index(db.print_agents, "agent_id", unique=True, name="idx_pa_agentid"): created += 1
    print(f"  print_agents: +1")

    # ── NOTIFICACIONES ──
    nt = db.notificaciones
    n = 0
    if await safe_index(nt, "usuario_id", name="idx_notif_usuario"): n += 1
    if await safe_index(nt, "created_at", name="idx_notif_fecha"): n += 1
    if await safe_index(nt, "leida", name="idx_notif_leida"): n += 1
    created += n
    print(f"  notificaciones: +{n}")

    # ── CONFIGURACION ──
    if await safe_index(db.configuracion, "tipo", unique=True, name="idx_config_tipo"): created += 1
    print(f"  configuracion: +1")

    # ── AUDIT LOG ──
    al = db.audit_log
    n = 0
    if await safe_index(al, "entity_id", name="idx_audit_entity"): n += 1
    if await safe_index(al, "timestamp", name="idx_audit_fecha"): n += 1
    if await safe_index(al, [("entity_type", 1), ("entity_id", 1)], name="idx_audit_type_entity"): n += 1
    created += n
    print(f"  audit_log: +{n}")

    print(f"\nTotal nuevos indices creados: {created}")
    client.close()


if __name__ == "__main__":
    asyncio.run(create_indexes())

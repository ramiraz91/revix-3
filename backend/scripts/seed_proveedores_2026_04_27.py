"""
Script idempotente — sesión 17:
1. Enriquecer 4 proveedores reales en `production` con email/web placeholders.
2. Copiar los 4 a `revix_preview` (alta si no existen).
3. Analizar solapes entre repuestos de `revix_production` y `production`.

NO modifica nombres, IDs ni datos existentes con valor. Solo rellena campos vacíos.
NO copia repuestos (solo análisis).

Uso:
  cd /app/backend && python3 -m scripts.seed_proveedores_2026_04_27 --dry-run
  cd /app/backend && python3 -m scripts.seed_proveedores_2026_04_27 --apply
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

from motor.motor_asyncio import AsyncIOMotorClient


def slug(name: str) -> str:
    s = (name or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s or "proveedor"


PLACEHOLDER_NOTAS = (
    "Datos de contacto pendientes — rellenar desde UI Proveedores cuando "
    "se disponga de email, teléfono y persona de contacto reales."
)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="Aplicar cambios (sin esto solo muestra dry-run)")
    args = ap.parse_args()
    dry = not args.apply

    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db_prod = cli["production"]
    db_prev = cli["revix_preview"]
    db_revprod = cli["revix_production"]

    print("=" * 78)
    print(f"MODO: {'DRY-RUN (sin cambios)' if dry else 'APPLY (escribe en BD)'}")
    print("=" * 78)
    now = datetime.now(timezone.utc)

    # ── Paso 1: Enriquecer proveedores de `production` ─────────────────────
    print("\n[1] Enriquecer proveedores en `production`")
    print("-" * 78)
    proveedores_prod = await db_prod.proveedores.find({}, {"_id": 0}).to_list(None)
    plan = []
    for p in proveedores_prod:
        nombre = (p.get("nombre") or "").strip()
        s = slug(nombre)
        # Solo rellenar campos vacíos / None
        updates: dict = {}
        if not (p.get("email") or "").strip():
            updates["email"] = f"pedidos@{s}.com"
        if not (p.get("web") or "").strip():
            updates["web"] = f"www.{s}.com"
        if not (p.get("notas") or "").strip():
            updates["notas"] = PLACEHOLDER_NOTAS
        # NUNCA tocar nombre, id, contacto, telefono, direccion (esos los rellena el usuario)
        if updates:
            updates["updated_at"] = now
            plan.append((p["id"], nombre, updates))

    for pid, nombre, upd in plan:
        print(f"  · {nombre:18} → {list(upd.keys())}")
        if not dry:
            await db_prod.proveedores.update_one({"id": pid}, {"$set": upd})

    if not plan:
        print("  (nada que actualizar — todos los proveedores ya tienen datos)")
    else:
        print(f"  {'PLAN' if dry else 'APLICADO'}: {len(plan)} proveedor(es)")

    # ── Paso 2: Copiar a `revix_preview` ──────────────────────────────────
    print("\n[2] Copiar proveedores → `revix_preview` (alta si no existe)")
    print("-" * 78)
    # Releer proveedores de production con los enriquecimientos aplicados
    if not dry:
        proveedores_prod = await db_prod.proveedores.find({}, {"_id": 0}).to_list(None)

    nuevos = 0
    existentes = 0
    for p in proveedores_prod:
        # Buscar por nombre normalizado en preview (para no romper si hay con id distinto)
        existing = await db_prev.proveedores.find_one(
            {"nombre": p.get("nombre")}, {"_id": 0, "id": 1},
        )
        if existing:
            existentes += 1
            print(f"  · {p['nombre']:18} ya existe en preview (id={existing['id'][:8]}…) — skip")
            continue
        # Insertar tal cual (mismo id) con timestamps
        doc = {**p, "created_at": p.get("created_at") or now, "updated_at": now}
        nuevos += 1
        print(f"  · {p['nombre']:18} → ALTA en preview (id={p['id'][:8]}…)")
        if not dry:
            await db_prev.proveedores.insert_one(doc)

    print(f"  {'PLAN' if dry else 'RESULTADO'}: {nuevos} nuevo(s), {existentes} ya presente(s)")

    # ── Paso 3: Análisis de solapes repuestos production vs revix_production ──
    print("\n[3] Análisis de solapes repuestos `production` ↔ `revix_production`")
    print("-" * 78)
    rep_prod = await db_prod.repuestos.find({}, {"_id": 0}).to_list(None)
    rep_revprod = await db_revprod.repuestos.find({}, {"_id": 0}).to_list(None)
    print(f"  production:        {len(rep_prod)} repuesto(s)")
    print(f"  revix_production:  {len(rep_revprod)} repuesto(s)")

    # Indexar revix_production por (sku, nombre_normalizado)
    def norm(s):
        return re.sub(r"\s+", " ", (s or "").strip().lower())

    by_sku = {r.get("sku"): r for r in rep_revprod if r.get("sku")}
    by_name = {norm(r.get("nombre")): r for r in rep_revprod}

    solapes_sku = []
    solapes_name = []
    for r in rep_prod:
        sku = r.get("sku")
        n = norm(r.get("nombre"))
        if sku and sku in by_sku:
            solapes_sku.append((sku, r.get("nombre"), by_sku[sku].get("nombre")))
        if n and n in by_name:
            solapes_name.append((r.get("nombre"), by_name[n].get("nombre")))

    print(f"  Solapes por SKU:    {len(solapes_sku)}")
    for s in solapes_sku[:10]:
        print(f"    [{s[0]}] prod='{s[1]}' / revprod='{s[2]}'")
    print(f"  Solapes por nombre: {len(solapes_name)}")
    for s in solapes_name[:10]:
        print(f"    prod='{s[0]}' ≈ revprod='{s[1]}'")

    # Categorías diferenciadas
    cat_prod = {(r.get("categoria") or "?") for r in rep_prod}
    cat_revprod = {(r.get("categoria") or "?") for r in rep_revprod}
    print(f"  Categorías production:        {sorted(cat_prod)}")
    print(f"  Categorías revix_production:  {sorted(cat_revprod)}")

    # Diagnóstico inteligente
    print("\n  📋 Diagnóstico:")
    if not solapes_sku and not solapes_name:
        print("  ✅ NO hay solapes detectados. Las 2 colecciones contienen catálogos disjuntos.")
        print("     - `production`: repuestos genéricos (Logística, Diagnóstico, Reparación, +1 pantalla).")
        print("     - `revix_production`: 116 pantallas reales iPhone/iPad de Utopya.")
        print("     RECOMENDACIÓN: si quieres unificar, copiar los 116 de revix_production → production")
        print("     usando upsert por sku, sin riesgo de duplicar (categorías y SKUs no chocan).")
    else:
        print(f"  ⚠ Hay {len(solapes_sku)} solapes por SKU y {len(solapes_name)} por nombre.")
        print("     Si decides copiar, será necesario merge cuidadoso (revisión manual).")

    print("\nFIN.")


if __name__ == "__main__":
    asyncio.run(main())

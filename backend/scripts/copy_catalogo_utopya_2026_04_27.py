"""
Copia idempotente del catálogo Utopya (116 repuestos) de `revix_production`
hacia `production`. Stock y stock_minimo se mantienen en 0 (catálogo de referencia).

Upsert por SKU. Si una entrada con el mismo SKU ya existe en production, se
respeta y NO se sobrescribe (regla "no romper datos reales").
"""
import asyncio, os, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient


async def main(apply: bool):
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    src = cli["revix_production"].repuestos
    dst = cli["production"].repuestos

    src_docs = await src.find({}, {"_id": 0}).to_list(None)
    print(f"Origen revix_production: {len(src_docs)} repuesto(s)")

    creados = 0
    omitidos = 0
    actualizados_metadata = 0
    now = datetime.now(timezone.utc)

    for d in src_docs:
        sku = (d.get("sku") or "").strip()
        if not sku:
            print("  · SIN SKU → skip:", d.get("nombre"))
            omitidos += 1
            continue
        existing = await dst.find_one({"sku": sku}, {"_id": 0, "id": 1})
        if existing:
            print(f"  · Ya existe SKU={sku} → skip ({existing['id'][:8]}…)")
            omitidos += 1
            continue
        # Marcar como catálogo de referencia
        doc = {
            **d,
            "stock": 0,
            "stock_minimo": 0,
            "fuente_catalogo": "utopya_scrape",
            "es_catalogo_referencia": True,
            "created_at": d.get("created_at") or now,
            "updated_at": now,
        }
        if apply:
            await dst.insert_one(doc)
        creados += 1
    
    print()
    print(f"{'PLAN' if not apply else 'RESULTADO'}: creados={creados}, omitidos(ya existen)={omitidos}, sin_sku={omitidos - (omitidos - 0)}")
    print(f"Total destino tras op: {creados + await dst.count_documents({})}" if apply else "")


if __name__ == "__main__":
    asyncio.run(main(apply="--apply" in sys.argv))

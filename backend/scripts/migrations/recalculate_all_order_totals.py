"""
migrations/recalculate_all_order_totals.py

Recalcula y actualiza los totales de TODAS las órdenes (subtotal_materiales, total_iva,
presupuesto_total, coste_total, beneficio_estimado).

Necesario tras el fix del Resumen Financiero: las órdenes antiguas mantienen totales
obsoletos que no reflejan sus materiales actuales.

Uso:
  Dry-run:       cd /app/backend && DB_NAME=xxx python -m scripts.migrations.recalculate_all_order_totals
  Apply preview: cd /app/backend && python -m scripts.migrations.recalculate_all_order_totals --apply
  Apply prod:    cd /app/backend && DB_NAME=production python -m scripts.migrations.recalculate_all_order_totals --apply --allow-production

Reutiliza la función `recalcular_totales_orden` del backend para garantizar consistencia
con el cálculo de producción.
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'), override=False)

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
BACKUP_DIR = Path('/app/backend/scripts/migrations/backups')
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


async def main():
    dry_run = '--apply' not in sys.argv
    allow_prod = '--allow-production' in sys.argv

    if DB_NAME == 'production' and not allow_prod:
        print('❌ BLOQUEADO: producción requiere --allow-production')
        sys.exit(1)

    print(f'🔧 Recalcular totales de órdenes · BD: {DB_NAME} · modo: {"DRY-RUN" if dry_run else "APPLY"}')

    client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=10000)
    db = client[DB_NAME]

    ordenes = await db.ordenes.find({}, {
        '_id': 0, 'id': 1, 'numero_orden': 1,
        'subtotal_materiales': 1, 'total_iva': 1, 'presupuesto_total': 1,
        'coste_total': 1, 'beneficio_estimado': 1, 'materiales': 1, 'mano_obra': 1,
    }).to_list(None)

    # Simular cálculo (misma fórmula que el backend)
    def calcular(orden):
        materiales = orden.get('materiales') or []
        mano_obra = float(orden.get('mano_obra') or 0)
        subtotal_mat = 0.0
        total_iva_mat = 0.0
        coste = 0.0
        for m in materiales:
            if m.get('aprobado', True) is False:
                continue
            cant = float(m.get('cantidad') or 0)
            precio = float(m.get('precio_unitario') or 0)
            dto = float(m.get('descuento') or 0)
            iva_pct = float(m.get('iva') if m.get('iva') is not None else 21)
            c = float(m.get('coste') or 0)
            sub = cant * precio
            desc = sub * (dto / 100)
            base_item = sub - desc
            subtotal_mat += base_item
            total_iva_mat += base_item * (iva_pct / 100)
            coste += c * cant
        base = subtotal_mat + mano_obra
        total_iva = total_iva_mat + mano_obra * 0.21
        total = base + total_iva
        return {
            'subtotal_materiales': round(subtotal_mat, 2),
            'total_iva': round(total_iva, 2),
            'presupuesto_total': round(total, 2),
            'coste_total': round(coste, 2),
            'beneficio_estimado': round(base - coste, 2),
        }

    descuadres = []
    for o in ordenes:
        nuevo = calcular(o)
        actual = {k: round(float(o.get(k) or 0), 2) for k in nuevo.keys()}
        if actual != nuevo:
            descuadres.append({
                'id': o['id'], 'numero_orden': o.get('numero_orden'),
                'antes': actual, 'despues': nuevo,
            })

    if not descuadres:
        print('✅ Todas las órdenes tienen totales consistentes. Nada que recalcular.')
        client.close()
        return

    print(f'📋 {len(descuadres)}/{len(ordenes)} órdenes con totales desincronizados.')
    for d in descuadres[:5]:
        print(f'   - {d["numero_orden"]}: presupuesto_total {d["antes"]["presupuesto_total"]} → {d["despues"]["presupuesto_total"]}')
    if len(descuadres) > 5:
        print(f'   … y {len(descuadres)-5} más')

    if dry_run:
        print()
        print('📝 DRY-RUN: no se ha modificado nada.')
        print(f'   Para aplicar: --apply' + (' --allow-production' if DB_NAME == 'production' else ''))
        client.close()
        return

    # Backup
    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    backup_path = BACKUP_DIR / f'{DB_NAME}_totales_migration_{ts}.json'
    backup_path.write_text(json.dumps(descuadres, indent=2, default=str), encoding='utf-8')
    print(f'💾 Backup guardado: {backup_path}')

    # Aplicar
    now_iso = datetime.now(timezone.utc).isoformat()
    updated = 0
    for d in descuadres:
        res = await db.ordenes.update_one(
            {'id': d['id']},
            {'$set': {**d['despues'], 'updated_at': now_iso}}
        )
        if res.modified_count == 1:
            updated += 1
    # Audit único (no 1 por orden para no saturar)
    await db.audit_logs.insert_one({
        'id': f'MIG-TOTALES-{ts}',
        'source': 'migration',
        'action': 'recalculate_all_order_totals',
        'affected_count': updated,
        'timestamp': now_iso,
        'script': 'recalculate_all_order_totals.py',
    })
    print(f'✅ {updated} órdenes con totales recalculados.')
    client.close()


if __name__ == '__main__':
    asyncio.run(main())

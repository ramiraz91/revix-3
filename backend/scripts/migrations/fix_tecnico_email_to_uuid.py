"""
migrations/fix_tecnico_email_to_uuid.py

Migra órdenes donde `tecnico_asignado` contiene un email en lugar del UUID del user.

Modo por defecto: --dry-run (solo muestra qué cambiaría, no escribe).
Para aplicar: --apply
Para producción: --apply --allow-production (requiere autorización explícita).

Características:
  - Idempotente: correr N veces = correr 1 vez.
  - Reversible: antes de modificar, guarda un backup en backup_tecnico_migration_{ts}.json
  - Audit: graba entrada en audit_logs con source="migration" por cada orden tocada.
  - Validación previa: si algún email no tiene user correspondiente, aborta sin modificar nada.
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

    print(f'🔧 Fix técnico email → UUID · BD: {DB_NAME} · modo: {"DRY-RUN" if dry_run else "APPLY"}')

    client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=10000)
    db = client[DB_NAME]

    # 1. Detectar órdenes afectadas
    target_ordenes = await db.ordenes.find(
        {'tecnico_asignado': {'$regex': '@', '$options': 'i'}},
        {'_id': 0, 'id': 1, 'numero_orden': 1, 'tecnico_asignado': 1, 'updated_at': 1}
    ).to_list(None)

    if not target_ordenes:
        print('✅ Nada que migrar. Todas las órdenes ya usan UUID.')
        client.close()
        return

    # 2. Resolver emails → UUIDs (validación previa)
    emails_needed = list({o['tecnico_asignado'] for o in target_ordenes})
    users_by_email = {}
    for email in emails_needed:
        u = await db.users.find_one({'email': email}, {'_id': 0, 'id': 1, 'email': 1})
        if u and u.get('id'):
            users_by_email[email] = u['id']

    missing = [e for e in emails_needed if e not in users_by_email]
    if missing:
        print('❌ ABORTA: hay emails sin user correspondiente, no puedo resolver a UUID:')
        for m in missing:
            print(f'   - {m}')
        client.close()
        sys.exit(1)

    # 3. Resumen
    print(f'📋 {len(target_ordenes)} órdenes con email, {len(users_by_email)} users resueltos:')
    for email, uid in users_by_email.items():
        affected = sum(1 for o in target_ordenes if o['tecnico_asignado'] == email)
        print(f'   - {email} → {uid} ({affected} órdenes)')

    if dry_run:
        print()
        print('📝 DRY-RUN: no se ha modificado nada.')
        print('   Para aplicar: --apply' + (' --allow-production' if DB_NAME == 'production' else ''))
        client.close()
        return

    # 4. Backup
    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    backup_path = BACKUP_DIR / f'{DB_NAME}_tecnico_email_migration_{ts}.json'
    backup_path.write_text(json.dumps(target_ordenes, indent=2, default=str), encoding='utf-8')
    print(f'💾 Backup guardado: {backup_path}')

    # 5. Aplicar (uno a uno con audit)
    now_iso = datetime.now(timezone.utc).isoformat()
    migrated = 0
    for orden in target_ordenes:
        new_uuid = users_by_email[orden['tecnico_asignado']]
        old_val = orden['tecnico_asignado']
        res = await db.ordenes.update_one(
            {'id': orden['id'], 'tecnico_asignado': old_val},
            {
                '$set': {
                    'tecnico_asignado': new_uuid,
                    'updated_at': now_iso,
                }
            }
        )
        if res.modified_count == 1:
            migrated += 1
            await db.audit_logs.insert_one({
                'id': f'MIG-TECNICO-{orden["id"]}-{ts}',
                'source': 'migration',
                'action': 'fix_tecnico_email_to_uuid',
                'orden_id': orden['id'],
                'numero_orden': orden.get('numero_orden'),
                'before': {'tecnico_asignado': old_val},
                'after': {'tecnico_asignado': new_uuid},
                'timestamp': now_iso,
                'script': 'fix_tecnico_email_to_uuid.py',
            })

    print(f'✅ {migrated} órdenes migradas correctamente.')
    print(f'   Rollback manual disponible en: {backup_path}')
    client.close()


if __name__ == '__main__':
    asyncio.run(main())

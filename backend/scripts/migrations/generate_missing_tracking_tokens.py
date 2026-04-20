"""
migrations/generate_missing_tracking_tokens.py

Genera `token_seguimiento` para órdenes que no lo tienen.
El token permite a los clientes consultar su reparación en /consulta.

Modo por defecto: --dry-run
Para aplicar: --apply
Para producción: --apply --allow-production

Token: 12 chars alfanuméricos mayúsculas, único verificado contra `ordenes.token_seguimiento`.
"""
import asyncio
import json
import os
import string
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'), override=False)

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
BACKUP_DIR = Path('/app/backend/scripts/migrations/backups')
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

TOKEN_ALPHABET = string.ascii_uppercase + string.digits


def gen_token() -> str:
    return ''.join(random.choices(TOKEN_ALPHABET, k=12))


async def main():
    dry_run = '--apply' not in sys.argv
    allow_prod = '--allow-production' in sys.argv

    if DB_NAME == 'production' and not allow_prod:
        print('❌ BLOQUEADO: producción requiere --allow-production')
        sys.exit(1)

    print(f'🔧 Generar tokens seguimiento · BD: {DB_NAME} · modo: {"DRY-RUN" if dry_run else "APPLY"}')

    client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=10000)
    db = client[DB_NAME]

    # 1. Cargar órdenes sin token
    target = await db.ordenes.find(
        {'$or': [
            {'token_seguimiento': {'$exists': False}},
            {'token_seguimiento': None},
            {'token_seguimiento': ''},
        ]},
        {'_id': 0, 'id': 1, 'numero_orden': 1, 'estado': 1}
    ).to_list(None)

    if not target:
        print('✅ Todas las órdenes ya tienen token_seguimiento.')
        client.close()
        return

    print(f'📋 {len(target)} órdenes sin token.')

    # 2. Cargar tokens existentes para evitar colisiones
    existing = set()
    async for o in db.ordenes.find({'token_seguimiento': {'$exists': True, '$ne': None, '$ne': ''}}, {'_id': 0, 'token_seguimiento': 1}):
        if o.get('token_seguimiento'):
            existing.add(o['token_seguimiento'])

    # 3. Pre-generar tokens únicos en memoria
    new_tokens = {}
    for orden in target:
        while True:
            t = gen_token()
            if t not in existing:
                existing.add(t)
                new_tokens[orden['id']] = t
                break

    if dry_run:
        print(f'📝 DRY-RUN: se generarían {len(new_tokens)} tokens. Muestra:')
        for i, (oid, t) in enumerate(list(new_tokens.items())[:3]):
            print(f'   - orden {oid[:8]}… → token {t}')
        print(f'   Para aplicar: --apply' + (' --allow-production' if DB_NAME == 'production' else ''))
        client.close()
        return

    # 4. Backup
    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    backup_path = BACKUP_DIR / f'{DB_NAME}_tokens_migration_{ts}.json'
    backup_payload = [{'id': t['id'], 'numero_orden': t.get('numero_orden'), 'new_token': new_tokens[t['id']]} for t in target]
    backup_path.write_text(json.dumps(backup_payload, indent=2, default=str), encoding='utf-8')
    print(f'💾 Backup guardado: {backup_path}')

    # 5. Aplicar
    now_iso = datetime.now(timezone.utc).isoformat()
    done = 0
    for orden in target:
        token = new_tokens[orden['id']]
        # Condición de carrera: sólo si sigue vacío
        res = await db.ordenes.update_one(
            {
                'id': orden['id'],
                '$or': [
                    {'token_seguimiento': {'$exists': False}},
                    {'token_seguimiento': None},
                    {'token_seguimiento': ''},
                ],
            },
            {'$set': {'token_seguimiento': token, 'updated_at': now_iso}}
        )
        if res.modified_count == 1:
            done += 1
            await db.audit_logs.insert_one({
                'id': f'MIG-TOKEN-{orden["id"]}-{ts}',
                'source': 'migration',
                'action': 'generate_tracking_token',
                'orden_id': orden['id'],
                'numero_orden': orden.get('numero_orden'),
                'after': {'token_seguimiento': token},
                'timestamp': now_iso,
                'script': 'generate_missing_tracking_tokens.py',
            })

    print(f'✅ {done} tokens generados. Backup: {backup_path}')
    client.close()


if __name__ == '__main__':
    asyncio.run(main())

"""
audit/data_integrity.py — Audita la integridad de la BD conectada.

Comprueba:
  - Registros huérfanos (ej. orden con cliente_id que no existe)
  - Duplicados por campos identificadores
  - Campos obligatorios faltantes
  - Inconsistencias de tipo (fechas como string vs datetime)
  - Referencias rotas entre colecciones

⚠️ ABORTA si DB_NAME == 'production'. Nunca debe correrse contra producción.

Uso:
  cd /app/backend && python -m scripts.audit.data_integrity
"""
import asyncio
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'), override=False)

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
DOCS = Path('/app/docs')
DOCS.mkdir(exist_ok=True)


async def iter_all(coll, projection=None):
    items = []
    async for doc in coll.find({}, projection):
        items.append(doc)
    return items


async def main():
    allow_prod = '--allow-production' in sys.argv
    if DB_NAME == 'production' and not allow_prod:
        print('❌ BLOQUEADO: este script no debe correrse sobre DB production.')
        print('   Si es intencional y solo-lectura, pasa --allow-production')
        sys.exit(1)
    if DB_NAME == 'production' and allow_prod:
        print('⚠️  AUTORIZACIÓN EXPLÍCITA recibida para auditar producción (SOLO LECTURA).')

    client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=10000)
    db = client[DB_NAME]

    print(f'🔍 Auditando integridad de BD: {DB_NAME}')

    findings = []

    # ── 1. Inventario de colecciones ────────────────────────────────────────
    all_colls = await db.list_collection_names()
    coll_stats = {}
    for c in all_colls:
        cnt = await db[c].count_documents({})
        coll_stats[c] = cnt

    # ── 2. Huérfanos y referencias rotas ────────────────────────────────────
    orphan_checks = [
        # (col, field, target_col, target_field)
        ('ordenes', 'cliente_id', 'clientes', 'id'),
        ('ordenes', 'tecnico_asignado', 'users', 'id'),
        ('facturas', 'cliente_id', 'clientes', 'id'),
        ('facturas', 'orden_id', 'ordenes', 'id'),
        ('mensajes', 'orden_id', 'ordenes', 'id'),
        ('notificaciones', 'orden_id', 'ordenes', 'id'),
        ('ordenes_compra', 'proveedor_id', 'proveedores', 'id'),
        ('liquidaciones', 'ordenes', 'ordenes', 'id'),  # array de IDs
        ('repuestos', 'proveedor_id', 'proveedores', 'id'),
    ]

    orphans = {}
    for col, field, target_col, target_field in orphan_checks:
        if col not in coll_stats or target_col not in coll_stats:
            continue
        target_ids = set()
        async for d in db[target_col].find({}, {target_field: 1, '_id': 0}):
            v = d.get(target_field)
            if v:
                target_ids.add(v)
        broken = []
        async for d in db[col].find({}, {field: 1, 'id': 1, 'numero_orden': 1, 'numero': 1, '_id': 0}):
            val = d.get(field)
            if isinstance(val, list):
                for v in val:
                    if v and v not in target_ids:
                        broken.append({'doc_id': d.get('id'), 'missing': v})
            elif val and val not in target_ids:
                broken.append({'doc_id': d.get('id') or d.get('numero_orden') or d.get('numero'), 'missing': val})
            if len(broken) >= 20:
                break
        if broken:
            orphans[f'{col}.{field} → {target_col}.{target_field}'] = broken

    # ── 3. Duplicados ───────────────────────────────────────────────────────
    dup_checks = [
        ('clientes', 'dni'),
        ('clientes', 'email'),
        ('users', 'email'),
        ('ordenes', 'numero_orden'),
        ('ordenes', 'numero_autorizacion'),
        ('facturas', 'numero'),
        ('repuestos', 'sku'),
        ('proveedores', 'nif'),
    ]
    duplicates = {}
    for col, field in dup_checks:
        if col not in coll_stats:
            continue
        counter = Counter()
        async for d in db[col].find({field: {'$exists': True, '$ne': None, '$ne': ''}}, {field: 1, '_id': 0}):
            v = d.get(field)
            if v:
                counter[v] += 1
        dups = {k: v for k, v in counter.items() if v > 1}
        if dups:
            duplicates[f'{col}.{field}'] = dups

    # ── 4. Campos obligatorios faltantes ───────────────────────────────────
    required_checks = {
        'ordenes': ['id', 'numero_orden', 'cliente_id', 'estado', 'created_at'],
        'clientes': ['id', 'nombre'],
        'users': ['id', 'email', 'role', 'password_hash'],
        'facturas': ['id', 'numero', 'cliente_id'],
        'repuestos': ['id', 'nombre'],
    }
    missing_fields = {}
    for col, fields in required_checks.items():
        if col not in coll_stats:
            continue
        for field in fields:
            count = await db[col].count_documents({'$or': [
                {field: {'$exists': False}},
                {field: None},
                {field: ''},
            ]})
            if count > 0:
                missing_fields[f'{col}.{field}'] = count

    # ── 5. Tipos inconsistentes (fechas como string vs ISO vs datetime) ────
    date_fields = [('ordenes', 'created_at'), ('ordenes', 'updated_at'),
                   ('facturas', 'fecha_emision'), ('clientes', 'created_at'),
                   ('notificaciones', 'created_at'), ('users', 'created_at')]
    date_types = {}
    for col, f in date_fields:
        if col not in coll_stats:
            continue
        type_counter = Counter()
        async for d in db[col].find({f: {'$exists': True}}, {f: 1, '_id': 0}):
            v = d.get(f)
            if v is None:
                type_counter['null'] += 1
            elif isinstance(v, datetime):
                type_counter['datetime'] += 1
            elif isinstance(v, str):
                type_counter['string'] += 1
            else:
                type_counter[type(v).__name__] += 1
        if len(type_counter) > 1:
            date_types[f'{col}.{f}'] = dict(type_counter)

    # ── 6. Render ───────────────────────────────────────────────────────────
    lines = []
    lines.append(f'# Informe de integridad de datos · BD `{DB_NAME}`')
    lines.append('')
    lines.append(f'_Generado · {datetime.now(timezone.utc).isoformat(timespec="seconds")}_')
    lines.append('')

    # Summary
    total_findings = len(orphans) + len(duplicates) + len(missing_fields) + len(date_types)
    lines.append('## Resumen ejecutivo')
    lines.append('')
    lines.append(f'- Colecciones totales: **{len(all_colls)}**')
    lines.append(f'- Documentos totales: **{sum(coll_stats.values()):,}**')
    lines.append(f'- Hallazgos totales: **{total_findings}**')
    lines.append(f'  - Referencias rotas: **{len(orphans)}**')
    lines.append(f'  - Duplicados: **{len(duplicates)}**')
    lines.append(f'  - Campos obligatorios faltantes: **{len(missing_fields)}**')
    lines.append(f'  - Tipos inconsistentes: **{len(date_types)}**')
    lines.append('')

    # 1. Inventory
    lines.append('## 1. Inventario de colecciones')
    lines.append('')
    lines.append('| Colección | Documentos |')
    lines.append('|---|---|')
    for c, n in sorted(coll_stats.items(), key=lambda x: -x[1]):
        lines.append(f'| `{c}` | {n:,} |')
    lines.append('')

    # 2. Orphans
    lines.append('## 2. Referencias rotas / huérfanos')
    lines.append('')
    if orphans:
        for rel, broken in orphans.items():
            lines.append(f'### 🚨 `{rel}`')
            lines.append(f'{len(broken)}+ documentos con referencia inexistente (muestra max 20):')
            lines.append('')
            lines.append('| Doc ID | Target inexistente |')
            lines.append('|---|---|')
            for b in broken[:20]:
                lines.append(f'| `{b["doc_id"]}` | `{b["missing"]}` |')
            lines.append('')
    else:
        lines.append('✅ No se detectan referencias rotas.')
        lines.append('')

    # 3. Duplicates
    lines.append('## 3. Duplicados')
    lines.append('')
    if duplicates:
        for field, dups in duplicates.items():
            lines.append(f'### 🟠 `{field}`')
            lines.append(f'{len(dups)} valores duplicados:')
            lines.append('')
            lines.append('| Valor | Apariciones |')
            lines.append('|---|---|')
            for val, cnt in list(dups.items())[:15]:
                lines.append(f'| `{val}` | {cnt} |')
            lines.append('')
    else:
        lines.append('✅ No se detectan duplicados en campos clave.')
        lines.append('')

    # 4. Missing fields
    lines.append('## 4. Campos obligatorios faltantes')
    lines.append('')
    if missing_fields:
        lines.append('| Campo | Docs sin valor |')
        lines.append('|---|---|')
        for k, v in sorted(missing_fields.items(), key=lambda x: -x[1]):
            lines.append(f'| `{k}` | {v} |')
    else:
        lines.append('✅ Todos los campos obligatorios están presentes.')
    lines.append('')

    # 5. Type inconsistencies
    lines.append('## 5. Tipos inconsistentes en campos fecha')
    lines.append('')
    if date_types:
        lines.append('Un mismo campo con varios tipos indica mezcla de criterios. Riesgo alto para ordenaciones y filtros.')
        lines.append('')
        lines.append('| Campo | Tipos encontrados |')
        lines.append('|---|---|')
        for k, types in date_types.items():
            lines.append(f'| `{k}` | ' + ', '.join(f'{t}={n}' for t, n in types.items()) + ' |')
    else:
        lines.append('✅ Todos los campos fecha usan tipo coherente.')
    lines.append('')

    out = DOCS / 'data_integrity_report.md'
    out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'✅ Generado: {out}')
    print(f'   {total_findings} hallazgos totales')
    print(f'   - Huérfanos: {len(orphans)}, Duplicados: {len(duplicates)}, Missing: {len(missing_fields)}, Tipos mixtos: {len(date_types)}')

    client.close()


if __name__ == '__main__':
    asyncio.run(main())

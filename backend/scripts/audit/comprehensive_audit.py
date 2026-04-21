"""
audit/comprehensive_audit.py — Auditoría profunda READ-ONLY de la BD.

Amplía data_integrity.py con:
  - Análisis operacional (estados, tiempos, SLA)
  - Análisis financiero (liquidaciones vs órdenes vs facturas)
  - Análisis de calidad ISO
  - Análisis de comunicación (notificaciones, emails)
  - Patrones sospechosos (órdenes estancadas, clientes duplicados blandos)
  - Cross-collection consistency

⚠️ 100% READ-ONLY. Ningún insert/update/delete. Ninguna colección se crea.

Uso:
  cd /app/backend && DB_NAME=production python -m scripts.audit.comprehensive_audit --allow-production
"""
import asyncio
import os
import sys
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'), override=False)

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
DOCS = Path('/app/docs')


def pct(n, total):
    if not total: return '0%'
    return f'{100*n/total:.1f}%'


def parse_dt(v):
    """Convierte string ISO o datetime a datetime aware."""
    if v is None: return None
    if isinstance(v, datetime):
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v
    if isinstance(v, str):
        try:
            s = v.replace('Z', '+00:00')
            return datetime.fromisoformat(s)
        except Exception:
            return None
    return None


async def main():
    allow_prod = '--allow-production' in sys.argv
    if DB_NAME == 'production' and not allow_prod:
        print('❌ BLOQUEADO: no autorizado en producción.')
        sys.exit(1)
    if DB_NAME == 'production' and allow_prod:
        print('⚠️  EJECUCIÓN SOLO-LECTURA sobre producción · autorización explícita recibida')

    client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=10000)
    db = client[DB_NAME]
    now = datetime.now(timezone.utc)

    print(f'🔍 Auditoría profunda READ-ONLY · BD: {DB_NAME}')

    # ═══════════════════════════════════════════════════════════════════════════
    # Cargas base
    # ═══════════════════════════════════════════════════════════════════════════
    ordenes = await db.ordenes.find({}).to_list(None)
    clientes = await db.clientes.find({}, {'_id': 0}).to_list(None)
    users = await db.users.find({}, {'_id': 0}).to_list(None)
    liquidaciones = await db.liquidaciones.find({}, {'_id': 0}).to_list(None)
    incidencias = await db.incidencias.find({}, {'_id': 0}).to_list(None)
    notifs = await db.notificaciones.find({}, {'_id': 0, 'id': 1, 'orden_id': 1, 'leida': 1, 'tipo': 1, 'created_at': 1}).to_list(None)

    client_ids = {c['id'] for c in clientes if c.get('id')}
    user_ids = {u['id'] for u in users if u.get('id')}
    orden_ids = {o['id'] for o in ordenes if o.get('id')}

    users_by_id = {u['id']: u for u in users if u.get('id')}

    lines = []
    lines.append(f'# 🔬 Auditoría profunda · BD `{DB_NAME}`')
    lines.append(f'_Generado · {now.isoformat(timespec="seconds")}_')
    lines.append('')
    lines.append(f'**Volumen:** {len(ordenes)} órdenes · {len(clientes)} clientes · {len(users)} usuarios · {len(liquidaciones)} liquidaciones · {len(incidencias)} incidencias')
    lines.append('')

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMINIO 1 · ÓRDENES — salud operacional
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append('## 🔧 Dominio Órdenes')
    lines.append('')

    # 1.1 Distribución de estados
    estado_counter = Counter(o.get('estado', '∅') for o in ordenes)
    lines.append('### Distribución de estados')
    lines.append('')
    lines.append('| Estado | Nº | % |')
    lines.append('|---|---|---|')
    for estado, n in estado_counter.most_common():
        lines.append(f'| `{estado}` | {n} | {pct(n, len(ordenes))} |')
    lines.append('')

    # 1.2 Órdenes estancadas (en estado "activo" > 15 días sin updated_at reciente)
    ACTIVE_STATES = {'pendiente', 'pendiente_recibir', 'recibida', 'diagnosticada', 'en_reparacion', 'esperando_aprobacion', 'esperando_material', 'reparada_pendiente_envio'}
    estancadas = []
    umbral = now - timedelta(days=15)
    for o in ordenes:
        if o.get('estado') in ACTIVE_STATES:
            upd = parse_dt(o.get('updated_at') or o.get('created_at'))
            if upd and upd < umbral:
                estancadas.append({
                    'id': o.get('id'), 'num': o.get('numero_orden'),
                    'estado': o.get('estado'), 'dias': (now - upd).days,
                    'tecnico': o.get('tecnico_asignado'),
                })

    lines.append('### ⏱ Órdenes estancadas (>15 d sin updates en estado activo)')
    lines.append('')
    if estancadas:
        lines.append(f'🟠 **{len(estancadas)}** órdenes estancadas.')
        lines.append('')
        lines.append('| Nº OT | Estado | Días estancada | Técnico |')
        lines.append('|---|---|---|---|')
        for e in sorted(estancadas, key=lambda x: -x['dias'])[:15]:
            t = users_by_id.get(e['tecnico'], {}).get('email', e['tecnico'] or '—')
            lines.append(f'| `{e["num"]}` | {e["estado"]} | **{e["dias"]}** | {t} |')
        if len(estancadas) > 15:
            lines.append(f'| … | | | +{len(estancadas)-15} más |')
    else:
        lines.append('✅ Ninguna orden estancada >15 d.')
    lines.append('')

    # 1.3 Técnicos: productividad
    tecnico_counter = Counter()
    for o in ordenes:
        t = o.get('tecnico_asignado')
        if t: tecnico_counter[t] += 1
    lines.append('### Carga por técnico')
    lines.append('')
    lines.append('| Técnico | Órdenes totales | ✅ Existe user | ⚠️ Notas |')
    lines.append('|---|---|---|---|')
    for t, n in tecnico_counter.most_common():
        u = users_by_id.get(t)
        if u:
            email = u.get('email', '—')
            flag = f'✅ {u.get("role")}'
            note = ''
        elif t and '@' in t:
            flag = '❌'
            email = t
            note = '🚨 valor es email, no UUID → refactor de datos pendiente'
        else:
            flag = '❌'
            email = t
            note = 'user no existe'
        lines.append(f'| `{email}` | {n} | {flag} | {note} |')
    lines.append('')

    # 1.4 Campos nulos críticos en órdenes
    sin_imei = sum(1 for o in ordenes if not (o.get('dispositivo') or {}).get('imei'))
    sin_averia = sum(1 for o in ordenes if not (o.get('dispositivo') or {}).get('averia_reportada'))
    sin_token = sum(1 for o in ordenes if not o.get('token_seguimiento'))
    sin_created = sum(1 for o in ordenes if not o.get('created_at'))
    lines.append('### Calidad de datos en órdenes')
    lines.append('')
    lines.append('| Campo crítico | Órdenes sin el dato | % |')
    lines.append('|---|---|---|')
    lines.append(f'| Dispositivo sin IMEI | {sin_imei} | {pct(sin_imei, len(ordenes))} |')
    lines.append(f'| Sin avería reportada | {sin_averia} | {pct(sin_averia, len(ordenes))} |')
    lines.append(f'| Sin token de seguimiento | {sin_token} | {pct(sin_token, len(ordenes))} |')
    lines.append(f'| Sin `created_at` | {sin_created} | {pct(sin_created, len(ordenes))} |')
    lines.append('')

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMINIO 2 · CLIENTES — salud y duplicados blandos
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append('## 👥 Dominio Clientes')
    lines.append('')

    # 2.1 Clientes sin órdenes (inactivos)
    clientes_con_orden = {o.get('cliente_id') for o in ordenes}
    sin_ordenes = [c for c in clientes if c.get('id') not in clientes_con_orden]
    lines.append(f'- **{len(sin_ordenes)}** clientes sin ninguna orden ({pct(len(sin_ordenes), len(clientes))}). Candidatos a revisar si son reales.')

    # 2.2 Duplicados blandos: mismo nombre+apellidos (sin DNI igual ya lo detecta integrity)
    key_counter = Counter()
    for c in clientes:
        n = (c.get('nombre') or '').strip().lower()
        a = (c.get('apellidos') or '').strip().lower()
        t = (c.get('telefono') or '').strip()
        if n and a:
            key_counter[(n, a)] += 1
    soft_dups = {k: v for k, v in key_counter.items() if v > 1}
    lines.append(f'- **{len(soft_dups)}** posibles duplicados blandos (mismo nombre+apellidos).')
    if soft_dups:
        lines.append('')
        lines.append('| Nombre + apellidos | Nº registros |')
        lines.append('|---|---|')
        for (n, a), cnt in sorted(soft_dups.items(), key=lambda x: -x[1])[:10]:
            lines.append(f'| `{n} {a}` | {cnt} |')
    lines.append('')

    # 2.3 Clientes sin email ni teléfono
    sin_contacto = sum(1 for c in clientes if not c.get('email') and not c.get('telefono'))
    lines.append(f'- **{sin_contacto}** clientes sin email NI teléfono ({pct(sin_contacto, len(clientes))}). Imposibles de contactar.')
    lines.append('')

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMINIO 3 · FINANZAS / LIQUIDACIONES
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append('## 💰 Dominio Finanzas')
    lines.append('')

    # 3.1 Liquidaciones: estado
    liq_estado = Counter(l.get('estado', '∅') for l in liquidaciones)
    lines.append('### Estado de liquidaciones')
    lines.append('')
    lines.append('| Estado | Nº |')
    lines.append('|---|---|')
    for e, n in liq_estado.most_common():
        lines.append(f'| `{e}` | {n} |')
    lines.append('')

    # 3.2 Órdenes con nº autorización que NO están en ninguna liquidación
    liq_orden_ids = set()
    liq_autorizaciones = set()
    for l in liquidaciones:
        liq_autorizaciones.update(l.get('numeros_autorizacion', []) or [])
        for oid in l.get('ordenes', []) or []:
            if isinstance(oid, str): liq_orden_ids.add(oid)
            elif isinstance(oid, dict): liq_orden_ids.add(oid.get('id') or oid.get('orden_id'))

    cerradas_sin_liquidar = []
    for o in ordenes:
        if o.get('numero_autorizacion') and o.get('estado') in {'entregada', 'facturada', 'reparado', 'cerrada', 'cerrado'}:
            if o['id'] not in liq_orden_ids and o.get('numero_autorizacion') not in liq_autorizaciones:
                cerradas_sin_liquidar.append({
                    'num': o.get('numero_orden'),
                    'autoriz': o.get('numero_autorizacion'),
                    'estado': o.get('estado'),
                    'fecha': o.get('updated_at') or o.get('created_at'),
                })
    lines.append('### 🚨 Órdenes cerradas con autorización pero SIN liquidar')
    lines.append('')
    if cerradas_sin_liquidar:
        lines.append(f'🟠 **{len(cerradas_sin_liquidar)}** órdenes son dinero potencialmente no facturado a aseguradora.')
        lines.append('')
        lines.append('| Nº OT | Autorización | Estado | Fecha |')
        lines.append('|---|---|---|---|')
        for e in cerradas_sin_liquidar[:15]:
            lines.append(f'| `{e["num"]}` | `{e["autoriz"]}` | {e["estado"]} | {e["fecha"]} |')
        if len(cerradas_sin_liquidar) > 15:
            lines.append(f'| … +{len(cerradas_sin_liquidar)-15} más | | | |')
    else:
        lines.append('✅ Toda orden cerrada con autorización está liquidada.')
    lines.append('')

    # 3.3 Números de autorización duplicados (detallado)
    aut_counter = Counter(o.get('numero_autorizacion') for o in ordenes if o.get('numero_autorizacion'))
    aut_dups = {k: v for k, v in aut_counter.items() if v > 1}
    lines.append('### Autorizaciones con varias órdenes (posibles garantías)')
    lines.append('')
    if aut_dups:
        lines.append(f'**{len(aut_dups)}** autorizaciones aparecen en >1 orden.')
        lines.append('')
        lines.append('| Autorización | Órdenes | Detalle |')
        lines.append('|---|---|---|')
        for aut, n in list(aut_dups.items())[:10]:
            ords = [o for o in ordenes if o.get('numero_autorizacion') == aut]
            detalle = ', '.join(f'{o.get("numero_orden")} ({o.get("estado")}, garantia={o.get("es_garantia", False)})' for o in ords)
            lines.append(f'| `{aut}` | {n} | {detalle} |')
    lines.append('')

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMINIO 4 · COMUNICACIONES
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append('## ✉️ Dominio Comunicaciones')
    lines.append('')

    notif_huerf = [n for n in notifs if n.get('orden_id') and n['orden_id'] not in orden_ids]
    notif_no_leidas = sum(1 for n in notifs if n.get('leida') is False)
    lines.append(f'- Total notificaciones: **{len(notifs)}**')
    lines.append(f'- No leídas: **{notif_no_leidas}** ({pct(notif_no_leidas, len(notifs))})')
    lines.append(f'- Huérfanas (orden_id inexistente): **{len(notif_huerf)}**')
    lines.append('')

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMINIO 5 · INCIDENCIAS
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append('## ⚠️ Dominio Incidencias')
    lines.append('')

    inc_estado = Counter(i.get('estado', '∅') for i in incidencias)
    inc_abiertas = [i for i in incidencias if i.get('estado') not in ('cerrada', 'resuelta')]
    lines.append(f'- Total: **{len(incidencias)}**')
    lines.append(f'- Abiertas: **{len(inc_abiertas)}**')
    lines.append('')
    lines.append('| Estado | Nº |')
    lines.append('|---|---|')
    for e, n in inc_estado.most_common():
        lines.append(f'| `{e}` | {n} |')
    lines.append('')

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMINIO 6 · CALIDAD / ISO
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append('## 🏅 Dominio Calidad ISO')
    lines.append('')

    iso_qa = await db.iso_qa_muestreos.count_documents({}) if 'iso_qa_muestreos' in await db.list_collection_names() else 0
    iso_docs = await db.iso_documentos.count_documents({}) if 'iso_documentos' in await db.list_collection_names() else 0
    iso_eval = await db.iso_proveedores_evaluacion.count_documents({})
    iso_ncs = await db.iso_no_conformidades.count_documents({}) if 'iso_no_conformidades' in await db.list_collection_names() else 0
    lines.append('| Registro | Cantidad |')
    lines.append('|---|---|')
    lines.append(f'| Muestreos QA | {iso_qa} |')
    lines.append(f'| Documentos controlados | {iso_docs} |')
    lines.append(f'| Evaluaciones proveedores | {iso_eval} |')
    lines.append(f'| No-conformidades | {iso_ncs} |')
    lines.append('')
    if iso_qa == 0 and iso_ncs == 0 and iso_docs == 0:
        lines.append('🟠 **El SGC ISO está vacío en la BD** → el módulo existe en código pero no se ha alimentado con datos reales todavía. Candidato claro para el agente ISO Officer.')
    lines.append('')

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMINIO 7 · SEGURIDAD / AUTH
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append('## 🔐 Dominio Seguridad')
    lines.append('')

    roles = Counter(u.get('role') for u in users)
    lines.append('### Usuarios por rol')
    lines.append('')
    lines.append('| Rol | Nº |')
    lines.append('|---|---|')
    for r, n in roles.most_common():
        lines.append(f'| `{r}` | {n} |')
    lines.append('')

    # Users con contraseña temporal o sin password_hash
    sin_hash = sum(1 for u in users if not u.get('password_hash'))
    pwd_temp = sum(1 for u in users if u.get('password_temporal'))
    lines.append(f'- Sin `password_hash`: **{sin_hash}** (imposibilitados de hacer login)')
    lines.append(f'- Con `password_temporal=true`: **{pwd_temp}** (deben cambiar al loguearse)')
    lines.append('')

    # Audit logs recientes
    audit_count = await db.audit_logs.count_documents({})
    last_audit = await db.audit_logs.find_one({}, sort=[('timestamp', -1)])
    lines.append(f'- Total audit_logs: **{audit_count}**')
    if last_audit:
        lines.append(f'- Último evento audit: `{last_audit.get("action", "?")}` · {last_audit.get("timestamp")}')
    lines.append('')

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMINIO 8 · INVENTARIO
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append('## 📦 Dominio Inventario')
    lines.append('')
    repuestos = await db.repuestos.find({}).to_list(None)
    sin_sku = sum(1 for r in repuestos if not r.get('sku'))
    sin_stock_actual = sum(1 for r in repuestos if r.get('stock_actual') is None)
    stock_total = sum((r.get('stock_actual') or 0) for r in repuestos)
    lines.append(f'- Total repuestos: **{len(repuestos)}**')
    lines.append(f'- Sin SKU: **{sin_sku}**')
    lines.append(f'- Sin `stock_actual`: **{sin_stock_actual}**')
    lines.append(f'- Stock total (suma unidades): **{stock_total}**')
    lines.append('')

    # Materiales consumidos en órdenes vs repuestos existentes
    mat_refs = []
    for o in ordenes:
        for m in (o.get('materiales') or []):
            r = m.get('repuesto_id') or m.get('id')
            if r: mat_refs.append(r)
    repuesto_ids_existentes = {r.get('id') for r in repuestos}
    mat_rotos = [r for r in mat_refs if r not in repuesto_ids_existentes]
    lines.append(f'- Materiales referenciados en órdenes que apuntan a repuestos inexistentes: **{len(mat_rotos)}**')
    lines.append('')

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMINIO 9 · IA / AGENTE ARIA
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append('## 🤖 Dominio IA')
    lines.append('')
    agent_logs = await db.agent_logs.count_documents({})
    agent_conv = await db.agent_conversations.count_documents({})
    lines.append(f'- `agent_logs`: **{agent_logs:,}** entradas · indica uso real del agente ARIA')
    lines.append(f'- `agent_conversations`: **{agent_conv}** hilos')
    lines.append('')

    # ═══════════════════════════════════════════════════════════════════════════
    # RESUMEN FINAL — flags
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append('---')
    lines.append('')
    lines.append('## 🎯 Resumen ejecutivo')
    lines.append('')
    flags = []
    if estancadas:
        flags.append(f'🟠 {len(estancadas)} órdenes estancadas >15d sin actualización')
    if any('@' in (t or '') for t in tecnico_counter.keys()):
        emails_t = [t for t in tecnico_counter.keys() if '@' in (t or '')]
        afectadas = sum(tecnico_counter[t] for t in emails_t)
        flags.append(f'🔴 {afectadas} órdenes con `tecnico_asignado` como email en vez de UUID')
    if soft_dups:
        flags.append(f'🟡 {len(soft_dups)} grupos de clientes duplicados blandos')
    if sin_contacto:
        flags.append(f'🟡 {sin_contacto} clientes sin email ni teléfono')
    if cerradas_sin_liquidar:
        flags.append(f'🔴 {len(cerradas_sin_liquidar)} órdenes cerradas con autorización SIN liquidar (posible dinero perdido)')
    if aut_dups:
        flags.append(f'🟠 {len(aut_dups)} nº autorización en >1 orden (verificar si son garantías)')
    if notif_huerf:
        flags.append(f'🟡 {len(notif_huerf)} notificaciones huérfanas')
    if inc_abiertas:
        flags.append(f'🟡 {len(inc_abiertas)} incidencias abiertas')
    if iso_qa == 0:
        flags.append('🟢 SGC ISO vacío en datos (módulo existe pero sin uso) → oportunidad para agente ISO')
    if mat_rotos:
        flags.append(f'🔴 {len(mat_rotos)} materiales referenciados a repuestos inexistentes')

    if flags:
        for f in flags:
            lines.append(f'- {f}')
    else:
        lines.append('✅ Sistema sano en todos los dominios auditados.')
    lines.append('')

    out = DOCS / 'comprehensive_audit.md'
    out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'✅ Generado: {out}')
    print(f'   Flags: {len(flags)}')
    for f in flags: print(f'   {f}')

    client.close()


if __name__ == '__main__':
    asyncio.run(main())

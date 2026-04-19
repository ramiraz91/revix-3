"""
audit/domain_map.py — Mapa automático de dominios del backend Revix.

Analiza /app/backend/routes/*.py y agrupa endpoints por dominio de negocio.
Detecta:
  - Duplicación entre archivos (mismo path o path similar en distintos módulos)
  - Modelos Pydantic usados por cada archivo
  - Colecciones MongoDB accedidas por cada archivo
  - Número de endpoints, decorador de auth, etc.

Genera /app/docs/domain_map.md (no toca la BD).

Uso:
  cd /app/backend && python -m scripts.audit.domain_map
"""
import os
import re
from collections import defaultdict
from pathlib import Path

BACKEND = Path('/app/backend')
ROUTES = BACKEND / 'routes'
DOCS = Path('/app/docs')
DOCS.mkdir(exist_ok=True)

# ── Patrones ────────────────────────────────────────────────────────────────
RE_ROUTE = re.compile(
    r'@router\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']'
)
RE_DB_COLL = re.compile(r'db\.([a-zA-Z_][a-zA-Z0-9_]*)')
RE_MODEL_IMPORT = re.compile(r'from\s+models\s+import\s+([^\n]+)')
RE_AUTH = re.compile(r'Depends\(\s*(require_auth|require_admin|require_master|get_current_user)')
RE_PREFIX = re.compile(r'APIRouter\(\s*prefix\s*=\s*["\']([^"\']+)["\']')

# ── Clasificación por dominio (heurístico basado en prefix/keywords) ────────
DOMAINS = {
    'Órdenes': ['/ordenes', '/scan', '/nuevas', 'ordenes_', 'nuevas_ordenes', 'ordenes_mejorado'],
    'Clientes': ['/clientes', '/cliente/', 'clientes'],
    'Proveedores': ['/proveedores', 'proveedor'],
    'Inventario/Repuestos': ['/repuestos', '/inventario', '/kits', '/restos', 'repuesto', 'inventario', 'kits_', 'restos_'],
    'Finanzas/Contabilidad': ['/facturas', '/contabilidad', '/finanzas', '/liquidaciones', '/pagos', 'contabilidad', 'finanzas', 'liquidaciones'],
    'Logística': ['/logistica', '/envio', '/gls', '/print', 'logistica', 'print_'],
    'Aseguradoras (Insurama)': ['/insurama', '/peticiones', '/siniestros', 'insurama', 'peticiones'],
    'Calidad ISO': ['/iso', 'iso_'],
    'Comunicaciones': ['/notificaciones', '/mensajes', '/email', 'notificaciones'],
    'Calendario': ['/calendario', '/eventos', 'calendario'],
    'IA / Agentes': ['/agent', '/ia', '/aria', 'agent_', 'ia_', 'insurama_ia', 'inteligencia'],
    'Compras': ['/compras', '/ordenes-compra', '/mobilesentrix', '/utopya', 'compras', 'mobilesentrix', 'utopya'],
    'Web pública': ['/web/', '/public', '/presupuesto', '/consulta', '/faqs', 'web_publica', 'apple_manuals'],
    'Admin / Master': ['/admin', '/master', '/users', '/empresa', '/config', 'admin_', 'master_', 'config_empresa'],
    'Autenticación': ['/auth', '/login', '/register', 'auth_'],
    'Dashboard / Datos': ['/dashboard', 'dashboard', 'data_'],
    'WebSocket': ['/ws', 'websocket'],
}


def classify_module(filename: str, prefix: str, paths: list[str]) -> str:
    """Clasifica un módulo por su nombre de fichero + prefix + rutas."""
    candidates = [filename] + ([prefix] if prefix else []) + paths
    target = ' '.join(candidates).lower()
    best_match = 'Otros'
    best_score = 0
    for domain, keywords in DOMAINS.items():
        score = sum(1 for kw in keywords if kw.lower() in target)
        if score > best_score:
            best_match = domain
            best_score = score
    return best_match


def parse_module(filepath: Path) -> dict:
    code = filepath.read_text(encoding='utf-8', errors='replace')
    routes = [(m.lower(), p) for m, p in RE_ROUTE.findall(code)]
    prefix_m = RE_PREFIX.search(code)
    prefix = prefix_m.group(1) if prefix_m else ''
    collections = sorted(set(RE_DB_COLL.findall(code)))
    models = []
    for m in RE_MODEL_IMPORT.finditer(code):
        models += [x.strip() for x in m.group(1).split(',') if x.strip()]
    has_auth = bool(RE_AUTH.search(code))
    return {
        'file': filepath.name,
        'prefix': prefix,
        'routes': routes,
        'paths': [p for _, p in routes],
        'collections': collections,
        'models': sorted(set(models)),
        'has_auth_guard': has_auth,
        'lines': len(code.splitlines()),
    }


def normalize_path(p: str) -> str:
    """Sustituye {id} por {:id} para detectar paths equivalentes."""
    return re.sub(r'\{[^}]+\}', '{:var}', p)


def main():
    modules = []
    for f in sorted(ROUTES.glob('*_routes.py')):
        modules.append(parse_module(f))

    # Clasificar por dominio
    by_domain = defaultdict(list)
    for m in modules:
        domain = classify_module(m['file'], m['prefix'], m['paths'])
        m['domain'] = domain
        by_domain[domain].append(m)

    # Detectar paths duplicados entre módulos
    path_owners = defaultdict(list)
    for m in modules:
        for method, p in m['routes']:
            key = f"{method.upper()} {normalize_path(p)}"
            path_owners[key].append(m['file'])

    duplicates = {k: v for k, v in path_owners.items() if len(set(v)) > 1}

    # Detectar colecciones compartidas (potenciales solapamientos de escritura)
    coll_owners = defaultdict(list)
    for m in modules:
        for c in m['collections']:
            coll_owners[c].append(m['file'])
    shared_collections = {
        c: sorted(set(owners))
        for c, owners in coll_owners.items()
        if len(set(owners)) > 1
    }

    # ── Render ──────────────────────────────────────────────────────────────
    lines = []
    lines.append('# Mapa de dominios — Backend Revix')
    lines.append('')
    lines.append(f'_Generado automáticamente · {len(modules)} módulos · {sum(len(m["routes"]) for m in modules)} endpoints_')
    lines.append('')

    # 1. Resumen por dominio
    lines.append('## 1. Resumen por dominio')
    lines.append('')
    lines.append('| Dominio | Módulos | Endpoints | Colecciones Mongo |')
    lines.append('|---|---|---|---|')
    for domain in sorted(by_domain.keys()):
        mods = by_domain[domain]
        total_endpoints = sum(len(m['routes']) for m in mods)
        colls = sorted({c for m in mods for c in m['collections']})
        lines.append(
            f'| **{domain}** | {len(mods)} | {total_endpoints} | {", ".join(colls[:6]) or "—"}{" …" if len(colls) > 6 else ""} |'
        )
    lines.append('')

    # 2. Detalle por dominio
    lines.append('## 2. Detalle por dominio')
    lines.append('')
    for domain in sorted(by_domain.keys()):
        mods = by_domain[domain]
        lines.append(f'### {domain}')
        lines.append('')
        for m in mods:
            auth_badge = '🔒' if m['has_auth_guard'] else '⚠️ SIN AUTH'
            lines.append(f'**`{m["file"]}`** · prefix `{m["prefix"] or "—"}` · {len(m["routes"])} endpoints · {m["lines"]} líneas · {auth_badge}')
            lines.append('')
            if m['collections']:
                lines.append(f'- Colecciones: `{", ".join(m["collections"])}`')
            if m['paths']:
                # mostrar solo primeros 6
                sample = m['paths'][:6]
                lines.append(f'- Rutas: `{", ".join(sample)}`{" …" if len(m["paths"]) > 6 else ""}')
            lines.append('')
        lines.append('')

    # 3. Duplicados de paths (🚨)
    lines.append('## 3. ⚠️ Paths duplicados entre módulos')
    lines.append('')
    if duplicates:
        lines.append('Paths iguales o equivalentes expuestos por más de un módulo. **Candidatos a consolidación.**')
        lines.append('')
        lines.append('| Método + Path | Módulos |')
        lines.append('|---|---|')
        for k, owners in sorted(duplicates.items()):
            lines.append(f'| `{k}` | {", ".join(sorted(set(owners)))} |')
    else:
        lines.append('✅ No se detectan paths duplicados entre módulos.')
    lines.append('')

    # 4. Colecciones compartidas
    lines.append('## 4. Colecciones Mongo compartidas entre módulos')
    lines.append('')
    lines.append('Un dominio limpio tendría cada colección escrita por **un solo módulo**. Colecciones leídas por varios es OK, escritas por varios = riesgo de inconsistencias.')
    lines.append('')
    lines.append('| Colección | Módulos que la usan |')
    lines.append('|---|---|')
    for c, owners in sorted(shared_collections.items()):
        badge = '🟠' if len(owners) >= 3 else '🟡'
        lines.append(f'| {badge} `{c}` | {", ".join(owners)} |')
    if not shared_collections:
        lines.append('| ✅ Ninguna | — |')
    lines.append('')

    # 5. Modelos Pydantic huérfanos / potenciales
    lines.append('## 5. Modelos Pydantic referenciados')
    lines.append('')
    all_models = set()
    for m in modules:
        all_models.update(m['models'])
    lines.append(f'Total de modelos **importados en routes/**: {len(all_models)}')
    lines.append('')
    lines.append('<details><summary>Ver lista completa</summary>')
    lines.append('')
    lines.append(', '.join(f'`{x}`' for x in sorted(all_models)))
    lines.append('')
    lines.append('</details>')
    lines.append('')

    # 6. Endpoints sin auth (banderas rojas)
    lines.append('## 6. 🚨 Módulos sin guards de auth')
    lines.append('')
    unguarded = [m for m in modules if not m['has_auth_guard']]
    if unguarded:
        lines.append('Estos módulos no detectan `require_auth` en el fichero. **Revisar** (pueden ser públicos legítimos como `/api/web/*` o estar exponiendo datos sin control).')
        lines.append('')
        for m in unguarded:
            lines.append(f'- `{m["file"]}` · {len(m["routes"])} endpoints · prefix `{m["prefix"] or "—"}`')
    else:
        lines.append('✅ Todos los módulos tienen al menos una referencia a un guard de auth.')
    lines.append('')

    out = DOCS / 'domain_map.md'
    out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'✅ Generado: {out} ({len(lines)} líneas)')
    print(f'   {len(modules)} módulos · {sum(len(m["routes"]) for m in modules)} endpoints · {len(by_domain)} dominios')
    if duplicates:
        print(f'   ⚠️  {len(duplicates)} paths duplicados detectados')
    if shared_collections:
        print(f'   ⚠️  {len(shared_collections)} colecciones compartidas entre módulos')
    if unguarded:
        print(f'   ⚠️  {len(unguarded)} módulos sin guard de auth visible')


if __name__ == '__main__':
    main()

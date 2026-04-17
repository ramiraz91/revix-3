# Revix CRM/ERP - Product Requirements Document

## Original Problem Statement
CRM/ERP para taller de reparacion de telefonia movil (Revix.es).

## Tech Stack
- Frontend: React 18, Tailwind CSS, Shadcn/UI, JsBarcode
- Backend: FastAPI, Motor (async MongoDB)
- Database: MongoDB Atlas (production) — 27 indices optimizados
- Label Printing: Agente Windows (Waitress + Pillow + python-barcode + pywin32)

---

## Latest — 2026-04-17

### Estabilidad y Calidad de Codigo
- **27 indices MongoDB** creados: ordenes (7), clientes (3), users (3), repuestos (3), liquidaciones (2), print_jobs (3), notificaciones (3), audit_log (3). Se verifican en cada startup.
- **24 tests automaticos** (pytest): auth, ordenes, dashboard, clientes, liquidaciones, impresion, seguimiento, verificacion URLs produccion. 100% passed.
- **Lint backend**: 94 errores -> 40 (cosmeticos). 0 undefined names, 0 bare excepts.
- **Empty catch blocks**: Corregidos con console.error() en 4 paginas frontend.
- **MD5 -> SHA-256** en utopya_routes.py
- **Wildcard import eliminado** en email_service.py
- **Usuarios duplicados** en MongoDB limpiados (master-001 x2 -> x1)
- **URLs produccion**: FRONTEND_URL hardcodeado a https://revix.es en config.py, helpers.py, auth_routes.py, ordenes_routes.py. Eliminado override dinamico de startup.

### Indices MongoDB creados
- ordenes: id(unique), numero_autorizacion, origen, created_at, tecnico_asignado, estado+auth, estado+fecha
- clientes: id(unique), email, nombre
- users: id(unique), email(unique), role
- repuestos: id(unique), sku, categoria
- liquidaciones: codigo_siniestro, estado
- print_jobs: job_id(unique), status, requested_at
- notificaciones: usuario_id, created_at, leida
- audit_log: entity_id, timestamp, entity_type+entity_id

---

## Backlog
- P2: Google Business Profile + Gemini Flash
- P2: Flujo gestion de incidencias

## Credentials
- master@revix.es / RevixMaster2026!
- Agent key: revix-brother-agent-2026-key

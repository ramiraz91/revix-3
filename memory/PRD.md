# Revix CRM/ERP - Product Requirements Document

## Original Problem Statement
CRM/ERP para taller de reparacion de telefonia movil (Revix.es).

## Tech Stack
- Frontend: React 18, Tailwind CSS, Shadcn/UI, JsBarcode
- Backend: FastAPI, Motor (async MongoDB)
- Database: MongoDB Atlas (production) — 27 indices optimizados
- Label Printing: Agente Windows (Waitress + Pillow + python-barcode + pywin32)

---

## Latest — 2026-04-18

### Aislamiento Preview/Producción
- Preview ahora usa BD `revix_preview` (mismo cluster Atlas, DB separada).
- Producción sigue en BD `production`, intocable desde este entorno.
- Seed idempotente `scripts/seed_preview.py`: 3 usuarios + 2 clientes + 3 órdenes demo.
- El seed aborta si detecta `DB_NAME=production` (salvaguarda).

### Deployment Readiness — PASS
- Deployment Agent: **status: pass** — listo para despliegue a producción.
- FRONTEND_URL ahora lee de env var con filtro anti-preview-URL (default: https://revix.es).
- CORS_ORIGINS ahora configurable via env var.
- JWT_SECRET exige env var (raise RuntimeError si falta).
- database.py: eliminado fallback hardcodeado de MONGO_URL/DB_NAME (exige env vars).
- .gitignore: eliminados patrones `*.env` para permitir deploy; añadido `memory/test_credentials.md`.
- 24/24 tests críticos pasan tras cambios.

## 2026-04-17 — Estabilidad y Calidad
- 27 indices MongoDB + 24 tests automaticos (pytest).
- Lint backend 94→40 errores (cosmeticos), 0 undefined/bare excepts.
- MD5→SHA-256, wildcard imports eliminados, usuarios duplicados limpiados.
- Seguridad: SlowAPI rate limiting, middleware NoSQL injection, JWT 24h.
- Refactorización server.py: 3400→1000 líneas (routes modulares).

## 2026-04 — Features
- Sistema impresión Brother QL-800 centralizado con agente Windows + cola MongoDB.
- Historial de impresiones, SKUs cortos automáticos, sección Comunicaciones Insurama.
- Estado "FUERA DE GARANTIA" en PDF/UI.
- Liquidaciones: agrupación por nº autorización, separación garantías, sin duplicados.
- Fix enlaces seguimiento en emails (producción, no preview).

---

## Backlog
- P2: Google Business Profile + Gemini Flash.
- P2: Flujo gestión de incidencias.

## Credentials
- master@revix.es / RevixMaster2026!
- Agent key: revix-brother-agent-2026-key

# Revix CRM/ERP - Product Requirements Document

## Original Problem Statement
CRM/ERP para taller de reparacion de telefonia movil (Revix.es).

## Tech Stack
- Frontend: React 18, Tailwind CSS, Shadcn/UI, JsBarcode
- Backend: FastAPI, Motor (async MongoDB)
- Database: MongoDB Atlas (production) — 27 indices optimizados
- Label Printing: Agente Windows (Waitress + Pillow + python-barcode + pywin32)

---

## Latest — 2026-04-20

### Fase 0 Pre-agentes MCP — COMPLETADA
- Script `fix_tecnico_email_to_uuid.py` aplicado en producción: 5 órdenes migradas (email → UUID). Backup + audit log generados.
- Script `generate_missing_tracking_tokens.py` aplicado en producción: 87 tokens creados. Todas las órdenes ya consultables en portal cliente.
- 2 órdenes detectadas con autorización sin liquidar (380€): reportadas para revisión manual del usuario.
- `seed_preview.py` ampliado: ahora crea plantilla_email, configuracion, incidencia, factura, liquidación e iso_qa_muestreo. Idempotente. Preview ya es representativo.
- Frontend OrdenDetalle: Resumen Financiero calcula en vivo con la MISMA fórmula que el backend (incluyendo `mano_obra × 0.5` en beneficio). Coherencia total tabla ↔ resumen.
- Scripts de migración en `/app/backend/scripts/migrations/` con patrón dry-run/apply, backups automáticos y safeguard `--allow-production`.

## Latest — 2026-04-21

### Agentes IA nativos en Revix ✅ (sustituye Rowboat)
Montado un orquestador multi-agente propio dentro del CRM. Los agentes hablan con Claude Sonnet 4.5 (vía Emergent LLM Key + LiteLLM) y ejecutan tools a través del servidor MCP interno con audit_logs automáticos.

**3 agentes Fase 1 (read-only)** en `/app/backend/modules/agents/`:
- **KPI Analyst** 📊 — dashboard + métricas + análisis de órdenes/clientes/inventario (8 tools).
- **Auditor Transversal** 🔍 — detección de anomalías, SLA, coherencia ISO 9001 (8 tools).
- **Seguimiento Público** 📱 — asistente al cliente final, solo token (scope `public:track_by_token` estricto).

**Arquitectura**:
- `agent_defs.py`: catálogo de agentes (system prompt + scopes + tools + modelo).
- `engine.py`: agent loop con tool-calling (`litellm.completion` + Emergent proxy), hasta 8 iteraciones, convierte tools MCP al esquema OpenAI function-calling que Claude entiende.
- `routes.py`: API `/api/agents*` con sesiones persistentes + endpoint público sin auth para widget cliente.
- `revix_mcp.runtime.execute_tool_internal()` nuevo: permite al orquestador ejecutar tools sin API key física, manteniendo audit + scopes.

**Frontend** `/app/frontend/src/pages/AgentesIA.jsx`:
- Ruta `/crm/agentes` (admin) con layout 3 columnas: agentes, chat, audit panel.
- Sample prompts, markdown rendering (react-markdown), badges de tools ejecutadas con duración, scroll auto, gestión de sesiones (crear, seleccionar, borrar).
- Audit logs en vivo desde el panel lateral.
- Nueva entrada en sidebar "Agentes IA · Nuevo".

**Testing**:
- Smoke test end-to-end: login → `/crm/agentes` → sample prompt → respuesta markdown ejecutiva en 13s con tool `obtener_dashboard` (843ms). ✅
- Audit logs MCP persistidos correctamente (timestamp, agent_id, tool, duration_ms).
- Endpoint público sin auth responde correctamente pidiendo token.
- Tests MCP existentes: 41/41 siguen pasando.

### Credenciales
- Chat admin: `master@revix.es` / `RevixMaster2026!` → `/crm/agentes`
- Chat público (widget cliente): `POST /api/public/agents/seguimiento/chat` — sin auth, solo `public:track_by_token`.

## Latest — 2026-04-20 (3)

### Fase 1 MCP · 8 Tools Read-Only completadas ✅
Tools registradas (`/app/revix_mcp/tools/`), todas con proyecciones estrictas Mongo y audit log automático:
1. `buscar_orden(ref)` — orders:read · resuelve por UUID, numero_orden o numero_autorizacion.
2. `listar_ordenes(filtros)` — orders:read · paginado, filtros por estado/técnico/cliente/garantía/autorización/fechas.
3. `buscar_cliente(q)` — customers:read · búsqueda exacta (id/dni/email/tel/cif) o fuzzy por nombre.
4. `obtener_historial_cliente(cliente_id)` — customers:read · resumen + órdenes, materiales opcionales.
5. `consultar_inventario(filtros)` — inventory:read · texto libre, proveedor, solo_bajo_minimo, solo_sin_stock, es_pantalla · etiqueta `nivel_stock`.
6. `obtener_metricas(metrica, periodo)` — metrics:read · 11 métricas (estados, técnicos, ingresos, beneficio, top modelos, SLA, garantía, aprobación presupuestos...).
7. `obtener_dashboard(periodo)` — dashboard:read · snapshot agregado órdenes + finanzas + inventario + clientes.
8. `buscar_por_token_seguimiento(token)` — public:track_by_token · info mínima apta para cliente final (NO expone costes/materiales/técnico). `*:read` NO cubre este scope por diseño.

### Tests MCP: 41/41 pasando
- `/app/revix_mcp/tests/test_foundation.py` (19 tests) — scopes, API keys, runtime, audit, idempotencia.
- `/app/revix_mcp/tests/test_tools_readonly.py` (22 tests) — las 8 tools con fixtures seed limpiables (prefijo `test_mcp_`).
- Ejecutar: `/app/revix_mcp/.venv/bin/pytest /app/revix_mcp/tests/ -v`
- Verificación transversal: ninguna tool filtra clave Mongo `_id` en sus respuestas.

### Próximo paso
- P1: Rate limiting por API key en `runtime.py` (límite `rate_limit_per_min` por (agent_id, minuto)).
- P0: Panel de observabilidad MCP en el CRM (`/crm/agentes-mcp`) — visualizar audit_logs filtrables + botón pausar agente.
- P1: Fase 2 MCP — agentes de escritura supervisada + 16 tools de escritura.

## Latest — 2026-04-20 (2)

### Fase 1 MCP · Fundación completada
- Servidor MCP aislado en `/app/revix_mcp/` (venv propio, sin contaminar backend).
- Arquitectura: `config.py` · `scopes.py` · `auth.py` · `audit.py` · `runtime.py` · `server.py` · `cli.py` · `tools/_registry.py` · `tools/meta.py (ping)`.
- **Auth**: API keys `revix_mcp_*` almacenadas hasheadas en `mcp_api_keys`, una key por agente.
- **Scopes**: catálogo 24 scopes + 10 perfiles preconfigurados (AGENT_PROFILES) + regla `*:read` para KPI/Auditor.
- **Audit log**: cada tool call → `audit_logs` con source=`mcp_agent`, params sanitizados, duration_ms, error, idempotency_key.
- **Idempotencia**: tools de escritura aceptan `_idempotency_key` → cache en `mcp_idempotency`.
- **Sandbox**: `MCP_ENV=preview` + tool flag `sandbox_skip` bloquea side effects peligrosos.
- **CLI**: `create/list/revoke` API keys.
- **Tests**: 19 unitarios + smoke test stdio end-to-end funcional.

### Fase 0 completada previamente
- 5 órdenes migradas (tecnico_asignado email → UUID), 87 tokens de seguimiento generados, preview ampliado, Resumen Financiero alineado con backend.

## Latest — 2026-04-18

### Rediseño completo de la web pública (Apple Care style)
- 10 páginas públicas rediseñadas: Home, Servicios, Presupuesto, Contacto, Aseguradoras, Partners, Garantía, Garantía Extendida, FAQs, Consulta (Seguimiento).
- Nueva página `/marca` con descarga de logos (SVG vectorizado + PNG 2048px + versión dark + isologo para favicons).
- Assets generados: `revix-logo.svg/png`, `revix-logo-dark.svg/png`, `revix-isologo.svg/png` en `/app/frontend/public/brand/`.
- Sistema de primitives UI compartido (`components/public/ui.jsx`) + componente `Logo.jsx` tipográfico.
- Layout público nuevo con glassmorphism header, footer limpio de 4 columnas.
- Paleta: #0055FF brand, #111111 texto, #F5F5F7 fondos sutiles.
- Tipografía: Plus Jakarta Sans 800 headings + Inter body.
- Motion: framer-motion fade-up on scroll.
- Todas las funcionalidades preservadas: formularios de contacto/presupuesto, portal `/consulta`, chatbot flotante, login de CRM.

### Branding dinámico título/favicon
- Hook `useBrandingByRoute.js`: rutas públicas muestran "Revix.es" + favicon "R" azul.
- Rutas CRM (/crm, /login...) muestran "NEXORA - CRM/ERP" + favicon Nexora.

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

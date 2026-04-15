# Revix CRM/ERP - Product Requirements Document

## Original Problem Statement
Sistema CRM/ERP para taller de reparacion de telefonia movil (Revix.es). Incluye gestion de ordenes, clientes, inventario, facturacion, integracion con aseguradoras (Insurama/Sumbroker), logistica (GLS), portal publico de seguimiento, e impresion centralizada de etiquetas Brother QL-800.

## Tech Stack
- **Frontend**: React 18, Tailwind CSS, Shadcn/UI, Framer Motion, JsBarcode
- **Backend**: FastAPI, Motor (async MongoDB), BeautifulSoup4
- **Database**: MongoDB Atlas (production)
- **Storage**: Cloudinary
- **Email**: Resend
- **Logistics**: GLS API
- **AI/LLM**: Gemini 2.5 Flash (Emergent LLM Key)
- **Label Printing**: Agente local Windows (Flask + Pillow + python-barcode + pywin32) con cola MongoDB

---

## What's Been Implemented (Latest First)

### 2026-04-15 - Sistema Centralizado de Impresion Brother QL-800
- **Arquitectura**: Cola de impresion en MongoDB. Cualquier sesion del CRM envia trabajos al backend; agente del taller hace polling y imprime.
- **Backend endpoints**:
  - `POST /api/print/send` — Crea job en cola (JWT auth, registra usuario)
  - `GET /api/print/status` — Estado agente/impresora (JWT auth)
  - `GET /api/print/jobs` — Historial de impresiones (JWT auth)
  - `GET /api/print/job/{id}` — Estado de un job concreto (JWT auth)
  - `GET /api/print/pending` — Agente consulta trabajos pendientes (agent_key)
  - `POST /api/print/complete` — Agente reporta resultado (X-Agent-Key)
  - `POST /api/print/heartbeat` — Agente envia estado periodico (X-Agent-Key)
  - `GET /api/print/agent/download` — Descarga ZIP del agente
- **MongoDB colecciones**: `print_jobs` (cola), `print_agents` (heartbeat)
- **Agente v2.0.0**: Polling cada 3s + heartbeat cada 10s + servidor HTTP local fallback
- **Frontend**: BrotherPrintButton con estado en tiempo real, boton descarga, job polling
- **Seguridad**: JWT para frontend, agent_key para agente, registro completo en MongoDB
- **Sin dependencia de localhost**: funciona desde cualquier dispositivo con sesion CRM
- **Testing**: 100% (iteration_14.json) — 21 backend + 13 frontend

### 2026-04-15 - Migracion QR a Codigos de Barras Code128
- Reemplazo completo react-qr-code por jsbarcode
- Nuevo EtiquetaInventario con vista previa
- Testing: 100% (iteration_12.json)

### 2026-04-13 - Multiples Mejoras y Correcciones
- Refrescar datos Insurama, fix /crm/crm, metricas corregidas
- QC Checklist PDF, flujo garantias, paginacion, branding eliminado
- IA diagnosticos, fix pantalla blanca, paginacion Contabilidad/Insurama

---

## Prioritized Backlog

### P1
- [ ] Sistema solicitud cambio de estado (Admin -> Master)

### P2
- [ ] Google Business Profile + Gemini Flash
- [ ] Flujo gestion de incidencias
- [ ] Acortar SKUs inventario

### P3
- [ ] Refactorizar server.py

---

## Key Files
- `/app/backend/routes/print_routes.py` — Cola centralizada de impresion
- `/app/brother-label-agent/` — Agente Windows completo (8 archivos)
- `/app/frontend/src/components/BrotherPrintButton.jsx` — Boton impresion directa
- `/app/frontend/src/components/EtiquetaInventario.jsx` — Etiqueta inventario con Brother

## Credentials
- `master@revix.es` / `RevixMaster2026!`
- Agent key: `revix-brother-agent-2026-key`

## Critical Notes
- **Base de datos**: Solo MongoDB Atlas (revix.d7soggd.mongodb.net/production)
- **DK-11204**: 17x54mm, 638x201px @300 DPI
- **Agent key**: Debe coincidir en backend .env y agent config.json
- **Heartbeat**: 30s timeout — agente se marca offline si no envia heartbeat

## 3rd Party Integrations
- Emergent LLM Key (Gemini 2.5 Flash)
- Cloudinary, Resend, GLS, Sumbroker API
- JsBarcode, python-barcode + Pillow + pywin32 (agente Brother)

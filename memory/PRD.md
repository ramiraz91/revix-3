# Revix CRM/ERP - PRD (Product Requirements Document)

## Original Problem Statement
Importar código desde repositorio GitHub (ramiraz91/revix) - CRM/ERP para taller de reparaciones con FastAPI + MongoDB backend y React frontend. Configurar DB_NAME=production, crear usuarios de acceso y preparar para deploy.

## Architecture
- **Backend**: FastAPI (Python) running on port 8001
- **Frontend**: React with TailwindCSS + ShadCN UI
- **Database**: MongoDB (DB_NAME: production)
- **AI**: Gemini via Emergent LLM Key (emergentintegrations)
- **Email**: SMTP (mail.privateemail.com)
- **Domain**: revix.es

## What's Been Implemented

### Session 1 - Initial Import
- [x] Code imported from GitHub (ramiraz91/revix)
- [x] DB configured as 'production', 3 users created
- [x] All services running

### Session 2 - Bug Fixes
- [x] Legacy URL redirects (/ordenes/nueva → /crm/ordenes/nueva)

### Session 3 - Insurama Improvements
- [x] Timeouts 120s→180s backend, 200s frontend
- [x] Retry + re-authentication (MAX_RETRIES=2)
- [x] Fixed competitor prices bug
- [x] Added reserve_value, claim_real_value, margin badges
- [x] Winner badges, price difference, improved competitor view

### Session 4 - Performance: MongoDB Cache System
- [x] **Cache presupuestos**: First load from Sumbroker (35-57s), subsequent loads from MongoDB cache (0.1s)
- [x] **Cache competidores**: First load (42s), cached (0.2s)
- [x] **Background sync**: Stale cache triggers background refresh without blocking UI
- [x] **Fallback**: If Sumbroker is down, serves stale cache
- [x] **Pre-warm endpoint**: POST /api/insurama/sync forces background refresh
- [x] Cache TTL: 10 minutes
- [x] Credenciales Sumbroker: servicios@revix.es (conexion_ok=True, 674 presupuestos)

### Session 4 - Email Config Fix
- [x] Fixed plantilla reset not resetting `asunto` field

### Session 5 - Bug Fixes (12 Mar 2026)
- [x] **Bug 1 - Subestados para técnico**: Añadido componente `OrdenSubestadoCard` a la vista del técnico (`OrdenTecnico.jsx`) para que pueda cambiar subestados como "Esperando repuestos", igual que el admin
- [x] **Bug 2 - Fotos del técnico no visibles al admin**: Modificado `todasLasFotos` en `OrdenDetalle.jsx` para incluir `fotos_antes` y `fotos_despues` que sube el técnico. Ahora el admin puede ver todas las fotos categorizadas
- [x] **UX - Carga múltiple de fotos**: Añadido atributo `multiple` a todos los inputs de archivo para permitir subir varias fotos a la vez
- [x] **UX - Tab persistente**: Los tabs de la orden ahora mantienen su posición después de actualizar datos (añadir materiales, subir fotos, etc.)

## Prioritized Backlog
### P1 (High)
- Configure SMTP password for real email sending
- GLS API real integration

### P2 (Medium)  
- Auto-refresh scheduler (cron job every 10 min)
- WebSocket notifications
- Full ISO 9001 module testing

## Next Tasks
1. Deploy updated code to production
2. Test Insurama page on revix.es after deploy
3. Configure SMTP password

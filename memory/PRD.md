# Revix CRM/ERP - PRD (Product Requirements Document)

## Original Problem Statement
Importar código desde repositorio GitHub (ramiraz91/revix) - CRM/ERP para taller de reparaciones con FastAPI + MongoDB backend y React frontend. Configurar DB_NAME=production, crear usuarios de acceso y preparar para deploy.

## Architecture
- **Backend**: FastAPI (Python) running on port 8001
- **Frontend**: React with TailwindCSS + ShadCN UI
- **Database**: MongoDB (DB_NAME: production)
- **AI**: Gemini via Emergent LLM Key (emergentintegrations)
- **Email**: SMTP (mail.privateemail.com)
- **Domain**: revix.es (to be connected post-deploy)

## User Personas
1. **Master (ramiraz91@gmail.com)**: Full system access, ISO management, analytics, configuration
2. **Admin (admin@techrepair.local)**: Order management, clients, inventory, operations
3. **Tecnico (tecnico@techrepair.local)**: Repair work orders, diagnostics, material requests

## What's Been Implemented

### Session 1 (Jan 2026) - Initial Import
- [x] Code imported from GitHub repository
- [x] Database configured as 'production'
- [x] 3 users created (master, admin, tecnico)
- [x] Backend running with all routes
- [x] Frontend compiled and serving
- [x] AI integration (Gemini via Emergent LLM Key)
- [x] SMTP email service configured

### Session 2 - Bug Fixes
- [x] Fixed legacy URL redirects (/ordenes/nueva → /crm/ordenes/nueva etc.)

### Session 3 - Insurama/Sumbroker Improvements
- [x] Increased all Sumbroker API timeouts (120s → 180s backend, 200s frontend)
- [x] Added retry with re-authentication (MAX_RETRIES=2) on auth failures and timeouts
- [x] Created API_SLOW axios instance for Insurama/Sumbroker calls
- [x] Fixed competitor prices bug (httpx direct calls → scraper with retry)
- [x] Added `get_claim_store_budgets()` method to scraper
- [x] Removed all direct httpx calls to Sumbroker API from routes
- [x] Added `reserve_value` (max claim amount) to budget listings and search
- [x] Added `claim_real_value`, `product_name`, `internal_status_text`, `external_status_text` to API responses
- [x] Added `device_purchase_date`, `device_purchase_price` to budget details
- [x] Updated InsuramaPresupuestosTable: shows reserve_value column with margin badge
- [x] Updated InsuramaDetalleTab: reserve_value banner, policy number, repair type, warranty type, purchase info
- [x] Updated competitor view: winner badge, price difference badges, improved layout
- [x] Updated search results: reserve_value display, product info, internal states

## Prioritized Backlog
### P0 (Critical)
- [x] All above completed

### P1 (High)
- Configure correct Sumbroker credentials (current ones are invalid)
- Configure custom domain revix.es after deploy
- Set up SMTP password for email sending

### P2 (Medium)
- GLS API real integration (currently UI only, no API connection)
- WebSocket notifications setup
- Full ISO 9001 module testing
- Status history endpoint integration

## Next Tasks
1. Fix Sumbroker credentials to enable full Insurama functionality
2. Deploy to Emergent production
3. Connect revix.es domain
4. GLS integration if needed

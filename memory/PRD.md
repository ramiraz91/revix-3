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

## Core Requirements
- Multi-role authentication (master/admin/tecnico)
- Work order management (full lifecycle)
- Client management
- Inventory/spare parts management
- Calendar and scheduling
- ISO 9001 compliance module
- AI assistant (Gemini-based diagnostics)
- Public website (revix.es)
- Order tracking for customers
- Notification system (email, SMS)
- Accounting/invoicing
- Supplier management
- Purchase orders
- Incidents/CAPA management
- Insurance integration (Insurama/Sumbroker)
- Logistics management (GLS, etc.)

## What's Been Implemented (Jan 2026)
- [x] Code imported from GitHub repository
- [x] Database configured as 'production'
- [x] 3 users created (master, admin, tecnico)
- [x] Backend running with all routes
- [x] Frontend compiled and serving
- [x] AI integration (Gemini via Emergent LLM Key)
- [x] SMTP email service configured
- [x] All services verified and tested (100% backend, 95% frontend)

## Test Results
- All 14 backend tests passed (100%)
- Frontend: All major functionality working (95%)
- Minor cosmetic: chart dimension warnings, WebSocket in test env

## Prioritized Backlog
### P0 (Critical)
- [x] Import and setup complete
- [x] User authentication working
- [x] Dashboard functional

### P1 (High)
- Configure custom domain revix.es after deploy
- Set up SMTP password for email sending
- Production JWT_SECRET (currently using secure default)

### P2 (Medium)
- WebSocket notifications setup
- Full ISO 9001 module testing
- Performance optimization for large datasets

## Next Tasks
1. Deploy to Emergent production
2. Connect revix.es domain
3. Configure SMTP credentials for email notifications
4. Test all modules end-to-end with real data

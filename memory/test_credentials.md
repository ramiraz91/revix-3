# Test Credentials — Revix CRM/ERP

## Entorno PREVIEW (BD: `revix_preview`, aislada de producción)

| Email | Password | Rol |
|---|---|---|
| master@revix.es | RevixMaster2026! | master |
| tecnico1@revix.es | Tecnico1Demo! | tecnico |
| tecnico2@revix.es | Tecnico2Demo! | tecnico |

Datos demo: 2 clientes (Ana García, Luis Martínez), 3 órdenes (OT-DEMO-001/002/003).

Re-seedear (idempotente):
```
cd /app/backend && python -m scripts.seed_preview
```

## Agent key (print agent Brother QL-800)
`revix-brother-agent-2026-key`

## Entorno PRODUCCIÓN
- BD: `production` (mismo cluster Atlas).
- NO se toca desde este entorno de desarrollo/preview.
- Credenciales reales gestionadas por el cliente.

# Revix CRM/ERP - Product Requirements Document

## Original Problem Statement
CRM/ERP para taller de reparacion de telefonia movil (Revix.es).

## Tech Stack
- Frontend: React 18, Tailwind CSS, Shadcn/UI, JsBarcode
- Backend: FastAPI, Motor (async MongoDB)
- Database: MongoDB Atlas (production)
- Label Printing: Agente Windows (Waitress + Pillow + python-barcode + pywin32)

---

## Latest — 2026-04-15

### Refactorizacion server.py: 3455 -> 988 lineas (72% reduccion)
Extraidos 7 modulos de rutas:
- `dashboard_routes.py` (698 lines): stats, metricas avanzadas, alertas, operativo, tecnico
- `master_routes.py` (1180 lines): metricas tecnicos, facturacion, ISO, analiticas, finanzas
- `ia_routes.py` (151 lines): mejorar texto, diagnosticos, consultas, historial
- `restos_routes.py` (185 lines): despiece de dispositivos
- `calendario_routes.py` (103 lines): eventos, asignacion ordenes, disponibilidad
- `notificaciones_routes.py` (136 lines): CRUD notificaciones, email config
- `config_empresa_routes.py` (83 lines): configuracion sistema y empresa

server.py ahora solo contiene: app setup, middleware, uploads, seguimiento publico, presupuestos, startup/shutdown.

### SKUs Descriptivos Cortos
- Formato `CAT-MODELO-TIPO`: BAT-IP15PM-COM, PANT-S24U-ORI
- Frontend + backend sincronizados

### Brother QL-800 Centralizado v2.1.0
- Waitress (produccion), cola serializada, servicio Windows
- Panel historial de impresiones
- Barcode con numero de autorizacion

---

## Architecture
```
/app/backend/
  server.py (988 lines) - Core: app, middleware, uploads, seguimiento, startup
  routes/
    auth_routes.py        - Autenticacion JWT
    data_routes.py        - CRUD clientes, repuestos
    ordenes_routes.py     - Ordenes de trabajo
    dashboard_routes.py   - Dashboard y metricas      [NUEVO]
    master_routes.py      - Analiticas, ISO, finanzas  [NUEVO]
    ia_routes.py          - Asistente IA               [NUEVO]
    restos_routes.py      - Despiece                   [NUEVO]
    calendario_routes.py  - Calendario                 [NUEVO]
    notificaciones_routes.py - Notificaciones          [NUEVO]
    config_empresa_routes.py - Config empresa           [NUEVO]
    print_routes.py       - Impresion Brother
    insurama_routes.py    - Aseguradoras
    + 12 mas...
```

## Backlog
- P2: Google Business Profile + Gemini Flash
- P2: Flujo gestion de incidencias

## Credentials
- master@revix.es / RevixMaster2026!
- Agent key: revix-brother-agent-2026-key

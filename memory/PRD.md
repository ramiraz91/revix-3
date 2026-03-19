# PRD - Revix CRM/ERP

## Descripción
CRM/ERP para servicio técnico de reparación de dispositivos móviles (Revix.es).

## Stack
- **Backend**: FastAPI, Python, Motor (MongoDB async), httpx (SOAP)
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **BD**: MongoDB Atlas
- **Integraciones**: GLS (SOAP), SMTP, Gemini, Cloudinary

## Arquitectura GLS (Reescritura completa)
```
/app/backend/modules/gls/
├── __init__.py
├── models.py            # Pydantic models, entity types, label formats
├── state_mapper.py      # 22 estados envíos, 12 recogidas, 57+ incidencias, mapper central
├── soap_client.py       # SOAP 1.2 directo (GrabaServicios, EtiquetaEnvioV2, GetExp, GetExpCli)
├── shipment_service.py  # Lógica de negocio: crear, etiquetar, tracking, sync, cancelar
├── sync_service.py      # Background polling scheduler
└── routes.py            # FastAPI endpoints (config, CRUD envíos, etiquetas, tracking, sync, maestros, logs)

/app/frontend/src/
├── pages/GLSConfigPage.jsx  # Configuración completa GLS
├── pages/GLSAdmin.jsx       # Panel admin: listado, búsqueda, detalle, acciones
├── pages/EtiquetasEnvio.jsx # Búsqueda y reimpresión de etiquetas
└── components/orden/GLSLogistica.jsx  # Crear envíos/recogidas desde orden
```

## BD GLS (Collections)
- `gls_shipments` - Envíos/recogidas con 30+ campos (tracking, POD, incidencias, raw SOAP)
- `gls_tracking_events` - Historial cronológico de eventos por envío
- `gls_logs` - Logs de cada operación SOAP

## Funcionalidades Completadas
- Auth y roles (master/admin/tecnico)
- Órdenes de trabajo con flujo de estados
- Clientes, Inventario, Dashboard, Analíticas
- Integración Insurama (poller, deduplicación)
- Email SMTP configurable + modo demo
- Scanner auto-detección (primera vez=recibir, resto=buscar)
- IMEI dual con discriminación (separados por //)
- Master puede forzar Validación/Envío desde cualquier estado
- Selector de transportista en Nueva Orden (GLS/MRW/SEUR/Manual)
- **GLS completa (reescritura):**
  - Config UI (UID, remitente, servicios, horarios, polling, etiquetas)
  - Crear envíos/recogidas via SOAP directo
  - Etiquetas PDF/PNG/JPG/EPL/DPL (descarga, reimpresión)
  - Tracking completo con eventos, incidencias, POD
  - Sync batch manual + automático (scheduler)
  - Panel admin con listado, búsqueda, filtros, detalle modal
  - Mapeo central de 22 estados GLS → 14 estados internos
  - Anulación de envíos
  - Logs de integración por envío
  - Búsqueda de etiquetas por fecha/referencia/código

## Pendiente
- Credenciales GLS de producción (UI lista para configurar)

## Backlog
- P1: Validar GLS con credenciales reales
- P2: Google Business Profile + Gemini Flash
- P2: Flujo de incidencias
- P2: Acortar SKU inventario

## Credenciales Test
- master@techrepair.local / master123
- SMTP: notificaciones@revix.es / RDdQn_GMmR6;%FJ

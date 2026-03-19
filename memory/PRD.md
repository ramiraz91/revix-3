# PRD - Revix CRM/ERP

## Descripcion
CRM/ERP para servicio tecnico de reparacion de dispositivos moviles (Revix.es).

## Stack
- **Backend**: FastAPI, Python, Motor (MongoDB async), httpx (SOAP)
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **BD**: MongoDB Atlas
- **Integraciones**: GLS (SOAP), SMTP, Gemini, Cloudinary

## Arquitectura GLS (Integracion Profunda v3)
```
/app/backend/modules/gls/
├── __init__.py
├── models.py            # Pydantic models, entity types, label formats
├── state_mapper.py      # 22 estados envios, 12 recogidas, 57+ incidencias, mapper central
├── soap_client.py       # SOAP 1.2 directo (GrabaServicios, EtiquetaEnvioV2, GetExp, GetExpCli)
├── shipment_service.py  # Logica de negocio: crear, etiquetar, tracking, sync, cancelar
├── sync_service.py      # Background polling scheduler
└── routes.py            # FastAPI endpoints (config, CRUD envios, etiquetas, tracking, sync, maestros, logs)

/app/backend/routes/ordenes_routes.py  # Endpoints de logistica integrados en la OT:
  - GET  /api/ordenes/{id}/logistics
  - POST /api/ordenes/{id}/logistics/pickup
  - POST /api/ordenes/{id}/logistics/delivery
  - POST /api/ordenes/{id}/logistics/{shipment_id}/sync
  - GET  /api/ordenes/{id}/logistics/{shipment_id}/label

/app/frontend/src/
├── pages/GLSConfigPage.jsx  # Configuracion completa GLS
├── pages/GLSAdmin.jsx       # Panel admin: listado, busqueda, detalle, acciones
├── pages/EtiquetasEnvio.jsx # Busqueda y reimpresion de etiquetas
└── components/orden/
    ├── GLSLogistica.jsx     # Panel logistica integrado en OT: 2 bloques (Recogida/Envio)
    ├── OrdenHistorialEstados.jsx  # Timeline con soporte para eventos de logistica
    └── GenerarEnvioModal.jsx      # Modal de creacion con datos pre-rellenados
```

## BD GLS (Collections)
- `gls_shipments` - Envios/recogidas con 30+ campos (tracking, POD, incidencias, raw SOAP)
- `gls_tracking_events` - Historial cronologico de eventos por envio
- `gls_logs` - Logs de cada operacion SOAP

## Flujo de Logistica en la OT
1. **Recogida**: Disponible en estados pendiente_recibir, recibida, cuarentena, en_taller (master puede en cualquier estado)
2. **Envio**: Disponible en estados reparado, validacion, enviado (master puede en cualquier estado)
3. Cada creacion registra un evento en historial_estados de la orden (tipo: "logistica")
4. Emails automaticos al cliente al crear recogida o envio con codigo de seguimiento
5. Portal publico (Seguimiento) muestra datos separados de recogida y envio con enlaces GLS
6. Sincronizacion automatica de tracking con registro de cambios de estado

## Funcionalidades Completadas
- Auth y roles (master/admin/tecnico)
- Ordenes de trabajo con flujo de estados
- Clientes, Inventario, Dashboard, Analiticas
- Integracion Insurama (poller, deduplicacion)
- Email SMTP configurable + modo demo
- Scanner auto-deteccion (primera vez=recibir, resto=buscar)
- IMEI dual con discriminacion (separados por //)
- Master puede forzar Validacion/Envio desde cualquier estado
- Selector de transportista en Nueva Orden (GLS/MRW/SEUR/Manual)
- **GLS Integracion Profunda v3:**
  - Config UI (UID, remitente, servicios, horarios, polling, etiquetas)
  - Crear envios/recogidas via SOAP directo
  - Etiquetas PDF/PNG/JPG/EPL/DPL (descarga, reimpresion)
  - Tracking completo con eventos, incidencias, POD
  - Sync batch manual + automatico (scheduler)
  - Panel admin con listado, busqueda, filtros, detalle modal
  - Mapeo central de 22 estados GLS → 14 estados internos
  - Anulacion de envios
  - Logs de integracion por envio
  - Busqueda de etiquetas por fecha/referencia/codigo
  - **NUEVO: Integracion profunda en OT** (endpoints dedicados, 2 bloques separados, timeline, emails, portal cliente)

## Pendiente
- Credenciales GLS de produccion (UI lista para configurar)

## Backlog
- P1: Validar GLS con credenciales reales
- P2: Checklist QC no se muestra en impresion de la orden
- P2: Endpoint /api/dashboard/stats lento
- P2: Google Business Profile + Gemini Flash
- P2: Flujo de incidencias
- P2: Acortar SKU inventario

## Credenciales Test
- master@techrepair.local / master123
- SMTP: notificaciones@revix.es / RDdQn_GMmR6;%FJ

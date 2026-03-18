# PRD - Revix CRM/ERP

## Descripción del Producto
CRM/ERP para servicio técnico de reparación de dispositivos móviles (Revix.es). Backend FastAPI, Frontend React, MongoDB Atlas.

## Stack Técnico
- **Backend**: FastAPI, Python, Motor (MongoDB async)
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **BD**: MongoDB Atlas
- **Integraciones**: SOAP (GLS), SMTP, Gemini, Cloudinary

## Arquitectura de Archivos
```
/app/backend/
  ├── routes/gls_routes.py         # Rutas GLS completas
  ├── services/
  │   ├── gls_soap_client.py       # Cliente SOAP GLS
  │   ├── gls_state_mapper.py      # Mapeador de estados GLS
  │   ├── gls_sync_scheduler.py    # Polling en background
  │   ├── email_service.py         # Servicio SMTP
  │   └── cloudinary_service.py    # Almacenamiento imágenes
  ├── server.py                    # App principal FastAPI
  └── config.py                    # Configuración

/app/frontend/src/
  ├── pages/
  │   ├── GLSConfig.jsx            # Configuración GLS
  │   ├── EtiquetasEnvio.jsx       # Etiquetas (GLS + manuales)
  │   └── Logistica.jsx            # Control logística general
  └── components/orden/
      └── GLSLogistica.jsx         # GLS en detalle de orden
```

## Usuarios del Sistema
- master@techrepair.local / master123
- admin@techrepair.local / Admin2026!
- tecnico@techrepair.local / Tecnico2026!

## Estado de Funcionalidades

### Completado
- Sistema de autenticación y roles (master/admin/tecnico)
- Órdenes de trabajo completas con flujo de estados
- Clientes y gestión CRM
- Inventario con SKUs
- Dashboard y analíticas
- Notificaciones en tiempo real
- Integración Insurama (poller, deduplicación)
- Sistema de email SMTP (configurable, modo demo)
- Descarga de fotos ZIP (antes/después)
- Integración GLS completa (config, envíos, etiquetas, tracking, sync, admin)
- Scanner simplificado: auto-detección primera vez=recibir, resto=buscar (sin dropdown)
- Soporte IMEI dual: discriminación de IMEIs separados por //, selección en validación
  - Configuración UI (UID, remitente, servicios, polling)
  - Creación de envíos y recogidas via SOAP
  - Generación y descarga de etiquetas (PDF/PNG/ZPL)
  - Tracking y consulta de estados
  - Sincronización batch manual y automática (scheduler)
  - Panel admin con listado y búsqueda de envíos
  - Búsqueda de etiquetas por fecha/referencia
  - Email automático con etiqueta en recogidas
  - Mapeo de estados GLS → estados internos
  - Anulación de envíos
  - Reintento de envíos fallidos
  - Logs de integración

### Pendiente por Credenciales
- Activación de GLS en producción (requiere uid_cliente del usuario)

## Backlog (P1/P2)
- P1: Validación con credenciales reales de GLS
- P2: Integración Google Business Profile con Gemini Flash
- P2: Refinamiento flujo de incidencias
- P2: Acortar SKU generado en inventario

## Credenciales Externas
- **SMTP**: notificaciones@revix.es / RDdQn_GMmR6;%FJ
- **GLS**: Pendiente del usuario
- **Cloudinary**: Configurado en .env

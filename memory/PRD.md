# CRM/ERP Revix - Product Requirements Document

## Original Problem Statement
Sistema CRM/ERP para taller de reparación de móviles con funcionalidades de:
- Gestión de órdenes de trabajo
- Inventario y repuestos
- Facturación y contabilidad
- Integración con Insurama (presupuestos de seguros)
- Logística con GLS
- Notificaciones automáticas (Email/WhatsApp)
- Dashboard con métricas en tiempo real

## User Personas
- **Master Admin**: Control total del sistema
- **Admin**: Gestión de órdenes y usuarios
- **Técnico**: Reparaciones y QC
- **Cliente**: Seguimiento de órdenes

## Core Requirements
- Conexión exclusiva a MongoDB Atlas (`revix.d7soggd.mongodb.net/production`)
- SMTP configurado para `mail.privateemail.com:465`
- Integración con Cloudinary para imágenes
- Integración con GLS para envíos

## Architecture
```
/app
├── backend/
│   ├── server.py (main FastAPI app)
│   ├── config.py, auth.py, models.py, helpers.py
│   ├── database.py (conexión MongoDB bloqueada)
│   ├── email_service.py (SMTP asíncrono)
│   ├── routes/ (modular routers)
│   ├── logic/ (inventory.py, orders.py, billing.py)
│   └── tests/ (test_logic.py, backend_test.py)
├── frontend/
│   └── src/components/ (React + Tailwind)
└── memory/
    └── PRD.md
```

## Key API Endpoints
- `GET /api/dashboard/stats` - Estadísticas dashboard (OPTIMIZADO)
- `GET /api/dashboard/metricas-avanzadas` - Métricas detalladas (OPTIMIZADO)
- `POST /api/insurama/presupuesto/{codigo}/importar` - Importar a CRM

## Credentials
- `master@revix.es` / `RevixMaster2026!`
- `ramiraz91@gmail.com` / `@100918Vm`

---

# CHANGELOG

## 2026-03-26
### Fixed
- **Carga Masiva IA**: Corregido parámetro `image_contents` → `file_contents` en UserMessage
- **ARIA búsqueda**: Añadida búsqueda por `numero_autorizacion` y `token_seguimiento`
- **Auditoría cambios de estado**: Ahora usa email del usuario autenticado + rol en historial_estados
- **Avería en Seguimiento**: Corregido para leer campo `daños` además de `averia`
- **Links Seguimiento**: Corregido `getUploadUrl()` para manejar objetos `{src, tipo}`

### Added
- **Chatbot público ARIA**: El chatbot de la web ahora puede consultar estado de órdenes
- Los clientes pueden preguntar por su reparación con código de seguimiento

### Changed
- **Integración Resend**: Reemplazado SMTP por Resend API (ayer)

## 2026-03-25
### Fixed
- **P0: Dashboard optimization** - Corregido `IndexError` en `/dashboard/stats` y `/metricas-avanzadas`
  - Causa: MongoDB `$count` devuelve `[]` si no hay documentos
  - Solución: Manejo seguro de listas vacías antes de acceder a `[0]`
  - Resultado: Dashboard carga en ~0.25s (antes 5s+)

### Changed
- **Integración Resend** - Reemplazado SMTP por Resend API
  - Eliminadas variables SMTP del `.env` y `config.py`
  - Actualizado `email_service.py` para usar Resend SDK
  - Email de prueba enviado exitosamente
  - Endpoint `/api/resend-config` para verificar configuración

### Previously Completed (sesión anterior)
- Módulos de lógica de negocio con Pytest tests
- Refactor de `database.py` con bloqueo de seguridad
- Refactor de `email_service.py` asíncrono
- Corrección de credenciales Master

---

# ROADMAP

## P0 (Crítico)
- [x] Optimización endpoints dashboard

## P1 (Alta Prioridad)
- [ ] Error al importar presupuesto de Insurama ("las guarda pero aparece error")
- [ ] Validar Carga Masiva IA (Insurama)

## P2 (Media Prioridad)
- [ ] Error "Error al cargar detalle" en módulo Insurama
- [ ] Checklist QC faltante en impresión de orden
- [ ] Google Business Profile + Gemini Flash integration
- [ ] Flujo de gestión de incidencias
- [ ] Acortar SKUs generados en inventario

## Backlog
- Mejoras de UI/UX
- Reportes avanzados
- Integración con más proveedores de logística

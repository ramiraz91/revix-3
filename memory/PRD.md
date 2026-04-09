# Revix CRM/ERP - Product Requirements Document

## Original Problem Statement
Sistema CRM/ERP para taller de reparación de telefonía móvil (Revix.es). Incluye gestión de órdenes de trabajo, clientes, inventario, facturación, integración con aseguradoras (Insurama/Sumbroker), logística (GLS), y portal público de seguimiento.

## User Personas
- **Master/Admin**: Gestión completa del sistema, analíticas, configuración
- **Técnicos**: Gestión de órdenes, reparaciones, inventario
- **Clientes públicos**: Seguimiento de reparaciones, solicitud de presupuestos

## Core Requirements
- Conexión EXCLUSIVA a MongoDB Atlas (`revix.d7soggd.mongodb.net`, base de datos: `production`)
- Autenticación JWT segura con bloqueo temporal por intentos fallidos
- Integración con portal de aseguradoras (Sumbroker API)
- Sistema de logística con GLS
- Portal público de seguimiento de reparaciones
- Sistema de emails transaccionales (Resend)
- Almacenamiento de imágenes en Cloudinary

## Tech Stack
- **Frontend**: React 18, Tailwind CSS, Shadcn/UI, Framer Motion
- **Backend**: FastAPI, Motor (async MongoDB), BeautifulSoup4
- **Database**: MongoDB Atlas (production)
- **Storage**: Cloudinary (imágenes)
- **Email**: Resend
- **Logistics**: GLS API
- **AI/LLM**: Gemini 2.5 Flash (vía Emergent LLM Key)

---

## What's Been Implemented (Latest First)

### 2026-04-09 - Dashboard y Permisos de Técnico
- **Dashboard específico para técnicos**: "Mi Panel de Técnico" con KPIs personales (asignadas, reparadas 30 días, tiempo promedio)
- **Menú lateral restringido**: Técnicos solo ven Dashboard, Órdenes de Trabajo, Escáner QR, Notificaciones
- **Protección de rutas**: Técnicos no pueden acceder a Nuevas Órdenes, Clientes, Envíos, Calendario, Incidencias
- **Endpoint `/dashboard/tecnico`**: Devuelve métricas personalizadas del técnico
- **Files**: `Dashboard.jsx`, `Layout.jsx`, `App.js`, `server.py`

### 2026-04-09 - Fix Mixed Content / Redirect HTTPS
- **Problema**: FastAPI hacía redirect 307 a HTTP causando bloqueo de peticiones
- **Solución**: Middleware `HTTPSRedirectMiddleware` que fuerza HTTPS en redirects
- **Doble decorador**: `@router.get("")` y `@router.get("/")` en rutas problemáticas
- **Files**: `server.py`, `compras_routes.py`, `nuevas_ordenes_routes.py`

### 2026-04-07 - Dashboard Operativo Rediseñado
- **Nuevo Dashboard**: Totalmente rediseñado con métricas operativas reales (Total Órdenes, Enviados, En Taller, Por Recibir, Reparados, Con Demora, Garantías, Cambios Hoy/Ayer)
- **Tarjetas Clicables**: Las tarjetas de KPIs ahora navegan directamente a vistas filtradas (`/crm/ordenes?estado=X`)
- **Desglose En Taller**: Visualización de subestados (Recibidas, En Reparación, Re-presupuestar, Validación)
- **Órdenes con Demora**: Lista de órdenes con más de 4 días sin movimiento
- **Gráfico Semanal**: Visualización de órdenes de la semana con Recharts
- **Métricas de Tiempo**: Promedio de días/horas de reparación
- **Fix**: Corregido `</div>` extra que rompía el layout
- **Files**: `Dashboard.jsx`, `server.py`

### 2026-04-07 - Eliminación Catálogo Proveedores
- **Eliminado**: Toda la arquitectura de scrapers de proveedores a petición del usuario
- **Razón**: El usuario no necesita esta funcionalidad y causaba confusión en la base de datos

### 2026-04-07 - Fix: Gestión de Compras con IA
- **Issue**: Error `float() argument must be a string or a real number, not 'NoneType'` al procesar facturas con IA
- **Causa**: Gemini devolvía `null` para campos numéricos y `float(None)` fallaba
- **Solución**: Funciones `safe_float()` y `safe_int()` para conversiones seguras
- **Adicional**: Corregida ruta `/compras` que no estaba registrada (ahora `/crm/compras`)
- **Files**: `compras_routes.py`, `App.js`, `Layout.jsx`

### 2026-04-07 - Fotos Cloudinary + Analíticas + Métricas Insurama
- **Fotos del Portal a Cloudinary**: Las fotos descargadas del portal de aseguradoras ahora se suben automáticamente a Cloudinary
- **Analíticas con Fechas Personalizadas**: Selector de período con DatePicker personalizado
- **Métricas Insurama con Filtros e Informes**: Filtros por período + botón "Generar Informe" (CSV)
- **Files**: `cloudinary_service.py`, `scraper.py`, `insurama_routes.py`, `processor.py`, `server.py`, `Seguimiento.jsx`, `Analiticas.jsx`, `InteligenciaDashboard.jsx`, `inteligencia_precios_routes.py`

### 2026-04-06 - Fix: Fotos en Seguimiento Público
- Backend consolida todas las fuentes de fotos
- Frontend maneja errores de carga (oculta imágenes que no existen)

### 2026-04-05 - Formulario Público de Presupuesto Ampliado
- Añadidos campos: DNI, dirección, código postal, ciudad, provincia, "¿cómo nos conociste?"
- Fix de pérdida de foco en inputs

### 2026-04-04 - Sistema de Scrapers de Proveedores (En Progreso)
- Arquitectura base creada en `/backend/providers/`
- **Estado**: Esqueleto funcional, falta implementación real de extracción

---

## Prioritized Backlog

### P0 - Crítico
- [ ] Error 520 en Producción (Deploy) - Requiere que el usuario presione "Deploy" en el panel de Emergent

### P1 - Alto
- [ ] Validar importación de órdenes Insurama con nueva lógica de Cloudinary

### P2 - Medio
- [ ] El checklist de control de calidad (QC) no se muestra en la impresión final de la orden (`OrdenDetalle.jsx`)
- [ ] Google Business Profile + Gemini Flash integration
- [ ] Flujo de gestión de incidencias
- [ ] Acortar SKUs generados en inventario

### P3 - Bajo
- [ ] Refactorizar server.py (mover rutas a routers específicos)

---

## Key API Endpoints
- `POST /api/compras/analizar-factura` - Sube factura PDF y extrae datos con IA (CORREGIDO)
- `POST /api/compras/confirmar` - Confirma compra y crea materiales en inventario (CORREGIDO)
- `POST /api/seguimiento/verificar` - Verificar seguimiento público
- `GET /api/master/finanzas?periodo=X&fecha_inicio=Y&fecha_fin=Z` - Analíticas financieras
- `GET /api/inteligencia-precios/dashboard?periodo=X` - Dashboard Insurama con filtros

## Key Files
- `/app/backend/routes/compras_routes.py` - Gestión de compras con IA
- `/app/backend/server.py` - Servidor principal FastAPI
- `/app/backend/database.py` - Conexión MongoDB (con fallback seguro)
- `/app/backend/services/cloudinary_service.py` - Servicio de subida de imágenes
- `/app/frontend/src/pages/Compras.jsx` - UI de gestión de compras
- `/app/frontend/src/components/Layout.jsx` - Navegación del CRM

## Credentials (Test)
- `master@revix.es` / `RevixMaster2026!`

## Critical Notes
- **NO modificar conexión a base de datos** - El fallback de seguridad en `database.py` fuerza Atlas
- **NO hacer commit de .env** - Usar System Keys en panel de Emergent
- **Bloqueos temporales en memoria** - Reiniciar backend si hay "Demasiados intentos"
- **Fotos del portal** - Ahora se suben a Cloudinary automáticamente
- **Gestión de Compras** - Usa funciones `safe_float/safe_int` para evitar errores de conversión

## 3rd Party Integrations
- Emergent LLM Key (Gemini 2.5 Flash para extracción de facturas)
- Cloudinary (almacenamiento de imágenes)
- Resend (emails transaccionales)
- GLS (logística)
- Sumbroker API (portal aseguradoras)

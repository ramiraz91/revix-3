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

---

## What's Been Implemented (Latest First)

### 2026-04-07 - Fotos Cloudinary + Analíticas + Métricas Insurama
- **Fotos del Portal a Cloudinary**: Las fotos descargadas del portal de aseguradoras ahora se suben automáticamente a Cloudinary en lugar de guardarse localmente. Evita pérdida de datos.
- **Analíticas con Fechas Personalizadas**: Selector de período (Semana, Mes, Trimestre, Año, Personalizado) con DatePicker
- **Métricas Insurama con Filtros e Informes**: 
  - Filtros por período en el dashboard de Insurama
  - Botón "Generar Informe" que descarga CSV con métricas completas
- **Files Modified**: 
  - `cloudinary_service.py` (nueva función `upload_bytes_to_cloudinary`)
  - `scraper.py` (ahora sube a Cloudinary)
  - `insurama_routes.py`, `processor.py` (integración Cloudinary)
  - `server.py`, `Seguimiento.jsx` (consolidación de fotos)
  - `Analiticas.jsx` (DatePicker personalizado)
  - `InteligenciaDashboard.jsx` (filtros y generación de informes)
  - `inteligencia_precios_routes.py` (parámetros de período)

### 2026-04-06 - Fix: Fotos en Seguimiento Público
- **Issue**: Las fotos no cargaban en `/web/consulta` (seguimiento de usuario)
- **Causa**: Solo se devolvía el campo `fotos` (vacío), ignorando `evidencias`, `fotos_antes`, `fotos_despues`
- **Solución**: Backend consolida todas las fuentes de fotos + manejo de errores en frontend

### 2026-04-05 - Formulario Público de Presupuesto Ampliado
- Añadidos campos: DNI, dirección, código postal, ciudad, provincia, "¿cómo nos conociste?"
- Textos legales personalizables
- Fix de pérdida de foco en inputs (componente InputField movido fuera del render)

### 2026-04-04 - Sistema de Scrapers de Proveedores (En Progreso)
- Arquitectura base creada en `/backend/providers/`
- Scrapers: Mobilax, Utopya, SpainSellers
- Frontend: `CatalogoProveedores.jsx`
- **Estado**: Esqueleto funcional, falta implementación real de extracción

### 2026-04-03 - Mejoras Dashboard Insurama
- Botón eliminar permanentemente
- Polling optimizado (4h)
- Separación SKU/Nombre en `OrdenPDF.jsx`

### 2026-04-02 - Resolución Error 520 en Producción
- Configuración correcta de System Keys (JWT_SECRET)
- Bloqueo de seguridad en `database.py` para forzar conexión a Atlas

---

## Prioritized Backlog

### P1 - Alto
- [ ] Completar implementación de Scrapers de Proveedores (lógica real de extracción BeautifulSoup)
- [ ] Polling automático semanal de precios de proveedores

### P2 - Medio
- [ ] Error al importar presupuesto de Insurama al CRM (mensaje de error tras guardar)
- [ ] Error "Error al cargar detalle" en módulo Insurama
- [ ] Google Business Profile + Gemini Flash integration
- [ ] Flujo de gestión de incidencias
- [ ] Acortar SKUs generados en inventario

### P3 - Bajo
- [ ] Refactorizar server.py (mover rutas a routers específicos)

---

## Key API Endpoints
- `POST /api/seguimiento/verificar` - Verificar seguimiento público (ACTUALIZADO - consolida fotos)
- `GET /api/master/finanzas?periodo=X&fecha_inicio=Y&fecha_fin=Z` - Analíticas financieras
- `GET /api/inteligencia-precios/dashboard?periodo=X` - Dashboard Insurama con filtros
- `GET /api/dashboard/stats` - Estadísticas del dashboard
- `GET /api/ordenes/metricas-avanzadas` - Métricas de órdenes
- `POST /api/insurama/presupuesto/{codigo}/importar` - Importar presupuesto
- `POST /api/web-publica/presupuesto` - Formulario público

## Key Files
- `/app/backend/server.py` - Servidor principal FastAPI
- `/app/backend/database.py` - Conexión MongoDB (con fallback seguro)
- `/app/backend/services/cloudinary_service.py` - Servicio de subida de imágenes
- `/app/backend/agent/scraper.py` - Scraper de Sumbroker
- `/app/backend/routes/inteligencia_precios_routes.py` - Métricas Insurama
- `/app/frontend/src/pages/Seguimiento.jsx` - Portal de seguimiento público
- `/app/frontend/src/pages/Analiticas.jsx` - Dashboard de analíticas
- `/app/frontend/src/components/insurama/InteligenciaDashboard.jsx` - Dashboard Insurama
- `/app/frontend/src/pages/public/PublicPresupuesto.jsx` - Formulario público
- `/app/backend/providers/` - Sistema de scrapers de proveedores

## Credentials (Test)
- `master@revix.es` / `RevixMaster2026!`

## Critical Notes
- **NO modificar conexión a base de datos** - El fallback de seguridad en `database.py` está diseñado para evitar errores de configuración
- **NO hacer commit de .env** - Usar System Keys en panel de Emergent
- **Bloqueos temporales en memoria** - Reiniciar backend si hay "Demasiados intentos"
- **Fotos del portal** - Ahora se suben a Cloudinary automáticamente para evitar pérdida de datos

## 3rd Party Integrations
- Emergent LLM Key (para funciones IA)
- Cloudinary (almacenamiento de imágenes)
- Resend (emails transaccionales)
- GLS (logística)
- Sumbroker API (portal aseguradoras)

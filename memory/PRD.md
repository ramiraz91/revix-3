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

### 2026-04-06 - Fix: Fotos en Seguimiento Público
- **Issue**: Las fotos no cargaban en `/web/consulta` (seguimiento de usuario)
- **Causa**: Solo se devolvía el campo `fotos` (vacío), ignorando `evidencias`, `fotos_antes`, `fotos_despues`
- **Solución**: 
  - Backend consolida todas las fuentes de fotos
  - Frontend maneja errores de carga (oculta imágenes que no existen)
- **Files**: `server.py`, `Seguimiento.jsx`

### 2026-04-05 - Formulario Público de Presupuesto Ampliado
- Añadidos campos: DNI, dirección, código postal, ciudad, provincia, "¿cómo nos conociste?"
- Textos legales personalizables
- **Pendiente**: Verificar fix de pérdida de foco en inputs

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

### P0 - Crítico
- [ ] Verificar fix de pérdida de foco en formulario público (`/presupuesto`)

### P1 - Alto
- [ ] Verificar selector de fechas en Analíticas y cálculo de Ticket Medio
- [ ] Completar implementación de Scrapers de Proveedores (lógica real de extracción)
- [ ] Polling automático semanal de precios de proveedores

### P2 - Medio
- [ ] Error al importar presupuesto de Insurama al CRM
- [ ] Error "Error al cargar detalle" en módulo Insurama
- [ ] Google Business Profile + Gemini Flash integration
- [ ] Flujo de gestión de incidencias
- [ ] Acortar SKUs generados en inventario

### P3 - Bajo
- [ ] Migrar fotos de portal (/api/uploads/) a Cloudinary
- [ ] Refactorizar server.py (mover rutas a routers específicos)

---

## Key API Endpoints
- `POST /api/seguimiento/verificar` - Verificar seguimiento público (ACTUALIZADO)
- `GET /api/dashboard/stats` - Estadísticas del dashboard
- `GET /api/ordenes/metricas-avanzadas` - Métricas de órdenes
- `POST /api/insurama/presupuesto/{codigo}/importar` - Importar presupuesto
- `POST /api/web-publica/presupuesto` - Formulario público

## Key Files
- `/app/backend/server.py` - Servidor principal FastAPI
- `/app/backend/database.py` - Conexión MongoDB (con fallback seguro)
- `/app/frontend/src/pages/Seguimiento.jsx` - Portal de seguimiento público
- `/app/frontend/src/pages/public/PublicPresupuesto.jsx` - Formulario público
- `/app/backend/providers/` - Sistema de scrapers de proveedores

## Credentials (Test)
- `master@revix.es` / `RevixMaster2026!`

## Critical Notes
- **NO modificar conexión a base de datos** - El fallback de seguridad en `database.py` está diseñado para evitar errores de configuración
- **NO hacer commit de .env** - Usar System Keys en panel de Emergent
- **Bloqueos temporales en memoria** - Reiniciar backend si hay "Demasiados intentos"

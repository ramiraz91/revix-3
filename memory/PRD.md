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

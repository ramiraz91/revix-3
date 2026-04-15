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
- **Frontend**: React 18, Tailwind CSS, Shadcn/UI, Framer Motion, JsBarcode
- **Backend**: FastAPI, Motor (async MongoDB), BeautifulSoup4
- **Database**: MongoDB Atlas (production)
- **Storage**: Cloudinary (imágenes)
- **Email**: Resend
- **Logistics**: GLS API
- **AI/LLM**: Gemini 2.5 Flash (vía Emergent LLM Key)

---

## What's Been Implemented (Latest First)

### 2026-04-15 - Migración QR → Códigos de Barras Code128 + Etiquetas Inventario
- **Reemplazo completo QR → Barcode**: Todos los códigos QR reemplazados por Code128 estándar usando `jsbarcode`
- **OrdenDetalle.jsx**: QRCode sustituido por componente `Barcode` con pistola láser compatible
- **OrdenTecnico.jsx**: QRCode sustituido por componente `Barcode`
- **OrdenPDF.jsx**: BarcodeImage con canvas → base64 → img para PDFs
- **EtiquetaOrden.jsx**: Ya usaba JsBarcode (verificado y funcional)
- **NUEVO: EtiquetaInventario.jsx**: Diálogo con vista previa, selector de 4 tamaños (29x90mm Brother, 50x30, 60x40, 70x50), selector de copias, código de barras Code128 real
- **Inventario.jsx**: printLabels actualizado de SVG falso a JsBarcode real; dropdown ahora abre modal de vista previa
- **Testing**: 100% - Todos los tests pasados (iteration_12.json)
- **Files**: `OrdenDetalle.jsx`, `OrdenTecnico.jsx`, `OrdenPDF.jsx`, `EtiquetaOrden.jsx`, `EtiquetaInventario.jsx`, `Inventario.jsx`, `Barcode.jsx`

### 2026-04-13 - Botón Refrescar Datos Insurama + Mejoras UI
- **Nuevo endpoint** `POST /api/insurama/orden/{orden_id}/refrescar`: Refresca datos desde Sumbroker
- **Panel Insurama mejorado**: Botón "Refrescar datos" con animación
- **Tarjeta Cliente mejorada**: CP + Ciudad + Provincia separados
- **Fix Bug doble /crm/crm/**: Corregido en `App.js` y `Layout.jsx`
- **Métricas Dashboard corregidas**: 100% órdenes completadas
- **QC Checklist en PDF**: Trazabilidad de baterías y notas cierre técnico
- **Flujo de garantías**: GarantiaModal + opción "Garantía no procede" en QC y PDF
- **Paginación**: Contabilidad y Presupuestos Insurama
- **Eliminación branding**: Removido de `index.html`
- **IA diagnósticos**: Solo texto técnico, sin datos de cliente
- **Fix pantalla blanca**: Mensajes del técnico (parsing JSON)

### 2026-04-09 - Dashboard y Permisos de Técnico
- Dashboard específico para técnicos con KPIs personales
- Menú lateral restringido por rol
- Protección de rutas

### 2026-04-07 - Dashboard Operativo + Gestión de Compras con IA
- Dashboard rediseñado con métricas operativas
- Tarjetas clicables a vistas filtradas
- Gestión de compras con funciones safe_float/safe_int

---

## Prioritized Backlog

### P0 - Crítico
- (Todos resueltos)

### P1 - Alto
- [ ] Sistema de solicitud de cambio de estado (Admin → Master)

### P2 - Medio
- [ ] Google Business Profile + Gemini Flash integration
- [ ] Flujo de gestión de incidencias
- [ ] Acortar SKUs generados en inventario

### P3 - Bajo
- [ ] Refactorizar server.py (mover rutas a routers específicos)

---

## Key Files
- `/app/frontend/src/components/Barcode.jsx` - Componente reutilizable de barcode
- `/app/frontend/src/components/EtiquetaOrden.jsx` - Diálogo de etiqueta para órdenes
- `/app/frontend/src/components/EtiquetaInventario.jsx` - Diálogo de etiqueta para inventario
- `/app/frontend/src/components/OrdenPDF.jsx` - PDF de orden con barcode
- `/app/frontend/src/pages/OrdenDetalle.jsx` - Detalle de orden con barcode
- `/app/frontend/src/pages/OrdenTecnico.jsx` - Vista técnico con barcode
- `/app/frontend/src/pages/Inventario.jsx` - Inventario con etiquetas Code128
- `/app/backend/server.py` - Servidor principal FastAPI

## Credentials (Test)
- `master@revix.es` / `RevixMaster2026!`

## Critical Notes
- **NO modificar conexión a base de datos** - Forzado a Atlas
- **NO hacer commit de .env** - Usar System Keys
- **Códigos de barras**: Todos los QR han sido eliminados. Usar componente `Barcode` o `JsBarcode` directamente
- **Fotos del portal** - Se suben a Cloudinary automáticamente

## 3rd Party Integrations
- Emergent LLM Key (Gemini 2.5 Flash)
- Cloudinary (imágenes)
- Resend (emails)
- GLS (logística)
- Sumbroker API (aseguradoras)
- JsBarcode (códigos de barras Code128)

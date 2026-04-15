# Revix CRM/ERP - Product Requirements Document

## Original Problem Statement
Sistema CRM/ERP para taller de reparacion de telefonia movil (Revix.es). Incluye gestion de ordenes de trabajo, clientes, inventario, facturacion, integracion con aseguradoras (Insurama/Sumbroker), logistica (GLS), y portal publico de seguimiento.

## User Personas
- **Master/Admin**: Gestion completa del sistema, analiticas, configuracion
- **Tecnicos**: Gestion de ordenes, reparaciones, inventario
- **Clientes publicos**: Seguimiento de reparaciones, solicitud de presupuestos

## Core Requirements
- Conexion EXCLUSIVA a MongoDB Atlas (`revix.d7soggd.mongodb.net`, base de datos: `production`)
- Autenticacion JWT segura con bloqueo temporal por intentos fallidos
- Integracion con portal de aseguradoras (Sumbroker API)
- Sistema de logistica con GLS
- Portal publico de seguimiento de reparaciones
- Sistema de emails transaccionales (Resend)
- Almacenamiento de imagenes en Cloudinary
- Impresion directa de etiquetas Brother QL-800 via agente local

## Tech Stack
- **Frontend**: React 18, Tailwind CSS, Shadcn/UI, Framer Motion, JsBarcode
- **Backend**: FastAPI, Motor (async MongoDB), BeautifulSoup4
- **Database**: MongoDB Atlas (production)
- **Storage**: Cloudinary (imagenes)
- **Email**: Resend
- **Logistics**: GLS API
- **AI/LLM**: Gemini 2.5 Flash (via Emergent LLM Key)
- **Label Printing**: Agente local Windows (Flask + Pillow + python-barcode + pywin32)

---

## What's Been Implemented (Latest First)

### 2026-04-15 - Agente Local Brother QL-800 + Impresion Directa DK-11204
- **Agente local Windows** (`/app/brother-label-agent/`): Servidor Flask en `localhost:5555` para impresion directa
  - Endpoints: GET /health, GET /printers, POST /print, POST /test-print
  - Generacion de etiquetas DK-11204 (17x54mm) a 300 DPI (638x201 px)
  - Impresion via Win32 GDI (pywin32) — sin depender del navegador
  - Auto-rotacion de imagen segun orientacion del driver
  - Deteccion de estado de impresora (online/offline/error spooler)
  - Plantilla OT: Code128 barcode + numero OT + modelo dispositivo
  - Plantilla Inventario: Code128 barcode SKU + nombre producto + precio
  - Plantilla Test: Verificacion de impresora con borde y texto
  - Scripts: install.bat, start.bat, config.json
  - README.md con instrucciones completas de instalacion
- **Frontend CRM**:
  - Nuevo componente `BrotherPrintButton.jsx` con health check periodico (15s)
  - Integrado en `OrdenDetalle.jsx` (columna derecha, debajo del barcode)
  - Boton "Imprimir Etiqueta" directo (1 clic, sin dialogo del navegador)
  - Boton "Probar Impresora" secundario
  - Estado visible: conectado (verde), no detectado (rojo), error impresora (amarillo)
  - Instrucciones cuando el agente no esta corriendo
  - Integracion Brother en `EtiquetaInventario.jsx` como opcion principal
- **Backend CRM**:
  - `GET /api/print/agent/status`: Info del agente disponible
  - `GET /api/print/agent/download`: Descarga del agente como ZIP (8 archivos)
- **Justificacion tecnica**: Win32 GDI + Pillow en lugar de b-PAC porque:
  - 0 dependencias adicionales vs P-touch Editor + SDK + COM
  - Misma calidad 300 DPI
  - Mas fiable (Windows API estandar vs COM automation)
  - Mas facil de desplegar y depurar
- **Testing**: 100% (iteration_13.json) - Backend + Frontend verificados
- **Files**: `BrotherPrintButton.jsx`, `EtiquetaInventario.jsx`, `OrdenDetalle.jsx`, `print_routes.py`, `server.py`, `brother-label-agent/*`

### 2026-04-15 - Migracion QR a Codigos de Barras Code128
- Reemplazo completo de react-qr-code por jsbarcode en todo el CRM
- OrdenDetalle, OrdenTecnico, OrdenPDF actualizados con componente Barcode
- Nuevo componente EtiquetaInventario con vista previa y selector de tamano
- Inventario: printLabels actualizado de SVG falso a JsBarcode real
- Testing: 100% (iteration_12.json)

### 2026-04-13 - Multiples Mejoras y Correcciones
- Boton Refrescar Datos Insurama
- Fix doble /crm/crm/
- Metricas Dashboard corregidas (80 ordenes vs 56)
- QC Checklist en PDF con trazabilidad baterias
- Flujo de garantias (GarantiaModal + "Garantia no procede")
- Paginacion en Contabilidad y Presupuestos Insurama
- Eliminacion branding Emergent
- IA diagnosticos solo texto tecnico
- Fix pantalla blanca mensajes tecnico

---

## Prioritized Backlog

### P0 - Critico
- (Todos resueltos)

### P1 - Alto
- [ ] Sistema de solicitud de cambio de estado (Admin -> Master)

### P2 - Medio
- [ ] Google Business Profile + Gemini Flash integration
- [ ] Flujo de gestion de incidencias
- [ ] Acortar SKUs generados en inventario

### P3 - Bajo
- [ ] Refactorizar server.py (mover rutas a routers especificos)

---

## Key Files
- `/app/brother-label-agent/` - Agente local de impresion completo
- `/app/frontend/src/components/BrotherPrintButton.jsx` - Boton impresion directa
- `/app/frontend/src/components/Barcode.jsx` - Componente barcode reutilizable
- `/app/frontend/src/components/EtiquetaOrden.jsx` - Etiqueta orden (web fallback)
- `/app/frontend/src/components/EtiquetaInventario.jsx` - Etiqueta inventario
- `/app/frontend/src/components/OrdenPDF.jsx` - PDF de orden
- `/app/backend/routes/print_routes.py` - Endpoints descarga agente

## Credentials (Test)
- `master@revix.es` / `RevixMaster2026!`

## Critical Notes
- **NO modificar conexion a base de datos** - Forzado a Atlas
- **Agente Brother**: Solo funciona en Windows con pywin32. En el servidor Linux funciona en modo simulacion.
- **DK-11204**: Todo el sistema de etiquetas esta configurado para 17x54mm. No usar otros tamanos.
- **Puerto 5555**: El agente local escucha en 127.0.0.1:5555. CORS habilitado para cualquier origen.

## 3rd Party Integrations
- Emergent LLM Key (Gemini 2.5 Flash)
- Cloudinary (imagenes)
- Resend (emails)
- GLS (logistica)
- Sumbroker API (aseguradoras)
- JsBarcode (codigos de barras Code128)
- python-barcode + Pillow + pywin32 (agente local Brother)

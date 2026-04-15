# Revix CRM/ERP - Product Requirements Document

## Original Problem Statement
CRM/ERP para taller de reparacion de telefonia movil (Revix.es). Gestion de ordenes, clientes, inventario, facturacion, aseguradoras, logistica, portal publico, impresion centralizada Brother QL-800.

## Tech Stack
- Frontend: React 18, Tailwind CSS, Shadcn/UI, JsBarcode
- Backend: FastAPI, Motor (async MongoDB)
- Database: MongoDB Atlas (production)
- Label Printing: Agente Windows (Waitress + Pillow + python-barcode + pywin32)

---

## Latest — 2026-04-15

### Panel Historial de Impresiones
- Nueva pagina `/crm/historial-impresion` accesible desde menu Herramientas Admin
- KPIs: estado agente, total trabajos, impresas, errores, pendientes
- Tabla con fecha, usuario, plantilla (OT/Inventario), referencia, estado, fecha impresion
- Filtro por estado, paginacion, boton reimprimir
- Seccion de errores recientes
- Boton "Descargar Agente" y "Actualizar"

### Brother Agent v2.1.0 Produccion
- Waitress (produccion) reemplaza Flask dev server
- Cola serializada (PrintWorker), reinicio automatico, logs rotativos
- Servicio Windows (service.py), install-service.bat
- DEVMODE forzado DK-11204, barcode con numero_autorizacion
- 10 archivos en ZIP

### Barcodes con numero de autorizacion
- OrdenDetalle, OrdenTecnico, OrdenPDF, EtiquetaOrden, Brother print
- Fallback a numero_orden si no hay autorizacion

---

## Backlog
- P1: Sistema solicitud cambio de estado
- P2: Google Business Profile + Gemini Flash
- P2: Flujo gestion incidencias
- P2: Acortar SKUs inventario
- P3: Refactorizar server.py

## Credentials
- master@revix.es / RevixMaster2026!
- Agent key: revix-brother-agent-2026-key

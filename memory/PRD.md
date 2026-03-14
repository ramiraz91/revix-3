# Revix CRM/ERP - PRD (Product Requirements Document)

## Versión Actual: 1.0.0
📅 Última actualización: 2026-03-14
📋 Ver [CHANGELOG.md](/app/CHANGELOG.md) para historial completo

## Original Problem Statement
Importar código desde repositorio GitHub (ramiraz91/revix) - CRM/ERP para taller de reparaciones con FastAPI + MongoDB backend y React frontend. Configurar DB_NAME=production, crear usuarios de acceso y preparar para deploy.

## Architecture
- **Backend**: FastAPI (Python) running on port 8001
- **Frontend**: React with TailwindCSS + ShadCN UI
- **Database**: MongoDB (DB_NAME: production)
- **AI**: Gemini via Emergent LLM Key (emergentintegrations)
- **Email**: SMTP (mail.privateemail.com)
- **Images**: Cloudinary (cloud: dw0exxafh) - almacenamiento permanente
- **Domain**: revix.es

## What's Been Implemented

### Session 1 - Initial Import
- [x] Code imported from GitHub (ramiraz91/revix)
- [x] DB configured as 'production', 3 users created
- [x] All services running

### Session 2 - Bug Fixes
- [x] Legacy URL redirects (/ordenes/nueva → /crm/ordenes/nueva)

### Session 3 - Insurama Improvements
- [x] Timeouts 120s→180s backend, 200s frontend
- [x] Retry + re-authentication (MAX_RETRIES=2)
- [x] Fixed competitor prices bug
- [x] Added reserve_value, claim_real_value, margin badges
- [x] Winner badges, price difference, improved competitor view

### Session 4 - Performance: MongoDB Cache System
- [x] **Cache presupuestos**: First load from Sumbroker (35-57s), subsequent loads from MongoDB cache (0.1s)
- [x] **Cache competidores**: First load (42s), cached (0.2s)
- [x] **Background sync**: Stale cache triggers background refresh without blocking UI
- [x] **Fallback**: If Sumbroker is down, serves stale cache
- [x] **Pre-warm endpoint**: POST /api/insurama/sync forces background refresh
- [x] Cache TTL: 10 minutes
- [x] Credenciales Sumbroker: servicios@revix.es (conexion_ok=True, 674 presupuestos)

### Session 4 - Email Config Fix
- [x] Fixed plantilla reset not resetting `asunto` field

### Session 5 - Bug Fixes (12 Mar 2026)
- [x] **Bug 1 - Subestados para técnico**: Añadido componente `OrdenSubestadoCard` a la vista del técnico (`OrdenTecnico.jsx`) para que pueda cambiar subestados como "Esperando repuestos", igual que el admin
- [x] **Bug 2 - Fotos del técnico no visibles al admin**: Modificado `todasLasFotos` en `OrdenDetalle.jsx` para incluir `fotos_antes` y `fotos_despues` que sube el técnico. Ahora el admin puede ver todas las fotos categorizadas con badges ANTES/DESPUÉS
- [x] **UX - Carga múltiple de fotos**: Añadido atributo `multiple` a todos los inputs de archivo para permitir subir varias fotos a la vez
- [x] **UX - Tab persistente**: Los tabs de la orden ahora mantienen su posición después de actualizar datos (añadir materiales, subir fotos, etc.)
- [x] **Polling excesivo de notificaciones**: Reducido el polling de `PresupuestoAceptadoPopup.jsx` de 5s a 60s y `Layout.jsx` de 30s a 180s (3 minutos)
- [x] **Verificación notificaciones automáticas**: Verificado funcionamiento correcto con toggles y modo demo
- [x] **Dashboard financiero para Master**: Añadidas métricas de Total Cobrado, Total Gastos, Pendiente Cobrar y Margen de Beneficio en `/crm/analiticas`
- [x] **Dashboard Insurama mejorado**: Añadidas métricas reales del negocio (Total Órdenes, Ratio Aceptación, Ticket Medio, Ingresos, Gastos, Beneficio, estado de órdenes) + métricas de competencia
- [x] **Panel de Facturación Completo**: Nueva página de Analíticas con 3 tabs:
  - **Facturación**: Filtro por período (semana/mes/trimestre/año), total a facturar, clasificación por estado, desglose semanal, costes y beneficios
  - **Proyecciones**: Ritmo diario, proyección mensual/anual, análisis de tendencia vs período anterior
  - **Operaciones**: KPIs operativos, ingresos/órdenes por mes, distribución por estado, ranking técnicos
- [x] **Módulo de Compras con Trazabilidad**: Nueva sección `/crm/compras` con:
  - Upload de facturas PDF con extracción automática IA (Gemini)
  - Revisión y confirmación de productos antes de aplicar
  - Creación automática de inventario o actualización de stock existente
  - Sistema de trazabilidad por lote (código TRZ-AAAA-MMDD-NNN)
  - Dashboard de compras con métricas y alertas de stock bajo
- [x] **Búsqueda por código de barras**: Añadido `codigo_barras` al buscador de materiales/repuestos

## Prioritized Backlog
### P1 (High)
- Configure SMTP password for real email sending
- GLS API real integration

### P2 (Medium)  
- Auto-refresh scheduler (cron job every 10 min)
- WebSocket notifications
- Full ISO 9001 module testing

### Session 6 - Bug Fixes (13 Mar 2026)
- [x] **Error módulo compras (LlmChat)**: Corregido import de `emergentintegrations.llm.chat` usando sintaxis correcta con `LlmChat`, `UserMessage` y `FileContentWithMimeType`
- [x] **Endpoint descarga ZIP de fotos**: Creado `/api/ordenes/{id}/fotos-zip` para descargar todas las fotos de una orden en formato ZIP
- [x] **División galería de fotos (Admin)**: Las fotos ahora se organizan en secciones separadas: "ANTES", "DESPUÉS" y "OTRAS FOTOS" con bordes de colores distintivos
- [x] **Bug visualización imágenes**: Verificado funcionamiento correcto - el problema eran archivos de prueba corruptos eliminados
- [x] **Cálculos financieros automatizados**: Función `recalcular_totales_orden` que calcula presupuesto, coste y beneficio automáticamente
- [x] **Flujo de estados corregido**: Técnico → REPARADO → Admin → ENVIADO con validación QC obligatoria
- [x] **Protección de fotos**: Backend ignora intentos de borrar arrays de fotos durante actualizaciones
- [x] **Descarga ZIP sin nueva pestaña**: Corregido handler frontend para descarga directa
- [x] **Etiquetas inventario 29x90mm**: Ajustado CSS de impresión para Brother QL-800
- [x] **Mejora UX sin recarga**: TablaMaterialesEditable y TecnicoMaterialesCard usan estado local
- [x] **Consistencia analíticas**: Endpoints de finanzas usan campos calculados de órdenes

### Session 7 - Verificación P0 (13 Mar 2026)
- [x] **Código de envío se guarda correctamente**: Verificado que `codigo_recogida_salida` se almacena al finalizar orden con estado ENVIADO
- [x] **Sin fotos "durante" para técnico**: Confirmado que TecnicoFotosCard solo tiene tabs ANTES, DESPUÉS y General
- [x] **Órdenes irreparables pueden finalizarse**: Añadida transición `irreparable → enviado` para poder contabilizar dispositivos irreparables

### Session 8 - Cloudinary Integration (14 Mar 2026)
- [x] **Integración Cloudinary**: Las fotos ahora se almacenan permanentemente en Cloudinary
- [x] **Organización por carpetas**: Fotos organizadas en `revix/ordenes/{numero_orden}/{tipo}/`
- [x] **URLs persistentes**: Las URLs de Cloudinary se guardan en MongoDB y nunca se pierden
- [x] **Compatibilidad**: Frontend actualizado para manejar tanto URLs de Cloudinary como archivos locales antiguos
- [x] **Descarga ZIP**: Endpoint actualizado para descargar fotos desde Cloudinary
- [x] **Credenciales**: Cloud name: dw0exxafh

## Next Tasks
1. Probar módulo de Compras con un PDF real de factura
2. Implementar automatizaciones de Insurama (sincronización de estados)
3. Integración completa con GLS (etiquetas, recogidas, tracking)
4. Verificar envío de emails SMTP
5. Acortar SKU generado en inventario

## Completed Tasks
- ~~Deploy updated code to production~~ - En progreso
- ~~Polling excesivo de notificaciones~~ - COMPLETADO
- ~~Notificaciones automáticas~~ - COMPLETADO
- ~~Integración Gemini IA~~ - YA FUNCIONANDO
- ~~Dashboard financiero master~~ - COMPLETADO
- ~~Dashboard Insurama mejorado~~ - COMPLETADO (métricas negocio + competencia)
- ~~Error módulo compras (LlmChat)~~ - COMPLETADO
- ~~Endpoint descarga ZIP~~ - COMPLETADO
- ~~División galería de fotos~~ - COMPLETADO
- ~~Almacenamiento permanente de fotos~~ - COMPLETADO (Cloudinary)

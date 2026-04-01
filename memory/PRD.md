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

## 2026-04-01
### Fixed - Correcciones GLS (5 Prioridades)
- **P1: TRACKING_URL desde URLPARTNER**: 
  - Ya no se construye manualmente con `apptracking.asp`
  - Ahora busca evento `URLPARTNER` en `tracking_list`
  - Fallback usa URL pública oficial: `gls-spain.es/es/ayuda/seguimiento-de-envio/`
  - Nuevos campos: `tracking_source`, `urlpartner_found`

- **P2: uid_cliente NO expuesto**:
  - `GET /api/gls/config` ya NO devuelve `uid_cliente`
  - Solo devuelve `uid_masked` y `uid_configurado`

- **P3: Fallback de identificadores mejorado**:
  - Orden: `gls_uid` → `gls_codbarras` → `gls_codexp` → `referencia_interna`
  - Campo `identificador_usado` en respuesta de tracking

- **P4: Múltiples expediciones**:
  - Función `_select_correct_expedition()` identifica expedición correcta
  - Detecta retorno vs ida por campo `retorno="S"`

- **P5: Mantenido funcionamiento existente**: Cache de etiquetas, historial, eventos, sync

### Added
- **Módulo Logístico GLS Completo** - Refactorizado como sistema desacoplado y auditable:
  - **Tipos de envío**: Recogida, Envío, Devolución
  - **Prevención de duplicados**: Validación antes de crear nuevo envío del mismo tipo
  - **Almacenamiento de etiquetas**: Las etiquetas se guardan en BD para reimpresión sin llamar a GLS
  - **Notificaciones al cliente**: Emails automáticos al crear envío o cambiar estado
  - **Trazabilidad completa**: Historial de logística integrado en la orden (`historial_logistica`)
  - **Timeline de eventos**: Todos los eventos de tracking guardados en `gls_tracking_events`
  - **Auditoría**: Logs detallados de cada operación en `gls_logs`

### Changed
- **Backend** (`/app/backend/modules/gls/`):
  - `shipment_service.py`: Reescrito con validaciones, cache de etiquetas, notificaciones
  - `routes.py`: Endpoints completos para CRUD, tracking, sync, maestros
- **Frontend** (`GLSLogistica.jsx`):
  - Ahora muestra 3 bloques: Recogida, Envío, Devolución
  - Botón para crear devolución
  - Títulos dinámicos según tipo
- **API de órdenes** (`ordenes_routes.py`):
  - Nuevo endpoint `POST /ordenes/{id}/logistics/return` para devoluciones
  - Nuevo endpoint `DELETE /ordenes/{id}/logistics/{shipment_id}` para anular
  - Validación de duplicados en pickup y delivery

### API Endpoints GLS
- `GET /api/gls/status` - Estado de la integración
- `GET /api/gls/envios` - Listar envíos con filtros
- `POST /api/gls/envios` - Crear envío
- `GET /api/gls/envios/{id}` - Detalle de envío
- `DELETE /api/gls/envios/{id}` - Anular envío
- `GET /api/gls/check-duplicate/{orden_id}/{tipo}` - Verificar duplicados
- `GET /api/gls/etiqueta/{id}` - Descargar etiqueta (con cache)
- `GET /api/gls/tracking/{id}` - Consultar tracking
- `POST /api/gls/sync` - Sincronizar todos los envíos activos
- `GET /api/gls/maestros` - Datos de referencia (servicios, estados)
- `GET /api/gls/orden/{orden_id}` - Logística completa de una orden

## 2026-03-27
### Fixed
- **P0: GLS Persistencia verificada** - Los envíos SÍ se guardan correctamente en BD
  - Verificado: 6 documentos en `gls_shipments` con tracking_url, codbarras, estado
  - Los envíos están asociados a órdenes via `gls_envios` array
  - Corregidos enlaces de tracking en `GLSLogistica.jsx` y `Seguimiento.jsx` para usar `tracking_url` del BD

### Added
- **Sincronización automática con GLS**: Al cargar la página de Logística o el detalle de una orden, se consulta automáticamente el estado actual de los envíos en GLS
  - `GLSAdmin.jsx`: Auto-sync al cargar la página
  - `GLSLogistica.jsx`: Auto-sync de envíos activos (no finales) al cargar el componente
  - Indicador visual "Consultando estado en GLS..." durante la sincronización

### Verified
- **Testing Agent**: 9/9 tests backend pasados, frontend 100%
- **API endpoints**: GET /api/gls/envios, GET /api/ordenes/{id}/logistics funcionan correctamente
- **Frontend /crm/logistica**: Muestra 6 envíos con enlaces de tracking
- **Frontend orden/logistica**: Muestra panel con bloques de Recogida y Envío con estado actualizado

## 2026-03-26
### Fixed
- **Carga Masiva IA**: Corregido parámetro `image_contents` → `file_contents` en UserMessage
- **ARIA búsqueda**: Añadida búsqueda por `numero_autorizacion` y `token_seguimiento`
- **Auditoría cambios de estado**: Ahora usa email del usuario autenticado + rol en historial_estados
- **Avería en Seguimiento**: Corregido para leer campo `daños` además de `averia`
- **Links Seguimiento**: Corregido `getUploadUrl()` para manejar objetos `{src, tipo}`
- **Comunicación SOAP GLS**: Refactor completo a SOAP 1.1, eliminados CDATA, credenciales actualizadas

### Added
- **Chatbot público blindado**: Solo responde FAQs, ventas, links directos (no acceso interno)
- **Tracking URL GLS**: Guardada en BD y mostrada al cliente

### Changed
- **Integración Resend**: Reemplazado SMTP por Resend API

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
- [x] GLS persistencia en BD (verificado funcionando)
- [x] Módulo logístico GLS completo (recogidas, envíos, devoluciones, tracking, etiquetas, auditoría)

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

---

## 2026-04-01 - Optimización de Actualizaciones en OrdenDetalle

### Fixed - Recargas innecesarias de página
- **Problema**: Al añadir/editar/eliminar materiales, la página recargaba TODO (orden, cliente, repuestos, mensajes, métricas, garantías) causando lentitud extrema.
- **Solución**: Implementado sistema de actualizaciones parciales en segundo plano.

### Changed - Frontend (`OrdenDetalle.jsx`)
- Nueva función `updateOrdenPartial(partialData)`: Actualiza solo campos específicos del estado
- Nueva función `updateOrdenTotales(totales)`: Actualiza solo los totales financieros
- Nueva función `updateOrdenMateriales(materiales, totales)`: Actualiza materiales y totales juntos
- Nueva función `refreshOrdenSilent()`: Recarga silenciosa sin mostrar spinner de loading
- `fetchOrden` ahora acepta parámetro `showLoading` para recargas silenciosas

### Changed - Frontend (`TablaMaterialesEditable.jsx`)
- Ya no llama a `onUpdate` para recargar toda la página
- Ahora pasa `(nuevosMateriales, totales)` al callback para actualización local
- Nueva prop `onTotalesUpdate` para solo actualizar totales

### Changed - Frontend (`OrdenSubestadoCard.jsx`)
- Nueva prop `onSubestadoChange` para actualización parcial de subestado
- Ya no requiere recarga completa al cambiar subestado

### Changed - Frontend (`GLSLogistica.jsx`)
- Removida llamada a `onUpdate` en refresh de logística
- El componente maneja su propio estado sin afectar al padre

### Impact
- **Antes**: ~4-6 peticiones HTTP por cada cambio de material
- **Después**: 1 petición HTTP + actualización local inmediata
- Experiencia de usuario mucho más fluida y ágil

---

## 2026-04-01 - Optimización Vista Técnico (OrdenTecnico.jsx)

### Fixed - Recargas innecesarias en la vista de técnico
- **Problema**: Al validar materiales o cargar imágenes desde la vista de técnico, se recargaba toda la página causando lentitud.
- **Solución**: Implementado el mismo patrón de actualizaciones parciales.

### Changed - Frontend (`OrdenTecnico.jsx`)
- `fetchOrden(showLoading)`: Ahora acepta parámetro para recargas silenciosas
- `updateOrdenPartial(partialData)`: Actualiza solo campos específicos
- `addFotosLocal(fotos, tipo)`: Añade fotos localmente sin recargar
- `updateMaterialesLocal(materiales)`: Actualiza materiales localmente
- `addMensajeLocal(mensaje)`: Añade mensaje sin recargar
- `refreshSilent()`: Recarga en segundo plano

### Changed - Frontend (`TecnicoFotosCard.jsx`)
- Estado local para fotos (ANTES, DESPUÉS, General)
- Actualización inmediata al subir fotos sin recargar página
- Nueva prop `onFotosChange` para notificar al padre

### Changed - Frontend (`TecnicoMaterialesCard.jsx`)
- Nueva prop `onMaterialesChange` para notificar cambios al padre
- `notifyMaterialesChange()` helper para sincronizar estado

### Changed - Frontend (`TecnicoMensajesCard.jsx`)
- Estado local para mensajes
- Nueva prop `onMensajeAdd` para actualización inmediata

### Impact
- **Antes**: Cada validación de material o foto recargaba toda la orden
- **Después**: Actualización instantánea local
- Los técnicos pueden trabajar de forma fluida sin esperas

---

## 2026-04-01 - Diagnóstico Técnico Visible para Admin

### Added - Vista de Diagnóstico para Administradores
- **Problema**: Los admins no podían ver ni editar el diagnóstico técnico de las órdenes
- **Solución**: El card "Diagnóstico Técnico y Control de Calidad" ahora es visible para Admin/Master

### Changed - Frontend (`OrdenDetalle.jsx`)
- `OrdenDiagnosticoCard` ahora se muestra para todos los roles (no solo técnicos)
- Añadido callback `onGuardarDiagnostico` para edición por admin
- Props `puedeEditarDiagnostico` y `esAdmin` para controlar permisos

### Changed - Frontend (`OrdenDiagnosticoCard.jsx`)
- Rediseño completo del componente con mejor organización visual
- Badge "Vista Admin" para indicar el contexto
- Botón "Editar" para modificar el diagnóstico técnico (solo admin)
- Textarea editable con botones "Guardar" y "Cancelar"
- Estados locales para edición sin recargar página
- Mensaje de autoguardado para checkboxes

### Features para Admin
- Ver diagnóstico técnico registrado por el técnico
- Editar/modificar el diagnóstico técnico
- Modificar checklist de recepción y QC
- Gestionar trazabilidad de baterías
- Editar notas de cierre técnico

---

## 2026-04-01 - Correcciones de Subestados, QC y Cierre de Reparación

### Fixed - BUG: Página en blanco al marcar como reparado
- **Causa**: El endpoint de cambio de estado ahora requiere `mensaje` obligatorio
- **Solución**: `TecnicoCierreReparacion.jsx` ahora envía mensaje con las notas del QC

### Added - Alertas automáticas de vencimiento de subestados
- Popup automático al abrir una orden con plazo vencido o próximo a vencer
- Badge visual en el card de subestado: "⚠️ VENCIDO", "⏰ HOY", "⏳ PRÓXIMO"
- Colores de borde dinámicos según estado (rojo/naranja/amarillo)
- Banner clickeable para ver detalles y actualizar subestado

### Improved - Sección QC en ficha impresa (OrdenPDF.jsx)
- Recuadro visual con fondo verde (conforme) o rojo (pendiente)
- Estado claro: "✅ VERIFICADO - CONFORME" o "⚠️ PENDIENTE DE VERIFICACIÓN"
- Grid con diagnóstico salida, funciones verificadas, limpieza
- Lista de funciones del sistema verificadas (si disponible)
- Estado de batería con porcentaje y ciclos
- Técnico responsable y fecha del QC

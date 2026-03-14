# Changelog - Revix CRM/ERP

Todas las actualizaciones notables del proyecto se documentan en este archivo.

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto sigue [Semantic Versioning](https://semver.org/lang/es/).

---

## [1.2.1] - 2026-03-14

### Liquidaciones - Auto-cruce de Códigos
- Al importar Excel de Insurama, el sistema cruza automáticamente los códigos de siniestro con las órdenes del sistema
- Códigos con orden encontrada y sin garantía pendiente → marcados como PAGADO automáticamente
- Códigos con garantía pendiente → quedan como PENDIENTE (requieren revisión)
- Códigos duplicados (ya pagados) → se ignoran
- Códigos no encontrados en el sistema → registrados como pendientes
- Modal de resultado muestra desglose detallado: auto-liquidados, pendientes garantía, duplicados, no encontrados

### Garantías - Órdenes Dependientes
- Fix: Navegación tras crear garantía ahora redirige correctamente a la nueva orden
- La orden de garantía hereda todos los campos del dispositivo, cliente y datos del seguro
- Se muestra el campo `numero_orden_padre` para referencia clara
- Badge **GARANTÍA** visible en el header con enlace "Ver original" a la orden padre
- Sección "Órdenes de Garantía" en OrdenDetalle muestra todas las garantías hijas con estado y enlace

---

## [1.2.0] - 2026-03-14

### Auditoría Funcional y Consolidación Financiera

### Cambios Principales
- **Auto-albarán en ENVIADO**: Al pasar una orden a "enviado", se genera automáticamente albarán si no tiene uno ya (las facturas se emiten manualmente por el usuario)
- **Dashboard Financiero Unificado**: El nuevo hub `/crm/finanzas` integra:
  - Resumen financiero con KPIs
  - Listado de facturas (venta y compra)
  - Panel de cobros y pagos pendientes
  - Gastos por proveedor y materiales
  - Valor del inventario en tiempo real
  - Evolución mensual

### Correcciones
- **Fix: datos no se mostraban en FinanzasDashboard** - Las respuestas axios no extraían `.data` correctamente
- **Navegación clarificada**: "Dashboard Financiero" renombrado a "Finanzas", "Contabilidad" renombrado a "Facturas y Albaranes"
- **Flujo Orden → Albarán** confirmado como automático (facturación es manual)

### Auditoría Completada
- Mapa completo de módulos, flujos de negocio y conexiones
- Módulo de compras auditado: correctamente conectado con inventario, proveedores, trazabilidad y dashboard financiero
- Compras reflejan gastos reales en el dashboard financiero sin duplicar facturas
- Documentados los hallazgos y plan de acción

---

## [1.1.0] - 2026-03-14

### ✨ Nueva Funcionalidad Principal
- **Dashboard Financiero Centralizado**: Nueva sección que unifica TODA la información financiera
  - Ingresos de órdenes enviadas
  - Gastos de compras
  - Valor del inventario en tiempo real
  - Evolución mensual (últimos 6 meses)
  - Desglose por proveedor y materiales consumidos
  - Balance general del negocio

### 🔗 Conexiones Implementadas
- **Compras → Contabilidad**: Las compras ahora se pueden registrar como facturas de compra
- **Órdenes → Facturación**: Las órdenes enviadas se pueden facturar automáticamente
- **Materiales → Gastos**: Se contabiliza el coste de materiales usados en cada orden
- **Inventario → Valor**: Cálculo en tiempo real del valor del stock

### 📊 Nuevos Endpoints API
- `GET /api/finanzas/dashboard` - Dashboard principal con filtro por periodo
- `GET /api/finanzas/evolucion` - Evolución mensual para gráficos
- `GET /api/finanzas/gastos/detalle` - Detalle de gastos por categoría
- `GET /api/finanzas/inventario/valor` - Análisis del valor del inventario
- `GET /api/finanzas/balance` - Balance general del año
- `POST /api/finanzas/registrar-compra/{id}` - Conecta compra con contabilidad
- `POST /api/finanzas/registrar-orden/{id}` - Genera factura de venta

### 📁 Archivos Nuevos
- `/app/backend/routes/finanzas_routes.py` - Backend del módulo financiero
- `/app/frontend/src/pages/FinanzasDashboard.jsx` - Frontend del dashboard

---

## [1.0.0] - 2026-03-14

### ✨ Nuevas Funcionalidades
- **Integración Cloudinary**: Almacenamiento permanente de fotos en la nube
  - Fotos organizadas por orden: `revix/ordenes/{numero_orden}/{tipo}/`
  - URLs persistentes que nunca se pierden
  - Descarga ZIP compatible con Cloudinary
- **Endpoint de emergencia**: `/api/auth/emergency-access` para recuperación de acceso
- **Órdenes irreparables**: Ahora pueden finalizarse (transición `irreparable → enviado`)
- **Activación automática del agente Insurama**: Se activa al guardar credenciales
- **Creación automática de órdenes**: Cuando un presupuesto es aceptado en Insurama

### 🔧 Correcciones
- **SMTP configurado**: Contraseña añadida para `notificaciones@revix.es`
- **Rutas de recuperación de contraseña**: `/forgot-password` redirige a `/crm/forgot-password`
- **Código de envío**: Se guarda correctamente en `codigo_recogida_salida`
- **Fotos "durante" eliminadas**: Técnico solo tiene tabs ANTES, DESPUÉS y General

### 🧹 Limpieza de Código
- Eliminados 48 archivos de test antiguos
- Eliminados scripts de utilidad obsoletos (seed_users.py, pre_production_check.py, benchmark.py)
- Eliminados documentos de memoria antiguos
- Limpieza de cache Python

### 📧 Configuración SMTP
- Host: mail.privateemail.com
- Puerto: 465 (SSL)
- Usuario: notificaciones@revix.es
- Estados que notifican: recibida, en_taller, reparado, enviado

### 🗄️ Integraciones
- MongoDB Atlas (producción)
- Cloudinary (imágenes)
- Insurama/Sumbroker (presupuestos)
- SMTP PrivateEmail (notificaciones)

---

## Versionado

- **MAJOR**: Cambios incompatibles con versiones anteriores
- **MINOR**: Nueva funcionalidad compatible hacia atrás
- **PATCH**: Correcciones de bugs compatibles hacia atrás


# Revix CRM/ERP - Product Requirements Document

## Descripción
CRM/ERP para gestión integral de un taller de reparaciones de dispositivos electrónicos. Gestiona clientes, órdenes de trabajo, inventario, compras, facturación, contabilidad y comunicaciones.

## Stack Tecnológico
- **Backend**: FastAPI, Python, Motor (MongoDB async)
- **Frontend**: React, Axios, Tailwind CSS, Shadcn UI
- **Base de Datos**: MongoDB (Atlas en producción)
- **Almacenamiento**: Cloudinary (imágenes)
- **Integraciones**: Insurama/Sumbroker, SMTP, Gemini AI (vía Emergent LLM Key)

## Versión Actual: v1.2.0

## Módulos del Sistema y Estado de Conexión
1. **Autenticación** - Login, roles (master/admin/tecnico), endpoint de emergencia ✅
2. **Clientes** - CRUD, historial de órdenes ✅
3. **Órdenes de Trabajo** - Ciclo completo: recepción → diagnóstico → presupuesto → reparación → validación → envío. Auto-albarán en VALIDACION y ENVIADO ✅
4. **Inventario** - Gestión de repuestos, stock, lotes, alertas ✅ Conectado con compras y dashboard financiero
5. **Compras** - Subida de factura PDF → Extracción IA → Confirmación → Actualización inventario + trazabilidad por lotes ✅ Conectado con inventario, proveedores, y dashboard financiero
6. **Finanzas** (HUB CENTRAL v1.2.0) - Dashboard unificado: KPIs, facturas, cobros/pagos, gastos, inventario, evolución ✅
7. **Contabilidad** - Facturas (venta/compra), albaranes, pagos, informes IVA, Modelo 347 ✅ Integrado como pestaña de Finanzas
8. **Insurama** - Integración con aseguradora, polling de presupuestos ✅
9. **Comunicaciones** - Email (SMTP), notificaciones automáticas ✅
10. **Calendario** - Gestión de citas y tareas ✅
11. **Incidencias** - Gestión básica ⚠️ (funcional pero poco conectado)
12. **Garantías** - Gestión de garantías ⚠️ (funcional pero poco conectado)

## Reglas de Negocio Clave
- **Albaranes**: Se generan automáticamente al pasar una orden a VALIDACION o ENVIADO
- **Facturas**: Solo se emiten manualmente por decisión del usuario, nunca automáticas
- **Compras**: Se registran subiendo la factura del proveedor (PDF). No generan facturas de compra automáticas en contabilidad porque la factura original ya está en el sistema

## Completado
- [x] Integración Cloudinary para imágenes persistentes (v1.1.0)
- [x] Endpoint de emergencia para acceso (v1.1.0)
- [x] Corrección SMTP y notificaciones automáticas (v1.1.0)
- [x] Página de recuperar contraseña (v1.1.0)
- [x] Flujo órdenes irreparables → enviado (v1.1.0)
- [x] Sistema de versionado (v1.1.0)
- [x] Guía de despliegue (v1.1.0)
- [x] Auditoría funcional completa (v1.2.0)
- [x] Dashboard Financiero Centralizado con 6 tabs (v1.2.0)
- [x] Auto-albarán en VALIDACION y ENVIADO (v1.2.0)
- [x] Navegación unificada Finanzas y Logística (v1.2.0)
- [x] Auditoría módulo compras: confirmado correctamente conectado (v1.2.0)

## Pendientes (P0)
- [ ] Validar creación automática de órdenes desde Insurama
- [ ] Validar notificaciones SMTP en producción post-despliegue

## Pendientes (P1)
- [ ] Integración completa con GLS (etiquetas, recogidas, tracking)
- [ ] Refinar flujo de garantías e incidencias (conectar con órdenes e inventario)

## Pendientes (P2)
- [ ] Acortar SKU generado en inventario

## Credenciales de Test
- Admin: admin@techrepair.local / Admin2026!
- Emergency key: RevixEmergency2026SecureKey!

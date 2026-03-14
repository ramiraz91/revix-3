# Revix CRM/ERP - Product Requirements Document

## Descripción
CRM/ERP para gestión integral de un taller de reparaciones de dispositivos electrónicos. Gestiona clientes, órdenes de trabajo, inventario, compras, facturación, contabilidad, liquidaciones y comunicaciones.

## Stack Tecnológico
- **Backend**: FastAPI, Python, Motor (MongoDB async)
- **Frontend**: React, Axios, Tailwind CSS, Shadcn UI
- **Base de Datos**: MongoDB (Atlas en producción)
- **Almacenamiento**: Cloudinary (imágenes)
- **Integraciones**: Insurama/Sumbroker, SMTP, Gemini AI (vía Emergent LLM Key)

## Versión Actual: v1.2.1

## Módulos del Sistema y Estado
1. **Autenticación** - Login, roles (master/admin/tecnico), endpoint de emergencia ✅
2. **Clientes** - CRUD, historial de órdenes ✅
3. **Órdenes de Trabajo** - Ciclo completo con auto-albarán ✅
4. **Inventario** - Repuestos, stock, lotes, alertas ✅
5. **Compras** - Subida factura PDF → IA → Inventario ✅
6. **Finanzas** (Hub Central) - Dashboard unificado con 6 tabs ✅
7. **Contabilidad** - Facturas, albaranes, pagos, IVA ✅
8. **Liquidaciones** - Importar Excel Insurama, auto-cruce de códigos, marcado automático ✅
9. **Garantías** - Órdenes dependientes con ciclo completo y presupuesto nuevo ✅
10. **Insurama** - Integración con aseguradora, polling ✅
11. **Comunicaciones** - Email SMTP, notificaciones ✅
12. **Calendario** - Citas y tareas ✅
13. **Incidencias** - Gestión básica ⚠️

## Reglas de Negocio Clave
- **Albaranes**: Auto-generados al pasar a VALIDACION o ENVIADO
- **Facturas**: Solo manuales, decisión del usuario
- **Compras**: Registradas con factura del proveedor (PDF), no duplican en contabilidad
- **Liquidaciones**: Al importar Excel, auto-marcar como pagados salvo duplicados o garantías pendientes
- **Garantías**: Crean orden dependiente del mismo dispositivo con ciclo completo nuevo

## Completado
- [x] Cloudinary para imágenes (v1.1.0)
- [x] Endpoint de emergencia (v1.1.0)
- [x] SMTP y notificaciones (v1.1.0)
- [x] Recuperar contraseña (v1.1.0)
- [x] Órdenes irreparables → enviado (v1.1.0)
- [x] Sistema de versionado (v1.1.0)
- [x] Guía de despliegue (v1.1.0)
- [x] Auditoría funcional completa (v1.2.0)
- [x] Dashboard Financiero Centralizado (v1.2.0)
- [x] Auto-albarán en VALIDACION y ENVIADO (v1.2.0)
- [x] Corrección lógica: facturas manuales, no auto-compras (v1.2.0)
- [x] Liquidaciones: auto-cruce de códigos al importar Excel (v1.2.1)
- [x] Garantías: orden dependiente con campos heredados y ciclo completo (v1.2.1)
- [x] Fix: navegación tras crear garantía (v1.2.1)
- [x] Badge GARANTÍA y enlaces bidireccionales padre↔hijo (v1.2.1)

## Pendientes (P0)
- [ ] Validar creación automática de órdenes desde Insurama
- [ ] Validar notificaciones SMTP en producción

## Pendientes (P1)
- [ ] Integración completa con GLS
- [ ] Refinar módulo de incidencias

## Pendientes (P2)
- [ ] Acortar SKU inventario

## Credenciales de Test
- Admin: admin@techrepair.local / Admin2026!
- Master: master@test.local / Master2026!
- Emergency key: RevixEmergency2026SecureKey!

# Revix CRM/ERP - Product Requirements Document

## Descripción
CRM/ERP para gestión integral de un taller de reparaciones de dispositivos electrónicos.

## Stack Tecnológico
- **Backend**: FastAPI, Python, Motor (MongoDB async)
- **Frontend**: React, Axios, Tailwind CSS, Shadcn UI
- **Base de Datos**: MongoDB (Atlas en producción, DB: "production")
- **Almacenamiento**: Cloudinary (imágenes)
- **Integraciones**: Insurama/Sumbroker (polling 2h), SMTP, Gemini AI

## Versión Actual: v1.3.0

## Flujo Nuevas Órdenes
1. Polling cada 2h (o manual con botón "Consultar Insurama") → detecta presupuestos aceptados
2. Pre-orden llega a "Nuevas Órdenes" como `pendiente_tramitar`
3. Tramitador abre detalle completo (como orden de trabajo), edita datos si necesario
4. Introduce código de recogida → crea orden de trabajo en `pendiente_recibir`
5. Sigue flujo normal

## Reglas de Negocio
- **Albaranes**: Auto-generados al pasar a VALIDACION o ENVIADO
- **Facturas**: Solo manuales por decisión del usuario
- **Compras**: Con factura del proveedor (PDF)
- **Liquidaciones**: Auto-cruce de códigos al importar Excel
- **Garantías**: Orden dependiente del mismo dispositivo
- **Nuevas Órdenes**: Pre-ordenes editables como una orden completa

## Completado
- [x] Cloudinary, endpoint emergencia, SMTP, recuperar contraseña (v1.1.0)
- [x] Versionado, guía despliegue, órdenes irreparables (v1.1.0)
- [x] Auditoría funcional, Dashboard Financiero, auto-albarán (v1.2.0)
- [x] Liquidaciones auto-cruce, garantías mejoradas (v1.2.1)
- [x] Nuevas Órdenes con polling 2h y badge (v1.3.0)
- [x] Botón "Consultar Insurama" para polling manual (v1.3.0)
- [x] Vista detalle completa de pre-ordenes con edición de todos los campos (v1.3.0)
- [x] KPIs financieros y operativos globales en Dashboard Finanzas (v1.3.1)

## Pendientes (P0)
- [ ] Validar notificaciones SMTP en producción

## Pendientes (P1)
- [ ] Integración completa con GLS
- [ ] Refinar módulo de incidencias

## Pendientes (P2)
- [ ] Acortar SKU inventario

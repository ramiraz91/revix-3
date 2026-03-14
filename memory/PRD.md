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

## Flujo Nuevas Órdenes (v1.3.0)
1. Polling cada 2h consulta Insurama → detecta presupuestos aceptados
2. Pre-orden llega a "Nuevas Órdenes" como `pendiente_tramitar` (con notificación urgente)
3. Tramitador revisa datos, introduce código de recogida
4. Al confirmar → se crea orden de trabajo en `pendiente_recibir`
5. A partir de ahí sigue el flujo normal: recibida → diagnóstico → presupuesto → reparación → validación → envío

## Reglas de Negocio
- **Albaranes**: Auto-generados al pasar a VALIDACION o ENVIADO
- **Facturas**: Solo manuales por decisión del usuario
- **Compras**: Con factura del proveedor (PDF), sin duplicar en contabilidad
- **Liquidaciones**: Auto-cruce de códigos al importar Excel (pagados auto salvo duplicados/garantías)
- **Garantías**: Orden dependiente del mismo dispositivo, ciclo completo nuevo
- **Nuevas Órdenes**: Presupuestos aceptados → tramitador revisa → código recogida → orden de trabajo

## Completado
- [x] Cloudinary, endpoint emergencia, SMTP, recuperar contraseña (v1.1.0)
- [x] Versionado, guía despliegue, órdenes irreparables (v1.1.0)
- [x] Auditoría funcional, Dashboard Financiero, auto-albarán (v1.2.0)
- [x] Liquidaciones auto-cruce, garantías mejoradas (v1.2.1)
- [x] **Nuevas Órdenes** con polling 2h, tramitación y badge (v1.3.0)

## Pendientes (P0)
- [ ] Validar notificaciones SMTP en producción post-despliegue

## Pendientes (P1)
- [ ] Integración completa con GLS
- [ ] Refinar módulo de incidencias

## Pendientes (P2)
- [ ] Acortar SKU inventario

## Credenciales de Test
- Admin: admin@techrepair.local / Admin2026!
- Emergency key: RevixEmergency2026SecureKey!

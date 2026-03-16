# Revix CRM/ERP - Product Requirements Document

## Descripción
CRM/ERP para gestión integral de un taller de reparaciones de dispositivos electrónicos.

## Stack Tecnológico
- **Backend**: FastAPI, Python, Motor (MongoDB async)
- **Frontend**: React, Axios, Tailwind CSS, Shadcn UI
- **Base de Datos**: MongoDB (Atlas en producción, DB: "revix_production")
- **Almacenamiento**: Cloudinary (imágenes)
- **Integraciones**: Insurama/Sumbroker (polling 2h), SMTP, Gemini AI

## Versión Actual: v1.4.0

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
- **Re-presupuesto**: Cambio de estado a re_presupuestar, notificación al cliente, redirección a materiales

## Completado
- [x] Cloudinary, endpoint emergencia, SMTP, recuperar contraseña (v1.1.0)
- [x] Versionado, guía despliegue, órdenes irreparables (v1.1.0)
- [x] Auditoría funcional, Dashboard Financiero, auto-albarán (v1.2.0)
- [x] Liquidaciones auto-cruce, garantías mejoradas (v1.2.1)
- [x] Nuevas Órdenes con polling 2h y badge (v1.3.0)
- [x] Botón "Consultar Insurama" para polling manual (v1.3.0)
- [x] Vista detalle completa de pre-ordenes con edición de todos los campos (v1.3.0)
- [x] KPIs financieros y operativos globales en Dashboard Finanzas (v1.3.1)
- [x] Eliminación de módulos Utopya, MobileSentrix, Pre-Registros (v1.4.0)
- [x] Reorganización menú: Logística → Envíos y Recogidas (v1.4.0)
- [x] Configuración SMTP centralizada con UI (v1.4.0)
- [x] Portal seguimiento: responsive, sin logo, recuperación credenciales (v1.4.0)
- [x] Endpoint POST /ordenes/{id}/enviar-whatsapp - Botón "Notificar" (v1.4.0)
- [x] Flujo Re-presupuesto completo: endpoints, UI dialog, banner, auto-redirect a materiales (v1.4.0)
- [x] Edición inline de materiales en TablaMaterialesEditable con estado local (v1.4.0)
- [x] Indicador de consentimiento legal visible en vista de orden (v1.4.0)
- [x] Fix bug TablaMaterialesEditable: materiales → localMateriales (v1.4.0)

## Pendientes (P0)
- [ ] Validar notificaciones SMTP en producción (deploy del usuario)

## Pendientes (P1)
- [ ] Integración completa con GLS
- [ ] Refinar módulo de incidencias

## Pendientes (P2)
- [ ] Acortar SKU inventario
- [ ] Módulo playwright_stealth - verificar en producción

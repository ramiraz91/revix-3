# Revix CRM/ERP - Product Requirements Document

## Descripcion
CRM/ERP para gestion integral de un taller de reparaciones de dispositivos electronicos.

## Stack Tecnologico
- **Backend**: FastAPI, Python, Motor (MongoDB async)
- **Frontend**: React, Axios, Tailwind CSS, Shadcn UI
- **Base de Datos**: MongoDB (Atlas en produccion, DB: "revix_production")
- **Almacenamiento**: Cloudinary (imagenes)
- **Integraciones**: Insurama/Sumbroker (polling 2h), SMTP, Gemini AI

## Version Actual: v1.4.0

## Flujo Nuevas Ordenes
1. Polling cada 2h (o manual con boton "Consultar Insurama") -> detecta presupuestos aceptados
2. Pre-orden llega a "Nuevas Ordenes" como `pendiente_tramitar`
3. Tramitador abre detalle completo (como orden de trabajo), edita datos si necesario
4. Introduce codigo de recogida -> crea orden de trabajo en `pendiente_recibir`
5. Sigue flujo normal

## Reglas de Negocio
- **Albaranes**: Auto-generados al pasar a VALIDACION o ENVIADO
- **Facturas**: Solo manuales por decision del usuario
- **Compras**: Con factura del proveedor (PDF)
- **Liquidaciones**: Auto-cruce de codigos al importar Excel
- **Garantias**: Orden dependiente del mismo dispositivo
- **Nuevas Ordenes**: Pre-ordenes editables como una orden completa
- **Re-presupuesto**: Cambio de estado a re_presupuestar, notificacion al cliente, redireccion a materiales

## Completado
- [x] Cloudinary, endpoint emergencia, SMTP, recuperar contrasena (v1.1.0)
- [x] Versionado, guia despliegue, ordenes irreparables (v1.1.0)
- [x] Auditoria funcional, Dashboard Financiero, auto-albaran (v1.2.0)
- [x] Liquidaciones auto-cruce, garantias mejoradas (v1.2.1)
- [x] Nuevas Ordenes con polling 2h y badge (v1.3.0)
- [x] Boton "Consultar Insurama" para polling manual (v1.3.0)
- [x] Vista detalle completa de pre-ordenes con edicion de todos los campos (v1.3.0)
- [x] KPIs financieros y operativos globales en Dashboard Finanzas (v1.3.1)
- [x] Eliminacion de modulos Utopya, MobileSentrix, Pre-Registros (v1.4.0)
- [x] Reorganizacion menu: Logistica -> Envios y Recogidas (v1.4.0)
- [x] Configuracion SMTP centralizada con UI (v1.4.0)
- [x] Portal seguimiento: responsive, sin logo, recuperacion credenciales (v1.4.0)
- [x] Endpoint POST /ordenes/{id}/enviar-whatsapp - Boton "Notificar" (v1.4.0)
- [x] Flujo Re-presupuesto completo: endpoints, UI dialog, banner, auto-redirect a materiales (v1.4.0)
- [x] Edicion inline de materiales en TablaMaterialesEditable con estado local (v1.4.0)
- [x] Indicador de consentimiento legal visible en vista de orden (v1.4.0)
- [x] Fix bug TablaMaterialesEditable: materiales -> localMateriales (v1.4.0)
- [x] Preparacion para redeploy: verificacion completa de dependencias, build, env vars (v1.4.0)
- [x] Deduplicacion Nuevas Ordenes: si codigo ya existe en ordenes, se descarta sin notificar (v1.4.1)
- [x] Deduplicacion Notificaciones Insurama: no se repite notificacion si ya existe para el mismo siniestro+tipo (v1.4.1)
- [x] Fix fotos admin visibles en seccion Antes para tecnicos en OrdenDetalle (v1.4.1)
- [x] Fix descarga ZIP de fotos: fetch+blob en vez de window.open (v1.4.1)

## Pendientes (P0)
- [ ] Verificar notificacion automatica por email al crear orden en produccion

## Pendientes (P1)
- [ ] Integracion completa con GLS
- [ ] Refinar modulo de incidencias

## Pendientes (P2)
- [ ] Acortar SKU inventario
- [ ] Modulo playwright_stealth - verificar en produccion

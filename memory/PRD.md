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

## Módulos del Sistema
1. **Autenticación** - Login, roles (master/admin/tecnico), endpoint de emergencia
2. **Clientes** - CRUD, historial de órdenes
3. **Órdenes de Trabajo** - Ciclo completo: recepción → diagnóstico → presupuesto → reparación → validación → envío
4. **Inventario** - Gestión de repuestos, stock, lotes, alertas
5. **Compras** - Pedidos a proveedores, auto-registro en contabilidad
6. **Finanzas** (CENTRALIZADO v1.2.0) - Dashboard unificado con KPIs, facturas, cobros/pagos, gastos, inventario, evolución
7. **Contabilidad** - Facturas (venta/compra), albaranes, pagos, informes IVA, Modelo 347
8. **Insurama** - Integración con aseguradora, polling de presupuestos
9. **Comunicaciones** - Email (SMTP), notificaciones automáticas
10. **Calendario** - Gestión de citas y tareas
11. **Incidencias** - Gestión básica de incidencias
12. **Garantías** - Gestión de garantías de reparaciones

## Completado
- [x] Integración Cloudinary para imágenes persistentes (v1.1.0)
- [x] Endpoint de emergencia para acceso (/api/auth/emergency-access) (v1.1.0)
- [x] Corrección SMTP y notificaciones automáticas (v1.1.0)
- [x] Página de recuperar contraseña (v1.1.0)
- [x] Flujo órdenes irreparables → enviado (v1.1.0)
- [x] Sistema de versionado (v1.1.0)
- [x] Guía de despliegue (DEPLOYMENT_GUIDE.md) (v1.1.0)
- [x] **Auditoría funcional completa** (v1.2.0)
- [x] **Dashboard Financiero Centralizado** con 6 tabs (v1.2.0)
- [x] **Auto-facturación** de órdenes al pasar a ENVIADO (v1.2.0)
- [x] **Auto-registro de compras** en contabilidad al confirmar (v1.2.0)
- [x] Navegación unificada Finanzas y Logística (v1.2.0)

## Pendientes (P0)
- [ ] Validar creación automática de órdenes desde Insurama con el usuario
- [ ] Validar notificaciones SMTP en producción post-despliegue

## Pendientes (P1)
- [ ] Integración completa con GLS (etiquetas, recogidas, tracking)
- [ ] Refinar flujo de garantías e incidencias (conectar con órdenes e inventario)

## Pendientes (P2)
- [ ] Acortar SKU generado en inventario
- [ ] Mejorar automatización de albaranes (conectar con facturas)

## Arquitectura de Archivos Clave
```
/app
├── backend/routes/
│   ├── finanzas_routes.py       # Dashboard financiero centralizado
│   ├── contabilidad_routes.py   # Facturas, albaranes, pagos, informes
│   ├── ordenes_routes.py        # Órdenes + auto-facturación
│   ├── compras_routes.py        # Compras + auto-registro contable
│   └── auth_routes.py           # Autenticación + emergency access
├── frontend/src/pages/
│   ├── FinanzasDashboard.jsx    # Hub financiero unificado
│   └── Contabilidad.jsx         # Gestión detallada facturas/albaranes
├── version.json                 # v1.2.0
├── CHANGELOG.md                 # Historial de cambios
└── memory/
    ├── PRD.md                   # Este archivo
    └── DEPLOYMENT_GUIDE.md      # Guía de despliegue producción
```

## Credenciales de Test
- Admin: admin@techrepair.local / Admin2026!
- Emergency key: RevixEmergency2026SecureKey!

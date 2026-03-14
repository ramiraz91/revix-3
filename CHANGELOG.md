# Changelog - Revix CRM/ERP

Todas las actualizaciones notables del proyecto se documentan en este archivo.

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto sigue [Semantic Versioning](https://semver.org/lang/es/).

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


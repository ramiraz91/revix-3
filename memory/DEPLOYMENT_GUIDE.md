# Guía de Despliegue a Producción - ERP/CRM Revix

## 🚀 Inicio Rápido

### 1. Verificación Pre-Producción
```bash
cd /app/backend
python3 pre_production_check.py
```
Este script verificará:
- Variables de entorno críticas (JWT_SECRET, MONGO_URL, CORS)
- Configuración de archivos .env
- Búsqueda de credenciales hardcodeadas
- Existencia de scripts de índices

### 2. Plantillas de Configuración
```bash
# Backend
cp /app/backend/.env.production.template /app/backend/.env
# Editar con valores reales

# Frontend
cp /app/frontend/.env.production.template /app/frontend/.env
# Configurar URL del backend
```

---

## 📋 Pre-requisitos

### Infraestructura
- [ ] MongoDB Atlas o servidor MongoDB dedicado (mínimo 4GB RAM)
- [ ] Servidor con Node.js 18+ y Python 3.11+
- [ ] Dominio configurado con SSL (HTTPS)
- [ ] CDN para archivos estáticos (opcional pero recomendado)

### Variables de Entorno Requeridas

#### Backend (`/app/backend/.env`)
```env
# Base de datos (OBLIGATORIO - Cambiar en producción)
MONGO_URL="mongodb+srv://usuario:password@cluster.mongodb.net/revix_prod?retryWrites=true&w=majority"
DB_NAME="revix_production"

# Seguridad (OBLIGATORIO - Generar nuevo secreto)
JWT_SECRET="GENERAR_SECRETO_SEGURO_DE_32_CARACTERES_MINIMO"

# CORS (Restringir en producción)
CORS_ORIGINS="https://revix.es,https://app.revix.es"

# Twilio (SMS)
TWILIO_ACCOUNT_SID="tu_account_sid"
TWILIO_AUTH_TOKEN="tu_auth_token"
TWILIO_PHONE_NUMBER="+34xxxxxxxxx"

# SendGrid (Email alternativo)
SENDGRID_API_KEY="SG.xxxxx"
SENDGRID_FROM_EMAIL="notificaciones@revix.es"

# SMTP (Email principal)
SMTP_HOST="mail.privateemail.com"
SMTP_PORT=465
SMTP_SECURE=true
SMTP_USER="notificaciones@revix.es"
SMTP_PASS="tu_password_smtp"
SMTP_FROM="Revix <notificaciones@revix.es>"
SMTP_REPLY_TO="help@revix.es"

# LLM Key (Emergent)
EMERGENT_LLM_KEY="tu_key"

# Sumbroker/Insurama (opcional)
SUMBROKER_LOGIN="tu_login"
SUMBROKER_PASSWORD="tu_password"
```

#### Frontend (`/app/frontend/.env`)
```env
REACT_APP_BACKEND_URL=https://api.revix.es
```

---

## 🔐 Checklist de Seguridad

### Crítico (MUST)
- [ ] **JWT_SECRET** diferente del valor por defecto (mínimo 32 caracteres aleatorios)
- [ ] **CORS_ORIGINS** restringido a dominios de producción
- [ ] **MONGO_URL** apuntando a servidor de producción con autenticación
- [ ] Certificado SSL válido en el dominio
- [ ] Contraseñas de usuarios de prueba eliminadas o cambiadas
- [ ] Logs sensibles deshabilitados en producción

### Recomendado (SHOULD)
- [ ] Rate limiting en endpoints de autenticación
- [ ] Backup automático de MongoDB (diario)
- [ ] Monitoreo de errores (Sentry o similar)
- [ ] WAF (Web Application Firewall)

---

## 📦 Comandos de Despliegue

### Backend (FastAPI)
```bash
# Instalar dependencias
cd /app/backend
pip install -r requirements.txt

# Crear índices de MongoDB (solo primera vez)
python create_indexes.py

# Ejecutar con Gunicorn (producción)
gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001
```

### Frontend (React)
```bash
cd /app/frontend
yarn install
yarn build

# Servir con Nginx o CDN
# Los archivos estarán en /app/frontend/build
```

---

## 🗄️ Índices de MongoDB

Ejecutar en producción para optimizar rendimiento:
```bash
python /app/backend/create_indexes.py
```

Índices críticos:
- `ordenes.estado_created_at_idx`
- `ordenes.dispositivo_imei_idx`
- `ordenes.numero_autorizacion_idx`
- `clientes.telefono_1`
- `clientes.email_idx`

---

## 🔄 Migraciones de Datos

### Antes de producción:
1. **Eliminar datos de prueba:**
```javascript
// En MongoDB Shell
db.ordenes.deleteMany({ numero_orden: /^TEST_/ });
db.clientes.deleteMany({ email: /@test\./ });
```

2. **Cambiar contraseñas de usuarios administrativos:**
```javascript
// Actualizar contraseñas (hasheadas con bcrypt)
db.users.updateOne(
  { email: "admin@revix.es" },
  { $set: { password_hash: "NUEVO_HASH_BCRYPT" } }
);
```

---

## 📊 Monitoreo Post-Despliegue

### Endpoints de salud
- `GET /api/health` - Estado del servidor
- `GET /api/metrics/slow-endpoints` - Endpoints lentos (admin)

### Métricas clave a monitorear
- Latencia p95 de `/api/ordenes/v2` (objetivo: <100ms)
- Uso de memoria MongoDB
- Errores 5xx por hora
- Tiempo de respuesta de APIs externas (Sumbroker, MobileSentrix)

---

## 🚨 Plan de Rollback

### Si hay problemas críticos:
1. Revertir código al commit anterior
2. Si hay problemas de BD, restaurar backup
3. Notificar a usuarios

### Endpoints con fallback:
- `/api/ordenes/v2` → `/api/ordenes` (original, más lento pero funcional)

---

## 📞 Contactos de Emergencia

- **Soporte MongoDB Atlas:** support.mongodb.com
- **Soporte Twilio:** twilio.com/help
- **Soporte SendGrid:** sendgrid.com/support

---

## ✅ Checklist Final Pre-Launch

- [ ] Variables de entorno configuradas
- [ ] JWT_SECRET cambiado
- [ ] CORS restringido
- [ ] Índices de MongoDB creados
- [ ] Datos de prueba eliminados
- [ ] Contraseñas de admin cambiadas
- [ ] SSL configurado
- [ ] Backup configurado
- [ ] Monitoreo activo
- [ ] Pruebas de humo pasadas

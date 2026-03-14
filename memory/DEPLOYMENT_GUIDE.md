# Guía de Deployment - Revix CRM/ERP

## Versión Actual: 1.1.0

---

## ⚠️ CONFIGURACIÓN CRÍTICA DE BASE DE DATOS

### Para que la producción funcione correctamente, debes configurar las variables de entorno en Emergent:

**Antes del deploy, en el panel de Emergent, configura:**

```
MONGO_URL=mongodb+srv://repair-workshop-crm:d6o5694lqs2c73ftftr0@customer-apps.wwutd8.mongodb.net/?retryWrites=true&w=majority&appName=workshop-erp-3
DB_NAME=production
```

### ¿Por qué es necesario?
- El archivo `.env` contiene `localhost` para el preview (desarrollo)
- El preview no tiene acceso de red a MongoDB Atlas
- Emergent debe sobrescribir `MONGO_URL` en producción con tu MongoDB Atlas

---

## Pasos para Deploy

### 1. Configurar Variables de Entorno (ANTES del deploy)
En Emergent, ve a Settings → Environment Variables y añade:

| Variable | Valor |
|----------|-------|
| `MONGO_URL` | `mongodb+srv://repair-workshop-crm:d6o5694lqs2c73ftftr0@customer-apps.wwutd8.mongodb.net/?retryWrites=true&w=majority&appName=workshop-erp-3` |
| `DB_NAME` | `production` |

### 2. Hacer Deploy
1. Ve a https://app.emergent.sh/
2. Busca el proyecto `workshop-erp-3`
3. Haz clic en **Deploy** → **Deploy Now**
4. Espera 10-15 minutos

### 3. Verificar Acceso
Después del deploy, prueba el login:
- URL: https://repair-workshop-crm-r-1773426268.emergent.host/crm/login
- Email: `master@revix.es`
- Password: `Master123!`

### 4. Si hay problemas de acceso
Ejecuta el endpoint de emergencia:
```bash
curl -X POST "https://TU-URL-PRODUCCION/api/auth/emergency-access" \
  -H "Content-Type: application/json" \
  -d '{
    "emergency_key": "RevixEmergency2026SecureKey!",
    "email": "master@revix.es",
    "password": "Master123!"
  }'
```

---

## Credenciales

### MongoDB Atlas
- **Cluster**: customer-apps.wwutd8.mongodb.net
- **Database**: production
- **User**: repair-workshop-crm

### Cloudinary (Imágenes)
- **Cloud Name**: dw0exxafh
- **API Key**: 466555137182474

### SMTP (Emails)
- **Host**: mail.privateemail.com
- **Port**: 465
- **User**: notificaciones@revix.es

---

## Usuarios del Sistema

| Email | Password | Rol |
|-------|----------|-----|
| master@revix.es | Master123! | master |
| admin@techrepair.local | Admin2026! | admin |
| tecnico@techrepair.local | Tecnico2026! | tecnico |
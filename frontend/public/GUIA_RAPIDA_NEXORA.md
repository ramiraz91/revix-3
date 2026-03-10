# 📋 NEXORA - Guía Rápida de Referencia

## 🔑 Acceso Rápido

| Acción | Cómo hacerlo |
|--------|--------------|
| Login | Email + Contraseña → "Iniciar Sesión" |
| Cerrar sesión | Menú lateral → "Cerrar Sesión" |
| Buscar orden | Campo superior → Escanear QR o escribir número |

---

## 📊 Dashboard - Indicadores

| Icono | Significado |
|-------|-------------|
| 📋 | Órdenes activas |
| 👥 | Total clientes |
| 📦 | Repuestos en stock |
| 🔔 | Notificaciones nuevas |
| 🛒 | Compras pendientes |

---

## 🔄 Estados de Orden

```
Pendiente Recibir → En Diagnóstico → Presupuesto Enviado →
Presupuesto Aceptado → En Reparación → Reparado → Entregado
```

**Estados especiales:**
- ❌ Presupuesto Rechazado
- 🚫 Irreparable
- ⚫ Cancelado
- 🛡️ En Garantía

---

## 📱 Crear Orden Rápido

1. **+ Nueva Orden**
2. Buscar/Crear cliente
3. Datos dispositivo: Marca, Modelo, IMEI
4. Descripción del problema
5. **Crear Orden**

---

## 🔧 Materiales - Validación (Técnicos)

### Proceso de Picking:
1. Abrir orden → Pestaña **Materiales**
2. Clic en **"Validar (N pendientes)"**
3. Escanear SKU de cada material
4. ✅ Verde = Validado
5. ⬜ Gris = Pendiente

### Añadir material:
- **Existente**: Buscar en inventario
- **Nuevo**: Material no registrado (requiere aprobación admin)

---

## 🏥 Insurama - Enviar Presupuesto

### Campos obligatorios:
| Campo | Opciones |
|-------|----------|
| Precio | €XX.XX |
| Disponibilidad | Inmediata / 24h / 48h / 7días / Sin stock |
| Tiempo (horas) | X.X horas |
| Tipo recambio | Original / Compatible / Reacondicionado |
| Tipo garantía | Fabricante / Taller / Sin garantía |
| Descripción | Texto libre |

---

## ⚡ Flujos Automáticos

| Proceso | Frecuencia |
|---------|-----------|
| 🔄 Polling Insurama | Cada 5 minutos |
| 🗑️ Limpieza pre-registros | Cada 7 días |
| 📧 Notificaciones | Tiempo real |

---

## 🔔 Tipos de Notificación

| Color | Tipo |
|-------|------|
| 🟢 | Presupuesto aceptado / Completado |
| 🔴 | Rechazado / Error |
| 🔵 | Nuevo siniestro |
| 🟡 | Material pendiente |
| 🟣 | Mensaje admin |

---

## ⌨️ Atajos de Teclado

| Tecla | Acción |
|-------|--------|
| `Enter` | Confirmar acción / Validar material |
| `Esc` | Cerrar modal / Cancelar |
| `Tab` | Siguiente campo |

---

## 📞 Soporte

- 📧 soporte@nexora.es
- 💬 Chat interno (botón azul)
- 📱 +34 XXX XXX XXX

---

*NEXORA v2.0 - Febrero 2026*

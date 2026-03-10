# 📘 Manual de Usuario - NEXORA CRM/ERP

## Sistema de Gestión para Servicios Técnicos de Telefonía Móvil

**Versión:** 2.0  
**Fecha:** Febrero 2026  
**Empresa:** NEXORA

---

## 📑 Índice

1. [Introducción](#1-introducción)
2. [Acceso al Sistema](#2-acceso-al-sistema)
3. [Panel de Control (Dashboard)](#3-panel-de-control-dashboard)
4. [Órdenes de Trabajo](#4-órdenes-de-trabajo)
5. [Gestión de Clientes](#5-gestión-de-clientes)
6. [Inventario](#6-inventario)
7. [Integración Insurama/Sumbroker](#7-integración-insuramasumbroker)
8. [Pre-Registros](#8-pre-registros)
9. [Notificaciones](#9-notificaciones)
10. [Calendario](#10-calendario)
11. [Flujos Automáticos](#11-flujos-automáticos)
12. [Guía para Técnicos](#12-guía-para-técnicos)
13. [Preguntas Frecuentes](#13-preguntas-frecuentes)

---

## 1. Introducción

### ¿Qué es NEXORA?

NEXORA es un sistema CRM/ERP diseñado específicamente para talleres de reparación de dispositivos móviles. Permite gestionar:

- **Órdenes de trabajo** completas con seguimiento de estado
- **Clientes** y su historial de reparaciones
- **Inventario** de repuestos con control de stock
- **Integración con Insurama** para gestión de siniestros de seguros
- **Comunicaciones** automáticas con clientes
- **Facturación** y presupuestos

### Características principales

| Característica | Descripción |
|----------------|-------------|
| 🔄 **Automatización** | Polling automático de Insurama, notificaciones en tiempo real |
| 🤖 **Asistente IA** | Diagnósticos y sugerencias de reparación con Gemini |
| 📱 **Multi-dispositivo** | Acceso desde ordenador, tablet o móvil |
| 👥 **Multi-usuario** | Roles de Admin, Técnico y Master |
| 🔔 **Tiempo real** | Notificaciones instantáneas vía WebSocket |

---

## 2. Acceso al Sistema

### Pantalla de Login

Para acceder al sistema:

1. Abrir el navegador y acceder a la URL del sistema
2. Introducir **Email** y **Contraseña**
3. Pulsar **"Iniciar Sesión"**

### Roles de Usuario

| Rol | Permisos |
|-----|----------|
| **Master** | Acceso total: configuración, usuarios, integraciones |
| **Admin** | Gestión completa de órdenes, clientes, inventario |
| **Técnico** | Ver órdenes asignadas, actualizar estado, añadir materiales |

### Cerrar Sesión

- Pulsar **"Cerrar Sesión"** en la parte inferior del menú lateral

---

## 3. Panel de Control (Dashboard)

### Vista General

El Dashboard muestra un resumen del estado del taller:

#### Indicadores Principales

| Indicador | Significado |
|-----------|-------------|
| **Órdenes** | Total de órdenes activas |
| **Clientes** | Número de clientes registrados |
| **Repuestos** | Productos en inventario |
| **Notificaciones** | Alertas pendientes de leer |
| **Compras Pend.** | Pedidos de material pendientes |

#### Métricas de Rendimiento

- **Tasa de Éxito**: Porcentaje de reparaciones completadas
- **Tasa de Cancelación**: Porcentaje de órdenes canceladas
- **Garantías Activas**: Órdenes en periodo de garantía

### Escáner Rápido

En la parte superior del Dashboard hay un campo para **escanear códigos** de orden rápidamente:

1. Colocar el cursor en el campo de escaneo
2. Escanear el código QR o de barras de la orden
3. El sistema abrirá automáticamente la ficha de la orden

---

## 4. Órdenes de Trabajo

### Lista de Órdenes

La pantalla de órdenes muestra todas las reparaciones:

#### Filtros Disponibles

- **Todos los estados**: Ver todas las órdenes
- **Pendiente Recibir**: Esperando llegada del dispositivo
- **En Diagnóstico**: Evaluando el daño
- **Presupuesto Enviado**: Esperando aprobación del cliente
- **En Reparación**: Trabajo en curso
- **Reparado**: Listo para entregar
- **Entregado**: Completado

#### Búsqueda

- Por **número de orden** (OT-20260212-...)
- Por **modelo de dispositivo** (iPhone 15, Samsung S24...)
- Por **IMEI** del dispositivo
- Por **teléfono del cliente**

### Crear Nueva Orden

1. Pulsar **"+ Nueva Orden"**
2. Rellenar los datos:
   - **Cliente**: Buscar existente o crear nuevo
   - **Dispositivo**: Marca, modelo, IMEI, color
   - **Descripción del problema**
   - **Tipo de servicio**: Normal, Urgente, Garantía
3. Pulsar **"Crear Orden"**

### Ficha de Orden

Al abrir una orden se muestra:

#### Pestañas Disponibles

| Pestaña | Contenido |
|---------|-----------|
| **Información** | Datos del cliente y dispositivo |
| **Estado** | Cambiar estado de la orden |
| **Materiales** | Repuestos utilizados |
| **Evidencias** | Fotos del dispositivo |
| **Mensajes** | Comunicación interna |
| **Historial** | Registro de cambios |

#### Acciones Rápidas

- **Imprimir etiqueta**: Genera etiqueta adhesiva para el dispositivo
- **Enviar presupuesto**: Notifica al cliente por email/SMS
- **Generar QR**: Código para seguimiento
- **Crear garantía**: Si es una reparación repetida

### Estados de una Orden

```
Pendiente Recibir → En Diagnóstico → Presupuesto Enviado → 
Presupuesto Aceptado → En Reparación → Reparado → Entregado
```

#### Estados Especiales

- **Presupuesto Rechazado**: Cliente no acepta el precio
- **Irreparable**: No se puede reparar
- **Cancelado**: Orden anulada
- **En Garantía**: Reparación bajo garantía anterior

---

## 5. Gestión de Clientes

### Lista de Clientes

Muestra todos los clientes registrados con:

- Nombre completo
- DNI/NIF
- Teléfono
- Email
- Dirección

### Crear Nuevo Cliente

1. Pulsar **"+ Nuevo Cliente"**
2. Rellenar:
   - Nombre y apellidos
   - DNI/NIF
   - Teléfono (para notificaciones SMS)
   - Email (para notificaciones email)
   - Dirección completa
3. Pulsar **"Guardar"**

### Ficha de Cliente

Al abrir un cliente se muestra:

- **Datos personales**
- **Historial de órdenes**: Todas sus reparaciones anteriores
- **Métricas**: Total gastado, órdenes completadas
- **Notas**: Observaciones sobre el cliente

---

## 6. Inventario

### Vista de Inventario

Muestra todos los repuestos disponibles:

| Campo | Descripción |
|-------|-------------|
| **SKU** | Código único del producto (generado automáticamente) |
| **Nombre** | Descripción del repuesto |
| **Categoría** | Pantallas, Baterías, Conectores, etc. |
| **P. Compra** | Precio de coste |
| **P. Venta** | Precio al cliente |
| **Stock** | Unidades disponibles |

### Alertas de Stock

- 🔴 **Stock bajo**: Cuando queda menos del mínimo configurado
- El sistema notifica automáticamente cuando hay que reponer

### Añadir Nuevo Repuesto

1. Pulsar **"+ Nuevo Repuesto"**
2. Introducir **nombre** del producto
3. Seleccionar **categoría**
4. El **SKU se genera automáticamente**
5. Añadir precios y stock inicial
6. Pulsar **"Guardar"**

### Categorías de Repuestos

- **Pantallas**: LCDs, OLEDs, táctiles
- **Baterías**: Baterías originales y compatibles
- **Conectores**: Puertos de carga, flex
- **Cámaras**: Frontales y traseras
- **Altavoces**: Auriculares y altavoces
- **Carcasas**: Tapas traseras, marcos
- **Cristales**: Protectores y cristales templados
- **Otros**: Tornillos, adhesivos, herramientas

---

## 7. Integración Insurama/Sumbroker

### ¿Qué es Insurama?

Insurama es el portal de gestión de siniestros de seguros de móviles. NEXORA se integra directamente con este portal para:

- ✅ Recibir automáticamente nuevos siniestros
- ✅ Enviar presupuestos al portal
- ✅ Sincronizar estados de reparación
- ✅ Gestionar fotos y evidencias

### Pantalla de Insurama

#### Sección Superior: Conexión

Muestra el estado de conexión con Sumbroker:
- 🟢 **Conectado**: Sistema sincronizado
- 🔴 **Desconectado**: Verificar credenciales

#### Buscar Siniestro

1. Introducir el **código de siniestro** (ej: 26BE000833)
2. Pulsar **"Buscar"**
3. Se muestra el detalle completo del siniestro

### Enviar Presupuesto a Insurama

Cuando se encuentra un siniestro pendiente:

1. Ir a la pestaña **"Acciones"**
2. Rellenar el formulario de presupuesto:
   - **Precio (€)**: Coste total de la reparación
   - **Disponibilidad de Recambios**: Inmediata, 24h, 48h, 7 días, Sin stock
   - **Tiempo en Horas**: Horas estimadas de trabajo
   - **Tipo de Recambio**: Original, Compatible, Reacondicionado
   - **Tipo de Garantía**: Fabricante, Taller, Sin garantía
   - **Descripción**: Detalle de la reparación
3. Pulsar **"Enviar Presupuesto"**

### Flujo Automático de Insurama

```
1. Sumbroker envía nuevo siniestro
   ↓
2. NEXORA detecta automáticamente (polling cada 5 min)
   ↓
3. Se crea Pre-Registro en el sistema
   ↓
4. Notificación al administrador
   ↓
5. Admin envía presupuesto
   ↓
6. Cliente acepta/rechaza
   ↓
7. Si acepta → Se crea Orden de Trabajo automáticamente
```

---

## 8. Pre-Registros

### ¿Qué son los Pre-Registros?

Los Pre-Registros son siniestros de Insurama que aún no tienen orden de trabajo creada. Representan trabajos potenciales.

### Lista de Pre-Registros

Muestra todos los siniestros pendientes con:

- **Código de siniestro** (26BE...)
- **Cliente**: Nombre del asegurado
- **Dispositivo**: Modelo del móvil
- **Estado**: Pendiente Presupuesto, Enviado, Aceptado, etc.
- **Fecha**: Cuándo se recibió

### Acciones en Pre-Registros

| Botón | Acción |
|-------|--------|
| **Enviar Presupuesto** | Ir a Insurama para enviar precio |
| **Crear Orden** | Generar orden de trabajo directamente |
| **Ver Orden** | Abrir orden existente (si ya se creó) |

### Estados de Pre-Registro

- **Pendiente Presupuesto**: Sin precio enviado
- **Presupuesto Enviado**: Esperando respuesta
- **Aceptado**: Cliente aprobó → Crear orden
- **Rechazado**: Cliente no aceptó
- **Orden Creada**: Ya tiene orden de trabajo
- **Cancelado**: Siniestro anulado

### Limpieza Automática

Los pre-registros **cancelados** se eliminan automáticamente después de **7 días**.

---

## 9. Notificaciones

### Centro de Notificaciones

Muestra todas las alertas del sistema:

#### Tipos de Notificaciones

| Tipo | Color | Significado |
|------|-------|-------------|
| **Presupuesto Aceptado** | 🟢 Verde | Cliente aprobó, crear orden |
| **Presupuesto Rechazado** | 🔴 Rojo | Cliente no aceptó |
| **Nuevo Siniestro** | 🔵 Azul | Llegó trabajo de Insurama |
| **Material Pendiente** | 🟡 Amarillo | Técnico solicita repuesto |
| **Orden Completada** | 🟢 Verde | Reparación terminada |

### Acciones

- **Ver Ficha**: Ir directamente a la orden relacionada
- **Marcar Leída**: Quitar de notificaciones nuevas
- **Eliminar**: Borrar notificación

### Selección Múltiple

1. Pulsar **"Seleccionar"**
2. Marcar las notificaciones deseadas
3. Pulsar **"Eliminar (N)"** o **"Marcar leídas"**

---

## 10. Calendario

### Vista de Calendario

Muestra una vista mensual con todos los eventos:

#### Tipos de Eventos

| Color | Tipo |
|-------|------|
| 🟢 Verde | Orden Asignada |
| 🔵 Azul | Llegada de Dispositivo |
| 🟠 Naranja | Llegada de Repuesto |
| 🟣 Morado | Reunión |
| ⚫ Gris | Ausencia |
| 🔴 Rojo | Vacaciones |

### Crear Evento

1. Pulsar **"+ Nuevo Evento"**
2. Seleccionar tipo de evento
3. Elegir fecha y hora
4. Añadir descripción
5. Asignar técnico (si aplica)
6. Pulsar **"Guardar"**

### Asignar Orden a Fecha

1. Pulsar **"Asignar Orden"**
2. Seleccionar la orden de la lista
3. Elegir fecha estimada de entrega
4. Asignar técnico responsable

---

## 11. Flujos Automáticos

### 🔄 Polling de Insurama

**¿Qué hace?**
Cada 5 minutos el sistema consulta automáticamente el portal de Sumbroker buscando:
- Nuevos siniestros asignados
- Presupuestos aceptados/rechazados
- Cambios de estado

**Resultado:**
- Se crean Pre-Registros automáticamente
- Se generan Órdenes cuando se acepta presupuesto
- Se notifica al administrador

### 📧 Notificaciones Automáticas

**¿Cuándo se envían?**

| Evento | Email | SMS | App |
|--------|-------|-----|-----|
| Nueva orden creada | ✅ | ❌ | ✅ |
| Presupuesto enviado | ✅ | ✅ | ✅ |
| Presupuesto aceptado | ✅ | ❌ | ✅ |
| Reparación completada | ✅ | ✅ | ✅ |
| Stock bajo | ❌ | ❌ | ✅ |

### 🗑️ Limpieza Automática

- **Pre-registros cancelados**: Se eliminan tras 7 días
- **Notificaciones antiguas**: Según configuración

### 📊 Sincronización de Estados

Cuando cambia el estado en NEXORA:
1. Se actualiza el portal de Insurama
2. Se notifica al cliente
3. Se registra en el historial

---

## 12. Guía para Técnicos

### Acceso al Panel de Técnico

1. Iniciar sesión con credenciales de técnico
2. Acceder a **"Panel Técnico"** en el menú

### Ver Órdenes Asignadas

El técnico solo ve las órdenes que le han sido asignadas:
- Ordenadas por prioridad
- Con indicador de urgencia
- Fecha estimada de entrega

### Actualizar Estado de Orden

1. Abrir la ficha de la orden
2. Seleccionar nuevo estado
3. Añadir notas si es necesario
4. Pulsar **"Guardar"**

### Añadir Materiales

#### Desde Inventario
1. Ir a pestaña **"Materiales"**
2. Pulsar **"Existente"**
3. Buscar el repuesto
4. Confirmar (la orden se bloquea hasta aprobación)

#### Material No Registrado
1. Pulsar **"Nuevo"**
2. Escribir nombre del material
3. Indicar cantidad
4. El admin asignará precios

### ✅ Validar Materiales Usados

Sistema de "picking" para confirmar uso de materiales:

1. Pulsar **"Validar (N pendientes)"**
2. Escanear el SKU o código de barras de cada material
3. El sistema confirma automáticamente
4. Se registra quién validó y cuándo

**Progreso visible:**
- Barra de progreso: X/Y materiales validados
- Color verde = validado
- Color gris = pendiente

### Subir Evidencias (Fotos)

1. Ir a pestaña **"Evidencias"**
2. Pulsar **"Subir Foto"**
3. Seleccionar imagen del dispositivo
4. Añadir descripción
5. La foto se guarda con la orden

### Comunicación con Admin

1. Ir a pestaña **"Mensajes"**
2. Escribir mensaje
3. Pulsar **"Enviar"**
4. El admin recibe notificación

---

## 13. Preguntas Frecuentes

### ❓ ¿Cómo cambio mi contraseña?

1. Ir a **Administración → Usuarios**
2. Buscar tu usuario
3. Pulsar **"Editar"**
4. Cambiar contraseña
5. Guardar

### ❓ ¿Por qué no puedo cambiar el estado de una orden?

La orden puede estar **bloqueada** por:
- Material pendiente de aprobación
- Esperando datos del cliente
- Bloqueo administrativo

Contacta con el administrador.

### ❓ ¿Cómo imprimo la etiqueta del taller?

1. Abrir la ficha de la orden
2. Pulsar **"Imprimir Etiqueta"**
3. Seleccionar tamaño de etiqueta (50x30mm, 60x40mm, etc.)
4. Pulsar **"Imprimir"**

### ❓ ¿Cómo busco un dispositivo por IMEI?

1. Ir a **Órdenes de Trabajo**
2. En el campo de búsqueda, escribir el IMEI
3. Pulsar **"Buscar"**
4. También funciona con el escáner QR

### ❓ ¿Por qué no aparecen los siniestros de Insurama?

Posibles causas:
1. **Conexión perdida**: Verificar en pantalla Insurama
2. **Credenciales incorrectas**: Contactar admin
3. **Polling pausado**: El sistema puede estar en mantenimiento

### ❓ ¿Cómo solicito un repuesto que no está en inventario?

1. Abrir la orden
2. Ir a **Materiales → Nuevo**
3. Escribir el nombre del repuesto
4. La orden se bloqueará hasta que admin apruebe y cree el producto

### ❓ ¿Cómo genero una factura?

1. Abrir la orden completada
2. Ir a pestaña **"Facturación"**
3. Verificar datos y precios
4. Pulsar **"Generar Factura"**
5. Descargar PDF o enviar por email

---

## 📞 Soporte

**Para asistencia técnica:**
- 📧 Email: soporte@nexora.es
- 📱 Teléfono: +34 XXX XXX XXX
- 💬 Chat interno: Botón azul en esquina inferior derecha

---

© 2026 NEXORA. Todos los derechos reservados.

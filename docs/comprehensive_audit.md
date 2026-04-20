# 🔬 Auditoría profunda · BD `production`
_Generado · 2026-04-20T19:57:55+00:00_

**Volumen:** 133 órdenes · 121 clientes · 5 usuarios · 56 liquidaciones · 10 incidencias

## 🔧 Dominio Órdenes

### Distribución de estados

| Estado | Nº | % |
|---|---|---|
| `enviado` | 101 | 75.9% |
| `pendiente_recibir` | 13 | 9.8% |
| `en_taller` | 7 | 5.3% |
| `irreparable` | 5 | 3.8% |
| `recibida` | 4 | 3.0% |
| `reparado` | 2 | 1.5% |
| `cancelado` | 1 | 0.8% |

### ⏱ Órdenes estancadas (>15 d sin updates en estado activo)

✅ Ninguna orden estancada >15 d.

### Carga por técnico

| Técnico | Órdenes totales | ✅ Existe user | ⚠️ Notas |
|---|---|---|---|
| `ramiraz91@gmail.com` | 6 | ✅ tecnico |  |

### Calidad de datos en órdenes

| Campo crítico | Órdenes sin el dato | % |
|---|---|---|
| Dispositivo sin IMEI | 3 | 2.3% |
| Sin avería reportada | 133 | 100.0% |
| Sin token de seguimiento | 0 | 0.0% |
| Sin `created_at` | 0 | 0.0% |

## 👥 Dominio Clientes

- **0** clientes sin ninguna orden (0.0%). Candidatos a revisar si son reales.
- **0** posibles duplicados blandos (mismo nombre+apellidos).

- **0** clientes sin email NI teléfono (0.0%). Imposibles de contactar.

## 💰 Dominio Finanzas

### Estado de liquidaciones

| Estado | Nº |
|---|---|
| `pagado` | 46 |
| `pendiente` | 10 |

### 🚨 Órdenes cerradas con autorización pero SIN liquidar

🟠 **2** órdenes son dinero potencialmente no facturado a aseguradora.

| Nº OT | Autorización | Estado | Fecha |
|---|---|---|---|
| `OT-20260409-D87B5D35` | `2601000090` | reparado | 2026-04-20T10:23:45.636414+00:00 |
| `OT-20260409-CECD7097` | `26BE001789` | reparado | 2026-04-20T14:02:44.123380+00:00 |

### Autorizaciones con varias órdenes (posibles garantías)

**9** autorizaciones aparecen en >1 orden.

| Autorización | Órdenes | Detalle |
|---|---|---|
| `26BE001571` | 2 | OT-20260324-9690D058 (enviado, garantia=False), OT-20260413-E24A2C64 (enviado, garantia=True) |
| `26BE001530` | 3 | OT-20260324-7C1EA088 (enviado, garantia=False), OT-20260330-7A57C8D3 (enviado, garantia=True), OT-20260420-94568739 (pendiente_recibir, garantia=True) |
| `26BE001509` | 2 | OT-20260324-1F92E76C (enviado, garantia=False), OT-20260330-DD3C5C98 (enviado, garantia=True) |
| `26BE001424` | 2 | OT-20260324-6A46B5FD (enviado, garantia=False), OT-20260414-CD54DA7A (enviado, garantia=True) |
| `26BE001114` | 2 | OT-20260324-7A3A94CE (enviado, garantia=False), OT-20260325-CAA00705 (enviado, garantia=True) |
| `26BE001021` | 2 | OT-20260325-61B4C093 (enviado, garantia=False), OT-20260325-88DE0280 (enviado, garantia=True) |
| `26BE001676` | 2 | OT-20260325-6000E3F7 (enviado, garantia=False), OT-20260413-91C6B25A (en_taller, garantia=True) |
| `25BE006578` | 2 | OT-20260407-DD873C17 (enviado, garantia=False), OT-20260407-C74E4BFC (enviado, garantia=True) |
| `26BE000609` | 2 | OT-20260408-278C9FA4 (enviado, garantia=False), OT-20260408-F0C6D92F (enviado, garantia=True) |

## ✉️ Dominio Comunicaciones

- Total notificaciones: **122**
- No leídas: **84** (68.9%)
- Huérfanas (orden_id inexistente): **0**

## ⚠️ Dominio Incidencias

- Total: **10**
- Abiertas: **5**

| Estado | Nº |
|---|---|
| `resuelta` | 5 |
| `abierta` | 5 |

## 🏅 Dominio Calidad ISO

| Registro | Cantidad |
|---|---|
| Muestreos QA | 0 |
| Documentos controlados | 0 |
| Evaluaciones proveedores | 3 |
| No-conformidades | 0 |

🟠 **El SGC ISO está vacío en la BD** → el módulo existe en código pero no se ha alimentado con datos reales todavía. Candidato claro para el agente ISO Officer.

## 🔐 Dominio Seguridad

### Usuarios por rol

| Rol | Nº |
|---|---|
| `tecnico` | 2 |
| `master` | 2 |
| `admin` | 1 |

- Sin `password_hash`: **0** (imposibilitados de hacer login)
- Con `password_temporal=true`: **0** (deben cambiar al loguearse)

- Total audit_logs: **292**
- Último evento audit: `generate_tracking_token` · 2026-04-20T19:57:26.306389+00:00

## 📦 Dominio Inventario

- Total repuestos: **4**
- Sin SKU: **0**
- Sin `stock_actual`: **0**
- Stock total (suma unidades): **23**

- Materiales referenciados en órdenes que apuntan a repuestos inexistentes: **0**

## 🤖 Dominio IA

- `agent_logs`: **4,395** entradas · indica uso real del agente ARIA
- `agent_conversations`: **49** hilos

---

## 🎯 Resumen ejecutivo

- 🔴 2 órdenes cerradas con autorización SIN liquidar (posible dinero perdido)
- 🟠 9 nº autorización en >1 orden (verificar si son garantías)
- 🟡 5 incidencias abiertas
- 🟢 SGC ISO vacío en datos (módulo existe pero sin uso) → oportunidad para agente ISO

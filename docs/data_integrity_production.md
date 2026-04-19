# Informe de integridad de datos · BD `production`

_Generado · 2026-04-19T21:58:44+00:00_

## Resumen ejecutivo

- Colecciones totales: **41**
- Documentos totales: **7,030**
- Hallazgos totales: **4**
  - Referencias rotas: **2**
  - Duplicados: **1**
  - Campos obligatorios faltantes: **1**
  - Tipos inconsistentes: **0**

## 1. Inventario de colecciones

| Colección | Documentos |
|---|---|
| `agent_logs` | 4,352 |
| `ot_event_log` | 791 |
| `insurama_cache` | 387 |
| `gls_logs` | 235 |
| `audit_logs` | 184 |
| `historial_mercado` | 159 |
| `pre_registros` | 138 |
| `ordenes` | 129 |
| `ot_print_logs` | 118 |
| `clientes` | 118 |
| `notificaciones` | 75 |
| `chatbot_web` | 62 |
| `liquidaciones` | 56 |
| `albaranes` | 55 |
| `agent_conversations` | 49 |
| `print_jobs` | 24 |
| `faqs` | 18 |
| `ia_chat_history` | 12 |
| `consentimientos_seguimiento` | 11 |
| `incidencias` | 9 |
| `gls_shipments` | 6 |
| `users` | 5 |
| `configuracion` | 5 |
| `plantillas_email` | 5 |
| `repuestos` | 4 |
| `capas` | 4 |
| `proveedores` | 4 |
| `iso_proveedores_evaluacion` | 3 |
| `gls_tracking_events` | 3 |
| `peticiones_exteriores` | 2 |
| `solicitudes_web` | 2 |
| `insurama_ia_logs` | 1 |
| `contabilidad_series` | 1 |
| `iso_qa_config` | 1 |
| `print_agents` | 1 |
| `restos` | 1 |
| `audit_log` | 0 |
| `alertas_sla` | 0 |
| `agent_idempotency` | 0 |
| `gls_envios` | 0 |
| `notificaciones_externas` | 0 |

## 2. Referencias rotas / huérfanos

### 🚨 `ordenes.cliente_id → clientes.id`
1+ documentos con referencia inexistente (muestra max 20):

| Doc ID | Target inexistente |
|---|---|
| `5c313372-d1f8-4299-991f-e667cca7960e` | `723c9fce-649c-4ecd-b25a-32857f385042` |

### 🚨 `ordenes.tecnico_asignado → users.id`
5+ documentos con referencia inexistente (muestra max 20):

| Doc ID | Target inexistente |
|---|---|
| `6a68fbaa-8e2b-46d5-8a72-34590877b8e2` | `ramiraz91@gmail.com` |
| `552db4e1-4eca-4e39-a15a-a3b39218afc6` | `ramiraz91@gmail.com` |
| `600e4a61-1bde-449d-afcd-c09b2f6fde4b` | `ramiraz91@gmail.com` |
| `f70702ac-db9b-4d2f-9600-98470d7dd6fe` | `ramiraz91@gmail.com` |
| `83c88665-b1cb-442f-a905-517e56d8e189` | `ramiraz91@gmail.com` |

## 3. Duplicados

### 🟠 `ordenes.numero_autorizacion`
9 valores duplicados:

| Valor | Apariciones |
|---|---|
| `25BE006578` | 2 |
| `26BE000609` | 2 |
| `26BE001021` | 2 |
| `26BE001114` | 2 |
| `26BE001424` | 2 |
| `26BE001509` | 2 |
| `26BE001530` | 2 |
| `26BE001571` | 2 |
| `26BE001676` | 2 |

## 4. Campos obligatorios faltantes

| Campo | Docs sin valor |
|---|---|
| `clientes.nombre` | 1 |

## 5. Tipos inconsistentes en campos fecha

✅ Todos los campos fecha usan tipo coherente.

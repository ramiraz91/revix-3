# Mapa de dominios — Backend Revix

_Generado automáticamente · 33 módulos · 423 endpoints_

## 1. Resumen por dominio

| Dominio | Módulos | Endpoints | Colecciones Mongo |
|---|---|---|---|
| **Admin / Master** | 2 | 29 | alertas_sla, audit_logs, clientes, comisiones, configuracion, etiquetas_envio … |
| **Aseguradoras (Insurama)** | 2 | 34 | clientes, configuracion, historial_mercado, insurama_cache, ordenes, peticiones_exteriores |
| **Autenticación** | 1 | 16 | password_reset_tokens, users |
| **Calendario** | 1 | 6 | calendario, notificaciones, ordenes, users |
| **Compras** | 3 | 45 | compras, configuracion, lotes_compra, ordenes, pedidos_proveedor, proveedores … |
| **Comunicaciones** | 1 | 11 | configuracion, notificaciones, repuestos |
| **Dashboard / Datos** | 1 | 6 | clientes, notificaciones, ordenes, ordenes_compra, repuestos |
| **Finanzas/Contabilidad** | 2 | 35 | abonos, albaranes, clientes, configuracion, contabilidad_series, facturas … |
| **IA / Agentes** | 4 | 24 | agent_conversations, historial_mercado, ia_chat_history, insurama_ia_logs, ordenes, pre_registros |
| **Inventario/Repuestos** | 5 | 76 | capas, clientes, compras, contabilidad_series, facturas, incidencias … |
| **Logística** | 2 | 13 | clientes, ordenes, print_agents, print_jobs |
| **Proveedores** | 2 | 32 | capas, configuracion, consentimientos_seguimiento, incidencias, iso_documentos, iso_proveedores_evaluacion … |
| **Web pública** | 3 | 14 | chatbot_web, faqs, peticiones_exteriores, solicitudes_web |
| **WebSocket** | 1 | 1 | — |
| **Órdenes** | 3 | 81 | albaranes, audit_logs, clientes, configuracion, contabilidad_series, gls_shipments … |

## 2. Detalle por dominio

### Admin / Master

**`admin_routes.py`** · prefix `—` · 23 endpoints · 671 líneas · 🔒

- Colecciones: `alertas_sla, audit_logs, clientes, comisiones, configuracion, etiquetas_envio, ordenes, plantillas_email, transportistas, users`
- Rutas: `/control-cambios, /auditoria, /auditoria/entidad/{entidad}/{entidad_id}, /alertas-sla, /alertas-sla/verificar, /alertas-sla/{alerta_id}/resolver` …

**`config_empresa_routes.py`** · prefix `—` · 6 endpoints · 84 líneas · 🔒

- Colecciones: `configuracion`
- Rutas: `/configuracion/notificaciones, /configuracion/notificaciones, /configuracion/empresa, /configuracion/empresa/publica, /configuracion/empresa/logo, /configuracion/empresa`


### Aseguradoras (Insurama)

**`insurama_routes.py`** · prefix `/insurama` · 25 endpoints · 2190 líneas · 🔒

- Colecciones: `clientes, configuracion, historial_mercado, insurama_cache, ordenes`
- Rutas: `/config, /config, /test-conexion, /debug-budgets/{codigo}, /debug-competidores-raw/{codigo}, /presupuestos` …

**`peticiones_routes.py`** · prefix `—` · 9 endpoints · 417 líneas · 🔒

- Colecciones: `clientes, ordenes, peticiones_exteriores`
- Rutas: `/peticiones-exteriores, /peticiones-exteriores/{peticion_id}, /peticiones-exteriores, /peticiones-exteriores/{peticion_id}, /peticiones-exteriores/{peticion_id}/contactar, /peticiones-exteriores/{peticion_id}/aceptar` …


### Autenticación

**`auth_routes.py`** · prefix `—` · 16 endpoints · 571 líneas · 🔒

- Colecciones: `password_reset_tokens, users`
- Rutas: `/auth/register, /auth/login, /auth/me, /auth/users, /usuarios, /usuarios/{usuario_id}` …


### Calendario

**`calendario_routes.py`** · prefix `—` · 6 endpoints · 104 líneas · 🔒

- Colecciones: `calendario, notificaciones, ordenes, users`
- Rutas: `/calendario/eventos, /calendario/eventos, /calendario/eventos/{evento_id}, /calendario/eventos/{evento_id}, /calendario/asignar-orden, /tecnicos/disponibilidad`


### Compras

**`compras_routes.py`** · prefix `/compras` · 7 endpoints · 715 líneas · 🔒

- Colecciones: `compras, lotes_compra, ordenes, proveedores, repuestos`
- Rutas: `/analizar-factura, /confirmar, /, /{compra_id}, /lote/{codigo_lote}, /trazabilidad/repuesto/{repuesto_id}` …

**`mobilesentrix_routes.py`** · prefix `/mobilesentrix` · 31 endpoints · 1556 líneas · 🔒

- Colecciones: `configuracion, pedidos_proveedor, repuestos`
- Rutas: `/config, /config, /oauth/start, /oauth/callback, /oauth/exchange, /test-connection` …

**`utopya_routes.py`** · prefix `/utopya` · 7 endpoints · 692 líneas · 🔒

- Colecciones: `configuracion, repuestos`
- Rutas: `/categories, /config, /config, /sync-catalogo/progress, /sync-catalogo, /sync-catalogo/stop` …


### Comunicaciones

**`notificaciones_routes.py`** · prefix `—` · 11 endpoints · 136 líneas · 🔒

- Colecciones: `configuracion, notificaciones, repuestos`
- Rutas: `/notificaciones, /notificaciones/{notificacion_id}/leer, /notificaciones/{notificacion_id}, /notificaciones/eliminar-masivo, /notificaciones/marcar-leidas-masivo, /notificaciones/marcar-leidas-orden/{orden_id}` …


### Dashboard / Datos

**`dashboard_routes.py`** · prefix `—` · 6 endpoints · 698 líneas · 🔒

- Colecciones: `clientes, notificaciones, ordenes, ordenes_compra, repuestos`
- Rutas: `/dashboard/stats, /dashboard/metricas-avanzadas, /dashboard/alertas-stock, /dashboard/ordenes-compra-urgentes, /dashboard/operativo, /dashboard/tecnico`


### Finanzas/Contabilidad

**`contabilidad_routes.py`** · prefix `/contabilidad` · 26 endpoints · 1361 líneas · 🔒

- Colecciones: `abonos, albaranes, clientes, configuracion, contabilidad_series, facturas, notificaciones, ordenes, proveedores`
- Rutas: `/facturas, /facturas, /facturas/{factura_id}, /facturas/{factura_id}, /facturas/{factura_id}/emitir, /facturas/{factura_id}/anular` …

**`liquidaciones_routes.py`** · prefix `/liquidaciones` · 9 endpoints · 635 líneas · 🔒

- Colecciones: `liquidaciones, ordenes`
- Rutas: `/pendientes, /por-mes/{mes}, /{codigo_siniestro}/estado, /{codigo_siniestro}/garantia, /importar-excel, /marcar-pagados` …


### IA / Agentes

**`agent_routes.py`** · prefix `/agent` · 9 endpoints · 182 líneas · 🔒

- Colecciones: `agent_conversations`
- Rutas: `/chat, /summary, /alerts, /conversations, /conversations/{conversation_id}, /conversations/{conversation_id}` …

**`ia_routes.py`** · prefix `/ia` · 6 endpoints · 151 líneas · 🔒

- Colecciones: `ia_chat_history`
- Rutas: `/mejorar-texto, /mejorar-diagnostico, /consulta, /historial/{session_id}, /historial/{session_id}, /diagnostico`

**`insurama_ia_routes.py`** · prefix `/insurama/ia` · 3 endpoints · 384 líneas · 🔒

- Colecciones: `insurama_ia_logs, ordenes, pre_registros`
- Rutas: `/extraer-codigos, /importar-codigos, /historial`

**`inteligencia_precios_routes.py`** · prefix `/inteligencia-precios` · 6 endpoints · 822 líneas · 🔒

- Colecciones: `historial_mercado, ordenes`
- Rutas: `/registrar-resultado, /dashboard, /recomendar-precio, /historial, /capturar-desde-competidores/{codigo}, /analisis-competidor/{nombre}`


### Inventario/Repuestos

**`data_routes.py`** · prefix `—` · 47 endpoints · 2059 líneas · 🔒

- Colecciones: `capas, clientes, incidencias, notificaciones, ordenes, ordenes_compra, proveedores, repuestos, restos`
- Rutas: `/clientes, /clientes, /clientes/{cliente_id}, /clientes/{cliente_id}, /clientes/{cliente_id}, /clientes/{cliente_id}/historial` …

**`finanzas_routes.py`** · prefix `/finanzas` · 7 endpoints · 770 líneas · 🔒

- Colecciones: `clientes, compras, contabilidad_series, facturas, ordenes, repuestos`
- Rutas: `/dashboard, /evolucion, /gastos/detalle, /inventario/valor, /registrar-compra/{compra_id}, /registrar-orden/{orden_id}` …

**`inventario_mejorado_routes.py`** · prefix `/inventario` · 6 endpoints · 222 líneas · 🔒

- Colecciones: `repuestos`
- Rutas: `/{repuesto_id}/movimiento, /{repuesto_id}/historial, /alertas, /valoracion, /sugerencias-reposicion, /{repuesto_id}/stock-disponible`

**`kits_routes.py`** · prefix `/kits` · 9 endpoints · 391 líneas · 🔒

- Colecciones: `kits, repuestos`
- Rutas: `/stats, /por-producto/{producto_id}, /{kit_id}, /{kit_id}, /{kit_id}, /{kit_id}/expandir` …

**`restos_routes.py`** · prefix `—` · 7 endpoints · 182 líneas · 🔒

- Colecciones: `ordenes, restos`
- Rutas: `/restos, /restos/{resto_id}, /restos, /restos/{resto_id}, /restos/{resto_id}/piezas, /restos/{resto_id}/piezas/{pieza_id}` …


### Logística

**`logistica_routes.py`** · prefix `—` · 4 endpoints · 451 líneas · 🔒

- Colecciones: `clientes, ordenes`
- Rutas: `/logistica/resumen, /logistica/recogidas, /logistica/envios, /logistica/orden/{orden_id}`

**`print_routes.py`** · prefix `/print` · 9 endpoints · 280 líneas · 🔒

- Colecciones: `print_agents, print_jobs`
- Rutas: `/send, /status, /jobs, /job/{job_id}, /pending, /complete` …


### Proveedores

**`iso_routes.py`** · prefix `—` · 14 endpoints · 594 líneas · 🔒

- Colecciones: `iso_documentos, iso_proveedores_evaluacion, ordenes, proveedores, qa_muestreo, users`
- Rutas: `/iso/qa/muestreo, /iso/qa/muestreos, /iso/qa/muestreo/{muestreo_id}, /iso/qa/muestreo/{muestreo_id}/resultado, /iso/proveedores/evaluacion, /iso/proveedores/evaluaciones` …

**`master_routes.py`** · prefix `—` · 18 endpoints · 1193 líneas · 🔒

- Colecciones: `capas, configuracion, consentimientos_seguimiento, incidencias, iso_documentos, iso_proveedores_evaluacion, iso_qa_config, ordenes, ot_event_log, qa_muestreos, seguridad_eventos, users`
- Rutas: `/master/metricas-tecnicos, /master/facturacion, /master/iso/documentos, /master/iso/documentos, /master/iso/proveedores, /master/iso/proveedores/evaluar` …


### Web pública

**`apple_manuals_routes.py`** · prefix `/api/apple-manuals` · 3 endpoints · 52 líneas · ⚠️ SIN AUTH

- Rutas: `/lookup, /models, /detect-repair-type`

**`faqs_routes.py`** · prefix `—` · 8 endpoints · 315 líneas · 🔒

- Colecciones: `faqs`
- Rutas: `/faqs/public, /faqs, /faqs/{faq_id}, /faqs, /faqs/{faq_id}, /faqs/{faq_id}` …

**`web_publica_routes.py`** · prefix `/web` · 3 endpoints · 443 líneas · ⚠️ SIN AUTH

- Colecciones: `chatbot_web, peticiones_exteriores, solicitudes_web`
- Rutas: `/chatbot, /contacto, /presupuesto`


### WebSocket

**`websocket_routes.py`** · prefix `—` · 1 endpoints · 82 líneas · ⚠️ SIN AUTH

- Rutas: `/api/ws/test`


### Órdenes

**`nuevas_ordenes_routes.py`** · prefix `/nuevas-ordenes` · 9 endpoints · 377 líneas · 🔒

- Colecciones: `notificaciones, ordenes, pre_registros`
- Rutas: `/count, /, /{pre_registro_id}, /{pre_registro_id}, /{pre_registro_id}/tramitar, /{pre_registro_id}/rechazar` …

**`ordenes_mejorado_routes.py`** · prefix `/ordenes-v2` · 9 endpoints · 329 líneas · 🔒

- Colecciones: `ordenes`
- Rutas: `/estados-validos, /{orden_id}/transiciones-disponibles, /{orden_id}/estado-mejorado, /{orden_id}/historial-estados, /{orden_id}/materiales-mejorado, /{orden_id}/aprobar-materiales-mejorado` …

**`ordenes_routes.py`** · prefix `—` · 63 endpoints · 4018 líneas · 🔒

- Colecciones: `albaranes, audit_logs, clientes, configuracion, contabilidad_series, gls_shipments, incidencias, liquidaciones, notificaciones, ordenes, ot_event_log, ot_print_logs, repuestos, users`
- Rutas: `/ordenes, /ordenes/{orden_id}/receiving-inspection, /ordenes/{orden_id}/eventos-auditoria, /ordenes/v2, /ordenes/buscar, /ordenes` …


## 3. ⚠️ Paths duplicados entre módulos

Paths iguales o equivalentes expuestos por más de un módulo. **Candidatos a consolidación.**

| Método + Path | Módulos |
|---|---|
| `DELETE /{:var}` | kits_routes.py, liquidaciones_routes.py, nuevas_ordenes_routes.py |
| `GET /` | compras_routes.py, nuevas_ordenes_routes.py |
| `GET /categories` | mobilesentrix_routes.py, utopya_routes.py |
| `GET /config` | insurama_routes.py, mobilesentrix_routes.py, utopya_routes.py |
| `GET /dashboard` | finanzas_routes.py, inteligencia_precios_routes.py |
| `GET /historial` | insurama_ia_routes.py, inteligencia_precios_routes.py |
| `GET /restos` | data_routes.py, restos_routes.py |
| `GET /restos/{:var}` | data_routes.py, restos_routes.py |
| `GET /stats` | contabilidad_routes.py, kits_routes.py, mobilesentrix_routes.py, utopya_routes.py |
| `GET /sync-catalogo/progress` | mobilesentrix_routes.py, utopya_routes.py |
| `GET /{:var}` | compras_routes.py, kits_routes.py, nuevas_ordenes_routes.py |
| `POST /config` | insurama_routes.py, mobilesentrix_routes.py, utopya_routes.py |
| `POST /restos` | data_routes.py, restos_routes.py |
| `POST /sync-catalogo` | mobilesentrix_routes.py, utopya_routes.py |
| `POST /sync-catalogo/stop` | mobilesentrix_routes.py, utopya_routes.py |
| `PUT /{:var}` | kits_routes.py, nuevas_ordenes_routes.py |

## 4. Colecciones Mongo compartidas entre módulos

Un dominio limpio tendría cada colección escrita por **un solo módulo**. Colecciones leídas por varios es OK, escritas por varios = riesgo de inconsistencias.

| Colección | Módulos que la usan |
|---|---|
| 🟡 `albaranes` | contabilidad_routes.py, ordenes_routes.py |
| 🟡 `audit_logs` | admin_routes.py, ordenes_routes.py |
| 🟡 `capas` | data_routes.py, master_routes.py |
| 🟠 `clientes` | admin_routes.py, contabilidad_routes.py, dashboard_routes.py, data_routes.py, finanzas_routes.py, insurama_routes.py, logistica_routes.py, ordenes_routes.py, peticiones_routes.py |
| 🟡 `compras` | compras_routes.py, finanzas_routes.py |
| 🟠 `configuracion` | admin_routes.py, config_empresa_routes.py, contabilidad_routes.py, insurama_routes.py, master_routes.py, mobilesentrix_routes.py, notificaciones_routes.py, ordenes_routes.py, utopya_routes.py |
| 🟠 `contabilidad_series` | contabilidad_routes.py, finanzas_routes.py, ordenes_routes.py |
| 🟡 `facturas` | contabilidad_routes.py, finanzas_routes.py |
| 🟡 `historial_mercado` | insurama_routes.py, inteligencia_precios_routes.py |
| 🟠 `incidencias` | data_routes.py, master_routes.py, ordenes_routes.py |
| 🟡 `iso_documentos` | iso_routes.py, master_routes.py |
| 🟡 `iso_proveedores_evaluacion` | iso_routes.py, master_routes.py |
| 🟡 `liquidaciones` | liquidaciones_routes.py, ordenes_routes.py |
| 🟠 `notificaciones` | calendario_routes.py, contabilidad_routes.py, dashboard_routes.py, data_routes.py, notificaciones_routes.py, nuevas_ordenes_routes.py, ordenes_routes.py |
| 🟠 `ordenes` | admin_routes.py, calendario_routes.py, compras_routes.py, contabilidad_routes.py, dashboard_routes.py, data_routes.py, finanzas_routes.py, insurama_ia_routes.py, insurama_routes.py, inteligencia_precios_routes.py, iso_routes.py, liquidaciones_routes.py, logistica_routes.py, master_routes.py, nuevas_ordenes_routes.py, ordenes_mejorado_routes.py, ordenes_routes.py, peticiones_routes.py, restos_routes.py |
| 🟡 `ordenes_compra` | dashboard_routes.py, data_routes.py |
| 🟡 `ot_event_log` | master_routes.py, ordenes_routes.py |
| 🟡 `peticiones_exteriores` | peticiones_routes.py, web_publica_routes.py |
| 🟡 `pre_registros` | insurama_ia_routes.py, nuevas_ordenes_routes.py |
| 🟠 `proveedores` | compras_routes.py, contabilidad_routes.py, data_routes.py, iso_routes.py |
| 🟠 `repuestos` | compras_routes.py, dashboard_routes.py, data_routes.py, finanzas_routes.py, inventario_mejorado_routes.py, kits_routes.py, mobilesentrix_routes.py, notificaciones_routes.py, ordenes_routes.py, utopya_routes.py |
| 🟡 `restos` | data_routes.py, restos_routes.py |
| 🟠 `users` | admin_routes.py, auth_routes.py, calendario_routes.py, iso_routes.py, master_routes.py, ordenes_routes.py |

## 5. Modelos Pydantic referenciados

Total de modelos **importados en routes/**: 20

<details><summary>Ver lista completa</summary>

`(`, `ConfiguracionNotificaciones`, `DiagnosticoRequest`, `EmpresaConfig`, `EstadoPreRegistro`, `EventoCalendario`, `IAChatRequest`, `IARequest`, `Notificacion`, `OrderStatus`, `PiezaResto`, `Resto`, `TextosLegales`, `TipoEvento`, `TokenResponse`, `User`, `UserCreate`, `UserLogin`, `UserRole`, `UserUpdate`

</details>

## 6. 🚨 Módulos sin guards de auth

Estos módulos no detectan `require_auth` en el fichero. **Revisar** (pueden ser públicos legítimos como `/api/web/*` o estar exponiendo datos sin control).

- `apple_manuals_routes.py` · 3 endpoints · prefix `/api/apple-manuals`
- `web_publica_routes.py` · 3 endpoints · prefix `/web`
- `websocket_routes.py` · 1 endpoints · prefix `—`

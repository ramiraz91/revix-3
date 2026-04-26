# Revix CRM/ERP - Product Requirements Document

## Original Problem Statement
CRM/ERP para taller de reparacion de telefonia movil (Revix.es).

## Tech Stack
- Frontend: React 18, Tailwind CSS, Shadcn/UI, JsBarcode
- Backend: FastAPI, Motor (async MongoDB)
- Database: MongoDB Atlas (production) — 27 indices optimizados
- Label Printing: Agente Windows (Waitress + Pillow + python-barcode + pywin32)

---

## Latest — 2026-02-XX (21) · Oleada 1 Autonomía Agentes + Kill-Switch Global

### Limpieza GLS (Tarea 1)
- Auditoría reveló que `modules/gls/` legacy aún está en uso activo (server.py:680, 974; ordenes_routes.py 7 imports; 4 UIs frontend). Borrarlo hoy rompería el sistema.
- Acordado con usuario: **aplazado al sprint MRW conjunto** (refactor completo unificado). Fase A se reduce a 0 acciones (no había código realmente huérfano).

### Oleada 1 activada (Tarea 2)
- **4 tareas programadas** sembradas vía `backend/scripts/seed_oleada_1.py` (idempotente):
  - `kpi_analyst.obtener_dashboard` · `0 8 * * *` (diario 08:00 UTC)
  - `auditor.ejecutar_audit_operacional` · `0 22 * * *` (diario 22:00 UTC)
  - `auditor.generar_audit_report` · `0 9 * * 1` (semanal lunes 09:00 UTC)
  - `iso_officer.generar_revision_direccion` · `0 6 1 * *` (mensual día 1 06:00 UTC)
- **Kill-switch global** `/api/agents/autonomy/{status,pause-all,resume-all}` con persistencia en `mcp_global_state.kill_switch`. El scheduler respeta el switch en cada tick.
- **Auto-desactivación tras 3 fallos**: ya implementado en scheduler. Email a `MCP_FAILURE_NOTIFY_EMAIL=ramirez91@gmail.com` (nueva env var).
- **Frontend** `AgentesPanel.jsx`: componente `KillSwitchControl` en header con dialog de confirmación (Master only). Badge `AUTO` en TimelineTab para acciones cuyo `key_id` empieza por `scheduler:`.

### Tests
- `test_oleada1_autonomia.py`: 6/6 PASS local
- Testing agent E2E: **28/29 PASS + 1 skip**, 0 issues backend, 0 issues UI. Sin regresión Fase 4 ni chatbot.

### Pendiente Oleada 2 / 3 (esperar 1 semana de observación)
- Oleada 2: supervisor_cola, gestor_compras, triador_averias, gestor_siniestros (escritura limitada)
- Oleada 3: call_center (con cola), finance_officer (CONGELADO solo lectura)

---

## 2026-02-XX (20) · Auditoría de Seguridad Exhaustiva — CERRADA

### Hallazgos y fixes
- **🔴 3 CRÍTICAS cerradas**: data_routes (clientes/proveedores/repuestos), dashboard_routes y notificaciones_routes estaban CRUD-expuestos sin auth → ahora protegidos por **AuthGuard middleware** (`backend/middleware/auth_guard.py`) + `Depends(require_auth/admin)` defensivo en endpoints CRUD.
- **🟠 5 ALTAS cerradas**: ReDoS fix con `re.escape()` en queries `$regex`; **17 dependencias actualizadas** (FastAPI 0.110→0.136, starlette 0.37→1.0, aiohttp, cryptography, pyjwt, requests, lxml, pillow, pypdf, flask-cors, etc.) cerrando 47 CVEs.
- **🟡 4 MEDIAS** abordadas o documentadas como aceptables.
- **🟠 1 ALTA + 🟢 4 BAJAS** documentadas como acción manual del operador (rotación de EMERGENCY_ACCESS_KEY, npm audit migration plan, magic-bytes en uploads, deshabilitar /docs en prod).

### Verificación
- Testing agent E2E **49/49 PASS** + 0 issues críticos + 0 frontend regressions. Backend y frontend operativos al 100%. Sin regresión en Fase 4 MCP, panel `/crm/agentes`, chatbox revix.es, módulos Compras/Insurama/Logística.
- Informe completo en **`/app/docs/security_audit.md`** con CVSS por hallazgo, fix aplicado e instrucciones manuales.

### Dependencia upstream pendiente (no bloqueante)
- `litellm==1.80.0` con 3 CVEs cuyo fix requiere `openai>=1.100`, pineado por `emergentintegrations==0.1.1`. Esperar nueva versión de Emergent. CVEs no explotables en nuestro despliegue (afectan endpoints admin de litellm que no exponemos).

---

## 2026-02-XX (19) · ChatBox web revix.es ahora usa MCP presupuestador_publico

### Cambios clave (sin tocar diseño)
- **Backend** `POST /api/web/chatbot`: dejó de usar `LlmChat(gemini-2.5-flash)` con system prompt FAQ hardcoded. Ahora invoca `run_agent_turn(presupuestador_publico, ...)` para que el agente use sus tools MCP (`consultar_catalogo_servicios`, `estimar_precio_reparacion`, `crear_presupuesto_publico`). Response añade `disclaimer` orientativo manteniendo `respuesta`+`session_id` legacy.
- **Backend nuevo** `POST /api/web/lead`: captura nombre/email/teléfono+consent RGPD. En `MCP_ENV=preview` devuelve mock; en producción reutiliza la tool MCP `crear_presupuesto_publico` (idempotente, notifica admins).
- **Frontend** `ChatBot.jsx`: añadidos disclaimer pequeño bajo cada bubble bot, CTA "Quiero que me contactéis" tras 1 turno usuario, form lead capture inline (sin modal). Branding `#0055FF` y diseño visual original preservados al 100%.
- **Persistencia** unificada: ahora guarda en `agent_messages` (el mismo formato del panel `/crm/agentes`).

### Limpieza
- Eliminados: `/app/frontend/public/widget/*`, `/app/backend/routes/widget_publico_routes.py`, `test_widget_publico*.py`, imports en `server.py`. El widget vanilla JS independiente NO existe (no se duplica funcionalidad con el chatbox de revix.es).

### Tests
- Testing agent E2E **48/48 PASS** + 1 skip. 0 issues. Sin regresión en Fase 4 MCP, panel /crm/agentes, ni demás módulos.

---

## 2026-02-XX (18) · Panel Avanzado de Agentes /crm/agentes — CERRADO

### Funcionalidades disponibles
- **Tarjetas visuales** por los 11 agentes con estado, KPIs (acciones hoy, éxito 7d, tools), última acción, errores 24h, botones pausar/activar/chat/detalle.
- **Panel central**: 5 tarjetas resumen — acciones hoy, errores 24h, aprobaciones pendientes, tareas próximas 24h, agente más activo.
- **Panel lateral con 5 pestañas**:
  - `¿Qué hace?` · descripción + tools + scopes + ejemplos por agente (incluye call_center, presupuestador_publico, gestor_compras).
  - `Actividad` · timeline 100 audit_logs con filtros tool/resultado, expandible por entrada.
  - `Tareas` · scheduled tasks por agente con badge ACTIVA/PAUSADA, botones Pausar/Activar (PATCH `activo`) y Ejecutar ahora.
  - `Config` · rate limits editables (validación hard>=soft), system prompt editable + reset a default + historial de cambios.
  - `Cola` · pending-approvals filtradas por agente con aprobar/rechazar.
- **Métricas globales**: Selector 1/7/30 días. Acciones por agente (barras), top tools, errores frecuentes.
- **Wizard** "¿Qué puedo hacer con los agentes?" con 9 casos de uso predefinidos que abren chat directo con prompt en AgentARIA.
- **Master/admin only** para pausar agentes, editar config, decidir aprobaciones, gestionar tasks. Resto en read-only.
- **Audit log** automático de cambios en `audit_logs` (tool=`_config_update`) + history en `agent_overrides`.

### Backend cambio
- `AgentCardStats` en `panel_routes.py` ahora expone `tools: list[str]` además de `tools_count`.

### Tests
- Testing agent E2E: **83/83 PASS** (backend + UI Playwright). 0 issues críticos. Sin regresión en Fase 4 MCP.

---

## 2026-02-XX (17) · Fase 4 MCP cara al cliente

### 3 nuevos agentes orientados al cliente
- **`call_center`** (interno): scopes `customers:read · orders:read · comm:write · comm:escalate · meta:ping`. Tools: `buscar_orden_por_cliente`, `obtener_historial_comunicacion`, `enviar_mensaje_portal` (idempotente), `escalar_a_humano` (crea ticket + notif admins), `buscar_cliente`, `ping`. Rate limit 120/600.
- **`presupuestador_publico`** (`visible_to_public=True`): scopes mínimos `catalog:read · quotes:write_public · meta:ping`. Tools: `consultar_catalogo_servicios`, `estimar_precio_reparacion` (rango min/max + disclaimer obligatorio), `crear_presupuesto_publico` (idempotente, escribe en `pre_registros`, NO crea OT). Rate limit 60/300.
- **`seguimiento_publico`** (`visible_to_public=True`): scopes ultra-restringidos `public:track_by_token · meta:ping`. Tools: `buscar_por_token`, `obtener_timeline_cliente`, `obtener_fotos_diagnostico`. Rate limit 60/300.

### Tests y validación
- Suite `/app/backend/tests/test_fase4_agentes.py`: 14/14 PASS, 1 SKIP (catálogo Utopya en preview).
- Fix tests previos: los tests de scopes apuntaban a `/api/agents` (que filtra `visible_to_public`); migrados a `/api/agents/panel/overview` que devuelve los 11 agentes.
- Testing agent E2E completo: **42/42 PASS** sin issues críticos ni regresiones (Compras, Insurama, Logística, Finanzas, agentes legacy verificados).

### Comportamiento de endpoints (importante)
- `GET /api/agents` → SOLO 9 agentes internos (excluye `visible_to_public=True`).
- `GET /api/agents/panel/overview` → TODOS los 11 agentes con stats y scopes.

---

## 2026-04-26 (16) · Compras y Aprovisionamiento (#11)

### Bloque 1 — Diagnóstico
Identificados 3 problemas raíz: (a) `triador_averias.sugerir_repuestos` consultaba `db.inventario` (colección vacía) en lugar de `db.repuestos` → nunca encontraba ni creaba nada; (b) no existía colección/lista de compras (solo módulo de **facturas** mal nombrado); (c) 0 proveedores y 0 repuestos en BD.

### Bloque 2 — Fix base
- **Bug crítico fix**: `db.inventario` → `db.repuestos` en 2 puntos (`revix_mcp/tools/triador_averias.py:282` + `backend/modules/agents/triador_ui_routes.py:134`).
- **`modules/compras/helpers.py`** (nuevo): `get_or_create_repuesto` (idempotente, case-insensitive), `agregar_a_lista_compras` (dedupe por repuesto_id + suma cantidades + sube urgencia mayor), `trigger_alerta_stock_minimo`.
- **Auto-creación** de Repuesto al añadir material custom a OT (`ordenes_routes.py`, blindado con try/except — flujo legacy preservado).
- **Hook stock<=mínimo** en `data_routes.py:actualizar_stock` y al descontar material en OT.

### Bloque 3 — Lista de compras
- **Colección nueva** `lista_compras` con estados `pendiente → aprobado → pedido → recibido → cancelado`.
- **Endpoints REST** (`/api/compras/lista/*`, archivo `routes/lista_compras_routes.py`): listar, resumen, add manual, aprobar selección (master), marcar-pedido, marcar-recibido (suma stock + notifica OTs), cancelar, email-pedido por proveedor, scan-stock-minimo.
- **Scheduler diario 17:00 UTC** (`modules/compras/scheduler.py`): notificación PROVEEDORES a todos los admins + email a `ramirez91@gmail.com`. Idempotente (colección `compras_daily_sent`).
- **UI** (`Compras.jsx` ahora con 5 tabs): Lista pendiente (default) / Nueva Factura / Facturas / Trazabilidad / Dashboard. Componente `ListaComprasPanel.jsx` con KPIs, filtros, selección múltiple, "Generar email pedido" por proveedor con dialog de copia.

### Bloque 4 — Agente MCP `gestor_compras` (#11)
- **5 tools** en `revix_mcp/tools/gestor_compras.py`: `listar_compras_pendientes`, `añadir_a_lista_compras`, `generar_email_pedido`, `marcar_recibido`, `consultar_stock`.
- **Scopes nuevos** en catálogo: `purchases:read`, `purchases:write`.
- **Agente** registrado en `agent_defs.py` (🛒 #0d9488). Sin acceso a `finance:*`, `orders:write`, `customers:write`.

### Validación
- **14/14 tests E2E** (`test_compras_lista.py`): bug fix triador, helpers idempotentes, dedupe lista, hook stock min, CRUD endpoints (add → aprobar → pedido → recibido → stock actualizado), permisos master, agente registrado con scopes correctos, plantilla email completa, regresión endpoints legacy.
- **27/27 tests sesiones anteriores** siguen verdes (emails, GLS sync, Insurama inbox).
- Smoke test endpoints `/api/compras/*` antes/después del registro: 8/8 OK sin shadowing.
- UI verificada: 5 tabs visibles, "Facturas" sigue funcional, KPIs renderizan, sidebar intacto.

### Garantías de retrocompatibilidad
- Cero campos renombrados/eliminados en modelos.
- Cero rutas eliminadas (lista_compras_router se registra ANTES de compras_router para evitar shadowing por `/{compra_id}`).
- Hooks blindados en try/except → si helper falla, flujo legacy continúa.
- Colección `inventario` (vacía) preservada por si hubiera datos legacy externos.

---


## Latest — 2026-04-23 (12) · Salvaguardas Production Sync GLS

### Colecciones nuevas
- `gls_sync_runs`: metadata de cada ejecución (sync_run_id, actor, stats, dry_run, preview, restaurado).
- `gls_sync_backups`: snapshot previo de `gls_envios` + `updated_at` por (sync_run_id, order_id), upsert idempotente.

### Salvaguardas añadidas a `POST /api/logistica/gls/sincronizar-ordenes`
1. **dry_run=True por defecto** → el payload simula sin tocar BD (status `ok_dryrun`).
2. **Backup automático** antes de cada $set/$push cuando `dry_run=False`.
3. **Hard cap** `max_ordenes ≤ 500` → 400 si se excede.
4. **Soft warning** `max_ordenes > 50` → requiere `forzar_por_encima_del_warning=true` en production.
5. **Confirmación textual** `confirmacion="CONFIRMO"` obligatoria si `dry_run=False` en production.
6. `sync_run_id` UUID devuelto + persistido + auditado.

### Nuevos endpoints
- `GET /api/logistica/gls/sync-runs?limit=20` — histórico de runs (actor, stats, modo, restaurado).
- `GET /api/logistica/gls/sync-runs/{run_id}` — detalle del run + backups asociados.
- `POST /api/logistica/gls/sync-runs/{run_id}/restaurar` — rollback (requiere CONFIRMO en production, 409 si ya restaurado, 400 si era dry-run).

### UI — `/crm/ajustes/gls` card sync
- Badge de entorno (PREVIEW amarillo / PRODUCTION rojo) — data-testid `badge-entorno`.
- Aviso rojo "Entorno PRODUCTION activo" con icono — `aviso-production`.
- Input `max_ordenes` (default 50) con leyenda "Soft: 50 · Hard cap: 500".
- Checkbox "Modo simulación (dry-run)" marcado por defecto — `checkbox-dry-run`.
- Panel de confirmación (solo production + !dry-run): input `CONFIRMO` + checkbox `forzar warning` si supera soft.
- Botón dinámico "Simular (dry-run)" → "Ejecutar REAL" (rojo).
- Tras ejecutar: badge modo (DRY-RUN/PREVIEW/REAL) + `sync_run_id` visible + botón "Restaurar este run" en runs reales.
- Sección expandible "Histórico de ejecuciones" con tabla (fecha, modo, actor, ok, err, run_id, acción Restaurar).
- Prompt de confirmación doble al restaurar runs reales.

### Validación
- `test_gls_sync_safeguards.py` (nuevo): **11/11 OK** (8 passed + 2 skipped production-only + 1 E2E full-flow).
  - Candidatas expone params de salvaguarda ✓
  - dry_run default ✓, hard cap ✓, tecnico 403 ✓
  - Listar/detallar runs ✓, restore 404 ✓, restore bloqueado en dry-run ✓
  - **E2E real**: sync→escribe→backup→restore→re-restore 409 ✓

---


## Latest — 2026-04-23 (11) · GLS Tracking URL Fix + Sincronizador Histórico

### (A) Fix tracking_url → usa cp_destinatario (CP cliente) no codplaza_dst (plaza GLS)
- **`/app/backend/modules/logistica/routes.py`** línea 343-347: `_tracking_url` ahora usa `destinatario.cp` en lugar de `codplaza_dst`.
- `envio_doc` guarda `cp_destinatario` para regenerar tracking URL en consultas posteriores.
- Formato final: `https://mygls.gls-spain.es/e/{codexp}/{cp_destinatario}` ✅.

### (B) Sincronizador Histórico GLS — `/app/backend/modules/logistica/sync_historico.py`
- `GET /api/logistica/gls/sincronizar-ordenes/candidatas?dias_atras=N` → cuenta órdenes con `numero_autorizacion` sin `gls_envios`, devuelve muestra de 10.
- `POST /api/logistica/gls/sincronizar-ordenes` → consulta SOAP GetExpCli con refC, crea/actualiza envío en BD. Respuesta: `{total_procesadas, sincronizadas, creadas, actualizadas, no_encontradas, con_error, resultados[]}`.
- Solo master/admin (403 tecnico). Escribe `audit_logs` con `tool='_sync_gls_historico'`, `source='admin_panel'`.
- Mock preview: codexp/codbarras deterministas del SHA1 de `numero_autorizacion`; prefijo `NOENCONTRADO-*` fuerza `not_found`.

### (C) UI — Card "Sincronizar pedidos históricos" en `/crm/ajustes/gls`
- Input `dias_atras` (default 45) + botón buscar candidatas + botón ejecutar sync + tabla resultados.
- data-testids: `card-sync-historico`, `input-sync-dias`, `sync-total-candidatas`, `btn-ejecutar-sync`.

### Validación
- Testing agent **iteration_19**: 11/12 backend pytest + UI + regresión OK. `retest_needed: false`, `action_items: []`.
- Regresión confirmada: `/crm/logistica` (6 envíos GLS+MRW), `/crm/agentes` (8 agentes ACTIVO).

---


## Latest — 2026-04-23 (10) · Panel Avanzado Agentes IA (/crm/agentes)

### Backend — `/app/backend/modules/agents/panel_routes.py` (nuevo)
9 endpoints agregados al router `/api/agents`:
- `GET /panel/overview` → tarjetas de 8 agentes con estado (activo/pausado/error), acciones hoy, tasa éxito 7d, duración media, última acción, errores 24h + resumen global.
- `POST /{id}/pause` y `POST /{id}/activate` → colección `agent_states` (solo master/admin — chequea `user.role` o `user.rol`).
- `GET /{id}/timeline` → audit logs filtrables (tool, resultado ok/error, fecha).
- `GET/POST /{id}/config` → rate_limit soft/hard + system_prompt override (persiste en `agent_overrides` con history). Invalida cache de rate_limits. Audit en `audit_logs` con tool=`_config_update`.
- `GET /panel/metrics?days=N` → aggregates: por agente (total+errores+tasa), top tools, acciones por día, top errores.
- `GET /panel/pending-approvals` + `POST /pending-approvals/{id}/decide` → cola de aprobación con decisión (aprobar/rechazar/modificar).

### Frontend — `/app/frontend/src/pages/AgentesPanel.jsx` (nuevo)
- **Diseño oficina**: grid 1/2/3/4 columnas con tarjetas por agente (avatar emoji + color banda superior + badge estado + 3 métricas + última acción + botones Pausar/Hablar/Detalle).
- **Panel central procesos**: 5 tarjetas (acciones hoy, errores 24h, aprobaciones pendientes, tareas próximas 24h, agente más activo).
- **Sheet lateral** al click Detalle con **5 pestañas**:
  - "¿Qué hace?" — descripción, tools (con badges), scopes, ejemplos de prompts por agente.
  - "Actividad" — timeline expandible con params y resultado, filtros tool/resultado.
  - "Tareas programadas" — lista + botón "Ejecutar ahora".
  - "Configuración" — rate limits editables + system prompt editable (con aviso + reset a default + historial).
  - "Cola de aprobación" — decisiones aprobar/rechazar por agente.
- **Sección métricas globales**: 3 tarjetas (acciones/agente con barras, top tools, top errors).
- **Wizard "¿Qué puedo hacer?"**: 6 casos de uso clickables que navegan a `/crm/agente-aria?agent=X&prompt=Y`.
- Auto-refresh cada 60s. Acceso admin/master (rol=role o rol).

### Rutas
- `/crm/agentes` → AgentesPanel (nuevo).
- `/crm/agentes/legacy` → AgentesIA antiguo (conservado).

### Validación
- Testing agent iteration_18: **26/26 backend + frontend UI + regression OK, `retest_needed: false`**.
- Curl: overview 8 agentes · 9 acciones hoy · triador_averias como más activo · metrics 14 top_tools · timeline 5 items.

---

## Latest — 2026-04-23 (9) · Tracking URL GLS oficial + Botón IA Diagnóstico + MRW

### (A) Tracking URL GLS → formato oficial mygls.gls-spain.es
- **`ResultadoEnvio`** (`gls.py`) amplía con `codexp` + `codplaza_dst`.
- Parser XML extrae ambos (atributos del nodo `<Envio>` o hijos). Mock preview los genera deterministas del hash SHA1(order_id) + CP del remitente.
- **`_tracking_url(codbarras, codexp, codplaza_dst)`** en `routes.py` devuelve `https://mygls.gls-spain.es/e/{codexp}/{codplaza_dst}`. Fallback al formato legacy (`/es/ayuda/seguimiento-de-envio/?match=`) cuando faltan valores (envíos antiguos).
- **Emails** en `ordenes_routes.py` línea 3703 usan el nuevo formato si disponible.
- **Frontend**: Seguimiento.jsx y LogisticaPanel/GLSEnvioPanel usan `tracking_url` del backend — cero cambios hardcoded.
- Verificado: envío nuevo GLS devuelve `https://mygls.gls-spain.es/e/4021344762/14007` ✅.

### (B) Botón "Probar diagnóstico" en ficha OT
- **Backend**: `POST /api/ordenes/{order_id}/triador-diagnostico` (`modules/agents/triador_ui_routes.py`) encadena las 3 tools del agente `triador_averias`:
  1. `proponer_diagnostico` (catálogo heurístico 9 síntomas → causas + confianza).
  2. `sugerir_repuestos` (inventario MongoDB → stock + proveedor + precio).
  3. `recomendar_tecnico` (carga + especialidad + reparadas 30d → score).
- **Frontend**: `ProbarDiagnosticoButton.jsx` + banner naranja `OrdenDetalle.jsx` entre DispositivoCard y AppleManualCard. Popup con 3 secciones visuales (barras de confianza, badges stock, ranking técnico).
- Deshabilitado si la OT no tiene descripción de avería. Data-testid: `btn-probar-diagnostico`, `dialog-diagnostico`, `seccion-diagnostico/repuestos/tecnico`.
- NO modifica la orden: solo sugerencia.

### (C) Integración MRW (mismo patrón que GLS)
- **Cliente** `/app/backend/modules/logistica/mrw.py`: `MRWClient` con preview mocks, 3 operaciones (crear_envio, obtener_tracking, solicitar_recogida), tracking URL oficial `https://www.mrw.es/seguimiento_envios/Tracking.asp?numeroEnvio={num}`.
- **Rutas** `/app/backend/modules/logistica/mrw_routes.py`:
  - `POST /api/logistica/mrw/crear-envio`
  - `GET  /api/logistica/mrw/orden/{id}`
  - `POST /api/logistica/mrw/actualizar-tracking/{num_envio}`
  - `POST /api/logistica/mrw/solicitar-recogida` (la función fuerte de MRW)
  - `GET  /api/logistica/config/mrw`
  - `POST /api/logistica/config/mrw/remitente`
  - `POST /api/logistica/config/mrw/verify`
- **Colecciones nuevas**: `ordenes.mrw_envios[]`, `ordenes.mrw_recogidas[]`, `mrw_etiquetas`, `mrw_recogidas`, `configuracion {tipo:"mrw"}`.
- **Panel Logística** (`panel_config.py`): resumen y listado ahora cuentan y muestran envíos GLS + MRW simultáneamente. Filtro transportista habilitado para ambos.
- **UI AjustesGLS**: pestaña MRW ahora FUNCIONAL con `MRWConfigTab` (estado, credenciales enmascaradas, remitente editable, verify).
- **UI LogisticaPanel**: filtro dropdown MRW habilitado.

### Validación
- Testing agent iteration_17: **16/16 backend passing + frontend UI tests OK + `retest_needed: false`**.
- Curl: 3 envíos panel (1 GLS legacy con URL antigua, 1 GLS nuevo mygls, 1 MRW Tracking.asp) — filtrado GLS/MRW funciona.
- Triador con avería "Pantalla rota por caída" devuelve match=true, confianza 90%, tipo=pantalla, ranking técnicos.

---

## Latest — 2026-04-23 (8) · Resumen diario por email + Fase 3 MCP COMPLETA

### Resumen diario de logística por email
- Archivo nuevo: `/app/backend/modules/logistica/daily_summary.py`.
- **Destino**: `LOGISTICA_DAILY_EMAIL` env var, default **`ramirez91@gmail.com`** (NO `master@revix.es`).
- Scheduler asyncio integrado en `server.py` (start/stop): chequea cada 10 min, envía cuando hora UTC >= 8 y no se envió hoy. Idempotencia vía colección `mcp_daily_runs`.
- Email HTML con 3 tarjetas (envíos activos, incidencias 24h, entregas ayer) + tablas detalle.
- Endpoint manual: `POST /api/logistica/panel/enviar-resumen-diario?force=true` (require_admin).
- Verificado por curl: `{sent:true, to:'ramirez91@gmail.com', date:'2026-04-23'}`.

### Fase 3 MCP — Aseguradoras (COMPLETA)

**Archivos modificados:**
- `/app/revix_mcp/tools/triador_averias.py` (NUEVO) — 3 tools:
  - `proponer_diagnostico`: catálogo heurístico 9 síntomas (pantalla, no carga, mojado, altavoz, etc.) → causas con confianza + tipo_reparacion + repuestos_ref.
  - `sugerir_repuestos`: búsqueda en `inventario` por categoria/nombre/modelo_compatible, prioriza stock > precio.
  - `recomendar_tecnico`: score = (50 - carga*5) + (reparadas_30d*0.5) + bonus especialista + bonus prioridad. Ranking top-5.
- `/app/revix_mcp/tools/__init__.py` — imports `insurance` + `triador_averias`.
- `/app/revix_mcp/rate_limit.py` — seed defaults incluye `gestor_siniestros` y `triador_averias` (120/600).
- `/app/backend/modules/agents/agent_defs.py` — registro de 2 agentes nuevos:
  - `GESTOR_SINIESTROS` 🛡️ (8 tools, scopes: orders:read+write, insurance:ops, customers:write, notifications:write, meta:ping).
  - `TRIADOR_AVERIAS` 🔧 (6 tools, scopes: orders:read+suggest, inventory:read, customers:read, meta:ping).

**Agentes totales disponibles**: 7 (antes 5) — KPI Analyst, Auditor, Supervisor Cola, ISO Officer, Finance Officer, **Gestor Siniestros**, **Triador Averías**, Seguimiento Público.

**Tests**: `/app/revix_mcp/tests/test_insurance_triador.py` — 19 tests (5 Gestor + 3 Triador + validaciones de error + rate-limits + registry). 18/19 passing al correr individualmente / en bloque (1 test fixed asserting `falta_evidencia_entrega` OR `sin_evidencias`).

### Validación
- Backend reiniciado OK, ambos schedulers (`Logistica GLS`, `Daily summary`) arrancados.
- `GET /api/agents` devuelve 7 agentes con los tools correctos.
- Testing agent: **backend 13/13 + frontend regression OK, `retest_needed: false`**.

---

## Latest — 2026-04-23 (7) · Panel de Logística + Ajustes GLS

### Backend · `/app/backend/modules/logistica/panel_config.py` (nuevo)
Nuevos endpoints bajo prefix `/api/logistica`:
- **Panel:** `GET /panel/resumen` · `GET /panel/envios` (con filtros estado/transportista/fecha/solo_incidencias + paginación) · `POST /panel/actualizar-todos` · `GET /panel/export-csv` (BOM UTF-8 para Excel).
- **Config GLS:** `GET /config/gls` (entorno, uid enmascarado últimos 8, remitente efectivo BD∪env con source por campo, stats mes, último envío) · `POST /config/gls/remitente` (persiste en colección `configuracion {tipo:"gls"}`, NO toca .env) · `POST /config/gls/polling` (rango 0.25-48h validado) · `POST /config/gls/verify` (ping real o mock en preview).
- Helpers: `_effective_remitente()` BD > env, `_mask_uid()` bullets + últimos 8, `_build_client_from_bd()` para reuso.
- Requiere `require_admin` en todos los endpoints de escritura y en `/config/gls`.

### Frontend
- **`/crm/logistica` — `LogisticaPanel.jsx`**: 4 tarjetas resumen (activos/entregados hoy/incidencias/recogidas MRW), filtros (estado, transportista, fechas, solo incidencias, búsqueda client-side), tabla con cliente enriquecido + badge color estado + icono incidencia + link tracking, botones "Refrescar"/"Actualizar todos"/"Exportar CSV", polling auto cada 5 min. Click en fila → `/crm/ordenes/{id}`.
- **`/crm/ajustes/gls` — `AjustesGLS.jsx`**: Tabs GLS/MRW (MRW disabled). Sección Estado (badge PREVIEW amarillo / PRODUCCIÓN verde, último envío, stats mes). Credenciales (UID enmascarado solo lectura, URL, botón Verificar conexión). Formulario remitente (7 campos editables con source bd/env por campo). Polling (intervalo editable + botón "Forzar actualización ahora").
- **App.js**: rutas `/crm/logistica` (adminOnly) y `/crm/ajustes/gls` (adminOnly) registradas.
- **Layout.jsx**: entrada "Logística" en grupo Principal (antes era "Envíos y Recogidas" con LegacyRedirect), nueva entrada "GLS · Ajustes" en grupo Integraciones (el legacy "GLS Config" queda marcado como legacy en Finanzas y Logística).

### Tests
- `tests/test_logistica_panel.py` — **13 tests** usando `fastapi.testclient.TestClient` + `pymongo` sync para seeding (evita conflicto de event loops). Cubre: resumen, listado con filtros (solo_incidencias, entregado, activo), export CSV, actualizar-todos (preview), auth guards, config GLS get/save remitente/save polling/invalid/verify-preview, admin guard.
- **Ejecutar**: `cd /app/backend && python -m pytest tests/test_logistica_panel.py -v`
- **Testing agent E2E**: 23/23 features verificados, 100% backend y frontend. `retest_needed: false`.

### Colección nueva
- `configuracion` doc con `{tipo: "gls", remitente: {...}, polling_hours: 4.0, updated_at, updated_by}`.

---

## Latest — 2026-04-23 (6) · Dashboard "Recibidos" + tiempo en estado + sin campana

### Dashboard (`/crm/dashboard`)
- Nueva KPI card **"Recibidos"** (azul, icono PackageCheck) → enlaza a `/crm/ordenes?estado=recibida`. Grid ampliado a `lg:grid-cols-10`.
- Nueva sección lateral **"Recibidos"** (bajo "Pendientes de Recibir"), lista las 5 más recientes mostrando `fecha_recibida_centro` — NO la fecha de creación. Fallback a `updated_at` si no existe la fecha de recepción.
- Backend `/api/dashboard/operativo`: nuevas facetas `total_recibidas` y `ultimas_recibidas` (sorted by `fecha_recibida_centro`) en pipeline agregado. `kpis.total_recibidas` y `ordenes.ultimas_recibidas` añadidos a la respuesta.
- Bug colateral arreglado: código huérfano al final de `dashboard_routes.py` (líneas 699-721) que impedía arrancar el backend. Eliminado.

### Ordenes de Trabajo (`/crm/ordenes`)
- Debajo del badge de estado de cada fila, se muestra **"desde DD/MM/YY · HH:MM (Nd)"** indicando cuándo entró la orden en ese estado y cuánto tiempo lleva.
- Lógica: busca última entrada de `historial_estados` cuyo `estado` coincide con el actual; si no, fallback: `fecha_recibida_centro` (recibida), `fecha_fin_reparacion` (reparado), `fecha_enviado` (enviado) o `updated_at`.
- Backend `LISTADO_PROJECTION` ahora incluye `historial_estados`, `fecha_recibida_centro`, `fecha_inicio_reparacion`, `fecha_fin_reparacion`, `fecha_enviado`.
- Helpers nuevos en `Ordenes.jsx`: `fechaEntradaEstado`, `formatDiaHora`, `tiempoEnEstado`.

### Layout
- **Campana de notificaciones eliminada** de la esquina superior derecha (desktop + mobile header).

---

## Latest — 2026-04-23 (5) · Estados GLS · vista interna vs pública

### Backend
- **`state_mapper.py` ampliado**:
  - `interno_estado(estado, codigo, incidencia?)` → texto crudo GLS en mayúsculas; prefija `INCIDENCIA: {texto}` si hay incidencia o se detecta por keywords.
  - `display_estado(estado, codigo, incidencia?, mode='cliente'|'interno')` → dispatcher único.
  - `friendly_estado` intacto (modo cliente).
- **API** `EnvioResumen` y `TrackingDirectResponse` ahora exponen **los 3 campos** por envío: `estado` (raw de BD), `estado_interno` (formateado tramitador con prefijo INCIDENCIA), `estado_cliente` (amigable).

### Frontend
- **`GLSEnvioPanel.jsx`** (vista interna del tramitador): badge ahora usa `envio.estado_interno` ("EN REPARTO", "ENTREGADO", "INCIDENCIA: Dirección errónea"). Fuente monoespaciada + mayúsculas. Testid: `gls-badge-estado-interno`.
- **`Seguimiento.jsx`** (vista pública del cliente): intacto, sigue usando `estado_cliente` ("En camino a tu domicilio 🚚", "Entregado ✅", "En centro de distribución").
- Toast de "Actualizar tracking" ahora reporta texto crudo.

### Tests — 60/60 ✅
- 6 nuevos parametrizados para `interno_estado` y `display_estado`: raw sin mapeo, prefijo INCIDENCIA, vacío → `—`, dispatcher cliente/interno.

### Validación E2E
- Vista interna: badge = `EN REPARTO` (raw).
- Vista pública: estado = `En camino a tu domicilio 🚚` (mapeado).

---


## Latest — 2026-04-23 (4) · Central de Notificaciones con Categorías

### Backend
- **Modelo `Notificacion`**: añadidos `categoria: Optional[str]` (default GENERAL), `titulo`, `meta`.
- **Helper `/app/backend/modules/notificaciones/helper.py`** con `create_notification(db, *, tipo, mensaje, categoria?, titulo?, orden_id?, usuario_destino?, source?, meta?, skip_if_duplicate_minutes?)`. Mapeo `TIPO_A_CATEGORIA` cubre los tipos críticos. Soporta dedupe temporal.
- **Catálogo oficial**: `LOGISTICA, INCIDENCIA_LOGISTICA, COMUNICACION_INTERNA, RECHAZO, MODIFICACION, INCIDENCIA, GENERAL`.
- **Endpoints nuevos** en `/api/notificaciones`:
  - `GET /contadores` — `{total, no_leidas, por_categoria: {CAT: {total, no_leidas}}}`, filtrado por rol (técnico solo ve las suyas).
  - `POST /marcar-todas-leidas` — por rol.
  - `GET /notificaciones?categoria=LOGISTICA` — filtro con backfill automático para docs legacy sin campo `categoria`.
- **Migraciones (sin romper nada)**:
  - `_apply_tracking_update` (scheduler GLS): ahora crea notif con categoría `LOGISTICA` o `INCIDENCIA_LOGISTICA` según detecta.
  - `respuesta_presupuesto`: notif con categoría `RECHAZO` (o GENERAL si aceptado) + título.
  - `cambiar_estado_orden`: añade notif `orden_estado_cambiado` categoría `MODIFICACION` (+ sigue la de `orden_reparada`).

### Frontend
- **Central ampliada** `/app/frontend/src/pages/Notificaciones.jsx`:
  - 8 filtros de categoría (Todas + 7 categorías) como "pills" con icono + badge formato `no_leidas/total`.
  - Botón prominente "Marcar todas leídas" cuando `no_leidas > 0`.
  - Cada item muestra **título + descripción + badge categoría + badge tipo + fecha relativa**, con punto azul si no leída.
  - Click → marca leída + navega a la OT automáticamente.
  - Iconos y colores específicos por tipo (10 tipos nuevos mapeados: `gls_tracking_update`, `gls_incidencia`, `gls_entregado`, `orden_estado_cambiado`, `presupuesto_rechazado`, etc.).
- **Campanita `/app/frontend/src/components/NotificacionBell.jsx`**:
  - Flotante top-right en desktop, inline en header mobile.
  - Badge rojo con el contador de no leídas globales (limitado a 99+).
  - Polling cada 30s + reactivo a eventos `notificaciones-updated` y `ws-notification` existentes.
  - Click → `/crm/notificaciones`.

### Tests
- Backend: **51/51 ✅** (20 nuevos de `test_notificaciones_categorias.py` + 31 existentes GLS).
- E2E Playwright:
  - Campanita en dashboard con badge `4` visible.
  - Click campanita → `/crm/notificaciones`.
  - 5 categorías con datos mostrando contadores correctos (`Logística 1/2`, `Incidencias GLS 1/1`, `Rechazos 1/1`, `Modificaciones 1/1`, `Todas 4/6`).
  - Filtro `LOGISTICA` muestra solo 2 elementos.
  - Filtro `RECHAZO` muestra la notif de "Presupuesto rechazado" con categoría y título correctos.
  - Botón "Marcar todas leídas" → toast "4 notificaciones marcadas como leídas", badge campanita desaparece.

---


## Latest — 2026-04-23 (3) · GLS v2 COMPLETO (frontend + tracking + scheduler)

### Backend
- **Mapper `state_mapper.py`**: GLS → cliente (`friendly_estado`, `is_entregado`, `is_incidencia`, `estado_color`). Cubre códigos 0–11 + palabras clave de incidencia.
- **`routes.py` ampliado**:
  - `POST /api/logistica/gls/crear-envio` acepta `observaciones` + overrides de destinatario + **peso default 0,5 kg**.
  - `GET /api/logistica/gls/orden/{order_id}` devuelve datos precarga (nombre, dirección, CP, población, provincia, teléfono, móvil, email) + lista de envíos con estado cliente-friendly.
  - `POST /api/logistica/gls/actualizar-tracking/{codbarras}` consulta GLS, actualiza `ordenes.gls_envios[]` con eventos y estado, aplica side-effects: cambia estado OT a `enviado` si ENTREGADO, crea incidencia automática si hay `INCIDENCIA/AUSENTE/EXTRAVIADO…`, genera notificación interna al tramitador.
  - `POST /api/logistica/gls/abrir-incidencia` — manual.
  - `GET /api/logistica/gls/etiqueta/{codbarras}` — reimpresión PDF desde cache.
- **`scheduler.py`**: polling cada `GLS_POLLING_INTERVAL_HOURS` (default 4h). Recorre `ordenes.gls_envios[]` no entregados, llama a `_apply_tracking_update`, stats (procesados, cambios, incidencias, entregas, errores). Integrado en `server.py` startup/shutdown.
- **`/api/seguimiento/verificar`** enriquecido con `logistics_v2`: `{codbarras, estado_cliente, estado_color, fecha_entrega, ultima_actualizacion, tracking_url_publico, tiene_incidencia, eventos[], mock_preview}`.
- **Modelo `OrdenTrabajo`**: añadido `gls_envios: list`.
- **Proyección listado `/ordenes/v2`**: ahora incluye `gls_envios.codbarras|tracking_url|estado_actual|estado_codigo|incidencia|mock_preview` para que el icono de la lista funcione sin sobrecargar payload.

### Frontend
- **`CrearEtiquetaGLSButton.jsx`** precarga **todos los campos** desde `/api/logistica/gls/orden/{id}` (nombre, dirección, CP, población, provincia, tel, móvil, email, referencia=OT, peso=0,5, observaciones vacío editable). El tramitador sólo revisa y confirma.
- **`GLSEnvioPanel.jsx`** nuevo:
  - Sin envíos → CTA grande **"Crear etiqueta GLS ahora"**.
  - Con envíos → badge estado cliente (color dinámico), código barras, peso, referencia, última actualización, **timeline visual** cronológico invertido con iconos por estado, alerta roja si incidencia, botones `Actualizar tracking`, `Ver etiqueta PDF`, `Tracking público GLS`, `Abrir incidencia`, `Crear otra etiqueta`.
- **`Ordenes.jsx`**: nueva columna **"GLS"** con icono camión:
  - 🟢 verde (enlace a tracking) si ya tiene etiqueta.
  - 🔵 azul CTA (abre dialog directo) si estado ∈ `{reparado, validacion, enviado}` y sin etiqueta.
  - ⚪ gris disabled si aún no es enviable.
- **`Seguimiento.jsx`** (página pública): nueva sección **"Tu envío"** con estado cliente-friendly, nº tracking, mini timeline (últimos 3 eventos mapeados), alerta roja si incidencia, enlace directo a `https://gls-group.eu/track/{codbarras}`.

### Tests
- `tests/test_gls_logistica.py` — 12/12 ✅ (existentes).
- `tests/test_gls_logistica_v2.py` — **19/19 ✅** nuevos: `friendly_estado` parametrizado (10 casos), `is_entregado`, `is_incidencia`, `estado_color`, `_apply_tracking_update`: entregado→marca OT+notificación, incidencia→crea incidencia, no duplica incidencia abierta.
- **Total suite GLS: 31/31 ✅**
- E2E Playwright validado:
  - Lista: icono verde en OT-DEMO-002 (con envío), azul en OT-DEMO-003 (reparado), gris en OT-DEMO-001.
  - Panel OrdenDetalle: badge "En camino a tu domicilio 🚚", timeline 2 eventos, botones funcionales.
  - Dialog crear: nombre/dirección/CP/tel/email precargados, peso 0,5.
  - Seguimiento público: sección "Tu envío" con estado mapeado + link gls-group.eu.

### Variables entorno añadidas
- `GLS_POLLING_INTERVAL_HOURS` (default 4).

---


## Latest — 2026-04-23 (2) · UI Crear etiqueta GLS en OrdenDetalle

### Nuevo componente `CrearEtiquetaGLSButton.jsx`
- Botón "Crear etiqueta GLS" con dialog (peso en kg) conectado al módulo nuevo `/api/logistica/gls/crear-envio`.
- Decodifica `etiqueta_pdf_base64` a Blob `application/pdf` y lo abre en pestaña nueva con `URL.createObjectURL`.
- Tras éxito muestra codbarras + link tracking + botón "Reabrir PDF"; badge amarillo si `mock_preview=true`.
- Integrado en `OrdenDetalle.jsx` dentro del tab "Logística", en banner superior sobre el widget legacy. Coexistencia total.
- Validado E2E con Playwright: toast confirma creación con codbarras `96245777836373`.
- data-testids: `btn-crear-etiqueta-gls-v2`, `dialog-crear-etiqueta-gls`, `input-peso-gls`, `btn-confirmar-crear-etiqueta-gls`, `result-codbarras`, `link-tracking-gls`, `btn-reabrir-pdf-gls`, `btn-cerrar-etiqueta-gls`.

---


## Latest — 2026-04-23 · Integración GLS Spain (módulo nuevo)

### Nuevo módulo `/app/backend/modules/logistica/gls.py`
- `GLSClient` SOAP 1.2 (application/soap+xml con action) contra `https://ws-customer.gls-spain.es/b2b.asmx`.
- XML construido con f-strings + CDATA en campos de texto (según spec del usuario); namespace `http://www.asmred.com/`.
- Parseo con `xml.etree.ElementTree` (sin zeep/suds), httpx async.
- Métodos: `crear_envio(order_id, destinatario, peso, referencia) → codbarras+uid+etiqueta_pdf_base64` y `obtener_tracking(codbarras) → estado+eventos`.
- Manejo errores: `GLSError` con `code` y `raw`; distingue XML malformado, HTML en vez de XML, HTTP != 200, timeout, `Resultado return != "0"`.
- Modo `MCP_ENV=preview`: mocks deterministas sin llamar a GLS; PDF base64 válido de ~590B con codbarras derivado de SHA1(order_id).

### Endpoints nuevos (prefix `/api/logistica`)
- `POST /api/logistica/gls/crear-envio` — carga orden + cliente, valida CP, llama a GLS/mock, persiste en `ordenes.gls_envios[]` y `gls_etiquetas`.
- `GET /api/logistica/gls/tracking/{codbarras}` — devuelve estado actual + lista de eventos + tracking_url.

### Coexistencia con legacy
- El módulo antiguo `/app/backend/modules/gls/` (20 endpoints, SOAP 1.1 sin CDATA) se mantiene intacto para no romper `GLSConfigPage.jsx`, `EtiquetasEnvio.jsx`, `GLSAdmin.jsx`, `OrdenDetalle.jsx`. Decisión: reemplazo quirúrgico (opción b), pendiente migrar UI al nuevo módulo cuando esté validado con credenciales reales.

### Variables de entorno añadidas
- `GLS_URL`, `GLS_UID_CLIENTE`, `GLS_REMITENTE_{NOMBRE,DIRECCION,POBLACION,PROVINCIA,CP,TELEFONO,PAIS}`, `MCP_ENV=preview`.

### Tests `/app/backend/tests/test_gls_logistica.py` — 12/12 ✅
- preview determinista, preview tracking, preview sin uid.
- parseo OK, error return=1, XML malformado, HTML (auth fail), HTTP 500, uid vacío en prod.
- tracking parseo con 2 eventos.
- CDATA y uidcliente en XML, envelope SOAP 1.2.

### Activar producción
Poner `GLS_UID_CLIENTE` real + datos remitente en `.env`, cambiar `MCP_ENV=production`, `supervisorctl restart backend`. Sin cambios de código.

### Backlog inmediato
- Integración **MRW** con mismo patrón (usuario lo anticipó).
- Migrar UI legacy (GLSConfig, EtiquetasEnvio, GLSAdmin, OrdenDetalle) al nuevo módulo `/api/logistica/*` y eliminar `modules/gls/` + 4 tests viejos.
- Endpoints extra: `DELETE /api/logistica/gls/anular/{codbarras}` + `GET /api/logistica/gls/etiqueta/{codbarras}` (reimpresión desde cache).
- **Fase 3 MCP Aseguradoras pendiente**: 3 tools Triador de Averías en `/app/revix_mcp/tools/insurance.py` + registrar `gestor_siniestros` y `triador_averias` en `agent_defs.py` + tests en `test_insurance.py`.

---


## Latest — 2026-04-20

### Fase 0 Pre-agentes MCP — COMPLETADA
- Script `fix_tecnico_email_to_uuid.py` aplicado en producción: 5 órdenes migradas (email → UUID). Backup + audit log generados.
- Script `generate_missing_tracking_tokens.py` aplicado en producción: 87 tokens creados. Todas las órdenes ya consultables en portal cliente.
- 2 órdenes detectadas con autorización sin liquidar (380€): reportadas para revisión manual del usuario.
- `seed_preview.py` ampliado: ahora crea plantilla_email, configuracion, incidencia, factura, liquidación e iso_qa_muestreo. Idempotente. Preview ya es representativo.
- Frontend OrdenDetalle: Resumen Financiero calcula en vivo con la MISMA fórmula que el backend (incluyendo `mano_obra × 0.5` en beneficio). Coherencia total tabla ↔ resumen.
- Scripts de migración en `/app/backend/scripts/migrations/` con patrón dry-run/apply, backups automáticos y safeguard `--allow-production`.

## Latest — 2026-04-21 (6) · Auditor + Auditoría código + Modo Autónomo

### BLOQUE 1 · Auditor Transversal (5 tools escritura/reporte) ✅
Tools en `/app/revix_mcp/tools/auditor.py`:
1. **`ejecutar_audit_financiero`** — facturas sin orden, órdenes cerradas sin facturar, discrepancias orden↔factura, liquidaciones duplicadas, materiales 0€. Clasifica LOW/MEDIUM/HIGH/CRITICAL.
2. **`ejecutar_audit_operacional`** — órdenes sin token, `enviado` sin `fecha_enviado`, duraciones >30d, técnicos inactivos.
3. **`ejecutar_audit_seguridad`** — accesos MCP fuera de horario (22:00-05:00 UTC), volumen inusual por minuto, intentos scope_denied.
4. **`generar_audit_report`** (idempotente) — requiere haber ejecutado al menos una tool de auditoría en los 30 min previos y mínimo 1 hallazgo con evidencia.
5. **`abrir_nc_audit`** (idempotente) — SOLO para hallazgos HIGH/CRITICAL. NC persiste en `capas` con `asignado_a=iso_officer` para delegación explícita.

**Agente auditor actualizado**: scopes ahora `audit:read + audit:report + meta:ping` (eliminado `*:read`). Tools: las 5 nuevas + 5 de lectura globales.

**Tests**: 6 nuevos en `test_auditor.py`. Cubre: detección de hallazgos, rechazo sin auditoría previa, severidad insuficiente para NC, asignación a iso_officer.

### BLOQUE 2 · Auditoría de código ✅
**Corregido** (29 fixes auto + 4 manuales):
- Imports/variables sin uso en 8 archivos (ruff auto).
- Bug real en `/api/master/enviar-credenciales/{id}`: `email_mask` no definido → añadido enmascaramiento del email del cliente.
- Variables `ESTADOS_FINALIZADOS`, `hace_30_dias` sin uso en dashboard_routes.py → borradas.
- 2 `result` sin uso en liquidaciones_routes.py → borrados.
- F-strings sin placeholder en revix_agent.py → corregidos.

**Verificado**:
- Las 28 tools MCP tienen `required_scope` declarado.
- Todos los endpoints POST/PUT/DELETE/PATCH tienen `Depends(require_auth/admin/master)` o protección por secret env (emergency scan).
- Endpoint público (`/api/public/agents/seguimiento/chat`) limitado al agente público con scope `public:track_by_token`.

**No tocado** (decisión explícita):
- 84 warnings estilísticos restantes (E701/E741/E722 — single-line statements, nombre de variable `l`, bare except) en `/agent/`, `/scripts/` y routes legacy. No son bugs funcionales. Son fixables con `ruff --fix --unsafe` pero podrían cambiar semántica de código maduro.

### BLOQUE 3 · CRM Modo Autónomo ✅
**Nuevo módulo** `/app/revix_mcp/scheduler.py`:
- `compute_next_run` con croniter (instalado en venv).
- CRUD + `ejecutar_tarea_una_vez` + `scheduler_tick` + loop de background.
- **3 fallos consecutivos** → `activo=False` + `desactivada_motivo` + notificación interna + email a `master@revix.es` (solo en production).
- **Rate-limit diferido**: `ToolRateLimitError` NO cuenta como fallo; posterga 60s.
- Loop arranca en `server.py` startup (interval 30s), stop en shutdown.

**Endpoints nuevos**:
- `GET /api/agents/scheduled-tasks` (lista, filtrable por agent_id).
- `POST /api/agents/scheduled-tasks` (crea · valida que la tool pertenezca al agente).
- `PATCH /api/agents/scheduled-tasks/{id}` (pausar/reactivar/cambiar cron).
- `DELETE /api/agents/scheduled-tasks/{id}`.
- `POST /api/agents/scheduled-tasks/{id}/run-now` (ejecución manual).

**Índices creados al startup**:
- `audit_logs.timestamp_dt` TTL 90 días (campo datetime añadido a `audit.py`).
- `audit_logs` (source, agent_id, timestamp desc).
- `mcp_scheduled_tasks.agent_id`.

**UI `/crm/agentes`**: botón "Tareas programadas" en sidebar, panel derecho con lista + acciones (Ejecutar ahora, Pausar/Reactivar), muestra estado (activa/pausada), última ejecución, resultado, próxima ejecución, fallos consecutivos.

**Tests**: 9 nuevos en `test_scheduler.py`. Cubre: cron parsing, CRUD, ejecución OK, 3 fallos desactivan+notifican, rate-limit diferido no cuenta como fallo, tick solo procesa vencidas+activas, integración autónoma completa end-to-end.

**Total MCP**: **104 tests / 104 pasando**.

### Archivos tocados en esta iteración
- `+/app/revix_mcp/tools/auditor.py` (nuevo · 5 tools)
- `+/app/revix_mcp/scheduler.py` (nuevo · scheduler)
- `+/app/revix_mcp/tests/test_auditor.py` (6 tests)
- `+/app/revix_mcp/tests/test_scheduler.py` (9 tests)
- `~/app/revix_mcp/audit.py` (timestamp_dt para TTL)
- `~/app/revix_mcp/tools/__init__.py` + `server.py` (registros)
- `~/app/backend/modules/agents/agent_defs.py` (auditor actualizado)
- `~/app/backend/modules/agents/routes.py` (endpoints scheduled-tasks + startup TTL)
- `~/app/backend/server.py` (startup/shutdown scheduler + `email_mask` fix)
- `~/app/backend/routes/dashboard_routes.py` (vars no usadas)
- `~/app/backend/routes/liquidaciones_routes.py` (result no usado)
- `~/app/frontend/src/pages/AgentesIA.jsx` (panel Tareas programadas)
- `~/app/backend/requirements.txt` (croniter)
- 29 fixes ruff auto en 8 archivos más.

## Latest — 2026-04-21 (5)

### Fase 2 MCP · Finance Officer ✅
Tercer agente de escritura supervisada. Cubre facturación, cobros, dunning y Modelo 303.

**4 tools nuevas** en `/app/revix_mcp/tools/finance_officer.py`:
1. **`listar_facturas_pendientes_cobro`** (read) — semáforo verde/amarillo/rojo por antigüedad, filtros `antiguedad_minima_dias`, `cliente_id`, `canal`. Devuelve contacto del cliente + importe total pendiente.
2. **`emitir_factura_orden`** (write · idempotente) — 5 validaciones ANTES de emitir: (a) estado ∈ {enviado, reparado, completada, entregada}, (b) total>0 con materiales o mano_obra, (c) no factura normal previa, (d) cliente con NIF/CIF y dirección, (e) rectificativa requiere `factura_origen_id`. Numeración vía `contabilidad_series`. Genera `url_pdf` apuntando a endpoint existente del CRM.
3. **`enviar_recordatorio_cobro`** (write · idempotente) — tipos amistoso/formal/ultimo_aviso. Bloquea ultimo_aviso sin recordatorio previo. Warning si el tipo pedido es más severo que el sugerido por antigüedad. Mock `[PREVIEW]` en entorno preview (no envía email real). Traza en `mcp_recordatorios_cobro`.
4. **`calcular_modelo_303`** (read agregado) — IVA repercutido (ventas) + soportado deducible (compras) del trimestre. Resultado a_ingresar/a_devolver/cero. **Aviso legal obligatorio** incluido en cada respuesta: *"Requiere revisión y presentación por el asesor fiscal"*.

**Agente IA `finance_officer` 💰** con 8 tools. Rate limit 120/600. Scopes: finance:read + finance:bill + finance:dunning + finance:fiscal_calc + orders:read + customers:read.

**Testing**: 13 tests nuevos en `test_finance_officer.py`. **Total MCP: 89/89 tests pasando**.
- Cubre todas las validaciones de emitir_factura (5 paths de fallo + emisión OK + rectificativa encadenada con origen).
- Recordatorio: bloqueo ultimo_aviso sin previos, warning por severidad, preview mock.
- Modelo 303: cálculo correcto + aviso legal siempre presente.

**Bug fix crítico**:
- Claude tiene pattern `^[a-zA-Z0-9_.-]{1,64}$` para nombres de propiedades → `año` no era válido. Cambio `año → anno` en el schema de `calcular_modelo_303`. Pydantic acepta ambos via alias.

**E2E Claude**: `calcular_modelo_303(Q1, 2026)` ejecutado en 2 iteraciones / 11.5s. Informe formal markdown con aviso legal. ✅

## Latest — 2026-04-21 (4)

### Fase 2 MCP · Agente ISO 9001 Quality Officer ✅
Segundo agente de escritura supervisada. Sistema de calidad ISO 9001 end-to-end.

**6 tools nuevas** en `/app/revix_mcp/tools/iso_officer.py`:
1. **`crear_muestreo_qa`** (write · doble scope `iso:quality + orders:read`) — lotes por aleatorio / por_tecnico / por_tipo_reparacion / por_reclamacion. Nueva colección `mcp_qa_muestreos`.
2. **`registrar_resultado`** (write · idempotente) — conforme/no_conforme. Si `no_conforme` la respuesta incluye `accion_requerida='abrir_nc'` + `mensaje_accion` guiando al agente.
3. **`abrir_nc`** (write · idempotente) — NC en colección `capas` (CAPA). Tipos: menor/mayor/crítica. `numero_nc` formato `NC-YYYYMMDD-XXXXXX`.
4. **`listar_acuses_pendientes`** (read) — documentos ISO sin acuse + filtro por rol + `incluir_vencidos_dias`.
5. **`evaluar_proveedor`** (write) — ISO 9001 §8.4. Score ponderado (calidad 40% · plazo 30% · precio 15% · doc 15%). Clasificación A/B/C/D + comparativa con evaluación previa (delta + tendencia).
6. **`generar_revision_direccion`** (read agregado) — Revisión por la Dirección §9.3. 6 secciones: indicadores · no_conformidades · acuses_pendientes · proveedores · sla · acciones_recomendadas.

**Agente IA `iso_officer` 📋** con 11 tools (6 nuevas + 5 lectura compartidas). Rate limit 120/600.

**Testing**: 13 tests nuevos en `test_iso_officer.py`. **Total MCP: 76/76 pasando**.
- Cubre: muestreo aleatorio/por_tecnico/dual_scope, idempotencia registrar_resultado, mensaje guía a abrir_nc, NC persiste correctamente, acuses filtro rol/vencidos, score ponderado A-D + delta comparativa, informe secciones custom.

**E2E real con Claude**:
- Cadena ejecutada: `crear_muestreo_qa → registrar_resultado (no_conforme) → abrir_nc` en 6 iteraciones, 42s. Claude generó informe formal markdown con tablas y 3 secciones (Hallazgos / Análisis / Acciones).

**Cambios auxiliares**:
- `agent_defs.py`: AGENTS dict incluye `ISO_OFFICER`.
- `rate_limit.py`: seed idempotente añade `iso_officer`.

## Latest — 2026-04-21 (3)

### Fase 2 MCP · Agente Supervisor de Cola Operacional ✅
Primer agente de **escritura supervisada**. Prioriza la cola SLA, marca órdenes en riesgo, abre incidencias y notifica al equipo.

**4 tools nuevas** en `/app/revix_mcp/tools/supervisor_cola.py`:
1. **`listar_ordenes_en_riesgo_sla`** (read) · semáforo crítico/rojo/amarillo por `created_at + sla_dias`. Umbral amarillo configurable.
2. **`marcar_orden_en_riesgo`** (write · idempotente) · requiere doble scope `orders:read + incidents:write` (verificación manual en handler). Añade `historial_riesgo[]` en la orden.
3. **`abrir_incidencia`** (write · idempotente · anti-duplicado) · rechaza si ya hay incidencia abierta para la orden. Genera `numero_incidencia` automático.
4. **`enviar_notificacion`** (write) · crea notificación en `notificaciones`. En `MCP_ENV=preview` emails prefijados `[PREVIEW]` y NO se envían por Resend (source=`mcp_agent`).

**Agente IA** `supervisor_cola` 🚦 registrado con:
- 7 tools (4 nuevas + listar_ordenes + buscar_orden + ping)
- Scopes: `orders:read`, `incidents:write`, `notifications:write`, `meta:ping`
- Rate limit default: 120/600 (seedeado al startup).

**Testing** (`test_supervisor_cola.py`, 12 tests) — **Total MCP: 63/63 passing** ✅:
- Semáforo SLA ordenado por severidad.
- Idempotencia end-to-end (mismo key no re-ejecuta).
- Verificación double-scope.
- Anti-duplicado de incidencias.
- Preview mock `[PREVIEW]` para emails.
- Audit log en todas las tools.

**Bug fix detectado y corregido en E2E**:
- `abrir_incidencia` pete cuando una incidencia antigua no tenía `numero_incidencia` → fallback defensivo `.get('numero_incidencia') or .get('id')`.

**Prueba E2E con Claude** (`POST /api/agents/supervisor_cola/chat`):
- Agente abrió correctamente `INC-20260421-72B985` con `source='mcp_agent'`, `created_by='mcp:supervisor_cola'` y devolvió tabla markdown.

## Latest — 2026-04-21 (2)

### Rate Limiting por agente (MCP) ✅
Protección anti-loop y anti-abuso para cada agente. Sliding window 60s en MongoDB con TTL auto-cleanup.

**Comportamiento**:
- `soft_limit` superado → warning en log + entrada `rate_limit_soft_crossed` en `audit_logs`. NO bloquea.
- `hard_limit` superado → `ToolRateLimitError` → HTTP 429 al cliente + entrada `rate_limit_exceeded` en `audit_logs`.
- Configurable por agente en la colección `mcp_agent_limits` (editable por BD o API).

**Defaults sembrados al arranque** (idempotentes, respetan cambios manuales):
| Agente | soft | hard |
|---|---|---|
| kpi_analyst | 120 | 600 |
| auditor | 120 | 600 |
| seguimiento_publico (público) | 60 | 300 |

**Arquitectura** (`/app/revix_mcp/rate_limit.py`):
- `ensure_indexes(db)` crea TTL index (120s) en `mcp_rate_limits` + unique en `mcp_agent_limits`.
- `seed_default_limits(db)` corre al startup de FastAPI.
- `get_limits(db, agent_id)` con cache en memoria (TTL 30s) para no consultar BD en cada tool call.
- `check_and_record(db, agent_id)` sliding window 60s, inserta la llamada solo si está dentro del hard.
- Hook en `runtime._execute_tool_with_identity` aplica a `execute_tool` Y `execute_tool_internal`.

**API admin** (nuevos):
- `GET /api/agents/rate-limits` → lista límites + contador actual por agente.
- `PUT /api/agents/{agent_id}/rate-limits` → editar soft/hard.

**Tests**: 10 nuevos (`test_rate_limit.py`) · Total MCP: **51/51** pasando.
- Cubre: fallback de defaults, cache invalidation, set_limits persiste, aislamiento entre agentes, soft/hard crossing, audit entries, 429 end-to-end.

**Mitigación de regresiones**:
- Probado tras activar: `/api/agents/kpi_analyst/chat` sigue funcionando correctamente (ping 4.8s, tool call registrada, contador actualiza a 1).

## Latest — 2026-04-21

### Agentes IA nativos en Revix ✅ (sustituye Rowboat)
Montado un orquestador multi-agente propio dentro del CRM. Los agentes hablan con Claude Sonnet 4.5 (vía Emergent LLM Key + LiteLLM) y ejecutan tools a través del servidor MCP interno con audit_logs automáticos.

**3 agentes Fase 1 (read-only)** en `/app/backend/modules/agents/`:
- **KPI Analyst** 📊 — dashboard + métricas + análisis de órdenes/clientes/inventario (8 tools).
- **Auditor Transversal** 🔍 — detección de anomalías, SLA, coherencia ISO 9001 (8 tools).
- **Seguimiento Público** 📱 — asistente al cliente final, solo token (scope `public:track_by_token` estricto).

**Arquitectura**:
- `agent_defs.py`: catálogo de agentes (system prompt + scopes + tools + modelo).
- `engine.py`: agent loop con tool-calling (`litellm.completion` + Emergent proxy), hasta 8 iteraciones, convierte tools MCP al esquema OpenAI function-calling que Claude entiende.
- `routes.py`: API `/api/agents*` con sesiones persistentes + endpoint público sin auth para widget cliente.
- `revix_mcp.runtime.execute_tool_internal()` nuevo: permite al orquestador ejecutar tools sin API key física, manteniendo audit + scopes.

**Frontend** `/app/frontend/src/pages/AgentesIA.jsx`:
- Ruta `/crm/agentes` (admin) con layout 3 columnas: agentes, chat, audit panel.
- Sample prompts, markdown rendering (react-markdown), badges de tools ejecutadas con duración, scroll auto, gestión de sesiones (crear, seleccionar, borrar).
- Audit logs en vivo desde el panel lateral.
- Nueva entrada en sidebar "Agentes IA · Nuevo".

**Testing**:
- Smoke test end-to-end: login → `/crm/agentes` → sample prompt → respuesta markdown ejecutiva en 13s con tool `obtener_dashboard` (843ms). ✅
- Audit logs MCP persistidos correctamente (timestamp, agent_id, tool, duration_ms).
- Endpoint público sin auth responde correctamente pidiendo token.
- Tests MCP existentes: 41/41 siguen pasando.

### Credenciales
- Chat admin: `master@revix.es` / `RevixMaster2026!` → `/crm/agentes`
- Chat público (widget cliente): `POST /api/public/agents/seguimiento/chat` — sin auth, solo `public:track_by_token`.

## Latest — 2026-04-20 (3)

### Fase 1 MCP · 8 Tools Read-Only completadas ✅
Tools registradas (`/app/revix_mcp/tools/`), todas con proyecciones estrictas Mongo y audit log automático:
1. `buscar_orden(ref)` — orders:read · resuelve por UUID, numero_orden o numero_autorizacion.
2. `listar_ordenes(filtros)` — orders:read · paginado, filtros por estado/técnico/cliente/garantía/autorización/fechas.
3. `buscar_cliente(q)` — customers:read · búsqueda exacta (id/dni/email/tel/cif) o fuzzy por nombre.
4. `obtener_historial_cliente(cliente_id)` — customers:read · resumen + órdenes, materiales opcionales.
5. `consultar_inventario(filtros)` — inventory:read · texto libre, proveedor, solo_bajo_minimo, solo_sin_stock, es_pantalla · etiqueta `nivel_stock`.
6. `obtener_metricas(metrica, periodo)` — metrics:read · 11 métricas (estados, técnicos, ingresos, beneficio, top modelos, SLA, garantía, aprobación presupuestos...).
7. `obtener_dashboard(periodo)` — dashboard:read · snapshot agregado órdenes + finanzas + inventario + clientes.
8. `buscar_por_token_seguimiento(token)` — public:track_by_token · info mínima apta para cliente final (NO expone costes/materiales/técnico). `*:read` NO cubre este scope por diseño.

### Tests MCP: 41/41 pasando
- `/app/revix_mcp/tests/test_foundation.py` (19 tests) — scopes, API keys, runtime, audit, idempotencia.
- `/app/revix_mcp/tests/test_tools_readonly.py` (22 tests) — las 8 tools con fixtures seed limpiables (prefijo `test_mcp_`).
- Ejecutar: `/app/revix_mcp/.venv/bin/pytest /app/revix_mcp/tests/ -v`
- Verificación transversal: ninguna tool filtra clave Mongo `_id` en sus respuestas.

### Próximo paso
- P1: Rate limiting por API key en `runtime.py` (límite `rate_limit_per_min` por (agent_id, minuto)).
- P0: Panel de observabilidad MCP en el CRM (`/crm/agentes-mcp`) — visualizar audit_logs filtrables + botón pausar agente.
- P1: Fase 2 MCP — agentes de escritura supervisada + 16 tools de escritura.

## Latest — 2026-04-20 (2)

### Fase 1 MCP · Fundación completada
- Servidor MCP aislado en `/app/revix_mcp/` (venv propio, sin contaminar backend).
- Arquitectura: `config.py` · `scopes.py` · `auth.py` · `audit.py` · `runtime.py` · `server.py` · `cli.py` · `tools/_registry.py` · `tools/meta.py (ping)`.
- **Auth**: API keys `revix_mcp_*` almacenadas hasheadas en `mcp_api_keys`, una key por agente.
- **Scopes**: catálogo 24 scopes + 10 perfiles preconfigurados (AGENT_PROFILES) + regla `*:read` para KPI/Auditor.
- **Audit log**: cada tool call → `audit_logs` con source=`mcp_agent`, params sanitizados, duration_ms, error, idempotency_key.
- **Idempotencia**: tools de escritura aceptan `_idempotency_key` → cache en `mcp_idempotency`.
- **Sandbox**: `MCP_ENV=preview` + tool flag `sandbox_skip` bloquea side effects peligrosos.
- **CLI**: `create/list/revoke` API keys.
- **Tests**: 19 unitarios + smoke test stdio end-to-end funcional.

### Fase 0 completada previamente
- 5 órdenes migradas (tecnico_asignado email → UUID), 87 tokens de seguimiento generados, preview ampliado, Resumen Financiero alineado con backend.

## Latest — 2026-04-18

### Rediseño completo de la web pública (Apple Care style)
- 10 páginas públicas rediseñadas: Home, Servicios, Presupuesto, Contacto, Aseguradoras, Partners, Garantía, Garantía Extendida, FAQs, Consulta (Seguimiento).
- Nueva página `/marca` con descarga de logos (SVG vectorizado + PNG 2048px + versión dark + isologo para favicons).
- Assets generados: `revix-logo.svg/png`, `revix-logo-dark.svg/png`, `revix-isologo.svg/png` en `/app/frontend/public/brand/`.
- Sistema de primitives UI compartido (`components/public/ui.jsx`) + componente `Logo.jsx` tipográfico.
- Layout público nuevo con glassmorphism header, footer limpio de 4 columnas.
- Paleta: #0055FF brand, #111111 texto, #F5F5F7 fondos sutiles.
- Tipografía: Plus Jakarta Sans 800 headings + Inter body.
- Motion: framer-motion fade-up on scroll.
- Todas las funcionalidades preservadas: formularios de contacto/presupuesto, portal `/consulta`, chatbot flotante, login de CRM.

### Branding dinámico título/favicon
- Hook `useBrandingByRoute.js`: rutas públicas muestran "Revix.es" + favicon "R" azul.
- Rutas CRM (/crm, /login...) muestran "NEXORA - CRM/ERP" + favicon Nexora.

### Aislamiento Preview/Producción
- Preview ahora usa BD `revix_preview` (mismo cluster Atlas, DB separada).
- Producción sigue en BD `production`, intocable desde este entorno.
- Seed idempotente `scripts/seed_preview.py`: 3 usuarios + 2 clientes + 3 órdenes demo.
- El seed aborta si detecta `DB_NAME=production` (salvaguarda).

### Deployment Readiness — PASS
- Deployment Agent: **status: pass** — listo para despliegue a producción.
- FRONTEND_URL ahora lee de env var con filtro anti-preview-URL (default: https://revix.es).
- CORS_ORIGINS ahora configurable via env var.
- JWT_SECRET exige env var (raise RuntimeError si falta).
- database.py: eliminado fallback hardcodeado de MONGO_URL/DB_NAME (exige env vars).
- .gitignore: eliminados patrones `*.env` para permitir deploy; añadido `memory/test_credentials.md`.
- 24/24 tests críticos pasan tras cambios.

## 2026-04-17 — Estabilidad y Calidad
- 27 indices MongoDB + 24 tests automaticos (pytest).
- Lint backend 94→40 errores (cosmeticos), 0 undefined/bare excepts.
- MD5→SHA-256, wildcard imports eliminados, usuarios duplicados limpiados.
- Seguridad: SlowAPI rate limiting, middleware NoSQL injection, JWT 24h.
- Refactorización server.py: 3400→1000 líneas (routes modulares).

## 2026-04 — Features
- Sistema impresión Brother QL-800 centralizado con agente Windows + cola MongoDB.
- Historial de impresiones, SKUs cortos automáticos, sección Comunicaciones Insurama.
- Estado "FUERA DE GARANTIA" en PDF/UI.
- Liquidaciones: agrupación por nº autorización, separación garantías, sin duplicados.
- Fix enlaces seguimiento en emails (producción, no preview).

---

## Backlog
- P2: Google Business Profile + Gemini Flash.
- P2: Flujo gestión de incidencias.

## Credentials
- master@revix.es / RevixMaster2026!
- Agent key: revix-brother-agent-2026-key

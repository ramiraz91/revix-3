# PRD - Revix CRM/ERP + Web Pública

## Problema Original
Sistema CRM/ERP completo para taller de reparación de dispositivos móviles (Revix.es, Córdoba), con integración de aseguradoras (Insurama/Sumbroker), gestión de proveedores y ahora presencia web pública para clientes.

## Arquitectura
- **Backend**: FastAPI + MongoDB
- **Frontend**: React + Tailwind CSS + framer-motion
- **Integraciones**: MobileSentrix, Utopya, Insurama/Sumbroker, Gemini Flash (IA)

---

## Lo Implementado

### ✅ Core CRM/ERP
- Gestión de órdenes de trabajo con sub-estados
- Inventario con variantes de producto y kits
- Integración con proveedor MobileSentrix (sync de precios - con problemas de rendimiento)
- Scraping Utopya.es via Playwright

### ✅ Módulo Insurama / Inteligencia de Precios
- Vista de mercado con comentarios de competidores (arreglado)
- **Price Intelligence Center (Fase 1)**: Captura automática de datos de siniestros cerrados
  - Dashboard en `/insurama` tab "Inteligencia"
  - Historial de mercado
  - Recomendaciones de precios
- **Liquidaciones**: Página para master user de pagos Insurama
  - Importación Excel (.xlsx)
  - Estados: pendiente/pagado/reclamado
  - Historial mensual

### ✅ Web Pública (revix.es) - COMPLETADO [26 Feb 2026]
Accesible en `/web` (sin autenticación)
- **`/web`** - Página principal con hero, servicios destacados, CTA
- **`/web/servicios`** - Catálogo completo de reparaciones (smartphones, tablets, smartwatches, consolas)
- **`/web/contacto`** - Formulario conectado a BD + datos reales (help@revix.es, Julio Alarcón 8, local, 14007 Córdoba)
- **`/web/presupuesto`** - Formulario multi-paso de solicitud presupuesto
- **`/web/aseguradoras`** - Información para aseguradoras
- **`/web/garantia`** - Información de garantía (6 meses, certificación WISE/ACS)
- **`/web/garantia-extendida`** - Página de garantía extendida (placeholder para e-commerce)
- **`/web/consulta`** - Portal de seguimiento conectado a BD real
- **Chatbot IA** - Gemini Flash via emergentintegrations, con historial de sesión en MongoDB

### ✅ Seguridad - COMPLETADO [27 Feb 2026]
- **Rate Limiting en Login**: Bloqueo de 15 minutos tras 5 intentos fallidos (por IP y email)
- **Mensajes de error específicos**: "Email o contraseña incorrectos" con contador de intentos restantes
- **Recuperación de contraseña**:
  - `/forgot-password` - Formulario para solicitar enlace de recuperación
  - `/reset-password?token=X` - Página para establecer nueva contraseña
  - Tokens seguros con 1 hora de validez
- **Gestión de contraseñas Master**: El usuario master puede cambiar/resetear contraseñas de empleados
- **Headers de seguridad**: CSP, X-Frame-Options, etc. en middleware

---

## Backlog Priorizado

### P0 - Completado
- [x] Web pública con todas las páginas
- [x] Chatbot IA con Gemini Flash
- [x] Formularios de contacto y presupuesto conectados a BD
- [x] Medidas de seguridad (rate limiting, recuperación contraseña, mensajes error)

### P1 - Pendiente
- [ ] Activar precios/pagos en página "Garantía Extendida"
- [ ] UI para programador de sincronización semanal de proveedores
- [ ] Completar visualizaciones Price Intelligence Center (gráficos/charts en InteligenciaDashboard.jsx)
- [ ] Sistema de búsqueda de productos (Marca → Modelo → Tipo) - backend listo, falta frontend `SelectorProductos.jsx`

### P2 - Pendiente
- [ ] Fix rendimiento MobileSentrix price sync (refactorizar a asyncio.gather para procesamiento paralelo)

### P3 - Bloqueado por usuario
- [ ] Sync datos Utopya (el usuario debe ejecutar sync manual desde UI)

### Futuro
- [ ] Despliegue en revix.es (configuración DNS)
- [ ] Notificaciones al cliente cuando cambia estado de reparación

---

## Datos de Contacto Reales (Revix.es)
- Email: help@revix.es
- Dirección: Julio Alarcón 8, local, 14007 Córdoba
- Horario: L-V 10:00-14:00 / 17:00-20:00, Sáb 10:00-14:00
- Certificaciones: WISE + estándares ACS

## Credenciales de Test
- CRM Login: ramiraz91@gmail.com / temp123
- Utopya: ramiraz91@gmail.com / @100918Vm


---

## Actualización de Rendimiento (Marzo 2026)

### ✅ Optimización de Rendimiento Completada

#### Fase 1: Diagnóstico
- Benchmark inicial identificó `/api/ordenes` como cuello de botella (2044 KB, 230ms p95)
- Sistema de instrumentación implementado con métricas p50/p95/p99

#### Fase 2: Base de Datos
- **7 nuevos índices** creados en MongoDB:
  - `ordenes.estado_created_at_idx`
  - `ordenes.dispositivo_imei_idx`
  - `ordenes.numero_autorizacion_idx`
  - `ordenes.tecnico_asignado_idx`
  - `ordenes.cliente_estado_idx`
  - `clientes.id_idx`, `clientes.email_idx`
  - `audit_logs.audit_action_date_idx`

#### Fase 3: API Backend
- **Nuevo endpoint** `/api/ordenes/v2` con:
  - Paginación obligatoria (`page`, `page_size`)
  - Proyección reducida (solo campos para listado)
  - **Reducción de payload: 2044 KB → 23 KB (98.9%)**
  - **Reducción de latencia: 230ms → 48ms p95 (79%)**

#### Fase 4: Frontend
- `ordenesAPI.listarPaginado()` integrado en:
  - `/ordenes` - Listado principal con paginación
  - `/dashboard` - Órdenes recientes
  - `/calendario` - Órdenes pendientes
  - `/incidencias` - Selector de órdenes
- Hooks de rendimiento creados:
  - `useDebounce(value, delay)` - Búsqueda con debounce 300ms
  - `useDebouncedSearch()`, `useInfiniteScroll()`, `useSimpleCache()`

#### Archivos Nuevos/Modificados
- `/backend/routes/ordenes_routes.py` - Endpoint v2
- `/backend/create_indexes.py` - Script de índices
- `/backend/benchmark.py` - Benchmarking
- `/backend/middleware/performance.py` - Instrumentación
- `/frontend/src/hooks/usePerformance.js` - Hooks de rendimiento
- `/frontend/src/pages/Ordenes.jsx` - Paginación integrada

---

### ✅ Flujo de Técnico ISO 9001 Completado

#### Mejoras de UX Técnico
- **Bug P0 corregido**: Técnicos ahora pueden buscar/abrir órdenes sin RI completada
- **Opción "Solo Buscar/Abrir"** añadida al scanner del Dashboard
- **RI automáticamente inicia reparación**: Al marcar "RI OK", estado cambia a "en_taller"
- **Botón "Finalizar Reparación"** añadido para técnicos
- **Información explicativa de RI** con guía de cuándo usar cada opción

#### RBAC Mejorado
- Sección "Diagnóstico y Control de Calidad" oculta para admin/master
- Solo técnicos pueden editar checklists de batería y certificaciones
- Modal QC Final con verificación completa ISO 9001 / WISE ASC

---

### 📋 Guía de Producción
Ver `/app/memory/DEPLOYMENT_GUIDE.md` para:
- Variables de entorno requeridas
- Checklist de seguridad
- Comandos de despliegue
- Plan de rollback

---


## Actualización de ejecución (Diciembre 2025) - P0/P1 completados

### ✅ P0 resuelto: estabilidad de base de datos en cargas/listados
- Corregido error 500 en `GET /api/clientes` por documentos legacy sin `dni`.
- Se añadió normalización en backend para clientes legacy (`dni`, `ciudad`, `tipo_cliente`, fechas).
- Se blindó `GET /api/ordenes` y `GET /api/ordenes/{ref}` para evitar caídas por documentos incompletos.
- `GET /api/incidencias` verificado operativo sin regresiones.

### ✅ P1 resuelto: fix raíz en `POST /api/insurama/carga-masiva`
- La carga masiva ahora hace **upsert de cliente real** en `db.clientes` y reutiliza `cliente_id` consistente.
- Se normaliza la estructura de `dispositivo` antes de crear/actualizar órdenes.
- Se crea payload de orden con campos mínimos completos del esquema (incluyendo listas/defaults requeridos).
- Mapeo de estado corregido: `status=6` de Sumbroker ahora mapea a `enviado` (antes: `entregado`, inválido para el enum CRM).

### ✅ Testing ejecutado
- Reporte: `/app/test_reports/iteration_39.json`
- Resultado: **13/13 tests backend OK**
- Endpoints validados: `/api/clientes`, `/api/ordenes`, `/api/incidencias`, `/api/insurama/carga-masiva`.

### Próximo bloque (según prioridad de usuario)
1. Refactorizar componentes grandes sin romper flujo:
   - `frontend/src/pages/Insurama.jsx`
   - `frontend/src/pages/OrdenDetalle.jsx`
2. Mantener pendiente técnico:
   - Optimización rendimiento sync MobileSentrix (`asyncio.gather`)
   - UI de programación semanal de sincronización de proveedores


### ✅ Nuevo valor añadido: Pre-check + Confirmación en Carga Masiva Insurama
- Implementado flujo en 2 pasos en `/insurama`:
  1) **Pre-check** del Excel (sin crear órdenes)
  2) **Confirmar y ejecutar** carga real
- Nuevo endpoint backend: `POST /api/insurama/carga-masiva/precheck`
  - Devuelve resumen: `total_filas`, `validos_unicos`, `duplicados`, `vacios`, `formato_invalido`, `existentes_en_crm`, `nuevos_estimados`, `actualizaciones_estimadas`, `listos_para_procesar`.
- Frontend actualizado con tarjeta de pre-check, detalle por fila y botones cancelar/confirmar.
- Añadidos `data-testid` para testeo E2E del nuevo flujo.

### ✅ Testing ejecutado (pre-check flow)
- Reporte: `/app/test_reports/iteration_40.json`
- Resultado: **Backend 8/8 PASS + Frontend verificado**
- Verificado: endpoint pre-check, validación de formato, UI de pre-check, confirmación y regresión básica de `/insurama`.

### Siguiente paso acordado
- Iniciar refactor controlado de `Insurama.jsx` y `OrdenDetalle.jsx` sin cambiar comportamiento funcional.


### ✅ P0 ISO implementado sobre funcionalidades existentes del ERP/CRM
- **Consentimiento de datos + RGPD en seguimiento** (sin reinventar):
  - Reutilizado flujo actual de `/web/consulta` y modal legal existente.
  - Añadido segundo consentimiento RGPD obligatorio.
  - Evidencia auditable guardada en backend en `consentimientos_seguimiento` con fecha, token, teléfono enmascarado, IP y user-agent.
- **Checklists operativos OT** (recepción + QC final + baterías):
  - Reutilizado endpoint existente `PATCH /api/ordenes/{id}` para autoguardado de campos.
  - Reglas ISO operativas activadas en transición de estados:
    - `recibida -> en_taller` bloqueado sin checklist recepción.
    - `validacion -> enviado` bloqueado sin QC final completo.
- **No Conformidades + CAPA en incidencias**:
  - Reutilizado flujo existente de incidencias.
  - Tipos NC (`reclamacion`, `garantia`, `daño_transporte`) requieren causa raíz + acción correctiva para resolver/cerrar.
  - UI detalle incidencias ampliada con bloque CAPA y guardado parcial.

### ✅ Validación técnica ejecutada
- Testing subagente: `/app/test_reports/iteration_41.json`
  - Backend: **15/15 PASS**
  - Frontend: verificado
- Bug adicional detectado por testing agent (`OrdenDetalle` crash en acceso directo) corregido y revalidado por main agent.

### Próximo bloque recomendado (P1)
1. Control documental ISO en ERP (LMD, versión, aprobador, vigencia, retención).
2. Evaluación de proveedores críticos (GLS, MobileSentrix, Utopya) con scoring y reevaluación.
3. Dashboard KPI ISO mensual + acta de revisión por dirección.


### ✅ Next Actions ejecutados (orden A) + reporte exportable PDF
- **Control documental ISO (LMD)** implementado en backend y UI master:
  - `GET/POST /api/master/iso/documentos`
  - Campos controlados: código, título, tipo, versión, retención, estado, cláusulas.
- **Control de proveedores críticos** implementado:
  - `GET /api/master/iso/proveedores`
  - `POST /api/master/iso/proveedores/evaluar`
  - Cálculo de score automático y estado (`aprobado`, `condicional`, `bloqueado`).
- **Cuadro de mando ISO** implementado:
  - `GET /api/master/iso/kpis`
  - KPIs operativos para auditoría y seguimiento mensual.
- **Reporte exportable PDF manual** implementado (según elección usuario):
  - `GET /api/master/iso/reporte-pdf`
  - Filtros soportados: `orden_id`, `fecha_desde`, `fecha_hasta` (OT + rango).
  - Evidencias incluidas: consentimiento seguimiento, checklist recepción/QC, batería, NC/CAPA vinculada.
- **Frontend Panel Master**:
  - Nueva pestaña `ISO 9001` con formularios de LMD/proveedores y botón de descarga PDF.

### ✅ Testing de este bloque
- Reporte: `/app/test_reports/iteration_42.json`
- Resultado: **Backend 22/22 PASS + Frontend 18/18 PASS**
- Sin issues pendientes reportados por testing agent.


### ✅ Blueprint integral ISO+WISE creado
- Archivo generado: `/app/memory/ISO_WISE_BLUEPRINT.md`
- Incluye: inventario real ERP, gap analysis ISO 4–10 + WISE 3.1–3.27, top 15 no negociables, diseño técnico BD/UI/API/automatizaciones, checklist auditoría, plan de despliegue sin interrupción y tareas fuera del ERP.
- Decisiones aprobadas por usuario integradas:
  - Garantía: 6 meses
  - Borrado de datos: mixto por tipo OT
  - Flasheo: aplica (herramienta pendiente de definir)
  - Baterías: almacenamiento temporal + retirada periódica


### ✅ Must #1 ISO+WISE implementado (Event Log + RI/Cuarentena + Audit Pack)
- **Event Log OT inmutable (append-only)**
  - Se registra automáticamente en: creación OT, cambio de estado, RI y patch parcial.
  - Endpoint: `GET /api/ordenes/{id}/eventos-auditoria`.
- **Receiving Inspection (RI) formal**
  - Endpoint: `POST /api/ordenes/{id}/receiving-inspection`.
  - Requiere >=3 fotos de recepción.
  - Resultado `sospechoso/no_conforme` mueve OT a `cuarentena`.
  - Se bloquea `en_taller` si RI obligatoria no completada.
- **Audit Pack OT/Período**
  - `GET /api/master/iso/audit-pack/ot/{id}`
  - `GET /api/master/iso/audit-pack/periodo`
  - `GET /api/master/iso/audit-pack/periodo/csv`
  - PDF ISO enriquecido con RI y conteo EventLog.
- **Frontend**
  - `OrdenDetalle`: tarjeta RI con acciones rápidas.
  - Workflow visual y modal estado incluyen `cuarentena`.
  - `PanelMaster` ISO incluye botón `Descargar Audit Pack CSV` y validación de OT.

### ✅ Testing Must #1
- Reporte: `/app/test_reports/iteration_43.json`
- Resultado: **Backend 19/19 PASS + Frontend 100% verificado**
- Sin issues críticos pendientes.


### ✅ Permisos ajustados según operación real
- Diagnóstico y Control de Calidad ahora son **solo del técnico**.
- Admin/master quedan en solo lectura para campos QC/diagnóstico.
- Trazabilidad de baterías se mantiene editable por técnico/admin/master (como solicitado).
- Validado por testing agent con reporte `/app/test_reports/iteration_44.json` (Backend 17/17 PASS, Frontend 100%).


### ✅ Next Action Items finalizados (Must #2/#3/#4)
- NCM avanzada con severidad/disposición/origen/impacto/contención en incidencias.
- CAPA automática implementada según regla aprobada:
  - severidad alta/crítica **o** 2+ NC iguales en 30 días.
- QA por muestreo AQL configurable:
  - default 10% diario mínimo 1,
  - fallo en muestreo => escalado 20% durante 7 días + apertura CAPA.
- CPI/NIST por tipo OT:
  - B2B obligatorio,
  - B2C mixto según autorización.
- Endpoints y UI validados por testing subagente.

### ✅ Testing final de este apartado
- Reporte: `/app/test_reports/iteration_45.json`
- Resultado: **Backend 20/20 PASS + Frontend 100% verificado**
- Sin pendientes críticos para este bloque.


### ✅ Flujo técnico completo ISO/WISE en OrdenTecnico [01 Mar 2026]
**Componentes nuevos:**
- `TecnicoAccionesCard`: botón "Iniciar Reparación" (recibida→en_taller) + "Marcar Irreparable"
- `TecnicoRICard`: 3 botones RI (OK/Sospechoso/No Conforme) con validación y nombre técnico
- `TecnicoCPICard`: 3 opciones radio CPI/NIST 800-88 + sub-formulario SAT con método
- `TecnicoCierreReparacion` (reescrito): QC completo con verificación de batería (nivel/ciclos/estado), funciones del sistema (11 checks, 9 obligatorios WISE), pre-requisitos bloqueantes (RI+CPI+diagnóstico+materiales), cierre → estado `reparado`
**Permisos:** todos los cambios de estado técnicos (en_taller/reparado/validacion/irreparable) requieren rol `tecnico` (HTTP 403 para admin/master)
**Testing:** Backend 19/19 PASS + Frontend 10/10 PASS (iteration_49)
**Matriz de permisos implementada:**
- `require_tecnico` añadido a `auth.py`
- `PATCH /ordenes/{id}/cpi` → solo técnico (HTTP 403 para admin/master)
- `POST /ordenes/{id}/receiving-inspection` → solo técnico
- `PATCH /ordenes/{id}/diagnostico` → solo técnico
- `PATCH /ordenes/{id}/estado` → estados técnicos (en_taller, reparado, validacion, irreparable, cuarentena→recibida) → solo técnico; estados admin (enviado, cancelado, etc.) solo admin/master

**CPI redeseñado — 3 opciones estructuradas ISO/WISE:**
1. "Ya venía restablecido por el cliente (verificado)"
2. "Cliente NO autoriza restablecer/borrar (Privacidad alta)"
3. "Restablecimiento realizado por el SAT (método + NIST 800-88)"
- Campo `cpi_opcion` guardado en MongoDB + `cpi_usuario_nombre` (nombre+apellido, nunca email)

**UI:**
- `OrdenTecnico.jsx`: nuevas tarjetas `TecnicoRICard` + `TecnicoCPICard` con acceso completo de edición
- `OrdenDetalle.jsx` (admin/master): CPI/RI como solo-lectura con badge "Solo técnico"
- `OrdenCambioEstadoModal.jsx`: filtrado de estados por rol (admin/master solo estados admin; técnico solo estados técnicos)
- `OrdenPDF.jsx`: nombre técnico desde `cpi_usuario_nombre` (nunca email); fallback "Nombre no configurado"

**Testing:** Backend 18/18 PASS + Frontend Admin 8/8 PASS + Frontend Técnico RI/CPI confirmado visual
- Motor existente (`OrdenPDF` + `react-to-print`) conservado, JSX roto corregido.
- **Layout 2 columnas**: Cliente+Dispositivo en cabecera; Avería+Diagnóstico | RI+QC+CPI en sección técnica
- **Fechas** (5 col) + **Referencias** (4 col) en filas compactas
- **Tabla materiales** con totales (solo modo `full`)
- **Anexo fotográfico multipágina** (8 fotos/página, máx 16, grid 4×2) con `page-break-before`
- 3 modos: `full` (admin/master, con fotos en anexo), `no_prices`, `blank_no_prices`
- Footer indica conteo de fotos y paginación (ej. "Pág. 1/2")
- Logging auditable: `POST /api/ordenes/{id}/registro-impresion` → `ot_print_logs` + `ot_event_log`

### ✅ Testing rediseño OT-PDF v2.0
- Reporte: `/app/test_reports/iteration_47.json`
- Resultado: **Backend 12/12 PASS + Frontend 8/8 PASS**
- Verificado: layout 2 col, anexo fotos, permisos, 3 modos, audit log.

---

## Agente ARIA (Asistente Revix de Inteligencia Artificial) - Marzo 2026

### ✅ Implementación Completada

**Descripción**: Agente IA interno para ayudar al equipo de administración con consultas, automatización de tareas y detección proactiva de problemas.

**Tecnología**: Gemini 2.0 Flash vía `emergentintegrations.llm.chat`

**Ubicación**: `/crm/agente-aria` (acceso: admin/master)

#### Funcionalidades Implementadas:

**Consultas de Información:**
- `obtener_resumen_sistema()` - Resumen completo: órdenes por estado, peticiones, alertas SLA
- `listar_peticiones_pendientes()` - Peticiones sin llamar, con horas de espera y estado SLA
- `listar_ordenes_validacion()` - Órdenes pendientes de validación
- `listar_ordenes_por_estado()` - Filtrar órdenes por estados específicos
- `buscar_orden()` - Buscar por número, ID o código siniestro
- `buscar_peticion()` - Buscar petición por número, nombre, teléfono o email
- `buscar_cliente()` - Buscar clientes por cualquier campo
- `obtener_historial_cliente()` - Historial completo de un cliente
- `detectar_alertas_sla()` - Detectar elementos fuera de SLA
- `obtener_stock_bajo()` - Repuestos bajo mínimo
- `listar_incidencias_abiertas()` - Incidencias activas
- `obtener_ordenes_compra_pendientes()` - OCs sin recibir

**Acciones Ejecutables:**
- `actualizar_estado_orden()` - Cambiar estado de orden
- `marcar_peticion_contactada()` - Marcar resultado de llamada
- `agregar_nota_orden()` - Agregar comentario interno
- `crear_notificacion()` - Crear alerta para el equipo
- `asignar_tecnico()` - Asignar técnico a orden

**Reportes y Análisis:**
- `obtener_estadisticas()` - Métricas por periodo (hoy/semana/mes/trimestre)
- `generar_reporte_diario()` - Reporte detallado del día
- `analizar_rendimiento_tecnicos()` - Performance de técnicos
- `analizar_tendencias()` - Dispositivos/averías más frecuentes

#### Arquitectura:
- `/app/backend/agent/agent_core.py` - Clase RevixAgent con integración LLM
- `/app/backend/agent/revix_agent.py` - 21 funciones ejecutables, SYSTEM_KNOWLEDGE
- `/app/backend/routes/agent_routes.py` - Endpoints API
- `/app/frontend/src/pages/AgentARIA.jsx` - UI de chat

#### Endpoints API:
- `GET /api/agent/summary` - Resumen del sistema
- `POST /api/agent/chat` - Chat conversacional con IA
- `GET /api/agent/alerts` - Alertas activas
- `GET /api/agent/conversations` - Historial de conversaciones
- `POST /api/agent/quick-action/*` - Acciones rápidas

#### UI Features:
- Tarjetas de resumen (llamadas pendientes, validación, en taller, peticiones hoy, alertas SLA)
- Chat conversacional con memoria de sesión
- Indicador de funciones ejecutadas
- Panel de acciones rápidas
- Ejemplos de uso

#### Testing:
- Reporte: `/app/test_reports/iteration_50.json`
- Resultado: **Backend 20/20 PASS + Frontend ALL PASS (100%)**
- Bug corregido: paths de datos en tarjetas de resumen

---

## Manuales de Reparación Apple - Marzo 2026

### ✅ Implementación Completada

**Descripción**: Integración con la documentación oficial de Apple para mostrar manuales de reparación relevantes automáticamente en las órdenes de trabajo de dispositivos iPhone.

**Funcionalidades:**
- Detección automática del modelo de iPhone desde el campo `dispositivo.modelo`
- Mapeo a la documentación oficial de Apple Support
- Detección inteligente del tipo de reparación basado en el problema reportado
- Enlaces directos a:
  - Página del dispositivo en Apple Support
  - Manual de reparación oficial (si existe)
  - Especificaciones técnicas
  - Secciones relevantes de troubleshooting (pantalla, batería, cámara, etc.)

**Modelos Soportados:**
- iPhone 17, 17 Pro, 17 Pro Max, Air (2025)
- iPhone 16, 16 Plus, 16 Pro, 16 Pro Max, 16e (2024)
- iPhone 15, 15 Plus, 15 Pro, 15 Pro Max (2023)
- iPhone 14, 14 Plus, 14 Pro, 14 Pro Max (2022)
- iPhone 13, 13 mini, 13 Pro, 13 Pro Max (2021)
- iPhone 12, 12 mini, 12 Pro, 12 Pro Max (2020)
- iPhone SE (todas las generaciones)
- iPhone 11, 11 Pro, 11 Pro Max (2019)
- iPhone X, XS, XS Max, XR (2017-2018)
- iPhone 8, 8 Plus, 7, 7 Plus, 6s, 6 (2014-2017)

**Tipos de Reparación Detectados:**
- Pantalla (display, LCD, OLED, táctil)
- Batería (carga, energía)
- Cámara (foto, flash, LiDAR, TrueDepth, Face ID)
- Altavoz/Audio (sonido, micrófono)
- Botones (power, volumen, home, Touch ID)
- Conectividad (WiFi, Bluetooth, SIM)
- Vibrador (Taptic Engine)
- Tapa trasera

**Archivos:**
- `/app/backend/services/apple_manuals_service.py` - Servicio de mapeo de modelos
- `/app/backend/routes/apple_manuals_routes.py` - Endpoints API
- `/app/frontend/src/components/AppleManualCard.jsx` - Componente UI

**Endpoints API:**
- `GET /api/apple-manuals/lookup?model={modelo}&problem={problema}` - Busca documentación
- `GET /api/apple-manuals/models` - Lista todos los modelos soportados
- `GET /api/apple-manuals/detect-repair-type?problem={problema}` - Detecta tipo de reparación

**Integración:**
- Componente `AppleManualCard` integrado en `OrdenDetalle.jsx`
- Se muestra automáticamente cuando el dispositivo es un iPhone
- Panel colapsable con diseño azul distintivo


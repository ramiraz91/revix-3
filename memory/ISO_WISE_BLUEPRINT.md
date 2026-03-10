# ISO+WISE Blueprint (Revix.es CRM/ERP)

Fecha: 2026-03-01
Ámbito: Centro único de reparación móvil (España) – operación B2C/B2B

---

## 0) Respuestas mínimas (estado actual)

1. B2C/B2B: **AMBOS**
2. Garantía actual: **PENDIENTE DE APROBACIÓN** (decisión tomada: **6 meses para todo**)
3. Logística principal: **GLS**
4. Proveedores críticos de piezas: **MobileSentrix, Utopya**
5. Borrado de datos: **Mixto por tipo OT**
6. Flasheo/actualización software: **Sí aplica**, herramienta **PENDIENTE DE DEFINICIÓN**
7. Baterías: **Reemplazo + almacenamiento temporal + retirada periódica** (flujo formal de gestor: **PENDIENTE DE FORMALIZACIÓN**)
8. Subcontratación reparaciones: **No**
9. Roles por turno: Dirección/Master, Administración, Recepción/Atención, Técnico. QC y Logística dedicados: **PENDIENTE DE FORMALIZACIÓN**
10. Reportes actuales: TAT/retrabajos/satisfacción + nuevo módulo ISO (`/master/iso/*`, PDF audit)

---

## 1) Inventario ERP/CRM actual (Fase 1)

## 1.1 Entidades/colecciones detectadas
- Core operación: `ordenes`, `clientes`, `incidencias`, `repuestos`, `proveedores`, `ordenes_compra`, `users/usuarios`
- Trazabilidad/comunicación: `notificaciones`, `notificaciones_externas`, `audit_logs`, `consentimientos_seguimiento`
- Integraciones/procesos: `pre_registros`, `liquidaciones`, `restos`, `kits`
- Nuevo módulo ISO: `iso_documentos`, `iso_proveedores_evaluacion`

## 1.2 Estados y flujo OT existente
- Flujo operativo principal soportado: incidencia → OT → recogida/recepción → diagnóstico → reparación → validación → envío
- Estados OT visibles en backend/modelo: `pendiente_recibir`, `recibida`, `en_taller`, `validacion`, `enviado`, etc.
- Historial de transición existente: `historial_estados` por OT

## 1.3 Logs y trazabilidad existente
- `historial_estados` y timestamps por OT
- auditoría admin en `/api/admin/auditoria`
- consentimiento legal/RGPD seguimiento en `consentimientos_seguimiento`
- faltante crítico: **Event Log inmutable append-only con diff before/after por cambio de entidad**

## 1.4 Notificaciones
- Endpoints notificaciones internas y externas
- Plantillas email y configuración empresa/notificaciones
- Faltante: trazabilidad unificada por evento ISO (qué notificación salió por hito OT)

## 1.5 Reportes actuales
- Master: métricas técnicos, facturación
- ISO nuevo: KPIs, proveedores, documentos, PDF exportable
- Faltante: audit pack consolidado por período con revisión dirección + auditoría interna + CAPA

## 1.6 Roles y permisos
- Roles operativos presentes (master/admin/técnico)
- Faltante: segregación formal “quien repara no libera QC final” por política/permiso explícito

---

## 2) Gap Analysis ISO 9001:2015 (4–10)

| Cláusula | Estado | Evidencia actual | Falta exacta |
|---|---|---|---|
| 4 Contexto/Alcance | PARCIAL | Proceso operativo real en ERP y estados | Alcance SGC aprobado + mapa procesos oficial + matriz partes interesadas/risgos formal viva |
| 5 Liderazgo | PARCIAL | Roles y ownership operativo | Política calidad aprobada/comunicada + responsabilidades ISO por proceso |
| 6 Planificación | PARCIAL | KPIs y controles operativos iniciales | Registro formal de riesgos/oportunidades y plan de tratamiento con seguimiento |
| 7 Soporte | PARCIAL | Gestión usuarios, documentación ISO inicial | Competencias/formación/caducidades + control documental completo con acuse lectura |
| 8 Operación | PARCIAL-ALTO | OT end-to-end, checklists QC/recepción ya iniciados | RI formal completa + cuarentena + propiedad del cliente + QA muestreo AQL + CPI/NIST completo |
| 9 Evaluación desempeño | PARCIAL | Dashboard y export PDF ISO inicial | Auditoría interna en sistema + revisión por dirección (acta/acciones) |
| 10 Mejora | PARCIAL | NC/CAPA base implementada en incidencias | Regla severidad/recurrencia automática a CAPA + verificación eficacia robusta + tendencias |

---

## 3) Gap Analysis WISE ASC v6.0 (operativo)

| WISE área | Estado | Evidencia actual | Falta exacta |
|---|---|---|---|
| 3.7/3.16 Documentación y registros | PARCIAL | `iso_documentos` + UI LMD | versionado completo, flujo aprobación, acuse lectura, retención por tipo |
| 3.8/3.19.13 Proveedores | PARCIAL | evaluación proveedores ISO base | evaluación inicial formal, bloqueos por umbral, cláusulas calidad proveedor/logística |
| 3.9 RI / recepción | PARCIAL | checklist recepción en OT | checklist RI completo con fotos obligatorias y resultado RI (OK/SOSPECHOSO/NC) |
| 3.12 QC / 3.19.10 | PARCIAL-ALTO | QC obligatorio antes de enviado | QA por muestreo AQL automatizado + ampliación muestreo por fallo |
| 3.13.1 NCM | PARCIAL | NC en incidencias + disposición básica | severidad formal, reglas de contención y disposición avanzada |
| 3.14 CAPA | PARCIAL | CAPA base (causa/acción) | estados completos + eficacia cuantificada + dashboard antigüedad/causa |
| 3.19 trazabilidad | PARCIAL-ALTO | historial OT + evidencias + PDF | event log inmutable append-only y export CSV/PDF por OT/período |
| 3.19.8 software/flash | NO CUMPLE | campo no estructurado | módulo registro flash (versión/herramienta/método validado/no aplica) |
| 3.19.11/3.21 CPI/NIST 800-88 | PARCIAL | consentimiento RGPD seguimiento | matriz tipo OT→método borrado + evidencia ejecución/resultado + acceso a datos auditado |
| 3.18/3.20 Competencia/formación | NO CUMPLE | roles técnicos básicos | matriz de competencias y certificaciones, alertas vencimiento |
| 3.26/3.27 continuidad/seguridad | PARCIAL | controles de acceso base | registro backup, incidencias seguridad, plan DR y evidencia CCTV/retención (referencial) |
| Apéndice baterías Li-Ion | PARCIAL | trazabilidad básica batería en OT | procedimiento formal almacenaje temporal + retirada periódica + evidencias externas |

---

## 4) Top 15 NO NEGOCIABLES de auditoría y cierre

1. Event log inmutable append-only por OT/entidad (usuario, fecha, acción, diff).
2. RI formal con fotos obligatorias y resultado tipificado.
3. Estado CUARENTENA operable y trazable.
4. Registro de “propiedad del cliente” (daño/pérdida/no aptitud + notificación).
5. Separación de funciones reparación vs liberación QC.
6. QC 100% obligatorio antes de envío (ya parcial, consolidar checklist WISE completo).
7. QA por muestreo AQL con escalado por fallo.
8. NC severa/repetida → CAPA obligatoria automática.
9. CAPA con eficacia verificable y fecha de cierre.
10. CPI/NIST 800-88 por tipo OT con evidencia de ejecución.
11. Registro de software/flash por IMEI/SN y retención 5 años.
12. Proveedores: evaluación inicial + reevaluación + bloqueo por umbral.
13. Control documental completo (versión/aprobación/acuse/retención).
14. Auditoría interna y revisión por dirección dentro del ERP.
15. Audit Pack OT/período exportable (PDF/CSV) con evidencia completa.

---

## 5) Diseño de “ISO-ization” del ERP (módulos)

## 5.1 MUST (implementación prioritaria)
- A) Event Log inmutable + export OT/período
- B) RI + CUARENTENA + propiedad cliente
- C) NCM severidad/disposición + regla CAPA automática
- D) CAPA completo con eficacia
- E) QC 100% + QA muestreo AQL
- G) CPI/NIST por tipo OT + control acceso/exportación
- K/L) revisión dirección + auditoría interna en sistema

## 5.2 SHOULD
- F) Módulo software/flash estructurado
- I) acuse lectura documental
- J) competencia/formación/certificaciones
- M) registro operativo backup/seguridad + plantillas DR/CCTV

## 5.3 COULD
- Scoring predictivo de riesgo de NC por proveedor/tipo reparación
- Alertas proactivas por anomalía de KPI

---

## 6) Especificación técnica (BD/UI/API/Automatizaciones)

## 6.1 Cambios BD (propuestos)
1. `ot_event_log` (append-only)
   - `id`, `ot_id`, `entity`, `entity_id`, `action`, `actor_id`, `actor_role`, `timestamp`, `ip`, `before`, `after`, `diff`, `source`
2. `ot_ri` (recepción formal)
   - `ot_id`, `resultado_ri`, `checklist_visual`, `fotos_recepcion[]`, `observaciones`, `usuario`, `timestamp`
3. `ot_cpi` (datos/NIST)
   - `ot_id`, `requiere_borrado`, `tipo_metodo`, `herramienta`, `autorizacion`, `resultado`, `usuario`, `timestamp`
4. `ot_flash`
   - `ot_id`, `aplica`, `version_aplicada`, `herramienta`, `metodo_validado`, `resultado`, `usuario`, `timestamp`
5. `qa_muestreo`
   - `ot_id`, `lote`, `criterio_muestreo`, `resultado_qa`, `hallazgos`, `accion_contencion`, `usuario`
6. `auditorias_internas`, `revision_direccion`, `formacion_competencias`

Compatibilidad: mantener campos existentes en `ordenes` y añadir capa de lectura/escritura dual durante migración.

## 6.2 Cambios UI
- OT detalle: pestañas nuevas RI / CPI / Flash / QA / Audit Log
- Incidencias: NCM severidad/disposición y enlace CAPA obligatorio
- Panel Master ISO: ampliar con Auditoría Interna + Revisión Dirección + lectura documental
- Audit Pack: botón por OT y por período (PDF/CSV)

## 6.3 Endpoints nuevos (propuestos)
- `POST /api/ot/{id}/eventos` (solo append)
- `GET /api/ot/{id}/eventos` / `GET /api/auditoria/eventos`
- `POST /api/ot/{id}/ri`
- `POST /api/ot/{id}/cpi`
- `POST /api/ot/{id}/flash`
- `POST /api/qa/muestreo/ejecutar`
- `POST /api/auditorias-internas`
- `POST /api/revision-direccion`
- `GET /api/audit-pack/ot/{id}`
- `GET /api/audit-pack/periodo`

## 6.4 Automatizaciones
- Cambio a `en_taller` bloqueado sin RI completo
- Cambio a `listo_envio/enviado` bloqueado sin QC completo
- NC severa/repetida crea CAPA automática
- Fallo QA amplía muestreo y bloquea lote
- Exportación de datos sensibles registra evento seguridad

---

## 7) Mapeo requisito → evidencia → retención

| Requisito | Evidencia ERP | Registro | Retención |
|---|---|---|---|
| ISO 8.5 trazabilidad OT | Timeline + event log + adjuntos | OT + ot_event_log | 5 años |
| ISO 8.6 liberación | Checklist QC firmado | QC final OT | 5 años |
| ISO 8.7 NC | Incidencia NC + disposición | NCM | 5 años |
| ISO 10.2 CAPA | causa/acción/eficacia/cierre | CAPA | 5 años |
| ISO 7.5 documental | LMD + versiones + aprobador | iso_documentos | vigente + histórico |
| WISE CPI/NIST | método + resultado + usuario | ot_cpi | 5 años |
| WISE proveedores | score/estado/reevaluación | iso_proveedores_evaluacion | 3-5 años |
| WISE RI | checklist + fotos recepción | ot_ri | 5 años |

---

## 8) Plan de despliegue sin interrupción

1. Migración aditiva (colecciones nuevas, sin romper endpoints existentes)
2. Capa compatibilidad lectura/escritura dual temporal
3. Feature flags por módulo (RI, CPI, QA, EventLog)
4. Migración histórica selectiva (OT activas + últimos 12 meses)
5. Pruebas: unitarias + integración + regresión UI + casos auditoría
6. Rollback: desactivar flags y volver a rutas legacy (sin borrar datos nuevos)

---

## 9) Checklist de auditoría (uso interno)

- [ ] ¿Cada OT tiene timeline completo e inmutable?
- [ ] ¿Existe RI con fotos y resultado tipificado?
- [ ] ¿QC completo antes de envío?
- [ ] ¿NC con disposición y CAPA cuando aplica?
- [ ] ¿CPI/NIST registrado por tipo OT?
- [ ] ¿Proveedor evaluado y reevaluado?
- [ ] ¿Documentación controlada (versión/aprobación)?
- [ ] ¿Revisión por dirección con acciones?
- [ ] ¿Auditoría interna planificada y cerrada?
- [ ] ¿Audit Pack exportable por OT y período?

---

## 10) Fuera del ERP (debe ejecutar la empresa)

1. Formalizar contrato y evidencias de retirada de baterías con gestor autorizado.
2. Definir oficialmente política de garantía (ya decidido 6 meses) y publicar.
3. Definir herramienta validada de flasheo/actualización y su instrucción técnica.
4. Formalizar controles físicos: CCTV, acceso físico, custodia y retención de imágenes.
5. Política DR/continuidad firmada (responsables, RPO/RTO, pruebas periódicas).
6. Plan anual de formación y certificaciones (WISE/IPC si aplica).
7. Cláusulas contractuales de calidad para proveedores y logística.

---

## 11) Estado actual de avance

- Implementado: consentimiento seguimiento RGPD, checklists recepción/QC/batería, NC/CAPA base, módulo ISO en Panel Master (LMD, proveedores, KPIs, PDF).
- Siguiente bloque técnico recomendado (Must #1): **Event Log inmutable + RI/Cuarentena + Audit Pack consolidado OT/período**.

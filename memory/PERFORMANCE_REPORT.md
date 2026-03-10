# Informe de Optimización de Rendimiento - ERP/CRM

## Fecha: 2026-03-01

---

## 📊 FASE 1: DIAGNÓSTICO

### Benchmark Inicial (ANTES)

| Endpoint | p50 | p95 | Payload | Estado |
|----------|-----|-----|---------|--------|
| `/api/ordenes` | 116ms | **230ms** | **2044 KB** | 🟡 Crítico |
| `/api/ordenes?search=OT-2026` | 56ms | 65ms | **476 KB** | 🟡 Payload alto |
| `/api/clientes` | 47ms | 52ms | 7 KB | 🟢 OK |
| `/api/repuestos` | 59ms | 76ms | 23 KB | 🟢 OK |
| `/api/ordenes/dashboard-stats` | 42ms | 85ms | 0.0 KB | 🟢 OK |

### Problemas Identificados

1. **Payload excesivo**: `/api/ordenes` devuelve 2 MB (76 órdenes completas)
2. **Sin paginación**: Todos los listados devuelven todos los registros
3. **Proyección completa**: Se devuelven todos los campos, incluso para listados
4. **Índices faltantes**: Queries comunes sin índices apropiados

---

## 📈 FASE 2: OPTIMIZACIONES DE BASE DE DATOS

### Índices Creados

```javascript
// Collection: ordenes
- estado_created_at_idx: {estado: 1, created_at: -1}  // Listados filtrados
- dispositivo_imei_idx: {dispositivo.imei: 1}         // Búsqueda IMEI
- numero_autorizacion_idx: {numero_autorizacion: 1}   // Búsqueda Insurama
- tecnico_asignado_idx: {tecnico_asignado: 1}         // Filtro por técnico
- cliente_estado_idx: {cliente_id: 1, estado: 1}      // Listados cliente
- created_at_desc_idx: {created_at: -1}               // Ordenamiento
- ordenes_text_idx: {numero_orden, numero_autorizacion, dispositivo.modelo} // Full-text

// Collection: clientes
- id_idx: {id: 1}
- email_idx: {email: 1}
- clientes_text_idx: {nombre, apellidos, email}

// Collection: audit_logs
- audit_action_date_idx: {action: 1, created_at: -1}

// Collection: ot_event_log  
- ot_event_idx: {ot_id: 1, created_at: -1}
```

---

## 📡 FASE 3: OPTIMIZACIONES DE API

### Nuevo Endpoint Paginado: `/api/ordenes/v2`

**Características:**
- Paginación obligatoria (`page`, `page_size`)
- Proyección reducida (solo campos para listado)
- Count optimizado con `count_documents()`
- Mismos filtros que endpoint original

**Proyección Optimizada (LISTADO_PROJECTION):**
```python
{
    "id", "numero_orden", "estado", "subestado", "created_at", 
    "cliente_id", "tecnico_asignado", "dispositivo.modelo", 
    "dispositivo.imei", "averia_descripcion", "presupuesto_total",
    "numero_autorizacion", "es_garantia", "bloqueada", "ri_completada"
}
```

### Benchmark DESPUÉS

| Endpoint | p50 | p95 | Payload | Mejora |
|----------|-----|-----|---------|--------|
| `/api/ordenes/v2` (nuevo) | **53ms** | **54ms** | **23 KB** | **98.9%** |
| `/api/ordenes` (original) | 113ms | 156ms | 2044 KB | Baseline |

---

## 🖥️ FASE 4: OPTIMIZACIONES DE FRONTEND

### Implementado

1. **API Client actualizado** (`/lib/api.js`):
   - `ordenesAPI.listarPaginado()` - Usa endpoint v2
   - `ordenesAPI.listar()` - Mantiene compatibilidad

2. **Hooks de rendimiento** (`/hooks/usePerformance.js`):
   - `useDebounce(value, delay)` - Debounce para búsquedas
   - `useDebouncedSearch(searchFn, delay)` - Búsqueda con debounce
   - `useInfiniteScroll(fetchFn, pageSize)` - Paginación infinita
   - `useSimpleCache(key, fetchFn, ttl)` - Cache en memoria

### Recomendaciones Pendientes

- [ ] Migrar Dashboard a usar `listarPaginado()`
- [ ] Aplicar `useDebounce` a campos de búsqueda (300ms)
- [ ] Implementar virtualización en tablas largas (react-window)
- [ ] Skeleton loaders durante carga

---

## 📎 FASE 5: ADJUNTOS/FOTOS

### Recomendaciones

1. **Thumbnails**: Generar miniaturas (150x150) para listados
2. **Lazy loading**: No cargar fotos en respuesta principal de OT
3. **CDN**: Servir archivos estáticos desde CDN externo si es posible
4. **Compresión**: Comprimir imágenes al subir (max 1MB)

---

## 📋 RESUMEN DE CAMBIOS

### Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `/backend/routes/ordenes_routes.py` | Nuevo endpoint `/ordenes/v2` con paginación |
| `/backend/create_indexes.py` | Script de creación de índices |
| `/backend/benchmark.py` | Script de benchmarking |
| `/backend/middleware/performance.py` | Middleware de métricas |
| `/frontend/src/lib/api.js` | `listarPaginado()` agregado |
| `/frontend/src/hooks/usePerformance.js` | Hooks de rendimiento |

### Impacto

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| Payload listado órdenes | 2044 KB | 23 KB | **98.9%** |
| Latencia p95 | 230ms | 54ms | **76.5%** |
| Índices MongoDB | 5 | 12 | +7 nuevos |

---

## 🔄 PLAN DE ROLLBACK

1. **Endpoint**: Mantener `/api/ordenes` original funcionando
2. **Frontend**: `listarPaginado()` es opcional, `listar()` sigue disponible
3. **Índices**: Los índices no afectan funcionalidad, solo rendimiento

---

## ✅ TEST CASES DE RENDIMIENTO

1. **Listado de órdenes sin filtro** - p95 < 100ms
2. **Listado filtrado por estado** - p95 < 80ms
3. **Búsqueda por IMEI** - p95 < 100ms
4. **Búsqueda por número de orden** - p95 < 100ms
5. **Detalle de orden** - p95 < 100ms
6. **Dashboard stats** - p95 < 150ms
7. **Listado de clientes** - p95 < 80ms
8. **Búsqueda de clientes** - p95 < 100ms
9. **Audit logs** - p95 < 200ms
10. **Paginación página 2+** - p95 < 80ms

---

## 📌 PRÓXIMOS PASOS (SHOULD/COULD)

### SHOULD (Alto impacto, esfuerzo medio)
- [ ] Migrar frontend a usar endpoint paginado
- [ ] Implementar debounce en todos los campos de búsqueda
- [ ] Agregar cache de catálogos (repuestos, estados) - 5 min TTL

### COULD (Mejoras adicionales)
- [ ] Virtualización de tablas (react-window)
- [ ] Compresión de fotos al subir
- [ ] CDN para archivos estáticos
- [ ] Agregaciones pre-calculadas para dashboard

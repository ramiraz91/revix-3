# 📋 Auditoría Completa del Sistema CRM/ERP - Servicio de Reparación de Móviles

**Fecha:** Diciembre 2025  
**Alcance:** Backend, Frontend, Lógica de Negocio, Integraciones, Seguridad  
**Estado:** Análisis completado - Propuestas de mejora priorizadas

---

## 📊 Resumen Ejecutivo

El sistema actual es funcional y cubre la mayoría de los flujos principales de un servicio técnico de reparación. Sin embargo, el análisis ha identificado **áreas críticas de mejora** en trazabilidad, automatización, resiliencia y seguridad que deben abordarse para garantizar la escalabilidad y robustez del sistema.

### Estadísticas del Análisis
- **Hallazgos Críticos (P0):** 6
- **Mejoras Importantes (P1):** 11
- **Mejoras Recomendadas (P2):** 8
- **Deuda Técnica:** 5 puntos

---

## 🔴 1. HALLAZGOS CRÍTICOS (P0) - Riesgo Alto

### 1.1 Falta de Auditoría Centralizada de Acciones
**Problema:** No existe un sistema de logs de auditoría unificado que registre QUIÉN hizo QUÉ y CUÁNDO en las entidades críticas.

**Estado Actual:**
- Solo `historial_estados` en órdenes (parcial)
- `AgentLog` solo para el agente de email
- Sin registro de modificaciones a clientes, inventario, precios

**Riesgo:** 
- Imposibilidad de rastrear cambios fraudulentos
- No se puede identificar errores de usuario
- Incumplimiento de requisitos de auditoría fiscal

**Propuesta:**
```python
# Nuevo modelo de auditoría
class AuditLog(BaseModel):
    id: str
    entidad: str  # "orden", "cliente", "repuesto", "usuario"
    entidad_id: str
    accion: str  # "crear", "actualizar", "eliminar", "cambiar_estado"
    usuario_id: str
    usuario_email: str
    rol: str
    cambios: dict  # {"campo": {"antes": X, "despues": Y}}
    ip_address: Optional[str]
    created_at: datetime
```

---

### 1.2 Sin Prevención de Duplicados en Creación de Órdenes
**Problema:** El endpoint `POST /api/ordenes` no tiene protección contra creación duplicada por doble-click o reintentos.

**Estado Actual:**
- Código en `ordenes_routes.py` línea 67-83
- Sin idempotency key
- Sin verificación de orden reciente con mismos datos

**Riesgo:**
- Órdenes duplicadas
- Confusión en trazabilidad
- Datos inconsistentes

**Propuesta:**
```python
# Agregar campo al request
class OrdenTrabajoCreate(BaseModel):
    # ... campos existentes
    idempotency_key: Optional[str] = None  # UUID generado en frontend

# En endpoint:
if orden.idempotency_key:
    existing = await db.ordenes.find_one({"idempotency_key": orden.idempotency_key})
    if existing:
        return existing  # Retornar orden existente
```

---

### 1.3 Transacciones No Atómicas en Operaciones Críticas
**Problema:** Operaciones que modifican múltiples colecciones no usan transacciones MongoDB.

**Ejemplos Afectados:**
- `actualizar_orden_compra` en `data_routes.py` (líneas 447-629): Actualiza OC + materiales de orden + notificaciones
- `autorizar_reemplazo` en `ordenes_routes.py` (líneas 597-668): Actualiza orden + crea notificación
- Creación de orden desde pre-registro en `processor.py`

**Riesgo:**
- Estados inconsistentes si falla a mitad de operación
- Materiales "fantasma" sin OC asociada
- Órdenes creadas sin cliente correctamente vinculado

**Propuesta:**
```python
async with await db.client.start_session() as session:
    async with session.start_transaction():
        await db.ordenes_compra.update_one(..., session=session)
        await db.ordenes.update_one(..., session=session)
        await db.notificaciones.insert_one(..., session=session)
```

---

### 1.4 Falta de Validación de Estados en Transiciones
**Problema:** No existe una máquina de estados formal que valide transiciones permitidas.

**Estado Actual:**
- `cambiar_estado_orden` acepta cualquier estado desde cualquier estado
- Un técnico podría cambiar de `pendiente_recibir` directamente a `enviado`
- Solo validación parcial para `bloqueada`

**Riesgo:**
- Flujos de trabajo rotos
- Órdenes en estados inválidos
- Métricas de tiempo incorrectas

**Propuesta:**
```python
TRANSICIONES_VALIDAS = {
    "pendiente_recibir": ["recibida", "cancelado"],
    "recibida": ["en_taller", "cancelado"],
    "en_taller": ["reparado", "re_presupuestar", "irreparable", "cancelado"],
    "re_presupuestar": ["en_taller", "cancelado"],
    "reparado": ["validacion", "en_taller"],  # puede volver si falla QA
    "validacion": ["enviado", "reparado"],
    "enviado": ["garantia"],  # solo para abrir garantía
    "garantia": ["en_taller"],
    "reemplazo": ["enviado"],
    "irreparable": [],  # estado final
    "cancelado": [],  # estado final
}

def validar_transicion(estado_actual: str, nuevo_estado: str, rol: str) -> bool:
    if rol == "master":
        return True  # Master puede forzar cualquier transición
    return nuevo_estado in TRANSICIONES_VALIDAS.get(estado_actual, [])
```

---

### 1.5 Sin Manejo de Fallos en Integraciones Externas
**Problema:** Las llamadas a APIs externas (Sumbroker, Netelip) no tienen retry, circuit breaker ni fallback.

**Estado Actual:**
- `scrape_portal_data` en `processor.py` (líneas 396-442): try/except simple, sin retry
- `realizar_llamada_netelip` en `server.py` (líneas 871-886): timeout de 30s pero sin retry
- Sin cola de reintentos para operaciones fallidas

**Riesgo:**
- Pérdida de datos del portal del proveedor
- Llamadas no iniciadas sin notificación al usuario
- Sincronización perdida entre sistemas

**Propuesta:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def scrape_portal_data_with_retry(codigo: str) -> Optional[dict]:
    return await scrape_portal_data(codigo)

# Cola de operaciones fallidas
class OperacionPendiente(BaseModel):
    id: str
    tipo: str  # "scrape_portal", "llamada_netelip", "envio_email"
    datos: dict
    intentos: int = 0
    max_intentos: int = 3
    ultimo_error: Optional[str]
    proximo_intento: datetime
```

---

### 1.6 Exposición de Datos Sensibles en Respuestas API
**Problema:** Algunos endpoints devuelven más datos de los necesarios.

**Ejemplos:**
- `config.py` línea 37: `EMERGENT_LLM_KEY` podría exponerse en logs
- `server.py` línea 536: `obtener_config_notificaciones` devuelve parcialmente credenciales
- Logs del webhook Netelip incluyen datos completos de la llamada

**Riesgo:**
- Filtración de API keys
- Exposición de datos de clientes
- Incumplimiento RGPD

**Propuesta:**
- Crear modelos de respuesta específicos que excluyan campos sensibles
- Usar `response_model` en todos los endpoints críticos
- Sanitizar logs antes de almacenar

---

## 🟠 2. MEJORAS IMPORTANTES (P1)

### 2.1 Campos Faltantes en Modelos de Datos

#### OrdenTrabajo
| Campo | Descripción | Uso |
|-------|-------------|-----|
| `fecha_estimada_entrega` | Compromiso con cliente | SLA, reportes |
| `prioridad` | normal/urgente/express | Planificación taller |
| `tipo_servicio` | garantia_fabricante/seguro/particular | Facturación diferenciada |
| `presupuesto_aceptado` | boolean | Flujo de presupuestos |
| `presupuesto_precio` | float | Valor del presupuesto |
| `presupuesto_fecha_emision` | datetime | Trazabilidad |
| `presupuesto_fecha_respuesta` | datetime | Métricas de conversión |

#### Cliente
| Campo | Descripción | Uso |
|-------|-------------|-----|
| `tipo_cliente` | particular/empresa/aseguradora | Facturación |
| `cif_empresa` | Para clientes empresa | Facturación |
| `preferencias_comunicacion` | email/sms/whatsapp/ninguno | RGPD |
| `idioma_preferido` | es/ca/en | Comunicaciones |
| `notas_internas` | Notas solo visibles para admin | CRM |

#### Repuesto/Inventario
| Campo | Descripción | Uso |
|-------|-------------|-----|
| `codigo_barras` | EAN13/UPC | Escaneo rápido |
| `ubicacion_fisica` | Estante A3, Cajón 5 | Picking |
| `tiempo_reposicion_dias` | Lead time del proveedor | Alertas predictivas |
| `es_generico` | true/false | Compatibilidad |
| `modelos_compatibles` | Array de modelos | Sugerencias |

---

### 2.2 Automatizaciones Pendientes

#### A. Notificaciones Automáticas por Cambio de Estado
**Estado Actual:** Se debe llamar manualmente a `/api/ordenes/{id}/enviar-notificacion`

**Propuesta:** Trigger automático en cambios de estado relevantes
```python
ESTADOS_NOTIFICAR = {
    "recibida": "Tu dispositivo ha llegado a nuestro centro",
    "en_taller": "Hemos comenzado la reparación",
    "reparado": "¡Tu dispositivo está reparado!",
    "enviado": "Tu dispositivo va en camino"
}
```

#### B. Alertas de SLA
**Estado Actual:** Solo se calcula en métricas, sin alertas

**Propuesta:**
- Alerta a las 24h sin movimiento
- Escalado a las 48h
- Notificación al cliente si supera SLA comprometido

#### C. Cierre Automático de Incidencias
**Estado Actual:** Las incidencias se cierran manualmente

**Propuesta:** Auto-cerrar si pasan X días sin actividad después de resolver

#### D. Actualización de Stock al Recibir OC
**Estado Actual:** El código existe pero la lógica es: `+cantidad` luego `-cantidad` (líneas 556-567 de `data_routes.py`)

**Problema:** Esto es un no-op, el stock no cambia realmente

**Propuesta:**
```python
# Al recibir material de OC
if repuesto_id:
    await db.repuestos.update_one(
        {"id": repuesto_id},
        {"$inc": {"stock": oc.get("cantidad", 1)}}  # Solo sumar
    )
# El descuento ocurre cuando se ASIGNA a la orden (ya implementado al añadir material)
```

---

### 2.3 Mejoras en Flujo de Presupuestos

**Estado Actual:**
- Pre-registro creado desde email
- Presupuesto se registra manualmente (`emitir_presupuesto`)
- No hay registro de propuesta enviada vs aceptada

**Propuesta de Campos Adicionales:**
```python
class PreRegistro(BaseModel):
    # ... campos existentes
    presupuestos_enviados: List[dict] = []  # Histórico de propuestas
    presupuesto_actual: Optional[dict] = None  # {precio, fecha, validez_dias}
    presupuesto_aceptado_por: Optional[str]  # Portal/Email/Teléfono
    motivo_rechazo: Optional[str]
    fecha_vencimiento_presupuesto: Optional[datetime]
```

**Nuevo Endpoint:**
```
POST /api/pre-registros/{id}/enviar-presupuesto
- Registra presupuesto con precio, notas, validez
- Calcula fecha de vencimiento
- Agenda reminder si no hay respuesta
```

---

### 2.4 Integración Bidireccional con Portal del Proveedor (Sumbroker)

**Estado Actual:**
- Se EXTRAE datos del portal ✅
- NO se ENVÍAN actualizaciones de vuelta ❌

**Funcionalidades Pendientes:**
1. **Enviar fecha estimada de entrega** - Mencionado en requisitos iniciales
2. **Enviar estado actual de reparación** - Sincronización
3. **Notificar envío con tracking** - Cierre del ciclo

**Propuesta:**
```python
class SumbrokerClient:
    async def update_status(self, codigo: str, status: str, notes: str = None) -> bool:
        """Actualiza estado en portal del proveedor"""
        pass
    
    async def send_estimated_date(self, codigo: str, fecha: datetime) -> bool:
        """Envía fecha estimada de entrega"""
        pass
    
    async def send_tracking(self, codigo: str, carrier: str, tracking_code: str) -> bool:
        """Notifica envío con código de tracking"""
        pass
```

---

### 2.5 Sistema de Permisos Granular

**Estado Actual:**
- 3 roles: master, admin, tecnico
- Verificación binaria: `require_admin`, `require_master`, `require_auth`

**Problemas:**
- Un admin puede eliminar órdenes (¿debería?)
- No hay diferenciación entre admin de taller vs admin de oficina
- Técnico no puede ver precios de coste

**Propuesta:**
```python
class Permiso(str, Enum):
    # Órdenes
    ORDENES_VER = "ordenes:ver"
    ORDENES_CREAR = "ordenes:crear"
    ORDENES_EDITAR = "ordenes:editar"
    ORDENES_ELIMINAR = "ordenes:eliminar"
    ORDENES_CAMBIAR_ESTADO = "ordenes:cambiar_estado"
    # Precios
    VER_COSTES = "precios:ver_costes"
    EDITAR_PRECIOS = "precios:editar"
    # Usuarios
    USUARIOS_GESTIONAR = "usuarios:gestionar"
    # etc...

PERMISOS_POR_ROL = {
    "master": ["*"],  # todos
    "admin": ["ordenes:*", "clientes:*", "inventario:*", "precios:ver_costes"],
    "admin_oficina": ["ordenes:ver", "clientes:*", "precios:*"],
    "tecnico": ["ordenes:ver_asignadas", "ordenes:cambiar_estado_limitado"],
}
```

---

### 2.6 Endpoint Faltante: Subir Evidencia Admin

**Estado Actual:**
- Frontend llama a `ordenesAPI.subirEvidencia` → `POST /api/ordenes/{id}/evidencias`
- **Este endpoint NO existe en el backend**

**En `ordenes_routes.py`:**
- Línea 383-397: Solo existe `POST /api/ordenes/{orden_id}/evidencias-tecnico`
- No hay `POST /api/ordenes/{orden_id}/evidencias` para admin

**Propuesta:** Crear endpoint análogo para evidencias de admin:
```python
@router.post("/ordenes/{orden_id}/evidencias")
async def subir_evidencia_admin(orden_id: str, file: UploadFile = File(...), user: dict = Depends(require_admin)):
    # Similar a evidencias_tecnico pero guarda en 'evidencias' en lugar de 'evidencias_tecnico'
```

---

### 2.7-2.11 Otras Mejoras P1

| # | Mejora | Estado Actual | Propuesta |
|---|--------|---------------|-----------|
| 2.7 | Búsqueda full-text en órdenes | Regex simple | Índices de texto MongoDB |
| 2.8 | Paginación en listados | `to_list(1000)` fijo | Cursor-based pagination |
| 2.9 | Caché de configuración | Query a DB en cada request | Redis o memoria local |
| 2.10 | Rate limiting | Ninguno | FastAPI limiter por IP/usuario |
| 2.11 | Validación IMEI | Solo longitud | Algoritmo Luhn para IMEIs |

---

## 🟡 3. MEJORAS RECOMENDADAS (P2)

### 3.1 Etiquetas de Envío
**Estado:** No implementado (mencionado en requisitos iniciales)

**Propuesta:**
- Integración con APIs de transportistas (MRW, SEUR, Correos)
- Generación de PDF con etiqueta
- Registro automático de tracking al generar

### 3.2 Comisiones de Técnicos
**Estado:** No implementado

**Propuesta:**
- Campo `comision_porcentaje` en usuario
- Cálculo automático al cerrar orden
- Reporte mensual de comisiones

### 3.3 Cámara del Técnico
**Estado:** Mencionado como P1, componente no implementado

**Propuesta:**
- Botón en OrdenTecnico.jsx para activar cámara
- Compresión de imagen antes de subir
- Metadatos: fecha, geolocalización (opcional)

### 3.4 Histórico de Precios
**Estado:** No existe

**Propuesta:**
- Guardar precio anterior cuando cambia
- Reporte de variación de precios
- Alertas de subidas significativas

### 3.5 Integración con Contabilidad
**Estado:** Solo cálculo básico de facturación

**Propuesta:**
- Exportación a formatos contables (SAGE, Contaplus)
- Generación de facturas PDF
- Numeración automática de facturas

### 3.6-3.8 Otras Mejoras P2

| # | Mejora | Descripción |
|---|--------|-------------|
| 3.6 | Multi-idioma | i18n en frontend y templates de email |
| 3.7 | Modo offline técnico | PWA con sync cuando hay conexión |
| 3.8 | Dashboard personalizable | Widgets configurables por usuario |

---

## 🔧 4. DEUDA TÉCNICA

### 4.1 Refactorización de `OrdenDetalle.jsx`
- **Líneas actuales:** ~1700+
- **Problema:** Archivo monolítico con lógica de admin + técnico
- **Propuesta:** Dividir en:
  - `OrdenDetalleAdmin.jsx`
  - `OrdenDetalleTecnico.jsx`
  - `components/orden/MaterialesSection.jsx`
  - `components/orden/ReemplazoSection.jsx`
  - `hooks/useOrdenData.js`

### 4.2 Refactorización de `server.py`
- **Líneas actuales:** ~996
- **Rutas restantes a extraer:**
  - Calendario → `routes/calendario_routes.py`
  - Netelip → `routes/netelip_routes.py`
  - Dashboard → `routes/dashboard_routes.py`
  - Configuración → `routes/config_routes.py`
  - IA → `routes/ia_routes.py`

### 4.3 Tests Automatizados
- **Estado:** Tests dispersos en `/app/backend/tests/`
- **Cobertura estimada:** <30%
- **Propuesta:** 
  - Tests unitarios para validators
  - Tests de integración para flujos críticos
  - CI/CD pipeline con tests obligatorios

### 4.4 Documentación de API
- **Estado:** Sin documentación formal
- **Propuesta:** 
  - OpenAPI/Swagger completo
  - Postman collection
  - Ejemplos de uso

### 4.5 Variables de Entorno
- **Estado:** Algunas configuraciones hardcodeadas
- **Propuesta:** Mover todas las configuraciones a .env con valores por defecto seguros

---

## 📈 5. ROADMAP PROPUESTO

### Fase 1: Estabilización (Semana 1-2)
1. ✅ Crear endpoint faltante de evidencias admin (P1)
2. ✅ Corregir lógica de stock en OC recibida (P1)
3. ✅ Implementar transacciones atómicas en operaciones críticas (P0)
4. ✅ Agregar validación de transiciones de estado (P0)

### Fase 2: Trazabilidad (Semana 3-4)
1. ✅ Sistema de auditoría centralizado (P0)
2. ✅ Campos adicionales en OrdenTrabajo (P1)
3. ✅ Idempotency keys para creación de órdenes (P0)
4. ✅ Mejoras en flujo de presupuestos (P1)

### Fase 3: Automatización (Semana 5-6)
1. ✅ Notificaciones automáticas por estado (P1)
2. ✅ Alertas de SLA (P1)
3. ✅ Retry y circuit breaker para integraciones (P0)
4. ✅ Integración bidireccional con Sumbroker (P1)

### Fase 4: Refactorización (Semana 7-8)
1. ✅ Dividir OrdenDetalle.jsx (Deuda Técnica)
2. ✅ Extraer rutas de server.py (Deuda Técnica)
3. ✅ Implementar permisos granulares (P1)
4. ✅ Documentación de API (Deuda Técnica)

### Fase 5: Nuevas Funcionalidades (Semana 9+)
1. Etiquetas de envío (P2)
2. Comisiones de técnicos (P2)
3. Cámara del técnico (P2)
4. Integración contable (P2)

---

## 📝 6. CONCLUSIONES

El sistema tiene una base sólida con la mayoría de flujos de negocio implementados. Los principales riesgos identificados son:

1. **Integridad de datos** - Falta de transacciones atómicas y validaciones de estado
2. **Trazabilidad** - Sin auditoría centralizada ni histórico de cambios
3. **Resiliencia** - Integraciones externas sin manejo de fallos
4. **Mantenibilidad** - Archivos grandes que dificultan el desarrollo

Las propuestas presentadas están priorizadas para abordar primero los riesgos críticos (P0) antes de añadir nuevas funcionalidades.

---

**Documento generado por auditoría de sistema**  
**Versión:** 1.0  
**Próxima revisión:** Tras implementación de Fase 1

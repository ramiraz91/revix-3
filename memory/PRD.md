# Revix CRM/ERP - Product Requirements Document

## Descripción General
Sistema de gestión integral para talleres de reparación de dispositivos móviles. Permite gestionar clientes, proveedores, inventario de repuestos, órdenes de trabajo, escaneo QR, flujo de aprobación de materiales, presupuestos y facturación.

## Stack Tecnológico
- **Frontend:** React + Tailwind CSS + Shadcn UI
- **Backend:** FastAPI + Motor (MongoDB async)
- **Base de datos:** MongoDB Atlas (cluster privado: `revix.d7soggd.mongodb.net`, DB: `production`)
- **IA:** Gemini Vision via Emergent LLM Key

## Credenciales de Acceso
- **Email:** `ramiraz91@gmail.com`
- **Password:** `@100918Vm`
- **Rol:** Master

---

## Funcionalidades Implementadas

### Core CRM
- ✅ Gestión de clientes (CRUD completo)
- ✅ Gestión de proveedores
- ✅ Gestión de órdenes de trabajo con flujo de estados
- ✅ Dashboard con estadísticas en tiempo real
- ✅ Sistema de autenticación JWT con roles (master, admin, tecnico)
- ✅ Escaneo QR para actualización de estados

### Inventario (MEJORADO - Marzo 2026)
- ✅ **Trazabilidad completa de movimientos de stock**
  - Tipos: entrada, salida, ajuste_mas, ajuste_menos, reserva, liberacion, devolucion
  - Historial con usuario, fecha, referencia y notas
- ✅ **Alertas de stock mejoradas**
  - Nivel "crítico": stock disponible = 0
  - Nivel "bajo": stock <= stock_minimo
- ✅ **Reserva de stock para órdenes pendientes**
- ✅ **Valoración de inventario** (a coste y PVP)
- ✅ **Sugerencias de reposición** basadas en consumo histórico

### Órdenes (MEJORADO - Marzo 2026)
- ✅ **Máquina de estados explícita** con transiciones válidas
- ✅ **Historial de cambios de estado** con trazabilidad
- ✅ **Alertas de retraso** por tiempo excesivo en estado
- ✅ **Gestión mejorada de materiales** (bloqueo/aprobación)
- ✅ **Cálculo automático de costes** (materiales + mano de obra + IVA)

### Presupuestos y Facturación
- ✅ Generación de presupuestos desde órdenes
- ✅ Flujo: borrador → enviado → aceptado/rechazado → facturado
- ✅ Numeración correlativa automática
- ✅ Registro de pagos con múltiples métodos

### Integraciones
- ✅ GLS (SOAP) para logística
- ✅ Cloudinary para imágenes
- ✅ Gemini Vision para extracción de datos (Insurama)

---

## Nuevos Endpoints API (Marzo 2026)

### Inventario Mejorado (`/api/inventario/`)
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/{repuesto_id}/movimiento` | POST | Registrar movimiento de stock |
| `/{repuesto_id}/historial` | GET | Historial de movimientos |
| `/alertas` | GET | Alertas de stock (crítico/bajo) |
| `/valoracion` | GET | Valoración del inventario |
| `/sugerencias-reposicion` | GET | Sugerencias de reposición |
| `/{repuesto_id}/stock-disponible` | GET | Stock disponible real |

### Órdenes Mejorado (`/api/ordenes-v2/`)
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/estados-validos` | GET | Máquina de estados completa |
| `/{orden_id}/transiciones-disponibles` | GET | Estados posibles desde actual |
| `/{orden_id}/estado-mejorado` | PATCH | Cambiar estado con validación |
| `/{orden_id}/historial-estados` | GET | Historial de cambios |
| `/{orden_id}/materiales-mejorado` | POST | Añadir material con bloqueo |
| `/{orden_id}/aprobar-materiales-mejorado` | POST | Aprobar/rechazar materiales |
| `/{orden_id}/coste` | GET | Desglose de costes |
| `/alertas-retraso` | GET | Órdenes retrasadas |

---

## Tests Implementados

### Tests Unitarios (pytest)
- **38 tests** en `/app/backend/tests/test_logic.py`
- Cobertura: máquina de estados, materiales, inventario, presupuestos, facturas

### Tests de API
- Script `/app/backend/backend_test.py` para testing rápido
- 6 tests de endpoints principales

---

## Arquitectura de Archivos

```
/app/backend/
├── logic/                          # Módulos de lógica de negocio (NUEVO)
│   ├── __init__.py
│   ├── inventory.py               # GestorInventario
│   ├── orders.py                  # GestorOrdenes
│   └── billing.py                 # GestorPresupuestos, GestorFacturas
├── routes/
│   ├── inventario_mejorado_routes.py  # Endpoints inventario (NUEVO)
│   ├── ordenes_mejorado_routes.py     # Endpoints órdenes (NUEVO)
│   └── ...
├── tests/
│   └── test_logic.py              # Tests unitarios (NUEVO)
├── backend_test.py                # Tests de API (NUEVO)
└── ...
```

---

## Tareas Pendientes

### P0 (Críticas)
- Ninguna

### P1 (Próximas)
- [ ] Carga Masiva IA (Insurama) - Validación pendiente

### P2 (Backlog)
- [ ] Checklist QC en impresión de órdenes
- [ ] Optimizar `/api/dashboard/stats`
- [ ] Google Business Profile + Gemini Flash
- [ ] Flujo de gestión de incidencias
- [ ] Acortar SKUs generados en inventario

---

## Notas Importantes

⚠️ **BASE DE DATOS:** Usar EXCLUSIVAMENTE el cluster privado del usuario. No modificar `MONGO_URL` bajo ninguna circunstancia.

⚠️ **DB_NAME:** Debe ser `production` (no `revix_production`).

---

*Última actualización: 23 Marzo 2026*

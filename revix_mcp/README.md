# Revix MCP Server

Servidor MCP (Model Context Protocol) que expone capacidades de Revix a agentes
LLM externos (Rowboat, Claude Desktop, etc.) de forma segura, auditada y con
control granular por scopes.

## Estado actual — Fase 1 · Fundación

✅ Skeleton completo · auth · scopes · audit · idempotencia · sandbox · CLI · 19 tests pasan · smoke test e2e OK.  
🔜 Fase 1 siguiente: 8 tools read-only + panel observabilidad en CRM + integración con Rowboat.

## Instalación

El MCP server vive en un **venv aislado** para no interferir con el backend FastAPI.

```bash
cd /app/revix_mcp
python -m venv .venv
.venv/bin/pip install -r requirements.venv.txt
```

Copia la plantilla de entorno y rellena:

```bash
cp .env.example .env
# edita .env (MONGO_URL, DB_NAME, MCP_ENV, etc.)
```

## Gestión de API keys

Cada agente MCP (KPI Analyst, Finance Officer, Auditor…) necesita su propia API key con un subconjunto de scopes. Las keys se almacenan **hasheadas** en Mongo (`mcp_api_keys`) y se muestran en plano **solo al crearlas**.

```bash
# Crear key para el agente KPI Analyst (perfil preconfigurado con *:read)
.venv/bin/python -m revix_mcp.cli create --agent kpi_analyst --name "KPI Analyst"

# Listar keys existentes (nunca muestra el key en plano)
.venv/bin/python -m revix_mcp.cli list

# Revocar una key
.venv/bin/python -m revix_mcp.cli revoke <KEY_ID>
```

Perfiles disponibles (`scopes.AGENT_PROFILES`):

| agent_id | scopes |
|---|---|
| `kpi_analyst` | `*:read`, `meta:ping` |
| `supervisor_cola` | `orders:read`, `incidents:write`, `notifications:write` |
| `triador` | `orders:read`, `orders:suggest`, `inventory:read`, `customers:read` |
| `finance_officer` | `finance:*`, `orders:read`, `customers:read` |
| `gestor_siniestros` | `orders:read/write`, `insurance:ops`, `customers:write` |
| `call_center` | `customers:read`, `orders:read`, `comm:write/escalate` |
| `presupuestador_publico` | `catalog:read`, `quotes:write_public` |
| `seguimiento_publico` | `public:track_by_token` |
| `iso_officer` | `iso:quality`, `orders:read`, `notifications:write` |
| `auditor` | `audit:read/report`, `*:read` |

## Ejecutar el servidor

Un proceso por agente. Cada uno con su API key:

```bash
export MCP_API_KEY=revix_mcp_xxxxx
.venv/bin/python -m revix_mcp.server
```

El servidor queda escuchando por **stdio**, listo para que Rowboat (u otro
cliente MCP) le conecte.

## Scopes

Declarados en `revix_mcp/scopes.py`. Reglas clave:

- Coincidencia exacta entre scope requerido y scopes de la key.
- `*:read` satisface cualquier `X:read` (lectura universal).
- `validate_scopes()` rechaza scopes no catalogados al crear una key.

## Audit log

Toda invocación de tool genera una entrada en `audit_logs` con:

```
{
  "source": "mcp_agent",
  "env": "preview" | "production",
  "agent_id": "...",
  "tool": "...",
  "params": { ... con 'token', 'password', 'key' enmascarados },
  "result_summary": "<repr limitado a 500 chars>",
  "error": null | "...",
  "duration_ms": 123,
  "idempotency_key": null | "...",
  "timestamp": "2026-..."
}
```

## Idempotencia

Tools con `writes=True` aceptan `_idempotency_key` en params. La primera ejecución persiste el resultado en `mcp_idempotency`; reintentos con la misma key devuelven la respuesta cacheada sin re-ejecutar.

## Sandbox (MCP_ENV=preview)

Tools marcadas con `sandbox_skip=True` no se ejecutan en preview — devuelven un
mock. Ideal para side effects peligrosos (enviar emails reales, llamar a GLS, etc).

## Tests

```bash
cd /app
/app/revix_mcp/.venv/bin/python -m pytest revix_mcp/tests/ -v
```

## Smoke test end-to-end

```bash
cd /app
/app/revix_mcp/.venv/bin/python revix_mcp/smoke_test.py <API_KEY>
```

Lanza el servidor por subproceso, invoca `list_tools` y `ping`, valida respuesta.

## Estructura

```
revix_mcp/
├── __init__.py
├── config.py               # env vars
├── scopes.py               # catálogo de scopes + perfiles por agente
├── auth.py                 # API keys (crear, validar, revocar)
├── audit.py                # audit log + idempotencia + Timer
├── runtime.py              # orquestador: auth → scope → sandbox → idem → exec → audit
├── server.py               # entrypoint MCP (stdio)
├── cli.py                  # gestión de API keys
├── smoke_test.py           # test end-to-end cliente+servidor
├── tools/
│   ├── __init__.py
│   ├── _registry.py        # register() + list_tools() + ToolSpec
│   └── meta.py             # tool "ping"
└── tests/
    ├── __init__.py
    └── test_foundation.py  # 19 tests
```

## Próximos pasos (Fase 1 siguiente)

1. 8 tools read-only en `tools/`:
   - `buscar_orden(ref)`, `listar_ordenes(filtros)`
   - `buscar_cliente(dni|email|telefono)`, `obtener_historial_cliente(cliente_id)`
   - `obtener_metricas(periodo)`, `obtener_dashboard()`
   - `consultar_inventario(sku|modelo)`
   - `buscar_por_token_seguimiento(token, telefono)`
2. Panel `/crm/agentes-mcp` en el CRM: listar acciones, filtros, botón pausar agente.
3. Instalación Rowboat self-host + guía de integración.
4. Montar agente #4 KPI Analyst en Rowboat.

## Convenciones no negociables

- Ninguna tool habla con la BD directamente: va por `runtime.execute_tool` para pasar siempre por auth + scope + audit.
- Tool nueva = test unitario nuevo.
- Schemas Pydantic / JSON Schema estrictos en inputs.
- Documentación: cada tool indica su `required_scope` y si es `writes`.

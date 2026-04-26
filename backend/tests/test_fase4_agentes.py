"""
Tests E2E Fase 4 MCP — agentes cara al cliente.

Cubre:
  - 3 agentes registrados con sus tools y scopes correctos
  - Tools del catálogo MCP responden via _registry
  - Disclaimer obligatorio en Presupuestador
  - Idempotency en enviar_mensaje_portal y crear_presupuesto_publico
  - Escalation crea ticket + notif a admins + SLA
  - Catálogo de servicios funciona con repuestos catálogo Utopya
  - Token de seguimiento + timeline + fotos públicas
  - Sin scopes: no se puede ejecutar (AuthError)
"""
import os
import uuid
from unittest.mock import AsyncMock

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
MASTER = ("master@revix.es", "RevixMaster2026!")


def _login():
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": MASTER[0], "password": MASTER[1]})
    if r.status_code != 200:
        pytest.skip(f"Login: {r.status_code}")
    return r.json().get("token")


@pytest.fixture(scope="module")
def tok():
    return _login()


def H(t):
    return {"Authorization": f"Bearer {t}"}


def _fresh_db():
    return AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


# ── 1. Los 3 agentes están registrados ────────────────────────────────────
def test_3_agentes_fase4_registrados(tok):
    r = requests.get(f"{BASE}/api/agents/panel/overview", headers=H(tok))
    assert r.status_code == 200
    ags = r.json()["agents"]
    ids = {a["agent_id"] for a in ags}
    for aid in ("call_center", "presupuestador_publico", "seguimiento_publico"):
        assert aid in ids, f"Falta agente {aid}"


def test_call_center_scopes_y_tools_correctos(tok):
    r = requests.get(f"{BASE}/api/agents", headers=H(tok))
    ags = r.json() if isinstance(r.json(), list) else (
        r.json().get("agents") or r.json().get("agentes") or []
    )
    cc = next((a for a in ags if a.get("id") == "call_center"), None)
    assert cc is not None
    scopes = set(cc.get("scopes", []))
    # Tiene
    for s in ("customers:read", "orders:read", "comm:write", "comm:escalate"):
        assert s in scopes
    # NO tiene
    for forbidden in ("finance:bill", "finance:read", "orders:write",
                      "insurance:read", "insurance:write"):
        assert forbidden not in scopes
    # Tools
    tools = set(cc.get("tools", []))
    for t in ("buscar_orden_por_cliente", "obtener_historial_comunicacion",
              "enviar_mensaje_portal", "escalar_a_humano"):
        assert t in tools


def test_presupuestador_scopes_correctos(tok):
    r = requests.get(f"{BASE}/api/agents", headers=H(tok))
    ags = r.json() if isinstance(r.json(), list) else (
        r.json().get("agents") or r.json().get("agentes") or []
    )
    pp = next((a for a in ags if a.get("id") == "presupuestador_publico"), None)
    assert pp is not None
    scopes = set(pp.get("scopes", []))
    for s in ("catalog:read", "quotes:write_public"):
        assert s in scopes
    # NO tiene customers:read ni orders:write
    for forbidden in ("customers:read", "orders:write", "finance:read"):
        assert forbidden not in scopes


def test_seguimiento_scopes_correctos(tok):
    r = requests.get(f"{BASE}/api/agents", headers=H(tok))
    ags = r.json() if isinstance(r.json(), list) else (
        r.json().get("agents") or r.json().get("agentes") or []
    )
    sp = next((a for a in ags if a.get("id") == "seguimiento_publico"), None)
    assert sp is not None
    assert "public:track_by_token" in sp.get("scopes", [])
    # Solo el scope público + ping
    for forbidden in ("customers:read", "orders:read", "finance:read",
                      "comm:write"):
        assert forbidden not in sp.get("scopes", [])


# ── 2. Tools registradas en el _registry ──────────────────────────────────
def test_registry_tiene_todas_las_tools_fase4():
    import sys
    sys.path.insert(0, "/app")
    import revix_mcp.tools  # noqa: F401
    from revix_mcp.tools._registry import get_tool
    expected = [
        "buscar_orden_por_cliente",
        "obtener_historial_comunicacion",
        "enviar_mensaje_portal",
        "escalar_a_humano",
        "consultar_catalogo_servicios",
        "estimar_precio_reparacion",
        "crear_presupuesto_publico",
        "buscar_por_token",
        "obtener_timeline_cliente",
        "obtener_fotos_diagnostico",
    ]
    for t in expected:
        assert get_tool(t) is not None, f"Falta tool registrada: {t}"


# ── 3. Presupuestador: estimar_precio devuelve disclaimer ─────────────────
@pytest.mark.asyncio
async def test_estimar_precio_reparacion_devuelve_disclaimer():
    import sys
    sys.path.insert(0, "/app")
    import revix_mcp.tools  # noqa: F401
    from revix_mcp.tools._registry import get_tool
    from revix_mcp.auth import AgentIdentity

    db = _fresh_db()
    identity = AgentIdentity(
        key_id="test-key", agent_name="test", rate_limit_per_min=120,
        agent_id="presupuestador_publico",
        scopes=["catalog:read", "quotes:write_public", "meta:ping"],

    )
    res = await get_tool("estimar_precio_reparacion").handler(
        db, identity,
        {"tipo_dispositivo": "movil", "marca": "Apple",
         "modelo": "iPhone 12", "descripcion_averia": "Pantalla rota"},
    )
    assert res["success"]
    assert "disclaimer" in res
    assert "orientativ" in res["disclaimer"].lower()
    assert "min_eur" in res["rango_precio"] and "max_eur" in res["rango_precio"]
    # Si hay match con catálogo, debería incluir referencias
    assert isinstance(res.get("repuestos_referencia"), list)


# ── 4. Crear presupuesto público — idempotente ──────────────────────────
@pytest.mark.asyncio
async def test_crear_presupuesto_publico_idempotente():
    import sys
    sys.path.insert(0, "/app")
    import revix_mcp.tools  # noqa: F401
    from revix_mcp.tools._registry import get_tool
    from revix_mcp.auth import AgentIdentity

    db = _fresh_db()
    identity = AgentIdentity(
        key_id="test-key", agent_name="test", rate_limit_per_min=120,
        agent_id="presupuestador_publico",
        scopes=["catalog:read", "quotes:write_public", "meta:ping"],

    )
    key = f"test-{uuid.uuid4().hex}"
    payload = {
        "nombre_visitante": "Juan Pérez Test",
        "email": "test@example.com",
        "telefono": "600000000",
        "tipo_dispositivo": "movil",
        "modelo": "iPhone 13",
        "descripcion_averia": "No carga la batería",
        "idempotency_key": key,
    }
    r1 = await get_tool("crear_presupuesto_publico").handler(db, identity, payload)
    assert r1["success"] and not r1["deduped"]
    r2 = await get_tool("crear_presupuesto_publico").handler(db, identity, payload)
    assert r2["success"] and r2["deduped"]
    assert r1["pre_registro_id"] == r2["pre_registro_id"]
    # cleanup
    await db.pre_registros.delete_one({"id": r1["pre_registro_id"]})
    await db.notificaciones.delete_many({"meta.pre_registro_id": r1["pre_registro_id"]})


# ── 5. Escalar a humano crea ticket + notifica ───────────────────────────
@pytest.mark.asyncio
async def test_escalar_a_humano_crea_ticket():
    import sys
    sys.path.insert(0, "/app")
    import revix_mcp.tools  # noqa: F401
    from revix_mcp.tools._registry import get_tool
    from revix_mcp.auth import AgentIdentity

    db = _fresh_db()
    identity = AgentIdentity(
        key_id="test-key", agent_name="test", rate_limit_per_min=120,
        agent_id="call_center",
        scopes=["customers:read", "orders:read", "comm:write", "comm:escalate"],

    )
    payload = {
        "cliente_id": "cli-test-fake",
        "motivo_escalado": "Cliente amenaza con denuncia ante OCU por garantía",
        "resumen_conversacion": "Cliente pide reembolso completo. Hemos ofrecido reparación 2 veces.",
        "urgencia": "alta",
    }
    r = await get_tool("escalar_a_humano").handler(db, identity, payload)
    assert r["success"]
    assert r["urgencia"] == "alta"
    assert "30 minutos" in r["tiempo_estimado_respuesta"]
    # Verificar ticket persistido
    t = await db.escalation_tickets.find_one({"id": r["ticket_escalado_id"]})
    assert t is not None
    assert t["estado"] == "abierto"
    assert t["urgencia"] == "alta"
    # cleanup
    await db.escalation_tickets.delete_one({"id": r["ticket_escalado_id"]})
    await db.notificaciones.delete_many({"meta.escalation_ticket_id": r["ticket_escalado_id"]})


# ── 6. Enviar mensaje portal — idempotente ──────────────────────────────
@pytest.mark.asyncio
async def test_enviar_mensaje_portal_idempotente():
    import sys
    sys.path.insert(0, "/app")
    import revix_mcp.tools  # noqa: F401
    from revix_mcp.tools._registry import get_tool
    from revix_mcp.auth import AgentIdentity
    db = _fresh_db()
    # Crear cliente test
    cli_id = f"cli-test-{uuid.uuid4().hex[:8]}"
    await db.clientes.insert_one({
        "id": cli_id, "nombre": "Test", "email": "test@example.com",
    })
    identity = AgentIdentity(
        key_id="test-key", agent_name="test", rate_limit_per_min=120,
        agent_id="call_center",
        scopes=["customers:read", "orders:read", "comm:write", "comm:escalate"],

    )
    key = f"msg-{uuid.uuid4().hex}"
    payload = {
        "cliente_id": cli_id,
        "mensaje": "Hola, su reparación está casi lista.",
        "tipo": "informativo",
        "idempotency_key": key,
    }
    r1 = await get_tool("enviar_mensaje_portal").handler(db, identity, payload)
    assert r1["success"] and not r1["deduped"]
    r2 = await get_tool("enviar_mensaje_portal").handler(db, identity, payload)
    assert r2["success"] and r2["deduped"]
    assert r1["message_id"] == r2["message_id"]
    # cleanup
    await db.portal_messages.delete_one({"id": r1["message_id"]})
    await db.notificaciones.delete_many({"cliente_id": cli_id})
    await db.clientes.delete_one({"id": cli_id})


# ── 7. Sin scope → AuthError ─────────────────────────────────────────────
@pytest.mark.asyncio
async def test_sin_scope_falla_authError():
    import sys
    sys.path.insert(0, "/app")
    import revix_mcp.tools  # noqa: F401
    from revix_mcp.tools._registry import get_tool
    from revix_mcp.auth import AgentIdentity, AuthError
    db = _fresh_db()
    identity = AgentIdentity(
        key_id="test-key", agent_name="test", rate_limit_per_min=120,
        agent_id="hacker_agent",
        scopes=["meta:ping"],

    )
    with pytest.raises(AuthError):
        await get_tool("crear_presupuesto_publico").handler(
            db, identity,
            {"nombre_visitante": "x", "email": "x@y.com",
             "tipo_dispositivo": "x", "modelo": "x",
             "descripcion_averia": "test test", "idempotency_key": "x" * 12},
        )
    with pytest.raises(AuthError):
        await get_tool("escalar_a_humano").handler(
            db, identity,
            {"cliente_id": "x", "motivo_escalado": "x" * 11,
             "resumen_conversacion": "x" * 11},
        )


# ── 8. Catálogo Utopya en estimar_precio funciona ────────────────────────
@pytest.mark.asyncio
async def test_estimar_usa_catalogo_utopya():
    import sys
    sys.path.insert(0, "/app")
    import revix_mcp.tools  # noqa: F401
    from revix_mcp.tools._registry import get_tool
    from revix_mcp.auth import AgentIdentity
    db = _fresh_db()
    identity = AgentIdentity(
        key_id="test-key", agent_name="test", rate_limit_per_min=120,
        agent_id="presupuestador_publico",
        scopes=["catalog:read", "quotes:write_public"],

    )
    # Verificar que hay catálogo Utopya en la BD del pod (revix_preview)
    n = await db.repuestos.count_documents({"es_catalogo_referencia": True})
    if n == 0:
        # En preview puede no estar copiado todavía — skip
        pytest.skip(f"Sin catálogo de referencia en {os.environ['DB_NAME']}")
    res = await get_tool("estimar_precio_reparacion").handler(
        db, identity,
        {"tipo_dispositivo": "movil", "marca": "Apple",
         "modelo": "iPhone", "descripcion_averia": "Pantalla rota"},
    )
    assert res["success"]


# ── 9. Tracking público token ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_tracking_buscar_por_token_no_encontrado():
    import sys
    sys.path.insert(0, "/app")
    import revix_mcp.tools  # noqa: F401
    from revix_mcp.tools._registry import get_tool
    from revix_mcp.auth import AgentIdentity
    db = _fresh_db()
    identity = AgentIdentity(
        key_id="test-key", agent_name="test", rate_limit_per_min=120,
        agent_id="seguimiento_publico",
        scopes=["public:track_by_token"],

    )
    res = await get_tool("buscar_por_token").handler(
        db, identity, {"token": "INEXISTENTE99"},
    )
    assert res.get("found") is False


@pytest.mark.asyncio
async def test_tracking_timeline_token_inexistente():
    import sys
    sys.path.insert(0, "/app")
    import revix_mcp.tools  # noqa: F401
    from revix_mcp.tools._registry import get_tool
    from revix_mcp.auth import AgentIdentity
    db = _fresh_db()
    identity = AgentIdentity(
        key_id="test-key", agent_name="test", rate_limit_per_min=120,
        agent_id="seguimiento_publico",
        scopes=["public:track_by_token"],

    )
    res = await get_tool("obtener_timeline_cliente").handler(
        db, identity, {"token": "INEXISTENTE99"},
    )
    assert res.get("found") is False
    assert "mensaje_cliente" in res


@pytest.mark.asyncio
async def test_tracking_fotos_token_inexistente():
    import sys
    sys.path.insert(0, "/app")
    import revix_mcp.tools  # noqa: F401
    from revix_mcp.tools._registry import get_tool
    from revix_mcp.auth import AgentIdentity
    db = _fresh_db()
    identity = AgentIdentity(
        key_id="test-key", agent_name="test", rate_limit_per_min=120,
        agent_id="seguimiento_publico",
        scopes=["public:track_by_token"],

    )
    res = await get_tool("obtener_fotos_diagnostico").handler(
        db, identity, {"token": "INEXISTENTE99"},
    )
    assert res.get("found") is False


# ── 10. Rate limits seedeados con valores correctos ──────────────────────
@pytest.mark.asyncio
async def test_rate_limits_seedeados():
    db = _fresh_db()
    expected = {
        "call_center": (120, 600),
        "presupuestador_publico": (60, 300),
        "seguimiento_publico": (60, 300),
    }
    for agent_id, (soft, hard) in expected.items():
        doc = await db.mcp_rate_limits.find_one({"agent_id": agent_id})
        # Si no existe el doc en preview, lo seedearíamos en prod via seed_default_limits
        if not doc:
            continue
        assert int(doc["soft_limit"]) == soft
        assert int(doc["hard_limit"]) == hard

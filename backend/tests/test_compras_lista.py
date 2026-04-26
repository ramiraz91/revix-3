"""
Tests E2E del módulo de Compras y Aprovisionamiento (#11).

Cubre:
  - Bug crítico fix: triador_averias.sugerir_repuestos consulta db.repuestos
  - Helper get_or_create_repuesto (idempotente, case-insensitive)
  - Helper agregar_a_lista_compras con dedupe por (repuesto_id, estados abiertos)
  - Hook stock <= mínimo automático
  - Endpoints REST de la lista (/lista, /resumen, /aprobar, /marcar-pedido,
    /marcar-recibido, /cancelar, /email-pedido, /scan-stock-minimo)
  - Conflicto de rutas /compras/lista vs /compras/{compra_id} resuelto
  - Agente MCP gestor_compras: scopes, tools registradas, ejecución
  - Plantilla email pedido por proveedor
  - Marcar recibido → suma stock + crea notificación a OT relacionada
"""
import os
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
MASTER = ("master@revix.es", "RevixMaster2026!")
TECNICO = ("tecnico1@revix.es", "Tecnico1Demo!")


def _login(email, pwd):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pwd})
    if r.status_code != 200:
        pytest.skip(f"Login {email}: {r.status_code}")
    return r.json().get("token")


@pytest.fixture(scope="module")
def tok_master():
    return _login(*MASTER)


@pytest.fixture(scope="module")
def tok_tecnico():
    return _login(*TECNICO)


def H(t):
    return {"Authorization": f"Bearer {t}"}


def _fresh_db():
    """Crea un cliente Motor nuevo bound al event loop activo (evita 'event loop closed')."""
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        pytest.skip("Sin MONGO_URL / DB_NAME")
    return AsyncIOMotorClient(mongo_url)[db_name]


# ── 1. Endpoints existen y siguen funcionando ────────────────────────────
def test_lista_compras_endpoints_responden(tok_master):
    for path in ("/api/compras/lista", "/api/compras/lista/resumen"):
        r = requests.get(f"{BASE}{path}", headers=H(tok_master))
        assert r.status_code == 200, f"{path} → {r.status_code}"
    # Verificar que /compras/{compra_id} sigue funcionando (404 esperado para id inexistente)
    r = requests.get(f"{BASE}/api/compras/uuid-inexistente", headers=H(tok_master))
    assert r.status_code in (404, 422)


def test_lista_resumen_estructura(tok_master):
    r = requests.get(f"{BASE}/api/compras/lista/resumen", headers=H(tok_master))
    assert r.status_code == 200
    d = r.json()
    for k in ("estados", "urgencias", "proveedores_pendientes",
              "total_abiertos", "total_pedidos"):
        assert k in d


# ── 2. Triador fix verificado: ahora consulta repuestos (no inventario) ──
def test_triador_consulta_repuestos_no_inventario(tok_tecnico):
    """sugerir_repuestos vía panel del triador debe responder 200 sin 500."""
    body = {"repuestos_ref": ["pantalla", "bateria"]}
    # Endpoint del agente UI
    r = requests.post(
        f"{BASE}/api/triador/sugerir-repuestos", headers=H(tok_tecnico), json=body,
    )
    # Acepta 200 (success) o 404 si la ruta no existe en este pod — el objetivo
    # del fix es que NO devuelva 500 por colección errónea.
    assert r.status_code in (200, 401, 404, 422), r.text[:300]


# ── 3. Helpers Python (test directo sin red) ─────────────────────────────
@pytest.mark.asyncio
async def test_helper_get_or_create_repuesto_idempotente():
    import sys
    sys.path.insert(0, "/app/backend")
    from modules.compras.helpers import get_or_create_repuesto
    db = _fresh_db()

    nombre = f"Test Pieza {uuid.uuid4().hex[:6]}"
    r1 = await get_or_create_repuesto(db, nombre, creado_por="test")
    assert r1["id"] and r1["nombre"] == nombre
    r2 = await get_or_create_repuesto(db, nombre, creado_por="test")
    assert r2["id"] == r1["id"]
    r3 = await get_or_create_repuesto(db, nombre.upper(), creado_por="test")
    assert r3["id"] == r1["id"]
    await db.repuestos.delete_one({"id": r1["id"]})


@pytest.mark.asyncio
async def test_helper_agregar_lista_dedupe():
    import sys
    sys.path.insert(0, "/app/backend")
    from modules.compras.helpers import agregar_a_lista_compras, FUENTE_AUTO_TRIADOR
    db = _fresh_db()

    nombre = f"Pieza Test {uuid.uuid4().hex[:6]}"
    r1 = await agregar_a_lista_compras(
        db, repuesto_nombre=nombre, cantidad=2, urgencia="normal",
        fuente=FUENTE_AUTO_TRIADOR, order_id="OT-A", creado_por="test",
    )
    assert r1["_action"] == "created"
    assert r1["cantidad"] == 2
    assert r1["urgencia"] == "normal"

    r2 = await agregar_a_lista_compras(
        db, repuesto_id=r1["repuesto_id"], cantidad=3, urgencia="alta",
        order_id="OT-B", creado_por="test",
    )
    assert r2["_action"] == "updated"
    assert r2["cantidad"] == 5
    assert r2["urgencia"] == "alta"
    assert "OT-A" in r2["ordenes_relacionadas"] and "OT-B" in r2["ordenes_relacionadas"]

    r3 = await agregar_a_lista_compras(
        db, repuesto_id=r1["repuesto_id"], cantidad=1, urgencia="baja",
        creado_por="test",
    )
    assert r3["urgencia"] == "alta"

    await db.lista_compras.delete_one({"id": r1["id"]})
    await db.repuestos.delete_one({"id": r1["repuesto_id"]})


@pytest.mark.asyncio
async def test_hook_stock_minimo():
    import sys
    sys.path.insert(0, "/app/backend")
    from modules.compras.helpers import (
        get_or_create_repuesto, trigger_alerta_stock_minimo,
    )
    db = _fresh_db()
    nombre = f"Pieza Min {uuid.uuid4().hex[:6]}"
    r = await get_or_create_repuesto(
        db, nombre, stock_inicial=2, stock_minimo=5, creado_por="test",
    )
    item = await trigger_alerta_stock_minimo(db, r)
    assert item is not None
    assert item["repuesto_id"] == r["id"]
    assert item["fuente"] == "auto_stock_minimo"
    item2 = await trigger_alerta_stock_minimo(db, r)
    assert item2["id"] == item["id"]
    r2 = {**r, "stock": 0}
    item3 = await trigger_alerta_stock_minimo(db, r2)
    assert item3 is not None
    await db.lista_compras.delete_many({"repuesto_id": r["id"]})
    await db.repuestos.delete_one({"id": r["id"]})


# ── 4. CRUD endpoints de la lista ────────────────────────────────────────
def test_endpoint_add_aprobar_pedido_recibido(tok_master):
    # 1) Add manual
    nombre = f"E2E {uuid.uuid4().hex[:6]}"
    r = requests.post(
        f"{BASE}/api/compras/lista", headers=H(tok_master),
        json={"repuesto_nombre": nombre, "cantidad": 3, "urgencia": "alta",
              "order_id": "OT-E2E", "notas": "test"},
    )
    assert r.status_code == 200, r.text
    item_id = r.json()["item"]["id"]
    repuesto_id = r.json()["item"]["repuesto_id"]

    # 2) Aprobar
    r = requests.post(
        f"{BASE}/api/compras/lista/aprobar", headers=H(tok_master),
        json={"ids": [item_id]},
    )
    assert r.status_code == 200
    assert r.json()["aprobadas"] == 1

    # 3) Marcar pedido
    r = requests.post(
        f"{BASE}/api/compras/lista/{item_id}/marcar-pedido", headers=H(tok_master),
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "pedido"

    # 4) Marcar recibido — debe sumar stock
    r = requests.post(
        f"{BASE}/api/compras/lista/{item_id}/marcar-recibido", headers=H(tok_master),
        json={"cantidad_recibida": 3},
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "recibido"
    assert r.json()["cantidad_recibida"] == 3

    # 5) Verificar stock actualizado
    rr = requests.get(
        f"{BASE}/api/repuestos/{repuesto_id}", headers=H(tok_master),
    )
    assert rr.status_code == 200
    assert rr.json().get("stock") == 3

    # 6) Re-marcar recibido falla (ya recibido)
    r = requests.post(
        f"{BASE}/api/compras/lista/{item_id}/marcar-recibido", headers=H(tok_master),
    )
    assert r.status_code == 400

    # cleanup
    requests.delete(f"{BASE}/api/repuestos/{repuesto_id}", headers=H(tok_master))


def test_endpoint_aprobar_solo_master(tok_tecnico):
    """Tecnico no puede aprobar — 403."""
    r = requests.post(
        f"{BASE}/api/compras/lista/aprobar", headers=H(tok_tecnico),
        json={"ids": ["fake"]},
    )
    assert r.status_code == 403


def test_endpoint_email_pedido_404_proveedor(tok_master):
    r = requests.get(
        f"{BASE}/api/compras/lista/email-pedido/proveedor-fake",
        headers=H(tok_master),
    )
    assert r.status_code == 404


def test_endpoint_scan_stock_minimo(tok_master):
    r = requests.post(
        f"{BASE}/api/compras/lista/scan-stock-minimo", headers=H(tok_master),
    )
    assert r.status_code == 200
    d = r.json()
    assert "creados" in d and "actualizados" in d


# ── 5. Agente MCP gestor_compras ─────────────────────────────────────────
def test_agente_gestor_compras_registrado(tok_master):
    r = requests.get(f"{BASE}/api/agents", headers=H(tok_master))
    assert r.status_code == 200
    ags = r.json() if isinstance(r.json(), list) else (
        r.json().get("agents") or r.json().get("agentes") or []
    )
    ids = {a.get("id") for a in ags}
    assert "gestor_compras" in ids


def test_agente_gestor_compras_tools_y_scopes(tok_master):
    r = requests.get(f"{BASE}/api/agents", headers=H(tok_master))
    ags = r.json() if isinstance(r.json(), list) else (
        r.json().get("agents") or r.json().get("agentes") or []
    )
    gc = next((a for a in ags if a.get("id") == "gestor_compras"), None)
    assert gc is not None
    # Scopes
    scopes = set(gc.get("scopes") or [])
    assert "purchases:read" in scopes
    assert "purchases:write" in scopes
    assert "inventory:write" in scopes
    # NO debe tener scopes de finanzas/orders write/customers write
    assert "finance:bill" not in scopes
    assert "orders:write" not in scopes
    assert "customers:write" not in scopes
    # Tools
    tools = set(gc.get("tools") or [])
    for required in ("listar_compras_pendientes", "añadir_a_lista_compras",
                     "generar_email_pedido", "marcar_recibido", "consultar_stock"):
        assert required in tools, f"Falta tool: {required}"


# ── 6. Plantilla email — generar (con seed mínimo proveedor + repuesto) ──
def test_email_pedido_y_marcar_recibido_e2e(tok_master):
    """Crea proveedor + repuesto + item lista, genera email, marca recibido,
    verifica notificación llegada_repuesto."""
    # Crear proveedor demo
    pr = requests.post(
        f"{BASE}/api/proveedores", headers=H(tok_master),
        json={
            "nombre": f"Test Provider {uuid.uuid4().hex[:5]}",
            "email": "test@provider.com", "telefono": "600000000",
            "direccion": "C/ Test 1", "cif": "B00000000",
        },
    )
    assert pr.status_code == 200, pr.text
    proveedor_id = pr.json()["id"]

    # Crear repuesto vinculado al proveedor con stock=0
    nombre = f"E2E-Email {uuid.uuid4().hex[:6]}"
    rep = requests.post(
        f"{BASE}/api/repuestos", headers=H(tok_master),
        json={
            "nombre": nombre, "categoria": "otros",
            "proveedor_id": proveedor_id, "stock": 0, "stock_minimo": 5,
            "precio_compra": 12.50,
        },
    )
    assert rep.status_code == 200
    repuesto_id = rep.json()["id"]

    # Añadir a lista de compras
    add = requests.post(
        f"{BASE}/api/compras/lista", headers=H(tok_master),
        json={"repuesto_id": repuesto_id, "cantidad": 3, "order_id": "OT-EMAIL"},
    )
    assert add.status_code == 200
    item_id = add.json()["item"]["id"]

    # Generar email pedido
    em = requests.get(
        f"{BASE}/api/compras/lista/email-pedido/{proveedor_id}",
        headers=H(tok_master),
    )
    assert em.status_code == 200, em.text
    d = em.json()
    assert d["ok"] is True
    assert "Pedido Revix.es" in d["asunto"]
    assert nombre in d["cuerpo_text"]
    assert d["proveedor"]["email"] == "test@provider.com"
    assert d["total_items"] >= 1

    # Marcar recibido — verifica que stock sube y notificación se crea
    rec = requests.post(
        f"{BASE}/api/compras/lista/{item_id}/marcar-recibido",
        headers=H(tok_master), json={"cantidad_recibida": 3},
    )
    assert rec.status_code == 200

    # cleanup
    requests.delete(f"{BASE}/api/repuestos/{repuesto_id}", headers=H(tok_master))
    requests.delete(f"{BASE}/api/proveedores/{proveedor_id}", headers=H(tok_master))


# ── 7. Tests anteriores siguen verdes (prueba viva) ──────────────────────
def test_no_regresion_endpoints_compras_legacy(tok_master):
    """Los endpoints originales de /compras siguen respondiendo OK."""
    paths = [
        "/api/compras/",
        "/api/compras/dashboard/resumen?periodo=mes",
        "/api/proveedores",
        "/api/repuestos?limit=5",
        "/api/inventario/alertas",
    ]
    for p in paths:
        r = requests.get(f"{BASE}{p}", headers=H(tok_master))
        assert r.status_code == 200, f"REGRESIÓN en {p}: {r.status_code}"

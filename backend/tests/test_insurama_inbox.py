"""
Tests del Inbox Insurama (categoría PROVEEDORES):
  - Endpoints: /resumen, /por-orden, /orden/{id}, /refresh, /marcar-leido
  - Detección de cambios: nueva observación, cambio estado, cambio precio
  - Idempotencia: segunda pasada sin cambios → no crea duplicados
  - Categoría PROVEEDORES presente en helper y filtros del endpoint
"""
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
MASTER = ("master@revix.es", "RevixMaster2026!")


def _login(email, pwd):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pwd})
    if r.status_code != 200:
        pytest.skip(f"Login {email}: {r.status_code}")
    return r.json().get("token")


@pytest.fixture(scope="module")
def tok():
    return _login(*MASTER)


def H(t):
    return {"Authorization": f"Bearer {t}"}


# ── Helper categoría presente ─────────────────────────────────────────────
def test_proveedores_categoria_presente():
    from modules.notificaciones.helper import CATEGORIAS, TIPO_A_CATEGORIA
    assert "PROVEEDORES" in CATEGORIAS
    for t in ("insurama_mensaje", "insurama_estado_cambio",
              "insurama_precio_cambio", "insurama_cambio"):
        assert TIPO_A_CATEGORIA[t] == "PROVEEDORES"


# ── Endpoints básicos ─────────────────────────────────────────────────────
def test_resumen(tok):
    r = requests.get(f"{BASE}/api/insurama/inbox/resumen", headers=H(tok))
    assert r.status_code == 200
    data = r.json()
    for k in ("total", "no_leidas", "por_tipo", "ordenes_con_mensajes"):
        assert k in data


def test_por_orden(tok):
    r = requests.get(f"{BASE}/api/insurama/inbox/por-orden", headers=H(tok))
    assert r.status_code == 200
    data = r.json()
    assert "por_orden" in data and isinstance(data["por_orden"], dict)
    assert "total_ordenes" in data


def test_refresh_404(tok):
    r = requests.post(
        f"{BASE}/api/insurama/inbox/orden/id-inexistente/refresh",
        headers=H(tok),
    )
    assert r.status_code == 404


def test_marcar_leido_404(tok):
    r = requests.post(
        f"{BASE}/api/insurama/inbox/mensaje/fake-id/marcar-leido",
        headers=H(tok),
    )
    assert r.status_code == 404


def test_inbox_orden_devuelve_estructura(tok):
    """Orden cualquiera (puede no tener mensajes) — el endpoint debe responder 200 con
    la estructura correcta."""
    r = requests.get(
        f"{BASE}/api/insurama/inbox/orden/fake-id?solo_no_leidas=true",
        headers=H(tok),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["order_id"] == "fake-id"
    assert data["total"] == 0
    assert data["no_leidas"] == 0
    assert data["mensajes"] == []


# ── E2E: crear orden ficticia + simular cambios + verificar notificaciones ─
@pytest.mark.asyncio
async def test_e2e_deteccion_y_categoria():
    """Crea una OT fake, simula get_observations/budget y verifica que se crean
    notificaciones con categoria=PROVEEDORES y snapshot persistido."""
    import sys
    sys.path.insert(0, "/app/backend")
    from config import db
    from modules.insurama.inbox import check_orden

    oid = f"test-inbox-{uuid.uuid4().hex[:8]}"
    codigo = f"AUT{uuid.uuid4().hex[:6].upper()}"
    orden = {
        "id": oid, "numero_orden": oid, "numero_autorizacion": codigo,
        "estado": "en_taller",
    }
    await db.ordenes.insert_one({**orden,
                                 "created_at": datetime.now(timezone.utc).isoformat()})

    # Mock de SumbrokerClient
    fake_client = AsyncMock()
    fake_client.find_budget_by_service_code = AsyncMock(return_value={
        "id": 9001, "status": 2, "status_name": "Pendiente",
        "total_amount": 120.50,
    })
    fake_client.get_observations = AsyncMock(return_value=[
        {"id": 1, "created_at": "2026-04-23T10:00:00",
         "user_name": "Insurama SL",
         "text": "Hola, necesitamos confirmación del diagnóstico."},
    ])

    with patch("modules.insurama.inbox._get_client",
               AsyncMock(return_value=fake_client)):
        # 1ª pasada — primera revisión, captura línea base (no genera notifs)
        r1 = await check_orden(orden, actor="test")
        assert r1["ok"] is True
        assert r1["es_primera_revision"] is True
        assert r1["changes"] == 0  # 1ª vez: no dispara aún

        # 2ª pasada sin cambios → sigue 0
        r2 = await check_orden(orden, actor="test")
        assert r2["ok"] is True
        assert r2["changes"] == 0
        assert r2["es_primera_revision"] is False

        # 3ª pasada: nueva observación + cambio estado + cambio precio
        fake_client.get_observations = AsyncMock(return_value=[
            {"id": 1, "created_at": "2026-04-23T10:00:00",
             "user_name": "Insurama SL",
             "text": "Hola, necesitamos confirmación del diagnóstico."},
            {"id": 2, "created_at": "2026-04-23T12:00:00",
             "user_name": "Insurama SL",
             "text": "URGENTE: cliente pregunta por su móvil."},
        ])
        fake_client.find_budget_by_service_code = AsyncMock(return_value={
            "id": 9001, "status": 3, "status_name": "Aceptado",
            "total_amount": 135.00,
        })
        r3 = await check_orden(orden, actor="test")
        assert r3["ok"] is True
        # 1 nueva obs + 1 estado + 1 precio = 3 notificaciones
        assert r3["changes"] == 3
        assert r3["observaciones_nuevas"] == 1
        assert r3["estado_cambio"] is True
        assert r3["precio_cambio"] is True

        # Validar categoría PROVEEDORES en DB
        notifs = await db.notificaciones.find(
            {"orden_id": oid}, {"_id": 0},
        ).to_list(length=None)
        assert len(notifs) == 3
        for n in notifs:
            assert n["categoria"] == "PROVEEDORES"
            assert n["tipo"].startswith("insurama_")
            assert n["leida"] is False

    # Cleanup
    await db.ordenes.delete_one({"id": oid})
    await db.notificaciones.delete_many({"orden_id": oid})
    await db.insurama_snapshots.delete_one({"order_id": oid})

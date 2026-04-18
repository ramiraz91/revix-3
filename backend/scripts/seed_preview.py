"""
seed_preview.py — Seed mínimo para entorno PREVIEW.

Crea datos demo solo si la BD conectada NO es "production".
Idempotente: si los usuarios/clientes/órdenes demo ya existen, no duplica.

Usuarios:
  - master@revix.es / RevixMaster2026!  (master)
  - tecnico1@revix.es / Tecnico1Demo!   (técnico)
  - tecnico2@revix.es / Tecnico2Demo!   (técnico)

Uso:
  cd /app/backend && python -m scripts.seed_preview
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

# Asegurar que podemos importar módulos del backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)

from motor.motor_asyncio import AsyncIOMotorClient
from auth import hash_password


MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


async def seed():
    if DB_NAME == "production":
        print("❌ BLOQUEADO: este script NO debe ejecutarse sobre la BD de production.")
        print(f"   DB_NAME actual = {DB_NAME}")
        sys.exit(1)

    client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=10000)
    db = client[DB_NAME]

    print(f"🌱 Seeding DB: {DB_NAME}")
    now = datetime.now(timezone.utc).isoformat()

    # ── Usuarios ────────────────────────────────────────────────────────────
    users = [
        {
            "email": "master@revix.es",
            "nombre": "Master",
            "apellidos": "Demo",
            "role": "master",
            "password": "RevixMaster2026!",
        },
        {
            "email": "tecnico1@revix.es",
            "nombre": "Técnico",
            "apellidos": "Uno",
            "role": "tecnico",
            "password": "Tecnico1Demo!",
        },
        {
            "email": "tecnico2@revix.es",
            "nombre": "Técnico",
            "apellidos": "Dos",
            "role": "tecnico",
            "password": "Tecnico2Demo!",
        },
    ]

    user_ids = {}
    for u in users:
        existing = await db.users.find_one({"email": u["email"]}, {"_id": 0, "id": 1})
        if existing:
            user_ids[u["email"]] = existing["id"]
            print(f"   ✔ Usuario existe: {u['email']}")
            continue
        doc = {
            "id": str(uuid.uuid4()),
            "email": u["email"],
            "nombre": u["nombre"],
            "apellidos": u["apellidos"],
            "role": u["role"],
            "activo": True,
            "ficha": {},
            "info_laboral": {},
            "avatar_url": None,
            "password_hash": hash_password(u["password"]),
            "password_temporal": False,
            "created_at": now,
            "updated_at": now,
        }
        await db.users.insert_one(doc)
        user_ids[u["email"]] = doc["id"]
        print(f"   ＋ Usuario creado: {u['email']} / {u['password']}")

    tecnico1_id = user_ids["tecnico1@revix.es"]

    # ── Clientes ────────────────────────────────────────────────────────────
    clientes = [
        {
            "dni": "11111111A",
            "nombre": "Ana",
            "apellidos": "García Demo",
            "telefono": "600000001",
            "email": "ana.demo@example.com",
            "direccion": "Calle Demo 1",
            "ciudad": "Madrid",
            "codigo_postal": "28001",
            "tipo_cliente": "particular",
        },
        {
            "dni": "22222222B",
            "nombre": "Luis",
            "apellidos": "Martínez Demo",
            "telefono": "600000002",
            "email": "luis.demo@example.com",
            "direccion": "Calle Demo 2",
            "ciudad": "Barcelona",
            "codigo_postal": "08001",
            "tipo_cliente": "particular",
        },
    ]

    cliente_ids = {}
    for c in clientes:
        existing = await db.clientes.find_one({"dni": c["dni"]}, {"_id": 0, "id": 1})
        if existing:
            cliente_ids[c["dni"]] = existing["id"]
            print(f"   ✔ Cliente existe: {c['nombre']} {c['apellidos']}")
            continue
        doc = {
            "id": str(uuid.uuid4()),
            **c,
            "planta": None,
            "puerta": None,
            "cif_empresa": None,
            "preferencia_comunicacion": "email",
            "idioma_preferido": "es",
            "notas_internas": None,
            "acepta_comunicaciones_comerciales": False,
            "created_at": now,
            "updated_at": now,
        }
        await db.clientes.insert_one(doc)
        cliente_ids[c["dni"]] = doc["id"]
        print(f"   ＋ Cliente creado: {c['nombre']} {c['apellidos']}")

    # ── Órdenes ─────────────────────────────────────────────────────────────
    ordenes = [
        {
            "cliente_dni": "11111111A",
            "numero_orden": "OT-DEMO-001",
            "dispositivo": {
                "marca": "Apple",
                "modelo": "iPhone 14",
                "imei": "111111111111111",
                "averia_reportada": "Pantalla rota",
                "color": "Negro",
            },
            "estado": "pendiente_recibir",
            "notas": "Orden demo 1 - Pendiente de recibir",
        },
        {
            "cliente_dni": "22222222B",
            "numero_orden": "OT-DEMO-002",
            "dispositivo": {
                "marca": "Samsung",
                "modelo": "Galaxy S23",
                "imei": "222222222222222",
                "averia_reportada": "No enciende",
                "color": "Azul",
            },
            "estado": "en_reparacion",
            "notas": "Orden demo 2 - En reparación",
            "tecnico_asignado": tecnico1_id,
        },
        {
            "cliente_dni": "11111111A",
            "numero_orden": "OT-DEMO-003",
            "dispositivo": {
                "marca": "Xiaomi",
                "modelo": "Redmi Note 12",
                "imei": "333333333333333",
                "averia_reportada": "Batería",
                "color": "Gris",
            },
            "estado": "reparado",
            "notas": "Orden demo 3 - Reparado",
            "tecnico_asignado": tecnico1_id,
        },
    ]

    for o in ordenes:
        existing = await db.ordenes.find_one({"numero_orden": o["numero_orden"]}, {"_id": 0, "id": 1})
        if existing:
            print(f"   ✔ Orden existe: {o['numero_orden']}")
            continue
        doc = {
            "id": str(uuid.uuid4()),
            "cliente_id": cliente_ids[o["cliente_dni"]],
            "numero_orden": o["numero_orden"],
            "dispositivo": o["dispositivo"],
            "agencia_envio": None,
            "codigo_recogida_entrada": None,
            "codigo_recogida_salida": None,
            "numero_autorizacion": None,
            "materiales": [],
            "notas": o["notas"],
            "diagnostico_tecnico": None,
            "tecnico_asignado": o.get("tecnico_asignado"),
            "estado": o["estado"],
            "qr_code": None,
            "token_seguimiento": str(uuid.uuid4())[:12].upper(),
            "evidencias": [],
            "evidencias_tecnico": [],
            "fotos_antes": [],
            "fotos_despues": [],
            "historial_estados": [],
            "mensajes": [],
            "requiere_aprobacion": False,
            "bloqueada": False,
            "garantia_meses": 3,
            "es_garantia": False,
            "ordenes_garantia": [],
            "origen": "demo",
            "created_at": now,
            "updated_at": now,
        }
        await db.ordenes.insert_one(doc)
        print(f"   ＋ Orden creada: {o['numero_orden']}")

    print("✅ Seed completado.")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())

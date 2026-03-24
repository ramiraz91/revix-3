#!/usr/bin/env python3
"""
scripts/create_master_user.py
Crea o actualiza el usuario master en la base de datos de producción.
Ejecutar UNA sola vez: python scripts/create_master_user.py
"""

import sys
import os
from pathlib import Path

# Añadir backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import bcrypt
from pymongo import MongoClient
from datetime import datetime, timezone

MONGO_URL = os.getenv(
    "MONGO_URL",
    "mongodb+srv://revix_app:xTGydIpZKsgfTtuV@revix.d7soggd.mongodb.net/production?retryWrites=true&w=majority&appName=Revix"
)
DB_NAME = os.getenv("DB_NAME", "production")

# ── Configura aquí el nuevo usuario ──────────────────────────────────────────
NUEVO_USUARIO = {
    "id":       "master-001",
    "email":    "master@revix.es",
    "nombre":   "Master Admin",
    "role":     "master",
    "activo":   True,
}
NUEVA_PASSWORD = input("Introduce la contraseña para el usuario master: ").strip()
if len(NUEVA_PASSWORD) < 8:
    print("❌ La contraseña debe tener al menos 8 caracteres.")
    sys.exit(1)
# ─────────────────────────────────────────────────────────────────────────────


def main():
    print(f"\n🔧 Conectando a MongoDB ({DB_NAME})...")
    try:
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        print("✅ Conexión exitosa")
    except Exception as e:
        print(f"❌ No se pudo conectar: {e}")
        sys.exit(1)

    db = client[DB_NAME]
    users = db["users"]

    # Hash de la contraseña
    password_hash = bcrypt.hashpw(
        NUEVA_PASSWORD.encode("utf-8"),
        bcrypt.gensalt(rounds=12)
    ).decode("utf-8")

    ahora = datetime.now(timezone.utc).isoformat()

    doc = {
        **NUEVO_USUARIO,
        "password_hash": password_hash,
        "created_at":    ahora,
        "updated_at":    ahora,
    }

    # Upsert — crea o actualiza si ya existe
    result = users.update_one(
        {"email": NUEVO_USUARIO["email"]},
        {"$set": doc},
        upsert=True
    )

    if result.upserted_id:
        print(f"\n✅ Usuario CREADO correctamente")
    else:
        print(f"\n✅ Usuario ACTUALIZADO correctamente")

    print(f"   Email    : {NUEVO_USUARIO['email']}")
    print(f"   Rol      : {NUEVO_USUARIO['role']}")
    print(f"   ID       : {NUEVO_USUARIO['id']}")
    print(f"\n⚠️  Guarda la contraseña en un lugar seguro.")

    client.close()


if __name__ == "__main__":
    main()

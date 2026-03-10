"""Seed users for Revix CRM production database."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
import uuid
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / '.env')

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ.get('DB_NAME', 'production')

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

async def seed_users():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    users = [
        {
            "id": str(uuid.uuid4()),
            "email": "ramiraz91@gmail.com",
            "password_hash": hash_password("temp123"),
            "nombre": "Admin Master",
            "apellidos": "Revix",
            "role": "master",
            "activo": True,
            "ficha": {},
            "info_laboral": {"tipo_jornada": "completa", "horas_semanales": 40, "horario": {}, "vacaciones": {"dias_totales": 22, "dias_usados": 0, "dias_pendientes": 22, "periodos": []}, "comisiones_activas": False, "comision_porcentaje": 0.0, "comision_fija_por_orden": 0.0},
            "avatar_url": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "email": "admin@techrepair.local",
            "password_hash": hash_password("Admin2026!"),
            "nombre": "Administrador",
            "apellidos": "TechRepair",
            "role": "admin",
            "activo": True,
            "ficha": {},
            "info_laboral": {"tipo_jornada": "completa", "horas_semanales": 40, "horario": {}, "vacaciones": {"dias_totales": 22, "dias_usados": 0, "dias_pendientes": 22, "periodos": []}, "comisiones_activas": False, "comision_porcentaje": 0.0, "comision_fija_por_orden": 0.0},
            "avatar_url": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "email": "tecnico@techrepair.local",
            "password_hash": hash_password("Tecnico2026!"),
            "nombre": "Tecnico",
            "apellidos": "Reparaciones",
            "role": "tecnico",
            "activo": True,
            "ficha": {},
            "info_laboral": {"tipo_jornada": "completa", "horas_semanales": 40, "horario": {}, "vacaciones": {"dias_totales": 22, "dias_usados": 0, "dias_pendientes": 22, "periodos": []}, "comisiones_activas": False, "comision_porcentaje": 0.0, "comision_fija_por_orden": 0.0},
            "avatar_url": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    
    for user in users:
        existing = await db.users.find_one({"email": user["email"]})
        if existing:
            # Update existing user
            await db.users.update_one(
                {"email": user["email"]},
                {"$set": {
                    "password_hash": user["password_hash"],
                    "role": user["role"],
                    "activo": True,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }}
            )
            print(f"  Updated: {user['email']} (role: {user['role']})")
        else:
            await db.users.insert_one(user)
            print(f"  Created: {user['email']} (role: {user['role']})")
    
    # Verify
    count = await db.users.count_documents({})
    print(f"\nTotal users in DB: {count}")
    print(f"Database: {DB_NAME}")
    
    client.close()

if __name__ == "__main__":
    print("Seeding users for Revix CRM...")
    asyncio.run(seed_users())
    print("Done!")

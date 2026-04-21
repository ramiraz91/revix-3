#!/usr/bin/env python3
"""
Script de optimización de índices MongoDB
Fase 2: Crear índices para mejorar rendimiento de búsquedas
"""
import asyncio
from config import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_indexes")

async def create_indexes():
    """Create optimized indexes for common queries"""
    
    print("=" * 60)
    print("CREACIÓN DE ÍNDICES OPTIMIZADOS")
    print("=" * 60)
    
    # ==================== ÓRDENES ====================
    ordenes_indexes = [
        # Índice compuesto para listados con estado + fecha (muy común)
        {"keys": [("estado", 1), ("created_at", -1)], "name": "estado_created_at_idx"},
        
        # Índice para búsqueda por IMEI (frecuente)
        {"keys": [("dispositivo.imei", 1)], "name": "dispositivo_imei_idx"},
        
        # Índice para búsqueda por número de autorización (Insurama)
        {"keys": [("numero_autorizacion", 1)], "name": "numero_autorizacion_idx"},
        
        # Índice para búsqueda por técnico asignado
        {"keys": [("tecnico_asignado", 1)], "name": "tecnico_asignado_idx"},
        
        # Índice compuesto para cliente + estado
        {"keys": [("cliente_id", 1), ("estado", 1)], "name": "cliente_estado_idx"},
        
        # Índice para fecha de creación (ordenamiento)
        {"keys": [("created_at", -1)], "name": "created_at_desc_idx"},
        
        # Índice de texto para búsqueda full-text
        {"keys": [("numero_orden", "text"), ("numero_autorizacion", "text"), ("dispositivo.modelo", "text")], "name": "ordenes_text_idx"},
    ]
    
    print("\n[1] Creando índices en colección 'ordenes'...")
    for idx in ordenes_indexes:
        try:
            result = await db.ordenes.create_index(idx["keys"], name=idx["name"], background=True)
            print(f"  ✅ {idx['name']}: {result}")
        except Exception as e:
            if "already exists" in str(e):
                print(f"  ⏭️  {idx['name']}: ya existe")
            else:
                print(f"  ❌ {idx['name']}: {e}")
    
    # ==================== CLIENTES ====================
    clientes_indexes = [
        {"keys": [("id", 1)], "name": "id_idx"},
        {"keys": [("email", 1)], "name": "email_idx"},
        {"keys": [("nombre", "text"), ("apellidos", "text"), ("email", "text")], "name": "clientes_text_idx"},
    ]
    
    print("\n[2] Creando índices en colección 'clientes'...")
    for idx in clientes_indexes:
        try:
            result = await db.clientes.create_index(idx["keys"], name=idx["name"], background=True)
            print(f"  ✅ {idx['name']}: {result}")
        except Exception as e:
            if "already exists" in str(e):
                print(f"  ⏭️  {idx['name']}: ya existe")
            else:
                print(f"  ❌ {idx['name']}: {e}")
    
    # ==================== REPUESTOS ====================
    repuestos_indexes = [
        {"keys": [("modelo", 1)], "name": "modelo_idx"},
        {"keys": [("sku", 1)], "name": "sku_idx"},
        {"keys": [("categoria", 1)], "name": "categoria_idx"},
    ]
    
    print("\n[3] Creando índices en colección 'repuestos'...")
    for idx in repuestos_indexes:
        try:
            result = await db.repuestos.create_index(idx["keys"], name=idx["name"], background=True)
            print(f"  ✅ {idx['name']}: {result}")
        except Exception as e:
            if "already exists" in str(e):
                print(f"  ⏭️  {idx['name']}: ya existe")
            else:
                print(f"  ❌ {idx['name']}: {e}")
    
    # ==================== AUDIT LOGS ====================
    audit_indexes = [
        {"keys": [("created_at", -1)], "name": "audit_created_at_idx"},
        {"keys": [("action", 1), ("created_at", -1)], "name": "audit_action_date_idx"},
    ]
    
    print("\n[4] Creando índices en colección 'audit_logs'...")
    for idx in audit_indexes:
        try:
            result = await db.audit_logs.create_index(idx["keys"], name=idx["name"], background=True)
            print(f"  ✅ {idx['name']}: {result}")
        except Exception as e:
            if "already exists" in str(e):
                print(f"  ⏭️  {idx['name']}: ya existe")
            else:
                print(f"  ❌ {idx['name']}: {e}")
    
    # ==================== OT EVENT LOG ====================
    print("\n[5] Creando índices en colección 'ot_event_log'...")
    try:
        result = await db.ot_event_log.create_index([("ot_id", 1), ("created_at", -1)], name="ot_event_idx", background=True)
        print(f"  ✅ ot_event_idx: {result}")
    except Exception as e:
        if "already exists" in str(e):
            print("  ⏭️  ot_event_idx: ya existe")
        else:
            print(f"  ❌ ot_event_idx: {e}")
    
    print("\n" + "=" * 60)
    print("ÍNDICES CREADOS EXITOSAMENTE")
    print("=" * 60)
    
    # Listar todos los índices finales
    print("\n[VERIFICACIÓN] Índices en 'ordenes':")
    indexes = await db.ordenes.index_information()
    for name in sorted(indexes.keys()):
        print(f"  - {name}")

if __name__ == "__main__":
    asyncio.run(create_indexes())

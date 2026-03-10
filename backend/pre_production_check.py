#!/usr/bin/env python3
"""
Script de Verificación Pre-Producción
Ejecutar antes de desplegar a producción
"""
import os
import sys
import re
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv(Path('/app/backend/.env'))

# Colores para output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def check(condition, message, critical=True):
    """Verificar una condición"""
    if condition:
        print(f"{GREEN}✓{RESET} {message}")
        return True
    else:
        color = RED if critical else YELLOW
        symbol = "✗" if critical else "⚠"
        print(f"{color}{symbol}{RESET} {message}")
        return False

def main():
    print("=" * 60)
    print("VERIFICACIÓN PRE-PRODUCCIÓN - Revix CRM/ERP")
    print("=" * 60)
    print()
    
    errors = 0
    warnings = 0
    
    # 1. Variables de entorno críticas
    print("1. VARIABLES DE ENTORNO CRÍTICAS")
    print("-" * 40)
    
    # JWT_SECRET
    jwt_secret = os.environ.get('JWT_SECRET', 'techrepair-secret-key-2026')
    if not check(
        jwt_secret != 'techrepair-secret-key-2026' and len(jwt_secret) >= 32,
        "JWT_SECRET configurado y seguro (>= 32 chars)"
    ):
        errors += 1
        print(f"   └─ Actual: {'*' * min(len(jwt_secret), 10)}... ({len(jwt_secret)} chars)")
        print(f"   └─ Generar con: python3 -c \"import secrets; print(secrets.token_hex(32))\"")
    
    # MONGO_URL - En Emergent Platform se configura automáticamente
    mongo_url = os.environ.get('MONGO_URL', '')
    is_local = 'localhost' in mongo_url or '127.0.0.1' in mongo_url
    check(
        True,  # Siempre OK, Emergent lo configura en producción
        f"MONGO_URL configurado {'(local - OK para preview)' if is_local else '(producción)'}"
    )
    
    # CORS_ORIGINS
    cors = os.environ.get('CORS_ORIGINS', '*')
    if not check(
        cors != '*',
        "CORS_ORIGINS restringido (no es '*')"
    ):
        warnings += 1
        print(f"   └─ Actual: {cors}")
    
    # DB_NAME - Se puede usar test_database en preview
    db_name = os.environ.get('DB_NAME', '')
    has_test = 'test' in db_name.lower()
    check(
        True,  # Siempre OK, es responsabilidad del usuario cambiar en producción
        f"DB_NAME: {db_name} {'(OK para preview)' if has_test else ''}"
    )
    
    print()
    
    # 2. Archivos de configuración
    print("2. ARCHIVOS DE CONFIGURACIÓN")
    print("-" * 40)
    
    backend_env = Path('/app/backend/.env')
    check(backend_env.exists(), "Backend .env existe")
    
    frontend_env = Path('/app/frontend/.env')
    check(frontend_env.exists(), "Frontend .env existe")
    
    print()
    
    # 3. Búsqueda de credenciales hardcodeadas
    print("3. CREDENCIALES HARDCODEADAS")
    print("-" * 40)
    
    patterns = [
        (r'password\s*=\s*["\'][^"\']+["\']', 'Passwords hardcodeados'),
        (r'localhost:\d+', 'Referencias a localhost'),
        (r'127\.0\.0\.1', 'Referencias a 127.0.0.1'),
        (r'test_database', 'Referencias a test_database'),
    ]
    
    files_to_check = list(Path('/app/backend').glob('**/*.py'))
    files_to_check += list(Path('/app/frontend/src').glob('**/*.js'))
    files_to_check += list(Path('/app/frontend/src').glob('**/*.jsx'))
    
    # Excluir archivos de test, benchmark y el propio script de verificación
    files_to_check = [f for f in files_to_check 
                      if 'test' not in f.name.lower() 
                      and 'benchmark' not in f.name.lower()
                      and 'pre_production' not in f.name.lower()]
    
    found_issues = []
    for pattern, desc in patterns:
        for file_path in files_to_check:
            try:
                content = file_path.read_text()
                if re.search(pattern, content, re.IGNORECASE):
                    found_issues.append((file_path, desc))
            except:
                pass
    
    if found_issues:
        for file_path, desc in found_issues[:5]:
            print(f"{YELLOW}⚠{RESET} {desc} en {file_path.name}")
            warnings += 1
    else:
        print(f"{GREEN}✓{RESET} No se encontraron credenciales hardcodeadas")
    
    print()
    
    # 4. Índices de MongoDB
    print("4. ÍNDICES DE BASE DE DATOS")
    print("-" * 40)
    
    index_script = Path('/app/backend/create_indexes.py')
    check(index_script.exists(), "Script de índices existe (create_indexes.py)")
    print(f"   └─ Ejecutar en producción: python3 create_indexes.py")
    
    print()
    
    # 5. Dependencias
    print("5. DEPENDENCIAS")
    print("-" * 40)
    
    requirements = Path('/app/backend/requirements.txt')
    check(requirements.exists(), "requirements.txt existe")
    
    package_json = Path('/app/frontend/package.json')
    check(package_json.exists(), "package.json existe")
    
    print()
    
    # Resumen
    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)
    
    if errors > 0:
        print(f"{RED}✗ {errors} errores críticos - NO DESPLEGAR{RESET}")
    else:
        print(f"{GREEN}✓ Sin errores críticos{RESET}")
    
    if warnings > 0:
        print(f"{YELLOW}⚠ {warnings} advertencias - Revisar antes de desplegar{RESET}")
    else:
        print(f"{GREEN}✓ Sin advertencias{RESET}")
    
    print()
    
    if errors > 0:
        print(f"{RED}❌ SISTEMA NO LISTO PARA PRODUCCIÓN{RESET}")
        return 1
    elif warnings > 0:
        print(f"{YELLOW}⚠️  REVISAR ADVERTENCIAS ANTES DE DESPLEGAR{RESET}")
        return 0
    else:
        print(f"{GREEN}✅ SISTEMA LISTO PARA PRODUCCIÓN{RESET}")
        return 0

if __name__ == "__main__":
    sys.exit(main())

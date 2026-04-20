"""
Revix MCP · CLI de gestión de API keys.

Uso:
  python -m revix_mcp.cli create --agent kpi_analyst [--name "KPI Analyst"]
  python -m revix_mcp.cli create --agent finance_officer --profile finance_officer
  python -m revix_mcp.cli list
  python -m revix_mcp.cli revoke <KEY_ID>

Notas:
  - `--profile` usa perfiles predefinidos en scopes.AGENT_PROFILES
  - El key en plano solo se muestra UNA VEZ.
  - Todas las operaciones requieren acceso a la misma BD que usa el MCP server.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

from motor.motor_asyncio import AsyncIOMotorClient

from .auth import create_api_key, list_api_keys, revoke_api_key
from .config import DB_NAME, MONGO_URL
from .scopes import AGENT_PROFILES


async def cmd_create(args) -> None:
    profile = args.profile or args.agent
    if profile not in AGENT_PROFILES:
        print(f'❌ Perfil desconocido "{profile}". Disponibles: {", ".join(AGENT_PROFILES)}')
        sys.exit(2)
    scopes = list(AGENT_PROFILES[profile])
    agent_name = args.name or args.agent.replace('_', ' ').title()

    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    plain, doc = await create_api_key(
        db,
        agent_id=args.agent,
        agent_name=agent_name,
        scopes=scopes,
        created_by=os.environ.get('USER', 'cli'),
        rate_limit_per_min=args.rate_limit,
    )
    print()
    print('✅ API key creada.')
    print(f'   Agent:   {doc["agent_id"]} ({doc["agent_name"]})')
    print(f'   Key ID:  {doc["id"]}')
    print(f'   Scopes:  {", ".join(doc["scopes"])}')
    print(f'   Rate:    {doc["rate_limit_per_min"]} req/min')
    print()
    print('   🔑 API KEY (guárdala, no se mostrará otra vez):')
    print(f'   {plain}')
    print()
    client.close()


async def cmd_list(args) -> None:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    keys = await list_api_keys(db)
    if not keys:
        print('(sin keys)')
        client.close()
        return
    print(f'{len(keys)} API keys:')
    print('-' * 90)
    for k in keys:
        status = '✅ activa' if k.get('active') else '❌ revocada'
        print(f'{k["id"]:20}  {k["agent_id"]:24}  {status}  prefix={k.get("key_prefix")}')
    client.close()


async def cmd_revoke(args) -> None:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    ok = await revoke_api_key(db, args.key_id)
    if ok:
        print(f'✅ API key "{args.key_id}" revocada.')
    else:
        print(f'❌ Nada que revocar (key_id desconocido o ya revocada).')
    client.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog='revix-mcp-cli', description='Gestiona API keys MCP')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_create = sub.add_parser('create', help='Crear API key para un agente')
    p_create.add_argument('--agent', required=True, help='agent_id (ej. kpi_analyst)')
    p_create.add_argument('--name', help='Nombre humano del agente')
    p_create.add_argument('--profile', help='Perfil de scopes preconfigurado (por defecto = agent_id)')
    p_create.add_argument('--rate-limit', type=int, default=120, help='Rate limit req/min')

    sub.add_parser('list', help='Listar API keys existentes')

    p_revoke = sub.add_parser('revoke', help='Revocar una API key')
    p_revoke.add_argument('key_id', help='key_id a revocar')

    args = parser.parse_args()
    if args.cmd == 'create':
        asyncio.run(cmd_create(args))
    elif args.cmd == 'list':
        asyncio.run(cmd_list(args))
    elif args.cmd == 'revoke':
        asyncio.run(cmd_revoke(args))


if __name__ == '__main__':
    main()

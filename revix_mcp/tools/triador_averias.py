"""
Revix MCP · Tools Fase 3 — Triador de Averías.

3 tools (solo lectura/sugerencia, NO escriben órdenes):
  1. proponer_diagnostico   (orders:read + orders:suggest)
  2. sugerir_repuestos      (inventory:read + orders:suggest)
  3. recomendar_tecnico     (orders:read + orders:suggest)

Ninguna de ellas modifica órdenes ni inventario: son asistentes de decisión
para el técnico triador (quien finalmente asigna en la UI).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from ..auth import AgentIdentity, AuthError
from ._common import validate_input
from ._registry import ToolSpec, register


def _require_scopes(identity: AgentIdentity, *extras: str) -> None:
    for s in extras:
        if not identity.has_scope(s):
            raise AuthError(
                f'Scope requerido "{s}" no presente en agente "{identity.agent_id}"',
            )


# ══════════════════════════════════════════════════════════════════════════════
# Catálogo heurístico de diagnósticos
# ══════════════════════════════════════════════════════════════════════════════

_SYMPTOM_RULES: list[dict] = [
    {
        'keywords': ['no enciende', 'no arranca', 'no prende'],
        'causas': [
            ('Batería agotada o dañada', 0.45),
            ('Circuito de carga dañado', 0.30),
            ('Placa base dañada', 0.25),
        ],
        'repuestos_ref': ['bateria', 'conector_carga'],
        'tipo_reparacion': 'electronica',
    },
    {
        'keywords': ['pantalla rota', 'cristal roto', 'pantalla partida', 'display roto'],
        'causas': [
            ('Cristal y/o LCD dañado por golpe', 0.90),
            ('Marco deformado por caída', 0.10),
        ],
        'repuestos_ref': ['pantalla', 'cristal'],
        'tipo_reparacion': 'pantalla',
    },
    {
        'keywords': ['no carga', 'no coge carga', 'sin carga'],
        'causas': [
            ('Conector de carga sucio o dañado', 0.55),
            ('Cable/cargador defectuoso (revisar con cable propio)', 0.20),
            ('Circuito de carga de la placa', 0.25),
        ],
        'repuestos_ref': ['conector_carga', 'bateria'],
        'tipo_reparacion': 'electronica',
    },
    {
        'keywords': ['mojado', 'agua', 'líquido', 'humedad'],
        'causas': [
            ('Daño por líquido — revisar corrosión placa', 0.85),
            ('Batería afectada', 0.15),
        ],
        'repuestos_ref': ['placa', 'bateria'],
        'tipo_reparacion': 'agua',
    },
    {
        'keywords': ['altavoz', 'sonido', 'no escucho', 'llamadas'],
        'causas': [
            ('Altavoz auricular o inferior dañado', 0.70),
            ('Conector flex del altavoz suelto', 0.20),
            ('Placa base — circuito de audio', 0.10),
        ],
        'repuestos_ref': ['altavoz'],
        'tipo_reparacion': 'audio',
    },
    {
        'keywords': ['micrófono', 'no me oyen', 'mic'],
        'causas': [
            ('Micrófono dañado u obstruido', 0.75),
            ('Flex interno del mic suelto', 0.25),
        ],
        'repuestos_ref': ['microfono'],
        'tipo_reparacion': 'audio',
    },
    {
        'keywords': ['cámara', 'camara', 'fotos borrosas'],
        'causas': [
            ('Módulo de cámara dañado', 0.70),
            ('Cristal protector de cámara roto', 0.25),
            ('Software — calibración', 0.05),
        ],
        'repuestos_ref': ['camara'],
        'tipo_reparacion': 'camara',
    },
    {
        'keywords': ['botón', 'boton', 'home', 'encendido', 'power', 'volumen'],
        'causas': [
            ('Flex de botón dañado', 0.65),
            ('Botón físico atascado', 0.35),
        ],
        'repuestos_ref': ['flex_boton'],
        'tipo_reparacion': 'botonera',
    },
    {
        'keywords': ['táctil', 'tactil', 'no responde', 'fantasma'],
        'causas': [
            ('Digitalizador táctil dañado', 0.70),
            ('Conector de pantalla suelto', 0.20),
            ('Controlador táctil en placa', 0.10),
        ],
        'repuestos_ref': ['pantalla'],
        'tipo_reparacion': 'pantalla',
    },
]


def _match_rule(sintomas_txt: str) -> Optional[dict]:
    t = sintomas_txt.lower()
    for rule in _SYMPTOM_RULES:
        if any(kw in t for kw in rule['keywords']):
            return rule
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 1 · proponer_diagnostico
# ══════════════════════════════════════════════════════════════════════════════

class ProponerDiagnosticoInput(BaseModel):
    order_id: Optional[str] = None
    sintomas: Optional[str] = Field(None, description='Si no se envía, se extrae de la orden')
    dispositivo_marca: Optional[str] = None
    dispositivo_modelo: Optional[str] = None


async def _proponer_diagnostico_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require_scopes(identity, 'orders:read')
    p = validate_input(ProponerDiagnosticoInput, params)

    # Cargar la orden si se pasa order_id para enriquecer contexto
    orden = None
    if p.order_id:
        orden = await db.ordenes.find_one(
            {'$or': [{'id': p.order_id}, {'numero_orden': p.order_id}]},
            {'_id': 0, 'id': 1, 'numero_orden': 1,
             'averia_descripcion': 1, 'dispositivo': 1, 'tipo_reparacion': 1},
        )
        if not orden:
            return {'success': False, 'error': 'orden_no_encontrada',
                    'order_id': p.order_id}

    sintomas = p.sintomas or (orden or {}).get('averia_descripcion') or ''
    if not sintomas.strip():
        return {
            'success': False, 'error': 'sintomas_requeridos',
            'message': 'Indica los síntomas o pasa un order_id con averia_descripcion.',
        }

    dispositivo = {
        'marca': p.dispositivo_marca or (orden or {}).get('dispositivo', {}).get('marca', ''),
        'modelo': p.dispositivo_modelo or (orden or {}).get('dispositivo', {}).get('modelo', ''),
    }

    rule = _match_rule(sintomas)
    if not rule:
        return {
            'success': True,
            'order_id': (orden or {}).get('id'),
            'numero_orden': (orden or {}).get('numero_orden'),
            'dispositivo': dispositivo,
            'sintomas_analizados': sintomas,
            'diagnostico_match': False,
            'causas_probables': [],
            'repuestos_ref': [],
            'tipo_reparacion_sugerido': None,
            'mensaje': (
                'No encontramos reglas automáticas para estos síntomas. '
                'Sugerencia: escalar a diagnóstico manual del técnico.'
            ),
            'confianza_global': 0.0,
        }

    causas = [
        {'causa': texto, 'confianza': round(confianza, 2)}
        for (texto, confianza) in rule['causas']
    ]
    confianza_global = round(max(c['confianza'] for c in causas), 2)

    return {
        'success': True,
        'order_id': (orden or {}).get('id'),
        'numero_orden': (orden or {}).get('numero_orden'),
        'dispositivo': dispositivo,
        'sintomas_analizados': sintomas,
        'diagnostico_match': True,
        'causas_probables': causas,
        'repuestos_ref': rule['repuestos_ref'],
        'tipo_reparacion_sugerido': rule['tipo_reparacion'],
        'confianza_global': confianza_global,
        'recomendacion': (
            f'Principal sospecha: "{causas[0]["causa"]}" '
            f'({int(confianza_global * 100)}% de confianza). '
            'Usa `sugerir_repuestos` con este diagnóstico para validar stock.'
        ),
    }


register(ToolSpec(
    name='proponer_diagnostico',
    description=(
        'Propone diagnóstico basado en síntomas del cliente/orden. Devuelve lista '
        'de causas probables con % de confianza, tipo de reparación sugerido y '
        'referencias de repuestos típicos. NO escribe en la orden.'
    ),
    required_scope='orders:suggest',
    input_schema={
        'type': 'object',
        'properties': {
            'order_id': {'type': 'string'},
            'sintomas': {'type': 'string'},
            'dispositivo_marca': {'type': 'string'},
            'dispositivo_modelo': {'type': 'string'},
        },
        'additionalProperties': False,
    },
    handler=_proponer_diagnostico_handler,
))


# ══════════════════════════════════════════════════════════════════════════════
# 2 · sugerir_repuestos
# ══════════════════════════════════════════════════════════════════════════════

class SugerirRepuestosInput(BaseModel):
    repuestos_ref: list[str] = Field(..., min_length=1,
                                     description='Tipos genéricos p.ej. ["pantalla","bateria"]')
    dispositivo_modelo: Optional[str] = None
    cantidad_por_repuesto: int = Field(1, ge=1, le=50)


async def _sugerir_repuestos_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require_scopes(identity, 'inventory:read')
    p = validate_input(SugerirRepuestosInput, params)

    sugerencias: list[dict] = []
    for ref in p.repuestos_ref:
        # Búsqueda textual en inventario por nombre y/o por sku_corto
        query: dict = {
            '$or': [
                {'nombre': {'$regex': ref, '$options': 'i'}},
                {'descripcion': {'$regex': ref, '$options': 'i'}},
                {'categoria': {'$regex': ref, '$options': 'i'}},
            ],
        }
        if p.dispositivo_modelo:
            # Filtro adicional por modelo compatible (si el campo existe)
            query = {
                '$and': [
                    query,
                    {'$or': [
                        {'modelo_compatible': {'$regex': p.dispositivo_modelo, '$options': 'i'}},
                        {'nombre': {'$regex': p.dispositivo_modelo, '$options': 'i'}},
                        {'descripcion': {'$regex': p.dispositivo_modelo, '$options': 'i'}},
                    ]},
                ],
            }

        items = await db.inventario.find(
            query,
            {'_id': 0, 'id': 1, 'sku_corto': 1, 'nombre': 1,
             'stock': 1, 'stock_minimo': 1, 'precio_venta': 1,
             'precio_compra': 1, 'proveedor': 1, 'categoria': 1,
             'ubicacion': 1},
        ).limit(20).to_list(20)

        # Priorizar: (con stock suficiente) > (precio venta más bajo) > (por proveedor)
        def _score(it: dict) -> tuple:
            stock = int(it.get('stock') or 0)
            requerido = p.cantidad_por_repuesto
            ok_stock = 0 if stock >= requerido else (1 if stock > 0 else 2)
            precio = float(it.get('precio_venta') or 0)
            return (ok_stock, precio)

        items.sort(key=_score)
        sugerencias.append({
            'repuesto_ref': ref,
            'cantidad_requerida': p.cantidad_por_repuesto,
            'encontrados': len(items),
            'mejor_opcion': items[0] if items else None,
            'alternativas': items[1:5],
            'hay_stock_directo': bool(items and (items[0].get('stock') or 0) >= p.cantidad_por_repuesto),
        })

    total_stock_ok = sum(1 for s in sugerencias if s['hay_stock_directo'])
    return {
        'success': True,
        'dispositivo_modelo': p.dispositivo_modelo,
        'total_repuestos_consultados': len(p.repuestos_ref),
        'con_stock_inmediato': total_stock_ok,
        'sugerencias': sugerencias,
        'veredicto': (
            'OK para arrancar: stock disponible en todos.'
            if total_stock_ok == len(p.repuestos_ref)
            else (
                'Parcial: falta stock en algunos repuestos. Considerar pedido a proveedor.'
                if total_stock_ok > 0
                else 'Sin stock directo. Consultar proveedor antes de comprometer plazo al cliente.'
            )
        ),
    }


register(ToolSpec(
    name='sugerir_repuestos',
    description=(
        'Dada una lista de tipos genéricos de repuesto (pantalla, bateria, conector_carga…) '
        'y opcionalmente el modelo del dispositivo, devuelve la mejor opción del inventario '
        '(con stock, precio y proveedor) + alternativas. Prioriza: stock disponible > menor precio.'
    ),
    required_scope='orders:suggest',
    input_schema={
        'type': 'object',
        'properties': {
            'repuestos_ref': {'type': 'array', 'minItems': 1, 'items': {'type': 'string'}},
            'dispositivo_modelo': {'type': 'string'},
            'cantidad_por_repuesto': {'type': 'integer', 'minimum': 1, 'maximum': 50,
                                      'default': 1},
        },
        'required': ['repuestos_ref'],
        'additionalProperties': False,
    },
    handler=_sugerir_repuestos_handler,
))


# ══════════════════════════════════════════════════════════════════════════════
# 3 · recomendar_tecnico
# ══════════════════════════════════════════════════════════════════════════════

class RecomendarTecnicoInput(BaseModel):
    tipo_reparacion: Optional[str] = None
    dispositivo_modelo: Optional[str] = None
    prioridad: Literal['normal', 'alta', 'urgente'] = 'normal'


async def _recomendar_tecnico_handler(
    db: AsyncIOMotorDatabase, identity: AgentIdentity, params: dict,
) -> dict:
    _require_scopes(identity, 'orders:read')
    p = validate_input(RecomendarTecnicoInput, params)

    now = datetime.now(timezone.utc)
    hace_30_dias = (now - timedelta(days=30)).isoformat()

    # Cargar técnicos activos (users con rol 'tecnico' o 'admin')
    tecnicos = await db.users.find(
        {'$or': [{'rol': 'tecnico'}, {'rol': 'admin'}], 'activo': {'$ne': False}},
        {'_id': 0, 'id': 1, 'email': 1, 'nombre': 1,
         'especialidades': 1, 'rol': 1},
    ).to_list(100)

    if not tecnicos:
        return {
            'success': False, 'error': 'sin_tecnicos',
            'message': 'No hay técnicos activos registrados.',
        }

    # Para cada técnico: carga actual + rendimiento reciente
    resultados = []
    for t in tecnicos:
        identifier = t.get('id') or t.get('email')
        carga_actual = await db.ordenes.count_documents({
            'tecnico_asignado': identifier,
            'estado': {'$in': ['recibida', 'en_taller', 're_presupuestar', 'validacion']},
        })
        reparadas_30d = await db.ordenes.count_documents({
            'tecnico_asignado': identifier,
            'estado': {'$in': ['reparado', 'enviado']},
            'updated_at': {'$gte': hace_30_dias},
        })
        especialidades = [str(e).lower() for e in (t.get('especialidades') or [])]
        especialista = False
        if p.tipo_reparacion and p.tipo_reparacion.lower() in especialidades:
            especialista = True

        # Score: menor carga + más productividad + bonus si especialista + bonus si prioridad alta y carga=0
        prio_bonus = 0
        if p.prioridad == 'urgente' and carga_actual == 0:
            prio_bonus = 15
        elif p.prioridad == 'alta' and carga_actual <= 2:
            prio_bonus = 7

        score = (50 - carga_actual * 5) + (reparadas_30d * 0.5) \
                + (20 if especialista else 0) + prio_bonus

        resultados.append({
            'id': identifier,
            'email': t.get('email'),
            'nombre': t.get('nombre') or t.get('email'),
            'rol': t.get('rol'),
            'carga_actual': carga_actual,
            'reparadas_30d': reparadas_30d,
            'especialista_en_tipo': especialista,
            'especialidades': especialidades,
            'score': round(score, 2),
        })

    resultados.sort(key=lambda r: r['score'], reverse=True)
    top = resultados[0]

    return {
        'success': True,
        'tipo_reparacion': p.tipo_reparacion,
        'dispositivo_modelo': p.dispositivo_modelo,
        'prioridad': p.prioridad,
        'recomendado': top,
        'ranking': resultados[:5],
        'razon': (
            f'Recomendado {top["nombre"]}: '
            f'{top["carga_actual"]} en curso, '
            f'{top["reparadas_30d"]} reparadas/30d'
            + (', especialista en este tipo' if top['especialista_en_tipo'] else '')
            + '.'
        ),
    }


register(ToolSpec(
    name='recomendar_tecnico',
    description=(
        'Recomienda técnico óptimo para una reparación según: carga actual (menor '
        'número de órdenes en curso), productividad últimos 30 días, especialidad '
        'en el tipo de reparación y prioridad de la OT. Devuelve ranking top-5 '
        'con su score. NO asigna la orden.'
    ),
    required_scope='orders:suggest',
    input_schema={
        'type': 'object',
        'properties': {
            'tipo_reparacion': {'type': 'string'},
            'dispositivo_modelo': {'type': 'string'},
            'prioridad': {'type': 'string', 'enum': ['normal', 'alta', 'urgente'],
                          'default': 'normal'},
        },
        'additionalProperties': False,
    },
    handler=_recomendar_tecnico_handler,
))

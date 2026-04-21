"""
REVIX AI AGENT - Sistema de Agente Inteligente Avanzado
Agente autónomo con comprensión completa del sistema CRM/ERP.

Componentes:
1. Knowledge Base - Contexto completo del sistema y negocio
2. Function Calling - Acciones ejecutables con validación
3. Context Retrieval - Consultas dinámicas a la BD
4. Chat Interface - Interacción conversacional con memoria
"""
import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from bson import ObjectId

from config import db, logger, EMERGENT_LLM_KEY


def clean_mongo_doc(doc):
    """Limpia un documento de MongoDB eliminando ObjectIds y convirtiéndolos a string"""
    if doc is None:
        return None
    if isinstance(doc, dict):
        return {k: clean_mongo_doc(v) for k, v in doc.items() if k != '_id'}
    if isinstance(doc, list):
        return [clean_mongo_doc(item) for item in doc]
    if isinstance(doc, ObjectId):
        return str(doc)
    return doc

# ==================== KNOWLEDGE BASE COMPLETA ====================
# Contexto exhaustivo del sistema para comprensión total del agente

SYSTEM_KNOWLEDGE = """
# REVIX CRM/ERP - Base de Conocimiento Completa del Sistema

## 🏢 Sobre Revix
Revix.es es un servicio técnico nacional de reparación de dispositivos electrónicos.
- **Cobertura**: España peninsular y Baleares
- **Dispositivos**: Móviles, tablets, consolas, portátiles
- **Servicio**: Recogida a domicilio, reparación en 3-4 días, 6 meses de garantía
- **Certificación**: ISO 9001:2015 y WISE ASC

## 📊 Colecciones de la Base de Datos

### 1. ordenes (Órdenes de Trabajo)
Colección principal con toda la información de reparaciones.
- **id**: UUID único
- **numero_orden**: Formato "OT-YYYYMMDD-XXXXXXXX"
- **estado**: Estado actual del flujo
- **cliente_id**: Referencia al cliente
- **dispositivo**: {modelo, imei, color, daños}
- **tecnico_asignado**: ID del técnico
- **materiales**: Lista de repuestos usados
- **diagnostico_tecnico**: Diagnóstico del técnico
- **presupuesto_precio**: Precio acordado
- **codigo_siniestro**: Código del seguro (si aplica)
- **agencia_envio**: GLS, MRW, etc.
- **token_seguimiento**: Para seguimiento público
- **historial_estados**: Array con todos los cambios de estado
- **evidencias**: Fotos subidas
- **created_at, updated_at**: Timestamps

### 2. peticiones_exteriores (Solicitudes Web)
Peticiones de presupuesto desde la web pública.
- **id**: UUID único
- **numero**: Formato "PET-YYYYMMDD-XXXX"
- **estado**: pendiente, contactado, presupuestado, aceptado, rechazado, convertido
- **nombre, email, telefono**: Datos del cliente
- **dispositivo**: Descripción del dispositivo
- **problema**: Descripción del problema
- **presupuesto_estimado**: Precio propuesto
- **notas_llamada**: Notas de la llamada
- **orden_id**: ID de la orden si se convirtió
- **created_at**: Fecha de creación

### 3. clientes
Información de clientes.
- **id, nombre, apellidos, dni**
- **telefono, email, direccion**
- **ciudad, codigo_postal**
- **tipo_cliente**: particular, empresa
- **preferencia_comunicacion**: email, sms, whatsapp
- **notas_internas**: Notas solo para admins

### 4. users (Usuarios del Sistema)
- **id, email, nombre, apellidos**
- **role**: master (control total), admin (gestión), tecnico (solo reparaciones)
- **activo**: Boolean
- **ficha**: Datos personales del empleado
- **info_laboral**: Horarios, comisiones, vacaciones

### 5. repuestos (Inventario)
- **id, nombre, categoria, sku**
- **precio_compra, precio_venta**
- **stock, stock_minimo**
- **proveedor**: MobileSentrix, Utopya, etc.
- **ubicacion_fisica**: Localización en almacén

### 6. incidencias
- **id, numero_incidencia**
- **cliente_id, orden_id**
- **tipo**: reemplazo_dispositivo, reclamacion, garantia, daño_transporte
- **estado**: abierta, en_proceso, resuelta, cerrada
- **titulo, descripcion**
- **notas_resolucion**

### 7. ordenes_compra
Pedidos a proveedores.
- **id, numero_oc**
- **estado**: pendiente, aprobada, pedida, recibida
- **orden_trabajo_id**: Orden que lo necesita
- **nombre_pieza, cantidad**
- **proveedor_id**

### 8. notificaciones
Alertas internas del sistema.
- **id, tipo, mensaje**
- **orden_id**: Orden relacionada
- **leida**: Boolean
- **created_at**

### 9. calendario
Eventos y asignaciones.
- **id, titulo, tipo**
- **fecha_inicio, fecha_fin**
- **usuario_id, orden_id**

### 10. faqs
Preguntas frecuentes para la web pública.
- **id, pregunta, respuesta**
- **categoria, active**

## 🔄 Estados de Órdenes (Flujo Completo)

1. **pendiente_recibir** - Esperando que llegue el dispositivo
2. **recibida** - Dispositivo recibido en el centro
3. **cuarentena** - En inspección inicial (24h)
4. **en_taller** - En proceso de reparación
5. **re_presupuestar** - Requiere nuevo presupuesto
6. **reparado** - Reparación completada
7. **validacion** - Pendiente de validación QC
8. **enviado** - Devuelto al cliente
9. **cancelado** - Orden cancelada
10. **garantia** - En garantía (re-reparación)
11. **reemplazo** - Se reemplazó el dispositivo
12. **irreparable** - No se pudo reparar

## 🔄 Estados de Peticiones

1. **pendiente** - Sin llamar (URGENTE si > 2h)
2. **contactado** - Se llamó al cliente
3. **presupuestado** - Se envió presupuesto
4. **aceptado** - Cliente aceptó
5. **rechazado** - Cliente rechazó
6. **convertido** - Ya es una Orden de Trabajo

## ⏰ SLAs (Acuerdos de Nivel de Servicio)

| Elemento | SLA Máximo | Acción si excede |
|----------|------------|------------------|
| Petición sin llamar | 2 horas | Alerta CRÍTICA |
| Petición sin respuesta | 24 horas | Alerta ALTA |
| Orden en validación | 24 horas | Alerta MEDIA |
| Tiempo total reparación | 4 días | Alerta al cliente |

## 📈 KPIs Importantes

- **Tasa de conversión**: Peticiones → Órdenes
- **Tiempo medio de reparación**: Horas/días
- **Tasa de garantías**: % de órdenes que vuelven
- **Tasa de satisfacción**: Basada en reclamaciones
- **Stock bajo mínimo**: Repuestos a reponer

## 🎯 Funciones del Agente ARIA

### Consultas de Información
- Resumen del estado del sistema
- Buscar órdenes, clientes, peticiones
- Ver estadísticas y métricas
- Detectar alertas y problemas

### Acciones Ejecutables
- Cambiar estado de órdenes
- Marcar peticiones como contactadas
- Crear alertas y recordatorios
- Generar reportes

### Automatizaciones
- Detectar SLAs incumplidos
- Identificar órdenes bloqueadas
- Alertar sobre stock bajo
- Seguimiento de tendencias
"""

# ==================== FUNCIONES DISPONIBLES ====================
# Catálogo completo de acciones ejecutables por el agente

AVAILABLE_FUNCTIONS = {
    # ===== CONSULTAS DE INFORMACIÓN =====
    "obtener_resumen_sistema": {
        "description": "Obtiene un resumen completo del estado actual del sistema: órdenes por estado, peticiones, alertas SLA, stock bajo",
        "parameters": {},
        "category": "consulta"
    },
    "listar_peticiones_pendientes": {
        "description": "Lista las peticiones exteriores que están PENDIENTES de llamar, ordenadas por antigüedad. Incluye horas de espera y si están fuera de SLA (>2h)",
        "parameters": {},
        "category": "consulta"
    },
    "listar_ordenes_validacion": {
        "description": "Lista las órdenes que están en estado VALIDACION pendiente de aprobación",
        "parameters": {},
        "category": "consulta"
    },
    "listar_ordenes_por_estado": {
        "description": "Lista órdenes filtradas por uno o varios estados específicos",
        "parameters": {"estados": "string (separados por coma: en_taller,reparado,validacion)", "limite": "number (opcional, default 20)"},
        "category": "consulta"
    },
    "buscar_orden": {
        "description": "Busca una orden específica por número de orden (OT-...), ID, código de siniestro, número de autorización o token de seguimiento",
        "parameters": {"busqueda": "string (número orden, ID, código siniestro, nº autorización o token)"},
        "category": "consulta"
    },
    "buscar_peticion": {
        "description": "Busca una petición por número (PET-...), nombre, teléfono o email",
        "parameters": {"busqueda": "string"},
        "category": "consulta"
    },
    "buscar_cliente": {
        "description": "Busca clientes por nombre, email, teléfono o DNI",
        "parameters": {"query": "string"},
        "category": "consulta"
    },
    "obtener_historial_cliente": {
        "description": "Obtiene el historial completo de un cliente: todas sus órdenes, peticiones e incidencias",
        "parameters": {"cliente_id": "string (ID o búsqueda)"},
        "category": "consulta"
    },
    "obtener_estadisticas": {
        "description": "Obtiene estadísticas y métricas del periodo especificado: conversiones, tiempos, volúmenes",
        "parameters": {"periodo": "hoy|semana|mes|trimestre"},
        "category": "consulta"
    },
    "detectar_alertas_sla": {
        "description": "Detecta elementos fuera de SLA: peticiones sin llamar >2h, órdenes en validación >24h, órdenes bloqueadas",
        "parameters": {},
        "category": "consulta"
    },
    "obtener_stock_bajo": {
        "description": "Lista repuestos con stock por debajo del mínimo",
        "parameters": {},
        "category": "consulta"
    },
    "listar_incidencias_abiertas": {
        "description": "Lista incidencias abiertas o en proceso",
        "parameters": {},
        "category": "consulta"
    },
    "obtener_ordenes_compra_pendientes": {
        "description": "Lista órdenes de compra pendientes o aprobadas sin recibir",
        "parameters": {},
        "category": "consulta"
    },
    
    # ===== ACCIONES EJECUTABLES =====
    "actualizar_estado_orden": {
        "description": "Cambia el estado de una orden de trabajo. Estados: pendiente_recibir, recibida, cuarentena, en_taller, reparado, validacion, enviado, cancelado",
        "parameters": {"orden_id": "string (número o ID)", "nuevo_estado": "string", "notas": "string (opcional)"},
        "category": "accion"
    },
    "marcar_peticion_contactada": {
        "description": "Marca una petición como contactada después de llamar al cliente",
        "parameters": {"peticion_id": "string (número o ID)", "resultado": "exito|no_contesta|llamar_luego|rechazado", "notas": "string (opcional)"},
        "category": "accion"
    },
    "agregar_nota_orden": {
        "description": "Agrega una nota o comentario interno a una orden",
        "parameters": {"orden_id": "string", "nota": "string"},
        "category": "accion"
    },
    "crear_notificacion": {
        "description": "Crea una notificación/alerta interna para el equipo",
        "parameters": {"mensaje": "string", "tipo": "info|warning|urgente", "orden_id": "string (opcional)"},
        "category": "accion"
    },
    "asignar_tecnico": {
        "description": "Asigna un técnico a una orden de trabajo",
        "parameters": {"orden_id": "string", "tecnico_id": "string (ID o nombre del técnico)"},
        "category": "accion"
    },
    
    # ===== REPORTES Y ANÁLISIS =====
    "generar_reporte_diario": {
        "description": "Genera un reporte detallado del día: entradas, salidas, conversiones, tiempos",
        "parameters": {"fecha": "string (YYYY-MM-DD, opcional, default hoy)"},
        "category": "reporte"
    },
    "analizar_rendimiento_tecnicos": {
        "description": "Analiza el rendimiento de los técnicos: órdenes completadas, tiempos, calidad",
        "parameters": {"periodo": "semana|mes"},
        "category": "reporte"
    },
    "analizar_tendencias": {
        "description": "Analiza tendencias: tipos de dispositivos más frecuentes, averías comunes, etc.",
        "parameters": {},
        "category": "reporte"
    }
}

# ==================== IMPLEMENTACIÓN DE FUNCIONES ====================

async def fn_obtener_resumen_sistema():
    """Obtiene resumen completo del estado del sistema"""
    ahora = datetime.now(timezone.utc)
    inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Peticiones
    peticiones_total = await db.peticiones_exteriores.count_documents({})
    peticiones_pendientes = await db.peticiones_exteriores.count_documents({"estado": "pendiente"})
    peticiones_hoy = await db.peticiones_exteriores.count_documents({"created_at": {"$gte": inicio_dia.isoformat()}})
    
    # Órdenes por estado
    estados_ordenes = {}
    for estado in ["pendiente_recibir", "recibida", "cuarentena", "en_taller", "reparado", "validacion", "enviado"]:
        estados_ordenes[estado] = await db.ordenes.count_documents({"estado": estado})
    
    ordenes_total = await db.ordenes.count_documents({})
    ordenes_hoy = await db.ordenes.count_documents({"created_at": {"$gte": inicio_dia.isoformat()}})
    
    # Alertas SLA
    hace_2h = (ahora - timedelta(hours=2)).isoformat()
    hace_24h = (ahora - timedelta(hours=24)).isoformat()
    
    peticiones_sla = await db.peticiones_exteriores.count_documents({
        "estado": "pendiente",
        "created_at": {"$lt": hace_2h}
    })
    ordenes_sla = await db.ordenes.count_documents({
        "estado": "validacion",
        "updated_at": {"$lt": hace_24h}
    })
    
    # Stock bajo
    repuestos_bajo_stock = await db.repuestos.count_documents({
        "$expr": {"$lte": ["$stock", "$stock_minimo"]}
    })
    
    # Incidencias abiertas
    incidencias_abiertas = await db.incidencias.count_documents({
        "estado": {"$in": ["abierta", "en_proceso"]}
    })
    
    # Órdenes de compra pendientes
    oc_pendientes = await db.ordenes_compra.count_documents({
        "estado": {"$in": ["pendiente", "aprobada", "pedida"]}
    })
    
    return {
        "fecha_hora": ahora.strftime("%d/%m/%Y %H:%M"),
        "peticiones": {
            "total": peticiones_total,
            "pendientes_llamar": peticiones_pendientes,
            "nuevas_hoy": peticiones_hoy,
            "fuera_sla_2h": peticiones_sla
        },
        "ordenes": {
            "total": ordenes_total,
            "por_estado": estados_ordenes,
            "nuevas_hoy": ordenes_hoy,
            "en_validacion_fuera_sla": ordenes_sla
        },
        "alertas": {
            "total_alertas_sla": peticiones_sla + ordenes_sla,
            "repuestos_bajo_stock": repuestos_bajo_stock,
            "incidencias_abiertas": incidencias_abiertas,
            "ordenes_compra_pendientes": oc_pendientes
        }
    }

async def fn_listar_peticiones_pendientes():
    """Lista peticiones pendientes de llamar con detalle"""
    peticiones = await db.peticiones_exteriores.find(
        {"estado": "pendiente"},
        {"_id": 0}
    ).sort("created_at", 1).to_list(30)
    
    ahora = datetime.now(timezone.utc)
    for p in peticiones:
        created = datetime.fromisoformat(p.get("created_at", ahora.isoformat()).replace("Z", "+00:00"))
        espera = (ahora - created).total_seconds() / 3600
        p["horas_espera"] = round(espera, 1)
        p["urgente"] = espera > 2
        p["estado_sla"] = "🔴 CRÍTICO" if espera > 2 else "🟡 Normal" if espera > 1 else "🟢 OK"
    
    urgentes = [p for p in peticiones if p.get("urgente")]
    
    return {
        "peticiones": peticiones,
        "total": len(peticiones),
        "urgentes_fuera_sla": len(urgentes),
        "mensaje": f"Hay {len(urgentes)} peticiones URGENTES fuera de SLA (>2h)" if urgentes else "Todas las peticiones están dentro de SLA"
    }

async def fn_listar_ordenes_validacion():
    """Lista órdenes en estado validación"""
    ordenes = await db.ordenes.find(
        {"estado": "validacion"},
        {"_id": 0, "id": 1, "numero_orden": 1, "dispositivo": 1, "tecnico_asignado": 1, "updated_at": 1, "presupuesto_precio": 1}
    ).sort("updated_at", 1).to_list(30)
    
    ahora = datetime.now(timezone.utc)
    for o in ordenes:
        updated = datetime.fromisoformat(o.get("updated_at", ahora.isoformat()).replace("Z", "+00:00"))
        espera = (ahora - updated).total_seconds() / 3600
        o["horas_en_validacion"] = round(espera, 1)
        o["urgente"] = espera > 24
        o["estado_sla"] = "🔴 CRÍTICO" if espera > 24 else "🟡 Atención" if espera > 12 else "🟢 OK"
    
    return {"ordenes": ordenes, "total": len(ordenes)}

async def fn_listar_ordenes_por_estado(estados: str, limite: int = 20):
    """Lista órdenes por estados específicos"""
    lista_estados = [e.strip() for e in estados.split(",")]
    ordenes = await db.ordenes.find(
        {"estado": {"$in": lista_estados}},
        {"_id": 0, "id": 1, "numero_orden": 1, "estado": 1, "dispositivo": 1, "tecnico_asignado": 1, "created_at": 1, "updated_at": 1}
    ).sort("updated_at", -1).limit(limite).to_list(limite)
    
    return {"ordenes": ordenes, "total": len(ordenes), "estados_filtrados": lista_estados}

async def fn_buscar_orden(busqueda: str):
    """Busca una orden por número, ID, código siniestro o número de autorización"""
    busqueda_upper = busqueda.upper().strip()
    busqueda_clean = busqueda.strip()
    orden = await db.ordenes.find_one(
        {"$or": [
            {"numero_orden": {"$regex": busqueda_upper, "$options": "i"}},
            {"id": busqueda_clean},
            {"codigo_siniestro": {"$regex": busqueda_clean, "$options": "i"}},
            {"numero_autorizacion": {"$regex": busqueda_clean, "$options": "i"}},
            {"token_seguimiento": {"$regex": busqueda_upper, "$options": "i"}}
        ]},
        {"_id": 0}
    )
    if not orden:
        return {"error": f"No se encontró ninguna orden con '{busqueda}'", "sugerencia": "Intenta con el número de orden (OT-XXXXXXXX), código de siniestro, número de autorización o token de seguimiento"}
    
    # Limpiar ObjectIds
    orden = clean_mongo_doc(orden)
    
    # Obtener info del cliente
    cliente = await db.clientes.find_one({"id": orden.get("cliente_id")}, {"_id": 0, "nombre": 1, "telefono": 1, "email": 1})
    orden["cliente_info"] = clean_mongo_doc(cliente)
    
    # Obtener info del técnico si está asignado
    if orden.get("tecnico_asignado"):
        tecnico = await db.users.find_one({"id": orden["tecnico_asignado"]}, {"_id": 0, "nombre": 1, "email": 1})
        orden["tecnico_info"] = clean_mongo_doc(tecnico)
    
    return {"orden": orden}

async def fn_buscar_peticion(busqueda: str):
    """Busca una petición por número, nombre, teléfono o email"""
    regex = {"$regex": busqueda, "$options": "i"}
    peticion = await db.peticiones_exteriores.find_one(
        {"$or": [
            {"numero": regex},
            {"nombre": regex},
            {"telefono": {"$regex": busqueda}},
            {"email": regex}
        ]},
        {"_id": 0}
    )
    if not peticion:
        return {"error": f"No se encontró ninguna petición con '{busqueda}'"}
    return {"peticion": peticion}

async def fn_buscar_cliente(query: str):
    """Busca clientes por nombre, email, teléfono o DNI"""
    regex = {"$regex": query, "$options": "i"}
    clientes = await db.clientes.find(
        {"$or": [
            {"nombre": regex},
            {"apellidos": regex},
            {"email": regex},
            {"telefono": {"$regex": query}},
            {"dni": regex}
        ]},
        {"_id": 0}
    ).limit(10).to_list(10)
    return {"clientes": clientes, "total": len(clientes)}

async def fn_obtener_historial_cliente(cliente_id: str):
    """Obtiene historial completo de un cliente"""
    # Buscar cliente
    cliente = await db.clientes.find_one(
        {"$or": [{"id": cliente_id}, {"nombre": {"$regex": cliente_id, "$options": "i"}}]},
        {"_id": 0}
    )
    if not cliente:
        return {"error": f"Cliente no encontrado: {cliente_id}"}
    
    # Órdenes del cliente
    ordenes = await db.ordenes.find(
        {"cliente_id": cliente.get("id")},
        {"_id": 0, "id": 1, "numero_orden": 1, "estado": 1, "dispositivo": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(50)
    
    # Incidencias
    incidencias = await db.incidencias.find(
        {"cliente_id": cliente.get("id")},
        {"_id": 0}
    ).to_list(20)
    
    return {
        "cliente": cliente,
        "ordenes": ordenes,
        "total_ordenes": len(ordenes),
        "incidencias": incidencias,
        "total_incidencias": len(incidencias)
    }

async def fn_actualizar_estado_orden(orden_id: str, nuevo_estado: str, notas: str = None):
    """Actualiza el estado de una orden"""
    estados_validos = ["pendiente_recibir", "recibida", "cuarentena", "en_taller", "reparado", "validacion", "enviado", "cancelado", "garantia", "reemplazo", "irreparable"]
    nuevo_estado = nuevo_estado.lower().strip()
    
    if nuevo_estado not in estados_validos:
        return {"error": f"Estado no válido: {nuevo_estado}", "estados_validos": estados_validos}
    
    # Buscar orden
    orden = await db.ordenes.find_one(
        {"$or": [{"id": orden_id}, {"numero_orden": {"$regex": orden_id.upper()}}]},
        {"_id": 0, "id": 1, "numero_orden": 1, "estado": 1}
    )
    if not orden:
        return {"error": f"Orden no encontrada: {orden_id}"}
    
    estado_anterior = orden.get("estado")
    ahora = datetime.now(timezone.utc).isoformat()
    
    # Actualizar
    result = await db.ordenes.update_one(
        {"id": orden.get("id")},
        {
            "$set": {"estado": nuevo_estado, "updated_at": ahora},
            "$push": {
                "historial_estados": {
                    "estado": nuevo_estado,
                    "estado_anterior": estado_anterior,
                    "fecha": ahora,
                    "usuario": "agente_aria",
                    "notas": notas or "Cambio de estado por Agente ARIA"
                }
            }
        }
    )
    
    if result.modified_count == 0:
        return {"error": "No se pudo actualizar la orden"}
    
    return {
        "success": True,
        "mensaje": f"✅ Orden {orden.get('numero_orden')} actualizada: {estado_anterior} → {nuevo_estado}",
        "orden_id": orden.get("id"),
        "numero_orden": orden.get("numero_orden")
    }

async def fn_marcar_peticion_contactada(peticion_id: str, resultado: str, notas: str = None):
    """Marca una petición como contactada"""
    resultados_validos = ["exito", "no_contesta", "llamar_luego", "rechazado"]
    resultado = resultado.lower().strip()
    
    if resultado not in resultados_validos:
        return {"error": f"Resultado no válido: {resultado}", "opciones": resultados_validos}
    
    nuevo_estado = "contactado"
    if resultado == "rechazado":
        nuevo_estado = "rechazado"
    elif resultado == "exito":
        nuevo_estado = "presupuestado"
    
    ahora = datetime.now(timezone.utc).isoformat()
    
    result = await db.peticiones_exteriores.update_one(
        {"$or": [{"id": peticion_id}, {"numero": {"$regex": peticion_id.upper()}}]},
        {"$set": {
            "estado": nuevo_estado,
            "fecha_llamada": ahora,
            "resultado_llamada": resultado,
            "notas_llamada": notas,
            "updated_at": ahora
        }}
    )
    
    if result.modified_count == 0:
        return {"error": f"Petición no encontrada: {peticion_id}"}
    
    return {
        "success": True,
        "mensaje": f"✅ Petición marcada como: {nuevo_estado} (resultado: {resultado})"
    }

async def fn_agregar_nota_orden(orden_id: str, nota: str):
    """Agrega una nota a una orden"""
    ahora = datetime.now(timezone.utc).isoformat()
    
    result = await db.ordenes.update_one(
        {"$or": [{"id": orden_id}, {"numero_orden": {"$regex": orden_id.upper()}}]},
        {
            "$push": {
                "mensajes": {
                    "id": str(uuid.uuid4()),
                    "autor": "agente_aria",
                    "autor_nombre": "ARIA",
                    "rol": "sistema",
                    "mensaje": nota,
                    "fecha": ahora
                }
            },
            "$set": {"updated_at": ahora}
        }
    )
    
    if result.modified_count == 0:
        return {"error": f"Orden no encontrada: {orden_id}"}
    
    return {"success": True, "mensaje": "✅ Nota agregada a la orden"}

async def fn_crear_notificacion(mensaje: str, tipo: str = "info", orden_id: str = None):
    """Crea una notificación interna"""
    import uuid
    ahora = datetime.now(timezone.utc).isoformat()
    
    notif = {
        "id": str(uuid.uuid4()),
        "tipo": tipo,
        "mensaje": mensaje,
        "orden_id": orden_id,
        "leida": False,
        "created_at": ahora
    }
    
    await db.notificaciones.insert_one(notif)
    return {"success": True, "mensaje": "✅ Notificación creada", "notificacion_id": notif["id"]}

async def fn_asignar_tecnico(orden_id: str, tecnico_id: str):
    """Asigna un técnico a una orden"""
    # Buscar técnico
    tecnico = await db.users.find_one(
        {"$or": [{"id": tecnico_id}, {"nombre": {"$regex": tecnico_id, "$options": "i"}}], "role": "tecnico"},
        {"_id": 0, "id": 1, "nombre": 1}
    )
    if not tecnico:
        # Listar técnicos disponibles
        tecnicos = await db.users.find({"role": "tecnico", "activo": True}, {"_id": 0, "id": 1, "nombre": 1}).to_list(20)
        return {"error": f"Técnico no encontrado: {tecnico_id}", "tecnicos_disponibles": tecnicos}
    
    ahora = datetime.now(timezone.utc).isoformat()
    
    result = await db.ordenes.update_one(
        {"$or": [{"id": orden_id}, {"numero_orden": {"$regex": orden_id.upper()}}]},
        {"$set": {"tecnico_asignado": tecnico.get("id"), "updated_at": ahora}}
    )
    
    if result.modified_count == 0:
        return {"error": f"Orden no encontrada: {orden_id}"}
    
    return {"success": True, "mensaje": f"✅ Técnico {tecnico.get('nombre')} asignado a la orden"}

async def fn_detectar_alertas_sla():
    """Detecta todos los elementos fuera de SLA"""
    ahora = datetime.now(timezone.utc)
    hace_2h = (ahora - timedelta(hours=2)).isoformat()
    hace_24h = (ahora - timedelta(hours=24)).isoformat()
    
    alertas = []
    
    # Peticiones sin llamar > 2h
    peticiones_urgentes = await db.peticiones_exteriores.find(
        {"estado": "pendiente", "created_at": {"$lt": hace_2h}},
        {"_id": 0, "numero": 1, "nombre": 1, "telefono": 1, "created_at": 1, "dispositivo": 1}
    ).to_list(50)
    
    for p in peticiones_urgentes:
        created = datetime.fromisoformat(p["created_at"].replace("Z", "+00:00"))
        horas = round((ahora - created).total_seconds() / 3600, 1)
        alertas.append({
            "tipo": "peticion_sin_llamar",
            "prioridad": "critica",
            "icono": "🔴",
            "mensaje": f"Petición {p['numero']} lleva {horas}h sin llamar",
            "detalle": f"{p['nombre']} - {p.get('telefono', 'Sin tel')} - {p.get('dispositivo', '')}",
            "accion_sugerida": f"Llamar inmediatamente al {p.get('telefono', '')}"
        })
    
    # Órdenes en validación > 24h
    ordenes_validacion = await db.ordenes.find(
        {"estado": "validacion", "updated_at": {"$lt": hace_24h}},
        {"_id": 0, "numero_orden": 1, "dispositivo": 1, "updated_at": 1}
    ).to_list(50)
    
    for o in ordenes_validacion:
        updated = datetime.fromisoformat(o["updated_at"].replace("Z", "+00:00"))
        horas = round((ahora - updated).total_seconds() / 3600, 1)
        alertas.append({
            "tipo": "orden_validacion_pendiente",
            "prioridad": "alta",
            "icono": "🟠",
            "mensaje": f"Orden {o['numero_orden']} lleva {horas}h en validación",
            "detalle": f"Dispositivo: {o.get('dispositivo', {}).get('modelo', 'N/A')}",
            "accion_sugerida": "Revisar y aprobar la orden"
        })
    
    # Órdenes bloqueadas
    ordenes_bloqueadas = await db.ordenes.find(
        {"bloqueada": True, "estado": {"$nin": ["enviado", "cancelado"]}},
        {"_id": 0, "numero_orden": 1, "dispositivo": 1}
    ).to_list(20)
    
    for o in ordenes_bloqueadas:
        alertas.append({
            "tipo": "orden_bloqueada",
            "prioridad": "media",
            "icono": "🟡",
            "mensaje": f"Orden {o['numero_orden']} está BLOQUEADA",
            "detalle": f"Dispositivo: {o.get('dispositivo', {}).get('modelo', 'N/A')}",
            "accion_sugerida": "Revisar motivo del bloqueo"
        })
    
    return {"alertas": alertas, "total": len(alertas), "criticas": len([a for a in alertas if a["prioridad"] == "critica"])}

async def fn_obtener_stock_bajo():
    """Lista repuestos con stock bajo"""
    repuestos = await db.repuestos.find(
        {"$expr": {"$lte": ["$stock", "$stock_minimo"]}},
        {"_id": 0, "id": 1, "nombre": 1, "stock": 1, "stock_minimo": 1, "proveedor": 1}
    ).to_list(50)
    
    criticos = [r for r in repuestos if r.get("stock", 0) == 0]
    
    return {
        "repuestos": repuestos,
        "total": len(repuestos),
        "criticos_sin_stock": len(criticos),
        "mensaje": f"⚠️ {len(criticos)} repuestos con stock CERO" if criticos else "Stock controlado"
    }

async def fn_listar_incidencias_abiertas():
    """Lista incidencias abiertas"""
    incidencias = await db.incidencias.find(
        {"estado": {"$in": ["abierta", "en_proceso"]}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(30)
    
    return {"incidencias": incidencias, "total": len(incidencias)}

async def fn_obtener_ordenes_compra_pendientes():
    """Lista órdenes de compra pendientes"""
    ocs = await db.ordenes_compra.find(
        {"estado": {"$in": ["pendiente", "aprobada", "pedida"]}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(30)
    
    return {"ordenes_compra": ocs, "total": len(ocs)}

async def fn_obtener_estadisticas(periodo: str = "hoy"):
    """Obtiene estadísticas del periodo"""
    ahora = datetime.now(timezone.utc)
    
    if periodo == "hoy":
        desde = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "semana":
        desde = ahora - timedelta(days=7)
    elif periodo == "trimestre":
        desde = ahora - timedelta(days=90)
    else:  # mes
        desde = ahora - timedelta(days=30)
    
    desde_str = desde.isoformat()
    
    # Peticiones
    peticiones_creadas = await db.peticiones_exteriores.count_documents({"created_at": {"$gte": desde_str}})
    peticiones_convertidas = await db.peticiones_exteriores.count_documents({
        "created_at": {"$gte": desde_str},
        "estado": "convertido"
    })
    peticiones_rechazadas = await db.peticiones_exteriores.count_documents({
        "created_at": {"$gte": desde_str},
        "estado": "rechazado"
    })
    
    # Órdenes
    ordenes_creadas = await db.ordenes.count_documents({"created_at": {"$gte": desde_str}})
    ordenes_enviadas = await db.ordenes.count_documents({
        "estado": "enviado",
        "updated_at": {"$gte": desde_str}
    })
    ordenes_canceladas = await db.ordenes.count_documents({
        "estado": "cancelado",
        "updated_at": {"$gte": desde_str}
    })
    
    tasa_conversion = round(peticiones_convertidas / peticiones_creadas * 100, 1) if peticiones_creadas > 0 else 0
    tasa_entrega = round(ordenes_enviadas / ordenes_creadas * 100, 1) if ordenes_creadas > 0 else 0
    
    return {
        "periodo": periodo,
        "rango": f"{desde.strftime('%d/%m/%Y')} - {ahora.strftime('%d/%m/%Y')}",
        "peticiones": {
            "creadas": peticiones_creadas,
            "convertidas": peticiones_convertidas,
            "rechazadas": peticiones_rechazadas,
            "tasa_conversion": f"{tasa_conversion}%"
        },
        "ordenes": {
            "creadas": ordenes_creadas,
            "enviadas": ordenes_enviadas,
            "canceladas": ordenes_canceladas,
            "tasa_entrega": f"{tasa_entrega}%"
        }
    }

async def fn_generar_reporte_diario(fecha: str = None):
    """Genera reporte detallado del día"""
    if fecha:
        try:
            dia = datetime.fromisoformat(fecha)
        except:
            dia = datetime.now(timezone.utc)
    else:
        dia = datetime.now(timezone.utc)
    
    inicio_dia = dia.replace(hour=0, minute=0, second=0, microsecond=0)
    fin_dia = dia.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    inicio_str = inicio_dia.isoformat()
    fin_str = fin_dia.isoformat()
    
    # Métricas del día
    peticiones_nuevas = await db.peticiones_exteriores.count_documents({"created_at": {"$gte": inicio_str, "$lte": fin_str}})
    peticiones_llamadas = await db.peticiones_exteriores.count_documents({
        "fecha_llamada": {"$gte": inicio_str, "$lte": fin_str}
    })
    
    ordenes_nuevas = await db.ordenes.count_documents({"created_at": {"$gte": inicio_str, "$lte": fin_str}})
    ordenes_enviadas = await db.ordenes.count_documents({
        "estado": "enviado",
        "fecha_enviado": {"$gte": inicio_str, "$lte": fin_str}
    })
    
    return {
        "fecha": dia.strftime("%d/%m/%Y"),
        "peticiones": {
            "nuevas": peticiones_nuevas,
            "llamadas": peticiones_llamadas
        },
        "ordenes": {
            "nuevas": ordenes_nuevas,
            "enviadas": ordenes_enviadas
        }
    }

async def fn_analizar_rendimiento_tecnicos(periodo: str = "semana"):
    """Analiza rendimiento de técnicos"""
    ahora = datetime.now(timezone.utc)
    desde = ahora - timedelta(days=7 if periodo == "semana" else 30)
    desde_str = desde.isoformat()
    
    tecnicos = await db.users.find({"role": "tecnico", "activo": True}, {"_id": 0, "id": 1, "nombre": 1}).to_list(50)
    
    resultados = []
    for t in tecnicos:
        ordenes_asignadas = await db.ordenes.count_documents({
            "tecnico_asignado": t["id"],
            "created_at": {"$gte": desde_str}
        })
        ordenes_completadas = await db.ordenes.count_documents({
            "tecnico_asignado": t["id"],
            "estado": "enviado",
            "updated_at": {"$gte": desde_str}
        })
        
        resultados.append({
            "tecnico": t["nombre"],
            "ordenes_asignadas": ordenes_asignadas,
            "ordenes_completadas": ordenes_completadas,
            "tasa_completado": f"{round(ordenes_completadas/ordenes_asignadas*100, 1)}%" if ordenes_asignadas > 0 else "N/A"
        })
    
    return {"periodo": periodo, "tecnicos": resultados}

async def fn_analizar_tendencias():
    """Analiza tendencias del sistema"""
    # Últimos 30 días
    ahora = datetime.now(timezone.utc)
    desde = (ahora - timedelta(days=30)).isoformat()
    
    ordenes = await db.ordenes.find(
        {"created_at": {"$gte": desde}},
        {"_id": 0, "dispositivo": 1, "estado": 1}
    ).to_list(1000)
    
    # Contar modelos
    modelos = {}
    for o in ordenes:
        modelo = o.get("dispositivo", {}).get("modelo", "Desconocido")
        modelos[modelo] = modelos.get(modelo, 0) + 1
    
    top_modelos = sorted(modelos.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "periodo": "últimos 30 días",
        "total_ordenes": len(ordenes),
        "dispositivos_mas_frecuentes": [{"modelo": m[0], "cantidad": m[1]} for m in top_modelos]
    }

# ==================== MAPEO DE FUNCIONES ====================
import uuid

FUNCTION_MAP = {
    "obtener_resumen_sistema": fn_obtener_resumen_sistema,
    "obtener_resumen_diario": fn_obtener_resumen_sistema,  # Alias
    "listar_peticiones_pendientes": fn_listar_peticiones_pendientes,
    "listar_ordenes_validacion": fn_listar_ordenes_validacion,
    "listar_ordenes_por_estado": fn_listar_ordenes_por_estado,
    "buscar_orden": fn_buscar_orden,
    "buscar_peticion": fn_buscar_peticion,
    "buscar_cliente": fn_buscar_cliente,
    "obtener_historial_cliente": fn_obtener_historial_cliente,
    "actualizar_estado_orden": fn_actualizar_estado_orden,
    "marcar_peticion_contactada": fn_marcar_peticion_contactada,
    "agregar_nota_orden": fn_agregar_nota_orden,
    "crear_notificacion": fn_crear_notificacion,
    "asignar_tecnico": fn_asignar_tecnico,
    "detectar_alertas_sla": fn_detectar_alertas_sla,
    "obtener_stock_bajo": fn_obtener_stock_bajo,
    "listar_incidencias_abiertas": fn_listar_incidencias_abiertas,
    "obtener_ordenes_compra_pendientes": fn_obtener_ordenes_compra_pendientes,
    "obtener_estadisticas": fn_obtener_estadisticas,
    "generar_reporte_diario": fn_generar_reporte_diario,
    "analizar_rendimiento_tecnicos": fn_analizar_rendimiento_tecnicos,
    "analizar_tendencias": fn_analizar_tendencias,
}

async def execute_function(function_name: str, parameters: dict = None) -> dict:
    """Ejecuta una función del agente"""
    if function_name not in FUNCTION_MAP:
        return {"error": f"Función no encontrada: {function_name}"}
    
    try:
        func = FUNCTION_MAP[function_name]
        if parameters:
            result = await func(**parameters)
        else:
            result = await func()
        return result
    except Exception as e:
        logger.error(f"Error ejecutando función {function_name}: {e}")
        return {"error": str(e)}

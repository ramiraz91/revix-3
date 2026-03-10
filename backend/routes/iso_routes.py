"""
Módulo ISO/WISE - Rutas de API
- QA Muestreo (AQL)
- Evaluación de Proveedores
- Control Documental
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel
from bson import ObjectId
import uuid
import math
import random

from config import db
from auth import require_auth, require_admin, require_master

router = APIRouter(tags=["ISO/WISE"])

# ==================== MODELOS ====================

class QAMuestreoCreate(BaseModel):
    """Crear un muestreo QA"""
    lote_fecha_inicio: str
    lote_fecha_fin: str
    nivel_inspeccion: str = "normal"  # reducida, normal, estricta
    criterio_aql: float = 2.5  # Acceptable Quality Level

class QAMuestreoResultado(BaseModel):
    """Resultado de inspección de una orden"""
    orden_id: str
    resultado: str  # aprobado, rechazado, observaciones
    hallazgos: Optional[str] = None
    accion_correctiva: Optional[str] = None

class ProveedorEvaluacion(BaseModel):
    """Evaluación de proveedor"""
    proveedor_id: str
    periodo: str  # "2026-Q1", "2026-H1", "2026"
    calidad_puntuacion: int  # 0-100
    entrega_puntuacion: int  # 0-100
    precio_puntuacion: int  # 0-100
    servicio_puntuacion: int  # 0-100
    observaciones: Optional[str] = None
    no_conformidades: int = 0
    entregas_tardias: int = 0
    total_pedidos: int = 0

class DocumentoISO(BaseModel):
    """Documento del Sistema de Gestión de Calidad"""
    codigo: str  # "PRO-001", "INS-002"
    titulo: str
    tipo: str  # procedimiento, instruccion, formato, registro, politica
    version: str = "1.0"
    contenido: Optional[str] = None
    archivo_url: Optional[str] = None
    responsable: str
    fecha_vigencia: str
    fecha_revision: Optional[str] = None
    requiere_acuse: bool = False

class AcuseLectura(BaseModel):
    """Acuse de lectura de documento"""
    documento_id: str


# ==================== QA MUESTREO (AQL) ====================

def calcular_tamano_muestra(tamano_lote: int, nivel: str = "normal", aql: float = 2.5) -> dict:
    """
    Calcula el tamaño de muestra según tabla AQL simplificada (MIL-STD-105E)
    """
    # Tabla simplificada de tamaños de muestra
    tabla_muestra = {
        "reducida": {
            (2, 8): 2, (9, 15): 2, (16, 25): 3, (26, 50): 5,
            (51, 90): 5, (91, 150): 8, (151, 280): 13, (281, 500): 20,
            (501, 1200): 32, (1201, 3200): 50
        },
        "normal": {
            (2, 8): 2, (9, 15): 3, (16, 25): 5, (26, 50): 8,
            (51, 90): 13, (91, 150): 20, (151, 280): 32, (281, 500): 50,
            (501, 1200): 80, (1201, 3200): 125
        },
        "estricta": {
            (2, 8): 3, (9, 15): 5, (16, 25): 8, (26, 50): 13,
            (51, 90): 20, (91, 150): 32, (151, 280): 50, (281, 500): 80,
            (501, 1200): 125, (1201, 3200): 200
        }
    }
    
    # Número de aceptación según AQL 2.5%
    tabla_aceptacion = {
        2: 0, 3: 0, 5: 0, 8: 0, 13: 1, 20: 1, 32: 2, 50: 3, 80: 5, 125: 7, 200: 10
    }
    
    tabla = tabla_muestra.get(nivel, tabla_muestra["normal"])
    
    tamano_muestra = 2  # default mínimo
    for (min_lote, max_lote), muestra in tabla.items():
        if min_lote <= tamano_lote <= max_lote:
            tamano_muestra = muestra
            break
    
    # Si el lote es mayor que la tabla
    if tamano_lote > 3200:
        tamano_muestra = 200 if nivel == "estricta" else 125
    
    aceptacion = tabla_aceptacion.get(tamano_muestra, 0)
    
    return {
        "tamano_lote": tamano_lote,
        "tamano_muestra": tamano_muestra,
        "numero_aceptacion": aceptacion,
        "numero_rechazo": aceptacion + 1,
        "nivel_inspeccion": nivel,
        "aql": aql
    }


@router.post("/iso/qa/muestreo")
async def crear_muestreo_qa(data: QAMuestreoCreate, user: dict = Depends(require_admin)):
    """
    Crear un nuevo plan de muestreo QA para un período.
    Selecciona automáticamente las órdenes a inspeccionar.
    """
    # Buscar órdenes completadas (reparado/validacion/enviado) en el período
    query = {
        "estado": {"$in": ["reparado", "validacion", "enviado"]},
        "updated_at": {
            "$gte": data.lote_fecha_inicio,
            "$lte": data.lote_fecha_fin
        }
    }
    
    ordenes = await db.ordenes.find(query, {"id": 1, "numero_orden": 1, "estado": 1}).to_list(5000)
    tamano_lote = len(ordenes)
    
    if tamano_lote == 0:
        raise HTTPException(400, "No hay órdenes en el período especificado")
    
    # Calcular tamaño de muestra
    params_muestreo = calcular_tamano_muestra(tamano_lote, data.nivel_inspeccion, data.criterio_aql)
    
    # Seleccionar órdenes aleatorias para inspección
    ordenes_seleccionadas = random.sample(ordenes, min(params_muestreo["tamano_muestra"], len(ordenes)))
    
    muestreo = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.get("email"),
        "lote_fecha_inicio": data.lote_fecha_inicio,
        "lote_fecha_fin": data.lote_fecha_fin,
        "tamano_lote": tamano_lote,
        "tamano_muestra": params_muestreo["tamano_muestra"],
        "nivel_inspeccion": data.nivel_inspeccion,
        "criterio_aql": data.criterio_aql,
        "numero_aceptacion": params_muestreo["numero_aceptacion"],
        "numero_rechazo": params_muestreo["numero_rechazo"],
        "ordenes_seleccionadas": [{"id": o["id"], "numero_orden": o["numero_orden"]} for o in ordenes_seleccionadas],
        "estado": "pendiente",  # pendiente, en_progreso, completado, rechazado
        "resultados": [],
        "aprobados": 0,
        "rechazados": 0,
        "resultado_final": None
    }
    
    await db.qa_muestreo.insert_one(muestreo)
    del muestreo["_id"]
    
    return {
        "message": f"Muestreo creado: {params_muestreo['tamano_muestra']} órdenes de {tamano_lote} (AQL {data.criterio_aql}%)",
        "muestreo": muestreo
    }


@router.get("/iso/qa/muestreos")
async def listar_muestreos_qa(
    estado: Optional[str] = None,
    limit: int = 20,
    user: dict = Depends(require_auth)
):
    """Listar planes de muestreo QA"""
    query = {}
    if estado:
        query["estado"] = estado
    
    muestreos = await db.qa_muestreo.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return muestreos


@router.get("/iso/qa/muestreo/{muestreo_id}")
async def obtener_muestreo_qa(muestreo_id: str, user: dict = Depends(require_auth)):
    """Obtener detalle de un muestreo QA"""
    muestreo = await db.qa_muestreo.find_one({"id": muestreo_id}, {"_id": 0})
    if not muestreo:
        raise HTTPException(404, "Muestreo no encontrado")
    return muestreo


@router.post("/iso/qa/muestreo/{muestreo_id}/resultado")
async def registrar_resultado_inspeccion(
    muestreo_id: str,
    data: QAMuestreoResultado,
    user: dict = Depends(require_admin)
):
    """
    Registrar el resultado de inspección de una orden dentro del muestreo.
    Actualiza automáticamente el estado del muestreo según AQL.
    """
    muestreo = await db.qa_muestreo.find_one({"id": muestreo_id})
    if not muestreo:
        raise HTTPException(404, "Muestreo no encontrado")
    
    if muestreo["estado"] == "completado":
        raise HTTPException(400, "El muestreo ya está completado")
    
    # Verificar que la orden está en la selección
    orden_en_muestra = any(o["id"] == data.orden_id for o in muestreo["ordenes_seleccionadas"])
    if not orden_en_muestra:
        raise HTTPException(400, "La orden no pertenece a este muestreo")
    
    # Registrar resultado
    resultado = {
        "orden_id": data.orden_id,
        "resultado": data.resultado,
        "hallazgos": data.hallazgos,
        "accion_correctiva": data.accion_correctiva,
        "inspector": user.get("email"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Actualizar contadores
    update = {
        "$push": {"resultados": resultado},
        "$set": {"estado": "en_progreso"}
    }
    
    if data.resultado == "aprobado":
        update["$inc"] = {"aprobados": 1}
    else:
        update["$inc"] = {"rechazados": 1}
    
    await db.qa_muestreo.update_one({"id": muestreo_id}, update)
    
    # Verificar si el muestreo está completo
    muestreo = await db.qa_muestreo.find_one({"id": muestreo_id})
    total_inspeccionados = muestreo["aprobados"] + muestreo["rechazados"]
    
    resultado_final = None
    if total_inspeccionados >= muestreo["tamano_muestra"]:
        # Evaluar según criterio AQL
        if muestreo["rechazados"] <= muestreo["numero_aceptacion"]:
            resultado_final = "LOTE_APROBADO"
        else:
            resultado_final = "LOTE_RECHAZADO"
        
        await db.qa_muestreo.update_one(
            {"id": muestreo_id},
            {"$set": {"estado": "completado", "resultado_final": resultado_final}}
        )
    
    return {
        "message": f"Resultado registrado: {data.resultado}",
        "inspeccionados": total_inspeccionados,
        "tamano_muestra": muestreo["tamano_muestra"],
        "aprobados": muestreo["aprobados"] + (1 if data.resultado == "aprobado" else 0),
        "rechazados": muestreo["rechazados"] + (1 if data.resultado != "aprobado" else 0),
        "resultado_final": resultado_final
    }


# ==================== EVALUACIÓN DE PROVEEDORES ====================

@router.post("/iso/proveedores/evaluacion")
async def crear_evaluacion_proveedor(data: ProveedorEvaluacion, user: dict = Depends(require_admin)):
    """Crear o actualizar evaluación de proveedor"""
    
    # Verificar que el proveedor existe
    proveedor = await db.proveedores.find_one({"id": data.proveedor_id})
    if not proveedor:
        raise HTTPException(404, "Proveedor no encontrado")
    
    # Calcular puntuación global (promedio ponderado)
    puntuacion_global = round(
        (data.calidad_puntuacion * 0.40) +
        (data.entrega_puntuacion * 0.25) +
        (data.precio_puntuacion * 0.20) +
        (data.servicio_puntuacion * 0.15)
    )
    
    # Determinar clasificación
    if puntuacion_global >= 90:
        clasificacion = "A"  # Excelente
    elif puntuacion_global >= 75:
        clasificacion = "B"  # Bueno
    elif puntuacion_global >= 60:
        clasificacion = "C"  # Aceptable
    else:
        clasificacion = "D"  # Requiere mejora/bloqueo
    
    evaluacion = {
        "id": str(uuid.uuid4()),
        "proveedor_id": data.proveedor_id,
        "proveedor_nombre": proveedor.get("nombre"),
        "periodo": data.periodo,
        "calidad_puntuacion": data.calidad_puntuacion,
        "entrega_puntuacion": data.entrega_puntuacion,
        "precio_puntuacion": data.precio_puntuacion,
        "servicio_puntuacion": data.servicio_puntuacion,
        "puntuacion_global": puntuacion_global,
        "clasificacion": clasificacion,
        "observaciones": data.observaciones,
        "no_conformidades": data.no_conformidades,
        "entregas_tardias": data.entregas_tardias,
        "total_pedidos": data.total_pedidos,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.get("email"),
        "estado": "activa"
    }
    
    # Verificar si ya existe evaluación para este período
    existente = await db.iso_proveedores_evaluacion.find_one({
        "proveedor_id": data.proveedor_id,
        "periodo": data.periodo
    })
    
    if existente:
        await db.iso_proveedores_evaluacion.update_one(
            {"id": existente["id"]},
            {"$set": {**evaluacion, "id": existente["id"], "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        mensaje = "Evaluación actualizada"
    else:
        await db.iso_proveedores_evaluacion.insert_one(evaluacion)
        mensaje = "Evaluación creada"
    
    # Actualizar clasificación en el proveedor
    await db.proveedores.update_one(
        {"id": data.proveedor_id},
        {"$set": {
            "clasificacion_iso": clasificacion,
            "puntuacion_iso": puntuacion_global,
            "ultima_evaluacion": data.periodo
        }}
    )
    
    return {
        "message": f"{mensaje}: {proveedor.get('nombre')} - Clasificación {clasificacion} ({puntuacion_global}%)",
        "evaluacion": {k: v for k, v in evaluacion.items() if k != "_id"}
    }


@router.get("/iso/proveedores/evaluaciones")
async def listar_evaluaciones_proveedores(
    proveedor_id: Optional[str] = None,
    periodo: Optional[str] = None,
    clasificacion: Optional[str] = None,
    user: dict = Depends(require_auth)
):
    """Listar evaluaciones de proveedores"""
    query = {}
    if proveedor_id:
        query["proveedor_id"] = proveedor_id
    if periodo:
        query["periodo"] = periodo
    if clasificacion:
        query["clasificacion"] = clasificacion
    
    evaluaciones = await db.iso_proveedores_evaluacion.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return evaluaciones


@router.get("/iso/proveedores/ranking")
async def ranking_proveedores(user: dict = Depends(require_auth)):
    """Obtener ranking de proveedores por puntuación"""
    # Agregación para obtener última evaluación de cada proveedor
    pipeline = [
        {"$sort": {"created_at": -1}},
        {"$group": {
            "_id": "$proveedor_id",
            "proveedor_nombre": {"$first": "$proveedor_nombre"},
            "periodo": {"$first": "$periodo"},
            "puntuacion_global": {"$first": "$puntuacion_global"},
            "clasificacion": {"$first": "$clasificacion"},
            "no_conformidades": {"$first": "$no_conformidades"}
        }},
        {"$sort": {"puntuacion_global": -1}},
        {"$project": {"_id": 0, "proveedor_id": "$_id", "proveedor_nombre": 1, 
                      "periodo": 1, "puntuacion_global": 1, "clasificacion": 1, "no_conformidades": 1}}
    ]
    
    ranking = await db.iso_proveedores_evaluacion.aggregate(pipeline).to_list(50)
    return ranking


# ==================== CONTROL DOCUMENTAL ====================

@router.post("/iso/documentos")
async def crear_documento(data: DocumentoISO, user: dict = Depends(require_admin)):
    """Crear un nuevo documento ISO"""
    
    # Verificar código único
    existente = await db.iso_documentos.find_one({"codigo": data.codigo})
    if existente:
        raise HTTPException(400, f"Ya existe un documento con código {data.codigo}")
    
    documento = {
        "id": str(uuid.uuid4()),
        "codigo": data.codigo,
        "titulo": data.titulo,
        "tipo": data.tipo,
        "version": data.version,
        "contenido": data.contenido,
        "archivo_url": data.archivo_url,
        "responsable": data.responsable,
        "fecha_vigencia": data.fecha_vigencia,
        "fecha_revision": data.fecha_revision,
        "requiere_acuse": data.requiere_acuse,
        "estado": "vigente",  # vigente, obsoleto, en_revision
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.get("email"),
        "historial_versiones": [{
            "version": data.version,
            "fecha": datetime.now(timezone.utc).isoformat(),
            "autor": user.get("email"),
            "cambios": "Versión inicial"
        }],
        "acuses_lectura": []
    }
    
    await db.iso_documentos.insert_one(documento)
    del documento["_id"]
    
    return {"message": f"Documento {data.codigo} creado", "documento": documento}


@router.get("/iso/documentos")
async def listar_documentos(
    tipo: Optional[str] = None,
    estado: str = "vigente",
    user: dict = Depends(require_auth)
):
    """Listar documentos ISO"""
    query = {"estado": estado}
    if tipo:
        query["tipo"] = tipo
    
    documentos = await db.iso_documentos.find(query, {"_id": 0, "contenido": 0}).sort("codigo", 1).to_list(200)
    return documentos


@router.get("/iso/documentos/{documento_id}")
async def obtener_documento(documento_id: str, user: dict = Depends(require_auth)):
    """Obtener detalle de un documento"""
    documento = await db.iso_documentos.find_one({"id": documento_id}, {"_id": 0})
    if not documento:
        raise HTTPException(404, "Documento no encontrado")
    return documento


@router.put("/iso/documentos/{documento_id}")
async def actualizar_documento(documento_id: str, data: DocumentoISO, user: dict = Depends(require_admin)):
    """Actualizar documento (crea nueva versión)"""
    documento = await db.iso_documentos.find_one({"id": documento_id})
    if not documento:
        raise HTTPException(404, "Documento no encontrado")
    
    # Incrementar versión
    version_actual = documento.get("version", "1.0")
    partes = version_actual.split(".")
    nueva_version = f"{partes[0]}.{int(partes[1]) + 1}"
    
    # Añadir al historial
    historial = documento.get("historial_versiones", [])
    historial.append({
        "version": nueva_version,
        "fecha": datetime.now(timezone.utc).isoformat(),
        "autor": user.get("email"),
        "cambios": f"Actualización de versión {version_actual} a {nueva_version}"
    })
    
    update = {
        "titulo": data.titulo,
        "contenido": data.contenido,
        "archivo_url": data.archivo_url,
        "responsable": data.responsable,
        "fecha_vigencia": data.fecha_vigencia,
        "fecha_revision": data.fecha_revision,
        "requiere_acuse": data.requiere_acuse,
        "version": nueva_version,
        "historial_versiones": historial,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": user.get("email"),
        "acuses_lectura": []  # Reset acuses para nueva versión
    }
    
    await db.iso_documentos.update_one({"id": documento_id}, {"$set": update})
    
    return {"message": f"Documento actualizado a versión {nueva_version}"}


@router.post("/iso/documentos/{documento_id}/acuse")
async def registrar_acuse_lectura(documento_id: str, user: dict = Depends(require_auth)):
    """Registrar acuse de lectura de un documento"""
    documento = await db.iso_documentos.find_one({"id": documento_id})
    if not documento:
        raise HTTPException(404, "Documento no encontrado")
    
    # Verificar si ya tiene acuse
    acuses = documento.get("acuses_lectura", [])
    ya_firmado = any(a["usuario"] == user.get("email") for a in acuses)
    
    if ya_firmado:
        return {"message": "Ya has confirmado la lectura de este documento"}
    
    acuse = {
        "usuario": user.get("email"),
        "nombre": f"{user.get('nombre', '')} {user.get('apellidos', '')}".strip() or user.get("email"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.iso_documentos.update_one(
        {"id": documento_id},
        {"$push": {"acuses_lectura": acuse}}
    )
    
    return {"message": "Acuse de lectura registrado"}


@router.get("/iso/documentos/{documento_id}/acuses")
async def listar_acuses_documento(documento_id: str, user: dict = Depends(require_admin)):
    """Listar acuses de lectura de un documento"""
    documento = await db.iso_documentos.find_one({"id": documento_id}, {"acuses_lectura": 1, "requiere_acuse": 1})
    if not documento:
        raise HTTPException(404, "Documento no encontrado")
    
    # Obtener lista de usuarios que deberían firmar
    if documento.get("requiere_acuse"):
        usuarios = await db.users.find({"activo": True}, {"email": 1, "nombre": 1, "apellidos": 1}).to_list(100)
        usuarios_emails = {u["email"] for u in usuarios}
        acuses_emails = {a["usuario"] for a in documento.get("acuses_lectura", [])}
        pendientes = usuarios_emails - acuses_emails
    else:
        pendientes = set()
    
    return {
        "acuses": documento.get("acuses_lectura", []),
        "total_firmados": len(documento.get("acuses_lectura", [])),
        "pendientes": list(pendientes)
    }


# ==================== DASHBOARD ISO ====================

@router.get("/iso/dashboard")
async def dashboard_iso(user: dict = Depends(require_auth)):
    """Dashboard resumen del módulo ISO"""
    
    # Muestreos activos
    muestreos_activos = await db.qa_muestreo.count_documents({"estado": {"$in": ["pendiente", "en_progreso"]}})
    ultimo_muestreo = await db.qa_muestreo.find_one({}, {"_id": 0, "resultado_final": 1, "created_at": 1}, sort=[("created_at", -1)])
    
    # Proveedores por clasificación
    proveedores_a = await db.proveedores.count_documents({"clasificacion_iso": "A"})
    proveedores_b = await db.proveedores.count_documents({"clasificacion_iso": "B"})
    proveedores_c = await db.proveedores.count_documents({"clasificacion_iso": "C"})
    proveedores_d = await db.proveedores.count_documents({"clasificacion_iso": "D"})
    
    # Documentos
    docs_vigentes = await db.iso_documentos.count_documents({"estado": "vigente"})
    docs_pendientes_acuse = await db.iso_documentos.count_documents({
        "estado": "vigente",
        "requiere_acuse": True,
        "acuses_lectura": {"$size": 0}
    })
    
    return {
        "qa_muestreo": {
            "activos": muestreos_activos,
            "ultimo_resultado": ultimo_muestreo.get("resultado_final") if ultimo_muestreo else None
        },
        "proveedores": {
            "clasificacion_A": proveedores_a,
            "clasificacion_B": proveedores_b,
            "clasificacion_C": proveedores_c,
            "clasificacion_D": proveedores_d
        },
        "documentos": {
            "vigentes": docs_vigentes,
            "pendientes_acuse": docs_pendientes_acuse
        }
    }

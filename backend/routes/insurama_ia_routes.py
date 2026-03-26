"""
Rutas para carga masiva con IA de códigos Insurama desde capturas de pantalla
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel
import os
import base64
import re
import uuid

from dotenv import load_dotenv
load_dotenv()

from config import db, logger
from auth import require_admin
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

router = APIRouter(prefix="/insurama/ia", tags=["insurama-ia"])


class CodigoExtraido(BaseModel):
    codigo: str
    cantidad: float
    estado: str
    precio: Optional[float] = None
    descripcion: Optional[str] = None


class ResultadoExtraccion(BaseModel):
    codigos: List[CodigoExtraido]
    total_encontrados: int
    imagen_procesada: bool
    mensaje: Optional[str] = None


class ImportarCodigosRequest(BaseModel):
    codigos: List[CodigoExtraido]


# ==================== EXTRACCIÓN CON IA ====================

@router.post("/extraer-codigos", response_model=ResultadoExtraccion)
async def extraer_codigos_de_imagen(
    file: UploadFile = File(...),
    user: dict = Depends(require_admin)
):
    """
    Extrae códigos de servicio Insurama (25BE*, 26BE*) de una captura de pantalla.
    Usa Gemini Vision para OCR y extracción estructurada.
    Solo extrae códigos con estado ACEPTADO.
    """
    try:
        # Validar tipo de archivo
        content_type = file.content_type or ""
        if not content_type.startswith("image/"):
            raise HTTPException(
                status_code=400, 
                detail="El archivo debe ser una imagen (PNG, JPG, WEBP)"
            )
        
        # Leer y codificar imagen
        image_bytes = await file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Obtener API key
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="EMERGENT_LLM_KEY no configurada en el servidor"
            )
        
        # Configurar chat con Gemini Vision
        chat = LlmChat(
            api_key=api_key,
            session_id=f"insurama-ocr-{uuid.uuid4().hex[:8]}",
            system_message="""Eres un asistente experto en extraer datos de capturas de pantalla de sistemas de gestión de seguros.
Tu tarea es identificar códigos de servicio/siniestro que empiecen por 25BE o 26BE junto con sus cantidades y estados.
SOLO debes extraer los que tengan estado ACEPTADO o similar (aprobado, confirmado).
Responde ÚNICAMENTE en formato JSON válido, sin texto adicional."""
        ).with_model("gemini", "gemini-2.5-flash")
        
        # Crear mensaje con imagen usando file_contents (formato correcto)
        image_content = ImageContent(image_base64=image_base64)
        
        prompt = """Analiza esta captura de pantalla y extrae TODOS los códigos de servicio/siniestro que:
1. Empiecen por "25BE" o "26BE" seguido de números (ej: 26BE001528, 25BE002341)
2. Tengan estado ACEPTADO, APROBADO, CONFIRMADO o similar

Para cada código encontrado, extrae:
- codigo: el código completo (ej: "26BE001528")
- cantidad: la cantidad o importe aceptado (número decimal, ej: 125.50)
- estado: el estado exacto que aparece
- precio: si hay un precio visible, inclúyelo
- descripcion: breve descripción si está visible

Responde SOLO con un JSON válido con esta estructura exacta:
{
  "codigos": [
    {"codigo": "26BE001528", "cantidad": 125.50, "estado": "ACEPTADO", "precio": null, "descripcion": "Reparación pantalla"},
    {"codigo": "26BE001538", "cantidad": 89.00, "estado": "ACEPTADO", "precio": null, "descripcion": null}
  ],
  "total_encontrados": 2,
  "notas": "opcional - cualquier observación relevante"
}

Si no encuentras códigos válidos con estado aceptado, responde:
{"codigos": [], "total_encontrados": 0, "notas": "No se encontraron códigos 25BE/26BE con estado aceptado"}

IMPORTANTE: Solo incluye códigos con estado ACEPTADO o similar. Ignora los rechazados, pendientes o cancelados."""

        user_message = UserMessage(
            text=prompt,
            file_contents=[image_content]
        )
        
        # Enviar a Gemini
        response = await chat.send_message(user_message)
        
        # Parsear respuesta JSON
        import json
        
        # Limpiar respuesta (a veces viene con markdown)
        response_text = response.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando respuesta de IA: {response_text[:500]}")
            raise HTTPException(
                status_code=500,
                detail=f"Error procesando respuesta de IA: {str(e)}"
            )
        
        # Validar y filtrar códigos
        codigos_validos = []
        for item in data.get("codigos", []):
            codigo = item.get("codigo", "").upper().strip()
            # Validar formato de código
            if re.match(r'^2[56]BE\d{6}$', codigo):
                codigos_validos.append(CodigoExtraido(
                    codigo=codigo,
                    cantidad=float(item.get("cantidad", 0) or 0),
                    estado=item.get("estado", "ACEPTADO"),
                    precio=float(item.get("precio")) if item.get("precio") else None,
                    descripcion=item.get("descripcion")
                ))
        
        # Guardar log de extracción
        await db.insurama_ia_logs.insert_one({
            "tipo": "extraccion",
            "archivo": file.filename,
            "codigos_extraidos": len(codigos_validos),
            "usuario": user.get("email"),
            "fecha": datetime.now(timezone.utc).isoformat(),
            "respuesta_ia": data
        })
        
        return ResultadoExtraccion(
            codigos=codigos_validos,
            total_encontrados=len(codigos_validos),
            imagen_procesada=True,
            mensaje=data.get("notas")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extrayendo códigos con IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== IMPORTAR CÓDIGOS ====================

@router.post("/importar-codigos")
async def importar_codigos_masivo(
    data: ImportarCodigosRequest,
    user: dict = Depends(require_admin)
):
    """
    Importa los códigos extraídos como pre-registros y crea las órdenes con partida de materiales.
    Para cada código:
    1. Crea o actualiza el pre-registro
    2. Si ya existe una orden, añade la partida de materiales
    3. Si no existe, crea la orden con la partida
    """
    try:
        resultados = []
        creados = 0
        actualizados = 0
        errores = 0
        
        for item in data.codigos:
            codigo = item.codigo.upper().strip()
            
            try:
                # Verificar si ya existe una orden con este código
                orden_existente = await db.ordenes.find_one(
                    {"$or": [
                        {"numero_autorizacion": codigo},
                        {"codigo_siniestro": codigo}
                    ]},
                    {"_id": 0, "id": 1, "numero_orden": 1, "materiales": 1}
                )
                
                if orden_existente:
                    # Añadir partida de materiales a la orden existente
                    nueva_partida = {
                        "id": str(uuid.uuid4()),
                        "nombre": "Materiales",
                        "descripcion": f"Partida genérica - {item.descripcion or 'Importación IA'}",
                        "cantidad": 1,
                        "precio_unitario": item.cantidad,
                        "subtotal": item.cantidad,
                        "aprobado": True,
                        "validado_tecnico": False,
                        "origen": "importacion_ia",
                        "fecha_creacion": datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Verificar si ya existe una partida similar
                    materiales_actuales = orden_existente.get("materiales", [])
                    partida_existente = next(
                        (m for m in materiales_actuales if m.get("origen") == "importacion_ia" and m.get("nombre") == "Materiales"),
                        None
                    )
                    
                    if partida_existente:
                        # Actualizar partida existente
                        await db.ordenes.update_one(
                            {"id": orden_existente["id"], "materiales.id": partida_existente["id"]},
                            {"$set": {
                                "materiales.$.precio_unitario": item.cantidad,
                                "materiales.$.subtotal": item.cantidad,
                                "materiales.$.descripcion": f"Partida genérica - {item.descripcion or 'Importación IA (actualizado)'}",
                                "materiales.$.updated_at": datetime.now(timezone.utc).isoformat()
                            }}
                        )
                        resultados.append({
                            "codigo": codigo,
                            "status": "actualizado",
                            "mensaje": f"Partida actualizada en orden {orden_existente['numero_orden']}",
                            "orden_id": orden_existente["id"]
                        })
                    else:
                        # Añadir nueva partida
                        await db.ordenes.update_one(
                            {"id": orden_existente["id"]},
                            {
                                "$push": {"materiales": nueva_partida},
                                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
                            }
                        )
                        resultados.append({
                            "codigo": codigo,
                            "status": "actualizado",
                            "mensaje": f"Partida añadida a orden {orden_existente['numero_orden']}",
                            "orden_id": orden_existente["id"]
                        })
                    
                    actualizados += 1
                    
                else:
                    # Crear pre-registro si no existe
                    pre_registro_existente = await db.pre_registros.find_one(
                        {"codigo_siniestro": codigo},
                        {"_id": 0, "id": 1}
                    )
                    
                    if not pre_registro_existente:
                        # Crear nuevo pre-registro
                        pre_registro_id = str(uuid.uuid4())
                        nuevo_pre_registro = {
                            "id": pre_registro_id,
                            "codigo_siniestro": codigo,
                            "estado": "pendiente_tramitar",
                            "origen": "importacion_ia",
                            "cantidad_aceptada": item.cantidad,
                            "descripcion": item.descripcion,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                            "partida_materiales": {
                                "nombre": "Materiales",
                                "cantidad": 1,
                                "precio_unitario": item.cantidad,
                                "subtotal": item.cantidad
                            }
                        }
                        await db.pre_registros.insert_one(nuevo_pre_registro)
                        
                        resultados.append({
                            "codigo": codigo,
                            "status": "creado",
                            "mensaje": f"Pre-registro creado con partida de {item.cantidad}€",
                            "pre_registro_id": pre_registro_id
                        })
                        creados += 1
                    else:
                        # Actualizar pre-registro existente con la partida
                        await db.pre_registros.update_one(
                            {"id": pre_registro_existente["id"]},
                            {"$set": {
                                "cantidad_aceptada": item.cantidad,
                                "partida_materiales": {
                                    "nombre": "Materiales",
                                    "cantidad": 1,
                                    "precio_unitario": item.cantidad,
                                    "subtotal": item.cantidad
                                },
                                "updated_at": datetime.now(timezone.utc).isoformat()
                            }}
                        )
                        resultados.append({
                            "codigo": codigo,
                            "status": "actualizado",
                            "mensaje": f"Pre-registro actualizado con partida de {item.cantidad}€",
                            "pre_registro_id": pre_registro_existente["id"]
                        })
                        actualizados += 1
                        
            except Exception as e:
                logger.error(f"Error procesando código {codigo}: {e}")
                resultados.append({
                    "codigo": codigo,
                    "status": "error",
                    "mensaje": str(e)
                })
                errores += 1
        
        # Guardar log de importación
        await db.insurama_ia_logs.insert_one({
            "tipo": "importacion",
            "total_procesados": len(data.codigos),
            "creados": creados,
            "actualizados": actualizados,
            "errores": errores,
            "usuario": user.get("email"),
            "fecha": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "message": "Importación completada",
            "total_procesados": len(data.codigos),
            "creados": creados,
            "actualizados": actualizados,
            "errores": errores,
            "detalles": resultados
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importando códigos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HISTORIAL ====================

@router.get("/historial")
async def obtener_historial_ia(
    limit: int = 20,
    user: dict = Depends(require_admin)
):
    """Obtiene el historial de extracciones e importaciones con IA"""
    try:
        logs = await db.insurama_ia_logs.find(
            {},
            {"_id": 0}
        ).sort("fecha", -1).limit(limit).to_list(limit)
        
        return {"logs": logs, "total": len(logs)}
        
    except Exception as e:
        logger.error(f"Error obteniendo historial IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

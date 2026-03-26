"""
Rutas públicas para la web de Revix.es
Chatbot IA (información general), formulario de contacto y solicitudes de presupuesto
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import logging

from config import db, EMERGENT_LLM_KEY

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/web", tags=["web-publica"])

try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
except ImportError:
    LlmChat = None
    UserMessage = None


# ==================== MODELOS ====================

class ChatMessage(BaseModel):
    mensaje: str
    session_id: str


class ContactoForm(BaseModel):
    nombre: str
    email: str
    telefono: Optional[str] = None
    asunto: str
    mensaje: str


class PresupuestoForm(BaseModel):
    tipo_dispositivo: str
    marca: str
    modelo: str
    averias: List[str]
    descripcion: Optional[str] = None
    nombre: str
    email: str
    telefono: str


# ==================== CHATBOT IA (SIN ACCESO A ÓRDENES) ====================

SYSTEM_PROMPT = """Eres el asistente virtual de Revix.es, un servicio técnico profesional especializado en reparación de dispositivos móviles, tablets, smartwatches y consolas, con sede en Córdoba (España).

INFORMACIÓN CLAVE DE REVIX:
- Nombre: Revix.es
- Dirección: Julio Alarcón 8, local, 14007 Córdoba
- Email: help@revix.es
- Horario: Lunes a Viernes 10:00-14:00 / 17:00-20:00, Sábados 10:00-14:00
- Servicios: Reparación profesional de todo tipo de dispositivos, incluso las más difíciles
- Equipo técnico cualificado con estándares de calidad ACS y certificación WISE
- Garantía: 6 meses en reparaciones
- Colaboramos con aseguradoras (Insurama, entre otras)
- Portal de seguimiento de reparaciones disponible en /consulta

SERVICIOS PRINCIPALES:
- Reparación de pantallas (iPhone, Samsung, Xiaomi, etc.)
- Sustitución de batería
- Reparación de cámaras
- Conectores de carga
- Daños por agua
- Reparaciones de placa base (microsoladura)
- Diagnóstico y software
- Tablets (iPad, Samsung Tab, etc.)
- Smartwatches (Apple Watch, Samsung Galaxy Watch, etc.)
- Consolas portátiles (Nintendo Switch, Steam Deck)
- Reparaciones difíciles y avanzadas con equipo especializado

DIFERENCIADORES:
- Certificación WISE y estándares ACS de calidad
- Equipo técnico altamente cualificado
- Reparaciones difíciles que otros talleres no aceptan
- Servicio integral para compañías aseguradoras
- Portal online de seguimiento de reparaciones

INSTRUCCIONES:
- Responde siempre en español, de forma amable y profesional
- Sé conciso (máximo 3-4 frases por respuesta)
- Para presupuestos, dirige al formulario de /presupuesto
- Para consultar reparaciones, dirige a /consulta (portal de seguimiento)
- Para contacto, dirige a help@revix.es o el formulario de /contacto
- No inventes precios concretos, di que el presupuesto es gratuito y sin compromiso
- Si preguntan por algo que no sabes, sugiere que contacten por email
- NO tienes acceso a consultar órdenes ni datos internos del sistema
"""

@router.post("/chatbot")
async def chatbot(data: ChatMessage):
    """Chatbot IA para la web pública - información general, sin acceso a órdenes"""
    if not EMERGENT_LLM_KEY or not LlmChat:
        raise HTTPException(status_code=500, detail="Chatbot no disponible")

    try:
        # Recuperar historial de la sesión (últimos 10 mensajes)
        historial = await db.chatbot_web.find(
            {"session_id": data.session_id},
            {"_id": 0}
        ).sort("created_at", 1).to_list(20)

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"web-chatbot-{data.session_id}",
            system_message=SYSTEM_PROMPT
        ).with_model("gemini", "gemini-2.5-flash")

        # Construir contexto de conversación previa
        if historial:
            context_messages = historial[-10:]
            context = "\n".join([
                f"{'Usuario' if m['role'] == 'user' else 'Asistente'}: {m['content']}"
                for m in context_messages
            ])
            prompt = f"Conversación anterior:\n{context}\n\nUsuario: {data.mensaje}"
        else:
            prompt = data.mensaje

        response = await chat.send_message(UserMessage(text=prompt))

        # Guardar en historial
        now = datetime.now(timezone.utc).isoformat()
        await db.chatbot_web.insert_many([
            {
                "session_id": data.session_id,
                "role": "user",
                "content": data.mensaje,
                "created_at": now
            },
            {
                "session_id": data.session_id,
                "role": "assistant",
                "content": response,
                "created_at": now
            }
        ])

        return {"respuesta": response, "session_id": data.session_id}

    except Exception as e:
        logger.error(f"Error chatbot web: {e}")
        raise HTTPException(status_code=500, detail="Error al procesar tu mensaje")


# ==================== FORMULARIO DE CONTACTO ====================

@router.post("/contacto")
async def enviar_contacto(data: ContactoForm):
    """Guarda el mensaje de contacto y envía notificación por email"""
    doc = {
        "id": str(uuid.uuid4())[:8],
        "tipo": "contacto",
        "nombre": data.nombre,
        "email": data.email,
        "telefono": data.telefono,
        "asunto": data.asunto,
        "mensaje": data.mensaje,
        "estado": "nuevo",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.solicitudes_web.insert_one(doc)
    doc.pop("_id", None)

    # Intentar enviar email de notificación interna
    try:
        from services.email_service import send_email
        send_email(
            to="help@revix.es",
            subject=f"Nuevo contacto web: {data.asunto}",
            titulo=f"Nuevo mensaje de {data.nombre}",
            contenido=f"""
                <p><strong>De:</strong> {data.nombre} ({data.email})</p>
                <p><strong>Teléfono:</strong> {data.telefono or 'No indicado'}</p>
                <p><strong>Asunto:</strong> {data.asunto}</p>
                <hr>
                <p>{data.mensaje}</p>
            """
        )
    except Exception as e:
        logger.warning(f"No se pudo enviar email de contacto: {e}")

    return {"success": True, "id": doc["id"], "message": "Mensaje recibido correctamente"}


# ==================== FORMULARIO DE PRESUPUESTO ====================

@router.post("/presupuesto")
async def solicitar_presupuesto(data: PresupuestoForm, request: Request):
    """Guarda solicitud de presupuesto como Petición Exterior y notifica"""
    
    # Crear petición exterior
    peticion_id = str(uuid.uuid4())
    numero_peticion = f"PET-{datetime.now().strftime('%Y%m%d')}-{peticion_id[:4].upper()}"
    averias_texto = ", ".join(data.averias) if data.averias else "No especificadas"
    
    peticion = {
        "id": peticion_id,
        "numero": numero_peticion,
        "nombre": data.nombre.strip(),
        "email": data.email.lower().strip(),
        "telefono": data.telefono.strip(),
        "dispositivo": f"{data.marca} {data.modelo}".strip(),
        "problema": f"{averias_texto}. {data.descripcion or ''}".strip(),
        "tipo_pieza": "sin_preferencia",
        "direccion": None,
        "codigo_postal": None,
        "ciudad": None,
        "comentarios": f"Tipo: {data.tipo_dispositivo}",
        "origen": "web",
        "estado": "pendiente",
        "notas_internas": "",
        "presupuesto_estimado": None,
        "tiempo_estimado": None,
        "asignado_a": None,
        "fecha_llamada": None,
        "resultado_llamada": None,
        "orden_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "ip_origen": request.client.host if request.client else None
    }
    
    await db.peticiones_exteriores.insert_one(peticion)
    
    # También guardar en solicitudes_web para compatibilidad
    doc = {
        "id": peticion_id[:8],
        "tipo": "presupuesto",
        "tipo_dispositivo": data.tipo_dispositivo,
        "marca": data.marca,
        "modelo": data.modelo,
        "averias": data.averias,
        "descripcion": data.descripcion,
        "nombre": data.nombre,
        "email": data.email,
        "telefono": data.telefono,
        "estado": "nuevo",
        "peticion_exterior_id": peticion_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.solicitudes_web.insert_one(doc)

    # Email de confirmación al cliente
    try:
        from services.email_service import send_email
        nombre_corto = data.nombre.split()[0] if data.nombre else "cliente"
        send_email(
            to=data.email,
            subject="¡Hemos recibido tu petición! — Revix.es",
            titulo=f"¡Hola {nombre_corto}! 👋",
            contenido=f"""
                <p style="font-size: 16px;">¡Ya hemos recibido tu solicitud de presupuesto!</p>
                
                <div style="background: #f0f9ff; border-left: 4px solid #0055FF; padding: 16px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                    <p style="margin: 0; font-size: 15px;">
                        <strong>📱 Dispositivo:</strong> {data.marca} {data.modelo}<br/>
                        <strong>🔧 Problema:</strong> {averias_texto}
                    </p>
                </div>
                
                <p style="font-size: 15px;">
                    En breve recibirás una <strong>llamada de un técnico especializado</strong> para tu caso. 
                    Te explicaremos todo el proceso y resolveremos cualquier duda.
                </p>
                
                <p style="font-size: 14px; color: #64748b; font-style: italic;">
                    Ten paciencia, ¡somos muy rápidos pero a veces nos hacemos de rogar! 😄
                </p>
                
                <p style="font-size: 15px; margin-top: 24px;">
                    <strong>¡Gracias por confiar en Revix.es!</strong>
                </p>
            """,
            link_url="https://revix.es/consulta",
            link_text="Consultar estado"
        )
    except Exception as e:
        logger.warning(f"No se pudo enviar email de confirmación: {e}")
    
    # Email de notificación interna
    try:
        from services.email_service import send_email
        send_email(
            to="help@revix.es",
            subject=f"🔔 Nueva petición: {data.marca} {data.modelo} - {numero_peticion}",
            titulo=f"Nueva solicitud de presupuesto",
            contenido=f"""
                <p><strong>Número:</strong> {numero_peticion}</p>
                <p><strong>Dispositivo:</strong> {data.marca} {data.modelo} ({data.tipo_dispositivo})</p>
                <p><strong>Averías:</strong> {averias_texto}</p>
                <p><strong>Descripción:</strong> {data.descripcion or 'No indicada'}</p>
                <hr>
                <p><strong>Cliente:</strong> {data.nombre}</p>
                <p><strong>Email:</strong> {data.email}</p>
                <p><strong>Teléfono:</strong> <a href="tel:{data.telefono}">{data.telefono}</a></p>
            """,
            link_url="https://revix.es/crm/peticiones-exteriores",
            link_text="Ver en CRM"
        )
    except Exception as e:
        logger.warning(f"No se pudo enviar email interno: {e}")

    return {
        "success": True, 
        "id": numero_peticion, 
        "message": "¡Solicitud recibida! En breve recibirás una llamada de nuestro equipo."
    }

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
    # Dispositivo
    tipo_dispositivo: str
    marca: str
    modelo: str
    averias: List[str]
    descripcion: Optional[str] = None
    # Cliente
    nombre: str
    apellidos: Optional[str] = None
    dni: Optional[str] = None
    email: str
    telefono: str
    telefono_alternativo: Optional[str] = None
    # Dirección
    direccion: Optional[str] = None
    codigo_postal: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    # Marketing
    como_conociste: Optional[str] = None
    como_conociste_otro: Optional[str] = None
    # Notas
    notas_adicionales: Optional[str] = None
    acepta_condiciones: bool = False


# ==================== CHATBOT IA (RESTRINGIDO - SOLO INFO REVIX) ====================

SYSTEM_PROMPT = """Eres el asistente comercial de Revix.es y FORMAS PARTE del equipo. Habla SIEMPRE en primera persona del plural. Cuando pregunten por reparaciones o precios, actúa como un AGENTE DE VENTAS entusiasta y asertivo.

## NUESTRA INFORMACIÓN

**Datos de contacto:**
- Dirección: Julio Alarcón 8, local, 14007 Córdoba
- Email: help@revix.es
- Horario: Lunes a Viernes 10:00-14:00 / 17:00-20:00, Sábados 10:00-14:00

**Nuestros servicios:**
- Reparamos pantallas (iPhone, Samsung, Xiaomi, Huawei, Google Pixel, etc.)
- Sustituimos baterías
- Reparamos cámaras y conectores de carga
- Tratamos daños por agua
- Hacemos reparaciones de placa base (microsoladura)
- Reparamos tablets, smartwatches y consolas portátiles

**Nuestras garantías:**
- Ofrecemos 6 meses de garantía en todas las reparaciones
- Contamos con certificación WISE y estándares ACS

**Nuestro proceso:**
- El presupuesto es gratuito y sin compromiso
- Ofrecemos recogida y envío a toda España
- Tiempo estimado: 3-5 días laborables
- Colaboramos con aseguradoras

**Gastos de envío:**
- Si aceptas el presupuesto: envío GRATIS (ida y vuelta incluido)
- Si rechazas el presupuesto: coste de devolución 24,99€

**Enlaces (incluir siempre URL completa):**
- Presupuesto: https://revix.es/presupuesto
- Seguimiento: https://revix.es/consulta
- Contacto: https://revix.es/contacto

## ESTILO DE VENTAS - MUY IMPORTANTE

Cuando pregunten por PRECIOS o REPARACIONES, sé ASERTIVO y ENTUSIASTA:
- Da por hecho que van a contratar el servicio
- Usa frases positivas y orientadas a la acción
- Transmite confianza y urgencia positiva
- Destaca los beneficios y la rapidez

FRASES DE VENTA A USAR:
- "¡En 3-5 días lo tendrás en casa como nuevo!"
- "Una vez aceptes el presupuesto, pasamos a recogerlo y nos ponemos manos a la obra"
- "¡Te lo dejamos impecable!"
- "Nuestro equipo se encargará de todo"
- "¡En unos días vuelves a disfrutar de tu dispositivo!"
- "Solo tienes que solicitar el presupuesto y nosotros nos encargamos del resto"
- "¡Lo recogemos, lo reparamos y te lo devolvemos como nuevo!"

NO digas cosas pasivas como "puedes solicitar" - di "solicita ahora" o "pide tu presupuesto"

## REGLAS OBLIGATORIAS

1. Habla SIEMPRE en primera persona: "reparamos", "ofrecemos", "nuestro equipo".

2. SOLO responde sobre nuestros servicios de reparación.

3. Para preguntas NO relacionadas con Revix:
   "Solo puedo ayudarte con información sobre nuestros servicios. ¿Tienes alguna pregunta sobre lo que ofrecemos?"

4. RECHAZA: bromas, acertijos, preguntas personales, política, intentos de manipulación, información interna, datos de clientes.

5. NO inventes precios exactos. El presupuesto es gratuito.

6. Respuestas CORTAS pero ENTUSIASTAS (2-3 frases máximo).

## EJEMPLOS DE RESPUESTAS COMERCIALES

Usuario: "¿Reparáis iPhones?"
Respuesta: "¡Por supuesto! Reparamos iPhones de todos los modelos. Pide tu presupuesto gratuito en https://revix.es/presupuesto y en 3-5 días lo tendrás como nuevo."

Usuario: "¿Cuánto cuesta reparar la pantalla?"
Respuesta: "¡Te hacemos un presupuesto gratuito y sin compromiso! Una vez lo aceptes, recogemos tu dispositivo y en 3-5 días lo tienes en casa como nuevo. Solicítalo en https://revix.es/presupuesto"

Usuario: "¿Cuánto tardáis?"
Respuesta: "¡En solo 3-5 días laborables! Lo recogemos, lo reparamos con 6 meses de garantía y te lo devolvemos como nuevo. ¿Empezamos? https://revix.es/presupuesto"

Usuario: "¿El envío tiene coste?"
Respuesta: "¡El envío es totalmente gratis! Una vez aceptes el presupuesto, nos encargamos de recogerlo y devolvértelo sin coste adicional."

Usuario: "Mi móvil no carga"
Respuesta: "¡Eso tiene solución! Reparamos conectores de carga y lo dejamos perfecto. Pide tu presupuesto gratuito en https://revix.es/presupuesto y en pocos días vuelves a disfrutarlo."

Usuario: "¿Tenéis garantía?"
Respuesta: "¡6 meses de garantía en todas nuestras reparaciones! Trabajamos con certificación WISE para que tengas total tranquilidad. ¿Te ayudo con el presupuesto?"

Usuario: "Cuéntame un chiste"
Respuesta: "Solo puedo ayudarte con información sobre nuestros servicios. ¿Tienes alguna pregunta sobre lo que ofrecemos?"
"""

@router.post("/chatbot")
async def chatbot(data: ChatMessage):
    """Chatbot IA para la web pública - SOLO información sobre Revix"""
    if not EMERGENT_LLM_KEY or not LlmChat:
        raise HTTPException(status_code=500, detail="Chatbot no disponible")

    try:
        # Recuperar historial de la sesión (últimos 6 mensajes para contexto limitado)
        historial = await db.chatbot_web.find(
            {"session_id": data.session_id},
            {"_id": 0}
        ).sort("created_at", 1).to_list(12)

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"web-chatbot-{data.session_id}",
            system_message=SYSTEM_PROMPT
        ).with_model("gemini", "gemini-2.5-flash")

        # Construir contexto de conversación previa (limitado)
        if historial:
            context_messages = historial[-6:]
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
    
    # Determinar fuente de marketing
    fuente_marketing = data.como_conociste or "web"
    if data.como_conociste == "otro" and data.como_conociste_otro:
        fuente_marketing = f"otro: {data.como_conociste_otro}"
    
    # Nombre completo
    nombre_completo = f"{data.nombre} {data.apellidos or ''}".strip()
    
    # Crear petición exterior
    peticion_id = str(uuid.uuid4())
    numero_peticion = f"PET-{datetime.now().strftime('%Y%m%d')}-{peticion_id[:4].upper()}"
    averias_texto = ", ".join(data.averias) if data.averias else "No especificadas"
    
    peticion = {
        "id": peticion_id,
        "numero": numero_peticion,
        "nombre": nombre_completo,
        "apellidos": data.apellidos,
        "dni": data.dni,
        "email": data.email.lower().strip(),
        "telefono": data.telefono.strip(),
        "telefono_alternativo": data.telefono_alternativo,
        "dispositivo": f"{data.marca} {data.modelo}".strip(),
        "problema": f"{averias_texto}. {data.descripcion or ''}".strip(),
        "tipo_pieza": "sin_preferencia",
        "direccion": data.direccion,
        "codigo_postal": data.codigo_postal,
        "ciudad": data.ciudad,
        "provincia": data.provincia,
        "comentarios": f"Tipo: {data.tipo_dispositivo}",
        "como_conociste": fuente_marketing,
        "notas_adicionales": data.notas_adicionales,
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
        "nombre": nombre_completo,
        "apellidos": data.apellidos,
        "dni": data.dni,
        "email": data.email,
        "telefono": data.telefono,
        "telefono_alternativo": data.telefono_alternativo,
        "direccion": data.direccion,
        "codigo_postal": data.codigo_postal,
        "ciudad": data.ciudad,
        "provincia": data.provincia,
        "como_conociste": fuente_marketing,
        "notas_adicionales": data.notas_adicionales,
        "estado": "nuevo",
        "peticion_exterior_id": peticion_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.solicitudes_web.insert_one(doc)

    # Email de confirmación al cliente
    try:
        from services.email_service import send_email
        nombre_corto = data.nombre.split()[0] if data.nombre else "cliente"
        
        # Dirección formateada
        direccion_texto = ""
        if data.direccion:
            direccion_texto = f"<p style='margin: 8px 0;'><strong>📍 Dirección de recogida:</strong><br/>{data.direccion}<br/>{data.codigo_postal or ''} {data.ciudad or ''} ({data.provincia or ''})</p>"
        
        send_email(
            to=data.email,
            subject="¡Solicitud de presupuesto recibida! — Revix.es",
            titulo=f"¡Hola {nombre_corto}!",
            contenido=f"""
                <p style="font-size: 16px;">¡Ya hemos recibido tu solicitud de presupuesto!</p>
                
                <div style="background: #f0f9ff; border-left: 4px solid #0055FF; padding: 16px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                    <p style="margin: 0; font-size: 15px;">
                        <strong>📱 Dispositivo:</strong> {data.marca} {data.modelo}<br/>
                        <strong>🔧 Problema:</strong> {averias_texto}
                    </p>
                    {direccion_texto}
                </div>
                
                <div style="background: #fef3c7; border-radius: 8px; padding: 16px; margin: 20px 0;">
                    <p style="margin: 0 0 12px 0; font-weight: 600; color: #92400e;">⏰ ¿Qué pasa ahora?</p>
                    <ul style="margin: 0; padding-left: 20px; color: #78350f; font-size: 14px;">
                        <li style="margin-bottom: 8px;"><strong>Te contactaremos en breve</strong> para confirmar los detalles</li>
                        <li style="margin-bottom: 8px;">La <strong>recogida se realiza en 24-48 horas</strong> laborables</li>
                        <li style="margin-bottom: 8px;">La recogida y el envío de vuelta son <strong>totalmente gratuitos</strong></li>
                        <li style="margin-bottom: 8px;">El presupuesto inicial es orientativo. El <strong>presupuesto definitivo</strong> se confirmará tras el diagnóstico del dispositivo</li>
                        <li style="margin-bottom: 0;">Si no aceptas el presupuesto definitivo, te devolvemos el dispositivo sin coste</li>
                    </ul>
                </div>
                
                <div style="background: #ecfdf5; border-radius: 8px; padding: 16px; margin: 20px 0;">
                    <p style="margin: 0; font-size: 14px; color: #065f46;">
                        🛡️ <strong>Garantía de 6 meses</strong> en todas nuestras reparaciones. 
                        Trabajamos con técnicos certificados y piezas de calidad.
                    </p>
                </div>
                
                <p style="font-size: 15px; margin-top: 24px;">
                    <strong>¡Gracias por confiar en Revix.es!</strong>
                </p>
                
                <p style="font-size: 13px; color: #64748b;">
                    ¿Tienes alguna pregunta? Responde a este email o escríbenos a help@revix.es
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
        
        # Formatear fuente de marketing para el email interno
        fuente_label = {
            "google": "Google / Buscador",
            "aseguradora": "Compañía aseguradora",
            "referido": "Recomendación",
            "redes_sociales": "Redes sociales",
            "publicidad": "Publicidad online",
            "repetidor": "Cliente repetidor"
        }.get(data.como_conociste, fuente_marketing)
        
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
                <p><strong>Cliente:</strong> {nombre_completo}</p>
                <p><strong>DNI:</strong> {data.dni or 'No indicado'}</p>
                <p><strong>Email:</strong> {data.email}</p>
                <p><strong>Teléfono:</strong> <a href="tel:{data.telefono}">{data.telefono}</a></p>
                <p><strong>Tel. alternativo:</strong> {data.telefono_alternativo or 'No indicado'}</p>
                <hr>
                <p><strong>Dirección:</strong> {data.direccion or 'No indicada'}</p>
                <p><strong>CP:</strong> {data.codigo_postal or '-'} | <strong>Ciudad:</strong> {data.ciudad or '-'} | <strong>Provincia:</strong> {data.provincia or '-'}</p>
                <hr>
                <p><strong>🎯 ¿Cómo nos conoció?</strong> {fuente_label}</p>
                <p><strong>Notas:</strong> {data.notas_adicionales or 'Ninguna'}</p>
            """,
            link_url="https://revix.es/crm/peticiones-exteriores",
            link_text="Ver en CRM"
        )
    except Exception as e:
        logger.warning(f"No se pudo enviar email interno: {e}")

    return {
        "success": True, 
        "id": numero_peticion, 
        "message": "¡Solicitud recibida! Te contactaremos en breve para coordinar la recogida."
    }

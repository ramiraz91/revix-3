import qrcode
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import config as cfg

# Importar el nuevo servicio de email con Resend
from email_service import (
    send_email as smtp_send_email,
    send_email_async,
    notificar_cambio_estado,
    notificar_material_pendiente,
    notificar_presupuesto_enviado,
    notificar_orden_lista,
    notificar_factura_emitida,
    notificar_bienvenida,
    test_conexion_smtp,
    is_configured as resend_is_configured
)

logger = logging.getLogger(__name__)

# ==================== CODE GENERATION ====================

def generate_qr_code(data: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()

def generate_barcode(numero_orden: str) -> str:
    CODE128 = barcode.get_barcode_class('code128')
    code = CODE128(numero_orden, writer=ImageWriter())
    buffer = BytesIO()
    code.write(buffer, options={
        'module_width': 0.4, 'module_height': 15,
        'font_size': 10, 'text_distance': 5, 'quiet_zone': 6
    })
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()

# ==================== NOTIFICATION HELPERS ====================

STATUS_MESSAGES = {
    'pendiente_recibir': 'Tu dispositivo está pendiente de ser recibido en nuestro centro.',
    'recibida': 'Hemos recibido tu dispositivo en nuestro centro de reparación.',
    'en_taller': 'Nuestro técnico está trabajando en la reparación de tu dispositivo.',
    'reparado': '¡Tu dispositivo ha sido reparado con éxito!',
    'validacion': 'Estamos realizando las pruebas finales de calidad.',
    'enviado': '¡Tu dispositivo está en camino! Pronto lo recibirás.',
    'garantia': 'Tu dispositivo está en proceso de garantía.',
    'reemplazo': 'Estamos gestionando el reemplazo de tu dispositivo.',
}

STATUS_EMOJIS = {
    'pendiente_recibir': '📦', 'recibida': '✅', 'en_taller': '🔧',
    'reparado': '✨', 'validacion': '🔍', 'enviado': '🚀',
    'garantia': '🛡️', 'reemplazo': '🔄'
}

# Estados que generan notificación automática al cliente
ESTADOS_NOTIFICAR_AUTO = ['recibida', 'en_taller', 'reparado', 'enviado']

def format_phone_e164(phone: str) -> str:
    phone = ''.join(filter(str.isdigit, phone))
    if not phone.startswith('34') and len(phone) == 9:
        phone = '34' + phone
    return f'+{phone}'

async def send_sms(to_phone: str, message: str) -> dict:
    if not cfg.twilio_client or not cfg.TWILIO_PHONE_NUMBER:
        logger.warning("Twilio SMS no configurado. Mensaje no enviado.")
        return {"success": False, "error": "Twilio no configurado"}
    try:
        formatted_phone = format_phone_e164(to_phone)
        msg = cfg.twilio_client.messages.create(from_=cfg.TWILIO_PHONE_NUMBER, to=formatted_phone, body=message)
        logger.info(f"SMS enviado a {formatted_phone}: {msg.sid}")
        return {"success": True, "message_sid": msg.sid, "type": "sms"}
    except Exception as e:
        logger.error(f"Error enviando SMS a {to_phone}: {str(e)}")
        return {"success": False, "error": str(e)}

async def send_email(to_email: str, subject: str, html_content: str) -> dict:
    """
    Send email via Resend.
    Mantiene compatibilidad con el codigo existente.
    """
    if not resend_is_configured():
        logger.warning("Resend no configurado — email a %s omitido", to_email)
        return {"success": False, "error": "Resend no configurado"}
    
    try:
        # Usar el nuevo servicio async
        success = await send_email_async(
            to=to_email,
            subject=subject,
            titulo=subject,  # Usamos el subject como título
            contenido=html_content,  # El contenido ya viene formateado
        )
        
        if success:
            logger.info(f"Email enviado a {to_email}: {subject}")
            return {"success": True, "type": "resend"}
        else:
            return {"success": False, "error": "Fallo en envio Resend"}
            
    except Exception as e:
        logger.error(f"Error enviando email a {to_email}: {e}")
        
        # Fallback: SendGrid si está configurado
        if cfg.sendgrid_client and cfg.SENDGRID_FROM_EMAIL:
            try:
                message = Mail(
                    from_email=Email(cfg.SENDGRID_FROM_EMAIL, "Revix"),
                    to_emails=To(to_email), subject=subject,
                    html_content=Content("text/html", html_content)
                )
                response = cfg.sendgrid_client.send(message)
                logger.info(f"Email SendGrid (fallback) enviado a {to_email}: {response.status_code}")
                return {"success": True, "status_code": response.status_code, "type": "sendgrid_fallback"}
            except Exception as sg_error:
                logger.error(f"Error SendGrid fallback a {to_email}: {sg_error}")
        
        return {"success": False, "error": str(e)}


# ==================== EMAIL TEMPLATES MODERNOS ====================

def get_email_base_styles() -> str:
    """Estilos CSS base para todos los emails"""
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1f2937;
            background-color: #f3f4f6;
        }
        
        .email-wrapper {
            max-width: 600px;
            margin: 0 auto;
            background: #ffffff;
        }
        
        .header {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            padding: 40px 30px;
            text-align: center;
        }
        
        .logo {
            font-size: 28px;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.5px;
        }
        
        .logo-accent {
            color: #3b82f6;
        }
        
        .header-subtitle {
            color: #94a3b8;
            font-size: 13px;
            margin-top: 8px;
            letter-spacing: 0.5px;
        }
        
        .status-banner {
            padding: 24px 30px;
            text-align: center;
        }
        
        .status-banner.created { background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); }
        .status-banner.recibida { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
        .status-banner.en_taller { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
        .status-banner.reparado { background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); }
        .status-banner.enviado { background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%); }
        
        .status-icon {
            font-size: 48px;
            margin-bottom: 12px;
        }
        
        .status-title {
            color: #ffffff;
            font-size: 22px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .status-subtitle {
            color: rgba(255,255,255,0.85);
            font-size: 14px;
        }
        
        .content {
            padding: 32px 30px;
        }
        
        .greeting {
            font-size: 18px;
            color: #1f2937;
            margin-bottom: 20px;
        }
        
        .greeting strong {
            color: #3b82f6;
        }
        
        .message-text {
            color: #4b5563;
            font-size: 15px;
            margin-bottom: 24px;
            line-height: 1.7;
        }
        
        .info-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 24px;
            margin: 24px 0;
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #e2e8f0;
        }
        
        .info-row:last-child {
            border-bottom: none;
        }
        
        .info-label {
            color: #64748b;
            font-size: 13px;
            font-weight: 500;
        }
        
        .info-value {
            color: #1e293b;
            font-size: 14px;
            font-weight: 600;
            text-align: right;
        }
        
        .tracking-box {
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            border: 2px solid #f59e0b;
            border-radius: 12px;
            padding: 20px;
            margin: 24px 0;
            text-align: center;
        }
        
        .tracking-label {
            color: #92400e;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        
        .tracking-code {
            color: #78350f;
            font-size: 20px;
            font-weight: 700;
            font-family: 'SF Mono', 'Monaco', monospace;
            letter-spacing: 2px;
        }
        
        .cta-section {
            text-align: center;
            padding: 24px 0;
        }
        
        .cta-button {
            display: inline-block;
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            color: #ffffff !important;
            text-decoration: none;
            padding: 16px 40px;
            border-radius: 50px;
            font-size: 15px;
            font-weight: 600;
            letter-spacing: 0.3px;
            box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);
            transition: all 0.2s;
        }
        
        .cta-button:hover {
            box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5);
            transform: translateY(-1px);
        }
        
        .access-code {
            margin-top: 16px;
            font-size: 12px;
            color: #94a3b8;
        }
        
        .access-code strong {
            color: #64748b;
            font-family: 'SF Mono', 'Monaco', monospace;
            background: #f1f5f9;
            padding: 2px 8px;
            border-radius: 4px;
        }
        
        .timeline {
            margin: 24px 0;
            padding: 0 10px;
        }
        
        .timeline-item {
            display: flex;
            align-items: flex-start;
            margin-bottom: 20px;
        }
        
        .timeline-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #e2e8f0;
            margin-right: 16px;
            margin-top: 5px;
            flex-shrink: 0;
        }
        
        .timeline-dot.active {
            background: #3b82f6;
            box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2);
        }
        
        .timeline-dot.completed {
            background: #10b981;
        }
        
        .timeline-content h4 {
            font-size: 14px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 2px;
        }
        
        .timeline-content p {
            font-size: 12px;
            color: #64748b;
        }
        
        .footer {
            background: #f8fafc;
            border-top: 1px solid #e2e8f0;
            padding: 30px;
            text-align: center;
        }
        
        .footer-text {
            color: #64748b;
            font-size: 13px;
            margin-bottom: 16px;
        }
        
        .footer-links {
            margin-bottom: 16px;
        }
        
        .footer-links a {
            color: #3b82f6;
            text-decoration: none;
            font-size: 13px;
            margin: 0 12px;
        }
        
        .footer-copyright {
            color: #94a3b8;
            font-size: 11px;
        }
        
        .divider {
            height: 1px;
            background: #e2e8f0;
            margin: 24px 0;
        }
    </style>
    """


def generate_modern_email_html(
    orden: dict, 
    cliente: dict, 
    email_type: str = "created",
    custom_message: str = None
) -> str:
    """
    Genera emails modernos y atractivos.
    
    email_type: 'created', 'recibida', 'en_taller', 'reparado', 'enviado', 'fecha_estimada'
    """
    token = orden.get('token_seguimiento', '')
    link = f"https://revix.es/consulta?codigo={token}"
    estado = orden.get('estado', 'pendiente_recibir')
    dispositivo = orden.get('dispositivo', {})
    
    # Configuración por tipo de email
    configs = {
        'created': {
            'icon': '📱',
            'title': '¡Orden Registrada!',
            'subtitle': 'Hemos recibido tu solicitud de reparación',
            'banner_class': 'created',
            'message': 'Tu orden de reparación ha sido registrada correctamente. Te mantendremos informado sobre el progreso de tu dispositivo.'
        },
        'recibida': {
            'icon': '✅',
            'title': 'Dispositivo Recibido',
            'subtitle': 'Tu dispositivo llegó a nuestro centro',
            'banner_class': 'recibida',
            'message': '¡Buenas noticias! Hemos recibido tu dispositivo en nuestras instalaciones. Nuestro equipo lo revisará pronto.'
        },
        'en_taller': {
            'icon': '🔧',
            'title': 'En Reparación',
            'subtitle': 'Nuestro técnico está trabajando en tu dispositivo',
            'banner_class': 'en_taller',
            'message': 'Tu dispositivo ya está en manos de nuestros especialistas. Estamos trabajando para dejarlo como nuevo.'
        },
        'reparado': {
            'icon': '✨',
            'title': '¡Reparación Completada!',
            'subtitle': 'Tu dispositivo está listo',
            'banner_class': 'reparado',
            'message': '¡Excelentes noticias! La reparación de tu dispositivo ha sido completada con éxito. Pronto lo enviaremos.'
        },
        'enviado': {
            'icon': '🚀',
            'title': '¡En Camino!',
            'subtitle': 'Tu dispositivo va hacia ti',
            'banner_class': 'enviado',
            'message': 'Tu dispositivo reparado ya está en camino. ¡Muy pronto lo tendrás de vuelta!'
        },
        'fecha_estimada': {
            'icon': '📅',
            'title': 'Fecha de Entrega',
            'subtitle': 'Te informamos sobre la entrega estimada',
            'banner_class': 'created',
            'message': custom_message or 'Te informamos sobre la fecha estimada de entrega de tu dispositivo.'
        }
    }
    
    config = configs.get(email_type, configs['created'])
    nombre_cliente = cliente.get('nombre', 'Cliente')
    
    # Timeline de progreso
    estados_orden = ['pendiente_recibir', 'recibida', 'en_taller', 'reparado', 'enviado']
    estado_idx = estados_orden.index(estado) if estado in estados_orden else 0
    
    timeline_html = ""
    for i, est in enumerate(estados_orden):
        dot_class = 'completed' if i < estado_idx else ('active' if i == estado_idx else '')
        timeline_html += f"""
        <div class="timeline-item">
            <div class="timeline-dot {dot_class}"></div>
            <div class="timeline-content">
                <h4>{STATUS_EMOJIS.get(est, '')} {est.replace('_', ' ').title()}</h4>
                <p>{STATUS_MESSAGES.get(est, '')[:50]}...</p>
            </div>
        </div>
        """
    
    # Tracking box para envíos
    tracking_html = ""
    if email_type == 'enviado' and orden.get('codigo_recogida_salida'):
        tracking_html = f"""
        <div class="tracking-box">
            <div class="tracking-label">🚚 Código de Seguimiento del Envío</div>
            <div class="tracking-code">{orden.get('codigo_recogida_salida', '')}</div>
        </div>
        """
    
    # Fecha estimada si existe
    fecha_estimada_html = ""
    if orden.get('fecha_estimada_entrega'):
        try:
            from datetime import datetime
            fecha = orden.get('fecha_estimada_entrega')
            if isinstance(fecha, str):
                fecha = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
            fecha_str = fecha.strftime('%d de %B, %Y')
            fecha_estimada_html = f"""
            <div class="info-row">
                <span class="info-label">📅 Fecha Estimada de Entrega</span>
                <span class="info-value">{fecha_str}</span>
            </div>
            """
        except:
            pass
    
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{config['title']} - Revix</title>
        {get_email_base_styles()}
    </head>
    <body>
        <div class="email-wrapper">
            <!-- Header -->
            <div class="header">
                <div class="logo">Revix<span class="logo-accent">.</span></div>
                <div class="header-subtitle">SERVICIO TÉCNICO ESPECIALIZADO</div>
            </div>
            
            <!-- Status Banner -->
            <div class="status-banner {config['banner_class']}">
                <div class="status-icon">{config['icon']}</div>
                <div class="status-title">{config['title']}</div>
                <div class="status-subtitle">{config['subtitle']}</div>
            </div>
            
            <!-- Content -->
            <div class="content">
                <p class="greeting">Hola <strong>{nombre_cliente}</strong>,</p>
                <p class="message-text">{config['message']}</p>
                
                <!-- Info Card -->
                <div class="info-card">
                    <div class="info-row">
                        <span class="info-label">📱 Dispositivo</span>
                        <span class="info-value">{dispositivo.get('marca', '')} {dispositivo.get('modelo', 'N/A')}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">🔢 Número de Orden</span>
                        <span class="info-value">{orden.get('numero_orden', 'N/A')}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">📋 Estado Actual</span>
                        <span class="info-value">{estado.replace('_', ' ').title()}</span>
                    </div>
                    {fecha_estimada_html}
                </div>
                
                {tracking_html}
                
                <!-- CTA Button -->
                <div class="cta-section">
                    <a href="{link}" class="cta-button">
                        🔍 Ver Estado de mi Reparación
                    </a>
                    <div class="access-code">
                        Código de acceso: <strong>{token}</strong>
                    </div>
                    <p style="margin-top:10px;font-size:12px;color:#94a3b8;">
                        También puedes consultar tu reparación en <strong>revix.es/consulta</strong> usando tu código y el teléfono con el que hiciste la orden.
                    </p>
                </div>
                
                <div class="divider"></div>
                
                <!-- Progress Timeline (simplificado) -->
                <h3 style="font-size: 14px; color: #64748b; margin-bottom: 16px; font-weight: 600;">
                    📊 Progreso de tu reparación
                </h3>
                <div class="timeline">
                    {timeline_html}
                </div>
            </div>
            
            <!-- Footer -->
            <div class="footer">
                <p class="footer-text">
                    ¿Tienes alguna pregunta? Estamos aquí para ayudarte.
                </p>
                <div class="footer-links">
                    <a href="https://revix.es/contacto">Contacto</a>
                    <a href="https://revix.es/consulta">Portal de Seguimiento</a>
                    <a href="https://revix.es/garantia">Garantía</a>
                </div>
                <p class="footer-copyright">
                    © 2025 Revix. Todos los derechos reservados.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


# Mantener compatibilidad con función anterior
def generate_order_email_html(orden: dict, cliente: dict, status_message: str = None) -> str:
    """Función legacy - redirige a la nueva función moderna"""
    estado = orden.get('estado', 'pendiente_recibir')
    return generate_modern_email_html(orden, cliente, email_type=estado if estado in ESTADOS_NOTIFICAR_AUTO else 'created')


async def send_order_notification(orden: dict, cliente: dict, notification_type: str = "created"):
    """
    Envía notificaciones al cliente sobre su orden.
    Respeta los flags enabled y demo_mode de email_config.
    Usa el nuevo servicio SMTP mejorado.
    """
    results = {"sms": None, "email": None}

    # Cargar configuración de notificaciones desde DB
    try:
        email_cfg_doc = await cfg.db.configuracion.find_one({"tipo": "email_config"}, {"_id": 0})
        email_cfg = email_cfg_doc.get("datos", {}) if email_cfg_doc else {}
    except Exception:
        email_cfg = {}

    # Verificar si las notificaciones están habilitadas
    if email_cfg.get("enabled") is False:
        logger.info(f"Notificaciones desactivadas — email no enviado para orden {orden.get('numero_orden')}")
        return results

    token = orden.get('token_seguimiento', '')
    estado = orden.get('estado', 'pendiente_recibir')
    orden_id = orden.get('id', '')
    numero_orden = orden.get('numero_orden', '')
    auth_code = orden.get('codigo_recogida_salida') or token

    # Determinar destinatario (demo_mode redirige todo a demo_email)
    demo_mode = email_cfg.get("demo_mode", False)
    demo_email = email_cfg.get("demo_email", "")
    destinatario_email = demo_email if (demo_mode and demo_email) else cliente.get('email', '')

    if not destinatario_email:
        logger.warning(f"Sin email de destino para orden {numero_orden}")
        return results

    # Enviar SMS si está habilitado
    sms_enabled = email_cfg.get("sms_enabled", True)
    link = f"https://revix.es/consulta?codigo={token}"
    
    if notification_type == "created":
        sms_message = f"Revix: Orden {numero_orden} registrada. Sigue tu reparación: {link}"
    elif notification_type == "fecha_estimada":
        fecha = orden.get('fecha_estimada_entrega', 'Próximamente')
        sms_message = f"Revix: Tu reparación estará lista aproximadamente el {fecha}. Sigue tu orden: {link}"
    else:
        emoji = STATUS_EMOJIS.get(estado, '')
        status_msg = STATUS_MESSAGES.get(estado, f'Estado: {estado}')
        sms_message = f"Revix {emoji}: {status_msg} Orden: {numero_orden}. Ver estado: {link}"
        if estado == 'enviado' and orden.get('codigo_recogida_salida'):
            sms_message += f" Seguimiento envío: {orden['codigo_recogida_salida']}"

    if sms_enabled and cliente.get('telefono') and not demo_mode:
        results["sms"] = await send_sms(cliente['telefono'], sms_message)

    # Enviar email usando el nuevo servicio mejorado
    try:
        if notification_type == "created":
            # Orden nueva - usar template moderno
            html_content = generate_modern_email_html(orden, cliente, email_type='created')
            email_subject = f"Nueva Orden de Reparación - {numero_orden}"
            email_result = await send_email(destinatario_email, email_subject, html_content)
            results["email"] = email_result
            
        elif notification_type == "fecha_estimada":
            html_content = generate_modern_email_html(orden, cliente, email_type='fecha_estimada')
            email_subject = f"Fecha de Entrega Estimada - {numero_orden}"
            email_result = await send_email(destinatario_email, email_subject, html_content)
            results["email"] = email_result
            
        else:
            # Cambio de estado - verificar si debemos notificar
            estados_activos = email_cfg.get("estados_activos", {})
            if estado not in ESTADOS_NOTIFICAR_AUTO:
                logger.info(f"Estado {estado} no requiere notificación automática")
                return results
                
            if estados_activos and estados_activos.get(estado) is False:
                logger.info(f"Notificación para estado '{estado}' desactivada por configuración")
                return results

            # Usar la nueva función de notificación de cambio de estado
            email_success = await notificar_cambio_estado(
                to=destinatario_email,
                orden_numero=numero_orden,
                auth_code=auth_code,
                nuevo_estado=estado,
                orden_id=orden_id
            )
            results["email"] = {"success": email_success, "type": "smtp_mejorado"}

        if demo_mode:
            logger.info(f"MODO DEMO: Email redirigido de {cliente.get('email', 'N/A')} → {demo_email}")

    except Exception as e:
        logger.error(f"Error enviando notificación para orden {numero_orden}: {e}")
        results["email"] = {"success": False, "error": str(e)}

    logger.info(f"Notificación para orden {numero_orden}: tipo={notification_type}, estado={estado}, demo={demo_mode}")
    return results


async def notificar_cambio_estado_automatico(orden: dict, cliente: dict, estado_anterior: str, estado_nuevo: str):
    """
    Función para notificaciones automáticas en cambios de estado.
    Solo notifica si el nuevo estado está en ESTADOS_NOTIFICAR_AUTO.
    """
    if estado_nuevo not in ESTADOS_NOTIFICAR_AUTO:
        return {"notificado": False, "razon": f"Estado {estado_nuevo} no requiere notificación"}
    
    results = await send_order_notification(orden, cliente, "status_change")
    return {
        "notificado": True,
        "estado_anterior": estado_anterior,
        "estado_nuevo": estado_nuevo,
        "results": results
    }


"""
Script to generate PDF manual from HTML using reportlab
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.colors import HexColor, black, white, gray
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus.flowables import HRFlowable
import os

# Colors
PRIMARY_BLUE = HexColor('#1e3a5f')
ACCENT_BLUE = HexColor('#2563eb')
LIGHT_BLUE = HexColor('#eff6ff')
SUCCESS_GREEN = HexColor('#22c55e')
WARNING_YELLOW = HexColor('#f59e0b')
LIGHT_GRAY = HexColor('#f8fafc')
BORDER_GRAY = HexColor('#e2e8f0')

def create_manual_pdf():
    # Create document
    doc = SimpleDocTemplate(
        '/app/frontend/public/MANUAL_NEXORA.pdf',
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    styles.add(ParagraphStyle(
        name='MainTitle',
        fontSize=28,
        textColor=PRIMARY_BLUE,
        alignment=TA_CENTER,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='Subtitle',
        fontSize=14,
        textColor=gray,
        alignment=TA_CENTER,
        spaceAfter=30
    ))
    
    styles.add(ParagraphStyle(
        name='SectionTitle',
        fontSize=18,
        textColor=PRIMARY_BLUE,
        spaceBefore=20,
        spaceAfter=10,
        fontName='Helvetica-Bold',
        borderColor=ACCENT_BLUE,
        borderWidth=2,
        borderPadding=5
    ))
    
    styles.add(ParagraphStyle(
        name='SubsectionTitle',
        fontSize=14,
        textColor=PRIMARY_BLUE,
        spaceBefore=15,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='CustomBody',
        fontSize=10,
        textColor=black,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
        leading=14
    ))
    
    styles.add(ParagraphStyle(
        name='BulletText',
        fontSize=10,
        textColor=black,
        leftIndent=20,
        spaceAfter=4,
        bulletIndent=10
    ))
    
    styles.add(ParagraphStyle(
        name='InfoBox',
        fontSize=10,
        textColor=PRIMARY_BLUE,
        backColor=LIGHT_BLUE,
        borderColor=ACCENT_BLUE,
        borderWidth=1,
        borderPadding=10,
        spaceAfter=10
    ))
    
    # Build story
    story = []
    
    # ===== COVER PAGE =====
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph("📘 NEXORA", styles['MainTitle']))
    story.append(Paragraph("Manual de Usuario", styles['MainTitle']))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Sistema CRM/ERP para Servicios Técnicos de Telefonía Móvil", styles['Subtitle']))
    story.append(Spacer(1, 2*cm))
    story.append(HRFlowable(width="50%", thickness=2, color=ACCENT_BLUE))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Versión 2.0 - Febrero 2026", styles['Subtitle']))
    story.append(PageBreak())
    
    # ===== TABLE OF CONTENTS =====
    story.append(Paragraph("📑 Índice de Contenidos", styles['SectionTitle']))
    story.append(Spacer(1, 0.5*cm))
    
    toc_data = [
        ['1.', 'Introducción', '3'],
        ['2.', 'Acceso al Sistema', '4'],
        ['3.', 'Panel de Control (Dashboard)', '5'],
        ['4.', 'Órdenes de Trabajo', '6'],
        ['5.', 'Gestión de Clientes', '8'],
        ['6.', 'Inventario', '9'],
        ['7.', 'Integración Insurama/Sumbroker', '10'],
        ['8.', 'Pre-Registros', '12'],
        ['9.', 'Notificaciones', '13'],
        ['10.', 'Calendario', '14'],
        ['11.', 'Flujos Automáticos', '15'],
        ['12.', 'Guía para Técnicos', '16'],
        ['13.', 'Preguntas Frecuentes', '18'],
    ]
    
    toc_table = Table(toc_data, colWidths=[1*cm, 12*cm, 2*cm])
    toc_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), ACCENT_BLUE),
        ('TEXTCOLOR', (2, 0), (2, -1), gray),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(toc_table)
    story.append(PageBreak())
    
    # ===== SECTION 1: INTRODUCTION =====
    story.append(Paragraph("1. Introducción", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("¿Qué es NEXORA?", styles['SubsectionTitle']))
    story.append(Paragraph(
        "NEXORA es un sistema CRM/ERP diseñado específicamente para talleres de reparación de "
        "dispositivos móviles. Permite gestionar de forma integral todas las operaciones del negocio: "
        "órdenes de trabajo, clientes, inventario, integración con aseguradoras y comunicaciones automáticas.",
        styles['CustomBody']
    ))
    
    story.append(Paragraph("Características Principales", styles['SubsectionTitle']))
    
    features_data = [
        ['Característica', 'Descripción'],
        ['🔄 Automatización', 'Polling automático de Insurama, notificaciones en tiempo real'],
        ['🤖 Asistente IA', 'Diagnósticos y sugerencias de reparación con Gemini'],
        ['📱 Multi-dispositivo', 'Acceso desde ordenador, tablet o móvil'],
        ['👥 Multi-usuario', 'Roles de Admin, Técnico y Master'],
        ['🔔 Tiempo real', 'Notificaciones instantáneas vía WebSocket'],
    ]
    
    features_table = Table(features_data, colWidths=[4*cm, 11*cm])
    features_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(features_table)
    story.append(PageBreak())
    
    # ===== SECTION 2: ACCESS =====
    story.append(Paragraph("2. Acceso al Sistema", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("Pantalla de Login", styles['SubsectionTitle']))
    story.append(Paragraph("Para acceder al sistema:", styles['CustomBody']))
    story.append(Paragraph("1. Abrir el navegador y acceder a la URL del sistema", styles['BulletText']))
    story.append(Paragraph("2. Introducir Email y Contraseña", styles['BulletText']))
    story.append(Paragraph("3. Pulsar 'Iniciar Sesión'", styles['BulletText']))
    
    story.append(Paragraph("Roles de Usuario", styles['SubsectionTitle']))
    
    roles_data = [
        ['Rol', 'Permisos'],
        ['Master', 'Acceso total: configuración, usuarios, integraciones'],
        ['Admin', 'Gestión completa de órdenes, clientes, inventario'],
        ['Técnico', 'Ver órdenes asignadas, actualizar estado, añadir materiales'],
    ]
    
    roles_table = Table(roles_data, colWidths=[3*cm, 12*cm])
    roles_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (0, 1), HexColor('#fee2e2')),
        ('BACKGROUND', (0, 2), (0, 2), HexColor('#dbeafe')),
        ('BACKGROUND', (0, 3), (0, 3), HexColor('#dcfce7')),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(roles_table)
    story.append(PageBreak())
    
    # ===== SECTION 3: DASHBOARD =====
    story.append(Paragraph("3. Panel de Control (Dashboard)", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph(
        "El Dashboard muestra un resumen del estado del taller con indicadores clave de rendimiento.",
        styles['CustomBody']
    ))
    
    story.append(Paragraph("Indicadores Principales", styles['SubsectionTitle']))
    
    indicators_data = [
        ['Indicador', 'Significado'],
        ['📋 Órdenes', 'Total de órdenes activas'],
        ['👥 Clientes', 'Número de clientes registrados'],
        ['📦 Repuestos', 'Productos en inventario'],
        ['🔔 Notificaciones', 'Alertas pendientes de leer'],
        ['🛒 Compras Pend.', 'Pedidos de material pendientes'],
    ]
    
    ind_table = Table(indicators_data, colWidths=[4*cm, 11*cm])
    ind_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(ind_table)
    
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "💡 TIP: Usa el escáner rápido en la parte superior para abrir órdenes escaneando su código QR.",
        styles['CustomBody']
    ))
    story.append(PageBreak())
    
    # ===== SECTION 4: ORDERS =====
    story.append(Paragraph("4. Órdenes de Trabajo", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("Estados de una Orden", styles['SubsectionTitle']))
    story.append(Paragraph(
        "Pendiente Recibir → En Diagnóstico → Presupuesto Enviado → "
        "Presupuesto Aceptado → En Reparación → Reparado → Entregado",
        styles['CustomBody']
    ))
    
    story.append(Paragraph("Estados Especiales:", styles['SubsectionTitle']))
    story.append(Paragraph("• Presupuesto Rechazado: Cliente no acepta el precio", styles['BulletText']))
    story.append(Paragraph("• Irreparable: No se puede reparar", styles['BulletText']))
    story.append(Paragraph("• Cancelado: Orden anulada", styles['BulletText']))
    story.append(Paragraph("• En Garantía: Reparación bajo garantía anterior", styles['BulletText']))
    
    story.append(Paragraph("Crear Nueva Orden", styles['SubsectionTitle']))
    story.append(Paragraph("1. Pulsar '+ Nueva Orden'", styles['BulletText']))
    story.append(Paragraph("2. Buscar o crear cliente", styles['BulletText']))
    story.append(Paragraph("3. Rellenar datos del dispositivo (marca, modelo, IMEI)", styles['BulletText']))
    story.append(Paragraph("4. Describir el problema", styles['BulletText']))
    story.append(Paragraph("5. Seleccionar tipo de servicio", styles['BulletText']))
    story.append(Paragraph("6. Pulsar 'Crear Orden'", styles['BulletText']))
    
    story.append(Paragraph("Pestañas de la Ficha de Orden", styles['SubsectionTitle']))
    
    tabs_data = [
        ['Pestaña', 'Contenido'],
        ['📄 Información', 'Datos del cliente y dispositivo'],
        ['🔄 Estado', 'Cambiar estado de la orden'],
        ['🔧 Materiales', 'Repuestos utilizados'],
        ['📷 Evidencias', 'Fotos del dispositivo'],
        ['💬 Mensajes', 'Comunicación interna'],
        ['📜 Historial', 'Registro de cambios'],
    ]
    
    tabs_table = Table(tabs_data, colWidths=[4*cm, 11*cm])
    tabs_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(tabs_table)
    story.append(PageBreak())
    
    # ===== SECTION 5: CLIENTS =====
    story.append(Paragraph("5. Gestión de Clientes", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("Lista de Clientes", styles['SubsectionTitle']))
    story.append(Paragraph(
        "Muestra todos los clientes registrados con su información de contacto y historial de reparaciones.",
        styles['CustomBody']
    ))
    
    clients_data = [
        ['Campo', 'Descripción'],
        ['Nombre completo', 'Nombre y apellidos del cliente'],
        ['DNI/NIF', 'Documento de identificación'],
        ['Teléfono', 'Para notificaciones SMS'],
        ['Email', 'Para notificaciones por correo'],
        ['Dirección', 'Dirección completa de envío'],
    ]
    
    clients_table = Table(clients_data, colWidths=[4*cm, 11*cm])
    clients_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(clients_table)
    
    story.append(Paragraph("Crear Nuevo Cliente", styles['SubsectionTitle']))
    story.append(Paragraph("1. Pulsar '+ Nuevo Cliente'", styles['BulletText']))
    story.append(Paragraph("2. Rellenar nombre y apellidos", styles['BulletText']))
    story.append(Paragraph("3. Introducir DNI/NIF", styles['BulletText']))
    story.append(Paragraph("4. Añadir teléfono y email", styles['BulletText']))
    story.append(Paragraph("5. Completar dirección", styles['BulletText']))
    story.append(Paragraph("6. Pulsar 'Guardar'", styles['BulletText']))
    
    story.append(Paragraph("Ficha de Cliente", styles['SubsectionTitle']))
    story.append(Paragraph("• Datos personales: Toda la información de contacto", styles['BulletText']))
    story.append(Paragraph("• Historial de órdenes: Todas sus reparaciones anteriores", styles['BulletText']))
    story.append(Paragraph("• Métricas: Total gastado, número de órdenes", styles['BulletText']))
    story.append(Paragraph("• Notas: Observaciones especiales", styles['BulletText']))
    story.append(PageBreak())
    
    # ===== SECTION 6: INVENTORY =====
    story.append(Paragraph("6. Inventario", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("Gestión de Repuestos", styles['SubsectionTitle']))
    story.append(Paragraph(
        "El inventario permite controlar todo el stock de repuestos del taller con alertas automáticas de stock bajo.",
        styles['CustomBody']
    ))
    
    story.append(Paragraph("Añadir Nuevo Repuesto", styles['SubsectionTitle']))
    story.append(Paragraph("1. Pulsar '+ Nuevo Repuesto'", styles['BulletText']))
    story.append(Paragraph("2. Introducir nombre del producto", styles['BulletText']))
    story.append(Paragraph("3. Seleccionar categoría", styles['BulletText']))
    story.append(Paragraph("4. El SKU se genera automáticamente", styles['BulletText']))
    story.append(Paragraph("5. Añadir precios y stock inicial", styles['BulletText']))
    story.append(Paragraph("6. Pulsar 'Guardar'", styles['BulletText']))
    
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "📝 SKU Automático: El código SKU se genera basándose en la categoría y nombre. "
        "Ejemplo: PANT-IPHO-PRO-A1B2",
        styles['CustomBody']
    ))
    
    story.append(Paragraph("Categorías de Repuestos", styles['SubsectionTitle']))
    story.append(Paragraph("• Pantallas: LCDs, OLEDs, táctiles", styles['BulletText']))
    story.append(Paragraph("• Baterías: Originales y compatibles", styles['BulletText']))
    story.append(Paragraph("• Conectores: Puertos de carga, flex", styles['BulletText']))
    story.append(Paragraph("• Cámaras: Frontales y traseras", styles['BulletText']))
    story.append(Paragraph("• Altavoces: Auriculares y altavoces", styles['BulletText']))
    story.append(Paragraph("• Carcasas: Tapas traseras, marcos", styles['BulletText']))
    story.append(PageBreak())
    
    # ===== SECTION 7: INSURAMA =====
    story.append(Paragraph("7. Integración Insurama/Sumbroker", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("¿Qué es Insurama?", styles['SubsectionTitle']))
    story.append(Paragraph(
        "Insurama es el portal de gestión de siniestros de seguros de móviles. NEXORA se integra "
        "directamente con este portal para automatizar todo el proceso de gestión de siniestros.",
        styles['CustomBody']
    ))
    
    story.append(Paragraph("Funcionalidades de la Integración:", styles['SubsectionTitle']))
    story.append(Paragraph("✅ Recibir automáticamente nuevos siniestros", styles['BulletText']))
    story.append(Paragraph("✅ Enviar presupuestos completos al portal", styles['BulletText']))
    story.append(Paragraph("✅ Sincronizar estados de reparación", styles['BulletText']))
    story.append(Paragraph("✅ Gestionar fotos y evidencias", styles['BulletText']))
    
    story.append(Paragraph("Campos Obligatorios del Presupuesto", styles['SubsectionTitle']))
    
    budget_data = [
        ['Campo', 'Descripción'],
        ['Precio (€)', 'Coste total de la reparación'],
        ['Disponibilidad', 'Inmediata, 24h, 48h, 7 días, Sin stock'],
        ['Tiempo en Horas', 'Horas estimadas de trabajo'],
        ['Tipo de Recambio', 'Original, Compatible, Reacondicionado'],
        ['Tipo de Garantía', 'Fabricante, Taller, Sin garantía'],
        ['Descripción', 'Detalle de la reparación a realizar'],
    ]
    
    budget_table = Table(budget_data, colWidths=[4*cm, 11*cm])
    budget_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(budget_table)
    story.append(PageBreak())
    
    # ===== SECTION 8: PRE-REGISTROS =====
    story.append(Paragraph("8. Pre-Registros", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("¿Qué son los Pre-Registros?", styles['SubsectionTitle']))
    story.append(Paragraph(
        "Los Pre-Registros son siniestros de Insurama que aún no tienen orden de trabajo creada. "
        "Representan trabajos potenciales que el sistema ha detectado automáticamente.",
        styles['CustomBody']
    ))
    
    story.append(Paragraph("Acciones Disponibles:", styles['SubsectionTitle']))
    story.append(Paragraph("• Enviar Presupuesto: Ir a Insurama para enviar precio", styles['BulletText']))
    story.append(Paragraph("• Crear Orden: Generar orden de trabajo directamente", styles['BulletText']))
    story.append(Paragraph("• Ver Orden: Abrir orden existente (si ya se creó)", styles['BulletText']))
    
    story.append(Paragraph("Estados de Pre-Registro:", styles['SubsectionTitle']))
    story.append(Paragraph("• Pendiente Presupuesto - Sin precio enviado", styles['BulletText']))
    story.append(Paragraph("• Presupuesto Enviado - Esperando respuesta", styles['BulletText']))
    story.append(Paragraph("• Aceptado - Cliente aprobó → Crear orden", styles['BulletText']))
    story.append(Paragraph("• Rechazado - Cliente no aceptó", styles['BulletText']))
    story.append(Paragraph("• Orden Creada - Ya tiene orden de trabajo", styles['BulletText']))
    story.append(Paragraph("• Cancelado - Siniestro anulado", styles['BulletText']))
    
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "🗑️ Limpieza Automática: Los pre-registros cancelados se eliminan automáticamente después de 7 días.",
        styles['CustomBody']
    ))
    story.append(PageBreak())
    
    # ===== SECTION 9: NOTIFICACIONES =====
    story.append(Paragraph("9. Notificaciones", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("Centro de Notificaciones", styles['SubsectionTitle']))
    story.append(Paragraph(
        "Muestra todas las alertas del sistema en tiempo real, permitiendo gestión individual o masiva.",
        styles['CustomBody']
    ))
    
    story.append(Paragraph("Tipos de Notificaciones:", styles['SubsectionTitle']))
    notif_types = [
        ['Tipo', 'Significado'],
        ['Presupuesto Aceptado', 'Cliente aprobó, crear orden'],
        ['Presupuesto Rechazado', 'Cliente no aceptó'],
        ['Nuevo Siniestro', 'Llegó trabajo de Insurama'],
        ['Material Pendiente', 'Técnico solicita repuesto'],
        ['Orden Completada', 'Reparación terminada'],
    ]
    
    notif_types_table = Table(notif_types, colWidths=[5*cm, 10*cm])
    notif_types_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(notif_types_table)
    
    story.append(Paragraph("Selección Múltiple:", styles['SubsectionTitle']))
    story.append(Paragraph("1. Pulsar 'Seleccionar'", styles['BulletText']))
    story.append(Paragraph("2. Marcar las notificaciones con checkboxes", styles['BulletText']))
    story.append(Paragraph("3. Usar 'Seleccionar todas' o 'Deseleccionar'", styles['BulletText']))
    story.append(Paragraph("4. Pulsar 'Eliminar (N)' o 'Marcar leídas'", styles['BulletText']))
    story.append(PageBreak())
    
    # ===== SECTION 10: CALENDARIO =====
    story.append(Paragraph("10. Calendario", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("Vista de Calendario", styles['SubsectionTitle']))
    story.append(Paragraph(
        "Muestra una vista mensual con todos los eventos y asignaciones del taller.",
        styles['CustomBody']
    ))
    
    story.append(Paragraph("Tipos de Eventos:", styles['SubsectionTitle']))
    eventos_data = [
        ['Color', 'Tipo de Evento'],
        ['Verde', 'Orden Asignada'],
        ['Azul', 'Llegada de Dispositivo'],
        ['Naranja', 'Llegada de Repuesto'],
        ['Morado', 'Reunión'],
        ['Gris', 'Ausencia'],
        ['Rojo', 'Vacaciones'],
    ]
    
    eventos_table = Table(eventos_data, colWidths=[4*cm, 11*cm])
    eventos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(eventos_table)
    
    story.append(Paragraph("Crear Evento:", styles['SubsectionTitle']))
    story.append(Paragraph("1. Pulsar '+ Nuevo Evento'", styles['BulletText']))
    story.append(Paragraph("2. Seleccionar tipo de evento", styles['BulletText']))
    story.append(Paragraph("3. Elegir fecha y hora", styles['BulletText']))
    story.append(Paragraph("4. Añadir descripción", styles['BulletText']))
    story.append(Paragraph("5. Asignar técnico (si aplica)", styles['BulletText']))
    story.append(Paragraph("6. Pulsar 'Guardar'", styles['BulletText']))
    story.append(PageBreak())
    
    # ===== SECTION 11: AUTOMATIC FLOWS =====
    story.append(Paragraph("11. Flujos Automáticos", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("🔄 Polling de Insurama", styles['SubsectionTitle']))
    story.append(Paragraph(
        "Cada 5 minutos el sistema consulta automáticamente el portal de Sumbroker buscando "
        "nuevos siniestros asignados, presupuestos aceptados/rechazados y cambios de estado.",
        styles['CustomBody']
    ))
    
    story.append(Paragraph("Flujo Automático de Insurama:", styles['SubsectionTitle']))
    story.append(Paragraph("1. Sumbroker envía nuevo siniestro", styles['BulletText']))
    story.append(Paragraph("2. NEXORA detecta automáticamente (polling cada 5 min)", styles['BulletText']))
    story.append(Paragraph("3. Se crea Pre-Registro en el sistema", styles['BulletText']))
    story.append(Paragraph("4. Notificación al administrador", styles['BulletText']))
    story.append(Paragraph("5. Admin envía presupuesto", styles['BulletText']))
    story.append(Paragraph("6. Cliente acepta/rechaza", styles['BulletText']))
    story.append(Paragraph("7. Si acepta → Se crea Orden de Trabajo automáticamente", styles['BulletText']))
    
    story.append(Paragraph("📧 Notificaciones Automáticas", styles['SubsectionTitle']))
    
    notif_data = [
        ['Evento', 'Email', 'SMS', 'App'],
        ['Nueva orden creada', '✅', '❌', '✅'],
        ['Presupuesto enviado', '✅', '✅', '✅'],
        ['Presupuesto aceptado', '✅', '❌', '✅'],
        ['Reparación completada', '✅', '✅', '✅'],
        ['Stock bajo', '❌', '❌', '✅'],
    ]
    
    notif_table = Table(notif_data, colWidths=[6*cm, 3*cm, 3*cm, 3*cm])
    notif_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(notif_table)
    
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("🗑️ Limpieza Automática", styles['SubsectionTitle']))
    story.append(Paragraph("• Pre-registros cancelados: Se eliminan tras 7 días", styles['BulletText']))
    story.append(Paragraph("• Notificaciones antiguas: Según configuración del sistema", styles['BulletText']))
    story.append(PageBreak())
    
    # ===== SECTION 12: TECHNICIAN GUIDE =====
    story.append(Paragraph("12. Guía para Técnicos", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("✅ Validar Materiales Usados", styles['SubsectionTitle']))
    story.append(Paragraph(
        "Sistema de 'picking' para confirmar que los materiales asignados realmente fueron utilizados:",
        styles['CustomBody']
    ))
    
    story.append(Paragraph("1. Ir a la pestaña 'Materiales' de la orden", styles['BulletText']))
    story.append(Paragraph("2. Pulsar 'Validar (N pendientes)'", styles['BulletText']))
    story.append(Paragraph("3. Escanear el SKU o código de barras de cada material", styles['BulletText']))
    story.append(Paragraph("4. El sistema confirma automáticamente al detectar el código", styles['BulletText']))
    story.append(Paragraph("5. Se registra quién validó y cuándo", styles['BulletText']))
    
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("Progreso visible:", styles['SubsectionTitle']))
    story.append(Paragraph("• Barra de progreso: X/Y materiales validados", styles['BulletText']))
    story.append(Paragraph("• Verde = Material validado", styles['BulletText']))
    story.append(Paragraph("• Gris = Pendiente de validar", styles['BulletText']))
    
    story.append(Paragraph("Añadir Materiales", styles['SubsectionTitle']))
    story.append(Paragraph("Desde Inventario:", styles['CustomBody']))
    story.append(Paragraph("1. Pulsar 'Existente'", styles['BulletText']))
    story.append(Paragraph("2. Buscar el repuesto", styles['BulletText']))
    story.append(Paragraph("3. Confirmar (la orden se bloquea hasta aprobación del admin)", styles['BulletText']))
    
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("Material No Registrado:", styles['CustomBody']))
    story.append(Paragraph("1. Pulsar 'Nuevo'", styles['BulletText']))
    story.append(Paragraph("2. Escribir nombre del material", styles['BulletText']))
    story.append(Paragraph("3. Indicar cantidad", styles['BulletText']))
    story.append(Paragraph("4. El admin asignará los precios", styles['BulletText']))
    
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "⚠️ IMPORTANTE: Cuando un técnico añade material, la orden queda BLOQUEADA hasta que "
        "el administrador lo apruebe.",
        styles['CustomBody']
    ))
    story.append(PageBreak())
    
    # ===== FOOTER PAGE =====
    story.append(Spacer(1, 5*cm))
    story.append(Paragraph("📞 Soporte", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Para asistencia técnica:", styles['CustomBody']))
    story.append(Paragraph("📧 Email: soporte@nexora.es", styles['BulletText']))
    story.append(Paragraph("📱 Teléfono: +34 XXX XXX XXX", styles['BulletText']))
    story.append(Paragraph("💬 Chat interno: Botón azul en esquina inferior derecha", styles['BulletText']))
    
    story.append(Spacer(1, 3*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("© 2026 NEXORA. Todos los derechos reservados.", styles['Subtitle']))
    
    # Build PDF
    doc.build(story)
    print("PDF generated successfully!")

if __name__ == '__main__':
    create_manual_pdf()

"""
Core event processor: State machine, consolidation window, orchestration.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from config import db, logger
from models import (
    TipoEventoEmail, EstadoPreRegistro, SeveridadNotificacion,
    PreRegistro, NotificacionExterna, EventoPendiente, AgentLog
)
from agent.classifier import (
    extract_codigo_siniestro, classify_email, generate_idempotency_key
)
from agent.email_client import EmailMessage

CONSOLIDATION_WINDOW_SECONDS = 300  # 5 minutes


async def log_agent(accion: str, resultado: str, nivel: str = "info",
                    codigo: str = None, email_id: str = None,
                    error: str = None, detalles: dict = None):
    entry = AgentLog(
        accion=accion, resultado=resultado, nivel=nivel,
        codigo_siniestro=codigo, email_id=email_id,
        error=error, detalles=detalles
    )
    doc = entry.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.agent_logs.insert_one(doc)


async def check_idempotency(key: str) -> bool:
    existing = await db.agent_idempotency.find_one({"key": key})
    return existing is not None


async def mark_idempotent(key: str, event_id: str):
    await db.agent_idempotency.update_one(
        {"key": key},
        {"$set": {"key": key, "event_id": event_id,
                  "created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )


async def process_email(msg: EmailMessage, code_pattern: Optional[str] = None) -> dict:
    """Main entry point: classify and route an email event."""
    subject = msg.subject
    body = msg.body

    # 1. Extract codigo_siniestro
    codigo = extract_codigo_siniestro(f"{subject} {body}", code_pattern)
    if not codigo:
        await log_agent("email_sin_codigo", "ignorado", "warning",
                        email_id=msg.message_id,
                        detalles={"subject": subject[:200]})
        return {"action": "ignored", "reason": "no_codigo_siniestro"}

    # 2. Classify event
    tipo_evento, severidad = classify_email(subject, body)

    # 3. Check idempotency
    idem_key = generate_idempotency_key(codigo, tipo_evento.value, msg.date)
    if await check_idempotency(idem_key):
        await log_agent("email_duplicado", "ignorado", "info",
                        codigo=codigo, email_id=msg.message_id)
        return {"action": "ignored", "reason": "duplicate", "key": idem_key}

    # 4. Mark as processed
    await mark_idempotent(idem_key, msg.message_id)

    # 5. Route by event type
    if tipo_evento == TipoEventoEmail.NUEVO_SINIESTRO:
        return await handle_nuevo_siniestro(msg, codigo)

    elif tipo_evento in (TipoEventoEmail.PRESUPUESTO_ACEPTADO,
                         TipoEventoEmail.PRESUPUESTO_RECHAZADO):
        return await handle_decision_presupuesto(msg, codigo, tipo_evento)

    elif tipo_evento != TipoEventoEmail.DESCONOCIDO:
        return await handle_post_aceptacion(msg, codigo, tipo_evento, severidad)

    else:
        await log_agent("email_no_clasificado", "pendiente_revision", "warning",
                        codigo=codigo, email_id=msg.message_id,
                        detalles={"subject": subject[:200]})
        return {"action": "unclassified", "codigo": codigo}


async def handle_nuevo_siniestro(msg: EmailMessage, codigo: str) -> dict:
    """Create a PRE-RECORD (not a work order)."""
    existing = await db.pre_registros.find_one(
        {"codigo_siniestro": codigo}, {"_id": 0}
    )
    if existing:
        await log_agent("pre_registro_existente", "ignorado", "info",
                        codigo=codigo, email_id=msg.message_id)
        return {"action": "ignored", "reason": "pre_registro_exists",
                "pre_registro_id": existing['id']}

    pre_reg = PreRegistro(
        codigo_siniestro=codigo,
        email_message_id=msg.message_id,
        email_subject=msg.subject,
        email_body=msg.body[:5000] if msg.body else None,
        email_from=msg.from_addr,
        email_date=msg.date,
        historial=[{
            "evento": "creado",
            "fecha": datetime.now(timezone.utc).isoformat(),
            "detalle": "Pre-registro creado desde email"
        }]
    )
    doc = pre_reg.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.pre_registros.insert_one(doc)

    # Internal notification for admins
    from models import Notificacion
    notif = Notificacion(
        tipo="nuevo_pre_registro",
        mensaje=f"Nuevo siniestro {codigo}: {msg.subject[:100]}",
        orden_id=None
    )
    notif_doc = notif.model_dump()
    notif_doc['created_at'] = notif_doc['created_at'].isoformat()
    notif_doc['codigo_siniestro'] = codigo
    notif_doc['pre_registro_id'] = pre_reg.id
    await db.notificaciones.insert_one(notif_doc)

    await log_agent("pre_registro_creado", "ok", "info",
                    codigo=codigo, email_id=msg.message_id,
                    detalles={"pre_registro_id": pre_reg.id})

    return {"action": "pre_registro_created", "id": pre_reg.id, "codigo": codigo}


async def handle_decision_presupuesto(msg: EmailMessage, codigo: str,
                                       tipo: TipoEventoEmail) -> dict:
    """
    Queue accept/reject into consolidation window.
    Does NOT act immediately.
    """
    procesar_en = datetime.now(timezone.utc) + timedelta(seconds=CONSOLIDATION_WINDOW_SECONDS)

    evento = EventoPendiente(
        codigo_siniestro=codigo,
        tipo_evento=tipo,
        email_message_id=msg.message_id,
        email_subject=msg.subject,
        email_body=msg.body[:5000] if msg.body else None,
        email_from=msg.from_addr,
        email_date=msg.date,
        procesar_despues_de=procesar_en
    )
    doc = evento.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['procesar_despues_de'] = doc['procesar_despues_de'].isoformat()
    await db.agent_eventos_pendientes.insert_one(doc)

    await log_agent(
        "decision_en_ventana", "encolado", "info",
        codigo=codigo, email_id=msg.message_id,
        detalles={"tipo": tipo.value,
                  "procesar_despues_de": procesar_en.isoformat()}
    )
    return {"action": "queued_for_consolidation", "tipo": tipo.value,
            "process_after": procesar_en.isoformat(), "codigo": codigo}


async def process_consolidated_events():
    """
    Called periodically. Processes events whose consolidation window has expired.
    For each codigo_siniestro with pending events, takes the LAST one.
    """
    now = datetime.now(timezone.utc)
    # Find all unprocessed events past their window
    pendientes = await db.agent_eventos_pendientes.find(
        {"procesado": False, "procesar_despues_de": {"$lte": now.isoformat()}},
        {"_id": 0}
    ).to_list(500)

    if not pendientes:
        return []

    # Group by codigo_siniestro
    by_code = {}
    for ev in pendientes:
        code = ev['codigo_siniestro']
        if code not in by_code:
            by_code[code] = []
        by_code[code].append(ev)

    results = []
    for codigo, events in by_code.items():
        # Check if there are NEWER events still inside their window
        still_pending = await db.agent_eventos_pendientes.find_one({
            "codigo_siniestro": codigo,
            "procesado": False,
            "procesar_despues_de": {"$gt": now.isoformat()}
        })
        if still_pending:
            # Wait for the window to close
            continue

        # Take the LAST event by email_date (or created_at as fallback)
        events.sort(key=lambda e: e.get('email_date') or e.get('created_at', ''))
        last_event = events[-1]
        tipo = last_event['tipo_evento']

        # Mark ALL events for this code as processed
        event_ids = [e['id'] for e in events]
        await db.agent_eventos_pendientes.update_many(
            {"id": {"$in": event_ids}},
            {"$set": {"procesado": True,
                      "consolidado_en": last_event['id']}}
        )

        if tipo == TipoEventoEmail.PRESUPUESTO_ACEPTADO.value:
            result = await execute_aceptacion(codigo, last_event)
        elif tipo == TipoEventoEmail.PRESUPUESTO_RECHAZADO.value:
            result = await execute_rechazo(codigo, last_event)
        else:
            result = {"action": "unknown_consolidated_type", "tipo": tipo}

        results.append(result)

    return results


async def execute_aceptacion(codigo: str, event: dict) -> dict:
    """
    Execute acceptance: update pre-registro, scrape portal, create order.
    """
    pre_reg = await db.pre_registros.find_one(
        {"codigo_siniestro": codigo}, {"_id": 0}
    )
    if not pre_reg:
        await log_agent("aceptacion_sin_pre_registro", "error", "error",
                        codigo=codigo,
                        error="No pre-registro found for accepted quotation")
        return {"action": "error", "reason": "no_pre_registro", "codigo": codigo}

    if pre_reg.get('estado') == EstadoPreRegistro.ORDEN_CREADA.value:
        await log_agent("aceptacion_ya_procesada", "ignorado", "info", codigo=codigo)
        return {"action": "ignored", "reason": "already_processed", "codigo": codigo}

    # Update pre-registro state
    historial = pre_reg.get('historial', [])
    historial.append({
        "evento": "presupuesto_aceptado",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "detalle": f"Aceptación consolidada (email: {event.get('email_subject', '')[:100]})"
    })

    await db.pre_registros.update_one(
        {"codigo_siniestro": codigo},
        {"$set": {
            "estado": EstadoPreRegistro.ACEPTADO.value,
            "historial": historial,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    # Portal scraping placeholder (will be implemented with real credentials)
    datos_portal = await scrape_portal_data(codigo)

    if datos_portal:
        await db.pre_registros.update_one(
            {"codigo_siniestro": codigo},
            {"$set": {"datos_portal": datos_portal}}
        )

    # Create the final work order
    orden_id = await create_orden_from_pre_registro(pre_reg, datos_portal)

    if orden_id:
        historial.append({
            "evento": "orden_creada",
            "fecha": datetime.now(timezone.utc).isoformat(),
            "detalle": f"Orden {orden_id} creada"
        })
        await db.pre_registros.update_one(
            {"codigo_siniestro": codigo},
            {"$set": {
                "estado": EstadoPreRegistro.ORDEN_CREADA.value,
                "orden_id": orden_id,
                "historial": historial,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        await log_agent("orden_creada_desde_aceptacion", "ok", "info",
                        codigo=codigo,
                        detalles={"orden_id": orden_id})
        
        # NOTIFICACIÓN IMPORTANTE: Presupuesto aceptado - crear popup para admin
        orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0, "numero_orden": 1, "numero_autorizacion": 1, "dispositivo": 1, "cliente_id": 1})
        cliente = await db.clientes.find_one({"id": orden.get('cliente_id')}, {"_id": 0, "nombre": 1, "apellidos": 1}) if orden else None
        cliente_nombre = f"{cliente.get('nombre', '')} {cliente.get('apellidos', '')}".strip() if cliente else "Cliente"
        dispositivo_info = f"{orden.get('dispositivo', {}).get('marca', '')} {orden.get('dispositivo', {}).get('modelo', '')}".strip() if orden else ""
        
        await db.notificaciones.insert_one({
            "id": str(uuid.uuid4()),
            "tipo": "presupuesto_aceptado",
            "titulo": "🎉 ¡PRESUPUESTO ACEPTADO!",
            "mensaje": f"El proveedor ha aceptado el presupuesto para {codigo}. {cliente_nombre} - {dispositivo_info}",
            "orden_id": orden_id,
            "codigo_siniestro": codigo,
            "urgente": True,
            "popup": True,  # Flag para mostrar popup
            "leida": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {"action": "order_created", "orden_id": orden_id, "codigo": codigo}

    await log_agent("error_creando_orden", "error", "error", codigo=codigo,
                    error="Could not create order from pre-registro")
    return {"action": "error", "reason": "order_creation_failed", "codigo": codigo}


async def execute_rechazo(codigo: str, event: dict) -> dict:
    """Close and archive the pre-registro."""
    pre_reg = await db.pre_registros.find_one(
        {"codigo_siniestro": codigo}, {"_id": 0}
    )
    if not pre_reg:
        await log_agent("rechazo_sin_pre_registro", "warning", "warning",
                        codigo=codigo)
        return {"action": "warning", "reason": "no_pre_registro", "codigo": codigo}

    if pre_reg.get('estado') == EstadoPreRegistro.ORDEN_CREADA.value:
        await log_agent("rechazo_orden_ya_creada", "warning", "warning",
                        codigo=codigo)
        return {"action": "warning", "reason": "order_already_created", "codigo": codigo}

    historial = pre_reg.get('historial', [])
    historial.append({
        "evento": "presupuesto_rechazado",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "detalle": f"Rechazo consolidado (email: {event.get('email_subject', '')[:100]})"
    })

    await db.pre_registros.update_one(
        {"codigo_siniestro": codigo},
        {"$set": {
            "estado": EstadoPreRegistro.ARCHIVADO.value,
            "historial": historial,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    await log_agent("pre_registro_archivado", "ok", "info", codigo=codigo)
    return {"action": "archived", "codigo": codigo}


async def handle_post_aceptacion(msg: EmailMessage, codigo: str,
                                  tipo: TipoEventoEmail,
                                  severidad: SeveridadNotificacion) -> dict:
    """Create an external notification linked to existing order."""
    # Find linked order
    pre_reg = await db.pre_registros.find_one(
        {"codigo_siniestro": codigo}, {"_id": 0}
    )
    orden_id = pre_reg.get('orden_id') if pre_reg else None
    pre_reg_id = pre_reg.get('id') if pre_reg else None

    notif = NotificacionExterna(
        codigo_siniestro=codigo,
        orden_id=orden_id,
        pre_registro_id=pre_reg_id,
        tipo=tipo,
        severidad=severidad,
        titulo=msg.subject[:200],
        contenido=msg.body[:5000] if msg.body else "",
        email_message_id=msg.message_id,
        email_subject=msg.subject,
        email_date=msg.date
    )
    doc = notif.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.notificaciones_externas.insert_one(doc)

    await log_agent("notificacion_externa_creada", "ok", "info",
                    codigo=codigo, email_id=msg.message_id,
                    detalles={"tipo": tipo.value, "severidad": severidad.value,
                              "orden_id": orden_id})

    return {"action": "external_notification_created", "id": notif.id,
            "tipo": tipo.value, "codigo": codigo, "orden_id": orden_id}


# ==================== PORTAL API CLIENT ====================

async def scrape_portal_data(codigo: str) -> Optional[dict]:
    """
    Query the Sumbroker REST API to extract service/customer data.
    Only budget-related admin queries go through the external API.
    Returns structured dict or None on failure.
    """
    config = await db.configuracion.find_one({"tipo": "agent_config"}, {"_id": 0})
    if not config:
        await log_agent("portal_sin_config", "error", "error", codigo=codigo,
                        error="Agent config not found")
        return None

    datos = config.get('datos', {})
    portal_user = datos.get('portal_user')
    portal_pass = datos.get('portal_password')

    if not portal_user or not portal_pass:
        await log_agent("portal_credenciales_incompletas", "error", "error",
                        codigo=codigo)
        return None

    # Decrypt password
    try:
        from agent.crypto import decrypt_value
        portal_pass = decrypt_value(portal_pass)
    except Exception:
        pass  # Use as-is if not encrypted

    try:
        from agent.scraper import SumbrokerClient
        client = SumbrokerClient(login=portal_user, password=portal_pass)
        extracted = await client.extract_service_data(codigo)

        if extracted:
            await log_agent("portal_datos_obtenidos", "ok", "info", codigo=codigo,
                            detalles={"budget_id": extracted.get("budget_id"),
                                      "claim_identifier": extracted.get("claim_identifier")})
            return extracted

        await log_agent("portal_sin_datos", "warning", "warning", codigo=codigo,
                        error=f"No budget found for code {codigo}")
        return None

    except Exception as e:
        await log_agent("portal_error", "error", "error", codigo=codigo,
                        error=str(e))
        return None


# ==================== ORDER CREATION ====================

async def download_portal_photos(codigo: str, docs: list[dict]) -> list[str]:
    """Download photos from portal and save locally. Returns list of filenames."""
    config = await db.configuracion.find_one({"tipo": "agent_config"}, {"_id": 0})
    if not config:
        return []
    datos = config.get('datos', {})
    portal_user = datos.get('portal_user')
    portal_pass = datos.get('portal_password')
    if not portal_user or not portal_pass:
        return []
    try:
        from agent.crypto import decrypt_value
        portal_pass = decrypt_value(portal_pass)
    except Exception:
        pass

    try:
        from agent.scraper import SumbrokerClient
        client = SumbrokerClient(login=portal_user, password=portal_pass)
        saved = await client.download_and_save_photos(docs, codigo)
        await log_agent("fotos_descargadas", "ok", "info", codigo=codigo,
                        detalles={"total": len(saved), "archivos": saved})
        return saved
    except Exception as e:
        await log_agent("error_descarga_fotos", "error", "error", codigo=codigo,
                        error=str(e))
        return []


async def create_orden_from_pre_registro(pre_reg: dict,
                                          datos_portal: Optional[dict]) -> Optional[str]:
    """
    Create a final work order from pre-registro + Sumbroker API data.
    Portal data enriches device/customer info; operational fields stay in CRM.
    Downloads photos from provider and attaches them.
    Returns the order ID or None.
    """
    from models import OrdenTrabajo, OrderStatus, Cliente
    from helpers import generate_barcode
    import uuid

    codigo = pre_reg['codigo_siniestro']
    dp = datos_portal or {}

    # ── Ensure customer exists in CRM ───────────────────────
    cliente_id = pre_reg.get('cliente_id', '')
    client_phone = dp.get('client_phone') or dp.get('customer_phone') or ''
    client_full_name = dp.get('client_full_name') or ''
    client_name = dp.get('client_name') or ''
    client_last1 = dp.get('client_last_name_1') or ''
    client_last2 = dp.get('client_last_name_2') or ''
    client_nif = dp.get('client_nif') or ''
    client_email = dp.get('client_email') or ''
    client_address = dp.get('client_address') or ''
    client_city = dp.get('client_city') or ''
    client_province = dp.get('client_province') or ''
    client_zip = dp.get('client_zip') or ''

    if not cliente_id and client_phone:
        # Try to find existing customer by phone or NIF
        existing_client = None
        if client_nif:
            existing_client = await db.clientes.find_one(
                {"dni": client_nif}, {"_id": 0}
            )
        if not existing_client:
            existing_client = await db.clientes.find_one(
                {"telefono": client_phone}, {"_id": 0}
            )
        if existing_client:
            cliente_id = existing_client['id']
            # Update existing client with any new data from portal
            update_fields = {}
            if client_email and not existing_client.get('email'):
                update_fields['email'] = client_email
            if client_nif and not existing_client.get('dni'):
                update_fields['dni'] = client_nif
            if update_fields:
                update_fields['updated_at'] = datetime.now(timezone.utc).isoformat()
                await db.clientes.update_one(
                    {"id": cliente_id}, {"$set": update_fields}
                )
        else:
            # Auto-create customer from portal data with full details
            apellidos = f"{client_last1} {client_last2}".strip() if client_last1 else ''
            new_client = Cliente(
                nombre=client_name or client_full_name or client_phone,
                apellidos=apellidos,
                dni=client_nif,
                telefono=client_phone,
                email=client_email,
                direccion=client_address,
                ciudad=client_city,
                codigo_postal=client_zip,
            )
            client_doc = new_client.model_dump()
            client_doc['created_at'] = client_doc['created_at'].isoformat()
            client_doc['updated_at'] = client_doc['updated_at'].isoformat()
            client_doc['creado_por_agente'] = True
            client_doc['codigo_siniestro_origen'] = codigo
            client_doc['provincia'] = client_province
            await db.clientes.insert_one(client_doc)
            cliente_id = new_client.id

    # ── Build device info from portal data ──────────────────
    device_brand = dp.get('device_brand') or ''
    device_model_raw = dp.get('device_model') or ''
    device_model = device_model_raw or pre_reg.get('dispositivo_modelo', 'Pendiente datos')
    if device_brand and device_model_raw:
        device_model = f"{device_brand} {device_model_raw}"
    elif device_brand:
        device_model = device_brand

    device_imei = dp.get('device_imei') or pre_reg.get('dispositivo_imei')
    device_colour = dp.get('device_colour') or ''

    damage_desc = dp.get('damage_description') or \
                  dp.get('damage_type_text') or \
                  pre_reg.get('email_subject', '')

    # ── Download photos from provider ───────────────────────
    portal_photos = []
    docs = dp.get('docs', [])
    if docs:
        portal_photos = await download_portal_photos(codigo, docs)

    # ── Create the work order ───────────────────────────────
    orden = OrdenTrabajo(
        cliente_id=cliente_id,
        dispositivo={
            "modelo": device_model,
            "imei": device_imei,
            "color": device_colour,
            "daños": damage_desc,
        },
        agencia_envio=dp.get('shipping_company') or '',
        codigo_recogida_entrada=dp.get('tracking_number') or '',
        numero_autorizacion=codigo,
        notas=f"Orden automática — siniestro {codigo} "
              f"({dp.get('claim_type_text', '')}). "
              f"Póliza: {dp.get('policy_number', 'N/A')}. "
              f"Producto: {dp.get('product_name', 'N/A')}.",
    )
    orden.qr_code = generate_barcode(orden.numero_orden)
    orden.historial_estados = [{
        "estado": OrderStatus.PENDIENTE_RECIBIR.value,
        "fecha": datetime.now(timezone.utc).isoformat(),
        "usuario": "agente_email",
    }]
    # Attach portal photos as evidencias
    orden.evidencias = portal_photos

    doc = orden.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['codigo_siniestro'] = codigo
    doc['creado_por_agente'] = True
    doc['fotos_portal'] = portal_photos

    # Store all portal-enriched fields for the work order
    doc['datos_proveedor'] = {
        "claim_identifier": dp.get('claim_identifier'),
        "damage_type_text": dp.get('damage_type_text'),
        "damage_description": dp.get('damage_description'),
        "device_brand": device_brand,
        "device_model": device_model_raw,
        "device_imei": device_imei,
        "device_colour": device_colour,
        "device_type": dp.get('device_type'),
        "device_purchase_date": dp.get('device_purchase_date'),
        "device_purchase_price": dp.get('device_purchase_price'),
        "client_full_name": client_full_name,
        "client_nif": client_nif,
        "client_phone": client_phone,
        "client_email": client_email,
        "client_address": client_address,
        "client_city": client_city,
        "client_province": client_province,
        "client_zip": client_zip,
        "claim_type_text": dp.get('claim_type_text'),
        "repair_type_text": dp.get('repair_type_text'),
        "repair_time_text": dp.get('repair_time_text'),
        "warranty_type_text": dp.get('warranty_type_text'),
        "status_text": dp.get('status_text'),
        "external_status_text": dp.get('external_status_text'),
        "price": dp.get('price'),
        "reserve_value": dp.get('reserve_value'),
        "policy_number": dp.get('policy_number'),
        "product_name": dp.get('product_name'),
        "accepted_date": dp.get('accepted_date'),
        "pickup_date": dp.get('pickup_date'),
        "docs_count": len(dp.get('docs', [])),
        "docs_downloaded": len(portal_photos),
    }

    # Attach portal data for audit/reference
    if datos_portal:
        portal_clean = {k: v for k, v in datos_portal.items() if k != 'docs'}
        portal_clean['docs_count'] = len(dp.get('docs', []))
        portal_clean['docs_downloaded'] = len(portal_photos)
        doc['datos_portal'] = portal_clean

    try:
        await db.ordenes.insert_one(doc)
        await log_agent("orden_creada", "ok", "info", codigo=codigo,
                        detalles={"orden_id": orden.id,
                                  "numero_orden": orden.numero_orden,
                                  "cliente_id": cliente_id,
                                  "fotos_descargadas": len(portal_photos)})
        return orden.id
    except Exception as e:
        await log_agent("error_insert_orden", "error", "error", codigo=codigo,
                        error=str(e))
        return None

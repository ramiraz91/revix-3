"""
Insurama/Sumbroker direct polling: replaces email-based flow.
Polls the Sumbroker API periodically for new/changed budgets and
automatically creates pre-registros and orders.
"""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional
from config import db, logger
from models import OrderStatus, EstadoPreRegistro
from agent.processor import (
    scrape_portal_data, create_orden_from_pre_registro,
    download_portal_photos, log_agent
)

# Lazy import to avoid circular deps
def _get_ws_broadcast():
    try:
        from websocket_manager import ws_manager
        return ws_manager
    except ImportError:
        return None


async def _get_sumbroker_client():
    """Get authenticated SumbrokerClient from DB config or agent config."""
    from agent.scraper import SumbrokerClient
    
    # Try sumbroker config first
    config = await db.configuracion.find_one({"tipo": "sumbroker"}, {"_id": 0})
    if config and config.get("datos", {}).get("login"):
        datos = config["datos"]
        return SumbrokerClient(login=datos["login"], password=datos["password"])
    
    # Fallback to agent_config
    config = await db.configuracion.find_one({"tipo": "agent_config"}, {"_id": 0})
    if config:
        datos = config.get("datos", {})
        portal_user = datos.get("portal_user")
        portal_pass = datos.get("portal_password")
        if portal_user and portal_pass:
            try:
                from agent.crypto import decrypt_value
                portal_pass = decrypt_value(portal_pass)
            except Exception:
                pass
            return SumbrokerClient(login=portal_user, password=portal_pass)
    
    return None


async def poll_insurama_budgets():
    """
    Main polling function. Fetches all budgets from Sumbroker and:
    1. New budgets (not in DB) → create pre_registro + notification
    2. Accepted budgets (pre_registro exists, no order) → create order
    3. Status changes → update pre_registro + notification
    """
    client = await _get_sumbroker_client()
    if not client:
        logger.debug("Insurama polling skipped: no credentials")
        return {"action": "skipped", "reason": "no_credentials"}
    
    try:
        # Usar limit=100 para reducir número de peticiones
        budgets = await client.list_store_budgets(limit=100)
    except Exception as e:
        logger.error(f"Insurama polling error fetching budgets: {e}")
        return {"action": "error", "error": str(e)}
    
    if not budgets:
        return {"action": "ok", "new": 0, "accepted": 0, "changes": 0}
    
    stats = {"new": 0, "accepted": 0, "changes": 0, "errors": 0}
    
    for b in budgets:
        try:
            cb = b.get("claim_budget") or {}
            prc = cb.get("policy_risk_claim") or {}
            codigo = prc.get("identifier")
            if not codigo:
                continue
            
            budget_id = b.get("id")
            # Status can be string or int from API - normalize to int
            status_raw = b.get("status")
            status = int(status_raw) if status_raw is not None else None
            status_text = b.get("status_text")
            price = b.get("price")
            
            # Check if we already track this budget
            pre_reg = await db.pre_registros.find_one(
                {"codigo_siniestro": codigo}, {"_id": 0}
            )
            
            if not pre_reg:
                # NEW budget — create pre_registro
                await _handle_new_budget(codigo, b, prc, cb)
                stats["new"] += 1
            else:
                # Existing — check for status changes
                prev_status = pre_reg.get("sumbroker_status")
                estado_pre = pre_reg.get("estado")
                
                if status == 3 and estado_pre not in [
                    EstadoPreRegistro.ORDEN_CREADA.value,
                    EstadoPreRegistro.ACEPTADO.value
                ]:
                    # ACCEPTED — create order and notify with popup
                    result = await _handle_accepted_budget(codigo, pre_reg, b)
                    if result:
                        stats["accepted"] += 1
                        # Capturar datos de inteligencia de precios - GANADO
                        await _capturar_inteligencia_precios(codigo, pre_reg, "ganado")
                elif status == 2 and prev_status != 2:
                    # REJECTED — mark pre-registro as rejected/cancelled
                    await _handle_rejected_budget(codigo, pre_reg, b, status_text)
                    stats["changes"] += 1
                elif status == 4 and prev_status != 4:
                    # RECOTIZAR / MODIFICADO — needs re-budget, urgent notification
                    await _handle_recotizar(codigo, pre_reg, b, status_text)
                    stats["changes"] += 1
                elif status == 7 and prev_status != 7:
                    # CANCELLED — mark as cancelled (with or without order)
                    if pre_reg.get("orden_id"):
                        await _handle_cancellation(codigo, pre_reg)
                    else:
                        await _handle_rejected_budget(codigo, pre_reg, b, status_text)
                    stats["changes"] += 1
                    
                    # Capturar datos de inteligencia de precios
                    await _capturar_inteligencia_precios(codigo, pre_reg, "cancelado")
                elif prev_status and prev_status != status:
                    # Status changed
                    await _handle_status_change(codigo, pre_reg, b, status, status_text)
                    stats["changes"] += 1
                
                # Check for photo rejections in observations (runs on every poll for existing budgets)
                try:
                    if budget_id:
                        from agent.scraper import SumbrokerClient
                        client = await _get_sumbroker_client()
                        if client:
                            observations = await client.get_observations(budget_id)
                            if observations:
                                await _handle_photo_rejection(codigo, pre_reg, b, observations)
                except Exception as e:
                    logger.debug(f"Error checking photo rejections for {codigo}: {e}")
                
                # Always update sumbroker_status for tracking
                if prev_status != status:
                    await db.pre_registros.update_one(
                        {"codigo_siniestro": codigo},
                        {"$set": {
                            "sumbroker_status": status,
                            "sumbroker_status_text": status_text,
                            "sumbroker_price": price,
                            "sumbroker_budget_id": budget_id,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
        except Exception as e:
            logger.error(f"Insurama polling error for budget {b.get('id')}: {e}")
            stats["errors"] += 1
    
    if stats["new"] or stats["accepted"] or stats["changes"]:
        logger.info(f"Insurama poll: {stats['new']} new, {stats['accepted']} accepted, "
                     f"{stats['changes']} changes, {stats['errors']} errors")
    
    # Auto-cleanup old cancelled pre-registros (default: 7 days)
    try:
        await cleanup_old_cancelled_preregistros(days=7)
    except Exception as e:
        logger.debug(f"Cleanup pre-registros error: {e}")
    
    return {"action": "ok", **stats}


async def _handle_new_budget(codigo: str, budget: dict, prc: dict, cb: dict):
    """Create pre_registro for a new Sumbroker budget."""
    policy = cb.get("policy") or {}
    client_name = policy.get("complete_name") or \
                  f"{policy.get('name', '')} {policy.get('last_name_1', '')}".strip()
    
    terminals = policy.get("mobile_terminals_active") or []
    device_str = ""
    if terminals:
        t = terminals[0]
        device_str = f"{t.get('brand', '')} {t.get('model', '')}".strip()
    
    damage = (prc.get("description") or "")[:200]
    status_raw = budget.get("status")
    status = int(status_raw) if status_raw is not None else None
    status_text = budget.get("status_text")
    
    pre_reg_id = str(uuid.uuid4())
    pre_reg_doc = {
        "id": pre_reg_id,
        "codigo_siniestro": codigo,
        "estado": EstadoPreRegistro.PENDIENTE_PRESUPUESTO.value,
        "sumbroker_budget_id": budget.get("id"),
        "sumbroker_status": status,
        "sumbroker_status_text": status_text,
        "sumbroker_price": budget.get("price"),
        "cliente_nombre": client_name,
        "dispositivo_modelo": device_str,
        "daño_descripcion": damage,
        "origen": "polling_insurama",
        "historial": [{
            "evento": "creado_desde_polling",
            "fecha": datetime.now(timezone.utc).isoformat(),
            "detalle": f"Detectado desde Sumbroker API (status: {status_text})"
        }],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.pre_registros.insert_one(pre_reg_doc)
    
    # Determine notification type based on status
    if status == 1:
        # Pendiente — needs budget submission
        notif_tipo = "nuevo_servicio_insurama"
        notif_titulo = "Nuevo servicio Insurama"
        notif_msg = f"Nuevo siniestro {codigo} pendiente de presupuesto. {client_name} — {device_str}. Daño: {damage}"
        urgente = True
    elif status == 3:
        # Already accepted — will be handled by _handle_accepted_budget next cycle
        notif_tipo = "presupuesto_aceptado_detectado"
        notif_titulo = "Presupuesto aceptado detectado"
        notif_msg = f"Siniestro {codigo} ya aceptado en Sumbroker. {client_name} — {device_str}"
        urgente = True
    else:
        notif_tipo = "nuevo_pre_registro"
        notif_titulo = f"Siniestro detectado ({status_text})"
        notif_msg = f"Nuevo siniestro {codigo} ({status_text}). {client_name} — {device_str}"
        urgente = False
    
    await db.notificaciones.insert_one({
        "id": str(uuid.uuid4()),
        "tipo": notif_tipo,
        "titulo": notif_titulo,
        "mensaje": notif_msg,
        "codigo_siniestro": codigo,
        "pre_registro_id": pre_reg_id,
        "urgente": urgente,
        "popup": urgente,
        "leida": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Broadcast via WebSocket
    ws = _get_ws_broadcast()
    if ws:
        asyncio.create_task(ws.notify_event(
            notif_tipo,
            {"titulo": notif_titulo, "mensaje": notif_msg, "urgente": urgente, "popup": urgente}
        ))
    
    await log_agent("pre_registro_polling", "ok", "info", codigo=codigo,
                    detalles={"budget_id": budget.get("id"), "status": status_text})


async def _handle_accepted_budget(codigo: str, pre_reg: dict, budget: dict) -> bool:
    """Create work order from accepted budget."""
    historial = pre_reg.get("historial", [])
    historial.append({
        "evento": "presupuesto_aceptado_polling",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "detalle": "Aceptación detectada por polling Sumbroker"
    })
    
    await db.pre_registros.update_one(
        {"codigo_siniestro": codigo},
        {"$set": {
            "estado": EstadoPreRegistro.ACEPTADO.value,
            "historial": historial,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Scrape full portal data
    datos_portal = await scrape_portal_data(codigo)
    if datos_portal:
        await db.pre_registros.update_one(
            {"codigo_siniestro": codigo},
            {"$set": {"datos_portal": datos_portal}}
        )
    
    # Create order
    orden_id = await create_orden_from_pre_registro(pre_reg, datos_portal)
    
    if orden_id:
        historial.append({
            "evento": "orden_creada",
            "fecha": datetime.now(timezone.utc).isoformat(),
            "detalle": f"Orden {orden_id} creada desde polling"
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
        
        # Notification
        orden = await db.ordenes.find_one(
            {"id": orden_id},
            {"_id": 0, "numero_orden": 1, "dispositivo": 1, "cliente_id": 1}
        )
        cliente = None
        if orden and orden.get("cliente_id"):
            cliente = await db.clientes.find_one(
                {"id": orden["cliente_id"]}, {"_id": 0, "nombre": 1, "apellidos": 1}
            )
        cliente_nombre = f"{cliente.get('nombre', '')} {cliente.get('apellidos', '')}".strip() if cliente else ""
        dispositivo = orden.get("dispositivo", {}).get("modelo", "") if orden else ""
        
        await db.notificaciones.insert_one({
            "id": str(uuid.uuid4()),
            "tipo": "presupuesto_aceptado",
            "titulo": "PRESUPUESTO ACEPTADO",
            "mensaje": f"Presupuesto aceptado para {codigo}. {cliente_nombre} — {dispositivo}. Orden creada: {orden.get('numero_orden', '') if orden else ''}",
            "orden_id": orden_id,
            "codigo_siniestro": codigo,
            "urgente": True,
            "popup": True,
            "leida": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Broadcast via WebSocket
        ws = _get_ws_broadcast()
        if ws:
            asyncio.create_task(ws.notify_event(
                "presupuesto_aceptado",
                {"titulo": "PRESUPUESTO ACEPTADO", "mensaje": f"{codigo} — {cliente_nombre} — {dispositivo}", "urgente": True, "popup": True, "orden_id": orden_id}
            ))
        
        await log_agent("orden_creada_polling", "ok", "info", codigo=codigo,
                        detalles={"orden_id": orden_id})
        return True
    
    await log_agent("error_creando_orden_polling", "error", "error", codigo=codigo)
    return False


async def _handle_rejected_budget(codigo: str, pre_reg: dict, budget: dict, status_text: str):
    """Handle rejected/cancelled budget - mark pre-registro as anulado."""
    historial = pre_reg.get("historial", [])
    historial.append({
        "evento": "presupuesto_rechazado",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "detalle": f"Presupuesto rechazado/cancelado por cliente: {status_text}"
    })
    
    await db.pre_registros.update_one(
        {"codigo_siniestro": codigo},
        {"$set": {
            "estado": EstadoPreRegistro.RECHAZADO.value,
            "historial": historial,
            "sumbroker_status_text": status_text,
            "fecha_anulacion": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    cliente_nombre = pre_reg.get("cliente_nombre", "")
    dispositivo = pre_reg.get("dispositivo_modelo", "")
    
    await db.notificaciones.insert_one({
        "id": str(uuid.uuid4()),
        "tipo": "presupuesto_rechazado",
        "titulo": "Presupuesto Rechazado",
        "mensaje": f"El cliente ha rechazado el presupuesto para {codigo}. {cliente_nombre} — {dispositivo}",
        "codigo_siniestro": codigo,
        "urgente": False,
        "popup": False,
        "leida": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    await log_agent("presupuesto_rechazado", "ok", "info", codigo=codigo,
                    detalles={"status_text": status_text})
    
    logger.info(f"Pre-registro {codigo} marcado como RECHAZADO")


async def _handle_status_change(codigo: str, pre_reg: dict, budget: dict,
                                 new_status: int, status_text: str):
    """Handle budget status change notification."""
    prev_status_text = pre_reg.get("sumbroker_status_text", "desconocido")
    
    historial = pre_reg.get("historial", [])
    historial.append({
        "evento": "cambio_estado_sumbroker",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "detalle": f"Estado cambiado: {prev_status_text} → {status_text}"
    })
    
    await db.pre_registros.update_one(
        {"codigo_siniestro": codigo},
        {"$set": {"historial": historial, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Only notify for significant changes
    orden_id = pre_reg.get("orden_id")
    if new_status == 7:  # Cancelled
        tipo = "servicio_cancelado"
        titulo = "Servicio cancelado"
        urgente = True
    else:
        tipo = "cambio_estado_insurama"
        titulo = "Cambio estado Insurama"
        urgente = False
    
    await db.notificaciones.insert_one({
        "id": str(uuid.uuid4()),
        "tipo": tipo,
        "titulo": titulo,
        "mensaje": f"Siniestro {codigo}: {prev_status_text} → {status_text}",
        "codigo_siniestro": codigo,
        "orden_id": orden_id,
        "urgente": urgente,
        "popup": urgente,
        "leida": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })


async def _handle_photo_rejection(codigo: str, pre_reg: dict, budget: dict, observations: list):
    """
    Detect when Sumbroker rejects uploaded photos by analyzing observations.
    Creates urgent notification for admin to re-upload photos.
    
    Common rejection patterns in observations:
    - "fotos rechazadas"
    - "foto no válida"
    - "reenviar fotos"
    - "documentación insuficiente"
    - "imagen borrosa"
    - "foto no legible"
    """
    rejection_keywords = [
        "fotos rechazadas", "foto rechazada", "fotos no válidas", "foto no válida",
        "reenviar fotos", "reenviar foto", "volver a enviar fotos", "enviar de nuevo",
        "documentación insuficiente", "documentacion insuficiente",
        "imagen borrosa", "foto borrosa", "no se aprecia", "no legible",
        "foto incorrecta", "fotos incorrectas", "adjuntar nuevamente",
        "imagen no válida", "calidad insuficiente", "foto dañada"
    ]
    
    orden_id = pre_reg.get("orden_id")
    
    # Get tracked rejections to avoid duplicate notifications
    tracked = pre_reg.get("fotos_rechazadas_detectadas", [])
    
    for obs in observations:
        obs_text = (obs.get("observation") or obs.get("message") or "").lower()
        obs_id = obs.get("id") or obs.get("created_at", "")
        
        # Skip if already tracked
        if obs_id in tracked:
            continue
        
        # Check for rejection keywords
        is_rejection = any(keyword in obs_text for keyword in rejection_keywords)
        
        if is_rejection:
            # Mark as tracked
            tracked.append(obs_id)
            
            await db.pre_registros.update_one(
                {"codigo_siniestro": codigo},
                {"$set": {
                    "fotos_rechazadas_detectadas": tracked,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                },
                "$push": {
                    "historial": {
                        "evento": "fotos_rechazadas",
                        "fecha": datetime.now(timezone.utc).isoformat(),
                        "detalle": f"Rechazo de fotos detectado: {obs_text[:150]}"
                    }
                }}
            )
            
            # Update order if exists
            if orden_id:
                await db.ordenes.update_one(
                    {"id": orden_id},
                    {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
                    "$push": {
                        "notas_insurama": {
                            "fecha": datetime.now(timezone.utc).isoformat(),
                            "mensaje": f"📷 FOTOS RECHAZADAS: {obs_text[:200]}"
                        }
                    }}
                )
            
            # Get context for notification
            cliente_nombre = pre_reg.get("cliente_nombre", "")
            dispositivo = pre_reg.get("dispositivo_modelo", "")
            
            notif_msg = (f"📷 FOTOS RECHAZADAS: Siniestro {codigo}. "
                        f"{cliente_nombre} — {dispositivo}. "
                        f"Motivo: {obs_text[:100]}... "
                        f"Reenvíe las fotos desde el portal Sumbroker.")
            
            await db.notificaciones.insert_one({
                "id": str(uuid.uuid4()),
                "tipo": "fotos_rechazadas_insurama",
                "titulo": "📷 FOTOS RECHAZADAS",
                "mensaje": notif_msg,
                "codigo_siniestro": codigo,
                "orden_id": orden_id,
                "urgente": True,
                "popup": True,
                "leida": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            # WebSocket broadcast
            ws = _get_ws_broadcast()
            if ws:
                asyncio.create_task(ws.notify_event(
                    "fotos_rechazadas_insurama",
                    {"titulo": "📷 FOTOS RECHAZADAS", "mensaje": notif_msg, 
                     "urgente": True, "popup": True, "orden_id": orden_id}
                ))
            
            await log_agent("fotos_rechazadas_detectado", "ok", "warning", codigo=codigo,
                           detalles={"orden_id": orden_id, "observacion": obs_text[:200]})
            
            logger.warning(f"Insurama photo rejection detected: {codigo}")


async def _handle_recotizar(codigo: str, pre_reg: dict, budget: dict, status_text: str):
    """
    Handle RECOTIZAR / MODIFICADO status (status=4).
    This means the insurance company rejected the initial budget and requests a new one.
    Creates urgent notification for admin to submit a new budget.
    """
    historial = pre_reg.get("historial", [])
    historial.append({
        "evento": "recotizar_detectado",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "detalle": f"Sumbroker solicita RECOTIZAR el presupuesto ({status_text})"
    })
    
    await db.pre_registros.update_one(
        {"codigo_siniestro": codigo},
        {"$set": {
            "estado": "recotizar",
            "historial": historial,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    orden_id = pre_reg.get("orden_id")
    
    # Update order if exists
    if orden_id:
        await db.ordenes.update_one(
            {"id": orden_id},
            {"$set": {
                "estado": "re_presupuestar",
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            "$push": {
                "notas_insurama": {
                    "fecha": datetime.now(timezone.utc).isoformat(),
                    "mensaje": f"⚠️ RECOTIZAR: Sumbroker solicita nuevo presupuesto ({status_text})"
                },
                "historial_estados": {
                    "estado": "re_presupuestar",
                    "fecha": datetime.now(timezone.utc).isoformat(),
                    "usuario": "sistema_insurama",
                    "notas": f"Recotización solicitada: {status_text}"
                }
            }}
        )
    
    # Get client/device info for notification
    cliente_nombre = pre_reg.get("cliente_nombre", "")
    dispositivo = pre_reg.get("dispositivo_modelo", "")
    
    notif_msg = (f"⚠️ RECOTIZAR URGENTE: Siniestro {codigo} requiere nuevo presupuesto. "
                 f"{cliente_nombre} — {dispositivo}. "
                 f"Estado Sumbroker: {status_text}")
    
    await db.notificaciones.insert_one({
        "id": str(uuid.uuid4()),
        "tipo": "recotizar_insurama",
        "titulo": "RECOTIZAR PRESUPUESTO",
        "mensaje": notif_msg,
        "codigo_siniestro": codigo,
        "orden_id": orden_id,
        "urgente": True,
        "popup": True,
        "leida": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # WebSocket broadcast
    ws = _get_ws_broadcast()
    if ws:
        asyncio.create_task(ws.notify_event(
            "recotizar_insurama",
            {"titulo": "RECOTIZAR PRESUPUESTO", "mensaje": notif_msg, "urgente": True, "popup": True, "orden_id": orden_id}
        ))
    
    await log_agent("recotizar_detectado", "ok", "warning", codigo=codigo,
                    detalles={"orden_id": orden_id, "status_text": status_text})
    
    logger.warning(f"Insurama RECOTIZAR detected: {codigo} -> requires new budget")


CANCELACION_PRECIO = 42.0  # IVA incluido

async def _ensure_cancelacion_item():
    """Ensure 'Cancelación' inventory item exists, create if not."""
    item = await db.repuestos.find_one({"nombre": "Cancelación Insurama"}, {"_id": 0})
    if item:
        return item["id"]
    
    item_id = str(uuid.uuid4())
    await db.repuestos.insert_one({
        "id": item_id,
        "nombre": "Cancelación Insurama",
        "descripcion": "Gastos de cancelación de servicio Insurama/Sumbroker",
        "precio_venta": CANCELACION_PRECIO,
        "precio_coste": 0,
        "iva": 0,  # 42€ IVA incluido
        "categoria": "Servicios",
        "activo": True,
        "stock": 9999,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    return item_id


async def _handle_cancellation(codigo: str, pre_reg: dict):
    """
    Handle budget cancellation after acceptance:
    1. Remove all materials from the order
    2. Add single 'Cancelación' item at 42€
    3. Notify admin urgently
    """
    orden_id = pre_reg.get("orden_id")
    if not orden_id:
        return
    
    orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0})
    if not orden:
        return
    
    # Ensure cancelación item exists in inventory
    cancelacion_id = await _ensure_cancelacion_item()
    
    # Replace all materials with single cancellation item
    material_cancelacion = {
        "repuesto_id": cancelacion_id,
        "nombre": "Cancelación Insurama",
        "descripcion": f"Cancelación siniestro {codigo}",
        "cantidad": 1,
        "precio_unitario": CANCELACION_PRECIO,
        "coste": 0,
        "iva": 0,
        "descuento": 0,
        "añadido_por_tecnico": False,
        "aprobado": True,
        "pendiente_precios": False
    }
    
    await db.ordenes.update_one(
        {"id": orden_id},
        {"$set": {
            "materiales": [material_cancelacion],
            "cancelado_insurama": True,
            "fecha_cancelacion_insurama": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        "$push": {
            "notas_insurama": {
                "fecha": datetime.now(timezone.utc).isoformat(),
                "mensaje": "CANCELADO por Sumbroker. Materiales reemplazados por partida de cancelación (42€)"
            }
        }}
    )
    
    # Update pre_registro
    historial = pre_reg.get("historial", [])
    historial.append({
        "evento": "cancelacion_procesada",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "detalle": "Cancelación detectada. Materiales reemplazados por partida cancelación 42€"
    })
    await db.pre_registros.update_one(
        {"codigo_siniestro": codigo},
        {"$set": {
            "estado": "cancelado",
            "historial": historial,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Urgent notification
    numero_orden = orden.get("numero_orden", "?")
    notif_msg = (f"CANCELACIÓN Insurama: Siniestro {codigo} (Orden {numero_orden}). "
                 f"Materiales reemplazados por partida de cancelación (42€ IVA inc.). "
                 f"Valide y envíe presupuesto de gastos.")
    
    await db.notificaciones.insert_one({
        "id": str(uuid.uuid4()),
        "tipo": "cancelacion_insurama",
        "titulo": "CANCELACIÓN INSURAMA",
        "mensaje": notif_msg,
        "orden_id": orden_id,
        "codigo_siniestro": codigo,
        "urgente": True,
        "popup": True,
        "leida": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # WebSocket broadcast
    ws = _get_ws_broadcast()
    if ws:
        asyncio.create_task(ws.notify_event(
            "cancelacion_insurama",
            {"titulo": "CANCELACIÓN INSURAMA", "mensaje": notif_msg, "urgente": True, "popup": True, "orden_id": orden_id}
        ))
    
    await log_agent("cancelacion_insurama", "ok", "warning", codigo=codigo,
                    detalles={"orden_id": orden_id, "numero_orden": numero_orden})
    
    logger.warning(f"Insurama cancellation processed: {codigo} -> Order {numero_orden}, materials replaced with 42€ cancellation fee")


async def cleanup_old_cancelled_preregistros(days: int = 7):
    """
    Auto-cleanup pre-registros that have been cancelled/rejected/archived for more than X days.
    This runs as part of the polling cycle to keep the database clean.
    """
    from datetime import timedelta
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_iso = cutoff_date.isoformat()
    
    # Find and delete old cancelled pre-registros
    result = await db.pre_registros.delete_many({
        "estado": {"$in": ["cancelado", "rechazado", "archivado"]},
        "updated_at": {"$lt": cutoff_iso}
    })
    
    if result.deleted_count > 0:
        logger.info(f"Auto-cleanup: Deleted {result.deleted_count} old cancelled pre-registros (older than {days} days)")
        await log_agent("cleanup_preregistros", "ok", "info", 
                       detalles={"eliminados": result.deleted_count, "dias_antiguedad": days})
    
    return result.deleted_count



async def _capturar_inteligencia_precios(codigo: str, pre_reg: dict, resultado: str):
    """
    Captura automática de datos de inteligencia de precios cuando un presupuesto
    cambia a estado final (ganado/cancelado).
    """
    try:
        client = await _get_sumbroker_client()
        if not client:
            return
        
        # Obtener datos de competidores
        budget = await client.find_budget_by_service_code(codigo)
        if not budget:
            return
        
        claim_budget_id = budget.get("claim_budget_id")
        my_budget_id = budget.get("id")
        
        if not claim_budget_id:
            return
        
        # Obtener todos los presupuestos del siniestro
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as http:
            resp = await http.get(
                f"https://api.sumbroker.es/api/v2/claim-budget/{claim_budget_id}/store-budgets",
                headers=client._headers()
            )
            
            if resp.status_code != 200:
                return
            
            all_budgets = resp.json()
        
        # Procesar datos
        mi_presupuesto = None
        competidores = []
        precio_ganador = None
        ganador_nombre = None
        precios_validos = []
        
        for b in all_budgets:
            store = b.get("store", {})
            precio = float(b.get("price", 0) or 0)
            budget_status = int(b.get("status", 0)) if b.get("status") else 0
            
            budget_info = {
                "nombre": store.get("name", "N/A"),
                "precio": precio,
                "estado": b.get("status_text"),
                "estado_codigo": budget_status
            }
            
            if b.get("id") == my_budget_id:
                mi_presupuesto = budget_info
            else:
                competidores.append(budget_info)
                
                # Si este competidor fue aceptado (ganó)
                if budget_status == 3:
                    precio_ganador = precio
                    ganador_nombre = store.get("name")
            
            if precio > 0:
                precios_validos.append(precio)
        
        # Determinar resultado real basado en estados
        resultado_final = resultado
        if mi_presupuesto:
            if mi_presupuesto.get("estado_codigo") == 3:
                resultado_final = "ganado"
                precio_ganador = mi_presupuesto.get("precio")
                ganador_nombre = mi_presupuesto.get("nombre")
            elif precio_ganador and ganador_nombre:
                resultado_final = "perdido"
            else:
                resultado_final = "cancelado_cliente"
        
        # Obtener datos del dispositivo del pre_registro
        dispositivo_marca = pre_reg.get("dispositivo_marca") or ""
        dispositivo_modelo = pre_reg.get("dispositivo_modelo") or ""
        tipo_reparacion = pre_reg.get("descripcion_dano") or pre_reg.get("tipo_servicio") or ""
        
        # Crear registro en historial_mercado
        registro = {
            "codigo_siniestro": codigo,
            "dispositivo_marca": dispositivo_marca,
            "dispositivo_modelo": dispositivo_modelo,
            "dispositivo_key": f"{dispositivo_marca} {dispositivo_modelo}".strip().upper(),
            "tipo_reparacion": tipo_reparacion,
            "fecha_cierre": datetime.now(timezone.utc).isoformat(),
            "resultado": resultado_final,
            
            "mi_precio": mi_presupuesto.get("precio") if mi_presupuesto else None,
            "precio_ganador": precio_ganador,
            "ganador_nombre": ganador_nombre,
            "ganador_nombre_key": (ganador_nombre or "").upper(),
            
            "num_competidores": len(competidores),
            "precio_minimo": min(precios_validos) if precios_validos else None,
            "precio_maximo": max(precios_validos) if precios_validos else None,
            "precio_medio": round(sum(precios_validos) / len(precios_validos), 2) if precios_validos else None,
            
            "competidores": [{"nombre": c["nombre"], "precio": c["precio"], "posicion": i+1} 
                           for i, c in enumerate(sorted(competidores, key=lambda x: x.get("precio", 0) if x.get("precio", 0) > 0 else 999999))],
            
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Normalizar tipo de reparación
        tipo_upper = (tipo_reparacion or "").upper()
        if any(x in tipo_upper for x in ["PANTALLA", "LCD", "DISPLAY", "OLED", "INCELL"]):
            registro["tipo_reparacion_key"] = "PANTALLA"
        elif any(x in tipo_upper for x in ["BATERIA", "BATTERY"]):
            registro["tipo_reparacion_key"] = "BATERIA"
        elif any(x in tipo_upper for x in ["CAMARA", "CAMERA"]):
            registro["tipo_reparacion_key"] = "CAMARA"
        elif any(x in tipo_upper for x in ["TAPA", "BACK", "COVER"]):
            registro["tipo_reparacion_key"] = "TAPA_TRASERA"
        else:
            registro["tipo_reparacion_key"] = "OTROS"
        
        # Guardar o actualizar
        await db.historial_mercado.update_one(
            {"codigo_siniestro": codigo},
            {"$set": registro},
            upsert=True
        )
        
        logger.info(f"Inteligencia de precios capturada: {codigo} -> {resultado_final}")
        
    except Exception as e:
        logger.error(f"Error capturando inteligencia de precios para {codigo}: {e}")


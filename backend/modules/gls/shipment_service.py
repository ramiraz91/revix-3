"""
GLS Shipment Service - Business logic layer.
Orchestrates SOAP calls, persistence, state mapping, event handling, and notifications.

MÓDULO LOGÍSTICO COMPLETO:
- Crear recogidas y envíos desde OT
- Crear devoluciones
- Obtener y almacenar etiquetas (persistente)
- Consultar tracking y eventos
- Sincronización automática de estados no finales
- Trazabilidad total dentro de la OT
- Notificaciones al cliente
- Prevención de duplicados
- Auditoría completa
"""
import uuid
import base64
import logging
from datetime import datetime, timezone
from typing import Optional, Literal

from modules.gls.soap_client import graba_servicios, etiqueta_envio_v2, get_exp, get_exp_cli
from modules.gls.state_mapper import map_gls_state, is_final_state, STATE_BADGES

logger = logging.getLogger("gls.shipment")

# URL de seguimiento de GLS España
GLS_TRACKING_URL = "https://www.gls-spain.es/apptracking.asp"

# Tipos de envío soportados
ShipmentType = Literal["envio", "recogida", "devolucion"]


def get_tracking_url(codbarras: str) -> str:
    """Genera la URL de seguimiento para el cliente."""
    if not codbarras:
        return ""
    return f"{GLS_TRACKING_URL}?codigo={codbarras}"


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

async def get_config(db) -> dict:
    """Get GLS configuration from DB."""
    doc = await db.configuracion.find_one({"tipo": "gls_config"}, {"_id": 0})
    return doc.get("datos", {}) if doc else {}


async def save_config(db, config_data: dict):
    """Save GLS configuration to DB."""
    await db.configuracion.update_one(
        {"tipo": "gls_config"},
        {"$set": {"datos": config_data, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )


async def is_gls_active(db) -> bool:
    """Check if GLS integration is active and configured."""
    config = await get_config(db)
    return bool(config.get("activo") and config.get("uid_cliente"))


# ═══════════════════════════════════════════════════════════════════════════════
# AUDITORÍA Y LOGS
# ═══════════════════════════════════════════════════════════════════════════════

async def _log_operation(
    db, 
    shipment_id: str, 
    operation: str, 
    request_summary: str, 
    response_summary: str, 
    error: str = None,
    orden_id: str = None,
    user_email: str = None
):
    """Log a GLS integration operation with full audit trail."""
    await db.gls_logs.insert_one({
        "shipment_id": shipment_id,
        "orden_id": orden_id,
        "tipo_operacion": operation,
        "request_resumen": request_summary[:2000] if request_summary else "",
        "response_resumen": response_summary[:2000] if response_summary else "",
        "error": error,
        "usuario": user_email,
        "fecha": datetime.now(timezone.utc).isoformat(),
    })


async def _add_orden_historial(db, orden_id: str, mensaje: str, user_email: str, tipo: str = "logistica"):
    """Add entry to order's historial for traceability."""
    if not orden_id:
        return
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "fecha": now,
        "tipo": tipo,
        "mensaje": mensaje,
        "usuario": user_email,
        "sistema": "GLS",
    }
    await db.ordenes.update_one(
        {"id": orden_id},
        {"$push": {"historial_logistica": entry}, "$set": {"updated_at": now}}
    )


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDACIONES Y PREVENCIÓN DE DUPLICADOS
# ═══════════════════════════════════════════════════════════════════════════════

async def check_duplicate_shipment(db, orden_id: str, tipo: ShipmentType) -> Optional[dict]:
    """
    Check if there's already an active shipment of this type for the order.
    Returns the existing shipment if found, None otherwise.
    """
    if not orden_id:
        return None
    
    # Buscar envíos activos (no anulados, no en error) del mismo tipo para esta orden
    existing = await db.gls_shipments.find_one({
        "entidad_id": orden_id,
        "tipo": tipo,
        "estado_interno": {"$nin": ["anulado", "error", "devuelto", "cerrado"]},
    }, {"_id": 0, "id": 1, "gls_codbarras": 1, "estado_interno": 1, "created_at": 1})
    
    return existing


async def validate_shipment_data(data: dict, tipo: ShipmentType) -> tuple[bool, str]:
    """Validate shipment data before creation."""
    errors = []
    
    # Campos obligatorios para todos los tipos
    if not data.get("dest_nombre"):
        errors.append("Nombre del destinatario es obligatorio")
    if not data.get("dest_direccion"):
        errors.append("Dirección del destinatario es obligatoria")
    if not data.get("dest_cp"):
        errors.append("Código postal del destinatario es obligatorio")
    if not data.get("dest_telefono"):
        errors.append("Teléfono del destinatario es obligatorio para el transportista")
    
    # Validaciones específicas
    if data.get("dest_cp") and (len(str(data["dest_cp"])) != 5 or not str(data["dest_cp"]).isdigit()):
        errors.append("El código postal debe tener 5 dígitos")
    
    if data.get("bultos", 1) < 1:
        errors.append("El número de bultos debe ser al menos 1")
    
    if data.get("peso", 1) <= 0:
        errors.append("El peso debe ser mayor que 0")
    
    if errors:
        return False, "; ".join(errors)
    return True, ""


# ═══════════════════════════════════════════════════════════════════════════════
# CREACIÓN DE ENVÍOS
# ═══════════════════════════════════════════════════════════════════════════════

async def create_shipment(
    db, 
    data: dict, 
    user_email: str,
    skip_duplicate_check: bool = False,
    notify_client: bool = False
) -> dict:
    """
    Create a GLS shipment (envio, recogida, or devolucion).
    
    Args:
        db: Database connection
        data: Shipment data dict
        user_email: User creating the shipment
        skip_duplicate_check: If True, skip duplicate validation (for forced re-creation)
        notify_client: If True, send notification to client after creation
    
    Returns: {"success": bool, "shipment": dict, "error": str, "duplicate": bool}
    """
    config = await get_config(db)
    uid_cliente = config.get("uid_cliente", "")

    if not config.get("activo") or not uid_cliente:
        return {"success": False, "error": "Integración GLS no activada o sin UID de cliente configurado."}

    tipo = data.get("tipo", "envio")
    orden_id = data.get("orden_id", "")

    # Validar datos
    valid, validation_error = await validate_shipment_data(data, tipo)
    if not valid:
        return {"success": False, "error": validation_error}

    # Verificar duplicados
    if not skip_duplicate_check and orden_id:
        existing = await check_duplicate_shipment(db, orden_id, tipo)
        if existing:
            return {
                "success": False, 
                "error": f"Ya existe un {tipo} activo para esta orden (código: {existing.get('gls_codbarras', 'N/A')}). Anúlalo primero o usa 'forzar creación'.",
                "duplicate": True,
                "existing_shipment": existing
            }

    # Set defaults from config
    if not data.get("servicio"):
        data["servicio"] = config.get("servicio_defecto", "96")
    if not data.get("horario"):
        data["horario"] = config.get("horario_defecto", "18")

    # Generate internal reference
    if not data.get("referencia"):
        # Intentar usar número de orden si existe
        if orden_id:
            orden = await db.ordenes.find_one({"id": orden_id}, {"_id": 0, "numero_orden": 1})
            if orden:
                data["referencia"] = (orden.get("numero_orden") or orden_id)[:20]
            else:
                data["referencia"] = orden_id[:20]
        else:
            data["referencia"] = str(uuid.uuid4())[:8]

    # Para devoluciones, intercambiar remitente y destinatario
    if tipo == "devolucion":
        data["tipo"] = "envio"  # GLS lo procesa como envío normal
        # El destinatario original se convierte en remitente (desde donde devuelven)
        # Revix (config) se convierte en destinatario (hacia donde devuelven)

    # Call GLS SOAP
    result = await graba_servicios(uid_cliente, config, data)

    # Create shipment record
    shipment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    envio_data = result.get("envios", [{}])[0] if result.get("envios") else {}
    codbarras = envio_data.get("codbarras", "")

    # Obtener etiqueta inline si fue solicitada y está disponible
    label_base64 = envio_data.get("label_base64", "")

    shipment = {
        "id": shipment_id,
        "entidad_tipo": data.get("entidad_tipo", "orden"),
        "entidad_id": orden_id,
        "cliente_id": data.get("cliente_id", ""),
        "tipo": tipo if tipo != "devolucion" else "devolucion",  # Mantener tipo original para tracking
        "gls_codexp": envio_data.get("codexp", ""),
        "gls_uid": envio_data.get("uid", ""),
        "gls_codbarras": codbarras,
        "tracking_url": get_tracking_url(codbarras),
        "referencia_interna": data.get("referencia", ""),
        "servicio": data.get("servicio", ""),
        "horario": data.get("horario", ""),
        "estado_interno": "grabado" if result["success"] else "error",
        "estado_gls_codigo": -10 if result["success"] else None,
        "estado_gls_texto": "GRABADO" if result["success"] else "ERROR",
        "es_final": False,
        "incidencia_codigo": None,
        "incidencia_texto": None,
        "entrega_fecha": None,
        "entrega_receptor": None,
        "entrega_dni": None,
        "pod_url": None,
        "fecha_prevista_entrega": None,
        # Almacenar etiqueta para reimpresión sin llamar a GLS
        "label_base64": label_base64,
        "label_generada": bool(label_base64),
        "label_formato": data.get("formato_etiqueta", "PDF"),
        "bultos": data.get("bultos", 1),
        "peso": data.get("peso", 1.0),
        "reembolso": data.get("reembolso", 0.0),
        "observaciones": data.get("dest_observaciones", ""),
        "remitente": {
            "nombre": config.get("remitente_nombre", ""),
            "direccion": config.get("remitente_direccion", ""),
            "poblacion": config.get("remitente_poblacion", ""),
            "cp": config.get("remitente_cp", ""),
            "telefono": config.get("remitente_telefono", ""),
            "email": config.get("remitente_email", ""),
        },
        "destinatario": {
            "nombre": data.get("dest_nombre", ""),
            "direccion": data.get("dest_direccion", ""),
            "poblacion": data.get("dest_poblacion", ""),
            "cp": data.get("dest_cp", ""),
            "telefono": data.get("dest_telefono", ""),
            "email": data.get("dest_email", ""),
        },
        "raw_request": result.get("raw_request", ""),
        "raw_response": result.get("raw_response", ""),
        "tracking_json": None,
        "fecha_ultima_sync": None,
        "sync_status": "ok" if result["success"] else "error",
        "sync_error": "; ".join(result.get("errors", [])) if not result["success"] else None,
        "notificacion_enviada": False,
        "created_by": user_email,
        "updated_by": None,
        "created_at": now,
        "updated_at": now,
    }

    # Persist shipment (exclude _id to let MongoDB generate it)
    shipment_doc = {k: v for k, v in shipment.items() if k != "_id"}
    await db.gls_shipments.insert_one(shipment_doc)

    # Log operation
    await _log_operation(
        db, shipment_id, f"crear_{tipo}",
        f"Referencia: {data.get('referencia', '')} | Destino: {data.get('dest_nombre', '')}",
        f"Success: {result['success']} | Codbarras: {codbarras}",
        error="; ".join(result.get("errors", [])) if not result["success"] else None,
        orden_id=orden_id,
        user_email=user_email
    )

    if result["success"]:
        # Update the order with GLS codes and references
        orden_update = {
            "agencia_envio": "GLS",
            "updated_at": now,
        }
        envio_ref = {
            "id": shipment_id,
            "tipo": tipo,
            "codbarras": codbarras,
            "tracking_url": get_tracking_url(codbarras),
            "estado_gls": "grabado",
            "created_at": now,
            "created_by": user_email,
        }
        
        # Asignar código según tipo
        if tipo == "recogida":
            orden_update["codigo_recogida_entrada"] = codbarras
        elif tipo == "devolucion":
            orden_update["codigo_devolucion"] = codbarras
        else:
            orden_update["codigo_recogida_salida"] = codbarras

        if orden_id:
            await db.ordenes.update_one(
                {"id": orden_id},
                {"$set": orden_update, "$push": {"gls_envios": envio_ref}}
            )
            
            # Añadir al historial de la OT
            tipo_label = {"envio": "Envío", "recogida": "Recogida", "devolucion": "Devolución"}.get(tipo, tipo)
            await _add_orden_historial(
                db, orden_id,
                f"{tipo_label} GLS creado - Código: {codbarras}",
                user_email
            )

        # Notificar al cliente si se solicitó
        if notify_client and data.get("dest_email"):
            await _notify_client_shipment_created(db, shipment, config)

    # Clean response (no raw XML in public response)
    public_shipment = {k: v for k, v in shipment.items() if k not in ("raw_request", "raw_response", "_id", "label_base64")}
    return {
        "success": result["success"], 
        "shipment": public_shipment, 
        "error": "; ".join(result.get("errors", [])) if not result["success"] else None,
        "duplicate": False
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ETIQUETAS (CON ALMACENAMIENTO PERSISTENTE)
# ═══════════════════════════════════════════════════════════════════════════════

async def get_label(db, shipment_id: str, force_refresh: bool = False) -> dict:
    """
    Get label for a shipment. Uses cached version if available.
    
    Args:
        db: Database connection
        shipment_id: Shipment ID
        force_refresh: If True, fetch new label from GLS even if cached
    
    Returns: {"success": bool, "labels": [base64], "formato": str, "cached": bool}
    """
    shipment = await db.gls_shipments.find_one({"id": shipment_id}, {"_id": 0})
    if not shipment:
        return {"success": False, "error": "Envío no encontrado"}

    # Si tenemos etiqueta cacheada y no se fuerza refresh, usarla
    if not force_refresh and shipment.get("label_base64"):
        return {
            "success": True, 
            "labels": [shipment["label_base64"]], 
            "formato": shipment.get("label_formato", "PDF"),
            "cached": True
        }

    # Obtener de GLS
    config = await get_config(db)
    uid = config.get("uid_cliente", "")
    if not uid:
        return {"success": False, "error": "GLS no configurado"}

    codigo = shipment.get("gls_codbarras") or shipment.get("referencia_interna", "")
    if not codigo:
        return {"success": False, "error": "No hay código de barras para obtener etiqueta"}
    
    formato = shipment.get("label_formato", "PDF")
    result = await etiqueta_envio_v2(uid, codigo, formato)

    await _log_operation(
        db, shipment_id, "etiqueta",
        f"Codigo: {codigo} | Formato: {formato}",
        f"Success: {result['success']} | Labels: {len(result.get('labels', []))}",
        error=result.get("error"),
        orden_id=shipment.get("entidad_id")
    )

    if result["success"] and result.get("labels"):
        # Guardar etiqueta en BD para futuras reimpresiones
        await db.gls_shipments.update_one(
            {"id": shipment_id}, 
            {"$set": {
                "label_base64": result["labels"][0],
                "label_generada": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        result["cached"] = False
    
    return result


async def get_label_by_code(db, codigo: str, formato: str = "PDF") -> dict:
    """Get label directly by code (for reprint without shipment_id)."""
    config = await get_config(db)
    uid = config.get("uid_cliente", "")
    if not uid:
        return {"success": False, "error": "GLS no configurado"}
    return await etiqueta_envio_v2(uid, codigo, formato)


# ═══════════════════════════════════════════════════════════════════════════════
# TRACKING Y SINCRONIZACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

async def get_tracking(db, shipment_id: str, notify_on_change: bool = False) -> dict:
    """
    Get full tracking for a shipment and update DB.
    
    Args:
        db: Database connection
        shipment_id: Shipment ID
        notify_on_change: If True, notify client when status changes
    
    Returns: {"success": bool, "expediciones": [...], "shipment": dict}
    """
    config = await get_config(db)
    uid = config.get("uid_cliente", "")
    if not uid:
        return {"success": False, "error": "GLS no configurado"}

    shipment = await db.gls_shipments.find_one({"id": shipment_id}, {"_id": 0})
    if not shipment:
        return {"success": False, "error": "Envío no encontrado"}

    old_state = shipment.get("estado_interno", "")

    # Try GetExp first (by uid), then GetExpCli
    gls_uid = shipment.get("gls_uid")
    if gls_uid:
        result = await get_exp(gls_uid)
    else:
        codigo = shipment.get("gls_codbarras") or shipment.get("referencia_interna", "")
        result = await get_exp_cli(uid, codigo)

    if result["success"] and result["expediciones"]:
        exp = result["expediciones"][0]
        mapped = map_gls_state(exp.get("codestado", ""))
        now = datetime.now(timezone.utc).isoformat()
        new_state = mapped["estado"]

        # Update shipment with tracking data
        update = {
            "estado_interno": new_state,
            "estado_gls_codigo": mapped["gls_code"],
            "estado_gls_texto": exp.get("estado", ""),
            "es_final": mapped["es_final"],
            "tracking_json": result,
            "fecha_ultima_sync": now,
            "updated_at": now,
            "sync_status": "ok",
            "sync_error": None,
        }
        if exp.get("FPEntrega"):
            update["fecha_prevista_entrega"] = exp["FPEntrega"]
        if exp.get("NombreEntrega"):
            update["entrega_receptor"] = exp["NombreEntrega"]
        if exp.get("DniEntrega"):
            update["entrega_dni"] = exp["DniEntrega"]
        if exp.get("pod"):
            update["entrega_fecha"] = exp["pod"]
        if exp.get("incidencia") and exp["incidencia"] != "SIN INCIDENCIA":
            update["incidencia_codigo"] = exp.get("codincidencia")
            update["incidencia_texto"] = exp["incidencia"]
        else:
            update["incidencia_codigo"] = None
            update["incidencia_texto"] = None

        # Extract POD URL
        for dig in exp.get("digitalizaciones", []):
            if dig.get("codtipo") == "1" and dig.get("imagen"):
                update["pod_url"] = dig["imagen"]
                break

        await db.gls_shipments.update_one({"id": shipment_id}, {"$set": update})

        # Save new tracking events
        new_events_count = 0
        for track in exp.get("tracking_list", []):
            exists = await db.gls_tracking_events.find_one({
                "shipment_id": shipment_id,
                "fecha_evento": track.get("fecha", ""),
                "codigo_evento": track.get("codigo", ""),
                "tipo": track.get("tipo", ""),
            })
            if not exists:
                await db.gls_tracking_events.insert_one({
                    "shipment_id": shipment_id,
                    "orden_id": shipment.get("entidad_id"),
                    "fecha_evento": track.get("fecha", ""),
                    "tipo": track.get("tipo", ""),
                    "codigo_evento": track.get("codigo", ""),
                    "descripcion_evento": track.get("evento", ""),
                    "plaza": track.get("plaza", ""),
                    "nombre_plaza": track.get("nombreplaza", ""),
                    "raw_event": track,
                    "created_at": now,
                })
                new_events_count += 1

        # Update order's gls_envios array
        if shipment.get("entidad_id"):
            await db.ordenes.update_one(
                {"id": shipment["entidad_id"], "gls_envios.id": shipment_id},
                {"$set": {
                    "gls_envios.$.estado_gls": new_state,
                    "gls_envios.$.es_final": mapped["es_final"],
                    "gls_envios.$.ultima_sync": now,
                }}
            )
            
            # Si el estado cambió, añadir al historial de la OT
            if old_state != new_state:
                badge = STATE_BADGES.get(new_state, {})
                await _add_orden_historial(
                    db, shipment["entidad_id"],
                    f"Estado GLS actualizado: {old_state} → {new_state} ({badge.get('label', new_state)})",
                    "sistema"
                )
                
                # Notificar al cliente si está habilitado
                if notify_on_change and shipment.get("destinatario", {}).get("email"):
                    await _notify_client_status_change(db, shipment, old_state, new_state, config)

        result["new_events"] = new_events_count
        result["state_changed"] = old_state != new_state

    await _log_operation(
        db, shipment_id, "tracking",
        f"UID: {shipment.get('gls_uid', '')} | Codbarras: {shipment.get('gls_codbarras', '')}",
        f"Success: {result['success']} | Estado: {result.get('expediciones', [{}])[0].get('estado', '') if result.get('expediciones') else 'N/A'}",
        orden_id=shipment.get("entidad_id")
    )

    # Añadir datos del shipment actualizado
    updated_shipment = await db.gls_shipments.find_one({"id": shipment_id}, {"_id": 0, "raw_request": 0, "raw_response": 0, "label_base64": 0})
    result["shipment"] = updated_shipment

    return result


async def sync_shipments(db, notify_on_change: bool = False) -> dict:
    """
    Sync all non-final shipments. Returns stats.
    
    Args:
        db: Database connection
        notify_on_change: If True, notify clients when status changes
    
    Returns: {"synced": int, "errors": int, "state_changes": int, ...}
    """
    config = await get_config(db)
    uid = config.get("uid_cliente", "")
    if not uid:
        return {"synced": 0, "errors": 0, "skipped": 0, "message": "GLS no configurado"}

    cursor = db.gls_shipments.find(
        {"es_final": False, "estado_interno": {"$nin": ["error", "anulado"]}},
        {"_id": 0, "id": 1, "gls_uid": 1, "gls_codbarras": 1, "referencia_interna": 1, "estado_interno": 1}
    )
    shipments = await cursor.to_list(500)

    synced, errors, skipped, state_changes = 0, 0, 0, 0
    for s in shipments:
        try:
            result = await get_tracking(db, s["id"], notify_on_change=notify_on_change)
            if result.get("success"):
                synced += 1
                if result.get("state_changed"):
                    state_changes += 1
            else:
                errors += 1
        except Exception as e:
            logger.error(f"Sync error for {s['id']}: {e}")
            errors += 1

    return {
        "synced": synced, 
        "errors": errors, 
        "total": len(shipments), 
        "skipped": skipped,
        "state_changes": state_changes
    }


async def sync_orden_shipments(db, orden_id: str) -> dict:
    """Sync all shipments for a specific order."""
    cursor = db.gls_shipments.find(
        {"entidad_id": orden_id, "es_final": False, "estado_interno": {"$nin": ["error", "anulado"]}},
        {"_id": 0, "id": 1}
    )
    shipments = await cursor.to_list(50)
    
    results = []
    for s in shipments:
        result = await get_tracking(db, s["id"])
        results.append({"id": s["id"], "success": result.get("success", False)})
    
    return {"shipments": results, "total": len(shipments)}


# ═══════════════════════════════════════════════════════════════════════════════
# ANULACIÓN Y GESTIÓN
# ═══════════════════════════════════════════════════════════════════════════════

async def cancel_shipment(db, shipment_id: str, user_email: str, motivo: str = "") -> dict:
    """Cancel/annul a GLS shipment (mark as anulado internally)."""
    shipment = await db.gls_shipments.find_one({"id": shipment_id}, {"_id": 0})
    if not shipment:
        return {"success": False, "error": "Envío no encontrado"}
    if shipment.get("es_final"):
        return {"success": False, "error": "No se puede anular un envío en estado final"}

    now = datetime.now(timezone.utc).isoformat()
    await db.gls_shipments.update_one({"id": shipment_id}, {"$set": {
        "estado_interno": "anulado",
        "estado_gls_texto": "ANULADO (manual)",
        "es_final": True,
        "motivo_anulacion": motivo,
        "updated_by": user_email,
        "updated_at": now,
    }})

    orden_id = shipment.get("entidad_id")
    if orden_id:
        await db.ordenes.update_one(
            {"id": orden_id, "gls_envios.id": shipment_id},
            {"$set": {"gls_envios.$.estado_gls": "anulado", "gls_envios.$.es_final": True}}
        )
        
        await _add_orden_historial(
            db, orden_id,
            f"Envío GLS anulado - Código: {shipment.get('gls_codbarras', 'N/A')}" + (f" - Motivo: {motivo}" if motivo else ""),
            user_email
        )

    await _log_operation(
        db, shipment_id, "anular",
        f"Anulado por {user_email}" + (f" - Motivo: {motivo}" if motivo else ""),
        "OK",
        orden_id=orden_id,
        user_email=user_email
    )

    return {"success": True}


# ═══════════════════════════════════════════════════════════════════════════════
# LISTADOS Y CONSULTAS
# ═══════════════════════════════════════════════════════════════════════════════

async def list_shipments(db, filters: dict = None, page: int = 1, limit: int = 50) -> dict:
    """List shipments with pagination and filters."""
    query = {}
    if filters:
        if filters.get("entidad_id"):
            query["entidad_id"] = filters["entidad_id"]
        if filters.get("estado_interno"):
            query["estado_interno"] = filters["estado_interno"]
        if filters.get("tipo"):
            query["tipo"] = filters["tipo"]
        if filters.get("es_final") is not None:
            query["es_final"] = filters["es_final"]
        if filters.get("search"):
            s = filters["search"]
            query["$or"] = [
                {"gls_codbarras": {"$regex": s, "$options": "i"}},
                {"referencia_interna": {"$regex": s, "$options": "i"}},
                {"destinatario.nombre": {"$regex": s, "$options": "i"}},
                {"gls_codexp": {"$regex": s, "$options": "i"}},
            ]
        if filters.get("fecha_desde"):
            query.setdefault("created_at", {})["$gte"] = filters["fecha_desde"]
        if filters.get("fecha_hasta"):
            query.setdefault("created_at", {})["$lte"] = filters["fecha_hasta"]

    total = await db.gls_shipments.count_documents(query)
    skip = (page - 1) * limit
    cursor = db.gls_shipments.find(
        query, 
        {"_id": 0, "raw_request": 0, "raw_response": 0, "label_base64": 0, "tracking_json": 0}
    ).sort("created_at", -1).skip(skip).limit(limit)
    items = await cursor.to_list(limit)

    return {"data": items, "total": total, "page": page, "limit": limit}


async def get_shipment_detail(db, shipment_id: str, include_raw: bool = False, include_label: bool = False) -> dict:
    """Get full shipment detail including tracking events and logs."""
    projection = {"_id": 0}
    if not include_raw:
        projection["raw_request"] = 0
        projection["raw_response"] = 0
    if not include_label:
        projection["label_base64"] = 0

    shipment = await db.gls_shipments.find_one({"id": shipment_id}, projection)
    if not shipment:
        return None

    events = await db.gls_tracking_events.find(
        {"shipment_id": shipment_id}, {"_id": 0}
    ).sort("fecha_evento", -1).to_list(200)

    logs = await db.gls_logs.find(
        {"shipment_id": shipment_id}, {"_id": 0}
    ).sort("fecha", -1).to_list(50)

    shipment["eventos"] = events
    shipment["logs"] = logs
    
    # Añadir badge info para UI
    estado = shipment.get("estado_interno", "")
    shipment["estado_badge"] = STATE_BADGES.get(estado, {"color": "bg-gray-100", "label": estado})
    
    return shipment


async def get_orden_logistics(db, orden_id: str) -> dict:
    """Get all logistics data for an order."""
    # Obtener config
    config = await get_config(db)
    gls_activo = bool(config.get("activo") and config.get("uid_cliente"))
    
    # Obtener todos los envíos de la orden
    cursor = db.gls_shipments.find(
        {"entidad_id": orden_id},
        {"_id": 0, "raw_request": 0, "raw_response": 0, "label_base64": 0, "tracking_json": 0}
    ).sort("created_at", -1)
    shipments = await cursor.to_list(50)
    
    # Organizar por tipo
    recogidas = [s for s in shipments if s.get("tipo") == "recogida"]
    envios = [s for s in shipments if s.get("tipo") == "envio"]
    devoluciones = [s for s in shipments if s.get("tipo") == "devolucion"]
    
    # Obtener eventos de tracking del más reciente de cada tipo
    async def get_eventos(shipment_id):
        if not shipment_id:
            return []
        return await db.gls_tracking_events.find(
            {"shipment_id": shipment_id}, {"_id": 0}
        ).sort("fecha_evento", -1).limit(10).to_list(10)
    
    recogida_eventos = await get_eventos(recogidas[0]["id"]) if recogidas else []
    envio_eventos = await get_eventos(envios[0]["id"]) if envios else []
    devolucion_eventos = await get_eventos(devoluciones[0]["id"]) if devoluciones else []
    
    return {
        "gls_activo": gls_activo,
        "recogida": {
            "shipment": recogidas[0] if recogidas else None,
            "eventos": recogida_eventos,
            "total": len(recogidas),
            "historial": recogidas[1:] if len(recogidas) > 1 else []
        },
        "envio": {
            "shipment": envios[0] if envios else None,
            "eventos": envio_eventos,
            "total": len(envios),
            "historial": envios[1:] if len(envios) > 1 else []
        },
        "devolucion": {
            "shipment": devoluciones[0] if devoluciones else None,
            "eventos": devolucion_eventos,
            "total": len(devoluciones),
            "historial": devoluciones[1:] if len(devoluciones) > 1 else []
        },
        "total_envios": len(shipments),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICACIONES AL CLIENTE
# ═══════════════════════════════════════════════════════════════════════════════

async def _notify_client_shipment_created(db, shipment: dict, config: dict):
    """Send notification to client when shipment is created."""
    try:
        from email_service import send_email
        
        tipo_label = {"envio": "envío", "recogida": "recogida", "devolucion": "devolución"}.get(shipment.get("tipo"), "envío")
        email = shipment.get("destinatario", {}).get("email")
        if not email:
            return
        
        tracking_url = shipment.get("tracking_url", "")
        codbarras = shipment.get("gls_codbarras", "")
        
        subject = f"Tu {tipo_label} GLS ha sido generado - {codbarras}"
        html_content = f"""
        <h2>Tu {tipo_label} ha sido generado</h2>
        <p>Hola {shipment.get('destinatario', {}).get('nombre', '')},</p>
        <p>Te informamos que tu {tipo_label} con GLS ha sido creado correctamente.</p>
        <p><strong>Código de seguimiento:</strong> {codbarras}</p>
        <p><a href="{tracking_url}" style="background-color: #FFA500; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Seguir envío</a></p>
        <p>Saludos,<br>{config.get('remitente_nombre', 'El equipo')}</p>
        """
        
        await send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
        
        # Marcar como notificado
        await db.gls_shipments.update_one(
            {"id": shipment["id"]},
            {"$set": {"notificacion_enviada": True, "notificacion_fecha": datetime.now(timezone.utc).isoformat()}}
        )
        
    except Exception as e:
        logger.error(f"Error sending shipment notification: {e}")


async def _notify_client_status_change(db, shipment: dict, old_state: str, new_state: str, config: dict):
    """Send notification to client when shipment status changes."""
    try:
        from email_service import send_email
        
        email = shipment.get("destinatario", {}).get("email")
        if not email:
            return
        
        # Solo notificar cambios importantes
        important_states = ["en_reparto", "entregado", "devuelto", "incidencia"]
        if new_state not in important_states:
            return
        
        badge = STATE_BADGES.get(new_state, {})
        state_label = badge.get("label", new_state)
        codbarras = shipment.get("gls_codbarras", "")
        tracking_url = shipment.get("tracking_url", "")
        
        subject = f"Actualización de tu envío GLS - {state_label}"
        html_content = f"""
        <h2>Tu envío tiene un nuevo estado</h2>
        <p>Hola {shipment.get('destinatario', {}).get('nombre', '')},</p>
        <p>El estado de tu envío ha cambiado a: <strong>{state_label}</strong></p>
        <p><strong>Código de seguimiento:</strong> {codbarras}</p>
        <p><a href="{tracking_url}" style="background-color: #FFA500; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Ver detalles</a></p>
        <p>Saludos,<br>{config.get('remitente_nombre', 'El equipo')}</p>
        """
        
        await send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
        
    except Exception as e:
        logger.error(f"Error sending status change notification: {e}")


async def notify_client(db, shipment_id: str, tipo_notificacion: str = "tracking") -> dict:
    """Manually trigger client notification for a shipment."""
    shipment = await db.gls_shipments.find_one({"id": shipment_id}, {"_id": 0})
    if not shipment:
        return {"success": False, "error": "Envío no encontrado"}
    
    email = shipment.get("destinatario", {}).get("email")
    if not email:
        return {"success": False, "error": "El destinatario no tiene email configurado"}
    
    config = await get_config(db)
    
    try:
        if tipo_notificacion == "creacion":
            await _notify_client_shipment_created(db, shipment, config)
        else:
            # Notificación de tracking genérica
            await _notify_client_status_change(db, shipment, "", shipment.get("estado_interno", ""), config)
        
        return {"success": True, "message": f"Notificación enviada a {email}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

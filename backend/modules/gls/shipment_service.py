"""
GLS Shipment Service - Business logic layer.
Orchestrates SOAP calls, persistence, state mapping, and event handling.
"""
import uuid
import logging
from datetime import datetime, timezone

from modules.gls.soap_client import graba_servicios, etiqueta_envio_v2, get_exp, get_exp_cli
from modules.gls.state_mapper import map_gls_state, is_final_state

logger = logging.getLogger("gls.shipment")


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


async def _log_operation(db, shipment_id: str, operation: str, request_summary: str, response_summary: str, error: str = None):
    """Log a GLS integration operation."""
    await db.gls_logs.insert_one({
        "shipment_id": shipment_id,
        "tipo_operacion": operation,
        "request_resumen": request_summary[:2000],
        "response_resumen": response_summary[:2000],
        "error": error,
        "fecha": datetime.now(timezone.utc).isoformat(),
    })


async def create_shipment(db, data: dict, user_email: str) -> dict:
    """Create a GLS shipment (envio or recogida).
    
    Returns: {"success": bool, "shipment": dict, "error": str}
    """
    config = await get_config(db)
    uid_cliente = config.get("uid_cliente", "")

    if not config.get("activo") or not uid_cliente:
        return {"success": False, "error": "Integración GLS no activada o sin UID de cliente configurado."}

    # Validate required fields
    if not data.get("dest_nombre") or not data.get("dest_direccion") or not data.get("dest_cp"):
        return {"success": False, "error": "Faltan datos obligatorios del destinatario (nombre, dirección, CP)."}

    # Set defaults from config
    if not data.get("servicio"):
        data["servicio"] = config.get("servicio_defecto", "96")
    if not data.get("horario"):
        data["horario"] = config.get("horario_defecto", "18")

    # Generate internal reference
    orden_id = data.get("orden_id", "")
    if not data.get("referencia"):
        data["referencia"] = orden_id[:20] if orden_id else str(uuid.uuid4())[:8]

    tipo = data.get("tipo", "envio")

    # Call GLS SOAP
    result = await graba_servicios(uid_cliente, config, data)

    # Create shipment record
    shipment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    envio_data = result.get("envios", [{}])[0] if result.get("envios") else {}

    shipment = {
        "id": shipment_id,
        "entidad_tipo": data.get("entidad_tipo", "orden"),
        "entidad_id": orden_id,
        "cliente_id": data.get("cliente_id", ""),
        "tipo": tipo,
        "gls_codexp": envio_data.get("codexp", ""),
        "gls_uid": envio_data.get("uid", ""),
        "gls_codbarras": envio_data.get("codbarras", ""),
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
        "label_generada": bool(envio_data.get("label_base64")),
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
        f"Success: {result['success']} | Codbarras: {envio_data.get('codbarras', '')}",
        error="; ".join(result.get("errors", [])) if not result["success"] else None
    )

    if result["success"]:
        # Update the order with GLS codes
        orden_update = {
            "agencia_envio": "GLS",
        }
        envio_ref = {
            "id": shipment_id,
            "tipo": tipo,
            "codbarras": envio_data.get("codbarras", ""),
            "estado_gls": "grabado",
            "created_at": now,
            "created_by": user_email,
        }
        if tipo == "recogida":
            orden_update["codigo_recogida_entrada"] = envio_data.get("codbarras", "")
        else:
            orden_update["codigo_recogida_salida"] = envio_data.get("codbarras", "")

        if orden_id:
            await db.ordenes.update_one(
                {"id": orden_id},
                {"$set": orden_update, "$push": {"gls_envios": envio_ref}}
            )

    # Clean response (no raw XML in public response)
    public_shipment = {k: v for k, v in shipment.items() if k not in ("raw_request", "raw_response", "_id")}
    return {"success": result["success"], "shipment": public_shipment, "error": "; ".join(result.get("errors", [])) if not result["success"] else None}


async def get_label(db, shipment_id: str) -> dict:
    """Get label for a shipment."""
    config = await get_config(db)
    uid = config.get("uid_cliente", "")
    if not uid:
        return {"success": False, "error": "GLS no configurado"}

    shipment = await db.gls_shipments.find_one({"id": shipment_id}, {"_id": 0})
    if not shipment:
        return {"success": False, "error": "Envío no encontrado"}

    codigo = shipment.get("gls_codbarras") or shipment.get("referencia_interna", "")
    formato = shipment.get("label_formato", "PDF")

    result = await etiqueta_envio_v2(uid, codigo, formato)

    await _log_operation(db, shipment_id, "etiqueta",
        f"Codigo: {codigo} | Formato: {formato}",
        f"Success: {result['success']} | Labels: {len(result.get('labels', []))}",
        error=result.get("error"))

    if result["success"]:
        await db.gls_shipments.update_one({"id": shipment_id}, {"$set": {"label_generada": True}})

    return result


async def get_label_by_code(db, codigo: str, formato: str = "PDF") -> dict:
    """Get label directly by code (for reprint without shipment_id)."""
    config = await get_config(db)
    uid = config.get("uid_cliente", "")
    if not uid:
        return {"success": False, "error": "GLS no configurado"}
    return await etiqueta_envio_v2(uid, codigo, formato)


async def get_tracking(db, shipment_id: str) -> dict:
    """Get full tracking for a shipment."""
    config = await get_config(db)
    uid = config.get("uid_cliente", "")
    if not uid:
        return {"success": False, "error": "GLS no configurado"}

    shipment = await db.gls_shipments.find_one({"id": shipment_id}, {"_id": 0})
    if not shipment:
        return {"success": False, "error": "Envío no encontrado"}

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

        # Update shipment with tracking data
        update = {
            "estado_interno": mapped["estado"],
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
            update["incidencia_texto"] = exp["incidencia"]

        # Extract POD URL
        for dig in exp.get("digitalizaciones", []):
            if dig.get("codtipo") == "1" and dig.get("imagen"):
                update["pod_url"] = dig["imagen"]
                break

        await db.gls_shipments.update_one({"id": shipment_id}, {"$set": update})

        # Save new tracking events
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
                    "fecha_evento": track.get("fecha", ""),
                    "tipo": track.get("tipo", ""),
                    "codigo_evento": track.get("codigo", ""),
                    "descripcion_evento": track.get("evento", ""),
                    "plaza": track.get("plaza", ""),
                    "nombre_plaza": track.get("nombreplaza", ""),
                    "raw_event": track,
                })

        # Update order's gls_envios array
        if shipment.get("entidad_id"):
            await db.ordenes.update_one(
                {"id": shipment["entidad_id"], "gls_envios.id": shipment_id},
                {"$set": {"gls_envios.$.estado_gls": mapped["estado"]}}
            )

    await _log_operation(db, shipment_id, "tracking",
        f"UID: {shipment.get('gls_uid', '')} | Codbarras: {shipment.get('gls_codbarras', '')}",
        f"Success: {result['success']} | Estado: {result.get('expediciones', [{}])[0].get('estado', '') if result.get('expediciones') else 'N/A'}")

    return result


async def sync_shipments(db) -> dict:
    """Sync all non-final shipments. Returns stats."""
    config = await get_config(db)
    uid = config.get("uid_cliente", "")
    if not uid:
        return {"synced": 0, "errors": 0, "skipped": 0, "message": "GLS no configurado"}

    cursor = db.gls_shipments.find(
        {"es_final": False, "estado_interno": {"$ne": "error"}},
        {"_id": 0, "id": 1, "gls_uid": 1, "gls_codbarras": 1, "referencia_interna": 1}
    )
    shipments = await cursor.to_list(500)

    synced, errors, skipped = 0, 0, 0
    for s in shipments:
        try:
            result = await get_tracking(db, s["id"])
            if result.get("success"):
                synced += 1
            else:
                errors += 1
        except Exception as e:
            logger.error(f"Sync error for {s['id']}: {e}")
            errors += 1

    return {"synced": synced, "errors": errors, "total": len(shipments), "skipped": skipped}


async def cancel_shipment(db, shipment_id: str, user_email: str) -> dict:
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
        "updated_by": user_email,
        "updated_at": now,
    }})

    if shipment.get("entidad_id"):
        await db.ordenes.update_one(
            {"id": shipment["entidad_id"], "gls_envios.id": shipment_id},
            {"$set": {"gls_envios.$.estado_gls": "anulado"}}
        )

    await _log_operation(db, shipment_id, "anular",
        f"Anulado por {user_email}", "OK")

    return {"success": True}


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
    cursor = db.gls_shipments.find(query, {"_id": 0, "raw_request": 0, "raw_response": 0}).sort("created_at", -1).skip(skip).limit(limit)
    items = await cursor.to_list(limit)

    return {"data": items, "total": total, "page": page, "limit": limit}


async def get_shipment_detail(db, shipment_id: str, include_raw: bool = False) -> dict:
    """Get full shipment detail including tracking events and logs."""
    projection = {"_id": 0}
    if not include_raw:
        projection["raw_request"] = 0
        projection["raw_response"] = 0

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
    return shipment

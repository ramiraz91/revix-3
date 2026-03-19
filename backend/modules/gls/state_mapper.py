"""
GLS State Mapper - Central state mapping between GLS codes and internal CRM states.
Source of truth: ES-GLS-Maestros_V2.xlsx
"""

# ─── GLS Shipment States (from Maestros) ──────────────────────────
GLS_SHIPMENT_STATES = {
    -10: {"desc": "GRABADO", "final": False},
    0:   {"desc": "MANIFESTADA", "final": False},
    2:   {"desc": "EN TRANSITO A DESTINO", "final": False},
    3:   {"desc": "EN DELEGACION DESTINO", "final": False},
    5:   {"desc": "ANULADA", "final": False},
    6:   {"desc": "EN REPARTO", "final": False},
    7:   {"desc": "ENTREGADO", "final": True},
    8:   {"desc": "ENTREGA PARCIAL", "final": False},
    9:   {"desc": "ALMACENADO", "final": False},
    10:  {"desc": "DEVUELTA", "final": False},
    12:  {"desc": "DEVUELTA AL CLIENTE", "final": True},
    14:  {"desc": "SOLICITUD DE DEVOLUCION", "final": False},
    15:  {"desc": "EN DEVOLUCION", "final": False},
    17:  {"desc": "DESTRUIDO POR ORDEN DEL CLIENTE", "final": True},
    18:  {"desc": "RETENIDO POR ORDEN DE PAGA", "final": False},
    19:  {"desc": "EN PLATAFORMA DE DESTINO", "final": False},
    20:  {"desc": "CERRADO POR SINIESTRO", "final": True},
    21:  {"desc": "RECANALIZADA", "final": False},
    22:  {"desc": "POSICIONADO EN PARCELSHOP", "final": False},
    25:  {"desc": "PARCELSHOP CONFIRMA RECEPCION", "final": False},
    90:  {"desc": "CERRADO DEFINITIVO", "final": True},
}

# ─── GLS Pickup States (from Maestros) ──────────────────────────
GLS_PICKUP_STATES = {
    0:  {"desc": "Anulada", "final": True},
    1:  {"desc": "Solicitada", "final": False},
    2:  {"desc": "Realizada con éxito", "final": True},
    3:  {"desc": "No Realizada", "final": False},
    4:  {"desc": "Recibida", "final": False},
    5:  {"desc": "Realizada con Incidencia", "final": True},
    6:  {"desc": "Recogido en Cliente", "final": False},
    7:  {"desc": "Recepcionada en Agencia", "final": False},
    9:  {"desc": "Asignada", "final": False},
    10: {"desc": "A preconfirmar", "final": False},
    16: {"desc": "Recogida pendiente de etiquetar", "final": False},
}

# ─── GLS → Internal State Mapping ──────────────────────────
# Maps GLS codestado (int) to our internal state string
_GLS_TO_INTERNAL = {
    -10: "grabado",
    0:   "manifestado",
    2:   "en_transito",
    19:  "en_transito",
    3:   "en_delegacion",
    9:   "en_delegacion",
    6:   "en_reparto",
    22:  "en_parcelshop",
    25:  "en_parcelshop",
    7:   "entregado",
    8:   "entregado_parcial",
    5:   "anulado",
    14:  "en_devolucion",
    15:  "en_devolucion",
    10:  "devuelto",
    12:  "devuelto",
    17:  "cerrado",
    18:  "retenido",
    20:  "cerrado",
    21:  "recanalizado",
    90:  "cerrado",
}

# Internal states that are considered final (no more sync needed)
FINAL_INTERNAL_STATES = {"entregado", "devuelto", "cerrado", "anulado"}

# ─── GLS Incidences ──────────────────────────
GLS_INCIDENCES = {
    2: "METEOROLOGIA", 3: "FALTA EXPEDICION COMPLETA", 4: "FALTAN BULTOS",
    8: "CLASIFICACION EN PLATAFORMA", 9: "AUSENTE", 10: "NO ACEPTA EXPEDICION",
    11: "NO ACEPTA P.DEBIDO Y/O REEMBOLSO", 12: "FALTAN DATOS",
    13: "DIRECCION INCORRECTA", 14: "CAMBIO DOMICILIO", 15: "AUSENTE SEGUNDA VEZ",
    18: "RETRASO EN RUTA NACIONAL", 19: "RETORNO NO PREPARADO",
    20: "ROBADA PARTE DE LA MERCANCIA", 21: "DETERIORADA", 23: "ROBADA",
    24: "EN AEROPUERTO", 25: "EN ADUANA", 26: "CERRADO POR VACACIONES",
    29: "MAL DOCUMENTADA", 40: "FESTIVO", 42: "NO ACEPTA FIRMA ALBARAN DAC",
    43: "FALTA ALBARAN DAC", 44: "DPTO. INSULAR: RETENIDA",
    45: "NO TIENE DINERO", 48: "NO ENLAZA", 64: "EXCEDIDO TIEMPO ESPERA GG.SS",
    69: "ENTREGA EN MAX 72H", 70: "DNI NO COINCIDENTE", 71: "CLASIFICACION RED",
    72: "RET. EN INSULAR FALTA DOCUMENTACION", 73: "TRANSITO MARITIMO SEMANAL",
    74: "AEREO +24H", 75: "EN TRANSITO POR AVERIA",
}

# ─── GLS Services ──────────────────────────
GLS_SERVICES = {
    "1":  "Express / Courier",
    "6":  "CARGA",
    "12": "INTERNACIONAL EXPRESS",
    "13": "INTERNACIONAL ECONOMY",
    "30": "Express 8:30",
    "37": "ECONOMYPARCEL",
    "74": "EUROBUSINESS PARCEL",
    "76": "EUROBUSINESS SMALL PARCEL",
    "96": "BusinessParcel",
    "99": "TRACKED24",
}

GLS_SCHEDULES = {
    "0":  "Express 10:30",
    "2":  "Express 14:00",
    "3":  "Express 19:00 (24h)",
    "5":  "Saturday Service",
    "10": "Maritimo",
    "11": "Rec. en agencia",
    "16": "Economy",
    "17": "Express (Int.)",
    "18": "BusinessParcel / EconomyParcel",
    "19": "ParcelShop",
}

# UI badge colors for internal states
STATE_BADGES = {
    "grabado":          {"color": "bg-slate-100 text-slate-700", "label": "Grabado"},
    "manifestado":      {"color": "bg-blue-100 text-blue-700", "label": "Manifestado"},
    "en_transito":      {"color": "bg-indigo-100 text-indigo-700", "label": "En tránsito"},
    "en_delegacion":    {"color": "bg-cyan-100 text-cyan-700", "label": "En delegación"},
    "en_reparto":       {"color": "bg-purple-100 text-purple-700", "label": "En reparto"},
    "en_parcelshop":    {"color": "bg-teal-100 text-teal-700", "label": "En ParcelShop"},
    "entregado":        {"color": "bg-green-100 text-green-700", "label": "Entregado"},
    "entregado_parcial": {"color": "bg-lime-100 text-lime-700", "label": "Entrega parcial"},
    "en_devolucion":    {"color": "bg-orange-100 text-orange-700", "label": "En devolución"},
    "devuelto":         {"color": "bg-red-100 text-red-700", "label": "Devuelto"},
    "anulado":          {"color": "bg-gray-100 text-gray-500", "label": "Anulado"},
    "retenido":         {"color": "bg-amber-100 text-amber-700", "label": "Retenido"},
    "recanalizado":     {"color": "bg-yellow-100 text-yellow-700", "label": "Recanalizado"},
    "cerrado":          {"color": "bg-gray-200 text-gray-700", "label": "Cerrado"},
    "incidencia":       {"color": "bg-red-100 text-red-700", "label": "Incidencia"},
}


def map_gls_state(codestado) -> dict:
    """Map a GLS codestado to internal state info."""
    try:
        code = int(codestado)
    except (ValueError, TypeError):
        return {"estado": "desconocido", "es_final": False, "gls_desc": "Desconocido"}

    gls_info = GLS_SHIPMENT_STATES.get(code, {})
    internal = _GLS_TO_INTERNAL.get(code, "desconocido")

    return {
        "estado": internal,
        "es_final": gls_info.get("final", False),
        "gls_desc": gls_info.get("desc", f"Estado {code}"),
        "gls_code": code,
    }


def is_final_state(internal_state: str) -> bool:
    """Check if an internal state is final (no more sync needed)."""
    return internal_state in FINAL_INTERNAL_STATES

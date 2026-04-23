"""
Mapeo de estados GLS → lenguaje cliente + detección de incidencias severas.

GLS devuelve:
  - `codestado` (código numérico) y `estado` (texto en mayúsculas)
  - lista de eventos con `codigo` + `evento` (texto)

Mapeo acordado con el usuario:
  RECIBIDA INFORMACION         → "Envío registrado"
  EN DELEGACION DESTINO        → "En centro de distribución"
  EN REPARTO                   → "En camino a tu domicilio 🚚"
  ENTREGADO                    → "Entregado ✅"
  Incidencia (*)               → "Incidencia en el envío, contacta con nosotros"
"""
from __future__ import annotations

from typing import Optional


# Códigos GLS oficiales relevantes (abreviado; ampliable).
# El código oficial más importante es 10 = ENTREGADO.
_CODIGO_A_ESTADO: dict[str, str] = {
    "0": "RECIBIDA INFORMACION",
    "1": "ADMITIDO EN CENTRO",
    "2": "EN DELEGACION ORIGEN",
    "3": "EN TRANSITO",
    "4": "EN DELEGACION DESTINO",
    "5": "EN REPARTO",
    "6": "EN REPARTO",
    "10": "ENTREGADO",
    "11": "DEVUELTO",
}

# Palabras clave que marcan incidencia en el texto del evento GLS.
_INCIDENCIA_KEYWORDS = {
    "INCIDENCIA", "AUSENTE", "DIRECCION ERRONEA", "DIRECCIÓN ERRÓNEA",
    "EXTRAVIADO", "PERDIDO", "DAÑADO", "DANADO", "RECHAZADO",
    "DEVUELTO", "NO LOCALIZADO", "FRACASO",
}


def friendly_estado(estado_texto: str, codigo: Optional[str] = None) -> str:
    """Devuelve el texto CLIENTE-FRIENDLY para un estado/codigo GLS.

    Usar en la vista pública /seguimiento. Ver `interno_estado()` para la
    vista del tramitador.
    """
    txt = (estado_texto or "").strip().upper()
    codigo = (codigo or "").strip()

    # Si hay incidencia, prevalece
    if is_incidencia(txt):
        return "Incidencia en el envío, contacta con nosotros"

    if codigo == "10" or "ENTREGADO" in txt:
        return "Entregado ✅"
    if codigo in ("5", "6") or "EN REPARTO" in txt:
        return "En camino a tu domicilio 🚚"
    if codigo == "4" or "DELEGACION DESTINO" in txt or "DELEGACIÓN DESTINO" in txt:
        return "En centro de distribución"
    if codigo in ("1", "2", "3") or txt in ("ADMITIDO EN CENTRO", "EN DELEGACION ORIGEN",
                                              "EN DELEGACIÓN ORIGEN", "EN TRANSITO", "EN TRÁNSITO"):
        return "Envío registrado"
    if codigo == "0" or "RECIBIDA" in txt:
        return "Envío registrado"
    if codigo == "11" or "DEVUELTO" in txt:
        return "Incidencia en el envío, contacta con nosotros"

    # Desconocido: devolver el texto tal cual, capitalizado bonito
    return (estado_texto or "Estado desconocido").capitalize()


def interno_estado(estado_texto: str,
                   codigo: Optional[str] = None,
                   incidencia: Optional[str] = None) -> str:
    """Devuelve el estado CRUDO tal como lo da GLS, para la vista interna del tramitador.

    - Sin mapeo a lenguaje cliente.
    - Si hay incidencia, se prefija con `INCIDENCIA:` seguido del texto exacto.
    - Si no hay texto, devuelve '—'.
    """
    txt = (estado_texto or "").strip()
    inc = (incidencia or "").strip()
    if inc:
        return f"INCIDENCIA: {inc}"
    if is_incidencia(txt):
        return f"INCIDENCIA: {txt}"
    if not txt:
        return "—"
    return txt.upper()


def display_estado(estado_texto: str,
                   codigo: Optional[str] = None,
                   incidencia: Optional[str] = None,
                   mode: str = "cliente") -> str:
    """Dispatcher único: ``mode='interno'`` → raw GLS; ``mode='cliente'`` → amigable."""
    if (mode or "").lower() == "interno":
        return interno_estado(estado_texto, codigo, incidencia)
    return friendly_estado(estado_texto, codigo)


def is_incidencia(estado_texto: str) -> bool:
    """True si el texto del estado indica una incidencia."""
    if not estado_texto:
        return False
    up = estado_texto.upper()
    return any(k in up for k in _INCIDENCIA_KEYWORDS)


def is_entregado(estado_texto: str, codigo: Optional[str] = None) -> bool:
    codigo = (codigo or "").strip()
    if codigo == "10":
        return True
    return "ENTREGADO" in (estado_texto or "").upper()


def estado_color(estado_texto: str, codigo: Optional[str] = None) -> str:
    """Color tailwind sugerido para el badge."""
    if is_incidencia(estado_texto or ""):
        return "red"
    if is_entregado(estado_texto, codigo):
        return "emerald"
    codigo = (codigo or "").strip()
    if codigo in ("5", "6") or "REPARTO" in (estado_texto or "").upper():
        return "blue"
    return "slate"

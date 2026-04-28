"""
Helpers para generación robusta de respuestas ZIP.

Resuelve los problemas más comunes que producen "carpeta comprimida no es
válida" en Chrome/Windows al descargar archivos comprimidos:

  1. Falta de Content-Length → conexión chunked truncada en proxies/CDN.
  2. `Content-Disposition: filename=...` con caracteres no-ASCII rotos.
  3. Nombres internos del ZIP con caracteres reservados de Windows
     (\\ / : * ? " < > |) o duplicados que algunos unzippers rechazan.
  4. Extensiones erróneas inferidas de URLs Cloudinary.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from urllib.parse import quote

logger = logging.getLogger(__name__)


# Caracteres prohibidos en nombres de archivo en Windows (los más estrictos).
_WIN_FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def safe_inner_filename(name: str, max_len: int = 180) -> str:
    """Sanea un nombre para incluirlo dentro de un ZIP.

    - Elimina caracteres reservados de Windows.
    - Normaliza Unicode (NFC).
    - Trunca a max_len para evitar zip32 limit.
    - Si queda vacío, devuelve 'archivo'.
    """
    if not name:
        return "archivo"
    s = unicodedata.normalize("NFC", str(name))
    s = _WIN_FORBIDDEN.sub("_", s).strip(" .")
    if not s:
        return "archivo"
    return s[:max_len]


def safe_content_disposition(filename: str) -> str:
    """Construye un Content-Disposition compatible RFC 5987.

    Doble encoding: ASCII fallback + UTF-8 percent-encoded para clientes
    modernos. Soporta nombres con espacios, ñ, tildes, /, etc.
    """
    if not filename:
        filename = "archivo.zip"
    # ASCII fallback: sustituye no-ASCII por _
    ascii_fallback = unicodedata.normalize("NFKD", filename)
    ascii_fallback = ascii_fallback.encode("ascii", "ignore").decode("ascii")
    ascii_fallback = _WIN_FORBIDDEN.sub("_", ascii_fallback).strip(" .")
    if not ascii_fallback:
        ascii_fallback = "archivo.zip"
    # UTF-8 percent encoded para nombre real
    utf8_encoded = quote(filename, safe="")
    return (
        f'attachment; filename="{ascii_fallback}"; '
        f"filename*=UTF-8''{utf8_encoded}"
    )


# Mapeo MIME → extensión para deducir la extensión correcta cuando la URL
# de Cloudinary no la incluye (caso común con transformaciones).
_MIME_TO_EXT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/heic": "heic",
    "image/heif": "heif",
    "image/avif": "avif",
    "image/svg+xml": "svg",
    "application/pdf": "pdf",
}

# Extensiones permitidas en filename interno (whitelist conservadora).
_VALID_EXT = re.compile(r"^(jpg|jpeg|png|webp|gif|heic|heif|avif|svg|pdf)$", re.I)


def detect_extension(url: str, content_type: str | None = None) -> str:
    """Determina la extensión correcta para guardar el archivo en el ZIP.

    Prioridad:
      1. Content-Type del HTTP response (más fiable).
      2. Última extensión válida en la URL (antes del query string).
      3. Fallback 'jpg'.
    """
    if content_type:
        ext = _MIME_TO_EXT.get(content_type.split(";")[0].strip().lower())
        if ext:
            return ext
    if url and "." in url:
        # Toma la parte antes del primer '?', luego la última '.'
        path = url.split("?", 1)[0]
        candidate = path.rsplit(".", 1)[-1].lower()
        if _VALID_EXT.match(candidate):
            return candidate
    return "jpg"


def deduplicate_zip_entries(entries: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    """Asegura que cada entrada del ZIP tiene un nombre único.

    Si hay colisiones añade `_2`, `_3`, ... antes de la extensión.
    """
    seen: dict[str, int] = {}
    out: list[tuple[str, bytes]] = []
    for name, data in entries:
        n = safe_inner_filename(name)
        if n not in seen:
            seen[n] = 1
            out.append((n, data))
            continue
        # Colisión → añadir sufijo
        seen[n] += 1
        if "." in n:
            base, ext = n.rsplit(".", 1)
            new_name = f"{base}_{seen[n]}.{ext}"
        else:
            new_name = f"{n}_{seen[n]}"
        seen[new_name] = 1
        out.append((new_name, data))
    return out

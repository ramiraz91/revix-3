"""
Email classifier: Extracts codigo_siniestro and determines event type.
Uses configurable regex patterns stored in DB.
"""
import re
from typing import Optional, Tuple
from models import TipoEventoEmail, SeveridadNotificacion
import logging

logger = logging.getLogger(__name__)

# Default regex pattern for codigo_siniestro (e.g. 26BE000534)
DEFAULT_CODE_PATTERN = r'\b(\d{2}[A-Z]{2}\d{6})\b'

# Default classification patterns (subject + body matching)
# Each entry: (TipoEventoEmail, severity, [subject_patterns], [body_patterns])
DEFAULT_PATTERNS = [
    (
        TipoEventoEmail.NUEVO_SINIESTRO,
        SeveridadNotificacion.INFO,
        [r'nuevo\s+siniestro', r'nuevo\s+servicio', r'alta\s+de\s+siniestro', r'nueva\s+solicitud'],
        [r'se\s+ha\s+(creado|dado\s+de\s+alta)', r'nuevo\s+siniestro']
    ),
    (
        TipoEventoEmail.PRESUPUESTO_ACEPTADO,
        SeveridadNotificacion.INFO,
        [r'presupuesto\s+aceptado', r'aceptaci[oó]n\s+de\s+presupuesto', r'aprobaci[oó]n'],
        [r'presupuesto.*aceptado', r'ha\s+sido\s+aceptado', r'aprobado']
    ),
    (
        TipoEventoEmail.PRESUPUESTO_RECHAZADO,
        SeveridadNotificacion.INFO,
        [r'presupuesto\s+rechazado', r'rechazo\s+de\s+presupuesto', r'denegado'],
        [r'presupuesto.*rechazado', r'ha\s+sido\s+rechazado', r'denegado']
    ),
    (
        TipoEventoEmail.IMAGENES_FALTANTES,
        SeveridadNotificacion.WARNING,
        [r'im[aá]genes?\s+(faltantes?|pendientes?)', r'falt.*foto', r'foto.*falt',
         r'faltan?\s+im[aá]gen', r'im[aá]gen.*falt'],
        [r'im[aá]genes?.*falt', r'foto.*falt', r'adjunt.*im[aá]gen',
         r'necesitamos.*foto', r'faltan?\s+im[aá]gen', r'necesit.*im[aá]gen']
    ),
    (
        TipoEventoEmail.DOCUMENTACION_FALTANTE,
        SeveridadNotificacion.WARNING,
        [r'documentaci[oó]n\s+(faltante|pendiente)', r'falta.*document', r'document.*falta'],
        [r'documentaci[oó]n.*falt', r'falta.*documentaci[oó]n', r'necesitamos.*document']
    ),
    (
        TipoEventoEmail.SLA_24H,
        SeveridadNotificacion.WARNING,
        [r'aviso\s+24\s*h', r'24\s*horas?', r'plazo\s+24'],
        [r'24\s*horas?', r'plazo.*24', r'vencimiento.*24']
    ),
    (
        TipoEventoEmail.SLA_48H,
        SeveridadNotificacion.CRITICAL,
        [r'aviso\s+48\s*h', r'48\s*horas?', r'plazo\s+48', r'[uú]ltimo\s+aviso'],
        [r'48\s*horas?', r'plazo.*48', r'[uú]ltimo\s+aviso', r'urgente']
    ),
    (
        TipoEventoEmail.RECORDATORIO,
        SeveridadNotificacion.INFO,
        [r'recordatorio', r'reminder', r'pendiente\s+de\s+acci[oó]n'],
        [r'recordatorio', r'le\s+recordamos', r'pendiente']
    ),
    (
        TipoEventoEmail.INCIDENCIA_PROVEEDOR,
        SeveridadNotificacion.CRITICAL,
        [r'incidencia', r'problema', r'anomal[ií]a', r'error\s+en\s+servicio'],
        [r'incidencia', r'problema.*servicio', r'anomal[ií]a']
    ),
]


def extract_codigo_siniestro(text: str, pattern: Optional[str] = None) -> Optional[str]:
    p = pattern or DEFAULT_CODE_PATTERN
    combined = text or ""
    match = re.search(p, combined, re.IGNORECASE)
    return match.group(1) if match else None


def classify_email(subject: str, body: str,
                   custom_patterns: Optional[list] = None) -> Tuple[TipoEventoEmail, SeveridadNotificacion]:
    patterns = custom_patterns or DEFAULT_PATTERNS
    text_lower_subject = (subject or "").lower()
    text_lower_body = (body or "").lower()

    best_match = None
    best_score = 0

    for tipo, severidad, subject_pats, body_pats in patterns:
        score = 0
        for pat in subject_pats:
            if re.search(pat, text_lower_subject, re.IGNORECASE):
                score += 3  # Subject match weighs more
        for pat in body_pats:
            if re.search(pat, text_lower_body, re.IGNORECASE):
                score += 1
        if score > best_score:
            best_score = score
            best_match = (tipo, severidad)

    if best_match and best_score >= 1:
        return best_match

    return (TipoEventoEmail.DESCONOCIDO, SeveridadNotificacion.INFO)


def generate_idempotency_key(codigo_siniestro: str, tipo_evento: str,
                              email_date: Optional[str]) -> str:
    date_normalized = ""
    if email_date:
        # Normalize to minute precision (ignore seconds)
        date_normalized = email_date[:16] if len(email_date) >= 16 else email_date
    return f"{codigo_siniestro}:{tipo_evento}:{date_normalized}"

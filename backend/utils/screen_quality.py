"""
Utilidades para detectar y clasificar la calidad de pantallas.
Analiza el nombre del producto para determinar automáticamente el tipo de panel.
"""
import re
from typing import Optional, Tuple


# Patrones de detección para cada tipo de calidad
# Orden de prioridad: de más específico a menos específico
QUALITY_PATTERNS = {
    # Apple - Genuine (Original nuevo)
    'genuine': [
        r'\bgenuine\s+oem\b',
        r'\boem\s+genuine\b',
        r'\boriginal\s+apple\b',
        r'\bapple\s+original\b',
        r'\b\(genuine\)\b',
    ],
    # Apple - Refurbished Genuine (Original reacondicionado)
    'refurbished_genuine': [
        r'\brefurbished\)\s*$',
        r'\brefurb\b.*\bgenuine\b',
        r'\bgenuine\b.*\brefurb',
        r'\brelife\b',  # Utopya usa ReLife para reacondicionados
        r'\bpull\b',  # "Pull" suele indicar parte extraída de dispositivo original
    ],
    # Soft OLED (mejor calidad aftermarket)
    'soft_oled': [
        r'\bsoft\s*oled\b',
        r'\boled\b.*\bsoft\b',
        r'\bxo7\s*soft\b',
        r'\baftermarket\s+pro\b.*\bsoft\b',
        r'\baftermarket\s*:\s*soft\b',
        r'\bplus\s*:\s*soft\b',
    ],
    # Hard OLED
    'hard_oled': [
        r'\bhard\s*oled\b',
        r'\boled\b.*\bhard\b',
        r'\baftermarket\s+plus\b.*\bhard\b',
        r'\bplus\s*:\s*hard\b',
    ],
    # Service Pack (Original de marca - Samsung, Xiaomi, etc.)
    'service_pack': [
        r'\bservice\s+pack\b',
        r'\bservicepack\b',
        r'\bgh\d{2}-\d+',  # Códigos Samsung GH82-XXXXX
    ],
    # OLED genérico (aftermarket)
    'oled': [
        r'\boled\s+assembly\b',
        r'\boled\s+screen\b',
        r'\bamoled\b',
        r'\bsuper\s+amoled\b',
    ],
    # InCell (LCD con digitalizador integrado)
    'incell': [
        r'\bincell\b',
        r'\bin-cell\b',
        r'\baq7\b.*\bincell\b',
        r'\bincell\b.*\baq7\b',
        r'\baftermarket\b.*\bincell\b',
        r'\blcd\s+assembly\b(?!.*\boled\b)',  # LCD Assembly sin OLED
    ],
}

# Palabras clave que indican que es un producto de pantalla
SCREEN_KEYWORDS = [
    r'\bpantalla\b',
    r'\bscreen\b',
    r'\blcd\s+assembly\b',
    r'\boled\s+assembly\b',
    r'\bdisplay\s+assembly\b',
    r'\blcd\s+display\b',
    r'\bcomplete\s+lcd\b',
    r'\bpantalla\s+completa\b',
]

# Palabras que excluyen (no son pantallas aunque contengan keywords)
EXCLUDE_KEYWORDS = [
    r'\badhesive\b',
    r'\badhesivo\b',
    r'\bcable\b',
    r'\bflex\b',
    r'\bconnector\b',
    r'\bconector\b',
    r'\bprotector\b',
    r'\bfilm\b',
    r'\bgasket\b',
    r'\bfoam\b',
    r'\btape\b',
    r'\bcover\b',
    r'\bframe\b(?!.*assembly)',  # Frame solo, no "Frame Assembly"
    r'\bsensor\b',
    r'\bcamera\b',
]


def is_screen_product(nombre: str) -> bool:
    """
    Determina si un producto es una pantalla/display.
    
    Args:
        nombre: Nombre del producto
        
    Returns:
        True si es una pantalla, False en caso contrario
    """
    nombre_lower = nombre.lower()
    
    # Primero verificar exclusiones
    for pattern in EXCLUDE_KEYWORDS:
        if re.search(pattern, nombre_lower, re.IGNORECASE):
            return False
    
    # Luego verificar si contiene keywords de pantalla
    for pattern in SCREEN_KEYWORDS:
        if re.search(pattern, nombre_lower, re.IGNORECASE):
            return True
    
    return False


def detect_screen_quality(nombre: str) -> Optional[str]:
    """
    Detecta automáticamente la calidad de una pantalla basándose en su nombre.
    
    Args:
        nombre: Nombre del producto
        
    Returns:
        Código de calidad ('genuine', 'soft_oled', 'hard_oled', 'incell', etc.)
        o None si no se puede determinar
    """
    if not nombre:
        return None
    
    nombre_lower = nombre.lower()
    
    # Primero verificar si es una pantalla
    if not is_screen_product(nombre):
        return None
    
    # Buscar patrones en orden de prioridad
    for quality, patterns in QUALITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, nombre_lower, re.IGNORECASE):
                return quality
    
    # Si es una pantalla pero no se detectó calidad específica
    # Intentar inferir por contexto
    
    # Si contiene "OLED" pero no se clasificó antes
    if re.search(r'\boled\b', nombre_lower):
        return 'oled'
    
    # Si es LCD sin especificar, probablemente InCell
    if re.search(r'\blcd\b', nombre_lower):
        return 'incell'
    
    return 'desconocido'


def get_quality_info(calidad: str) -> dict:
    """
    Obtiene información detallada sobre una calidad de pantalla.
    
    Args:
        calidad: Código de calidad
        
    Returns:
        Diccionario con label, color, descripción, orden de calidad
    """
    QUALITY_INFO = {
        'genuine': {
            'label': 'Genuine',
            'label_es': 'Original',
            'color': '#FFD700',  # Dorado
            'bg_color': '#FEF3C7',
            'text_color': '#92400E',
            'description': 'Pantalla original Apple/OEM nueva',
            'orden': 1,  # Mayor calidad
            'icon': '⭐'
        },
        'refurbished_genuine': {
            'label': 'Refurb Genuine',
            'label_es': 'Original Reacon.',
            'color': '#9CA3AF',  # Plateado
            'bg_color': '#F3F4F6',
            'text_color': '#374151',
            'description': 'Pantalla original reacondicionada',
            'orden': 2,
            'icon': '🔄'
        },
        'soft_oled': {
            'label': 'Soft OLED',
            'label_es': 'Soft OLED',
            'color': '#10B981',  # Verde
            'bg_color': '#D1FAE5',
            'text_color': '#065F46',
            'description': 'OLED flexible aftermarket de alta calidad',
            'orden': 3,
            'icon': '✨'
        },
        'hard_oled': {
            'label': 'Hard OLED',
            'label_es': 'Hard OLED',
            'color': '#3B82F6',  # Azul
            'bg_color': '#DBEAFE',
            'text_color': '#1E40AF',
            'description': 'OLED rígido aftermarket',
            'orden': 4,
            'icon': '💎'
        },
        'service_pack': {
            'label': 'Service Pack',
            'label_es': 'Service Pack',
            'color': '#14B8A6',  # Teal
            'bg_color': '#CCFBF1',
            'text_color': '#0F766E',
            'description': 'Pantalla original de marca (Samsung, etc.)',
            'orden': 2,  # Equivalente a Genuine para otras marcas
            'icon': '🏭'
        },
        'oled': {
            'label': 'OLED',
            'label_es': 'OLED',
            'color': '#8B5CF6',  # Púrpura
            'bg_color': '#EDE9FE',
            'text_color': '#5B21B6',
            'description': 'OLED aftermarket genérico',
            'orden': 5,
            'icon': '📱'
        },
        'incell': {
            'label': 'InCell',
            'label_es': 'InCell',
            'color': '#F97316',  # Naranja
            'bg_color': '#FFEDD5',
            'text_color': '#C2410C',
            'description': 'LCD con digitalizador integrado',
            'orden': 6,
            'icon': '📟'
        },
        'desconocido': {
            'label': 'Sin clasificar',
            'label_es': 'Sin clasificar',
            'color': '#6B7280',  # Gris
            'bg_color': '#F9FAFB',
            'text_color': '#4B5563',
            'description': 'Calidad no determinada',
            'orden': 99,
            'icon': '❓'
        }
    }
    
    return QUALITY_INFO.get(calidad, QUALITY_INFO['desconocido'])


def analyze_product(nombre: str) -> dict:
    """
    Analiza un producto y devuelve toda la información relevante.
    
    Args:
        nombre: Nombre del producto
        
    Returns:
        Diccionario con es_pantalla, calidad_pantalla e info de calidad
    """
    es_pantalla = is_screen_product(nombre)
    calidad = detect_screen_quality(nombre) if es_pantalla else None
    
    result = {
        'es_pantalla': es_pantalla,
        'calidad_pantalla': calidad,
    }
    
    if calidad:
        result['calidad_info'] = get_quality_info(calidad)
    
    return result

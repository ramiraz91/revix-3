"""
Sistema de traducción y búsqueda inteligente de productos.
Traduce nombres de inglés a español y expande búsquedas con sinónimos.
"""
import re
from typing import List, Tuple, Optional

# Diccionario de traducciones inglés → español
TRANSLATIONS = {
    # Pantallas
    'lcd assembly': 'Pantalla completa',
    'oled assembly': 'Pantalla OLED',
    'screen assembly': 'Pantalla completa',
    'display assembly': 'Pantalla completa',
    'lcd display': 'Pantalla LCD',
    'touch screen': 'Pantalla táctil',
    'digitizer': 'Digitalizador',
    'inner screen': 'Pantalla interior',
    'main screen': 'Pantalla principal',
    'outer screen': 'Pantalla exterior',
    
    # Baterías
    'battery': 'Batería',
    'battery tape': 'Adhesivo de batería',
    'battery connector': 'Conector de batería',
    
    # Cámaras
    'back camera': 'Cámara trasera',
    'rear camera': 'Cámara trasera',
    'front camera': 'Cámara frontal',
    'selfie camera': 'Cámara frontal',
    'camera lens': 'Lente de cámara',
    'camera glass': 'Cristal de cámara',
    'camera frame': 'Marco de cámara',
    
    # Conectores y puertos
    'charging port': 'Puerto de carga',
    'charge port': 'Puerto de carga',
    'usb port': 'Puerto USB',
    'lightning connector': 'Conector Lightning',
    'dock connector': 'Conector dock',
    'headphone jack': 'Jack de auriculares',
    'audio jack': 'Jack de audio',
    'sim card tray': 'Bandeja SIM',
    'sim tray': 'Bandeja SIM',
    'card tray': 'Bandeja de tarjeta',
    
    # Altavoces y audio
    'speaker': 'Altavoz',
    'loudspeaker': 'Altavoz',
    'ear speaker': 'Auricular',
    'earpiece': 'Auricular',
    'ringer': 'Timbre',
    'buzzer': 'Zumbador',
    'microphone': 'Micrófono',
    
    # Botones
    'home button': 'Botón Home',
    'power button': 'Botón de encendido',
    'volume button': 'Botón de volumen',
    'side button': 'Botón lateral',
    'mute switch': 'Interruptor silencio',
    
    # Carcasas y tapas
    'back housing': 'Carcasa trasera',
    'back cover': 'Tapa trasera',
    'back glass': 'Cristal trasero',
    'rear housing': 'Carcasa trasera',
    'mid-frame': 'Marco medio',
    'middle frame': 'Marco medio',
    'frame': 'Marco',
    'bezel': 'Bisel',
    'chassis': 'Chasis',
    
    # Flex y cables
    'flex cable': 'Cable flex',
    'flex': 'Flex',
    'ribbon cable': 'Cable plano',
    'fpc': 'FPC',
    'antenna': 'Antena',
    'wifi antenna': 'Antena WiFi',
    'gps antenna': 'Antena GPS',
    'nfc antenna': 'Antena NFC',
    'nfc coil': 'Bobina NFC',
    'wireless charging coil': 'Bobina carga inalámbrica',
    
    # Sensores
    'sensor': 'Sensor',
    'proximity sensor': 'Sensor de proximidad',
    'light sensor': 'Sensor de luz',
    'fingerprint sensor': 'Sensor de huella',
    'touch id': 'Touch ID',
    'face id': 'Face ID',
    
    # Motores y vibración
    'vibrator': 'Vibrador',
    'taptic engine': 'Motor Taptic',
    'vibration motor': 'Motor de vibración',
    
    # Otros componentes
    'motherboard': 'Placa base',
    'logic board': 'Placa lógica',
    'small parts': 'Componentes pequeños',
    'small components': 'Componentes pequeños',
    'screws': 'Tornillos',
    'adhesive': 'Adhesivo',
    'tape': 'Cinta',
    'gasket': 'Junta',
    'foam': 'Espuma',
    'shield': 'Blindaje',
    'bracket': 'Soporte',
    'holder': 'Soporte',
    'clip': 'Clip',
    'connector': 'Conector',
    'socket': 'Zócalo',
    
    # Calidades/Estados
    'service pack': 'Service Pack',
    'genuine oem': 'Original OEM',
    'aftermarket': 'Aftermarket',
    'refurbished': 'Reacondicionado',
    'used oem pull': 'OEM usado',
    'grade a': 'Grado A',
    'grade b': 'Grado B',
    'grade c': 'Grado C',
    
    # Colores
    'black': 'Negro',
    'white': 'Blanco',
    'silver': 'Plateado',
    'gold': 'Dorado',
    'rose gold': 'Oro rosa',
    'space gray': 'Gris espacial',
    'graphite': 'Grafito',
    'pacific blue': 'Azul pacífico',
    'sierra blue': 'Azul sierra',
    'alpine green': 'Verde alpino',
    'deep purple': 'Púrpura oscuro',
    'starlight': 'Blanco estrella',
    'midnight': 'Medianoche',
    'red': 'Rojo',
    'blue': 'Azul',
    'green': 'Verde',
    'yellow': 'Amarillo',
    'purple': 'Púrpura',
    'pink': 'Rosa',
    'coral': 'Coral',
    'lavender': 'Lavanda',
    'cream': 'Crema',
    'phantom': 'Phantom',
    'navy': 'Azul marino',
    
    # Preposiciones y palabras comunes
    'for': 'para',
    'with': 'con',
    'without': 'sin',
    'compatible': 'compatible',
    'replacement': 'repuesto',
    'repair': 'reparación',
    'tool': 'herramienta',
    'kit': 'kit',
    'set': 'conjunto',
    'pack': 'pack',
    'piece': 'pieza',
    'pair': 'par',
}

# Sinónimos para búsqueda (español → términos de búsqueda)
SEARCH_SYNONYMS = {
    'pantalla': ['lcd', 'oled', 'screen', 'display', 'assembly', 'digitizer', 'pantalla'],
    'bateria': ['battery', 'batería', 'bateria', 'pila'],
    'batería': ['battery', 'batería', 'bateria', 'pila'],
    'camara': ['camera', 'cámara', 'camara', 'lens'],
    'cámara': ['camera', 'cámara', 'camara', 'lens'],
    'conector': ['connector', 'port', 'charging', 'dock', 'lightning', 'usb', 'conector', 'puerto'],
    'puerto': ['port', 'charging', 'dock', 'connector', 'puerto', 'conector'],
    'altavoz': ['speaker', 'loudspeaker', 'ringer', 'buzzer', 'altavoz', 'auricular'],
    'auricular': ['earpiece', 'ear speaker', 'auricular', 'speaker'],
    'microfono': ['microphone', 'mic', 'micrófono', 'microfono'],
    'micrófono': ['microphone', 'mic', 'micrófono', 'microfono'],
    'tapa': ['back cover', 'back glass', 'back housing', 'housing', 'cover', 'tapa', 'carcasa', 'trasera'],
    'carcasa': ['housing', 'back housing', 'cover', 'frame', 'carcasa', 'tapa', 'chasis'],
    'marco': ['frame', 'mid-frame', 'bezel', 'chassis', 'marco', 'chasis'],
    'flex': ['flex', 'cable', 'ribbon', 'fpc', 'flex'],
    'boton': ['button', 'switch', 'botón', 'boton'],
    'botón': ['button', 'switch', 'botón', 'boton'],
    'nfc': ['nfc', 'wireless', 'coil', 'antenna'],
    'antena': ['antenna', 'wifi', 'gps', 'nfc', 'antena'],
    'sensor': ['sensor', 'proximity', 'light', 'fingerprint', 'touch id', 'face id'],
    'huella': ['fingerprint', 'touch id', 'huella', 'sensor'],
    'vibrador': ['vibrator', 'taptic', 'vibration', 'motor', 'vibrador'],
    'cristal': ['glass', 'cristal', 'lens', 'cover'],
    'adhesivo': ['adhesive', 'tape', 'glue', 'adhesivo', 'cinta'],
    'tornillo': ['screw', 'tornillo', 'tornillos'],
    'bandeja': ['tray', 'sim', 'card', 'bandeja'],
    'sim': ['sim', 'tray', 'card', 'bandeja'],
    'jack': ['jack', 'headphone', 'audio', 'auriculares'],
}

# Categorías detectables por palabras clave
CATEGORY_KEYWORDS = {
    'Pantallas': ['lcd', 'oled', 'screen', 'display', 'pantalla', 'digitizer'],
    'Baterías': ['battery', 'batería', 'bateria'],
    'Cámaras': ['camera', 'cámara', 'camara', 'lens'],
    'Conectores': ['connector', 'port', 'charging', 'dock', 'lightning', 'usb', 'conector', 'puerto'],
    'Altavoces': ['speaker', 'loudspeaker', 'earpiece', 'ringer', 'buzzer', 'altavoz', 'auricular'],
    'Flex': ['flex', 'cable', 'ribbon', 'fpc', 'antenna', 'antena'],
    'Carcasas': ['housing', 'cover', 'frame', 'chassis', 'back glass', 'carcasa', 'tapa', 'marco'],
    'Botones': ['button', 'switch', 'home', 'power', 'volume', 'botón', 'boton'],
    'Sensores': ['sensor', 'proximity', 'fingerprint', 'touch id', 'face id'],
    'Accesorios': ['tool', 'kit', 'adhesive', 'tape', 'screw', 'tempered glass', 'protector'],
    'NFC': ['nfc', 'wireless charging', 'coil'],
}


def translate_name(nombre: str) -> str:
    """
    Traduce un nombre de producto de inglés a español.
    Mantiene la estructura y capitalización apropiada.
    """
    if not nombre:
        return nombre
    
    resultado = nombre
    
    # Ordenar traducciones por longitud (más largas primero) para evitar conflictos
    sorted_translations = sorted(TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True)
    
    for eng, esp in sorted_translations:
        # Buscar el término en inglés (case insensitive)
        pattern = re.compile(re.escape(eng), re.IGNORECASE)
        if pattern.search(resultado):
            # Preservar el caso original si es posible
            def replace_match(match):
                original = match.group(0)
                # Si el original está en mayúsculas, poner traducción en mayúsculas
                if original.isupper():
                    return esp.upper()
                # Si la primera letra es mayúscula, capitalizar
                elif original[0].isupper():
                    return esp.capitalize() if len(esp) > 0 else esp
                return esp
            
            resultado = pattern.sub(replace_match, resultado)
    
    # Limpiar espacios múltiples
    resultado = re.sub(r'\s+', ' ', resultado).strip()
    
    return resultado


def detect_category(nombre: str) -> Optional[str]:
    """
    Detecta la categoría de un producto basándose en su nombre.
    """
    nombre_lower = nombre.lower()
    
    for categoria, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in nombre_lower:
                return categoria
    
    return None


def expand_search_terms(query: str) -> List[str]:
    """
    Expande los términos de búsqueda para incluir sinónimos.
    Ej: "pantalla s23" → ["pantalla", "lcd", "oled", "screen", "display", "s23"]
    """
    words = query.lower().split()
    expanded = set(words)  # Mantener términos originales
    
    for word in words:
        # Buscar sinónimos directos
        if word in SEARCH_SYNONYMS:
            expanded.update(SEARCH_SYNONYMS[word])
        
        # Buscar sinónimos parciales (si la palabra está contenida en una clave)
        for key, synonyms in SEARCH_SYNONYMS.items():
            if word in key or key in word:
                expanded.update(synonyms)
    
    return list(expanded)


def build_search_regex(query: str) -> str:
    """
    Construye una expresión regular para búsqueda flexible.
    Expande términos y crea un patrón que coincida con cualquiera.
    """
    expanded = expand_search_terms(query)
    
    # Escapar caracteres especiales de regex
    escaped = [re.escape(term) for term in expanded]
    
    # Crear patrón OR para todos los términos
    return '|'.join(escaped)


def build_search_query(query: str) -> dict:
    """
    Construye una query de MongoDB para búsqueda inteligente.
    
    Args:
        query: Términos de búsqueda del usuario (ej: "pantalla s23")
    
    Returns:
        Query de MongoDB que busca con sinónimos expandidos
    """
    if not query or len(query) < 2:
        return {}
    
    words = query.lower().split()
    conditions = []
    
    # Para cada palabra, crear condiciones con sinónimos
    for word in words:
        word_conditions = []
        
        # Términos expandidos para esta palabra
        if word in SEARCH_SYNONYMS:
            terms = SEARCH_SYNONYMS[word] + [word]
        else:
            terms = [word]
        
        # Crear regex para cada término
        for term in terms:
            word_conditions.append({
                "nombre": {"$regex": re.escape(term), "$options": "i"}
            })
        
        # También buscar en SKU
        word_conditions.append({
            "sku": {"$regex": re.escape(word), "$options": "i"}
        })
        word_conditions.append({
            "sku_proveedor": {"$regex": re.escape(word), "$options": "i"}
        })
        
        # OR entre todos los sinónimos de esta palabra
        conditions.append({"$or": word_conditions})
    
    # AND entre todas las palabras (todas deben coincidir)
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def normalize_product_name(nombre: str, translate: bool = True) -> str:
    """
    Normaliza el nombre de un producto:
    1. Traduce al español si está en inglés
    2. Limpia formato
    """
    if not nombre:
        return nombre
    
    if translate:
        nombre = translate_name(nombre)
    
    # Limpiar espacios
    nombre = re.sub(r'\s+', ' ', nombre).strip()
    
    return nombre

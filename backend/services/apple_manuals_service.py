"""
Servicio de Manuales de Reparación Apple
Mapea modelos de dispositivos a su documentación oficial de Apple.
"""
from typing import Optional, Dict, List
import re

# ==================== BASE DE DATOS DE MODELOS APPLE ====================
# Mapeo de modelos de iPhone a sus IDs de producto en Apple Support

APPLE_IPHONE_MODELS = {
    # iPhone 17 Series
    "iphone 17": {"product_id": "301247", "manual_url": None, "year": 2025},
    "iphone 17 pro": {"product_id": "301245", "manual_url": None, "year": 2025},
    "iphone 17 pro max": {"product_id": "301246", "manual_url": None, "year": 2025},
    "iphone air": {"product_id": "301244", "manual_url": None, "year": 2025},
    
    # iPhone 16 Series
    "iphone 16": {"product_id": "301045", "manual_url": "https://support.apple.com/es-es/120078", "year": 2024},
    "iphone 16 plus": {"product_id": "301046", "manual_url": "https://support.apple.com/es-es/120079", "year": 2024},
    "iphone 16 pro": {"product_id": "301047", "manual_url": "https://support.apple.com/es-es/120080", "year": 2024},
    "iphone 16 pro max": {"product_id": "301048", "manual_url": "https://support.apple.com/es-es/120081", "year": 2024},
    "iphone 16e": {"product_id": "301076", "manual_url": None, "year": 2025},
    
    # iPhone 15 Series
    "iphone 15": {"product_id": "300991", "manual_url": "https://support.apple.com/es-es/104862", "year": 2023},
    "iphone 15 plus": {"product_id": "301004", "manual_url": "https://support.apple.com/es-es/104863", "year": 2023},
    "iphone 15 pro": {"product_id": "300993", "manual_url": "https://support.apple.com/es-es/104872", "year": 2023},
    "iphone 15 pro max": {"product_id": "301003", "manual_url": "https://support.apple.com/es-es/104871", "year": 2023},
    
    # iPhone 14 Series
    "iphone 14": {"product_id": "300878", "manual_url": "https://support.apple.com/es-es/111865", "year": 2022},
    "iphone 14 plus": {"product_id": "300879", "manual_url": "https://support.apple.com/es-es/111866", "year": 2022},
    "iphone 14 pro": {"product_id": "300880", "manual_url": "https://support.apple.com/es-es/111867", "year": 2022},
    "iphone 14 pro max": {"product_id": "300881", "manual_url": "https://support.apple.com/es-es/111868", "year": 2022},
    
    # iPhone 13 Series
    "iphone 13": {"product_id": "300428", "manual_url": "https://support.apple.com/es-es/111854", "year": 2021},
    "iphone 13 mini": {"product_id": "300426", "manual_url": "https://support.apple.com/es-es/111853", "year": 2021},
    "iphone 13 pro": {"product_id": "300429", "manual_url": "https://support.apple.com/es-es/111855", "year": 2021},
    "iphone 13 pro max": {"product_id": "300430", "manual_url": "https://support.apple.com/es-es/111856", "year": 2021},
    
    # iPhone 12 Series
    "iphone 12": {"product_id": "300241", "manual_url": "https://support.apple.com/es-es/111858", "year": 2020},
    "iphone 12 mini": {"product_id": "300239", "manual_url": "https://support.apple.com/es-es/111857", "year": 2020},
    "iphone 12 pro": {"product_id": "300242", "manual_url": "https://support.apple.com/es-es/111859", "year": 2020},
    "iphone 12 pro max": {"product_id": "300240", "manual_url": "https://support.apple.com/es-es/111860", "year": 2020},
    
    # iPhone SE
    "iphone se 3": {"product_id": "300865", "manual_url": "https://support.apple.com/es-es/111864", "year": 2022},
    "iphone se (3.ª generación)": {"product_id": "300865", "manual_url": "https://support.apple.com/es-es/111864", "year": 2022},
    "iphone se (3ª generación)": {"product_id": "300865", "manual_url": "https://support.apple.com/es-es/111864", "year": 2022},
    "iphone se 2": {"product_id": "509370", "manual_url": "https://support.apple.com/es-es/111869", "year": 2020},
    "iphone se (2nd generation)": {"product_id": "509370", "manual_url": "https://support.apple.com/es-es/111869", "year": 2020},
    "iphone se (2ª generación)": {"product_id": "509370", "manual_url": "https://support.apple.com/es-es/111869", "year": 2020},
    "iphone se": {"product_id": "501343", "manual_url": None, "year": 2016},
    
    # iPhone 11 Series
    "iphone 11": {"product_id": "507882", "manual_url": "https://support.apple.com/es-es/111861", "year": 2019},
    "iphone 11 pro": {"product_id": "507808", "manual_url": "https://support.apple.com/es-es/111862", "year": 2019},
    "iphone 11 pro max": {"product_id": "507845", "manual_url": "https://support.apple.com/es-es/111863", "year": 2019},
    
    # iPhone X Series
    "iphone xr": {"product_id": "505602", "manual_url": None, "year": 2018},
    "iphone xs": {"product_id": "505753", "manual_url": None, "year": 2018},
    "iphone xs max": {"product_id": "505716", "manual_url": None, "year": 2018},
    "iphone x": {"product_id": "504268", "manual_url": None, "year": 2017},
    
    # iPhone 8
    "iphone 8": {"product_id": "504266", "manual_url": None, "year": 2017},
    "iphone 8 plus": {"product_id": "504267", "manual_url": None, "year": 2017},
    
    # iPhone 7
    "iphone 7": {"product_id": "502272", "manual_url": None, "year": 2016},
    "iphone 7 plus": {"product_id": "502287", "manual_url": None, "year": 2016},
    
    # iPhone 6s
    "iphone 6s": {"product_id": "500016", "manual_url": None, "year": 2015},
    "iphone 6s plus": {"product_id": "500040", "manual_url": None, "year": 2015},
    
    # iPhone 6
    "iphone 6": {"product_id": "134711", "manual_url": None, "year": 2014},
    "iphone 6 plus": {"product_id": "134710", "manual_url": None, "year": 2014},
}

# Secciones comunes de reparación disponibles en los manuales
REPAIR_SECTIONS = {
    "pantalla": {
        "keywords": ["pantalla", "display", "lcd", "oled", "tactil", "touch", "cristal", "vidrio"],
        "apple_section": "display",
        "article_suffix": "#display1"
    },
    "bateria": {
        "keywords": ["bateria", "battery", "carga", "cargador", "no enciende", "no carga", "energia"],
        "apple_section": "battery",
        "article_suffix": "#power1"
    },
    "camara": {
        "keywords": ["camara", "camera", "foto", "flash", "lente", "lidar", "truedepth", "face id", "faceid"],
        "apple_section": "camera",
        "article_suffix": "#camera1"
    },
    "altavoz": {
        "keywords": ["altavoz", "speaker", "sonido", "audio", "microfono", "auricular", "no se escucha"],
        "apple_section": "audio",
        "article_suffix": "#mech1"
    },
    "boton": {
        "keywords": ["boton", "button", "power", "volumen", "home", "touch id", "encendido", "silencio"],
        "apple_section": "mechanical",
        "article_suffix": "#mech5"
    },
    "conectividad": {
        "keywords": ["wifi", "bluetooth", "señal", "antena", "sim", "red", "datos", "celular"],
        "apple_section": "connectivity",
        "article_suffix": "#mech2"
    },
    "vibrador": {
        "keywords": ["vibrador", "taptic", "vibracion", "haptic"],
        "apple_section": "taptic",
        "article_suffix": "#mech3"
    },
    "trasera": {
        "keywords": ["tapa", "trasera", "back", "carcasa", "housing", "chasis"],
        "apple_section": "back_glass",
        "article_suffix": None
    }
}


def normalize_model_name(model: str) -> str:
    """Normaliza el nombre del modelo para búsqueda"""
    if not model:
        return ""
    
    # Convertir a minúsculas
    normalized = model.lower().strip()
    
    # Eliminar caracteres especiales excepto espacios y guiones
    normalized = re.sub(r'[^\w\s-]', '', normalized)
    
    # Normalizar espacios múltiples
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized


def find_model_info(model_name: str) -> Optional[Dict]:
    """
    Busca información del modelo en la base de datos.
    Soporta búsqueda flexible (ej: "iPhone 15 Pro", "15 pro", "iphone15pro")
    """
    if not model_name:
        return None
    
    normalized = normalize_model_name(model_name)
    
    # Búsqueda exacta primero
    if normalized in APPLE_IPHONE_MODELS:
        return {**APPLE_IPHONE_MODELS[normalized], "matched_name": normalized}
    
    # Búsqueda parcial
    for key, value in APPLE_IPHONE_MODELS.items():
        # Verificar si el modelo buscado está contenido en la key
        if normalized in key or key in normalized:
            return {**value, "matched_name": key}
        
        # Búsqueda sin "iphone" prefix
        normalized_no_prefix = normalized.replace("iphone", "").strip()
        key_no_prefix = key.replace("iphone", "").strip()
        
        if normalized_no_prefix and key_no_prefix:
            if normalized_no_prefix in key_no_prefix or key_no_prefix in normalized_no_prefix:
                return {**value, "matched_name": key}
    
    return None


def detect_repair_type(problem_description: str) -> List[Dict]:
    """
    Detecta el tipo de reparación basándose en la descripción del problema.
    Retorna las secciones relevantes del manual.
    """
    if not problem_description:
        return []
    
    normalized = problem_description.lower()
    detected_sections = []
    
    for section_name, section_info in REPAIR_SECTIONS.items():
        for keyword in section_info["keywords"]:
            if keyword in normalized:
                detected_sections.append({
                    "section": section_name,
                    "apple_section": section_info["apple_section"],
                    "article_suffix": section_info["article_suffix"],
                    "matched_keyword": keyword
                })
                break  # Solo agregar una vez por sección
    
    return detected_sections


def get_apple_documentation(model_name: str, problem_description: str = None) -> Dict:
    """
    Obtiene la documentación de Apple para un modelo y problema específicos.
    
    Args:
        model_name: Nombre del modelo (ej: "iPhone 15 Pro")
        problem_description: Descripción del problema (ej: "pantalla rota")
    
    Returns:
        Dict con URLs y información relevante
    """
    result = {
        "found": False,
        "model_info": None,
        "main_page_url": None,
        "manual_url": None,
        "specs_url": None,
        "relevant_sections": [],
        "message": ""
    }
    
    # Buscar modelo
    model_info = find_model_info(model_name)
    
    if not model_info:
        result["message"] = f"No se encontró documentación para el modelo: {model_name}"
        return result
    
    result["found"] = True
    result["model_info"] = {
        "name": model_info["matched_name"].title(),
        "year": model_info.get("year"),
        "product_id": model_info.get("product_id")
    }
    
    # URLs principales
    product_id = model_info.get("product_id")
    result["main_page_url"] = f"https://support.apple.com/es-es/docs/iphone/{product_id}"
    result["specs_url"] = f"https://support.apple.com/es-es/docs/iphone/{product_id}#specs"
    
    # Manual de reparación (si existe)
    if model_info.get("manual_url"):
        result["manual_url"] = model_info["manual_url"]
    
    # Detectar secciones relevantes basadas en el problema
    if problem_description:
        sections = detect_repair_type(problem_description)
        for section in sections:
            section_data = {
                "name": section["section"].title(),
                "type": section["apple_section"],
                "keyword_matched": section["matched_keyword"]
            }
            
            # Agregar URL específica si hay manual
            if model_info.get("manual_url") and section.get("article_suffix"):
                section_data["troubleshooting_url"] = model_info["manual_url"] + section["article_suffix"]
            
            result["relevant_sections"].append(section_data)
    
    # Mensaje descriptivo
    if result["manual_url"]:
        result["message"] = f"Documentación disponible para {result['model_info']['name']}"
    else:
        result["message"] = f"Página de soporte disponible para {result['model_info']['name']} (sin manual de reparación oficial)"
    
    return result


def get_all_supported_models() -> List[Dict]:
    """Retorna la lista de todos los modelos soportados con sus URLs"""
    models = []
    seen = set()
    
    for name, info in APPLE_IPHONE_MODELS.items():
        product_id = info.get("product_id")
        if product_id and product_id not in seen:
            seen.add(product_id)
            models.append({
                "name": name.title(),
                "product_id": product_id,
                "year": info.get("year"),
                "has_repair_manual": bool(info.get("manual_url")),
                "page_url": f"https://support.apple.com/es-es/docs/iphone/{product_id}",
                "manual_url": info.get("manual_url")
            })
    
    # Ordenar por año descendente
    models.sort(key=lambda x: (x.get("year") or 0, x["name"]), reverse=True)
    
    return models

"""
Rutas para FAQs (Preguntas Frecuentes)
Gestión de FAQs para la web pública
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from config import db, logger
from auth import require_auth, require_admin, require_master

router = APIRouter()

# ==================== MODELOS ====================

class FAQCreate(BaseModel):
    pregunta: str
    respuesta: str
    categoria: str  # proceso, garantia, envio, piezas, pagos, otras
    orden: Optional[int] = 0
    activo: bool = True

class FAQUpdate(BaseModel):
    pregunta: Optional[str] = None
    respuesta: Optional[str] = None
    categoria: Optional[str] = None
    orden: Optional[int] = None
    activo: Optional[bool] = None

# ==================== CATEGORÍAS ====================

CATEGORIAS_FAQ = {
    "envio": {
        "nombre": "Envíos y Logística",
        "icono": "📦",
        "descripcion": "Tiempos, preparación de paquetes y cobertura"
    },
    "privacidad": {
        "nombre": "Privacidad y Seguridad",
        "icono": "🛡️",
        "descripcion": "Protocolo ISO 9001 y protección de datos"
    },
    "pagos": {
        "nombre": "Presupuestos y Pagos",
        "icono": "💰",
        "descripcion": "Costes, métodos de pago y cancelaciones"
    },
    "garantia": {
        "nombre": "Reparaciones y Garantía",
        "icono": "🔧",
        "descripcion": "Dispositivos, piezas y cobertura de garantía"
    },
    "tecnologia": {
        "nombre": "Tecnología e IA",
        "icono": "🤖",
        "descripcion": "Cómo usamos la IA para mejorar el servicio"
    },
    "otras": {
        "nombre": "Casos Especiales",
        "icono": "💡",
        "descripcion": "Daños por agua y situaciones particulares"
    }
}

# ==================== ENDPOINTS PÚBLICOS ====================

@router.get("/faqs/public")
async def listar_faqs_publicas():
    """Lista todas las FAQs activas para la web pública"""
    faqs = await db.faqs.find(
        {"activo": True},
        {"_id": 0}
    ).sort([("categoria", 1), ("orden", 1)]).to_list(100)
    
    # Agrupar por categoría
    por_categoria = {}
    for cat_id, cat_info in CATEGORIAS_FAQ.items():
        faqs_cat = [f for f in faqs if f.get("categoria") == cat_id]
        if faqs_cat:
            por_categoria[cat_id] = {
                "info": cat_info,
                "faqs": faqs_cat
            }
    
    return {
        "categorias": CATEGORIAS_FAQ,
        "faqs_por_categoria": por_categoria,
        "total": len(faqs)
    }

# ==================== ENDPOINTS ADMIN ====================

@router.get("/faqs")
async def listar_faqs(user: dict = Depends(require_admin)):
    """Lista todas las FAQs (incluyendo inactivas)"""
    faqs = await db.faqs.find({}, {"_id": 0}).sort([("categoria", 1), ("orden", 1)]).to_list(200)
    return {
        "faqs": faqs,
        "categorias": CATEGORIAS_FAQ,
        "total": len(faqs)
    }

@router.get("/faqs/{faq_id}")
async def obtener_faq(faq_id: str, user: dict = Depends(require_admin)):
    """Obtiene una FAQ por ID"""
    faq = await db.faqs.find_one({"id": faq_id}, {"_id": 0})
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ no encontrada")
    return faq

@router.post("/faqs")
async def crear_faq(data: FAQCreate, user: dict = Depends(require_master)):
    """Crea una nueva FAQ (solo master)"""
    if data.categoria not in CATEGORIAS_FAQ:
        raise HTTPException(status_code=400, detail=f"Categoría inválida. Opciones: {list(CATEGORIAS_FAQ.keys())}")
    
    faq_id = str(uuid.uuid4())
    faq = {
        "id": faq_id,
        "pregunta": data.pregunta.strip(),
        "respuesta": data.respuesta.strip(),
        "categoria": data.categoria,
        "orden": data.orden,
        "activo": data.activo,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.get("email")
    }
    
    await db.faqs.insert_one(faq)
    return {"message": "FAQ creada", "id": faq_id}

@router.put("/faqs/{faq_id}")
async def actualizar_faq(faq_id: str, data: FAQUpdate, user: dict = Depends(require_master)):
    """Actualiza una FAQ (solo master)"""
    faq = await db.faqs.find_one({"id": faq_id})
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ no encontrada")
    
    if data.categoria and data.categoria not in CATEGORIAS_FAQ:
        raise HTTPException(status_code=400, detail="Categoría inválida")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.faqs.update_one({"id": faq_id}, {"$set": update_data})
    return {"message": "FAQ actualizada"}

@router.delete("/faqs/{faq_id}")
async def eliminar_faq(faq_id: str, user: dict = Depends(require_master)):
    """Elimina una FAQ (solo master)"""
    result = await db.faqs.delete_one({"id": faq_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="FAQ no encontrada")
    return {"message": "FAQ eliminada"}

@router.post("/faqs/reordenar")
async def reordenar_faqs(orden: List[dict], user: dict = Depends(require_master)):
    """Reordena las FAQs. orden = [{"id": "...", "orden": 1}, ...]"""
    for item in orden:
        await db.faqs.update_one(
            {"id": item["id"]},
            {"$set": {"orden": item["orden"], "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    return {"message": "Orden actualizado"}

# ==================== INICIALIZAR FAQs POR DEFECTO ====================

@router.post("/faqs/inicializar")
async def inicializar_faqs_defecto(user: dict = Depends(require_master)):
    """Inicializa FAQs por defecto si no existen"""
    count = await db.faqs.count_documents({})
    if count > 0:
        return {"message": f"Ya existen {count} FAQs, no se inicializaron nuevas"}
    
    faqs_defecto = [
        # PROCESO
        {
            "categoria": "proceso",
            "orden": 1,
            "pregunta": "¿Cómo funciona el proceso de reparación?",
            "respuesta": "Es muy sencillo: 1) Solicitas presupuesto en nuestra web o por teléfono. 2) Un técnico especializado te llamará para confirmar los detalles. 3) Coordinamos la recogida en tu domicilio (normalmente en 24h). 4) Diagnosticamos y reparamos tu dispositivo. 5) Te lo devolvemos reparado con 6 meses de garantía."
        },
        {
            "categoria": "proceso",
            "orden": 2,
            "pregunta": "¿Cuánto tarda la reparación?",
            "respuesta": "El tiempo medio de reparación es de 24-72 horas desde que recibimos el dispositivo, dependiendo de la complejidad y disponibilidad de piezas. Para reparaciones express (pantallas, baterías), solemos tardar 24-48h. Te mantendremos informado en todo momento."
        },
        {
            "categoria": "proceso",
            "orden": 3,
            "pregunta": "¿Qué pasa si detectáis una avería adicional?",
            "respuesta": "Si durante el diagnóstico detectamos alguna avería adicional que no estaba prevista, te llamaremos inmediatamente para informarte del nuevo presupuesto. No realizamos ninguna reparación adicional sin tu autorización expresa."
        },
        
        # ENVÍO
        {
            "categoria": "envio",
            "orden": 1,
            "pregunta": "¿Cómo funciona la recogida a domicilio?",
            "respuesta": "Una vez confirmado el presupuesto, coordinamos con nuestra empresa de mensajería la recogida en tu domicilio. Normalmente la recogida se realiza en 24 horas. Te proporcionamos un embalaje seguro o puedes usar el tuyo propio bien protegido."
        },
        {
            "categoria": "envio",
            "orden": 2,
            "pregunta": "¿Cuánto tarda el envío?",
            "respuesta": "La mensajería tarda normalmente 24 horas en entregar el dispositivo, tanto para la recogida como para la devolución. En zonas rurales o islas puede tardar 24-48h adicionales."
        },
        {
            "categoria": "envio",
            "orden": 3,
            "pregunta": "¿Tiene coste el envío?",
            "respuesta": "El envío es GRATUITO tanto para la recogida como para la devolución en toda España peninsular. Para Baleares, Canarias, Ceuta y Melilla consulta condiciones especiales."
        },
        
        # GARANTÍA
        {
            "categoria": "garantia",
            "orden": 1,
            "pregunta": "¿Qué garantía tienen las reparaciones?",
            "respuesta": "Todas nuestras reparaciones incluyen 6 meses de garantía que cubre tanto la mano de obra como las piezas utilizadas. Si surge cualquier problema relacionado con la reparación, lo solucionamos sin coste adicional."
        },
        {
            "categoria": "garantia",
            "orden": 2,
            "pregunta": "¿Qué cubre la garantía?",
            "respuesta": "La garantía cubre defectos de fabricación de las piezas y cualquier problema derivado de la reparación realizada. No cubre daños por mal uso, golpes, líquidos o manipulación posterior por terceros."
        },
        {
            "categoria": "garantia",
            "orden": 3,
            "pregunta": "¿Ofrecéis garantía extendida?",
            "respuesta": "Sí, ofrecemos la posibilidad de ampliar la garantía a 12 o 24 meses por un coste adicional. Consulta las condiciones al solicitar tu presupuesto."
        },
        
        # PIEZAS
        {
            "categoria": "piezas",
            "orden": 1,
            "pregunta": "¿Qué diferencia hay entre piezas originales y compatibles?",
            "respuesta": "Las piezas ORIGINALES son fabricadas por el mismo fabricante del dispositivo (Apple, Samsung, etc.) y ofrecen la máxima calidad y durabilidad. Las piezas COMPATIBLES son fabricadas por terceros con excelente calidad y ofrecen mejor relación calidad-precio. Ambas tienen 6 meses de garantía."
        },
        {
            "categoria": "piezas",
            "orden": 2,
            "pregunta": "¿Puedo elegir qué tipo de pieza quiero?",
            "respuesta": "¡Por supuesto! Tú decides qué tipo de pieza prefieres. Te explicaremos las diferencias de precio y características para que puedas tomar la mejor decisión según tus necesidades y presupuesto."
        },
        {
            "categoria": "piezas",
            "orden": 3,
            "pregunta": "¿Las piezas compatibles son de buena calidad?",
            "respuesta": "Sí, trabajamos únicamente con proveedores certificados que ofrecen piezas compatibles de alta calidad (grado AAA). Pasan controles de calidad y tienen la misma garantía de 6 meses que las originales."
        },
        
        # PAGOS
        {
            "categoria": "pagos",
            "orden": 1,
            "pregunta": "¿Qué métodos de pago aceptáis?",
            "respuesta": "Aceptamos múltiples formas de pago: Bizum, transferencia bancaria, y pago con tarjeta a través de un enlace seguro que te enviaremos. El pago se realiza una vez confirmada la reparación, antes de la devolución del dispositivo."
        },
        {
            "categoria": "pagos",
            "orden": 2,
            "pregunta": "¿Hay que pagar algo por adelantado?",
            "respuesta": "No, no cobramos nada por adelantado. Solo pagas una vez que la reparación está completada y confirmada. Si por cualquier motivo no podemos reparar tu dispositivo, te lo devolvemos sin coste alguno."
        },
        {
            "categoria": "pagos",
            "orden": 3,
            "pregunta": "¿Emitís factura?",
            "respuesta": "Sí, emitimos factura oficial por todas las reparaciones. Si eres empresa o autónomo y necesitas factura con IVA desglosado, indícalo al solicitar el presupuesto."
        },
        
        # OTRAS
        {
            "categoria": "otras",
            "orden": 1,
            "pregunta": "¿Qué dispositivos reparáis?",
            "respuesta": "Reparamos todo tipo de dispositivos electrónicos: smartphones (iPhone, Samsung, Xiaomi, Huawei...), tablets (iPad, Samsung Tab...), smartwatches (Apple Watch, Galaxy Watch...), consolas portátiles (Nintendo Switch, Steam Deck) y más."
        },
        {
            "categoria": "otras",
            "orden": 2,
            "pregunta": "¿Trabajáis con aseguradoras?",
            "respuesta": "Sí, somos taller autorizado por las principales aseguradoras de dispositivos electrónicos. Si tienes un seguro, podemos gestionar la reparación directamente con tu aseguradora."
        },
        {
            "categoria": "otras",
            "orden": 3,
            "pregunta": "¿Puedo hacer seguimiento de mi reparación?",
            "respuesta": "Sí, te mantendremos informado en todo momento por email y/o SMS. Además, puedes consultar el estado de tu reparación en cualquier momento desde nuestra web con el código que te proporcionamos."
        }
    ]
    
    # Insertar todas las FAQs
    for faq_data in faqs_defecto:
        faq = {
            "id": str(uuid.uuid4()),
            "pregunta": faq_data["pregunta"],
            "respuesta": faq_data["respuesta"],
            "categoria": faq_data["categoria"],
            "orden": faq_data["orden"],
            "activo": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "created_by": "sistema"
        }
        await db.faqs.insert_one(faq)
    
    return {"message": f"Se han creado {len(faqs_defecto)} FAQs por defecto"}

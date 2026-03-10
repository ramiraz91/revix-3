from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
from config import db, logger
from auth import require_auth, require_admin
from models import (
    Cliente, ClienteCreate, Proveedor, ProveedorCreate,
    Repuesto, RepuestoCreate, Incidencia, IncidenciaCreate,
    DispositivoResto, DispositivoRestoCreate, Notificacion,
    OrdenCompra, OrdenCompraCreate, OrdenCompraUpdate
)

router = APIRouter()


def _parse_datetime_safe(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


def _normalizar_cliente_doc(cliente: dict) -> dict:
    normalized = dict(cliente)
    normalized["nombre"] = normalized.get("nombre") or ""
    normalized["apellidos"] = normalized.get("apellidos") or ""
    normalized["dni"] = normalized.get("dni") or normalized.get("nif") or ""
    normalized["telefono"] = normalized.get("telefono") or ""
    normalized["email"] = normalized.get("email")
    normalized["direccion"] = normalized.get("direccion") or ""
    normalized["planta"] = normalized.get("planta")
    normalized["puerta"] = normalized.get("puerta")
    normalized["ciudad"] = normalized.get("ciudad") or normalized.get("localidad")
    normalized["codigo_postal"] = normalized.get("codigo_postal")
    normalized["tipo_cliente"] = normalized.get("tipo_cliente") or normalized.get("tipo") or "particular"
    normalized["cif_empresa"] = normalized.get("cif_empresa")
    normalized["preferencia_comunicacion"] = normalized.get("preferencia_comunicacion") or "email"
    normalized["idioma_preferido"] = normalized.get("idioma_preferido") or "es"
    normalized["notas_internas"] = normalized.get("notas_internas")
    normalized["acepta_comunicaciones_comerciales"] = bool(normalized.get("acepta_comunicaciones_comerciales", False))
    normalized["created_at"] = _parse_datetime_safe(normalized.get("created_at"))
    normalized["updated_at"] = _parse_datetime_safe(normalized.get("updated_at"))
    return normalized

# ==================== CLIENTES ====================

@router.post("/clientes", response_model=Cliente)
async def crear_cliente(cliente: ClienteCreate):
    cliente_obj = Cliente(**cliente.model_dump())
    doc = cliente_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.clientes.insert_one(doc)
    return cliente_obj

@router.get("/clientes", response_model=List[Cliente])
async def listar_clientes(search: Optional[str] = None):
    query = {}
    if search:
        query = {"$or": [{"nombre": {"$regex": search, "$options": "i"}}, {"apellidos": {"$regex": search, "$options": "i"}}, {"dni": {"$regex": search, "$options": "i"}}, {"telefono": {"$regex": search, "$options": "i"}}]}
    clientes = await db.clientes.find(query, {"_id": 0}).to_list(1000)

    clientes_normalizados = []
    for cliente in clientes:
        normalized = _normalizar_cliente_doc(cliente)
        try:
            Cliente(**normalized)
            clientes_normalizados.append(normalized)
        except Exception as e:
            logger.warning(f"Cliente inválido omitido en listado ({cliente.get('id', 'sin-id')}): {e}")

    return clientes_normalizados

@router.get("/clientes/{cliente_id}", response_model=Cliente)
async def obtener_cliente(cliente_id: str):
    cliente = await db.clientes.find_one({"id": cliente_id}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    normalized = _normalizar_cliente_doc(cliente)
    return normalized

@router.put("/clientes/{cliente_id}", response_model=Cliente)
async def actualizar_cliente(cliente_id: str, cliente: ClienteCreate):
    existing = await db.clientes.find_one({"id": cliente_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    update_data = cliente.model_dump()
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    await db.clientes.update_one({"id": cliente_id}, {"$set": update_data})
    updated = await db.clientes.find_one({"id": cliente_id}, {"_id": 0})
    return _normalizar_cliente_doc(updated)

@router.delete("/clientes/{cliente_id}")
async def eliminar_cliente(cliente_id: str):
    result = await db.clientes.delete_one({"id": cliente_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return {"message": "Cliente eliminado"}

@router.get("/clientes/{cliente_id}/historial")
async def obtener_historial_cliente(cliente_id: str, user: dict = Depends(require_auth)):
    cliente = await db.clientes.find_one({"id": cliente_id}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    ordenes = await db.ordenes.find({"cliente_id": cliente_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    total_ordenes = len(ordenes)
    ordenes_completadas = len([o for o in ordenes if o.get('estado') == 'enviado'])
    ordenes_garantia = len([o for o in ordenes if o.get('es_garantia')])
    dispositivos = {}
    for orden in ordenes:
        disp = orden.get('dispositivo', {})
        imei = disp.get('imei')
        if imei:
            if imei not in dispositivos:
                dispositivos[imei] = {"modelo": disp.get('modelo'), "color": disp.get('color'), "imei": imei, "servicios": [], "total_reparaciones": 0, "reemplazado": False, "irreparable": False}
            dispositivos[imei]['servicios'].append({"numero_orden": orden.get('numero_orden'), "estado": orden.get('estado'), "fecha": orden.get('created_at'), "daños": disp.get('daños'), "es_garantia": orden.get('es_garantia', False)})
            dispositivos[imei]['total_reparaciones'] += 1
            if orden.get('estado') == 'reemplazo':
                dispositivos[imei]['reemplazado'] = True
            if orden.get('estado') == 'irreparable':
                dispositivos[imei]['irreparable'] = True
    total_gastado = sum(m.get('cantidad', 0) * m.get('precio_unitario', 0) for o in ordenes for m in o.get('materiales', []))
    return {"cliente": cliente, "ordenes": ordenes, "dispositivos": list(dispositivos.values()), "estadisticas": {"total_ordenes": total_ordenes, "ordenes_completadas": ordenes_completadas, "ordenes_garantia": ordenes_garantia, "ordenes_irreparables": len([o for o in ordenes if o.get('estado') == 'irreparable']), "ordenes_reemplazo": len([o for o in ordenes if o.get('estado') == 'reemplazo']), "total_gastado": round(total_gastado, 2), "dispositivos_unicos": len(dispositivos)}}


NC_TIPOS = {'reclamacion', 'garantia', 'daño_transporte'}
NC_SEVERIDADES = {'baja', 'media', 'alta', 'critica'}
NC_DISPOSICIONES = {'retrabajo', 'reemplazo', 'devolucion', 'scrap', 'bloqueo'}


def _normalizar_severidad_nc(valor: Optional[str], prioridad: Optional[str]) -> str:
    severidad = (valor or '').strip().lower()
    if severidad in NC_SEVERIDADES:
        return severidad
    if (prioridad or '').lower() == 'critica':
        return 'alta'
    if (prioridad or '').lower() == 'alta':
        return 'media'
    return 'media'


def _normalizar_disposicion_nc(valor: Optional[str]) -> str:
    disposicion = (valor or '').strip().lower()
    if disposicion in NC_DISPOSICIONES:
        return disposicion
    return 'retrabajo'


async def _calcular_recurrencia_nc_30d(tipo: str, origen: Optional[str], excluir_id: Optional[str] = None) -> int:
    desde = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    query = {
        'es_no_conformidad': True,
        'tipo': tipo,
        'created_at': {'$gte': desde},
    }
    if origen:
        query['origen_ncm'] = origen
    if excluir_id:
        query['id'] = {'$ne': excluir_id}

    anteriores = await db.incidencias.count_documents(query)
    return int(anteriores) + 1


async def _crear_capa_automatica_desde_nc(incidencia_doc: dict, user: dict, motivo: str) -> str:
    now = datetime.now(timezone.utc).isoformat()
    capa_id = str(uuid.uuid4())
    capa_doc = {
        'id': capa_id,
        'incidencia_id': incidencia_doc.get('id'),
        'orden_id': incidencia_doc.get('orden_id'),
        'cliente_id': incidencia_doc.get('cliente_id'),
        'estado': 'abierta',
        'motivo_apertura': motivo,
        'problema': incidencia_doc.get('descripcion'),
        'causa_raiz': incidencia_doc.get('capa_causa_raiz'),
        'accion_correctiva': incidencia_doc.get('capa_accion_correctiva'),
        'responsable': incidencia_doc.get('capa_responsable') or user.get('email'),
        'evidencia_inicial': {
            'numero_incidencia': incidencia_doc.get('numero_incidencia'),
            'tipo': incidencia_doc.get('tipo'),
            'severidad_ncm': incidencia_doc.get('severidad_ncm'),
            'disposicion_ncm': incidencia_doc.get('disposicion_ncm'),
            'recurrencia_30d': incidencia_doc.get('recurrencia_30d'),
        },
        'created_at': now,
        'updated_at': now,
        'created_by': user.get('email'),
    }
    await db.capas.insert_one(capa_doc)
    return capa_id


async def _resolver_automatizacion_nc(doc: dict, user: dict, excluir_id: Optional[str] = None) -> dict:
    es_no_conformidad = doc.get('tipo') in NC_TIPOS or bool(doc.get('es_no_conformidad'))
    doc['es_no_conformidad'] = es_no_conformidad

    if not es_no_conformidad:
        return doc

    doc['severidad_ncm'] = _normalizar_severidad_nc(doc.get('severidad_ncm'), doc.get('prioridad'))
    doc['disposicion_ncm'] = _normalizar_disposicion_nc(doc.get('disposicion_ncm'))
    doc['origen_ncm'] = doc.get('origen_ncm') or 'proceso_reparacion'

    recurrencia = await _calcular_recurrencia_nc_30d(doc.get('tipo'), doc.get('origen_ncm'), excluir_id=excluir_id)
    doc['recurrencia_30d'] = recurrencia

    severidad_alta = doc.get('severidad_ncm') in {'alta', 'critica'}
    recurrente = recurrencia >= 2
    capa_obligatoria = severidad_alta or recurrente
    doc['capa_obligatoria'] = capa_obligatoria

    if capa_obligatoria:
        doc['capa_estado'] = doc.get('capa_estado') or 'abierta'
        if not doc.get('capa_id'):
            motivo = 'severidad_alta' if severidad_alta else 'recurrencia_30d'
            doc['capa_id'] = await _crear_capa_automatica_desde_nc(doc, user, motivo)

    return doc

# ==================== INCIDENCIAS ====================

@router.post("/incidencias")
async def crear_incidencia(incidencia: IncidenciaCreate, user: dict = Depends(require_admin)):
    cliente = await db.clientes.find_one({"id": incidencia.cliente_id}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    incidencia_obj = Incidencia(**incidencia.model_dump())
    incidencia_obj.created_by = user['user_id']
    doc = incidencia_obj.model_dump()

    doc = await _resolver_automatizacion_nc(doc, user)

    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.incidencias.insert_one(doc)
    doc.pop('_id', None)
    return doc

@router.get("/incidencias")
async def listar_incidencias(cliente_id: Optional[str] = None, estado: Optional[str] = None, tipo: Optional[str] = None, user: dict = Depends(require_auth)):
    query = {}
    conditions = []
    if cliente_id:
        conditions.append({"cliente_id": cliente_id})
    if estado:
        conditions.append({"estado": estado})
    if tipo:
        conditions.append({"tipo": tipo})
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    return await db.incidencias.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)

@router.get("/incidencias/{incidencia_id}")
async def obtener_incidencia(incidencia_id: str, user: dict = Depends(require_auth)):
    incidencia = await db.incidencias.find_one({"id": incidencia_id}, {"_id": 0})
    if not incidencia:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    return incidencia

@router.put("/incidencias/{incidencia_id}")
async def actualizar_incidencia(incidencia_id: str, data: dict, user: dict = Depends(require_admin)):
    existing = await db.incidencias.find_one({"id": incidencia_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    update_data = {k: v for k, v in data.items() if v is not None and k not in ['id', 'numero_incidencia', 'created_at']}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()

    merged_doc = {**existing, **update_data}
    merged_doc = await _resolver_automatizacion_nc(merged_doc, user, excluir_id=incidencia_id)

    for campo in [
        'es_no_conformidad',
        'severidad_ncm',
        'disposicion_ncm',
        'origen_ncm',
        'recurrencia_30d',
        'capa_obligatoria',
        'capa_estado',
        'capa_id',
    ]:
        if campo in merged_doc:
            update_data[campo] = merged_doc.get(campo)

    estado_objetivo = data.get('estado')
    es_no_conformidad = bool(merged_doc.get('es_no_conformidad'))
    if estado_objetivo in ['resuelta', 'cerrada'] and es_no_conformidad:
        causa_raiz = data.get('capa_causa_raiz') or existing.get('capa_causa_raiz')
        accion_correctiva = data.get('capa_accion_correctiva') or existing.get('capa_accion_correctiva')
        if not causa_raiz or not accion_correctiva:
            raise HTTPException(
                status_code=400,
                detail='Para cerrar una No Conformidad debes completar causa raíz y acción correctiva (CAPA).'
            )
        if merged_doc.get('capa_obligatoria') and not merged_doc.get('capa_id'):
            raise HTTPException(
                status_code=400,
                detail='CAPA obligatoria no creada. Revisa severidad/recurrencia antes de cerrar.'
            )
        update_data['capa_estado'] = 'cerrada' if estado_objetivo == 'cerrada' else 'en_seguimiento'

    if data.get('estado') in ['resuelta', 'cerrada'] and existing.get('estado') not in ['resuelta', 'cerrada']:
        update_data['resuelto_por'] = user['user_id']
        update_data['fecha_resolucion'] = datetime.now(timezone.utc).isoformat()
    await db.incidencias.update_one({"id": incidencia_id}, {"$set": update_data})

    capa_id = update_data.get('capa_id') or existing.get('capa_id')
    if capa_id and update_data.get('capa_estado'):
        await db.capas.update_one(
            {'id': capa_id},
            {'$set': {
                'estado': update_data.get('capa_estado'),
                'causa_raiz': update_data.get('capa_causa_raiz') or existing.get('capa_causa_raiz'),
                'accion_correctiva': update_data.get('capa_accion_correctiva') or existing.get('capa_accion_correctiva'),
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }}
        )

    return await db.incidencias.find_one({"id": incidencia_id}, {"_id": 0})

@router.get("/clientes/{cliente_id}/incidencias")
async def obtener_incidencias_cliente(cliente_id: str, user: dict = Depends(require_auth)):
    return await db.incidencias.find({"cliente_id": cliente_id}, {"_id": 0}).sort("created_at", -1).to_list(100)

# ==================== PROVEEDORES ====================

@router.post("/proveedores", response_model=Proveedor)
async def crear_proveedor(proveedor: ProveedorCreate):
    proveedor_obj = Proveedor(**proveedor.model_dump())
    doc = proveedor_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.proveedores.insert_one(doc)
    return proveedor_obj

@router.get("/proveedores", response_model=List[Proveedor])
async def listar_proveedores(search: Optional[str] = None):
    query = {}
    if search:
        query = {"nombre": {"$regex": search, "$options": "i"}}
    proveedores = await db.proveedores.find(query, {"_id": 0}).to_list(1000)
    for p in proveedores:
        if isinstance(p.get('created_at'), str):
            p['created_at'] = datetime.fromisoformat(p['created_at'])
        if isinstance(p.get('updated_at'), str):
            p['updated_at'] = datetime.fromisoformat(p['updated_at'])
    return proveedores

@router.get("/proveedores/{proveedor_id}", response_model=Proveedor)
async def obtener_proveedor(proveedor_id: str):
    proveedor = await db.proveedores.find_one({"id": proveedor_id}, {"_id": 0})
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    if isinstance(proveedor.get('created_at'), str):
        proveedor['created_at'] = datetime.fromisoformat(proveedor['created_at'])
    if isinstance(proveedor.get('updated_at'), str):
        proveedor['updated_at'] = datetime.fromisoformat(proveedor['updated_at'])
    return proveedor

@router.put("/proveedores/{proveedor_id}", response_model=Proveedor)
async def actualizar_proveedor(proveedor_id: str, proveedor: ProveedorCreate):
    existing = await db.proveedores.find_one({"id": proveedor_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    update_data = proveedor.model_dump()
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    await db.proveedores.update_one({"id": proveedor_id}, {"$set": update_data})
    updated = await db.proveedores.find_one({"id": proveedor_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    if isinstance(updated.get('updated_at'), str):
        updated['updated_at'] = datetime.fromisoformat(updated['updated_at'])
    return updated

@router.delete("/proveedores/{proveedor_id}")
async def eliminar_proveedor(proveedor_id: str):
    result = await db.proveedores.delete_one({"id": proveedor_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return {"message": "Proveedor eliminado"}

# ==================== INVENTARIO/REPUESTOS ====================

def generate_barcode_number() -> str:
    """Genera un código de barras único de 12 dígitos."""
    import random
    # Prefijo 107 (interno) + 9 dígitos aleatorios
    code = "107" + "".join([str(random.randint(0, 9)) for _ in range(9)])
    return code

@router.post("/repuestos", response_model=Repuesto)
async def crear_repuesto(repuesto: RepuestoCreate):
    repuesto_obj = Repuesto(**repuesto.model_dump())
    doc = repuesto_obj.model_dump()
    
    # Auto-generar código de barras si no se proporciona
    if not doc.get('codigo_barras'):
        doc['codigo_barras'] = generate_barcode_number()
    
    # Auto-generar SKU si no se proporciona
    if not doc.get('sku'):
        categoria_prefix = (doc.get('categoria') or 'GEN')[:3].upper()
        count = await db.repuestos.count_documents({"categoria": doc.get('categoria')})
        doc['sku'] = f"{categoria_prefix}-{count + 1:04d}"
    
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.repuestos.insert_one(doc)
    
    # Reconstruct with generated values
    repuesto_obj = Repuesto(**{**repuesto.model_dump(), 'id': doc['id'], 'codigo_barras': doc['codigo_barras'], 'sku': doc['sku']})
    return repuesto_obj

@router.get("/repuestos")
async def listar_repuestos(
    search: Optional[str] = None, 
    categoria: Optional[str] = None, 
    proveedor: Optional[str] = None,
    low_stock: Optional[bool] = None,
    page: int = 1,
    page_size: int = 50
):
    """
    Listar repuestos con paginación del servidor.
    Búsqueda inteligente con sinónimos español/inglés.
    Devuelve items + total para paginación en frontend.
    """
    from utils.product_translator import build_search_query
    
    query = {}
    conditions = []
    
    if search:
        # Usar búsqueda inteligente con sinónimos
        search_query = build_search_query(search)
        if search_query:
            conditions.append(search_query)
    
    if categoria and categoria != "all":
        conditions.append({"categoria": categoria})
    if proveedor and proveedor != "all":
        conditions.append({"proveedor": proveedor})
    if low_stock:
        conditions.append({"$expr": {"$lte": ["$stock", {"$ifNull": ["$stock_minimo", 0]}]}})
    
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    
    # Contar total para paginación
    total = await db.repuestos.count_documents(query)
    
    # Calcular skip
    skip = (page - 1) * page_size
    
    # Proyección optimizada - solo campos necesarios
    projection = {
        "_id": 0,
        "id": 1,
        "nombre": 1,
        "nombre_es": 1,
        "sku": 1,
        "sku_proveedor": 1,
        "categoria": 1,
        "proveedor": 1,
        "precio_compra": 1,
        "precio_venta": 1,
        "stock": 1,
        "stock_minimo": 1,
        "imagen_url": 1,
        "calidad_pantalla": 1,
        "es_pantalla": 1
    }
    
    # Obtener página actual
    repuestos = await db.repuestos.find(query, projection).skip(skip).limit(page_size).to_list(page_size)
    
    # Traducir nombres al español si no están traducidos
    from utils.product_translator import normalize_product_name
    for r in repuestos:
        if not r.get('nombre_es'):
            r['nombre_es'] = normalize_product_name(r.get('nombre', ''), translate=True)
    
    return {
        "items": repuestos,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


# ==================== FILTROS DE PRODUCTOS ====================

@router.get("/repuestos/filtros/marcas")
async def obtener_marcas_productos():
    """
    Obtiene las marcas de dispositivos disponibles en el inventario.
    Extrae la marca del nombre del producto.
    """
    import re
    
    # Mapeo de keywords a marcas
    keyword_to_marca = {
        'iphone': 'Apple', 'ipad': 'Apple', 'macbook': 'Apple', 'apple watch': 'Apple', 'airpods': 'Apple',
        'galaxy': 'Samsung', 'samsung': 'Samsung',
        'xiaomi': 'Xiaomi', 'redmi': 'Xiaomi', 'poco': 'Xiaomi', 'mi ': 'Xiaomi',
        'huawei': 'Huawei', 'honor': 'Honor', 'mate ': 'Huawei', 'p30': 'Huawei', 'p40': 'Huawei',
        'oneplus': 'OnePlus', 'pixel': 'Google', 'moto': 'Motorola', 'motorola': 'Motorola',
        'lg': 'LG', 'sony': 'Sony', 'xperia': 'Sony', 'nokia': 'Nokia',
        'oppo': 'Oppo', 'vivo': 'Vivo', 'realme': 'Realme', 'asus': 'Asus', 'rog': 'Asus',
        'nothing': 'Nothing', 'fairphone': 'Fairphone', 'zte': 'ZTE', 'alcatel': 'Alcatel', 'tcl': 'TCL'
    }
    
    # Obtener nombres únicos de productos
    productos = await db.repuestos.find({}, {"_id": 0, "nombre": 1}).to_list(10000)
    
    marcas_encontradas = {}
    for prod in productos:
        nombre = prod.get('nombre', '').lower()
        for keyword, marca in keyword_to_marca.items():
            if keyword in nombre:
                marcas_encontradas[marca] = marcas_encontradas.get(marca, 0) + 1
                break
    
    # Ordenar por cantidad de productos
    marcas_ordenadas = sorted(marcas_encontradas.items(), key=lambda x: -x[1])
    
    return {
        "marcas": [{"nombre": m, "cantidad": c} for m, c in marcas_ordenadas]
    }


@router.get("/repuestos/filtros/modelos")
async def obtener_modelos_por_marca(marca: str):
    """
    Obtiene los modelos disponibles para una marca específica.
    """
    import re
    
    # Patrones para extraer modelos según la marca
    patrones_modelo = {
        'Apple': [
            r'(iphone\s*\d+\s*(?:pro\s*max|pro|plus|mini)?)',
            r'(ipad\s*(?:pro|air|mini)?\s*\d*(?:\s*\d+(?:\.\d+)?)?(?:st|nd|rd|th)?(?:\s*gen)?)',
            r'(macbook\s*(?:pro|air)?\s*\d*)',
            r'(apple\s*watch\s*(?:series\s*)?\d+|watch\s*(?:se|ultra)\s*\d*)',
            r'(airpods\s*(?:pro|max)?\s*\d*)'
        ],
        'Samsung': [
            r'(galaxy\s*[a-z]?\d+\s*(?:ultra|plus|\+|fe|lite)?)',
            r'(galaxy\s*(?:note|fold|flip|tab)\s*\d*\s*(?:ultra|plus|\+)?)'
        ],
        'Xiaomi': [
            r'(redmi\s*(?:note\s*)?\d+\s*(?:pro|plus|ultra)?)',
            r'(xiaomi\s*\d+\s*(?:t|s|ultra|pro)?)',
            r'(poco\s*[a-z]?\d+\s*(?:pro)?)',
            r'(mi\s*\d+\s*(?:t|s|ultra|pro|lite)?)'
        ],
        'Huawei': [
            r'(p\d+\s*(?:pro|lite|plus)?)',
            r'(mate\s*\d+\s*(?:pro|lite|x)?)',
            r'(nova\s*\d+\s*(?:pro|lite|se)?)'
        ],
        'Google': [r'(pixel\s*\d+\s*(?:a|pro|xl)?)'],
        'OnePlus': [r'(oneplus\s*\d+\s*(?:t|r|pro)?)'],
        'Motorola': [r'(moto\s*[a-z]\d+\s*(?:play|plus|edge)?)'],
    }
    
    # Patrón genérico para marcas sin patrón específico
    patron_generico = r'(' + marca.lower() + r'\s*[\w\s\d]+)'
    
    # Mapeo de keywords para filtrar productos de la marca
    marca_keywords = {
        'Apple': ['iphone', 'ipad', 'macbook', 'apple watch', 'airpods'],
        'Samsung': ['galaxy', 'samsung'],
        'Xiaomi': ['xiaomi', 'redmi', 'poco', 'mi '],
        'Huawei': ['huawei', 'mate ', 'p30', 'p40', 'nova'],
        'Honor': ['honor'],
        'Google': ['pixel'],
        'OnePlus': ['oneplus'],
        'Motorola': ['moto', 'motorola'],
        'LG': ['lg '],
        'Sony': ['sony', 'xperia'],
    }
    
    keywords = marca_keywords.get(marca, [marca.lower()])
    patrones = patrones_modelo.get(marca, [patron_generico])
    
    # Buscar productos de la marca
    or_conditions = [{"nombre": {"$regex": kw, "$options": "i"}} for kw in keywords]
    productos = await db.repuestos.find({"$or": or_conditions}, {"_id": 0, "nombre": 1}).to_list(10000)
    
    modelos_encontrados = {}
    for prod in productos:
        nombre = prod.get('nombre', '')
        for patron in patrones:
            match = re.search(patron, nombre, re.IGNORECASE)
            if match:
                modelo = match.group(1).strip().title()
                # Normalizar espacios
                modelo = re.sub(r'\s+', ' ', modelo)
                modelos_encontrados[modelo] = modelos_encontrados.get(modelo, 0) + 1
                break
    
    # Ordenar por nombre
    modelos_ordenados = sorted(modelos_encontrados.items(), key=lambda x: x[0])
    
    return {
        "marca": marca,
        "modelos": [{"nombre": m, "cantidad": c} for m, c in modelos_ordenados]
    }


@router.get("/repuestos/filtros/tipos")
async def obtener_tipos_servicio():
    """
    Obtiene los tipos de servicio/componente disponibles.
    """
    tipos = [
        {"id": "pantalla", "nombre": "Pantalla / Display", "keywords": ["pantalla", "screen", "lcd", "display", "oled"]},
        {"id": "bateria", "nombre": "Batería", "keywords": ["bateria", "battery", "bater"]},
        {"id": "conector", "nombre": "Conector de Carga", "keywords": ["conector", "connector", "charging", "carga", "dock"]},
        {"id": "camara", "nombre": "Cámara", "keywords": ["camara", "camera", "cam"]},
        {"id": "altavoz", "nombre": "Altavoz / Speaker", "keywords": ["altavoz", "speaker", "auricular", "earpiece"]},
        {"id": "flex", "nombre": "Flex / Cable", "keywords": ["flex", "cable", "ribbon"]},
        {"id": "boton", "nombre": "Botón", "keywords": ["boton", "button", "home", "power", "volume"]},
        {"id": "tapa", "nombre": "Tapa Trasera", "keywords": ["tapa", "back", "cover", "housing", "carcasa"]},
        {"id": "cristal", "nombre": "Cristal / Vidrio", "keywords": ["cristal", "glass", "vidrio", "lens"]},
        {"id": "placa", "nombre": "Placa / Board", "keywords": ["placa", "board", "motherboard", "logic"]},
        {"id": "sim", "nombre": "Bandeja SIM", "keywords": ["sim", "tray", "bandeja"]},
        {"id": "antena", "nombre": "Antena", "keywords": ["antena", "antenna", "wifi", "gps", "nfc"]},
        {"id": "vibrador", "nombre": "Vibrador / Motor", "keywords": ["vibrador", "vibrator", "taptic", "motor"]},
        {"id": "sensor", "nombre": "Sensor", "keywords": ["sensor", "proximity", "light", "face id"]},
        {"id": "otro", "nombre": "Otro", "keywords": []}
    ]
    
    return {"tipos": tipos}


@router.get("/repuestos/filtros/buscar")
async def buscar_por_filtros(
    marca: Optional[str] = None,
    modelo: Optional[str] = None,
    tipo: Optional[str] = None,
    proveedor: Optional[str] = None,
    solo_stock: bool = False,
    limit: int = 50
):
    """
    Busca productos usando los filtros de marca, modelo y tipo.
    """
    import re
    from utils.product_translator import normalize_product_name
    from utils.screen_quality import detect_screen_quality, get_quality_info
    
    # Construir query
    conditions = []
    
    # Filtro por marca
    marca_keywords = {
        'Apple': ['iphone', 'ipad', 'macbook', 'apple watch', 'airpods'],
        'Samsung': ['galaxy', 'samsung'],
        'Xiaomi': ['xiaomi', 'redmi', 'poco'],
        'Huawei': ['huawei', 'mate', 'nova'],
        'Honor': ['honor'],
        'Google': ['pixel'],
        'OnePlus': ['oneplus'],
        'Motorola': ['moto', 'motorola'],
    }
    
    if marca:
        keywords = marca_keywords.get(marca, [marca.lower()])
        or_conds = [{"nombre": {"$regex": kw, "$options": "i"}} for kw in keywords]
        conditions.append({"$or": or_conds})
    
    # Filtro por modelo
    if modelo:
        # Escapar caracteres especiales y buscar
        modelo_escaped = re.escape(modelo)
        conditions.append({"nombre": {"$regex": modelo_escaped, "$options": "i"}})
    
    # Filtro por tipo de servicio
    tipos_keywords = {
        "pantalla": ["pantalla", "screen", "lcd", "display", "oled"],
        "bateria": ["bateria", "battery"],
        "conector": ["conector", "connector", "charging", "dock"],
        "camara": ["camara", "camera"],
        "altavoz": ["altavoz", "speaker", "auricular"],
        "flex": ["flex", "cable", "ribbon"],
        "boton": ["boton", "button", "home", "power"],
        "tapa": ["tapa", "back", "cover", "housing"],
        "cristal": ["cristal", "glass", "vidrio"],
        "placa": ["placa", "board"],
        "sim": ["sim", "tray"],
        "antena": ["antena", "antenna"],
        "vibrador": ["vibrador", "vibrator", "taptic"],
        "sensor": ["sensor", "proximity"]
    }
    
    if tipo and tipo in tipos_keywords:
        keywords = tipos_keywords[tipo]
        or_conds = [{"nombre": {"$regex": kw, "$options": "i"}} for kw in keywords]
        conditions.append({"$or": or_conds})
    
    # Filtro por proveedor
    if proveedor:
        conditions.append({"proveedor": proveedor})
    
    # Filtro por stock
    if solo_stock:
        conditions.append({"stock": {"$gt": 0}})
    
    # Query final
    query = {"$and": conditions} if conditions else {}
    
    # Proyección
    projection = {
        "_id": 0, "id": 1, "nombre": 1, "nombre_es": 1, "sku": 1, "sku_proveedor": 1,
        "precio_compra": 1, "precio_venta": 1, "stock": 1, "proveedor": 1,
        "categoria": 1, "imagen_url": 1, "calidad_pantalla": 1, "es_pantalla": 1, "color": 1
    }
    
    # Ejecutar búsqueda
    productos = await db.repuestos.find(query, projection).limit(limit).to_list(limit)
    
    # Procesar resultados
    for p in productos:
        if not p.get('nombre_es'):
            p['nombre_es'] = normalize_product_name(p.get('nombre', ''), translate=True)
        
        calidad = p.get('calidad_pantalla') or detect_screen_quality(p.get('nombre', ''))
        if calidad:
            p['calidad_pantalla'] = calidad
            p['calidad_info'] = get_quality_info(calidad)
    
    return {
        "productos": productos,
        "total": len(productos),
        "filtros_aplicados": {
            "marca": marca,
            "modelo": modelo,
            "tipo": tipo,
            "proveedor": proveedor,
            "solo_stock": solo_stock
        }
    }


@router.get("/repuestos/buscar/rapido")
async def buscar_repuestos_rapido(
    q: str = "",
    proveedor: Optional[str] = None,
    limit: int = 20
):
    """
    Búsqueda rápida de repuestos con autocompletado inteligente.
    Entiende sinónimos español/inglés (pantalla→screen/lcd/oled, batería→battery, etc.)
    Incluye información de calidad de pantalla si aplica.
    Prioriza coincidencias exactas y por relevancia.
    """
    if not q or len(q) < 2:
        return []
    
    from utils.product_translator import normalize_product_name
    import re
    
    q_lower = q.lower().strip()
    q_escaped = re.escape(q_lower)
    
    # Pipeline de agregación para ordenar por relevancia
    pipeline = []
    
    # Match stage - buscar por nombre, sku, sku_proveedor, nombre_es
    match_conditions = [
        {"nombre": {"$regex": q_escaped, "$options": "i"}},
        {"sku": {"$regex": q_escaped, "$options": "i"}},
        {"sku_proveedor": {"$regex": q_escaped, "$options": "i"}},
        {"nombre_es": {"$regex": q_escaped, "$options": "i"}},
    ]
    
    # Si tiene múltiples palabras, también buscar cada una
    words = q_lower.split()
    if len(words) > 1:
        for word in words:
            if len(word) >= 2:
                word_escaped = re.escape(word)
                match_conditions.append({"nombre": {"$regex": word_escaped, "$options": "i"}})
    
    match_stage = {"$match": {"$or": match_conditions}}
    
    # Filtro por proveedor si se especifica
    if proveedor:
        match_stage = {"$match": {"$and": [{"$or": match_conditions}, {"proveedor": proveedor}]}}
    
    pipeline.append(match_stage)
    
    # Add fields para calcular score de relevancia
    pipeline.append({
        "$addFields": {
            "relevance_score": {
                "$add": [
                    # Coincidencia exacta en nombre (case insensitive) = máxima prioridad
                    {"$cond": [{"$eq": [{"$toLower": "$nombre"}, q_lower]}, 100, 0]},
                    # Coincidencia exacta en SKU
                    {"$cond": [{"$eq": [{"$toLower": "$sku"}, q_lower]}, 90, 0]},
                    # Nombre empieza con la búsqueda
                    {"$cond": [{"$regexMatch": {"input": {"$toLower": "$nombre"}, "regex": f"^{q_escaped}"}}, 50, 0]},
                    # SKU empieza con la búsqueda
                    {"$cond": [{"$regexMatch": {"input": {"$toLower": {"$ifNull": ["$sku", ""]}}, "regex": f"^{q_escaped}"}}, 40, 0]},
                    # Nombre contiene la búsqueda completa
                    {"$cond": [{"$regexMatch": {"input": {"$toLower": "$nombre"}, "regex": q_escaped}}, 20, 0]},
                    # Boost por stock disponible
                    {"$cond": [{"$gt": [{"$ifNull": ["$stock", 0]}, 0]}, 5, 0]},
                ]
            }
        }
    })
    
    # Ordenar por relevancia descendente
    pipeline.append({"$sort": {"relevance_score": -1, "nombre": 1}})
    
    # Limitar resultados
    pipeline.append({"$limit": limit})
    
    # Proyección
    pipeline.append({
        "$project": {
            "_id": 0,
            "id": 1,
            "nombre": 1,
            "nombre_es": 1,
            "sku": 1,
            "sku_proveedor": 1,
            "precio_compra": 1,
            "precio_venta": 1,
            "stock": 1,
            "proveedor": 1,
            "categoria": 1,
            "imagen_url": 1,
            "calidad_pantalla": 1,
            "es_pantalla": 1,
            "relevance_score": 1
        }
    })
    
    # Ejecutar agregación
    resultados = await db.repuestos.aggregate(pipeline).to_list(limit)
    
    # Añadir info de calidad para pantallas y traducir nombres
    from utils.screen_quality import get_quality_info, detect_screen_quality
    
    for r in resultados:
        # Traducir nombre si no está ya traducido
        if not r.get('nombre_es'):
            r['nombre_es'] = normalize_product_name(r.get('nombre', ''), translate=True)
        
        # Si no tiene calidad guardada, intentar detectar
        calidad = r.get('calidad_pantalla')
        if not calidad and r.get('es_pantalla'):
            calidad = detect_screen_quality(r.get('nombre', ''))
        elif not calidad:
            calidad = detect_screen_quality(r.get('nombre', ''))
            if calidad:
                r['es_pantalla'] = True
        
        if calidad:
            r['calidad_pantalla'] = calidad
            r['calidad_info'] = get_quality_info(calidad)
        
        # Remover el score del resultado final (solo era para ordenar)
        r.pop('relevance_score', None)
    
    return resultados

@router.get("/repuestos/calidades-pantalla")
async def obtener_calidades_pantalla():
    """
    Obtiene la lista de calidades de pantalla disponibles con sus colores e información.
    """
    from utils.screen_quality import get_quality_info
    
    calidades = ['genuine', 'refurbished_genuine', 'soft_oled', 'hard_oled', 
                 'service_pack', 'oled', 'incell', 'desconocido']
    
    return {q: get_quality_info(q) for q in calidades}

@router.get("/repuestos/{repuesto_id}/alternativas")
async def obtener_alternativas(repuesto_id: str, limit: int = 10):
    """
    Obtiene productos alternativos/similares de otros proveedores para comparar precios.
    Busca productos con nombres similares de diferentes proveedores.
    """
    import re
    
    # Obtener el producto original
    producto = await db.repuestos.find_one({"id": repuesto_id}, {"_id": 0})
    if not producto:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")
    
    nombre = producto.get('nombre', '')
    proveedor_actual = producto.get('proveedor', '')
    
    # Extraer palabras clave del nombre (modelo, marca, etc.)
    # Limpiar el nombre de términos genéricos
    nombre_limpio = re.sub(r'\(.*?\)', '', nombre)  # Quitar paréntesis
    nombre_limpio = re.sub(r'aftermarket|assembly|compatible|for|para|con|with', '', nombre_limpio, flags=re.IGNORECASE)
    
    # Extraer modelo de dispositivo (ej: "iPhone 14 Pro", "Galaxy S24")
    modelo_match = re.search(r'(iphone\s+\d+\s*(?:pro|plus|max|mini)*|galaxy\s+[a-z]?\d+\s*(?:ultra|plus|\+)*|ipad\s+(?:pro|air|mini)?\s*\d*|pixel\s+\d+\s*(?:pro|a)*)', nombre, re.IGNORECASE)
    modelo = modelo_match.group(1) if modelo_match else None
    
    # Determinar tipo de producto (pantalla, batería, etc.)
    tipo_producto = None
    if re.search(r'lcd|oled|screen|pantalla|display', nombre, re.IGNORECASE):
        tipo_producto = 'pantalla'
    elif re.search(r'bater[ií]a|battery', nombre, re.IGNORECASE):
        tipo_producto = 'bateria'
    elif re.search(r'connector|conector|puerto|port|charging', nombre, re.IGNORECASE):
        tipo_producto = 'conector'
    
    # Construir query para buscar alternativas
    conditions = []
    
    # Debe ser de otro proveedor
    if proveedor_actual:
        conditions.append({"proveedor": {"$ne": proveedor_actual}})
    
    # Debe coincidir el modelo
    if modelo:
        conditions.append({"nombre": {"$regex": re.escape(modelo), "$options": "i"}})
    
    # Debe ser el mismo tipo de producto
    if tipo_producto == 'pantalla':
        conditions.append({"$or": [
            {"nombre": {"$regex": "lcd|oled|screen|pantalla|display", "$options": "i"}},
            {"es_pantalla": True}
        ]})
    elif tipo_producto:
        type_patterns = {
            'bateria': 'bater|battery',
            'conector': 'connector|conector|puerto|port|charging'
        }
        if tipo_producto in type_patterns:
            conditions.append({"nombre": {"$regex": type_patterns[tipo_producto], "$options": "i"}})
    
    if not conditions:
        return {"producto_original": producto, "alternativas": [], "mensaje": "No se pudo determinar criterios de búsqueda"}
    
    query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    
    # Buscar alternativas
    projection = {
        "_id": 0,
        "id": 1,
        "nombre": 1,
        "proveedor": 1,
        "precio_compra": 1,
        "precio_venta": 1,
        "stock": 1,
        "calidad_pantalla": 1,
        "es_pantalla": 1,
        "imagen_url": 1
    }
    
    alternativas = await db.repuestos.find(query, projection).limit(limit).to_list(limit)
    
    # Añadir info de calidad a cada alternativa
    from utils.screen_quality import get_quality_info, detect_screen_quality
    
    for alt in alternativas:
        calidad = alt.get('calidad_pantalla') or detect_screen_quality(alt.get('nombre', ''))
        if calidad:
            alt['calidad_pantalla'] = calidad
            alt['calidad_info'] = get_quality_info(calidad)
    
    # También añadir info al producto original
    calidad_orig = producto.get('calidad_pantalla') or detect_screen_quality(nombre)
    if calidad_orig:
        producto['calidad_pantalla'] = calidad_orig
        producto['calidad_info'] = get_quality_info(calidad_orig)
    
    return {
        "producto_original": producto,
        "alternativas": alternativas,
        "modelo_detectado": modelo,
        "tipo_producto": tipo_producto
    }

@router.patch("/repuestos/{repuesto_id}/calidad-pantalla")
async def actualizar_calidad_pantalla(repuesto_id: str, calidad: str, user: dict = Depends(require_admin)):
    """
    Actualiza manualmente la calidad de pantalla de un producto.
    """
    from utils.screen_quality import get_quality_info
    
    # Validar calidad
    calidades_validas = ['genuine', 'refurbished_genuine', 'soft_oled', 'hard_oled', 
                        'service_pack', 'oled', 'incell', 'desconocido']
    if calidad not in calidades_validas:
        raise HTTPException(status_code=400, detail=f"Calidad inválida. Valores permitidos: {calidades_validas}")
    
    repuesto = await db.repuestos.find_one({"id": repuesto_id}, {"_id": 0})
    if not repuesto:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")
    
    await db.repuestos.update_one(
        {"id": repuesto_id}, 
        {"$set": {
            "calidad_pantalla": calidad,
            "es_pantalla": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "Calidad actualizada",
        "calidad_pantalla": calidad,
        "calidad_info": get_quality_info(calidad)
    }


# ==================== VARIANTES DE PRODUCTOS ====================

@router.get("/repuestos/{repuesto_id}/variantes")
async def obtener_variantes_producto(repuesto_id: str):
    """
    Obtiene todas las variantes de un producto agrupadas automáticamente.
    Las variantes son productos similares que difieren en color, calidad, proveedor o capacidad.
    """
    import re
    from utils.screen_quality import get_quality_info, detect_screen_quality
    
    # Obtener el producto base
    producto = await db.repuestos.find_one({"id": repuesto_id}, {"_id": 0})
    if not producto:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")
    
    nombre = producto.get('nombre', '')
    
    # Extraer el "nombre base" normalizando el producto
    # Quitamos: colores, calidades, capacidades, paréntesis, etc.
    nombre_base = nombre.lower()
    
    # Quitar colores comunes
    colores = ['black', 'white', 'blue', 'red', 'green', 'gold', 'silver', 'purple', 'pink', 'yellow', 'orange',
               'negro', 'blanco', 'azul', 'rojo', 'verde', 'dorado', 'plateado', 'morado', 'rosa', 'amarillo', 'naranja',
               'space gray', 'midnight', 'starlight', 'graphite', 'pacific blue', 'sierra blue', 'alpine green']
    for color in colores:
        nombre_base = re.sub(rf'\b{color}\b', '', nombre_base, flags=re.IGNORECASE)
    
    # Quitar calidades de pantalla
    calidades = ['soft oled', 'hard oled', 'incell', 'original', 'oem', 'refurbished', 'genuine', 'service pack', 
                 'aftermarket', 'compatible', 'premium', 'high quality', 'hq', 'aaa', 'copy']
    for calidad in calidades:
        nombre_base = re.sub(rf'\b{calidad}\b', '', nombre_base, flags=re.IGNORECASE)
    
    # Quitar capacidades
    nombre_base = re.sub(r'\b\d+\s*gb\b', '', nombre_base, flags=re.IGNORECASE)
    nombre_base = re.sub(r'\b\d+\s*tb\b', '', nombre_base, flags=re.IGNORECASE)
    nombre_base = re.sub(r'\b\d+\s*mah\b', '', nombre_base, flags=re.IGNORECASE)
    
    # Quitar paréntesis y su contenido
    nombre_base = re.sub(r'\([^)]*\)', '', nombre_base)
    
    # Quitar caracteres especiales y espacios múltiples
    nombre_base = re.sub(r'[^\w\s]', ' ', nombre_base)
    nombre_base = re.sub(r'\s+', ' ', nombre_base).strip()
    
    # Extraer modelo del dispositivo para búsqueda más precisa
    modelo_match = re.search(r'(iphone\s+\d+\s*(?:pro|plus|max|mini)*|galaxy\s+[a-z]?\d+\s*(?:ultra|plus|\+)*|ipad\s+(?:pro|air|mini)?\s*\d*)', nombre, re.IGNORECASE)
    modelo = modelo_match.group(1).strip() if modelo_match else None
    
    # Extraer tipo de producto
    tipo_match = re.search(r'(pantalla|screen|lcd|display|bater[íi]a|battery|conector|connector|flex|cable|c[áa]mara|camera|altavoz|speaker|bot[óo]n|button)', nombre, re.IGNORECASE)
    tipo = tipo_match.group(1).lower() if tipo_match else None
    
    # Construir query de búsqueda para variantes
    if modelo and tipo:
        # Búsqueda precisa: mismo modelo y tipo de producto
        query = {
            "id": {"$ne": repuesto_id},
            "nombre": {
                "$regex": f"(?=.*{re.escape(modelo)})(?=.*{re.escape(tipo)})",
                "$options": "i"
            }
        }
    elif nombre_base and len(nombre_base) > 5:
        # Búsqueda por nombre base
        palabras = nombre_base.split()[:4]  # Tomar primeras 4 palabras
        regex_pattern = ".*".join([re.escape(p) for p in palabras if len(p) > 2])
        query = {
            "id": {"$ne": repuesto_id},
            "nombre": {"$regex": regex_pattern, "$options": "i"}
        }
    else:
        return {
            "producto_base": producto,
            "variantes": [],
            "nombre_base_detectado": nombre_base,
            "modelo_detectado": modelo,
            "tipo_detectado": tipo,
            "total_variantes": 0
        }
    
    # Proyección
    projection = {
        "_id": 0, "id": 1, "nombre": 1, "nombre_es": 1, "sku": 1, "sku_proveedor": 1,
        "precio_compra": 1, "precio_venta": 1, "stock": 1, "proveedor": 1,
        "color": 1, "calidad_pantalla": 1, "es_pantalla": 1, "imagen_url": 1
    }
    
    variantes = await db.repuestos.find(query, projection).limit(50).to_list(50)
    
    # Añadir info de calidad a cada variante
    for v in variantes:
        calidad = v.get('calidad_pantalla') or detect_screen_quality(v.get('nombre', ''))
        if calidad:
            v['calidad_pantalla'] = calidad
            v['calidad_info'] = get_quality_info(calidad)
        
        # Detectar color si no está asignado
        if not v.get('color'):
            for color in colores:
                if re.search(rf'\b{color}\b', v.get('nombre', ''), re.IGNORECASE):
                    v['color_detectado'] = color.capitalize()
                    break
    
    # También añadir info al producto base
    calidad_base = producto.get('calidad_pantalla') or detect_screen_quality(nombre)
    if calidad_base:
        producto['calidad_pantalla'] = calidad_base
        producto['calidad_info'] = get_quality_info(calidad_base)
    
    return {
        "producto_base": producto,
        "variantes": variantes,
        "nombre_base_detectado": nombre_base,
        "modelo_detectado": modelo,
        "tipo_detectado": tipo,
        "total_variantes": len(variantes)
    }


@router.patch("/repuestos/{repuesto_id}/color")
async def actualizar_color_producto(repuesto_id: str, color: str, user: dict = Depends(require_admin)):
    """
    Actualiza el color de un producto.
    """
    repuesto = await db.repuestos.find_one({"id": repuesto_id}, {"_id": 0})
    if not repuesto:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")
    
    await db.repuestos.update_one(
        {"id": repuesto_id},
        {"$set": {"color": color}}
    )
    
    return {"message": "Color actualizado", "color": color}


@router.get("/repuestos/grupos-variantes")
async def listar_grupos_variantes(
    page: int = 1,
    page_size: int = 20,
    search: str = ""
):
    """
    Lista productos agrupados por variantes.
    Agrupa productos similares para facilitar la gestión de variantes.
    """
    import re
    from utils.screen_quality import detect_screen_quality, get_quality_info
    
    # Pipeline de agregación para agrupar productos
    pipeline = []
    
    # Match opcional por búsqueda
    if search:
        pipeline.append({
            "$match": {
                "$or": [
                    {"nombre": {"$regex": search, "$options": "i"}},
                    {"sku": {"$regex": search, "$options": "i"}}
                ]
            }
        })
    
    # Crear un campo de agrupación basado en modelo/tipo extraído del nombre
    pipeline.append({
        "$addFields": {
            "grupo_key": {
                "$toLower": {
                    "$trim": {
                        "input": {
                            "$regexFind": {
                                "input": "$nombre",
                                "regex": "(iphone\\s+\\d+\\s*(?:pro|plus|max|mini)*|galaxy\\s+[a-z]?\\d+\\s*(?:ultra|plus|\\+)*|ipad\\s+(?:pro|air|mini)?\\s*\\d*)",
                                "options": "i"
                            }
                        }
                    }
                }
            }
        }
    })
    
    # Agrupar por modelo detectado
    pipeline.append({
        "$group": {
            "_id": "$grupo_key.match",
            "productos": {
                "$push": {
                    "id": "$id",
                    "nombre": "$nombre",
                    "sku": "$sku",
                    "precio_venta": "$precio_venta",
                    "precio_compra": "$precio_compra",
                    "stock": "$stock",
                    "proveedor": "$proveedor",
                    "color": "$color",
                    "calidad_pantalla": "$calidad_pantalla",
                    "imagen_url": "$imagen_url"
                }
            },
            "total_stock": {"$sum": "$stock"},
            "precio_min": {"$min": "$precio_venta"},
            "precio_max": {"$max": "$precio_venta"},
            "num_variantes": {"$sum": 1},
            "proveedores": {"$addToSet": "$proveedor"}
        }
    })
    
    # Filtrar grupos válidos (con modelo detectado y más de 1 variante)
    pipeline.append({
        "$match": {
            "_id": {"$ne": None},
            "num_variantes": {"$gt": 1}
        }
    })
    
    # Ordenar por número de variantes
    pipeline.append({"$sort": {"num_variantes": -1}})
    
    # Paginación
    pipeline.append({"$skip": (page - 1) * page_size})
    pipeline.append({"$limit": page_size})
    
    grupos = await db.repuestos.aggregate(pipeline).to_list(page_size)
    
    # Contar total de grupos
    count_pipeline = [
        {"$addFields": {
            "grupo_key": {
                "$toLower": {
                    "$trim": {
                        "input": {
                            "$regexFind": {
                                "input": "$nombre",
                                "regex": "(iphone\\s+\\d+\\s*(?:pro|plus|max|mini)*|galaxy\\s+[a-z]?\\d+\\s*(?:ultra|plus|\\+)*|ipad\\s+(?:pro|air|mini)?\\s*\\d*)",
                                "options": "i"
                            }
                        }
                    }
                }
            }
        }},
        {"$group": {"_id": "$grupo_key.match"}},
        {"$match": {"_id": {"$ne": None}}},
        {"$count": "total"}
    ]
    
    total_result = await db.repuestos.aggregate(count_pipeline).to_list(1)
    total = total_result[0]["total"] if total_result else 0
    
    return {
        "grupos": grupos,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.post("/repuestos/clasificar-pantallas")
async def clasificar_pantallas_masivo(user: dict = Depends(require_admin)):
    """
    Clasifica automáticamente todas las pantallas existentes en el inventario.
    Analiza el nombre de cada producto para detectar si es pantalla y su calidad.
    """
    from utils.screen_quality import detect_screen_quality, is_screen_product
    
    # Buscar productos que podrían ser pantallas
    cursor = db.repuestos.find(
        {"$or": [
            {"nombre": {"$regex": "pantalla|screen|lcd|oled|display", "$options": "i"}},
            {"categoria": {"$regex": "pantalla|screen|display", "$options": "i"}}
        ]},
        {"_id": 0, "id": 1, "nombre": 1, "calidad_pantalla": 1, "es_pantalla": 1}
    )
    
    productos = await cursor.to_list(50000)  # Procesar hasta 50k productos
    
    clasificados = 0
    ya_clasificados = 0
    no_pantalla = 0
    sin_calidad = 0
    
    for producto in productos:
        nombre = producto.get('nombre', '')
        id_producto = producto.get('id')
        
        # Si ya está clasificado, saltar
        if producto.get('calidad_pantalla') and producto.get('es_pantalla'):
            ya_clasificados += 1
            continue
        
        # Verificar si es pantalla
        if not is_screen_product(nombre):
            no_pantalla += 1
            continue
        
        # Detectar calidad
        calidad = detect_screen_quality(nombre)
        
        if calidad:
            await db.repuestos.update_one(
                {"id": id_producto},
                {"$set": {
                    "calidad_pantalla": calidad,
                    "es_pantalla": True,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            clasificados += 1
            if calidad == 'desconocido':
                sin_calidad += 1
    
    return {
        "mensaje": "Clasificación completada",
        "productos_analizados": len(productos),
        "nuevos_clasificados": clasificados,
        "ya_clasificados": ya_clasificados,
        "no_son_pantalla": no_pantalla,
        "sin_calidad_determinada": sin_calidad
    }

@router.post("/repuestos/traducir-nombres")
async def traducir_nombres_masivo(user: dict = Depends(require_admin)):
    """
    Traduce los nombres de productos de inglés a español.
    Solo procesa productos que no tienen nombre_es guardado.
    """
    from utils.product_translator import normalize_product_name, detect_category
    
    # Buscar productos sin nombre traducido (principalmente MobileSentrix)
    cursor = db.repuestos.find(
        {"$or": [
            {"nombre_es": {"$exists": False}},
            {"nombre_es": None},
            {"nombre_es": ""}
        ]},
        {"_id": 0, "id": 1, "nombre": 1, "categoria": 1}
    )
    
    productos = await cursor.to_list(50000)
    
    traducidos = 0
    categorias_actualizadas = 0
    
    for producto in productos:
        nombre = producto.get('nombre', '')
        id_producto = producto.get('id')
        
        if not nombre or not id_producto:
            continue
        
        # Traducir nombre
        nombre_es = normalize_product_name(nombre, translate=True)
        
        update_data = {
            "nombre_es": nombre_es,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Detectar categoría si no tiene
        if not producto.get('categoria'):
            categoria = detect_category(nombre)
            if categoria:
                update_data["categoria"] = categoria
                categorias_actualizadas += 1
        
        await db.repuestos.update_one(
            {"id": id_producto},
            {"$set": update_data}
        )
        traducidos += 1
    
    return {
        "mensaje": "Traducción completada",
        "productos_procesados": len(productos),
        "nombres_traducidos": traducidos,
        "categorias_asignadas": categorias_actualizadas
    }

@router.get("/repuestos/categorias")
async def listar_categorias():
    return await db.repuestos.distinct("categoria")

@router.get("/repuestos/{repuesto_id}", response_model=Repuesto)
async def obtener_repuesto(repuesto_id: str):
    repuesto = await db.repuestos.find_one({"id": repuesto_id}, {"_id": 0})
    if not repuesto:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")
    if isinstance(repuesto.get('created_at'), str):
        repuesto['created_at'] = datetime.fromisoformat(repuesto['created_at'])
    if isinstance(repuesto.get('updated_at'), str):
        repuesto['updated_at'] = datetime.fromisoformat(repuesto['updated_at'])
    return repuesto

@router.put("/repuestos/{repuesto_id}", response_model=Repuesto)
async def actualizar_repuesto(repuesto_id: str, repuesto: RepuestoCreate):
    existing = await db.repuestos.find_one({"id": repuesto_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")
    update_data = repuesto.model_dump()
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    await db.repuestos.update_one({"id": repuesto_id}, {"$set": update_data})
    updated = await db.repuestos.find_one({"id": repuesto_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    if isinstance(updated.get('updated_at'), str):
        updated['updated_at'] = datetime.fromisoformat(updated['updated_at'])
    return updated

@router.delete("/repuestos/{repuesto_id}")
async def eliminar_repuesto(repuesto_id: str):
    result = await db.repuestos.delete_one({"id": repuesto_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")
    return {"message": "Repuesto eliminado"}

@router.patch("/repuestos/{repuesto_id}/stock")
async def actualizar_stock(repuesto_id: str, cantidad: int, operacion: str = "set"):
    repuesto = await db.repuestos.find_one({"id": repuesto_id}, {"_id": 0})
    if not repuesto:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")
    if operacion == "add":
        nuevo_stock = repuesto['stock'] + cantidad
    elif operacion == "subtract":
        nuevo_stock = max(0, repuesto['stock'] - cantidad)
    else:
        nuevo_stock = cantidad
    await db.repuestos.update_one({"id": repuesto_id}, {"$set": {"stock": nuevo_stock, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": "Stock actualizado", "nuevo_stock": nuevo_stock}

@router.post("/repuestos/etiquetas")
async def generar_etiquetas(request: dict, user: dict = Depends(require_auth)):
    """
    Genera PDF con etiquetas de productos estilo profesional/industrial.
    Cada etiqueta contiene: nombre abreviado, modelo compatible, categoría, código de barras.
    request: { "ids": ["id1", "id2", ...], "cantidad_por_producto": 1, "formato": "65x30" }
    Formatos: "65x30" (estándar), "50x25" (pequeña), "70x40" (grande)
    """
    import io
    import barcode
    from barcode.writer import ImageWriter
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from fastapi.responses import StreamingResponse

    ids = request.get("ids", [])
    cantidad = request.get("cantidad_por_producto", 1)
    formato = request.get("formato", "65x30")

    if not ids:
        raise HTTPException(status_code=400, detail="Debe seleccionar al menos un producto")

    # Fetch products
    productos = []
    for pid in ids:
        p = await db.repuestos.find_one({"id": pid}, {"_id": 0})
        if p:
            productos.append(p)
    if not productos:
        raise HTTPException(status_code=404, detail="No se encontraron productos")

    # Label dimensions based on format
    if formato == "50x25":
        label_w, label_h = 50 * mm, 25 * mm
        cols, rows = 4, 10
        margin_x, margin_y = 5 * mm, 8 * mm
        gap_x, gap_y = 2 * mm, 2 * mm
        font_title, font_sub, font_small = 6, 5, 4
    elif formato == "70x40":
        label_w, label_h = 70 * mm, 40 * mm
        cols, rows = 2, 6
        margin_x, margin_y = 5 * mm, 10 * mm
        gap_x, gap_y = 3 * mm, 3 * mm
        font_title, font_sub, font_small = 9, 7, 5.5
    else:  # 65x30 default
        label_w, label_h = 65 * mm, 30 * mm
        cols, rows = 3, 9
        margin_x, margin_y = 3 * mm, 5 * mm
        gap_x, gap_y = 1.5 * mm, 1 * mm
        font_title, font_sub, font_small = 7, 5.5, 4.5

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4

    label_idx = 0
    labels_per_page = cols * rows

    # Build label list (with repetitions)
    all_labels = []
    for p in productos:
        for _ in range(cantidad):
            all_labels.append(p)

    for p in all_labels:
        if label_idx > 0 and label_idx % labels_per_page == 0:
            c.showPage()

        pos = label_idx % labels_per_page
        col = pos % cols
        row = pos // cols

        x = margin_x + col * (label_w + gap_x)
        y = page_h - margin_y - (row + 1) * (label_h + gap_y)

        # Get product info - use abreviatura if available, otherwise truncate nombre
        nombre_completo = p.get("nombre") or "Sin nombre"
        abreviatura = p.get("abreviatura") or ""
        modelo = p.get("modelo_compatible") or ""
        categoria = p.get("categoria") or ""
        sku = p.get("sku") or p.get("id", "")[:12]
        barcode_value = p.get("codigo_barras") or sku
        
        # Build display name: prefer abreviatura, fallback to first part of nombre
        if abreviatura:
            display_name = abreviatura[:30]
        else:
            # Try to abbreviate intelligently
            display_name = nombre_completo[:30]
        
        # Build specs line from modelo_compatible
        specs_line = ""
        if modelo:
            specs_line = f"({modelo})"[:35]

        # Draw label border
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.setLineWidth(0.5)
        c.rect(x, y, label_w, label_h)

        # Line 1: Product name (bold, centered)
        c.setFont("Helvetica-Bold", font_title)
        c.drawCentredString(x + label_w / 2, y + label_h - 4.5 * mm, display_name)

        # Line 2: Model/Specs (if available)
        if specs_line:
            c.setFont("Helvetica", font_sub)
            c.drawCentredString(x + label_w / 2, y + label_h - 8 * mm, specs_line)
            barcode_top = y + label_h - 10.5 * mm
        else:
            barcode_top = y + label_h - 7.5 * mm

        # Line 3: Category (small, gray)
        if categoria:
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.setFont("Helvetica", font_small)
            c.drawCentredString(x + label_w / 2, y + label_h - 11.5 * mm, categoria.upper())
            c.setFillColorRGB(0, 0, 0)
            barcode_top = y + label_h - 13.5 * mm

        # Generate barcode image (larger, professional style)
        try:
            clean_code = ''.join(c_char for c_char in str(barcode_value) if c_char.isalnum())
            if not clean_code:
                clean_code = sku.replace("-", "")[:12] or "0000000000"

            barcode_class = barcode.get_barcode_class('code128')
            bc = barcode_class(clean_code, writer=ImageWriter())
            bc_buf = io.BytesIO()
            bc.write(bc_buf, options={
                "write_text": False,  # We'll write text ourselves for better control
                "module_width": 0.3,
                "module_height": 10,
                "quiet_zone": 2,
            })
            bc_buf.seek(0)

            bc_img = ImageReader(bc_buf)
            bc_w = label_w - 6 * mm
            bc_h = barcode_top - y - 7 * mm
            if bc_h < 5 * mm:
                bc_h = 5 * mm
            c.drawImage(bc_img, x + 3 * mm, y + 5 * mm, width=bc_w, height=bc_h, preserveAspectRatio=True, anchor='c')
            
            # Barcode number below
            c.setFont("Courier", font_sub)
            c.drawCentredString(x + label_w / 2, y + 1.5 * mm, str(clean_code))
            
        except Exception:
            # Fallback: just print the code as text
            c.setFont("Courier", 8)
            c.drawCentredString(x + label_w / 2, y + 5 * mm, str(barcode_value))

        label_idx += 1

    c.save()
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=etiquetas_productos.pdf"}
    )


# ==================== ORDENES DE COMPRA ====================

@router.post("/ordenes-compra")
async def crear_orden_compra(orden_compra: OrdenCompraCreate, user: dict = Depends(require_auth)):
    """
    Crear orden de compra para material faltante.
    FLUJO DE TRAZABILIDAD:
    1. Al crear la OC, se añade el material a la orden de trabajo con estado 'pendiente_compra'
    2. La orden de trabajo queda bloqueada hasta que se resuelva
    3. El material en la orden tiene referencia a la OC
    """
    orden_trabajo = await db.ordenes.find_one({"id": orden_compra.orden_trabajo_id}, {"_id": 0})
    if not orden_trabajo:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada")
    
    # Crear la orden de compra
    oc = OrdenCompra(**orden_compra.model_dump())
    doc = oc.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    # Añadir el material a la orden de trabajo inmediatamente (estado pendiente_compra)
    materiales = orden_trabajo.get('materiales', [])
    nuevo_material = {
        "repuesto_id": orden_compra.repuesto_id,
        "nombre": orden_compra.nombre_pieza,
        "descripcion": orden_compra.descripcion,
        "cantidad": orden_compra.cantidad,
        "precio_unitario": orden_compra.precio_unitario or 0,
        "coste": orden_compra.coste_unitario or 0,
        "iva": 21.0,
        "descuento": 0,
        "añadido_por_tecnico": True,
        "aprobado": False,
        "pendiente_precios": True,
        "estado_material": "pendiente_compra",  # NUEVO: Estado de trazabilidad
        "orden_compra_id": oc.id,  # NUEVO: Vinculación a OC
        "orden_compra_numero": oc.numero_oc,  # NUEVO: Para búsquedas
        "solicitado_por": orden_compra.solicitado_por,
        "fecha_solicitud": datetime.now(timezone.utc).isoformat()
    }
    material_index = len(materiales)
    materiales.append(nuevo_material)
    
    # Guardar el índice del material en la OC
    doc['material_index_en_orden'] = material_index
    
    await db.ordenes_compra.insert_one(doc)
    
    # Eliminar _id de MongoDB de la respuesta
    doc.pop('_id', None)
    
    # Actualizar orden de trabajo con el nuevo material y bloquearla
    await db.ordenes.update_one(
        {"id": orden_compra.orden_trabajo_id},
        {"$set": {
            "materiales": materiales,
            "requiere_aprobacion": True,
            "bloqueada": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notificación
    notif = Notificacion(
        tipo="orden_compra_urgente", 
        mensaje=f"Nueva solicitud de pieza: {orden_compra.nombre_pieza} para {orden_trabajo['numero_orden']}. Orden BLOQUEADA hasta aprobación.",
        orden_id=orden_compra.orden_trabajo_id
    )
    notif_doc = notif.model_dump()
    notif_doc['created_at'] = notif_doc['created_at'].isoformat()
    notif_doc['orden_compra_id'] = oc.id
    await db.notificaciones.insert_one(notif_doc)
    
    return {**doc, "material_añadido": True, "material_index": material_index}

@router.get("/ordenes-compra")
async def listar_ordenes_compra(estado: Optional[str] = None, prioridad: Optional[str] = None, numero_pedido: Optional[str] = None, user: dict = Depends(require_auth)):
    """Listar órdenes de compra con filtros. Incluye búsqueda por número de pedido del proveedor."""
    query = {}
    conditions = []
    if estado:
        conditions.append({"estado": estado})
    if prioridad:
        conditions.append({"prioridad": prioridad})
    if numero_pedido:
        conditions.append({"numero_pedido_proveedor": {"$regex": numero_pedido, "$options": "i"}})
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    
    ordenes = await db.ordenes_compra.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Enriquecer con datos de la orden de trabajo
    for oc in ordenes:
        orden_trabajo = await db.ordenes.find_one(
            {"id": oc.get("orden_trabajo_id")}, 
            {"_id": 0, "numero_orden": 1, "numero_autorizacion": 1, "dispositivo": 1, "cliente_id": 1}
        )
        if orden_trabajo:
            oc["orden_trabajo_info"] = {
                "numero_orden": orden_trabajo.get("numero_orden"),
                "numero_autorizacion": orden_trabajo.get("numero_autorizacion"),
                "dispositivo": orden_trabajo.get("dispositivo", {}).get("modelo", "")
            }
    
    return ordenes

@router.get("/ordenes-compra/buscar-pedido/{numero_pedido}")
async def buscar_por_numero_pedido(numero_pedido: str, user: dict = Depends(require_auth)):
    """Buscar órdenes de compra por número de pedido del proveedor para identificar destino del material."""
    ordenes = await db.ordenes_compra.find(
        {"numero_pedido_proveedor": {"$regex": numero_pedido, "$options": "i"}},
        {"_id": 0}
    ).to_list(100)
    
    resultados = []
    for oc in ordenes:
        orden_trabajo = await db.ordenes.find_one(
            {"id": oc.get("orden_trabajo_id")},
            {"_id": 0, "numero_orden": 1, "numero_autorizacion": 1, "dispositivo": 1, "cliente_id": 1}
        )
        cliente = None
        if orden_trabajo:
            cliente = await db.clientes.find_one(
                {"id": orden_trabajo.get("cliente_id")},
                {"_id": 0, "nombre": 1, "apellidos": 1, "telefono": 1}
            )
        resultados.append({
            "orden_compra": oc,
            "orden_trabajo": orden_trabajo,
            "cliente": cliente
        })
    
    return {"numero_pedido": numero_pedido, "resultados": resultados, "total": len(resultados)}

@router.get("/ordenes-compra/{oc_id}")
async def obtener_orden_compra(oc_id: str, user: dict = Depends(require_auth)):
    oc = await db.ordenes_compra.find_one({"id": oc_id}, {"_id": 0})
    if not oc:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    
    # Enriquecer con información completa
    orden_trabajo = await db.ordenes.find_one({"id": oc.get("orden_trabajo_id")}, {"_id": 0})
    if orden_trabajo:
        oc["orden_trabajo_completa"] = {
            "numero_orden": orden_trabajo.get("numero_orden"),
            "numero_autorizacion": orden_trabajo.get("numero_autorizacion"),
            "dispositivo": orden_trabajo.get("dispositivo"),
            "estado": orden_trabajo.get("estado"),
            "cliente_id": orden_trabajo.get("cliente_id")
        }
        cliente = await db.clientes.find_one({"id": orden_trabajo.get("cliente_id")}, {"_id": 0, "nombre": 1, "apellidos": 1, "telefono": 1})
        if cliente:
            oc["cliente"] = cliente
    
    return oc

@router.patch("/ordenes-compra/{oc_id}")
async def actualizar_orden_compra(oc_id: str, data: OrdenCompraUpdate, user: dict = Depends(require_admin)):
    """
    Actualizar orden de compra con trazabilidad completa.
    
    ESTADOS Y ACCIONES:
    - pendiente -> aprobada: Material queda en estado 'compra_aprobada', orden sigue bloqueada
    - aprobada -> pedida: Se registra número de pedido, material en estado 'pedido_proveedor'
    - pedida -> recibida: Material se activa, se descuenta de inventario si aplica, orden se desbloquea
    - pendiente -> rechazada: Se elimina el material de la orden, se desbloquea
    """
    oc = await db.ordenes_compra.find_one({"id": oc_id}, {"_id": 0})
    if not oc:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    
    now = datetime.now(timezone.utc)
    update_data = {"updated_at": now.isoformat()}
    
    # Actualizar campos básicos
    if data.proveedor_id:
        update_data["proveedor_id"] = data.proveedor_id
    if data.precio_estimado is not None:
        update_data["precio_estimado"] = data.precio_estimado
    if data.precio_unitario is not None:
        update_data["precio_unitario"] = data.precio_unitario
    if data.coste_unitario is not None:
        update_data["coste_unitario"] = data.coste_unitario
    if data.notas_admin:
        update_data["notas_admin"] = data.notas_admin
    elif data.notas:
        update_data["notas_admin"] = data.notas
    if data.numero_pedido_proveedor:
        update_data["numero_pedido_proveedor"] = data.numero_pedido_proveedor
    if data.fecha_pedido:
        update_data["fecha_pedido"] = data.fecha_pedido
    
    orden_trabajo_id = oc.get("orden_trabajo_id")
    material_index = oc.get("material_index_en_orden")
    pieza_nombre = oc.get("nombre_pieza", "Repuesto")
    
    # Procesar cambio de estado
    if data.estado and data.estado != oc.get("estado"):
        update_data["estado"] = data.estado
        
        orden_trabajo = await db.ordenes.find_one({"id": orden_trabajo_id}, {"_id": 0}) if orden_trabajo_id else None
        materiales = orden_trabajo.get("materiales", []) if orden_trabajo else []
        
        if data.estado == "aprobada":
            # Material aprobado para compra
            if material_index is not None and material_index < len(materiales):
                materiales[material_index]["estado_material"] = "compra_aprobada"
                materiales[material_index]["fecha_aprobacion"] = now.isoformat()
                materiales[material_index]["aprobado_por"] = user.get("email", "admin")
                if data.precio_unitario:
                    materiales[material_index]["precio_unitario"] = data.precio_unitario
                if data.coste_unitario:
                    materiales[material_index]["coste"] = data.coste_unitario
                await db.ordenes.update_one(
                    {"id": orden_trabajo_id},
                    {"$set": {"materiales": materiales, "updated_at": now.isoformat()}}
                )
            
            notif = Notificacion(
                tipo="material_aprobado",
                mensaje=f"Material '{pieza_nombre}' APROBADO para compra. Pendiente hacer pedido al proveedor.",
                orden_id=orden_trabajo_id,
            )
            notif_doc = notif.model_dump()
            notif_doc['created_at'] = notif_doc['created_at'].isoformat()
            notif_doc['orden_compra_id'] = oc_id
            await db.notificaciones.insert_one(notif_doc)
        
        elif data.estado == "pedida":
            # Se hizo el pedido al proveedor
            if not data.numero_pedido_proveedor:
                raise HTTPException(status_code=400, detail="Se requiere número de pedido del proveedor")
            
            update_data["fecha_pedido"] = data.fecha_pedido or now.isoformat()
            
            if material_index is not None and material_index < len(materiales):
                materiales[material_index]["estado_material"] = "pedido_proveedor"
                materiales[material_index]["numero_pedido"] = data.numero_pedido_proveedor
                materiales[material_index]["fecha_pedido"] = update_data["fecha_pedido"]
                await db.ordenes.update_one(
                    {"id": orden_trabajo_id},
                    {"$set": {"materiales": materiales, "updated_at": now.isoformat()}}
                )
            
            notif = Notificacion(
                tipo="material_pedido",
                mensaje=f"Material '{pieza_nombre}' PEDIDO al proveedor. Nº Pedido: {data.numero_pedido_proveedor}",
                orden_id=orden_trabajo_id,
            )
            notif_doc = notif.model_dump()
            notif_doc['created_at'] = notif_doc['created_at'].isoformat()
            notif_doc['orden_compra_id'] = oc_id
            await db.notificaciones.insert_one(notif_doc)
        
        elif data.estado == "recibida":
            # Material recibido - activar en orden y posiblemente actualizar inventario
            update_data["fecha_recepcion"] = now.isoformat()
            
            if material_index is not None and material_index < len(materiales):
                materiales[material_index]["estado_material"] = "recibido"
                materiales[material_index]["aprobado"] = True
                materiales[material_index]["pendiente_precios"] = False
                materiales[material_index]["fecha_recepcion"] = now.isoformat()
                
                # NOTA: El stock NO se modifica aquí porque:
                # - El material ya fue descontado cuando se añadió originalmente a la orden
                # - Si es material nuevo (OC), no hay stock previo que descontar
                # - El stock se gestiona en el momento de añadir material desde inventario existente
                # 
                # Si en el futuro se quiere trackear entrada de stock por OC:
                # repuesto_id = oc.get("repuesto_id") or materiales[material_index].get("repuesto_id")
                # if repuesto_id:
                #     await db.repuestos.update_one({"id": repuesto_id}, {"$inc": {"stock": oc.get("cantidad", 1)}})
                
                # Verificar si hay más materiales pendientes
                materiales_pendientes = [m for m in materiales if m.get("estado_material") in ("pendiente_compra", "compra_aprobada", "pedido_proveedor")]
                
                update_orden = {"materiales": materiales, "updated_at": now.isoformat()}
                if not materiales_pendientes:
                    # Ya no hay materiales pendientes, desbloquear orden
                    update_orden["bloqueada"] = False
                    update_orden["requiere_aprobacion"] = False
                
                await db.ordenes.update_one({"id": orden_trabajo_id}, {"$set": update_orden})
            
            # Marcar notificaciones anteriores como leídas
            await db.notificaciones.update_many(
                {"orden_compra_id": oc_id, "leida": False},
                {"$set": {"leida": True}}
            )
            
            notif = Notificacion(
                tipo="material_recibido",
                mensaje=f"Material '{pieza_nombre}' RECIBIDO y asignado a orden {orden_trabajo.get('numero_orden', '')}.",
                orden_id=orden_trabajo_id,
            )
            notif_doc = notif.model_dump()
            notif_doc['created_at'] = notif_doc['created_at'].isoformat()
            notif_doc['orden_compra_id'] = oc_id
            await db.notificaciones.insert_one(notif_doc)
        
        elif data.estado == "rechazada":
            # Rechazar - eliminar material de la orden y desbloquear
            if material_index is not None and material_index < len(materiales):
                materiales.pop(material_index)
                
                # Actualizar índices de otras OC que apuntan a materiales posteriores
                await db.ordenes_compra.update_many(
                    {"orden_trabajo_id": orden_trabajo_id, "material_index_en_orden": {"$gt": material_index}},
                    {"$inc": {"material_index_en_orden": -1}}
                )
                
                # Verificar si hay más materiales pendientes
                materiales_pendientes = [m for m in materiales if m.get("estado_material") in ("pendiente_compra", "compra_aprobada", "pedido_proveedor")]
                
                update_orden = {"materiales": materiales, "updated_at": now.isoformat()}
                if not materiales_pendientes:
                    update_orden["bloqueada"] = False
                    update_orden["requiere_aprobacion"] = False
                
                await db.ordenes.update_one({"id": orden_trabajo_id}, {"$set": update_orden})
            
            notif = Notificacion(
                tipo="material_rechazado",
                mensaje=f"Material '{pieza_nombre}' RECHAZADO para {orden_trabajo.get('numero_orden', '')}.",
                orden_id=orden_trabajo_id,
            )
            notif_doc = notif.model_dump()
            notif_doc['created_at'] = notif_doc['created_at'].isoformat()
            notif_doc['orden_compra_id'] = oc_id
            await db.notificaciones.insert_one(notif_doc)
    
    await db.ordenes_compra.update_one({"id": oc_id}, {"$set": update_data})
    
    return {"message": "Orden de compra actualizada", "nuevo_estado": data.estado}

# ==================== RESTOS ====================

@router.post("/restos", response_model=DispositivoResto)
async def crear_resto(resto: DispositivoRestoCreate, user: dict = Depends(require_admin)):
    resto_obj = DispositivoResto(**resto.model_dump())
    doc = resto_obj.model_dump()
    doc['fecha_ingreso'] = doc['fecha_ingreso'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.restos.insert_one(doc)
    return resto_obj

@router.get("/restos")
async def listar_restos(activo: Optional[bool] = True, search: Optional[str] = None, user: dict = Depends(require_admin)):
    query = {}
    conditions = []
    if activo is not None:
        conditions.append({"activo": activo})
    if search:
        conditions.append({"$or": [{"modelo": {"$regex": search, "$options": "i"}}, {"imei": {"$regex": search, "$options": "i"}}, {"codigo": {"$regex": search, "$options": "i"}}]})
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    return await db.restos.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)

@router.get("/restos/{resto_id}")
async def obtener_resto(resto_id: str, user: dict = Depends(require_admin)):
    resto = await db.restos.find_one({"id": resto_id}, {"_id": 0})
    if not resto:
        raise HTTPException(status_code=404, detail="Dispositivo de restos no encontrado")
    return resto

@router.patch("/restos/{resto_id}/usar-pieza")
async def usar_pieza_resto(resto_id: str, pieza: str, orden_id: Optional[str] = None, user: dict = Depends(require_admin)):
    resto = await db.restos.find_one({"id": resto_id}, {"_id": 0})
    if not resto:
        raise HTTPException(status_code=404, detail="Dispositivo de restos no encontrado")
    piezas_disponibles = resto.get('piezas_aprovechables', [])
    if pieza not in piezas_disponibles:
        raise HTTPException(status_code=400, detail=f"La pieza '{pieza}' no está disponible")
    piezas_disponibles.remove(pieza)
    piezas_usadas = resto.get('piezas_usadas', [])
    piezas_usadas.append({"pieza": pieza, "orden_id": orden_id, "fecha": datetime.now(timezone.utc).isoformat(), "usado_por": user['user_id']})
    update_data = {"piezas_aprovechables": piezas_disponibles, "piezas_usadas": piezas_usadas}
    if not piezas_disponibles:
        update_data["activo"] = False
    await db.restos.update_one({"id": resto_id}, {"$set": update_data})
    return {"message": f"Pieza '{pieza}' marcada como usada", "piezas_restantes": len(piezas_disponibles)}

@router.delete("/restos/{resto_id}")
async def eliminar_resto(resto_id: str, user: dict = Depends(require_admin)):
    result = await db.restos.delete_one({"id": resto_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Dispositivo de restos no encontrado")
    return {"message": "Dispositivo de restos eliminado"}

"""
MobileSentrix API Integration Routes
Integración con el proveedor MobileSentrix para sincronización de productos, precios y pedidos.
API basada en Magento 2 REST API con OAuth 1.0a
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import httpx
import hashlib
import hmac
import base64
import urllib.parse
import uuid
import time
import asyncio
import os

from config import db, logger
from auth import require_auth, require_master

router = APIRouter(prefix="/mobilesentrix", tags=["MobileSentrix"])

# ==================== MODELS ====================

class MobileSentrixConfig(BaseModel):
    consumer_key: str
    consumer_secret: str
    access_token: Optional[str] = None
    access_token_secret: Optional[str] = None
    environment: str = "staging"  # staging | production
    # Feature flags - el master decide cuáles activar
    sync_products: bool = False
    sync_prices: bool = False
    sync_stock: bool = False
    auto_orders: bool = False
    sync_interval_minutes: int = 60
    last_sync: Optional[str] = None
    active: bool = False

class ProveedorMargenConfig(BaseModel):
    proveedor: str  # Nombre del proveedor
    margen: float = 27.0  # Margen en porcentaje (27% por defecto)
    activo: bool = True

class ProductSearchRequest(BaseModel):
    query: Optional[str] = None
    category_id: Optional[int] = None
    sku: Optional[str] = None
    page: int = 1
    page_size: int = 20

class ImportProductsRequest(BaseModel):
    product_ids: List[str]
    update_prices: bool = True
    update_stock: bool = True

class CreateOrderRequest(BaseModel):
    items: List[dict]  # [{sku, qty}]
    shipping_address: Optional[dict] = None
    notes: Optional[str] = None

class OAuthCallbackRequest(BaseModel):
    oauth_token: str
    oauth_verifier: str

# ==================== OAUTH 1.0a HELPER ====================

class MobileSentrixClient:
    """Cliente OAuth 1.0a para MobileSentrix API (Magento 2)"""
    
    # URLs de MobileSentrix - usar .eu para Europa
    STAGING_URL = "https://preprod.mobilesentrix.eu"
    PRODUCTION_URL = "https://www.mobilesentrix.eu"
    
    def __init__(self, consumer_key: str, consumer_secret: str, 
                 access_token: str = None, access_token_secret: str = None,
                 environment: str = "staging"):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.environment = environment
        self.base_url = self.PRODUCTION_URL if environment == "production" else self.STAGING_URL
    
    def _generate_nonce(self) -> str:
        return uuid.uuid4().hex
    
    def _generate_timestamp(self) -> str:
        return str(int(time.time()))
    
    def _percent_encode(self, s: str) -> str:
        return urllib.parse.quote(str(s), safe='')
    
    def _generate_signature(self, method: str, url: str, params: dict) -> str:
        """Generate OAuth 1.0a signature"""
        # Sort parameters
        sorted_params = sorted(params.items())
        param_string = '&'.join([f"{self._percent_encode(k)}={self._percent_encode(v)}" 
                                  for k, v in sorted_params])
        
        # Create signature base string
        base_string = '&'.join([
            method.upper(),
            self._percent_encode(url),
            self._percent_encode(param_string)
        ])
        
        # Create signing key
        signing_key = f"{self._percent_encode(self.consumer_secret)}&"
        if self.access_token_secret:
            signing_key += self._percent_encode(self.access_token_secret)
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            signing_key.encode('utf-8'),
            base_string.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    
    def _get_oauth_header(self, method: str, url: str, extra_params: dict = None) -> str:
        """Generate OAuth Authorization header"""
        oauth_params = {
            'oauth_consumer_key': self.consumer_key,
            'oauth_nonce': self._generate_nonce(),
            'oauth_signature_method': 'HMAC-SHA256',
            'oauth_timestamp': self._generate_timestamp(),
            'oauth_version': '1.0'
        }
        
        if self.access_token:
            oauth_params['oauth_token'] = self.access_token
        
        # Combine with extra params for signature
        all_params = {**oauth_params}
        if extra_params:
            all_params.update(extra_params)
        
        # Generate signature
        signature = self._generate_signature(method, url, all_params)
        oauth_params['oauth_signature'] = signature
        
        # Build Authorization header
        header_params = ', '.join([
            f'{self._percent_encode(k)}="{self._percent_encode(v)}"'
            for k, v in sorted(oauth_params.items())
        ])
        
        return f'OAuth {header_params}'
    
    def get_authorization_url(self, callback_url: str, for_admin: bool = False) -> str:
        """Generate URL for user authorization (Step 1)"""
        endpoint = "/oauth/authorize/identifier"
        params = {
            'consumer': 'revix.es',
            'authtype': '1',
            'flowentry': 'SignIn',
            'consumer_key': self.consumer_key,
            'consumer_secret': self.consumer_secret,
            'callback': callback_url
        }
        
        if for_admin:
            params['authorize_for'] = 'admin'
        
        query_string = '&'.join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
        return f"{self.base_url}{endpoint}?{query_string}"
    
    async def exchange_tokens(self, oauth_token: str, oauth_verifier: str) -> dict:
        """Exchange oauth_token and oauth_verifier for access_token (Step 2)"""
        endpoint = "/oauth/authorize/identifiercallback"
        url = f"{self.base_url}{endpoint}"
        
        # Intentar primero con JSON, luego con form-urlencoded si falla
        payload = {
            "consumer_key": self.consumer_key,
            "consumer_secret": self.consumer_secret,
            "oauth_token": oauth_token,
            "oauth_verifier": oauth_verifier
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                # Intento 1: JSON
                headers_json = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': 'NEXORA-CRM/1.0 (Revix.es Integration)'
                }
                response = await client.post(url, json=payload, headers=headers_json)
                
                logger.info(f"Token exchange response: {response.status_code} - {response.text[:300]}")
                
                # Si falla con JSON, probar form-urlencoded
                if response.status_code != 200 or '"status":0' in response.text:
                    logger.info("Reintentando con form-urlencoded...")
                    headers_form = {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Accept': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    form_data = f"consumer_key={self.consumer_key}&consumer_secret={self.consumer_secret}&oauth_token={oauth_token}&oauth_verifier={oauth_verifier}"
                    response = await client.post(url, content=form_data, headers=headers_form)
                    logger.info(f"Token exchange (form) response: {response.status_code} - {response.text[:300]}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get("status") == 1 and data.get("data"):
                            return {
                                "success": True,
                                "access_token": data["data"].get("access_token"),
                                "access_token_secret": data["data"].get("access_token_secret")
                            }
                        else:
                            return {"success": False, "error": f"Respuesta de MobileSentrix: {data.get('messgae', data)}"}
                    except:
                        return {"success": False, "error": f"Respuesta no JSON: {response.text[:200]}"}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text[:200]}"}
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _request(self, method: str, endpoint: str, params: dict = None, json_data: dict = None) -> dict:
        """Make authenticated request to MobileSentrix API"""
        if not self.access_token:
            return {"success": False, "error": "No hay Access Token configurado. Completa el proceso de autorización primero."}
        
        # MobileSentrix usa /api/rest/ no /rest/V1/
        url = f"{self.base_url}/api/rest{endpoint}"
        
        # Usar Bearer token simple (no OAuth header)
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'NEXORA-CRM/1.0 (Revix.es Integration)',
            'Authorization': f'Bearer {self.access_token}'
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                if method.upper() == 'GET':
                    response = await client.get(url, headers=headers, params=params)
                elif method.upper() == 'POST':
                    response = await client.post(url, headers=headers, json=json_data)
                elif method.upper() == 'PUT':
                    response = await client.put(url, headers=headers, json=json_data)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                if response.status_code == 403 and 'cloudflare' in response.text.lower():
                    return {"success": False, "error": "La API está protegida por Cloudflare.", "status": 403}
                
                if response.status_code == 200:
                    try:
                        return {"success": True, "data": response.json()}
                    except:
                        return {"success": True, "data": {"raw": response.text[:500]}}
                elif response.status_code == 401:
                    return {"success": False, "error": "Access Token inválido o expirado. Necesitas re-autorizar.", "status": 401}
                else:
                    logger.error(f"MobileSentrix API error: {response.status_code} - {response.text[:500]}")
                    return {"success": False, "error": f"Error {response.status_code}: {response.text[:200]}", "status": response.status_code}
        except httpx.ConnectError:
            return {"success": False, "error": "No se pudo conectar con MobileSentrix."}
        except httpx.TimeoutException:
            return {"success": False, "error": "Timeout: La API no respondió a tiempo."}
        except Exception as e:
            logger.error(f"MobileSentrix request error: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== API METHODS ====================
    
    async def test_connection(self) -> dict:
        """Test API connection - get products list"""
        return await self._request('GET', '/products?limit=1')
    
    async def get_categories(self) -> dict:
        """Get product categories - returns structured tree"""
        result = await self._request('GET', '/categories')
        if not result.get("success"):
            return result
        
        # La API puede devolver lista o diccionario
        categories_data = result.get("data", [])
        categories = []
        
        def parse_category_dict(cat_id, cat_data, parent_name=""):
            """Parsear categoría en formato diccionario"""
            if not isinstance(cat_data, dict):
                return None
            
            name = cat_data.get("name", f"Categoría {cat_id}")
            full_name = f"{parent_name} > {name}" if parent_name else name
            
            cat = {
                "id": int(cat_id) if str(cat_id).isdigit() else cat_id,
                "name": name,
                "full_name": full_name,
                "children": []
            }
            
            # Buscar subcategorías
            children = cat_data.get("children", {})
            if isinstance(children, dict):
                for child_id, child_data in children.items():
                    child = parse_category_dict(child_id, child_data, full_name)
                    if child:
                        cat["children"].append(child)
            elif isinstance(children, list):
                for child_data in children:
                    if isinstance(child_data, dict):
                        child = parse_category_list(child_data, full_name)
                        if child:
                            cat["children"].append(child)
            
            return cat
        
        def parse_category_list(cat_data, parent_name=""):
            """Parsear categoría en formato lista (Magento style)"""
            if not isinstance(cat_data, dict):
                return None
            
            cat_id = cat_data.get("id") or cat_data.get("entity_id") or cat_data.get("category_id")
            name = cat_data.get("name", f"Categoría {cat_id}")
            full_name = f"{parent_name} > {name}" if parent_name else name
            
            cat = {
                "id": cat_id,
                "name": name,
                "full_name": full_name,
                "children": []
            }
            
            # Buscar subcategorías
            children = cat_data.get("children_data", []) or cat_data.get("children", [])
            if isinstance(children, list):
                for child_data in children:
                    child = parse_category_list(child_data, full_name)
                    if child:
                        cat["children"].append(child)
            
            return cat
        
        # Procesar según el formato de la respuesta
        if isinstance(categories_data, dict):
            # Formato diccionario {id: {name, children}}
            for cat_id, cat_data in categories_data.items():
                if isinstance(cat_data, dict) and 'name' in cat_data:
                    cat = parse_category_dict(cat_id, cat_data)
                    if cat:
                        categories.append(cat)
        elif isinstance(categories_data, list):
            # Formato lista [{id, name, children_data}]
            for cat_data in categories_data:
                cat = parse_category_list(cat_data)
                if cat:
                    categories.append(cat)
        
        return {"success": True, "data": categories}
    
    async def search_products(self, query: str = None, category_id: int = None, 
                             page: int = 1, page_size: int = 20) -> dict:
        """Search products - optimizado para ser más rápido"""
        all_items = []
        
        # Si hay category_id, la búsqueda es más rápida (solo 1-2 páginas)
        # Si solo hay query sin categoría, limitar a 2 páginas para evitar timeouts
        pages_to_fetch = 2 if category_id else (2 if query else 1)
        
        for p in range(1, pages_to_fetch + 1):
            params = {'limit': 100, 'page': p}
            if category_id:
                params['category_id'] = category_id
            
            result = await self._request('GET', '/products', params)
            
            if not result.get("success"):
                if p == 1:
                    return result
                break
            
            products = result.get("data", {})
            
            # Filtrar solo los que son productos (tienen 'name')
            product_items = {k: v for k, v in products.items() 
                           if isinstance(v, dict) and 'name' in v}
            
            if not product_items:
                break
            
            # Convertir dict a lista
            for entity_id, prod in product_items.items():
                item = {
                    "entity_id": entity_id,
                    "sku": prod.get("sku"),
                    "name": prod.get("name"),
                    "price": prod.get("price"),
                    "qty": prod.get("qty"),
                    "status": prod.get("status"),
                    "default_image": prod.get("default_image")
                }
                
                # Filtrar por query si existe
                if query:
                    name = (prod.get("name") or "").lower()
                    sku = (prod.get("sku") or "").lower()
                    query_lower = query.lower().strip()
                    
                    # Dividir query en palabras y buscar todas
                    query_words = query_lower.split()
                    
                    # Buscar que todas las palabras estén en nombre o SKU
                    matches = True
                    for word in query_words:
                        if word not in name and word not in sku:
                            matches = False
                            break
                    
                    if not matches:
                        continue
                
                all_items.append(item)
            
            # Si hay menos de 100 productos, no hay más páginas
            if len(product_items) < 100:
                break
        
        # Paginar resultados
        start = (page - 1) * page_size
        end = start + page_size
        
        return {"success": True, "data": {"items": all_items[start:end], "total_count": len(all_items)}}
    
    async def get_product_by_sku(self, sku: str) -> dict:
        """Get single product by SKU"""
        # Buscar en la lista de productos
        result = await self._request('GET', '/products', {'limit': 1000})
        if not result.get("success"):
            return result
        
        for entity_id, prod in result.get("data", {}).items():
            if prod.get("sku") == sku:
                return {"success": True, "data": prod}
        
        return {"success": False, "error": f"Producto con SKU {sku} no encontrado"}
    
    async def get_stock_item(self, sku: str) -> dict:
        """Get stock info for a product"""
        return await self.get_product_by_sku(sku)
    
    async def create_cart(self) -> dict:
        """Create a new cart for guest checkout"""
        return await self._request('POST', '/guest-carts', json_data={})
    
    async def add_to_cart(self, cart_id: str, sku: str, qty: int) -> dict:
        """Add item to cart"""
        return await self._request('POST', f'/guest-carts/{cart_id}/items', json_data={
            'cartItem': {
                'sku': sku,
                'qty': qty,
                'quote_id': cart_id
            }
        })
    
    async def get_cart(self, cart_id: str) -> dict:
        """Get cart details"""
        return await self._request('GET', f'/guest-carts/{cart_id}')


# ==================== HELPER FUNCTIONS ====================

async def get_mobilesentrix_config() -> dict:
    """Get MobileSentrix configuration from database"""
    config = await db.configuracion.find_one({"tipo": "mobilesentrix"}, {"_id": 0})
    return config.get("datos", {}) if config else {}

async def save_mobilesentrix_config(config: dict):
    """Save MobileSentrix configuration to database"""
    await db.configuracion.update_one(
        {"tipo": "mobilesentrix"},
        {"$set": {"datos": config, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )

async def get_client() -> MobileSentrixClient:
    """Get configured MobileSentrix client"""
    config = await get_mobilesentrix_config()
    if not config.get("consumer_key") or not config.get("consumer_secret"):
        raise HTTPException(status_code=400, detail="MobileSentrix no está configurado")
    
    return MobileSentrixClient(
        consumer_key=config["consumer_key"],
        consumer_secret=config["consumer_secret"],
        access_token=config.get("access_token"),
        access_token_secret=config.get("access_token_secret"),
        environment=config.get("environment", "staging")
    )


# ==================== ROUTES ====================

@router.get("/config")
async def get_config(user: dict = Depends(require_master)):
    """Obtener configuración actual de MobileSentrix (solo master)"""
    config = await get_mobilesentrix_config()
    # Ocultar secretos parcialmente
    if config.get("consumer_secret"):
        config["consumer_secret"] = config["consumer_secret"][:8] + "..." + config["consumer_secret"][-4:]
    if config.get("access_token_secret"):
        config["access_token_secret"] = "***configurado***"
    return config

@router.post("/config")
async def save_config(config: MobileSentrixConfig, user: dict = Depends(require_master)):
    """Guardar configuración de MobileSentrix (solo master)"""
    config_dict = config.model_dump()
    config_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    config_dict["updated_by"] = user.get("email")
    
    await save_mobilesentrix_config(config_dict)
    
    logger.info(f"MobileSentrix config updated by {user.get('email')}")
    return {"message": "Configuración guardada", "config": config_dict}

@router.get("/oauth/start")
async def start_oauth(request: Request, user: dict = Depends(require_master)):
    """Iniciar proceso de autorización OAuth - devuelve URL para abrir en navegador"""
    config = await get_mobilesentrix_config()
    if not config.get("consumer_key") or not config.get("consumer_secret"):
        raise HTTPException(status_code=400, detail="Primero guarda Consumer Key y Consumer Secret")
    
    # Construir callback URL desde el request
    # Primero intentar desde env, si no desde el request
    frontend_url = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
    if not frontend_url:
        # Construir desde el request
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
        frontend_url = f"{scheme}://{host}"
    
    callback_url = f"{frontend_url}/api/mobilesentrix/oauth/callback"
    
    client = MobileSentrixClient(
        consumer_key=config["consumer_key"],
        consumer_secret=config["consumer_secret"],
        environment=config.get("environment", "staging")
    )
    
    auth_url = client.get_authorization_url(callback_url, for_admin=False)
    
    return {
        "authorization_url": auth_url,
        "callback_url": callback_url,
        "instructions": "Abre la URL de autorización en tu navegador y completa el login en MobileSentrix"
    }

@router.get("/oauth/callback")
async def oauth_callback(oauth_token: str = None, oauth_verifier: str = None):
    """Callback de OAuth - recibe tokens del navegador y los intercambia por Access Token"""
    if not oauth_token or not oauth_verifier:
        # Mostrar página de error
        return RedirectResponse(url="/mobilesentrix?error=missing_tokens")
    
    config = await get_mobilesentrix_config()
    if not config.get("consumer_key") or not config.get("consumer_secret"):
        return RedirectResponse(url="/mobilesentrix?error=not_configured")
    
    client = MobileSentrixClient(
        consumer_key=config["consumer_key"],
        consumer_secret=config["consumer_secret"],
        environment=config.get("environment", "staging")
    )
    
    # Intercambiar tokens
    result = await client.exchange_tokens(oauth_token, oauth_verifier)
    
    if result.get("success"):
        # Guardar access tokens en la configuración
        config["access_token"] = result["access_token"]
        config["access_token_secret"] = result["access_token_secret"]
        config["oauth_completed"] = True
        config["oauth_completed_at"] = datetime.now(timezone.utc).isoformat()
        await save_mobilesentrix_config(config)
        
        logger.info("MobileSentrix OAuth completed successfully")
        return RedirectResponse(url="/mobilesentrix?oauth=success")
    else:
        logger.error(f"MobileSentrix OAuth failed: {result.get('error')}")
        error_msg = urllib.parse.quote(result.get("error", "unknown"))
        return RedirectResponse(url=f"/mobilesentrix?oauth=error&message={error_msg}")

@router.post("/oauth/exchange")
async def exchange_tokens_manual(request: OAuthCallbackRequest, user: dict = Depends(require_master)):
    """Intercambiar tokens manualmente si el callback automático no funciona"""
    config = await get_mobilesentrix_config()
    if not config.get("consumer_key") or not config.get("consumer_secret"):
        raise HTTPException(status_code=400, detail="Primero guarda Consumer Key y Consumer Secret")
    
    client = MobileSentrixClient(
        consumer_key=config["consumer_key"],
        consumer_secret=config["consumer_secret"],
        environment=config.get("environment", "staging")
    )
    
    result = await client.exchange_tokens(request.oauth_token, request.oauth_verifier)
    
    if result.get("success"):
        config["access_token"] = result["access_token"]
        config["access_token_secret"] = result["access_token_secret"]
        config["oauth_completed"] = True
        config["oauth_completed_at"] = datetime.now(timezone.utc).isoformat()
        await save_mobilesentrix_config(config)
        
        return {"success": True, "message": "Access Token obtenido correctamente"}
    else:
        return {"success": False, "error": result.get("error")}

@router.post("/test-connection")
async def test_connection(user: dict = Depends(require_master)):
    """Probar conexión con la API de MobileSentrix"""
    try:
        client = await get_client()
        result = await client.test_connection()
        
        if result.get("success"):
            # Actualizar estado de conexión
            config = await get_mobilesentrix_config()
            config["last_connection_test"] = datetime.now(timezone.utc).isoformat()
            config["connection_status"] = "ok"
            await save_mobilesentrix_config(config)
            
            return {"success": True, "message": "Conexión exitosa", "data": result.get("data")}
        else:
            return {"success": False, "error": result.get("error")}
    except Exception as e:
        logger.error(f"MobileSentrix connection test failed: {e}")
        return {"success": False, "error": str(e)}

@router.get("/categories")
async def get_categories(user: dict = Depends(require_auth)):
    """Obtener categorías de productos de MobileSentrix"""
    client = await get_client()
    result = await client.get_categories()
    
    if result.get("success"):
        return result.get("data")
    else:
        raise HTTPException(status_code=500, detail=result.get("error"))

@router.post("/products/search")
async def search_products(request: ProductSearchRequest, user: dict = Depends(require_auth)):
    """Buscar productos en MobileSentrix"""
    client = await get_client()
    
    if request.sku:
        result = await client.get_product_by_sku(request.sku)
    else:
        result = await client.search_products(
            query=request.query,
            category_id=request.category_id,
            page=request.page,
            page_size=request.page_size
        )
    
    if result.get("success"):
        return result.get("data")
    else:
        raise HTTPException(status_code=500, detail=result.get("error"))

@router.get("/products/{sku}")
async def get_product(sku: str, user: dict = Depends(require_auth)):
    """Obtener detalle de un producto por SKU"""
    client = await get_client()
    result = await client.get_product_by_sku(sku)
    
    if result.get("success"):
        return result.get("data")
    else:
        raise HTTPException(status_code=500, detail=result.get("error"))

@router.get("/stock/{sku}")
async def get_stock(sku: str, user: dict = Depends(require_auth)):
    """Obtener stock de un producto"""
    client = await get_client()
    result = await client.get_stock_item(sku)
    
    if result.get("success"):
        return result.get("data")
    else:
        raise HTTPException(status_code=500, detail=result.get("error"))

@router.post("/import-products")
async def import_products(request: ImportProductsRequest, user: dict = Depends(require_master)):
    """Importar productos seleccionados al inventario local"""
    client = await get_client()
    imported = []
    errors = []
    
    for product_id in request.product_ids:
        try:
            result = await client.get_product_by_sku(product_id)
            if not result.get("success"):
                errors.append({"sku": product_id, "error": result.get("error")})
                continue
            
            product = result.get("data")
            
            # Buscar si ya existe en inventario local
            existing = await db.repuestos.find_one({"sku_proveedor": product_id}, {"_id": 0})
            
            # Extraer datos del producto
            price = 0
            for attr in product.get("custom_attributes", []):
                if attr.get("attribute_code") == "price":
                    price = float(attr.get("value", 0))
                    break
            if not price:
                price = float(product.get("price", 0))
            
            repuesto_data = {
                "nombre": product.get("name"),
                "sku_proveedor": product.get("sku"),
                "proveedor": "MobileSentrix",
                "proveedor_id": "mobilesentrix",
                "precio_coste": price,
                "precio_venta": round(price * 1.35, 2),  # 35% margen por defecto
                "stock_proveedor": product.get("extension_attributes", {}).get("stock_item", {}).get("qty", 0),
                "categoria": "Importado",
                "activo": True,
                "ultima_sync": datetime.now(timezone.utc).isoformat()
            }
            
            if existing:
                # Actualizar existente
                if request.update_prices:
                    repuesto_data["precio_coste"] = price
                if request.update_stock:
                    repuesto_data["stock_proveedor"] = product.get("extension_attributes", {}).get("stock_item", {}).get("qty", 0)
                
                await db.repuestos.update_one(
                    {"sku_proveedor": product_id},
                    {"$set": repuesto_data}
                )
                imported.append({"sku": product_id, "action": "updated", "name": product.get("name")})
            else:
                # Crear nuevo
                repuesto_data["id"] = str(uuid.uuid4())
                repuesto_data["sku"] = f"MS-{product.get('sku', '')[:20]}"
                repuesto_data["stock"] = 0  # Stock local inicial
                repuesto_data["created_at"] = datetime.now(timezone.utc).isoformat()
                
                await db.repuestos.insert_one(repuesto_data)
                imported.append({"sku": product_id, "action": "created", "name": product.get("name")})
                
        except Exception as e:
            errors.append({"sku": product_id, "error": str(e)})
    
    return {
        "imported": imported,
        "errors": errors,
        "total_imported": len(imported),
        "total_errors": len(errors)
    }

@router.post("/sync-prices")
async def sync_prices(background_tasks: BackgroundTasks, user: dict = Depends(require_master)):
    """Sincronizar precios de productos importados desde MobileSentrix"""
    config = await get_mobilesentrix_config()
    if not config.get("sync_prices"):
        raise HTTPException(status_code=400, detail="La sincronización de precios no está activada")
    
    # Ejecutar en background
    background_tasks.add_task(sync_prices_task)
    
    return {"message": "Sincronización de precios iniciada en segundo plano"}

async def sync_prices_task():
    """Background task para sincronizar precios"""
    try:
        client = await get_client()
        
        # Obtener productos importados de MobileSentrix
        productos = await db.repuestos.find(
            {"proveedor_id": "mobilesentrix"},
            {"_id": 0, "sku_proveedor": 1}
        ).to_list(1000)
        
        updated = 0
        for prod in productos:
            sku = prod.get("sku_proveedor")
            if not sku:
                continue
            
            result = await client.get_product_by_sku(sku)
            if result.get("success"):
                product = result.get("data")
                price = float(product.get("price", 0))
                
                await db.repuestos.update_one(
                    {"sku_proveedor": sku},
                    {"$set": {
                        "precio_coste": price,
                        "ultima_sync": datetime.now(timezone.utc).isoformat()
                    }}
                )
                updated += 1
            
            await asyncio.sleep(0.5)  # Rate limiting
        
        # Actualizar última sync
        config = await get_mobilesentrix_config()
        config["last_sync"] = datetime.now(timezone.utc).isoformat()
        config["last_sync_type"] = "prices"
        config["last_sync_count"] = updated
        await save_mobilesentrix_config(config)
        
        logger.info(f"MobileSentrix price sync completed: {updated} products updated")
    except Exception as e:
        logger.error(f"MobileSentrix price sync error: {e}")

@router.post("/sync-stock")
async def sync_stock(background_tasks: BackgroundTasks, user: dict = Depends(require_master)):
    """Sincronizar stock de productos desde MobileSentrix"""
    config = await get_mobilesentrix_config()
    if not config.get("sync_stock"):
        raise HTTPException(status_code=400, detail="La sincronización de stock no está activada")
    
    background_tasks.add_task(sync_stock_task)
    
    return {"message": "Sincronización de stock iniciada en segundo plano"}

async def sync_stock_task():
    """Background task para sincronizar stock"""
    try:
        client = await get_client()
        
        productos = await db.repuestos.find(
            {"proveedor_id": "mobilesentrix"},
            {"_id": 0, "sku_proveedor": 1}
        ).to_list(1000)
        
        updated = 0
        for prod in productos:
            sku = prod.get("sku_proveedor")
            if not sku:
                continue
            
            result = await client.get_stock_item(sku)
            if result.get("success"):
                stock_data = result.get("data")
                qty = stock_data.get("qty", 0)
                
                await db.repuestos.update_one(
                    {"sku_proveedor": sku},
                    {"$set": {
                        "stock_proveedor": qty,
                        "ultima_sync_stock": datetime.now(timezone.utc).isoformat()
                    }}
                )
                updated += 1
            
            await asyncio.sleep(0.5)
        
        config = await get_mobilesentrix_config()
        config["last_sync"] = datetime.now(timezone.utc).isoformat()
        config["last_sync_type"] = "stock"
        config["last_sync_count"] = updated
        await save_mobilesentrix_config(config)
        
        logger.info(f"MobileSentrix stock sync completed: {updated} products updated")
    except Exception as e:
        logger.error(f"MobileSentrix stock sync error: {e}")

@router.get("/orders")
async def get_orders(user: dict = Depends(require_auth)):
    """Obtener pedidos realizados a MobileSentrix"""
    orders = await db.pedidos_proveedor.find(
        {"proveedor_id": "mobilesentrix"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return orders

@router.post("/sync-precios")
async def sync_precios_productos(background_tasks: BackgroundTasks, user: dict = Depends(require_master)):
    """
    Sincronizar precios de productos MobileSentrix.
    Obtiene precios del endpoint individual de cada producto.
    """
    global sync_progress
    
    if sync_progress["running"]:
        return {"message": "Ya hay una sincronización en curso", "progress": sync_progress}
    
    # Obtener margen
    margenes_config = await db.configuracion.find_one({"tipo": "margenes_proveedores"}, {"_id": 0})
    margen = 27.0
    if margenes_config and margenes_config.get("proveedores", {}).get("MobileSentrix"):
        margen = margenes_config["proveedores"]["MobileSentrix"].get("margen", 27.0)
    
    background_tasks.add_task(sync_precios_task, margen)
    
    return {"message": "Sincronización de precios iniciada en segundo plano", "margen": margen}

async def sync_precios_task(margen: float):
    """Tarea de fondo para sincronizar precios"""
    global sync_progress
    
    try:
        sync_progress = {
            "running": True,
            "phase": "precios",
            "total": 0,
            "processed": 0,
            "imported": 0,
            "updated": 0,
            "errors": 0,
            "current_page": 0,
            "last_error": None
        }
        
        client = await get_client()
        
        # Obtener productos sin precio o con precio 0
        productos = await db.repuestos.find(
            {"proveedor": "MobileSentrix", "$or": [{"precio_compra": 0}, {"precio_compra": {"$exists": False}}]},
            {"_id": 0, "id": 1, "nombre": 1, "sku_proveedor": 1}
        ).limit(5000).to_list(5000)
        
        sync_progress["total"] = len(productos)
        logger.info(f"MobileSentrix: Actualizando precios de {len(productos)} productos")
        
        updated = 0
        errors = 0
        
        for idx, producto in enumerate(productos):
            if not sync_progress["running"]:
                break
            
            sync_progress["processed"] = idx + 1
            sku = producto.get("sku_proveedor")
            
            if not sku:
                continue
            
            try:
                # Buscar el producto por SKU - esto devuelve el precio directamente
                search_result = await client._request('GET', '/products', {'sku': sku})
                
                if not search_result.get("success"):
                    continue
                
                products_data = search_result.get("data", {})
                if not products_data:
                    continue
                
                # Obtener el primer producto de la respuesta
                for entity_id, prod in products_data.items():
                    if not isinstance(prod, dict):
                        continue
                    
                    # Obtener precio directamente de la búsqueda
                    price = 0
                    if prod.get("final_price_with_tax"):
                        price = float(prod.get("final_price_with_tax", 0))
                    elif prod.get("regular_price_with_tax"):
                        price = float(prod.get("regular_price_with_tax", 0))
                    
                    if price > 0:
                        precio_venta = round(price * (1 + margen / 100), 2)
                        
                        # Obtener imagen
                        imagen_url = prod.get("image_url") or prod.get("default_image")
                        
                        update_data = {
                            "precio_compra": price,
                            "precio_venta": precio_venta,
                            "ultima_sync": datetime.now(timezone.utc).isoformat()
                        }
                        
                        if imagen_url:
                            update_data["imagen_url"] = imagen_url
                        
                        await db.repuestos.update_one(
                            {"id": producto["id"]},
                            {"$set": update_data}
                        )
                        updated += 1
                        sync_progress["updated"] = updated
                        
                        if updated % 100 == 0:
                            logger.info(f"MobileSentrix: {updated} precios actualizados de {idx + 1} procesados")
                    
                    break  # Solo procesar el primer resultado
                
                # Pequeña pausa para no saturar la API
                if idx % 10 == 0:
                    await asyncio.sleep(0.2)
                    
            except Exception as e:
                errors += 1
                sync_progress["errors"] = errors
                if errors < 10:
                    logger.error(f"Error actualizando precio de {sku}: {e}")
        
        # Actualizar config
        config = await get_mobilesentrix_config()
        config["last_sync"] = datetime.now(timezone.utc).isoformat()
        config["last_sync_type"] = "precios"
        config["last_sync_count"] = updated
        await save_mobilesentrix_config(config)
        
        logger.info(f"MobileSentrix: Sincronización de precios completada. Actualizados: {updated}, Errores: {errors}")
        
    except Exception as e:
        logger.error(f"MobileSentrix sync precios error: {e}")
        sync_progress["last_error"] = str(e)
    finally:
        sync_progress["running"] = False

@router.post("/orders")
async def create_order(request: CreateOrderRequest, user: dict = Depends(require_master)):
    """Crear pedido a MobileSentrix"""
    config = await get_mobilesentrix_config()
    if not config.get("auto_orders"):
        raise HTTPException(status_code=400, detail="Los pedidos automáticos no están activados")
    
    client = await get_client()
    
    # Crear carrito
    cart_result = await client.create_cart()
    if not cart_result.get("success"):
        raise HTTPException(status_code=500, detail=f"Error creando carrito: {cart_result.get('error')}")
    
    cart_id = cart_result.get("data")
    
    # Añadir items
    for item in request.items:
        add_result = await client.add_to_cart(cart_id, item["sku"], item["qty"])
        if not add_result.get("success"):
            raise HTTPException(status_code=500, detail=f"Error añadiendo {item['sku']}: {add_result.get('error')}")
    
    # Obtener carrito final
    cart = await client.get_cart(cart_id)
    
    # Guardar pedido local
    order_doc = {
        "id": str(uuid.uuid4()),
        "proveedor_id": "mobilesentrix",
        "proveedor_nombre": "MobileSentrix",
        "cart_id": cart_id,
        "items": request.items,
        "cart_data": cart.get("data") if cart.get("success") else None,
        "status": "cart_created",
        "notes": request.notes,
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.pedidos_proveedor.insert_one(order_doc)
    
    return {
        "message": "Carrito creado correctamente",
        "order_id": order_doc["id"],
        "cart_id": cart_id,
        "cart": cart.get("data") if cart.get("success") else None
    }

@router.get("/stats")
async def get_stats(user: dict = Depends(require_auth)):
    """Obtener estadísticas de la integración"""
    config = await get_mobilesentrix_config()
    
    # Contar productos importados
    productos_count = await db.repuestos.count_documents({"proveedor_id": "mobilesentrix"})
    
    # Contar pedidos
    pedidos_count = await db.pedidos_proveedor.count_documents({"proveedor_id": "mobilesentrix"})
    
    return {
        "productos_importados": productos_count,
        "pedidos_realizados": pedidos_count,
        "ultima_sync": config.get("last_sync"),
        "ultima_sync_tipo": config.get("last_sync_type"),
        "connection_status": config.get("connection_status"),
        "features": {
            "sync_products": config.get("sync_products", False),
            "sync_prices": config.get("sync_prices", False),
            "sync_stock": config.get("sync_stock", False),
            "auto_orders": config.get("auto_orders", False)
        }
    }


# ==================== MÁRGENES POR PROVEEDOR ====================

@router.get("/margenes")
async def get_margenes_proveedores(user: dict = Depends(require_auth)):
    """Obtener configuración de márgenes por proveedor"""
    margenes = await db.configuracion.find_one({"tipo": "margenes_proveedores"}, {"_id": 0})
    
    if not margenes:
        # Crear configuración por defecto
        margenes = {
            "tipo": "margenes_proveedores",
            "proveedores": {
                "MobileSentrix": {"margen": 27.0, "activo": True},
                "Utopya": {"margen": 25.0, "activo": True},
                "Otro": {"margen": 30.0, "activo": True}
            }
        }
        await db.configuracion.insert_one(margenes)
    
    return margenes.get("proveedores", {})

@router.post("/margenes")
async def save_margenes_proveedores(request: dict, user: dict = Depends(require_master)):
    """Guardar configuración de márgenes por proveedor (Solo Master)"""
    await db.configuracion.update_one(
        {"tipo": "margenes_proveedores"},
        {"$set": {"proveedores": request}},
        upsert=True
    )
    return {"message": "Márgenes actualizados correctamente"}

@router.post("/margenes/{proveedor}")
async def set_margen_proveedor(proveedor: str, margen: float, user: dict = Depends(require_master)):
    """Establecer margen para un proveedor específico (Solo Master)"""
    await db.configuracion.update_one(
        {"tipo": "margenes_proveedores"},
        {"$set": {f"proveedores.{proveedor}": {"margen": margen, "activo": True}}},
        upsert=True
    )
    return {"message": f"Margen de {proveedor} actualizado a {margen}%"}

# ==================== DESCARGA DEL CATÁLOGO POR CATEGORÍAS ====================

# Variable global para tracking del progreso
sync_progress = {
    "running": False,
    "total": 0,
    "processed": 0,
    "imported": 0,
    "updated": 0,
    "errors": 0,
    "current_page": 0,
    "total_pages": 0,
    "current_category": "",
    "categories_done": 0,
    "categories_total": 0,
    "status": "idle",
    "last_error": None
}

@router.get("/sync-catalogo/progress")
async def get_sync_progress(user: dict = Depends(require_auth)):
    """Obtener progreso de la sincronización del catálogo"""
    return sync_progress

@router.get("/selected-categories")
async def get_selected_categories(user: dict = Depends(require_auth)):
    """Obtener categorías seleccionadas para sincronización"""
    config = await get_mobilesentrix_config()
    return config.get("selected_categories", [])

@router.post("/selected-categories")
async def save_selected_categories(request: dict, user: dict = Depends(require_master)):
    """Guardar categorías seleccionadas para sincronización"""
    config = await get_mobilesentrix_config()
    config["selected_categories"] = request.get("categories", [])
    await save_mobilesentrix_config(config)
    return {"message": "Categorías guardadas", "count": len(config["selected_categories"])}

@router.post("/sync-catalogo")
async def sync_catalogo_completo(background_tasks: BackgroundTasks, user: dict = Depends(require_master)):
    """
    Descargar catálogo de MobileSentrix (categorías seleccionadas o todo).
    """
    global sync_progress
    
    if sync_progress["running"]:
        raise HTTPException(status_code=400, detail="Ya hay una sincronización en curso")
    
    config = await get_mobilesentrix_config()
    if not config.get("sync_products"):
        raise HTTPException(status_code=400, detail="Activa 'Sincronizar Productos' en la configuración primero")
    
    # Obtener categorías seleccionadas
    selected_categories = config.get("selected_categories", [])
    
    # Obtener margen del proveedor
    margenes_config = await db.configuracion.find_one({"tipo": "margenes_proveedores"}, {"_id": 0})
    margen = 27.0
    if margenes_config and margenes_config.get("proveedores", {}).get("MobileSentrix"):
        margen = margenes_config["proveedores"]["MobileSentrix"].get("margen", 27.0)
    
    background_tasks.add_task(sync_catalogo_task, margen, selected_categories)
    
    return {
        "message": "Sincronización del catálogo iniciada",
        "margen_aplicado": margen,
        "categorias": len(selected_categories) if selected_categories else "todas"
    }

async def sync_catalogo_task(margen: float, selected_category_ids: list = None):
    """Background task para sincronizar el catálogo por categorías"""
    global sync_progress
    
    sync_progress = {
        "running": True,
        "total": 0,
        "processed": 0,
        "imported": 0,
        "updated": 0,
        "errors": 0,
        "current_page": 0,
        "total_pages": 0,
        "current_category": "",
        "categories_done": 0,
        "categories_total": 0,
        "status": "starting",
        "last_error": None
    }
    
    try:
        client = await get_client()
        
        # Obtener categorías del API
        sync_progress["status"] = "loading_categories"
        cat_result = await client.get_categories()
        
        if not cat_result.get("success"):
            sync_progress["status"] = "error"
            sync_progress["last_error"] = f"No se pudieron cargar categorías: {cat_result.get('error')}"
            sync_progress["running"] = False
            return
        
        all_categories = cat_result.get("data", [])
        
        # Aplanar categorías para obtener lista de IDs
        def flatten_categories(cats, result=None):
            if result is None:
                result = []
            for cat in cats:
                if isinstance(cat, dict):
                    result.append(cat)
                    if cat.get("children"):
                        flatten_categories(cat["children"], result)
            return result
        
        flat_cats = flatten_categories(all_categories)
        
        # Filtrar por categorías seleccionadas si hay alguna
        if selected_category_ids:
            cats_to_sync = [c for c in flat_cats if str(c.get("id")) in [str(x) for x in selected_category_ids]]
        else:
            cats_to_sync = flat_cats
        
        if not cats_to_sync:
            # Si no hay categorías filtradas, sincronizar todo sin filtro
            sync_progress["status"] = "downloading"
            sync_progress["current_category"] = "Todo el catálogo"
            sync_progress["categories_total"] = 1
            await _sync_products_paginated(client, None, margen)
            sync_progress["categories_done"] = 1
        else:
            sync_progress["categories_total"] = len(cats_to_sync)
            
            for cat_idx, cat in enumerate(cats_to_sync):
                if not sync_progress["running"]:
                    break
                
                cat_name = cat.get("name", f"Cat {cat.get('id')}")
                cat_id = cat.get("id")
                sync_progress["current_category"] = cat_name
                sync_progress["status"] = "downloading"
                
                logger.info(f"MobileSentrix: Sincronizando categoría '{cat_name}' ({cat_idx+1}/{len(cats_to_sync)})")
                
                await _sync_products_paginated(client, cat_id, margen)
                
                sync_progress["categories_done"] = cat_idx + 1
        
        # Actualizar configuración
        config = await get_mobilesentrix_config()
        config["last_sync"] = datetime.now(timezone.utc).isoformat()
        config["last_sync_type"] = "catalogo"
        config["last_sync_count"] = sync_progress["imported"] + sync_progress["updated"]
        await save_mobilesentrix_config(config)
        
        sync_progress["status"] = "completed"
        logger.info(f"MobileSentrix sync completed: {sync_progress['imported']} imported, {sync_progress['updated']} updated, {sync_progress['errors']} errors")
        
    except Exception as e:
        sync_progress["status"] = "error"
        sync_progress["last_error"] = str(e)
        logger.error(f"MobileSentrix catalog sync error: {e}")
    
    finally:
        sync_progress["running"] = False


async def _sync_products_paginated(client, category_id, margen: float):
    """Descargar y procesar productos de una categoría (o todo si category_id es None)"""
    global sync_progress
    
    page = 1
    max_pages = 500  # Límite de seguridad
    
    while page <= max_pages and sync_progress["running"]:
        sync_progress["current_page"] = page
        
        params = {'limit': 100, 'page': page}
        if category_id:
            params['category_id'] = category_id
        
        result = await client._request('GET', '/products', params)
        
        if not result.get("success"):
            sync_progress["last_error"] = result.get("error")
            logger.error(f"MobileSentrix: Error página {page}: {result.get('error')}")
            break
        
        products_data = result.get("data", {})
        if not products_data:
            break
        
        # Filtrar solo productos válidos (diccionarios con 'name')
        if isinstance(products_data, dict):
            products = {k: v for k, v in products_data.items() if isinstance(v, dict) and v.get("name")}
        elif isinstance(products_data, list):
            products = {str(i): p for i, p in enumerate(products_data) if isinstance(p, dict) and p.get("name")}
        else:
            break
        
        if not products:
            break
        
        # Procesar cada producto de esta página inmediatamente
        for entity_id, product in products.items():
            if not sync_progress["running"]:
                break
            
            try:
                sku = product.get("sku", "")
                if not sku:
                    continue
                
                # Obtener precio - usar campos correctos de la API de MobileSentrix
                price = 0
                # Prioridad: final_price_with_tax > regular_price_with_tax > price
                if product.get("final_price_with_tax"):
                    price = float(product.get("final_price_with_tax", 0))
                elif product.get("regular_price_with_tax"):
                    price = float(product.get("regular_price_with_tax", 0))
                elif product.get("price"):
                    price = float(product.get("price", 0))
                
                precio_venta = round(price * (1 + margen / 100), 2) if price > 0 else 0
                
                stock_qty = 0
                # Verificar stock
                if product.get("is_in_stock"):
                    stock_qty = 1  # Al menos 1 si está en stock
                ext_attrs = product.get("extension_attributes", {})
                if isinstance(ext_attrs, dict):
                    stock_item = ext_attrs.get("stock_item", {})
                    if isinstance(stock_item, dict):
                        stock_qty = stock_item.get("qty", stock_qty)
                
                # Obtener imagen - usar campo correcto
                imagen_url = product.get("image_url") or product.get("default_image") or None
                
                repuesto_data = {
                    "nombre": product.get("name", sku),
                    "categoria": "MobileSentrix",
                    "sku_proveedor": sku,
                    "proveedor": "MobileSentrix",
                    "proveedor_id": "mobilesentrix",
                    "precio_compra": price,
                    "precio_venta": precio_venta,
                    "stock_proveedor": int(stock_qty) if stock_qty else 0,
                    "imagen_url": imagen_url,
                    "ultima_sync": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                existing = await db.repuestos.find_one({"sku_proveedor": sku, "proveedor": "MobileSentrix"})
                
                if existing:
                    await db.repuestos.update_one(
                        {"sku_proveedor": sku, "proveedor": "MobileSentrix"},
                        {"$set": repuesto_data}
                    )
                    sync_progress["updated"] += 1
                else:
                    repuesto_data["id"] = str(uuid.uuid4())
                    repuesto_data["sku"] = sku
                    repuesto_data["codigo_barras"] = sku
                    repuesto_data["stock"] = 0
                    repuesto_data["stock_minimo"] = 0
                    repuesto_data["created_at"] = datetime.now(timezone.utc).isoformat()
                    
                    await db.repuestos.insert_one(repuesto_data)
                    sync_progress["imported"] += 1
                
                sync_progress["processed"] += 1
                sync_progress["total"] = sync_progress["processed"]
                
            except Exception as e:
                sync_progress["errors"] += 1
                logger.error(f"Error procesando {product.get('sku', '?')}: {e}")
        
        logger.info(f"MobileSentrix: Página {page} procesada. Importados: {sync_progress['imported']}, Actualizados: {sync_progress['updated']}")
        
        if len(products) < 100:
            break
        
        page += 1
        await asyncio.sleep(0.3)  # Rate limiting

@router.post("/sync-catalogo/stop")
async def stop_sync_catalogo(user: dict = Depends(require_master)):
    """Detener la sincronización en curso"""
    global sync_progress
    
    if not sync_progress["running"]:
        raise HTTPException(status_code=400, detail="No hay sincronización en curso")
    
    sync_progress["status"] = "stopping"
    sync_progress["running"] = False
    
    return {"message": "Sincronización detenida"}

@router.post("/recalcular-precios")
async def recalcular_precios_proveedor(proveedor: str = "MobileSentrix", user: dict = Depends(require_master)):
    """Recalcular precios de venta de un proveedor según su margen configurado"""
    
    # Obtener margen
    margenes_config = await db.configuracion.find_one({"tipo": "margenes_proveedores"}, {"_id": 0})
    margen = 27.0
    if margenes_config and margenes_config.get("proveedores", {}).get(proveedor):
        margen = margenes_config["proveedores"][proveedor].get("margen", 27.0)
    
    # Actualizar todos los productos del proveedor
    productos = await db.repuestos.find({"proveedor": proveedor}, {"_id": 0}).to_list(None)
    
    updated = 0
    for prod in productos:
        precio_compra = prod.get("precio_compra", 0)
        nuevo_precio_venta = round(precio_compra * (1 + margen / 100), 2)
        
        await db.repuestos.update_one(
            {"id": prod["id"]},
            {"$set": {"precio_venta": nuevo_precio_venta}}
        )
        updated += 1
    
    return {
        "message": f"Precios actualizados para {proveedor}",
        "productos_actualizados": updated,
        "margen_aplicado": margen
    }

# ==================== SCHEDULER DE SINCRONIZACIÓN AUTOMÁTICA ====================

@router.get("/scheduler/config")
async def get_scheduler_config_endpoint(user: dict = Depends(require_auth)):
    """Obtener configuración del scheduler de sincronización automática"""
    from utils.sync_scheduler import get_scheduler_config, scheduler_state
    
    config = await get_scheduler_config()
    return {
        "config": config,
        "state": scheduler_state
    }

@router.post("/scheduler/config")
async def save_scheduler_config_endpoint(request: dict, user: dict = Depends(require_master)):
    """Guardar configuración del scheduler"""
    from utils.sync_scheduler import save_scheduler_config, get_scheduler_config
    
    config = await get_scheduler_config()
    
    # Actualizar campos permitidos
    if "enabled" in request:
        config["enabled"] = request["enabled"]
    if "interval_days" in request:
        config["interval_days"] = max(1, min(30, request["interval_days"]))  # Entre 1 y 30 días
    if "sync_mobilesentrix" in request:
        config["sync_mobilesentrix"] = request["sync_mobilesentrix"]
    if "sync_utopya" in request:
        config["sync_utopya"] = request["sync_utopya"]
    if "preferred_hour" in request:
        config["preferred_hour"] = max(0, min(23, request["preferred_hour"]))
    
    await save_scheduler_config(config)
    
    return {"message": "Configuración guardada", "config": config}

@router.post("/scheduler/start")
async def start_scheduler_endpoint(user: dict = Depends(require_master)):
    """Iniciar el scheduler de sincronización automática"""
    from utils.sync_scheduler import start_scheduler, scheduler_state
    
    if scheduler_state["running"]:
        return {"message": "El scheduler ya está en ejecución", "running": True}
    
    start_scheduler()
    return {"message": "Scheduler iniciado", "running": True}

@router.post("/scheduler/stop")
async def stop_scheduler_endpoint(user: dict = Depends(require_master)):
    """Detener el scheduler"""
    from utils.sync_scheduler import stop_scheduler, scheduler_state
    
    stop_scheduler()
    return {"message": "Scheduler detenido", "running": False}

@router.post("/scheduler/run-now")
async def run_sync_now(background_tasks: BackgroundTasks, user: dict = Depends(require_master)):
    """Ejecutar sincronización automática manualmente ahora"""
    from utils.sync_scheduler import run_auto_sync
    
    background_tasks.add_task(run_auto_sync)
    return {"message": "Sincronización iniciada en segundo plano"}


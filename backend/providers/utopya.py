"""
Scraper para Utopya.es - Mayorista de repuestos móviles.
Portal: https://www.utopya.es
"""
import asyncio
import httpx
import logging
import re
from typing import Optional, List
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

from .base import ProveedorBase, ProductoProveedor

logger = logging.getLogger(__name__)


class UtopyaScraper(ProveedorBase):
    """Scraper para el portal de Utopya.es"""
    
    NOMBRE = "utopya"
    URL_BASE = "https://www.utopya.es"
    REQUIERE_LOGIN = True
    
    def __init__(self, username: str = None, password: str = None):
        super().__init__(username, password)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Obtener cliente HTTP."""
        if not self._session:
            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "es-ES,es;q=0.9",
                }
            )
        return self._session
    
    async def authenticate(self) -> bool:
        """Autenticarse en Utopya."""
        if not self.username or not self.password:
            logger.warning("Utopya: No hay credenciales configuradas")
            return False
        
        try:
            client = await self._get_client()
            
            # Buscar página de login
            login_urls = [
                f"{self.URL_BASE}/login",
                f"{self.URL_BASE}/customer/account/login",
                f"{self.URL_BASE}/mi-cuenta",
            ]
            
            for login_url in login_urls:
                try:
                    login_page = await client.get(login_url)
                    if login_page.status_code == 200 and ('login' in login_page.text.lower() or 'email' in login_page.text.lower()):
                        break
                except:
                    continue
            
            # Preparar datos de login
            login_data = {
                "login[username]": self.username,
                "login[password]": self.password,
                "send": "",
            }
            
            # Buscar form key (Magento)
            soup = BeautifulSoup(login_page.text, 'html.parser')
            form_key = soup.find('input', {'name': 'form_key'})
            if form_key:
                login_data['form_key'] = form_key.get('value', '')
            
            response = await client.post(
                f"{self.URL_BASE}/customer/account/loginPost",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # Verificar login
            if 'logout' in response.text.lower() or 'mi cuenta' in response.text.lower():
                self._authenticated = True
                logger.info("Utopya: Login exitoso")
                return True
            
            logger.warning("Utopya: Login fallido")
            return False
            
        except Exception as e:
            logger.error(f"Utopya authenticate error: {e}")
            return False
    
    async def buscar_producto(self, query: str, marca: str = None, categoria: str = None) -> List[ProductoProveedor]:
        """Buscar productos en Utopya."""
        productos = []
        
        try:
            client = await self._get_client()
            
            # URL de búsqueda (puede variar según CMS)
            search_url = f"{self.URL_BASE}/catalogsearch/result/?q={quote_plus(query)}"
            
            response = await client.get(search_url)
            
            if response.status_code != 200:
                logger.warning(f"Utopya búsqueda error: {response.status_code}")
                return productos
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar productos (estructura típica de Magento/PrestaShop)
            product_cards = soup.select('.product-item, .item.product, .product, [class*="product-item"]')
            
            for card in product_cards[:50]:
                try:
                    producto = self._parse_product_card(card)
                    if producto:
                        productos.append(producto)
                except Exception as e:
                    logger.debug(f"Error parseando producto: {e}")
                    continue
            
            self._last_search_results = productos
            logger.info(f"Utopya: {len(productos)} productos encontrados para '{query}'")
            
        except Exception as e:
            logger.error(f"Utopya buscar_producto error: {e}")
        
        return productos
    
    def _parse_product_card(self, card) -> Optional[ProductoProveedor]:
        """Parsear tarjeta de producto."""
        try:
            # Nombre
            nombre_elem = card.select_one('.product-item-name, .product-name, h2 a, h3 a, .name')
            nombre = nombre_elem.get_text(strip=True) if nombre_elem else None
            
            if not nombre:
                return None
            
            # Precio
            precio_elem = card.select_one('.price, .price-box .price, [data-price-amount]')
            if precio_elem and precio_elem.get('data-price-amount'):
                precio = float(precio_elem.get('data-price-amount', 0))
            else:
                precio_text = precio_elem.get_text(strip=True) if precio_elem else "0"
                precio = self._parse_precio(precio_text)
            
            # SKU
            sku = card.get('data-product-sku', '') or card.get('data-sku', '')
            if not sku:
                sku_elem = card.select_one('.sku .value, [class*="sku"]')
                sku = sku_elem.get_text(strip=True) if sku_elem else ""
            
            # URL
            link = card.select_one('a.product-item-link, a[href*="product"], a.product-name')
            if not link:
                link = card.select_one('a')
            url = link.get('href', '') if link else ""
            
            # Imagen
            img = card.select_one('img.product-image-photo, img')
            imagen = ""
            if img:
                imagen = img.get('src', '') or img.get('data-src', '')
            
            # Stock
            stock_elem = card.select_one('.stock, [class*="availability"]')
            stock_text = stock_elem.get_text(strip=True).lower() if stock_elem else ""
            disponible = 'agotado' not in stock_text and 'sin stock' not in stock_text
            
            marca = self._extraer_marca(nombre)
            
            return ProductoProveedor(
                sku_proveedor=sku or f"UTO-{hash(nombre) % 100000}",
                nombre=nombre,
                precio=precio,
                precio_sin_iva=round(precio / 1.21, 2),
                stock=10 if disponible else 0,
                disponible=disponible,
                marca=marca,
                imagen_url=imagen,
                url_producto=url,
                proveedor=self.NOMBRE
            )
            
        except Exception as e:
            logger.debug(f"Error en _parse_product_card: {e}")
            return None
    
    def _parse_precio(self, texto: str) -> float:
        """Extraer precio numérico."""
        try:
            limpio = re.sub(r'[^\d,.]', '', texto)
            limpio = limpio.replace(',', '.')
            if limpio.count('.') > 1:
                partes = limpio.rsplit('.', 1)
                limpio = partes[0].replace('.', '') + '.' + partes[1]
            return float(limpio) if limpio else 0.0
        except:
            return 0.0
    
    def _extraer_marca(self, nombre: str) -> str:
        """Extraer marca del nombre."""
        marcas = ['apple', 'samsung', 'xiaomi', 'huawei', 'oppo', 'realme', 
                  'iphone', 'ipad', 'galaxy', 'redmi', 'poco', 'pixel']
        nombre_lower = nombre.lower()
        for marca in marcas:
            if marca in nombre_lower:
                return marca.capitalize()
        return ""
    
    async def obtener_detalle(self, sku: str) -> Optional[ProductoProveedor]:
        """Obtener detalle de un producto."""
        for p in self._last_search_results:
            if p.sku_proveedor == sku:
                return p
        
        resultados = await self.buscar_producto(sku)
        for p in resultados:
            if p.sku_proveedor == sku:
                return p
        
        return None

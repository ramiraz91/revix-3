"""
Scraper para Mobilax.es - Distribuidor de repuestos móviles.
Portal: https://www.mobilax.es
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


class MobilaxScraper(ProveedorBase):
    """Scraper para el portal de Mobilax.es"""
    
    NOMBRE = "mobilax"
    URL_BASE = "https://www.mobilax.es"
    REQUIERE_LOGIN = True
    
    def __init__(self, username: str = None, password: str = None):
        super().__init__(username, password)
        self._cookies = {}
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Obtener cliente HTTP con configuración apropiada."""
        if not self._session:
            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                }
            )
        return self._session
    
    async def authenticate(self) -> bool:
        """Autenticarse en Mobilax."""
        if not self.username or not self.password:
            logger.warning("Mobilax: No hay credenciales configuradas")
            return False
        
        try:
            client = await self._get_client()
            
            # Obtener página de login para extraer token CSRF si existe
            login_page = await client.get(f"{self.URL_BASE}/login")
            
            # Intentar login
            login_data = {
                "email": self.username,
                "password": self.password,
                "_remember_me": "on"
            }
            
            # Buscar token CSRF en la página
            soup = BeautifulSoup(login_page.text, 'html.parser')
            csrf_input = soup.find('input', {'name': '_csrf_token'}) or soup.find('input', {'name': '_token'})
            if csrf_input:
                login_data['_csrf_token'] = csrf_input.get('value', '')
            
            response = await client.post(
                f"{self.URL_BASE}/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # Verificar si el login fue exitoso
            if response.status_code == 200 and ('logout' in response.text.lower() or 'mi cuenta' in response.text.lower()):
                self._authenticated = True
                self._cookies = dict(response.cookies)
                logger.info("Mobilax: Login exitoso")
                return True
            
            # Verificar redirección exitosa
            if response.status_code in [302, 301] or 'dashboard' in str(response.url):
                self._authenticated = True
                logger.info("Mobilax: Login exitoso (redirección)")
                return True
            
            logger.warning(f"Mobilax: Login fallido - status {response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"Mobilax authenticate error: {e}")
            return False
    
    async def buscar_producto(self, query: str, marca: str = None, categoria: str = None) -> List[ProductoProveedor]:
        """Buscar productos en Mobilax."""
        productos = []
        
        try:
            client = await self._get_client()
            
            # Construir URL de búsqueda
            search_url = f"{self.URL_BASE}/buscar?q={quote_plus(query)}"
            if marca:
                search_url += f"&marca={quote_plus(marca)}"
            
            response = await client.get(search_url)
            
            if response.status_code != 200:
                logger.warning(f"Mobilax búsqueda error: {response.status_code}")
                return productos
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar productos en la página (ajustar selectores según estructura real)
            product_cards = soup.select('.product-card, .product-item, .item-product, [class*="product"]')
            
            for card in product_cards[:50]:  # Limitar a 50 resultados
                try:
                    producto = self._parse_product_card(card)
                    if producto:
                        productos.append(producto)
                except Exception as e:
                    logger.debug(f"Error parseando producto: {e}")
                    continue
            
            self._last_search_results = productos
            logger.info(f"Mobilax: {len(productos)} productos encontrados para '{query}'")
            
        except Exception as e:
            logger.error(f"Mobilax buscar_producto error: {e}")
        
        return productos
    
    def _parse_product_card(self, card) -> Optional[ProductoProveedor]:
        """Parsear una tarjeta de producto."""
        try:
            # Intentar extraer nombre
            nombre_elem = card.select_one('.product-name, .product-title, h3, h4, [class*="name"], [class*="title"]')
            nombre = nombre_elem.get_text(strip=True) if nombre_elem else None
            
            if not nombre:
                return None
            
            # Extraer precio
            precio_elem = card.select_one('.price, .product-price, [class*="price"]')
            precio_text = precio_elem.get_text(strip=True) if precio_elem else "0"
            precio = self._parse_precio(precio_text)
            
            # Extraer SKU/referencia
            sku_elem = card.select_one('.sku, .reference, [class*="ref"], [class*="sku"]')
            sku = sku_elem.get_text(strip=True) if sku_elem else ""
            if not sku:
                # Intentar extraer de data attributes
                sku = card.get('data-sku', '') or card.get('data-ref', '')
            
            # Extraer URL del producto
            link = card.select_one('a[href*="/"]')
            url = urljoin(self.URL_BASE, link.get('href', '')) if link else ""
            
            # Extraer imagen
            img = card.select_one('img')
            imagen = img.get('src', '') or img.get('data-src', '') if img else ""
            if imagen and not imagen.startswith('http'):
                imagen = urljoin(self.URL_BASE, imagen)
            
            # Extraer stock/disponibilidad
            stock_elem = card.select_one('.stock, [class*="stock"], [class*="availability"]')
            stock_text = stock_elem.get_text(strip=True).lower() if stock_elem else ""
            disponible = 'agotado' not in stock_text and 'sin stock' not in stock_text
            stock = self._parse_stock(stock_text)
            
            # Extraer marca del nombre si es posible
            marca = self._extraer_marca(nombre)
            
            return ProductoProveedor(
                sku_proveedor=sku or f"MOB-{hash(nombre) % 100000}",
                nombre=nombre,
                precio=precio,
                precio_sin_iva=round(precio / 1.21, 2),
                stock=stock,
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
        """Extraer precio numérico de un texto."""
        try:
            # Eliminar símbolos de moneda y espacios
            limpio = re.sub(r'[^\d,.]', '', texto)
            # Normalizar separador decimal
            limpio = limpio.replace(',', '.')
            # Si hay múltiples puntos, el último es el decimal
            if limpio.count('.') > 1:
                partes = limpio.rsplit('.', 1)
                limpio = partes[0].replace('.', '') + '.' + partes[1]
            return float(limpio) if limpio else 0.0
        except:
            return 0.0
    
    def _parse_stock(self, texto: str) -> int:
        """Extraer cantidad de stock de un texto."""
        try:
            numeros = re.findall(r'\d+', texto)
            if numeros:
                return int(numeros[0])
            if 'disponible' in texto.lower() or 'stock' in texto.lower():
                return 10  # Stock genérico si dice disponible
            return 0
        except:
            return 0
    
    def _extraer_marca(self, nombre: str) -> str:
        """Intentar extraer marca del nombre del producto."""
        marcas_conocidas = [
            'apple', 'samsung', 'xiaomi', 'huawei', 'oppo', 'realme', 'vivo',
            'oneplus', 'google', 'motorola', 'lg', 'sony', 'nokia', 'honor',
            'iphone', 'ipad', 'galaxy', 'redmi', 'poco', 'pixel'
        ]
        nombre_lower = nombre.lower()
        for marca in marcas_conocidas:
            if marca in nombre_lower:
                return marca.capitalize()
        return ""
    
    async def obtener_detalle(self, sku: str) -> Optional[ProductoProveedor]:
        """Obtener detalle completo de un producto por SKU."""
        # Buscar en resultados cacheados primero
        for p in self._last_search_results:
            if p.sku_proveedor == sku:
                return p
        
        # Si no está en caché, buscar
        resultados = await self.buscar_producto(sku)
        for p in resultados:
            if p.sku_proveedor == sku:
                return p
        
        return None

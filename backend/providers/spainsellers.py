"""
Scraper para SpainSellers.com - Distribuidor de repuestos móviles B2B.
Portal: https://www.spainsellers.com
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


class SpainSellersScraper(ProveedorBase):
    """Scraper para el portal de SpainSellers.com"""
    
    NOMBRE = "spainsellers"
    URL_BASE = "https://www.spainsellers.com"
    REQUIERE_LOGIN = True
    
    def __init__(self, username: str = None, password: str = None):
        super().__init__(username, password)
        self._cookies = {}
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Obtener cliente HTTP."""
        if not self._session:
            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "es-ES,es;q=0.9",
                }
            )
        return self._session
    
    async def authenticate(self) -> bool:
        """Autenticarse en SpainSellers."""
        if not self.username or not self.password:
            logger.warning("SpainSellers: No hay credenciales configuradas")
            return False
        
        try:
            client = await self._get_client()
            
            # Obtener página de login
            login_page = await client.get(f"{self.URL_BASE}/mi-cuenta")
            
            # Preparar datos de login
            login_data = {
                "username": self.username,
                "password": self.password,
                "login": "Acceder",
                "rememberme": "forever"
            }
            
            # Buscar nonce de WooCommerce
            soup = BeautifulSoup(login_page.text, 'html.parser')
            nonce_input = soup.find('input', {'name': 'woocommerce-login-nonce'})
            if nonce_input:
                login_data['woocommerce-login-nonce'] = nonce_input.get('value', '')
            
            response = await client.post(
                f"{self.URL_BASE}/mi-cuenta",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # Verificar login exitoso
            if 'logout' in response.text.lower() or 'cerrar sesión' in response.text.lower():
                self._authenticated = True
                logger.info("SpainSellers: Login exitoso")
                return True
            
            # Verificar si hay error de login
            if 'error' in response.text.lower() and 'incorrect' in response.text.lower():
                logger.warning("SpainSellers: Credenciales incorrectas")
                return False
            
            # Asumir éxito si no hay error claro
            self._authenticated = True
            return True
            
        except Exception as e:
            logger.error(f"SpainSellers authenticate error: {e}")
            return False
    
    async def buscar_producto(self, query: str, marca: str = None, categoria: str = None) -> List[ProductoProveedor]:
        """Buscar productos en SpainSellers."""
        productos = []
        
        try:
            client = await self._get_client()
            
            # URL de búsqueda de WooCommerce
            search_url = f"{self.URL_BASE}/?s={quote_plus(query)}&post_type=product"
            
            response = await client.get(search_url)
            
            if response.status_code != 200:
                logger.warning(f"SpainSellers búsqueda error: {response.status_code}")
                return productos
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar productos (estructura típica de WooCommerce)
            product_cards = soup.select('.product, .type-product, li.product, .products .product')
            
            for card in product_cards[:50]:
                try:
                    producto = self._parse_product_card(card)
                    if producto:
                        productos.append(producto)
                except Exception as e:
                    logger.debug(f"Error parseando producto: {e}")
                    continue
            
            self._last_search_results = productos
            logger.info(f"SpainSellers: {len(productos)} productos encontrados para '{query}'")
            
        except Exception as e:
            logger.error(f"SpainSellers buscar_producto error: {e}")
        
        return productos
    
    def _parse_product_card(self, card) -> Optional[ProductoProveedor]:
        """Parsear una tarjeta de producto de WooCommerce."""
        try:
            # Nombre del producto
            nombre_elem = card.select_one('.woocommerce-loop-product__title, .product-title, h2, h3')
            nombre = nombre_elem.get_text(strip=True) if nombre_elem else None
            
            if not nombre:
                return None
            
            # Precio
            precio_elem = card.select_one('.price .amount, .price ins .amount, .woocommerce-Price-amount')
            if not precio_elem:
                precio_elem = card.select_one('.price')
            precio_text = precio_elem.get_text(strip=True) if precio_elem else "0"
            precio = self._parse_precio(precio_text)
            
            # SKU (puede estar como data attribute o clase)
            sku = card.get('data-product_sku', '') or card.get('data-sku', '')
            if not sku:
                sku_elem = card.select_one('.sku, [class*="sku"]')
                sku = sku_elem.get_text(strip=True) if sku_elem else ""
            
            # URL del producto
            link = card.select_one('a.woocommerce-LoopProduct-link, a[href*="producto"], a[href*="product"]')
            if not link:
                link = card.select_one('a')
            url = link.get('href', '') if link else ""
            
            # Imagen
            img = card.select_one('img')
            imagen = ""
            if img:
                imagen = img.get('src', '') or img.get('data-src', '') or img.get('data-lazy-src', '')
            
            # Stock
            stock_elem = card.select_one('.stock, [class*="stock"]')
            stock_text = stock_elem.get_text(strip=True).lower() if stock_elem else ""
            disponible = 'agotado' not in stock_text and 'out' not in stock_text
            
            # Tipo de pieza
            tipo = "compatible"
            nombre_lower = nombre.lower()
            if 'original' in nombre_lower or 'service pack' in nombre_lower:
                tipo = "original"
            elif 'premium' in nombre_lower or 'oled' in nombre_lower:
                tipo = "premium"
            
            # Marca
            marca = self._extraer_marca(nombre)
            
            return ProductoProveedor(
                sku_proveedor=sku or f"SS-{hash(nombre) % 100000}",
                nombre=nombre,
                precio=precio,
                precio_sin_iva=round(precio / 1.21, 2),
                stock=10 if disponible else 0,
                disponible=disponible,
                marca=marca,
                tipo=tipo,
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
        marcas = ['apple', 'samsung', 'xiaomi', 'huawei', 'oppo', 'realme', 'vivo',
                  'oneplus', 'google', 'motorola', 'lg', 'sony', 'nokia', 'honor',
                  'iphone', 'ipad', 'galaxy', 'redmi', 'poco', 'pixel', 'nothing']
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

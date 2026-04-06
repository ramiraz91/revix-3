"""
Gestor de proveedores - Unifica la búsqueda en todos los proveedores configurados.
"""
import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

from .base import ProveedorBase, ProductoProveedor
from .mobilax import MobilaxScraper
from .spainsellers import SpainSellersScraper
from .utopya import UtopyaScraper

logger = logging.getLogger(__name__)

# Registro de proveedores disponibles
PROVEEDORES_DISPONIBLES = {
    "mobilax": MobilaxScraper,
    "spainsellers": SpainSellersScraper,
    "utopya": UtopyaScraper,
}


class GestorProveedores:
    """
    Gestor centralizado para buscar productos en múltiples proveedores.
    """
    
    def __init__(self, db=None):
        self.db = db
        self._proveedores: Dict[str, ProveedorBase] = {}
        self._cache: Dict[str, List[ProductoProveedor]] = {}
        self._cache_timestamp: Dict[str, datetime] = {}
        self._cache_ttl_seconds = 3600  # 1 hora de caché
    
    async def cargar_credenciales(self):
        """Cargar credenciales de proveedores desde la base de datos."""
        if not self.db:
            logger.warning("GestorProveedores: No hay conexión a BD")
            return
        
        try:
            config = await self.db.configuracion.find_one(
                {"tipo": "proveedores"},
                {"_id": 0}
            )
            
            if not config:
                logger.info("No hay configuración de proveedores en BD")
                return
            
            proveedores_config = config.get("datos", {}).get("proveedores", [])
            
            for prov in proveedores_config:
                nombre = prov.get("nombre", "").lower()
                if nombre in PROVEEDORES_DISPONIBLES and prov.get("activo", False):
                    username = prov.get("username")
                    password = prov.get("password")
                    
                    scraper_class = PROVEEDORES_DISPONIBLES[nombre]
                    self._proveedores[nombre] = scraper_class(username, password)
                    logger.info(f"Proveedor cargado: {nombre}")
            
        except Exception as e:
            logger.error(f"Error cargando credenciales de proveedores: {e}")
    
    def agregar_proveedor(self, nombre: str, username: str = None, password: str = None):
        """Agregar un proveedor manualmente."""
        nombre = nombre.lower()
        if nombre not in PROVEEDORES_DISPONIBLES:
            raise ValueError(f"Proveedor '{nombre}' no soportado. Disponibles: {list(PROVEEDORES_DISPONIBLES.keys())}")
        
        scraper_class = PROVEEDORES_DISPONIBLES[nombre]
        self._proveedores[nombre] = scraper_class(username, password)
        logger.info(f"Proveedor agregado: {nombre}")
    
    async def buscar_en_todos(
        self, 
        query: str, 
        marca: str = None,
        proveedores: List[str] = None,
        ordenar_por: str = "precio",
        solo_disponibles: bool = True
    ) -> List[ProductoProveedor]:
        """
        Buscar productos en todos los proveedores configurados.
        
        Args:
            query: Término de búsqueda
            marca: Filtrar por marca
            proveedores: Lista de proveedores específicos (None = todos)
            ordenar_por: "precio", "nombre", "proveedor"
            solo_disponibles: Filtrar solo productos con stock
            
        Returns:
            Lista de productos de todos los proveedores
        """
        todos_productos = []
        
        # Determinar qué proveedores usar
        provs_a_usar = proveedores or list(self._proveedores.keys())
        
        # Verificar caché
        cache_key = f"{query}:{marca}:{','.join(sorted(provs_a_usar))}"
        if cache_key in self._cache:
            cache_time = self._cache_timestamp.get(cache_key)
            if cache_time and (datetime.now(timezone.utc) - cache_time).total_seconds() < self._cache_ttl_seconds:
                logger.info(f"Usando caché para búsqueda: {query}")
                productos = self._cache[cache_key]
                if solo_disponibles:
                    productos = [p for p in productos if p.disponible]
                return self._ordenar_productos(productos, ordenar_por)
        
        # Buscar en paralelo en todos los proveedores
        async def buscar_en_proveedor(nombre: str, scraper: ProveedorBase):
            try:
                # Autenticar si es necesario
                if scraper.REQUIERE_LOGIN and not scraper._authenticated:
                    await scraper.authenticate()
                
                resultados = await scraper.buscar_producto(query, marca=marca)
                return resultados
            except Exception as e:
                logger.error(f"Error buscando en {nombre}: {e}")
                return []
        
        tasks = []
        for nombre, scraper in self._proveedores.items():
            if nombre in provs_a_usar:
                tasks.append(buscar_en_proveedor(nombre, scraper))
        
        if tasks:
            resultados = await asyncio.gather(*tasks)
            for productos in resultados:
                todos_productos.extend(productos)
        
        # Guardar en caché
        self._cache[cache_key] = todos_productos
        self._cache_timestamp[cache_key] = datetime.now(timezone.utc)
        
        # Filtrar y ordenar
        if solo_disponibles:
            todos_productos = [p for p in todos_productos if p.disponible]
        
        return self._ordenar_productos(todos_productos, ordenar_por)
    
    def _ordenar_productos(self, productos: List[ProductoProveedor], criterio: str) -> List[ProductoProveedor]:
        """Ordenar lista de productos."""
        if criterio == "precio":
            return sorted(productos, key=lambda p: p.precio)
        elif criterio == "nombre":
            return sorted(productos, key=lambda p: p.nombre.lower())
        elif criterio == "proveedor":
            return sorted(productos, key=lambda p: (p.proveedor, p.precio))
        return productos
    
    async def buscar_repuesto_compatible(
        self,
        marca: str,
        modelo: str,
        tipo_repuesto: str = None
    ) -> List[ProductoProveedor]:
        """
        Buscar repuestos compatibles con un dispositivo específico.
        
        Args:
            marca: Marca del dispositivo (Apple, Samsung, etc.)
            modelo: Modelo del dispositivo (iPhone 14 Pro, Galaxy S24, etc.)
            tipo_repuesto: Tipo de repuesto (pantalla, batería, etc.)
        """
        query_parts = [marca, modelo]
        if tipo_repuesto:
            query_parts.append(tipo_repuesto)
        
        query = " ".join(query_parts)
        return await self.buscar_en_todos(query, marca=marca)
    
    async def comparar_precios(self, sku_o_nombre: str) -> Dict[str, Any]:
        """
        Comparar precios de un producto entre proveedores.
        
        Returns:
            {
                "productos": [...],
                "mejor_precio": ProductoProveedor,
                "precio_medio": float,
                "ahorro_maximo": float
            }
        """
        productos = await self.buscar_en_todos(sku_o_nombre, solo_disponibles=True)
        
        if not productos:
            return {"productos": [], "mejor_precio": None, "precio_medio": 0, "ahorro_maximo": 0}
        
        precios = [p.precio for p in productos if p.precio > 0]
        mejor = min(productos, key=lambda p: p.precio) if productos else None
        precio_medio = sum(precios) / len(precios) if precios else 0
        precio_max = max(precios) if precios else 0
        
        return {
            "productos": [p.to_dict() for p in productos],
            "mejor_precio": mejor.to_dict() if mejor else None,
            "precio_medio": round(precio_medio, 2),
            "ahorro_maximo": round(precio_max - mejor.precio, 2) if mejor else 0
        }
    
    def listar_proveedores(self) -> List[Dict[str, Any]]:
        """Listar proveedores configurados."""
        return [
            {
                "nombre": nombre,
                "autenticado": scraper._authenticated,
                "requiere_login": scraper.REQUIERE_LOGIN,
                "url_base": scraper.URL_BASE
            }
            for nombre, scraper in self._proveedores.items()
        ]
    
    async def cerrar_todo(self):
        """Cerrar todas las sesiones de proveedores."""
        for nombre, scraper in self._proveedores.items():
            try:
                await scraper.close()
            except Exception as e:
                logger.error(f"Error cerrando {nombre}: {e}")


# Instancia global (se inicializa con la BD en server.py)
gestor_proveedores: Optional[GestorProveedores] = None


async def get_gestor_proveedores(db=None) -> GestorProveedores:
    """Obtener instancia del gestor de proveedores."""
    global gestor_proveedores
    if gestor_proveedores is None:
        gestor_proveedores = GestorProveedores(db)
        await gestor_proveedores.cargar_credenciales()
    return gestor_proveedores

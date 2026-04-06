"""
Base classes for provider integrations.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class ProductoProveedor:
    """Producto obtenido de un proveedor."""
    sku_proveedor: str
    nombre: str
    precio: float
    precio_sin_iva: float = 0.0
    stock: int = 0
    disponible: bool = True
    marca: str = ""
    modelo_compatible: str = ""
    categoria: str = ""
    tipo: str = ""  # original, compatible, premium
    imagen_url: str = ""
    url_producto: str = ""
    proveedor: str = ""
    ultima_actualizacion: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    datos_extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)


class ProveedorBase(ABC):
    """Clase base para scrapers de proveedores."""
    
    NOMBRE: str = "base"
    URL_BASE: str = ""
    REQUIERE_LOGIN: bool = True
    
    def __init__(self, username: str = None, password: str = None):
        self.username = username
        self.password = password
        self._session = None
        self._authenticated = False
        self._last_search_results: List[ProductoProveedor] = []
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Autenticarse en el portal del proveedor."""
        pass
    
    @abstractmethod
    async def buscar_producto(self, query: str, marca: str = None, categoria: str = None) -> List[ProductoProveedor]:
        """Buscar productos por término de búsqueda."""
        pass
    
    @abstractmethod
    async def obtener_detalle(self, sku: str) -> Optional[ProductoProveedor]:
        """Obtener detalle completo de un producto."""
        pass
    
    async def buscar_por_modelo(self, marca: str, modelo: str) -> List[ProductoProveedor]:
        """Buscar repuestos compatibles con un modelo específico."""
        query = f"{marca} {modelo}".strip()
        return await self.buscar_producto(query, marca=marca)
    
    async def close(self):
        """Cerrar sesión y liberar recursos."""
        if self._session:
            await self._session.aclose()
            self._session = None
        self._authenticated = False
    
    def __repr__(self):
        return f"<{self.__class__.__name__} authenticated={self._authenticated}>"

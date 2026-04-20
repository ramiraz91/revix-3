"""
Paquete de tools MCP.

Importar este módulo registra automáticamente todas las tools en el registry.
Así cualquier consumidor (server, tests, smoke_test) ve el catálogo completo
haciendo un único `from revix_mcp import tools`.
"""
# Nota: orden fijo para trazabilidad de registros
from . import meta        # noqa: F401
from . import orders      # noqa: F401
from . import clients     # noqa: F401
from . import inventory   # noqa: F401
from . import metrics     # noqa: F401
from . import tracking    # noqa: F401

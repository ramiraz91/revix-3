import { useState, useEffect, useCallback } from 'react';
import { Plus, Search, MoreVertical, Edit, Trash2, Package, AlertTriangle, Filter, Printer, Check, ChevronLeft, ChevronRight, ArrowLeftRight, Tag, Image, Grid, List, ExternalLink, Layers, GitBranch } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { repuestosAPI, proveedoresAPI } from '@/lib/api';
import { toast } from 'sonner';
import CalidadPantallaBadge, { CalidadPantallaSelector } from '@/components/CalidadPantallaBadge';
import KitsManager from '@/components/KitsManager';
import ProductoVariantes from '@/components/ProductoVariantes';

const PAGE_SIZE = 50;

const emptyRepuesto = {
  nombre: '',
  categoria: '',
  sku: '',  // Se genera automáticamente
  modelo_compatible: '',
  codigo_barras: '',
  precio_compra: 0,
  precio_venta: 0,
  stock: 0,
  stock_minimo: 5,
  ubicacion: '',
  proveedor_id: '',
  iva_compra: 21,  // Por defecto 21%
  inversion_sujeto_pasivo: false,  // True si exento de IVA en compra
  iva_venta: 21
};

const categorias = [
  'Pantallas',
  'Baterías',
  'Conectores',
  'Cámaras',
  'Altavoces',
  'Flex',
  'Carcasas',
  'Cristales',
  'Otros'
];

export default function Inventario() {
  const [repuestos, setRepuestos] = useState([]);
  const [proveedores, setProveedores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [categoriaFilter, setCategoriaFilter] = useState('all');
  const [proveedorFilter, setProveedorFilter] = useState('all');
  const [lowStockFilter, setLowStockFilter] = useState(false);
  const [showDialog, setShowDialog] = useState(false);
  const [editingRepuesto, setEditingRepuesto] = useState(null);
  const [formData, setFormData] = useState(emptyRepuesto);
  const [selectedIds, setSelectedIds] = useState([]);
  const [labelQty, setLabelQty] = useState(1);
  
  // Vista tipo tienda (grid con imágenes) vs tabla
  const [viewMode, setViewMode] = useState('table');  // 'table' | 'grid'
  
  // Tab activa: repuestos o kits
  const [activeTab, setActiveTab] = useState('repuestos');
  
  // Paginación
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  
  // Modal de alternativas para comparar precios
  const [showAlternativasDialog, setShowAlternativasDialog] = useState(false);
  const [alternativasData, setAlternativasData] = useState(null);
  const [loadingAlternativas, setLoadingAlternativas] = useState(false);
  
  // Modal de edición de calidad de pantalla
  const [editingCalidad, setEditingCalidad] = useState(null);
  const [nuevaCalidad, setNuevaCalidad] = useState('');
  
  // Modal de variantes
  const [showVariantes, setShowVariantes] = useState(false);
  const [variantesProductoId, setVariantesProductoId] = useState(null);
  const [variantesProductoNombre, setVariantesProductoNombre] = useState('');

  // Búsqueda en tiempo real con debounce
  useEffect(() => {
    if (!search || search.length < 2) {
      setSearchResults([]);
      return;
    }
    
    const timer = setTimeout(async () => {
      try {
        setSearching(true);
        const params = new URLSearchParams({ q: search, limit: '50' });
        if (proveedorFilter && proveedorFilter !== 'all') {
          params.append('proveedor', proveedorFilter);
        }
        
        const response = await fetch(
          `${process.env.REACT_APP_BACKEND_URL}/api/repuestos/buscar/rapido?${params}`,
          { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
        );
        const data = await response.json();
        setSearchResults(data);
      } catch (error) {
        console.error('Error en búsqueda:', error);
      } finally {
        setSearching(false);
      }
    }, 200);
    
    return () => clearTimeout(timer);
  }, [search, proveedorFilter]);

  const fetchData = useCallback(async (page = 1) => {
    try {
      setLoading(true);
      const params = { page, page_size: PAGE_SIZE };
      if (categoriaFilter && categoriaFilter !== 'all') params.categoria = categoriaFilter;
      if (proveedorFilter && proveedorFilter !== 'all') params.proveedor = proveedorFilter;
      if (lowStockFilter) params.low_stock = true;
      
      const [repuestosRes, proveedoresRes] = await Promise.all([
        repuestosAPI.listar(params),
        proveedoresAPI.listar()
      ]);
      
      // La respuesta ahora tiene formato { items, total, page, total_pages }
      const data = repuestosRes.data;
      setRepuestos(data.items || []);
      setTotalItems(data.total || 0);
      setTotalPages(data.total_pages || 1);
      setCurrentPage(data.page || 1);
      setProveedores(proveedoresRes.data);
    } catch (error) {
      toast.error('Error al cargar inventario');
    } finally {
      setLoading(false);
    }
  }, [categoriaFilter, proveedorFilter, lowStockFilter]);

  useEffect(() => {
    fetchData(1); // Reset to page 1 when filters change
  }, [fetchData]);

  // Cambiar página
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      fetchData(newPage);
      setSelectedIds([]);
    }
  };

  // Los resultados a mostrar: si hay búsqueda, mostrar searchResults, sino repuestos
  const displayedProducts = search.length >= 2 ? searchResults : repuestos;

  const handleSearch = (e) => {
    e.preventDefault();
    // Ya no necesita hacer nada, la búsqueda es automática
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => {
      const newData = { ...prev, [field]: value };
      
      // Auto-generar SKU cuando cambia el nombre o categoría
      if (field === 'nombre' || field === 'categoria') {
        const nombre = field === 'nombre' ? value : prev.nombre;
        const categoria = field === 'categoria' ? value : prev.categoria;
        newData.sku = generateSKU(nombre, categoria);
      }
      
      return newData;
    });
  };

  // Genera SKU automático basado en nombre y categoría
  const generateSKU = (nombre, categoria) => {
    if (!nombre) return '';
    
    // Prefijo de categoría
    const prefijos = {
      'Pantallas': 'PANT',
      'Baterías': 'BAT',
      'Conectores': 'CON',
      'Cámaras': 'CAM',
      'Altavoces': 'ALT',
      'Flex': 'FLX',
      'Carcasas': 'CAR',
      'Cristales': 'CRI',
      'Otros': 'OTR'
    };
    const prefijo = prefijos[categoria] || 'REP';
    
    // Extraer palabras clave del nombre (máx 3 palabras significativas)
    const palabras = nombre
      .toUpperCase()
      .replace(/[^A-Z0-9\s]/g, '')
      .split(/\s+/)
      .filter(p => p.length > 2 && !['PARA', 'CON', 'DEL', 'LOS', 'LAS', 'THE'].includes(p))
      .slice(0, 3)
      .map(p => p.slice(0, 4))
      .join('-');
    
    // Generar número único basado en timestamp
    const numUnico = Date.now().toString(36).slice(-4).toUpperCase();
    
    return `${prefijo}-${palabras || 'X'}-${numUnico}`;
  };

  const handleOpenDialog = (repuesto = null) => {
    if (repuesto) {
      setEditingRepuesto(repuesto);
      setFormData(repuesto);
    } else {
      setEditingRepuesto(null);
      setFormData(emptyRepuesto);
    }
    setShowDialog(true);
  };

  const handleSubmit = async () => {
    try {
      const dataToSend = {
        ...formData,
        precio_compra: parseFloat(formData.precio_compra) || 0,
        precio_venta: parseFloat(formData.precio_venta) || 0,
        stock: parseInt(formData.stock) || 0,
        stock_minimo: parseInt(formData.stock_minimo) || 5
      };
      
      if (editingRepuesto) {
        await repuestosAPI.actualizar(editingRepuesto.id, dataToSend);
        toast.success('Repuesto actualizado');
      } else {
        await repuestosAPI.crear(dataToSend);
        toast.success('Repuesto creado');
      }
      setShowDialog(false);
      fetchData(currentPage);
    } catch (error) {
      toast.error('Error al guardar repuesto');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Estás seguro de eliminar este repuesto?')) return;
    try {
      await repuestosAPI.eliminar(id);
      toast.success('Repuesto eliminado');
      fetchData(currentPage);
    } catch (error) {
      toast.error('Error al eliminar repuesto');
    }
  };

  const getProveedorNombre = (id) => {
    const proveedor = proveedores.find(p => p.id === id);
    return proveedor ? proveedor.nombre : '-';
  };

  const toggleSelectProduct = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === displayedProducts.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(displayedProducts.map(r => r.id));
    }
  };

  // Comparar precios - obtener alternativas de otros proveedores
  const handleCompararPrecios = async (repuesto) => {
    try {
      setLoadingAlternativas(true);
      setShowAlternativasDialog(true);
      const res = await repuestosAPI.alternativas(repuesto.id, 15);
      setAlternativasData(res.data);
    } catch (error) {
      toast.error('Error al buscar alternativas');
      setShowAlternativasDialog(false);
    } finally {
      setLoadingAlternativas(false);
    }
  };

  // Actualizar calidad de pantalla manualmente
  const handleActualizarCalidad = async () => {
    if (!editingCalidad || !nuevaCalidad) return;
    
    try {
      await repuestosAPI.actualizarCalidadPantalla(editingCalidad.id, nuevaCalidad);
      toast.success('Calidad actualizada correctamente');
      setEditingCalidad(null);
      setNuevaCalidad('');
      fetchData(currentPage);
    } catch (error) {
      toast.error('Error al actualizar calidad');
    }
  };

  // Imprimir etiquetas directamente (Brother QL-800)
  const handlePrintLabels = () => {
    if (selectedIds.length === 0) {
      toast.error('Selecciona al menos un producto');
      return;
    }
    
    // Obtener datos de los productos seleccionados
    const productosSeleccionados = displayedProducts.filter(r => selectedIds.includes(r.id));
    printLabels(productosSeleccionados, labelQty);
    setSelectedIds([]);
  };

  // Imprimir etiqueta de un solo producto
  const handlePrintSingleLabel = (repuesto) => {
    printLabels([repuesto], 1);
  };

  // Función común para imprimir etiquetas - Brother QL-800 (29mm x 90mm - DK-11201)
  const printLabels = (productos, cantidadPorProducto) => {
    const printWindow = window.open('', '_blank', 'width=600,height=800');
    if (!printWindow) {
      toast.error('Permite ventanas emergentes para imprimir');
      return;
    }

    const etiquetas = [];
    productos.forEach(producto => {
      const codigo = producto.sku || producto.id || 'SIN-SKU';
      const precio = producto.precio_venta ? `${producto.precio_venta.toFixed(2)}€` : '';
      for (let i = 0; i < cantidadPorProducto; i++) {
        etiquetas.push(`
          <div class="etiqueta">
            <div class="info-left">
              <div class="nombre">${(producto.nombre || '').substring(0, 50)}</div>
              ${precio ? `<div class="precio">${precio}</div>` : ''}
            </div>
            <div class="barcode-section">
              <svg class="barcode" id="barcode-${i}">
                ${generateBarcodeSVG(codigo)}
              </svg>
              <div class="codigo">${codigo}</div>
            </div>
          </div>
        `);
      }
    });

    // Función para generar código de barras Code128-like simplificado
    function generateBarcodeSVG(text) {
      let bars = '';
      const barWidth = 1.5;
      let x = 0;
      
      // Start pattern
      bars += \`<rect x="\${x}" y="0" width="2" height="100%" fill="black"/>\`;
      x += 4;
      
      for (let i = 0; i < text.length; i++) {
        const charCode = text.charCodeAt(i);
        // Generar patrón basado en el código ASCII
        const pattern = [
          (charCode & 1) ? 2 : 1,
          (charCode & 2) ? 1 : 2,
          (charCode & 4) ? 2 : 1,
          (charCode & 8) ? 1 : 2,
        ];
        
        pattern.forEach((w, j) => {
          if (j % 2 === 0) {
            bars += \`<rect x="\${x}" y="0" width="\${w * barWidth}" height="100%" fill="black"/>\`;
          }
          x += w * barWidth + 1;
        });
        x += 2; // espacio entre caracteres
      }
      
      // End pattern
      bars += \`<rect x="\${x}" y="0" width="2" height="100%" fill="black"/>\`;
      
      return bars;
    }

    printWindow.document.write(\`
      <!DOCTYPE html>
      <html>
      <head>
        <title>Etiquetas Brother QL-800</title>
        <style>
          /* Reset y configuración base */
          * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
          }
          
          /* Configuración de página para impresión */
          @page {
            size: 90mm 29mm;
            margin: 0;
          }
          
          @media print {
            html, body {
              width: 90mm;
              margin: 0;
              padding: 0;
            }
            .no-print {
              display: none !important;
            }
            .etiqueta {
              border: none !important;
              page-break-after: always;
              page-break-inside: avoid;
            }
          }
          
          body {
            font-family: Arial, Helvetica, sans-serif;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }
          
          /* Panel de control (no se imprime) */
          .no-print {
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
            margin-bottom: 20px;
          }
          .no-print h2 {
            margin-bottom: 10px;
          }
          .no-print p {
            margin-bottom: 5px;
            opacity: 0.9;
          }
          .no-print .info-box {
            background: rgba(255,255,255,0.2);
            padding: 10px;
            border-radius: 8px;
            margin: 15px 0;
          }
          .btn-print {
            padding: 15px 40px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            background: white;
            color: #764ba2;
            border: none;
            border-radius: 8px;
            margin-top: 15px;
            transition: transform 0.2s;
          }
          .btn-print:hover {
            transform: scale(1.05);
          }
          
          /* Contenedor de etiquetas para preview */
          .etiquetas-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
            padding: 20px;
          }
          
          @media print {
            .etiquetas-container {
              padding: 0;
              gap: 0;
            }
          }
          
          /* Etiqueta individual - 90mm x 29mm */
          .etiqueta {
            width: 340px; /* ~90mm en pantalla */
            height: 110px; /* ~29mm en pantalla */
            padding: 8px 12px;
            display: flex;
            flex-direction: row;
            align-items: center;
            justify-content: space-between;
            border: 2px solid #333;
            border-radius: 4px;
            background: white;
            gap: 10px;
          }
          
          @media print {
            .etiqueta {
              width: 90mm;
              height: 29mm;
              padding: 2mm 3mm;
              border-radius: 0;
            }
          }
          
          /* Información del producto (izquierda) */
          .info-left {
            flex: 0 0 35%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            overflow: hidden;
          }
          
          .nombre {
            font-size: 9px;
            font-weight: bold;
            line-height: 1.2;
            max-height: 45px;
            overflow: hidden;
            word-break: break-word;
          }
          
          @media print {
            .nombre {
              font-size: 7pt;
              max-height: 18mm;
            }
          }
          
          .precio {
            font-size: 14px;
            font-weight: bold;
            color: #000;
            margin-top: 4px;
          }
          
          @media print {
            .precio {
              font-size: 10pt;
              margin-top: 1mm;
            }
          }
          
          /* Sección código de barras (derecha) */
          .barcode-section {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
          }
          
          .barcode {
            width: 100%;
            height: 50px;
            max-width: 180px;
          }
          
          @media print {
            .barcode {
              height: 15mm;
              max-width: 50mm;
            }
          }
          
          .codigo {
            font-size: 10px;
            font-weight: bold;
            font-family: 'Courier New', Courier, monospace;
            letter-spacing: 1px;
            margin-top: 2px;
            text-align: center;
          }
          
          @media print {
            .codigo {
              font-size: 7pt;
              margin-top: 0.5mm;
            }
          }
          
          /* Instrucciones */
          .instrucciones {
            padding: 20px;
            background: #f8f9fa;
            border-top: 1px solid #ddd;
            font-size: 13px;
            color: #666;
          }
          .instrucciones h4 {
            color: #333;
            margin-bottom: 10px;
          }
          .instrucciones ol {
            margin-left: 20px;
          }
          .instrucciones li {
            margin-bottom: 5px;
          }
        </style>
      </head>
      <body>
        <div class="no-print">
          <h2>🏷️ Brother QL-800</h2>
          <p>Etiquetas 29mm × 90mm (DK-11201)</p>
          <div class="info-box">
            <strong>Total: \${etiquetas.length} etiqueta(s)</strong>
          </div>
          <button class="btn-print" onclick="window.print()">
            🖨️ IMPRIMIR ETIQUETAS
          </button>
        </div>
        
        <div class="etiquetas-container">
          \${etiquetas.join('')}
        </div>
        
        <div class="no-print instrucciones">
          <h4>📋 Instrucciones de impresión:</h4>
          <ol>
            <li>Selecciona la impresora <strong>Brother QL-800</strong></li>
            <li>En "Más opciones" o "Configuración":</li>
            <li>Tamaño de papel: <strong>29mm x 90mm</strong> o <strong>DK-11201</strong></li>
            <li>Márgenes: <strong>Ninguno</strong> o <strong>Mínimos</strong></li>
            <li>Escala: <strong>100%</strong> (sin ajustar)</li>
          </ol>
        </div>
      </body>
      </html>
    \`);
    
    printWindow.document.close();
    toast.success(\`Preparando \${etiquetas.length} etiqueta(s) para Brother QL-800\`);
  };
            .no-print {
              display: none;
            }
          }
        </style>
      </head>
      <body>
        <div class="no-print">
          <h3>Etiquetas de Inventario</h3>
          <p>Tamaño: 29mm x 90mm</p>
          <p><strong>Total: ${etiquetas.length} etiqueta(s)</strong></p>
          <button onclick="window.print()">Imprimir Ahora</button>
        </div>
        ${etiquetas.join('')}
        <script>
          window.onload = function() {
            setTimeout(function() {
              window.print();
            }, 500);
          };
        </script>
      </body>
      </html>
    `);
    
    printWindow.document.close();
    toast.success(`Preparando ${etiquetas.length} etiqueta(s) para imprimir`);
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="inventario-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Inventario</h1>
          <p className="text-muted-foreground mt-1">Gestiona tus repuestos, stock y kits</p>
        </div>
      </div>

      {/* Tabs: Repuestos / Kits */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="repuestos" className="flex items-center gap-2">
            <Package className="w-4 h-4" />
            Repuestos
          </TabsTrigger>
          <TabsTrigger value="kits" className="flex items-center gap-2">
            <Layers className="w-4 h-4" />
            Kits
          </TabsTrigger>
        </TabsList>

        {/* Tab Repuestos */}
        <TabsContent value="repuestos" className="mt-6 space-y-6">
          {/* Toolbar de repuestos */}
          <div className="flex justify-end">
            <Dialog open={showDialog} onOpenChange={setShowDialog}>
              <DialogTrigger asChild>
                <Button onClick={() => handleOpenDialog()} data-testid="new-repuesto-btn">
                  <Plus className="w-4 h-4 mr-2" />
                  Nuevo Repuesto
                </Button>
              </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{editingRepuesto ? 'Editar Repuesto' : 'Nuevo Repuesto'}</DialogTitle>
            </DialogHeader>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label>Nombre *</Label>
                <Input 
                  value={formData.nombre}
                  onChange={(e) => handleInputChange('nombre', e.target.value)}
                  placeholder="Pantalla iPhone 15 Pro"
                  data-testid="input-nombre"
                />
              </div>
              <div>
                <Label>SKU (generado automáticamente)</Label>
                <Input 
                  value={formData.sku}
                  readOnly
                  className="bg-slate-50 font-mono"
                  placeholder="Se genera al escribir nombre..."
                  data-testid="input-sku"
                />
                <p className="text-xs text-muted-foreground mt-1">Código único para identificación y etiquetas</p>
              </div>
              <div>
                <Label>Código de Barras</Label>
                <Input 
                  value={formData.codigo_barras}
                  onChange={(e) => handleInputChange('codigo_barras', e.target.value)}
                  placeholder="107083546478"
                  data-testid="input-codigo-barras"
                />
                <p className="text-xs text-muted-foreground mt-1">EAN/UPC para escaneo (se genera auto si vacío)</p>
              </div>
              <div>
                <Label>Categoría *</Label>
                <Select value={formData.categoria} onValueChange={(v) => handleInputChange('categoria', v)}>
                  <SelectTrigger data-testid="select-categoria">
                    <SelectValue placeholder="Selecciona categoría" />
                  </SelectTrigger>
                  <SelectContent>
                    {categorias.map(cat => (
                      <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Modelo Compatible</Label>
                <Input 
                  value={formData.modelo_compatible}
                  onChange={(e) => handleInputChange('modelo_compatible', e.target.value)}
                  placeholder="iPhone 15 Pro, 15 Pro Max"
                />
              </div>
              <div>
                <Label>Precio Compra (€)</Label>
                <Input 
                  type="number"
                  step="0.01"
                  value={formData.precio_compra}
                  onChange={(e) => handleInputChange('precio_compra', e.target.value)}
                  data-testid="input-precio-compra"
                />
              </div>
              <div>
                <Label>Precio Venta (€)</Label>
                <Input 
                  type="number"
                  step="0.01"
                  value={formData.precio_venta}
                  onChange={(e) => handleInputChange('precio_venta', e.target.value)}
                  data-testid="input-precio-venta"
                />
              </div>
              <div>
                <Label>Stock Actual</Label>
                <Input 
                  type="number"
                  value={formData.stock}
                  onChange={(e) => handleInputChange('stock', e.target.value)}
                  data-testid="input-stock"
                />
              </div>
              <div>
                <Label>Stock Mínimo</Label>
                <Input 
                  type="number"
                  value={formData.stock_minimo}
                  onChange={(e) => handleInputChange('stock_minimo', e.target.value)}
                />
              </div>
              <div>
                <Label>Ubicación</Label>
                <Input 
                  value={formData.ubicacion}
                  onChange={(e) => handleInputChange('ubicacion', e.target.value)}
                  placeholder="Estante A-3"
                />
              </div>
              <div>
                <Label>Proveedor</Label>
                <Select value={formData.proveedor_id} onValueChange={(v) => handleInputChange('proveedor_id', v)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecciona proveedor" />
                  </SelectTrigger>
                  <SelectContent>
                    {proveedores.map(prov => (
                      <SelectItem key={prov.id} value={prov.id}>{prov.nombre}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            {/* Sección IVA */}
            <div className="border-t pt-4 mt-4">
              <h4 className="font-medium mb-3">Configuración de IVA</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>IVA Compra (%)</Label>
                  <Select 
                    value={formData.inversion_sujeto_pasivo ? 'exento' : String(formData.iva_compra || 21)} 
                    onValueChange={(v) => {
                      if (v === 'exento') {
                        handleInputChange('inversion_sujeto_pasivo', true);
                        handleInputChange('iva_compra', 0);
                      } else {
                        handleInputChange('inversion_sujeto_pasivo', false);
                        handleInputChange('iva_compra', parseFloat(v));
                      }
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="21">21% - General</SelectItem>
                      <SelectItem value="10">10% - Reducido</SelectItem>
                      <SelectItem value="4">4% - Superreducido</SelectItem>
                      <SelectItem value="exento">0% - Exento (ISP)</SelectItem>
                    </SelectContent>
                  </Select>
                  {formData.inversion_sujeto_pasivo && (
                    <p className="text-xs text-yellow-600 mt-1">
                      Inversión del Sujeto Pasivo - Sin IVA en compra
                    </p>
                  )}
                </div>
                <div>
                  <Label>IVA Venta (%)</Label>
                  <Select 
                    value={String(formData.iva_venta || 21)} 
                    onValueChange={(v) => handleInputChange('iva_venta', parseFloat(v))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="21">21% - General</SelectItem>
                      <SelectItem value="10">10% - Reducido</SelectItem>
                      <SelectItem value="4">4% - Superreducido</SelectItem>
                      <SelectItem value="0">0% - Exento</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
            
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="outline" onClick={() => setShowDialog(false)}>
                Cancelar
              </Button>
              <Button onClick={handleSubmit} data-testid="save-repuesto-btn">
                {editingRepuesto ? 'Guardar Cambios' : 'Crear Repuesto'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
          </div>

      {/* Label print bar */}
      {selectedIds.length > 0 && (
        <Card className="border-blue-200 bg-blue-50/50" data-testid="label-bar">
          <CardContent className="p-3 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <Badge variant="secondary">{selectedIds.length} seleccionados</Badge>
              <div className="flex items-center gap-2">
                <Label className="text-sm whitespace-nowrap">Copias:</Label>
                <Input 
                  type="number" min={1} max={50} value={labelQty}
                  onChange={e => setLabelQty(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-16 h-8"
                  data-testid="label-qty-input"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={() => setSelectedIds([])}>Cancelar</Button>
              <Button size="sm" onClick={handlePrintLabels} data-testid="print-labels-btn">
                <Printer className="w-4 h-4 mr-1" />
                Imprimir Etiquetas
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Escribe para buscar (mín. 2 caracteres)..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
                data-testid="search-input"
              />
              {searching && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
              )}
            </div>
            <Select value={proveedorFilter} onValueChange={setProveedorFilter}>
              <SelectTrigger className="w-full sm:w-44">
                <SelectValue placeholder="Proveedor" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos proveedores</SelectItem>
                <SelectItem value="MobileSentrix">MobileSentrix</SelectItem>
                <SelectItem value="Utopya">Utopya</SelectItem>
              </SelectContent>
            </Select>
            <Select value={categoriaFilter} onValueChange={setCategoriaFilter}>
              <SelectTrigger className="w-full sm:w-40">
                <SelectValue placeholder="Categoría" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                {categorias.map(cat => (
                  <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button 
              variant={lowStockFilter ? "default" : "outline"}
              onClick={() => setLowStockFilter(!lowStockFilter)}
              className="gap-2"
            >
              <AlertTriangle className="w-4 h-4" />
              Stock Bajo
            </Button>
            
            {/* Botones de vista */}
            <div className="flex border rounded-lg overflow-hidden">
              <Button 
                variant={viewMode === 'table' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('table')}
                className="rounded-none"
              >
                <List className="w-4 h-4" />
              </Button>
              <Button 
                variant={viewMode === 'grid' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('grid')}
                className="rounded-none"
              >
                <Grid className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table / Grid View */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-muted-foreground">
              Cargando inventario...
            </div>
          ) : displayedProducts.length === 0 ? (
            <div className="p-8 text-center">
              <Package className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-lg font-medium">
                {search.length >= 2 ? 'Sin resultados' : 'No hay repuestos'}
              </p>
              <p className="text-muted-foreground">
                {search.length >= 2 ? 'Intenta con otros términos de búsqueda' : 'Añade tu primer repuesto al inventario'}
              </p>
            </div>
          ) : viewMode === 'grid' ? (
            /* Vista Cuadrícula - Tipo Tienda */
            <div className="p-4">
              {search.length >= 2 && (
                <div className="mb-4 p-2 bg-blue-50 rounded-lg text-sm text-blue-700">
                  {displayedProducts.length} resultado(s) para "{search}"
                </div>
              )}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                {displayedProducts.map((repuesto) => {
                  const isLowStock = repuesto.stock <= (repuesto.stock_minimo || 0);
                  return (
                    <div
                      key={repuesto.id}
                      className={`border rounded-lg overflow-hidden bg-white hover:shadow-lg transition-shadow ${isLowStock ? 'border-red-200' : ''}`}
                    >
                      {/* Imagen */}
                      <div className="aspect-square bg-gray-100 relative">
                        {repuesto.imagen_url ? (
                          <img
                            src={repuesto.imagen_url}
                            alt={repuesto.nombre}
                            className="w-full h-full object-contain p-2"
                            loading="lazy"
                            onError={(e) => { e.target.style.display = 'none'; }}
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <Package className="w-12 h-12 text-gray-300" />
                          </div>
                        )}
                        {/* Badge de Stock */}
                        <div className={`absolute top-2 right-2 px-2 py-0.5 rounded-full text-xs font-bold ${
                          isLowStock ? 'bg-red-500 text-white' : repuesto.stock > 0 ? 'bg-green-500 text-white' : 'bg-gray-400 text-white'
                        }`}>
                          {repuesto.stock} uds
                        </div>
                        {/* Badge de Calidad */}
                        {repuesto.calidad_pantalla && (
                          <div className="absolute top-2 left-2">
                            <CalidadPantallaBadge calidad={repuesto.calidad_pantalla} size="xs" />
                          </div>
                        )}
                      </div>
                      
                      {/* Info */}
                      <div className="p-3">
                        <p className="text-xs text-muted-foreground font-mono mb-1">
                          {repuesto.sku || repuesto.sku_proveedor || repuesto.ean || '-'}
                        </p>
                        <h3 className="font-medium text-sm line-clamp-2 min-h-[2.5rem]" title={repuesto.nombre}>
                          {repuesto.nombre_es || repuesto.nombre}
                        </h3>
                        <div className="flex items-center justify-between mt-2">
                          <div>
                            <p className="text-xs text-muted-foreground">Compra</p>
                            <p className="font-medium text-sm">€{repuesto.precio_compra?.toFixed(2) || '0.00'}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-muted-foreground">Venta</p>
                            <p className="font-bold text-primary">€{repuesto.precio_venta?.toFixed(2) || '0.00'}</p>
                          </div>
                        </div>
                        <div className="flex items-center justify-between mt-2 pt-2 border-t">
                          <Badge variant={repuesto.proveedor === 'Utopya' ? 'default' : 'secondary'} className="text-[10px]">
                            {repuesto.proveedor || '-'}
                          </Badge>
                          <div className="flex items-center gap-1">
                            {repuesto.url_proveedor && (
                              <a href={repuesto.url_proveedor} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-700">
                                <ExternalLink className="w-4 h-4" />
                              </a>
                            )}
                            {/* Menú de acciones */}
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-7 w-7">
                                  <MoreVertical className="w-4 h-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => {
                                  setVariantesProductoId(repuesto.id);
                                  setVariantesProductoNombre(repuesto.nombre);
                                  setShowVariantes(true);
                                }}>
                                  <GitBranch className="w-4 h-4 mr-2" />
                                  Ver Variantes
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleOpenDialog(repuesto)}>
                                  <Edit className="w-4 h-4 mr-2" />
                                  Editar
                                </DropdownMenuItem>
                                <DropdownMenuItem 
                                  className="text-destructive"
                                  onClick={() => handleDelete(repuesto.id)}
                                >
                                  <Trash2 className="w-4 h-4 mr-2" />
                                  Eliminar
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              
              {/* Paginación Grid */}
              {!search && totalPages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t mt-4">
                  <div className="text-sm text-muted-foreground">
                    Mostrando {((currentPage - 1) * PAGE_SIZE) + 1} - {Math.min(currentPage * PAGE_SIZE, totalItems)} de {totalItems} productos
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <span className="text-sm">Página {currentPage} de {totalPages}</span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Vista Tabla */
            <div className="overflow-x-auto">
              {search.length >= 2 && (
                <div className="p-2 bg-blue-50 border-b text-sm text-blue-700">
                  {displayedProducts.length} resultado(s) para "{search}"
                </div>
              )}
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10">
                      <Checkbox 
                        checked={selectedIds.length === displayedProducts.length && displayedProducts.length > 0}
                        onCheckedChange={toggleSelectAll}
                        data-testid="select-all-checkbox"
                      />
                    </TableHead>
                    <TableHead>SKU</TableHead>
                    <TableHead>Nombre</TableHead>
                    <TableHead>Calidad</TableHead>
                    <TableHead>Proveedor</TableHead>
                    <TableHead className="text-right">P. Compra</TableHead>
                    <TableHead className="text-right">P. Venta</TableHead>
                    <TableHead className="text-center">Stock</TableHead>
                    <TableHead className="w-12"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {displayedProducts.map((repuesto) => {
                    const isLowStock = repuesto.stock <= (repuesto.stock_minimo || 0);
                    return (
                      <TableRow 
                        key={repuesto.id} 
                        className={isLowStock ? 'low-stock' : ''}
                        data-testid={`repuesto-row-${repuesto.id}`}
                      >
                        <TableCell>
                          <Checkbox 
                            checked={selectedIds.includes(repuesto.id)}
                            onCheckedChange={() => toggleSelectProduct(repuesto.id)}
                          />
                        </TableCell>
                        <TableCell className="font-mono text-sm font-bold text-primary">
                          {repuesto.sku || repuesto.sku_proveedor || '-'}
                        </TableCell>
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            {isLowStock && (
                              <AlertTriangle className="w-4 h-4 text-red-500" />
                            )}
                            <span className="line-clamp-1" title={repuesto.nombre}>
                              {repuesto.nombre_es || repuesto.nombre}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          {repuesto.calidad_pantalla || repuesto.es_pantalla ? (
                            <button
                              onClick={() => {
                                setEditingCalidad(repuesto);
                                setNuevaCalidad(repuesto.calidad_pantalla || '');
                              }}
                              className="hover:opacity-80 transition-opacity"
                              title="Clic para cambiar calidad"
                            >
                              <CalidadPantallaBadge calidad={repuesto.calidad_pantalla} size="xs" />
                            </button>
                          ) : (
                            <span className="text-muted-foreground text-xs">-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge variant={repuesto.proveedor === 'Utopya' ? 'default' : 'secondary'}>
                            {repuesto.proveedor || repuesto.categoria || '-'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">€{repuesto.precio_compra?.toFixed(2) || '0.00'}</TableCell>
                        <TableCell className="text-right font-medium">€{repuesto.precio_venta?.toFixed(2) || '0.00'}</TableCell>
                        <TableCell className="text-center">
                          <Badge 
                            variant={isLowStock ? "destructive" : "secondary"}
                            className="min-w-12 justify-center"
                          >
                            {repuesto.stock}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreVertical className="w-4 h-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => {
                                setVariantesProductoId(repuesto.id);
                                setVariantesProductoNombre(repuesto.nombre);
                                setShowVariantes(true);
                              }}>
                                <GitBranch className="w-4 h-4 mr-2" />
                                Ver Variantes
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => handleCompararPrecios(repuesto)}>
                                <ArrowLeftRight className="w-4 h-4 mr-2" />
                                Comparar Precios
                              </DropdownMenuItem>
                              {(repuesto.calidad_pantalla || repuesto.es_pantalla) && (
                                <DropdownMenuItem onClick={() => {
                                  setEditingCalidad(repuesto);
                                  setNuevaCalidad(repuesto.calidad_pantalla || '');
                                }}>
                                  <Tag className="w-4 h-4 mr-2" />
                                  Cambiar Calidad
                                </DropdownMenuItem>
                              )}
                              <DropdownMenuItem onClick={() => handlePrintSingleLabel(repuesto)}>
                                <Printer className="w-4 h-4 mr-2" />
                                Imprimir Etiqueta
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => handleOpenDialog(repuesto)}>
                                <Edit className="w-4 h-4 mr-2" />
                                Editar
                              </DropdownMenuItem>
                              <DropdownMenuItem 
                                className="text-destructive"
                                onClick={() => handleDelete(repuesto.id)}
                              >
                                <Trash2 className="w-4 h-4 mr-2" />
                                Eliminar
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
              
              {/* Paginación */}
              {!search && totalPages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t">
                  <div className="text-sm text-muted-foreground">
                    Mostrando {((currentPage - 1) * PAGE_SIZE) + 1} - {Math.min(currentPage * PAGE_SIZE, totalItems)} de {totalItems} productos
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="w-4 h-4" />
                      Anterior
                    </Button>
                    <div className="flex items-center gap-1">
                      {/* Mostrar números de página */}
                      {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        let pageNum;
                        if (totalPages <= 5) {
                          pageNum = i + 1;
                        } else if (currentPage <= 3) {
                          pageNum = i + 1;
                        } else if (currentPage >= totalPages - 2) {
                          pageNum = totalPages - 4 + i;
                        } else {
                          pageNum = currentPage - 2 + i;
                        }
                        return (
                          <Button
                            key={pageNum}
                            variant={pageNum === currentPage ? "default" : "outline"}
                            size="sm"
                            className="w-8 h-8 p-0"
                            onClick={() => handlePageChange(pageNum)}
                          >
                            {pageNum}
                          </Button>
                        );
                      })}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
                    >
                      Siguiente
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialog de Comparar Precios / Alternativas */}
      <Dialog open={showAlternativasDialog} onOpenChange={setShowAlternativasDialog}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ArrowLeftRight className="w-5 h-5" />
              Comparar Precios
            </DialogTitle>
          </DialogHeader>
          
          {loadingAlternativas ? (
            <div className="p-8 text-center">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p>Buscando alternativas...</p>
            </div>
          ) : alternativasData ? (
            <div className="space-y-4">
              {/* Producto original */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="text-sm font-medium text-blue-700 mb-2">Producto Seleccionado</div>
                <div className="flex justify-between items-start gap-4">
                  <div>
                    <p className="font-medium">{alternativasData.producto_original?.nombre}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="secondary">{alternativasData.producto_original?.proveedor}</Badge>
                      {alternativasData.producto_original?.calidad_pantalla && (
                        <CalidadPantallaBadge calidad={alternativasData.producto_original.calidad_pantalla} size="xs" />
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-blue-700">
                      €{alternativasData.producto_original?.precio_venta?.toFixed(2) || '0.00'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Coste: €{alternativasData.producto_original?.precio_compra?.toFixed(2) || '0.00'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Info de detección */}
              {alternativasData.modelo_detectado && (
                <div className="text-sm text-muted-foreground">
                  Modelo detectado: <span className="font-medium">{alternativasData.modelo_detectado}</span>
                  {alternativasData.tipo_producto && (
                    <> • Tipo: <span className="font-medium capitalize">{alternativasData.tipo_producto}</span></>
                  )}
                </div>
              )}

              {/* Lista de alternativas */}
              {alternativasData.alternativas?.length > 0 ? (
                <div>
                  <h4 className="font-medium mb-3">
                    {alternativasData.alternativas.length} Alternativa(s) de otros proveedores
                  </h4>
                  <div className="space-y-2">
                    {alternativasData.alternativas.map((alt, idx) => {
                      const precioOriginal = alternativasData.producto_original?.precio_venta || 0;
                      const diferencia = alt.precio_venta - precioOriginal;
                      const porcentaje = precioOriginal > 0 ? ((diferencia / precioOriginal) * 100) : 0;
                      
                      return (
                        <div key={idx} className="border rounded-lg p-3 hover:bg-slate-50 transition-colors">
                          <div className="flex justify-between items-start gap-4">
                            <div className="flex-1">
                              <p className="font-medium line-clamp-2">{alt.nombre}</p>
                              <div className="flex items-center gap-2 mt-1">
                                <Badge variant="outline">{alt.proveedor}</Badge>
                                {alt.calidad_pantalla && (
                                  <CalidadPantallaBadge calidad={alt.calidad_pantalla} size="xs" />
                                )}
                                <span className="text-xs text-muted-foreground">
                                  Stock: {alt.stock || 0}
                                </span>
                              </div>
                            </div>
                            <div className="text-right">
                              <p className="text-xl font-bold">€{alt.precio_venta?.toFixed(2) || '0.00'}</p>
                              <p className={`text-sm font-medium ${diferencia < 0 ? 'text-green-600' : diferencia > 0 ? 'text-red-500' : 'text-muted-foreground'}`}>
                                {diferencia < 0 ? '▼' : diferencia > 0 ? '▲' : '='} 
                                {Math.abs(diferencia).toFixed(2)}€ ({porcentaje > 0 ? '+' : ''}{porcentaje.toFixed(1)}%)
                              </p>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No se encontraron alternativas de otros proveedores</p>
                  <p className="text-sm">Prueba sincronizando más productos desde los proveedores</p>
                </div>
              )}
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      {/* Dialog de Edición de Calidad */}
      <Dialog open={!!editingCalidad} onOpenChange={(open) => !open && setEditingCalidad(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Tag className="w-5 h-5" />
              Cambiar Calidad de Pantalla
            </DialogTitle>
          </DialogHeader>
          
          {editingCalidad && (
            <div className="space-y-4">
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="font-medium line-clamp-2">{editingCalidad.nombre}</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Calidad actual: {editingCalidad.calidad_pantalla ? (
                    <CalidadPantallaBadge calidad={editingCalidad.calidad_pantalla} size="xs" />
                  ) : 'Sin asignar'}
                </p>
              </div>

              <div>
                <Label>Nueva Calidad</Label>
                <CalidadPantallaSelector 
                  value={nuevaCalidad} 
                  onChange={setNuevaCalidad}
                  className="w-full mt-1"
                />
              </div>

              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setEditingCalidad(null)}>
                  Cancelar
                </Button>
                <Button onClick={handleActualizarCalidad} disabled={!nuevaCalidad}>
                  Guardar
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
        </TabsContent>

        {/* Tab Kits */}
        <TabsContent value="kits" className="mt-6">
          <KitsManager />
        </TabsContent>
      </Tabs>

      {/* Modal de Variantes */}
      <Dialog open={showVariantes} onOpenChange={setShowVariantes}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-purple-600" />
              Variantes del Producto
            </DialogTitle>
          </DialogHeader>
          {variantesProductoId && (
            <ProductoVariantes 
              productoId={variantesProductoId}
              productoNombre={variantesProductoNombre}
              onClose={() => setShowVariantes(false)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

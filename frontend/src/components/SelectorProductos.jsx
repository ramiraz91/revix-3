import { useState, useEffect } from 'react';
import { 
  Search, Smartphone, Cpu, Wrench, Package, 
  ChevronRight, Loader2, Plus, Filter, X
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function SelectorProductos({ 
  open, 
  onOpenChange, 
  onSelectProduct,
  titulo = "Seleccionar Producto"
}) {
  const [marcas, setMarcas] = useState([]);
  const [modelos, setModelos] = useState([]);
  const [tipos, setTipos] = useState([]);
  const [productos, setProductos] = useState([]);
  
  const [selectedMarca, setSelectedMarca] = useState('');
  const [selectedModelo, setSelectedModelo] = useState('');
  const [selectedTipo, setSelectedTipo] = useState('');
  const [soloStock, setSoloStock] = useState(false);
  
  const [loadingMarcas, setLoadingMarcas] = useState(false);
  const [loadingModelos, setLoadingModelos] = useState(false);
  const [loadingProductos, setLoadingProductos] = useState(false);

  // Cargar marcas y tipos al abrir
  useEffect(() => {
    if (open) {
      cargarMarcas();
      cargarTipos();
    }
  }, [open]);

  // Cargar modelos cuando cambia la marca
  useEffect(() => {
    if (selectedMarca) {
      cargarModelos(selectedMarca);
      setSelectedModelo('');
    } else {
      setModelos([]);
    }
  }, [selectedMarca]);

  // Buscar productos cuando cambian los filtros
  useEffect(() => {
    if (selectedMarca || selectedTipo) {
      buscarProductos();
    } else {
      setProductos([]);
    }
  }, [selectedMarca, selectedModelo, selectedTipo, soloStock]);

  const cargarMarcas = async () => {
    setLoadingMarcas(true);
    try {
      const res = await api.get('/repuestos/filtros/marcas');
      setMarcas(res.data.marcas || []);
    } catch (error) {
      console.error('Error cargando marcas:', error);
    } finally {
      setLoadingMarcas(false);
    }
  };

  const cargarModelos = async (marca) => {
    setLoadingModelos(true);
    try {
      const res = await api.get(`/repuestos/filtros/modelos?marca=${encodeURIComponent(marca)}`);
      setModelos(res.data.modelos || []);
    } catch (error) {
      console.error('Error cargando modelos:', error);
    } finally {
      setLoadingModelos(false);
    }
  };

  const cargarTipos = async () => {
    try {
      const res = await api.get('/repuestos/filtros/tipos');
      setTipos(res.data.tipos || []);
    } catch (error) {
      console.error('Error cargando tipos:', error);
    }
  };

  const buscarProductos = async () => {
    setLoadingProductos(true);
    try {
      const params = new URLSearchParams();
      if (selectedMarca) params.append('marca', selectedMarca);
      if (selectedModelo) params.append('modelo', selectedModelo);
      if (selectedTipo) params.append('tipo', selectedTipo);
      if (soloStock) params.append('solo_stock', 'true');
      params.append('limit', '100');
      
      const res = await api.get(`/repuestos/filtros/buscar?${params.toString()}`);
      setProductos(res.data.productos || []);
    } catch (error) {
      console.error('Error buscando productos:', error);
    } finally {
      setLoadingProductos(false);
    }
  };

  const limpiarFiltros = () => {
    setSelectedMarca('');
    setSelectedModelo('');
    setSelectedTipo('');
    setSoloStock(false);
    setProductos([]);
  };

  const handleSelect = (producto) => {
    onSelectProduct(producto);
    onOpenChange(false);
  };

  const filtrosActivos = selectedMarca || selectedModelo || selectedTipo || soloStock;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="w-5 h-5 text-blue-600" />
            {titulo}
          </DialogTitle>
        </DialogHeader>

        {/* Filtros */}
        <Card className="border-blue-100 bg-blue-50/30">
          <CardContent className="pt-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Marca */}
              <div className="space-y-1.5">
                <Label className="text-xs flex items-center gap-1">
                  <Smartphone className="w-3 h-3" />
                  Marca
                </Label>
                <Select value={selectedMarca} onValueChange={setSelectedMarca}>
                  <SelectTrigger className="bg-white" data-testid="select-marca">
                    <SelectValue placeholder="Todas las marcas" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todas las marcas</SelectItem>
                    {marcas.map((m) => (
                      <SelectItem key={m.nombre} value={m.nombre}>
                        <span className="flex items-center justify-between w-full">
                          {m.nombre}
                          <Badge variant="secondary" className="ml-2 text-xs">{m.cantidad}</Badge>
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Modelo */}
              <div className="space-y-1.5">
                <Label className="text-xs flex items-center gap-1">
                  <Cpu className="w-3 h-3" />
                  Modelo
                </Label>
                <Select 
                  value={selectedModelo} 
                  onValueChange={setSelectedModelo}
                  disabled={!selectedMarca || loadingModelos}
                >
                  <SelectTrigger className="bg-white" data-testid="select-modelo">
                    <SelectValue placeholder={loadingModelos ? "Cargando..." : "Todos los modelos"} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todos los modelos</SelectItem>
                    {modelos.map((m) => (
                      <SelectItem key={m.nombre} value={m.nombre}>
                        <span className="flex items-center justify-between w-full">
                          {m.nombre}
                          <Badge variant="secondary" className="ml-2 text-xs">{m.cantidad}</Badge>
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Tipo de servicio */}
              <div className="space-y-1.5">
                <Label className="text-xs flex items-center gap-1">
                  <Wrench className="w-3 h-3" />
                  Tipo de Servicio
                </Label>
                <Select value={selectedTipo} onValueChange={setSelectedTipo}>
                  <SelectTrigger className="bg-white" data-testid="select-tipo">
                    <SelectValue placeholder="Todos los tipos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todos los tipos</SelectItem>
                    {tipos.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Solo con stock + Limpiar */}
              <div className="space-y-1.5">
                <Label className="text-xs">Opciones</Label>
                <div className="flex items-center gap-3 h-9">
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={soloStock}
                      onCheckedChange={setSoloStock}
                      id="solo-stock"
                    />
                    <Label htmlFor="solo-stock" className="text-xs cursor-pointer">
                      Con stock
                    </Label>
                  </div>
                  {filtrosActivos && (
                    <Button variant="ghost" size="sm" onClick={limpiarFiltros}>
                      <X className="w-4 h-4 mr-1" />
                      Limpiar
                    </Button>
                  )}
                </div>
              </div>
            </div>

            {/* Resumen de filtros */}
            {filtrosActivos && (
              <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t">
                {selectedMarca && (
                  <Badge variant="default" className="bg-blue-600">
                    {selectedMarca}
                  </Badge>
                )}
                {selectedModelo && (
                  <Badge variant="default" className="bg-purple-600">
                    {selectedModelo}
                  </Badge>
                )}
                {selectedTipo && (
                  <Badge variant="default" className="bg-green-600">
                    {tipos.find(t => t.id === selectedTipo)?.nombre || selectedTipo}
                  </Badge>
                )}
                {soloStock && (
                  <Badge variant="outline">Con stock</Badge>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Resultados */}
        <div className="flex-1 overflow-hidden border rounded-lg">
          {loadingProductos ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
              <span className="ml-2 text-muted-foreground">Buscando productos...</span>
            </div>
          ) : !filtrosActivos ? (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <Filter className="w-12 h-12 mb-3 opacity-30" />
              <p className="font-medium">Selecciona filtros para buscar</p>
              <p className="text-sm mt-1">Elige una marca, modelo o tipo de servicio</p>
            </div>
          ) : productos.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <Package className="w-12 h-12 mb-3 opacity-30" />
              <p>No se encontraron productos</p>
              <p className="text-sm mt-1">Prueba con otros filtros</p>
            </div>
          ) : (
            <div className="overflow-y-auto max-h-[350px]">
              <Table>
                <TableHeader className="sticky top-0 bg-white z-10">
                  <TableRow>
                    <TableHead>Producto</TableHead>
                    <TableHead>Calidad</TableHead>
                    <TableHead>Proveedor</TableHead>
                    <TableHead className="text-center">Stock</TableHead>
                    <TableHead className="text-right">Precio</TableHead>
                    <TableHead className="w-16"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {productos.map((producto) => (
                    <TableRow 
                      key={producto.id} 
                      className="cursor-pointer hover:bg-blue-50"
                      onClick={() => handleSelect(producto)}
                    >
                      <TableCell>
                        <div>
                          <p className="font-medium text-sm line-clamp-1">
                            {producto.nombre_es || producto.nombre}
                          </p>
                          {producto.sku && (
                            <p className="text-xs text-muted-foreground">{producto.sku}</p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        {producto.calidad_pantalla ? (
                          <Badge 
                            variant="outline" 
                            className="text-xs"
                            style={{
                              backgroundColor: producto.calidad_info?.color || '#f3f4f6',
                              color: producto.calidad_info?.textColor || '#374151'
                            }}
                          >
                            {producto.calidad_info?.label || producto.calidad_pantalla}
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="text-xs">
                          {producto.proveedor || '-'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge variant={producto.stock > 0 ? 'default' : 'secondary'}>
                          {producto.stock || 0}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        €{(producto.precio_venta || 0).toFixed(2)}
                      </TableCell>
                      <TableCell>
                        <Button size="sm" variant="ghost">
                          <Plus className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-2 border-t">
          <span className="text-sm text-muted-foreground">
            {productos.length > 0 && `${productos.length} productos encontrados`}
          </span>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cerrar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

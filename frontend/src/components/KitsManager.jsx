import { useState, useEffect } from 'react';
import { 
  Plus, Search, Package, Layers, Trash2, Edit, 
  ChevronRight, Euro, Tag, Copy, Wrench, Truck, 
  Settings, Box, Loader2, MoreVertical, CheckCircle2
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogFooter 
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import api from '@/lib/api';
import { toast } from 'sonner';

const tiposComponente = [
  { value: 'producto', label: 'Producto/Repuesto', icon: Box, color: 'bg-blue-100 text-blue-800' },
  { value: 'mano_obra', label: 'Mano de Obra', icon: Wrench, color: 'bg-orange-100 text-orange-800' },
  { value: 'logistica', label: 'Logística', icon: Truck, color: 'bg-green-100 text-green-800' },
  { value: 'servicio', label: 'Servicio', icon: Settings, color: 'bg-purple-100 text-purple-800' },
  { value: 'otro', label: 'Otro', icon: Tag, color: 'bg-gray-100 text-gray-800' }
];

const getTipoInfo = (tipo) => tiposComponente.find(t => t.value === tipo) || tiposComponente[4];

export default function KitsManager() {
  const [kits, setKits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingKit, setEditingKit] = useState(null);
  const [plantillas, setPlantillas] = useState([]);
  const [productos, setProductos] = useState([]);
  const [buscandoProducto, setBuscandoProducto] = useState('');
  const [stats, setStats] = useState(null);
  
  // Modal de búsqueda de productos para componentes
  const [showProductSearch, setShowProductSearch] = useState(false);
  const [productSearchQuery, setProductSearchQuery] = useState('');
  const [productSearchResults, setProductSearchResults] = useState([]);
  const [searchingProducts, setSearchingProducts] = useState(false);
  const [componenteIndexParaProducto, setComponenteIndexParaProducto] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    nombre: '',
    descripcion: '',
    categoria: '',
    producto_principal_id: null,
    producto_principal_nombre: '',
    componentes: [],
    activo: true,
    tags: []
  });

  useEffect(() => {
    cargarDatos();
  }, []);

  // Búsqueda dinámica de productos
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (productSearchQuery.length >= 2) {
        setSearchingProducts(true);
        try {
          const res = await api.get(`/repuestos/buscar/rapido?q=${encodeURIComponent(productSearchQuery)}&limit=30`);
          setProductSearchResults(res.data || []);
        } catch (error) {
          console.error('Error searching products:', error);
        } finally {
          setSearchingProducts(false);
        }
      } else {
        setProductSearchResults([]);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [productSearchQuery]);

  const cargarDatos = async () => {
    try {
      setLoading(true);
      const [kitsRes, plantillasRes, statsRes] = await Promise.all([
        api.get('/kits?activo=true'),
        api.get('/kits/plantillas/lista'),
        api.get('/kits/stats')
      ]);
      setKits(kitsRes.data.items || []);
      setPlantillas(plantillasRes.data || []);
      setStats(statsRes.data);
    } catch (error) {
      toast.error('Error cargando kits');
    } finally {
      setLoading(false);
    }
  };

  const buscarProductos = async (query) => {
    if (query.length < 2) {
      setProductos([]);
      return;
    }
    try {
      const res = await api.get(`/repuestos/buscar/rapido?q=${encodeURIComponent(query)}&limit=10`);
      setProductos(res.data || []);
    } catch (error) {
      console.error('Error buscando productos:', error);
    }
  };

  const abrirBuscadorProducto = (componenteIndex) => {
    setComponenteIndexParaProducto(componenteIndex);
    setProductSearchQuery('');
    setProductSearchResults([]);
    setShowProductSearch(true);
  };

  const seleccionarProducto = (producto) => {
    if (componenteIndexParaProducto !== null) {
      const nuevos = [...formData.componentes];
      nuevos[componenteIndexParaProducto] = {
        ...nuevos[componenteIndexParaProducto],
        repuesto_id: producto.id,
        repuesto_nombre: producto.nombre,
        descripcion: producto.nombre_es || producto.nombre,
        precio_unitario: producto.precio_venta || 0,
        precio_coste: producto.precio_compra || 0,
        sku: producto.sku || producto.sku_proveedor
      };
      setFormData({ ...formData, componentes: nuevos });
    }
    setShowProductSearch(false);
    setComponenteIndexParaProducto(null);
  };

  const abrirNuevoKit = (plantilla = null) => {
    if (plantilla) {
      setFormData({
        nombre: plantilla.nombre,
        descripcion: plantilla.descripcion,
        categoria: '',
        producto_principal_id: null,
        producto_principal_nombre: '',
        componentes: plantilla.componentes.map((c, idx) => ({
          ...c,
          id: `temp-${idx}`,
          iva_porcentaje: 21,
          descuento: 0
        })),
        activo: true,
        tags: []
      });
    } else {
      setFormData({
        nombre: '',
        descripcion: '',
        categoria: '',
        producto_principal_id: null,
        producto_principal_nombre: '',
        componentes: [],
        activo: true,
        tags: []
      });
    }
    setEditingKit(null);
    setShowDialog(true);
  };

  const abrirEditarKit = (kit) => {
    setFormData({
      nombre: kit.nombre,
      descripcion: kit.descripcion || '',
      categoria: kit.categoria || '',
      producto_principal_id: kit.producto_principal_id,
      producto_principal_nombre: kit.producto_principal_nombre || '',
      componentes: kit.componentes.map((c, idx) => ({ ...c, id: c.id || `comp-${idx}` })),
      activo: kit.activo,
      tags: kit.tags || []
    });
    setEditingKit(kit);
    setShowDialog(true);
  };

  const agregarComponente = (tipo = 'producto') => {
    const nuevoComponente = {
      id: `temp-${Date.now()}`,
      tipo,
      repuesto_id: null,
      repuesto_nombre: '',
      descripcion: tipo === 'mano_obra' ? 'Mano de obra' : tipo === 'logistica' ? 'Logística' : '',
      cantidad: 1,
      precio_unitario: 0,
      iva_porcentaje: 21,
      descuento: 0,
      precio_fijo: tipo !== 'producto'
    };
    setFormData({ ...formData, componentes: [...formData.componentes, nuevoComponente] });
  };

  const actualizarComponente = (index, campo, valor) => {
    const nuevos = [...formData.componentes];
    nuevos[index][campo] = valor;
    
    if (campo === 'repuesto_seleccionado' && valor) {
      nuevos[index].repuesto_id = valor.id;
      nuevos[index].repuesto_nombre = valor.nombre;
      nuevos[index].descripcion = valor.nombre;
      if (!nuevos[index].precio_fijo) {
        nuevos[index].precio_unitario = valor.precio_venta || 0;
      }
    }
    
    setFormData({ ...formData, componentes: nuevos });
  };

  const eliminarComponente = (index) => {
    setFormData({
      ...formData,
      componentes: formData.componentes.filter((_, i) => i !== index)
    });
  };

  const calcularTotal = () => {
    return formData.componentes.reduce((total, comp) => {
      const subtotal = (comp.cantidad || 1) * (comp.precio_unitario || 0) * (1 - (comp.descuento || 0) / 100);
      const iva = subtotal * (comp.iva_porcentaje || 21) / 100;
      return total + subtotal + iva;
    }, 0);
  };

  const guardarKit = async () => {
    if (!formData.nombre.trim()) {
      toast.error('El nombre es obligatorio');
      return;
    }
    if (formData.componentes.length === 0) {
      toast.error('Debe añadir al menos un componente');
      return;
    }

    try {
      const payload = {
        ...formData,
        componentes: formData.componentes.map(({ id, repuesto_seleccionado, ...rest }) => rest)
      };

      if (editingKit) {
        await api.put(`/kits/${editingKit.id}`, payload);
        toast.success('Kit actualizado');
      } else {
        await api.post('/kits/', payload);
        toast.success('Kit creado');
      }
      setShowDialog(false);
      cargarDatos();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error guardando kit');
    }
  };

  const eliminarKit = async (kitId) => {
    if (!window.confirm('¿Eliminar este kit?')) return;
    try {
      await api.delete(`/kits/${kitId}`);
      toast.success('Kit eliminado');
      cargarDatos();
    } catch (error) {
      toast.error('Error eliminando kit');
    }
  };

  const duplicarKit = async (kit) => {
    setFormData({
      nombre: `${kit.nombre} (copia)`,
      descripcion: kit.descripcion || '',
      categoria: kit.categoria || '',
      producto_principal_id: kit.producto_principal_id,
      producto_principal_nombre: kit.producto_principal_nombre || '',
      componentes: kit.componentes.map((c, idx) => ({ ...c, id: `dup-${idx}` })),
      activo: true,
      tags: kit.tags || []
    });
    setEditingKit(null);
    setShowDialog(true);
  };

  const filteredKits = kits.filter(kit => 
    kit.nombre.toLowerCase().includes(search.toLowerCase()) ||
    (kit.categoria || '').toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="kits-manager">
      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Kits</p>
                  <p className="text-2xl font-bold">{stats.total_kits}</p>
                </div>
                <Layers className="w-8 h-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Kits Activos</p>
                  <p className="text-2xl font-bold text-green-600">{stats.kits_activos}</p>
                </div>
                <CheckCircle2 className="w-8 h-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Componentes</p>
                  <p className="text-2xl font-bold">{stats.total_componentes}</p>
                </div>
                <Package className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Valor Promedio</p>
                  <p className="text-2xl font-bold">{stats.valor_promedio?.toFixed(0) || 0}€</p>
                </div>
                <Euro className="w-8 h-8 text-amber-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Buscar kits..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
            data-testid="search-kits-input"
          />
        </div>
        
        <div className="flex gap-2">
          {/* Plantillas */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                <Copy className="w-4 h-4 mr-2" />
                Usar Plantilla
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-64">
              {plantillas.map((p) => (
                <DropdownMenuItem key={p.id} onClick={() => abrirNuevoKit(p)}>
                  <div>
                    <p className="font-medium">{p.nombre}</p>
                    <p className="text-xs text-muted-foreground">{p.descripcion}</p>
                  </div>
                </DropdownMenuItem>
              ))}
              {plantillas.length === 0 && (
                <p className="text-sm text-muted-foreground p-2">Sin plantillas disponibles</p>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
          
          <Button onClick={() => abrirNuevoKit()} data-testid="btn-nuevo-kit">
            <Plus className="w-4 h-4 mr-2" />
            Nuevo Kit
          </Button>
        </div>
      </div>

      {/* Kits Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Kit</TableHead>
                <TableHead>Categoría</TableHead>
                <TableHead className="text-center">Componentes</TableHead>
                <TableHead className="text-right">Precio Total</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredKits.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    {search ? 'No se encontraron kits' : 'No hay kits creados. ¡Crea el primero!'}
                  </TableCell>
                </TableRow>
              ) : (
                filteredKits.map((kit) => (
                  <TableRow key={kit.id} className="cursor-pointer hover:bg-slate-50" onClick={() => abrirEditarKit(kit)}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                          <Layers className="w-5 h-5 text-purple-600" />
                        </div>
                        <div>
                          <p className="font-medium">{kit.nombre}</p>
                          {kit.descripcion && (
                            <p className="text-xs text-muted-foreground line-clamp-1">{kit.descripcion}</p>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      {kit.categoria ? (
                        <Badge variant="outline">{kit.categoria}</Badge>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex items-center justify-center gap-1">
                        {kit.componentes?.slice(0, 3).map((comp, idx) => {
                          const info = getTipoInfo(comp.tipo);
                          const Icon = info.icon;
                          return (
                            <div key={idx} className={`w-6 h-6 rounded flex items-center justify-center ${info.color}`}>
                              <Icon className="w-3 h-3" />
                            </div>
                          );
                        })}
                        {kit.componentes?.length > 3 && (
                          <span className="text-xs text-muted-foreground ml-1">+{kit.componentes.length - 3}</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono font-medium">
                      {kit.precio_total?.toFixed(2) || '0.00'}€
                    </TableCell>
                    <TableCell>
                      <Badge variant={kit.activo ? 'default' : 'secondary'}>
                        {kit.activo ? 'Activo' : 'Inactivo'}
                      </Badge>
                    </TableCell>
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => abrirEditarKit(kit)}>
                            <Edit className="w-4 h-4 mr-2" />
                            Editar
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => duplicarKit(kit)}>
                            <Copy className="w-4 h-4 mr-2" />
                            Duplicar
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => eliminarKit(kit.id)} className="text-red-600">
                            <Trash2 className="w-4 h-4 mr-2" />
                            Eliminar
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Dialog Crear/Editar Kit */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-purple-600" />
              {editingKit ? 'Editar Kit' : 'Nuevo Kit'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-6">
            {/* Info básica */}
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label>Nombre del Kit *</Label>
                <Input
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="Ej: Kit Pantalla iPhone 15 Pro"
                  data-testid="input-kit-nombre"
                />
              </div>
              <div>
                <Label>Categoría</Label>
                <Select 
                  value={formData.categoria} 
                  onValueChange={(v) => setFormData({ ...formData, categoria: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar categoría" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pantalla">Pantalla</SelectItem>
                    <SelectItem value="bateria">Batería</SelectItem>
                    <SelectItem value="carga">Puerto de carga</SelectItem>
                    <SelectItem value="reparacion_agua">Daño por agua</SelectItem>
                    <SelectItem value="premium">Servicio Premium</SelectItem>
                    <SelectItem value="otro">Otro</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={formData.activo}
                  onCheckedChange={(v) => setFormData({ ...formData, activo: v })}
                />
                <Label>Kit activo</Label>
              </div>
              <div className="col-span-2">
                <Label>Descripción</Label>
                <Textarea
                  value={formData.descripcion}
                  onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                  placeholder="Descripción del kit..."
                  rows={2}
                />
              </div>
            </div>

            {/* Componentes */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <Label className="text-base font-semibold">Componentes del Kit</Label>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                      <Plus className="w-4 h-4 mr-2" />
                      Añadir
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {tiposComponente.map((tipo) => {
                      const Icon = tipo.icon;
                      return (
                        <DropdownMenuItem key={tipo.value} onClick={() => agregarComponente(tipo.value)}>
                          <Icon className="w-4 h-4 mr-2" />
                          {tipo.label}
                        </DropdownMenuItem>
                      );
                    })}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              {formData.componentes.length === 0 ? (
                <div className="border-2 border-dashed rounded-lg p-8 text-center text-muted-foreground">
                  <Package className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>Añade componentes al kit</p>
                  <p className="text-xs mt-1">Productos, mano de obra, logística...</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {formData.componentes.map((comp, index) => {
                    const tipoInfo = getTipoInfo(comp.tipo);
                    const TipoIcon = tipoInfo.icon;
                    
                    return (
                      <div key={comp.id} className="border rounded-lg p-3 bg-slate-50/50">
                        <div className="flex items-start gap-3">
                          <div className={`w-8 h-8 rounded flex items-center justify-center flex-shrink-0 ${tipoInfo.color}`}>
                            <TipoIcon className="w-4 h-4" />
                          </div>
                          
                          <div className="flex-1 grid grid-cols-12 gap-2">
                            {/* Tipo producto: buscar en inventario */}
                            {comp.tipo === 'producto' ? (
                              <div className="col-span-5">
                                <div className="flex gap-1">
                                  <Input
                                    placeholder="Nombre del producto"
                                    value={comp.descripcion}
                                    onChange={(e) => actualizarComponente(index, 'descripcion', e.target.value)}
                                    className="text-sm flex-1"
                                    readOnly={!!comp.repuesto_id}
                                  />
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="icon"
                                    className="h-9 w-9 flex-shrink-0"
                                    onClick={() => abrirBuscadorProducto(index)}
                                    title="Buscar en inventario"
                                  >
                                    <Search className="w-4 h-4" />
                                  </Button>
                                </div>
                                {comp.repuesto_id && (
                                  <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
                                    <CheckCircle2 className="w-3 h-3" />
                                    Vinculado al inventario
                                    {comp.sku && <span className="text-muted-foreground">({comp.sku})</span>}
                                  </p>
                                )}
                              </div>
                            ) : (
                              <div className="col-span-5">
                                <Input
                                  placeholder="Descripción"
                                  value={comp.descripcion}
                                  onChange={(e) => actualizarComponente(index, 'descripcion', e.target.value)}
                                  className="text-sm"
                                />
                              </div>
                            )}
                            
                            <div className="col-span-2">
                              <Input
                                type="number"
                                min="1"
                                placeholder="Cant."
                                value={comp.cantidad}
                                onChange={(e) => actualizarComponente(index, 'cantidad', parseInt(e.target.value) || 1)}
                                className="text-sm text-center"
                              />
                            </div>
                            
                            <div className="col-span-2">
                              <Input
                                type="number"
                                step="0.01"
                                placeholder="Precio"
                                value={comp.precio_unitario}
                                onChange={(e) => actualizarComponente(index, 'precio_unitario', parseFloat(e.target.value) || 0)}
                                className="text-sm text-right"
                              />
                            </div>
                            
                            <div className="col-span-2">
                              <Select 
                                value={String(comp.iva_porcentaje || 21)}
                                onValueChange={(v) => actualizarComponente(index, 'iva_porcentaje', parseInt(v))}
                              >
                                <SelectTrigger className="text-sm h-9">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="0">0%</SelectItem>
                                  <SelectItem value="4">4%</SelectItem>
                                  <SelectItem value="10">10%</SelectItem>
                                  <SelectItem value="21">21%</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                            
                            <div className="col-span-1 flex items-center justify-end">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-red-500 hover:text-red-700"
                                onClick={() => eliminarComponente(index)}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </div>
                        </div>
                        
                        {/* Subtotal */}
                        <div className="text-right text-xs text-muted-foreground mt-2">
                          Subtotal: {((comp.cantidad || 1) * (comp.precio_unitario || 0) * (1 + (comp.iva_porcentaje || 21) / 100)).toFixed(2)}€
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Total */}
            {formData.componentes.length > 0 && (
              <div className="flex justify-end">
                <div className="bg-purple-50 rounded-lg px-6 py-3">
                  <p className="text-sm text-muted-foreground">Total del Kit (IVA incl.)</p>
                  <p className="text-2xl font-bold text-purple-700">{calcularTotal().toFixed(2)}€</p>
                </div>
              </div>
            )}
          </div>

          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setShowDialog(false)}>
              Cancelar
            </Button>
            <Button onClick={guardarKit} data-testid="btn-guardar-kit">
              {editingKit ? 'Guardar Cambios' : 'Crear Kit'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal de búsqueda de productos del inventario */}
      <Dialog open={showProductSearch} onOpenChange={setShowProductSearch}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="w-5 h-5 text-blue-600" />
              Seleccionar Producto del Inventario
            </DialogTitle>
          </DialogHeader>
          
          {/* Buscador */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Buscar por nombre, SKU..."
              value={productSearchQuery}
              onChange={(e) => setProductSearchQuery(e.target.value)}
              className="pl-10"
              autoFocus
            />
          </div>
          
          {/* Resultados */}
          <div className="flex-1 overflow-y-auto min-h-[250px] border rounded-lg">
            {searchingProducts ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="w-6 h-6 animate-spin" />
                <span className="ml-2 text-muted-foreground">Buscando...</span>
              </div>
            ) : productSearchQuery.length < 2 ? (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                <Search className="w-10 h-10 mb-2 opacity-30" />
                <p>Escribe al menos 2 caracteres</p>
              </div>
            ) : productSearchResults.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                <Package className="w-10 h-10 mb-2 opacity-30" />
                <p>No se encontraron productos</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Producto</TableHead>
                    <TableHead className="w-20 text-center">Stock</TableHead>
                    <TableHead className="w-24 text-right">Precio</TableHead>
                    <TableHead className="w-16"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {productSearchResults.map((producto) => (
                    <TableRow key={producto.id} className="cursor-pointer hover:bg-blue-50">
                      <TableCell>
                        <div>
                          <p className="font-medium text-sm">{producto.nombre_es || producto.nombre}</p>
                          <div className="flex gap-1 mt-0.5">
                            {producto.sku && (
                              <Badge variant="outline" className="text-[10px]">
                                {producto.sku}
                              </Badge>
                            )}
                            {producto.proveedor && (
                              <Badge variant="secondary" className="text-[10px]">
                                {producto.proveedor}
                              </Badge>
                            )}
                          </div>
                        </div>
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
                        <Button
                          size="sm"
                          onClick={() => seleccionarProducto(producto)}
                        >
                          <Plus className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
          
          <div className="flex justify-between items-center pt-2 border-t">
            <span className="text-sm text-muted-foreground">
              {productSearchResults.length > 0 && `${productSearchResults.length} resultados`}
            </span>
            <Button variant="outline" onClick={() => setShowProductSearch(false)}>
              Cancelar
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

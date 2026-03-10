import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Textarea } from '../components/ui/textarea';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';
import { 
  Plus, Search, Package, Layers, Trash2, Edit, 
  ChevronRight, Euro, Tag, Copy, GripVertical,
  Wrench, Truck, Settings, Box
} from 'lucide-react';

const tiposComponente = [
  { value: 'producto', label: 'Producto/Repuesto', icon: Box, color: 'bg-blue-100 text-blue-800' },
  { value: 'mano_obra', label: 'Mano de Obra', icon: Wrench, color: 'bg-orange-100 text-orange-800' },
  { value: 'logistica', label: 'Logística', icon: Truck, color: 'bg-green-100 text-green-800' },
  { value: 'servicio', label: 'Servicio', icon: Settings, color: 'bg-purple-100 text-purple-800' },
  { value: 'otro', label: 'Otro', icon: Tag, color: 'bg-gray-100 text-gray-800' }
];

const getTipoInfo = (tipo) => tiposComponente.find(t => t.value === tipo) || tiposComponente[4];

export default function Kits() {
  const navigate = useNavigate();
  const [kits, setKits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingKit, setEditingKit] = useState(null);
  const [plantillas, setPlantillas] = useState([]);
  const [productos, setProductos] = useState([]);
  const [buscandoProducto, setBuscandoProducto] = useState('');
  const [stats, setStats] = useState(null);
  
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
      toast.error('Error cargando datos');
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
    
    // Si selecciona un producto, actualizar nombre y precio
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
        await api.post('/kits', payload);
        toast.success('Kit creado');
      }
      setShowDialog(false);
      cargarDatos();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const eliminarKit = async (kit) => {
    if (!confirm(`¿Eliminar el kit "${kit.nombre}"?`)) return;
    try {
      await api.delete(`/kits/${kit.id}`);
      toast.success('Kit eliminado');
      cargarDatos();
    } catch (error) {
      toast.error('Error al eliminar');
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(amount || 0);
  };

  const filteredKits = kits.filter(k => 
    k.nombre.toLowerCase().includes(search.toLowerCase()) ||
    k.descripcion?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="kits-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Layers className="h-6 w-6 text-blue-600" />
            Artículos Compuestos / Kits
          </h1>
          <p className="text-gray-500">Crea combinaciones de productos y servicios</p>
        </div>
        <Button onClick={() => abrirNuevoKit()}>
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Kit
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Kits</p>
                <p className="text-2xl font-bold">{stats?.total_kits || 0}</p>
              </div>
              <Layers className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Kits Activos</p>
                <p className="text-2xl font-bold text-green-600">{stats?.kits_activos || 0}</p>
              </div>
              <Package className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Plantillas</p>
                <p className="text-2xl font-bold text-purple-600">{plantillas.length}</p>
              </div>
              <Copy className="h-8 w-8 text-purple-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Plantillas rápidas */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Crear desde plantilla</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {plantillas.map((plantilla, idx) => (
              <Button
                key={idx}
                variant="outline"
                onClick={() => abrirNuevoKit(plantilla)}
                className="flex items-center gap-2"
              >
                <Copy className="h-4 w-4" />
                {plantilla.nombre}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Búsqueda y lista */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Buscar kits..."
                className="pl-10"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredKits.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <Layers className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium">No hay kits</p>
              <p>Crea tu primer artículo compuesto</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredKits.map((kit) => (
                <div
                  key={kit.id}
                  className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-lg">{kit.nombre}</h3>
                        {kit.categoria && (
                          <Badge variant="outline">{kit.categoria}</Badge>
                        )}
                      </div>
                      {kit.descripcion && (
                        <p className="text-sm text-gray-500 mt-1">{kit.descripcion}</p>
                      )}
                      <div className="flex flex-wrap gap-2 mt-3">
                        {kit.componentes?.map((comp, idx) => {
                          const tipoInfo = getTipoInfo(comp.tipo);
                          return (
                            <Badge key={idx} className={tipoInfo.color}>
                              {comp.descripcion || comp.tipo}
                            </Badge>
                          );
                        })}
                      </div>
                    </div>
                    <div className="text-right ml-4">
                      <p className="text-2xl font-bold text-blue-600">{formatCurrency(kit.total)}</p>
                      <p className="text-sm text-gray-500">{kit.num_componentes} componentes</p>
                      <div className="flex gap-2 mt-2">
                        <Button variant="ghost" size="sm" onClick={() => abrirEditarKit(kit)}>
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => eliminarKit(kit)}>
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialog crear/editar kit */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingKit ? 'Editar Kit' : 'Nuevo Kit'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-6 py-4">
            {/* Info básica */}
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label>Nombre del Kit *</Label>
                <Input
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="Ej: Kit Pantalla iPhone 15"
                />
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
              <div>
                <Label>Categoría</Label>
                <Input
                  value={formData.categoria}
                  onChange={(e) => setFormData({ ...formData, categoria: e.target.value })}
                  placeholder="Ej: Pantallas, Baterías..."
                />
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={formData.activo}
                  onCheckedChange={(v) => setFormData({ ...formData, activo: v })}
                />
                <Label>Kit Activo</Label>
              </div>
            </div>

            {/* Componentes */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <Label className="text-base font-semibold">Componentes del Kit</Label>
                <div className="flex gap-2">
                  {tiposComponente.map((tipo) => (
                    <Button
                      key={tipo.value}
                      variant="outline"
                      size="sm"
                      onClick={() => agregarComponente(tipo.value)}
                      title={`Añadir ${tipo.label}`}
                    >
                      <tipo.icon className="h-4 w-4" />
                    </Button>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                {formData.componentes.map((comp, idx) => {
                  const tipoInfo = getTipoInfo(comp.tipo);
                  return (
                    <div key={comp.id || idx} className="border rounded-lg p-3 bg-gray-50">
                      <div className="flex items-start gap-3">
                        <div className="flex items-center gap-2 min-w-[100px]">
                          <GripVertical className="h-4 w-4 text-gray-400 cursor-move" />
                          <Badge className={tipoInfo.color}>
                            <tipoInfo.icon className="h-3 w-3 mr-1" />
                            {tipoInfo.label}
                          </Badge>
                        </div>
                        
                        <div className="flex-1 grid grid-cols-4 gap-3">
                          {comp.tipo === 'producto' ? (
                            <div className="col-span-2">
                              <Label className="text-xs">Buscar Producto</Label>
                              <Input
                                placeholder="Buscar producto..."
                                value={comp.repuesto_nombre || buscandoProducto}
                                onChange={(e) => {
                                  setBuscandoProducto(e.target.value);
                                  buscarProductos(e.target.value);
                                }}
                              />
                              {productos.length > 0 && !comp.repuesto_id && (
                                <div className="absolute z-10 mt-1 bg-white border rounded-lg shadow-lg max-h-40 overflow-y-auto">
                                  {productos.map((p) => (
                                    <div
                                      key={p.id}
                                      className="p-2 hover:bg-gray-100 cursor-pointer text-sm"
                                      onClick={() => {
                                        actualizarComponente(idx, 'repuesto_seleccionado', p);
                                        setProductos([]);
                                        setBuscandoProducto('');
                                      }}
                                    >
                                      {p.nombre} - {formatCurrency(p.precio_venta)}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          ) : (
                            <div className="col-span-2">
                              <Label className="text-xs">Descripción</Label>
                              <Input
                                value={comp.descripcion}
                                onChange={(e) => actualizarComponente(idx, 'descripcion', e.target.value)}
                                placeholder="Descripción..."
                              />
                            </div>
                          )}
                          
                          <div>
                            <Label className="text-xs">Cantidad</Label>
                            <Input
                              type="number"
                              value={comp.cantidad}
                              onChange={(e) => actualizarComponente(idx, 'cantidad', parseFloat(e.target.value) || 1)}
                              min="1"
                            />
                          </div>
                          
                          <div>
                            <Label className="text-xs">Precio €</Label>
                            <Input
                              type="number"
                              step="0.01"
                              value={comp.precio_unitario}
                              onChange={(e) => actualizarComponente(idx, 'precio_unitario', parseFloat(e.target.value) || 0)}
                              disabled={!comp.precio_fijo && comp.tipo === 'producto'}
                            />
                          </div>
                        </div>
                        
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => eliminarComponente(idx)}
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                      
                      {comp.tipo === 'producto' && (
                        <div className="mt-2 flex items-center gap-2 text-xs">
                          <Switch
                            checked={!comp.precio_fijo}
                            onCheckedChange={(v) => actualizarComponente(idx, 'precio_fijo', !v)}
                          />
                          <span className="text-gray-500">Usar precio del producto (actualiza automáticamente)</span>
                        </div>
                      )}
                    </div>
                  );
                })}
                
                {formData.componentes.length === 0 && (
                  <div className="text-center py-8 text-gray-500 border-2 border-dashed rounded-lg">
                    <Package className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>Añade componentes usando los botones de arriba</p>
                  </div>
                )}
              </div>
            </div>

            {/* Total */}
            {formData.componentes.length > 0 && (
              <div className="bg-blue-50 rounded-lg p-4">
                <div className="flex justify-between items-center">
                  <span className="font-semibold">Total del Kit:</span>
                  <span className="text-2xl font-bold text-blue-600">{formatCurrency(calcularTotal())}</span>
                </div>
                <p className="text-sm text-gray-500 mt-1">
                  {formData.componentes.length} componente(s) • IVA incluido
                </p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDialog(false)}>Cancelar</Button>
            <Button onClick={guardarKit}>
              {editingKit ? 'Guardar Cambios' : 'Crear Kit'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

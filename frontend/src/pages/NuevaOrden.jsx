import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Search, X, User, Smartphone, Truck, Package, Edit, Trash2, Percent, Layers, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
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
  DialogTrigger,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import api, { clientesAPI, repuestosAPI, ordenesAPI } from '@/lib/api';
import { toast } from 'sonner';

export default function NuevaOrden() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [clientes, setClientes] = useState([]);
  const [repuestos, setRepuestos] = useState([]);
  const [kits, setKits] = useState([]);
  const [clienteSeleccionado, setClienteSeleccionado] = useState(null);
  const [materialesSeleccionados, setMaterialesSeleccionados] = useState([]);
  const [openClienteSearch, setOpenClienteSearch] = useState(false);
  const [openMaterialSearch, setOpenMaterialSearch] = useState(false);
  const [openKitSearch, setOpenKitSearch] = useState(false);
  const [showNuevoCliente, setShowNuevoCliente] = useState(false);
  const [showMaterialPersonalizado, setShowMaterialPersonalizado] = useState(false);
  const [showEditarMaterial, setShowEditarMaterial] = useState(false);
  const [editingMaterialIndex, setEditingMaterialIndex] = useState(null);
  
  // Nuevo modal de búsqueda de materiales expandido
  const [showBuscarMaterial, setShowBuscarMaterial] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  
  const [formData, setFormData] = useState({
    dispositivo: {
      modelo: '',
      imei: '',
      color: '',
      daños: ''
    },
    agencia_envio: '',
    codigo_recogida_entrada: '',
    numero_autorizacion: '',
    notas: ''
  });

  const [nuevoCliente, setNuevoCliente] = useState({
    nombre: '',
    apellidos: '',
    dni: '',
    telefono: '',
    email: '',
    direccion: '',
    planta: '',
    puerta: '',
    ciudad: '',
    codigo_postal: ''
  });

  const [materialForm, setMaterialForm] = useState({
    nombre: '',
    cantidad: 1,
    precio_unitario: 0,
    coste: 0,
    iva: 21,
    descuento: 0
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [clientesRes, repuestosRes, kitsRes] = await Promise.all([
          clientesAPI.listar(),
          repuestosAPI.listar({ page_size: 200 }),
          api.get('/kits?activo=true')
        ]);
        setClientes(clientesRes.data);
        setRepuestos(repuestosRes.data.items || []);
        setKits(kitsRes.data.items || []);
      } catch (error) {
        toast.error('Error al cargar datos');
      }
    };
    fetchData();
  }, []);

  // Búsqueda dinámica de materiales con debounce
  useEffect(() => {
    const searchTimer = setTimeout(async () => {
      if (searchQuery.length >= 2) {
        setSearchLoading(true);
        try {
          const res = await api.get(`/repuestos/buscar/rapido?q=${encodeURIComponent(searchQuery)}&limit=50`);
          setSearchResults(res.data || []);
        } catch (error) {
          console.error('Error searching:', error);
          setSearchResults([]);
        } finally {
          setSearchLoading(false);
        }
      } else {
        setSearchResults([]);
      }
    }, 300);
    
    return () => clearTimeout(searchTimer);
  }, [searchQuery]);

  const handleInputChange = (field, value) => {
    if (field.includes('.')) {
      const [parent, child] = field.split('.');
      setFormData(prev => ({
        ...prev,
        [parent]: {
          ...prev[parent],
          [child]: value
        }
      }));
    } else {
      setFormData(prev => ({ ...prev, [field]: value }));
    }
  };

  const handleNuevoClienteChange = (field, value) => {
    setNuevoCliente(prev => ({ ...prev, [field]: value }));
  };

  const handleCrearCliente = async () => {
    try {
      const res = await clientesAPI.crear(nuevoCliente);
      setClientes(prev => [...prev, res.data]);
      setClienteSeleccionado(res.data);
      setShowNuevoCliente(false);
      setNuevoCliente({
        nombre: '', apellidos: '', dni: '', telefono: '', email: '',
        direccion: '', planta: '', puerta: '', ciudad: '', codigo_postal: ''
      });
      toast.success('Cliente creado');
    } catch (error) {
      toast.error('Error al crear cliente');
    }
  };

  const handleAddMaterial = (repuesto) => {
    const existe = materialesSeleccionados.find(m => m.repuesto_id === repuesto.id);
    if (existe) {
      setMaterialesSeleccionados(prev => 
        prev.map(m => m.repuesto_id === repuesto.id 
          ? { ...m, cantidad: m.cantidad + 1 }
          : m
        )
      );
    } else {
      setMaterialesSeleccionados(prev => [...prev, {
        repuesto_id: repuesto.id,
        nombre: repuesto.nombre,
        cantidad: 1,
        precio_unitario: repuesto.precio_venta || 0,
        coste: repuesto.precio_coste || 0,
        iva: 21,
        descuento: 0,
        añadido_por_tecnico: false,
        aprobado: true
      }]);
    }
    setOpenMaterialSearch(false);
  };

  const handleAddKit = async (kit) => {
    try {
      // Expandir el kit para obtener sus líneas
      const res = await api.post(`/kits/${kit.id}/expandir`, null, { params: { cantidad: 1 } });
      const lineas = res.data.lineas || [];
      
      // Convertir las líneas del kit a materiales
      const nuevosMateriales = lineas.map(linea => ({
        repuesto_id: linea.repuesto_id || null,
        nombre: linea.descripcion || `[${linea.tipo}]`,
        cantidad: linea.cantidad || 1,
        precio_unitario: linea.precio_unitario || 0,
        coste: 0,
        iva: linea.iva_porcentaje || 21,
        descuento: linea.descuento || 0,
        añadido_por_tecnico: false,
        aprobado: true,
        kit_origen: kit.nombre,
        tipo_componente: linea.tipo
      }));
      
      setMaterialesSeleccionados(prev => [...prev, ...nuevosMateriales]);
      setOpenKitSearch(false);
      toast.success(`Kit "${kit.nombre}" añadido (${nuevosMateriales.length} líneas)`);
    } catch (error) {
      toast.error('Error al añadir el kit');
      console.error(error);
    }
  };

  const handleAddMaterialPersonalizado = () => {
    if (!materialForm.nombre.trim()) {
      toast.error('El nombre del material es obligatorio');
      return;
    }
    
    setMaterialesSeleccionados(prev => [...prev, {
      repuesto_id: null, // Material personalizado
      nombre: materialForm.nombre,
      cantidad: materialForm.cantidad || 1,
      precio_unitario: parseFloat(materialForm.precio_unitario) || 0,
      coste: parseFloat(materialForm.coste) || 0,
      iva: parseFloat(materialForm.iva) || 21,
      descuento: parseFloat(materialForm.descuento) || 0,
      añadido_por_tecnico: false,
      aprobado: true
    }]);
    
    setMaterialForm({ nombre: '', cantidad: 1, precio_unitario: 0, coste: 0, iva: 21, descuento: 0 });
    setShowMaterialPersonalizado(false);
    toast.success('Material añadido');
  };

  const handleEditMaterial = (index) => {
    const material = materialesSeleccionados[index];
    setMaterialForm({
      nombre: material.nombre,
      cantidad: material.cantidad,
      precio_unitario: material.precio_unitario,
      coste: material.coste || 0,
      iva: material.iva || 21,
      descuento: material.descuento || 0
    });
    setEditingMaterialIndex(index);
    setShowEditarMaterial(true);
  };

  const handleSaveEditMaterial = () => {
    if (editingMaterialIndex === null) return;
    
    setMaterialesSeleccionados(prev => prev.map((m, i) => {
      if (i === editingMaterialIndex) {
        return {
          ...m,
          nombre: materialForm.nombre || m.nombre,
          cantidad: parseInt(materialForm.cantidad) || 1,
          precio_unitario: parseFloat(materialForm.precio_unitario) || 0,
          coste: parseFloat(materialForm.coste) || 0,
          iva: parseFloat(materialForm.iva) || 21,
          descuento: parseFloat(materialForm.descuento) || 0
        };
      }
      return m;
    }));
    
    setShowEditarMaterial(false);
    setEditingMaterialIndex(null);
    setMaterialForm({ nombre: '', cantidad: 1, precio_unitario: 0, coste: 0, iva: 21, descuento: 0 });
    toast.success('Material actualizado');
  };

  const handleRemoveMaterial = (index) => {
    setMaterialesSeleccionados(prev => prev.filter((_, i) => i !== index));
    toast.success('Material eliminado');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!clienteSeleccionado) {
      toast.error('Selecciona un cliente');
      return;
    }
    
    if (!formData.dispositivo.modelo || !formData.dispositivo.daños) {
      toast.error('Completa los datos del dispositivo');
      return;
    }
    
    if (!formData.agencia_envio) {
      toast.error('Selecciona un transportista');
      return;
    }
    
    // Solo requerir código de recogida si NO es GLS (GLS se genera desde la orden)
    if (formData.agencia_envio !== 'GLS' && !formData.codigo_recogida_entrada) {
      toast.error('Introduce el código de recogida');
      return;
    }

    try {
      setLoading(true);
      const ordenData = {
        cliente_id: clienteSeleccionado.id,
        dispositivo: formData.dispositivo,
        agencia_envio: formData.agencia_envio,
        codigo_recogida_entrada: formData.codigo_recogida_entrada,
        numero_autorizacion: formData.numero_autorizacion || null,
        materiales: materialesSeleccionados,
        notas: formData.notas
      };
      
      const res = await ordenesAPI.crear(ordenData);
      if (formData.agencia_envio === 'GLS') {
        toast.success('Orden creada. Genera la recogida GLS desde el detalle de la orden.');
      } else {
        toast.success('Orden creada correctamente');
      }
      navigate(`/crm/ordenes/${res.data.id}`);
    } catch (error) {
      toast.error('Error al crear la orden');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // Calcular totales con descuento
  const calcularPrecioConDescuento = (material) => {
    const subtotal = material.precio_unitario * material.cantidad;
    const descuentoValor = subtotal * ((material.descuento || 0) / 100);
    return subtotal - descuentoValor;
  };

  const totalMateriales = materialesSeleccionados.reduce(
    (acc, m) => acc + calcularPrecioConDescuento(m), 0
  );

  return (
    <div className="space-y-6 animate-fade-in" data-testid="nueva-orden-page">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Nueva Orden</h1>
          <p className="text-muted-foreground mt-1">Crea una nueva orden de trabajo</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column - Main form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Cliente Section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5" />
                Cliente
              </CardTitle>
            </CardHeader>
            <CardContent>
              {clienteSeleccionado ? (
                <div className="p-4 bg-slate-50 rounded-lg border">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-semibold">{clienteSeleccionado.nombre} {clienteSeleccionado.apellidos}</p>
                      <p className="text-sm text-muted-foreground">{clienteSeleccionado.dni}</p>
                      <p className="text-sm text-muted-foreground">{clienteSeleccionado.telefono}</p>
                      <p className="text-sm text-muted-foreground">{clienteSeleccionado.direccion}</p>
                    </div>
                    <Button 
                      type="button"
                      variant="ghost" 
                      size="sm"
                      onClick={() => setClienteSeleccionado(null)}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex gap-2">
                  <Popover open={openClienteSearch} onOpenChange={setOpenClienteSearch}>
                    <PopoverTrigger asChild>
                      <Button type="button" variant="outline" className="flex-1 justify-start">
                        <Search className="w-4 h-4 mr-2" />
                        Buscar cliente...
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-80 p-0" align="start">
                      <Command>
                        <CommandInput placeholder="Buscar por nombre, DNI..." />
                        <CommandList>
                          <CommandEmpty>No se encontraron clientes</CommandEmpty>
                          <CommandGroup>
                            {clientes.map((cliente) => (
                              <CommandItem
                                key={cliente.id}
                                onSelect={() => {
                                  setClienteSeleccionado(cliente);
                                  setOpenClienteSearch(false);
                                }}
                              >
                                <div>
                                  <p className="font-medium">{cliente.nombre} {cliente.apellidos}</p>
                                  <p className="text-sm text-muted-foreground">{cliente.dni} - {cliente.telefono}</p>
                                </div>
                              </CommandItem>
                            ))}
                          </CommandGroup>
                        </CommandList>
                      </Command>
                    </PopoverContent>
                  </Popover>
                  
                  <Dialog open={showNuevoCliente} onOpenChange={setShowNuevoCliente}>
                    <DialogTrigger asChild>
                      <Button type="button" variant="secondary">
                        <Plus className="w-4 h-4 mr-2" />
                        Nuevo
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-2xl">
                      <DialogHeader>
                        <DialogTitle>Nuevo Cliente</DialogTitle>
                      </DialogHeader>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label>Nombre *</Label>
                          <Input 
                            value={nuevoCliente.nombre}
                            onChange={(e) => handleNuevoClienteChange('nombre', e.target.value)}
                          />
                        </div>
                        <div>
                          <Label>Apellidos *</Label>
                          <Input 
                            value={nuevoCliente.apellidos}
                            onChange={(e) => handleNuevoClienteChange('apellidos', e.target.value)}
                          />
                        </div>
                        <div>
                          <Label>DNI *</Label>
                          <Input 
                            value={nuevoCliente.dni}
                            onChange={(e) => handleNuevoClienteChange('dni', e.target.value)}
                          />
                        </div>
                        <div>
                          <Label>Teléfono *</Label>
                          <Input 
                            value={nuevoCliente.telefono}
                            onChange={(e) => handleNuevoClienteChange('telefono', e.target.value)}
                          />
                        </div>
                        <div className="col-span-2">
                          <Label>Email</Label>
                          <Input 
                            type="email"
                            value={nuevoCliente.email}
                            onChange={(e) => handleNuevoClienteChange('email', e.target.value)}
                          />
                        </div>
                        <div className="col-span-2">
                          <Label>Dirección *</Label>
                          <Input 
                            value={nuevoCliente.direccion}
                            onChange={(e) => handleNuevoClienteChange('direccion', e.target.value)}
                          />
                        </div>
                        <div>
                          <Label>Planta</Label>
                          <Input 
                            value={nuevoCliente.planta}
                            onChange={(e) => handleNuevoClienteChange('planta', e.target.value)}
                          />
                        </div>
                        <div>
                          <Label>Puerta</Label>
                          <Input 
                            value={nuevoCliente.puerta}
                            onChange={(e) => handleNuevoClienteChange('puerta', e.target.value)}
                          />
                        </div>
                        <div>
                          <Label>Ciudad</Label>
                          <Input 
                            value={nuevoCliente.ciudad}
                            onChange={(e) => handleNuevoClienteChange('ciudad', e.target.value)}
                          />
                        </div>
                        <div>
                          <Label>Código Postal</Label>
                          <Input 
                            value={nuevoCliente.codigo_postal}
                            onChange={(e) => handleNuevoClienteChange('codigo_postal', e.target.value)}
                          />
                        </div>
                      </div>
                      <div className="flex justify-end gap-2 mt-4">
                        <Button type="button" variant="outline" onClick={() => setShowNuevoCliente(false)}>
                          Cancelar
                        </Button>
                        <Button type="button" onClick={handleCrearCliente}>
                          Crear Cliente
                        </Button>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Dispositivo Section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Smartphone className="w-5 h-5" />
                Dispositivo
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label>Modelo *</Label>
                  <Input 
                    value={formData.dispositivo.modelo}
                    onChange={(e) => handleInputChange('dispositivo.modelo', e.target.value)}
                    placeholder="iPhone 15 Pro Max"
                    data-testid="input-modelo"
                  />
                </div>
                <div>
                  <Label>IMEI</Label>
                  <Input 
                    value={formData.dispositivo.imei}
                    onChange={(e) => handleInputChange('dispositivo.imei', e.target.value)}
                    placeholder="123456789012345"
                    className="font-mono"
                    data-testid="input-imei"
                  />
                </div>
                <div>
                  <Label>Color</Label>
                  <Input 
                    value={formData.dispositivo.color}
                    onChange={(e) => handleInputChange('dispositivo.color', e.target.value)}
                    placeholder="Negro Titanio"
                    data-testid="input-color"
                  />
                </div>
                <div className="sm:col-span-2">
                  <Label>Daños / Avería *</Label>
                  <Textarea 
                    value={formData.dispositivo.daños}
                    onChange={(e) => handleInputChange('dispositivo.daños', e.target.value)}
                    placeholder="Descripción detallada de los daños o avería..."
                    rows={3}
                    data-testid="input-daños"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Envío Section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Truck className="w-5 h-5" />
                Datos de Envío y Autorización
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="sm:col-span-2">
                  <Label>Número de Autorización</Label>
                  <Input 
                    value={formData.numero_autorizacion}
                    onChange={(e) => handleInputChange('numero_autorizacion', e.target.value)}
                    placeholder="AUTH-0001"
                    className="font-mono text-lg font-bold"
                    data-testid="input-autorizacion"
                  />
                  <p className="text-xs text-muted-foreground mt-1">Número interno de autorización del servicio</p>
                </div>
                <div>
                  <Label>Transportista / Agencia *</Label>
                  <Select value={formData.agencia_envio} onValueChange={(v) => handleInputChange('agencia_envio', v)}>
                    <SelectTrigger data-testid="select-agencia">
                      <SelectValue placeholder="Selecciona transportista" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="GLS">GLS (Recogida automática)</SelectItem>
                      <SelectItem value="mrw">MRW</SelectItem>
                      <SelectItem value="seur">SEUR</SelectItem>
                      <SelectItem value="otro">Otro / Manual</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  {formData.agencia_envio === 'GLS' ? (
                    <>
                      <Label>Recogida GLS</Label>
                      <div className="flex items-center gap-2 h-10 px-3 rounded-md border bg-blue-50 border-blue-200 text-sm text-blue-700" data-testid="gls-pickup-notice">
                        <Truck className="w-4 h-4" />
                        Se generará desde la orden con GLS
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">La recogida se tramitará desde el detalle de la orden</p>
                    </>
                  ) : (
                    <>
                      <Label>Código de Recogida (Entrada)</Label>
                      <Input 
                        value={formData.codigo_recogida_entrada}
                        onChange={(e) => handleInputChange('codigo_recogida_entrada', e.target.value)}
                        placeholder="Código de tracking de entrada"
                        className="font-mono"
                        data-testid="input-codigo-entrada"
                      />
                    </>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Notas Section */}
          <Card>
            <CardHeader>
              <CardTitle>Notas Adicionales</CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea 
                value={formData.notas}
                onChange={(e) => handleInputChange('notas', e.target.value)}
                placeholder="Observaciones adicionales..."
                rows={3}
              />
            </CardContent>
          </Card>
        </div>

        {/* Right column - Materials and Summary */}
        <div className="space-y-6">
          {/* Materiales Section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Package className="w-5 h-5" />
                Materiales / Partidas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2 mb-4">
                {/* Botón para abrir modal de búsqueda expandida */}
                <Button 
                  type="button" 
                  variant="outline" 
                  className="flex-1 justify-start"
                  onClick={() => {
                    setSearchQuery('');
                    setSearchResults([]);
                    setShowBuscarMaterial(true);
                  }}
                  data-testid="btn-buscar-material"
                >
                  <Search className="w-4 h-4 mr-2" />
                  Del inventario...
                </Button>
                
                <Button 
                  type="button" 
                  variant="secondary"
                  onClick={() => setShowMaterialPersonalizado(true)}
                  data-testid="add-material-personalizado-btn"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Manual
                </Button>
                
                {/* Selector de Kits */}
                {kits.length > 0 && (
                  <Popover open={openKitSearch} onOpenChange={setOpenKitSearch}>
                    <PopoverTrigger asChild>
                      <Button type="button" variant="default" className="bg-purple-600 hover:bg-purple-700">
                        <Layers className="w-4 h-4 mr-2" />
                        Kit
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-80 p-0" align="start">
                      <Command>
                        <CommandInput placeholder="Buscar kit..." />
                        <CommandList>
                          <CommandEmpty>No hay kits disponibles</CommandEmpty>
                          <CommandGroup heading="Kits Disponibles">
                            {kits.map((kit) => (
                              <CommandItem
                                key={kit.id}
                                onSelect={() => handleAddKit(kit)}
                              >
                                <Layers className="w-4 h-4 mr-2 text-purple-600" />
                                <div className="flex-1">
                                  <p className="font-medium">{kit.nombre}</p>
                                  <p className="text-sm text-muted-foreground">
                                    {kit.num_componentes} componentes • €{kit.total?.toFixed(2)}
                                  </p>
                                </div>
                              </CommandItem>
                            ))}
                          </CommandGroup>
                        </CommandList>
                      </Command>
                    </PopoverContent>
                  </Popover>
                )}
              </div>

              {materialesSeleccionados.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No hay materiales añadidos
                </p>
              ) : (
                <div className="space-y-2">
                  {materialesSeleccionados.map((material, index) => (
                    <div 
                      key={index}
                      className={`p-3 rounded-lg border ${material.kit_origen ? 'bg-purple-50 border-purple-200' : 'bg-slate-50'}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium">{material.nombre}</p>
                          <p className="text-xs text-muted-foreground">
                            {material.cantidad} x €{material.precio_unitario.toFixed(2)}
                            {material.descuento > 0 && (
                              <span className="text-green-600 ml-1">(-{material.descuento}%)</span>
                            )}
                          </p>
                          <div className="flex gap-1 mt-1">
                            {material.kit_origen && (
                              <Badge variant="outline" className="text-[10px] bg-purple-100 text-purple-700 border-purple-300">
                                <Layers className="w-2 h-2 mr-1" />
                                {material.kit_origen}
                              </Badge>
                            )}
                            {!material.repuesto_id && !material.kit_origen && (
                              <Badge variant="outline" className="text-[10px]">Personalizado</Badge>
                            )}
                            {material.tipo_componente && material.tipo_componente !== 'producto' && (
                              <Badge variant="secondary" className="text-[10px]">{material.tipo_componente}</Badge>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <Badge variant="secondary">
                            €{calcularPrecioConDescuento(material).toFixed(2)}
                          </Badge>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEditMaterial(index)}
                          >
                            <Edit className="w-3 h-3" />
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="text-red-500 hover:text-red-600"
                            onClick={() => handleRemoveMaterial(index)}
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Resumen Section */}
          <Card>
            <CardHeader>
              <CardTitle>Resumen</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Materiales ({materialesSeleccionados.length}):</span>
                  <span>€{totalMateriales.toFixed(2)}</span>
                </div>
                <div className="border-t pt-3 flex justify-between font-semibold">
                  <span>Total:</span>
                  <span className="text-lg">€{totalMateriales.toFixed(2)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Submit Button */}
          <Button 
            type="submit" 
            className="w-full h-12"
            disabled={loading}
            data-testid="submit-orden-btn"
          >
            {loading ? 'Creando...' : 'Crear Orden de Trabajo'}
          </Button>
        </div>
      </form>

      {/* Modal Material Personalizado */}
      <Dialog open={showMaterialPersonalizado} onOpenChange={setShowMaterialPersonalizado}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Añadir Material Personalizado</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Nombre del material *</Label>
              <Input
                value={materialForm.nombre}
                onChange={(e) => setMaterialForm(prev => ({ ...prev, nombre: e.target.value }))}
                placeholder="Ej: Pantalla LCD genérica"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Cantidad</Label>
                <Input
                  type="number"
                  min="1"
                  value={materialForm.cantidad}
                  onChange={(e) => setMaterialForm(prev => ({ ...prev, cantidad: parseInt(e.target.value) || 1 }))}
                />
              </div>
              <div>
                <Label>Precio Unitario (€)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={materialForm.precio_unitario}
                  onChange={(e) => setMaterialForm(prev => ({ ...prev, precio_unitario: e.target.value }))}
                />
              </div>
              <div>
                <Label>Coste (€)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={materialForm.coste}
                  onChange={(e) => setMaterialForm(prev => ({ ...prev, coste: e.target.value }))}
                />
              </div>
              <div>
                <Label>IVA (%)</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  value={materialForm.iva}
                  onChange={(e) => setMaterialForm(prev => ({ ...prev, iva: e.target.value }))}
                />
              </div>
              <div className="col-span-2">
                <Label className="flex items-center gap-1">
                  <Percent className="w-3 h-3" />
                  Descuento (%)
                </Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  value={materialForm.descuento}
                  onChange={(e) => setMaterialForm(prev => ({ ...prev, descuento: e.target.value }))}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowMaterialPersonalizado(false)}>
              Cancelar
            </Button>
            <Button onClick={handleAddMaterialPersonalizado}>
              Añadir Material
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal Editar Material */}
      <Dialog open={showEditarMaterial} onOpenChange={setShowEditarMaterial}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Material</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Nombre</Label>
              <Input
                value={materialForm.nombre}
                onChange={(e) => setMaterialForm(prev => ({ ...prev, nombre: e.target.value }))}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Cantidad</Label>
                <Input
                  type="number"
                  min="1"
                  value={materialForm.cantidad}
                  onChange={(e) => setMaterialForm(prev => ({ ...prev, cantidad: parseInt(e.target.value) || 1 }))}
                />
              </div>
              <div>
                <Label>Precio Unitario (€)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={materialForm.precio_unitario}
                  onChange={(e) => setMaterialForm(prev => ({ ...prev, precio_unitario: e.target.value }))}
                />
              </div>
              <div>
                <Label>Coste (€)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={materialForm.coste}
                  onChange={(e) => setMaterialForm(prev => ({ ...prev, coste: e.target.value }))}
                />
              </div>
              <div>
                <Label>IVA (%)</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  value={materialForm.iva}
                  onChange={(e) => setMaterialForm(prev => ({ ...prev, iva: e.target.value }))}
                />
              </div>
              <div className="col-span-2">
                <Label className="flex items-center gap-1">
                  <Percent className="w-3 h-3" />
                  Descuento (%)
                </Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  value={materialForm.descuento}
                  onChange={(e) => setMaterialForm(prev => ({ ...prev, descuento: e.target.value }))}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditarMaterial(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSaveEditMaterial}>
              Guardar Cambios
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal de búsqueda de materiales expandido */}
      <Dialog open={showBuscarMaterial} onOpenChange={setShowBuscarMaterial}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="w-5 h-5" />
              Buscar Material del Inventario
            </DialogTitle>
          </DialogHeader>
          
          {/* Buscador */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Escribe para buscar... (mínimo 2 caracteres)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
              autoFocus
              data-testid="input-buscar-material"
            />
          </div>
          
          {/* Resultados */}
          <div className="flex-1 overflow-y-auto min-h-[300px] border rounded-lg">
            {searchLoading ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-muted-foreground">Buscando...</span>
              </div>
            ) : searchQuery.length < 2 ? (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                <Search className="w-12 h-12 mb-2 opacity-30" />
                <p>Escribe al menos 2 caracteres para buscar</p>
              </div>
            ) : searchResults.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                <Package className="w-12 h-12 mb-2 opacity-30" />
                <p>No se encontraron materiales para "{searchQuery}"</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Producto</TableHead>
                    <TableHead className="w-24 text-center">Stock</TableHead>
                    <TableHead className="w-24 text-right">Precio</TableHead>
                    <TableHead className="w-20"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {searchResults.map((repuesto) => (
                    <TableRow key={repuesto.id} className="cursor-pointer hover:bg-slate-50">
                      <TableCell>
                        <div>
                          <p className="font-medium">{repuesto.nombre}</p>
                          {repuesto.nombre_es && repuesto.nombre_es !== repuesto.nombre && (
                            <p className="text-xs text-muted-foreground">{repuesto.nombre_es}</p>
                          )}
                          <div className="flex gap-1 mt-1">
                            {repuesto.sku && (
                              <Badge variant="outline" className="text-xs">SKU: {repuesto.sku}</Badge>
                            )}
                            {repuesto.proveedor && (
                              <Badge variant="secondary" className="text-xs">{repuesto.proveedor}</Badge>
                            )}
                            {repuesto.calidad_pantalla && (
                              <Badge className="text-xs bg-blue-100 text-blue-800">{repuesto.calidad_pantalla}</Badge>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge variant={repuesto.stock > 0 ? "default" : "secondary"}>
                          {repuesto.stock || 0}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        €{(repuesto.precio_venta || 0).toFixed(2)}
                      </TableCell>
                      <TableCell>
                        <Button
                          size="sm"
                          variant={repuesto.stock > 0 ? "default" : "outline"}
                          onClick={() => {
                            handleAddMaterial(repuesto);
                            setShowBuscarMaterial(false);
                            setSearchQuery('');
                          }}
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
          
          {/* Footer con contador */}
          <div className="flex items-center justify-between pt-2 border-t">
            <span className="text-sm text-muted-foreground">
              {searchResults.length > 0 && `${searchResults.length} resultados`}
            </span>
            <Button variant="outline" onClick={() => setShowBuscarMaterial(false)}>
              Cerrar
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

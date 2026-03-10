import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import api from '../lib/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '../components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../components/ui/popover';
import { toast } from 'sonner';
import { 
  ArrowLeft, Save, Send, Trash2, Plus, Euro, CreditCard,
  CheckCircle, Clock, XCircle, AlertTriangle, Printer, UserPlus,
  Layers
} from 'lucide-react';

const estadoColors = {
  borrador: 'bg-gray-100 text-gray-800',
  emitida: 'bg-blue-100 text-blue-800',
  pagada: 'bg-green-100 text-green-800',
  parcial: 'bg-yellow-100 text-yellow-800',
  vencida: 'bg-red-100 text-red-800',
  anulada: 'bg-gray-300 text-gray-600'
};

const tiposIVA = [
  { value: 'general', label: '21% - General', porcentaje: 21 },
  { value: 'reducido', label: '10% - Reducido', porcentaje: 10 },
  { value: 'superreducido', label: '4% - Superreducido', porcentaje: 4 },
  { value: 'exento', label: '0% - Exento', porcentaje: 0 }
];

const metodosPago = [
  { value: 'efectivo', label: 'Efectivo' },
  { value: 'tarjeta', label: 'Tarjeta' },
  { value: 'transferencia', label: 'Transferencia' },
  { value: 'bizum', label: 'Bizum' },
  { value: 'domiciliacion', label: 'Domiciliación' },
  { value: 'pagare', label: 'Pagaré' }
];

export default function FacturaDetalle() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const isNew = id === 'nueva';
  const tipoInicial = searchParams.get('tipo') || 'venta';

  const [factura, setFactura] = useState({
    tipo: tipoInicial,
    nombre_fiscal: '',
    nif_cif: '',
    direccion_fiscal: '',
    lineas: [],
    notas: '',
    metodo_pago: 'transferencia',
    inversion_sujeto_pasivo: false,
    fecha_vencimiento: ''
  });
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [clientes, setClientes] = useState([]);
  const [showPagoModal, setShowPagoModal] = useState(false);
  const [pagoData, setPagoData] = useState({ importe: 0, metodo: 'transferencia', referencia: '' });
  const [clienteNoRegistrado, setClienteNoRegistrado] = useState(false);
  const [datosClienteNuevo, setDatosClienteNuevo] = useState({
    email: '',
    telefono: ''
  });
  const [guardandoCliente, setGuardandoCliente] = useState(false);
  
  // Kits
  const [kits, setKits] = useState([]);
  const [openKitSearch, setOpenKitSearch] = useState(false);

  useEffect(() => {
    if (!isNew) {
      cargarFactura();
    }
    cargarClientes();
    cargarKits();
  }, [id]);

  const cargarFactura = async () => {
    try {
      const res = await api.get(`/contabilidad/facturas/${id}`);
      setFactura(res.data);
      setPagoData({ ...pagoData, importe: res.data.pendiente_cobro || 0 });
    } catch (error) {
      toast.error('Error al cargar factura');
      navigate('/contabilidad');
    } finally {
      setLoading(false);
    }
  };

  const cargarClientes = async () => {
    try {
      const res = await api.get('/clientes');
      setClientes(res.data || []);
    } catch (error) {
      console.error('Error cargando clientes:', error);
    }
  };

  const cargarKits = async () => {
    try {
      const res = await api.get('/kits?activo=true');
      setKits(res.data.items || []);
    } catch (error) {
      console.error('Error cargando kits:', error);
    }
  };

  const handleAddKit = async (kit) => {
    try {
      // Expandir el kit para obtener sus líneas
      const res = await api.post(`/kits/${kit.id}/expandir`, null, { params: { cantidad: 1 } });
      const lineasKit = res.data.lineas || [];
      
      // Convertir las líneas del kit a líneas de factura
      const nuevasLineas = lineasKit.map(linea => ({
        descripcion: linea.descripcion || linea.nombre,
        cantidad: linea.cantidad || 1,
        precio_unitario: linea.precio_unitario || 0,
        descuento: linea.descuento || 0,
        tipo_iva: linea.iva_porcentaje === 21 ? 'general' : 
                  linea.iva_porcentaje === 10 ? 'reducido' : 
                  linea.iva_porcentaje === 4 ? 'superreducido' : 'exento',
        iva_porcentaje: linea.iva_porcentaje || 21,
        kit_origen: kit.nombre
      }));
      
      setFactura({ ...factura, lineas: [...factura.lineas, ...nuevasLineas] });
      setOpenKitSearch(false);
      toast.success(`Kit "${kit.nombre}" añadido (${nuevasLineas.length} líneas)`);
    } catch (error) {
      toast.error('Error al añadir el kit');
    }
  };

  const calcularTotales = () => {
    let base = 0;
    let iva = 0;
    factura.lineas.forEach(linea => {
      const subtotal = (linea.cantidad || 1) * (linea.precio_unitario || 0) * (1 - (linea.descuento || 0) / 100);
      const ivaLinea = subtotal * (linea.iva_porcentaje || 21) / 100;
      base += subtotal;
      iva += ivaLinea;
    });
    return { base: Math.round(base * 100) / 100, iva: Math.round(iva * 100) / 100, total: Math.round((base + iva) * 100) / 100 };
  };

  const agregarLinea = () => {
    setFactura({
      ...factura,
      lineas: [...factura.lineas, {
        descripcion: '',
        cantidad: 1,
        precio_unitario: 0,
        descuento: 0,
        tipo_iva: 'general',
        iva_porcentaje: 21
      }]
    });
  };

  const actualizarLinea = (index, campo, valor) => {
    const nuevasLineas = [...factura.lineas];
    nuevasLineas[index][campo] = valor;
    
    // Si cambia el tipo de IVA, actualizar porcentaje
    if (campo === 'tipo_iva') {
      const tipoIva = tiposIVA.find(t => t.value === valor);
      nuevasLineas[index].iva_porcentaje = tipoIva?.porcentaje || 21;
    }
    
    setFactura({ ...factura, lineas: nuevasLineas });
  };

  const eliminarLinea = (index) => {
    setFactura({
      ...factura,
      lineas: factura.lineas.filter((_, i) => i !== index)
    });
  };

  const seleccionarCliente = (clienteId) => {
    const cliente = clientes.find(c => c.id === clienteId);
    if (cliente) {
      setFactura({
        ...factura,
        cliente_id: cliente.id,
        nombre_fiscal: cliente.nombre_fiscal || `${cliente.nombre || ''} ${cliente.apellidos || ''}`.trim(),
        nif_cif: cliente.dni || cliente.nif || '',
        direccion_fiscal: cliente.direccion || ''
      });
      setDatosClienteNuevo({
        email: cliente.email || '',
        telefono: cliente.telefono || ''
      });
    }
  };

  const guardarClienteNuevo = async () => {
    if (!factura.nombre_fiscal) {
      toast.error('El nombre fiscal es obligatorio');
      return;
    }

    setGuardandoCliente(true);
    try {
      // Separar nombre y apellidos si es posible
      const partes = factura.nombre_fiscal.trim().split(' ');
      const nombre = partes[0] || '';
      const apellidos = partes.slice(1).join(' ') || '';

      const nuevoCliente = {
        nombre: nombre,
        apellidos: apellidos,
        nombre_fiscal: factura.nombre_fiscal,
        dni: factura.nif_cif || '',
        nif: factura.nif_cif || '',
        direccion: factura.direccion_fiscal || '',
        email: datosClienteNuevo.email || '',
        telefono: datosClienteNuevo.telefono || '',
        tipo: 'particular'
      };

      const res = await api.post('/clientes', nuevoCliente);
      
      // Actualizar factura con el ID del cliente creado
      setFactura({
        ...factura,
        cliente_id: res.data.id
      });
      
      // Añadir a la lista de clientes
      setClientes([...clientes, res.data]);
      
      // Desactivar modo cliente no registrado
      setClienteNoRegistrado(false);
      
      toast.success(`Cliente "${factura.nombre_fiscal}" guardado correctamente`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar el cliente');
    } finally {
      setGuardandoCliente(false);
    }
  };

  const guardarFactura = async () => {
    if (!factura.nombre_fiscal || !factura.nif_cif) {
      toast.error('Nombre fiscal y NIF/CIF son obligatorios');
      return;
    }
    if (factura.lineas.length === 0) {
      toast.error('Debe añadir al menos una línea');
      return;
    }

    setSaving(true);
    try {
      if (isNew) {
        const res = await api.post('/contabilidad/facturas', factura);
        toast.success(`Factura ${res.data.numero} creada`);
        navigate(`/contabilidad/factura/${res.data.id}`);
      } else {
        await api.patch(`/contabilidad/facturas/${id}`, {
          lineas: factura.lineas,
          notas: factura.notas,
          metodo_pago: factura.metodo_pago,
          fecha_vencimiento: factura.fecha_vencimiento
        });
        toast.success('Factura actualizada');
        cargarFactura();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  const emitirFactura = async () => {
    try {
      await api.post(`/contabilidad/facturas/${id}/emitir`);
      toast.success('Factura emitida correctamente');
      cargarFactura();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al emitir factura');
    }
  };

  const registrarPago = async () => {
    if (pagoData.importe <= 0) {
      toast.error('El importe debe ser mayor a 0');
      return;
    }
    try {
      await api.post('/contabilidad/pagos', {
        factura_id: id,
        importe: pagoData.importe,
        metodo: pagoData.metodo,
        referencia: pagoData.referencia
      });
      toast.success('Pago registrado');
      setShowPagoModal(false);
      cargarFactura();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al registrar pago');
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(amount || 0);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    return dateStr.split('T')[0];
  };

  const totales = calcularTotales();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="factura-detalle">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate('/contabilidad')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver
          </Button>
          <div>
            <h1 className="text-2xl font-bold">
              {isNew ? `Nueva Factura de ${factura.tipo === 'venta' ? 'Venta' : 'Compra'}` : factura.numero}
            </h1>
            {!isNew && (
              <Badge className={estadoColors[factura.estado]}>{factura.estado}</Badge>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          {!isNew && factura.estado === 'borrador' && (
            <Button variant="outline" onClick={emitirFactura}>
              <Send className="h-4 w-4 mr-2" />
              Emitir
            </Button>
          )}
          {!isNew && ['emitida', 'parcial', 'vencida'].includes(factura.estado) && (
            <Button variant="outline" onClick={() => setShowPagoModal(true)}>
              <CreditCard className="h-4 w-4 mr-2" />
              Registrar Pago
            </Button>
          )}
          <Button onClick={guardarFactura} disabled={saving}>
            <Save className="h-4 w-4 mr-2" />
            {saving ? 'Guardando...' : 'Guardar'}
          </Button>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {/* Datos fiscales */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Datos Fiscales</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {factura.tipo === 'venta' && isNew && (
              <div className="space-y-4">
                {/* Switch para cliente no registrado */}
                <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-2">
                    <UserPlus className="h-4 w-4 text-muted-foreground" />
                    <Label className="cursor-pointer">Cliente no registrado</Label>
                  </div>
                  <Switch
                    checked={clienteNoRegistrado}
                    onCheckedChange={(checked) => {
                      setClienteNoRegistrado(checked);
                      if (checked) {
                        // Limpiar datos si activa cliente no registrado
                        setFactura({
                          ...factura,
                          cliente_id: null,
                          nombre_fiscal: '',
                          nif_cif: '',
                          direccion_fiscal: ''
                        });
                        setDatosClienteNuevo({ email: '', telefono: '' });
                      }
                    }}
                  />
                </div>

                {/* Selector de clientes existentes */}
                {!clienteNoRegistrado && (
                  <div>
                    <Label>Seleccionar Cliente Existente</Label>
                    <Select onValueChange={seleccionarCliente} value={factura.cliente_id || ''}>
                      <SelectTrigger>
                        <SelectValue placeholder="Buscar cliente..." />
                      </SelectTrigger>
                      <SelectContent>
                        {clientes.map(cliente => (
                          <SelectItem key={cliente.id} value={cliente.id}>
                            {cliente.nombre} {cliente.apellidos} - {cliente.dni || 'Sin DNI'}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
            )}

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label>Nombre Fiscal *</Label>
                <Input
                  value={factura.nombre_fiscal}
                  onChange={(e) => setFactura({ ...factura, nombre_fiscal: e.target.value })}
                  placeholder="Nombre o razón social"
                  disabled={!isNew && factura.estado !== 'borrador'}
                />
              </div>
              <div>
                <Label>NIF/CIF *</Label>
                <Input
                  value={factura.nif_cif}
                  onChange={(e) => setFactura({ ...factura, nif_cif: e.target.value })}
                  placeholder="12345678A"
                  disabled={!isNew && factura.estado !== 'borrador'}
                />
              </div>
            </div>

            <div>
              <Label>Dirección Fiscal</Label>
              <Input
                value={factura.direccion_fiscal || ''}
                onChange={(e) => setFactura({ ...factura, direccion_fiscal: e.target.value })}
                placeholder="Calle, número, CP, ciudad"
                disabled={!isNew && factura.estado !== 'borrador'}
              />
            </div>

            {/* Campos adicionales para cliente no registrado */}
            {isNew && clienteNoRegistrado && (
              <div className="grid md:grid-cols-2 gap-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div>
                  <Label>Email</Label>
                  <Input
                    type="email"
                    value={datosClienteNuevo.email}
                    onChange={(e) => setDatosClienteNuevo({ ...datosClienteNuevo, email: e.target.value })}
                    placeholder="correo@ejemplo.com"
                  />
                </div>
                <div>
                  <Label>Teléfono</Label>
                  <Input
                    type="tel"
                    value={datosClienteNuevo.telefono}
                    onChange={(e) => setDatosClienteNuevo({ ...datosClienteNuevo, telefono: e.target.value })}
                    placeholder="600123456"
                  />
                </div>
                <div className="md:col-span-2">
                  <Button 
                    type="button" 
                    variant="outline" 
                    className="w-full"
                    onClick={guardarClienteNuevo}
                    disabled={guardandoCliente || !factura.nombre_fiscal}
                  >
                    <UserPlus className="h-4 w-4 mr-2" />
                    {guardandoCliente ? 'Guardando...' : 'Guardar como Cliente Nuevo'}
                  </Button>
                  <p className="text-xs text-muted-foreground mt-1 text-center">
                    Opcional: guarda los datos para futuras facturas
                  </p>
                </div>
              </div>
            )}

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label>Método de Pago</Label>
                <Select 
                  value={factura.metodo_pago} 
                  onValueChange={(v) => setFactura({ ...factura, metodo_pago: v })}
                  disabled={factura.estado === 'pagada'}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {metodosPago.map(m => (
                      <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Fecha Vencimiento</Label>
                <Input
                  type="date"
                  value={formatDate(factura.fecha_vencimiento)}
                  onChange={(e) => setFactura({ ...factura, fecha_vencimiento: e.target.value })}
                  disabled={factura.estado === 'pagada'}
                />
              </div>
            </div>

            {factura.tipo === 'compra' && (
              <div className="flex items-center gap-2 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                <Switch
                  checked={factura.inversion_sujeto_pasivo}
                  onCheckedChange={(v) => setFactura({ ...factura, inversion_sujeto_pasivo: v })}
                  disabled={!isNew && factura.estado !== 'borrador'}
                />
                <div>
                  <Label className="text-yellow-800">Inversión del Sujeto Pasivo</Label>
                  <p className="text-xs text-yellow-600">Marcar si el IVA no se paga en esta compra (intracomunitaria)</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Totales */}
        <Card>
          <CardHeader>
            <CardTitle>Totales</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">Base Imponible</span>
              <span className="font-medium">{formatCurrency(totales.base)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">IVA</span>
              <span className="font-medium">{formatCurrency(totales.iva)}</span>
            </div>
            <div className="flex justify-between border-t pt-3">
              <span className="font-semibold text-lg">Total</span>
              <span className="font-bold text-lg text-blue-600">{formatCurrency(totales.total)}</span>
            </div>
            
            {!isNew && factura.total_pagado > 0 && (
              <>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Pagado</span>
                  <span className="text-green-600">{formatCurrency(factura.total_pagado)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Pendiente</span>
                  <span className="text-orange-600 font-medium">{formatCurrency(factura.pendiente_cobro)}</span>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Líneas de factura */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Líneas</CardTitle>
          {(isNew || factura.estado === 'borrador') && (
            <div className="flex gap-2">
              {/* Selector de Kits */}
              {kits.length > 0 && (
                <Popover open={openKitSearch} onOpenChange={setOpenKitSearch}>
                  <PopoverTrigger asChild>
                    <Button variant="outline" size="sm" className="border-purple-200 text-purple-700 hover:bg-purple-50">
                      <Layers className="h-4 w-4 mr-2" />
                      Kit
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80 p-0" align="end">
                    <Command>
                      <CommandInput placeholder="Buscar kit..." />
                      <CommandList>
                        <CommandEmpty>No hay kits disponibles</CommandEmpty>
                        <CommandGroup heading="Kits Disponibles">
                          {kits.map((kit) => (
                            <CommandItem
                              key={kit.id}
                              onSelect={() => handleAddKit(kit)}
                              className="cursor-pointer"
                            >
                              <div className="flex flex-col">
                                <p className="font-medium">{kit.nombre}</p>
                                <p className="text-xs text-muted-foreground">
                                  {kit.num_componentes || kit.componentes?.length || 0} componentes • €{kit.precio_total?.toFixed(2) || kit.total?.toFixed(2) || '0.00'}
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
              <Button variant="outline" size="sm" onClick={agregarLinea}>
                <Plus className="h-4 w-4 mr-2" />
                Añadir Línea
              </Button>
            </div>
          )}
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-2 font-medium text-gray-600 w-1/3">Descripción</th>
                  <th className="text-right p-2 font-medium text-gray-600">Cantidad</th>
                  <th className="text-right p-2 font-medium text-gray-600">Precio</th>
                  <th className="text-right p-2 font-medium text-gray-600">Dto %</th>
                  <th className="text-center p-2 font-medium text-gray-600">IVA</th>
                  <th className="text-right p-2 font-medium text-gray-600">Subtotal</th>
                  <th className="p-2"></th>
                </tr>
              </thead>
              <tbody>
                {factura.lineas.map((linea, idx) => {
                  const subtotal = (linea.cantidad || 1) * (linea.precio_unitario || 0) * (1 - (linea.descuento || 0) / 100);
                  return (
                    <tr key={idx} className={`border-b ${linea.kit_origen ? 'bg-purple-50/50' : ''}`}>
                      <td className="p-2">
                        <div className="space-y-1">
                          <Input
                            value={linea.descripcion}
                            onChange={(e) => actualizarLinea(idx, 'descripcion', e.target.value)}
                            placeholder="Descripción del concepto"
                            disabled={factura.estado !== 'borrador' && !isNew}
                          />
                          {linea.kit_origen && (
                            <Badge variant="outline" className="text-xs text-purple-600 border-purple-300">
                              <Layers className="h-3 w-3 mr-1" />
                              {linea.kit_origen}
                            </Badge>
                          )}
                        </div>
                      </td>
                      <td className="p-2">
                        <Input
                          type="number"
                          value={linea.cantidad}
                          onChange={(e) => actualizarLinea(idx, 'cantidad', parseFloat(e.target.value) || 0)}
                          className="w-20 text-right"
                          disabled={factura.estado !== 'borrador' && !isNew}
                        />
                      </td>
                      <td className="p-2">
                        <Input
                          type="number"
                          step="0.01"
                          value={linea.precio_unitario}
                          onChange={(e) => actualizarLinea(idx, 'precio_unitario', parseFloat(e.target.value) || 0)}
                          className="w-24 text-right"
                          disabled={factura.estado !== 'borrador' && !isNew}
                        />
                      </td>
                      <td className="p-2">
                        <Input
                          type="number"
                          value={linea.descuento}
                          onChange={(e) => actualizarLinea(idx, 'descuento', parseFloat(e.target.value) || 0)}
                          className="w-16 text-right"
                          disabled={factura.estado !== 'borrador' && !isNew}
                        />
                      </td>
                      <td className="p-2">
                        <Select
                          value={linea.tipo_iva}
                          onValueChange={(v) => actualizarLinea(idx, 'tipo_iva', v)}
                          disabled={factura.estado !== 'borrador' && !isNew}
                        >
                          <SelectTrigger className="w-28">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {tiposIVA.map(t => (
                              <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </td>
                      <td className="p-2 text-right font-medium">
                        {formatCurrency(subtotal)}
                      </td>
                      <td className="p-2">
                        {(isNew || factura.estado === 'borrador') && (
                          <Button variant="ghost" size="sm" onClick={() => eliminarLinea(idx)}>
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {factura.lineas.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                No hay líneas. Haz clic en "Añadir Línea" para comenzar.
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Notas */}
      <Card>
        <CardHeader>
          <CardTitle>Notas</CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            value={factura.notas || ''}
            onChange={(e) => setFactura({ ...factura, notas: e.target.value })}
            placeholder="Notas adicionales para esta factura..."
            rows={3}
          />
        </CardContent>
      </Card>

      {/* Pagos registrados */}
      {!isNew && factura.pagos && factura.pagos.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Pagos Registrados</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {factura.pagos.map((pago, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                  <div>
                    <p className="font-medium text-green-800">{formatCurrency(pago.importe)}</p>
                    <p className="text-sm text-green-600">{pago.metodo} • {new Date(pago.fecha).toLocaleDateString('es-ES')}</p>
                    {pago.referencia && <p className="text-xs text-gray-500">Ref: {pago.referencia}</p>}
                  </div>
                  <CheckCircle className="h-5 w-5 text-green-600" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Modal Registrar Pago */}
      <Dialog open={showPagoModal} onOpenChange={setShowPagoModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Registrar Pago</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Importe</Label>
              <Input
                type="number"
                step="0.01"
                value={pagoData.importe}
                onChange={(e) => setPagoData({ ...pagoData, importe: parseFloat(e.target.value) || 0 })}
              />
              <p className="text-sm text-gray-500 mt-1">Pendiente: {formatCurrency(factura.pendiente_cobro)}</p>
            </div>
            <div>
              <Label>Método de Pago</Label>
              <Select value={pagoData.metodo} onValueChange={(v) => setPagoData({ ...pagoData, metodo: v })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {metodosPago.map(m => (
                    <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Referencia (opcional)</Label>
              <Input
                value={pagoData.referencia}
                onChange={(e) => setPagoData({ ...pagoData, referencia: e.target.value })}
                placeholder="Nº transferencia, concepto..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPagoModal(false)}>Cancelar</Button>
            <Button onClick={registrarPago}>
              <CreditCard className="h-4 w-4 mr-2" />
              Registrar Pago
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

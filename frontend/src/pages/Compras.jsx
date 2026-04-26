import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { 
  Upload, FileText, Package, CheckCircle, XCircle, AlertTriangle, 
  Plus, RefreshCw, Search, Eye, Truck, DollarSign, BarChart3,
  ArrowRight, Edit2, Trash2, History, QrCode, ShoppingCart
} from 'lucide-react';
import API from '@/lib/api';
import ListaComprasPanel from '@/components/compras/ListaComprasPanel';

export default function Compras() {
  const [activeTab, setActiveTab] = useState('lista');
  const [loading, setLoading] = useState(false);
  const [proveedores, setProveedores] = useState([]);
  const [compras, setCompras] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  
  // Estado para nueva compra
  const [archivo, setArchivo] = useState(null);
  const [datosExtraidos, setDatosExtraidos] = useState(null);
  const [archivoGuardado, setArchivoGuardado] = useState(null);
  const [procesando, setProcesando] = useState(false);
  const [editandoProducto, setEditandoProducto] = useState(null);
  
  const fileInputRef = useRef(null);

  useEffect(() => {
    cargarProveedores();
    cargarCompras();
    cargarDashboard();
  }, []);

  const cargarProveedores = async () => {
    try {
      const res = await API.get('/proveedores');
      setProveedores(res.data || []);
    } catch (err) {
      console.error('Error cargando proveedores:', err);
    }
  };

  const cargarCompras = async () => {
    try {
      const res = await API.get('/compras');
      setCompras(res.data.items || []);
    } catch (err) {
      console.error('Error cargando compras:', err);
    }
  };

  const cargarDashboard = async () => {
    try {
      const res = await API.get('/compras/dashboard/resumen?periodo=mes');
      setDashboard(res.data);
    } catch (err) {
      console.error('Error cargando dashboard:', err);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setArchivo(file);
      setDatosExtraidos(null);
    } else {
      toast.error('Solo se aceptan archivos PDF');
    }
  };

  const analizarFactura = async () => {
    if (!archivo) return;
    
    setProcesando(true);
    try {
      const formData = new FormData();
      formData.append('archivo', archivo);
      
      const res = await API.post('/compras/analizar-factura', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setDatosExtraidos(res.data.datos_extraidos);
      setArchivoGuardado(res.data.archivo_guardado);
      toast.success('Factura analizada correctamente');
    } catch (err) {
      console.error('Error analizando factura:', err);
      toast.error('Error al analizar la factura');
    } finally {
      setProcesando(false);
    }
  };

  const actualizarProducto = (index, campo, valor) => {
    const nuevosProductos = [...datosExtraidos.productos];
    nuevosProductos[index] = { ...nuevosProductos[index], [campo]: valor };
    setDatosExtraidos({ ...datosExtraidos, productos: nuevosProductos });
  };

  const confirmarCompra = async () => {
    if (!datosExtraidos) return;
    
    // Validar proveedor
    if (!datosExtraidos.proveedor_id) {
      toast.error('Selecciona un proveedor');
      return;
    }
    
    setLoading(true);
    try {
      const compraData = {
        proveedor_id: datosExtraidos.proveedor_id,
        numero_factura: datosExtraidos.numero_factura || 'SIN-NUMERO',
        fecha_factura: datosExtraidos.fecha_factura || new Date().toISOString().split('T')[0],
        productos: datosExtraidos.productos.map(p => ({
          descripcion: p.descripcion,
          codigo_referencia: p.codigo_referencia,
          cantidad: p.cantidad,
          precio_unitario: p.precio_unitario,
          accion: p.accion_sugerida,
          repuesto_id: p.repuesto_id
        })),
        base_imponible: datosExtraidos.base_imponible || 0,
        total_iva: datosExtraidos.total_iva || 0,
        total_factura: datosExtraidos.total_factura || 0,
        archivo_factura: archivoGuardado
      };
      
      const res = await API.post('/compras/confirmar', compraData);
      
      toast.success(`Compra registrada: ${res.data.resumen.productos_creados} productos creados, ${res.data.resumen.productos_actualizados} actualizados`);
      
      // Limpiar formulario
      setArchivo(null);
      setDatosExtraidos(null);
      setArchivoGuardado(null);
      
      // Recargar datos
      cargarCompras();
      cargarDashboard();
      
      // Cambiar a tab de historial
      setActiveTab('historial');
      
    } catch (err) {
      console.error('Error confirmando compra:', err);
      toast.error('Error al registrar la compra');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return (value || 0).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  return (
    <div className="space-y-6" data-testid="compras-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Gestión de Compras</h1>
          <p className="text-muted-foreground">Facturas, inventario y trazabilidad</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => { cargarCompras(); cargarDashboard(); }}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Actualizar
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="lista" className="flex items-center gap-2" data-testid="tab-lista-compras">
            <ShoppingCart className="w-4 h-4" />
            Lista pendiente
          </TabsTrigger>
          <TabsTrigger value="nueva" className="flex items-center gap-2">
            <Upload className="w-4 h-4" />
            Nueva Factura
          </TabsTrigger>
          <TabsTrigger value="historial" className="flex items-center gap-2">
            <History className="w-4 h-4" />
            Facturas
          </TabsTrigger>
          <TabsTrigger value="trazabilidad" className="flex items-center gap-2">
            <QrCode className="w-4 h-4" />
            Trazabilidad
          </TabsTrigger>
          <TabsTrigger value="dashboard" className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            Dashboard
          </TabsTrigger>
        </TabsList>

        {/* TAB LISTA DE COMPRAS PENDIENTES (nueva) */}
        <TabsContent value="lista" className="space-y-6">
          <ListaComprasPanel />
        </TabsContent>

        {/* TAB NUEVA COMPRA */}
        <TabsContent value="nueva" className="space-y-6">
          {!datosExtraidos ? (
            // Paso 1: Subir factura
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Subir Factura PDF
                </CardTitle>
                <CardDescription>
                  Sube la factura del proveedor y la IA extraerá los datos automáticamente
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div 
                  className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${archivo ? 'border-green-500 bg-green-50' : 'border-gray-300 hover:border-primary'}`}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileSelect}
                    accept=".pdf"
                    className="hidden"
                  />
                  {archivo ? (
                    <div className="space-y-2">
                      <CheckCircle className="w-12 h-12 mx-auto text-green-500" />
                      <p className="font-medium">{archivo.name}</p>
                      <p className="text-sm text-muted-foreground">{(archivo.size / 1024).toFixed(1)} KB</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Upload className="w-12 h-12 mx-auto text-gray-400" />
                      <p className="font-medium">Haz clic para seleccionar un archivo PDF</p>
                      <p className="text-sm text-muted-foreground">O arrastra y suelta aquí</p>
                    </div>
                  )}
                </div>

                {archivo && (
                  <div className="flex gap-2">
                    <Button onClick={analizarFactura} disabled={procesando} className="flex-1">
                      {procesando ? (
                        <>
                          <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                          Analizando con IA...
                        </>
                      ) : (
                        <>
                          <Search className="w-4 h-4 mr-2" />
                          Analizar Factura
                        </>
                      )}
                    </Button>
                    <Button variant="outline" onClick={() => setArchivo(null)}>
                      <XCircle className="w-4 h-4" />
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            // Paso 2: Revisar y confirmar datos extraídos
            <div className="space-y-4">
              {/* Información de confianza */}
              <Card className={datosExtraidos.confianza_extraccion >= 70 ? 'border-green-200 bg-green-50' : datosExtraidos.confianza_extraccion >= 40 ? 'border-amber-200 bg-amber-50' : 'border-red-200 bg-red-50'}>
                <CardContent className="py-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {datosExtraidos.confianza_extraccion >= 70 ? (
                        <CheckCircle className="w-5 h-5 text-green-600" />
                      ) : datosExtraidos.confianza_extraccion >= 40 ? (
                        <AlertTriangle className="w-5 h-5 text-amber-600" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-600" />
                      )}
                      <span className="font-medium">
                        Confianza de extracción: {datosExtraidos.confianza_extraccion}%
                      </span>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => { setDatosExtraidos(null); setArchivo(null); }}>
                      Subir otra factura
                    </Button>
                  </div>
                  {datosExtraidos.notas_extraccion && (
                    <p className="text-sm text-muted-foreground mt-1">{datosExtraidos.notas_extraccion}</p>
                  )}
                </CardContent>
              </Card>

              {/* Datos del proveedor y factura */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Datos de la Factura</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div>
                    <Label>Proveedor</Label>
                    <Select 
                      value={datosExtraidos.proveedor_id || ''} 
                      onValueChange={(v) => setDatosExtraidos({...datosExtraidos, proveedor_id: v})}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={datosExtraidos.proveedor_nombre || 'Seleccionar proveedor'} />
                      </SelectTrigger>
                      <SelectContent>
                        {proveedores.map(p => (
                          <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {datosExtraidos.proveedor_nombre && !datosExtraidos.proveedor_id && (
                      <p className="text-xs text-amber-600 mt-1">
                        Detectado: "{datosExtraidos.proveedor_nombre}" - Selecciona o crea el proveedor
                      </p>
                    )}
                  </div>
                  <div>
                    <Label>Nº Factura</Label>
                    <Input 
                      value={datosExtraidos.numero_factura || ''} 
                      onChange={(e) => setDatosExtraidos({...datosExtraidos, numero_factura: e.target.value})}
                    />
                  </div>
                  <div>
                    <Label>Fecha Factura</Label>
                    <Input 
                      type="date"
                      value={datosExtraidos.fecha_factura || ''} 
                      onChange={(e) => setDatosExtraidos({...datosExtraidos, fecha_factura: e.target.value})}
                    />
                  </div>
                  <div>
                    <Label>Total Factura</Label>
                    <Input 
                      type="number"
                      step="0.01"
                      value={datosExtraidos.total_factura || 0} 
                      onChange={(e) => setDatosExtraidos({...datosExtraidos, total_factura: parseFloat(e.target.value)})}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Lista de productos */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <Package className="w-5 h-5" />
                      Productos Detectados ({datosExtraidos.productos?.length || 0})
                    </span>
                  </CardTitle>
                  <CardDescription>
                    Revisa cada producto y confirma la acción a realizar
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-muted/50">
                          <th className="text-left py-2 px-3">Descripción</th>
                          <th className="text-left py-2 px-3">Ref.</th>
                          <th className="text-right py-2 px-3">Cant.</th>
                          <th className="text-right py-2 px-3">P. Unit.</th>
                          <th className="text-right py-2 px-3">Total</th>
                          <th className="text-center py-2 px-3">Stock Actual</th>
                          <th className="text-center py-2 px-3">Acción</th>
                        </tr>
                      </thead>
                      <tbody>
                        {datosExtraidos.productos?.map((producto, index) => (
                          <tr key={index} className="border-b hover:bg-muted/50">
                            <td className="py-2 px-3">
                              <Input 
                                value={producto.descripcion}
                                onChange={(e) => actualizarProducto(index, 'descripcion', e.target.value)}
                                className="h-8 text-sm"
                              />
                            </td>
                            <td className="py-2 px-3">
                              <Input 
                                value={producto.codigo_referencia || ''}
                                onChange={(e) => actualizarProducto(index, 'codigo_referencia', e.target.value)}
                                className="h-8 text-sm w-24"
                                placeholder="Ref."
                              />
                            </td>
                            <td className="py-2 px-3">
                              <Input 
                                type="number"
                                value={producto.cantidad}
                                onChange={(e) => actualizarProducto(index, 'cantidad', parseInt(e.target.value))}
                                className="h-8 text-sm w-16 text-right"
                              />
                            </td>
                            <td className="py-2 px-3">
                              <Input 
                                type="number"
                                step="0.01"
                                value={producto.precio_unitario}
                                onChange={(e) => actualizarProducto(index, 'precio_unitario', parseFloat(e.target.value))}
                                className="h-8 text-sm w-20 text-right"
                              />
                            </td>
                            <td className="py-2 px-3 text-right font-medium">
                              {formatCurrency(producto.cantidad * producto.precio_unitario)} €
                            </td>
                            <td className="py-2 px-3 text-center">
                              {producto.repuesto_id ? (
                                <Badge variant="secondary">{producto.stock_actual || 0}</Badge>
                              ) : (
                                <span className="text-muted-foreground">-</span>
                              )}
                            </td>
                            <td className="py-2 px-3">
                              <Select 
                                value={producto.accion_sugerida}
                                onValueChange={(v) => actualizarProducto(index, 'accion_sugerida', v)}
                              >
                                <SelectTrigger className="h-8 text-xs w-32">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="crear">
                                    <span className="flex items-center gap-1">
                                      <Plus className="w-3 h-3" /> Crear nuevo
                                    </span>
                                  </SelectItem>
                                  <SelectItem value="añadir_stock" disabled={!producto.repuesto_id}>
                                    <span className="flex items-center gap-1">
                                      <Package className="w-3 h-3" /> Añadir stock
                                    </span>
                                  </SelectItem>
                                  <SelectItem value="ignorar">
                                    <span className="flex items-center gap-1">
                                      <XCircle className="w-3 h-3" /> Ignorar
                                    </span>
                                  </SelectItem>
                                </SelectContent>
                              </Select>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="bg-muted/50 font-medium">
                          <td colSpan={4} className="py-2 px-3 text-right">Total:</td>
                          <td className="py-2 px-3 text-right">{formatCurrency(datosExtraidos.total_factura)} €</td>
                          <td colSpan={2}></td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {/* Botón confirmar */}
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => { setDatosExtraidos(null); setArchivo(null); }}>
                  Cancelar
                </Button>
                <Button onClick={confirmarCompra} disabled={loading || !datosExtraidos.proveedor_id}>
                  {loading ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Procesando...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Confirmar y Registrar Compra
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </TabsContent>

        {/* TAB HISTORIAL */}
        <TabsContent value="historial" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Historial de Compras</CardTitle>
            </CardHeader>
            <CardContent>
              {compras.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No hay compras registradas</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        <th className="text-left py-2 px-3">Fecha</th>
                        <th className="text-left py-2 px-3">Nº Factura</th>
                        <th className="text-left py-2 px-3">Proveedor</th>
                        <th className="text-right py-2 px-3">Productos</th>
                        <th className="text-right py-2 px-3">Total</th>
                        <th className="text-center py-2 px-3">Lotes</th>
                        <th className="text-center py-2 px-3">Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {compras.map((compra) => (
                        <tr key={compra.id} className="border-b hover:bg-muted/50">
                          <td className="py-2 px-3">{compra.fecha_factura}</td>
                          <td className="py-2 px-3 font-mono text-xs">{compra.numero_factura}</td>
                          <td className="py-2 px-3">{compra.proveedor_nombre}</td>
                          <td className="py-2 px-3 text-right">{compra.productos?.length || 0}</td>
                          <td className="py-2 px-3 text-right font-medium">{formatCurrency(compra.total_factura)} €</td>
                          <td className="py-2 px-3 text-center">
                            <Badge variant="outline">{compra.lotes_generados?.length || 0}</Badge>
                          </td>
                          <td className="py-2 px-3 text-center">
                            <Button variant="ghost" size="sm">
                              <Eye className="w-4 h-4" />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB TRAZABILIDAD */}
        <TabsContent value="trazabilidad" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <QrCode className="w-5 h-5" />
                Buscar por Código de Lote
              </CardTitle>
              <CardDescription>
                Introduce el código de trazabilidad (ej: TRZ-2026-0312-001) para ver el historial completo
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2 max-w-md">
                <Input placeholder="TRZ-XXXX-XXXX-XXX" />
                <Button>
                  <Search className="w-4 h-4 mr-2" />
                  Buscar
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">¿Cómo funciona la trazabilidad?</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="p-2 bg-blue-100 rounded-full">
                      <FileText className="w-5 h-5 text-blue-600" />
                    </div>
                    <span className="font-medium">1. Compra</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Al registrar una compra, cada producto recibe un código de lote único
                  </p>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="p-2 bg-amber-100 rounded-full">
                      <Package className="w-5 h-5 text-amber-600" />
                    </div>
                    <span className="font-medium">2. Uso</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Cuando usas un componente en una orden, se registra el lote utilizado
                  </p>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="p-2 bg-green-100 rounded-full">
                      <History className="w-5 h-5 text-green-600" />
                    </div>
                    <span className="font-medium">3. Seguimiento</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Si un dispositivo vuelve por fallo, puedes rastrear el componente hasta su origen
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB DASHBOARD */}
        <TabsContent value="dashboard" className="space-y-4">
          {dashboard ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="border-l-4 border-l-blue-500">
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground">Total Compras</div>
                    <div className="text-2xl font-bold">{dashboard.resumen?.total_compras || 0}</div>
                    <div className="text-xs text-muted-foreground">este mes</div>
                  </CardContent>
                </Card>
                <Card className="border-l-4 border-l-red-500">
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground">Total Gastado</div>
                    <div className="text-2xl font-bold text-red-600">{formatCurrency(dashboard.resumen?.total_gastado)} €</div>
                    <div className="text-xs text-muted-foreground">en compras</div>
                  </CardContent>
                </Card>
                <Card className="border-l-4 border-l-green-500">
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground">Productos Comprados</div>
                    <div className="text-2xl font-bold text-green-600">{dashboard.resumen?.total_productos || 0}</div>
                    <div className="text-xs text-muted-foreground">unidades</div>
                  </CardContent>
                </Card>
                <Card className="border-l-4 border-l-amber-500">
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground">Promedio por Compra</div>
                    <div className="text-2xl font-bold text-amber-600">{formatCurrency(dashboard.resumen?.promedio_por_compra)} €</div>
                  </CardContent>
                </Card>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Top Proveedores</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {dashboard.top_proveedores?.length > 0 ? (
                      <div className="space-y-2">
                        {dashboard.top_proveedores.map((p, i) => (
                          <div key={i} className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50">
                            <span>{p.nombre}</span>
                            <span className="font-medium">{formatCurrency(p.total)} €</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-center text-muted-foreground py-4">Sin datos</p>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-500" />
                      Alertas de Stock Bajo
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {dashboard.alertas_stock_bajo?.length > 0 ? (
                      <div className="space-y-2">
                        {dashboard.alertas_stock_bajo.map((p, i) => (
                          <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-amber-50">
                            <div>
                              <span className="font-medium">{p.nombre}</span>
                              <span className="text-xs text-muted-foreground ml-2">{p.sku}</span>
                            </div>
                            <Badge variant="destructive">
                              {p.stock} / {p.stock_minimo}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-center text-muted-foreground py-4">Sin alertas de stock</p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-32">
              <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

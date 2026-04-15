import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { 
  FileText, Receipt, CreditCard, TrendingUp, AlertCircle, 
  Plus, Search, Filter, Download, ChevronRight, Euro,
  Calendar, Clock, CheckCircle, XCircle, AlertTriangle,
  ChevronLeft, ChevronsLeft, ChevronsRight
} from 'lucide-react';

const estadoColors = {
  borrador: 'bg-gray-100 text-gray-800',
  emitida: 'bg-blue-100 text-blue-800',
  pagada: 'bg-green-100 text-green-800',
  parcial: 'bg-yellow-100 text-yellow-800',
  vencida: 'bg-red-100 text-red-800',
  anulada: 'bg-gray-300 text-gray-600'
};

const estadoIcons = {
  borrador: <FileText className="h-4 w-4" />,
  emitida: <Clock className="h-4 w-4" />,
  pagada: <CheckCircle className="h-4 w-4" />,
  parcial: <AlertTriangle className="h-4 w-4" />,
  vencida: <XCircle className="h-4 w-4" />,
  anulada: <XCircle className="h-4 w-4" />
};

export default function Contabilidad() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('resumen');
  const [stats, setStats] = useState(null);
  const [resumen, setResumen] = useState(null);
  const [facturas, setFacturas] = useState([]);
  const [albaranes, setAlbaranes] = useState([]);
  const [pendientes, setPendientes] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Filtros para facturas
  const [filtros, setFiltros] = useState({
    tipo: '',
    estado: '',
    busqueda: ''
  });

  // Paginación facturas
  const [facturasPagina, setFacturasPagina] = useState(1);
  const [facturasPorPagina, setFacturasPorPagina] = useState(20);
  const [facturasTotal, setFacturasTotal] = useState(0);

  // Filtros para albaranes
  const [filtrosAlbaranes, setFiltrosAlbaranes] = useState({
    estado: '', // '' | 'pendiente' | 'facturado'
    busqueda: ''
  });

  // Paginación albaranes
  const [albaranesPagina, setAlbaranesPagina] = useState(1);
  const [albaranesPorPagina, setAlbaranesPorPagina] = useState(20);
  const [albaranesTotal, setAlbaranesTotal] = useState(0);

  useEffect(() => {
    cargarDatosIniciales();
  }, []);

  // Cargar facturas cuando cambia página o filtros
  useEffect(() => {
    if (!loading) cargarFacturas();
  }, [facturasPagina, facturasPorPagina]);

  // Cargar albaranes cuando cambia página o filtros
  useEffect(() => {
    if (!loading) cargarAlbaranes();
  }, [albaranesPagina, albaranesPorPagina]);

  const cargarDatosIniciales = async () => {
    try {
      setLoading(true);
      const [statsRes, resumenRes, pendientesRes] = await Promise.all([
        api.get('/contabilidad/stats'),
        api.get('/contabilidad/informes/resumen'),
        api.get('/contabilidad/informes/pendientes')
      ]);
      
      setStats(statsRes.data);
      setResumen(resumenRes.data);
      setPendientes(pendientesRes.data);

      // Cargar facturas y albaranes
      await Promise.all([cargarFacturas(), cargarAlbaranes()]);
    } catch (error) {
      console.error('Error cargando datos:', error);
      toast.error('Error al cargar datos de contabilidad');
    } finally {
      setLoading(false);
    }
  };

  const cargarFacturas = async () => {
    try {
      const params = new URLSearchParams({
        page: facturasPagina,
        page_size: facturasPorPagina
      });
      if (filtros.tipo) params.append('tipo', filtros.tipo);
      if (filtros.estado) params.append('estado', filtros.estado);
      if (filtros.busqueda) params.append('search', filtros.busqueda);

      const res = await api.get(`/contabilidad/facturas?${params}`);
      setFacturas(res.data.items || []);
      setFacturasTotal(res.data.total || 0);
    } catch (error) {
      console.error('Error cargando facturas:', error);
    }
  };

  const cargarAlbaranes = async () => {
    try {
      const params = new URLSearchParams({
        page: albaranesPagina,
        page_size: albaranesPorPagina
      });
      if (filtrosAlbaranes.estado === 'pendiente') params.append('facturado', 'false');
      if (filtrosAlbaranes.estado === 'facturado') params.append('facturado', 'true');
      if (filtrosAlbaranes.busqueda) params.append('search', filtrosAlbaranes.busqueda);

      const res = await api.get(`/contabilidad/albaranes?${params}`);
      setAlbaranes(res.data.items || []);
      setAlbaranesTotal(res.data.total || 0);
    } catch (error) {
      console.error('Error cargando albaranes:', error);
    }
  };

  // Recargar todo
  const cargarDatos = async () => {
    await cargarDatosIniciales();
  };

  // Buscar facturas con debounce
  const handleBuscarFacturas = () => {
    setFacturasPagina(1);
    cargarFacturas();
  };

  // Buscar albaranes con debounce
  const handleBuscarAlbaranes = () => {
    setAlbaranesPagina(1);
    cargarAlbaranes();
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(amount || 0);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('es-ES');
  };

  // Componente de paginación reutilizable
  const Paginacion = ({ pagina, setPagina, porPagina, setPorPagina, total }) => {
    const totalPaginas = Math.ceil(total / porPagina) || 1;
    
    return (
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 px-4 py-3 border-t bg-gray-50">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <span>Mostrar</span>
          <Select value={porPagina.toString()} onValueChange={(v) => { setPorPagina(parseInt(v)); setPagina(1); }}>
            <SelectTrigger className="w-[70px] h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">10</SelectItem>
              <SelectItem value="20">20</SelectItem>
              <SelectItem value="50">50</SelectItem>
              <SelectItem value="100">100</SelectItem>
            </SelectContent>
          </Select>
          <span>de {total} resultados</span>
        </div>
        
        <div className="flex items-center gap-1">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => setPagina(1)} 
            disabled={pagina === 1}
            className="h-8 w-8 p-0"
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => setPagina(p => Math.max(1, p - 1))} 
            disabled={pagina === 1}
            className="h-8 w-8 p-0"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          
          <span className="px-3 text-sm">
            Página <strong>{pagina}</strong> de <strong>{totalPaginas}</strong>
          </span>
          
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => setPagina(p => Math.min(totalPaginas, p + 1))} 
            disabled={pagina >= totalPaginas}
            className="h-8 w-8 p-0"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => setPagina(totalPaginas)} 
            disabled={pagina >= totalPaginas}
            className="h-8 w-8 p-0"
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="contabilidad-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Contabilidad</h1>
          <p className="text-gray-500">Gestión de facturas, albaranes y pagos</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate('/contabilidad/factura/nueva?tipo=compra')}>
            <Plus className="h-4 w-4 mr-2" />
            Factura Compra
          </Button>
          <Button onClick={() => navigate('/contabilidad/factura/nueva?tipo=venta')}>
            <Plus className="h-4 w-4 mr-2" />
            Factura Venta
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-blue-600 font-medium">Facturas Venta</p>
                <p className="text-2xl font-bold text-blue-900">{stats?.facturas_venta || 0}</p>
              </div>
              <FileText className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-purple-600 font-medium">Facturas Compra</p>
                <p className="text-2xl font-bold text-purple-900">{stats?.facturas_compra || 0}</p>
              </div>
              <Receipt className="h-8 w-8 text-purple-500" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-green-600 font-medium">Pendiente Cobro</p>
                <p className="text-2xl font-bold text-green-900">{formatCurrency(stats?.pendiente_cobro)}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-red-50 to-red-100 border-red-200">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-red-600 font-medium">Pendiente Pago</p>
                <p className="text-2xl font-bold text-red-900">{formatCurrency(stats?.pendiente_pago)}</p>
              </div>
              <CreditCard className="h-8 w-8 text-red-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-5 w-full max-w-2xl">
          <TabsTrigger value="resumen">Resumen</TabsTrigger>
          <TabsTrigger value="facturas">Facturas</TabsTrigger>
          <TabsTrigger value="albaranes">Albaranes</TabsTrigger>
          <TabsTrigger value="pendientes">Pendientes</TabsTrigger>
          <TabsTrigger value="informes">Informes</TabsTrigger>
        </TabsList>

        {/* Tab: Resumen */}
        <TabsContent value="resumen" className="space-y-4">
          <div className="grid md:grid-cols-2 gap-6">
            {/* Ventas */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-600" />
                  Ventas {resumen?.año}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Base Imponible</span>
                  <span className="font-medium">{formatCurrency(resumen?.ventas?.base_imponible)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">IVA Repercutido</span>
                  <span className="font-medium">{formatCurrency(resumen?.ventas?.iva_repercutido)}</span>
                </div>
                <div className="flex justify-between border-t pt-2">
                  <span className="font-semibold">Total Facturado</span>
                  <span className="font-bold text-green-600">{formatCurrency(resumen?.ventas?.total)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Pendiente de cobro</span>
                  <span className="text-orange-600">{formatCurrency(resumen?.ventas?.pendiente_cobro)}</span>
                </div>
              </CardContent>
            </Card>

            {/* Compras */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Receipt className="h-5 w-5 text-purple-600" />
                  Compras {resumen?.año}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Base Imponible</span>
                  <span className="font-medium">{formatCurrency(resumen?.compras?.base_imponible)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">IVA Soportado</span>
                  <span className="font-medium">{formatCurrency(resumen?.compras?.iva_soportado)}</span>
                </div>
                <div className="flex justify-between border-t pt-2">
                  <span className="font-semibold">Total Compras</span>
                  <span className="font-bold text-purple-600">{formatCurrency(resumen?.compras?.total)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Pendiente de pago</span>
                  <span className="text-red-600">{formatCurrency(resumen?.compras?.pendiente_pago)}</span>
                </div>
              </CardContent>
            </Card>

            {/* Liquidación IVA */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Euro className="h-5 w-5 text-blue-600" />
                  Liquidación IVA
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">IVA Repercutido</span>
                  <span className="font-medium text-green-600">+{formatCurrency(resumen?.liquidacion_iva?.iva_repercutido)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">IVA Soportado</span>
                  <span className="font-medium text-red-600">-{formatCurrency(resumen?.liquidacion_iva?.iva_soportado)}</span>
                </div>
                <div className="flex justify-between border-t pt-2">
                  <span className="font-semibold">Resultado</span>
                  <span className={`font-bold ${resumen?.liquidacion_iva?.resultado >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {resumen?.liquidacion_iva?.resultado >= 0 ? 'A ingresar: ' : 'A compensar: '}
                    {formatCurrency(Math.abs(resumen?.liquidacion_iva?.resultado || 0))}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Beneficio */}
            <Card className="bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-200">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-emerald-600" />
                  Beneficio Bruto
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-emerald-700">{formatCurrency(resumen?.beneficio_bruto)}</p>
                <p className="text-sm text-emerald-600 mt-2">
                  Año {resumen?.año} • {resumen?.ventas?.num_facturas || 0} facturas emitidas
                </p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab: Facturas */}
        <TabsContent value="facturas" className="space-y-4">
          {/* Filtros */}
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Buscar por número o cliente..."
                className="pl-10"
                value={filtros.busqueda}
                onChange={(e) => setFiltros({ ...filtros, busqueda: e.target.value })}
                onKeyDown={(e) => e.key === 'Enter' && handleBuscarFacturas()}
              />
            </div>
            <Select value={filtros.tipo || 'all'} onValueChange={(v) => { setFiltros({ ...filtros, tipo: v === 'all' ? '' : v }); setFacturasPagina(1); }}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Tipo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="venta">Venta</SelectItem>
                <SelectItem value="compra">Compra</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filtros.estado || 'all'} onValueChange={(v) => { setFiltros({ ...filtros, estado: v === 'all' ? '' : v }); setFacturasPagina(1); }}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="borrador">Borrador</SelectItem>
                <SelectItem value="emitida">Emitida</SelectItem>
                <SelectItem value="pagada">Pagada</SelectItem>
                <SelectItem value="parcial">Pago Parcial</SelectItem>
                <SelectItem value="vencida">Vencida</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={handleBuscarFacturas}>
              <Search className="h-4 w-4 mr-2" />
              Buscar
            </Button>
          </div>

          {/* Lista de facturas */}
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left p-3 font-medium text-gray-600">Número</th>
                    <th className="text-left p-3 font-medium text-gray-600">Tipo</th>
                    <th className="text-left p-3 font-medium text-gray-600">Cliente/Proveedor</th>
                    <th className="text-left p-3 font-medium text-gray-600">Fecha</th>
                    <th className="text-right p-3 font-medium text-gray-600">Total</th>
                    <th className="text-right p-3 font-medium text-gray-600">Pendiente</th>
                    <th className="text-center p-3 font-medium text-gray-600">Estado</th>
                    <th className="text-center p-3 font-medium text-gray-600"></th>
                  </tr>
                </thead>
                <tbody>
                  {facturas.map((factura) => (
                    <tr key={factura.id} className="border-b hover:bg-gray-50">
                      <td className="p-3 font-medium">{factura.numero}</td>
                      <td className="p-3">
                        <Badge variant={factura.tipo === 'venta' ? 'default' : 'secondary'}>
                          {factura.tipo === 'venta' ? 'Venta' : 'Compra'}
                        </Badge>
                      </td>
                      <td className="p-3">{factura.nombre_fiscal}</td>
                      <td className="p-3 text-gray-600">{formatDate(factura.fecha_emision)}</td>
                      <td className="p-3 text-right font-medium">{formatCurrency(factura.total)}</td>
                      <td className="p-3 text-right">
                        {factura.pendiente_cobro > 0 ? (
                          <span className="text-orange-600 font-medium">{formatCurrency(factura.pendiente_cobro)}</span>
                        ) : (
                          <span className="text-green-600">-</span>
                        )}
                      </td>
                      <td className="p-3 text-center">
                        <Badge className={estadoColors[factura.estado]}>
                          <span className="flex items-center gap-1">
                            {estadoIcons[factura.estado]}
                            {factura.estado}
                          </span>
                        </Badge>
                      </td>
                      <td className="p-3 text-center">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/contabilidad/factura/${factura.id}`)}
                        >
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {facturas.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  No hay facturas que mostrar
                </div>
              )}
            </div>
            {/* Paginación Facturas */}
            <Paginacion
              pagina={facturasPagina}
              setPagina={setFacturasPagina}
              porPagina={facturasPorPagina}
              setPorPagina={setFacturasPorPagina}
              total={facturasTotal}
            />
          </Card>
        </TabsContent>

        {/* Tab: Albaranes */}
        <TabsContent value="albaranes" className="space-y-4">
          {/* Filtros para albaranes */}
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Buscar por número, orden o cliente..."
                className="pl-10"
                value={filtrosAlbaranes.busqueda}
                onChange={(e) => setFiltrosAlbaranes({ ...filtrosAlbaranes, busqueda: e.target.value })}
                onKeyDown={(e) => e.key === 'Enter' && handleBuscarAlbaranes()}
              />
            </div>
            <Select 
              value={filtrosAlbaranes.estado || 'all'} 
              onValueChange={(v) => { 
                setFiltrosAlbaranes({ ...filtrosAlbaranes, estado: v === 'all' ? '' : v }); 
                setAlbaranesPagina(1);
              }}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="pendiente">Pendiente facturar</SelectItem>
                <SelectItem value="facturado">Facturado</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={handleBuscarAlbaranes}>
              <Search className="h-4 w-4 mr-2" />
              Buscar
            </Button>
          </div>

          {/* Info de pendientes */}
          <div className="flex justify-between items-center">
            <p className="text-gray-600">
              {stats?.albaranes_sin_facturar || 0} albaranes pendientes de facturar
            </p>
            <Badge variant="outline">
              Total: {albaranesTotal} albaranes
            </Badge>
          </div>
          
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left p-3 font-medium text-gray-600">Número</th>
                    <th className="text-left p-3 font-medium text-gray-600">Orden</th>
                    <th className="text-left p-3 font-medium text-gray-600">Cliente</th>
                    <th className="text-left p-3 font-medium text-gray-600">Fecha</th>
                    <th className="text-right p-3 font-medium text-gray-600">Total</th>
                    <th className="text-center p-3 font-medium text-gray-600">Estado</th>
                    <th className="text-center p-3 font-medium text-gray-600"></th>
                  </tr>
                </thead>
                <tbody>
                  {albaranes.map((albaran) => (
                    <tr key={albaran.id} className="border-b hover:bg-gray-50">
                      <td className="p-3 font-medium">{albaran.numero}</td>
                      <td className="p-3">{albaran.numero_orden || '-'}</td>
                      <td className="p-3">{albaran.nombre_cliente}</td>
                      <td className="p-3 text-gray-600">{formatDate(albaran.fecha_emision)}</td>
                      <td className="p-3 text-right font-medium">{formatCurrency(albaran.total)}</td>
                      <td className="p-3 text-center">
                        {albaran.facturado ? (
                          <Badge className="bg-green-100 text-green-800">Facturado</Badge>
                        ) : (
                          <Badge className="bg-yellow-100 text-yellow-800">Pendiente</Badge>
                        )}
                      </td>
                      <td className="p-3 text-center">
                        {!albaran.facturado && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={async () => {
                              try {
                                await api.post(`/contabilidad/albaranes/${albaran.id}/facturar`);
                                toast.success('Factura creada correctamente');
                                cargarDatos();
                              } catch (error) {
                                toast.error('Error al crear factura');
                              }
                            }}
                          >
                            Facturar
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {albaranes.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  No hay albaranes
                </div>
              )}
            </div>
            {/* Paginación Albaranes */}
            <Paginacion
              pagina={albaranesPagina}
              setPagina={setAlbaranesPagina}
              porPagina={albaranesPorPagina}
              setPorPagina={setAlbaranesPorPagina}
              total={albaranesTotal}
            />
          </Card>
        </TabsContent>

        {/* Tab: Pendientes */}
        <TabsContent value="pendientes" className="space-y-4">
          <div className="grid md:grid-cols-2 gap-6">
            {/* Pendientes de Cobro */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-600" />
                  Pendiente de Cobro
                  <Badge className="ml-auto bg-green-100 text-green-800">
                    {formatCurrency(pendientes?.pendiente_cobro?.total)}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {pendientes?.pendiente_cobro?.facturas?.map((f) => (
                    <div key={f.id} className="flex items-center justify-between p-2 bg-gray-50 rounded hover:bg-gray-100 cursor-pointer"
                         onClick={() => navigate(`/contabilidad/factura/${f.id}`)}>
                      <div>
                        <p className="font-medium">{f.numero}</p>
                        <p className="text-sm text-gray-500">{f.nombre_fiscal}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium text-green-600">{formatCurrency(f.pendiente_cobro)}</p>
                        <p className="text-xs text-gray-500">Vence: {formatDate(f.fecha_vencimiento)}</p>
                      </div>
                    </div>
                  ))}
                  {pendientes?.pendiente_cobro?.facturas?.length === 0 && (
                    <p className="text-center text-gray-500 py-4">Sin facturas pendientes</p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Pendientes de Pago */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-red-600" />
                  Pendiente de Pago
                  <Badge className="ml-auto bg-red-100 text-red-800">
                    {formatCurrency(pendientes?.pendiente_pago?.total)}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {pendientes?.pendiente_pago?.facturas?.map((f) => (
                    <div key={f.id} className="flex items-center justify-between p-2 bg-gray-50 rounded hover:bg-gray-100 cursor-pointer"
                         onClick={() => navigate(`/contabilidad/factura/${f.id}`)}>
                      <div>
                        <p className="font-medium">{f.numero}</p>
                        <p className="text-sm text-gray-500">{f.nombre_fiscal}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium text-red-600">{formatCurrency(f.pendiente_cobro)}</p>
                        <p className="text-xs text-gray-500">Vence: {formatDate(f.fecha_vencimiento)}</p>
                      </div>
                    </div>
                  ))}
                  {pendientes?.pendiente_pago?.facturas?.length === 0 && (
                    <p className="text-center text-gray-500 py-4">Sin facturas pendientes</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab: Informes */}
        <TabsContent value="informes" className="space-y-4">
          <div className="grid md:grid-cols-4 gap-4">
            <Card className="cursor-pointer hover:shadow-lg transition-shadow"
                  onClick={() => navigate('/contabilidad/informe/iva')}>
              <CardContent className="pt-6 text-center">
                <Euro className="h-12 w-12 mx-auto text-blue-600 mb-3" />
                <h3 className="font-semibold">Informe IVA Trimestral</h3>
                <p className="text-sm text-gray-500 mt-1">Modelo 303</p>
              </CardContent>
            </Card>
            
            <Card className="cursor-pointer hover:shadow-lg transition-shadow"
                  onClick={() => navigate('/contabilidad/informe/modelo347')}>
              <CardContent className="pt-6 text-center">
                <FileText className="h-12 w-12 mx-auto text-orange-600 mb-3" />
                <h3 className="font-semibold">Modelo 347</h3>
                <p className="text-sm text-gray-500 mt-1">Operaciones con terceros</p>
              </CardContent>
            </Card>
            
            <Card className="cursor-pointer hover:shadow-lg transition-shadow"
                  onClick={() => navigate('/contabilidad/informe/beneficios')}>
              <CardContent className="pt-6 text-center">
                <TrendingUp className="h-12 w-12 mx-auto text-green-600 mb-3" />
                <h3 className="font-semibold">Informe de Beneficios</h3>
                <p className="text-sm text-gray-500 mt-1">Análisis de rentabilidad</p>
              </CardContent>
            </Card>
            
            <Card className="cursor-pointer hover:shadow-lg transition-shadow"
                  onClick={async () => {
                    try {
                      const res = await api.post('/contabilidad/recordatorios/verificar-vencidas');
                      toast.success(res.data.message);
                      cargarDatos();
                    } catch (e) {
                      toast.error('Error verificando facturas vencidas');
                    }
                  }}>
              <CardContent className="pt-6 text-center">
                <AlertCircle className="h-12 w-12 mx-auto text-red-600 mb-3" />
                <h3 className="font-semibold">Verificar Vencidas</h3>
                <p className="text-sm text-gray-500 mt-1">Marcar facturas vencidas</p>
              </CardContent>
            </Card>
          </div>
          
          {/* Acciones adicionales */}
          <Card>
            <CardHeader>
              <CardTitle>Recordatorios de Pago</CardTitle>
            </CardHeader>
            <CardContent className="flex gap-4">
              <Button 
                variant="outline"
                onClick={async () => {
                  try {
                    const res = await api.get('/contabilidad/recordatorios/vencidas');
                    if (res.data.length === 0) {
                      toast.info('No hay facturas vencidas');
                    } else {
                      toast.success(`${res.data.length} facturas vencidas encontradas`);
                    }
                  } catch (e) {
                    toast.error('Error');
                  }
                }}
              >
                <AlertCircle className="h-4 w-4 mr-2" />
                Ver Facturas Vencidas
              </Button>
              <Button 
                variant="default"
                onClick={async () => {
                  try {
                    const res = await api.post('/contabilidad/recordatorios/enviar-masivo');
                    toast.success(res.data.message);
                  } catch (e) {
                    toast.error('Error enviando recordatorios');
                  }
                }}
              >
                <Clock className="h-4 w-4 mr-2" />
                Enviar Recordatorios Masivos
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

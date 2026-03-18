import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  ClipboardList, 
  Users, 
  Package, 
  Truck, 
  AlertTriangle,
  Bell,
  ArrowRight,
  Clock,
  CheckCircle2,
  Wrench,
  Send,
  Search,
  QrCode,
  Lock,
  TrendingUp,
  TrendingDown,
  Timer,
  Shield,
  Download,
  Upload,
  BarChart3,
  PieChart,
  Plus,
  ShoppingCart
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart as RechartsPie,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { dashboardAPI, ordenesAPI, exportarAPI } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import * as XLSX from 'xlsx';

const statusLabels = {
  pendiente_recibir: { label: 'Pendiente Recibir', icon: Clock, color: 'bg-yellow-500', chartColor: '#eab308' },
  recibida: { label: 'Recibida', icon: CheckCircle2, color: 'bg-blue-500', chartColor: '#3b82f6' },
  en_taller: { label: 'En Taller', icon: Wrench, color: 'bg-purple-500', chartColor: '#8b5cf6' },
  re_presupuestar: { label: 'Re-presupuestar', icon: AlertTriangle, color: 'bg-orange-500', chartColor: '#f97316' },
  reparado: { label: 'Reparado', icon: CheckCircle2, color: 'bg-green-500', chartColor: '#22c55e' },
  validacion: { label: 'Validación', icon: ClipboardList, color: 'bg-indigo-500', chartColor: '#6366f1' },
  enviado: { label: 'Enviado', icon: Send, color: 'bg-emerald-500', chartColor: '#10b981' },
  garantia: { label: 'Garantía', icon: Shield, color: 'bg-red-500', chartColor: '#ef4444' },
  cancelado: { label: 'Cancelado', icon: AlertTriangle, color: 'bg-gray-500', chartColor: '#6b7280' },
};

const COLORS = ['#3b82f6', '#22c55e', '#eab308', '#8b5cf6', '#f97316', '#10b981', '#ef4444', '#6b7280'];

export default function Dashboard() {
  const navigate = useNavigate();
  const scannerInputRef = useRef(null);
  const { isAdmin, isTecnico, isMaster } = useAuth();
  
  const [stats, setStats] = useState(null);
  const [metricas, setMetricas] = useState(null);
  const [alertasStock, setAlertasStock] = useState(null);
  const [ordenesRecientes, setOrdenesRecientes] = useState([]);
  const [ordenesCompraUrgentes, setOrdenesCompraUrgentes] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('resumen');
  
  // Scanner states
  const [scannerValue, setScannerValue] = useState('');
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [statsRes, ordenesRes] = await Promise.all([
          dashboardAPI.stats(),
          ordenesAPI.listarPaginado({ page: 1, page_size: 5 })
        ]);
        setStats(statsRes.data);
        setOrdenesRecientes(ordenesRes.data.data || []);
        
        // Cargar métricas avanzadas, alertas de stock y órdenes de compra urgentes (solo admin)
        if (isAdmin()) {
          const [metricasRes, alertasRes, ocUrgentesRes] = await Promise.all([
            dashboardAPI.metricasAvanzadas(),
            dashboardAPI.alertasStock(),
            dashboardAPI.ordenesCompraUrgentes()
          ]);
          setMetricas(metricasRes.data);
          setAlertasStock(alertasRes.data);
          setOrdenesCompraUrgentes(ocUrgentesRes.data);
        }
      } catch (error) {
        toast.error('Error al cargar el dashboard');
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  // Scanner functions
  // Regla: primera vez (pendiente_recibir) → marcar recibido; el resto → buscar y abrir
  const handleScannerSubmit = async (e) => {
    e.preventDefault();
    if (!scannerValue.trim()) return;
    
    setProcessing(true);
    try {
      const ordenes = await ordenesAPI.listarPaginado({ search: scannerValue.trim(), page_size: 1 });
      
      if (!ordenes.data.data || ordenes.data.data.length === 0) {
        toast.error('Orden no encontrada');
        return;
      }
      
      const orden = ordenes.data.data[0];
      
      // Auto-detect: si está pendiente_recibir y el usuario es admin → marcar recibido
      if (orden.estado === 'pendiente_recibir' && !isTecnico()) {
        try {
          const response = await ordenesAPI.escanear(orden.id, {
            tipo_escaneo: 'recepcion',
            usuario: 'admin'
          });
          toast.success(`Orden ${orden.numero_orden} marcada como RECIBIDA`);
        } catch (scanError) {
          const detail = scanError.response?.data?.detail;
          toast.error(typeof detail === 'string' ? detail : 'Error al marcar como recibida');
        }
      } else {
        toast.success(`Orden ${orden.numero_orden} encontrada`);
      }
      
      navigate(`/crm/ordenes/${orden.id}`);
    } catch (error) {
      let msg = 'Error al procesar el escaneo';
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(d => d.msg || d).join(', ') : msg;
      }
      toast.error(msg);
    } finally {
      setProcessing(false);
      setScannerValue('');
    }
  };

  // Export functions
  const handleExportar = async (tipo) => {
    try {
      let response;
      switch (tipo) {
        case 'clientes':
          response = await exportarAPI.clientes();
          break;
        case 'ordenes':
          response = await exportarAPI.ordenes();
          break;
        case 'inventario':
          response = await exportarAPI.inventario();
          break;
        default:
          return;
      }
      
      const ws = XLSX.utils.json_to_sheet(response.data.data);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, tipo.charAt(0).toUpperCase() + tipo.slice(1));
      XLSX.writeFile(wb, `${tipo}_${new Date().toISOString().split('T')[0]}.xlsx`);
      
      toast.success(`${tipo} exportados correctamente`);
    } catch (error) {
      toast.error('Error al exportar');
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-slate-200 rounded w-1/3" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="h-32 bg-slate-200 rounded-xl" />)}
        </div>
      </div>
    );
  }

  // Prepare chart data
  const pieChartData = metricas?.ordenes_por_estado?.map(item => ({
    name: statusLabels[item.estado]?.label || item.estado,
    value: item.cantidad,
    color: statusLabels[item.estado]?.chartColor || '#6b7280'
  })) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Bienvenido al panel de control</p>
        </div>
        
        <div className="flex gap-2 flex-wrap">
          {/* BOTÓN NUEVA ORDEN - SIEMPRE VISIBLE Y PROMINENTE */}
          <Button 
            onClick={() => navigate('/ordenes/nueva')} 
            className="bg-green-600 hover:bg-green-700 gap-2"
            data-testid="nueva-orden-btn"
          >
            <Plus className="w-4 h-4" />
            Nueva Orden
          </Button>
          
          {isAdmin() && (
            <>
              <Button variant="outline" size="sm" onClick={() => handleExportar('clientes')}>
                <Download className="w-4 h-4 mr-2" />
                Clientes
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExportar('ordenes')}>
                <Download className="w-4 h-4 mr-2" />
                Órdenes
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExportar('inventario')}>
                <Download className="w-4 h-4 mr-2" />
                Inventario
              </Button>
            </>
          )}
        </div>
      </div>

      {/* ÓRDENES DE COMPRA URGENTES - BOTÓN EN STATS */}

      {/* Scanner Card (Compacto) */}
      <Card className="border border-primary/20">
        <CardContent className="py-3 px-4">
          <form onSubmit={handleScannerSubmit} className="flex items-center gap-3">
            <QrCode className="w-5 h-5 text-primary flex-shrink-0" />
            <Input
              ref={scannerInputRef}
              placeholder="Escanea o introduce código de orden..."
              value={scannerValue}
              onChange={(e) => setScannerValue(e.target.value)}
              className="h-9 font-mono text-sm"
              data-testid="scanner-input"
            />
            <Button type="submit" disabled={processing} size="sm" className="h-9 px-4" data-testid="scanner-submit">
              {processing ? 'Procesando...' : 'Escanear'}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Stats Cards */}
      <div className={`grid gap-4 ${isTecnico() ? 'grid-cols-2' : isMaster() ? 'grid-cols-2 md:grid-cols-5' : 'grid-cols-2 md:grid-cols-3'}`}>
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Órdenes</p>
                <p className="text-3xl font-bold">{stats?.total_ordenes || 0}</p>
              </div>
              <ClipboardList className="w-10 h-10 text-primary/20" />
            </div>
          </CardContent>
        </Card>
        {isMaster() && (
          <>
            <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={() => navigate('/clientes')}>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Clientes</p>
                    <p className="text-3xl font-bold">{stats?.total_clientes || 0}</p>
                  </div>
                  <Users className="w-10 h-10 text-primary/20" />
                </div>
              </CardContent>
            </Card>
            <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={() => navigate('/inventario')}>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Repuestos</p>
                    <p className="text-3xl font-bold">{stats?.total_repuestos || 0}</p>
                  </div>
                  <Package className="w-10 h-10 text-primary/20" />
                </div>
              </CardContent>
            </Card>
          </>
        )}
        <Card 
          className={`hover:shadow-md transition-shadow cursor-pointer ${stats?.notificaciones_pendientes > 0 ? 'border-orange-500' : ''}`}
          onClick={() => navigate('/notificaciones')}
        >
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Notificaciones</p>
                <p className="text-3xl font-bold">{stats?.notificaciones_pendientes || 0}</p>
              </div>
              <Bell className={`w-10 h-10 ${stats?.notificaciones_pendientes > 0 ? 'text-orange-500' : 'text-primary/20'}`} />
            </div>
          </CardContent>
        </Card>
        {isAdmin() && (
          <Card 
            className={`hover:shadow-md transition-shadow cursor-pointer ${
              ordenesCompraUrgentes?.total_pendientes > 0 ? 'border-red-500' : ''
            }`}
            onClick={() => navigate('/ordenes-compra')}
            data-testid="ordenes-compra-card"
          >
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Compras Pend.</p>
                  <p className="text-3xl font-bold">{ordenesCompraUrgentes?.total_pendientes || 0}</p>
                </div>
                <ShoppingCart className={`w-10 h-10 ${
                  ordenesCompraUrgentes?.total_pendientes > 0 ? 'text-red-500' : 'text-primary/20'
                }`} />
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Admin-only content */}
      {isAdmin() && metricas && (
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="resumen">Resumen</TabsTrigger>
            <TabsTrigger value="ordenes">Órdenes</TabsTrigger>
            <TabsTrigger value="tiempos">Tiempos</TabsTrigger>
            <TabsTrigger value="stock">Stock</TabsTrigger>
          </TabsList>

          {/* Tab: Resumen */}
          <TabsContent value="resumen" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* KPIs */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Tasa de Éxito</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-green-500" />
                    <span className="text-3xl font-bold text-green-600">{metricas.ratios.ratio_completado}%</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {metricas.ratios.completadas} de {metricas.ratios.total} órdenes completadas
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Tasa de Cancelación</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <TrendingDown className="w-5 h-5 text-red-500" />
                    <span className="text-3xl font-bold text-red-600">{metricas.ratios.ratio_cancelacion}%</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {metricas.ratios.canceladas} órdenes canceladas
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Garantías</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <Shield className="w-5 h-5 text-orange-500" />
                    <span className="text-3xl font-bold text-orange-600">{metricas.ratios.garantias}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Órdenes de garantía activas
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Pie Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <PieChart className="w-5 h-5" />
                  Distribución por Estado
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <RechartsPie>
                      <Pie
                        data={pieChartData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                        outerRadius={100}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {pieChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </RechartsPie>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Órdenes */}
          <TabsContent value="ordenes" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5" />
                  Órdenes por Día (Últimos 30 días)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={metricas.ordenes_por_dia}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="fecha" 
                        tick={{ fontSize: 12 }}
                        tickFormatter={(value) => value.slice(5)}
                      />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="ordenes" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Últimos 7 días</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-4xl font-bold">{metricas.comparativa.ultimos_7_dias}</p>
                  <p className="text-sm text-muted-foreground">órdenes creadas</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Últimos 30 días</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-4xl font-bold">{metricas.comparativa.total_30_dias}</p>
                  <p className="text-sm text-muted-foreground">órdenes creadas</p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Tab: Tiempos */}
          <TabsContent value="tiempos" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card className="border-l-4 border-l-blue-500">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2">
                    <Timer className="w-5 h-5 text-blue-500" />
                    Tiempo Promedio de Reparación
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-4xl font-bold">{metricas.tiempos.promedio_reparacion_horas} h</p>
                  <p className="text-sm text-muted-foreground">
                    ≈ {metricas.tiempos.promedio_reparacion_dias} días
                  </p>
                  <p className="text-xs text-muted-foreground mt-2">
                    Desde inicio hasta fin de reparación
                  </p>
                </CardContent>
              </Card>

              <Card className="border-l-4 border-l-green-500">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="w-5 h-5 text-green-500" />
                    Tiempo Promedio Total
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-4xl font-bold">{metricas.tiempos.promedio_total_horas} h</p>
                  <p className="text-sm text-muted-foreground">
                    ≈ {metricas.tiempos.promedio_total_dias} días
                  </p>
                  <p className="text-xs text-muted-foreground mt-2">
                    Desde creación hasta envío
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Top Repuestos */}
            {metricas.top_repuestos.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Repuestos Más Utilizados</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {metricas.top_repuestos.map((rep, idx) => (
                      <div key={idx} className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="text-lg font-bold text-muted-foreground">#{idx + 1}</span>
                          <span>{rep.nombre}</span>
                        </div>
                        <Badge variant="secondary">{rep.cantidad} uds</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Tab: Stock */}
          <TabsContent value="stock" className="space-y-4">
            {alertasStock && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card className={alertasStock.total_critico > 0 ? 'border-red-500 bg-red-50' : ''}>
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm text-muted-foreground">Stock Crítico</p>
                          <p className="text-3xl font-bold text-red-600">{alertasStock.total_critico}</p>
                        </div>
                        <AlertTriangle className="w-10 h-10 text-red-500" />
                      </div>
                      <p className="text-xs text-muted-foreground mt-2">Repuestos sin stock</p>
                    </CardContent>
                  </Card>
                  
                  <Card className={alertasStock.total_bajo > 0 ? 'border-orange-500 bg-orange-50' : ''}>
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm text-muted-foreground">Stock Bajo</p>
                          <p className="text-3xl font-bold text-orange-600">{alertasStock.total_bajo}</p>
                        </div>
                        <Package className="w-10 h-10 text-orange-500" />
                      </div>
                      <p className="text-xs text-muted-foreground mt-2">Por debajo del mínimo</p>
                    </CardContent>
                  </Card>
                </div>

                {alertasStock.alertas.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5 text-orange-500" />
                        Alertas de Stock
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {alertasStock.alertas.map((alerta, idx) => (
                          <div 
                            key={idx} 
                            className={`flex items-center justify-between p-3 rounded-lg ${
                              alerta.nivel === 'critico' ? 'bg-red-50 border border-red-200' : 'bg-orange-50 border border-orange-200'
                            }`}
                          >
                            <div>
                              <p className="font-medium">{alerta.nombre}</p>
                              <p className="text-sm text-muted-foreground">
                                Stock: {alerta.stock} / Mínimo: {alerta.stock_minimo}
                              </p>
                            </div>
                            <Badge variant={alerta.nivel === 'critico' ? 'destructive' : 'warning'}>
                              {alerta.nivel === 'critico' ? 'SIN STOCK' : 'BAJO'}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </TabsContent>
        </Tabs>
      )}

      {/* Recent Orders */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Órdenes Recientes</CardTitle>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/ordenes">
              Ver todas <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {ordenesRecientes.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">No hay órdenes recientes</p>
          ) : (
            <div className="space-y-3">
              {ordenesRecientes.map((orden) => {
                const StatusIcon = statusLabels[orden.estado]?.icon || Clock;
                return (
                  <Link
                    key={orden.id}
                    to={`/ordenes/${orden.id}`}
                    className="flex items-center justify-between p-3 rounded-lg border hover:bg-slate-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full ${statusLabels[orden.estado]?.color || 'bg-gray-500'} flex items-center justify-center text-white`}>
                        <StatusIcon className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="font-medium">{orden.numero_orden}</p>
                        <p className="text-sm text-muted-foreground">{orden.dispositivo?.modelo}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {orden.bloqueada && <Lock className="w-4 h-4 text-orange-500" />}
                      {orden.es_garantia && <Shield className="w-4 h-4 text-red-500" />}
                      <Badge variant="outline">{statusLabels[orden.estado]?.label || orden.estado}</Badge>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

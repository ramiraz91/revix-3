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
  TrendingUp,
  TrendingDown,
  Timer,
  Shield,
  BarChart3,
  Activity,
  Calendar,
  RefreshCw,
  ChevronRight,
  AlertCircle,
  PackageCheck,
  Inbox,
  History
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import API from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';

const statusLabels = {
  pendiente_recibir: { label: 'Pendiente Recibir', color: 'bg-yellow-500', textColor: 'text-yellow-600' },
  recibida: { label: 'Recibida', color: 'bg-blue-500', textColor: 'text-blue-600' },
  en_taller: { label: 'En Taller', color: 'bg-purple-500', textColor: 'text-purple-600' },
  re_presupuestar: { label: 'Re-presupuestar', color: 'bg-orange-500', textColor: 'text-orange-600' },
  reparado: { label: 'Reparado', color: 'bg-green-500', textColor: 'text-green-600' },
  validacion: { label: 'Validación', color: 'bg-indigo-500', textColor: 'text-indigo-600' },
  enviado: { label: 'Enviado', color: 'bg-emerald-500', textColor: 'text-emerald-600' },
  garantia: { label: 'Garantía', color: 'bg-red-500', textColor: 'text-red-600' },
  cancelado: { label: 'Cancelado', color: 'bg-gray-500', textColor: 'text-gray-600' },
};

export default function Dashboard() {
  const navigate = useNavigate();
  const scannerInputRef = useRef(null);
  const { isAdmin, isTecnico, isMaster } = useAuth();
  
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // Scanner states
  const [scannerValue, setScannerValue] = useState('');
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    fetchData();
    // Auto-refresh cada 5 minutos
    const interval = setInterval(fetchData, 300000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async (showRefreshing = false) => {
    try {
      if (showRefreshing) setRefreshing(true);
      else setLoading(true);
      
      const res = await API.get('/dashboard/operativo');
      setData(res.data);
    } catch (err) {
      console.error('Error cargando dashboard:', err);
      toast.error('Error al cargar el dashboard');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => fetchData(true);

  // Scanner logic
  const handleScannerSubmit = async (e) => {
    e.preventDefault();
    if (!scannerValue.trim() || processing) return;
    
    setProcessing(true);
    try {
      const searchValue = scannerValue.trim().toUpperCase();
      const res = await API.get(`/ordenes/buscar?q=${encodeURIComponent(searchValue)}`);
      
      if (res.data.ordenes && res.data.ordenes.length === 1) {
        navigate(`/crm/ordenes/${res.data.ordenes[0].id}`);
      } else if (res.data.ordenes && res.data.ordenes.length > 1) {
        navigate(`/crm/ordenes?buscar=${encodeURIComponent(searchValue)}`);
      } else {
        toast.error('No se encontró ninguna orden');
      }
    } catch (err) {
      toast.error('Error al buscar');
    } finally {
      setProcessing(false);
      setScannerValue('');
    }
  };

  const calcularDiasDesde = (fecha) => {
    if (!fecha) return '-';
    const ahora = new Date();
    const fechaOrden = new Date(fecha);
    const diff = Math.floor((ahora - fechaOrden) / (1000 * 60 * 60 * 24));
    return diff;
  };

  const formatFecha = (fecha) => {
    if (!fecha) return '-';
    return new Date(fecha).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const { kpis, en_taller, ordenes, tiempos, graficos } = data || {};

  return (
    <div className="space-y-6">
      {/* Header con escáner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Dashboard Operativo</h1>
          <p className="text-muted-foreground text-sm">
            Control diario del taller • Actualizado: {new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <form onSubmit={handleScannerSubmit} className="flex gap-2">
            <div className="relative">
              <QrCode className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                ref={scannerInputRef}
                placeholder="Escanear código..."
                value={scannerValue}
                onChange={(e) => setScannerValue(e.target.value)}
                className="pl-9 w-48"
              />
            </div>
            <Button type="submit" disabled={processing} size="sm">
              <Search className="w-4 h-4" />
            </Button>
          </form>
          
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>
      </div>

      {/* KPIs principales */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-9 gap-3">
        {/* Total órdenes */}
        <Card className="bg-gradient-to-br from-slate-700 to-slate-800 border-slate-600">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <ClipboardList className="w-5 h-5 text-white" />
              <span className="text-2xl font-bold text-white">{kpis?.total_ordenes || 0}</span>
            </div>
            <p className="text-xs text-slate-300 mt-1 font-medium">Total Órdenes</p>
          </CardContent>
        </Card>
        
        {/* Enviados */}
        <Card className="bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-950 dark:to-emerald-900 border-emerald-200">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <Send className="w-5 h-5 text-emerald-600" />
              <span className="text-2xl font-bold text-emerald-700">{kpis?.total_enviados || 0}</span>
            </div>
            <p className="text-xs text-emerald-600 mt-1 font-medium">Enviados</p>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950 dark:to-purple-900 border-purple-200">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <Wrench className="w-5 h-5 text-purple-600" />
              <span className="text-2xl font-bold text-purple-700">{kpis?.total_en_taller || 0}</span>
            </div>
            <p className="text-xs text-purple-600 mt-1 font-medium">En Taller</p>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-yellow-50 to-yellow-100 dark:from-yellow-950 dark:to-yellow-900 border-yellow-200">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <Inbox className="w-5 h-5 text-yellow-600" />
              <span className="text-2xl font-bold text-yellow-700">{kpis?.total_pendientes_recibir || 0}</span>
            </div>
            <p className="text-xs text-yellow-600 mt-1 font-medium">Por Recibir</p>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950 dark:to-green-900 border-green-200">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <PackageCheck className="w-5 h-5 text-green-600" />
              <span className="text-2xl font-bold text-green-700">{kpis?.total_reparados || 0}</span>
            </div>
            <p className="text-xs text-green-600 mt-1 font-medium">Reparados</p>
          </CardContent>
        </Card>
        
        <Card className={`bg-gradient-to-br ${kpis?.con_demora > 0 ? 'from-red-50 to-red-100 dark:from-red-950 dark:to-red-900 border-red-200' : 'from-slate-50 to-slate-100 border-slate-200'}`}>
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <AlertCircle className={`w-5 h-5 ${kpis?.con_demora > 0 ? 'text-red-600' : 'text-slate-400'}`} />
              <span className={`text-2xl font-bold ${kpis?.con_demora > 0 ? 'text-red-700' : 'text-slate-500'}`}>
                {kpis?.con_demora || 0}
              </span>
            </div>
            <p className={`text-xs mt-1 font-medium ${kpis?.con_demora > 0 ? 'text-red-600' : 'text-slate-500'}`}>Con Demora</p>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-rose-50 to-rose-100 dark:from-rose-950 dark:to-rose-900 border-rose-200">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <Shield className="w-5 h-5 text-rose-600" />
              <span className="text-2xl font-bold text-rose-700">{kpis?.garantias_activas || 0}</span>
            </div>
            <p className="text-xs text-rose-600 mt-1 font-medium">Garantías</p>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950 dark:to-blue-900 border-blue-200">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <Activity className="w-5 h-5 text-blue-600" />
              <span className="text-2xl font-bold text-blue-700">{kpis?.cambios_hoy || 0}</span>
            </div>
            <p className="text-xs text-blue-600 mt-1 font-medium">Cambios Hoy</p>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 border-slate-200">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <History className="w-5 h-5 text-slate-500" />
              <span className="text-2xl font-bold text-slate-600">{kpis?.cambios_ayer || 0}</span>
            </div>
            <p className="text-xs text-slate-500 mt-1 font-medium">Cambios Ayer</p>
          </CardContent>
        </Card>
      </div>

      {/* Contenido principal - 2 columnas */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Columna izquierda - Estados en taller y métricas */}
        <div className="lg:col-span-2 space-y-6">
          {/* Estados en taller */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Wrench className="w-5 h-5 text-purple-600" />
                    Órdenes en Taller
                  </CardTitle>
                  <CardDescription>Desglose por subestado</CardDescription>
                </div>
                <Badge variant="secondary" className="text-lg px-3 py-1">
                  {en_taller?.total || 0}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-950 border border-blue-200">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                    <span className="text-sm font-medium">Recibidas</span>
                  </div>
                  <span className="text-3xl font-bold text-blue-700">{en_taller?.detalle?.recibidas || 0}</span>
                </div>
                
                <div className="p-4 rounded-lg bg-purple-50 dark:bg-purple-950 border border-purple-200">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-3 h-3 rounded-full bg-purple-500" />
                    <span className="text-sm font-medium">En Reparación</span>
                  </div>
                  <span className="text-3xl font-bold text-purple-700">{en_taller?.detalle?.en_reparacion || 0}</span>
                </div>
                
                <div className="p-4 rounded-lg bg-orange-50 dark:bg-orange-950 border border-orange-200">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-3 h-3 rounded-full bg-orange-500" />
                    <span className="text-sm font-medium">Re-presupuestar</span>
                  </div>
                  <span className="text-3xl font-bold text-orange-700">{en_taller?.detalle?.re_presupuestar || 0}</span>
                </div>
                
                <div className="p-4 rounded-lg bg-indigo-50 dark:bg-indigo-950 border border-indigo-200">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-3 h-3 rounded-full bg-indigo-500" />
                    <span className="text-sm font-medium">Validación</span>
                  </div>
                  <span className="text-3xl font-bold text-indigo-700">{en_taller?.detalle?.validacion || 0}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Órdenes con demora */}
          {ordenes?.con_demora?.length > 0 && (
            <Card className="border-red-200 bg-red-50/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2 text-red-700">
                  <AlertCircle className="w-5 h-5" />
                  Órdenes con Demora (+4 días)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {ordenes.con_demora.slice(0, 5).map((orden) => (
                    <Link
                      key={orden.id}
                      to={`/crm/ordenes/${orden.id}`}
                      className="flex items-center justify-between p-3 rounded-lg bg-white dark:bg-slate-900 border hover:border-red-300 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <Badge variant="outline" className={statusLabels[orden.estado]?.textColor}>
                          {statusLabels[orden.estado]?.label || orden.estado}
                        </Badge>
                        <div>
                          <p className="font-medium text-sm">{orden.numero_orden}</p>
                          <p className="text-xs text-muted-foreground">
                            {orden.dispositivo?.modelo || 'Sin modelo'}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge variant="destructive" className="text-xs">
                          {orden.dias_demora} días
                        </Badge>
                      </div>
                    </Link>
                  ))}
                  {ordenes.con_demora.length > 5 && (
                    <Link to="/crm/ordenes?filtro=demora" className="flex items-center justify-center gap-2 p-2 text-sm text-red-600 hover:text-red-700">
                      Ver todas ({ordenes.con_demora.length})
                      <ChevronRight className="w-4 h-4" />
                    </Link>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Gráfico de órdenes de la semana */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-primary" />
                Órdenes esta Semana
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={graficos?.ordenes_semana || []}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis 
                      dataKey="fecha" 
                      tickFormatter={(val) => new Date(val).toLocaleDateString('es-ES', { weekday: 'short' })}
                      fontSize={12}
                    />
                    <YAxis fontSize={12} />
                    <Tooltip 
                      labelFormatter={(val) => new Date(val).toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'short' })}
                    />
                    <Bar dataKey="total" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Métricas de tiempo */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Timer className="w-5 h-5 text-primary" />
                Métricas de Tiempo
              </CardTitle>
              <CardDescription>Basado en las últimas {tiempos?.ordenes_analizadas || 0} órdenes completadas</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm text-muted-foreground mb-1">Tiempo Promedio Total</p>
                  <p className="text-3xl font-bold">{tiempos?.promedio_total_dias?.toFixed(1) || 0}</p>
                  <p className="text-sm text-muted-foreground">días</p>
                </div>
                <div className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm text-muted-foreground mb-1">En horas</p>
                  <p className="text-3xl font-bold">{tiempos?.promedio_total_horas?.toFixed(0) || 0}</p>
                  <p className="text-sm text-muted-foreground">horas</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Columna derecha - Listas */}
        <div className="space-y-6">
          {/* Pendientes de recibir */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <Inbox className="w-4 h-4 text-yellow-600" />
                  Pendientes de Recibir
                </CardTitle>
                <Badge variant="outline">{ordenes?.pendientes_recibir?.length || 0}</Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              {ordenes?.pendientes_recibir?.length > 0 ? (
                <div className="space-y-2">
                  {ordenes.pendientes_recibir.slice(0, 5).map((orden) => (
                    <Link
                      key={orden.id}
                      to={`/crm/ordenes/${orden.id}`}
                      className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div>
                        <p className="font-medium text-sm">{orden.numero_orden}</p>
                        <p className="text-xs text-muted-foreground">
                          {orden.dispositivo?.modelo || 'Sin modelo'}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">{orden.agencia_envio || '-'}</p>
                        <p className="text-xs font-mono">{orden.codigo_recogida_entrada?.slice(0, 10) || '-'}</p>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">Sin órdenes pendientes</p>
              )}
            </CardContent>
          </Card>

          {/* Últimos reparados */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-green-600" />
                  Últimos Reparados
                </CardTitle>
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                  {kpis?.total_reparados || 0}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              {ordenes?.ultimos_reparados?.length > 0 ? (
                <div className="space-y-2">
                  {ordenes.ultimos_reparados.slice(0, 5).map((orden) => (
                    <Link
                      key={orden.id}
                      to={`/crm/ordenes/${orden.id}`}
                      className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div>
                        <p className="font-medium text-sm">{orden.numero_orden}</p>
                        <p className="text-xs text-muted-foreground">
                          {orden.dispositivo?.modelo || 'Sin modelo'}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">{formatFecha(orden.updated_at)}</p>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">Sin órdenes reparadas</p>
              )}
            </CardContent>
          </Card>

          {/* Últimos enviados */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <Send className="w-4 h-4 text-emerald-600" />
                  Últimos Enviados
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              {ordenes?.ultimos_enviados?.length > 0 ? (
                <div className="space-y-2">
                  {ordenes.ultimos_enviados.slice(0, 5).map((orden) => (
                    <Link
                      key={orden.id}
                      to={`/crm/ordenes/${orden.id}`}
                      className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div>
                        <p className="font-medium text-sm">{orden.numero_orden}</p>
                        <p className="text-xs text-muted-foreground">
                          {orden.dispositivo?.modelo || 'Sin modelo'}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">{orden.agencia_envio || '-'}</p>
                        <p className="text-xs">{formatFecha(orden.updated_at)}</p>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">Sin envíos recientes</p>
              )}
            </CardContent>
          </Card>

          {/* Accesos rápidos */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Accesos Rápidos</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="grid grid-cols-2 gap-2">
                <Button variant="outline" size="sm" asChild className="justify-start">
                  <Link to="/crm/ordenes/nueva">
                    <ClipboardList className="w-4 h-4 mr-2" />
                    Nueva Orden
                  </Link>
                </Button>
                <Button variant="outline" size="sm" asChild className="justify-start">
                  <Link to="/crm/clientes">
                    <Users className="w-4 h-4 mr-2" />
                    Clientes
                  </Link>
                </Button>
                <Button variant="outline" size="sm" asChild className="justify-start">
                  <Link to="/crm/inventario">
                    <Package className="w-4 h-4 mr-2" />
                    Inventario
                  </Link>
                </Button>
                <Button variant="outline" size="sm" asChild className="justify-start">
                  <Link to="/crm/envios">
                    <Truck className="w-4 h-4 mr-2" />
                    Envíos
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

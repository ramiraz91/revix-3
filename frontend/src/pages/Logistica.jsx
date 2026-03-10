import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Package, 
  Truck, 
  Search, 
  AlertTriangle, 
  Clock, 
  CheckCircle2,
  Phone,
  MapPin,
  ExternalLink,
  RefreshCw,
  Filter
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function Logistica() {
  const [resumen, setResumen] = useState(null);
  const [recogidas, setRecogidas] = useState([]);
  const [envios, setEnvios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busqueda, setBusqueda] = useState('');
  const [filtroRecogidas, setFiltroRecogidas] = useState('todos');
  const [filtroEnvios, setFiltroEnvios] = useState('todos');
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      // Fetch resumen
      const resumenRes = await fetch(`${API_URL}/api/logistica/resumen`, { headers });
      if (resumenRes.ok) {
        setResumen(await resumenRes.json());
      }

      // Fetch recogidas
      let recogidasUrl = `${API_URL}/api/logistica/recogidas?limit=100`;
      if (filtroRecogidas !== 'todos') recogidasUrl += `&estado=${filtroRecogidas}`;
      if (busqueda) recogidasUrl += `&busqueda=${encodeURIComponent(busqueda)}`;
      
      const recogidasRes = await fetch(recogidasUrl, { headers });
      if (recogidasRes.ok) {
        setRecogidas(await recogidasRes.json());
      }

      // Fetch envios
      let enviosUrl = `${API_URL}/api/logistica/envios?limit=100`;
      if (filtroEnvios !== 'todos') enviosUrl += `&estado=${filtroEnvios}`;
      if (busqueda) enviosUrl += `&busqueda=${encodeURIComponent(busqueda)}`;
      
      const enviosRes = await fetch(enviosUrl, { headers });
      if (enviosRes.ok) {
        setEnvios(await enviosRes.json());
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Error al cargar datos de logística');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filtroRecogidas, filtroEnvios]);

  const handleBuscar = (e) => {
    e.preventDefault();
    fetchData();
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const formatHoras = (horas) => {
    if (!horas) return '-';
    if (horas < 1) return `${Math.round(horas * 60)} min`;
    if (horas < 24) return `${Math.round(horas)}h`;
    const dias = Math.floor(horas / 24);
    const horasRestantes = Math.round(horas % 24);
    return `${dias}d ${horasRestantes}h`;
  };

  const formatFecha = (fecha) => {
    if (!fecha) return '-';
    return new Date(fecha).toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const LogisticaItem = ({ item, tipo }) => {
    const isRetraso = item.en_retraso;
    const isPendiente = item.estado === 'pendiente';
    
    return (
      <div 
        className={`p-4 border rounded-lg hover:bg-slate-50 transition-colors ${
          isRetraso ? 'border-red-300 bg-red-50' : ''
        }`}
        data-testid={`${tipo}-item-${item.orden_id}`}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center gap-2 mb-1">
              <Link 
                to={`/ordenes/${item.orden_id}`}
                className="font-mono text-sm font-semibold hover:text-blue-600"
              >
                {item.numero_autorizacion || item.numero_orden}
              </Link>
              {isPendiente ? (
                <Badge variant="outline" className="text-yellow-600 border-yellow-300">
                  <Clock className="w-3 h-3 mr-1" />
                  Pendiente
                </Badge>
              ) : (
                <Badge variant="outline" className="text-green-600 border-green-300">
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  Completado
                </Badge>
              )}
              {isRetraso && (
                <Badge variant="destructive" className="gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  +48h
                </Badge>
              )}
            </div>
            
            {/* Dispositivo */}
            <p className="text-sm font-medium">{item.dispositivo_modelo}</p>
            
            {/* Cliente */}
            <p className="text-sm text-muted-foreground">{item.cliente_nombre}</p>
            
            {/* Dirección y teléfono */}
            <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
              {item.direccion && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {item.direccion}, {item.ciudad}
                </span>
              )}
              {item.cliente_telefono && (
                <span className="flex items-center gap-1">
                  <Phone className="w-3 h-3" />
                  {item.cliente_telefono}
                </span>
              )}
            </div>
            
            {/* Código tracking */}
            {item.codigo_tracking && (
              <p className="text-xs font-mono mt-1 text-blue-600">
                Tracking: {item.codigo_tracking}
              </p>
            )}
          </div>
          
          {/* Tiempo */}
          <div className="text-right">
            <p className={`text-lg font-bold ${isRetraso ? 'text-red-600' : 'text-slate-700'}`}>
              {formatHoras(item.horas_transcurridas)}
            </p>
            <p className="text-xs text-muted-foreground">
              {isPendiente ? 'en espera' : 'tardó'}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {formatFecha(item.fecha_solicitud)}
            </p>
          </div>
        </div>
        
        {/* Acciones */}
        <div className="flex items-center gap-2 mt-3 pt-3 border-t">
          <Link to={`/ordenes/${item.orden_id}`}>
            <Button variant="outline" size="sm">
              <ExternalLink className="w-3 h-3 mr-1" />
              Ver Orden
            </Button>
          </Link>
          {item.cliente_telefono && (
            <Button variant="ghost" size="sm" asChild>
              <a href={`tel:${item.cliente_telefono}`}>
                <Phone className="w-3 h-3 mr-1" />
                Llamar
              </a>
            </Button>
          )}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-10 bg-slate-200 rounded w-48" />
        <div className="grid grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="h-24 bg-slate-200 rounded-lg" />)}
        </div>
        <div className="h-96 bg-slate-200 rounded-lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="logistica-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Control de Logística</h1>
          <p className="text-muted-foreground">Gestión de recogidas y envíos</p>
        </div>
        <Button variant="outline" onClick={handleRefresh} disabled={refreshing}>
          <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          Actualizar
        </Button>
      </div>

      {/* Resumen */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 rounded-lg">
                <Package className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{resumen?.total_recogidas_pendientes || 0}</p>
                <p className="text-xs text-muted-foreground">Recogidas pendientes</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <Truck className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{resumen?.total_envios_pendientes || 0}</p>
                <p className="text-xs text-muted-foreground">Envíos pendientes</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className={resumen?.recogidas_en_retraso > 0 ? 'border-red-300 bg-red-50' : ''}>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${resumen?.recogidas_en_retraso > 0 ? 'bg-red-200' : 'bg-slate-100'}`}>
                <AlertTriangle className={`w-5 h-5 ${resumen?.recogidas_en_retraso > 0 ? 'text-red-600' : 'text-slate-400'}`} />
              </div>
              <div>
                <p className={`text-2xl font-bold ${resumen?.recogidas_en_retraso > 0 ? 'text-red-600' : ''}`}>
                  {resumen?.recogidas_en_retraso || 0}
                </p>
                <p className="text-xs text-muted-foreground">Recogidas +48h</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className={resumen?.envios_en_retraso > 0 ? 'border-red-300 bg-red-50' : ''}>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${resumen?.envios_en_retraso > 0 ? 'bg-red-200' : 'bg-slate-100'}`}>
                <AlertTriangle className={`w-5 h-5 ${resumen?.envios_en_retraso > 0 ? 'text-red-600' : 'text-slate-400'}`} />
              </div>
              <div>
                <p className={`text-2xl font-bold ${resumen?.envios_en_retraso > 0 ? 'text-red-600' : ''}`}>
                  {resumen?.envios_en_retraso || 0}
                </p>
                <p className="text-xs text-muted-foreground">Envíos +48h</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <CheckCircle2 className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{resumen?.completados_hoy || 0}</p>
                <p className="text-xs text-muted-foreground">Completados hoy</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Buscador */}
      <Card>
        <CardContent className="pt-4">
          <form onSubmit={handleBuscar} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por número de orden o autorización..."
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                className="pl-9"
                data-testid="search-input"
              />
            </div>
            <Button type="submit">
              <Search className="w-4 h-4 mr-2" />
              Buscar
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="recogidas" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="recogidas" className="gap-2">
            <Package className="w-4 h-4" />
            Recogidas ({recogidas.length})
          </TabsTrigger>
          <TabsTrigger value="envios" className="gap-2">
            <Truck className="w-4 h-4" />
            Envíos ({envios.length})
          </TabsTrigger>
        </TabsList>

        {/* Tab Recogidas */}
        <TabsContent value="recogidas" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Package className="w-5 h-5" />
                  Recogidas
                </CardTitle>
                <Select value={filtroRecogidas} onValueChange={setFiltroRecogidas}>
                  <SelectTrigger className="w-40">
                    <Filter className="w-4 h-4 mr-2" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="todos">Todos</SelectItem>
                    <SelectItem value="pendiente">Pendientes</SelectItem>
                    <SelectItem value="completada">Completadas</SelectItem>
                    <SelectItem value="retraso">En retraso (+48h)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              {recogidas.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  No hay recogidas que mostrar
                </p>
              ) : (
                <div className="space-y-3">
                  {recogidas.map((item) => (
                    <LogisticaItem key={item.orden_id} item={item} tipo="recogida" />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab Envíos */}
        <TabsContent value="envios" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Truck className="w-5 h-5" />
                  Envíos
                </CardTitle>
                <Select value={filtroEnvios} onValueChange={setFiltroEnvios}>
                  <SelectTrigger className="w-40">
                    <Filter className="w-4 h-4 mr-2" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="todos">Todos</SelectItem>
                    <SelectItem value="pendiente">Pendientes</SelectItem>
                    <SelectItem value="completado">Completados</SelectItem>
                    <SelectItem value="retraso">En retraso (+48h)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              {envios.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  No hay envíos que mostrar
                </p>
              ) : (
                <div className="space-y-3">
                  {envios.map((item) => (
                    <LogisticaItem key={item.orden_id} item={item} tipo="envio" />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

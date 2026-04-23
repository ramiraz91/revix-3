import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Truck, AlertTriangle, PackageCheck, RefreshCw, Download,
  Filter, ShieldAlert, Search, ExternalLink, Loader2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import API from '@/lib/api';
import { toast } from 'sonner';

const ESTADO_COLOR_BADGE = {
  green: 'bg-green-100 text-green-800 border-green-300',
  blue: 'bg-blue-100 text-blue-800 border-blue-300',
  amber: 'bg-amber-100 text-amber-800 border-amber-300',
  red: 'bg-red-100 text-red-800 border-red-300',
  slate: 'bg-slate-100 text-slate-800 border-slate-300',
};

function formatDT(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '—';
  return `${d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: '2-digit' })} · ${d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}`;
}

export default function LogisticaPanel() {
  const navigate = useNavigate();
  const [resumen, setResumen] = useState(null);
  const [envios, setEnvios] = useState([]);
  const [totalEnvios, setTotalEnvios] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [updatingAll, setUpdatingAll] = useState(false);

  // filtros
  const [busqueda, setBusqueda] = useState('');
  const [estadoFilter, setEstadoFilter] = useState('ALL');
  const [transportistaFilter, setTransportistaFilter] = useState('ALL');
  const [soloIncidencias, setSoloIncidencias] = useState(false);
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');

  const pollRef = useRef(null);

  const cargarDatos = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true);
    try {
      const params = new URLSearchParams();
      if (estadoFilter !== 'ALL') params.set('estado', estadoFilter);
      if (transportistaFilter !== 'ALL') params.set('transportista', transportistaFilter);
      if (soloIncidencias) params.set('solo_incidencias', 'true');
      if (fechaDesde) params.set('fecha_desde', fechaDesde);
      if (fechaHasta) params.set('fecha_hasta', fechaHasta);
      params.set('page', '1');
      params.set('page_size', '500');

      const [resR, resE] = await Promise.all([
        API.get('/logistica/panel/resumen'),
        API.get(`/logistica/panel/envios?${params.toString()}`),
      ]);
      setResumen(resR.data);
      setEnvios(resE.data.items || []);
      setTotalEnvios(resE.data.total || 0);
    } catch (err) {
      if (!silent) toast.error('Error cargando panel de logística');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [estadoFilter, transportistaFilter, soloIncidencias, fechaDesde, fechaHasta]);

  useEffect(() => {
    cargarDatos(false);
  }, [cargarDatos]);

  // Polling cada 5 min
  useEffect(() => {
    pollRef.current = setInterval(() => cargarDatos(true), 300000);
    return () => clearInterval(pollRef.current);
  }, [cargarDatos]);

  const handleActualizarTodos = async () => {
    setUpdatingAll(true);
    try {
      const { data } = await API.post('/logistica/panel/actualizar-todos');
      toast.success(
        `Tracking refrescado. Procesados: ${data.procesados} · Cambios: ${data.cambios_estado}` +
        (data.preview ? ' (PREVIEW)' : ''),
      );
      await cargarDatos(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error refrescando tracking');
    } finally {
      setUpdatingAll(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      const params = new URLSearchParams();
      if (estadoFilter !== 'ALL') params.set('estado', estadoFilter);
      if (transportistaFilter !== 'ALL') params.set('transportista', transportistaFilter);
      if (soloIncidencias) params.set('solo_incidencias', 'true');
      if (fechaDesde) params.set('fecha_desde', fechaDesde);
      if (fechaHasta) params.set('fecha_hasta', fechaHasta);

      const resp = await API.get(`/logistica/panel/export-csv?${params.toString()}`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `logistica-envios-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success('CSV exportado');
    } catch {
      toast.error('Error exportando CSV');
    }
  };

  // búsqueda client-side
  const enviosFiltrados = busqueda.trim()
    ? envios.filter((e) => {
        const q = busqueda.trim().toLowerCase();
        return (
          e.numero_orden.toLowerCase().includes(q) ||
          e.numero_autorizacion.toLowerCase().includes(q) ||
          e.codbarras.toLowerCase().includes(q) ||
          e.cliente_nombre.toLowerCase().includes(q) ||
          e.cliente_telefono.includes(q)
        );
      })
    : envios;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="logistica-panel">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Truck className="w-6 h-6 text-blue-600" />
            Panel de Logística
          </h1>
          <p className="text-muted-foreground text-sm">
            Envíos y recogidas en tiempo real · auto-refresh cada 5 min
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => cargarDatos(false)}
            disabled={refreshing}
            data-testid="btn-refrescar-panel"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refrescar
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={handleActualizarTodos}
            disabled={updatingAll}
            data-testid="btn-actualizar-todos"
          >
            {updatingAll ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Actualizar todos
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCSV}
            data-testid="btn-export-csv"
          >
            <Download className="w-4 h-4 mr-2" />
            Exportar CSV
          </Button>
        </div>
      </div>

      {/* Tarjetas resumen */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Card className="bg-blue-50 border-blue-200" data-testid="card-envios-activos">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <Truck className="w-5 h-5 text-blue-600" />
              <span className="text-3xl font-bold text-blue-700">{resumen?.envios_activos || 0}</span>
            </div>
            <p className="text-xs text-blue-600 mt-1 font-medium">Envíos activos</p>
          </CardContent>
        </Card>
        <Card className="bg-green-50 border-green-200" data-testid="card-entregados-hoy">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <PackageCheck className="w-5 h-5 text-green-600" />
              <span className="text-3xl font-bold text-green-700">{resumen?.entregados_hoy || 0}</span>
            </div>
            <p className="text-xs text-green-600 mt-1 font-medium">Entregados hoy</p>
          </CardContent>
        </Card>
        <Card className="bg-red-50 border-red-200" data-testid="card-incidencias">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              <span className="text-3xl font-bold text-red-700">{resumen?.incidencias_activas || 0}</span>
            </div>
            <p className="text-xs text-red-600 mt-1 font-medium">Incidencias activas</p>
          </CardContent>
        </Card>
        <Card className="bg-amber-50 border-amber-200" data-testid="card-recogidas">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <Truck className="w-5 h-5 text-amber-600" />
              <span className="text-3xl font-bold text-amber-700">{resumen?.recogidas_pendientes || 0}</span>
            </div>
            <p className="text-xs text-amber-600 mt-1 font-medium">Recogidas (MRW)</p>
          </CardContent>
        </Card>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[220px] relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Buscar OT, cliente, codbarras..."
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                className="pl-9"
                data-testid="input-busqueda-envios"
              />
            </div>
            <div className="w-[160px]">
              <label className="text-xs text-muted-foreground">Estado</label>
              <Select value={estadoFilter} onValueChange={setEstadoFilter}>
                <SelectTrigger data-testid="select-estado-envios">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Todos</SelectItem>
                  <SelectItem value="ACTIVO">Activos</SelectItem>
                  <SelectItem value="ENTREGADO">Entregados</SelectItem>
                  <SelectItem value="INCIDENCIA">Con incidencia</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-[140px]">
              <label className="text-xs text-muted-foreground">Transportista</label>
              <Select value={transportistaFilter} onValueChange={setTransportistaFilter}>
                <SelectTrigger data-testid="select-transportista">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Todos</SelectItem>
                  <SelectItem value="GLS">GLS</SelectItem>
                  <SelectItem value="MRW" disabled>MRW (próximamente)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Desde</label>
              <Input
                type="date"
                value={fechaDesde}
                onChange={(e) => setFechaDesde(e.target.value)}
                data-testid="input-fecha-desde"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Hasta</label>
              <Input
                type="date"
                value={fechaHasta}
                onChange={(e) => setFechaHasta(e.target.value)}
                data-testid="input-fecha-hasta"
              />
            </div>
            <Button
              variant={soloIncidencias ? 'destructive' : 'outline'}
              size="sm"
              onClick={() => setSoloIncidencias(!soloIncidencias)}
              data-testid="btn-solo-incidencias"
            >
              <ShieldAlert className="w-4 h-4 mr-2" />
              {soloIncidencias ? 'Todos' : 'Solo incidencias'}
            </Button>
            {(estadoFilter !== 'ALL' || transportistaFilter !== 'ALL' || fechaDesde
              || fechaHasta || soloIncidencias || busqueda) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setBusqueda('');
                  setEstadoFilter('ALL');
                  setTransportistaFilter('ALL');
                  setSoloIncidencias(false);
                  setFechaDesde('');
                  setFechaHasta('');
                }}
                data-testid="btn-limpiar-filtros"
              >
                Limpiar
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Tabla */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Filter className="w-4 h-4" /> Envíos ({enviosFiltrados.length}{totalEnvios !== enviosFiltrados.length ? ` / ${totalEnvios}` : ''})
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {enviosFiltrados.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Truck className="w-10 h-10 mx-auto mb-2 opacity-40" />
              Sin envíos que coincidan con los filtros
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>OT</TableHead>
                    <TableHead>Cliente</TableHead>
                    <TableHead>Transp.</TableHead>
                    <TableHead>Codbarras</TableHead>
                    <TableHead>Ref. autorización</TableHead>
                    <TableHead>Estado interno</TableHead>
                    <TableHead>Creado</TableHead>
                    <TableHead>Últ. actualización</TableHead>
                    <TableHead className="w-12"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {enviosFiltrados.map((e) => (
                    <TableRow
                      key={`${e.order_id}-${e.codbarras}`}
                      className="cursor-pointer hover:bg-slate-50"
                      onClick={() => navigate(`/crm/ordenes/${e.order_id}`)}
                      data-testid={`envio-row-${e.codbarras}`}
                    >
                      <TableCell>
                        <p className="font-mono text-sm font-medium">{e.numero_orden}</p>
                      </TableCell>
                      <TableCell>
                        <p className="font-medium text-sm">{e.cliente_nombre || '—'}</p>
                        <p className="text-xs text-muted-foreground">{e.cliente_telefono}</p>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="font-mono">{e.transportista}</Badge>
                        {e.mock_preview && (
                          <Badge variant="outline" className="ml-1 text-[9px] bg-yellow-50">mock</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <p className="font-mono text-xs">{e.codbarras}</p>
                      </TableCell>
                      <TableCell>
                        {e.numero_autorizacion ? (
                          <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded">
                            {e.numero_autorizacion}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          {e.tiene_incidencia && (
                            <AlertTriangle
                              className="w-4 h-4 text-red-500"
                              title={e.incidencia}
                              data-testid={`incidencia-${e.codbarras}`}
                            />
                          )}
                          <Badge
                            variant="outline"
                            className={`font-mono text-[10px] ${ESTADO_COLOR_BADGE[e.estado_color] || ESTADO_COLOR_BADGE.slate}`}
                          >
                            {e.estado_interno || '—'}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDT(e.creado_en)}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDT(e.ultima_actualizacion)}
                      </TableCell>
                      <TableCell onClick={(ev) => ev.stopPropagation()}>
                        {e.tracking_url && (
                          <a
                            href={e.tracking_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-blue-600 hover:text-blue-800"
                            title="Abrir tracking público"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

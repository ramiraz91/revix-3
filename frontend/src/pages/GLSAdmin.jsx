import { useState, useEffect, useCallback } from 'react';
import { Package, Search, RefreshCw, ExternalLink, ArrowDown, ArrowUp, FileDown, Eye, Loader2, Trash2, RotateCw, X, Clock, MapPin, User, Phone, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import api from '@/lib/api';
import { buildGLSTrackingUrl } from '@/lib/glsTracking';

const STATE_COLORS = {
  grabado: 'bg-slate-100 text-slate-700',
  manifestado: 'bg-blue-100 text-blue-700',
  en_transito: 'bg-indigo-100 text-indigo-700',
  en_delegacion: 'bg-cyan-100 text-cyan-700',
  en_reparto: 'bg-purple-100 text-purple-700',
  en_parcelshop: 'bg-teal-100 text-teal-700',
  entregado: 'bg-green-100 text-green-700',
  entregado_parcial: 'bg-lime-100 text-lime-700',
  en_devolucion: 'bg-orange-100 text-orange-700',
  devuelto: 'bg-red-100 text-red-700',
  anulado: 'bg-gray-100 text-gray-500',
  retenido: 'bg-amber-100 text-amber-700',
  recanalizado: 'bg-yellow-100 text-yellow-700',
  cerrado: 'bg-gray-200 text-gray-700',
  error: 'bg-red-200 text-red-800',
};

export default function GLSAdmin() {
  const [envios, setEnvios] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('');
  const [filtroTipo, setFiltroTipo] = useState('');
  const [syncing, setSyncing] = useState(false);
  // Detail modal
  const [detalle, setDetalle] = useState(null);
  const [detalleOpen, setDetalleOpen] = useState(false);
  const [loadingDetalle, setLoadingDetalle] = useState(false);

  const fetchEnvios = useCallback(async (autoSync = false) => {
    setLoading(true);
    try {
      // Si autoSync está activo, primero sincronizamos los envíos activos con GLS
      if (autoSync) {
        setSyncing(true);
        try {
          await api.post('/gls/sync');
        } catch (e) {
          // Silenciar error de sync, continuar con la carga
        } finally {
          setSyncing(false);
        }
      }
      
      const params = new URLSearchParams({ page, limit: 30 });
      if (search) params.set('search', search);
      if (filtroEstado) params.set('estado', filtroEstado);
      if (filtroTipo) params.set('tipo', filtroTipo);
      const res = await api.get(`/gls/envios?${params}`);
      setEnvios(res.data.data || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      toast.error('Error cargando envíos GLS');
    } finally {
      setLoading(false);
    }
  }, [page, search, filtroEstado, filtroTipo]);

  // Auto-sync al cargar la página por primera vez
  useEffect(() => { 
    fetchEnvios(true); // true = sincronizar automáticamente al cargar
  }, []);
  
  // Recargar sin sync cuando cambian los filtros
  useEffect(() => { 
    fetchEnvios(false); 
  }, [page, search, filtroEstado, filtroTipo]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await api.post('/gls/sync');
      toast.success(`Sincronización: ${res.data.synced} actualizados, ${res.data.errors} errores`);
      fetchEnvios();
    } catch (err) {
      toast.error('Error en sincronización');
    } finally {
      setSyncing(false);
    }
  };

  const handleSyncSingle = async (id) => {
    try {
      await api.post(`/gls/sync/${id}`);
      toast.success('Tracking actualizado');
      fetchEnvios();
      if (detalle?.id === id) openDetalle(id);
    } catch (err) {
      toast.error('Error al sincronizar');
    }
  };

  const handleAnular = async (id) => {
    if (!window.confirm('¿Anular este envío?')) return;
    try {
      await api.delete(`/gls/envios/${id}`);
      toast.success('Envío anulado');
      fetchEnvios();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al anular');
    }
  };

  const handleDescargarEtiqueta = async (id) => {
    try {
      const res = await api.get(`/gls/etiqueta/${id}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `etiqueta_gls_${id.substring(0, 8)}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      toast.error('Etiqueta no disponible');
    }
  };

  const openDetalle = async (id) => {
    setLoadingDetalle(true);
    setDetalleOpen(true);
    try {
      const res = await api.get(`/gls/envios/${id}`);
      setDetalle(res.data);
    } catch (err) {
      toast.error('Error cargando detalle');
    } finally {
      setLoadingDetalle(false);
    }
  };

  const handleBuscar = (e) => {
    e.preventDefault();
    setPage(1);
    fetchEnvios();
  };

  return (
    <div className="space-y-4" data-testid="gls-admin-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><Package className="w-6 h-6" /> Logística GLS</h1>
          <p className="text-muted-foreground text-sm">{total} envío(s) registrados</p>
        </div>
        <Button onClick={handleSync} disabled={syncing} variant="outline" data-testid="btn-sync-all">
          {syncing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
          Sincronizar todo
        </Button>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="py-3">
          <form onSubmit={handleBuscar} className="flex items-center gap-3">
            <Input placeholder="Buscar por código, referencia, cliente..." value={search} onChange={(e) => setSearch(e.target.value)} className="flex-1" data-testid="gls-admin-search" />
            <Select value={filtroEstado} onValueChange={(v) => { setFiltroEstado(v === 'all' ? '' : v); setPage(1); }}>
              <SelectTrigger className="w-48"><SelectValue placeholder="Estado" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                {Object.keys(STATE_COLORS).map(s => <SelectItem key={s} value={s}>{s.replace(/_/g, ' ')}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={filtroTipo} onValueChange={(v) => { setFiltroTipo(v === 'all' ? '' : v); setPage(1); }}>
              <SelectTrigger className="w-36"><SelectValue placeholder="Tipo" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="envio">Envío</SelectItem>
                <SelectItem value="recogida">Recogida</SelectItem>
              </SelectContent>
            </Select>
            <Button type="submit"><Search className="w-4 h-4" /></Button>
          </form>
        </CardContent>
      </Card>

      {/* Lista */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin" />
          {syncing && <p className="text-sm text-muted-foreground mt-2">Consultando estado actual en GLS...</p>}
        </div>
      ) : envios.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <Package className="w-16 h-16 mx-auto mb-4 opacity-30" />
          <p className="text-lg">No hay envíos GLS registrados</p>
        </div>
      ) : (
        <div className="space-y-2">
          {envios.map((e) => (
            <div key={e.id} className="p-4 bg-white rounded-lg border hover:border-orange-200 transition-colors cursor-pointer" onClick={() => openDetalle(e.id)} data-testid={`gls-row-${e.id}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 flex-1">
                  {e.tipo === 'recogida' ? <ArrowDown className="w-5 h-5 text-amber-600 shrink-0" /> : <ArrowUp className="w-5 h-5 text-green-600 shrink-0" />}
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium capitalize">{e.tipo}</span>
                      <Badge variant="outline" className="font-mono text-xs">{e.gls_codbarras || '-'}</Badge>
                      <Badge className={`text-xs ${STATE_COLORS[e.estado_interno] || 'bg-gray-100'}`}>
                        {e.estado_interno?.replace(/_/g, ' ')}
                      </Badge>
                      {e.incidencia_texto && <Badge variant="destructive" className="text-xs">Incidencia</Badge>}
                    </div>
                    <p className="text-sm text-muted-foreground truncate">
                      {e.destinatario?.nombre} · Ref: {e.referencia_interna || '-'} · {new Date(e.created_at).toLocaleDateString('es-ES')}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0" onClick={(ev) => ev.stopPropagation()}>
                  <Button variant="ghost" size="icon" onClick={() => handleSyncSingle(e.id)} title="Actualizar tracking"><RotateCw className="w-4 h-4" /></Button>
                  <Button variant="ghost" size="icon" onClick={() => handleDescargarEtiqueta(e.id)} title="Descargar etiqueta"><FileDown className="w-4 h-4" /></Button>
                  {!e.es_final && <Button variant="ghost" size="icon" onClick={() => handleAnular(e.id)} title="Anular"><Trash2 className="w-4 h-4 text-red-500" /></Button>}
                  {(e.tracking_url || e.gls_codbarras) && (
                    <a href={buildGLSTrackingUrl(e)} target="_blank" rel="noopener noreferrer" className="p-2" title="Tracking público">
                      <ExternalLink className="w-4 h-4 text-blue-500" />
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}
          {/* Pagination */}
          {total > 30 && (
            <div className="flex justify-center gap-2 pt-4">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Anterior</Button>
              <span className="px-3 py-1 text-sm text-muted-foreground">Página {page} de {Math.ceil(total / 30)}</span>
              <Button variant="outline" size="sm" disabled={page >= Math.ceil(total / 30)} onClick={() => setPage(p => p + 1)}>Siguiente</Button>
            </div>
          )}
        </div>
      )}

      {/* Detalle Modal */}
      <Dialog open={detalleOpen} onOpenChange={setDetalleOpen}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto" data-testid="gls-detail-modal">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="w-5 h-5" /> Detalle del Envío GLS
            </DialogTitle>
          </DialogHeader>
          {loadingDetalle ? (
            <div className="flex justify-center py-8"><Loader2 className="w-8 h-8 animate-spin" /></div>
          ) : detalle ? (
            <div className="space-y-4">
              {/* Header */}
              <div className="flex items-center gap-3 flex-wrap">
                <Badge className={`${STATE_COLORS[detalle.estado_interno] || 'bg-gray-100'} text-sm px-3 py-1`}>
                  {detalle.estado_gls_texto || detalle.estado_interno}
                </Badge>
                <Badge variant="outline" className="font-mono">{detalle.gls_codbarras}</Badge>
                {detalle.gls_codexp && <Badge variant="outline">Exp: {detalle.gls_codexp}</Badge>}
                <span className="text-sm text-muted-foreground capitalize">{detalle.tipo}</span>
              </div>

              <Separator />

              {/* Datos principales */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground uppercase">Referencia</p>
                  <p className="font-mono">{detalle.referencia_interna}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase">Servicio</p>
                  <p>{detalle.servicio} / Horario {detalle.horario}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase">Bultos / Peso</p>
                  <p>{detalle.bultos} bulto(s) · {detalle.peso} kg</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase">Creado</p>
                  <p>{new Date(detalle.created_at).toLocaleString('es-ES')} por {detalle.created_by}</p>
                </div>
              </div>

              {/* Destinatario */}
              {detalle.destinatario && (
                <Card>
                  <CardHeader className="py-2 px-4"><CardTitle className="text-sm flex items-center gap-1"><User className="w-4 h-4" /> Destinatario</CardTitle></CardHeader>
                  <CardContent className="px-4 pb-3 text-sm">
                    <p className="font-medium">{detalle.destinatario.nombre}</p>
                    <p className="text-muted-foreground flex items-center gap-1"><MapPin className="w-3 h-3" /> {detalle.destinatario.direccion}, {detalle.destinatario.cp} {detalle.destinatario.poblacion}</p>
                    {detalle.destinatario.telefono && <p className="flex items-center gap-1"><Phone className="w-3 h-3" /> {detalle.destinatario.telefono}</p>}
                  </CardContent>
                </Card>
              )}

              {/* Entrega */}
              {detalle.entrega_receptor && (
                <Card className="border-green-200 bg-green-50">
                  <CardContent className="py-3 px-4 text-sm">
                    <p className="font-medium text-green-700">Entregado a: {detalle.entrega_receptor}</p>
                    {detalle.entrega_dni && <p>DNI: {detalle.entrega_dni}</p>}
                    {detalle.entrega_fecha && <p>Fecha: {detalle.entrega_fecha}</p>}
                  </CardContent>
                </Card>
              )}

              {/* Incidencia */}
              {detalle.incidencia_texto && (
                <Card className="border-red-200 bg-red-50">
                  <CardContent className="py-3 px-4 text-sm flex items-center gap-2 text-red-700">
                    <AlertTriangle className="w-4 h-4" /> {detalle.incidencia_texto}
                  </CardContent>
                </Card>
              )}

              {/* Tracking Events */}
              {detalle.eventos?.length > 0 && (
                <div>
                  <p className="text-sm font-medium mb-2 flex items-center gap-1"><Clock className="w-4 h-4" /> Historial de Tracking ({detalle.eventos.length})</p>
                  <div className="space-y-1 max-h-60 overflow-y-auto">
                    {detalle.eventos.map((ev, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs p-2 bg-slate-50 rounded">
                        <span className="text-muted-foreground whitespace-nowrap">{ev.fecha_evento}</span>
                        <span className="font-medium">{ev.descripcion_evento || ev.tipo}</span>
                        {ev.nombre_plaza && <span className="text-muted-foreground">({ev.nombre_plaza})</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Logs */}
              {detalle.logs?.length > 0 && (
                <div>
                  <p className="text-sm font-medium mb-2">Logs de integración ({detalle.logs.length})</p>
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {detalle.logs.map((log, i) => (
                      <div key={i} className="text-xs p-2 bg-slate-50 rounded">
                        <span className="text-muted-foreground">{new Date(log.fecha).toLocaleString('es-ES')}</span>
                        <span className="ml-2 font-mono">{log.tipo_operacion}</span>
                        {log.error && <span className="ml-2 text-red-600">{log.error}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 pt-2">
                <Button onClick={() => handleSyncSingle(detalle.id)} variant="outline" size="sm"><RotateCw className="w-4 h-4 mr-1" /> Actualizar</Button>
                <Button onClick={() => handleDescargarEtiqueta(detalle.id)} variant="outline" size="sm"><FileDown className="w-4 h-4 mr-1" /> Etiqueta</Button>
                {(detalle.tracking_url || detalle.gls_codbarras) && (
                  <a href={buildGLSTrackingUrl(detalle)} target="_blank" rel="noopener noreferrer">
                    <Button variant="outline" size="sm"><ExternalLink className="w-4 h-4 mr-1" /> Tracking GLS</Button>
                  </a>
                )}
                {!detalle.es_final && <Button onClick={() => handleAnular(detalle.id)} variant="destructive" size="sm"><Trash2 className="w-4 h-4 mr-1" /> Anular</Button>}
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}

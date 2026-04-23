import { useEffect, useState } from 'react';
import {
  Truck, RefreshCw, AlertTriangle, CheckCircle2, Clock, Loader2,
  FileText, ExternalLink, PackageSearch,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import api from '@/lib/api';
import CrearEtiquetaGLSButton from '@/components/orden/CrearEtiquetaGLSButton';

const COLOR_MAP = {
  emerald: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  blue:    'bg-blue-100 text-blue-800 border-blue-300',
  slate:   'bg-slate-100 text-slate-700 border-slate-300',
  red:     'bg-red-100 text-red-800 border-red-300',
};

function formatDateTime(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString('es-ES', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch { return iso; }
}

/**
 * Panel completo del módulo logística v2 para OrdenDetalle.
 *
 * Muestra:
 *   - Si NO hay envíos: botón prominente de creación.
 *   - Si hay envíos: último envío con estado, timeline de eventos, incidencias,
 *     acciones (Actualizar tracking, Abrir incidencia, Reabrir PDF, Tracking GLS).
 */
export default function GLSEnvioPanel({ orden, onUpdate }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [incidenciaDialog, setIncidenciaDialog] = useState(null); // {codbarras}
  const [incidenciaText, setIncidenciaText] = useState('');
  const [creandoIncidencia, setCreandoIncidencia] = useState(false);

  const fetchDetail = async () => {
    if (!orden?.id) return;
    setLoading(true);
    try {
      const { data } = await api.get(`/logistica/gls/orden/${orden.id}`);
      setDetail(data);
    } catch (e) {
      console.error('fetchDetail error', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchDetail(); /* eslint-disable-next-line */ }, [orden?.id]);

  // Preferir envío con tracking activo (estado poblado y distinto de "creado");
  // si no hay ninguno, el último creado.
  const envios = detail?.envios || [];
  const envioActual =
    envios.filter((e) => e.estado && e.estado.toLowerCase() !== 'creado').slice(-1)[0]
    || envios[envios.length - 1];

  const handleActualizar = async (codbarras) => {
    setRefreshing(true);
    try {
      const { data } = await api.post(`/logistica/gls/actualizar-tracking/${codbarras}`);
      await fetchDetail();
      if (onUpdate) onUpdate();
      if (data.estado_cambio) {
        // Para el tramitador mostrar el estado CRUDO de GLS, no el mapeado.
        const estadoRaw = data.envio.estado_interno || data.envio.estado;
        toast.success(`Estado actualizado: ${estadoRaw}`);
      } else {
        toast.info('Tracking sin cambios');
      }
      if (data.incidencia_creada) toast.warning('Incidencia creada automáticamente');
      if (data.orden_estado_actualizado) toast.success('Orden marcada como enviada');
    } catch (e) {
      const msg = e?.response?.data?.detail || 'Error al actualizar';
      toast.error(msg);
    } finally {
      setRefreshing(false);
    }
  };

  const handleAbrirIncidencia = async () => {
    if (!incidenciaDialog || incidenciaText.trim().length < 5) {
      toast.error('Describe la incidencia (mínimo 5 caracteres)');
      return;
    }
    setCreandoIncidencia(true);
    try {
      await api.post('/logistica/gls/abrir-incidencia', {
        order_id: orden.id,
        codbarras: incidenciaDialog.codbarras,
        descripcion: incidenciaText.trim(),
        severidad: 'alta',
      });
      toast.success('Incidencia creada y vinculada a la OT');
      setIncidenciaDialog(null);
      setIncidenciaText('');
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Error creando incidencia');
    } finally {
      setCreandoIncidencia(false);
    }
  };

  if (loading && !detail) {
    return (
      <Card><CardContent className="py-10 flex items-center justify-center text-muted-foreground">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Cargando logística…
      </CardContent></Card>
    );
  }

  // Sin envíos: CTA prominente
  if (!envioActual) {
    return (
      <Card className="border-blue-200 bg-gradient-to-br from-blue-50 to-white"
            data-testid="gls-panel-vacio">
        <CardContent className="py-10 flex flex-col items-center gap-4 text-center">
          <div className="rounded-full bg-blue-100 p-4">
            <Truck className="w-8 h-8 text-blue-600" />
          </div>
          <div>
            <h3 className="font-semibold text-lg">Esta orden aún no tiene etiqueta GLS</h3>
            <p className="text-sm text-muted-foreground max-w-md">
              Crea una etiqueta de envío rápidamente. Los datos del cliente se precargan automáticamente.
            </p>
          </div>
          <CrearEtiquetaGLSButton
            orden={orden}
            onCreated={() => { fetchDetail(); if (onUpdate) onUpdate(); }}
            variant="default"
            label="Crear etiqueta GLS ahora"
          />
          {!detail?.puede_crear_envio && (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
              ⚠️ Faltan datos de dirección o CP en la ficha del cliente.
            </p>
          )}
        </CardContent>
      </Card>
    );
  }

  // Con envíos: vista completa del último + botón para crear otro
  return (
    <>
      <Card className={`border-2 ${COLOR_MAP[envioActual.estado_color] || COLOR_MAP.slate}`}
            data-testid="gls-panel-envio">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center justify-between gap-2 text-lg">
            <div className="flex items-center gap-2 flex-wrap">
              <Truck className="w-5 h-5" />
              <span>Envío GLS</span>
              <Badge className={`${COLOR_MAP[envioActual.estado_color] || COLOR_MAP.slate} border font-mono uppercase tracking-wide`}
                     data-testid="gls-badge-estado-interno"
                     title="Estado crudo GLS (vista tramitador)">
                {envioActual.estado_interno || envioActual.estado || '—'}
              </Badge>
              {envioActual.mock_preview && (
                <Badge variant="outline" className="border-amber-400 bg-amber-50 text-amber-800">
                  preview
                </Badge>
              )}
            </div>
            <Button variant="ghost" size="sm" disabled={refreshing}
                    onClick={() => handleActualizar(envioActual.codbarras)}
                    data-testid="gls-btn-actualizar-tracking">
              {refreshing
                ? <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Actualizando…</>
                : <><RefreshCw className="w-4 h-4 mr-2" /> Actualizar tracking</>}
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <Info label="Código de barras" value={envioActual.codbarras} mono
                  testid="gls-info-codbarras" />
            <Info label="Peso" value={`${envioActual.peso_kg} kg`} />
            <Info label="Referencia" value={envioActual.referencia} mono />
            <Info label="Última actualización" value={formatDateTime(envioActual.ultima_actualizacion)} />
          </div>

          {envioActual.incidencia && (
            <div className="rounded-md border-2 border-red-300 bg-red-50 p-3 flex items-start gap-3"
                 data-testid="gls-alerta-incidencia">
              <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-red-900 flex-1">
                <p className="font-semibold">Incidencia detectada</p>
                <p>{envioActual.incidencia}</p>
              </div>
            </div>
          )}

          {/* Timeline */}
          {envioActual.eventos?.length > 0 ? (
            <div>
              <p className="text-xs font-semibold uppercase text-muted-foreground mb-2">
                Historial del envío
              </p>
              <ol className="relative border-s-2 border-slate-200 ml-2 space-y-3"
                  data-testid="gls-timeline-eventos">
                {envioActual.eventos.slice().reverse().map((ev, i) => {
                  const isLatest = i === 0;
                  const isDelivered = ev.codigo === '10' || /ENTREGADO/i.test(ev.estado);
                  const Icon = isDelivered ? CheckCircle2 : (isLatest ? Truck : Clock);
                  return (
                    <li key={`${ev.codigo}-${i}-${ev.fecha}`} className="ms-5">
                      <span className={`absolute -start-3 flex items-center justify-center w-6 h-6 rounded-full ring-4 ring-white ${
                        isDelivered ? 'bg-emerald-200 text-emerald-800'
                        : isLatest ? 'bg-blue-200 text-blue-800'
                        : 'bg-slate-200 text-slate-700'}`}>
                        <Icon className="w-3 h-3" />
                      </span>
                      <p className={`text-sm ${isLatest ? 'font-semibold' : ''}`}>
                        {ev.estado}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {ev.fecha} {ev.plaza ? `· ${ev.plaza}` : ''}
                      </p>
                    </li>
                  );
                })}
              </ol>
            </div>
          ) : (
            <div className="text-sm text-muted-foreground flex items-center gap-2">
              <PackageSearch className="w-4 h-4" />
              Todavía no hay eventos de tracking. Pulsa <em>Actualizar tracking</em> para consultarlo.
            </div>
          )}

          <div className="flex flex-wrap gap-2 pt-2">
            <a href={`/api/logistica/gls/etiqueta/${envioActual.codbarras}`}
               target="_blank" rel="noopener noreferrer">
              <Button size="sm" variant="outline" className="gap-2"
                      data-testid="gls-btn-ver-etiqueta-pdf">
                <FileText className="w-4 h-4" /> Ver etiqueta PDF
              </Button>
            </a>
            <a href={envioActual.tracking_url} target="_blank" rel="noopener noreferrer">
              <Button size="sm" variant="outline" className="gap-2">
                <ExternalLink className="w-4 h-4" /> Tracking público GLS
              </Button>
            </a>
            <Button size="sm" variant="outline" className="gap-2 text-red-700 border-red-300 hover:bg-red-50"
                    onClick={() => setIncidenciaDialog({ codbarras: envioActual.codbarras })}
                    data-testid="gls-btn-abrir-incidencia">
              <AlertTriangle className="w-4 h-4" /> Abrir incidencia
            </Button>
            <CrearEtiquetaGLSButton
              orden={orden}
              onCreated={() => { fetchDetail(); if (onUpdate) onUpdate(); }}
              label="Crear otra etiqueta"
            />
          </div>
        </CardContent>
      </Card>

      <Dialog open={!!incidenciaDialog} onOpenChange={(v) => !v && setIncidenciaDialog(null)}>
        <DialogContent data-testid="gls-dialog-incidencia">
          <DialogHeader>
            <DialogTitle>Abrir incidencia del envío</DialogTitle>
            <DialogDescription>
              Codbarras: <span className="font-mono">{incidenciaDialog?.codbarras}</span>.
              La incidencia quedará vinculada a la OT y visible en el módulo de incidencias.
            </DialogDescription>
          </DialogHeader>
          <Textarea rows={4} placeholder="Describe qué ha pasado…"
                    value={incidenciaText}
                    onChange={(e) => setIncidenciaText(e.target.value)}
                    data-testid="gls-input-incidencia-desc" />
          <DialogFooter>
            <Button variant="ghost" onClick={() => setIncidenciaDialog(null)}
                    disabled={creandoIncidencia}>Cancelar</Button>
            <Button variant="destructive" onClick={handleAbrirIncidencia}
                    disabled={creandoIncidencia}
                    data-testid="gls-btn-confirmar-incidencia">
              {creandoIncidencia
                ? <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Creando…</>
                : 'Abrir incidencia'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

function Info({ label, value, mono, testid }) {
  return (
    <div data-testid={testid}>
      <p className="text-xs text-muted-foreground uppercase">{label}</p>
      <p className={`${mono ? 'font-mono' : ''} font-medium`}>{value || '—'}</p>
    </div>
  );
}

import { useState, useEffect } from 'react';
import {
  Truck, Save, ShieldCheck, RefreshCw, CheckCircle2, XCircle,
  AlertTriangle, Loader2, Info,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import API from '@/lib/api';
import { toast } from 'sonner';

function formatDT(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '—';
  return `${d.toLocaleDateString('es-ES')} · ${d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}`;
}

export default function AjustesGLS() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [forcing, setForcing] = useState(false);
  const [remitenteDraft, setRemitenteDraft] = useState({
    nombre: '', direccion: '', poblacion: '', provincia: '',
    cp: '', telefono: '', pais: '34',
  });
  const [pollingDraft, setPollingDraft] = useState(4);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const { data } = await API.get('/logistica/config/gls');
      setConfig(data);
      setRemitenteDraft(data.remitente);
      setPollingDraft(data.polling_hours);
    } catch {
      toast.error('Error cargando configuración GLS');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveRemitente = async () => {
    setSaving(true);
    try {
      const { data } = await API.post('/logistica/config/gls/remitente', remitenteDraft);
      setConfig(data);
      setRemitenteDraft(data.remitente);
      toast.success('Remitente guardado en BD');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error guardando remitente');
    } finally {
      setSaving(false);
    }
  };

  const handleSavePolling = async () => {
    setSaving(true);
    try {
      const { data } = await API.post('/logistica/config/gls/polling', {
        polling_hours: parseFloat(pollingDraft),
      });
      setConfig(data);
      setPollingDraft(data.polling_hours);
      toast.success(`Intervalo actualizado a ${data.polling_hours}h`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error guardando polling');
    } finally {
      setSaving(false);
    }
  };

  const handleForcePoll = async () => {
    setForcing(true);
    try {
      const { data } = await API.post('/logistica/panel/actualizar-todos');
      toast.success(
        `Polling forzado. Procesados: ${data.procesados} · Cambios: ${data.cambios_estado}` +
        (data.preview ? ' (PREVIEW)' : ''),
      );
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error forzando polling');
    } finally {
      setForcing(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const { data } = await API.post('/logistica/config/gls/verify');
      if (data.ok) {
        toast.success(data.mensaje);
      } else {
        toast.error(data.mensaje + (data.detalle ? ` · ${data.detalle}` : ''));
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error verificando conexión');
    } finally {
      setVerifying(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const isPreview = config?.entorno === 'preview';

  return (
    <div className="space-y-6 animate-fade-in" data-testid="ajustes-gls-page">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Truck className="w-6 h-6 text-blue-600" />
          Ajustes · Integraciones Logística
        </h1>
        <p className="text-muted-foreground text-sm">
          Configuración de transportistas. Los cambios se guardan en BD (no en .env).
        </p>
      </div>

      <Tabs defaultValue="gls" className="w-full">
        <TabsList data-testid="tabs-transportistas">
          <TabsTrigger value="gls" data-testid="tab-gls">GLS</TabsTrigger>
          <TabsTrigger value="mrw" data-testid="tab-mrw">MRW</TabsTrigger>
        </TabsList>

        <TabsContent value="gls" className="space-y-6 mt-4">
          {/* Estado de la integración */}
          <Card data-testid="card-estado-integracion">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Info className="w-4 h-4 text-blue-600" />
                Estado de la integración
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <Label className="text-xs text-muted-foreground">Entorno</Label>
                <div className="mt-1">
                  {isPreview ? (
                    <Badge className="bg-amber-100 text-amber-800 border-amber-300" data-testid="badge-entorno-preview">
                      <AlertTriangle className="w-3 h-3 mr-1" /> PREVIEW · mocks activos
                    </Badge>
                  ) : (
                    <Badge className="bg-green-100 text-green-800 border-green-300" data-testid="badge-entorno-production">
                      <CheckCircle2 className="w-3 h-3 mr-1" /> PRODUCCIÓN
                    </Badge>
                  )}
                </div>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Último envío</Label>
                <p className="text-sm font-mono mt-1">{config?.ultimo_envio?.codbarras || '—'}</p>
                <p className="text-[10px] text-muted-foreground">{formatDT(config?.ultimo_envio?.creado_en)}</p>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Envíos este mes</Label>
                <p className="text-2xl font-bold text-blue-700 mt-1" data-testid="stats-envios-mes">
                  {config?.stats_mes?.envios_mes || 0}
                </p>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Incidencias este mes</Label>
                <p className="text-2xl font-bold text-red-700 mt-1" data-testid="stats-incidencias-mes">
                  {config?.stats_mes?.incidencias_mes || 0}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Credenciales */}
          <Card data-testid="card-credenciales">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-green-600" />
                Credenciales
              </CardTitle>
              <CardDescription>Solo lectura por seguridad. Edítalas en el .env del servidor.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label className="text-xs text-muted-foreground">UID cliente</Label>
                <div className="flex gap-2 items-center mt-1">
                  <code className="flex-1 px-3 py-2 bg-slate-100 rounded font-mono text-sm tracking-wider" data-testid="uid-masked">
                    {config?.uid_cliente_masked || '(no configurado)'}
                  </code>
                  {config?.uid_cliente_set ? (
                    <Badge className="bg-green-100 text-green-800 border-green-300">✓ seteado</Badge>
                  ) : (
                    <Badge className="bg-red-100 text-red-800 border-red-300">✗ vacío</Badge>
                  )}
                </div>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">URL endpoint</Label>
                <code className="block mt-1 px-3 py-2 bg-slate-100 rounded font-mono text-xs text-slate-700">
                  {config?.gls_url || '(default)'}
                </code>
              </div>
              <Button
                variant="outline"
                onClick={handleVerify}
                disabled={verifying}
                data-testid="btn-verificar-conexion"
              >
                {verifying ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <ShieldCheck className="w-4 h-4 mr-2" />}
                Verificar conexión
              </Button>
            </CardContent>
          </Card>

          {/* Datos remitente */}
          <Card data-testid="card-remitente">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Datos del remitente</CardTitle>
              <CardDescription>
                Aparecerán en todas las etiquetas GLS. Se guardan en BD, no en .env.
                Los campos marcados "<span className="font-mono text-[10px] bg-slate-100 px-1">env</span>" se leen del entorno cuando BD está vacía.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                ['nombre', 'Nombre'],
                ['direccion', 'Dirección'],
                ['poblacion', 'Población'],
                ['provincia', 'Provincia'],
                ['cp', 'Código Postal'],
                ['telefono', 'Teléfono'],
                ['pais', 'País (prefijo)'],
              ].map(([key, label]) => (
                <div key={key}>
                  <Label className="text-xs flex items-center gap-2">
                    {label}
                    {config?.remitente_source?.[key] && (
                      <span className="font-mono text-[9px] bg-slate-100 px-1 rounded">
                        {config.remitente_source[key]}
                      </span>
                    )}
                  </Label>
                  <Input
                    value={remitenteDraft[key] || ''}
                    onChange={(e) => setRemitenteDraft({ ...remitenteDraft, [key]: e.target.value })}
                    data-testid={`input-remitente-${key}`}
                    className="mt-1"
                  />
                </div>
              ))}
              <div className="md:col-span-2 flex justify-end gap-2">
                <Button variant="outline" onClick={loadConfig} disabled={saving}>
                  Descartar
                </Button>
                <Button onClick={handleSaveRemitente} disabled={saving} data-testid="btn-guardar-remitente">
                  {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Guardar remitente
                </Button>
              </div>
              {config?.updated_at && (
                <p className="md:col-span-2 text-xs text-muted-foreground">
                  Última modificación: {formatDT(config.updated_at)} por {config.updated_by || '—'}
                </p>
              )}
            </CardContent>
          </Card>

          {/* Polling */}
          <Card data-testid="card-polling">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <RefreshCw className="w-4 h-4 text-purple-600" />
                Polling automático de tracking
              </CardTitle>
              <CardDescription>
                Intervalo en horas con el que el scheduler consulta GLS por cada envío activo.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-end gap-3">
                <div className="w-32">
                  <Label className="text-xs">Intervalo (horas)</Label>
                  <Input
                    type="number"
                    step="0.25"
                    min="0.25"
                    max="48"
                    value={pollingDraft}
                    onChange={(e) => setPollingDraft(e.target.value)}
                    data-testid="input-polling-hours"
                    className="mt-1"
                  />
                </div>
                <Button onClick={handleSavePolling} disabled={saving} data-testid="btn-guardar-polling">
                  {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Guardar
                </Button>
                <Separator orientation="vertical" className="h-10" />
                <Button
                  variant="outline"
                  onClick={handleForcePoll}
                  disabled={forcing}
                  data-testid="btn-force-poll"
                >
                  {forcing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
                  Forzar actualización ahora
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Actual: {config?.polling_hours}h. Los cambios requieren reinicio del backend para aplicar al scheduler (
                el botón <strong>Forzar actualización</strong> ejecuta un tick inmediato sin reiniciar).
              </p>
            </CardContent>
          </Card>

          {/* Sincronización histórica */}
          <SincronizacionHistoricaCard />
        </TabsContent>

        <TabsContent value="mrw">
          <MRWConfigTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Sincronización de órdenes históricas con GLS
// ──────────────────────────────────────────────────────────────────────────────

function SincronizacionHistoricaCard() {
  const [candidatas, setCandidatas] = useState(null);
  const [resultados, setResultados] = useState(null);
  const [loading, setLoading] = useState(false);
  const [diasAtras, setDiasAtras] = useState(45);

  const loadCandidatas = async () => {
    try {
      const { data } = await API.get(`/logistica/gls/sincronizar-ordenes/candidatas?dias_atras=${diasAtras}`);
      setCandidatas(data);
    } catch { /* silencioso */ }
  };

  useEffect(() => {
    loadCandidatas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [diasAtras]);

  const ejecutarSync = async () => {
    if (!window.confirm(
      `¿Sincronizar las ${candidatas?.total_candidatas || '?'} órdenes candidatas con GLS?\n` +
      `Esta acción es idempotente: solo añade/actualiza gls_envios, no toca otros campos.`,
    )) return;
    setLoading(true);
    try {
      const { data } = await API.post('/logistica/gls/sincronizar-ordenes', {
        solo_sin_envios: true,
        dias_atras: diasAtras,
        max_ordenes: 500,
      });
      setResultados(data);
      toast.success(
        `Sync completado. ${data.sincronizadas} ok, ${data.no_encontradas} no encontradas, ${data.con_error} errores.` +
        (data.preview ? ' (PREVIEW)' : ''),
      );
      loadCandidatas();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error ejecutando sync');
    } finally {
      setLoading(false);
    }
  };

  const statusBadge = (status) => {
    if (status === 'ok') return <Badge className="bg-green-100 text-green-800 border-green-300 text-[10px]">OK</Badge>;
    if (status === 'not_found') return <Badge className="bg-amber-100 text-amber-800 border-amber-300 text-[10px]">No encontrada</Badge>;
    if (status === 'skipped') return <Badge className="bg-slate-100 text-slate-700 border-slate-300 text-[10px]">Skip</Badge>;
    return <Badge className="bg-red-100 text-red-800 border-red-300 text-[10px]">Error</Badge>;
  };

  return (
    <Card data-testid="card-sync-historico">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <RefreshCw className="w-4 h-4 text-blue-600" />
          Sincronización de órdenes históricas
        </CardTitle>
        <CardDescription>
          Vincula órdenes antiguas con envíos GLS creados desde la extranet
          (usando `numero_autorizacion` como RefC). Idempotente: no modifica otros campos.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-end gap-3 flex-wrap">
          <div className="w-32">
            <Label className="text-xs">Ventana (días)</Label>
            <Input
              type="number" min="1" max="365"
              value={diasAtras}
              onChange={(e) => setDiasAtras(Number(e.target.value) || 45)}
              data-testid="input-sync-dias"
            />
          </div>
          <div className="flex-1 min-w-[200px]">
            <Label className="text-xs">Candidatas (sin gls_envios)</Label>
            <p className="text-2xl font-bold text-blue-700" data-testid="sync-total-candidatas">
              {candidatas?.total_candidatas ?? '—'}
            </p>
          </div>
          <Button
            onClick={ejecutarSync} disabled={loading || !candidatas?.total_candidatas}
            data-testid="btn-ejecutar-sync"
          >
            {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
            Sincronizar órdenes con GLS
          </Button>
        </div>

        {candidatas?.muestra?.length > 0 && !resultados && (
          <details className="text-xs">
            <summary className="cursor-pointer text-muted-foreground">
              Ver muestra de las 10 más recientes
            </summary>
            <div className="mt-2 space-y-1">
              {candidatas.muestra.map((o) => (
                <div key={o.id} className="flex justify-between border-b py-1 text-xs">
                  <span className="font-mono">{o.numero_orden}</span>
                  <span className="font-mono text-blue-700">{o.numero_autorizacion}</span>
                  <span className="text-muted-foreground">{o.cp_envio || '—'}</span>
                </div>
              ))}
            </div>
          </details>
        )}

        {resultados && (
          <div className="space-y-3" data-testid="sync-resultados">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-center text-xs">
              <div className="bg-green-50 rounded p-2">
                <p className="text-xl font-bold text-green-700">{resultados.sincronizadas}</p>
                <p className="text-[10px]">Sincronizadas</p>
              </div>
              <div className="bg-blue-50 rounded p-2">
                <p className="text-xl font-bold text-blue-700">{resultados.creadas}</p>
                <p className="text-[10px]">Creadas</p>
              </div>
              <div className="bg-indigo-50 rounded p-2">
                <p className="text-xl font-bold text-indigo-700">{resultados.actualizadas}</p>
                <p className="text-[10px]">Actualizadas</p>
              </div>
              <div className="bg-amber-50 rounded p-2">
                <p className="text-xl font-bold text-amber-700">{resultados.no_encontradas}</p>
                <p className="text-[10px]">No encontradas</p>
              </div>
              <div className="bg-red-50 rounded p-2">
                <p className="text-xl font-bold text-red-700">{resultados.con_error}</p>
                <p className="text-[10px]">Con error</p>
              </div>
            </div>

            <div className="max-h-96 overflow-y-auto border rounded-lg">
              <table className="w-full text-xs">
                <thead className="bg-slate-100 sticky top-0">
                  <tr>
                    <th className="p-2 text-left">OT</th>
                    <th className="p-2 text-left">Autorización</th>
                    <th className="p-2 text-left">Estado</th>
                    <th className="p-2 text-left">Codbarras</th>
                    <th className="p-2 text-left">CP</th>
                    <th className="p-2 text-left">Tracking</th>
                  </tr>
                </thead>
                <tbody>
                  {resultados.resultados.map((r, i) => (
                    <tr key={i} className="border-b hover:bg-slate-50" data-testid={`sync-row-${r.order_id}`}>
                      <td className="p-2 font-mono">{r.numero_orden || '—'}</td>
                      <td className="p-2 font-mono text-blue-700">{r.numero_autorizacion}</td>
                      <td className="p-2">{statusBadge(r.status)}{r.status !== 'ok' && r.reason && <span className="text-[10px] text-muted-foreground ml-1">({r.reason})</span>}</td>
                      <td className="p-2 font-mono">{r.codbarras || '—'}</td>
                      <td className="p-2">{r.cp_destinatario || '—'}</td>
                      <td className="p-2">
                        {r.tracking_url ? (
                          <a href={r.tracking_url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
                            abrir
                          </a>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {resultados.no_encontradas > 0 && (
              <div className="bg-amber-50 border border-amber-300 rounded p-2 text-xs">
                <p className="font-medium text-amber-900 mb-1">
                  {resultados.no_encontradas} órdenes no encontradas en GLS.
                </p>
                <p className="text-amber-700">
                  Verifica que el `numero_autorizacion` corresponde al `RefC` enviado a GLS.
                  Posibles causas: envío nunca creado en GLS, refC erróneo, o envío muy antiguo borrado del histórico GLS.
                </p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// MRW Config Tab (mismo patrón que GLS)
// ──────────────────────────────────────────────────────────────────────────────

function MRWConfigTab() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [remitenteDraft, setRemitenteDraft] = useState({
    nombre: '', direccion: '', poblacion: '', provincia: '', cp: '', telefono: '',
  });

  useEffect(() => {
    loadMRW();
  }, []);

  const loadMRW = async () => {
    try {
      const { data } = await API.get('/logistica/config/mrw');
      setConfig(data);
      setRemitenteDraft(data.remitente);
    } catch {
      toast.error('Error cargando configuración MRW');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveRemitente = async () => {
    setSaving(true);
    try {
      const { data } = await API.post('/logistica/config/mrw/remitente', remitenteDraft);
      setConfig(data);
      setRemitenteDraft(data.remitente);
      toast.success('Remitente MRW guardado en BD');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error guardando remitente MRW');
    } finally {
      setSaving(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const { data } = await API.post('/logistica/config/mrw/verify');
      if (data.ok) toast.success(data.mensaje);
      else toast.error(data.mensaje);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error verificando MRW');
    } finally {
      setVerifying(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>;
  }

  const isPreview = config?.entorno === 'preview';

  return (
    <div className="space-y-6 mt-4" data-testid="mrw-config-content">
      {/* Estado */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Info className="w-4 h-4 text-blue-600" /> Estado integración MRW
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <Label className="text-xs text-muted-foreground">Entorno</Label>
            <div className="mt-1">
              {isPreview ? (
                <Badge className="bg-amber-100 text-amber-800 border-amber-300" data-testid="mrw-badge-preview">
                  <AlertTriangle className="w-3 h-3 mr-1" /> PREVIEW · mocks activos
                </Badge>
              ) : (
                <Badge className="bg-green-100 text-green-800 border-green-300">
                  <CheckCircle2 className="w-3 h-3 mr-1" /> PRODUCCIÓN
                </Badge>
              )}
            </div>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Último envío</Label>
            <p className="text-sm font-mono mt-1">{config?.ultimo_envio?.num_envio || '—'}</p>
            <p className="text-[10px] text-muted-foreground">{config?.ultimo_envio?.creado_en ? new Date(config.ultimo_envio.creado_en).toLocaleString('es-ES') : '—'}</p>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Envíos este mes</Label>
            <p className="text-2xl font-bold text-blue-700 mt-1">{config?.stats_mes?.envios_mes || 0}</p>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Recogidas pendientes</Label>
            <p className="text-2xl font-bold text-amber-700 mt-1" data-testid="mrw-recogidas-pendientes">
              {config?.stats_mes?.recogidas_pendientes || 0}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Credenciales */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-green-600" /> Credenciales
          </CardTitle>
          <CardDescription>Solo lectura. Edita en el .env del servidor.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <Label className="text-xs text-muted-foreground">Franquicia</Label>
            <code className="block mt-1 px-2 py-2 bg-slate-100 rounded font-mono text-sm tracking-wider" data-testid="mrw-franquicia">
              {config?.franquicia_masked || '(no configurado)'}
            </code>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Abonado</Label>
            <code className="block mt-1 px-2 py-2 bg-slate-100 rounded font-mono text-sm tracking-wider">
              {config?.abonado_masked || '—'}
            </code>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Usuario</Label>
            <code className="block mt-1 px-2 py-2 bg-slate-100 rounded font-mono text-sm tracking-wider">
              {config?.usuario_masked || '—'}
            </code>
          </div>
          <div className="md:col-span-3">
            <Button variant="outline" onClick={handleVerify} disabled={verifying} data-testid="btn-mrw-verify">
              {verifying ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <ShieldCheck className="w-4 h-4 mr-2" />}
              Verificar conexión
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Remitente */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Datos del remitente</CardTitle>
          <CardDescription>Aparecerán en etiquetas MRW. Se guardan en BD (colección `configuracion` tipo=mrw).</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            ['nombre', 'Nombre'],
            ['direccion', 'Dirección'],
            ['poblacion', 'Población'],
            ['provincia', 'Provincia'],
            ['cp', 'CP'],
            ['telefono', 'Teléfono'],
          ].map(([key, label]) => (
            <div key={key}>
              <Label className="text-xs flex items-center gap-2">
                {label}
                {config?.remitente_source?.[key] && (
                  <span className="font-mono text-[9px] bg-slate-100 px-1 rounded">
                    {config.remitente_source[key]}
                  </span>
                )}
              </Label>
              <Input
                value={remitenteDraft[key] || ''}
                onChange={(e) => setRemitenteDraft({ ...remitenteDraft, [key]: e.target.value })}
                data-testid={`input-mrw-remitente-${key}`}
                className="mt-1"
              />
            </div>
          ))}
          <div className="md:col-span-2 flex justify-end gap-2">
            <Button variant="outline" onClick={loadMRW} disabled={saving}>Descartar</Button>
            <Button onClick={handleSaveRemitente} disabled={saving} data-testid="btn-mrw-guardar-remitente">
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
              Guardar remitente
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Truck, Package, Send, MapPin, RefreshCw, FileDown, X, ExternalLink, ArrowDown, ArrowUp } from 'lucide-react';
import { toast } from 'sonner';
import API from '@/lib/api';

const ESTADO_COLORS = {
  grabado: 'bg-blue-100 text-blue-800',
  'en transito': 'bg-amber-100 text-amber-800',
  entregado: 'bg-green-100 text-green-800',
  incidencia: 'bg-red-100 text-red-800',
  anulado: 'bg-slate-100 text-slate-500',
};

export default function GLSLogistica({ orden, onUpdate }) {
  const [glsActivo, setGlsActivo] = useState(false);
  const [glsConfig, setGlsConfig] = useState(null);
  const [showEnvio, setShowEnvio] = useState(false);
  const [showRecogida, setShowRecogida] = useState(false);
  const [sending, setSending] = useState(false);
  const [tracking, setTracking] = useState(null);
  const [loadingTracking, setLoadingTracking] = useState(false);

  const cliente = orden.cliente || {};
  const glsEnvios = orden.gls_envios || [];

  const [envioForm, setEnvioForm] = useState({
    nombre_dst: cliente.nombre || '', direccion_dst: cliente.direccion || '',
    poblacion_dst: cliente.poblacion || '', cp_dst: cliente.cp || '',
    telefono_dst: cliente.telefono || '', email_dst: cliente.email || '',
    observaciones: `Orden ${orden.numero_orden}`, servicio: '', horario: '',
    bultos: '1', peso: '1', portes: ''
  });

  const [recogidaForm, setRecogidaForm] = useState({
    nombre_org: cliente.nombre || '', direccion_org: cliente.direccion || '',
    poblacion_org: cliente.poblacion || '', cp_org: cliente.cp || '',
    telefono_org: cliente.telefono || '',
    observaciones: `Recogida orden ${orden.numero_orden}`, servicio: '', horario: '',
    bultos: '1', peso: '1', fecha: ''
  });

  useEffect(() => {
    API.get('/gls/config').then(r => {
      setGlsActivo(r.data?.activo || false);
      setGlsConfig(r.data);
    }).catch(() => {});
  }, []);

  const handleCrearEnvio = async () => {
    setSending(true);
    try {
      const res = await API.post('/gls/envio', { ...envioForm, orden_id: orden.id });
      if (res.data?.success) {
        toast.success(`Envío creado - Código: ${res.data.codbarras}`);
        setShowEnvio(false);
        onUpdate?.();
      } else {
        toast.error(res.data?.error || 'Error al crear envío');
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al crear envío GLS');
    }
    setSending(false);
  };

  const handleCrearRecogida = async () => {
    setSending(true);
    try {
      const res = await API.post('/gls/recogida', { ...recogidaForm, orden_id: orden.id });
      if (res.data?.success) {
        toast.success(`Recogida creada - Código: ${res.data.codbarras}`);
        setShowRecogida(false);
        onUpdate?.();
      } else {
        toast.error(res.data?.error || 'Error al crear recogida');
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al crear recogida GLS');
    }
    setSending(false);
  };

  const handleConsultarTracking = async (ref) => {
    setLoadingTracking(true);
    try {
      const res = await API.get(`/gls/tracking/${ref}`);
      setTracking(res.data);
      if (!res.data?.success) toast.error(res.data?.error || 'Sin datos');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error consultando tracking');
    }
    setLoadingTracking(false);
  };

  const handleDescargarEtiqueta = async (envioId, tipo = 'envio') => {
    const token = localStorage.getItem('token');
    const formato = glsConfig?.formato_etiqueta || 'PDF';
    try {
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/gls/etiqueta/${envioId}?formato=${formato}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Error descargando etiqueta');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `etiqueta_${tipo}_${ref}.${formato.toLowerCase()}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Etiqueta descargada');
    } catch (e) {
      toast.error('Error al descargar etiqueta');
    }
  };

  if (!glsActivo) {
    return (
      <Card className="border-dashed border-slate-300">
        <CardContent className="py-6 text-center text-muted-foreground">
          <Truck className="w-8 h-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">Integración GLS no activada</p>
          <p className="text-xs">Configúrala en Ajustes &gt; GLS</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Botones principales */}
      <div className="flex gap-3">
        <Dialog open={showRecogida} onOpenChange={setShowRecogida}>
          <DialogTrigger asChild>
            <Button variant="outline" className="flex-1 border-amber-300 hover:bg-amber-50" data-testid="gls-btn-recogida">
              <ArrowDown className="w-4 h-4 mr-2 text-amber-600" /> Solicitar Recogida
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader><DialogTitle className="flex items-center gap-2"><ArrowDown className="w-5 h-5 text-amber-600" /> Nueva Recogida GLS</DialogTitle></DialogHeader>
            <div className="space-y-3 mt-2">
              <p className="text-sm text-muted-foreground">Datos del origen (donde se recoge el dispositivo)</p>
              <div className="grid grid-cols-2 gap-3">
                <div><Label className="text-xs">Nombre</Label><Input value={recogidaForm.nombre_org} onChange={e => setRecogidaForm(p => ({...p, nombre_org: e.target.value}))} /></div>
                <div><Label className="text-xs">Teléfono</Label><Input value={recogidaForm.telefono_org} onChange={e => setRecogidaForm(p => ({...p, telefono_org: e.target.value}))} /></div>
              </div>
              <div><Label className="text-xs">Dirección</Label><Input value={recogidaForm.direccion_org} onChange={e => setRecogidaForm(p => ({...p, direccion_org: e.target.value}))} /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><Label className="text-xs">Población</Label><Input value={recogidaForm.poblacion_org} onChange={e => setRecogidaForm(p => ({...p, poblacion_org: e.target.value}))} /></div>
                <div><Label className="text-xs">C.P.</Label><Input value={recogidaForm.cp_org} onChange={e => setRecogidaForm(p => ({...p, cp_org: e.target.value}))} /></div>
              </div>
              <Separator />
              <div className="grid grid-cols-3 gap-3">
                <div><Label className="text-xs">Bultos</Label><Input type="number" value={recogidaForm.bultos} onChange={e => setRecogidaForm(p => ({...p, bultos: e.target.value}))} /></div>
                <div><Label className="text-xs">Peso (kg)</Label><Input value={recogidaForm.peso} onChange={e => setRecogidaForm(p => ({...p, peso: e.target.value}))} /></div>
                <div><Label className="text-xs">Fecha</Label><Input type="date" value={recogidaForm.fecha} onChange={e => setRecogidaForm(p => ({...p, fecha: e.target.value}))} /></div>
              </div>
              <div><Label className="text-xs">Observaciones</Label><Input value={recogidaForm.observaciones} onChange={e => setRecogidaForm(p => ({...p, observaciones: e.target.value}))} /></div>
              <Button onClick={handleCrearRecogida} disabled={sending} className="w-full" data-testid="gls-confirm-recogida">
                {sending ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <ArrowDown className="w-4 h-4 mr-2" />}
                Crear Recogida GLS
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        <Dialog open={showEnvio} onOpenChange={setShowEnvio}>
          <DialogTrigger asChild>
            <Button variant="outline" className="flex-1 border-green-300 hover:bg-green-50" data-testid="gls-btn-envio">
              <ArrowUp className="w-4 h-4 mr-2 text-green-600" /> Crear Envío
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader><DialogTitle className="flex items-center gap-2"><Send className="w-5 h-5 text-green-600" /> Nuevo Envío GLS</DialogTitle></DialogHeader>
            <div className="space-y-3 mt-2">
              <p className="text-sm text-muted-foreground">Datos del destinatario (donde se envía el dispositivo)</p>
              <div className="grid grid-cols-2 gap-3">
                <div><Label className="text-xs">Nombre</Label><Input value={envioForm.nombre_dst} onChange={e => setEnvioForm(p => ({...p, nombre_dst: e.target.value}))} /></div>
                <div><Label className="text-xs">Teléfono</Label><Input value={envioForm.telefono_dst} onChange={e => setEnvioForm(p => ({...p, telefono_dst: e.target.value}))} /></div>
              </div>
              <div><Label className="text-xs">Dirección</Label><Input value={envioForm.direccion_dst} onChange={e => setEnvioForm(p => ({...p, direccion_dst: e.target.value}))} /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><Label className="text-xs">Población</Label><Input value={envioForm.poblacion_dst} onChange={e => setEnvioForm(p => ({...p, poblacion_dst: e.target.value}))} /></div>
                <div><Label className="text-xs">C.P.</Label><Input value={envioForm.cp_dst} onChange={e => setEnvioForm(p => ({...p, cp_dst: e.target.value}))} /></div>
              </div>
              <div><Label className="text-xs">Email</Label><Input value={envioForm.email_dst} onChange={e => setEnvioForm(p => ({...p, email_dst: e.target.value}))} /></div>
              <Separator />
              <div className="grid grid-cols-3 gap-3">
                <div><Label className="text-xs">Bultos</Label><Input type="number" value={envioForm.bultos} onChange={e => setEnvioForm(p => ({...p, bultos: e.target.value}))} /></div>
                <div><Label className="text-xs">Peso (kg)</Label><Input value={envioForm.peso} onChange={e => setEnvioForm(p => ({...p, peso: e.target.value}))} /></div>
                <div><Label className="text-xs">Portes</Label>
                  <Select value={envioForm.portes || 'P'} onValueChange={v => setEnvioForm(p => ({...p, portes: v}))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent><SelectItem value="P">Pagados</SelectItem><SelectItem value="D">Debidos</SelectItem></SelectContent>
                  </Select>
                </div>
              </div>
              <div><Label className="text-xs">Observaciones</Label><Input value={envioForm.observaciones} onChange={e => setEnvioForm(p => ({...p, observaciones: e.target.value}))} /></div>
              <Button onClick={handleCrearEnvio} disabled={sending} className="w-full" data-testid="gls-confirm-envio">
                {sending ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
                Crear Envío GLS
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Envíos existentes */}
      {glsEnvios.length > 0 && (
        <div className="space-y-3">
          <h4 className="font-semibold text-sm flex items-center gap-2"><Package className="w-4 h-4" /> Envíos / Recogidas GLS</h4>
          {glsEnvios.map((envio, idx) => (
            <Card key={envio.id || idx} className={`${envio.tipo === 'recogida' ? 'border-l-4 border-l-amber-400' : 'border-l-4 border-l-green-400'}`}>
              <CardContent className="py-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {envio.tipo === 'recogida' ? <ArrowDown className="w-5 h-5 text-amber-600" /> : <ArrowUp className="w-5 h-5 text-green-600" />}
                    <div>
                      <p className="font-mono font-semibold text-sm" data-testid={`gls-codbarras-${idx}`}>{envio.codbarras}</p>
                      <p className="text-xs text-muted-foreground">
                        {envio.tipo === 'recogida' ? 'Recogida' : 'Envío'} &middot; {envio.nombre_dst || envio.nombre_org || ''} &middot; {new Date(envio.created_at).toLocaleDateString('es-ES')}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={ESTADO_COLORS[envio.estado_gls] || 'bg-slate-100'} data-testid={`gls-estado-${idx}`}>{envio.estado_gls || 'grabado'}</Badge>
                    <Button variant="ghost" size="sm" onClick={() => handleDescargarEtiqueta(envio.id, envio.tipo)} title="Descargar etiqueta" data-testid={`gls-label-${idx}`}>
                      <FileDown className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleConsultarTracking(envio.id)} title="Consultar tracking" data-testid={`gls-track-${idx}`}>
                      {loadingTracking ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ExternalLink className="w-4 h-4" />}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Códigos manuales (legacy) */}
      {(orden.codigo_recogida_entrada || orden.codigo_recogida_salida) && !glsEnvios.length && (
        <Card className="border-dashed">
          <CardContent className="py-3 space-y-2">
            <h4 className="font-semibold text-sm flex items-center gap-2"><MapPin className="w-4 h-4" /> Códigos Logística (manual)</h4>
            {orden.codigo_recogida_entrada && (
              <div className="flex justify-between text-sm"><span className="text-muted-foreground">Recogida:</span><span className="font-mono">{orden.codigo_recogida_entrada}</span></div>
            )}
            {(orden.codigo_recogida_salida || orden.codigo_seguimiento_salida) && (
              <div className="flex justify-between text-sm"><span className="text-muted-foreground">Envío:</span><span className="font-mono">{orden.codigo_recogida_salida || orden.codigo_seguimiento_salida}</span></div>
            )}
            {orden.agencia_envio && (
              <div className="flex justify-between text-sm"><span className="text-muted-foreground">Agencia:</span><span>{orden.agencia_envio}</span></div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tracking detail */}
      {tracking?.success && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-sm flex items-center gap-2"><Truck className="w-4 h-4" /> Tracking GLS: {tracking.codbarras}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-3 gap-2 text-sm">
              <div><span className="text-muted-foreground">Estado:</span> <Badge className={tracking.estado?.toLowerCase().includes('entreg') ? 'bg-green-500 text-white' : 'bg-blue-500 text-white'}>{tracking.estado || tracking.codestado}</Badge></div>
              <div><span className="text-muted-foreground">Fecha:</span> {tracking.fecha}</div>
              <div><span className="text-muted-foreground">Entrega prev.:</span> {tracking.fecha_entrega_prevista || '-'}</div>
            </div>
            {tracking.tracking_list?.length > 0 && (
              <>
                <Separator />
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {tracking.tracking_list.map((t, i) => (
                    <div key={i} className="flex items-start gap-3 text-xs py-1 border-b border-slate-50 last:border-0">
                      <span className="text-muted-foreground w-28 shrink-0">{t.fecha}</span>
                      <span className="font-medium">{t.evento}</span>
                      <span className="text-muted-foreground ml-auto">{t.nombre_plaza}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

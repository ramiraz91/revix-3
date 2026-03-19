import { useState, useEffect } from 'react';
import { Package, Send, ArrowDown, ArrowUp, FileDown, ExternalLink, RotateCw, Loader2, Plus, Truck, MapPin } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import api from '@/lib/api';

const STATE_COLORS = {
  grabado: 'bg-slate-100 text-slate-700',
  en_transito: 'bg-indigo-100 text-indigo-700',
  en_reparto: 'bg-purple-100 text-purple-700',
  entregado: 'bg-green-100 text-green-700',
  devuelto: 'bg-red-100 text-red-700',
  anulado: 'bg-gray-100 text-gray-500',
  error: 'bg-red-200 text-red-800',
};

export default function GLSLogistica({ orden, onUpdate }) {
  const [glsConfig, setGlsConfig] = useState(null);
  const [envios, setEnvios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCrear, setShowCrear] = useState(false);
  const [tipoCrear, setTipoCrear] = useState('recogida');
  const [creando, setCreando] = useState(false);
  const [servicios, setServicios] = useState({});
  const [form, setForm] = useState({});

  useEffect(() => {
    loadData();
  }, [orden?.id]);

  const loadData = async () => {
    try {
      const [cfgRes, maestrosRes, enviosRes] = await Promise.all([
        api.get('/gls/config').catch(() => ({ data: {} })),
        api.get('/gls/maestros').catch(() => ({ data: { servicios: {}, horarios: {} } })),
        api.get(`/gls/envios?orden_id=${orden.id}`),
      ]);
      setGlsConfig(cfgRes.data);
      setServicios(maestrosRes.data.servicios || {});
      setEnvios(enviosRes.data.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const initForm = (tipo) => {
    const cliente = orden.cliente || {};
    const isRecogida = tipo === 'recogida';
    setTipoCrear(tipo);
    setForm({
      dest_nombre: isRecogida ? (cliente.nombre || '') : (cliente.nombre || ''),
      dest_direccion: isRecogida ? (cliente.direccion || '') : (cliente.direccion || ''),
      dest_poblacion: isRecogida ? (cliente.ciudad || '') : (cliente.ciudad || ''),
      dest_cp: isRecogida ? (cliente.codigo_postal || '') : (cliente.codigo_postal || ''),
      dest_telefono: isRecogida ? (cliente.telefono || '') : (cliente.telefono || ''),
      dest_email: isRecogida ? (cliente.email || '') : (cliente.email || ''),
      dest_provincia: '',
      dest_observaciones: '',
      bultos: 1,
      peso: 1,
      servicio: '',
      referencia: orden.numero_orden || orden.numero_autorizacion || '',
    });
    setShowCrear(true);
  };

  const handleCrear = async () => {
    if (!form.dest_nombre || !form.dest_direccion || !form.dest_cp) {
      toast.error('Completa nombre, dirección y CP del destinatario');
      return;
    }
    setCreando(true);
    try {
      const payload = {
        orden_id: orden.id,
        tipo: tipoCrear,
        entidad_tipo: 'orden',
        ...form,
        bultos: parseInt(form.bultos) || 1,
        peso: parseFloat(form.peso) || 1,
        etiqueta_inline: true,
        formato_etiqueta: glsConfig?.formato_etiqueta || 'PDF',
      };
      const res = await api.post('/gls/envios', payload);
      toast.success(`${tipoCrear === 'recogida' ? 'Recogida' : 'Envío'} GLS creado correctamente`);
      setShowCrear(false);
      loadData();
      if (onUpdate) onUpdate();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al crear envío GLS');
    } finally {
      setCreando(false);
    }
  };

  const handleDescargarEtiqueta = async (id) => {
    try {
      const res = await api.get(`/gls/etiqueta/${id}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `etiqueta_gls.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      toast.error('Etiqueta no disponible');
    }
  };

  const handleSyncSingle = async (id) => {
    try {
      await api.post(`/gls/sync/${id}`);
      toast.success('Tracking actualizado');
      loadData();
    } catch (err) {
      toast.error('Error al sincronizar');
    }
  };

  if (loading) return <div className="flex justify-center py-4"><Loader2 className="w-6 h-6 animate-spin" /></div>;

  if (!glsConfig?.activo) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          <Truck className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>Integración GLS no activada</p>
          <p className="text-xs">Configura GLS desde Ajustes &gt; GLS Config</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4" data-testid="gls-logistica-panel">
      {/* Acciones */}
      <div className="flex gap-2">
        <Button onClick={() => initForm('recogida')} variant="outline" size="sm" data-testid="btn-crear-recogida">
          <ArrowDown className="w-4 h-4 mr-1 text-amber-600" /> Crear Recogida
        </Button>
        <Button onClick={() => initForm('envio')} variant="outline" size="sm" data-testid="btn-crear-envio">
          <ArrowUp className="w-4 h-4 mr-1 text-green-600" /> Crear Envío
        </Button>
      </div>

      {/* Lista de envíos */}
      {envios.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground text-sm">
          <Package className="w-10 h-10 mx-auto mb-2 opacity-30" />
          No hay envíos GLS vinculados a esta orden
        </div>
      ) : (
        <div className="space-y-2">
          {envios.map((e) => (
            <div key={e.id} className="p-3 bg-orange-50 rounded-lg border border-orange-100" data-testid={`gls-shipment-${e.id}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {e.tipo === 'recogida' ? <ArrowDown className="w-4 h-4 text-amber-600" /> : <ArrowUp className="w-4 h-4 text-green-600" />}
                  <span className="font-medium text-sm capitalize">{e.tipo}</span>
                  <Badge variant="outline" className="font-mono text-xs">{e.gls_codbarras || '-'}</Badge>
                  <Badge className={`text-xs ${STATE_COLORS[e.estado_interno] || 'bg-gray-100'}`}>
                    {e.estado_interno?.replace(/_/g, ' ')}
                  </Badge>
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleSyncSingle(e.id)} title="Actualizar"><RotateCw className="w-3 h-3" /></Button>
                  <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleDescargarEtiqueta(e.id)} title="Etiqueta"><FileDown className="w-3 h-3" /></Button>
                  {e.gls_codbarras && (
                    <a href={`https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/?match=${e.gls_codbarras}`} target="_blank" rel="noopener noreferrer" className="p-1">
                      <ExternalLink className="w-3 h-3 text-blue-500" />
                    </a>
                  )}
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Ref: {e.referencia_interna} · {e.destinatario?.nombre} · {new Date(e.created_at).toLocaleString('es-ES')}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Dialog Crear */}
      <Dialog open={showCrear} onOpenChange={setShowCrear}>
        <DialogContent className="max-w-lg" data-testid="gls-crear-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {tipoCrear === 'recogida' ? <ArrowDown className="w-5 h-5 text-amber-600" /> : <ArrowUp className="w-5 h-5 text-green-600" />}
              Crear {tipoCrear === 'recogida' ? 'Recogida' : 'Envío'} GLS
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
              {tipoCrear === 'recogida'
                ? 'Datos del punto de recogida (cliente):'
                : 'Datos del destinatario del envío:'}
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <Label className="text-xs">Nombre *</Label>
                <Input value={form.dest_nombre || ''} onChange={(e) => setForm(f => ({ ...f, dest_nombre: e.target.value }))} />
              </div>
              <div className="col-span-2">
                <Label className="text-xs">Dirección *</Label>
                <Input value={form.dest_direccion || ''} onChange={(e) => setForm(f => ({ ...f, dest_direccion: e.target.value }))} />
              </div>
              <div>
                <Label className="text-xs">Población</Label>
                <Input value={form.dest_poblacion || ''} onChange={(e) => setForm(f => ({ ...f, dest_poblacion: e.target.value }))} />
              </div>
              <div>
                <Label className="text-xs">CP *</Label>
                <Input value={form.dest_cp || ''} onChange={(e) => setForm(f => ({ ...f, dest_cp: e.target.value }))} />
              </div>
              <div>
                <Label className="text-xs">Teléfono</Label>
                <Input value={form.dest_telefono || ''} onChange={(e) => setForm(f => ({ ...f, dest_telefono: e.target.value }))} />
              </div>
              <div>
                <Label className="text-xs">Email</Label>
                <Input value={form.dest_email || ''} onChange={(e) => setForm(f => ({ ...f, dest_email: e.target.value }))} />
              </div>
              <div>
                <Label className="text-xs">Bultos</Label>
                <Input type="number" min={1} value={form.bultos || 1} onChange={(e) => setForm(f => ({ ...f, bultos: e.target.value }))} />
              </div>
              <div>
                <Label className="text-xs">Peso (kg)</Label>
                <Input type="number" min={0.1} step={0.1} value={form.peso || 1} onChange={(e) => setForm(f => ({ ...f, peso: e.target.value }))} />
              </div>
              <div className="col-span-2">
                <Label className="text-xs">Referencia</Label>
                <Input value={form.referencia || ''} onChange={(e) => setForm(f => ({ ...f, referencia: e.target.value }))} className="font-mono" />
              </div>
              <div className="col-span-2">
                <Label className="text-xs">Observaciones</Label>
                <Input value={form.dest_observaciones || ''} onChange={(e) => setForm(f => ({ ...f, dest_observaciones: e.target.value }))} />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setShowCrear(false)}>Cancelar</Button>
              <Button onClick={handleCrear} disabled={creando} data-testid="btn-confirmar-gls">
                {creando ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Send className="w-4 h-4 mr-1" />}
                {creando ? 'Creando...' : 'Crear'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

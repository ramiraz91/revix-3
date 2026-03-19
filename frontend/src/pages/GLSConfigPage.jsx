import { useState, useEffect } from 'react';
import { Settings, Save, TestTube, Loader2, ShieldCheck, RefreshCw, Truck } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import api from '@/lib/api';

export default function GLSConfigPage() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [servicios, setServicios] = useState({});
  const [horarios, setHorarios] = useState({});

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const [cfgRes, maestrosRes] = await Promise.all([
        api.get('/gls/config'),
        api.get('/gls/maestros'),
      ]);
      // Normalize: if config has nested remitente, flatten it
      const raw = cfgRes.data;
      if (raw.remitente && typeof raw.remitente === 'object') {
        raw.remitente_nombre = raw.remitente.nombre || '';
        raw.remitente_direccion = raw.remitente.direccion || '';
        raw.remitente_poblacion = raw.remitente.poblacion || '';
        raw.remitente_provincia = raw.remitente.provincia || '';
        raw.remitente_cp = raw.remitente.cp || '';
        raw.remitente_telefono = raw.remitente.telefono || '';
        raw.remitente_email = raw.remitente.email || '';
      }
      setConfig(raw);
      setServicios(maestrosRes.data.servicios || {});
      setHorarios(maestrosRes.data.horarios || {});
    } catch (err) {
      toast.error('Error cargando configuración GLS');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.post('/gls/config', config);
      toast.success('Configuración GLS guardada');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error guardando');
    } finally {
      setSaving(false);
    }
  };

  const handleSync = async () => {
    try {
      const res = await api.post('/gls/sync');
      toast.success(`Sincronización: ${res.data.synced} actualizados, ${res.data.errors} errores`);
    } catch (err) {
      toast.error('Error en sincronización');
    }
  };

  const update = (key, val) => setConfig(prev => ({ ...prev, [key]: val }));

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin" /></div>;
  if (!config) return null;

  return (
    <div className="space-y-6" data-testid="gls-config-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><Truck className="w-6 h-6" /> Configuración GLS</h1>
          <p className="text-muted-foreground text-sm">Configura la integración con el servicio de logística GLS</p>
        </div>
        <Button onClick={handleSave} disabled={saving} data-testid="btn-save-gls">
          {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
          Guardar
        </Button>
      </div>

      {/* Activación */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><ShieldCheck className="w-5 h-5" /> Estado de la integración</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between">
          <div>
            <p className="font-medium">{config.activo ? 'Integración ACTIVA' : 'Integración DESACTIVADA'}</p>
            <p className="text-sm text-muted-foreground">UID: {config.uid_masked || 'No configurado'}</p>
          </div>
          <Switch checked={config.activo} onCheckedChange={(v) => update('activo', v)} data-testid="switch-activo" />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Credenciales */}
        <Card>
          <CardHeader>
            <CardTitle>Credenciales</CardTitle>
            <CardDescription>UID proporcionado por GLS</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Label>UID Cliente GLS</Label>
              <Input value={config.uid_cliente || ''} onChange={(e) => update('uid_cliente', e.target.value)} placeholder="XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX" className="font-mono text-sm" data-testid="input-uid" />
            </div>
          </CardContent>
        </Card>

        {/* Remitente */}
        <Card>
          <CardHeader>
            <CardTitle>Datos del Remitente</CardTitle>
            <CardDescription>Dirección de origen para envíos</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <Label>Nombre / Empresa</Label>
                <Input value={config.remitente_nombre || ''} onChange={(e) => update('remitente_nombre', e.target.value)} data-testid="input-rem-nombre" />
              </div>
              <div className="col-span-2">
                <Label>Dirección</Label>
                <Input value={config.remitente_direccion || ''} onChange={(e) => update('remitente_direccion', e.target.value)} data-testid="input-rem-dir" />
              </div>
              <div>
                <Label>Población</Label>
                <Input value={config.remitente_poblacion || ''} onChange={(e) => update('remitente_poblacion', e.target.value)} />
              </div>
              <div>
                <Label>Provincia</Label>
                <Input value={config.remitente_provincia || ''} onChange={(e) => update('remitente_provincia', e.target.value)} />
              </div>
              <div>
                <Label>CP</Label>
                <Input value={config.remitente_cp || ''} onChange={(e) => update('remitente_cp', e.target.value)} />
              </div>
              <div>
                <Label>Teléfono</Label>
                <Input value={config.remitente_telefono || ''} onChange={(e) => update('remitente_telefono', e.target.value)} />
              </div>
              <div className="col-span-2">
                <Label>Email</Label>
                <Input value={config.remitente_email || ''} onChange={(e) => update('remitente_email', e.target.value)} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Defaults */}
        <Card>
          <CardHeader>
            <CardTitle>Opciones por Defecto</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Label>Servicio</Label>
              <Select value={config.servicio_defecto || '96'} onValueChange={(v) => update('servicio_defecto', v)}>
                <SelectTrigger data-testid="select-servicio"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(servicios).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{k} - {v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Horario</Label>
              <Select value={config.horario_defecto || '18'} onValueChange={(v) => update('horario_defecto', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(horarios).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{k} - {v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Formato Etiqueta</Label>
              <Select value={config.formato_etiqueta || 'PDF'} onValueChange={(v) => update('formato_etiqueta', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="PDF">PDF</SelectItem>
                  <SelectItem value="PNG">PNG</SelectItem>
                  <SelectItem value="JPG">JPG</SelectItem>
                  <SelectItem value="EPL">EPL (Zebra)</SelectItem>
                  <SelectItem value="DPL">DPL (Datamax)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Polling */}
        <Card>
          <CardHeader>
            <CardTitle>Sincronización Automática</CardTitle>
            <CardDescription>Polling de estados con GLS (recomendado: 4-5 veces/día)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Polling activo</Label>
              <Switch checked={config.polling_activo} onCheckedChange={(v) => update('polling_activo', v)} data-testid="switch-polling" />
            </div>
            <div>
              <Label>Intervalo (horas)</Label>
              <Input type="number" min={1} max={24} value={config.polling_intervalo_horas || 4} onChange={(e) => update('polling_intervalo_horas', parseInt(e.target.value) || 4)} />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <Label>Email al crear recogida</Label>
              <Switch checked={config.email_recogida_activo !== false} onCheckedChange={(v) => update('email_recogida_activo', v)} />
            </div>
            <Separator />
            <Button variant="outline" onClick={handleSync} className="w-full" data-testid="btn-sync">
              <RefreshCw className="w-4 h-4 mr-2" />Sincronizar ahora
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

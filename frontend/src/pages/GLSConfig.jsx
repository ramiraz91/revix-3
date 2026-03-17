import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Separator } from '../components/ui/separator';
import { Truck, Save, RefreshCw, Power, Building2, MapPin, Phone, FileText, Settings, Clock } from 'lucide-react';
import { toast } from 'sonner';
import API from '@/lib/api';

export default function GLSConfig() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState({
    activo: false, uid_cliente: '',
    remitente: { nombre: '', direccion: '', poblacion: '', cp: '', telefono: '', nif: '' },
    servicio_defecto: '1', horario_defecto: '18', portes_defecto: 'P',
    formato_etiqueta: 'PDF', polling_activo: false, polling_intervalo_horas: 4
  });
  const [servicios, setServicios] = useState({});
  const [horarios, setHorarios] = useState({});

  useEffect(() => { fetchConfig(); }, []);

  const fetchConfig = async () => {
    try {
      const res = await API.get('/gls/config');
      setConfig(res.data);
      setServicios(res.data.servicios_disponibles || {});
      setHorarios(res.data.horarios_disponibles || {});
    } catch (e) { /* first time */ }
    setLoading(false);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const { servicios_disponibles, horarios_disponibles, ...payload } = config;
      await API.post('/gls/config', payload);
      toast.success('Configuración GLS guardada');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al guardar');
    }
    setSaving(false);
  };

  const updateRemitente = (k, v) => setConfig(p => ({ ...p, remitente: { ...p.remitente, [k]: v } }));

  if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="w-6 h-6 animate-spin" /></div>;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <Truck className="w-7 h-7 text-amber-600" />
            Configuración GLS
          </h1>
          <p className="text-muted-foreground mt-1">Integración con GLS Spain para envíos y recogidas</p>
        </div>
        <Badge variant={config.activo ? "default" : "secondary"} className={config.activo ? 'bg-green-500 text-white' : ''} data-testid="gls-status-badge">
          <Power className="w-3 h-3 mr-1" />
          {config.activo ? 'ACTIVO' : 'INACTIVO'}
        </Badge>
      </div>

      {/* Activación */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Power className="w-5 h-5 text-amber-600" />
              <div>
                <p className="font-medium">Activar integración GLS</p>
                <p className="text-sm text-muted-foreground">Habilita las funciones de envío y recogida con GLS</p>
              </div>
            </div>
            <Switch checked={config.activo} onCheckedChange={(v) => setConfig(p => ({ ...p, activo: v }))} data-testid="gls-toggle" />
          </div>
        </CardContent>
      </Card>

      {/* UID Cliente */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg"><Settings className="w-5 h-5" /> Credenciales GLS</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label>UID Cliente GLS</Label>
            <Input
              value={config.uid_cliente}
              onChange={(e) => setConfig(p => ({ ...p, uid_cliente: e.target.value }))}
              placeholder="XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
              className="font-mono"
              data-testid="gls-uid"
            />
            <p className="text-xs text-muted-foreground">UUID proporcionado por GLS para autenticación en su API</p>
          </div>
        </CardContent>
      </Card>

      {/* Remitente */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg"><Building2 className="w-5 h-5" /> Datos del Remitente</CardTitle>
          <CardDescription>Datos de tu empresa que aparecerán en las etiquetas</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Nombre / Empresa</Label>
              <Input value={config.remitente?.nombre || ''} onChange={(e) => updateRemitente('nombre', e.target.value)} data-testid="gls-rem-nombre" />
            </div>
            <div className="space-y-2">
              <Label>NIF</Label>
              <Input value={config.remitente?.nif || ''} onChange={(e) => updateRemitente('nif', e.target.value)} data-testid="gls-rem-nif" />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Dirección</Label>
            <Input value={config.remitente?.direccion || ''} onChange={(e) => updateRemitente('direccion', e.target.value)} data-testid="gls-rem-dir" />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Población</Label>
              <Input value={config.remitente?.poblacion || ''} onChange={(e) => updateRemitente('poblacion', e.target.value)} data-testid="gls-rem-pob" />
            </div>
            <div className="space-y-2">
              <Label>Código Postal</Label>
              <Input value={config.remitente?.cp || ''} onChange={(e) => updateRemitente('cp', e.target.value)} data-testid="gls-rem-cp" />
            </div>
            <div className="space-y-2">
              <Label>Teléfono</Label>
              <Input value={config.remitente?.telefono || ''} onChange={(e) => updateRemitente('telefono', e.target.value)} data-testid="gls-rem-tel" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Opciones por defecto */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg"><FileText className="w-5 h-5" /> Opciones por Defecto</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Servicio</Label>
              <Select value={config.servicio_defecto} onValueChange={(v) => setConfig(p => ({ ...p, servicio_defecto: v }))}>
                <SelectTrigger data-testid="gls-servicio"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(servicios).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v} ({k})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Horario</Label>
              <Select value={config.horario_defecto} onValueChange={(v) => setConfig(p => ({ ...p, horario_defecto: v }))}>
                <SelectTrigger data-testid="gls-horario"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(horarios).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Formato Etiqueta</Label>
              <Select value={config.formato_etiqueta} onValueChange={(v) => setConfig(p => ({ ...p, formato_etiqueta: v }))}>
                <SelectTrigger data-testid="gls-formato"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="PDF">PDF</SelectItem>
                  <SelectItem value="PNG">PNG</SelectItem>
                  <SelectItem value="ZPL">ZPL (impresora térmica)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label>Portes por defecto</Label>
            <Select value={config.portes_defecto} onValueChange={(v) => setConfig(p => ({ ...p, portes_defecto: v }))}>
              <SelectTrigger className="w-48" data-testid="gls-portes"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="P">Pagados (P)</SelectItem>
                <SelectItem value="D">Debidos (D)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Polling */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-amber-600" />
              <div>
                <p className="font-medium">Polling automático de tracking</p>
                <p className="text-sm text-muted-foreground">Consulta automáticamente el estado de los envíos activos</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Input
                type="number" className="w-20 text-center" min={1} max={24}
                value={config.polling_intervalo_horas}
                onChange={(e) => setConfig(p => ({ ...p, polling_intervalo_horas: parseInt(e.target.value) || 4 }))}
                data-testid="gls-polling-interval"
              />
              <span className="text-sm text-muted-foreground">horas</span>
              <Switch checked={config.polling_activo} onCheckedChange={(v) => setConfig(p => ({ ...p, polling_activo: v }))} data-testid="gls-polling-toggle" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Button onClick={handleSave} disabled={saving} size="lg" className="w-full" data-testid="gls-save-btn">
        {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
        Guardar Configuración GLS
      </Button>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { 
  Mail, Settings, Save, Send, Power, AlertTriangle, CheckCircle, RefreshCw, 
  Eye, Smartphone, Package, Wrench, Sparkles, Rocket, Bell, Clock,
  ExternalLink, Palette, Monitor, Edit, RotateCcw, FileText, Server, Lock, ShieldCheck
} from 'lucide-react';
import API, { plantillasEmailAPI } from '@/lib/api';
import { toast } from 'sonner';

// Estados que generan notificación automática al cliente
const ESTADOS_NOTIFICAR = [
  { 
    key: 'recibida', 
    label: 'Dispositivo Recibido', 
    icon: Package,
    color: 'bg-green-500',
    desc: 'Cuando el dispositivo llega al centro de reparación',
    emoji: '✅'
  },
  { 
    key: 'en_taller', 
    label: 'En Reparación', 
    icon: Wrench,
    color: 'bg-orange-500',
    desc: 'Cuando el técnico comienza a trabajar en el dispositivo',
    emoji: '🔧'
  },
  { 
    key: 'reparado', 
    label: 'Reparación Completada', 
    icon: Sparkles,
    color: 'bg-purple-500',
    desc: 'Cuando la reparación ha sido completada con éxito',
    emoji: '✨'
  },
  { 
    key: 'enviado', 
    label: 'Dispositivo Enviado', 
    icon: Rocket,
    color: 'bg-cyan-500',
    desc: 'Cuando el dispositivo reparado es enviado al cliente',
    emoji: '🚀'
  },
];

// Notificaciones internas para admin
const NOTIFICACIONES_ADMIN = [
  { 
    key: 'material_solicitado', 
    label: 'Material Solicitado', 
    desc: 'Cuando un técnico solicita un material para una orden'
  },
  { 
    key: 'presupuesto_aceptado', 
    label: 'Presupuesto Aceptado', 
    desc: 'Cuando el proveedor acepta un presupuesto'
  },
  { 
    key: 'alerta_sla', 
    label: 'Alerta de SLA', 
    desc: 'Cuando una orden supera el tiempo objetivo de reparación'
  },
];

export default function EmailConfig() {
  const [config, setConfig] = useState({
    enabled: true,
    demo_mode: false,
    demo_email: '',
    smtp_from: 'Revix <notificaciones@revix.es>',
    reply_to: 'soporte@revix.es',
    empresa_nombre: 'Revix',
    // Estados que notifican (todos activados por defecto)
    estados_activos: {
      recibida: true,
      en_taller: true,
      reparado: true,
      enviado: true,
    },
    // Notificaciones internas
    notif_admin: {
      material_solicitado: true,
      presupuesto_aceptado: true,
      alerta_sla: true,
    },
    // SMS habilitado
    sms_enabled: false,
  });
  const [plantillas, setPlantillas] = useState([]);
  const [selectedPlantilla, setSelectedPlantilla] = useState(null);
  const [plantillaForm, setPlantillaForm] = useState({});
  const [showEditPlantilla, setShowEditPlantilla] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [activeTab, setActiveTab] = useState('smtp');
  
  // SMTP state
  const [smtp, setSmtp] = useState({
    host: '', port: 465, secure: true, user: '', password: '', from_name: '', reply_to: '', configured: false
  });
  const [smtpSaving, setSmtpSaving] = useState(false);
  const [smtpTesting, setSmtpTesting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    fetchConfig();
    fetchPlantillas();
    fetchSmtpConfig();
  }, []);

  const fetchSmtpConfig = async () => {
    try {
      const res = await API.get('/smtp-config');
      if (res.data) setSmtp(res.data);
    } catch (e) { /* first time */ }
  };

  const handleSaveSmtp = async () => {
    setSmtpSaving(true);
    try {
      const res = await API.post('/smtp-config', smtp);
      toast.success(res.data?.message || 'Configuración SMTP guardada');
      fetchSmtpConfig();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al guardar SMTP');
    } finally {
      setSmtpSaving(false);
    }
  };

  const handleTestSmtp = async () => {
    const to = config.demo_mode && config.demo_email ? config.demo_email : (smtp.reply_to || smtp.user);
    if (!to) { toast.error('No hay dirección de destino para la prueba'); return; }
    setSmtpTesting(true);
    try {
      const res = await API.post('/email/test', { to });
      if (res.data?.success) toast.success(`Email de prueba enviado a ${to}`);
      else toast.error('Error al enviar email de prueba');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error de conexión SMTP');
    } finally {
      setSmtpTesting(false);
    }
  };

  const fetchConfig = async () => {
    try {
      const res = await API.get('/email-config');
      if (res.data) {
        setConfig(prev => ({ ...prev, ...res.data }));
      }
    } catch (e) {
      // First time - use defaults
    } finally {
      setLoading(false);
    }
  };

  const fetchPlantillas = async () => {
    try {
      const res = await plantillasEmailAPI.listar();
      setPlantillas(res.data || []);
    } catch (e) {
      console.error('Error cargando plantillas:', e);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await API.put('/email-config', config);
      toast.success('Configuración de notificaciones guardada');
    } catch (e) {
      toast.error('Error al guardar configuración');
    } finally {
      setSaving(false);
    }
  };

  const handleTestEmail = async () => {
    setTesting(true);
    try {
      const to = config.demo_mode && config.demo_email ? config.demo_email : config.reply_to;
      const res = await API.post('/email/test', { to });
      if (res.data?.success) {
        toast.success(`Email de prueba enviado a ${to}`);
      } else {
        toast.error('Error al enviar email de prueba');
      }
    } catch (e) {
      toast.error('Error de conexión SMTP');
    } finally {
      setTesting(false);
    }
  };

  const toggleEstado = (key) => {
    setConfig(prev => ({
      ...prev,
      estados_activos: {
        ...prev.estados_activos,
        [key]: !prev.estados_activos[key]
      }
    }));
  };

  const toggleNotifAdmin = (key) => {
    setConfig(prev => ({
      ...prev,
      notif_admin: {
        ...prev.notif_admin,
        [key]: !prev.notif_admin[key]
      }
    }));
  };

  const handleEditPlantilla = (plantilla) => {
    setSelectedPlantilla(plantilla);
    setPlantillaForm({ ...plantilla });
    setShowEditPlantilla(true);
  };

  const handleSavePlantilla = async () => {
    setSaving(true);
    try {
      await plantillasEmailAPI.actualizar(selectedPlantilla.id, plantillaForm);
      toast.success('Plantilla actualizada');
      setShowEditPlantilla(false);
      fetchPlantillas();
    } catch (e) {
      toast.error('Error al guardar plantilla');
    } finally {
      setSaving(false);
    }
  };

  const handleResetPlantilla = async (id) => {
    if (!confirm('¿Restaurar esta plantilla a sus valores por defecto?')) return;
    try {
      await plantillasEmailAPI.resetear(id);
      toast.success('Plantilla restaurada');
      fetchPlantillas();
    } catch (e) {
      toast.error('Error al restaurar plantilla');
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
        Cargando configuración...
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Mail className="w-7 h-7 text-blue-600" />
            </div>
            Notificaciones Automáticas
          </h1>
          <p className="text-muted-foreground mt-1">
            Configura los emails y SMS que se envían automáticamente a tus clientes
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleTestEmail} disabled={testing}>
            {testing ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
            Enviar Prueba
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
            Guardar Cambios
          </Button>
        </div>
      </div>

      {/* Estado General */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Power className="w-5 h-5" /> 
            Estado del Sistema
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Email habilitado */}
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${config.enabled ? 'bg-green-100' : 'bg-slate-200'}`}>
                  <Mail className={`w-5 h-5 ${config.enabled ? 'text-green-600' : 'text-slate-400'}`} />
                </div>
                <div>
                  <p className="font-medium">Notificaciones Email</p>
                  <p className="text-sm text-muted-foreground">Envío automático de emails</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant={config.enabled ? "default" : "secondary"} className={config.enabled ? 'bg-green-500' : ''}>
                  {config.enabled ? 'ACTIVO' : 'INACTIVO'}
                </Badge>
                <Switch 
                  checked={config.enabled} 
                  onCheckedChange={(v) => setConfig(prev => ({ ...prev, enabled: v }))} 
                />
              </div>
            </div>

            {/* SMS habilitado */}
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${config.sms_enabled ? 'bg-purple-100' : 'bg-slate-200'}`}>
                  <Smartphone className={`w-5 h-5 ${config.sms_enabled ? 'text-purple-600' : 'text-slate-400'}`} />
                </div>
                <div>
                  <p className="font-medium">Notificaciones SMS</p>
                  <p className="text-sm text-muted-foreground">Envío automático de SMS</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant={config.sms_enabled ? "default" : "secondary"} className={config.sms_enabled ? 'bg-purple-500' : ''}>
                  {config.sms_enabled ? 'ACTIVO' : 'INACTIVO'}
                </Badge>
                <Switch 
                  checked={config.sms_enabled} 
                  onCheckedChange={(v) => setConfig(prev => ({ ...prev, sms_enabled: v }))} 
                />
              </div>
            </div>
          </div>

          {/* Modo Demo */}
          <div className={`flex items-center justify-between p-4 rounded-xl border ${config.demo_mode ? 'bg-yellow-50 border-yellow-200' : 'bg-slate-50'}`}>
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${config.demo_mode ? 'bg-yellow-100' : 'bg-slate-200'}`}>
                <AlertTriangle className={`w-5 h-5 ${config.demo_mode ? 'text-yellow-600' : 'text-slate-400'}`} />
              </div>
              <div>
                <p className="font-medium">Modo Demo / Pruebas</p>
                <p className="text-sm text-muted-foreground">
                  {config.demo_mode 
                    ? 'Todos los emails se envían solo a la dirección de prueba' 
                    : 'Los emails se envían a los clientes reales'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant="outline" className={config.demo_mode ? 'text-yellow-700 border-yellow-400' : 'text-green-700 border-green-400'}>
                {config.demo_mode ? 'MODO DEMO' : 'PRODUCCIÓN'}
              </Badge>
              <Switch 
                checked={config.demo_mode} 
                onCheckedChange={(v) => setConfig(prev => ({ ...prev, demo_mode: v }))} 
              />
            </div>
          </div>

          {config.demo_mode && (
            <div className="pl-6 border-l-2 border-yellow-300">
              <Label className="text-xs text-yellow-700">Email de prueba (todos los emails irán aquí)</Label>
              <Input 
                value={config.demo_email} 
                onChange={(e) => setConfig(prev => ({ ...prev, demo_email: e.target.value }))} 
                placeholder="tu-email@ejemplo.com"
                className="max-w-md mt-1"
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tabs de configuración */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="smtp" className="flex items-center gap-2" data-testid="tab-smtp">
            <Server className="w-4 h-4" />
            Servidor SMTP
          </TabsTrigger>
          <TabsTrigger value="cliente" className="flex items-center gap-2" data-testid="tab-cliente">
            <Bell className="w-4 h-4" />
            Notif. Cliente
          </TabsTrigger>
          <TabsTrigger value="admin" className="flex items-center gap-2" data-testid="tab-admin">
            <Settings className="w-4 h-4" />
            Notif. Admin
          </TabsTrigger>
          <TabsTrigger value="plantillas" className="flex items-center gap-2" data-testid="tab-plantillas">
            <FileText className="w-4 h-4" />
            Plantillas
          </TabsTrigger>
          <TabsTrigger value="diseño" className="flex items-center gap-2" data-testid="tab-diseno">
            <Palette className="w-4 h-4" />
            Diseño
          </TabsTrigger>
        </TabsList>

        {/* Tab: Servidor SMTP */}
        <TabsContent value="smtp">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Server className="w-5 h-5" />
                    Configuración del Servidor SMTP
                  </CardTitle>
                  <CardDescription>Configura los datos de conexión de tu servidor de correo saliente.</CardDescription>
                </div>
                <Badge 
                  variant={smtp.configured ? "default" : "destructive"} 
                  className={smtp.configured ? 'bg-green-500' : ''}
                  data-testid="smtp-status-badge"
                >
                  <ShieldCheck className="w-3 h-3 mr-1" />
                  {smtp.configured ? 'CONECTADO' : 'NO CONFIGURADO'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2 space-y-2">
                  <Label>Servidor SMTP (Host)</Label>
                  <Input 
                    value={smtp.host} 
                    onChange={(e) => setSmtp(p => ({...p, host: e.target.value}))}
                    placeholder="mail.privateemail.com"
                    data-testid="smtp-host"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Puerto</Label>
                  <Input 
                    type="number" 
                    value={smtp.port} 
                    onChange={(e) => setSmtp(p => ({...p, port: parseInt(e.target.value) || 465}))}
                    data-testid="smtp-port"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Usuario / Email</Label>
                  <Input 
                    value={smtp.user} 
                    onChange={(e) => setSmtp(p => ({...p, user: e.target.value}))}
                    placeholder="notificaciones@tudominio.com"
                    data-testid="smtp-user"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Contraseña</Label>
                  <div className="relative">
                    <Input 
                      type={showPassword ? 'text' : 'password'} 
                      value={smtp.password} 
                      onChange={(e) => setSmtp(p => ({...p, password: e.target.value}))}
                      placeholder="••••••••"
                      data-testid="smtp-password"
                    />
                    <button 
                      type="button"
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <Eye className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>

              <Separator />

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Nombre del remitente (From)</Label>
                  <Input 
                    value={smtp.from_name} 
                    onChange={(e) => setSmtp(p => ({...p, from_name: e.target.value}))}
                    placeholder="Revix <notificaciones@tudominio.com>"
                    data-testid="smtp-from"
                  />
                  <p className="text-xs text-muted-foreground">Lo que verá el cliente como remitente</p>
                </div>
                <div className="space-y-2">
                  <Label>Responder a (Reply-To)</Label>
                  <Input 
                    value={smtp.reply_to} 
                    onChange={(e) => setSmtp(p => ({...p, reply_to: e.target.value}))}
                    placeholder="help@tudominio.com"
                    data-testid="smtp-reply-to"
                  />
                  <p className="text-xs text-muted-foreground">Donde llegarán las respuestas del cliente</p>
                </div>
              </div>

              <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border">
                <div className="flex items-center gap-3">
                  <Lock className="w-5 h-5 text-slate-500" />
                  <div>
                    <p className="font-medium text-sm">Conexión SSL/TLS</p>
                    <p className="text-xs text-muted-foreground">Puerto 465 = SSL | Puerto 587 = STARTTLS</p>
                  </div>
                </div>
                <Switch 
                  checked={smtp.secure} 
                  onCheckedChange={(v) => setSmtp(p => ({...p, secure: v}))} 
                  data-testid="smtp-secure"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <Button onClick={handleSaveSmtp} disabled={smtpSaving} data-testid="smtp-save-btn">
                  {smtpSaving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Guardar y Verificar Conexión
                </Button>
                <Button variant="outline" onClick={handleTestSmtp} disabled={smtpTesting || !smtp.configured} data-testid="smtp-test-btn">
                  {smtpTesting ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
                  Enviar Email de Prueba
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Notificaciones Cliente */}
        <TabsContent value="cliente">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="w-5 h-5" />
                Estados que Notifican al Cliente
              </CardTitle>
              <CardDescription>
                Selecciona en qué cambios de estado se enviará automáticamente un email al cliente.
                Todos los emails incluyen un botón de "Ver estado de mi reparación".
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                {ESTADOS_NOTIFICAR.map((estado) => {
                  const Icon = estado.icon;
                  const isActive = config.estados_activos?.[estado.key] ?? true;
                  
                  return (
                    <div 
                      key={estado.key}
                      className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
                        isActive 
                          ? 'border-blue-200 bg-blue-50/50' 
                          : 'border-slate-200 bg-slate-50 opacity-60'
                      }`}
                      onClick={() => toggleEstado(estado.key)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg ${estado.color}`}>
                            <Icon className="w-5 h-5 text-white" />
                          </div>
                          <div>
                            <p className="font-medium flex items-center gap-2">
                              {estado.emoji} {estado.label}
                            </p>
                            <p className="text-sm text-muted-foreground mt-0.5">
                              {estado.desc}
                            </p>
                          </div>
                        </div>
                        <Switch 
                          checked={isActive}
                          onCheckedChange={() => toggleEstado(estado.key)}
                        />
                      </div>
                      
                      {isActive && (
                        <div className="mt-3 pt-3 border-t border-blue-200 text-xs text-blue-600 flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" />
                          Email + SMS automático al cambiar a este estado
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              
              <div className="mt-6 p-4 bg-slate-100 rounded-lg">
                <p className="text-sm text-slate-600 flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <strong>Nota:</strong> Los emails también se envían automáticamente al crear una nueva orden 
                  con el link de seguimiento para el cliente.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Notificaciones Admin */}
        <TabsContent value="admin">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="w-5 h-5" />
                Notificaciones Internas (Admin)
              </CardTitle>
              <CardDescription>
                Configura las notificaciones que recibirán los administradores del sistema.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {NOTIFICACIONES_ADMIN.map((notif) => {
                  const isActive = config.notif_admin?.[notif.key] ?? true;
                  
                  return (
                    <div 
                      key={notif.key}
                      className={`flex items-center justify-between p-4 rounded-lg border ${
                        isActive ? 'bg-white' : 'bg-slate-50 opacity-60'
                      }`}
                    >
                      <div>
                        <p className="font-medium">{notif.label}</p>
                        <p className="text-sm text-muted-foreground">{notif.desc}</p>
                      </div>
                      <Switch 
                        checked={isActive}
                        onCheckedChange={() => toggleNotifAdmin(notif.key)}
                      />
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Plantillas */}
        <TabsContent value="plantillas">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Plantillas de Email
              </CardTitle>
              <CardDescription>
                Personaliza el texto de cada tipo de email. Los cambios se aplican inmediatamente.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {plantillas.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Cargando plantillas...</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {plantillas.map((plantilla) => (
                    <div 
                      key={plantilla.id}
                      className="p-4 bg-slate-50 rounded-lg border hover:border-blue-200 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xl">{plantilla.emoji_estado}</span>
                            <span className="font-medium">{plantilla.nombre}</span>
                            <Badge variant="outline" className="text-xs">{plantilla.tipo}</Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">{plantilla.asunto}</p>
                          <div className="flex items-center gap-2">
                            <div 
                              className="w-4 h-4 rounded" 
                              style={{ backgroundColor: plantilla.color_banner }}
                            />
                            <span className="text-xs text-muted-foreground">
                              {plantilla.titulo}
                            </span>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={() => handleEditPlantilla(plantilla)}
                          >
                            <Edit className="w-4 h-4 mr-1" />
                            Editar
                          </Button>
                          <Button 
                            size="sm" 
                            variant="ghost"
                            className="text-slate-500"
                            onClick={() => handleResetPlantilla(plantilla.id)}
                          >
                            <RotateCcw className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <p className="text-sm text-blue-800">
                  <strong>💡 Variables disponibles:</strong> Usa <code className="bg-blue-100 px-1 rounded">{'{numero_orden}'}</code>, <code className="bg-blue-100 px-1 rounded">{'{nombre_cliente}'}</code>, <code className="bg-blue-100 px-1 rounded">{'{dispositivo}'}</code> en el asunto y mensajes para personalizar automáticamente.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Diseño */}
        <TabsContent value="diseño">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Palette className="w-5 h-5" />
                Diseño de Emails
              </CardTitle>
              <CardDescription>
                Los emails utilizan un diseño moderno, minimalista y responsive que incluye:
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Características del diseño */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-100">
                  <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center mb-3">
                    <Eye className="w-5 h-5 text-white" />
                  </div>
                  <h4 className="font-medium">Diseño Moderno</h4>
                  <p className="text-sm text-muted-foreground mt-1">
                    Tipografía Inter, gradientes suaves y colores profesionales
                  </p>
                </div>
                
                <div className="p-4 bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl border border-green-100">
                  <div className="w-10 h-10 bg-green-500 rounded-lg flex items-center justify-center mb-3">
                    <CheckCircle className="w-5 h-5 text-white" />
                  </div>
                  <h4 className="font-medium">Barra de Progreso</h4>
                  <p className="text-sm text-muted-foreground mt-1">
                    Muestra visualmente el estado de la reparación
                  </p>
                </div>
                
                <div className="p-4 bg-gradient-to-br from-purple-50 to-violet-50 rounded-xl border border-purple-100">
                  <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center mb-3">
                    <ExternalLink className="w-5 h-5 text-white" />
                  </div>
                  <h4 className="font-medium">Botón de Seguimiento</h4>
                  <p className="text-sm text-muted-foreground mt-1">
                    Link directo para que el cliente vea el estado
                  </p>
                </div>
              </div>

              <Separator className="my-6" />

              {/* Configuración de remitente */}
              <div className="space-y-4">
                <h4 className="font-medium flex items-center gap-2">
                  <Settings className="w-4 h-4" />
                  Configuración del Remitente
                </h4>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs">Nombre de la empresa</Label>
                    <Input 
                      value={config.empresa_nombre} 
                      onChange={(e) => setConfig(prev => ({ ...prev, empresa_nombre: e.target.value }))}
                      placeholder="Revix"
                    />
                    <p className="text-xs text-muted-foreground mt-1">Aparece en el logo del email</p>
                  </div>
                  <div>
                    <Label className="text-xs">Email de respuesta (Reply-To)</Label>
                    <Input 
                      value={config.reply_to} 
                      onChange={(e) => setConfig(prev => ({ ...prev, reply_to: e.target.value }))}
                      placeholder="soporte@tuempresa.com"
                    />
                  </div>
                </div>
              </div>

              <Separator className="my-6" />

              {/* Preview */}
              <div>
                <h4 className="font-medium flex items-center gap-2 mb-4">
                  <Monitor className="w-4 h-4" />
                  Vista Previa de Emails
                </h4>
                
                <div className="grid grid-cols-2 gap-4">
                  <a 
                    href="/email-preview.html" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="block p-4 bg-slate-50 rounded-xl border hover:border-blue-300 hover:bg-blue-50 transition-all group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-100 rounded-lg group-hover:bg-blue-200">
                        <Mail className="w-5 h-5 text-blue-600" />
                      </div>
                      <div>
                        <p className="font-medium group-hover:text-blue-600">Email: Nueva Orden</p>
                        <p className="text-sm text-muted-foreground">Ver diseño del email inicial</p>
                      </div>
                      <ExternalLink className="w-4 h-4 ml-auto text-slate-400 group-hover:text-blue-500" />
                    </div>
                  </a>
                  
                  <a 
                    href="/email-preview-enviado.html" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="block p-4 bg-slate-50 rounded-xl border hover:border-cyan-300 hover:bg-cyan-50 transition-all group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-cyan-100 rounded-lg group-hover:bg-cyan-200">
                        <Rocket className="w-5 h-5 text-cyan-600" />
                      </div>
                      <div>
                        <p className="font-medium group-hover:text-cyan-600">Email: Enviado</p>
                        <p className="text-sm text-muted-foreground">Ver diseño con tracking</p>
                      </div>
                      <ExternalLink className="w-4 h-4 ml-auto text-slate-400 group-hover:text-cyan-500" />
                    </div>
                  </a>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Dialog: Editar Plantilla */}
      <Dialog open={showEditPlantilla} onOpenChange={setShowEditPlantilla}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <span className="text-2xl">{plantillaForm.emoji_estado}</span>
              Editar Plantilla: {plantillaForm.nombre}
            </DialogTitle>
            <DialogDescription>
              Personaliza el contenido del email para este tipo de notificación
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4 max-h-[60vh] overflow-y-auto">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Emoji del Estado</Label>
                <Input
                  value={plantillaForm.emoji_estado || ''}
                  onChange={(e) => setPlantillaForm(prev => ({ ...prev, emoji_estado: e.target.value }))}
                  maxLength={2}
                  className="text-2xl text-center"
                />
              </div>
              <div className="space-y-2">
                <Label>Color del Banner</Label>
                <div className="flex gap-2">
                  <Input
                    type="color"
                    value={plantillaForm.color_banner || '#3b82f6'}
                    onChange={(e) => setPlantillaForm(prev => ({ ...prev, color_banner: e.target.value }))}
                    className="w-16 h-10 p-1"
                  />
                  <Input
                    value={plantillaForm.color_banner || ''}
                    onChange={(e) => setPlantillaForm(prev => ({ ...prev, color_banner: e.target.value }))}
                    placeholder="#3b82f6"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Asunto del Email</Label>
              <Input
                value={plantillaForm.asunto || ''}
                onChange={(e) => setPlantillaForm(prev => ({ ...prev, asunto: e.target.value }))}
                placeholder="Ej: ✨ Nueva Orden - {numero_orden}"
              />
              <p className="text-xs text-muted-foreground">
                Variables: {'{numero_orden}'}, {'{nombre_cliente}'}, {'{dispositivo}'}
              </p>
            </div>

            <div className="space-y-2">
              <Label>Título Principal</Label>
              <Input
                value={plantillaForm.titulo || ''}
                onChange={(e) => setPlantillaForm(prev => ({ ...prev, titulo: e.target.value }))}
                placeholder="Ej: ¡Orden Registrada!"
              />
            </div>

            <div className="space-y-2">
              <Label>Subtítulo</Label>
              <Input
                value={plantillaForm.subtitulo || ''}
                onChange={(e) => setPlantillaForm(prev => ({ ...prev, subtitulo: e.target.value }))}
                placeholder="Ej: Hemos recibido tu solicitud"
              />
            </div>

            <div className="space-y-2">
              <Label>Mensaje Principal</Label>
              <Textarea
                value={plantillaForm.mensaje_principal || ''}
                onChange={(e) => setPlantillaForm(prev => ({ ...prev, mensaje_principal: e.target.value }))}
                placeholder="Mensaje que se muestra al cliente..."
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label>Mensaje Secundario (opcional)</Label>
              <Textarea
                value={plantillaForm.mensaje_secundario || ''}
                onChange={(e) => setPlantillaForm(prev => ({ ...prev, mensaje_secundario: e.target.value }))}
                placeholder="Información adicional..."
                rows={2}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                <div>
                  <p className="font-medium text-sm">Mostrar barra de progreso</p>
                </div>
                <Switch
                  checked={plantillaForm.mostrar_progreso ?? true}
                  onCheckedChange={(v) => setPlantillaForm(prev => ({ ...prev, mostrar_progreso: v }))}
                />
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                <div>
                  <p className="font-medium text-sm">Mostrar tracking de envío</p>
                </div>
                <Switch
                  checked={plantillaForm.mostrar_tracking ?? false}
                  onCheckedChange={(v) => setPlantillaForm(prev => ({ ...prev, mostrar_tracking: v }))}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditPlantilla(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSavePlantilla} disabled={saving}>
              {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
              Guardar Cambios
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

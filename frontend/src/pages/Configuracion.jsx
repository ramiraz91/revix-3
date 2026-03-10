import { useState, useEffect } from 'react';
import { 
  Settings, 
  MessageSquare, 
  Mail, 
  Phone, 
  CheckCircle2, 
  XCircle, 
  Eye, 
  EyeOff,
  TestTube,
  Save,
  Loader2,
  ExternalLink
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import api from '@/lib/api';

export default function Configuracion() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [showTwilioToken, setShowTwilioToken] = useState(false);
  const [showSendgridKey, setShowSendgridKey] = useState(false);
  
  const [config, setConfig] = useState({
    twilio: { configurado: false, account_sid: '', phone_number: '' },
    sendgrid: { configurado: false, api_key: '', from_email: '' }
  });
  
  const [formData, setFormData] = useState({
    twilio_account_sid: '',
    twilio_auth_token: '',
    twilio_phone_number: '',
    sendgrid_api_key: '',
    sendgrid_from_email: ''
  });

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const response = await api.get('/configuracion/notificaciones');
      // Asegurar que config tenga la estructura esperada
      const data = response.data || {};
      setConfig({
        twilio: { 
          configurado: data.twilio?.configurado || false, 
          account_sid: data.twilio?.account_sid || '', 
          phone_number: data.twilio?.phone_number || '' 
        },
        sendgrid: { 
          configurado: data.sendgrid?.configurado || false, 
          api_key: data.sendgrid?.api_key || '', 
          from_email: data.sendgrid?.from_email || '' 
        }
      });
    } catch (error) {
      console.error('Error al cargar configuración:', error);
      toast.error('Error al cargar la configuración');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await api.post('/configuracion/notificaciones', formData);
      
      const results = response.data.results;
      
      if (results.twilio?.success) {
        toast.success('✅ Twilio configurado correctamente');
      } else if (results.twilio?.error) {
        toast.error(`❌ Error en Twilio: ${results.twilio.error}`);
      }
      
      if (results.sendgrid?.success) {
        toast.success('✅ SendGrid configurado correctamente');
      } else if (results.sendgrid?.error) {
        toast.error(`❌ Error en SendGrid: ${results.sendgrid.error}`);
      }
      
      // Recargar configuración
      await fetchConfig();
      
      // Limpiar formulario
      setFormData({
        twilio_account_sid: '',
        twilio_auth_token: '',
        twilio_phone_number: '',
        sendgrid_api_key: '',
        sendgrid_from_email: ''
      });
    } catch (error) {
      toast.error('Error al guardar la configuración');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      const response = await api.post('/configuracion/notificaciones/test');
      
      if (response.data.sms?.success) {
        toast.success('✅ SMS de prueba enviado correctamente');
      } else if (response.data.sms?.error) {
        toast.error(`❌ Error SMS: ${response.data.sms.error}`);
      }
      
      if (response.data.email?.success) {
        toast.success('✅ Email de prueba enviado correctamente');
      } else if (response.data.email?.error) {
        toast.error(`❌ Error Email: ${response.data.email.error}`);
      }
    } catch (error) {
      toast.error('Error al enviar pruebas');
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="configuracion-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Settings className="w-8 h-8" />
          Configuración
        </h1>
        <p className="text-muted-foreground mt-1">
          Gestiona las credenciales y configuración del sistema
        </p>
      </div>

      {/* Estado Actual */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            Estado de las Integraciones
          </CardTitle>
          <CardDescription>
            Estado actual de los servicios de notificación configurados
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Twilio Status */}
            <div className={`p-4 rounded-lg border-2 ${config.twilio.configurado ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
              <div className="flex items-center gap-3 mb-3">
                <Phone className={`w-6 h-6 ${config.twilio.configurado ? 'text-green-600' : 'text-red-600'}`} />
                <div>
                  <h3 className="font-semibold">Twilio SMS</h3>
                  <Badge variant={config.twilio.configurado ? 'default' : 'destructive'}>
                    {config.twilio.configurado ? 'Configurado' : 'No Configurado'}
                  </Badge>
                </div>
                {config.twilio.configurado ? (
                  <CheckCircle2 className="w-5 h-5 text-green-600 ml-auto" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600 ml-auto" />
                )}
              </div>
              {config.twilio.configurado && (
                <div className="text-sm space-y-1 text-muted-foreground">
                  <p><span className="font-medium">Account SID:</span> {config.twilio.account_sid}</p>
                  <p><span className="font-medium">Teléfono:</span> {config.twilio.phone_number}</p>
                </div>
              )}
            </div>

            {/* SendGrid Status */}
            <div className={`p-4 rounded-lg border-2 ${config.sendgrid.configurado ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
              <div className="flex items-center gap-3 mb-3">
                <Mail className={`w-6 h-6 ${config.sendgrid.configurado ? 'text-green-600' : 'text-red-600'}`} />
                <div>
                  <h3 className="font-semibold">SendGrid Email</h3>
                  <Badge variant={config.sendgrid.configurado ? 'default' : 'destructive'}>
                    {config.sendgrid.configurado ? 'Configurado' : 'No Configurado'}
                  </Badge>
                </div>
                {config.sendgrid.configurado ? (
                  <CheckCircle2 className="w-5 h-5 text-green-600 ml-auto" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600 ml-auto" />
                )}
              </div>
              {config.sendgrid.configurado && (
                <div className="text-sm space-y-1 text-muted-foreground">
                  <p><span className="font-medium">API Key:</span> {config.sendgrid.api_key}</p>
                  <p><span className="font-medium">Email remitente:</span> {config.sendgrid.from_email}</p>
                </div>
              )}
            </div>
          </div>

          {/* Test Button */}
          {(config.twilio.configurado || config.sendgrid.configurado) && (
            <div className="mt-6 flex justify-center">
              <Button 
                variant="outline" 
                onClick={handleTest} 
                disabled={testing}
                className="gap-2"
              >
                {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <TestTube className="w-4 h-4" />}
                Enviar Notificación de Prueba
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Configurar Twilio */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="w-5 h-5 text-blue-600" />
            Configurar Twilio SMS
          </CardTitle>
          <CardDescription>
            Introduce tus credenciales de Twilio para habilitar notificaciones SMS.
            <a 
              href="https://console.twilio.com" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-primary hover:underline ml-1 inline-flex items-center gap-1"
            >
              Obtener credenciales <ExternalLink className="w-3 h-3" />
            </a>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="twilio_account_sid">Account SID</Label>
              <Input
                id="twilio_account_sid"
                value={formData.twilio_account_sid}
                onChange={(e) => handleInputChange('twilio_account_sid', e.target.value)}
                placeholder="AC..."
                className="font-mono"
              />
            </div>
            <div>
              <Label htmlFor="twilio_auth_token">Auth Token</Label>
              <div className="relative">
                <Input
                  id="twilio_auth_token"
                  type={showTwilioToken ? 'text' : 'password'}
                  value={formData.twilio_auth_token}
                  onChange={(e) => handleInputChange('twilio_auth_token', e.target.value)}
                  placeholder="••••••••••••••••"
                  className="font-mono pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3"
                  onClick={() => setShowTwilioToken(!showTwilioToken)}
                >
                  {showTwilioToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </Button>
              </div>
            </div>
            <div className="md:col-span-2">
              <Label htmlFor="twilio_phone_number">Número de Teléfono Twilio</Label>
              <Input
                id="twilio_phone_number"
                value={formData.twilio_phone_number}
                onChange={(e) => handleInputChange('twilio_phone_number', e.target.value)}
                placeholder="+34612345678"
                className="font-mono"
              />
              <p className="text-xs text-muted-foreground mt-1">
                El número debe estar en formato E.164 (ej: +34612345678)
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Configurar SendGrid */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="w-5 h-5 text-blue-600" />
            Configurar SendGrid Email
          </CardTitle>
          <CardDescription>
            Introduce tus credenciales de SendGrid para habilitar notificaciones por email.
            <a 
              href="https://app.sendgrid.com/settings/api_keys" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-primary hover:underline ml-1 inline-flex items-center gap-1"
            >
              Obtener API Key <ExternalLink className="w-3 h-3" />
            </a>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="sendgrid_api_key">API Key</Label>
              <div className="relative">
                <Input
                  id="sendgrid_api_key"
                  type={showSendgridKey ? 'text' : 'password'}
                  value={formData.sendgrid_api_key}
                  onChange={(e) => handleInputChange('sendgrid_api_key', e.target.value)}
                  placeholder="SG.••••••••••••••••"
                  className="font-mono pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3"
                  onClick={() => setShowSendgridKey(!showSendgridKey)}
                >
                  {showSendgridKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </Button>
              </div>
            </div>
            <div>
              <Label htmlFor="sendgrid_from_email">Email Remitente</Label>
              <Input
                id="sendgrid_from_email"
                type="email"
                value={formData.sendgrid_from_email}
                onChange={(e) => handleInputChange('sendgrid_from_email', e.target.value)}
                placeholder="notificaciones@tudominio.com"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Debe ser un dominio verificado en SendGrid
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end gap-4">
        <Button 
          onClick={handleSave} 
          disabled={saving}
          size="lg"
          className="gap-2"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Guardar Configuración
        </Button>
      </div>

      {/* Help Section */}
      <Card className="bg-slate-50">
        <CardHeader>
          <CardTitle className="text-lg">¿Cómo configurar las notificaciones?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-semibold mb-2">📱 Twilio (SMS)</h4>
            <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
              <li>Crea una cuenta en <a href="https://www.twilio.com" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">twilio.com</a></li>
              <li>Ve a la <a href="https://console.twilio.com" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">consola de Twilio</a></li>
              <li>Copia tu Account SID y Auth Token</li>
              <li>Compra un número de teléfono con capacidad SMS</li>
              <li>Asegúrate de que el número esté habilitado para enviar SMS en España</li>
            </ol>
          </div>
          <Separator />
          <div>
            <h4 className="font-semibold mb-2">📧 SendGrid (Email)</h4>
            <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
              <li>Crea una cuenta en <a href="https://sendgrid.com" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">sendgrid.com</a></li>
              <li>Ve a Settings → API Keys y crea una nueva key con permisos "Full Access"</li>
              <li>Ve a Settings → Sender Authentication</li>
              <li>Verifica tu dominio (recomendado) o una dirección de email individual</li>
              <li>Usa el email verificado como remitente</li>
            </ol>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

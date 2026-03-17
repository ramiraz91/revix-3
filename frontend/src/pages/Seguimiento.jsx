import { useState, useEffect } from 'react';
import { 
  Smartphone, 
  Clock, 
  CheckCircle2, 
  Wrench, 
  Send,
  Package,
  Search,
  Phone,
  ArrowRight,
  Calendar,
  Truck,
  Image,
  X,
  AlertCircle,
  FileText,
  Shield,
  ExternalLink
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { seguimientoAPI, empresaAPI, getUploadUrl } from '@/lib/api';
import { toast } from 'sonner';

const statusConfig = {
  pendiente_recibir: { 
    label: 'Pendiente de Recibir', 
    icon: Clock, 
    color: 'bg-yellow-500',
    description: 'Tu dispositivo está en camino a nuestro centro de reparación'
  },
  recibida: { 
    label: 'Recibido', 
    icon: CheckCircle2, 
    color: 'bg-blue-500',
    description: 'Hemos recibido tu dispositivo en nuestro centro'
  },
  en_taller: { 
    label: 'En Reparación', 
    icon: Wrench, 
    color: 'bg-purple-500',
    description: 'Nuestro técnico está trabajando en tu dispositivo'
  },
  reparado: { 
    label: 'Reparado', 
    icon: CheckCircle2, 
    color: 'bg-green-500',
    description: '¡Tu dispositivo ha sido reparado con éxito!'
  },
  validacion: { 
    label: 'En Validación', 
    icon: Package, 
    color: 'bg-indigo-500',
    description: 'Estamos realizando las pruebas finales'
  },
  enviado: { 
    label: 'Enviado', 
    icon: Send, 
    color: 'bg-emerald-500',
    description: '¡Tu dispositivo está en camino de vuelta!'
  },
};

const statusOrder = ['pendiente_recibir', 'recibida', 'en_taller', 'reparado', 'validacion', 'enviado'];

export default function Seguimiento() {
  const [token, setToken] = useState('');
  const [telefono, setTelefono] = useState('');
  const [loading, setLoading] = useState(false);
  const [orden, setOrden] = useState(null);
  const [error, setError] = useState('');
  const [showImagePreview, setShowImagePreview] = useState(false);
  const [previewImage, setPreviewImage] = useState(null);
  
  // Legal acceptance
  const [showLegalModal, setShowLegalModal] = useState(false);
  const [legalAccepted, setLegalAccepted] = useState(false);
  const [rgpdAccepted, setRgpdAccepted] = useState(false);
  const [pendingOrden, setPendingOrden] = useState(null);
  const [empresaConfig, setEmpresaConfig] = useState(null);
  const [loadingConfig, setLoadingConfig] = useState(true);

  const [showRecoverForm, setShowRecoverForm] = useState(false);
  const [recoverData, setRecoverData] = useState({ email: '', telefono: '', dni: '' });
  const [recoverLoading, setRecoverLoading] = useState(false);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
  // Check URL params and load config on mount
    const urlToken = params.get('codigo');
    if (urlToken) {
      setToken(urlToken.toUpperCase());
    }
    
    // Load empresa config for legal text
    loadEmpresaConfig();
  }, []);

  const loadEmpresaConfig = async () => {
    try {
      setLoadingConfig(true);
      const response = await empresaAPI.obtenerPublica();
      setEmpresaConfig(response.data);
    } catch (error) {
      console.error('Error loading empresa config:', error);
      // Set default values
      setEmpresaConfig({
        nombre: 'Mi Empresa',
        textos_legales: {
          titulo_aceptacion: 'Condiciones del Servicio',
          aceptacion_seguimiento: 'Al acceder a este portal, el cliente acepta que la empresa no se hace responsable de los daños externos del dispositivo.'
        }
      });
    } finally {
      setLoadingConfig(false);
    }
  };

  const handleBuscar = async (e) => {
    e.preventDefault();
    if (!token.trim() || !telefono.trim()) {
      setError('Por favor, introduce el código de seguimiento y tu teléfono');
      return;
    }

    setLoading(true);
    setError('');
    setOrden(null);

    try {
      const response = await seguimientoAPI.verificar(token.trim(), telefono.trim());
      const ordenData = response.data.orden || response.data;
      const yaAcepto = response.data.ya_acepto_legal;
      
      if (yaAcepto) {
        // Ya aceptó antes, mostrar directamente
        setOrden(ordenData);
      } else {
        // Primera vez, mostrar modal legal
        setPendingOrden(ordenData);
        setShowLegalModal(true);
      }
    } catch (err) {
      const message = err.response?.data?.detail || 'Error al buscar la orden';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptLegal = async () => {
    if (!legalAccepted || !rgpdAccepted) {
      toast.error('Debes aceptar condiciones del servicio y RGPD para continuar');
      return;
    }

    try {
      setLoading(true);
      const response = await seguimientoAPI.verificar(token.trim(), telefono.trim(), {
        acepta_condiciones: true,
        acepta_rgpd: true,
      });
      const ordenData = response.data.orden || response.data;

      setOrden(ordenData || pendingOrden);
      setPendingOrden(null);
      setShowLegalModal(false);
      setLegalAccepted(false);
      setRgpdAccepted(false);
      toast.success('Consentimiento registrado correctamente');
    } catch (err) {
      const message = err.response?.data?.detail || 'No se pudo registrar el consentimiento';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelLegal = () => {
    setShowLegalModal(false);
    setPendingOrden(null);
    setLegalAccepted(false);
    setRgpdAccepted(false);
    toast.info('Debes aceptar las condiciones para ver el estado de tu reparación');
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getRgpdText = () => {
    const text = empresaConfig?.textos_legales?.politica_privacidad || '';
    const nombre = empresaConfig?.nombre || 'Mi Empresa';
    return text.replace(/\[NOMBRE_EMPRESA\]/g, nombre);
  };

  const handleRecover = async (e) => {
    e.preventDefault();
    if (!recoverData.email && !recoverData.telefono) {
      toast.error('Introduce al menos tu email o teléfono');
      return;
    }
    setRecoverLoading(true);
    try {
      const res = await seguimientoAPI.recuperar(recoverData);
      toast.success(res.data.message);
      setShowRecoverForm(false);
      setRecoverData({ email: '', telefono: '', dni: '' });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'No se encontraron datos');
    } finally {
      setRecoverLoading(false);
    }
  };

  const openPreview = (fileName) => {
    setPreviewImage(getUploadUrl(fileName));
    setShowImagePreview(true);
  };

  // Replace placeholder in legal text
  const getLegalText = () => {
    const text = empresaConfig?.textos_legales?.aceptacion_seguimiento || '';
    const nombre = empresaConfig?.nombre || 'Mi Empresa';
    return text.replace(/\[NOMBRE_EMPRESA\]/g, nombre);
  };

  const currentStatus = orden ? statusConfig[orden.estado] : null;
  const currentStep = orden ? statusOrder.indexOf(orden.estado) : -1;
  const logoUrl = empresaConfig?.logo?.url || empresaConfig?.logo_url;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Header */}
      <header className="bg-white border-b shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
            <Smartphone className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg">Portal de Seguimiento</h1>
            <p className="text-xs text-muted-foreground">Consulta el estado de tu reparación</p>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {!orden ? (
          /* Search Form */
          <div className="space-y-8">
            <div className="text-center">
              <h2 className="text-2xl font-bold mb-2">Consulta el estado de tu reparación</h2>
              <p className="text-muted-foreground">
                Introduce el código de seguimiento y tu teléfono para ver el estado
              </p>
            </div>

            <Card className="max-w-md mx-auto">
              <CardContent className="pt-6">
                <form onSubmit={handleBuscar} className="space-y-4">
                  <div>
                    <Label htmlFor="token">Código de Seguimiento</Label>
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        id="token"
                        placeholder="Ej: ABC123DEF456"
                        value={token}
                        onChange={(e) => setToken(e.target.value.toUpperCase())}
                        className="pl-10 font-mono uppercase"
                        data-testid="token-input"
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      El código que recibiste al crear tu orden
                    </p>
                  </div>

                  <div>
                    <Label htmlFor="telefono">Teléfono</Label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        id="telefono"
                        type="tel"
                        placeholder="Tu número de teléfono"
                        value={telefono}
                        onChange={(e) => setTelefono(e.target.value)}
                        className="pl-10"
                        data-testid="telefono-input"
                      />
                    </div>
                  </div>

                  {error && (
                    <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 p-3 rounded-lg">
                      <AlertCircle className="w-4 h-4 flex-shrink-0" />
                      {error}
                    </div>
                  )}

                  <Button 
                    type="submit" 
                    className="w-full" 
                    disabled={loading}
                    data-testid="buscar-btn"
                  >
                    {loading ? 'Buscando...' : 'Ver estado de mi reparación'}
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                </form>
              </CardContent>
            </Card>

            <div className="text-center text-sm text-muted-foreground space-y-3">
              <p>¿No tienes el código?</p>
              {!showRecoverForm ? (
                <Button variant="link" onClick={() => setShowRecoverForm(true)} className="text-blue-600">
                  Recuperar mis credenciales de seguimiento
                </Button>
              ) : (
                <Card className="max-w-md mx-auto text-left">
                  <CardContent className="pt-4">
                    <p className="text-sm font-medium mb-3">Recuperar credenciales</p>
                    <form onSubmit={handleRecover} className="space-y-3">
                      <Input
                        placeholder="Email"
                        type="email"
                        value={recoverData.email}
                        onChange={(e) => setRecoverData(prev => ({ ...prev, email: e.target.value }))}
                      />
                      <Input
                        placeholder="Teléfono"
                        type="tel"
                        value={recoverData.telefono}
                        onChange={(e) => setRecoverData(prev => ({ ...prev, telefono: e.target.value }))}
                      />
                      <Input
                        placeholder="DNI/NIE (opcional)"
                        value={recoverData.dni}
                        onChange={(e) => setRecoverData(prev => ({ ...prev, dni: e.target.value }))}
                      />
                      <div className="flex gap-2">
                        <Button type="submit" size="sm" disabled={recoverLoading} className="flex-1">
                          {recoverLoading ? 'Enviando...' : 'Enviar credenciales'}
                        </Button>
                        <Button type="button" variant="outline" size="sm" onClick={() => setShowRecoverForm(false)}>
                          Cancelar
                        </Button>
                      </div>
                    </form>
                  </CardContent>
                </Card>
              )}
              {empresaConfig?.telefono && (
                <p className="mt-1 font-medium">{empresaConfig.telefono}</p>
              )}
            </div>
          </div>
        ) : (
          /* Order Details */
          <div className="space-y-6 animate-fade-in">
            {/* Back Button */}
            <Button 
              variant="ghost" 
              onClick={() => setOrden(null)}
              className="mb-4"
            >
              ← Nueva consulta
            </Button>

            {/* Order Header */}
            <Card className="border-2 border-primary/20">
              <CardContent className="pt-6">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Orden de reparación</p>
                    <p className="text-2xl font-bold font-mono">{orden.numero_orden}</p>
                    {orden.cliente?.nombre && (
                      <p className="text-sm text-muted-foreground mt-1">
                        {orden.cliente.nombre}
                      </p>
                    )}
                    {orden.numero_autorizacion && (
                      <p className="text-xs text-blue-600 mt-1">
                        Nº Autorización: <span className="font-mono">{orden.numero_autorizacion}</span>
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <Badge className={`${currentStatus?.color} text-white px-4 py-2 text-sm`}>
                      {currentStatus?.label}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Status Message */}
            <Card className={`border-l-4 ${currentStatus?.color.replace('bg-', 'border-')}`}>
              <CardContent className="py-4">
                <div className="flex items-center gap-4">
                  {currentStatus && <currentStatus.icon className={`w-8 h-8 ${currentStatus.color.replace('bg-', 'text-')}`} />}
                  <div>
                    <p className="font-semibold">{currentStatus?.label}</p>
                    <p className="text-muted-foreground">{currentStatus?.description}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Shipping Codes - NEW SECTION */}
            <Card className="border-blue-200 bg-blue-50/50">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Truck className="w-5 h-5 text-blue-600" />
                  Información de Envío
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Código de Recogida (Entrada) */}
                  <div className="p-3 bg-white rounded-lg border">
                    <p className="text-xs text-muted-foreground uppercase mb-1">Nº Recogida</p>
                    {orden.codigo_recogida_entrada ? (
                      <>
                        <p className="font-mono font-semibold text-blue-700">{orden.codigo_recogida_entrada}</p>
                        {orden.agencia_envio === 'GLS' && (
                          <a href={`https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/?match=${orden.codigo_recogida_entrada}`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline mt-1">
                            <ExternalLink className="w-3 h-3" /> Seguir recogida en GLS
                          </a>
                        )}
                      </>
                    ) : (
                      <p className="text-muted-foreground text-sm">Pendiente</p>
                    )}
                  </div>
                  
                  {/* Código de Envío (Salida) */}
                  <div className="p-3 bg-white rounded-lg border">
                    <p className="text-xs text-muted-foreground uppercase mb-1">Nº Envío</p>
                    {(orden.codigo_seguimiento_salida || orden.codigo_recogida_salida) ? (
                      <>
                        <p className="font-mono font-semibold text-emerald-700">{orden.codigo_seguimiento_salida || orden.codigo_recogida_salida}</p>
                        {orden.agencia_envio === 'GLS' && (
                          <a href={`https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/?match=${orden.codigo_seguimiento_salida || orden.codigo_recogida_salida}`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-emerald-600 hover:underline mt-1">
                            <ExternalLink className="w-3 h-3" /> Seguir envío en GLS
                          </a>
                        )}
                      </>
                    ) : (
                      <p className="text-muted-foreground text-sm">Pendiente</p>
                    )}
                  </div>
                </div>
                
                {orden.agencia_envio && (
                  <div className="mt-3 pt-3 border-t">
                    <p className="text-sm">
                      <span className="text-muted-foreground">Agencia: </span>
                      <span className="font-medium">{orden.agencia_envio}</span>
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Progress Bar */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Progreso de la reparación</CardTitle>
              </CardHeader>
              <CardContent>
                {/* Desktop: horizontal */}
                <div className="hidden sm:flex items-center justify-between pb-2">
                  {statusOrder.map((status, index) => {
                    const config = statusConfig[status];
                    const Icon = config.icon;
                    const isCompleted = currentStep > index;
                    const isCurrent = currentStep === index;
                    
                    return (
                      <div key={status} className="flex items-center flex-1 min-w-0">
                        <div className="flex flex-col items-center">
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-all ${
                            isCompleted ? 'bg-green-500 text-white' :
                            isCurrent ? `${config.color} text-white ring-4 ring-offset-2` :
                            'bg-slate-200 text-slate-400'
                          }`}>
                            {isCompleted ? <CheckCircle2 className="w-5 h-5" /> : <Icon className="w-5 h-5" />}
                          </div>
                          <span className={`text-[10px] mt-2 text-center whitespace-nowrap ${
                            isCurrent ? 'font-semibold text-primary' : 'text-muted-foreground'
                          }`}>
                            {config.label}
                          </span>
                        </div>
                        {index < statusOrder.length - 1 && (
                          <div className={`flex-1 h-1 mx-1 rounded min-w-3 ${
                            currentStep > index ? 'bg-green-500' : 'bg-slate-200'
                          }`} />
                        )}
                      </div>
                    );
                  })}
                </div>
                {/* Mobile: vertical */}
                <div className="sm:hidden space-y-2">
                  {statusOrder.map((status, index) => {
                    const config = statusConfig[status];
                    const Icon = config.icon;
                    const isCompleted = currentStep > index;
                    const isCurrent = currentStep === index;
                    
                    return (
                      <div key={status} className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                          isCompleted ? 'bg-green-500 text-white' :
                          isCurrent ? `${config.color} text-white` :
                          'bg-slate-200 text-slate-400'
                        }`}>
                          {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                        </div>
                        <span className={`text-sm ${
                          isCurrent ? 'font-semibold text-primary' : isCompleted ? 'text-green-700' : 'text-muted-foreground'
                        }`}>
                          {config.label}
                        </span>
                        {isCurrent && <Badge className={`${config.color} text-white text-[10px] ml-auto`}>Actual</Badge>}
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Device Info */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Smartphone className="w-5 h-5" />
                  Tu dispositivo
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground uppercase">Modelo</p>
                    <p className="font-semibold">{orden.dispositivo.modelo}</p>
                  </div>
                  {orden.dispositivo.color && (
                    <div>
                      <p className="text-xs text-muted-foreground uppercase">Color</p>
                      <p className="font-medium">{orden.dispositivo.color}</p>
                    </div>
                  )}
                  <div className="sm:col-span-2">
                    <p className="text-xs text-muted-foreground uppercase">Avería reportada</p>
                    <p className="mt-1 p-3 bg-slate-50 rounded-lg text-sm">{orden.dispositivo.averia}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Timeline / Dates */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Calendar className="w-5 h-5" />
                  Fechas
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {orden.fechas?.creacion && (
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-blue-500" />
                      <div className="flex-1">
                        <p className="text-sm font-medium">Orden creada</p>
                        <p className="text-xs text-muted-foreground">{formatDate(orden.fechas.creacion)}</p>
                      </div>
                    </div>
                  )}
                  {orden.fechas?.recibida && (
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-blue-500" />
                      <div className="flex-1">
                        <p className="text-sm font-medium">Recibido en centro</p>
                        <p className="text-xs text-muted-foreground">{formatDate(orden.fechas.recibida)}</p>
                      </div>
                    </div>
                  )}
                  {orden.fechas?.inicio_reparacion && (
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-purple-500" />
                      <div className="flex-1">
                        <p className="text-sm font-medium">Inicio de reparación</p>
                        <p className="text-xs text-muted-foreground">{formatDate(orden.fechas.inicio_reparacion)}</p>
                      </div>
                    </div>
                  )}
                  {orden.fechas?.fin_reparacion && (
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-green-500" />
                      <div className="flex-1">
                        <p className="text-sm font-medium">Reparación completada</p>
                        <p className="text-xs text-muted-foreground">{formatDate(orden.fechas.fin_reparacion)}</p>
                      </div>
                    </div>
                  )}
                  {orden.fechas?.enviado && (
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-emerald-500" />
                      <div className="flex-1">
                        <p className="text-sm font-medium">Enviado</p>
                        <p className="text-xs text-muted-foreground">{formatDate(orden.fechas.enviado)}</p>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Shipping Confirmation when Enviado */}
            {orden.estado === 'enviado' && (orden.codigo_seguimiento_salida || orden.codigo_recogida_salida) && (
              <Card className="border-emerald-200 bg-emerald-50">
                <CardContent className="py-4">
                  <div className="flex items-center gap-4">
                    <Truck className="w-8 h-8 text-emerald-600" />
                    <div>
                      <p className="font-semibold text-emerald-800">¡Tu dispositivo está en camino!</p>
                      <p className="text-sm text-emerald-700">
                        {orden.agencia_envio && <>Agencia: {orden.agencia_envio} | </>}Código: <span className="font-mono">{orden.codigo_seguimiento_salida || orden.codigo_recogida_salida}</span>
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Photos */}
            {orden.fotos && orden.fotos.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Image className="w-5 h-5" />
                    Fotos del dispositivo
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2">
                    {orden.fotos.map((foto, index) => (
                      <div 
                        key={index}
                        className="aspect-square rounded-lg border overflow-hidden cursor-pointer hover:opacity-90 transition-opacity"
                        onClick={() => openPreview(foto)}
                      >
                        <img
                          src={getUploadUrl(foto)}
                          alt={`Foto ${index + 1}`}
                          className="w-full h-full object-cover"
                        />
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Last Update */}
            <p className="text-center text-xs text-muted-foreground">
              Última actualización: {formatDate(orden.fechas.ultima_actualizacion)}
            </p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-16">
        <div className="max-w-4xl mx-auto px-4 py-6 text-center text-sm text-muted-foreground">
          <p>Servicio Técnico de Telefonía Móvil</p>
          {empresaConfig?.telefono && <p className="mt-1">Tel: {empresaConfig.telefono}</p>}
        </div>
      </footer>

      {/* Legal Acceptance Modal */}
      <Dialog open={showLegalModal} onOpenChange={() => {}}>
        <DialogContent className="max-w-lg" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-amber-500" />
              {empresaConfig?.textos_legales?.titulo_aceptacion || 'Condiciones del Servicio'}
            </DialogTitle>
            <DialogDescription>
              Por favor, lee y acepta las siguientes condiciones antes de continuar.
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            <div className="max-h-60 overflow-y-auto p-4 bg-slate-50 rounded-lg border text-sm leading-relaxed">
              {getLegalText()}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-start gap-3 p-3 bg-amber-50 rounded-lg border border-amber-200">
              <Checkbox
                id="legal-accept"
                checked={legalAccepted}
                onCheckedChange={setLegalAccepted}
                data-testid="legal-checkbox"
              />
              <label htmlFor="legal-accept" className="text-sm cursor-pointer">
                He leído y acepto las condiciones del servicio. Entiendo que {empresaConfig?.nombre || 'la empresa'} no se hace responsable de los daños externos preexistentes en el dispositivo.
              </label>
            </div>

            <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <Checkbox
                id="rgpd-accept"
                checked={rgpdAccepted}
                onCheckedChange={setRgpdAccepted}
                data-testid="rgpd-checkbox"
              />
              <label htmlFor="rgpd-accept" className="text-sm cursor-pointer">
                Acepto el tratamiento de datos personales según RGPD para la gestión del servicio. {getRgpdText()}
              </label>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={handleCancelLegal}>
              Cancelar
            </Button>
            <Button onClick={handleAcceptLegal} disabled={!legalAccepted || !rgpdAccepted || loading} data-testid="accept-legal-btn">
              Aceptar y Continuar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Image Preview Dialog */}
      <Dialog open={showImagePreview} onOpenChange={setShowImagePreview}>
        <DialogContent className="max-w-3xl p-2">
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-2 top-2 z-10"
            onClick={() => setShowImagePreview(false)}
          >
            <X className="w-4 h-4" />
          </Button>
          {previewImage && (
            <img
              src={previewImage}
              alt="Preview"
              className="w-full h-auto rounded-lg"
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { 
  Truck, Settings, Save, Package, MapPin, Phone, Mail, Printer, 
  RefreshCw, AlertCircle, CheckCircle, ExternalLink, Plus, Trash2, Eye,
  Building2, Key, Globe
} from 'lucide-react';
import { transportistasAPI, etiquetasEnvioAPI, ordenesAPI } from '@/lib/api';
import { toast } from 'sonner';

const TRANSPORTISTAS_INFO = {
  mrw: { nombre: 'MRW', color: 'bg-red-500', logo: '🔴', docs: 'https://www.mrw.es/empresas/' },
  seur: { nombre: 'SEUR', color: 'bg-blue-500', logo: '🔵', docs: 'https://www.seur.com/empresas/' },
  correos: { nombre: 'Correos Express', color: 'bg-yellow-500', logo: '🟡', docs: 'https://www.correosexpress.com/' },
  dhl: { nombre: 'DHL', color: 'bg-yellow-400', logo: '🟨', docs: 'https://www.dhl.com/es-es/' },
  ups: { nombre: 'UPS', color: 'bg-amber-700', logo: '🟤', docs: 'https://www.ups.com/es/' },
  gls: { nombre: 'GLS', color: 'bg-orange-500', logo: '🟠', docs: 'https://www.gls-spain.es/' }
};

export default function EtiquetasEnvio() {
  const [transportistas, setTransportistas] = useState([]);
  const [etiquetas, setEtiquetas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('etiquetas');
  const [selectedTransportista, setSelectedTransportista] = useState(null);
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [configForm, setConfigForm] = useState({});
  const [showNuevaEtiqueta, setShowNuevaEtiqueta] = useState(false);
  const [nuevaEtiquetaForm, setNuevaEtiquetaForm] = useState({
    orden_id: '',
    transportista: 'mrw',
    tipo: 'salida',
    peso_kg: 0.5,
    contenido: 'Dispositivo móvil'
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [transRes, etiqRes] = await Promise.all([
        transportistasAPI.listar(),
        etiquetasEnvioAPI.listar()
      ]);
      setTransportistas(transRes.data || []);
      setEtiquetas(etiqRes.data || []);
    } catch (e) {
      console.error('Error:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleConfigTransportista = async (codigo) => {
    try {
      const res = await transportistasAPI.obtener(codigo);
      setConfigForm(res.data || { codigo, activo: false });
      setSelectedTransportista(codigo);
      setShowConfigDialog(true);
    } catch (e) {
      // Si no existe, crear uno nuevo
      setConfigForm({ codigo, nombre: TRANSPORTISTAS_INFO[codigo]?.nombre || codigo, activo: false });
      setSelectedTransportista(codigo);
      setShowConfigDialog(true);
    }
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      await transportistasAPI.actualizar(selectedTransportista, configForm);
      toast.success('Configuración guardada');
      setShowConfigDialog(false);
      fetchData();
    } catch (e) {
      toast.error('Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  const handleCrearEtiqueta = async () => {
    if (!nuevaEtiquetaForm.orden_id) {
      toast.error('Selecciona una orden');
      return;
    }
    
    try {
      setSaving(true);
      await etiquetasEnvioAPI.crear(nuevaEtiquetaForm);
      toast.success('Etiqueta creada');
      setShowNuevaEtiqueta(false);
      setNuevaEtiquetaForm({
        orden_id: '',
        transportista: 'mrw',
        tipo: 'salida',
        peso_kg: 0.5,
        contenido: 'Dispositivo móvil'
      });
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al crear etiqueta');
    } finally {
      setSaving(false);
    }
  };

  const handleEliminarEtiqueta = async (id) => {
    if (!confirm('¿Eliminar esta etiqueta?')) return;
    try {
      await etiquetasEnvioAPI.eliminar(id);
      toast.success('Etiqueta eliminada');
      fetchData();
    } catch (e) {
      toast.error('Error al eliminar');
    }
  };

  const getEstadoBadge = (estado) => {
    const estilos = {
      pendiente: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      pendiente_api: 'bg-orange-100 text-orange-800 border-orange-200',
      generada: 'bg-blue-100 text-blue-800 border-blue-200',
      enviada: 'bg-purple-100 text-purple-800 border-purple-200',
      entregada: 'bg-green-100 text-green-800 border-green-200',
      error: 'bg-red-100 text-red-800 border-red-200'
    };
    return estilos[estado] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
        Cargando...
      </div>
    );
  }

  const transportistasActivos = transportistas.filter(t => t.activo);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Truck className="w-7 h-7 text-blue-600" />
            </div>
            Etiquetas de Envío
          </h1>
          <p className="text-muted-foreground mt-1">
            Genera etiquetas de envío para tus reparaciones
          </p>
        </div>
        <Button onClick={() => setShowNuevaEtiqueta(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Nueva Etiqueta
        </Button>
      </div>

      {/* Banner de estado */}
      {transportistasActivos.length === 0 && (
        <Card className="border-yellow-200 bg-yellow-50/50">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-6 h-6 text-yellow-600" />
              <div>
                <p className="font-medium">Sin transportistas configurados</p>
                <p className="text-sm text-muted-foreground">
                  Configura al menos un transportista en la pestaña "Transportistas" para poder generar etiquetas automáticamente.
                  Mientras tanto, puedes crear etiquetas manuales.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="etiquetas" className="flex items-center gap-2">
            <Package className="w-4 h-4" />
            Etiquetas
          </TabsTrigger>
          <TabsTrigger value="transportistas" className="flex items-center gap-2">
            <Truck className="w-4 h-4" />
            Transportistas
          </TabsTrigger>
        </TabsList>

        {/* Tab: Etiquetas */}
        <TabsContent value="etiquetas">
          <Card>
            <CardHeader>
              <CardTitle>Etiquetas Generadas</CardTitle>
              <CardDescription>
                Lista de etiquetas de envío creadas
              </CardDescription>
            </CardHeader>
            <CardContent>
              {etiquetas.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <Package className="w-16 h-16 mx-auto mb-4 opacity-30" />
                  <p className="text-lg">No hay etiquetas creadas</p>
                  <p className="text-sm">Crea una etiqueta para una orden de envío</p>
                  <Button variant="outline" className="mt-4" onClick={() => setShowNuevaEtiqueta(true)}>
                    <Plus className="w-4 h-4 mr-2" />
                    Crear Primera Etiqueta
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {etiquetas.map((etq) => (
                    <div key={etq.id} className="p-4 bg-slate-50 rounded-lg border hover:border-blue-200 transition-colors">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-xl">{TRANSPORTISTAS_INFO[etq.transportista]?.logo || '📦'}</span>
                            <span className="font-medium">{TRANSPORTISTAS_INFO[etq.transportista]?.nombre || etq.transportista}</span>
                            <Badge className={getEstadoBadge(etq.estado)}>{etq.estado}</Badge>
                            <Badge variant="outline">{etq.tipo}</Badge>
                          </div>
                          
                          <p className="text-sm font-medium text-blue-600">Orden: {etq.numero_orden}</p>
                          
                          <div className="grid grid-cols-2 gap-4 mt-3 text-sm">
                            <div>
                              <p className="text-muted-foreground flex items-center gap-1">
                                <MapPin className="w-3 h-3" /> Destino
                              </p>
                              <p className="font-medium">{etq.destinatario_nombre}</p>
                              <p className="text-muted-foreground text-xs">
                                {etq.destinatario_direccion}, {etq.destinatario_cp} {etq.destinatario_ciudad}
                              </p>
                            </div>
                            <div>
                              <p className="text-muted-foreground flex items-center gap-1">
                                <Package className="w-3 h-3" /> Paquete
                              </p>
                              <p>{etq.peso_kg}kg - {etq.contenido}</p>
                            </div>
                          </div>

                          {etq.codigo_seguimiento && (
                            <div className="mt-3 p-2 bg-green-50 rounded border border-green-200">
                              <p className="text-xs text-green-600 font-medium">Código de Seguimiento</p>
                              <p className="font-mono font-bold text-green-800">{etq.codigo_seguimiento}</p>
                            </div>
                          )}

                          {etq.error_mensaje && (
                            <div className="mt-3 p-2 bg-red-50 rounded border border-red-200">
                              <p className="text-xs text-red-600">{etq.error_mensaje}</p>
                            </div>
                          )}
                        </div>

                        <div className="flex flex-col gap-2 ml-4">
                          {etq.etiqueta_pdf_url && (
                            <Button size="sm" variant="outline" asChild>
                              <a href={etq.etiqueta_pdf_url} target="_blank" rel="noopener noreferrer">
                                <Printer className="w-4 h-4 mr-1" />
                                Imprimir
                              </a>
                            </Button>
                          )}
                          {etq.url_seguimiento && (
                            <Button size="sm" variant="outline" asChild>
                              <a href={etq.url_seguimiento} target="_blank" rel="noopener noreferrer">
                                <ExternalLink className="w-4 h-4 mr-1" />
                                Seguimiento
                              </a>
                            </Button>
                          )}
                          <Button 
                            size="sm" 
                            variant="ghost" 
                            className="text-red-500 hover:text-red-700 hover:bg-red-50"
                            onClick={() => handleEliminarEtiqueta(etq.id)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Transportistas */}
        <TabsContent value="transportistas">
          <Card>
            <CardHeader>
              <CardTitle>Configuración de Transportistas</CardTitle>
              <CardDescription>
                Configura las credenciales de API de cada transportista para generar etiquetas automáticamente
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {Object.entries(TRANSPORTISTAS_INFO).map(([codigo, info]) => {
                  const config = transportistas.find(t => t.codigo === codigo);
                  const isActivo = config?.activo || false;
                  
                  return (
                    <div 
                      key={codigo}
                      className={`p-4 rounded-xl border-2 transition-all cursor-pointer hover:shadow-md ${
                        isActivo ? 'border-green-300 bg-green-50/50' : 'border-slate-200 bg-slate-50'
                      }`}
                      onClick={() => handleConfigTransportista(codigo)}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className="text-2xl">{info.logo}</span>
                          <span className="font-semibold">{info.nombre}</span>
                        </div>
                        <Badge variant={isActivo ? "default" : "secondary"} className={isActivo ? 'bg-green-500' : ''}>
                          {isActivo ? 'Activo' : 'Inactivo'}
                        </Badge>
                      </div>
                      
                      <p className="text-sm text-muted-foreground mb-3">
                        {isActivo 
                          ? 'API configurada y lista para usar' 
                          : 'Haz clic para configurar las credenciales'}
                      </p>
                      
                      <div className="flex items-center justify-between">
                        <Button size="sm" variant="outline">
                          <Settings className="w-4 h-4 mr-1" />
                          Configurar
                        </Button>
                        <a 
                          href={info.docs} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-xs text-blue-500 hover:underline flex items-center gap-1"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <ExternalLink className="w-3 h-3" />
                          Documentación
                        </a>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <p className="text-sm text-blue-800">
                  <strong>💡 Nota:</strong> Para obtener las credenciales de API, contacta con el departamento comercial 
                  del transportista. Normalmente necesitarás un contrato de servicios activo para acceder a su API.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Dialog: Configurar Transportista */}
      <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <span className="text-2xl">{TRANSPORTISTAS_INFO[selectedTransportista]?.logo}</span>
              Configurar {TRANSPORTISTAS_INFO[selectedTransportista]?.nombre || selectedTransportista}
            </DialogTitle>
            <DialogDescription>
              Introduce las credenciales de API proporcionadas por el transportista
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
              <div>
                <p className="font-medium">Integración Activa</p>
                <p className="text-sm text-muted-foreground">Habilita la generación automática de etiquetas</p>
              </div>
              <Switch
                checked={configForm.activo || false}
                onCheckedChange={(v) => setConfigForm(prev => ({ ...prev, activo: v }))}
              />
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Globe className="w-4 h-4" />
                URL de la API
              </Label>
              <Input
                placeholder="https://api.transportista.com/v1"
                value={configForm.api_url || ''}
                onChange={(e) => setConfigForm(prev => ({ ...prev, api_url: e.target.value }))}
              />
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Key className="w-4 h-4" />
                API Key
              </Label>
              <Input
                type="password"
                placeholder="••••••••"
                value={configForm.api_key || ''}
                onChange={(e) => setConfigForm(prev => ({ ...prev, api_key: e.target.value }))}
              />
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Key className="w-4 h-4" />
                API Secret
              </Label>
              <Input
                type="password"
                placeholder="••••••••"
                value={configForm.api_secret || ''}
                onChange={(e) => setConfigForm(prev => ({ ...prev, api_secret: e.target.value }))}
              />
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Building2 className="w-4 h-4" />
                Código de Cliente
              </Label>
              <Input
                placeholder="Código asignado por el transportista"
                value={configForm.cliente_id || ''}
                onChange={(e) => setConfigForm(prev => ({ ...prev, cliente_id: e.target.value }))}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConfigDialog(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSaveConfig} disabled={saving}>
              {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
              Guardar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Nueva Etiqueta */}
      <Dialog open={showNuevaEtiqueta} onOpenChange={setShowNuevaEtiqueta}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nueva Etiqueta de Envío</DialogTitle>
            <DialogDescription>
              Crea una etiqueta para enviar un dispositivo reparado
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>ID de Orden *</Label>
              <Input
                placeholder="Pega el ID de la orden"
                value={nuevaEtiquetaForm.orden_id}
                onChange={(e) => setNuevaEtiquetaForm(prev => ({ ...prev, orden_id: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground">
                Puedes obtener el ID desde el detalle de la orden
              </p>
            </div>

            <div className="space-y-2">
              <Label>Transportista</Label>
              <Select 
                value={nuevaEtiquetaForm.transportista} 
                onValueChange={(v) => setNuevaEtiquetaForm(prev => ({ ...prev, transportista: v }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(TRANSPORTISTAS_INFO).map(([codigo, info]) => (
                    <SelectItem key={codigo} value={codigo}>
                      {info.logo} {info.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Tipo de Envío</Label>
              <Select 
                value={nuevaEtiquetaForm.tipo} 
                onValueChange={(v) => setNuevaEtiquetaForm(prev => ({ ...prev, tipo: v }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="salida">Envío al cliente</SelectItem>
                  <SelectItem value="recogida">Recogida a domicilio</SelectItem>
                  <SelectItem value="devolucion">Devolución</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Peso (kg)</Label>
                <Input
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={nuevaEtiquetaForm.peso_kg}
                  onChange={(e) => setNuevaEtiquetaForm(prev => ({ ...prev, peso_kg: parseFloat(e.target.value) }))}
                />
              </div>
              <div className="space-y-2">
                <Label>Contenido</Label>
                <Input
                  value={nuevaEtiquetaForm.contenido}
                  onChange={(e) => setNuevaEtiquetaForm(prev => ({ ...prev, contenido: e.target.value }))}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowNuevaEtiqueta(false)}>
              Cancelar
            </Button>
            <Button onClick={handleCrearEtiqueta} disabled={saving}>
              {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Package className="w-4 h-4 mr-2" />}
              Crear Etiqueta
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

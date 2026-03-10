import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Search, 
  Shield,
  Loader2,
  Users,
  TrendingUp,
  MapPin,
  Euro,
  Trophy,
  Phone,
  Mail,
  User,
  Smartphone,
  FileText,
  Calendar,
  Download,
  Plus,
  Send,
  MessageSquare,
  Image,
  ExternalLink,
  CheckCircle2,
  XCircle,
  AlertCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { insuramaAPI } from '@/lib/api';
import { toast } from 'sonner';

// Import reusable components
import {
  InsuramaAccionesTab,
  InsuramaDetalleTab,
  InsuramaClienteTab,
  InsuramaObservacionesTab,
  InsuramaFotosTab,
} from '@/components/insurama';

export default function BuscarSiniestro() {
  const navigate = useNavigate();
  const [codigoBusqueda, setCodigoBusqueda] = useState('');
  const [buscando, setBuscando] = useState(false);
  
  // Detalle de presupuesto
  const [presupuesto, setPresupuesto] = useState(null);
  const [showDetalle, setShowDetalle] = useState(false);
  
  // Competidores
  const [competidores, setCompetidores] = useState(null);
  const [loadingCompetidores, setLoadingCompetidores] = useState(false);
  
  // Observaciones y fotos
  const [observaciones, setObservaciones] = useState([]);
  const [loadingObservaciones, setLoadingObservaciones] = useState(false);
  const [fotos, setFotos] = useState([]);
  const [loadingFotos, setLoadingFotos] = useState(false);
  
  // Importar
  const [importando, setImportando] = useState(false);

  // Estado de conexión
  const [configStatus, setConfigStatus] = useState(null);
  const [checkingConfig, setCheckingConfig] = useState(true);

  useEffect(() => {
    checkConfig();
  }, []);

  const checkConfig = async () => {
    try {
      const res = await insuramaAPI.obtenerConfig();
      setConfigStatus(res.data);
    } catch (error) {
      console.error('Error checking config:', error);
    } finally {
      setCheckingConfig(false);
    }
  };

  const handleBuscar = async () => {
    if (!codigoBusqueda.trim()) {
      toast.error('Introduce un código de siniestro');
      return;
    }

    setBuscando(true);
    setPresupuesto(null);
    setCompetidores(null);
    setObservaciones([]);
    setFotos([]);

    try {
      const res = await insuramaAPI.obtenerPresupuesto(codigoBusqueda.trim());
      setPresupuesto(res.data);
      setShowDetalle(true);
      // Load additional data
      loadCompetidores(codigoBusqueda.trim());
      loadObservaciones(codigoBusqueda.trim());
      loadFotos(codigoBusqueda.trim());
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Presupuesto no encontrado');
    } finally {
      setBuscando(false);
    }
  };

  const loadCompetidores = async (codigo) => {
    setLoadingCompetidores(true);
    try {
      const res = await insuramaAPI.obtenerCompetidores(codigo);
      setCompetidores(res.data);
    } catch (error) {
      console.error('Error cargando competidores:', error);
    } finally {
      setLoadingCompetidores(false);
    }
  };

  const loadObservaciones = async (codigo) => {
    setLoadingObservaciones(true);
    try {
      const res = await insuramaAPI.obtenerObservaciones(codigo);
      setObservaciones(res.data.observaciones || []);
    } catch (error) {
      console.error('Error cargando observaciones:', error);
    } finally {
      setLoadingObservaciones(false);
    }
  };

  const loadFotos = async (codigo) => {
    setLoadingFotos(true);
    try {
      const res = await insuramaAPI.obtenerFotos(codigo);
      setFotos(res.data.docs || []);
    } catch (error) {
      console.error('Error cargando fotos:', error);
    } finally {
      setLoadingFotos(false);
    }
  };

  const handleImportar = async (codigo) => {
    setImportando(true);
    try {
      const res = await insuramaAPI.importarPresupuesto(codigo);
      toast.success(`Orden ${res.data.numero_orden} creada correctamente`);
      setShowDetalle(false);
      // Navigate to the new order
      if (res.data.orden_id) {
        navigate(`/ordenes/${res.data.orden_id}`);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al importar');
    } finally {
      setImportando(false);
    }
  };

  const handleDescargarFotos = async (codigo) => {
    try {
      toast.info('Descargando fotos...');
      const res = await insuramaAPI.descargarFotos(codigo);
      toast.success(`${res.data.archivos?.length || 0} fotos descargadas`);
    } catch (error) {
      toast.error('Error al descargar fotos');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleBuscar();
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (checkingConfig) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  // Show warning if not configured
  if (!configStatus?.configurado || !configStatus?.conexion_ok) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Shield className="w-6 h-6 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Buscar Siniestro</h1>
            <p className="text-muted-foreground">Consulta presupuestos de Insurama/Sumbroker</p>
          </div>
        </div>

        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="py-8 text-center">
            <AlertCircle className="w-12 h-12 mx-auto text-yellow-600 mb-4" />
            <h3 className="text-lg font-semibold mb-2">Integración no configurada</h3>
            <p className="text-muted-foreground mb-4">
              La integración con Insurama/Sumbroker no está configurada o la conexión falló.
              <br />
              Contacta con un administrador master para configurar las credenciales.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-purple-100 rounded-lg">
          <Shield className="w-6 h-6 text-purple-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Buscar Siniestro</h1>
          <p className="text-muted-foreground">Consulta presupuestos de Insurama/Sumbroker</p>
        </div>
        <Badge variant="outline" className="ml-auto text-green-600 border-green-300">
          <CheckCircle2 className="w-3 h-3 mr-1" />
          Conectado
        </Badge>
      </div>

      {/* Búsqueda */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Search className="w-5 h-5" />
            Buscar por código de siniestro
          </CardTitle>
          <CardDescription>
            Introduce el código del siniestro para ver detalles, datos del cliente, fotos, mensajes y crear una orden de trabajo
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="Ej: 26BE001014"
              value={codigoBusqueda}
              onChange={(e) => setCodigoBusqueda(e.target.value.toUpperCase())}
              onKeyPress={handleKeyPress}
              className="max-w-xs font-mono"
              data-testid="codigo-siniestro-input"
            />
            <Button onClick={handleBuscar} disabled={buscando} data-testid="btn-buscar-siniestro">
              {buscando ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Buscando...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4 mr-2" />
                  Buscar
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Empty state */}
      {!presupuesto && !buscando && (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <Shield className="w-12 h-12 mx-auto text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">
              Introduce un código de siniestro para ver los detalles completos
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Podrás ver datos del cliente, fotos, mensajes, análisis de mercado e importar para crear una orden de trabajo
            </p>
          </CardContent>
        </Card>
      )}

      {/* Modal de Detalle de Presupuesto */}
      <Dialog open={showDetalle} onOpenChange={setShowDetalle}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Detalle del Siniestro: {presupuesto?.codigo_siniestro}
              <Badge 
                variant={presupuesto?.estado === 'Aceptado' ? 'default' : 
                         presupuesto?.estado === 'Cancelado' ? 'destructive' : 'secondary'}
                className="ml-2"
              >
                {presupuesto?.estado}
              </Badge>
            </DialogTitle>
          </DialogHeader>
          
          {presupuesto && (
            <Tabs defaultValue="datos" className="mt-4">
              <TabsList className="grid w-full grid-cols-6">
                <TabsTrigger value="datos">
                  <FileText className="w-3 h-3 mr-1" />
                  Datos
                </TabsTrigger>
                <TabsTrigger value="cliente">
                  <User className="w-3 h-3 mr-1" />
                  Cliente
                </TabsTrigger>
                <TabsTrigger value="mercado" className="text-purple-600">
                  <Users className="w-3 h-3 mr-1" />
                  Mercado
                </TabsTrigger>
                <TabsTrigger value="acciones">
                  <Send className="w-3 h-3 mr-1" />
                  Acciones
                </TabsTrigger>
                <TabsTrigger value="mensajes">
                  <MessageSquare className="w-3 h-3 mr-1" />
                  Mensajes ({observaciones.length})
                </TabsTrigger>
                <TabsTrigger value="fotos">
                  <Image className="w-3 h-3 mr-1" />
                  Fotos ({fotos.length})
                </TabsTrigger>
              </TabsList>
              
              {/* Tab Datos */}
              <TabsContent value="datos" className="mt-4">
                <InsuramaDetalleTab
                  presupuestoDetalle={presupuesto}
                  onDescargarFotos={handleDescargarFotos}
                  onImportar={handleImportar}
                  importando={importando}
                />
              </TabsContent>
              
              {/* Tab Cliente */}
              <TabsContent value="cliente" className="mt-4">
                <InsuramaClienteTab presupuestoDetalle={presupuesto} />
              </TabsContent>
              
              {/* Tab Mercado/Competidores */}
              <TabsContent value="mercado" className="mt-4">
                {loadingCompetidores ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                    <span>Cargando análisis de mercado...</span>
                  </div>
                ) : competidores ? (
                  <div className="space-y-4">
                    {/* Estadísticas */}
                    {competidores.estadisticas && (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <Card className="bg-gradient-to-br from-purple-50 to-purple-100">
                          <CardContent className="p-4">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-xs text-muted-foreground">Participantes</p>
                                <p className="text-2xl font-bold text-purple-700">
                                  {competidores.estadisticas.total_participantes}
                                </p>
                              </div>
                              <Users className="w-8 h-8 text-purple-400" />
                            </div>
                          </CardContent>
                        </Card>
                        
                        <Card className="bg-gradient-to-br from-green-50 to-green-100">
                          <CardContent className="p-4">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-xs text-muted-foreground">Tu posición</p>
                                <p className="text-2xl font-bold text-green-700">
                                  #{competidores.estadisticas.mi_posicion || '-'}
                                  <span className="text-sm font-normal">/{competidores.estadisticas.con_precio}</span>
                                </p>
                              </div>
                              <Trophy className="w-8 h-8 text-green-400" />
                            </div>
                          </CardContent>
                        </Card>
                        
                        <Card className="bg-gradient-to-br from-blue-50 to-blue-100">
                          <CardContent className="p-4">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-xs text-muted-foreground">Precio medio</p>
                                <p className="text-2xl font-bold text-blue-700">
                                  {competidores.estadisticas.precio_medio}€
                                </p>
                              </div>
                              <TrendingUp className="w-8 h-8 text-blue-400" />
                            </div>
                          </CardContent>
                        </Card>
                        
                        <Card className="bg-gradient-to-br from-orange-50 to-orange-100">
                          <CardContent className="p-4">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-xs text-muted-foreground">Rango precios</p>
                                <p className="text-lg font-bold text-orange-700">
                                  {competidores.estadisticas.precio_minimo}€ - {competidores.estadisticas.precio_maximo}€
                                </p>
                              </div>
                              <Euro className="w-8 h-8 text-orange-400" />
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    )}
                    
                    {/* Mi presupuesto destacado */}
                    {competidores.mi_presupuesto && (
                      <Card className="border-2 border-green-500 bg-green-50">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm flex items-center gap-2">
                            <Trophy className="w-4 h-4 text-green-600" />
                            Tu Presupuesto
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="font-semibold">{competidores.mi_presupuesto.tienda_nombre}</p>
                              <p className="text-sm text-muted-foreground">
                                {competidores.mi_presupuesto.tienda_ciudad}
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="text-2xl font-bold text-green-700">{competidores.mi_presupuesto.precio}€</p>
                              <Badge variant={competidores.mi_presupuesto.estado_codigo === 3 ? 'default' : 'secondary'}>
                                {competidores.mi_presupuesto.estado}
                              </Badge>
                            </div>
                          </div>
                          {/* Comentario de mi presupuesto */}
                          {competidores.mi_presupuesto.comentario && (
                            <div className="mt-3 pt-3 border-t border-green-200">
                              <p className="text-sm text-green-800">
                                💬 <span className="font-medium">Tu comentario:</span> {competidores.mi_presupuesto.comentario}
                              </p>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    )}
                    
                    {/* Lista de competidores */}
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-sm">Otros Presupuestos ({competidores.competidores?.length || 0})</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2 max-h-[300px] overflow-y-auto">
                          {competidores.competidores?.map((comp, idx) => (
                            <div 
                              key={comp.id}
                              className={`p-3 rounded-lg border ${
                                comp.estado_codigo === 7 ? 'bg-gray-50 opacity-60' : 'bg-white'
                              }`}
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                  <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-sm font-medium">
                                    {idx + 1}
                                  </div>
                                  <div>
                                    <p className="font-medium text-sm">{comp.tienda_nombre}</p>
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                      <MapPin className="w-3 h-3" />
                                      {comp.tienda_ciudad}
                                      {comp.distancia_km && (
                                        <span className="text-blue-600">({comp.distancia_km} km)</span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                <div className="text-right">
                                  <p className={`font-bold ${comp.precio_num > 0 ? '' : 'text-gray-400'}`}>
                                    {comp.precio_num > 0 ? `${comp.precio}€` : 'Sin precio'}
                                  </p>
                                  <Badge 
                                    variant={comp.estado_codigo === 3 ? 'default' : comp.estado_codigo === 7 ? 'destructive' : 'secondary'}
                                    className="text-xs"
                                  >
                                    {comp.estado}
                                  </Badge>
                                </div>
                              </div>
                              {/* Comentario/Observación del competidor */}
                              {comp.comentario && (
                                <div className="mt-2 pt-2 border-t border-dashed">
                                  <p className="text-xs text-muted-foreground italic">
                                    💬 {comp.comentario}
                                  </p>
                                </div>
                              )}
                            </div>
                          ))}
                          {!competidores.competidores?.length && (
                            <p className="text-center text-muted-foreground py-4">No hay otros presupuestos</p>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    No se pudo cargar la información de mercado
                  </div>
                )}
              </TabsContent>
              
              {/* Tab Acciones */}
              <TabsContent value="acciones" className="mt-4">
                <InsuramaAccionesTab
                  presupuestoDetalle={presupuesto}
                  onActualizarPresupuesto={() => {
                    handleBuscar();
                  }}
                />
              </TabsContent>
              
              {/* Tab Mensajes/Observaciones */}
              <TabsContent value="mensajes" className="mt-4">
                {loadingObservaciones ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                    <span>Cargando mensajes...</span>
                  </div>
                ) : (
                  <InsuramaObservacionesTab
                    observaciones={observaciones}
                    presupuestoDetalle={presupuesto}
                    onEnviarObservacion={async (mensaje) => {
                      try {
                        await insuramaAPI.enviarObservacion(presupuesto.codigo_siniestro, mensaje);
                        toast.success('Mensaje enviado');
                        loadObservaciones(presupuesto.codigo_siniestro);
                      } catch (error) {
                        toast.error('Error al enviar mensaje');
                      }
                    }}
                  />
                )}
              </TabsContent>
              
              {/* Tab Fotos */}
              <TabsContent value="fotos" className="mt-4">
                {loadingFotos ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                    <span>Cargando fotos...</span>
                  </div>
                ) : (
                  <InsuramaFotosTab
                    fotos={fotos}
                    presupuestoDetalle={presupuesto}
                    onDescargarFotos={handleDescargarFotos}
                  />
                )}
              </TabsContent>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

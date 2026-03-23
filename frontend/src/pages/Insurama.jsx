import { useState, useEffect } from 'react';
import { 
  Shield, 
  Settings, 
  RefreshCw, 
  Search, 
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Loader2,
  Send,
  Users,
  TrendingUp,
  MapPin,
  Euro,
  Trophy,
  BarChart3,
  History,
  Lightbulb,
  Upload,
  FileSpreadsheet
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { insuramaAPI, inteligenciaPreciosAPI } from '@/lib/api';
import { toast } from 'sonner';

// Import refactored components
import {
  InsuramaConfigModal,
  InsuramaAccionesTab,
  InsuramaDetalleTab,
  InsuramaClienteTab,
  InsuramaObservacionesTab,
  InsuramaFotosTab,
  InsuramaPresupuestosTable,
  InteligenciaDashboard,
  HistorialMercado,
  RecomendacionPrecios,
  InsuramaIACargaMasiva,
} from '@/components/insurama';

export default function Insurama() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [presupuestos, setPresupuestos] = useState([]);
  const [loadingPresupuestos, setLoadingPresupuestos] = useState(false);
  
  // Pestaña principal activa
  const [mainTab, setMainTab] = useState('dashboard');
  
  // Configuración
  const [showConfig, setShowConfig] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  
  // Búsqueda múltiple
  const [codigosBusqueda, setCodigosBusqueda] = useState('');
  const [buscando, setBuscando] = useState(false);
  const [resultadosBusqueda, setResultadosBusqueda] = useState([]);
  const [codigoSeleccionado, setCodigoSeleccionado] = useState(null);
  
  // Detalle de presupuesto
  const [presupuestoDetalle, setPresupuestoDetalle] = useState(null);
  const [showDetalle, setShowDetalle] = useState(false);
  const [loadingDetalle, setLoadingDetalle] = useState(false);
  
  // Competidores
  const [competidores, setCompetidores] = useState(null);
  const [loadingCompetidores, setLoadingCompetidores] = useState(false);
  
  // Observaciones y fotos
  const [observaciones, setObservaciones] = useState([]);
  const [loadingObservaciones, setLoadingObservaciones] = useState(false);
  const [fotos, setFotos] = useState([]);
  const [loadingFotos, setLoadingFotos] = useState(false);
  
  // Importar y sincronizar
  const [importando, setImportando] = useState(false);
  const [sincronizando, setSincronizando] = useState(false);
  
  // Carga masiva
  const [showCargaMasiva, setShowCargaMasiva] = useState(false);
  const [cargandoMasivo, setCargandoMasivo] = useState(false);
  const [precheckMasivo, setPrecheckMasivo] = useState(false);
  const [archivoMasivo, setArchivoMasivo] = useState(null);
  const [resumenPrecheck, setResumenPrecheck] = useState(null);
  const [resultadosCarga, setResultadosCarga] = useState(null);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await insuramaAPI.obtenerConfig();
      const configData = res.data;
      setConfig(configData);
      // Solo cargar presupuestos si está configurado y la conexión es OK
      if (configData?.configurado && configData?.conexion_ok) {
        fetchPresupuestosDirecto();
      }
    } catch (error) {
      console.error('Error cargando config:', error);
    } finally {
      setLoading(false);
    }
  };

  // Función separada para cargar presupuestos sin verificar config (ya verificado)
  const fetchPresupuestosDirecto = async () => {
    setLoadingPresupuestos(true);
    try {
      const res = await insuramaAPI.listarPresupuestos(15);
      setPresupuestos(res.data.presupuestos || []);
    } catch (error) {
      console.error('Error cargando presupuestos:', error);
      // No mostrar toast para errores de API lenta - es esperado
    } finally {
      setLoadingPresupuestos(false);
    }
  };

  const fetchPresupuestos = async () => {
    if (!config?.configurado) {
      toast.warning('Configura las credenciales de Sumbroker primero');
      return;
    }
    fetchPresupuestosDirecto();
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    try {
      const res = await insuramaAPI.testConexion();
      if (res.data.success) {
        toast.success(`Conexión OK - Usuario: ${res.data.user}`);
        setConfig(prev => ({ ...prev, conexion_ok: true }));
      } else {
        toast.error(`Error: ${res.data.error}`);
        setConfig(prev => ({ ...prev, conexion_ok: false }));
      }
    } catch (error) {
      toast.error('Error al probar conexión');
    } finally {
      setTestingConnection(false);
    }
  };

  const handleBuscarPresupuestos = async (e) => {
    e.preventDefault();
    if (!codigosBusqueda.trim()) {
      toast.error('Introduce al menos un código de siniestro');
      return;
    }
    
    // Parsear códigos (separados por comas, espacios o saltos de línea)
    const codigos = codigosBusqueda
      .split(/[\s,\n]+/)
      .map(c => c.trim().toUpperCase())
      .filter(c => c.length > 0)
      .slice(0, 10); // Máximo 10
    
    if (codigos.length === 0) {
      toast.error('No se encontraron códigos válidos');
      return;
    }
    
    setBuscando(true);
    setResultadosBusqueda([]);
    setCodigoSeleccionado(null);
    
    // Inicializar resultados con estado "loading"
    const resultadosIniciales = codigos.map(codigo => ({
      codigo,
      status: 'loading',
      presupuesto: null,
      competidores: null,
      error: null
    }));
    setResultadosBusqueda(resultadosIniciales);
    
    // Buscar cada código de forma secuencial para evitar timeouts
    let encontrados = 0;
    let noEncontrados = 0;
    
    for (let i = 0; i < codigos.length; i++) {
      const codigo = codigos[i];
      
      try {
        // Obtener datos del presupuesto
        const resPresupuesto = await insuramaAPI.obtenerPresupuesto(codigo);
        
        // Obtener competidores
        let competidoresData = null;
        try {
          const resCompetidores = await insuramaAPI.obtenerCompetidores(codigo);
          competidoresData = resCompetidores.data;
        } catch (compError) {
          console.warn(`No se pudieron obtener competidores para ${codigo}`);
        }
        
        // Actualizar el resultado de este código
        setResultadosBusqueda(prev => {
          const updated = [...prev];
          updated[i] = {
            codigo,
            status: 'success',
            presupuesto: resPresupuesto.data,
            competidores: competidoresData,
            error: null
          };
          return updated;
        });
        
        encontrados++;
        
        // Auto-seleccionar el primero que se encuentre
        if (encontrados === 1) {
          setCodigoSeleccionado(codigo);
        }
        
      } catch (error) {
        const isNotFound = error.response?.status === 404;
        
        setResultadosBusqueda(prev => {
          const updated = [...prev];
          updated[i] = {
            codigo,
            status: isNotFound ? 'not_found' : 'error',
            presupuesto: null,
            competidores: null,
            error: error.response?.data?.detail || error.message
          };
          return updated;
        });
        
        if (isNotFound) {
          noEncontrados++;
        }
      }
    }
    
    setBuscando(false);
    toast.success(`Búsqueda completada: ${encontrados} encontrados, ${noEncontrados} no encontrados`);
  };

  const getResultadoSeleccionado = () => {
    return resultadosBusqueda.find(r => r.codigo === codigoSeleccionado);
  };

  const handleVerDetalle = async (codigo) => {
    setLoadingDetalle(true);
    setShowDetalle(true);
    try {
      const res = await insuramaAPI.obtenerPresupuesto(codigo);
      setPresupuestoDetalle(res.data);
      loadObservaciones(codigo);
      loadFotos(codigo);
      loadCompetidores(codigo);
    } catch (error) {
      toast.error('Error al cargar detalle');
      setShowDetalle(false);
    } finally {
      setLoadingDetalle(false);
    }
  };

  const loadCompetidores = async (codigo) => {
    setLoadingCompetidores(true);
    try {
      const res = await insuramaAPI.obtenerCompetidores(codigo);
      setCompetidores(res.data);
    } catch (error) {
      console.error('Error cargando competidores:', error);
      setCompetidores(null);
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
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al importar');
    } finally {
      setImportando(false);
    }
  };

  const handleDescargarFotos = async (codigo) => {
    try {
      const res = await insuramaAPI.descargarFotos(codigo);
      toast.success(`${res.data.archivos?.length || 0} fotos descargadas`);
    } catch (error) {
      toast.error('Error al descargar fotos');
    }
  };

  const handleSincronizar = async () => {
    setSincronizando(true);
    try {
      const res = await insuramaAPI.sincronizar();
      toast.success(`${res.data.ordenes_actualizadas} órdenes sincronizadas`);
      if (res.data.errores?.length > 0) {
        toast.warning(`${res.data.errores.length} errores durante la sincronización`);
      }
    } catch (error) {
      toast.error('Error al sincronizar');
    } finally {
      setSincronizando(false);
    }
  };

  const handlePrecheckCargaMasiva = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!config?.configurado) {
      toast.error('Primero debes configurar las credenciales de Sumbroker');
      e.target.value = '';
      return;
    }

    setPrecheckMasivo(true);
    setResultadosCarga(null);
    setResumenPrecheck(null);
    setArchivoMasivo(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await insuramaAPI.precheckCargaMasiva(formData);
      setResumenPrecheck(res.data);
      setArchivoMasivo(file);

      const listos = res.data?.resumen?.listos_para_procesar || 0;
      const invalidos = (res.data?.resumen?.vacios || 0) + (res.data?.resumen?.duplicados || 0) + (res.data?.resumen?.formato_invalido || 0);

      if (listos > 0) {
        toast.success(`Pre-check completado: ${listos} códigos listos para procesar`);
      } else {
        toast.warning('Pre-check completado: no hay códigos válidos para procesar');
      }

      if (invalidos > 0) {
        toast.warning(`Se detectaron ${invalidos} filas con incidencias en el archivo`);
      }
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(detail || 'Error al ejecutar pre-check del archivo');
    } finally {
      setPrecheckMasivo(false);
      e.target.value = '';
    }
  };

  const handleConfirmarCargaMasiva = async () => {
    if (!archivoMasivo) {
      toast.error('Selecciona un archivo y ejecuta el pre-check primero');
      return;
    }

    setCargandoMasivo(true);
    setResultadosCarga(null);

    try {
      const formData = new FormData();
      formData.append('file', archivoMasivo);

      const res = await insuramaAPI.cargaMasiva(formData);
      setResultadosCarga(res.data);

      if (res.data.creados > 0 || res.data.actualizados > 0) {
        toast.success(`${res.data.creados} órdenes creadas, ${res.data.actualizados} actualizadas`);
      }
      if (res.data.errores > 0) {
        toast.warning(`${res.data.errores} siniestros con errores`);
      }
      if (res.data.total_procesados === 0) {
        toast.info('No se encontraron códigos de siniestro válidos en el archivo');
      }

      setArchivoMasivo(null);
      setResumenPrecheck(null);
    } catch (error) {
      console.error('Error carga masiva:', error);
      const detail = error.response?.data?.detail;
      if (detail?.includes('columna')) {
        toast.error(detail);
      } else if (detail?.includes('Sumbroker') || detail?.includes('conexión')) {
        toast.error('Error de conexión con Sumbroker. Verifica las credenciales.');
      } else {
        toast.error(detail || 'Error procesando el archivo');
      }
    } finally {
      setCargandoMasivo(false);
    }
  };

  const handleCancelarPrecheck = () => {
    setArchivoMasivo(null);
    setResumenPrecheck(null);
  };

  const handleConfigSaved = (newConfig) => {
    setConfig(newConfig);
    fetchPresupuestos();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="insurama-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-600" />
            Insurama / Sumbroker
          </h1>
          <p className="text-muted-foreground mt-1">
            Gestión de presupuestos y siniestros del portal de seguros
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button 
            variant="outline" 
            onClick={() => setShowConfig(true)}
            data-testid="config-btn"
          >
            <Settings className="w-4 h-4 mr-2" />
            Configuración
          </Button>
          {config?.configurado && (
            <>
              {/* Botón de Carga Masiva */}
              <label className="cursor-pointer">
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handlePrecheckCargaMasiva}
                  className="hidden"
                  disabled={precheckMasivo || cargandoMasivo}
                  data-testid="insurama-carga-masiva-file-input"
                />
                <Button 
                  variant="outline" 
                  className="bg-green-50 border-green-200 hover:bg-green-100 text-green-700"
                  disabled={precheckMasivo || cargandoMasivo}
                  asChild
                  data-testid="insurama-carga-masiva-precheck-button"
                >
                  <span>
                    {precheckMasivo ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <FileSpreadsheet className="w-4 h-4 mr-2" />
                    )}
                    Pre-check Carga Masiva
                  </span>
                </Button>
              </label>
              <Button 
                variant="outline"
                onClick={handleSincronizar}
                disabled={sincronizando}
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${sincronizando ? 'animate-spin' : ''}`} />
                Sincronizar
              </Button>
              <Button onClick={fetchPresupuestos} disabled={loadingPresupuestos}>
                <RefreshCw className={`w-4 h-4 mr-2 ${loadingPresupuestos ? 'animate-spin' : ''}`} />
                Actualizar
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Estado de conexión */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {config?.conexion_ok ? (
                <CheckCircle2 className="w-6 h-6 text-green-500" />
              ) : config?.configurado ? (
                <AlertTriangle className="w-6 h-6 text-amber-500" />
              ) : (
                <XCircle className="w-6 h-6 text-red-500" />
              )}
              <div>
                <p className="font-medium">
                  {config?.conexion_ok 
                    ? 'Conectado a Sumbroker' 
                    : config?.configurado 
                      ? 'Error de conexión' 
                      : 'No configurado'}
                </p>
                {config?.login && (
                  <p className="text-sm text-muted-foreground">Usuario: {config.login}</p>
                )}
              </div>
            </div>
            <Button 
              variant="ghost" 
              size="sm"
              onClick={handleTestConnection}
              disabled={!config?.configurado || testingConnection}
            >
              {testingConnection ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Probar conexión'}
            </Button>
          </div>
        </CardContent>
      </Card>


      {/* Pre-check de Carga Masiva */}
      {resumenPrecheck && (
        <Card className="border-amber-200 bg-amber-50/50" data-testid="insurama-carga-masiva-precheck-card">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileSpreadsheet className="w-5 h-5 text-amber-600" />
                  Pre-check de Carga Masiva
                </CardTitle>
                <CardDescription data-testid="insurama-carga-masiva-precheck-file-name">
                  Archivo: {resumenPrecheck.archivo}
                </CardDescription>
              </div>
              <Badge variant="secondary" data-testid="insurama-carga-masiva-precheck-column">
                Columna: {resumenPrecheck.columna_codigo}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              <div className="text-center p-3 bg-white rounded-lg border">
                <p className="text-xl font-bold text-slate-700" data-testid="precheck-total-filas">{resumenPrecheck.resumen?.total_filas || 0}</p>
                <p className="text-xs text-muted-foreground">Filas</p>
              </div>
              <div className="text-center p-3 bg-white rounded-lg border border-green-200">
                <p className="text-xl font-bold text-green-600" data-testid="precheck-listos">{resumenPrecheck.resumen?.listos_para_procesar || 0}</p>
                <p className="text-xs text-muted-foreground">Listos</p>
              </div>
              <div className="text-center p-3 bg-white rounded-lg border border-blue-200">
                <p className="text-xl font-bold text-blue-600" data-testid="precheck-existentes">{resumenPrecheck.resumen?.existentes_en_crm || 0}</p>
                <p className="text-xs text-muted-foreground">Ya en CRM</p>
              </div>
              <div className="text-center p-3 bg-white rounded-lg border border-emerald-200">
                <p className="text-xl font-bold text-emerald-600" data-testid="precheck-nuevos">{resumenPrecheck.resumen?.nuevos_estimados || 0}</p>
                <p className="text-xs text-muted-foreground">Nuevos</p>
              </div>
              <div className="text-center p-3 bg-white rounded-lg border border-red-200">
                <p className="text-xl font-bold text-red-600" data-testid="precheck-duplicados">{resumenPrecheck.resumen?.duplicados || 0}</p>
                <p className="text-xs text-muted-foreground">Duplicados</p>
              </div>
              <div className="text-center p-3 bg-white rounded-lg border border-orange-200">
                <p className="text-xl font-bold text-orange-600" data-testid="precheck-invalidos">{(resumenPrecheck.resumen?.vacios || 0) + (resumenPrecheck.resumen?.formato_invalido || 0)}</p>
                <p className="text-xs text-muted-foreground">Vacíos/Inválidos</p>
              </div>
            </div>

            {resumenPrecheck.detalles?.length > 0 && (
              <div className="max-h-56 overflow-y-auto space-y-1 text-sm" data-testid="insurama-carga-masiva-precheck-details">
                {resumenPrecheck.detalles.slice(0, 120).map((detalle, idx) => (
                  <div
                    key={`${detalle.fila}-${idx}`}
                    className={`flex items-center gap-2 p-2 rounded ${
                      detalle.status === 'nuevo' ? 'bg-green-100' :
                      detalle.status === 'existente' ? 'bg-blue-100' :
                      'bg-red-100'
                    }`}
                  >
                    <span className="text-xs font-mono">F{detalle.fila}</span>
                    <span className="font-mono text-xs">{detalle.codigo || '-'}</span>
                    <span className="text-muted-foreground">-</span>
                    <span className="truncate">{detalle.mensaje}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="flex flex-wrap gap-2 justify-end">
              <Button
                variant="outline"
                onClick={handleCancelarPrecheck}
                disabled={cargandoMasivo}
                data-testid="insurama-carga-masiva-cancel-precheck"
              >
                Cancelar
              </Button>
              <Button
                onClick={handleConfirmarCargaMasiva}
                disabled={cargandoMasivo || (resumenPrecheck.resumen?.listos_para_procesar || 0) === 0}
                data-testid="insurama-carga-masiva-confirm-execute"
              >
                {cargandoMasivo ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Upload className="w-4 h-4 mr-2" />}
                Confirmar y ejecutar carga
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Resultados de Carga Masiva */}
      {resultadosCarga && (
        <Card className="border-green-200 bg-green-50/50">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-green-600" />
                Resultado de Carga Masiva
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={() => setResultadosCarga(null)}>
                <XCircle className="w-4 h-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-4 mb-4">
              <div className="text-center p-3 bg-white rounded-lg border">
                <p className="text-2xl font-bold text-slate-700">{resultadosCarga.total_procesados}</p>
                <p className="text-xs text-muted-foreground">Total procesados</p>
              </div>
              <div className="text-center p-3 bg-white rounded-lg border border-green-200">
                <p className="text-2xl font-bold text-green-600">{resultadosCarga.creados}</p>
                <p className="text-xs text-muted-foreground">Creados</p>
              </div>
              <div className="text-center p-3 bg-white rounded-lg border border-blue-200">
                <p className="text-2xl font-bold text-blue-600">{resultadosCarga.actualizados}</p>
                <p className="text-xs text-muted-foreground">Actualizados</p>
              </div>
              <div className="text-center p-3 bg-white rounded-lg border border-red-200">
                <p className="text-2xl font-bold text-red-600">{resultadosCarga.errores}</p>
                <p className="text-xs text-muted-foreground">Errores</p>
              </div>
            </div>
            
            {resultadosCarga.detalles?.length > 0 && (
              <div className="max-h-48 overflow-y-auto space-y-1 text-sm">
                {resultadosCarga.detalles.map((d, i) => (
                  <div key={i} className={`flex items-center gap-2 p-2 rounded ${
                    d.status === 'creado' ? 'bg-green-100' : 
                    d.status === 'actualizado' ? 'bg-blue-100' : 'bg-red-100'
                  }`}>
                    {d.status === 'creado' ? <CheckCircle2 className="w-4 h-4 text-green-600" /> :
                     d.status === 'actualizado' ? <RefreshCw className="w-4 h-4 text-blue-600" /> :
                     <XCircle className="w-4 h-4 text-red-600" />}
                    <span className="font-mono">{d.codigo}</span>
                    <span className="text-muted-foreground">-</span>
                    <span className="truncate">{d.mensaje}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tabs principales de navegación */}
      <Tabs value={mainTab} onValueChange={setMainTab} className="w-full">
        <TabsList className="grid w-full grid-cols-5 mb-6">
          <TabsTrigger value="dashboard" className="flex items-center gap-2" data-testid="tab-dashboard">
            <BarChart3 className="w-4 h-4" />
            <span className="hidden sm:inline">Dashboard</span>
          </TabsTrigger>
          <TabsTrigger value="buscar" className="flex items-center gap-2" data-testid="tab-buscar">
            <Search className="w-4 h-4" />
            <span className="hidden sm:inline">Buscar</span>
          </TabsTrigger>
          <TabsTrigger value="ia-carga" className="flex items-center gap-2 text-purple-600" data-testid="tab-ia-carga">
            <Lightbulb className="w-4 h-4" />
            <span className="hidden sm:inline">Carga IA</span>
          </TabsTrigger>
          <TabsTrigger value="historial" className="flex items-center gap-2" data-testid="tab-historial">
            <History className="w-4 h-4" />
            <span className="hidden sm:inline">Historial</span>
          </TabsTrigger>
          <TabsTrigger value="presupuestos" className="flex items-center gap-2" data-testid="tab-presupuestos">
            <FileText className="w-4 h-4" />
            <span className="hidden sm:inline">Presupuestos</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab: Dashboard de Inteligencia */}
        <TabsContent value="dashboard">
          <InteligenciaDashboard />
        </TabsContent>

        {/* Tab: Carga Masiva con IA */}
        <TabsContent value="ia-carga">
          <InsuramaIACargaMasiva />
        </TabsContent>

        {/* Tab: Buscar Siniestros (Múltiple) */}
        <TabsContent value="buscar">
          <div className="space-y-4">
            {/* Búsqueda múltiple */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Search className="w-5 h-5" />
                  Búsqueda Múltiple de Siniestros
                </CardTitle>
                <CardDescription>
                  Introduce hasta 10 códigos de siniestro (separados por comas, espacios o líneas).
                  Los datos de mercado se cargarán automáticamente para todos.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleBuscarPresupuestos} className="flex gap-2">
                  <Input
                    placeholder="Ej: 26BE000826, 26BE000827, 26BE000830"
                    value={codigosBusqueda}
                    onChange={(e) => setCodigosBusqueda(e.target.value.toUpperCase())}
                    className="font-mono flex-1"
                    data-testid="codigos-busqueda-input"
                  />
                  <Button type="submit" disabled={buscando || !config?.conexion_ok}>
                    {buscando ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Search className="w-4 h-4 mr-2" />}
                    {buscando ? 'Buscando...' : 'Buscar Todos'}
                  </Button>
                </form>
                {codigosBusqueda && (
                  <p className="text-xs text-muted-foreground mt-2">
                    {codigosBusqueda.split(/[\s,\n]+/).filter(c => c.trim()).length} código(s) detectado(s)
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Resultados con lista lateral */}
            {resultadosBusqueda.length > 0 && (
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                {/* Lista lateral de códigos */}
                <Card className="lg:col-span-1">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <FileText className="w-4 h-4" />
                      Resultados ({resultadosBusqueda.filter(r => r.status !== 'loading').length}/{resultadosBusqueda.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-2">
                    <div className="space-y-1 max-h-[500px] overflow-y-auto">
                      {resultadosBusqueda.map((resultado) => (
                        <button
                          key={resultado.codigo}
                          onClick={() => resultado.status !== 'loading' && setCodigoSeleccionado(resultado.codigo)}
                          disabled={resultado.status === 'loading'}
                          className={`w-full text-left p-3 rounded-lg border transition-all ${
                            resultado.status === 'loading'
                              ? 'bg-gray-50 border-gray-200 cursor-wait'
                              : codigoSeleccionado === resultado.codigo
                                ? 'bg-blue-50 border-blue-300 shadow-sm'
                                : 'bg-white border-gray-100 hover:bg-gray-50'
                          }`}
                          data-testid={`resultado-${resultado.codigo}`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-sm font-medium">{resultado.codigo}</span>
                            {resultado.status === 'loading' ? (
                              <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                            ) : resultado.status === 'success' ? (
                              <CheckCircle2 className="w-4 h-4 text-green-500" />
                            ) : resultado.status === 'not_found' ? (
                              <XCircle className="w-4 h-4 text-gray-400" />
                            ) : (
                              <AlertTriangle className="w-4 h-4 text-red-500" />
                            )}
                          </div>
                          {resultado.status === 'loading' && (
                            <p className="text-xs text-blue-500 mt-1">Buscando...</p>
                          )}
                          {resultado.status === 'success' && resultado.presupuesto && (
                            <div className="mt-1 text-xs text-muted-foreground truncate">
                              {resultado.presupuesto.device_brand} {resultado.presupuesto.device_model}
                            </div>
                          )}
                          {resultado.competidores?.estadisticas && (
                            <div className="mt-1 flex items-center gap-2 text-xs">
                              <Badge variant="outline" className="text-[10px] py-0">
                                <Users className="w-3 h-3 mr-1" />
                                {resultado.competidores.estadisticas.total_participantes}
                              </Badge>
                              {resultado.competidores.estadisticas.mi_posicion && (
                                <Badge variant="secondary" className="text-[10px] py-0">
                                  #{resultado.competidores.estadisticas.mi_posicion}
                                </Badge>
                              )}
                            </div>
                          )}
                          {resultado.status === 'not_found' && (
                            <p className="text-xs text-gray-400 mt-1">No encontrado</p>
                          )}
                          {resultado.status === 'error' && (
                            <p className="text-xs text-red-400 mt-1 truncate">{resultado.error}</p>
                          )}
                        </button>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Panel de detalle del código seleccionado */}
                <div className="lg:col-span-3 space-y-4">
                  {codigoSeleccionado && getResultadoSeleccionado()?.status === 'success' ? (
                    <>
                      {/* Info del dispositivo */}
                      <Card>
                        <CardHeader className="pb-2">
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-lg flex items-center gap-2">
                              <span className="font-mono">{codigoSeleccionado}</span>
                              <Badge variant="outline">
                                {getResultadoSeleccionado()?.presupuesto?.status_text}
                              </Badge>
                            </CardTitle>
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => {
                                const res = getResultadoSeleccionado();
                                if (res?.presupuesto) {
                                  setPresupuestoDetalle(res.presupuesto);
                                  setCompetidores(res.competidores);
                                  setShowDetalle(true);
                                }
                              }}
                            >
                              Ver detalle completo
                            </Button>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                            <div>
                              <p className="text-xs text-muted-foreground">Dispositivo</p>
                              <p className="font-medium">
                                {getResultadoSeleccionado()?.presupuesto?.device_brand} {getResultadoSeleccionado()?.presupuesto?.device_model}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground">Cliente</p>
                              <p className="font-medium truncate">
                                {getResultadoSeleccionado()?.presupuesto?.client_full_name || 'N/A'}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground">Daño</p>
                              <p className="font-medium truncate">
                                {getResultadoSeleccionado()?.presupuesto?.damage_type_text || 'N/A'}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground">Mi precio</p>
                              <p className="font-bold text-lg text-green-600">
                                {getResultadoSeleccionado()?.presupuesto?.price || 0}€
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground">Máx. Siniestro</p>
                              {getResultadoSeleccionado()?.presupuesto?.reserve_value ? (
                                <p className="font-bold text-lg text-blue-600">
                                  {parseFloat(getResultadoSeleccionado()?.presupuesto?.reserve_value).toFixed(2)}€
                                </p>
                              ) : (
                                <p className="text-muted-foreground">-</p>
                              )}
                            </div>
                          </div>
                          {/* Extra info row */}
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3 pt-3 border-t">
                            {getResultadoSeleccionado()?.presupuesto?.product_name && (
                              <div>
                                <p className="text-xs text-muted-foreground">Producto/Seguro</p>
                                <p className="text-sm">{getResultadoSeleccionado()?.presupuesto?.product_name}</p>
                              </div>
                            )}
                            {getResultadoSeleccionado()?.presupuesto?.internal_status_text && (
                              <div>
                                <p className="text-xs text-muted-foreground">Estado interno</p>
                                <Badge variant="outline" className="text-xs">{getResultadoSeleccionado()?.presupuesto?.internal_status_text}</Badge>
                              </div>
                            )}
                            {getResultadoSeleccionado()?.presupuesto?.repair_time_text && (
                              <div>
                                <p className="text-xs text-muted-foreground">Tiempo reparación</p>
                                <p className="text-sm">{getResultadoSeleccionado()?.presupuesto?.repair_time_text}</p>
                              </div>
                            )}
                            {getResultadoSeleccionado()?.presupuesto?.device_purchase_price && (
                              <div>
                                <p className="text-xs text-muted-foreground">Precio compra dispositivo</p>
                                <p className="text-sm font-medium">{getResultadoSeleccionado()?.presupuesto?.device_purchase_price}€</p>
                              </div>
                            )}
                          </div>
                        </CardContent>
                      </Card>

                      {/* Estadísticas de mercado */}
                      {getResultadoSeleccionado()?.competidores?.estadisticas && (
                        <Card className="bg-gradient-to-r from-purple-50 to-blue-50">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm flex items-center gap-2">
                              <BarChart3 className="w-4 h-4 text-purple-600" />
                              Análisis de Mercado
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                              <div className="text-center p-3 bg-white rounded-lg border">
                                <p className="text-2xl font-bold text-purple-700">
                                  {getResultadoSeleccionado()?.competidores?.estadisticas?.total_participantes || 0}
                                </p>
                                <p className="text-xs text-muted-foreground">Participantes</p>
                              </div>
                              <div className="text-center p-3 bg-white rounded-lg border border-green-200">
                                <p className="text-2xl font-bold text-green-700">
                                  #{getResultadoSeleccionado()?.competidores?.estadisticas?.mi_posicion || '-'}
                                </p>
                                <p className="text-xs text-muted-foreground">Tu posición</p>
                              </div>
                              <div className="text-center p-3 bg-white rounded-lg border">
                                <p className="text-2xl font-bold text-blue-700">
                                  {getResultadoSeleccionado()?.competidores?.estadisticas?.precio_medio || 0}€
                                </p>
                                <p className="text-xs text-muted-foreground">Precio medio</p>
                              </div>
                              <div className="text-center p-3 bg-white rounded-lg border">
                                <p className="text-lg font-bold text-slate-700">
                                  {getResultadoSeleccionado()?.competidores?.estadisticas?.precio_minimo || 0}€
                                </p>
                                <p className="text-xs text-muted-foreground">Mínimo</p>
                              </div>
                              <div className="text-center p-3 bg-white rounded-lg border">
                                <p className="text-lg font-bold text-slate-700">
                                  {getResultadoSeleccionado()?.competidores?.estadisticas?.precio_maximo || 0}€
                                </p>
                                <p className="text-xs text-muted-foreground">Máximo</p>
                              </div>
                              {getResultadoSeleccionado()?.presupuesto?.reserve_value && (
                                <div className="text-center p-3 bg-white rounded-lg border border-blue-300">
                                  <p className="text-lg font-bold text-blue-700">
                                    {parseFloat(getResultadoSeleccionado()?.presupuesto?.reserve_value).toFixed(0)}€
                                  </p>
                                  <p className="text-xs text-muted-foreground">Máx. Siniestro</p>
                                </div>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      )}

                      {/* Lista de competidores */}
                      {getResultadoSeleccionado()?.competidores?.competidores?.length > 0 && (
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm flex items-center gap-2">
                              <Users className="w-4 h-4" />
                              Competidores ({getResultadoSeleccionado()?.competidores?.competidores?.length})
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-2 max-h-[300px] overflow-y-auto">
                              {getResultadoSeleccionado()?.competidores?.competidores?.map((comp, idx) => {
                                const miPrecio = parseFloat(getResultadoSeleccionado()?.competidores?.mi_presupuesto?.precio || 0);
                                const compPrecio = comp.precio_num || 0;
                                const diff = miPrecio > 0 && compPrecio > 0 ? compPrecio - miPrecio : null;
                                return (
                                <div 
                                  key={comp.id}
                                  className={`flex items-center justify-between p-3 rounded-lg border ${
                                    comp.estado_codigo === 3 ? 'bg-yellow-50 border-yellow-300' :
                                    comp.estado_codigo === 7 ? 'bg-gray-50 opacity-60' : 'bg-white'
                                  }`}
                                >
                                  <div className="flex items-center gap-3">
                                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                                      comp.estado_codigo === 3 ? 'bg-yellow-400 text-white' : 'bg-slate-200'
                                    }`}>
                                      {idx + 1}
                                    </div>
                                    <div>
                                      <div className="flex items-center gap-2">
                                        <p className="font-medium text-sm">{comp.tienda_nombre}</p>
                                        {comp.estado_codigo === 3 && (
                                          <Badge variant="destructive" className="text-[9px] px-1">GANADOR</Badge>
                                        )}
                                      </div>
                                      <p className="text-xs text-muted-foreground">{comp.tienda_ciudad}</p>
                                    </div>
                                  </div>
                                  <div className="text-right flex items-center gap-3">
                                    {diff !== null && (
                                      <Badge className={`text-[10px] ${diff < 0 ? 'bg-red-100 text-red-700' : diff > 0 ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                                        {diff > 0 ? '+' : ''}{diff.toFixed(0)}€
                                      </Badge>
                                    )}
                                    <div>
                                      <p className={`font-bold ${comp.precio_num > 0 ? 'text-slate-900' : 'text-gray-400'}`}>
                                        {comp.precio_num > 0 ? `${comp.precio}€` : 'Sin precio'}
                                      </p>
                                      <Badge 
                                        variant={comp.estado_codigo === 3 ? 'default' : comp.estado_codigo === 7 ? 'destructive' : 'secondary'}
                                        className="text-[10px]"
                                      >
                                        {comp.estado}
                                      </Badge>
                                    </div>
                                  </div>
                                </div>
                                );
                              })}
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </>
                  ) : codigoSeleccionado ? (
                    <Card>
                      <CardContent className="py-12 text-center">
                        <XCircle className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                        <p className="text-gray-500">
                          {getResultadoSeleccionado()?.status === 'not_found' 
                            ? 'Este código no se encontró en Sumbroker'
                            : `Error: ${getResultadoSeleccionado()?.error || 'Error desconocido'}`
                          }
                        </p>
                      </CardContent>
                    </Card>
                  ) : (
                    <Card>
                      <CardContent className="py-12 text-center">
                        <Search className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                        <p className="text-gray-500">Selecciona un código de la lista para ver sus detalles</p>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </div>
            )}

            {/* Estado inicial sin búsqueda */}
            {resultadosBusqueda.length === 0 && !buscando && (
              <Card>
                <CardContent className="py-12 text-center">
                  <Search className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                  <p className="text-gray-500 mb-2">Introduce códigos de siniestro para buscar</p>
                  <p className="text-xs text-muted-foreground">
                    Puedes buscar hasta 10 códigos a la vez. Los datos de mercado se cargarán automáticamente.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Tab: Historial de Mercado */}
        <TabsContent value="historial">
          <HistorialMercado />
        </TabsContent>

        {/* Tab: Lista de Presupuestos */}
        <TabsContent value="presupuestos">
          {config?.conexion_ok ? (
            <InsuramaPresupuestosTable 
              presupuestos={presupuestos}
              loading={loadingPresupuestos}
              onVerDetalle={handleVerDetalle}
            />
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <Shield className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-500">Configura la conexión con Sumbroker para ver los presupuestos</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Modal de Configuración */}
      <InsuramaConfigModal
        open={showConfig}
        onOpenChange={setShowConfig}
        onConfigSaved={handleConfigSaved}
      />

      {/* Modal de Detalle de Presupuesto */}
      <Dialog open={showDetalle} onOpenChange={setShowDetalle}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Detalle del Siniestro
            </DialogTitle>
          </DialogHeader>
          
          {loadingDetalle ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin" />
            </div>
          ) : presupuestoDetalle && (
            <Tabs defaultValue="datos" className="mt-4">
              <TabsList className="grid w-full grid-cols-6">
                <TabsTrigger value="datos">Datos</TabsTrigger>
                <TabsTrigger value="cliente">Cliente</TabsTrigger>
                <TabsTrigger value="competidores" className="text-purple-600">
                  <Users className="w-3 h-3 mr-1" />
                  Mercado
                </TabsTrigger>
                <TabsTrigger value="acciones">
                  <Send className="w-3 h-3 mr-1" />
                  Acciones
                </TabsTrigger>
                <TabsTrigger value="observaciones">
                  Mensajes ({observaciones.length})
                </TabsTrigger>
                <TabsTrigger value="fotos">
                  Fotos ({fotos.length})
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="datos" className="mt-4">
                <InsuramaDetalleTab
                  presupuestoDetalle={presupuestoDetalle}
                  onDescargarFotos={handleDescargarFotos}
                  onImportar={handleImportar}
                  importando={importando}
                />
              </TabsContent>
              
              <TabsContent value="cliente" className="mt-4">
                <InsuramaClienteTab presupuestoDetalle={presupuestoDetalle} />
              </TabsContent>
              
              <TabsContent value="competidores" className="mt-4">
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
                          {competidores.competidores?.map((comp, idx) => {
                            const miPrecio = parseFloat(competidores.mi_presupuesto?.precio || 0);
                            const compPrecio = comp.precio_num || 0;
                            const diff = miPrecio > 0 && compPrecio > 0 ? compPrecio - miPrecio : null;
                            return (
                            <div 
                              key={comp.id}
                              className={`p-3 rounded-lg border ${
                                comp.estado_codigo === 3 ? 'bg-yellow-50 border-yellow-300' :
                                comp.estado_codigo === 7 ? 'bg-gray-50 opacity-60' : 'bg-white'
                              }`}
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                                    comp.estado_codigo === 3 ? 'bg-yellow-400 text-white' : 'bg-slate-200'
                                  }`}>
                                    {idx + 1}
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <p className="font-medium text-sm">{comp.tienda_nombre}</p>
                                      {comp.estado_codigo === 3 && (
                                        <Badge variant="destructive" className="text-[9px] px-1">GANADOR</Badge>
                                      )}
                                    </div>
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                      <MapPin className="w-3 h-3" />
                                      {comp.tienda_ciudad}{comp.tienda_provincia ? `, ${comp.tienda_provincia}` : ''}
                                      {comp.distancia_km && (
                                        <span className="text-blue-600">({comp.distancia_km} km)</span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                <div className="text-right flex items-center gap-3">
                                  {diff !== null && (
                                    <Badge className={`text-[10px] ${diff < 0 ? 'bg-red-100 text-red-700' : diff > 0 ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                                      {diff > 0 ? '+' : ''}{diff.toFixed(0)}€
                                    </Badge>
                                  )}
                                  <div>
                                    <p className={`font-bold ${comp.precio_num > 0 ? 'text-slate-900' : 'text-gray-400'}`}>
                                      {comp.precio_num > 0 ? `${comp.precio}€` : 'Sin precio'}
                                    </p>
                                    <Badge 
                                      variant={
                                        comp.estado_codigo === 3 ? 'default' : 
                                        comp.estado_codigo === 7 ? 'destructive' : 
                                        'secondary'
                                      }
                                      className="text-[10px]"
                                    >
                                      {comp.estado}
                                    </Badge>
                                  </div>
                                </div>
                              </div>
                              {/* Comentario/Observación del competidor */}
                              {comp.comentario && (
                                <div className="mt-2 pt-2 border-t border-dashed">
                                  <p className="text-xs text-muted-foreground italic">
                                    <span className="font-medium">Comentario:</span> {comp.comentario}
                                  </p>
                                </div>
                              )}
                            </div>
                            );
                          })}
                          
                          {(!competidores.competidores || competidores.competidores.length === 0) && (
                            <p className="text-center text-muted-foreground py-4">
                              No hay otros presupuestos para este siniestro
                            </p>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    No se pudo cargar la información de competidores
                  </div>
                )}
              </TabsContent>
              
              <TabsContent value="acciones" className="mt-4">
                <InsuramaAccionesTab presupuestoDetalle={presupuestoDetalle} />
              </TabsContent>
              
              <TabsContent value="observaciones" className="mt-4">
                <InsuramaObservacionesTab 
                  observaciones={observaciones} 
                  loading={loadingObservaciones} 
                />
              </TabsContent>
              
              <TabsContent value="fotos" className="mt-4">
                <InsuramaFotosTab 
                  fotos={fotos} 
                  loading={loadingFotos} 
                />
              </TabsContent>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

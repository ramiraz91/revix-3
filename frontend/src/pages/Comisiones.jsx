import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  DollarSign, Settings, Save, Users, TrendingUp, Clock, CheckCircle, 
  AlertCircle, RefreshCw, Percent, Calculator, Calendar, Download, Filter
} from 'lucide-react';
import { comisionesAPI, usuariosAPI } from '@/lib/api';
import { toast } from 'sonner';

export default function Comisiones() {
  const [config, setConfig] = useState({
    sistema_activo: false,
    porcentaje_default: 5.0,
    fijo_default: 0.0,
    aplicar_a_garantias: false,
    aplicar_a_seguros: true,
    aplicar_a_particulares: true
  });
  const [comisiones, setComisiones] = useState([]);
  const [resumen, setResumen] = useState([]);
  const [tecnicos, setTecnicos] = useState([]);
  const [totales, setTotales] = useState({ pendiente: 0, aprobadas: 0, pagadas: 0 });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [filtros, setFiltros] = useState({
    tecnico_id: '',
    estado: '',
    periodo: new Date().toISOString().slice(0, 7) // YYYY-MM
  });
  const [activeTab, setActiveTab] = useState('config');

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (activeTab === 'listado') {
      fetchComisiones();
    } else if (activeTab === 'resumen') {
      fetchResumen();
    }
  }, [activeTab, filtros]);

  const fetchData = async () => {
    try {
      const [configRes, tecnicosRes] = await Promise.all([
        comisionesAPI.getConfig(),
        usuariosAPI.listar()
      ]);
      
      setConfig(configRes.data || config);
      setTecnicos((tecnicosRes.data || []).filter(u => u.role === 'tecnico'));
    } catch (e) {
      console.error('Error cargando datos:', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchComisiones = async () => {
    try {
      const params = {};
      if (filtros.tecnico_id) params.tecnico_id = filtros.tecnico_id;
      if (filtros.estado) params.estado = filtros.estado;
      if (filtros.periodo) params.periodo = filtros.periodo;
      
      const res = await comisionesAPI.listar(params);
      setComisiones(res.data?.comisiones || []);
      setTotales(res.data?.totales || { pendiente: 0, aprobadas: 0, pagadas: 0 });
    } catch (e) {
      console.error('Error cargando comisiones:', e);
    }
  };

  const fetchResumen = async () => {
    try {
      const res = await comisionesAPI.resumen(filtros.periodo);
      setResumen(res.data || []);
    } catch (e) {
      console.error('Error cargando resumen:', e);
    }
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      await comisionesAPI.updateConfig(config);
      toast.success('Configuración de comisiones guardada');
    } catch (e) {
      toast.error('Error al guardar configuración');
    } finally {
      setSaving(false);
    }
  };

  const handleAprobar = async (id) => {
    try {
      await comisionesAPI.aprobar(id);
      toast.success('Comisión aprobada');
      fetchComisiones();
    } catch (e) {
      toast.error('Error al aprobar comisión');
    }
  };

  const handlePagar = async (id) => {
    try {
      await comisionesAPI.pagar(id);
      toast.success('Comisión marcada como pagada');
      fetchComisiones();
    } catch (e) {
      toast.error('Error al marcar como pagada');
    }
  };

  const getEstadoBadge = (estado) => {
    const estilos = {
      pendiente: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      aprobada: 'bg-blue-100 text-blue-800 border-blue-200',
      pagada: 'bg-green-100 text-green-800 border-green-200',
      cancelada: 'bg-red-100 text-red-800 border-red-200'
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

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <DollarSign className="w-7 h-7 text-green-600" />
            </div>
            Comisiones de Técnicos
          </h1>
          <p className="text-muted-foreground mt-1">
            Gestiona las comisiones por reparaciones completadas
          </p>
        </div>
        {activeTab === 'config' && (
          <Button onClick={handleSaveConfig} disabled={saving}>
            {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
            Guardar Configuración
          </Button>
        )}
      </div>

      {/* Banner de estado */}
      <Card className={config.sistema_activo ? 'border-green-200 bg-green-50/50' : 'border-yellow-200 bg-yellow-50/50'}>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {config.sistema_activo ? (
                <CheckCircle className="w-6 h-6 text-green-600" />
              ) : (
                <AlertCircle className="w-6 h-6 text-yellow-600" />
              )}
              <div>
                <p className="font-medium">
                  {config.sistema_activo ? 'Sistema de Comisiones Activo' : 'Sistema de Comisiones Inactivo'}
                </p>
                <p className="text-sm text-muted-foreground">
                  {config.sistema_activo 
                    ? 'Las comisiones se generan automáticamente al completar reparaciones' 
                    : 'Activa el sistema para comenzar a registrar comisiones'}
                </p>
              </div>
            </div>
            <Switch
              checked={config.sistema_activo}
              onCheckedChange={(v) => setConfig(prev => ({ ...prev, sistema_activo: v }))}
            />
          </div>
        </CardContent>
      </Card>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="config" className="flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Configuración
          </TabsTrigger>
          <TabsTrigger value="listado" className="flex items-center gap-2">
            <DollarSign className="w-4 h-4" />
            Listado
          </TabsTrigger>
          <TabsTrigger value="resumen" className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Resumen
          </TabsTrigger>
        </TabsList>

        {/* Tab: Configuración */}
        <TabsContent value="config">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Valores por defecto */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calculator className="w-5 h-5" />
                  Valores por Defecto
                </CardTitle>
                <CardDescription>
                  Configura los valores base para las comisiones de todos los técnicos
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Percent className="w-4 h-4" />
                    Porcentaje sobre precio de reparación
                  </Label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      step="0.5"
                      value={config.porcentaje_default}
                      onChange={(e) => setConfig(prev => ({ ...prev, porcentaje_default: parseFloat(e.target.value) || 0 }))}
                      className="w-24"
                    />
                    <span className="text-muted-foreground">%</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Se aplica sobre el precio total de la reparación
                  </p>
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <DollarSign className="w-4 h-4" />
                    Cantidad fija por orden completada
                  </Label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      min="0"
                      step="0.5"
                      value={config.fijo_default}
                      onChange={(e) => setConfig(prev => ({ ...prev, fijo_default: parseFloat(e.target.value) || 0 }))}
                      className="w-24"
                    />
                    <span className="text-muted-foreground">€</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Se suma al porcentaje (si aplica)
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Tipos de servicio */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Filter className="w-5 h-5" />
                  Aplicar Comisiones a
                </CardTitle>
                <CardDescription>
                  Selecciona qué tipos de reparación generan comisión
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                  <div>
                    <p className="font-medium">Reparaciones de Seguro</p>
                    <p className="text-sm text-muted-foreground">Órdenes de aseguradoras</p>
                  </div>
                  <Switch
                    checked={config.aplicar_a_seguros}
                    onCheckedChange={(v) => setConfig(prev => ({ ...prev, aplicar_a_seguros: v }))}
                  />
                </div>

                <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                  <div>
                    <p className="font-medium">Reparaciones Particulares</p>
                    <p className="text-sm text-muted-foreground">Clientes directos</p>
                  </div>
                  <Switch
                    checked={config.aplicar_a_particulares}
                    onCheckedChange={(v) => setConfig(prev => ({ ...prev, aplicar_a_particulares: v }))}
                  />
                </div>

                <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                  <div>
                    <p className="font-medium">Reparaciones en Garantía</p>
                    <p className="text-sm text-muted-foreground">Sin coste para cliente</p>
                  </div>
                  <Switch
                    checked={config.aplicar_a_garantias}
                    onCheckedChange={(v) => setConfig(prev => ({ ...prev, aplicar_a_garantias: v }))}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Configuración por técnico */}
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="w-5 h-5" />
                  Configuración por Técnico
                </CardTitle>
                <CardDescription>
                  Puedes personalizar el porcentaje de comisión para cada técnico en su ficha de empleado
                </CardDescription>
              </CardHeader>
              <CardContent>
                {tecnicos.length === 0 ? (
                  <p className="text-muted-foreground text-center py-4">No hay técnicos registrados</p>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                    {tecnicos.map((tec) => (
                      <div key={tec.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border">
                        <div>
                          <p className="font-medium">{tec.nombre} {tec.apellidos || ''}</p>
                          <p className="text-xs text-muted-foreground">{tec.email}</p>
                        </div>
                        <div className="text-right">
                          <p className="font-medium">
                            {tec.info_laboral?.comision_porcentaje || config.porcentaje_default}%
                          </p>
                          <Badge variant={tec.info_laboral?.comisiones_activas ? 'default' : 'secondary'} className="text-xs">
                            {tec.info_laboral?.comisiones_activas ? 'Activo' : 'Inactivo'}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab: Listado */}
        <TabsContent value="listado">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Listado de Comisiones</CardTitle>
                <div className="flex gap-2">
                  <Select value={filtros.estado} onValueChange={(v) => setFiltros(prev => ({ ...prev, estado: v }))}>
                    <SelectTrigger className="w-[150px]">
                      <SelectValue placeholder="Estado" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Todos</SelectItem>
                      <SelectItem value="pendiente">Pendiente</SelectItem>
                      <SelectItem value="aprobada">Aprobada</SelectItem>
                      <SelectItem value="pagada">Pagada</SelectItem>
                    </SelectContent>
                  </Select>
                  <Input
                    type="month"
                    value={filtros.periodo}
                    onChange={(e) => setFiltros(prev => ({ ...prev, periodo: e.target.value }))}
                    className="w-[150px]"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {/* Totales */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                  <p className="text-sm text-yellow-600 font-medium">Pendientes</p>
                  <p className="text-2xl font-bold text-yellow-700">{totales.pendiente.toFixed(2)}€</p>
                </div>
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="text-sm text-blue-600 font-medium">Aprobadas</p>
                  <p className="text-2xl font-bold text-blue-700">{totales.aprobadas.toFixed(2)}€</p>
                </div>
                <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                  <p className="text-sm text-green-600 font-medium">Pagadas</p>
                  <p className="text-2xl font-bold text-green-700">{totales.pagadas.toFixed(2)}€</p>
                </div>
              </div>

              {/* Lista */}
              {comisiones.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <DollarSign className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No hay comisiones para mostrar</p>
                  <p className="text-sm">Las comisiones se generan al completar reparaciones</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {comisiones.map((com) => (
                    <div key={com.id} className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border">
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <p className="font-medium">{com.tecnico_nombre}</p>
                          <Badge className={getEstadoBadge(com.estado)}>{com.estado}</Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          Orden: {com.numero_orden} • {com.porcentaje_aplicado}% de {com.precio_reparacion}€
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xl font-bold">{com.monto_total.toFixed(2)}€</p>
                        <div className="flex gap-1 mt-1">
                          {com.estado === 'pendiente' && (
                            <Button size="sm" variant="outline" onClick={() => handleAprobar(com.id)}>
                              Aprobar
                            </Button>
                          )}
                          {com.estado === 'aprobada' && (
                            <Button size="sm" variant="default" onClick={() => handlePagar(com.id)}>
                              Marcar Pagada
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Resumen */}
        <TabsContent value="resumen">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Resumen por Técnico</CardTitle>
                <div className="flex gap-2">
                  <Input
                    type="month"
                    value={filtros.periodo}
                    onChange={(e) => setFiltros(prev => ({ ...prev, periodo: e.target.value }))}
                    className="w-[150px]"
                  />
                  <Button variant="outline">
                    <Download className="w-4 h-4 mr-2" />
                    Exportar
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {resumen.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <TrendingUp className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No hay datos para el período seleccionado</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {resumen.map((r) => (
                    <div key={r._id} className="p-4 bg-slate-50 rounded-lg border">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <p className="font-medium text-lg">{r.tecnico_nombre}</p>
                          <p className="text-sm text-muted-foreground">{r.total_ordenes} reparaciones</p>
                        </div>
                        <p className="text-2xl font-bold">{r.total_monto.toFixed(2)}€</p>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <div className="p-2 bg-yellow-100 rounded text-center">
                          <p className="text-yellow-600">Pendiente</p>
                          <p className="font-medium">{r.pendiente.toFixed(2)}€</p>
                        </div>
                        <div className="p-2 bg-blue-100 rounded text-center">
                          <p className="text-blue-600">Aprobada</p>
                          <p className="font-medium">{r.aprobada.toFixed(2)}€</p>
                        </div>
                        <div className="p-2 bg-green-100 rounded text-center">
                          <p className="text-green-600">Pagada</p>
                          <p className="font-medium">{r.pagada.toFixed(2)}€</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

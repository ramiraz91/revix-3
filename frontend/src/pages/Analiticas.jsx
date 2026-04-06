import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar } from '@/components/ui/calendar';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { 
  BarChart3, TrendingUp, Clock, Users, Trophy, PieChart, DollarSign, 
  Wallet, CreditCard, TrendingDown, ArrowUpRight, ArrowDownRight,
  Calendar as CalendarIcon, RefreshCw, FileText, Target, Calculator, AlertCircle
} from 'lucide-react';
import API from '@/lib/api';

const STATUS_LABELS = {
  pendiente_recibir: 'Pendiente',
  recibida: 'Recibida',
  en_taller: 'En Taller',
  reparado: 'Reparado',
  validacion: 'Validación',
  enviado: 'Enviado',
  cancelado: 'Cancelado',
  garantia: 'Garantía',
  reemplazo: 'Reemplazo',
  irreparable: 'Irreparable'
};

const STATUS_COLORS = {
  pendiente_recibir: '#94a3b8',
  recibida: '#3b82f6',
  en_taller: '#f59e0b',
  reparado: '#10b981',
  validacion: '#8b5cf6',
  enviado: '#22c55e',
  cancelado: '#ef4444',
  garantia: '#f97316',
  reemplazo: '#ec4899',
  irreparable: '#6b7280'
};

export default function Analiticas() {
  const [data, setData] = useState(null);
  const [finanzas, setFinanzas] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingFinanzas, setLoadingFinanzas] = useState(false);
  const [periodo, setPeriodo] = useState('mes');
  const [activeTab, setActiveTab] = useState('facturacion');

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    fetchFinanzas();
  }, [periodo]);

  const fetchData = async () => {
    try {
      const res = await API.get('/master/analiticas');
      setData(res.data);
    } catch (err) {
      console.error('Error cargando analíticas:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchFinanzas = async () => {
    try {
      setLoadingFinanzas(true);
      const res = await API.get(`/master/finanzas?periodo=${periodo}`);
      setFinanzas(res.data);
    } catch (err) {
      console.error('Error cargando finanzas:', err);
    } finally {
      setLoadingFinanzas(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
    </div>
  );

  if (!data) return <div className="text-center py-8 text-muted-foreground">Error cargando analíticas</div>;

  const maxIngresos = Math.max(...Object.values(data.ingresos_por_mes || {}), 1);
  const maxOrdenes = Math.max(...Object.values(data.ordenes_por_mes || {}), 1);
  const totalEstado = Object.values(data.distribucion_estado || {}).reduce((a, b) => a + b, 0);

  const formatCurrency = (value) => {
    return (value || 0).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  return (
    <div className="space-y-6" data-testid="analiticas-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Analíticas y Finanzas</h1>
          <p className="text-muted-foreground">Control financiero y rendimiento del negocio</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => { fetchData(); fetchFinanzas(); }}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Actualizar
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="facturacion" className="flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Facturación
          </TabsTrigger>
          <TabsTrigger value="proyecciones" className="flex items-center gap-2">
            <Target className="w-4 h-4" />
            Proyecciones
          </TabsTrigger>
          <TabsTrigger value="operaciones" className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            Operaciones
          </TabsTrigger>
        </TabsList>

        {/* TAB FACTURACIÓN */}
        <TabsContent value="facturacion" className="space-y-6">
          {/* Selector de período */}
          <div className="flex items-center gap-4 p-4 bg-muted/50 rounded-lg">
            <Calendar className="w-5 h-5 text-muted-foreground" />
            <span className="text-sm font-medium">Período:</span>
            <Select value={periodo} onValueChange={setPeriodo}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="semana">Esta Semana</SelectItem>
                <SelectItem value="mes">Este Mes</SelectItem>
                <SelectItem value="trimestre">Este Trimestre</SelectItem>
                <SelectItem value="año">Este Año</SelectItem>
              </SelectContent>
            </Select>
            {finanzas?.periodo && (
              <span className="text-xs text-muted-foreground">
                {new Date(finanzas.periodo.inicio).toLocaleDateString('es-ES')} - {new Date(finanzas.periodo.fin).toLocaleDateString('es-ES')}
                ({finanzas.periodo.dias_transcurridos} días)
              </span>
            )}
          </div>

          {loadingFinanzas ? (
            <div className="flex items-center justify-center h-32">
              <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : finanzas ? (
            <>
              {/* Resumen Principal de Facturación */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                <Card className="border-l-4 border-l-blue-500 lg:col-span-1">
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground mb-1">Total Órdenes</div>
                    <div className="text-3xl font-bold text-blue-600">{finanzas.resumen?.total_ordenes || 0}</div>
                    <div className="text-xs text-muted-foreground">en el período</div>
                  </CardContent>
                </Card>

                <Card className="border-l-4 border-l-purple-500 lg:col-span-2">
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground mb-1">Total a Facturar</div>
                    <div className="text-3xl font-bold text-purple-600">{formatCurrency(finanzas.resumen?.total_a_facturar)} €</div>
                    <div className="text-xs text-muted-foreground">rendimiento del período</div>
                  </CardContent>
                </Card>

                <Card className="border-l-4 border-l-amber-500">
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground mb-1">Ticket Medio</div>
                    <div className="text-3xl font-bold text-amber-600">{formatCurrency(finanzas.resumen?.ticket_medio)} €</div>
                    <div className="text-xs text-muted-foreground">por orden</div>
                  </CardContent>
                </Card>

                <Card className={`border-l-4 ${finanzas.comparativa?.variacion_porcentaje >= 0 ? 'border-l-green-500' : 'border-l-red-500'}`}>
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground mb-1">vs Período Anterior</div>
                    <div className={`text-3xl font-bold flex items-center gap-1 ${finanzas.comparativa?.variacion_porcentaje >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {finanzas.comparativa?.variacion_porcentaje >= 0 ? <ArrowUpRight className="w-6 h-6" /> : <ArrowDownRight className="w-6 h-6" />}
                      {Math.abs(finanzas.comparativa?.variacion_porcentaje || 0)}%
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Anterior: {formatCurrency(finanzas.comparativa?.periodo_anterior)} €
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Clasificación por Estado de Facturación */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="bg-green-50 border-green-200">
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-green-800">Ya Facturado</span>
                      <Badge variant="secondary" className="bg-green-100 text-green-800">
                        {finanzas.clasificacion?.facturado?.count || 0} órdenes
                      </Badge>
                    </div>
                    <div className="text-2xl font-bold text-green-700">
                      {formatCurrency(finanzas.resumen?.ya_facturado)} €
                    </div>
                    <div className="text-xs text-green-600 mt-1">Órdenes cerradas y cobradas</div>
                  </CardContent>
                </Card>

                <Card className="bg-amber-50 border-amber-200">
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-amber-800">Pendiente Facturar</span>
                      <Badge variant="secondary" className="bg-amber-100 text-amber-800">
                        {finanzas.clasificacion?.pendiente_facturar?.count || 0} órdenes
                      </Badge>
                    </div>
                    <div className="text-2xl font-bold text-amber-700">
                      {formatCurrency(finanzas.resumen?.pendiente_facturar)} €
                    </div>
                    <div className="text-xs text-amber-600 mt-1">Reparadas, listas para cerrar</div>
                  </CardContent>
                </Card>

                <Card className="bg-blue-50 border-blue-200">
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-blue-800">En Proceso</span>
                      <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                        {finanzas.clasificacion?.en_proceso?.count || 0} órdenes
                      </Badge>
                    </div>
                    <div className="text-2xl font-bold text-blue-700">
                      {formatCurrency(finanzas.resumen?.en_proceso)} €
                    </div>
                    <div className="text-xs text-blue-600 mt-1">En taller actualmente</div>
                  </CardContent>
                </Card>

                <Card className="bg-slate-50 border-slate-200">
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-slate-800">Por Recibir</span>
                      <Badge variant="secondary" className="bg-slate-100 text-slate-800">
                        {finanzas.clasificacion?.por_recibir?.count || 0} órdenes
                      </Badge>
                    </div>
                    <div className="text-2xl font-bold text-slate-700">
                      {formatCurrency(finanzas.resumen?.por_recibir)} €
                    </div>
                    <div className="text-xs text-slate-600 mt-1">Pendientes de recepción</div>
                  </CardContent>
                </Card>
              </div>

              {/* Desglose Semanal */}
              {Object.keys(finanzas.desglose_semanal || {}).length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Calendar className="w-4 h-4" />
                      Desglose Semanal
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left py-2 px-3">Semana</th>
                            <th className="text-right py-2 px-3">Órdenes</th>
                            <th className="text-right py-2 px-3">Valor Total</th>
                            <th className="text-right py-2 px-3">Facturado</th>
                            <th className="text-right py-2 px-3">Pendiente</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(finanzas.desglose_semanal).map(([semana, datos]) => (
                            <tr key={semana} className="border-b hover:bg-muted/50">
                              <td className="py-2 px-3 font-medium">{semana}</td>
                              <td className="text-right py-2 px-3">{datos.ordenes}</td>
                              <td className="text-right py-2 px-3 font-medium">{formatCurrency(datos.valor)} €</td>
                              <td className="text-right py-2 px-3 text-green-600">{formatCurrency(datos.facturado)} €</td>
                              <td className="text-right py-2 px-3 text-amber-600">{formatCurrency(datos.pendiente)} €</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Costes y Beneficios */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Calculator className="w-4 h-4" />
                      Costes
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between items-center p-3 bg-muted/50 rounded-lg">
                      <span className="text-sm">Total Costes (Materiales)</span>
                      <span className="font-bold text-red-600">{formatCurrency(finanzas.costes?.total_costes)} €</span>
                    </div>
                    <div className="flex justify-between items-center px-3">
                      <span className="text-sm text-muted-foreground">De órdenes facturadas</span>
                      <span className="text-sm">{formatCurrency(finanzas.costes?.costes_facturado)} €</span>
                    </div>
                    <div className="flex justify-between items-center px-3">
                      <span className="text-sm text-muted-foreground">De órdenes pendientes</span>
                      <span className="text-sm">{formatCurrency(finanzas.costes?.costes_pendiente)} €</span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <TrendingUp className="w-4 h-4" />
                      Beneficios
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                      <span className="text-sm font-medium">Beneficio Facturado</span>
                      <span className="font-bold text-green-600">{formatCurrency(finanzas.beneficio?.beneficio_facturado)} €</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-amber-50 rounded-lg">
                      <span className="text-sm font-medium">Beneficio Estimado Pendiente</span>
                      <span className="font-bold text-amber-600">{formatCurrency(finanzas.beneficio?.beneficio_estimado_pendiente)} €</span>
                    </div>
                    <div className="flex justify-between items-center px-3">
                      <span className="text-sm text-muted-foreground">Margen de beneficio</span>
                      <Badge variant={finanzas.beneficio?.margen_porcentaje >= 30 ? 'default' : 'secondary'}>
                        {finanzas.beneficio?.margen_porcentaje || 0}%
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Pendientes de períodos anteriores */}
              {finanzas.pendientes_anteriores?.count > 0 && (
                <Card className="border-orange-200 bg-orange-50">
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium text-orange-800">⚠️ Órdenes Pendientes de Períodos Anteriores</div>
                        <div className="text-xs text-orange-600">Órdenes sin cerrar de meses anteriores</div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-orange-700">{formatCurrency(finanzas.pendientes_anteriores.total)} €</div>
                        <div className="text-sm text-orange-600">{finanzas.pendientes_anteriores.count} órdenes</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-32 text-muted-foreground gap-2">
              <AlertCircle className="w-6 h-6" />
              <p className="text-sm">Error al cargar datos de finanzas. Intente recargar la página.</p>
            </div>
          )}
        </TabsContent>

        {/* TAB PROYECCIONES */}
        <TabsContent value="proyecciones" className="space-y-6">
          {finanzas?.proyeccion && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="border-t-4 border-t-blue-500">
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground mb-1">Ritmo Diario</div>
                    <div className="text-2xl font-bold text-blue-600">{formatCurrency(finanzas.proyeccion.ritmo_diario)} €</div>
                    <div className="text-xs text-muted-foreground">facturación media por día</div>
                  </CardContent>
                </Card>

                <Card className="border-t-4 border-t-purple-500">
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground mb-1">Proyección {periodo === 'mes' ? 'Mensual' : periodo === 'semana' ? 'Semanal' : periodo === 'trimestre' ? 'Trimestral' : 'Anual'}</div>
                    <div className="text-2xl font-bold text-purple-600">{formatCurrency(finanzas.proyeccion.proyeccion_periodo)} €</div>
                    <div className="text-xs text-muted-foreground">al ritmo actual</div>
                  </CardContent>
                </Card>

                <Card className="border-t-4 border-t-green-500">
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground mb-1">Proyección Mensual</div>
                    <div className="text-2xl font-bold text-green-600">{formatCurrency(finanzas.proyeccion.proyeccion_mensual)} €</div>
                    <div className="text-xs text-muted-foreground">estimado 30 días</div>
                  </CardContent>
                </Card>

                <Card className="border-t-4 border-t-amber-500">
                  <CardContent className="pt-4">
                    <div className="text-xs text-muted-foreground mb-1">Proyección Anual</div>
                    <div className="text-2xl font-bold text-amber-600">{formatCurrency(finanzas.proyeccion.proyeccion_anual)} €</div>
                    <div className="text-xs text-muted-foreground">estimado 365 días</div>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Análisis de Tendencia</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/50">
                    {finanzas.comparativa?.tendencia === 'alza' ? (
                      <>
                        <div className="p-3 bg-green-100 rounded-full">
                          <TrendingUp className="w-8 h-8 text-green-600" />
                        </div>
                        <div>
                          <div className="font-medium text-green-700">Tendencia al Alza</div>
                          <div className="text-sm text-muted-foreground">
                            Has mejorado un {finanzas.comparativa.variacion_porcentaje}% respecto al período anterior.
                            Si mantienes este ritmo, cerrarás el mes con {formatCurrency(finanzas.proyeccion.proyeccion_mensual)} €.
                          </div>
                        </div>
                      </>
                    ) : finanzas.comparativa?.tendencia === 'baja' ? (
                      <>
                        <div className="p-3 bg-red-100 rounded-full">
                          <TrendingDown className="w-8 h-8 text-red-600" />
                        </div>
                        <div>
                          <div className="font-medium text-red-700">Tendencia a la Baja</div>
                          <div className="text-sm text-muted-foreground">
                            Has disminuido un {Math.abs(finanzas.comparativa.variacion_porcentaje)}% respecto al período anterior.
                            Revisa las órdenes pendientes de facturar para mejorar los números.
                          </div>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="p-3 bg-blue-100 rounded-full">
                          <BarChart3 className="w-8 h-8 text-blue-600" />
                        </div>
                        <div>
                          <div className="font-medium text-blue-700">Tendencia Estable</div>
                          <div className="text-sm text-muted-foreground">
                            Tu rendimiento es similar al período anterior. Proyección mensual: {formatCurrency(finanzas.proyeccion.proyeccion_mensual)} €.
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>

        {/* TAB OPERACIONES */}
        <TabsContent value="operaciones" className="space-y-6">
          {/* KPIs Operativos */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-100 rounded-lg"><BarChart3 className="w-5 h-5 text-blue-600" /></div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total Órdenes</p>
                    <p className="text-2xl font-bold">{data.total_ordenes}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-100 rounded-lg"><TrendingUp className="w-5 h-5 text-green-600" /></div>
                  <div>
                    <p className="text-sm text-muted-foreground">Completadas</p>
                    <p className="text-2xl font-bold text-green-600">{data.total_completadas}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-amber-100 rounded-lg"><Clock className="w-5 h-5 text-amber-600" /></div>
                  <div>
                    <p className="text-sm text-muted-foreground">T. Medio Reparación</p>
                    <p className="text-2xl font-bold">{data.tiempo_medio_reparacion_horas}h</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-100 rounded-lg"><Users className="w-5 h-5 text-purple-600" /></div>
                  <div>
                    <p className="text-sm text-muted-foreground">En Proceso</p>
                    <p className="text-2xl font-bold text-purple-600">{data.total_en_proceso}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Ingresos por mes */}
            <Card>
              <CardHeader><CardTitle className="text-base flex items-center gap-2"><TrendingUp className="w-4 h-4" /> Ingresos por Mes</CardTitle></CardHeader>
              <CardContent>
                {Object.keys(data.ingresos_por_mes || {}).length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">Sin datos de ingresos</p>
                ) : (
                  <div className="space-y-2">
                    {Object.entries(data.ingresos_por_mes).map(([mes, total]) => (
                      <div key={mes} className="flex items-center gap-3">
                        <span className="text-xs w-16 text-muted-foreground">{mes}</span>
                        <div className="flex-1 h-6 bg-muted rounded-full overflow-hidden">
                          <div className="h-full bg-green-500 rounded-full transition-all" style={{ width: `${(total / maxIngresos) * 100}%` }} />
                        </div>
                        <span className="text-xs font-medium w-20 text-right">{total.toFixed(0)} €</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Órdenes por mes */}
            <Card>
              <CardHeader><CardTitle className="text-base flex items-center gap-2"><BarChart3 className="w-4 h-4" /> Órdenes por Mes</CardTitle></CardHeader>
              <CardContent>
                {Object.keys(data.ordenes_por_mes || {}).length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">Sin datos</p>
                ) : (
                  <div className="space-y-2">
                    {Object.entries(data.ordenes_por_mes).map(([mes, count]) => (
                      <div key={mes} className="flex items-center gap-3">
                        <span className="text-xs w-16 text-muted-foreground">{mes}</span>
                        <div className="flex-1 h-6 bg-muted rounded-full overflow-hidden">
                          <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${(count / maxOrdenes) * 100}%` }} />
                        </div>
                        <span className="text-xs font-medium w-10 text-right">{count}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Distribución por estado */}
            <Card>
              <CardHeader><CardTitle className="text-base flex items-center gap-2"><PieChart className="w-4 h-4" /> Distribución por Estado</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(data.distribucion_estado || {}).sort((a, b) => b[1] - a[1]).map(([estado, count]) => (
                    <div key={estado} className="flex items-center gap-3">
                      <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: STATUS_COLORS[estado] || '#94a3b8' }} />
                      <span className="text-xs flex-1">{STATUS_LABELS[estado] || estado}</span>
                      <div className="w-24 h-4 bg-muted rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all" style={{ width: `${(count / totalEstado) * 100}%`, backgroundColor: STATUS_COLORS[estado] || '#94a3b8' }} />
                      </div>
                      <span className="text-xs font-medium w-8 text-right">{count}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Ranking técnicos */}
            <Card>
              <CardHeader><CardTitle className="text-base flex items-center gap-2"><Trophy className="w-4 h-4" /> Ranking Técnicos</CardTitle></CardHeader>
              <CardContent>
                {data.ranking_tecnicos?.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">Sin técnicos registrados</p>
                ) : (
                  <div className="space-y-3">
                    {data.ranking_tecnicos?.map((t, i) => (
                      <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                        <span className={`text-lg font-bold w-8 text-center ${i === 0 ? 'text-yellow-500' : i === 1 ? 'text-gray-400' : i === 2 ? 'text-amber-700' : 'text-muted-foreground'}`}>
                          #{i + 1}
                        </span>
                        <div className="flex-1">
                          <p className="font-medium text-sm">{t.nombre}</p>
                          <p className="text-xs text-muted-foreground">{t.completadas} completadas de {t.total}</p>
                        </div>
                        <span className="text-sm font-bold text-green-600">{t.tasa}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

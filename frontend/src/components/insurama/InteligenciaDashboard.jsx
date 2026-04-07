/**
 * Dashboard de Inteligencia de Precios
 * Muestra KPIs, análisis de competidores, y recomendaciones
 */
import { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Trophy,
  Target,
  Users,
  BarChart3,
  AlertTriangle,
  Lightbulb,
  RefreshCw,
  ArrowUp,
  ArrowDown,
  Minus,
  Smartphone,
  Wrench,
  Calendar,
  Download,
  FileText
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar as CalendarComponent } from '@/components/ui/calendar';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { inteligenciaPreciosAPI } from '@/lib/api';
import { toast } from 'sonner';

export default function InteligenciaDashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [periodo, setPeriodo] = useState('mes');
  const [fechaInicio, setFechaInicio] = useState(null);
  const [fechaFin, setFechaFin] = useState(null);
  const [generandoInforme, setGenerandoInforme] = useState(false);

  useEffect(() => {
    cargarDashboard();
  }, [periodo, fechaInicio, fechaFin]);

  const cargarDashboard = async () => {
    try {
      setLoading(true);
      let queryParams = `?periodo=${periodo}`;
      if (periodo === 'custom' && fechaInicio && fechaFin) {
        queryParams = `?periodo=custom&fecha_inicio=${fechaInicio.toISOString()}&fecha_fin=${fechaFin.toISOString()}`;
      }
      const data = await inteligenciaPreciosAPI.getDashboard(queryParams);
      setDashboard(data);
    } catch (error) {
      console.error('Error cargando dashboard:', error);
      toast.error('Error al cargar dashboard de inteligencia');
    } finally {
      setLoading(false);
    }
  };
  
  const handlePeriodoChange = (value) => {
    setPeriodo(value);
    if (value === 'custom') {
      const hoy = new Date();
      const inicioMes = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
      setFechaInicio(inicioMes);
      setFechaFin(hoy);
    } else {
      setFechaInicio(null);
      setFechaFin(null);
    }
  };
  
  const generarInforme = async () => {
    if (!dashboard) return;
    
    setGenerandoInforme(true);
    try {
      const periodoTexto = periodo === 'custom' && fechaInicio && fechaFin
        ? `${format(fechaInicio, 'dd/MM/yyyy')} - ${format(fechaFin, 'dd/MM/yyyy')}`
        : periodo === 'semana' ? 'Esta Semana'
        : periodo === 'mes' ? 'Este Mes'
        : periodo === 'trimestre' ? 'Este Trimestre'
        : periodo === 'año' ? 'Este Año'
        : 'Todo el período';
      
      const { negocio, kpis, top_competidores, dispositivos_rentables, tipos_reparacion } = dashboard;
      
      // Generar CSV con los datos
      let csv = 'INFORME DE MÉTRICAS INSURAMA\n';
      csv += `Período: ${periodoTexto}\n`;
      csv += `Generado: ${format(new Date(), 'dd/MM/yyyy HH:mm')}\n\n`;
      
      csv += '=== MÉTRICAS DEL NEGOCIO ===\n';
      csv += `Total Órdenes,${negocio?.total_ordenes_insurama || 0}\n`;
      csv += `Órdenes últimos 30d,${negocio?.ordenes_30d || 0}\n`;
      csv += `Ratio Aceptación,${negocio?.ratio_aceptacion || 0}%\n`;
      csv += `Ticket Medio,${negocio?.ticket_medio || 0}€\n`;
      csv += `Total Ingresos,${negocio?.total_ingresos || 0}€\n`;
      csv += `Total Gastos,${negocio?.total_gastos || 0}€\n`;
      csv += `Beneficio,${negocio?.beneficio || 0}€\n`;
      csv += `Margen,${negocio?.margen_porcentaje || 0}%\n\n`;
      
      csv += '=== ANÁLISIS DE COMPETENCIA ===\n';
      csv += `Tasa de Éxito,${kpis?.tasa_exito || 0}%\n`;
      csv += `Posición Media,${kpis?.posicion_media || '-'}\n`;
      csv += `Total Análisis,${kpis?.total_analisis || 0}\n\n`;
      
      if (top_competidores?.length > 0) {
        csv += '=== TOP COMPETIDORES ===\n';
        csv += 'Nombre,Apariciones,Gana,Precio Medio\n';
        top_competidores.forEach(c => {
          csv += `${c.nombre},${c.apariciones},${c.ganador_count || 0},${c.precio_medio || 0}€\n`;
        });
      }
      
      // Descargar archivo
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `informe_insurama_${format(new Date(), 'yyyyMMdd_HHmm')}.csv`;
      link.click();
      URL.revokeObjectURL(url);
      
      toast.success('Informe generado correctamente');
    } catch (error) {
      console.error('Error generando informe:', error);
      toast.error('Error al generar informe');
    } finally {
      setGenerandoInforme(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!dashboard) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <BarChart3 className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Sin datos disponibles</h3>
          <p className="text-gray-500 mt-2">
            Los datos de inteligencia se capturarán automáticamente cuando se cierren presupuestos.
          </p>
        </CardContent>
      </Card>
    );
  }

  const { kpis, negocio, top_competidores, dispositivos_rentables, tipos_reparacion, evolucion_mensual } = dashboard;

  return (
    <div className="space-y-6">
      {/* FILTROS Y ACCIONES */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-muted/50 rounded-lg">
        <div className="flex items-center gap-4">
          <Calendar className="w-5 h-5 text-muted-foreground" />
          <span className="text-sm font-medium">Período:</span>
          <Select value={periodo} onValueChange={handlePeriodoChange}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todo">Todo</SelectItem>
              <SelectItem value="semana">Esta Semana</SelectItem>
              <SelectItem value="mes">Este Mes</SelectItem>
              <SelectItem value="trimestre">Este Trimestre</SelectItem>
              <SelectItem value="año">Este Año</SelectItem>
              <SelectItem value="custom">Personalizado</SelectItem>
            </SelectContent>
          </Select>
          
          {periodo === 'custom' && (
            <div className="flex items-center gap-2">
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" size="sm" className="w-[130px] justify-start text-left font-normal">
                    <Calendar className="mr-2 h-4 w-4" />
                    {fechaInicio ? format(fechaInicio, 'dd/MM/yyyy', { locale: es }) : 'Desde'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <CalendarComponent
                    mode="single"
                    selected={fechaInicio}
                    onSelect={setFechaInicio}
                    initialFocus
                    locale={es}
                  />
                </PopoverContent>
              </Popover>
              <span className="text-muted-foreground">→</span>
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" size="sm" className="w-[130px] justify-start text-left font-normal">
                    <Calendar className="mr-2 h-4 w-4" />
                    {fechaFin ? format(fechaFin, 'dd/MM/yyyy', { locale: es }) : 'Hasta'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <CalendarComponent
                    mode="single"
                    selected={fechaFin}
                    onSelect={setFechaFin}
                    initialFocus
                    locale={es}
                  />
                </PopoverContent>
              </Popover>
            </div>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={cargarDashboard} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
          <Button variant="default" size="sm" onClick={generarInforme} disabled={generandoInforme || !dashboard}>
            {generandoInforme ? (
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Download className="w-4 h-4 mr-2" />
            )}
            Generar Informe
          </Button>
        </div>
      </div>
      
      {/* NUEVAS MÉTRICAS DEL NEGOCIO */}
      <div>
        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-green-600" />
          Métricas del Negocio Insurama
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <Card className="border-l-4 border-l-blue-500">
            <CardContent className="p-3">
              <div className="text-xs text-muted-foreground">Total Órdenes</div>
              <div className="text-xl font-bold text-blue-600">{negocio?.total_ordenes_insurama || 0}</div>
              <div className="text-[10px] text-muted-foreground">{negocio?.ordenes_30d || 0} últimos 30d</div>
            </CardContent>
          </Card>
          
          <Card className="border-l-4 border-l-green-500">
            <CardContent className="p-3">
              <div className="text-xs text-muted-foreground">Ratio Aceptación</div>
              <div className="text-xl font-bold text-green-600">{negocio?.ratio_aceptacion || 0}%</div>
              <div className="text-[10px] text-muted-foreground">presupuestos aceptados</div>
            </CardContent>
          </Card>
          
          <Card className="border-l-4 border-l-amber-500">
            <CardContent className="p-3">
              <div className="text-xs text-muted-foreground">Ticket Medio</div>
              <div className="text-xl font-bold text-amber-600">{negocio?.ticket_medio || 0}€</div>
              <div className="text-[10px] text-muted-foreground">precio promedio</div>
            </CardContent>
          </Card>
          
          <Card className="border-l-4 border-l-emerald-500">
            <CardContent className="p-3">
              <div className="text-xs text-muted-foreground">Ingresos</div>
              <div className="text-xl font-bold text-emerald-600">{(negocio?.total_ingresos || 0).toLocaleString('es-ES')}€</div>
              <div className="text-[10px] text-muted-foreground">órdenes cerradas</div>
            </CardContent>
          </Card>
          
          <Card className="border-l-4 border-l-red-500">
            <CardContent className="p-3">
              <div className="text-xs text-muted-foreground">Gastos</div>
              <div className="text-xl font-bold text-red-600">{(negocio?.total_gastos || 0).toLocaleString('es-ES')}€</div>
              <div className="text-[10px] text-muted-foreground">coste materiales</div>
            </CardContent>
          </Card>
          
          <Card className="border-l-4 border-l-purple-500">
            <CardContent className="p-3">
              <div className="text-xs text-muted-foreground">Beneficio</div>
              <div className={`text-xl font-bold ${(negocio?.beneficio || 0) >= 0 ? 'text-purple-600' : 'text-red-600'}`}>
                {(negocio?.beneficio || 0).toLocaleString('es-ES')}€
              </div>
              <div className="text-[10px] text-muted-foreground">{negocio?.margen_porcentaje || 0}% margen</div>
            </CardContent>
          </Card>
        </div>
        
        {/* Estado de órdenes */}
        <div className="grid grid-cols-3 gap-3 mt-3">
          <Card className="bg-yellow-50 border-yellow-200">
            <CardContent className="p-3 text-center">
              <div className="text-2xl font-bold text-yellow-700">{negocio?.ordenes_pendientes || 0}</div>
              <div className="text-xs text-yellow-600">Pendientes de recibir</div>
            </CardContent>
          </Card>
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="p-3 text-center">
              <div className="text-2xl font-bold text-blue-700">{negocio?.ordenes_en_proceso || 0}</div>
              <div className="text-xs text-blue-600">En proceso</div>
              {negocio?.ingresos_pendientes > 0 && (
                <div className="text-[10px] text-blue-500 mt-1">
                  {negocio.ingresos_pendientes.toLocaleString('es-ES')}€ pendiente cobrar
                </div>
              )}
            </CardContent>
          </Card>
          <Card className="bg-green-50 border-green-200">
            <CardContent className="p-3 text-center">
              <div className="text-2xl font-bold text-green-700">{negocio?.ordenes_cerradas || 0}</div>
              <div className="text-xs text-green-600">Cerradas</div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* KPIs de Competencia */}
      <div>
        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <Trophy className="w-5 h-5 text-amber-500" />
          Análisis de Competencia
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            titulo="Tasa de Éxito"
            valor={`${kpis.tasa_exito}%`}
            subtitulo={`${kpis.ganados}/${kpis.ganados + kpis.perdidos} presupuestos`}
            icono={<Trophy className="w-5 h-5" />}
            color={kpis.tasa_exito >= 60 ? 'green' : kpis.tasa_exito >= 40 ? 'yellow' : 'red'}
            cambio={kpis.tasa_exito_30d - kpis.tasa_exito}
          />
          <KPICard
            titulo="Ganados (30d)"
            valor={kpis.ganados_30d}
            subtitulo={`de ${kpis.registros_30d} en el mes`}
            icono={<Target className="w-5 h-5" />}
            color="blue"
          />
          <KPICard
            titulo="Tu Precio Promedio"
            valor={`${kpis.mi_precio_promedio}€`}
            subtitulo="en presupuestos enviados"
            icono={<TrendingUp className="w-5 h-5" />}
            color="slate"
          />
          <KPICard
            titulo="Diferencia vs Ganador"
            valor={`${kpis.diferencia_promedio > 0 ? '+' : ''}${kpis.diferencia_promedio}€`}
            subtitulo={kpis.diferencia_promedio > 0 ? 'Tu precio es mayor' : 'Tu precio es menor'}
            icono={kpis.diferencia_promedio > 0 ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
            color={kpis.diferencia_promedio > 0 ? 'red' : 'green'}
          />
        </div>
      </div>

      {/* Contenido en tabs */}
      <Tabs defaultValue="competidores" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="competidores" className="flex items-center gap-2">
            <Users className="w-4 h-4" />
            Competidores
          </TabsTrigger>
          <TabsTrigger value="dispositivos" className="flex items-center gap-2">
            <Smartphone className="w-4 h-4" />
            Dispositivos
          </TabsTrigger>
          <TabsTrigger value="reparaciones" className="flex items-center gap-2">
            <Wrench className="w-4 h-4" />
            Reparaciones
          </TabsTrigger>
          <TabsTrigger value="evolucion" className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            Evolución
          </TabsTrigger>
        </TabsList>

        {/* Tab: Competidores que nos ganan */}
        <TabsContent value="competidores">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                Competidores que más nos ganan
              </CardTitle>
              <CardDescription>
                Análisis de talleres que han ganado presupuestos contra ti
              </CardDescription>
            </CardHeader>
            <CardContent>
              {top_competidores?.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Competidor</TableHead>
                      <TableHead className="text-center">Veces Ganado</TableHead>
                      <TableHead className="text-center">Precio Promedio</TableHead>
                      <TableHead className="text-center">Diferencia</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {top_competidores.map((comp, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            {idx < 3 && (
                              <Badge variant={idx === 0 ? 'destructive' : 'secondary'}>
                                #{idx + 1}
                              </Badge>
                            )}
                            {comp.nombre}
                          </div>
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge variant="outline">{comp.veces_ganado}</Badge>
                        </TableCell>
                        <TableCell className="text-center">{comp.precio_promedio?.toFixed(2)}€</TableCell>
                        <TableCell className="text-center">
                          <span className={comp.diferencia_promedio < 0 ? 'text-green-600' : 'text-red-600'}>
                            {comp.diferencia_promedio > 0 ? '+' : ''}{comp.diferencia_promedio?.toFixed(2)}€
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-center text-gray-500 py-8">
                  No hay datos de competidores aún
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Dispositivos más rentables */}
        <TabsContent value="dispositivos">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Smartphone className="w-5 h-5 text-blue-500" />
                Dispositivos más rentables
              </CardTitle>
              <CardDescription>
                Tu tasa de éxito por tipo de dispositivo
              </CardDescription>
            </CardHeader>
            <CardContent>
              {dispositivos_rentables?.length > 0 ? (
                <div className="space-y-4">
                  {dispositivos_rentables.map((disp, idx) => (
                    <div key={idx} className="flex items-center gap-4">
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-sm">{disp.dispositivo || 'Sin especificar'}</span>
                          <span className="text-sm text-gray-500">
                            {disp.ganados}/{disp.ganados + disp.perdidos} ({disp.total} total)
                          </span>
                        </div>
                        <Progress 
                          value={disp.tasa_exito} 
                          className={`h-2 ${disp.tasa_exito >= 60 ? 'bg-green-100' : disp.tasa_exito >= 40 ? 'bg-yellow-100' : 'bg-red-100'}`}
                        />
                      </div>
                      <Badge variant={disp.tasa_exito >= 60 ? 'default' : disp.tasa_exito >= 40 ? 'secondary' : 'destructive'}>
                        {disp.tasa_exito?.toFixed(0)}%
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-gray-500 py-8">
                  No hay datos de dispositivos aún
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Tipos de reparación */}
        <TabsContent value="reparaciones">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Wrench className="w-5 h-5 text-purple-500" />
                Tipos de reparación
              </CardTitle>
              <CardDescription>
                Distribución por tipo de servicio
              </CardDescription>
            </CardHeader>
            <CardContent>
              {tipos_reparacion?.length > 0 ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {tipos_reparacion.map((tipo, idx) => (
                    <Card key={idx} className="border">
                      <CardContent className="p-4 text-center">
                        <div className="text-2xl font-bold">{tipo.total}</div>
                        <div className="text-sm text-gray-500">{tipo.tipo || 'OTROS'}</div>
                        <div className="text-xs text-green-600 mt-1">
                          {tipo.ganados} ganados
                        </div>
                        {tipo.precio_promedio > 0 && (
                          <div className="text-xs text-gray-400">
                            ~{tipo.precio_promedio?.toFixed(0)}€ promedio
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-center text-gray-500 py-8">
                  No hay datos de tipos de reparación aún
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Evolución mensual */}
        <TabsContent value="evolucion">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-indigo-500" />
                Evolución mensual
              </CardTitle>
              <CardDescription>
                Rendimiento de los últimos meses
              </CardDescription>
            </CardHeader>
            <CardContent>
              {evolucion_mensual?.length > 0 ? (
                <div className="space-y-3">
                  {evolucion_mensual.map((mes, idx) => {
                    const total = mes.ganados + mes.perdidos;
                    const tasa = total > 0 ? (mes.ganados / total * 100) : 0;
                    return (
                      <div key={idx} className="flex items-center gap-4">
                        <div className="w-20 text-sm font-medium">{mes.mes}</div>
                        <div className="flex-1">
                          <div className="flex gap-1 h-6">
                            <div 
                              className="bg-green-500 rounded-l"
                              style={{ width: `${mes.ganados / mes.total * 100}%` }}
                              title={`Ganados: ${mes.ganados}`}
                            />
                            <div 
                              className="bg-red-500"
                              style={{ width: `${mes.perdidos / mes.total * 100}%` }}
                              title={`Perdidos: ${mes.perdidos}`}
                            />
                            <div 
                              className="bg-gray-300 rounded-r"
                              style={{ width: `${(mes.total - mes.ganados - mes.perdidos) / mes.total * 100}%` }}
                              title={`Otros: ${mes.total - mes.ganados - mes.perdidos}`}
                            />
                          </div>
                        </div>
                        <div className="w-24 text-right">
                          <span className="text-green-600 font-medium">{mes.ganados}</span>
                          <span className="text-gray-400 mx-1">/</span>
                          <span className="text-red-600">{mes.perdidos}</span>
                          <span className="text-gray-400 text-xs ml-2">({tasa.toFixed(0)}%)</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-center text-gray-500 py-8">
                  No hay datos de evolución aún
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Botón de actualizar */}
      <div className="flex justify-end">
        <Button variant="outline" onClick={cargarDashboard} disabled={loading}>
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Actualizar datos
        </Button>
      </div>
    </div>
  );
}

function KPICard({ titulo, valor, subtitulo, icono, color, cambio }) {
  const colorClasses = {
    green: 'bg-green-50 border-green-200 text-green-700',
    red: 'bg-red-50 border-red-200 text-red-700',
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    yellow: 'bg-amber-50 border-amber-200 text-amber-700',
    slate: 'bg-slate-50 border-slate-200 text-slate-700',
  };

  return (
    <Card className={`border ${colorClasses[color] || colorClasses.slate}`}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {icono}
            <span className="text-sm font-medium">{titulo}</span>
          </div>
          {cambio !== undefined && cambio !== 0 && (
            <Badge variant={cambio > 0 ? 'default' : 'destructive'} className="text-xs">
              {cambio > 0 ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
              {Math.abs(cambio).toFixed(1)}%
            </Badge>
          )}
        </div>
        <div className="mt-2">
          <div className="text-2xl font-bold">{valor}</div>
          <div className="text-xs opacity-75">{subtitulo}</div>
        </div>
      </CardContent>
    </Card>
  );
}

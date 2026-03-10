import { useState, useEffect } from 'react';
import { 
  Crown, 
  Users, 
  TrendingUp, 
  FileText,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Shield,
  XCircle,
  Calendar,
  Euro,
  Download,
  BarChart3
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { masterAPI } from '@/lib/api';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell
} from 'recharts';

const COLORS = ['#667eea', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function PanelMaster() {
  const [loading, setLoading] = useState(true);
  const [metricasTecnicos, setMetricasTecnicos] = useState([]);
  const [facturacion, setFacturacion] = useState(null);
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');

  // ISO 9001
  const [isoKpis, setIsoKpis] = useState(null);
  const [isoDocumentos, setIsoDocumentos] = useState([]);
  const [isoProveedores, setIsoProveedores] = useState([]);
  const [isoDocForm, setIsoDocForm] = useState({ codigo: '', titulo: '', tipo: 'documento', version: '1.0', retencion_anios: 3 });
  const [isoProveedorForm, setIsoProveedorForm] = useState({ proveedor: 'GLS', tipo: 'logistica', puntualidad: 80, calidad: 80, respuesta: 80, incidencias: 10, comentarios: '' });
  const [isoReporteFiltros, setIsoReporteFiltros] = useState({ orden_id: '', fecha_desde: '', fecha_hasta: '' });
  const [qaConfig, setQaConfig] = useState(null);
  const [qaRunResult, setQaRunResult] = useState(null);
  const [capaDashboard, setCapaDashboard] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [tecnicosRes, factRes, isoKpisRes, isoDocsRes, isoProvRes, qaCfgRes, capaRes] = await Promise.all([
        masterAPI.metricasTecnicos(),
        masterAPI.facturacion(),
        masterAPI.isoKpis(),
        masterAPI.isoDocumentos(),
        masterAPI.isoProveedores(),
        masterAPI.qaConfig(),
        masterAPI.capaDashboard(),
      ]);
      setMetricasTecnicos(tecnicosRes.data);
      setFacturacion(factRes.data);
      setIsoKpis(isoKpisRes.data);
      setIsoDocumentos(isoDocsRes.data || []);
      setIsoProveedores(isoProvRes.data || []);
      setQaConfig(qaCfgRes.data || null);
      setCapaDashboard(capaRes.data || null);
    } catch (error) {
      toast.error('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  const handleGuardarIsoDocumento = async () => {
    if (!isoDocForm.codigo || !isoDocForm.titulo) {
      toast.error('Código y título son obligatorios');
      return;
    }
    try {
      await masterAPI.guardarIsoDocumento(isoDocForm);
      toast.success('Documento ISO guardado');
      setIsoDocForm({ codigo: '', titulo: '', tipo: 'documento', version: '1.0', retencion_anios: 3 });
      const docsRes = await masterAPI.isoDocumentos();
      setIsoDocumentos(docsRes.data || []);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error guardando documento ISO');
    }
  };

  const handleEvaluarProveedorIso = async () => {
    if (!isoProveedorForm.proveedor) {
      toast.error('Proveedor obligatorio');
      return;
    }
    try {
      await masterAPI.evaluarIsoProveedor(isoProveedorForm);
      toast.success('Evaluación de proveedor actualizada');
      const provRes = await masterAPI.isoProveedores();
      setIsoProveedores(provRes.data || []);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error evaluando proveedor');
    }
  };

  const handleDescargarReporteIso = () => {
    const url = masterAPI.exportarIsoReportePdf(isoReporteFiltros);
    window.open(url, '_blank');
    toast.success('Generando reporte PDF de evidencias ISO...');
  };

  const handleDescargarAuditPackCsv = () => {
    const url = masterAPI.exportarAuditPackCsv({
      fecha_desde: isoReporteFiltros.fecha_desde,
      fecha_hasta: isoReporteFiltros.fecha_hasta,
    });
    window.open(url, '_blank');
    toast.success('Generando Audit Pack CSV por período...');
  };

  const handleAbrirAuditPackOt = async () => {
    if (!isoReporteFiltros.orden_id) {
      toast.error('Indica un ID de OT para abrir su Audit Pack');
      return;
    }
    try {
      const res = await masterAPI.auditPackOt(isoReporteFiltros.orden_id);
      const eventos = res.data?.event_log?.length || 0;
      toast.success(`Audit Pack OT cargado: ${eventos} eventos de auditoría`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cargar el Audit Pack de la OT');
    }
  };

  const handleGuardarQaConfig = async () => {
    if (!qaConfig) return;
    try {
      const res = await masterAPI.guardarQaConfig(qaConfig);
      setQaConfig(res.data);
      toast.success('Configuración QA guardada');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error guardando configuración QA');
    }
  };

  const handleEjecutarQaMuestreo = async () => {
    try {
      const res = await masterAPI.ejecutarQaMuestreo();
      setQaRunResult(res.data);
      toast.success(`Muestreo QA ejecutado: ${res.data.tam_muestra || 0} OT`);
      const kpisRes = await masterAPI.isoKpis();
      setIsoKpis(kpisRes.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error ejecutando muestreo QA');
    }
  };


  const filtrarFacturacion = async () => {
    try {
      const res = await masterAPI.facturacion({ 
        fecha_desde: fechaDesde, 
        fecha_hasta: fechaHasta 
      });
      setFacturacion(res.data);
      toast.success('Filtro aplicado');
    } catch (error) {
      toast.error('Error al filtrar');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const totalOrdenes = metricasTecnicos.reduce((acc, t) => acc + t.total_ordenes, 0);
  const totalCompletadas = metricasTecnicos.reduce((acc, t) => acc + t.completadas, 0);
  const totalGarantias = metricasTecnicos.reduce((acc, t) => acc + t.garantias, 0);

  return (
    <div className="space-y-6 animate-fade-in" data-testid="panel-master-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Crown className="w-8 h-8 text-yellow-500" />
            Panel Master
          </h1>
          <p className="text-muted-foreground mt-1">
            Control total de métricas, técnicos y facturación
          </p>
        </div>
      </div>

      {/* KPIs Globales */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-xl">
                <FileText className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Órdenes</p>
                <p className="text-2xl font-bold">{totalOrdenes}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-100 rounded-xl">
                <CheckCircle2 className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Completadas</p>
                <p className="text-2xl font-bold">{totalCompletadas}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-orange-100 rounded-xl">
                <Shield className="w-6 h-6 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Garantías</p>
                <p className="text-2xl font-bold">{totalGarantias}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-purple-100 rounded-xl">
                <Users className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Técnicos</p>
                <p className="text-2xl font-bold">{metricasTecnicos.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="tecnicos" className="space-y-4">
        <TabsList>
          <TabsTrigger value="tecnicos" data-testid="panel-master-tab-tecnicos">Métricas por Técnico</TabsTrigger>
          <TabsTrigger value="facturacion" data-testid="panel-master-tab-facturacion">Facturación</TabsTrigger>
          <TabsTrigger value="iso" data-testid="panel-master-tab-iso">ISO 9001</TabsTrigger>
        </TabsList>

        {/* Métricas por Técnico */}
        <TabsContent value="tecnicos" className="space-y-4">
          {metricasTecnicos.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Users className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No hay técnicos con órdenes asignadas</p>
              </CardContent>
            </Card>
          ) : (
            <>
              {/* Gráfico de barras */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Rendimiento por Técnico
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={metricasTecnicos} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" />
                        <YAxis dataKey="nombre" type="category" width={100} />
                        <Tooltip />
                        <Bar dataKey="completadas" name="Completadas" fill="#10b981" />
                        <Bar dataKey="en_proceso" name="En Proceso" fill="#667eea" />
                        <Bar dataKey="garantias" name="Garantías" fill="#f59e0b" />
                        <Bar dataKey="irreparables" name="Irreparables" fill="#ef4444" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              {/* Cards por técnico */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {metricasTecnicos.map((tecnico, index) => (
                  <Card key={tecnico.tecnico_id}>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="flex items-center gap-2">
                          <div 
                            className="w-3 h-3 rounded-full" 
                            style={{ backgroundColor: COLORS[index % COLORS.length] }}
                          />
                          {tecnico.nombre}
                        </CardTitle>
                        <Badge variant={tecnico.tasa_exito >= 80 ? 'default' : 'secondary'}>
                          {tecnico.tasa_exito}% éxito
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Tasa de éxito</span>
                          <span className="font-medium">{tecnico.tasa_exito}%</span>
                        </div>
                        <Progress value={tecnico.tasa_exito} className="h-2" />
                      </div>

                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div className="p-2 bg-slate-50 rounded-lg">
                          <p className="text-muted-foreground">Total</p>
                          <p className="font-bold text-lg">{tecnico.total_ordenes}</p>
                        </div>
                        <div className="p-2 bg-green-50 rounded-lg">
                          <p className="text-green-600">Completadas</p>
                          <p className="font-bold text-lg text-green-700">{tecnico.completadas}</p>
                        </div>
                        <div className="p-2 bg-blue-50 rounded-lg">
                          <p className="text-blue-600">En proceso</p>
                          <p className="font-bold text-lg text-blue-700">{tecnico.en_proceso}</p>
                        </div>
                        <div className="p-2 bg-orange-50 rounded-lg">
                          <p className="text-orange-600">Garantías</p>
                          <p className="font-bold text-lg text-orange-700">{tecnico.garantias}</p>
                        </div>
                        <div className="p-2 bg-red-50 rounded-lg col-span-2">
                          <p className="text-red-600">Irreparables</p>
                          <p className="font-bold text-lg text-red-700">{tecnico.irreparables}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </>
          )}
        </TabsContent>

        {/* Facturación */}
        <TabsContent value="facturacion" className="space-y-4">
          {/* Filtros de fecha */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="w-5 h-5" />
                Filtrar por Período
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4 items-end">
                <div>
                  <Label>Desde</Label>
                  <Input
                    type="date"
                    value={fechaDesde}
                    onChange={(e) => setFechaDesde(e.target.value)}
                  />
                </div>
                <div>
                  <Label>Hasta</Label>
                  <Input
                    type="date"
                    value={fechaHasta}
                    onChange={(e) => setFechaHasta(e.target.value)}
                  />
                </div>
                <Button onClick={filtrarFacturacion}>
                  Aplicar Filtro
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Resumen de facturación */}
          {facturacion && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Euro className="w-5 h-5 text-green-600" />
                  Resumen de Facturación
                </CardTitle>
                <CardDescription>
                  {facturacion.periodo.desde || facturacion.periodo.hasta 
                    ? `Período: ${facturacion.periodo.desde || 'Inicio'} - ${facturacion.periodo.hasta || 'Hoy'}`
                    : 'Total histórico'
                  }
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="text-center p-6 bg-gradient-to-br from-green-50 to-emerald-100 rounded-xl">
                  <p className="text-sm text-green-600 uppercase tracking-wider">Total Facturado</p>



                  <p className="text-5xl font-bold text-green-700 mt-2">
                    {facturacion.desglose.total.toLocaleString('es-ES', { 
                      style: 'currency', 
                      currency: 'EUR' 
                    })}
                  </p>
                  <p className="text-sm text-muted-foreground mt-2">
                    {facturacion.ordenes_facturadas} órdenes completadas
                  </p>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-slate-50 rounded-lg text-center">
                    <p className="text-sm text-muted-foreground">Materiales</p>
                    <p className="font-bold text-xl">
                      {facturacion.desglose.materiales.toLocaleString('es-ES', { 
                        style: 'currency', 
                        currency: 'EUR' 
                      })}
                    </p>
                  </div>
                  <div className="p-4 bg-slate-50 rounded-lg text-center">
                    <p className="text-sm text-muted-foreground">Mano de Obra</p>
                    <p className="font-bold text-xl">
                      {facturacion.desglose.mano_obra.toLocaleString('es-ES', { 
                        style: 'currency', 
                        currency: 'EUR' 
                      })}
                    </p>
                  </div>
                  <div className="p-4 bg-slate-50 rounded-lg text-center">
                    <p className="text-sm text-muted-foreground">Subtotal</p>
                    <p className="font-bold text-xl">
                      {facturacion.desglose.subtotal.toLocaleString('es-ES', { 
                        style: 'currency', 
                        currency: 'EUR' 
                      })}
                    </p>
                  </div>
                  <div className="p-4 bg-blue-50 rounded-lg text-center">
                    <p className="text-sm text-blue-600">IVA ({facturacion.desglose.iva_porcentaje}%)</p>
                    <p className="font-bold text-xl text-blue-700">
                      {facturacion.desglose.iva_importe.toLocaleString('es-ES', {
                        style: 'currency',
                        currency: 'EUR'
                      })}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>


        {/* ISO 9001 */}
        <TabsContent value="iso" className="space-y-4" data-testid="panel-master-iso-tab-content">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="w-5 h-5" />
                KPIs ISO 9001 (Auditoría)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                <div className="p-3 border rounded-lg"><p className="text-muted-foreground">% sin retrabajo</p><p className="text-xl font-bold">{isoKpis?.kpis?.reparaciones_sin_retrabajo_pct ?? '-'}%</p></div>
                <div className="p-3 border rounded-lg"><p className="text-muted-foreground">TAT promedio (h)</p><p className="text-xl font-bold">{isoKpis?.kpis?.tat_promedio_horas ?? '-'}</p></div>
                <div className="p-3 border rounded-lg"><p className="text-muted-foreground">% entregas a tiempo</p><p className="text-xl font-bold">{isoKpis?.kpis?.entregas_a_tiempo_pct ?? '-'}%</p></div>
                <div className="p-3 border rounded-lg"><p className="text-muted-foreground">Fallos QC</p><p className="text-xl font-bold">{isoKpis?.kpis?.qc_fallos ?? 0}</p></div>
                <div className="p-3 border rounded-lg"><p className="text-muted-foreground">FPY</p><p className="text-xl font-bold">{isoKpis?.kpis?.first_pass_yield_pct ?? '-'}%</p></div>
                <div className="p-3 border rounded-lg"><p className="text-muted-foreground">% garantías/devoluciones</p><p className="text-xl font-bold">{isoKpis?.kpis?.devoluciones_garantias_pct ?? '-'}%</p></div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="iso-capa-dashboard-card">
            <CardHeader>
              <CardTitle>Dashboard CAPA</CardTitle>
              <CardDescription>Abiertas por antigüedad, estado y causa.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-sm">
                <div className="p-3 border rounded-lg"><p className="text-muted-foreground">Total CAPA</p><p className="text-xl font-bold">{capaDashboard?.total_capas ?? 0}</p></div>
                <div className="p-3 border rounded-lg"><p className="text-muted-foreground">Abiertas</p><p className="text-xl font-bold">{(capaDashboard?.por_estado?.abierta || 0) + (capaDashboard?.por_estado?.en_curso || 0)}</p></div>
                <div className="p-3 border rounded-lg"><p className="text-muted-foreground">Antigüedad &gt;30d</p><p className="text-xl font-bold">{capaDashboard?.abiertas_antiguedad_30d ?? 0}</p></div>
                <div className="p-3 border rounded-lg"><p className="text-muted-foreground">Por recurrencia</p><p className="text-xl font-bold">{capaDashboard?.por_motivo?.recurrencia_30d ?? 0}</p></div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="iso-qa-config-card">
            <CardHeader>
              <CardTitle>QA por muestreo (AQL)</CardTitle>
              <CardDescription>Configurable (default 10%, mínimo 1). Si falla muestreo, escalar a 20% durante 7 días y abrir CAPA.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
                <div className="space-y-1">
                  <Label>% diario</Label>
                  <Input type="number" value={qaConfig?.porcentaje_diario ?? 10} onChange={(e) => setQaConfig({ ...(qaConfig || {}), porcentaje_diario: Number(e.target.value) })} data-testid="qa-config-porcentaje-input" />
                </div>
                <div className="space-y-1">
                  <Label>Mínimo muestras</Label>
                  <Input type="number" value={qaConfig?.minimo_muestras ?? 1} onChange={(e) => setQaConfig({ ...(qaConfig || {}), minimo_muestras: Number(e.target.value) })} data-testid="qa-config-minimo-input" />
                </div>
                <div className="space-y-1">
                  <Label>% escalado fallo</Label>
                  <Input type="number" value={qaConfig?.escalado_por_fallo_porcentaje ?? 20} onChange={(e) => setQaConfig({ ...(qaConfig || {}), escalado_por_fallo_porcentaje: Number(e.target.value) })} data-testid="qa-config-escalado-input" />
                </div>
                <div className="space-y-1">
                  <Label>Días escalado</Label>
                  <Input type="number" value={qaConfig?.escalado_dias ?? 7} onChange={(e) => setQaConfig({ ...(qaConfig || {}), escalado_dias: Number(e.target.value) })} data-testid="qa-config-dias-input" />
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={handleGuardarQaConfig} data-testid="qa-config-save-button">Guardar configuración QA</Button>
                <Button onClick={handleEjecutarQaMuestreo} data-testid="qa-muestreo-run-button">Ejecutar muestreo QA</Button>
              </div>
              {qaRunResult && (
                <div className="text-sm p-2 border rounded bg-muted/30" data-testid="qa-muestreo-result-box">
                  Muestreo ejecutado: {qaRunResult.tam_muestra || 0} de {qaRunResult.total_candidatas || 0} OT (porcentaje {qaRunResult.porcentaje_aplicado || '-'}%)
                </div>
              )}
            </CardContent>
          </Card>


          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>LMD - Información documentada</CardTitle>
                <CardDescription>Control documental mínimo ISO (código, versión, retención).</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <Input placeholder="Código (ej: DOC-SGC-001)" value={isoDocForm.codigo} onChange={(e) => setIsoDocForm({ ...isoDocForm, codigo: e.target.value.toUpperCase() })} data-testid="iso-doc-codigo-input" />
                  <Input placeholder="Título" value={isoDocForm.titulo} onChange={(e) => setIsoDocForm({ ...isoDocForm, titulo: e.target.value })} data-testid="iso-doc-titulo-input" />
                  <Input placeholder="Tipo: documento/registro" value={isoDocForm.tipo} onChange={(e) => setIsoDocForm({ ...isoDocForm, tipo: e.target.value })} data-testid="iso-doc-tipo-input" />
                  <Input placeholder="Versión" value={isoDocForm.version} onChange={(e) => setIsoDocForm({ ...isoDocForm, version: e.target.value })} data-testid="iso-doc-version-input" />
                </div>
                <Button onClick={handleGuardarIsoDocumento} data-testid="iso-doc-guardar-button">Guardar documento</Button>
                <Separator />
                <div className="space-y-2 max-h-52 overflow-y-auto" data-testid="iso-doc-list">
                  {isoDocumentos.map((doc) => (
                    <div key={doc.codigo} className="p-2 border rounded text-sm flex justify-between gap-2">
                      <div>
                        <p className="font-medium">{doc.codigo} - {doc.titulo}</p>
                        <p className="text-muted-foreground">{doc.tipo} v{doc.version} · retención {doc.retencion_anios} años</p>
                      </div>
                      <Badge variant="outline">{doc.estado || 'vigente'}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Proveedores críticos (ISO 8.4)</CardTitle>
                <CardDescription>Evaluación y reevaluación manual basada en desempeño.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <Input placeholder="Proveedor" value={isoProveedorForm.proveedor} onChange={(e) => setIsoProveedorForm({ ...isoProveedorForm, proveedor: e.target.value })} data-testid="iso-prov-nombre-input" />
                  <Input placeholder="Tipo" value={isoProveedorForm.tipo} onChange={(e) => setIsoProveedorForm({ ...isoProveedorForm, tipo: e.target.value })} data-testid="iso-prov-tipo-input" />
                  <Input type="number" placeholder="Puntualidad" value={isoProveedorForm.puntualidad} onChange={(e) => setIsoProveedorForm({ ...isoProveedorForm, puntualidad: Number(e.target.value) })} data-testid="iso-prov-puntualidad-input" />
                  <Input type="number" placeholder="Calidad" value={isoProveedorForm.calidad} onChange={(e) => setIsoProveedorForm({ ...isoProveedorForm, calidad: Number(e.target.value) })} data-testid="iso-prov-calidad-input" />
                  <Input type="number" placeholder="Respuesta" value={isoProveedorForm.respuesta} onChange={(e) => setIsoProveedorForm({ ...isoProveedorForm, respuesta: Number(e.target.value) })} data-testid="iso-prov-respuesta-input" />
                  <Input type="number" placeholder="Incidencias" value={isoProveedorForm.incidencias} onChange={(e) => setIsoProveedorForm({ ...isoProveedorForm, incidencias: Number(e.target.value) })} data-testid="iso-prov-incidencias-input" />
                </div>
                <Button onClick={handleEvaluarProveedorIso} data-testid="iso-prov-evaluar-button">Guardar evaluación</Button>
                <Separator />
                <div className="space-y-2 max-h-52 overflow-y-auto" data-testid="iso-proveedores-list">
                  {isoProveedores.map((p) => (
                    <div key={p.proveedor} className="p-2 border rounded text-sm flex justify-between gap-2">
                      <div>
                        <p className="font-medium">{p.proveedor}</p>
                        <p className="text-muted-foreground">score: {p.score ?? '-'} · incidencias: {p.incidencias ?? 0}</p>
                      </div>
                      <Badge variant="outline">{p.estado || 'pendiente'}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Download className="w-5 h-5" />Reporte exportable ISO (PDF)</CardTitle>
              <CardDescription>Manual, por OT o por rango de fechas (según tu elección).</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <Input placeholder="ID de OT (opcional)" value={isoReporteFiltros.orden_id} onChange={(e) => setIsoReporteFiltros({ ...isoReporteFiltros, orden_id: e.target.value })} data-testid="iso-reporte-orden-id-input" />
                <Input type="date" value={isoReporteFiltros.fecha_desde} onChange={(e) => setIsoReporteFiltros({ ...isoReporteFiltros, fecha_desde: e.target.value })} data-testid="iso-reporte-fecha-desde-input" />
                <Input type="date" value={isoReporteFiltros.fecha_hasta} onChange={(e) => setIsoReporteFiltros({ ...isoReporteFiltros, fecha_hasta: e.target.value })} data-testid="iso-reporte-fecha-hasta-input" />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button onClick={handleDescargarReporteIso} data-testid="iso-reporte-descargar-pdf-button">Descargar reporte PDF</Button>
                <Button variant="outline" onClick={handleDescargarAuditPackCsv} data-testid="iso-audit-pack-descargar-csv-button">Descargar Audit Pack CSV</Button>
                <Button variant="secondary" onClick={handleAbrirAuditPackOt} data-testid="iso-audit-pack-ot-button">Validar Audit Pack OT</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

      </Tabs>
    </div>
  );
}

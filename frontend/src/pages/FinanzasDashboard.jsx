/**
 * Dashboard de Finanzas Centralizado - Revix CRM v1.2.0
 * Hub financiero unificado: ingresos, gastos, facturas, inventario, contabilidad
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { 
  TrendingUp, TrendingDown, DollarSign, Package, ShoppingCart, 
  FileText, ArrowUpRight, ArrowDownRight, RefreshCw, Calendar,
  BarChart3, Wallet, AlertTriangle, Receipt, Eye, CheckCircle, Clock,
  CreditCard, ArrowRight
} from 'lucide-react';
import { finanzasAPI, contabilidadAPI } from '@/lib/api';
import { toast } from 'sonner';

export default function FinanzasDashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [periodo, setPeriodo] = useState('mes');
  const [dashboard, setDashboard] = useState(null);
  const [evolucion, setEvolucion] = useState(null);
  const [inventario, setInventario] = useState(null);
  const [gastos, setGastos] = useState(null);
  const [facturas, setFacturas] = useState([]);
  const [contaStats, setContaStats] = useState(null);
  const [pendientes, setPendientes] = useState(null);

  const cargarDatos = useCallback(async () => {
    setLoading(true);
    try {
      const [dashRes, evoRes, invRes, gastosRes, facturasRes, statsRes, pendRes] = await Promise.all([
        finanzasAPI.getDashboard(periodo),
        finanzasAPI.getEvolucion(6),
        finanzasAPI.getValorInventario(),
        finanzasAPI.getDetalleGastos(periodo),
        contabilidadAPI.listarFacturas({ page_size: 15 }),
        contabilidadAPI.stats(),
        contabilidadAPI.pendientes()
      ]);
      setDashboard(dashRes.data);
      setEvolucion(evoRes.data);
      setInventario(invRes.data);
      setGastos(gastosRes.data);
      setFacturas(facturasRes.data?.items || []);
      setContaStats(statsRes.data);
      setPendientes(pendRes.data);
    } catch (error) {
      console.error('Error cargando datos:', error);
      toast.error('Error cargando datos financieros');
    } finally {
      setLoading(false);
    }
  }, [periodo]);

  useEffect(() => { cargarDatos(); }, [cargarDatos]);

  const fmt = (v) => new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(v || 0);
  const fmtPct = (v) => `${(v || 0).toFixed(1)}%`;

  const estadoBadge = (estado) => {
    const map = {
      borrador: { label: 'Borrador', variant: 'secondary' },
      emitida: { label: 'Emitida', variant: 'default' },
      pagada: { label: 'Pagada', variant: 'outline', className: 'bg-green-50 text-green-700 border-green-200' },
      parcial: { label: 'Parcial', variant: 'outline', className: 'bg-amber-50 text-amber-700 border-amber-200' },
      vencida: { label: 'Vencida', variant: 'destructive' },
      anulada: { label: 'Anulada', variant: 'outline', className: 'bg-gray-50 text-gray-500' },
    };
    const cfg = map[estado] || { label: estado, variant: 'secondary' };
    return <Badge variant={cfg.variant} className={`text-[10px] ${cfg.className || ''}`}>{cfg.label}</Badge>;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const resumen = dashboard?.resumen || {};
  const ingresos = dashboard?.ingresos || {};
  const gastosInfo = dashboard?.gastos || {};
  const inv = dashboard?.inventario || {};
  const kpis = dashboard?.kpis_ordenes || {};

  return (
    <div className="space-y-6" data-testid="finanzas-dashboard">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Finanzas</h1>
          <p className="text-muted-foreground text-sm">
            Control centralizado de ingresos, gastos, facturas e inventario
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={periodo} onValueChange={setPeriodo}>
            <SelectTrigger className="w-[140px]" data-testid="periodo-selector">
              <Calendar className="w-4 h-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="dia">Hoy</SelectItem>
              <SelectItem value="semana">Esta semana</SelectItem>
              <SelectItem value="mes">Este mes</SelectItem>
              <SelectItem value="trimestre">Trimestre</SelectItem>
              <SelectItem value="año">Este año</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" onClick={cargarDatos} data-testid="refresh-btn">
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* KPIs de Órdenes (globales) */}
      <div>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">KPIs Operativos (Global)</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
          <Card data-testid="kpi-ordenes-totales">
            <CardContent className="pt-3 pb-3">
              <p className="text-xs text-muted-foreground">Órdenes Totales</p>
              <p className="text-xl font-bold">{kpis.ordenes_totales || 0}</p>
            </CardContent>
          </Card>
          <Card data-testid="kpi-ordenes-pendientes">
            <CardContent className="pt-3 pb-3">
              <p className="text-xs text-muted-foreground">Pendientes</p>
              <p className="text-xl font-bold text-amber-600">{kpis.ordenes_pendientes || 0}</p>
            </CardContent>
          </Card>
          <Card data-testid="kpi-ordenes-enviadas">
            <CardContent className="pt-3 pb-3">
              <p className="text-xs text-muted-foreground">Enviadas</p>
              <p className="text-xl font-bold text-green-600">{kpis.ordenes_enviadas || 0}</p>
            </CardContent>
          </Card>
          <Card data-testid="kpi-valor-pendientes">
            <CardContent className="pt-3 pb-3">
              <p className="text-xs text-muted-foreground">Valor Pendientes</p>
              <p className="text-lg font-bold text-amber-600">{fmt(kpis.valor_pendientes)}</p>
            </CardContent>
          </Card>
          <Card data-testid="kpi-valor-enviadas">
            <CardContent className="pt-3 pb-3">
              <p className="text-xs text-muted-foreground">Valor Enviadas</p>
              <p className="text-lg font-bold text-green-600">{fmt(kpis.valor_enviadas)}</p>
            </CardContent>
          </Card>
          <Card data-testid="kpi-coste-promedio">
            <CardContent className="pt-3 pb-3">
              <p className="text-xs text-muted-foreground">Coste Medio/Orden</p>
              <p className="text-lg font-bold text-red-500">{fmt(kpis.coste_promedio_orden)}</p>
            </CardContent>
          </Card>
          <Card data-testid="kpi-ticket-medio">
            <CardContent className="pt-3 pb-3">
              <p className="text-xs text-muted-foreground">Ticket Medio</p>
              <p className="text-lg font-bold text-blue-600">{fmt(kpis.ticket_medio)}</p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* KPI Cards (periodo) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card data-testid="kpi-ingresos">
          <CardContent className="pt-4">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-muted-foreground">Ingresos</p>
                <p className="text-2xl font-bold text-green-600">{fmt(resumen.total_ingresos)}</p>
              </div>
              <div className="p-2 bg-green-100 rounded-full"><TrendingUp className="w-5 h-5 text-green-600" /></div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {ingresos.ordenes_enviadas?.cantidad || 0} órdenes completadas
            </p>
          </CardContent>
        </Card>
        <Card data-testid="kpi-gastos">
          <CardContent className="pt-4">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-muted-foreground">Gastos</p>
                <p className="text-2xl font-bold text-red-600">{fmt(resumen.total_gastos)}</p>
              </div>
              <div className="p-2 bg-red-100 rounded-full"><TrendingDown className="w-5 h-5 text-red-600" /></div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {gastosInfo.compras?.cantidad || 0} compras registradas
            </p>
          </CardContent>
        </Card>
        <Card data-testid="kpi-beneficio">
          <CardContent className="pt-4">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-muted-foreground">Beneficio</p>
                <p className={`text-2xl font-bold ${resumen.beneficio_bruto >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                  {fmt(resumen.beneficio_bruto)}
                </p>
              </div>
              <div className={`p-2 rounded-full ${resumen.beneficio_bruto >= 0 ? 'bg-blue-100' : 'bg-red-100'}`}>
                <Wallet className={`w-5 h-5 ${resumen.beneficio_bruto >= 0 ? 'text-blue-600' : 'text-red-600'}`} />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">Margen: {fmtPct(resumen.margen_porcentaje)}</p>
          </CardContent>
        </Card>
        <Card data-testid="kpi-inventario">
          <CardContent className="pt-4">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-muted-foreground">Inventario</p>
                <p className="text-2xl font-bold text-violet-600">{fmt(inv.valor_coste)}</p>
              </div>
              <div className="p-2 bg-violet-100 rounded-full"><Package className="w-5 h-5 text-violet-600" /></div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">{inv.unidades_totales || 0} unidades en stock</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="resumen" className="space-y-4">
        <TabsList className="flex-wrap">
          <TabsTrigger value="resumen" data-testid="tab-resumen">Resumen</TabsTrigger>
          <TabsTrigger value="facturas" data-testid="tab-facturas">Facturas</TabsTrigger>
          <TabsTrigger value="cobros" data-testid="tab-cobros">Cobros y Pagos</TabsTrigger>
          <TabsTrigger value="gastos" data-testid="tab-gastos">Gastos</TabsTrigger>
          <TabsTrigger value="inventario" data-testid="tab-inventario">Inventario</TabsTrigger>
          <TabsTrigger value="evolucion" data-testid="tab-evolucion">Evolución</TabsTrigger>
        </TabsList>

        {/* === RESUMEN === */}
        <TabsContent value="resumen" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <ArrowUpRight className="w-4 h-4 text-green-500" />
                  Ingresos Pendientes
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Órdenes en proceso</span>
                    <span className="font-medium">{ingresos.pendientes?.ordenes_en_proceso || 0}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Ingresos estimados</span>
                    <span className="font-medium text-green-600">{fmt(ingresos.pendientes?.ingresos_estimados)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Pendiente de cobro</span>
                    <span className="font-medium text-amber-600">{fmt(ingresos.facturas_venta?.pendiente_cobro)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <ArrowDownRight className="w-4 h-4 text-red-500" />
                  Desglose de Gastos
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Compras</span>
                    <span className="font-medium">{fmt(gastosInfo.compras?.total)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Materiales usados</span>
                    <span className="font-medium">{fmt(gastosInfo.materiales_usados?.total)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Mano de obra</span>
                    <span className="font-medium">{fmt(gastosInfo.mano_obra?.total)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
          {/* Contabilidad stats */}
          {contaStats && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Card>
                <CardContent className="pt-3 pb-3 text-center">
                  <p className="text-xl font-bold">{contaStats.facturas_venta || 0}</p>
                  <p className="text-xs text-muted-foreground">Facturas venta</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-3 pb-3 text-center">
                  <p className="text-xl font-bold">{contaStats.facturas_compra || 0}</p>
                  <p className="text-xs text-muted-foreground">Facturas compra</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-3 pb-3 text-center">
                  <p className="text-xl font-bold text-amber-600">{fmt(contaStats.pendiente_cobro)}</p>
                  <p className="text-xs text-muted-foreground">Pendiente cobro</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-3 pb-3 text-center">
                  <p className="text-xl font-bold">{contaStats.albaranes_sin_facturar || 0}</p>
                  <p className="text-xs text-muted-foreground">Albaranes s/facturar</p>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        {/* === FACTURAS === */}
        <TabsContent value="facturas" className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex justify-between items-center">
                <CardTitle className="text-base">Últimas Facturas</CardTitle>
                <Button size="sm" variant="outline" onClick={() => navigate('/crm/contabilidad')} data-testid="ver-contabilidad-btn">
                  Ver contabilidad completa <ArrowRight className="w-3 h-3 ml-1" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {facturas.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No hay facturas registradas</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="p-2">Número</th>
                        <th className="p-2">Tipo</th>
                        <th className="p-2">Cliente/Proveedor</th>
                        <th className="p-2 text-right">Total</th>
                        <th className="p-2 text-right">Pendiente</th>
                        <th className="p-2">Estado</th>
                        <th className="p-2">Auto</th>
                      </tr>
                    </thead>
                    <tbody>
                      {facturas.map((f) => (
                        <tr key={f.id} className="border-b hover:bg-muted/50 cursor-pointer"
                            onClick={() => navigate(`/crm/contabilidad/factura/${f.id}`)}
                            data-testid={`factura-row-${f.id}`}>
                          <td className="p-2 font-medium">{f.numero}</td>
                          <td className="p-2">
                            <Badge variant={f.tipo === 'venta' ? 'default' : 'secondary'} className="text-[10px]">
                              {f.tipo === 'venta' ? 'Venta' : 'Compra'}
                            </Badge>
                          </td>
                          <td className="p-2 truncate max-w-[180px]">
                            {f.nombre_fiscal || f.cliente_nombre || f.proveedor_nombre || '-'}
                          </td>
                          <td className="p-2 text-right font-medium">{fmt(f.total)}</td>
                          <td className="p-2 text-right text-amber-600">
                            {f.pendiente_cobro > 0 ? fmt(f.pendiente_cobro) : '-'}
                          </td>
                          <td className="p-2">{estadoBadge(f.estado)}</td>
                          <td className="p-2">
                            {f.generada_automaticamente && (
                              <Badge variant="outline" className="text-[9px] bg-blue-50 text-blue-600 border-blue-200">Auto</Badge>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* === COBROS Y PAGOS === */}
        <TabsContent value="cobros" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <ArrowUpRight className="w-4 h-4 text-green-500" />
                  Pendiente de Cobro ({pendientes?.pendiente_cobro?.num_facturas || 0})
                </CardTitle>
                <CardDescription>Total: {fmt(pendientes?.pendiente_cobro?.total)}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-[350px] overflow-y-auto">
                  {(pendientes?.pendiente_cobro?.facturas || []).length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">Sin facturas pendientes de cobro</p>
                  ) : (
                    (pendientes?.pendiente_cobro?.facturas || []).map((f) => (
                      <div key={f.id} className="flex justify-between items-center p-2 bg-muted/50 rounded hover:bg-muted cursor-pointer"
                           onClick={() => navigate(`/crm/contabilidad/factura/${f.id}`)}>
                        <div>
                          <span className="text-sm font-medium">{f.numero}</span>
                          <span className="text-xs text-muted-foreground ml-2">{f.nombre_fiscal}</span>
                        </div>
                        <div className="text-right">
                          <span className="font-medium text-amber-600">{fmt(f.pendiente_cobro)}</span>
                          {f.estado === 'vencida' && (
                            <Badge variant="destructive" className="text-[9px] ml-1">Vencida</Badge>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <ArrowDownRight className="w-4 h-4 text-red-500" />
                  Pendiente de Pago ({pendientes?.pendiente_pago?.num_facturas || 0})
                </CardTitle>
                <CardDescription>Total: {fmt(pendientes?.pendiente_pago?.total)}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-[350px] overflow-y-auto">
                  {(pendientes?.pendiente_pago?.facturas || []).length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">Sin facturas pendientes de pago</p>
                  ) : (
                    (pendientes?.pendiente_pago?.facturas || []).map((f) => (
                      <div key={f.id} className="flex justify-between items-center p-2 bg-muted/50 rounded hover:bg-muted cursor-pointer"
                           onClick={() => navigate(`/crm/contabilidad/factura/${f.id}`)}>
                        <div>
                          <span className="text-sm font-medium">{f.numero}</span>
                          <span className="text-xs text-muted-foreground ml-2">{f.nombre_fiscal}</span>
                        </div>
                        <span className="font-medium text-red-600">{fmt(f.pendiente_cobro)}</span>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
          {pendientes && (
            <Card>
              <CardContent className="pt-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Balance neto (cobrar - pagar)</span>
                  <span className={`text-lg font-bold ${(pendientes.balance || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {fmt(pendientes.balance)}
                  </span>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* === GASTOS === */}
        <TabsContent value="gastos">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader><CardTitle className="text-base">Por Proveedor</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {(gastos?.compras_por_proveedor || []).slice(0, 8).map((prov, idx) => (
                    <div key={idx} className="flex justify-between items-center p-2 bg-muted/50 rounded">
                      <span className="text-sm truncate max-w-[200px]">{prov.proveedor}</span>
                      <div className="text-right">
                        <span className="font-medium">{fmt(prov.total)}</span>
                        <span className="text-xs text-muted-foreground ml-2">({prov.cantidad})</span>
                      </div>
                    </div>
                  ))}
                  {(gastos?.compras_por_proveedor || []).length === 0 && (
                    <p className="text-sm text-muted-foreground text-center py-4">Sin compras en este periodo</p>
                  )}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Top Materiales Consumidos</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {(gastos?.top_materiales_consumidos || []).slice(0, 8).map((mat, idx) => (
                    <div key={idx} className="flex justify-between items-center p-2 bg-muted/50 rounded">
                      <span className="text-sm truncate max-w-[200px]">{mat.nombre}</span>
                      <div className="text-right">
                        <span className="font-medium">{fmt(mat.coste_total)}</span>
                        <span className="text-xs text-muted-foreground ml-2">x{mat.cantidad}</span>
                      </div>
                    </div>
                  ))}
                  {(gastos?.top_materiales_consumidos || []).length === 0 && (
                    <p className="text-sm text-muted-foreground text-center py-4">Sin datos de consumo</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* === INVENTARIO === */}
        <TabsContent value="inventario">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card className="lg:col-span-1">
              <CardHeader><CardTitle className="text-base">Resumen Inventario</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Referencias con stock</span>
                  <span className="font-medium">{inventario?.resumen?.con_stock || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Unidades totales</span>
                  <span className="font-medium">{inventario?.resumen?.unidades_totales || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Valor a coste</span>
                  <span className="font-medium">{fmt(inventario?.resumen?.valor_coste)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Valor a PVP</span>
                  <span className="font-medium">{fmt(inventario?.resumen?.valor_venta)}</span>
                </div>
                <div className="pt-2 border-t">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Margen potencial</span>
                    <span className="font-bold text-green-600">{fmt(inventario?.resumen?.margen_potencial)}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {fmtPct(inventario?.resumen?.margen_porcentaje)} sobre coste
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card className="lg:col-span-2">
              <CardHeader><CardTitle className="text-base">Por Categoría</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {(inventario?.por_categoria || []).map((cat, idx) => (
                    <div key={idx} className="flex justify-between items-center p-2 bg-muted/50 rounded">
                      <div>
                        <span className="text-sm font-medium">{cat.categoria}</span>
                        <span className="text-xs text-muted-foreground ml-2">({cat.items} refs, {cat.unidades} uds)</span>
                      </div>
                      <span className="font-medium">{fmt(cat.valor_coste)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* === EVOLUCIÓN === */}
        <TabsContent value="evolucion">
          <Card>
            <CardHeader>
              <CardTitle>Evolución Mensual</CardTitle>
              <CardDescription>Últimos 6 meses de actividad</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">Mes</th>
                      <th className="text-right p-2">Ingresos</th>
                      <th className="text-right p-2">Gastos</th>
                      <th className="text-right p-2">Beneficio</th>
                      <th className="text-right p-2">Órdenes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(evolucion?.datos || []).map((mes, idx) => (
                      <tr key={idx} className="border-b hover:bg-muted/50">
                        <td className="p-2 font-medium">{mes.nombre_mes}</td>
                        <td className="p-2 text-right text-green-600">{fmt(mes.ingresos)}</td>
                        <td className="p-2 text-right text-red-600">{fmt(mes.gastos)}</td>
                        <td className={`p-2 text-right font-medium ${mes.beneficio >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                          {fmt(mes.beneficio)}
                        </td>
                        <td className="p-2 text-right">{mes.ordenes_enviadas}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-muted/30">
                    <tr>
                      <td className="p-2 font-bold">TOTAL</td>
                      <td className="p-2 text-right font-bold text-green-600">{fmt(evolucion?.totales?.ingresos)}</td>
                      <td className="p-2 text-right font-bold text-red-600">{fmt(evolucion?.totales?.gastos)}</td>
                      <td className={`p-2 text-right font-bold ${(evolucion?.totales?.beneficio || 0) >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                        {fmt(evolucion?.totales?.beneficio)}
                      </td>
                      <td className="p-2 text-right">-</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

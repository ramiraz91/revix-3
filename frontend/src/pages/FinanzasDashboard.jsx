/**
 * Dashboard de Finanzas Centralizado - Revix CRM v1.1.0
 * =====================================================
 * Este dashboard muestra toda la información financiera:
 * - Ingresos de órdenes
 * - Gastos de compras
 * - Valor del inventario
 * - Balance y evolución
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { 
  TrendingUp, TrendingDown, DollarSign, Package, ShoppingCart, 
  FileText, ArrowUpRight, ArrowDownRight, RefreshCw, Calendar,
  PieChart, BarChart3, Wallet, AlertTriangle
} from 'lucide-react';
import { finanzasAPI } from '@/lib/api';
import { toast } from 'sonner';

export default function FinanzasDashboard() {
  const [loading, setLoading] = useState(true);
  const [periodo, setPeriodo] = useState('mes');
  const [dashboard, setDashboard] = useState(null);
  const [evolucion, setEvolucion] = useState(null);
  const [inventario, setInventario] = useState(null);
  const [gastos, setGastos] = useState(null);

  const cargarDatos = async () => {
    setLoading(true);
    try {
      const [dashData, evoData, invData, gastosData] = await Promise.all([
        finanzasAPI.getDashboard(periodo),
        finanzasAPI.getEvolucion(6),
        finanzasAPI.getValorInventario(),
        finanzasAPI.getDetalleGastos(periodo)
      ]);
      setDashboard(dashData);
      setEvolucion(evoData);
      setInventario(invData);
      setGastos(gastosData);
    } catch (error) {
      console.error('Error cargando datos:', error);
      toast.error('Error cargando datos financieros');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarDatos();
  }, [periodo]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(value || 0);
  };

  const formatPercent = (value) => {
    return `${(value || 0).toFixed(1)}%`;
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-screen">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const resumen = dashboard?.resumen || {};
  const ingresos = dashboard?.ingresos || {};
  const gastosData = dashboard?.gastos || {};
  const inv = dashboard?.inventario || {};

  return (
    <div className="p-6 space-y-6" data-testid="finanzas-dashboard">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold">Dashboard Financiero</h1>
          <p className="text-muted-foreground text-sm">
            Control centralizado de ingresos, gastos e inventario
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={periodo} onValueChange={setPeriodo}>
            <SelectTrigger className="w-[140px]">
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
          <Button variant="outline" size="icon" onClick={cargarDatos}>
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Tarjetas resumen */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Ingresos */}
        <Card className="border-l-4 border-l-green-500">
          <CardContent className="pt-4">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-muted-foreground">Ingresos</p>
                <p className="text-2xl font-bold text-green-600">
                  {formatCurrency(resumen.total_ingresos)}
                </p>
              </div>
              <div className="p-2 bg-green-100 rounded-full">
                <TrendingUp className="w-5 h-5 text-green-600" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {ingresos.ordenes_enviadas?.cantidad || 0} órdenes completadas
            </p>
          </CardContent>
        </Card>

        {/* Gastos */}
        <Card className="border-l-4 border-l-red-500">
          <CardContent className="pt-4">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-muted-foreground">Gastos</p>
                <p className="text-2xl font-bold text-red-600">
                  {formatCurrency(resumen.total_gastos)}
                </p>
              </div>
              <div className="p-2 bg-red-100 rounded-full">
                <TrendingDown className="w-5 h-5 text-red-600" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {gastosData.compras?.cantidad || 0} compras registradas
            </p>
          </CardContent>
        </Card>

        {/* Beneficio */}
        <Card className="border-l-4 border-l-blue-500">
          <CardContent className="pt-4">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-muted-foreground">Beneficio</p>
                <p className={`text-2xl font-bold ${resumen.beneficio_bruto >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                  {formatCurrency(resumen.beneficio_bruto)}
                </p>
              </div>
              <div className={`p-2 rounded-full ${resumen.beneficio_bruto >= 0 ? 'bg-blue-100' : 'bg-red-100'}`}>
                <Wallet className={`w-5 h-5 ${resumen.beneficio_bruto >= 0 ? 'text-blue-600' : 'text-red-600'}`} />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Margen: {formatPercent(resumen.margen_porcentaje)}
            </p>
          </CardContent>
        </Card>

        {/* Inventario */}
        <Card className="border-l-4 border-l-purple-500">
          <CardContent className="pt-4">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-muted-foreground">Inventario</p>
                <p className="text-2xl font-bold text-purple-600">
                  {formatCurrency(inv.valor_coste)}
                </p>
              </div>
              <div className="p-2 bg-purple-100 rounded-full">
                <Package className="w-5 h-5 text-purple-600" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {inv.unidades_totales || 0} unidades en stock
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs de detalle */}
      <Tabs defaultValue="resumen" className="space-y-4">
        <TabsList>
          <TabsTrigger value="resumen">Resumen</TabsTrigger>
          <TabsTrigger value="ingresos">Ingresos</TabsTrigger>
          <TabsTrigger value="gastos">Gastos</TabsTrigger>
          <TabsTrigger value="inventario">Inventario</TabsTrigger>
          <TabsTrigger value="evolucion">Evolución</TabsTrigger>
        </TabsList>

        {/* Tab Resumen */}
        <TabsContent value="resumen" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Ingresos pendientes */}
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
                    <span className="font-medium text-green-600">
                      {formatCurrency(ingresos.pendientes?.ingresos_estimados)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Pendiente de cobro</span>
                    <span className="font-medium text-amber-600">
                      {formatCurrency(ingresos.facturas_venta?.pendiente_cobro)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Desglose de gastos */}
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
                    <span className="font-medium">{formatCurrency(gastosData.compras?.total)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Materiales usados</span>
                    <span className="font-medium">{formatCurrency(gastosData.materiales_usados?.total)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Mano de obra</span>
                    <span className="font-medium">{formatCurrency(gastosData.mano_obra?.total)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab Ingresos */}
        <TabsContent value="ingresos">
          <Card>
            <CardHeader>
              <CardTitle>Detalle de Ingresos</CardTitle>
              <CardDescription>Órdenes completadas y facturas emitidas</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <p className="text-3xl font-bold text-green-600">
                    {ingresos.ordenes_enviadas?.cantidad || 0}
                  </p>
                  <p className="text-sm text-muted-foreground">Órdenes enviadas</p>
                  <p className="text-lg font-semibold mt-2">
                    {formatCurrency(ingresos.ordenes_enviadas?.total)}
                  </p>
                </div>
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <p className="text-3xl font-bold text-blue-600">
                    {ingresos.facturas_venta?.cantidad || 0}
                  </p>
                  <p className="text-sm text-muted-foreground">Facturas emitidas</p>
                  <p className="text-lg font-semibold mt-2">
                    {formatCurrency(ingresos.facturas_venta?.total)}
                  </p>
                </div>
                <div className="text-center p-4 bg-amber-50 rounded-lg">
                  <p className="text-3xl font-bold text-amber-600">
                    {ingresos.pendientes?.ordenes_en_proceso || 0}
                  </p>
                  <p className="text-sm text-muted-foreground">En proceso</p>
                  <p className="text-lg font-semibold mt-2">
                    {formatCurrency(ingresos.pendientes?.ingresos_estimados)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab Gastos */}
        <TabsContent value="gastos">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Por Proveedor</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {(gastos?.compras_por_proveedor || []).slice(0, 5).map((prov, idx) => (
                    <div key={idx} className="flex justify-between items-center p-2 bg-muted/50 rounded">
                      <span className="text-sm">{prov.proveedor}</span>
                      <div className="text-right">
                        <span className="font-medium">{formatCurrency(prov.total)}</span>
                        <span className="text-xs text-muted-foreground ml-2">({prov.cantidad})</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Top Materiales Consumidos</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {(gastos?.top_materiales_consumidos || []).slice(0, 5).map((mat, idx) => (
                    <div key={idx} className="flex justify-between items-center p-2 bg-muted/50 rounded">
                      <span className="text-sm truncate max-w-[200px]">{mat.nombre}</span>
                      <div className="text-right">
                        <span className="font-medium">{formatCurrency(mat.coste_total)}</span>
                        <span className="text-xs text-muted-foreground ml-2">x{mat.cantidad}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab Inventario */}
        <TabsContent value="inventario">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card className="lg:col-span-1">
              <CardHeader>
                <CardTitle className="text-base">Resumen Inventario</CardTitle>
              </CardHeader>
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
                  <span className="font-medium">{formatCurrency(inventario?.resumen?.valor_coste)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Valor a PVP</span>
                  <span className="font-medium">{formatCurrency(inventario?.resumen?.valor_venta)}</span>
                </div>
                <div className="pt-2 border-t">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Margen potencial</span>
                    <span className="font-bold text-green-600">
                      {formatCurrency(inventario?.resumen?.margen_potencial)}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {formatPercent(inventario?.resumen?.margen_porcentaje)} sobre coste
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-base">Por Categoría</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {(inventario?.por_categoria || []).map((cat, idx) => (
                    <div key={idx} className="flex justify-between items-center p-2 bg-muted/50 rounded">
                      <div>
                        <span className="text-sm font-medium">{cat.categoria}</span>
                        <span className="text-xs text-muted-foreground ml-2">
                          ({cat.items} refs, {cat.unidades} uds)
                        </span>
                      </div>
                      <span className="font-medium">{formatCurrency(cat.valor_coste)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab Evolución */}
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
                        <td className="p-2 text-right text-green-600">{formatCurrency(mes.ingresos)}</td>
                        <td className="p-2 text-right text-red-600">{formatCurrency(mes.gastos)}</td>
                        <td className={`p-2 text-right font-medium ${mes.beneficio >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                          {formatCurrency(mes.beneficio)}
                        </td>
                        <td className="p-2 text-right">{mes.ordenes_enviadas}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-muted/30">
                    <tr>
                      <td className="p-2 font-bold">TOTAL</td>
                      <td className="p-2 text-right font-bold text-green-600">
                        {formatCurrency(evolucion?.totales?.ingresos)}
                      </td>
                      <td className="p-2 text-right font-bold text-red-600">
                        {formatCurrency(evolucion?.totales?.gastos)}
                      </td>
                      <td className={`p-2 text-right font-bold ${(evolucion?.totales?.beneficio || 0) >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                        {formatCurrency(evolucion?.totales?.beneficio)}
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

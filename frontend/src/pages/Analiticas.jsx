import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart3, TrendingUp, Clock, Users, Trophy, PieChart, DollarSign, Wallet, CreditCard, TrendingDown, ArrowUpRight, ArrowDownRight } from 'lucide-react';
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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
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
    fetchData();
  }, []);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" /></div>;
  if (!data) return <div className="text-center py-8 text-muted-foreground">Error cargando analíticas</div>;

  const maxIngresos = Math.max(...Object.values(data.ingresos_por_mes || {}), 1);
  const maxOrdenes = Math.max(...Object.values(data.ordenes_por_mes || {}), 1);
  const totalEstado = Object.values(data.distribucion_estado || {}).reduce((a, b) => a + b, 0);
  const finanzas = data.finanzas || {};

  return (
    <div className="space-y-6" data-testid="analiticas-page">
      <div>
        <h1 className="text-2xl font-bold">Analíticas</h1>
        <p className="text-muted-foreground">Panel de rendimiento del negocio</p>
      </div>

      {/* Panel Financiero */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-l-4 border-l-green-500">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Cobrado</p>
                <p className="text-2xl font-bold text-green-600">{finanzas.total_cobrado?.toLocaleString('es-ES', { minimumFractionDigits: 2 })} €</p>
                <p className="text-xs text-muted-foreground mt-1">De órdenes cerradas</p>
              </div>
              <div className="p-3 bg-green-100 rounded-full">
                <DollarSign className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-l-4 border-l-red-500">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Gastos</p>
                <p className="text-2xl font-bold text-red-600">{finanzas.total_gastos?.toLocaleString('es-ES', { minimumFractionDigits: 2 })} €</p>
                <p className="text-xs text-muted-foreground mt-1">Coste de materiales</p>
              </div>
              <div className="p-3 bg-red-100 rounded-full">
                <TrendingDown className="w-6 h-6 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-l-4 border-l-amber-500">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pendiente Cobrar</p>
                <p className="text-2xl font-bold text-amber-600">{finanzas.pendiente_cobrar?.toLocaleString('es-ES', { minimumFractionDigits: 2 })} €</p>
                <p className="text-xs text-muted-foreground mt-1">Órdenes completadas sin cerrar</p>
              </div>
              <div className="p-3 bg-amber-100 rounded-full">
                <Wallet className="w-6 h-6 text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-l-4 border-l-blue-500">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Margen Beneficio</p>
                <p className={`text-2xl font-bold ${finanzas.margen_beneficio >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                  {finanzas.margen_beneficio?.toLocaleString('es-ES', { minimumFractionDigits: 2 })} €
                </p>
                <div className="flex items-center gap-1 mt-1">
                  {finanzas.porcentaje_margen >= 0 ? (
                    <ArrowUpRight className="w-3 h-3 text-green-500" />
                  ) : (
                    <ArrowDownRight className="w-3 h-3 text-red-500" />
                  )}
                  <p className={`text-xs ${finanzas.porcentaje_margen >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {finanzas.porcentaje_margen}% margen
                  </p>
                </div>
              </div>
              <div className="p-3 bg-blue-100 rounded-full">
                <CreditCard className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

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
    </div>
  );
}

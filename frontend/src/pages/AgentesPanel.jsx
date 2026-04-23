import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bot, Pause, Play, MessageSquare, Eye, AlertTriangle, Activity,
  Clock, CheckCircle2, XCircle, TrendingUp, Loader2, RefreshCw, Sparkles,
  Calendar, ShieldCheck, Save, Users,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription,
} from '@/components/ui/sheet';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import API from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';

const ESTADO_BADGE = {
  activo: { label: 'ACTIVO', className: 'bg-green-100 text-green-800 border-green-300' },
  pausado: { label: 'PAUSADO', className: 'bg-amber-100 text-amber-800 border-amber-300' },
  error: { label: 'ERROR', className: 'bg-red-100 text-red-800 border-red-300' },
};

function timeAgo(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return 'hace un instante';
  if (diff < 3600) return `hace ${Math.round(diff / 60)}min`;
  if (diff < 86400) return `hace ${Math.round(diff / 3600)}h`;
  return `hace ${Math.round(diff / 86400)}d`;
}

export default function AgentesPanel() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [showWizard, setShowWizard] = useState(false);

  const isMaster = user?.role === 'master' || user?.role === 'admin' || user?.rol === 'master' || user?.rol === 'admin';

  const load = useCallback(async () => {
    try {
      const { data } = await API.get('/agents/panel/overview');
      setOverview(data);
    } catch {
      toast.error('Error cargando panel de agentes');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  // Auto-refresh cada 60s
  useEffect(() => {
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, [load]);

  const handleToggleState = async (agent) => {
    try {
      const endpoint = agent.estado === 'pausado' ? 'activate' : 'pause';
      await API.post(`/agents/${agent.agent_id}/${endpoint}`);
      toast.success(`Agente ${agent.nombre} ${endpoint === 'pause' ? 'pausado' : 'activado'}`);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error cambiando estado');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-96"><Loader2 className="w-8 h-8 animate-spin" /></div>;
  }

  const resumen = overview?.resumen || {};
  const agents = overview?.agents || [];

  return (
    <div className="space-y-6 animate-fade-in" data-testid="agentes-panel">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Bot className="w-6 h-6 text-indigo-600" />
            Oficina de Agentes IA
          </h1>
          <p className="text-muted-foreground text-sm">
            Centro de control de los {resumen.total_agentes || 0} agentes MCP · auto-refresh 60s
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} data-testid="btn-refrescar-panel-agentes">
            <RefreshCw className="w-4 h-4 mr-2" /> Refrescar
          </Button>
          <Button
            variant="default" size="sm"
            onClick={() => setShowWizard(true)}
            data-testid="btn-wizard-agentes"
            className="bg-gradient-to-r from-indigo-500 to-purple-600"
          >
            <Sparkles className="w-4 h-4 mr-2" /> ¿Qué puedo hacer con los agentes?
          </Button>
        </div>
      </div>

      {/* Panel central - procesos pendientes */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card className="bg-gradient-to-br from-indigo-50 to-indigo-100 border-indigo-200">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <Activity className="w-5 h-5 text-indigo-600" />
              <span className="text-3xl font-bold text-indigo-700">{resumen.acciones_hoy || 0}</span>
            </div>
            <p className="text-xs text-indigo-600 mt-1 font-medium">Acciones hoy</p>
          </CardContent>
        </Card>
        <Card className="bg-red-50 border-red-200" data-testid="card-errores-24h">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <XCircle className="w-5 h-5 text-red-600" />
              <span className="text-3xl font-bold text-red-700">{resumen.errores_24h || 0}</span>
            </div>
            <p className="text-xs text-red-600 mt-1 font-medium">Errores 24h</p>
          </CardContent>
        </Card>
        <Card className="bg-amber-50 border-amber-200" data-testid="card-aprobaciones">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <ShieldCheck className="w-5 h-5 text-amber-600" />
              <span className="text-3xl font-bold text-amber-700">{resumen.aprobaciones_pendientes || 0}</span>
            </div>
            <p className="text-xs text-amber-600 mt-1 font-medium">Aprobaciones pendientes</p>
          </CardContent>
        </Card>
        <Card className="bg-purple-50 border-purple-200">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <Calendar className="w-5 h-5 text-purple-600" />
              <span className="text-3xl font-bold text-purple-700">{resumen.tareas_proximas_24h || 0}</span>
            </div>
            <p className="text-xs text-purple-600 mt-1 font-medium">Tareas 24h</p>
          </CardContent>
        </Card>
        <Card className="bg-green-50 border-green-200">
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between">
              <TrendingUp className="w-5 h-5 text-green-600" />
              <span className="text-xs text-green-700 font-semibold">
                {resumen.agente_mas_activo ? agents.find(a => a.agent_id === resumen.agente_mas_activo)?.emoji : '—'}
              </span>
            </div>
            <p className="text-xs text-green-700 mt-1 font-medium truncate">
              {resumen.agente_mas_activo || 'Sin actividad'}
            </p>
            <p className="text-[10px] text-green-600">Más activo</p>
          </CardContent>
        </Card>
      </div>

      {/* Oficina de Agentes — Grid de tarjetas */}
      <div>
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <Users className="w-5 h-5 text-slate-600" /> Plantilla de agentes
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {agents.map((a) => (
            <AgentCard
              key={a.agent_id}
              agent={a}
              isMaster={isMaster}
              onToggle={handleToggleState}
              onViewDetail={() => setSelectedAgent(a)}
              onChat={() => navigate(`/crm/agente-aria?agent=${a.agent_id}`)}
            />
          ))}
        </div>
      </div>

      {/* Sección métricas */}
      <AgentMetricsSection />

      {/* Panel lateral del agente */}
      <Sheet open={!!selectedAgent} onOpenChange={(o) => !o && setSelectedAgent(null)}>
        <SheetContent className="w-full sm:max-w-2xl overflow-y-auto" data-testid="agent-detail-sheet">
          {selectedAgent && (
            <AgentDetailSheet
              agent={selectedAgent}
              isMaster={isMaster}
              onClose={() => setSelectedAgent(null)}
              onChange={() => { load(); setSelectedAgent({ ...selectedAgent }); }}
            />
          )}
        </SheetContent>
      </Sheet>

      {/* Wizard */}
      <Sheet open={showWizard} onOpenChange={setShowWizard}>
        <SheetContent className="w-full sm:max-w-xl overflow-y-auto" data-testid="wizard-sheet">
          <AgentUseCaseWizard agents={agents} onClose={() => setShowWizard(false)} navigate={navigate} />
        </SheetContent>
      </Sheet>
    </div>
  );
}

// ─── Tarjeta de agente ───────────────────────────────────────────────────────
function AgentCard({ agent, isMaster, onToggle, onViewDetail, onChat }) {
  const estadoStyle = ESTADO_BADGE[agent.estado] || ESTADO_BADGE.activo;
  const tasaColor = agent.tasa_exito_7d >= 95 ? 'text-green-700'
    : agent.tasa_exito_7d >= 80 ? 'text-amber-700' : 'text-red-700';

  return (
    <Card
      className="hover:shadow-md transition-shadow relative overflow-hidden"
      data-testid={`agent-card-${agent.agent_id}`}
      style={{ borderTopWidth: 3, borderTopColor: agent.color }}
    >
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start gap-3">
          <div
            className="w-12 h-12 rounded-lg flex items-center justify-center text-2xl shrink-0"
            style={{ background: `${agent.color}22` }}
          >
            {agent.emoji}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="font-semibold truncate">{agent.nombre}</p>
              <Badge variant="outline" className={`${estadoStyle.className} text-[10px] shrink-0`}>
                {estadoStyle.label}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">{agent.descripcion}</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="bg-slate-50 rounded p-1.5">
            <p className="text-lg font-bold text-slate-700">{agent.acciones_hoy}</p>
            <p className="text-[9px] text-muted-foreground uppercase">Hoy</p>
          </div>
          <div className="bg-slate-50 rounded p-1.5">
            <p className={`text-lg font-bold ${tasaColor}`}>{agent.tasa_exito_7d}%</p>
            <p className="text-[9px] text-muted-foreground uppercase">Éxito 7d</p>
          </div>
          <div className="bg-slate-50 rounded p-1.5">
            <p className="text-lg font-bold text-slate-700">{agent.tools_count}</p>
            <p className="text-[9px] text-muted-foreground uppercase">Tools</p>
          </div>
        </div>

        <p className="text-[11px] text-muted-foreground">
          {agent.ultima_accion ? (
            <>
              <Clock className="w-3 h-3 inline mr-1" />
              <span className="font-mono font-medium">{agent.ultima_accion.tool}</span>
              {' · '}{timeAgo(agent.ultima_accion.timestamp)}
            </>
          ) : (
            <span className="italic">Sin actividad reciente</span>
          )}
        </p>
        {agent.errores_24h > 0 && (
          <div className="flex items-center gap-1 text-[11px] text-red-600 bg-red-50 rounded px-2 py-1">
            <AlertTriangle className="w-3 h-3" />
            {agent.errores_24h} error(es) en 24h
          </div>
        )}

        <div className="flex gap-1.5">
          {isMaster && (
            <Button
              size="sm" variant={agent.estado === 'pausado' ? 'default' : 'outline'}
              onClick={() => onToggle(agent)} className="flex-1 h-8 text-xs"
              data-testid={`btn-toggle-${agent.agent_id}`}
            >
              {agent.estado === 'pausado'
                ? <><Play className="w-3 h-3 mr-1" /> Activar</>
                : <><Pause className="w-3 h-3 mr-1" /> Pausar</>}
            </Button>
          )}
          <Button
            size="sm" variant="outline" onClick={onChat}
            className="flex-1 h-8 text-xs"
            data-testid={`btn-chat-${agent.agent_id}`}
          >
            <MessageSquare className="w-3 h-3 mr-1" /> Hablar
          </Button>
          <Button
            size="sm" variant="outline" onClick={onViewDetail}
            className="flex-1 h-8 text-xs"
            data-testid={`btn-detail-${agent.agent_id}`}
          >
            <Eye className="w-3 h-3 mr-1" /> Detalle
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Panel lateral con 5 pestañas ────────────────────────────────────────────
function AgentDetailSheet({ agent, isMaster, onClose, onChange }) {
  return (
    <>
      <SheetHeader>
        <SheetTitle className="flex items-center gap-2">
          <span className="text-2xl">{agent.emoji}</span>
          {agent.nombre}
          <Badge variant="outline" className={`${ESTADO_BADGE[agent.estado]?.className} text-[10px]`}>
            {ESTADO_BADGE[agent.estado]?.label}
          </Badge>
        </SheetTitle>
        <SheetDescription>{agent.descripcion}</SheetDescription>
      </SheetHeader>

      <Tabs defaultValue="que-hace" className="mt-4">
        <TabsList className="grid grid-cols-5 w-full">
          <TabsTrigger value="que-hace" data-testid="tab-que-hace">¿Qué hace?</TabsTrigger>
          <TabsTrigger value="actividad" data-testid="tab-actividad">Actividad</TabsTrigger>
          <TabsTrigger value="tareas" data-testid="tab-tareas">Tareas</TabsTrigger>
          <TabsTrigger value="config" data-testid="tab-config">Config</TabsTrigger>
          <TabsTrigger value="cola" data-testid="tab-cola">Cola</TabsTrigger>
        </TabsList>

        <TabsContent value="que-hace" className="mt-4">
          <QueHaceTab agent={agent} />
        </TabsContent>
        <TabsContent value="actividad" className="mt-4">
          <ActividadTab agentId={agent.agent_id} />
        </TabsContent>
        <TabsContent value="tareas" className="mt-4">
          <TareasTab agentId={agent.agent_id} isMaster={isMaster} />
        </TabsContent>
        <TabsContent value="config" className="mt-4">
          <ConfigTab agentId={agent.agent_id} isMaster={isMaster} onChange={onChange} />
        </TabsContent>
        <TabsContent value="cola" className="mt-4">
          <ColaAprobacionTab agentId={agent.agent_id} isMaster={isMaster} />
        </TabsContent>
      </Tabs>
    </>
  );
}

// Pestaña: ¿Qué hace?
function QueHaceTab({ agent }) {
  const ejemplos = {
    kpi_analyst: ['Dame los KPIs de esta semana', '¿Cuántas órdenes reparamos en mayo?'],
    auditor: ['Revisa si hay órdenes con incumplimiento de SLA', 'Genera un informe de auditoría'],
    supervisor_cola: ['¿Cuántas órdenes hay atascadas?', 'Reasigna las órdenes urgentes'],
    iso_officer: ['Genera el informe de calidad del mes', 'Revisa no-conformidades'],
    finance_officer: ['Lista facturas pendientes', 'Prepara Modelo 303'],
    gestor_siniestros: ['Lista peticiones de aseguradora pendientes', 'Crea la orden de siniestro 123'],
    triador_averias: ['Se cayó y tiene la pantalla rota, iPhone 12', 'Recomienda técnico para una reparación de agua'],
    seguimiento_publico: ['¿Cuál es el estado de la OT 123?'],
  };
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold mb-1.5">Descripción</h3>
        <p className="text-sm text-muted-foreground">{agent.descripcion}</p>
      </div>
      <div>
        <h3 className="text-sm font-semibold mb-1.5">Tools disponibles ({agent.tools_count})</h3>
        <div className="grid grid-cols-2 gap-1.5">
          {(agent.tools || []).map((t) => (
            <Badge key={t} variant="secondary" className="font-mono text-[10px] justify-start">
              {t}
            </Badge>
          ))}
        </div>
      </div>
      <div>
        <h3 className="text-sm font-semibold mb-1.5">Permisos (scopes)</h3>
        <div className="flex flex-wrap gap-1">
          {(agent.scopes || []).map((s) => (
            <Badge key={s} variant="outline" className="text-[10px] font-mono">{s}</Badge>
          ))}
        </div>
      </div>
      <div>
        <h3 className="text-sm font-semibold mb-1.5">Prueba preguntarle...</h3>
        <ul className="space-y-1 text-sm">
          {(ejemplos[agent.agent_id] || ['Hazme un resumen']).map((e, i) => (
            <li key={i} className="flex items-start gap-2 text-muted-foreground">
              <Sparkles className="w-3 h-3 mt-1 text-indigo-500 shrink-0" /> <span className="italic">&quot;{e}&quot;</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

// Pestaña: Actividad
function ActividadTab({ agentId }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtroTool, setFiltroTool] = useState('');
  const [filtroResultado, setFiltroResultado] = useState('all');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filtroTool) params.set('tool', filtroTool);
      if (filtroResultado !== 'all') params.set('resultado', filtroResultado);
      params.set('limit', '100');
      const { data } = await API.get(`/agents/${agentId}/timeline?${params.toString()}`);
      setItems(data.items || []);
    } catch {
      toast.error('Error cargando actividad');
    } finally {
      setLoading(false);
    }
  }, [agentId, filtroTool, filtroResultado]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Input
          placeholder="Filtrar por tool..."
          value={filtroTool}
          onChange={(e) => setFiltroTool(e.target.value)}
          className="h-8 text-sm"
          data-testid="input-filtro-tool"
        />
        <Select value={filtroResultado} onValueChange={setFiltroResultado}>
          <SelectTrigger className="w-32 h-8 text-sm"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="ok">Éxito</SelectItem>
            <SelectItem value="error">Errores</SelectItem>
          </SelectContent>
        </Select>
      </div>
      {loading ? (
        <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin" /></div>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-8">Sin actividad registrada</p>
      ) : (
        <div className="space-y-1 max-h-[60vh] overflow-y-auto">
          {items.map((it, i) => (
            <details key={i} className="border rounded p-2 hover:bg-slate-50">
              <summary className="cursor-pointer flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  {it.error ? (
                    <XCircle className="w-3.5 h-3.5 text-red-500" />
                  ) : (
                    <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                  )}
                  <span className="font-mono font-medium">{it.tool}</span>
                  <span className="text-[10px] text-muted-foreground">{timeAgo(it.timestamp)}</span>
                </div>
                <span className="text-[10px] text-muted-foreground">{it.duration_ms}ms</span>
              </summary>
              <div className="mt-2 text-xs space-y-1">
                <div>
                  <span className="text-muted-foreground">Params:</span>
                  <pre className="bg-slate-100 rounded p-1 mt-0.5 overflow-auto font-mono text-[10px]">
                    {JSON.stringify(it.params, null, 2)}
                  </pre>
                </div>
                {it.result_summary && (
                  <div>
                    <span className="text-muted-foreground">Resultado:</span>
                    <pre className="bg-slate-100 rounded p-1 mt-0.5 overflow-auto font-mono text-[10px]">
                      {JSON.stringify(it.result_summary, null, 2).slice(0, 500)}
                    </pre>
                  </div>
                )}
                {it.error && (
                  <p className="text-red-700 bg-red-50 rounded p-1"><b>Error:</b> {it.error}</p>
                )}
              </div>
            </details>
          ))}
        </div>
      )}
    </div>
  );
}

// Pestaña: Tareas programadas
function TareasTab({ agentId, isMaster }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const { data } = await API.get(`/agents/scheduled-tasks?agent_id=${agentId}`);
      setTasks(Array.isArray(data) ? data : data.items || []);
    } catch {
      toast.error('Error cargando tareas');
    } finally {
      setLoading(false);
    }
  }, [agentId]);
  useEffect(() => { load(); }, [load]);

  const runNow = async (taskId) => {
    try {
      await API.post(`/agents/scheduled-tasks/${taskId}/run-now`);
      toast.success('Tarea ejecutándose');
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  if (loading) return <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin" /></div>;
  if (tasks.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-muted-foreground">
        <Calendar className="w-10 h-10 mx-auto mb-2 opacity-40" />
        Sin tareas programadas para este agente.
      </div>
    );
  }
  return (
    <div className="space-y-2">
      {tasks.map((t) => (
        <div key={t.id} className="border rounded-lg p-3 text-sm" data-testid={`task-${t.id}`}>
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className="font-medium">{t.nombre || t.tool}</span>
            <Badge variant="outline" className="text-[10px]">{t.estado}</Badge>
          </div>
          <div className="text-xs text-muted-foreground space-y-0.5">
            <p>Cron: <code className="font-mono">{t.cron_expression || t.cron || '—'}</code></p>
            <p>Próxima: {t.proxima_ejecucion || '—'}</p>
            <p>Última: {t.ultima_ejecucion || '—'}</p>
          </div>
          {isMaster && (
            <Button size="sm" variant="outline" className="mt-2 h-7 text-xs"
                    onClick={() => runNow(t.id)}
                    data-testid={`btn-run-task-${t.id}`}>
              <Play className="w-3 h-3 mr-1" /> Ejecutar ahora
            </Button>
          )}
        </div>
      ))}
    </div>
  );
}

// Pestaña: Configuración
function ConfigTab({ agentId, isMaster, onChange }) {
  const [config, setConfig] = useState(null);
  const [draft, setDraft] = useState({ rate_limit_soft: 120, rate_limit_hard: 600, system_prompt: '' });
  const [saving, setSaving] = useState(false);
  const [showPromptEdit, setShowPromptEdit] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await API.get(`/agents/${agentId}/config`);
      setConfig(data);
      setDraft({
        rate_limit_soft: data.rate_limit_soft,
        rate_limit_hard: data.rate_limit_hard,
        system_prompt: data.system_prompt_effective,
      });
    } catch {
      toast.error('Error cargando config');
    }
  }, [agentId]);
  useEffect(() => { load(); }, [load]);

  const save = async (onlyLimits = false) => {
    setSaving(true);
    try {
      const payload = onlyLimits
        ? { rate_limit_soft: Number(draft.rate_limit_soft), rate_limit_hard: Number(draft.rate_limit_hard) }
        : { system_prompt: draft.system_prompt };
      await API.post(`/agents/${agentId}/config`, payload);
      toast.success('Configuración guardada');
      setShowPromptEdit(false);
      load();
      onChange?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error guardando');
    } finally {
      setSaving(false);
    }
  };

  if (!config) return <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin" /></div>;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Rate limits</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-2 gap-3">
          <div>
            <Label className="text-xs">Soft (req/min)</Label>
            <Input
              type="number" min="1"
              value={draft.rate_limit_soft}
              onChange={(e) => setDraft({ ...draft, rate_limit_soft: e.target.value })}
              disabled={!isMaster}
              data-testid="input-rate-soft"
            />
          </div>
          <div>
            <Label className="text-xs">Hard (req/min)</Label>
            <Input
              type="number" min="1"
              value={draft.rate_limit_hard}
              onChange={(e) => setDraft({ ...draft, rate_limit_hard: e.target.value })}
              disabled={!isMaster}
              data-testid="input-rate-hard"
            />
          </div>
          {isMaster && (
            <Button
              size="sm" className="col-span-2"
              onClick={() => save(true)} disabled={saving}
              data-testid="btn-save-rate-limits"
            >
              {saving ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Save className="w-3 h-3 mr-1" />}
              Guardar rate limits
            </Button>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center justify-between">
            System prompt
            {config.system_prompt_override && (
              <Badge className="bg-indigo-100 text-indigo-800 border-indigo-300 text-[10px]">
                override activo
              </Badge>
            )}
          </CardTitle>
          <CardDescription className="text-[11px]">
            ⚠️ Cambiar esto afecta directamente el comportamiento del agente.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!showPromptEdit ? (
            <>
              <pre className="text-[11px] bg-slate-50 rounded p-2 max-h-60 overflow-auto whitespace-pre-wrap">
                {config.system_prompt_effective}
              </pre>
              {isMaster && (
                <Button size="sm" variant="outline" className="mt-2"
                        onClick={() => setShowPromptEdit(true)}
                        data-testid="btn-editar-prompt">
                  Editar prompt
                </Button>
              )}
            </>
          ) : (
            <>
              <Textarea
                rows={10}
                value={draft.system_prompt}
                onChange={(e) => setDraft({ ...draft, system_prompt: e.target.value })}
                className="font-mono text-[11px]"
                data-testid="textarea-system-prompt"
              />
              <div className="flex gap-2 mt-2">
                <Button size="sm" onClick={() => save(false)} disabled={saving} data-testid="btn-save-prompt">
                  Guardar prompt
                </Button>
                <Button size="sm" variant="outline" onClick={() => {
                  setDraft({ ...draft, system_prompt: config.system_prompt_default });
                }}>
                  Reset a default
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setShowPromptEdit(false)}>Cancelar</Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {config.history?.length > 0 && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Historial de cambios</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-1 text-xs">
              {config.history.slice().reverse().map((h, i) => (
                <li key={i} className="flex justify-between border-b py-1">
                  <span className="text-muted-foreground">{h.at}</span>
                  <span>{h.by}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// Pestaña: Cola de aprobación
function ColaAprobacionTab({ agentId, isMaster }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const { data } = await API.get('/agents/panel/pending-approvals');
      const filtrados = (data.items || []).filter((i) => i.agent_id === agentId);
      setItems(filtrados);
    } catch { /* pass */ }
    finally { setLoading(false); }
  }, [agentId]);
  useEffect(() => { load(); }, [load]);

  const decide = async (id, decision) => {
    try {
      await API.post(`/agents/panel/pending-approvals/${id}/decide`, { decision });
      toast.success(`Acción ${decision}`);
      load();
    } catch (err) { toast.error(err.response?.data?.detail || 'Error'); }
  };

  if (loading) return <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin" /></div>;

  if (items.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-muted-foreground">
        <ShieldCheck className="w-10 h-10 mx-auto mb-2 opacity-40" />
        Sin acciones pendientes de aprobación para este agente.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((i) => (
        <Card key={i.id} className="border-amber-300" data-testid={`approval-${i.id}`}>
          <CardContent className="p-3 space-y-1 text-sm">
            <div className="flex items-center justify-between">
              <code className="font-medium">{i.tool}</code>
              <Badge variant="outline" className="text-[10px]">{i.estado}</Badge>
            </div>
            <p className="text-xs text-muted-foreground">Solicitado: {timeAgo(i.solicitado_en)}</p>
            {i.impacto_estimado && (
              <p className="text-xs"><b>Impacto:</b> {i.impacto_estimado}</p>
            )}
            <pre className="text-[10px] bg-slate-50 rounded p-1 max-h-32 overflow-auto">
              {JSON.stringify(i.params, null, 2)}
            </pre>
            {isMaster && (
              <div className="flex gap-1">
                <Button size="sm" onClick={() => decide(i.id, 'aprobar')} className="flex-1 h-7 text-xs bg-green-600 hover:bg-green-700">
                  Aprobar
                </Button>
                <Button size="sm" variant="outline" onClick={() => decide(i.id, 'rechazar')} className="flex-1 h-7 text-xs">
                  Rechazar
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ─── Sección de Métricas globales ────────────────────────────────────────────
function AgentMetricsSection() {
  const [metrics, setMetrics] = useState(null);
  const [days, setDays] = useState(7);

  useEffect(() => {
    API.get(`/agents/panel/metrics?days=${days}`)
      .then((r) => setMetrics(r.data))
      .catch(() => {});
  }, [days]);

  const maxPorAgente = useMemo(() => {
    if (!metrics?.por_agente?.length) return 1;
    return Math.max(...metrics.por_agente.map((p) => p.total));
  }, [metrics]);

  return (
    <div data-testid="metrics-section">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-slate-600" /> Métricas y observabilidad
        </h2>
        <Select value={String(days)} onValueChange={(v) => setDays(Number(v))}>
          <SelectTrigger className="w-32 h-8 text-sm"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="1">Último día</SelectItem>
            <SelectItem value="7">Últimos 7 días</SelectItem>
            <SelectItem value="30">Últimos 30 días</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Acciones por agente</CardTitle></CardHeader>
          <CardContent>
            {(metrics?.por_agente || []).map((p) => (
              <div key={p.agent_id} className="mb-2">
                <div className="flex justify-between text-[11px] mb-0.5">
                  <span className="font-mono">{p.agent_id}</span>
                  <span><b>{p.total}</b> · {p.tasa_exito}%</span>
                </div>
                <div className="bg-slate-100 h-2 rounded">
                  <div className="bg-indigo-500 h-2 rounded"
                       style={{ width: `${(p.total / maxPorAgente) * 100}%` }} />
                </div>
              </div>
            ))}
            {(!metrics?.por_agente?.length) && <p className="text-xs text-muted-foreground">Sin datos</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Tools más usadas</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {(metrics?.top_tools || []).slice(0, 8).map((t, i) => (
              <div key={i} className="flex justify-between text-xs">
                <span className="font-mono truncate">{t.tool}</span>
                <span className="text-muted-foreground">{t.total}</span>
              </div>
            ))}
            {(!metrics?.top_tools?.length) && <p className="text-xs text-muted-foreground">Sin datos</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Errores más frecuentes</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {(metrics?.top_errors || []).slice(0, 8).map((e, i) => (
              <div key={i} className="flex justify-between text-xs">
                <span className="truncate text-red-700" title={e.error}>{e.error.slice(0, 40)}</span>
                <span className="text-muted-foreground">{e.count}</span>
              </div>
            ))}
            {(!metrics?.top_errors?.length) && (
              <p className="text-xs text-green-700 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Sin errores 🎉
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ─── Wizard ──────────────────────────────────────────────────────────────────
function AgentUseCaseWizard({ agents, onClose, navigate }) {
  const casos = [
    { id: 'kpis', pregunta: '¿Cómo va el negocio esta semana?', agent: 'kpi_analyst',
      prompt: 'Dame los KPIs principales de esta semana con tendencias', icon: '📊' },
    { id: 'atascadas', pregunta: 'Hay órdenes atascadas, ¿qué hago?', agent: 'supervisor_cola',
      prompt: 'Lista las órdenes atascadas y sugiere acciones', icon: '📋' },
    { id: 'finanzas', pregunta: 'Quiero preparar la declaración del 303', agent: 'finance_officer',
      prompt: 'Calcula el Modelo 303 del último trimestre', icon: '💰' },
    { id: 'siniestros', pregunta: 'Llegaron peticiones de Insurama', agent: 'gestor_siniestros',
      prompt: 'Lista las peticiones pendientes y priorízalas', icon: '🛡️' },
    { id: 'aria-diag', pregunta: 'Se cayó el móvil de un cliente', agent: 'triador_averias',
      prompt: 'Se cayó un iPhone 12, pantalla rota, no responde. Analiza', icon: '🔧' },
    { id: 'auditoria', pregunta: 'Necesito auditar SLA e incumplimientos', agent: 'auditor',
      prompt: 'Genera un informe de SLA e incumplimientos del mes', icon: '🔍' },
  ];
  return (
    <>
      <SheetHeader>
        <SheetTitle className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-indigo-600" />
          ¿Qué puedo hacer con los agentes?
        </SheetTitle>
        <SheetDescription>
          Casos de uso comunes. Haz click en cualquiera para ir directo a chatear con el agente.
        </SheetDescription>
      </SheetHeader>
      <div className="space-y-2 mt-4">
        {casos.map((c) => {
          const agent = agents.find((a) => a.agent_id === c.agent);
          return (
            <Card key={c.id} className="hover:shadow-md cursor-pointer transition"
                  onClick={() => {
                    navigate(`/crm/agente-aria?agent=${c.agent}&prompt=${encodeURIComponent(c.prompt)}`);
                    onClose();
                  }}
                  data-testid={`wizard-case-${c.id}`}>
              <CardContent className="p-3 flex items-center gap-3">
                <span className="text-2xl">{c.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm">{c.pregunta}</p>
                  <p className="text-[11px] text-muted-foreground truncate">
                    {agent?.nombre || c.agent} · &quot;{c.prompt}&quot;
                  </p>
                </div>
                <MessageSquare className="w-4 h-4 text-indigo-500" />
              </CardContent>
            </Card>
          );
        })}
      </div>
    </>
  );
}

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import API from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Send, Bot, Wrench, Clock, Plus, Trash2, MessageSquare,
  ChevronRight, Loader2, Sparkles, Activity,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { toast } from 'sonner';

/**
 * /crm/agentes
 * Chat con los agentes IA nativos de Revix (read-only en Fase 1).
 * Layout: 3 columnas (agentes | chat | audit panel opcional).
 */
export default function AgentesIA() {
  const { user, isAdmin } = useAuth();
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showAudit, setShowAudit] = useState(false);
  const [auditLogs, setAuditLogs] = useState([]);
  const [showTasks, setShowTasks] = useState(false);
  const [scheduledTasks, setScheduledTasks] = useState([]);
  const scrollRef = useRef(null);

  // Fetch agents
  useEffect(() => {
    (async () => {
      try {
        const { data } = await API.get('/agents');
        setAgents(data.agents);
        if (data.agents.length > 0) setSelectedAgent(data.agents[0]);
      } catch (e) {
        toast.error('No se pudieron cargar los agentes.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Fetch sessions when agent changes
  useEffect(() => {
    if (!selectedAgent) return;
    setMessages([]);
    setCurrentSessionId(null);
    (async () => {
      try {
        const { data } = await API.get(`/agents/${selectedAgent.id}/sessions`);
        setSessions(data.sessions);
      } catch (e) { /* silent */ }
    })();
  }, [selectedAgent]);

  // Scroll al final en cada cambio
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, sending]);

  const handleSelectSession = async (sid) => {
    setCurrentSessionId(sid);
    try {
      const { data } = await API.get(`/agents/sessions/${sid}`);
      setMessages(data.messages);
    } catch (e) {
      toast.error('No se pudo cargar la sesión.');
    }
  };

  const handleNewSession = () => {
    setCurrentSessionId(null);
    setMessages([]);
  };

  const handleDeleteSession = async (sid, e) => {
    e.stopPropagation();
    if (!window.confirm('¿Borrar esta conversación?')) return;
    try {
      await API.delete(`/agents/sessions/${sid}`);
      setSessions((s) => s.filter((x) => x.id !== sid));
      if (currentSessionId === sid) handleNewSession();
    } catch (e) {
      toast.error('Error al borrar.');
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending || !selectedAgent) return;
    setSending(true);
    // Optimistic UI
    const userMsg = { role: 'user', content: text, seq: messages.length };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    try {
      const { data } = await API.post(`/agents/${selectedAgent.id}/chat`, {
        message: text,
        session_id: currentSessionId,
      });
      const assistantMsg = {
        role: 'assistant',
        content: data.reply,
        seq: messages.length + 1,
        tool_calls_meta: data.tool_calls,
        duration_ms: data.duration_ms,
        iterations: data.iterations,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      if (!currentSessionId) {
        setCurrentSessionId(data.session_id);
        // refresh sessions list
        const { data: sList } = await API.get(`/agents/${selectedAgent.id}/sessions`);
        setSessions(sList.sessions);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Fallo del agente');
      setMessages((prev) => prev.slice(0, -1)); // rollback
      setInput(text);
    } finally {
      setSending(false);
    }
  };

  const loadAuditLogs = async () => {
    setShowAudit(true);
    setShowTasks(false);
    try {
      const { data } = await API.get('/agents/audit-logs', {
        params: { agent_id: selectedAgent?.id, limit: 50 },
      });
      setAuditLogs(data.logs);
    } catch (e) {
      toast.error('No se pudieron cargar los audit logs.');
    }
  };

  const loadScheduledTasks = async () => {
    setShowTasks(true);
    setShowAudit(false);
    try {
      const { data } = await API.get('/agents/scheduled-tasks', {
        params: { agent_id: selectedAgent?.id },
      });
      setScheduledTasks(data.tasks);
    } catch (e) {
      toast.error('No se pudieron cargar las tareas programadas.');
    }
  };

  const runTaskNow = async (taskId) => {
    try {
      const { data } = await API.post(`/agents/scheduled-tasks/${taskId}/run-now`);
      toast.success(data.success ? 'Tarea ejecutada correctamente' : `Fallo: ${data.error || 'desconocido'}`);
      await loadScheduledTasks();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error ejecutando tarea');
    }
  };

  const toggleTask = async (task) => {
    try {
      await API.patch(`/agents/scheduled-tasks/${task.id}`, { activo: !task.activo });
      await loadScheduledTasks();
    } catch (e) {
      toast.error('Error actualizando tarea');
    }
  };

  const SAMPLE_PROMPTS = {
    kpi_analyst: [
      '¿Cómo vamos este mes? Dame un resumen del dashboard.',
      '¿Qué modelos de móvil se reparan más últimamente?',
      '¿Cumplimos el SLA en las últimas reparaciones?',
      '¿Qué repuestos tengo por debajo del stock mínimo?',
    ],
    auditor: [
      'Auditoría completa del mes en curso.',
      '¿Hay órdenes reparadas sin entregar?',
      '¿Qué órdenes en garantía tienen datos incompletos?',
      '¿Detectas cuellos de botella por técnico?',
    ],
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" data-testid="agentes-loading">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div
      className="flex h-[calc(100vh-64px)] bg-gradient-to-br from-slate-50 to-blue-50/30"
      data-testid="agentes-ia-page"
    >
      {/* === Columna izquierda · Agentes & Sesiones === */}
      <aside className="w-72 border-r border-slate-200 bg-white/80 backdrop-blur flex flex-col">
        <div className="p-4 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-semibold">Agentes IA</h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Consulta tu CRM en lenguaje natural.
          </p>
        </div>
        <div className="p-3 space-y-1.5">
          {agents.map((a) => (
            <button
              key={a.id}
              data-testid={`agent-select-${a.id}`}
              onClick={() => setSelectedAgent(a)}
              className={`w-full text-left p-3 rounded-xl transition-all ${
                selectedAgent?.id === a.id
                  ? 'bg-blue-50 ring-1 ring-blue-200'
                  : 'hover:bg-slate-50'
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-xl">{a.emoji}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-900 truncate">{a.nombre}</div>
                  <div className="text-xs text-slate-500 truncate">{a.descripcion}</div>
                </div>
              </div>
            </button>
          ))}
        </div>

        {selectedAgent && (
          <>
            <div className="px-4 py-2 mt-2 flex items-center justify-between border-t border-slate-100">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Conversaciones
              </span>
              <button
                data-testid="new-session-btn"
                onClick={handleNewSession}
                className="p-1 hover:bg-slate-100 rounded-md"
                title="Nueva conversación"
              >
                <Plus className="w-4 h-4 text-slate-600" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-2 pb-2">
              {sessions.length === 0 && (
                <div className="text-xs text-slate-400 px-2 py-4 text-center">
                  Todavía no hay conversaciones.
                </div>
              )}
              {sessions.map((s) => (
                <div
                  key={s.id}
                  data-testid={`session-item-${s.id}`}
                  onClick={() => handleSelectSession(s.id)}
                  className={`group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer text-xs ${
                    currentSessionId === s.id ? 'bg-blue-50' : 'hover:bg-slate-50'
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span className="flex-1 truncate text-slate-700">{s.title || 'Sin título'}</span>
                  <button
                    onClick={(e) => handleDeleteSession(s.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-slate-200 rounded"
                  >
                    <Trash2 className="w-3 h-3 text-slate-500" />
                  </button>
                </div>
              ))}
            </div>
          </>
        )}

        {isAdmin() && (
          <div className="m-3 space-y-2">
            <button
              data-testid="audit-panel-toggle"
              onClick={loadAuditLogs}
              className="w-full p-2 text-xs text-slate-600 hover:bg-slate-50 rounded-lg flex items-center gap-2 border border-slate-200"
            >
              <Activity className="w-3.5 h-3.5" />
              Audit logs MCP
            </button>
            <button
              data-testid="scheduled-tasks-toggle"
              onClick={loadScheduledTasks}
              className="w-full p-2 text-xs text-slate-600 hover:bg-slate-50 rounded-lg flex items-center gap-2 border border-slate-200"
            >
              <Clock className="w-3.5 h-3.5" />
              Tareas programadas
            </button>
          </div>
        )}
      </aside>

      {/* === Columna central · Chat === */}
      <main className="flex-1 flex flex-col">
        {selectedAgent && (
          <header className="px-6 py-3.5 border-b border-slate-200 bg-white/60 backdrop-blur">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{selectedAgent.emoji}</span>
              <div className="flex-1">
                <h1 className="text-base font-semibold text-slate-900" data-testid="agent-name">
                  {selectedAgent.nombre}
                </h1>
                <p className="text-xs text-slate-500">{selectedAgent.descripcion}</p>
              </div>
              <Badge variant="outline" className="text-xs">
                <Wrench className="w-3 h-3 mr-1" />
                {selectedAgent.tools.length} tools
              </Badge>
            </div>
          </header>
        )}

        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-6 py-6 space-y-5"
          data-testid="chat-messages"
        >
          {messages.length === 0 && selectedAgent && (
            <div className="max-w-2xl mx-auto text-center pt-12">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 text-white text-3xl mb-4">
                {selectedAgent.emoji}
              </div>
              <h2 className="text-xl font-semibold text-slate-900">
                Habla con {selectedAgent.nombre}
              </h2>
              <p className="text-sm text-slate-600 mt-2">
                {selectedAgent.descripcion}
              </p>
              <div className="grid grid-cols-2 gap-2 mt-8 text-left">
                {(SAMPLE_PROMPTS[selectedAgent.id] || []).map((p, idx) => (
                  <button
                    key={idx}
                    data-testid={`sample-prompt-${idx}`}
                    onClick={() => setInput(p)}
                    className="p-3 text-sm text-slate-700 bg-white hover:bg-blue-50 border border-slate-200 rounded-xl transition-all hover:border-blue-300"
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-3xl rounded-2xl px-4 py-3 ${
                  m.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white border border-slate-200 text-slate-900'
                }`}
              >
                {m.role === 'assistant' && m.tool_calls_meta?.length > 0 && (
                  <div className="mb-2 flex flex-wrap gap-1">
                    {m.tool_calls_meta.map((tc, i) => (
                      <Badge key={i} variant="secondary" className="text-xs font-mono">
                        <Wrench className="w-3 h-3 mr-1" />
                        {tc.tool} · {tc.duration_ms}ms
                      </Badge>
                    ))}
                  </div>
                )}
                {m.role === 'user' ? (
                  <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                ) : (
                  <div className="prose prose-sm max-w-none prose-headings:mt-3 prose-headings:mb-2 prose-p:my-2 prose-ul:my-2">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {m.content || ''}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex justify-start">
              <div className="bg-white border border-slate-200 rounded-2xl px-4 py-3 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                <span className="text-sm text-slate-600">Pensando...</span>
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-slate-200 bg-white/80 backdrop-blur px-6 py-4">
          <div className="flex gap-2 items-end max-w-4xl mx-auto">
            <Textarea
              data-testid="agent-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder={
                selectedAgent
                  ? `Pregunta a ${selectedAgent.nombre}... (Enter para enviar)`
                  : 'Selecciona un agente'
              }
              rows={1}
              className="flex-1 resize-none min-h-[44px] max-h-32"
              disabled={sending || !selectedAgent}
            />
            <Button
              data-testid="agent-send-btn"
              onClick={handleSend}
              disabled={sending || !input.trim() || !selectedAgent}
              size="icon"
              className="h-11 w-11 rounded-xl bg-blue-600 hover:bg-blue-700"
            >
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
          <p className="text-[11px] text-slate-400 text-center mt-2">
            {selectedAgent?.nombre || 'Agente'} solo tiene acceso de lectura. Cada consulta queda auditada.
          </p>
        </div>
      </main>

      {/* === Columna derecha · Tareas programadas === */}
      {showTasks && isAdmin() && (
        <aside className="w-96 border-l border-slate-200 bg-white/90 flex flex-col" data-testid="scheduled-tasks-panel">
          <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-600" />
              <h3 className="text-sm font-semibold">Tareas programadas</h3>
            </div>
            <button onClick={() => setShowTasks(false)} className="text-slate-400 hover:text-slate-700">
              ✕
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {scheduledTasks.length === 0 && (
              <p className="text-xs text-slate-400 text-center py-4">Sin tareas programadas.</p>
            )}
            {scheduledTasks.map((t) => (
              <div key={t.id} className="text-xs p-3 rounded-lg bg-slate-50 border border-slate-100" data-testid={`task-${t.id}`}>
                <div className="flex items-center justify-between mb-1">
                  <code className="font-mono text-blue-700 text-[11px]">{t.tool}</code>
                  <Badge variant={t.activo ? 'default' : 'outline'} className="text-[10px]">
                    {t.activo ? 'activa' : 'pausada'}
                  </Badge>
                </div>
                <div className="text-slate-700 font-medium mb-1">{t.descripcion}</div>
                <div className="text-slate-500 space-y-0.5">
                  <div>agent: <span className="font-mono">{t.agent_id}</span></div>
                  <div>cron: <span className="font-mono">{t.cron_expression}</span></div>
                  <div>próxima: {t.proxima_ejecucion?.slice(0, 16).replace('T', ' ')}</div>
                  {t.ultima_ejecucion && (
                    <div className={t.ultima_ejecucion_resultado === 'ok' ? 'text-emerald-600' : 'text-red-600'}>
                      última: {t.ultima_ejecucion.slice(0, 16).replace('T', ' ')} ({t.ultima_ejecucion_resultado || '—'})
                    </div>
                  )}
                  {t.ultima_ejecucion_error && (
                    <div className="text-red-600 text-[10px] truncate">err: {t.ultima_ejecucion_error}</div>
                  )}
                  {t.consecutive_failures > 0 && (
                    <div className="text-amber-600">fallos consecutivos: {t.consecutive_failures}/3</div>
                  )}
                </div>
                <div className="flex gap-1 mt-2">
                  <button
                    data-testid={`task-run-${t.id}`}
                    onClick={() => runTaskNow(t.id)}
                    className="flex-1 px-2 py-1 text-[10px] bg-blue-100 hover:bg-blue-200 text-blue-700 rounded"
                  >
                    Ejecutar ahora
                  </button>
                  <button
                    data-testid={`task-toggle-${t.id}`}
                    onClick={() => toggleTask(t)}
                    className="flex-1 px-2 py-1 text-[10px] bg-slate-100 hover:bg-slate-200 text-slate-700 rounded"
                  >
                    {t.activo ? 'Pausar' : 'Reactivar'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </aside>
      )}

      {/* === Columna derecha · Audit panel === */}
      {showAudit && isAdmin() && (
        <aside className="w-96 border-l border-slate-200 bg-white/90 flex flex-col" data-testid="audit-panel">
          <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-slate-600" />
              <h3 className="text-sm font-semibold">Audit Logs MCP</h3>
            </div>
            <button onClick={() => setShowAudit(false)} className="text-slate-400 hover:text-slate-700">
              ✕
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {auditLogs.length === 0 && (
              <p className="text-xs text-slate-400 text-center py-4">Sin logs todavía.</p>
            )}
            {auditLogs.map((log, idx) => (
              <div key={idx} className="text-xs p-2 rounded-lg bg-slate-50 border border-slate-100">
                <div className="flex items-center justify-between mb-1">
                  <code className="font-mono text-blue-700">{log.tool}</code>
                  <span className="text-slate-400">{log.duration_ms}ms</span>
                </div>
                <div className="text-slate-600 truncate">agent: {log.agent_id}</div>
                <div className="text-slate-400 text-[10px]">{log.timestamp}</div>
                {log.error && <div className="text-red-600 text-[10px] mt-1">❌ {log.error}</div>}
              </div>
            ))}
          </div>
        </aside>
      )}
    </div>
  );
}

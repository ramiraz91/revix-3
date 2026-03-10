import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';
import { 
  Bot, Send, RefreshCw, AlertTriangle, CheckCircle2,
  Clock, Phone, FileText, TrendingUp, Sparkles,
  MessageSquare, X, Minimize2, Maximize2, ChevronDown
} from 'lucide-react';
import api from '@/lib/api';

export default function AgentARIA() {
  const { user, isAdmin } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [summary, setSummary] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [minimized, setMinimized] = useState(false);
  const messagesEndRef = useRef(null);

  // Cargar resumen inicial
  useEffect(() => {
    if (isAdmin()) {
      loadSummary();
    }
  }, []);

  // Auto-scroll a nuevos mensajes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadSummary = async () => {
    try {
      const res = await api.get('/agent/summary');
      setSummary(res.data.summary);
      setAlerts(res.data.alerts || []);
    } catch (error) {
      console.error('Error cargando resumen:', error);
    }
  };

  const sendMessage = async (e) => {
    e?.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);

    // Agregar mensaje del usuario
    setMessages(prev => [...prev, {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    }]);

    try {
      const res = await api.post('/agent/chat', {
        message: userMessage,
        conversation_id: conversationId
      });

      setConversationId(res.data.conversation_id);
      setAlerts(res.data.alerts || []);

      // Agregar respuesta del agente
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.data.response,
        functions_executed: res.data.functions_executed,
        timestamp: res.data.timestamp
      }]);

    } catch (error) {
      toast.error('Error comunicándose con ARIA');
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Lo siento, ha ocurrido un error. Por favor, intenta de nuevo.',
        timestamp: new Date().toISOString(),
        error: true
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickAction = async (action) => {
    let prompt = '';
    switch (action) {
      case 'resumen':
        prompt = 'Dame un resumen del estado actual del sistema';
        break;
      case 'pendientes':
        prompt = '¿Qué peticiones están pendientes de llamar?';
        break;
      case 'validacion':
        prompt = '¿Qué órdenes están pendientes de validación?';
        break;
      case 'alertas':
        prompt = '¿Hay alertas o problemas que deba atender?';
        break;
      case 'stats':
        prompt = 'Dame las estadísticas de hoy';
        break;
      default:
        return;
    }
    setInput(prompt);
    setTimeout(() => {
      document.querySelector('[data-testid="agent-input"]')?.focus();
    }, 100);
  };

  const newConversation = () => {
    setMessages([]);
    setConversationId(null);
  };

  if (!isAdmin()) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">ARIA</h1>
            <p className="text-sm text-muted-foreground">Asistente Revix de Inteligencia Artificial</p>
          </div>
        </div>
        <Button variant="outline" onClick={loadSummary}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Actualizar
        </Button>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-blue-700">{summary.peticiones?.pendientes_llamar || 0}</p>
                  <p className="text-xs text-blue-600">Llamadas pendientes</p>
                </div>
                <Phone className="w-8 h-8 text-blue-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-amber-50 to-amber-100 border-amber-200">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-amber-700">{summary.ordenes?.por_estado?.validacion || 0}</p>
                  <p className="text-xs text-amber-600">En validación</p>
                </div>
                <Clock className="w-8 h-8 text-amber-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-green-700">{summary.ordenes?.por_estado?.en_taller || 0}</p>
                  <p className="text-xs text-green-600">En taller</p>
                </div>
                <FileText className="w-8 h-8 text-green-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-purple-700">{summary.peticiones?.nuevas_hoy || 0}</p>
                  <p className="text-xs text-purple-600">Peticiones hoy</p>
                </div>
                <TrendingUp className="w-8 h-8 text-purple-400" />
              </div>
            </CardContent>
          </Card>

          <Card className={`border-2 ${(summary.alertas?.total_alertas_sla || 0) > 0 ? 'bg-red-50 border-red-300' : 'bg-slate-50 border-slate-200'}`}>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-2xl font-bold ${(summary.alertas?.total_alertas_sla || 0) > 0 ? 'text-red-700' : 'text-slate-700'}`}>
                    {summary.alertas?.total_alertas_sla || 0}
                  </p>
                  <p className={`text-xs ${(summary.alertas?.total_alertas_sla || 0) > 0 ? 'text-red-600' : 'text-slate-600'}`}>
                    Alertas SLA
                  </p>
                </div>
                <AlertTriangle className={`w-8 h-8 ${(summary.alertas?.total_alertas_sla || 0) > 0 ? 'text-red-400' : 'text-slate-400'}`} />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Alerts Banner */}
      {alerts.length > 0 && (
        <Card className="bg-red-50 border-red-200">
          <CardContent className="py-3">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium text-red-800 mb-2">Alertas activas ({alerts.length})</p>
                <div className="space-y-1">
                  {alerts.slice(0, 3).map((alert, i) => (
                    <p key={i} className="text-sm text-red-700">{alert.mensaje}</p>
                  ))}
                  {alerts.length > 3 && (
                    <p className="text-xs text-red-500">...y {alerts.length - 3} más</p>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Chat Panel */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="w-5 h-5" />
              Chat con ARIA
            </CardTitle>
            {messages.length > 0 && (
              <Button variant="ghost" size="sm" onClick={newConversation}>
                Nueva conversación
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {/* Messages Area */}
            <ScrollArea className="h-[400px] pr-4 mb-4">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-violet-100 to-purple-100 flex items-center justify-center mb-4">
                    <Sparkles className="w-8 h-8 text-violet-500" />
                  </div>
                  <p className="text-lg font-medium mb-2">¡Hola! Soy ARIA</p>
                  <p className="text-sm text-muted-foreground max-w-sm">
                    Tu asistente inteligente para el sistema Revix. Puedo ayudarte con consultas, 
                    ejecutar acciones y mantener todo bajo control.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {messages.map((msg, i) => (
                    <div
                      key={i}
                      className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                          msg.role === 'user'
                            ? 'bg-violet-600 text-white'
                            : msg.error
                              ? 'bg-red-50 text-red-800 border border-red-200'
                              : 'bg-slate-100 text-slate-800'
                        }`}
                      >
                        <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                        {msg.functions_executed?.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-slate-200">
                            <p className="text-xs text-slate-500 flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" />
                              Acciones ejecutadas: {msg.functions_executed.map(f => f.function).join(', ')}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {loading && (
                    <div className="flex justify-start">
                      <div className="bg-slate-100 rounded-2xl px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-violet-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                          <div className="w-2 h-2 bg-violet-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                          <div className="w-2 h-2 bg-violet-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </ScrollArea>

            {/* Input Area */}
            <form onSubmit={sendMessage} className="flex gap-2">
              <Input
                data-testid="agent-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Escribe tu mensaje..."
                disabled={loading}
                className="flex-1"
              />
              <Button type="submit" disabled={loading || !input.trim()}>
                <Send className="w-4 h-4" />
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Quick Actions Panel */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Acciones Rápidas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={() => handleQuickAction('resumen')}
            >
              <FileText className="w-4 h-4 mr-2 text-blue-500" />
              Ver resumen del sistema
            </Button>
            
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={() => handleQuickAction('pendientes')}
            >
              <Phone className="w-4 h-4 mr-2 text-amber-500" />
              Peticiones sin llamar
            </Button>
            
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={() => handleQuickAction('validacion')}
            >
              <Clock className="w-4 h-4 mr-2 text-purple-500" />
              Órdenes en validación
            </Button>
            
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={() => handleQuickAction('alertas')}
            >
              <AlertTriangle className="w-4 h-4 mr-2 text-red-500" />
              Ver alertas activas
            </Button>
            
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={() => handleQuickAction('stats')}
            >
              <TrendingUp className="w-4 h-4 mr-2 text-green-500" />
              Estadísticas de hoy
            </Button>

            <div className="pt-4 border-t mt-4">
              <p className="text-xs text-muted-foreground mb-3">Ejemplos de lo que puedo hacer:</p>
              <div className="space-y-2 text-xs text-muted-foreground">
                <p className="flex items-start gap-2">
                  <span className="text-violet-500">→</span>
                  "Busca la orden ORD-000123"
                </p>
                <p className="flex items-start gap-2">
                  <span className="text-violet-500">→</span>
                  "¿Cuántas órdenes hay en taller?"
                </p>
                <p className="flex items-start gap-2">
                  <span className="text-violet-500">→</span>
                  "Cambia el estado de la orden X a reparado"
                </p>
                <p className="flex items-start gap-2">
                  <span className="text-violet-500">→</span>
                  "Dame las estadísticas de esta semana"
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

import { useState, useRef, useEffect } from 'react';
import { 
  Bot, 
  Send, 
  X, 
  Sparkles, 
  Trash2, 
  Loader2,
  MessageSquare,
  Wand2,
  Stethoscope,
  ChevronDown
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { 
  Sheet, 
  SheetContent, 
  SheetHeader, 
  SheetTitle, 
  SheetTrigger,
  SheetDescription,
} from '@/components/ui/sheet';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { iaAPI } from '@/lib/api';

export default function AsistenteIA() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => `session-${Date.now()}`);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const res = await iaAPI.consulta(userMessage, sessionId);
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.respuesta }]);
    } catch (error) {
      toast.error('Error al comunicar con el asistente');
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Lo siento, hubo un error al procesar tu mensaje. Inténtalo de nuevo.' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = async () => {
    try {
      await iaAPI.limpiarHistorial(sessionId);
      setMessages([]);
      toast.success('Historial limpiado');
    } catch (error) {
      toast.error('Error al limpiar historial');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          className="fixed bottom-20 right-6 h-14 w-14 rounded-full shadow-lg z-40"
          size="icon"
          data-testid="asistente-ia-btn"
        >
          <Bot className="w-6 h-6" />
        </Button>
      </SheetTrigger>
      <SheetContent className="w-[400px] sm:w-[540px] flex flex-col p-0">
        <SheetHeader className="p-4 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <SheetTitle>Asistente IA</SheetTitle>
                <SheetDescription className="text-xs">
                  Gemini 3 Flash
                </SheetDescription>
              </div>
            </div>
            <Button 
              variant="ghost" 
              size="icon"
              onClick={handleClearHistory}
              title="Limpiar historial"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </SheetHeader>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6">
              <Bot className="w-16 h-16 text-muted-foreground/30 mb-4" />
              <h3 className="font-semibold text-lg mb-2">¿En qué puedo ayudarte?</h3>
              <p className="text-sm text-muted-foreground mb-6">
                Soy tu asistente para dudas sobre reparaciones, diagnósticos y gestión del negocio.
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                <Badge 
                  variant="outline" 
                  className="cursor-pointer hover:bg-slate-100"
                  onClick={() => setInput('¿Cómo diagnostico un iPhone que no enciende?')}
                >
                  Diagnóstico iPhone
                </Badge>
                <Badge 
                  variant="outline" 
                  className="cursor-pointer hover:bg-slate-100"
                  onClick={() => setInput('¿Cuáles son los problemas más comunes en Samsung?')}
                >
                  Problemas Samsung
                </Badge>
                <Badge 
                  variant="outline" 
                  className="cursor-pointer hover:bg-slate-100"
                  onClick={() => setInput('Consejos para gestionar el inventario')}
                >
                  Gestión inventario
                </Badge>
              </div>
            </div>
          ) : (
            messages.map((msg, index) => (
              <div 
                key={index}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div 
                  className={`max-w-[85%] rounded-2xl px-4 py-2 ${
                    msg.role === 'user' 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-slate-100'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-100 rounded-2xl px-4 py-3">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t bg-white">
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Escribe tu pregunta..."
              disabled={loading}
              className="flex-1"
              data-testid="ia-input"
            />
            <Button 
              onClick={handleSend} 
              disabled={loading || !input.trim()}
              data-testid="ia-send-btn"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

// Componente para mejorar texto con IA
export function MejorarTextoIA({ texto, onMejorado, contexto }) {
  const [loading, setLoading] = useState(false);

  const handleMejorar = async () => {
    if (!texto?.trim()) {
      toast.error('No hay texto para mejorar');
      return;
    }

    setLoading(true);
    try {
      const res = await iaAPI.mejorarTexto(texto, 'mejorar', contexto);
      if (onMejorado) {
        onMejorado(res.data.texto_mejorado);
      }
      toast.success('Texto mejorado con IA');
    } catch (error) {
      toast.error('Error al mejorar texto');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      onClick={handleMejorar}
      disabled={loading || !texto?.trim()}
      className="gap-1 text-xs"
    >
      {loading ? (
        <Loader2 className="w-3 h-3 animate-spin" />
      ) : (
        <Wand2 className="w-3 h-3" />
      )}
      Mejorar con IA
    </Button>
  );
}

// Componente de diagnóstico IA
export function DiagnosticoIA({ modelo, sintomas, onDiagnostico }) {
  const [loading, setLoading] = useState(false);

  const handleDiagnostico = async () => {
    if (!modelo?.trim() || !sintomas?.trim()) {
      toast.error('Introduce el modelo y los síntomas');
      return;
    }

    setLoading(true);
    try {
      const res = await iaAPI.diagnostico(modelo, sintomas);
      if (onDiagnostico) {
        onDiagnostico(res.data.diagnostico);
      }
      toast.success('Diagnóstico generado');
    } catch (error) {
      toast.error('Error al generar diagnóstico');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      type="button"
      variant="outline"
      onClick={handleDiagnostico}
      disabled={loading}
      className="gap-2"
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <Stethoscope className="w-4 h-4" />
      )}
      Diagnóstico IA
    </Button>
  );
}

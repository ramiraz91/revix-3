import { useState, useEffect } from 'react';
import { MessageSquare, Send } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { ordenesAPI } from '@/lib/api';
import { toast } from 'sonner';

export function TecnicoMensajesCard({ orden, mensajes, onRefresh, onMensajeAdd }) {
  const [nuevoMensaje, setNuevoMensaje] = useState('');
  const [enviandoMensaje, setEnviandoMensaje] = useState(false);
  
  // Estado local de mensajes para actualización inmediata
  const [localMensajes, setLocalMensajes] = useState(mensajes || []);
  
  // Sincronizar cuando cambian los mensajes desde el padre
  useEffect(() => {
    setLocalMensajes(mensajes || []);
  }, [mensajes]);

  const handleEnviarMensaje = async () => {
    if (!nuevoMensaje.trim()) return;
    
    setEnviandoMensaje(true);
    try {
      const response = await ordenesAPI.añadirMensaje(orden.id, {
        mensaje: nuevoMensaje.trim(),
        visible_tecnico: true
      });
      
      // Extraer el objeto mensaje de la respuesta
      // El backend devuelve: { message: "...", mensaje: {...} }
      const nuevoMsgObj = response?.data?.mensaje || {
        mensaje: nuevoMensaje.trim(),
        rol: 'tecnico',
        autor_nombre: 'Técnico',
        fecha: new Date().toISOString(),
        visible_tecnico: true
      };
      
      // Actualizar estado local
      setLocalMensajes(prev => [...prev, nuevoMsgObj]);
      if (onMensajeAdd) onMensajeAdd(nuevoMsgObj);
      
      setNuevoMensaje('');
      toast.success('Mensaje enviado');
    } catch (error) {
      toast.error('Error al enviar mensaje');
    } finally {
      setEnviandoMensaje(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5" />
          Comunicaciones
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3 max-h-64 overflow-y-auto mb-4">
          {localMensajes.length === 0 ? (
            <p className="text-center text-muted-foreground py-4">
              No hay mensajes en esta orden
            </p>
          ) : (
            localMensajes.map((msg, index) => (
              <div 
                key={index}
                className={`p-3 rounded-lg ${
                  msg.rol === 'admin' 
                    ? 'bg-blue-50 border-l-4 border-l-blue-500' 
                    : 'bg-slate-50 border-l-4 border-l-slate-400'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-sm">{msg.autor_nombre}</span>
                  <Badge variant="outline" className="text-[10px]">
                    {msg.rol === 'admin' ? 'Admin' : 'Técnico'}
                  </Badge>
                  <span className="text-xs text-muted-foreground ml-auto">
                    {new Date(msg.fecha).toLocaleString('es-ES', {
                      day: '2-digit',
                      month: 'short',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                </div>
                <p className="text-sm">{msg.mensaje}</p>
              </div>
            ))
          )}
        </div>

        <Separator className="my-4" />
        <div className="flex gap-2">
          <Textarea
            placeholder="Escribe un mensaje..."
            value={nuevoMensaje}
            onChange={(e) => setNuevoMensaje(e.target.value)}
            rows={2}
            className="flex-1"
          />
          <Button 
            onClick={handleEnviarMensaje}
            disabled={enviandoMensaje || !nuevoMensaje.trim()}
            className="self-end"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

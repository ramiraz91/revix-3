import { MessageSquare, Send, Eye, EyeOff } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';

export function OrdenMensajesTab({
  mensajes,
  nuevoMensaje,
  setNuevoMensaje,
  mensajeVisibleTecnico,
  setMensajeVisibleTecnico,
  onEnviarMensaje,
  enviandoMensaje,
  isAdmin
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5" />
          Mensajes Internos
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Lista de mensajes */}
        <div className="space-y-4 mb-6 max-h-96 overflow-y-auto">
          {mensajes.length === 0 ? (
            <p className="text-center text-muted-foreground py-4">No hay mensajes</p>
          ) : (
            mensajes.map((msg, index) => (
              <div 
                key={index}
                className={`p-3 rounded-lg ${
                  msg.autor?.includes('tecnico') || msg.autor?.includes('Técnico')
                    ? 'bg-purple-50 border-l-4 border-purple-500'
                    : 'bg-blue-50 border-l-4 border-blue-500'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-sm">{msg.autor}</span>
                  <div className="flex items-center gap-2">
                    {msg.visible_tecnico !== undefined && (
                      <Badge variant="outline" className="text-xs">
                        {msg.visible_tecnico ? (
                          <><Eye className="w-3 h-3 mr-1" /> Visible técnico</>
                        ) : (
                          <><EyeOff className="w-3 h-3 mr-1" /> Solo admin</>
                        )}
                      </Badge>
                    )}
                    <span className="text-xs text-muted-foreground">
                      {new Date(msg.fecha).toLocaleString('es-ES')}
                    </span>
                  </div>
                </div>
                <p className="text-sm whitespace-pre-wrap">{msg.mensaje}</p>
              </div>
            ))
          )}
        </div>

        {/* Formulario de nuevo mensaje */}
        <div className="space-y-3 pt-4 border-t">
          <Textarea
            placeholder="Escribe un mensaje..."
            value={nuevoMensaje}
            onChange={(e) => setNuevoMensaje(e.target.value)}
            rows={2}
          />
          <div className="flex items-center justify-between">
            {isAdmin && (
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="visible-tecnico"
                  checked={mensajeVisibleTecnico}
                  onCheckedChange={setMensajeVisibleTecnico}
                />
                <label
                  htmlFor="visible-tecnico"
                  className="text-sm font-medium leading-none cursor-pointer"
                >
                  Visible para técnico
                </label>
              </div>
            )}
            <Button 
              onClick={onEnviarMensaje}
              disabled={enviandoMensaje || !nuevoMensaje.trim()}
              size="sm"
            >
              <Send className="w-4 h-4 mr-2" />
              {enviandoMensaje ? 'Enviando...' : 'Enviar'}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

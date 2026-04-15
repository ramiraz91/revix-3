import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Shield, RefreshCw, MessageSquare, ArrowUpRight, ArrowDownLeft } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export function OrdenInsuramaPanel({ orden, onRefresh }) {
  const [refreshing, setRefreshing] = useState(false);
  const [showAll, setShowAll] = useState(false);

  if (!orden.numero_autorizacion) return null;

  const handleRefreshData = async () => {
    setRefreshing(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API}/api/insurama/orden/${orden.id}/refrescar`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Error al refrescar datos');
      }
      const data = await res.json();
      toast.success('Datos actualizados desde Insurama', {
        description: `Cliente: ${data.cliente_actualizado?.ciudad || 'Sin ciudad'}, CP: ${data.cliente_actualizado?.codigo_postal || 'Sin CP'}`
      });
      if (onRefresh) onRefresh();
    } catch (error) {
      toast.error('Error al refrescar datos', { description: error.message });
    } finally {
      setRefreshing(false);
    }
  };

  // Obtener observaciones/comunicaciones
  const observations = (orden.datos_portal?.observations || [])
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

  const STORE_ID = 'REVIX0SC';
  const visibleObs = showAll ? observations : observations.slice(0, 5);

  const fmtDate = (d) => {
    if (!d) return '';
    return new Date(d).toLocaleString('es-ES', {
      day: '2-digit', month: '2-digit', year: '2-digit',
      hour: '2-digit', minute: '2-digit',
    });
  };

  return (
    <Card className="border-blue-200 bg-blue-50/30" data-testid="insurama-history-panel">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-blue-700 text-sm">
            <Shield className="w-4 h-4" />
            Insurama — {orden.numero_autorizacion}
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefreshData}
            disabled={refreshing}
            className="h-7 text-xs border-blue-300 text-blue-700 hover:bg-blue-100"
            data-testid="refresh-insurama-btn"
          >
            <RefreshCw className={`w-3 h-3 mr-1 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Actualizando...' : 'Refrescar datos'}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Fechas de sincronización */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          {orden.insurama_sync_recibida && (
            <div className="p-2 bg-green-50 border border-green-200 rounded">
              <p className="text-green-600 font-medium">Recibida</p>
              <p className="text-green-700">{new Date(orden.insurama_sync_recibida).toLocaleDateString('es-ES')}</p>
            </div>
          )}
          {orden.insurama_sync_en_taller && (
            <div className="p-2 bg-yellow-50 border border-yellow-200 rounded">
              <p className="text-yellow-600 font-medium">En taller</p>
              <p className="text-yellow-700">{new Date(orden.insurama_sync_en_taller).toLocaleDateString('es-ES')}</p>
            </div>
          )}
          {orden.insurama_sync_reparado && (
            <div className="p-2 bg-purple-50 border border-purple-200 rounded">
              <p className="text-purple-600 font-medium">Reparado</p>
              <p className="text-purple-700">{new Date(orden.insurama_sync_reparado).toLocaleDateString('es-ES')}</p>
            </div>
          )}
          {orden.insurama_sync_enviado && (
            <div className="p-2 bg-blue-50 border border-blue-200 rounded">
              <p className="text-blue-600 font-medium">Enviado</p>
              <p className="text-blue-700">{new Date(orden.insurama_sync_enviado).toLocaleDateString('es-ES')}</p>
            </div>
          )}
        </div>

        {/* Comunicaciones Insurama */}
        {observations.length > 0 && (
          <div data-testid="insurama-communications">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-blue-800 flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5" />
                Comunicaciones ({observations.length})
              </p>
            </div>
            <div className="space-y-2">
              {visibleObs.map((obs, i) => {
                const isIncoming = obs.receiver_identifier === STORE_ID || obs.receiver_identifier === 'REVIX.ES';
                const isFromInsurama = !obs.user_name?.includes('REVIX');
                const sender = obs.user_name || 'Desconocido';
                const text = obs.observations || '';
                const date = fmtDate(obs.created_at);

                return (
                  <div
                    key={obs.id || i}
                    className={`p-2.5 rounded-lg border text-xs ${
                      isFromInsurama
                        ? 'bg-amber-50 border-amber-200'
                        : 'bg-slate-50 border-slate-200'
                    }`}
                    data-testid={`insurama-msg-${i}`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1.5">
                        {isFromInsurama ? (
                          <ArrowDownLeft className="w-3 h-3 text-amber-600" />
                        ) : (
                          <ArrowUpRight className="w-3 h-3 text-slate-500" />
                        )}
                        <span className={`font-semibold ${isFromInsurama ? 'text-amber-700' : 'text-slate-600'}`}>
                          {sender}
                        </span>
                        {isFromInsurama && (
                          <Badge variant="outline" className="text-[9px] h-4 px-1 border-amber-300 text-amber-600">
                            Insurama
                          </Badge>
                        )}
                      </div>
                      <span className="text-[10px] text-muted-foreground">{date}</span>
                    </div>
                    <p className={`leading-relaxed ${isFromInsurama ? 'text-amber-900' : 'text-slate-700'}`}>
                      {text}
                    </p>
                  </div>
                );
              })}
            </div>
            {observations.length > 5 && (
              <Button
                variant="ghost"
                size="sm"
                className="w-full mt-2 text-xs text-blue-600 hover:text-blue-800"
                onClick={() => setShowAll(!showAll)}
                data-testid="toggle-all-messages"
              >
                {showAll ? 'Ver menos' : `Ver todas (${observations.length})`}
              </Button>
            )}
          </div>
        )}

        {observations.length === 0 && (
          <p className="text-xs text-muted-foreground italic">Sin comunicaciones registradas</p>
        )}

        {/* Notas sync y diagnostico */}
        {orden.datos_portal_sync && (
          <p className="text-[10px] text-muted-foreground">
            Ultima sincronizacion: {new Date(orden.datos_portal_sync).toLocaleString('es-ES')}
          </p>
        )}
        {orden.insurama_diagnostico_enviado && (
          <p className="text-[10px] text-green-600">Diagnostico sincronizado con Insurama</p>
        )}
        {(orden.notas_insurama || []).length > 0 && (
          <div className="space-y-1">
            <p className="text-[10px] text-muted-foreground font-medium">Notas sync:</p>
            {orden.notas_insurama.map((nota, i) => (
              <p key={i} className="text-[10px] text-slate-600 pl-2 border-l-2 border-blue-200">
                <span className="text-muted-foreground">{new Date(nota.fecha).toLocaleDateString('es-ES')}</span> — {nota.mensaje}
              </p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

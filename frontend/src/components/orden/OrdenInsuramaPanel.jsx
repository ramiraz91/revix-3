import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Shield, RefreshCw } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export function OrdenInsuramaPanel({ orden, onRefresh }) {
  const [refreshing, setRefreshing] = useState(false);

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
      
      // Recargar la orden si hay callback
      if (onRefresh) {
        onRefresh();
      }
    } catch (error) {
      console.error('Error refreshing Insurama data:', error);
      toast.error('Error al refrescar datos', {
        description: error.message
      });
    } finally {
      setRefreshing(false);
    }
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
      <CardContent className="space-y-3">
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
        {orden.datos_portal_sync && (
          <p className="text-xs text-muted-foreground">
            Última sincronización: {new Date(orden.datos_portal_sync).toLocaleString('es-ES')}
          </p>
        )}
        {orden.insurama_diagnostico_enviado && (
          <p className="text-xs text-green-600">Diagnóstico sincronizado con Insurama</p>
        )}
        {(orden.notas_insurama || []).length > 0 && (
          <div className="space-y-1 mt-2">
            <p className="text-xs text-muted-foreground font-medium">Notas sync:</p>
            {orden.notas_insurama.map((nota, i) => (
              <p key={i} className="text-xs text-slate-600 pl-2 border-l-2 border-blue-200">
                <span className="text-muted-foreground">{new Date(nota.fecha).toLocaleDateString('es-ES')}</span> — {nota.mensaje}
              </p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

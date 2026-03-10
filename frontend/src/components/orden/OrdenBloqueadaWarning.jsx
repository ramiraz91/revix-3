import { Lock, Check } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export function OrdenBloqueadaWarning({ orden, onAbrirDesbloqueo }) {
  if (!orden.bloqueada) return null;

  return (
    <Card className="border-red-500 border-2 bg-red-50">
      <CardContent className="py-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <Lock className="w-8 h-8 text-red-500" />
            <div>
              <p className="font-semibold text-red-700">Orden Bloqueada</p>
              <p className="text-sm text-red-600">
                {orden.motivo_bloqueo === 'IMEI no coincide' 
                  ? `⚠️ IMEI no coincide - Escaneado: ${orden.imei_escaneado_incorrecto || 'N/A'}`
                  : 'El técnico ha añadido materiales que requieren tu validación.'}
              </p>
            </div>
          </div>
          <Button onClick={onAbrirDesbloqueo} className="bg-green-600 hover:bg-green-700" data-testid="btn-desbloquear">
            <Check className="w-4 h-4 mr-2" />
            Revisar y Desbloquear
          </Button>
        </div>
        
        {/* Resumen del bloqueo actual */}
        {orden.motivo_bloqueo === 'IMEI no coincide' && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg mb-4">
            <p className="text-sm font-medium text-amber-800 mb-2">Discrepancia detectada:</p>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-amber-600">IMEI Escaneado por Técnico:</p>
                <p className="font-mono font-bold text-red-600">{orden.imei_escaneado_incorrecto || 'N/A'}</p>
              </div>
              <div>
                <p className="text-amber-600">IMEI Registrado en Sistema:</p>
                <p className="font-mono font-bold text-blue-600">{orden.dispositivo?.imei || 'N/A'}</p>
              </div>
            </div>
          </div>
        )}
        
        {/* Historial de Bloqueos resumido */}
        {orden.historial_bloqueos && orden.historial_bloqueos.length > 0 && (
          <div className="mt-4 pt-4 border-t border-red-200">
            <p className="text-sm font-medium text-red-700 mb-2">Historial de Bloqueos ({orden.historial_bloqueos.length})</p>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {orden.historial_bloqueos.slice().reverse().map((bloqueo, idx) => (
                <div key={bloqueo.id || idx} className={`text-xs p-2 rounded ${bloqueo.resuelto ? 'bg-green-50 border border-green-200' : 'bg-red-100 border border-red-300'}`}>
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="font-medium">{bloqueo.motivo}</span>
                      {bloqueo.imei_escaneado && (
                        <span className="text-red-600 ml-2">
                          (Escaneado: {bloqueo.imei_escaneado} | Esperado: {bloqueo.imei_esperado})
                        </span>
                      )}
                    </div>
                    <span className={bloqueo.resuelto ? 'text-green-600' : 'text-red-600'}>
                      {bloqueo.resuelto ? '✅ Resuelto' : '🔒 Activo'}
                    </span>
                  </div>
                  <div className="mt-1 text-muted-foreground">
                    {new Date(bloqueo.fecha_bloqueo).toLocaleString('es-ES')}
                    {bloqueo.resuelto && bloqueo.fecha_resolucion && (
                      <span className="ml-2 text-green-600">
                        → Resuelto: {new Date(bloqueo.fecha_resolucion).toLocaleString('es-ES')}
                      </span>
                    )}
                  </div>
                  {bloqueo.notas_resolucion && (
                    <div className="mt-1 text-green-700 italic">
                      "{bloqueo.notas_resolucion}"
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

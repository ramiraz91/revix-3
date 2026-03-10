import { Lock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function OrdenBloqueosTab({ orden }) {
  const historial = orden.historial_bloqueos || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lock className="w-5 h-5" />
          Historial de Bloqueos
        </CardTitle>
      </CardHeader>
      <CardContent>
        {historial.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">
            Esta orden no tiene historial de bloqueos.
          </p>
        ) : (
          <div className="space-y-4">
            {historial.slice().reverse().map((bloqueo, idx) => (
              <div 
                key={bloqueo.id || idx} 
                className={`p-4 rounded-lg border-2 ${
                  bloqueo.resuelto 
                    ? 'bg-green-50 border-green-200' 
                    : 'bg-red-50 border-red-300'
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <span className="font-bold text-lg">{bloqueo.motivo}</span>
                    <span className={`ml-3 px-2 py-0.5 rounded text-xs font-medium ${
                      bloqueo.resuelto 
                        ? 'bg-green-200 text-green-800' 
                        : 'bg-red-200 text-red-800'
                    }`}>
                      {bloqueo.resuelto ? '✅ RESUELTO' : '🔒 ACTIVO'}
                    </span>
                  </div>
                </div>
                
                {/* Detalles del IMEI si aplica */}
                {bloqueo.imei_escaneado && (
                  <div className="mt-2 p-3 bg-white rounded border">
                    <p className="text-sm font-medium text-gray-700 mb-2">Discrepancia de IMEI:</p>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-red-600">Escaneado:</span>
                        <span className="ml-2 font-mono font-bold">{bloqueo.imei_escaneado}</span>
                      </div>
                      <div>
                        <span className="text-blue-600">Esperado:</span>
                        <span className="ml-2 font-mono font-bold">{bloqueo.imei_esperado}</span>
                      </div>
                    </div>
                    {bloqueo.imei_actualizado && (
                      <div className="mt-2 pt-2 border-t">
                        <span className="text-green-600 text-sm font-medium">
                          ✓ IMEI actualizado a: <span className="font-mono">{bloqueo.imei_nuevo}</span>
                        </span>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Fechas */}
                <div className="mt-3 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <span>📅 Bloqueado:</span>
                    <span>{new Date(bloqueo.fecha_bloqueo).toLocaleString('es-ES')}</span>
                  </div>
                  {bloqueo.resuelto && bloqueo.fecha_resolucion && (
                    <div className="flex items-center gap-2 mt-1 text-green-700">
                      <span>✅ Resuelto:</span>
                      <span>{new Date(bloqueo.fecha_resolucion).toLocaleString('es-ES')}</span>
                      {bloqueo.resuelto_por && (
                        <span className="ml-2">por <strong>{bloqueo.resuelto_por}</strong></span>
                      )}
                    </div>
                  )}
                </div>
                
                {/* Notas de resolución */}
                {bloqueo.notas_resolucion && (
                  <div className="mt-3 p-3 bg-green-100 rounded border border-green-300">
                    <p className="text-sm font-medium text-green-800 mb-1">Notas de resolución:</p>
                    <p className="text-sm text-green-700 italic">"{bloqueo.notas_resolucion}"</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

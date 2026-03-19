import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Clock, Truck } from 'lucide-react';

export function OrdenHistorialEstados({ historial, statusConfig }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="w-5 h-5" />
          Historial de Estados
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!historial?.length ? (
          <p className="text-center text-muted-foreground py-4">Sin historial</p>
        ) : (
          <div className="space-y-3">
            {historial.slice().reverse().map((entry, index) => {
              const isLogistica = entry.tipo === 'logistica';
              const dotColor = isLogistica
                ? 'bg-orange-400'
                : (statusConfig[entry.estado]?.color || 'bg-slate-300');
              const label = isLogistica
                ? entry.detalle || 'Evento de logistica'
                : (statusConfig[entry.estado]?.label || entry.estado);

              return (
                <div key={index} className="flex items-start gap-3">
                  <div className={`w-3 h-3 rounded-full mt-1.5 flex-shrink-0 ${dotColor}`} />
                  <div className="flex-1 min-w-0">
                    {isLogistica ? (
                      <div className="flex items-center gap-1.5">
                        <Truck className="w-3.5 h-3.5 text-orange-600 flex-shrink-0" />
                        <p className="font-medium text-sm text-orange-800 truncate">{label}</p>
                      </div>
                    ) : (
                      <p className="font-medium">{label}</p>
                    )}
                    <p className="text-sm text-muted-foreground">
                      {new Date(entry.fecha).toLocaleString('es-ES')} - {entry.usuario}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

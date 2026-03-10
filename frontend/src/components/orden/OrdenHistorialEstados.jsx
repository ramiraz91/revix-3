import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Clock } from 'lucide-react';

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
            {historial.slice().reverse().map((entry, index) => (
              <div key={index} className="flex items-start gap-3">
                <div className={`w-3 h-3 rounded-full mt-1.5 ${statusConfig[entry.estado]?.color || 'bg-slate-300'}`} />
                <div className="flex-1">
                  <p className="font-medium">{statusConfig[entry.estado]?.label || entry.estado}</p>
                  <p className="text-sm text-muted-foreground">
                    {new Date(entry.fecha).toLocaleString('es-ES')} - {entry.usuario}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

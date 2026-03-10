import { Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

export function InsuramaObservacionesTab({ observaciones, loading }) {
  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="pt-6">
        {observaciones.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">
            No hay observaciones
          </p>
        ) : (
          <div className="space-y-4">
            {observaciones.map((obs, idx) => (
              <div key={idx} className="p-4 rounded-lg bg-muted/50 border">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{obs.user_name || 'Sistema'}</span>
                  <span className="text-xs text-muted-foreground">
                    {obs.created_at ? new Date(obs.created_at).toLocaleString('es-ES') : ''}
                  </span>
                </div>
                <p className="text-sm">{obs.observation || obs.message}</p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

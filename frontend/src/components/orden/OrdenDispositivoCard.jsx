import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Smartphone } from 'lucide-react';

export function OrdenDispositivoCard({ dispositivo }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Smartphone className="w-5 h-5" />
          Dispositivo
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Modelo</p>
            <p className="font-medium">{dispositivo?.modelo}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">IMEI</p>
            <p className="font-mono">{dispositivo?.imei || '-'}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Color</p>
            <p>{dispositivo?.color || '-'}</p>
          </div>
          <div className="sm:col-span-3">
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Daños / Avería</p>
            <p className="mt-1">{dispositivo?.daños}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

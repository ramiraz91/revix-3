import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Smartphone, Pencil } from 'lucide-react';

/**
 * Parsea un campo IMEI que puede contener uno o dos IMEIs separados por "//"
 * Ejemplo: "123456789123456 // 152345678912345" → ["123456789123456", "152345678912345"]
 */
function parseIMEIs(imeiField) {
  if (!imeiField) return [];
  const parts = imeiField.split('//').map(s => s.trim()).filter(Boolean);
  return parts;
}

export function OrdenDispositivoCard({ dispositivo, onEdit }) {
  const imeis = parseIMEIs(dispositivo?.imei);
  const hasMultipleIMEIs = imeis.length > 1;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Smartphone className="w-5 h-5" />
          Dispositivo
          {onEdit && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="ml-auto h-7 px-2 gap-1 text-xs"
              onClick={onEdit}
              data-testid="btn-editar-dispositivo"
            >
              <Pencil className="w-3.5 h-3.5" />
              Editar
            </Button>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Modelo</p>
            <p className="font-medium">{dispositivo?.modelo}</p>
          </div>
          <div className={hasMultipleIMEIs ? 'sm:col-span-2' : ''}>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">
              {hasMultipleIMEIs ? 'IMEIs' : 'IMEI'}
            </p>
            {hasMultipleIMEIs ? (
              <div className="flex flex-col gap-1 mt-1">
                {imeis.map((imei, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs px-1.5 py-0">IMEI {idx + 1}</Badge>
                    <span className="font-mono text-sm" data-testid={`dispositivo-imei-${idx + 1}`}>{imei}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="font-mono" data-testid="dispositivo-imei-1">{imeis[0] || '-'}</p>
            )}
          </div>
          {!hasMultipleIMEIs && (
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Color</p>
              <p>{dispositivo?.color || '-'}</p>
            </div>
          )}
          {hasMultipleIMEIs && (
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Color</p>
              <p>{dispositivo?.color || '-'}</p>
            </div>
          )}
          <div className="sm:col-span-3">
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Daños / Avería</p>
            <p className="mt-1">{dispositivo?.daños}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

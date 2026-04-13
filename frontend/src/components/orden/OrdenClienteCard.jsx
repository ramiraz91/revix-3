import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { User, MapPin } from 'lucide-react';

export function OrdenClienteCard({ cliente, onEdit }) {
  // Construir dirección completa
  const buildFullAddress = () => {
    if (!cliente) return '-';
    const parts = [
      cliente.direccion,
      cliente.planta && `Planta ${cliente.planta}`,
      cliente.puerta && `Puerta ${cliente.puerta}`
    ].filter(Boolean);
    return parts.join(' ') || '-';
  };

  const buildLocation = () => {
    if (!cliente) return null;
    const parts = [
      cliente.codigo_postal,
      cliente.ciudad || cliente.localidad || cliente.poblacion,
      cliente.provincia && `(${cliente.provincia})`
    ].filter(Boolean);
    return parts.length > 0 ? parts.join(' ') : null;
  };

  const location = buildLocation();

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <User className="w-5 h-5" />
          Cliente
        </CardTitle>
        {cliente && (
          <Button variant="outline" size="sm" onClick={onEdit} data-testid="edit-cliente-btn">
            Editar
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {cliente ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Nombre</p>
              <p className="font-medium">{cliente.nombre} {cliente.apellidos}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">DNI</p>
              <p className="font-mono">{cliente.dni}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Teléfono</p>
              <p>{cliente.telefono}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Email</p>
              <p>{cliente.email || '-'}</p>
            </div>
            <div className="sm:col-span-2">
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Dirección</p>
              <p>{buildFullAddress()}</p>
              {location && (
                <p className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
                  <MapPin className="w-3 h-3" />
                  {location}
                </p>
              )}
            </div>
          </div>
        ) : (
          <p className="text-muted-foreground">Cliente no encontrado</p>
        )}
      </CardContent>
    </Card>
  );
}

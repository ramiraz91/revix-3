import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { User } from 'lucide-react';

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
              <p className="font-mono">{cliente.dni || '-'}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Teléfono</p>
              <p>{cliente.telefono || '-'}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Email</p>
              <p>{cliente.email || '-'}</p>
            </div>
            <div className="sm:col-span-2">
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Dirección</p>
              <p>{buildFullAddress()}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Código Postal</p>
              <p>{cliente.codigo_postal || '-'}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Ciudad / Localidad</p>
              <p>{cliente.ciudad || cliente.localidad || cliente.poblacion || '-'}</p>
            </div>
            {cliente.provincia && (
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">Provincia</p>
                <p>{cliente.provincia}</p>
              </div>
            )}
          </div>
        ) : (
          <p className="text-muted-foreground">Cliente no encontrado</p>
        )}
      </CardContent>
    </Card>
  );
}

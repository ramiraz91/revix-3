import { Phone, Mail, MapPin } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

export function InsuramaClienteTab({ presupuestoDetalle }) {
  return (
    <Card>
      <CardContent className="pt-6 space-y-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
            <span className="text-2xl font-bold text-primary">
              {presupuestoDetalle.client_name?.charAt(0) || '?'}
            </span>
          </div>
          <div>
            <h3 className="text-xl font-bold">{presupuestoDetalle.client_full_name}</h3>
            <p className="text-muted-foreground">DNI/NIF: {presupuestoDetalle.client_nif || 'N/A'}</p>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4 pt-4 border-t">
          <div className="flex items-center gap-3">
            <Phone className="w-5 h-5 text-muted-foreground" />
            <div>
              <p className="text-sm text-muted-foreground">Teléfono</p>
              <p className="font-medium">{presupuestoDetalle.client_phone || 'N/A'}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Mail className="w-5 h-5 text-muted-foreground" />
            <div>
              <p className="text-sm text-muted-foreground">Email</p>
              <p className="font-medium">{presupuestoDetalle.client_email || 'N/A'}</p>
            </div>
          </div>
        </div>
        
        <div className="flex items-start gap-3 pt-4 border-t">
          <MapPin className="w-5 h-5 text-muted-foreground mt-1" />
          <div>
            <p className="text-sm text-muted-foreground">Dirección</p>
            <p className="font-medium">{presupuestoDetalle.client_address}</p>
            <p className="text-muted-foreground">
              {presupuestoDetalle.client_zip} {presupuestoDetalle.client_city}, {presupuestoDetalle.client_province}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

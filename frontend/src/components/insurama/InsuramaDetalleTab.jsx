import { 
  FileText, 
  Smartphone, 
  Clock, 
  Download, 
  Import, 
  Loader2 
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export function InsuramaDetalleTab({ 
  presupuestoDetalle, 
  onDescargarFotos, 
  onImportar, 
  importando 
}) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Información del Siniestro
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Código:</span>
              <span className="font-mono font-bold">{presupuestoDetalle.claim_identifier}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Estado:</span>
              <Badge>{presupuestoDetalle.status_text}</Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Tipo:</span>
              <span>{presupuestoDetalle.claim_type_text}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Póliza:</span>
              <span className="font-mono">{presupuestoDetalle.policy_number}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Producto:</span>
              <span>{presupuestoDetalle.product_name}</span>
            </div>
            {presupuestoDetalle.price && (
              <div className="flex justify-between pt-2 border-t">
                <span className="text-muted-foreground">Precio:</span>
                <span className="font-bold text-green-600">{presupuestoDetalle.price}€</span>
              </div>
            )}
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Smartphone className="w-4 h-4" />
              Dispositivo
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Marca:</span>
              <span className="font-medium">{presupuestoDetalle.device_brand}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Modelo:</span>
              <span className="font-medium">{presupuestoDetalle.device_model}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Color:</span>
              <span>{presupuestoDetalle.device_colour}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">IMEI:</span>
              <span className="font-mono text-xs">{presupuestoDetalle.device_imei || 'N/A'}</span>
            </div>
            <div className="pt-2 border-t">
              <p className="text-muted-foreground mb-1">Daño reportado:</p>
              <p className="text-sm">{presupuestoDetalle.damage_description}</p>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Fechas y tracking */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Fechas y Envío
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Recogida</p>
              <p className="font-medium">{presupuestoDetalle.pickup_date || '-'}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Reparación</p>
              <p className="font-medium">{presupuestoDetalle.repair_date || '-'}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Envío</p>
              <p className="font-medium">{presupuestoDetalle.shipping_date || '-'}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Tracking</p>
              <p className="font-mono">{presupuestoDetalle.tracking_number || '-'}</p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Acciones */}
      <div className="flex justify-end gap-2 pt-4 border-t">
        <Button variant="outline" onClick={() => onDescargarFotos(presupuestoDetalle.claim_identifier)}>
          <Download className="w-4 h-4 mr-2" />
          Descargar Fotos
        </Button>
        <Button 
          onClick={() => onImportar(presupuestoDetalle.claim_identifier)}
          disabled={importando}
        >
          {importando ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Import className="w-4 h-4 mr-2" />}
          Importar al CRM
        </Button>
      </div>
    </div>
  );
}

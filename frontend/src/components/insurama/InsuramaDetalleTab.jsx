import { 
  FileText, 
  Smartphone, 
  Clock, 
  Download, 
  Import, 
  Loader2,
  Shield,
  DollarSign,
  AlertTriangle
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
  const precio = parseFloat(presupuestoDetalle.price || 0);
  const reserveValue = parseFloat(presupuestoDetalle.reserve_value || 0);
  const margen = reserveValue > 0 && precio > 0 ? ((reserveValue - precio) / reserveValue * 100).toFixed(1) : null;

  return (
    <div className="space-y-4">
      {/* Banner de valor máximo del siniestro */}
      {reserveValue > 0 && (
        <Card className={`border-2 ${precio > reserveValue ? 'border-red-300 bg-red-50' : 'border-blue-300 bg-blue-50'}`}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Shield className="w-6 h-6 text-blue-600" />
                <div>
                  <p className="text-sm font-medium text-blue-900">Valor máximo del siniestro (reserva aseguradora)</p>
                  <p className="text-3xl font-bold text-blue-700">{reserveValue.toFixed(2)}€</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted-foreground">Tu precio: <span className="font-bold text-green-600">{precio.toFixed(2)}€</span></p>
                {margen !== null && (
                  <Badge className={precio > reserveValue ? 'bg-red-200 text-red-800' : 'bg-green-200 text-green-800'}>
                    {precio > reserveValue ? (
                      <><AlertTriangle className="w-3 h-3 mr-1" /> Excedes el máximo</>
                    ) : (
                      <>Margen: {margen}%</>
                    )}
                  </Badge>
                )}
                {presupuestoDetalle.claim_real_value && parseFloat(presupuestoDetalle.claim_real_value) > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Valor real reclamación: {parseFloat(presupuestoDetalle.claim_real_value).toFixed(2)}€
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

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
            {presupuestoDetalle.internal_status_text && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Estado interno:</span>
                <Badge variant="outline" className="text-xs">{presupuestoDetalle.internal_status_text}</Badge>
              </div>
            )}
            {presupuestoDetalle.external_status_text && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Estado externo:</span>
                <Badge variant="outline" className="text-xs">{presupuestoDetalle.external_status_text}</Badge>
              </div>
            )}
            {presupuestoDetalle.price && (
              <div className="flex justify-between pt-2 border-t">
                <span className="text-muted-foreground">Mi Precio:</span>
                <span className="font-bold text-green-600">{presupuestoDetalle.price}€</span>
              </div>
            )}
            {presupuestoDetalle.repair_type_text && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Tipo recambio:</span>
                <span>{presupuestoDetalle.repair_type_text}</span>
              </div>
            )}
            {presupuestoDetalle.warranty_type_text && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Garantía:</span>
                <span>{presupuestoDetalle.warranty_type_text}</span>
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
            {presupuestoDetalle.device_type && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Tipo:</span>
                <span>{presupuestoDetalle.device_type}</span>
              </div>
            )}
            {presupuestoDetalle.device_purchase_date && (
              <div className="flex justify-between pt-2 border-t">
                <span className="text-muted-foreground">Fecha compra:</span>
                <span>{presupuestoDetalle.device_purchase_date}</span>
              </div>
            )}
            {presupuestoDetalle.device_purchase_price && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Precio compra:</span>
                <span className="font-medium">{presupuestoDetalle.device_purchase_price}€</span>
              </div>
            )}
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
          {presupuestoDetalle.accepted_date && (
            <div className="mt-3 pt-3 border-t text-sm">
              <p className="text-muted-foreground">Fecha aceptación: <span className="font-medium text-green-600">{presupuestoDetalle.accepted_date}</span></p>
            </div>
          )}
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

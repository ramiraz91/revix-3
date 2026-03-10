import { useState } from 'react';
import { Smartphone, ScanBarcode, ShieldCheck, ShieldAlert, Loader2, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { ordenesAPI } from '@/lib/api';
import { toast } from 'sonner';

export function TecnicoDispositivoCard({ orden, imeiValidado, setImeiValidado, onRefresh }) {
  const [showValidarIMEI, setShowValidarIMEI] = useState(false);
  const [imeiEscaneado, setImeiEscaneado] = useState('');
  const [validandoIMEI, setValidandoIMEI] = useState(false);

  const handleValidarIMEI = async () => {
    if (!imeiEscaneado.trim()) {
      toast.error('Por favor, escanea o introduce el IMEI');
      return;
    }
    
    const imeiRegistrado = orden?.dispositivo?.imei?.replace(/\s/g, '').toUpperCase();
    const imeiInput = imeiEscaneado.replace(/\s/g, '').toUpperCase();
    
    setValidandoIMEI(true);
    
    try {
      if (imeiInput === imeiRegistrado) {
        await ordenesAPI.actualizar(orden.id, { imei_validado: true });
        setImeiValidado(true);
        setShowValidarIMEI(false);
        setImeiEscaneado('');
        toast.success('✅ IMEI validado correctamente');
        onRefresh();
      } else {
        await ordenesAPI.actualizar(orden.id, { 
          bloqueada: true,
          motivo_bloqueo: 'IMEI no coincide',
          imei_escaneado_incorrecto: imeiInput
        });
        toast.error('❌ IMEI NO COINCIDE. La orden ha sido BLOQUEADA y se ha notificado al administrador.');
        setShowValidarIMEI(false);
        onRefresh();
      }
    } catch (error) {
      toast.error('Error al validar IMEI');
      console.error(error);
    } finally {
      setValidandoIMEI(false);
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Smartphone className="w-5 h-5" />
            Dispositivo
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Modelo</p>
              <p className="font-semibold text-lg">{orden.dispositivo?.modelo}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Color</p>
              <p className="font-medium">{orden.dispositivo?.color || '-'}</p>
            </div>
            {orden.dispositivo?.imei && (
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">IMEI/SN</p>
                <p className="font-mono text-sm">{orden.dispositivo?.imei}</p>
              </div>
            )}
            <div className="col-span-2">
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Daños / Avería</p>
              <p className="mt-1 p-3 bg-slate-50 rounded-lg">{orden.dispositivo?.daños}</p>
            </div>
          </div>
          
          {orden.dispositivo?.imei && !orden.bloqueada && (
            <div className="mt-4 pt-4 border-t">
              {imeiValidado ? (
                <div className="flex items-center gap-2 text-green-600 bg-green-50 p-3 rounded-lg">
                  <ShieldCheck className="w-5 h-5" />
                  <span className="font-medium">IMEI validado correctamente</span>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-amber-600 bg-amber-50 p-3 rounded-lg">
                    <ShieldAlert className="w-5 h-5" />
                    <span className="text-sm">Debes validar el IMEI antes de continuar</span>
                  </div>
                  <Button
                    onClick={() => setShowValidarIMEI(true)}
                    className="w-full gap-2"
                    variant="outline"
                    data-testid="btn-validar-imei"
                  >
                    <ScanBarcode className="w-4 h-4" />
                    Escanear y Validar IMEI
                  </Button>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialog para Validar IMEI */}
      <Dialog open={showValidarIMEI} onOpenChange={setShowValidarIMEI}>
        <DialogContent data-testid="dialog-validar-imei">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ScanBarcode className="w-5 h-5 text-blue-500" />
              Validar IMEI del Dispositivo
            </DialogTitle>
            <DialogDescription>
              Escanea el código de barras del dispositivo con la pistola lectora o introduce el IMEI manualmente.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-xs text-blue-600 uppercase tracking-wider mb-1">IMEI Registrado</p>
              <p className="font-mono text-lg font-semibold">{orden?.dispositivo?.imei}</p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="imei-scan">IMEI Escaneado</Label>
              <Input
                id="imei-scan"
                value={imeiEscaneado}
                onChange={(e) => setImeiEscaneado(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleValidarIMEI();
                  }
                }}
                placeholder="Escanea o escribe el IMEI aquí..."
                className="font-mono text-lg"
                autoFocus
                data-testid="input-imei-escaneado"
              />
              <p className="text-xs text-muted-foreground">
                💡 El campo está listo para recibir el escaneo. Presiona Enter para validar.
              </p>
            </div>
            
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
              <AlertTriangle className="w-4 h-4 inline mr-2" />
              <strong>Importante:</strong> Si el IMEI escaneado no coincide con el registrado, la orden será <strong>BLOQUEADA</strong> automáticamente.
            </div>
          </div>
          
          <div className="flex justify-end gap-2 mt-4">
            <Button 
              variant="outline" 
              onClick={() => {
                setShowValidarIMEI(false);
                setImeiEscaneado('');
              }}
            >
              Cancelar
            </Button>
            <Button 
              onClick={handleValidarIMEI}
              disabled={validandoIMEI || !imeiEscaneado.trim()}
              className="gap-2"
              data-testid="btn-confirmar-imei"
            >
              {validandoIMEI ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Validando...
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  Validar IMEI
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

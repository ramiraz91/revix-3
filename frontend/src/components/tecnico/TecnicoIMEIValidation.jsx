import { useRef, useEffect } from 'react';
import { ScanBarcode, ShieldCheck, ShieldAlert } from 'lucide-react';
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

export function TecnicoIMEIValidation({
  open,
  onOpenChange,
  orden,
  imeiEscaneado,
  setImeiEscaneado,
  imeiValidado,
  onValidarIMEI,
  validandoIMEI
}) {
  const imeiInputRef = useRef(null);

  // Auto-focus en input de IMEI cuando se abre el modal (para pistola escáner)
  useEffect(() => {
    if (open && imeiInputRef.current) {
      setTimeout(() => imeiInputRef.current?.focus(), 100);
    }
  }, [open]);

  return (
    <>
      {/* Botón para abrir validación (si no está validado) */}
      {!imeiValidado && !orden?.bloqueada && (
        <Button 
          variant="outline" 
          className="w-full border-amber-500 text-amber-700 hover:bg-amber-50"
          onClick={() => onOpenChange(true)}
          data-testid="btn-validar-imei"
        >
          <ScanBarcode className="w-4 h-4 mr-2" />
          Validar IMEI del Dispositivo
        </Button>
      )}

      {/* Badge de estado IMEI */}
      {imeiValidado && (
        <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
          <ShieldCheck className="w-5 h-5 text-green-600" />
          <span className="text-sm font-medium text-green-700">IMEI Validado correctamente</span>
        </div>
      )}

      {orden?.bloqueada && orden?.motivo_bloqueo === 'IMEI no coincide' && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-300 rounded-lg">
          <ShieldAlert className="w-5 h-5 text-red-600" />
          <div>
            <span className="text-sm font-bold text-red-700 block">ORDEN BLOQUEADA</span>
            <span className="text-xs text-red-600">IMEI no coincide. Esperando revisión del administrador.</span>
          </div>
        </div>
      )}

      {/* Modal de validación */}
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ScanBarcode className="w-5 h-5 text-amber-600" />
              Validar IMEI del Dispositivo
            </DialogTitle>
            <DialogDescription>
              Escanea el código IMEI/SN del dispositivo con la pistola o introdúcelo manualmente.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* IMEI esperado */}
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-xs text-blue-600 mb-1">IMEI registrado en el sistema:</p>
              <p className="font-mono font-bold text-blue-800 text-lg">
                {orden?.dispositivo?.imei || 'No disponible'}
              </p>
            </div>

            {/* Input para escaneo */}
            <div>
              <Label>Escanear / Introducir IMEI</Label>
              <Input
                ref={imeiInputRef}
                value={imeiEscaneado}
                onChange={(e) => setImeiEscaneado(e.target.value)}
                placeholder="Escanea o introduce el IMEI..."
                className="font-mono text-lg h-12"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    onValidarIMEI();
                  }
                }}
                data-testid="input-imei-scan"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Al escanear con la pistola, el código se introducirá automáticamente.
              </p>
            </div>

            {/* Comparación visual */}
            {imeiEscaneado && (
              <div className={`p-3 rounded-lg border-2 ${
                imeiEscaneado.replace(/\s/g, '').toUpperCase() === 
                orden?.dispositivo?.imei?.replace(/\s/g, '').toUpperCase()
                  ? 'bg-green-50 border-green-500'
                  : 'bg-red-50 border-red-500'
              }`}>
                <p className="text-sm font-medium mb-1">
                  {imeiEscaneado.replace(/\s/g, '').toUpperCase() === 
                   orden?.dispositivo?.imei?.replace(/\s/g, '').toUpperCase()
                    ? '✅ Los IMEI coinciden'
                    : '❌ Los IMEI NO coinciden'}
                </p>
                <p className="font-mono text-sm">
                  Escaneado: <strong>{imeiEscaneado}</strong>
                </p>
              </div>
            )}
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={onValidarIMEI}
              disabled={validandoIMEI || !imeiEscaneado.trim()}
              data-testid="btn-confirmar-validacion-imei"
            >
              {validandoIMEI ? 'Validando...' : 'Validar IMEI'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

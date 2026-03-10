import { Lock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';

export function OrdenDesbloquearModal({
  open,
  onOpenChange,
  orden,
  desbloqueoData,
  setDesbloqueoData,
  onDesbloquear,
  desbloqueando
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg" data-testid="dialog-desbloquear">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lock className="w-5 h-5 text-green-600" />
            Desbloquear Orden
          </DialogTitle>
          <DialogDescription>
            Revisa y actualiza los datos del dispositivo si es necesario antes de desbloquear.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Resumen del bloqueo */}
          {orden?.motivo_bloqueo === 'IMEI no coincide' && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-sm font-medium text-amber-800 mb-3">⚠️ Discrepancia de IMEI detectada</p>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="p-2 bg-red-50 rounded">
                  <p className="text-xs text-red-600">IMEI Escaneado:</p>
                  <p className="font-mono font-bold text-red-700">{orden?.imei_escaneado_incorrecto || 'N/A'}</p>
                </div>
                <div className="p-2 bg-blue-50 rounded">
                  <p className="text-xs text-blue-600">IMEI en Sistema:</p>
                  <p className="font-mono font-bold text-blue-700">{orden?.dispositivo?.imei || 'N/A'}</p>
                </div>
              </div>
              <div className="mt-3 flex gap-2">
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => setDesbloqueoData(prev => ({ ...prev, imei_correcto: orden?.imei_escaneado_incorrecto || '' }))}
                  className="text-xs"
                >
                  Usar IMEI Escaneado
                </Button>
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => setDesbloqueoData(prev => ({ ...prev, imei_correcto: orden?.dispositivo?.imei || '' }))}
                  className="text-xs"
                >
                  Mantener IMEI Actual
                </Button>
              </div>
            </div>
          )}

          {/* Formulario de datos del dispositivo */}
          <div className="space-y-4">
            <div>
              <Label>IMEI/SN Correcto *</Label>
              <Input
                value={desbloqueoData.imei_correcto}
                onChange={(e) => setDesbloqueoData(prev => ({ ...prev, imei_correcto: e.target.value }))}
                placeholder="Introduce el IMEI/SN correcto"
                className="font-mono"
                data-testid="input-imei-correcto"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Este será el IMEI que quedará registrado en la orden
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Modelo</Label>
                <Input
                  value={desbloqueoData.modelo}
                  onChange={(e) => setDesbloqueoData(prev => ({ ...prev, modelo: e.target.value }))}
                  placeholder="Modelo del dispositivo"
                />
              </div>
              <div>
                <Label>Color</Label>
                <Input
                  value={desbloqueoData.color}
                  onChange={(e) => setDesbloqueoData(prev => ({ ...prev, color: e.target.value }))}
                  placeholder="Color del dispositivo"
                />
              </div>
            </div>

            <div>
              <Label>Notas de resolución</Label>
              <Textarea
                value={desbloqueoData.notas_resolucion}
                onChange={(e) => setDesbloqueoData(prev => ({ ...prev, notas_resolucion: e.target.value }))}
                placeholder="Ej: IMEI verificado físicamente, error de transcripción inicial..."
                rows={2}
                data-testid="input-notas-desbloqueo"
              />
            </div>
          </div>

          {/* Advertencia si se va a cambiar el IMEI */}
          {desbloqueoData.imei_correcto && desbloqueoData.imei_correcto !== orden?.dispositivo?.imei && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm">
              <p className="font-medium text-blue-800">ℹ️ Se actualizará el IMEI en la orden:</p>
              <p className="text-blue-600 mt-1">
                <span className="line-through">{orden?.dispositivo?.imei}</span>
                <span className="mx-2">→</span>
                <span className="font-bold">{desbloqueoData.imei_correcto}</span>
              </p>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button 
            variant="outline" 
            onClick={() => onOpenChange(false)}
          >
            Cancelar
          </Button>
          <Button 
            onClick={onDesbloquear}
            disabled={desbloqueando || !desbloqueoData.imei_correcto}
            className="bg-green-600 hover:bg-green-700"
            data-testid="btn-confirmar-desbloqueo"
          >
            {desbloqueando ? 'Desbloqueando...' : 'Desbloquear Orden'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

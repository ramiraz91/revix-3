import { ClipboardCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';

export function TecnicoCierreReparacionModal({
  open,
  onOpenChange,
  checkDiagnosticoSalida,
  setCheckDiagnosticoSalida,
  checkFuncionesVerificadas,
  setCheckFuncionesVerificadas,
  checkLimpiezaRealizada,
  setCheckLimpiezaRealizada,
  notasCierre,
  setNotasCierre,
  onCerrarReparacion,
  cerrandoReparacion
}) {
  const canClose = checkDiagnosticoSalida && checkFuncionesVerificadas;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ClipboardCheck className="w-5 h-5 text-green-600" />
            Cerrar Reparación
          </DialogTitle>
          <DialogDescription>
            Confirma que has completado todas las verificaciones antes de cerrar la reparación.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Checklist obligatorio */}
          <div className="space-y-3">
            <div className="flex items-start space-x-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <Checkbox
                id="check-diagnostico"
                checked={checkDiagnosticoSalida}
                onCheckedChange={setCheckDiagnosticoSalida}
                className="mt-0.5"
              />
              <div>
                <label
                  htmlFor="check-diagnostico"
                  className="text-sm font-medium leading-none cursor-pointer"
                >
                  Diagnóstico de salida realizado *
                </label>
                <p className="text-xs text-muted-foreground mt-1">
                  He verificado que el dispositivo funciona correctamente después de la reparación.
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <Checkbox
                id="check-funciones"
                checked={checkFuncionesVerificadas}
                onCheckedChange={setCheckFuncionesVerificadas}
                className="mt-0.5"
              />
              <div>
                <label
                  htmlFor="check-funciones"
                  className="text-sm font-medium leading-none cursor-pointer"
                >
                  Funciones verificadas *
                </label>
                <p className="text-xs text-muted-foreground mt-1">
                  He probado todas las funciones relacionadas con la reparación (pantalla, batería, etc.)
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-3 p-3 bg-gray-50 border border-gray-200 rounded-lg">
              <Checkbox
                id="check-limpieza"
                checked={checkLimpiezaRealizada}
                onCheckedChange={setCheckLimpiezaRealizada}
                className="mt-0.5"
              />
              <div>
                <label
                  htmlFor="check-limpieza"
                  className="text-sm font-medium leading-none cursor-pointer"
                >
                  Limpieza realizada (opcional)
                </label>
                <p className="text-xs text-muted-foreground mt-1">
                  El dispositivo ha sido limpiado antes de la entrega.
                </p>
              </div>
            </div>
          </div>

          {/* Notas adicionales */}
          <div>
            <Label>Notas de cierre (opcional)</Label>
            <Textarea
              value={notasCierre}
              onChange={(e) => setNotasCierre(e.target.value)}
              placeholder="Observaciones adicionales sobre la reparación..."
              rows={2}
            />
          </div>

          {/* Advertencia */}
          {!canClose && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              ⚠️ Debes confirmar los checks obligatorios (*) para poder cerrar la reparación.
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button 
            onClick={onCerrarReparacion}
            disabled={cerrandoReparacion || !canClose}
            className="bg-green-600 hover:bg-green-700"
          >
            {cerrandoReparacion ? 'Cerrando...' : 'Cerrar Reparación'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

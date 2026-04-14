import { ClipboardCheck, Shield, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
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
  cerrandoReparacion,
  // Props de garantía
  esGarantia = false,
  resultadoGarantia,
  setResultadoGarantia,
  motivoNoGarantia,
  setMotivoNoGarantia
}) {
  // Si es garantía, se puede cerrar sin los checks normales si se marca como "no procede"
  const canClose = esGarantia 
    ? (resultadoGarantia === 'no_procede' || (checkDiagnosticoSalida && checkFuncionesVerificadas))
    : (checkDiagnosticoSalida && checkFuncionesVerificadas);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ClipboardCheck className="w-5 h-5 text-green-600" />
            Cerrar Reparación
            {esGarantia && (
              <span className="ml-2 px-2 py-0.5 bg-amber-100 text-amber-700 text-xs rounded-full">
                GARANTÍA
              </span>
            )}
          </DialogTitle>
          <DialogDescription>
            Confirma que has completado todas las verificaciones antes de cerrar la reparación.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Sección de GARANTÍA - Solo si es orden de garantía */}
          {esGarantia && (
            <div className="p-4 bg-amber-50 border border-amber-300 rounded-lg space-y-3">
              <div className="flex items-center gap-2 text-amber-700 font-medium">
                <Shield className="w-4 h-4" />
                Resultado de la Garantía
              </div>
              
              <RadioGroup 
                value={resultadoGarantia} 
                onValueChange={setResultadoGarantia}
                className="space-y-2"
              >
                <div className="flex items-center space-x-2 p-2 bg-white rounded border">
                  <RadioGroupItem value="procede" id="garantia-procede" />
                  <Label htmlFor="garantia-procede" className="cursor-pointer text-sm">
                    ✅ Garantía PROCEDE - Avería cubierta y reparada
                  </Label>
                </div>
                <div className="flex items-center space-x-2 p-2 bg-white rounded border">
                  <RadioGroupItem value="no_procede" id="garantia-no-procede" />
                  <Label htmlFor="garantia-no-procede" className="cursor-pointer text-sm">
                    ❌ Garantía NO PROCEDE - Avería fuera de garantía
                  </Label>
                </div>
              </RadioGroup>

              {resultadoGarantia === 'no_procede' && (
                <div className="space-y-2 pt-2">
                  <Label className="flex items-center gap-1 text-amber-700">
                    <AlertTriangle className="w-3 h-3" />
                    Motivo de no garantía *
                  </Label>
                  <Textarea
                    value={motivoNoGarantia}
                    onChange={(e) => setMotivoNoGarantia(e.target.value)}
                    placeholder="Ej: Daño por líquido, golpe externo, manipulación de terceros..."
                    rows={2}
                    className="bg-white"
                  />
                  <p className="text-xs text-amber-600">
                    Este motivo aparecerá en el PDF de la orden
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Checklist - Ocultar si garantía no procede */}
          {(!esGarantia || resultadoGarantia !== 'no_procede') && (
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
          )}

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
              ⚠️ {esGarantia && resultadoGarantia === 'no_procede' && !motivoNoGarantia?.trim()
                ? 'Debes indicar el motivo por el que la garantía no procede.'
                : 'Debes confirmar los checks obligatorios (*) para poder cerrar la reparación.'}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button 
            onClick={onCerrarReparacion}
            disabled={cerrandoReparacion || !canClose || (esGarantia && resultadoGarantia === 'no_procede' && !motivoNoGarantia?.trim())}
            className="bg-green-600 hover:bg-green-700"
          >
            {cerrandoReparacion ? 'Cerrando...' : 'Cerrar Reparación'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

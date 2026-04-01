import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

// Estados que solo el técnico puede ejecutar
const ESTADOS_TECNICO = new Set(['en_taller', 'reparado', 'irreparable']);
// Estados que solo admin/master puede ejecutar
const ESTADOS_ADMIN = new Set(['recibida', 'enviado', 'cancelado', 're_presupuestar', 'reemplazo', 'garantia', 'pendiente_recibir', 'validacion', 'cuarentena']);

const statusConfig = {
  pendiente_recibir: { label: 'Pendiente Recibir',  admin: true },
  recibida:          { label: 'Recibida',            admin: true },
  cuarentena:        { label: 'Cuarentena',          admin: true },
  en_taller:         { label: 'En Taller',           tecnico: true },
  re_presupuestar:   { label: 'Re-presupuestar',     admin: true },
  reparado:          { label: 'Reparado',            tecnico: true },
  validacion:        { label: 'Validación / QC OK',  admin: true },
  enviado:           { label: 'Enviado',             admin: true },
  garantia:          { label: 'Garantía',            admin: true },
  cancelado:         { label: 'Cancelado',           admin: true },
  reemplazo:         { label: 'Reemplazo',           admin: true },
  irreparable:       { label: 'Irreparable',         tecnico: true },
};

export function OrdenCambioEstadoModal({
  open,
  onOpenChange,
  nuevoEstado,
  setNuevoEstado,
  codigoEnvio,
  setCodigoEnvio,
  mensajeCambio,
  setMensajeCambio,
  onCambiarEstado,
  isTecnico = false,
  isMaster = false,
}) {
  // Filtrar estados según rol
  const estadosDisponibles = Object.entries(statusConfig).filter(([key, cfg]) => {
    // Técnico solo ve estados técnicos específicos
    if (isTecnico) return cfg.tecnico === true;
    // Master puede ver TODOS los estados
    if (isMaster) return true;
    // Admin ve estados admin
    return cfg.admin === true;
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Cambiar Estado de la Orden</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {isTecnico && (
            <p className="text-xs text-blue-600 bg-blue-50 border border-blue-200 rounded px-2 py-1.5" data-testid="estado-tecnico-notice">
              Como técnico, solo puedes cambiar a: En Taller, Reparado, Irreparable.
            </p>
          )}
          {!isTecnico && !isMaster && (
            <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-2 py-1.5" data-testid="estado-admin-only-notice">
              Solo admin/master pueden cambiar estados. Los técnicos tienen estados limitados.
            </p>
          )}
          {isMaster && (
            <p className="text-xs text-purple-600 bg-purple-50 border border-purple-200 rounded px-2 py-1.5" data-testid="estado-master-notice">
              Modo Master: acceso completo a todos los estados.
            </p>
          )}
          <div>
            <Label>Nuevo Estado</Label>
            <Select value={nuevoEstado} onValueChange={setNuevoEstado} data-testid="nuevo-estado-select">
              <SelectTrigger>
                <SelectValue placeholder="Selecciona un estado" />
              </SelectTrigger>
              <SelectContent>
                {estadosDisponibles.map(([key, { label }]) => (
                  <SelectItem key={key} value={key} data-testid={`estado-option-${key}`}>{label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          {/* Campo de mensaje OBLIGATORIO */}
          <div>
            <Label className="flex items-center gap-1">
              Motivo del cambio <span className="text-red-500">*</span>
            </Label>
            <Textarea
              value={mensajeCambio || ''}
              onChange={(e) => setMensajeCambio(e.target.value)}
              placeholder="Indica el motivo del cambio de estado (obligatorio)"
              rows={2}
              className="resize-none"
              data-testid="mensaje-cambio-textarea"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Este mensaje quedará registrado en el historial de la orden.
            </p>
          </div>
          
          {nuevoEstado === 'enviado' && (
            <div>
              <Label>Código de Envío (Salida) *</Label>
              <Input
                value={codigoEnvio}
                onChange={(e) => setCodigoEnvio(e.target.value)}
                placeholder="Código de tracking"
                className="font-mono"
                data-testid="codigo-envio-input"
              />
            </div>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={() => onCambiarEstado()} 
              disabled={!nuevoEstado || !mensajeCambio?.trim()}
              data-testid="confirmar-cambio-estado-btn"
            >
              Guardar
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

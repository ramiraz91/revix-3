import { useState } from 'react';
import {
  Play, XCircle, AlertTriangle, CheckCircle2, Loader2, ChevronRight
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { ordenesAPI } from '@/lib/api';
import { toast } from 'sonner';

export function TecnicoAccionesCard({ orden, onRefresh }) {
  const [showIrreparable, setShowIrreparable] = useState(false);
  const [motivoIrreparable, setMotivoIrreparable] = useState('');
  const [loading, setLoading] = useState(false);

  const handleIniciarReparacion = async () => {
    setLoading(true);
    try {
      await ordenesAPI.cambiarEstado(orden.id, {
        nuevo_estado: 'en_taller',
        usuario: 'tecnico',
        mensaje: 'Técnico inicia la reparación',
      });
      toast.success('Reparación iniciada — la orden está ahora "En Taller"');
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al iniciar la reparación');
    } finally {
      setLoading(false);
    }
  };

  const handleFinalizarReparacion = async () => {
    setLoading(true);
    try {
      // Pasar directamente a validación (el técnico ha completado su trabajo)
      await ordenesAPI.cambiarEstado(orden.id, {
        nuevo_estado: 'validacion',
        usuario: 'tecnico',
        mensaje: 'Reparación completada - Pendiente de validación para envío',
      });
      toast.success('Reparación finalizada — Orden en validación para envío');
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al finalizar la reparación');
    } finally {
      setLoading(false);
    }
  };

  const handleIrreparable = async () => {
    if (!motivoIrreparable.trim()) {
      toast.error('Indica el motivo por el que es irreparable');
      return;
    }
    setLoading(true);
    try {
      await ordenesAPI.cambiarEstado(orden.id, {
        nuevo_estado: 'irreparable',
        usuario: 'tecnico',
        mensaje: motivoIrreparable,
      });
      await ordenesAPI.actualizar(orden.id, {
        diagnostico_tecnico: motivoIrreparable,
      });
      toast.success('Orden marcada como Irreparable');
      setShowIrreparable(false);
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    } finally {
      setLoading(false);
    }
  };

  // Solo mostrar en estados técnicos relevantes
  if (!['recibida', 'cuarentena', 'en_taller'].includes(orden.estado)) {
    return null;
  }

  return (
    <>
      <Card className="border-blue-200 bg-blue-50/40" data-testid="tecnico-acciones-card">
        <CardHeader className="pb-3">
          <CardTitle className="text-base text-blue-800">Acciones de la Reparación</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">

          {/* Iniciar Reparación */}
          {(orden.estado === 'recibida' || orden.estado === 'cuarentena') && (
            <Button
              className="w-full bg-blue-600 hover:bg-blue-700 gap-2"
              onClick={handleIniciarReparacion}
              disabled={loading}
              data-testid="btn-iniciar-reparacion"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Iniciar Reparación
              <ChevronRight className="w-4 h-4 ml-auto" />
            </Button>
          )}

          {/* Acciones cuando está en taller */}
          {orden.estado === 'en_taller' && (
            <>
              {/* Finalizar Reparación */}
              <Button
                className="w-full bg-green-600 hover:bg-green-700 gap-2"
                onClick={handleFinalizarReparacion}
                disabled={loading}
                data-testid="btn-finalizar-reparacion"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-4 h-4" />
                )}
                Finalizar Reparación → Validación
                <ChevronRight className="w-4 h-4 ml-auto" />
              </Button>

              {/* Marcar Irreparable */}
              <Button
                variant="destructive"
                className="w-full gap-2"
                onClick={() => setShowIrreparable(true)}
                disabled={loading}
                data-testid="btn-marcar-irreparable"
              >
                <XCircle className="w-4 h-4" />
                Marcar como Irreparable
              </Button>
            </>
          )}

          <p className="text-xs text-blue-600 text-center pt-1">
            {orden.estado === 'recibida' || orden.estado === 'cuarentena'
              ? 'Confirma que el dispositivo está físicamente en el taller'
              : 'Al finalizar, la orden pasa a validación para que admin gestione el envío'}
          </p>
        </CardContent>
      </Card>

      {/* Dialog Irreparable */}
      <Dialog open={showIrreparable} onOpenChange={setShowIrreparable}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-700">
              <AlertTriangle className="w-5 h-5" />
              Confirmar: Dispositivo Irreparable
            </DialogTitle>
            <DialogDescription>
              Esta acción cambia el estado a Irreparable y notifica al administrador.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="p-3 bg-slate-50 rounded-lg text-sm">
              <p className="font-medium">{orden?.dispositivo?.modelo}</p>
              <p className="text-xs text-muted-foreground font-mono">{orden?.dispositivo?.imei}</p>
            </div>
            <div>
              <Label>Motivo técnico (obligatorio)</Label>
              <Textarea
                value={motivoIrreparable}
                onChange={(e) => setMotivoIrreparable(e.target.value)}
                placeholder="Ej: Daño por agua en placa base, corrosión severa en circuito de carga..."
                rows={3}
                className="mt-1"
                data-testid="motivo-irreparable-textarea"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowIrreparable(false)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleIrreparable}
              disabled={loading || !motivoIrreparable.trim()}
              data-testid="btn-confirmar-irreparable"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Confirmar Irreparable
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

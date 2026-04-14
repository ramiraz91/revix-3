import { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { AlertTriangle, Shield } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export function GarantiaModal({ isOpen, onClose, orden, onSuccess }) {
  const [indicacionesCliente, setIndicacionesCliente] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCrearGarantia = async () => {
    if (!indicacionesCliente.trim()) {
      toast.error('Debes introducir las indicaciones del cliente');
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/api/ordenes/${orden.id}/crear-garantia`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          indicaciones_cliente: indicacionesCliente.trim()
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error al crear garantía');
      }

      const data = await response.json();
      toast.success(`Orden de garantía ${data.orden_garantia?.numero_orden} creada`);
      onSuccess(data);
      onClose();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-amber-600">
            <Shield className="w-5 h-5" />
            Abrir Garantía
          </DialogTitle>
          <DialogDescription>
            Se creará una nueva orden de garantía vinculada a la orden <strong>{orden?.numero_orden}</strong>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Info del dispositivo */}
          <div className="p-3 bg-slate-50 rounded-lg text-sm">
            <p className="font-medium">{orden?.dispositivo?.marca} {orden?.dispositivo?.modelo}</p>
            <p className="text-muted-foreground">IMEI: {orden?.dispositivo?.imei || 'N/A'}</p>
            <p className="text-muted-foreground">Color: {orden?.dispositivo?.color || 'N/A'}</p>
          </div>

          {/* Indicaciones del cliente */}
          <div className="space-y-2">
            <Label htmlFor="indicaciones" className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              Indicaciones del cliente *
            </Label>
            <Textarea
              id="indicaciones"
              placeholder="Describe qué problema reporta el cliente para esta garantía..."
              value={indicacionesCliente}
              onChange={(e) => setIndicacionesCliente(e.target.value)}
              rows={4}
              className="resize-none"
            />
            <p className="text-xs text-muted-foreground">
              Estas indicaciones se guardarán en la nueva orden de garantía
            </p>
          </div>

          {/* Aviso */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
            <p className="font-medium">Al crear la garantía:</p>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li>Se generará una nueva orden vinculada</li>
              <li>Se creará una incidencia de tipo "garantía"</li>
              <li>Los datos del dispositivo se heredarán automáticamente</li>
            </ul>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancelar
          </Button>
          <Button 
            onClick={handleCrearGarantia} 
            disabled={loading || !indicacionesCliente.trim()}
            className="bg-amber-600 hover:bg-amber-700"
          >
            {loading ? 'Creando...' : 'Crear Garantía'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

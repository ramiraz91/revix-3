import { useState, useEffect } from 'react';
import { Package, Truck } from 'lucide-react';
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
import { toast } from 'sonner';

export function GenerarEnvioModal({ 
  open, 
  onOpenChange, 
  tipo, // 'recogida' o 'envio'
  cliente,
  orden,
  onConfirm,
  loading
}) {
  const [formData, setFormData] = useState({
    nombre: '',
    telefono: '',
    email: '',
    direccion: '',
    codigo_postal: '',
    ciudad: '',
    provincia: '',
    planta: '',
    puerta: '',
    observaciones: ''
  });

  // Pre-rellenar datos del cliente cuando se abre el modal
  useEffect(() => {
    if (open && cliente) {
      setFormData({
        nombre: `${cliente.nombre || ''} ${cliente.apellidos || ''}`.trim(),
        telefono: cliente.telefono || '',
        email: cliente.email || '',
        direccion: cliente.direccion || '',
        codigo_postal: cliente.codigo_postal || '',
        ciudad: cliente.ciudad || '',
        provincia: cliente.provincia || '',
        planta: cliente.planta || '',
        puerta: cliente.puerta || '',
        observaciones: ''
      });
    }
  }, [open, cliente]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = () => {
    if (!formData.nombre || !formData.direccion || !formData.codigo_postal || !formData.ciudad) {
      toast.error('Nombre, dirección, código postal y ciudad son obligatorios');
      return;
    }
    if (!formData.telefono) {
      toast.error('El teléfono es obligatorio para el transportista');
      return;
    }
    onConfirm(formData);
  };

  const isRecogida = tipo === 'recogida';
  const title = isRecogida ? 'Generar Recogida' : 'Generar Envío';
  const description = isRecogida 
    ? 'Confirma los datos de recogida del dispositivo. El transportista recogerá en esta dirección.'
    : 'Confirma los datos de envío. El dispositivo reparado se enviará a esta dirección.';
  const Icon = isRecogida ? Package : Truck;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Icon className="w-5 h-5" />
            {title}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-2">
          {/* Nombre */}
          <div>
            <Label>Nombre completo *</Label>
            <Input
              value={formData.nombre}
              onChange={(e) => handleChange('nombre', e.target.value)}
              placeholder="Nombre y apellidos"
            />
          </div>

          {/* Teléfono y Email */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Teléfono *</Label>
              <Input
                value={formData.telefono}
                onChange={(e) => handleChange('telefono', e.target.value)}
                placeholder="600 000 000"
              />
            </div>
            <div>
              <Label>Email</Label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) => handleChange('email', e.target.value)}
                placeholder="email@ejemplo.com"
              />
            </div>
          </div>

          {/* Dirección */}
          <div>
            <Label>Dirección *</Label>
            <Input
              value={formData.direccion}
              onChange={(e) => handleChange('direccion', e.target.value)}
              placeholder="Calle, número..."
            />
          </div>

          {/* Planta y Puerta */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Planta/Piso</Label>
              <Input
                value={formData.planta}
                onChange={(e) => handleChange('planta', e.target.value)}
                placeholder="2º"
              />
            </div>
            <div>
              <Label>Puerta</Label>
              <Input
                value={formData.puerta}
                onChange={(e) => handleChange('puerta', e.target.value)}
                placeholder="A"
              />
            </div>
          </div>

          {/* CP, Ciudad, Provincia */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label>Código Postal *</Label>
              <Input
                value={formData.codigo_postal}
                onChange={(e) => handleChange('codigo_postal', e.target.value)}
                placeholder="28001"
              />
            </div>
            <div>
              <Label>Ciudad *</Label>
              <Input
                value={formData.ciudad}
                onChange={(e) => handleChange('ciudad', e.target.value)}
                placeholder="Madrid"
              />
            </div>
            <div>
              <Label>Provincia</Label>
              <Input
                value={formData.provincia}
                onChange={(e) => handleChange('provincia', e.target.value)}
                placeholder="Madrid"
              />
            </div>
          </div>

          {/* Observaciones */}
          <div>
            <Label>Observaciones para el transportista</Label>
            <Input
              value={formData.observaciones}
              onChange={(e) => handleChange('observaciones', e.target.value)}
              placeholder="Ej: Llamar antes de entregar, horario de 9 a 14h..."
            />
          </div>

          {/* Info de la orden */}
          <div className="p-3 bg-slate-50 rounded-lg text-sm">
            <p className="text-muted-foreground">
              <strong>Orden:</strong> {orden?.numero_orden}
              {orden?.numero_autorizacion && <> · <strong>Auth:</strong> {orden.numero_autorizacion}</>}
            </p>
            <p className="text-muted-foreground">
              <strong>Dispositivo:</strong> {orden?.dispositivo?.modelo || 'N/A'}
            </p>
          </div>

          {/* Botones */}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSubmit} disabled={loading}>
              <Icon className="w-4 h-4 mr-2" />
              {loading ? 'Generando...' : `Confirmar ${isRecogida ? 'Recogida' : 'Envío'}`}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

import { useState } from 'react';
import { 
  Euro, 
  Send, 
  Loader2, 
  Package, 
  Wrench, 
  CheckCircle2, 
  Truck, 
  RefreshCw,
  MessageSquare
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { insuramaAPI } from '@/lib/api';
import { toast } from 'sonner';

export function InsuramaAccionesTab({ presupuestoDetalle }) {
  // Presupuesto form
  const [presupuestoForm, setPresupuestoForm] = useState({
    precio: presupuestoDetalle?.price || '',
    descripcion: presupuestoDetalle?.repair_description || '',
    tiempo_reparacion: presupuestoDetalle?.repair_time_text || '24-48h',
    garantia_meses: 12,
    // Nuevos campos requeridos por Sumbroker
    disponibilidad_recambios: '',
    tiempo_horas: '',
    tipo_recambio: '',
    tipo_garantia: ''
  });
  const [enviandoPresupuesto, setEnviandoPresupuesto] = useState(false);
  
  // Estado form
  const [nuevoEstado, setNuevoEstado] = useState('');
  const [trackingNumber, setTrackingNumber] = useState('');
  const [transportista, setTransportista] = useState('');
  const [notasEstado, setNotasEstado] = useState('');
  const [actualizandoEstado, setActualizandoEstado] = useState(false);

  const handleEnviarPresupuesto = async () => {
    if (!presupuestoForm.precio || !presupuestoForm.descripcion) {
      toast.error('Completa precio y descripción');
      return;
    }
    
    // Validar campos obligatorios adicionales
    if (!presupuestoForm.disponibilidad_recambios) {
      toast.error('Selecciona la disponibilidad de recambios');
      return;
    }
    if (!presupuestoForm.tiempo_horas) {
      toast.error('Indica el tiempo estimado en horas');
      return;
    }
    if (!presupuestoForm.tipo_recambio) {
      toast.error('Selecciona el tipo de recambio');
      return;
    }
    if (!presupuestoForm.tipo_garantia) {
      toast.error('Selecciona el tipo de garantía');
      return;
    }
    
    setEnviandoPresupuesto(true);
    try {
      await insuramaAPI.enviarPresupuesto(presupuestoDetalle.claim_identifier, {
        precio: parseFloat(presupuestoForm.precio),
        descripcion: presupuestoForm.descripcion,
        tiempo_reparacion: presupuestoForm.tiempo_reparacion,
        garantia_meses: parseInt(presupuestoForm.garantia_meses),
        disponibilidad_recambios: presupuestoForm.disponibilidad_recambios,
        tiempo_horas: parseFloat(presupuestoForm.tiempo_horas),
        tipo_recambio: presupuestoForm.tipo_recambio,
        tipo_garantia: presupuestoForm.tipo_garantia
      });
      toast.success('Presupuesto enviado correctamente');
      setPresupuestoForm({ 
        precio: '', 
        descripcion: '', 
        tiempo_reparacion: '24-48h', 
        garantia_meses: 12,
        disponibilidad_recambios: '',
        tiempo_horas: '',
        tipo_recambio: '',
        tipo_garantia: ''
      });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al enviar presupuesto');
    } finally {
      setEnviandoPresupuesto(false);
    }
  };

  const handleActualizarEstado = async () => {
    if (!nuevoEstado) {
      toast.error('Selecciona un estado');
      return;
    }
    
    if (nuevoEstado === 'enviado' && !trackingNumber) {
      toast.error('Se requiere número de tracking para marcar como enviado');
      return;
    }
    
    setActualizandoEstado(true);
    try {
      await insuramaAPI.actualizarEstado(presupuestoDetalle.claim_identifier, {
        estado: nuevoEstado,
        tracking_number: trackingNumber || null,
        transportista: transportista || null,
        notas: notasEstado || null
      });
      toast.success(`Estado actualizado a "${nuevoEstado}"`);
      setNuevoEstado('');
      setTrackingNumber('');
      setTransportista('');
      setNotasEstado('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al actualizar estado');
    } finally {
      setActualizandoEstado(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Enviar / Cambiar Presupuesto */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Euro className="w-4 h-4 text-green-600" />
            {presupuestoDetalle?.price ? 'Cambiar Presupuesto' : 'Enviar Presupuesto'}
          </CardTitle>
          <CardDescription>
            {presupuestoDetalle?.price 
              ? `Presupuesto actual: ${presupuestoDetalle.price}€ — Modifica precio o descripción`
              : 'Envía el precio y descripción de la reparación a Insurama'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Precio (€) *</Label>
              <Input
                type="number"
                step="0.01"
                placeholder="0.00"
                value={presupuestoForm.precio}
                onChange={(e) => setPresupuestoForm(prev => ({ ...prev, precio: e.target.value }))}
                data-testid="budget-price-input"
              />
            </div>
            <div>
              <Label>Tiempo de reparación</Label>
              <Select 
                value={presupuestoForm.tiempo_reparacion}
                onValueChange={(v) => setPresupuestoForm(prev => ({ ...prev, tiempo_reparacion: v }))}
              >
                <SelectTrigger data-testid="budget-repair-time-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="24h">24 horas</SelectItem>
                  <SelectItem value="24-48h">24-48 horas</SelectItem>
                  <SelectItem value="48-72h">48-72 horas</SelectItem>
                  <SelectItem value="3-5dias">3-5 días</SelectItem>
                  <SelectItem value="1semana">1 semana</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          
          {/* Nuevos campos requeridos por Sumbroker */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Disponibilidad de Recambios *</Label>
              <Select 
                value={presupuestoForm.disponibilidad_recambios}
                onValueChange={(v) => setPresupuestoForm(prev => ({ ...prev, disponibilidad_recambios: v }))}
              >
                <SelectTrigger data-testid="budget-parts-availability-select">
                  <SelectValue placeholder="Seleccionar..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="inmediata">Inmediata (en stock)</SelectItem>
                  <SelectItem value="24h">24 horas</SelectItem>
                  <SelectItem value="48h">48 horas</SelectItem>
                  <SelectItem value="7dias">7 días</SelectItem>
                  <SelectItem value="sin_stock">Sin stock disponible</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Tiempo en Horas *</Label>
              <Input
                type="number"
                step="0.5"
                min="0.5"
                placeholder="Ej: 2.5"
                value={presupuestoForm.tiempo_horas}
                onChange={(e) => setPresupuestoForm(prev => ({ ...prev, tiempo_horas: e.target.value }))}
                data-testid="budget-time-hours-input"
              />
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Tipo de Recambio *</Label>
              <Select 
                value={presupuestoForm.tipo_recambio}
                onValueChange={(v) => setPresupuestoForm(prev => ({ ...prev, tipo_recambio: v }))}
              >
                <SelectTrigger data-testid="budget-part-type-select">
                  <SelectValue placeholder="Seleccionar..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="original">Original (OEM)</SelectItem>
                  <SelectItem value="compatible">Compatible</SelectItem>
                  <SelectItem value="reacondicionado">Reacondicionado</SelectItem>
                  <SelectItem value="no_aplica">No aplica</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Tipo de Garantía *</Label>
              <Select 
                value={presupuestoForm.tipo_garantia}
                onValueChange={(v) => setPresupuestoForm(prev => ({ ...prev, tipo_garantia: v }))}
              >
                <SelectTrigger data-testid="budget-warranty-type-select">
                  <SelectValue placeholder="Seleccionar..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="fabricante">Garantía Fabricante</SelectItem>
                  <SelectItem value="taller">Garantía Taller</SelectItem>
                  <SelectItem value="sin_garantia">Sin Garantía</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <div>
            <Label>Descripción de la reparación *</Label>
            <Textarea
              placeholder="Describe la reparación a realizar..."
              value={presupuestoForm.descripcion}
              onChange={(e) => setPresupuestoForm(prev => ({ ...prev, descripcion: e.target.value }))}
              rows={2}
              data-testid="budget-description-textarea"
            />
          </div>
          <div className="flex justify-end">
            <Button onClick={handleEnviarPresupuesto} disabled={enviandoPresupuesto} data-testid="submit-budget-btn">
              {enviandoPresupuesto ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
              {presupuestoDetalle?.price ? 'Cambiar Presupuesto' : 'Enviar Presupuesto'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Actualizar Estado */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Package className="w-4 h-4 text-blue-600" />
            Actualizar Estado
          </CardTitle>
          <CardDescription>Cambia el estado del siniestro en Insurama</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Nuevo Estado *</Label>
              <Select value={nuevoEstado} onValueChange={setNuevoEstado}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="recibido">
                    <span className="flex items-center gap-2">
                      <Package className="w-3 h-3 text-blue-500" />
                      Recibido en taller
                    </span>
                  </SelectItem>
                  <SelectItem value="en_reparacion">
                    <span className="flex items-center gap-2">
                      <Wrench className="w-3 h-3 text-amber-500" />
                      En reparación
                    </span>
                  </SelectItem>
                  <SelectItem value="reparado">
                    <span className="flex items-center gap-2">
                      <CheckCircle2 className="w-3 h-3 text-green-500" />
                      Reparado
                    </span>
                  </SelectItem>
                  <SelectItem value="enviado">
                    <span className="flex items-center gap-2">
                      <Truck className="w-3 h-3 text-purple-500" />
                      Enviado
                    </span>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            {nuevoEstado === 'enviado' && (
              <div>
                <Label>Nº Tracking *</Label>
                <Input
                  placeholder="Código de seguimiento"
                  value={trackingNumber}
                  onChange={(e) => setTrackingNumber(e.target.value)}
                  className="font-mono"
                />
              </div>
            )}
          </div>
          {nuevoEstado === 'enviado' && (
            <div>
              <Label>Transportista</Label>
              <Select value={transportista} onValueChange={setTransportista}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona transportista" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MRW">MRW</SelectItem>
                  <SelectItem value="SEUR">SEUR</SelectItem>
                  <SelectItem value="GLS">GLS</SelectItem>
                  <SelectItem value="DHL">DHL</SelectItem>
                  <SelectItem value="UPS">UPS</SelectItem>
                  <SelectItem value="Correos">Correos Express</SelectItem>
                  <SelectItem value="Otro">Otro</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
          <div>
            <Label>Notas (opcional)</Label>
            <Textarea
              placeholder="Notas adicionales..."
              value={notasEstado}
              onChange={(e) => setNotasEstado(e.target.value)}
              rows={2}
            />
          </div>
          <div className="flex justify-end">
            <Button onClick={handleActualizarEstado} disabled={actualizandoEstado || !nuevoEstado}>
              {actualizandoEstado ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <RefreshCw className="w-4 h-4 mr-2" />}
              Actualizar Estado
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Nota */}
      <Card className="border-amber-200 bg-amber-50/50">
        <CardContent className="py-4">
          <p className="text-sm text-amber-700 flex items-center gap-2">
            <MessageSquare className="w-4 h-4" />
            Los mensajes/observaciones solo se pueden enviar desde el
            <a href="https://distribuidor.sumbroker.es" target="_blank" rel="noopener noreferrer" className="underline font-medium">
              portal web de Sumbroker
            </a>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

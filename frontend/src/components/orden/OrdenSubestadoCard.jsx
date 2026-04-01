import { useState, useEffect } from 'react';
import { 
  Clock, 
  Package, 
  Phone, 
  CreditCard, 
  HelpCircle, 
  Truck, 
  Shield,
  ChevronDown,
  History,
  CalendarClock,
  AlertCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { ordenesAPI } from '@/lib/api';
import { toast } from 'sonner';

const SUBESTADO_CONFIG = {
  ninguno: { label: 'Sin subestado', icon: null, color: 'bg-slate-100 text-slate-700' },
  esperando_repuestos: { label: 'Esperando repuestos', icon: Package, color: 'bg-orange-100 text-orange-700' },
  esperando_autorizacion: { label: 'Esperando autorización', icon: Shield, color: 'bg-yellow-100 text-yellow-700' },
  esperando_cliente: { label: 'Esperando cliente', icon: Phone, color: 'bg-blue-100 text-blue-700' },
  esperando_pago: { label: 'Esperando pago', icon: CreditCard, color: 'bg-purple-100 text-purple-700' },
  en_consulta_tecnica: { label: 'En consulta técnica', icon: HelpCircle, color: 'bg-cyan-100 text-cyan-700' },
  pendiente_recogida: { label: 'Pendiente recogida', icon: Truck, color: 'bg-green-100 text-green-700' },
  aseguradora: { label: 'Esperando aseguradora', icon: Shield, color: 'bg-indigo-100 text-indigo-700' },
  otro: { label: 'Otro', icon: AlertCircle, color: 'bg-gray-100 text-gray-700' },
};

export default function OrdenSubestadoCard({ ordenId, subestadoActual, motivoActual, fechaRevision, onUpdate, onSubestadoChange }) {
  const [showModal, setShowModal] = useState(false);
  const [showHistorial, setShowHistorial] = useState(false);
  const [showAlertaVencimiento, setShowAlertaVencimiento] = useState(false);
  const [loading, setLoading] = useState(false);
  const [historial, setHistorial] = useState([]);
  const [formData, setFormData] = useState({
    subestado: subestadoActual || 'ninguno',
    motivo: '',
    fecha_revision: ''
  });

  const currentConfig = SUBESTADO_CONFIG[subestadoActual] || SUBESTADO_CONFIG.ninguno;
  const IconComponent = currentConfig.icon;

  // Calcular estado de vencimiento
  const calcularEstadoVencimiento = () => {
    if (!fechaRevision || subestadoActual === 'ninguno') return null;
    
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    const fechaRev = new Date(fechaRevision);
    fechaRev.setHours(0, 0, 0, 0);
    
    const diffDias = Math.ceil((fechaRev - hoy) / (1000 * 60 * 60 * 24));
    
    if (diffDias < 0) return { tipo: 'vencido', dias: Math.abs(diffDias), mensaje: `Plazo vencido hace ${Math.abs(diffDias)} día(s)` };
    if (diffDias === 0) return { tipo: 'hoy', dias: 0, mensaje: 'El plazo vence HOY' };
    if (diffDias <= 2) return { tipo: 'proximo', dias: diffDias, mensaje: `El plazo vence en ${diffDias} día(s)` };
    return { tipo: 'ok', dias: diffDias, mensaje: `Faltan ${diffDias} días` };
  };

  const estadoVencimiento = calcularEstadoVencimiento();

  // Mostrar alerta automática al cargar si hay vencimiento
  useEffect(() => {
    if (estadoVencimiento && (estadoVencimiento.tipo === 'vencido' || estadoVencimiento.tipo === 'hoy')) {
      setShowAlertaVencimiento(true);
    }
  }, [subestadoActual, fechaRevision]);

  const fetchHistorial = async () => {
    try {
      const res = await ordenesAPI.obtenerSubestado(ordenId);
      setHistorial(res.data.historial || []);
    } catch (error) {
      console.error('Error fetching subestado historial:', error);
    }
  };

  useEffect(() => {
    if (showHistorial) {
      fetchHistorial();
    }
  }, [showHistorial, ordenId]);

  const handleOpenModal = () => {
    setFormData({
      subestado: subestadoActual || 'ninguno',
      motivo: '',
      fecha_revision: fechaRevision ? fechaRevision.split('T')[0] : ''
    });
    setShowModal(true);
  };

  const handleSubmit = async () => {
    if (formData.subestado !== 'ninguno' && !formData.motivo.trim()) {
      toast.error('Debes indicar un motivo');
      return;
    }

    setLoading(true);
    try {
      await ordenesAPI.cambiarSubestado(ordenId, {
        subestado: formData.subestado,
        motivo: formData.motivo || 'Sin motivo especificado',
        fecha_revision: formData.fecha_revision || null
      });
      toast.success('Subestado actualizado');
      setShowModal(false);
      
      // Usar callback de actualización parcial si está disponible
      if (onSubestadoChange) {
        onSubestadoChange({
          subestado: formData.subestado,
          motivo_subestado: formData.motivo,
          fecha_revision_subestado: formData.fecha_revision || null
        });
      } else if (onUpdate) {
        onUpdate();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al cambiar subestado');
    } finally {
      setLoading(false);
    }
  };

  const handleQuitar = async () => {
    setLoading(true);
    try {
      await ordenesAPI.cambiarSubestado(ordenId, {
        subestado: 'ninguno',
        motivo: 'Subestado eliminado manualmente'
      });
      toast.success('Subestado quitado');
      setShowModal(false);
      
      // Usar callback de actualización parcial si está disponible
      if (onSubestadoChange) {
        onSubestadoChange({
          subestado: 'ninguno',
          motivo_subestado: null,
          fecha_revision_subestado: null
        });
      } else if (onUpdate) {
        onUpdate();
      }
    } catch (error) {
      toast.error('Error al quitar subestado');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('es-ES', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  // Check if fecha_revision is today or past
  const isRevisionDue = fechaRevision && new Date(fechaRevision) <= new Date();

  // Colores según estado de vencimiento
  const getAlertStyle = () => {
    if (!estadoVencimiento) return '';
    switch (estadoVencimiento.tipo) {
      case 'vencido': return 'border-red-500 bg-red-50';
      case 'hoy': return 'border-orange-500 bg-orange-50';
      case 'proximo': return 'border-yellow-500 bg-yellow-50';
      default: return '';
    }
  };

  return (
    <>
      {/* Popup de alerta de vencimiento */}
      <Dialog open={showAlertaVencimiento} onOpenChange={setShowAlertaVencimiento}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className={`flex items-center gap-2 ${estadoVencimiento?.tipo === 'vencido' ? 'text-red-600' : 'text-orange-600'}`}>
              <AlertCircle className="w-5 h-5" />
              {estadoVencimiento?.tipo === 'vencido' ? '⚠️ Plazo Vencido' : '⏰ Plazo Próximo a Vencer'}
            </DialogTitle>
            <DialogDescription className="pt-2">
              <div className="space-y-3">
                <div className={`p-3 rounded-lg ${estadoVencimiento?.tipo === 'vencido' ? 'bg-red-100' : 'bg-orange-100'}`}>
                  <p className="font-medium">{estadoVencimiento?.mensaje}</p>
                </div>
                <div className="space-y-1">
                  <p><span className="font-medium">Subestado:</span> {currentConfig.label}</p>
                  {motivoActual && <p><span className="font-medium">Motivo:</span> {motivoActual}</p>}
                  <p><span className="font-medium">Fecha límite:</span> {fechaRevision ? new Date(fechaRevision).toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) : '-'}</p>
                </div>
              </div>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex gap-2">
            <Button variant="outline" onClick={() => setShowAlertaVencimiento(false)}>
              Cerrar
            </Button>
            <Button onClick={() => { setShowAlertaVencimiento(false); handleOpenModal(); }}>
              Actualizar Subestado
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Card data-testid="subestado-card" className={`transition-all ${getAlertStyle()}`}>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between text-base">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Subestado Interno
              {estadoVencimiento && estadoVencimiento.tipo !== 'ok' && (
                <Badge 
                  variant="destructive" 
                  className={`text-xs ${estadoVencimiento.tipo === 'vencido' ? 'bg-red-600' : estadoVencimiento.tipo === 'hoy' ? 'bg-orange-600' : 'bg-yellow-600'}`}
                >
                  {estadoVencimiento.tipo === 'vencido' ? '⚠️ VENCIDO' : estadoVencimiento.tipo === 'hoy' ? '⏰ HOY' : '⏳ PRÓXIMO'}
                </Badge>
              )}
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleOpenModal}
              data-testid="btn-cambiar-subestado"
            >
              Cambiar
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Banner de alerta si hay vencimiento */}
          {estadoVencimiento && (estadoVencimiento.tipo === 'vencido' || estadoVencimiento.tipo === 'hoy') && (
            <div 
              className={`p-3 rounded-lg cursor-pointer ${estadoVencimiento.tipo === 'vencido' ? 'bg-red-100 border border-red-300' : 'bg-orange-100 border border-orange-300'}`}
              onClick={() => setShowAlertaVencimiento(true)}
            >
              <div className="flex items-center gap-2">
                <AlertCircle className={`w-5 h-5 ${estadoVencimiento.tipo === 'vencido' ? 'text-red-600' : 'text-orange-600'}`} />
                <span className={`font-medium ${estadoVencimiento.tipo === 'vencido' ? 'text-red-700' : 'text-orange-700'}`}>
                  {estadoVencimiento.mensaje}
                </span>
              </div>
              <p className="text-xs mt-1 text-muted-foreground">Haz clic para ver más detalles</p>
            </div>
          )}

          {/* Current subestado */}
          <div className="flex items-center gap-3">
            <Badge className={`${currentConfig.color} flex items-center gap-1.5 px-3 py-1.5`}>
              {IconComponent && <IconComponent className="w-4 h-4" />}
              {currentConfig.label}
            </Badge>
          </div>

          {/* Show motivo if exists and not ninguno */}
          {subestadoActual && subestadoActual !== 'ninguno' && motivoActual && (
            <p className="text-sm text-muted-foreground">
              <span className="font-medium">Motivo:</span> {motivoActual}
            </p>
          )}

          {/* Show fecha revision if exists */}
          {fechaRevision && subestadoActual !== 'ninguno' && (
            <div className={`flex items-center gap-2 text-sm ${isRevisionDue ? 'text-red-600 font-medium' : 'text-muted-foreground'}`}>
              <CalendarClock className="w-4 h-4" />
              <span>
                {isRevisionDue ? '⚠️ Revisar: ' : 'Revisar el: '}
                {new Date(fechaRevision).toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' })}
              </span>
            </div>
          )}

          {/* Historial colapsable */}
          <Collapsible open={showHistorial} onOpenChange={setShowHistorial}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="w-full justify-between mt-2">
                <span className="flex items-center gap-2">
                  <History className="w-4 h-4" />
                  Ver historial
                </span>
                <ChevronDown className={`w-4 h-4 transition-transform ${showHistorial ? 'rotate-180' : ''}`} />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2">
              {historial.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-2">Sin cambios registrados</p>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {historial.slice().reverse().map((entry, idx) => {
                    const config = SUBESTADO_CONFIG[entry.subestado_nuevo] || SUBESTADO_CONFIG.ninguno;
                    return (
                      <div key={entry.id || idx} className="text-xs border-l-2 border-slate-200 pl-3 py-1">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs px-1.5 py-0">
                            {config.label}
                          </Badge>
                        </div>
                        <p className="text-muted-foreground mt-0.5">{entry.motivo}</p>
                        <p className="text-muted-foreground/70">
                          {formatDate(entry.fecha_cambio)} - {entry.cambiado_por}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </CollapsibleContent>
          </Collapsible>
        </CardContent>
      </Card>

      {/* Modal para cambiar subestado */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent data-testid="modal-cambiar-subestado">
          <DialogHeader>
            <DialogTitle>Cambiar Subestado</DialogTitle>
            <DialogDescription>
              Los subestados permiten rastrear el motivo de espera sin cambiar el estado principal de la orden.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Subestado</Label>
              <Select 
                value={formData.subestado} 
                onValueChange={(v) => setFormData({ ...formData, subestado: v })}
              >
                <SelectTrigger data-testid="select-subestado">
                  <SelectValue placeholder="Selecciona un subestado" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(SUBESTADO_CONFIG).map(([value, config]) => {
                    const Icon = config.icon;
                    return (
                      <SelectItem key={value} value={value}>
                        <span className="flex items-center gap-2">
                          {Icon && <Icon className="w-4 h-4" />}
                          {config.label}
                        </span>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>

            {formData.subestado !== 'ninguno' && (
              <>
                <div className="space-y-2">
                  <Label>Motivo <span className="text-red-500">*</span></Label>
                  <Textarea 
                    value={formData.motivo}
                    onChange={(e) => setFormData({ ...formData, motivo: e.target.value })}
                    placeholder="Describe el motivo de este subestado..."
                    rows={3}
                    data-testid="input-motivo-subestado"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Fecha de revisión (opcional)</Label>
                  <Input 
                    type="date"
                    value={formData.fecha_revision}
                    onChange={(e) => setFormData({ ...formData, fecha_revision: e.target.value })}
                    min={new Date().toISOString().split('T')[0]}
                    data-testid="input-fecha-revision"
                  />
                  <p className="text-xs text-muted-foreground">
                    Si indicas una fecha, recibirás un recordatorio cuando llegue el momento.
                  </p>
                </div>
              </>
            )}
          </div>

          <DialogFooter className="flex gap-2">
            {subestadoActual && subestadoActual !== 'ninguno' && (
              <Button 
                variant="outline" 
                onClick={handleQuitar}
                disabled={loading}
              >
                Quitar subestado
              </Button>
            )}
            <Button 
              variant="outline" 
              onClick={() => setShowModal(false)}
              disabled={loading}
            >
              Cancelar
            </Button>
            <Button 
              onClick={handleSubmit}
              disabled={loading}
              data-testid="btn-guardar-subestado"
            >
              {loading ? 'Guardando...' : 'Guardar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

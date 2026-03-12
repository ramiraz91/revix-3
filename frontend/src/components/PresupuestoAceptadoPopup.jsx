import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  PartyPopper, 
  CheckCircle2, 
  ExternalLink,
  X
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { notificacionesAPI } from '@/lib/api';
import { toast } from 'sonner';

export default function PresupuestoAceptadoPopup() {
  const navigate = useNavigate();
  const [notificacion, setNotificacion] = useState(null);
  const [showPopup, setShowPopup] = useState(false);
  const [ultimoId, setUltimoId] = useState(null);

  // Polling para detectar notificaciones de presupuesto aceptado
  useEffect(() => {
    const checkPresupuestoAceptado = async () => {
      try {
        const res = await notificacionesAPI.listar({ limit: 5, no_leidas: true });
        // Buscar notificaciones de tipo presupuesto_aceptado con popup=true
        const notifPopup = res.data.find(n => 
          n.tipo === 'presupuesto_aceptado' && 
          n.popup === true && 
          !n.leida &&
          n.id !== ultimoId
        );
        
        if (notifPopup) {
          setNotificacion(notifPopup);
          setShowPopup(true);
          setUltimoId(notifPopup.id);
          
          // Reproducir sonido de notificación (opcional)
          try {
            const audio = new Audio('/notification.mp3');
            audio.play().catch(() => {});
          } catch (e) {}
        }
      } catch (error) {
        // Silently fail
      }
    };

    // Check cada 60 segundos (antes era 5s - causaba polling excesivo)
    const interval = setInterval(checkPresupuestoAceptado, 60000);
    checkPresupuestoAceptado(); // Check inicial
    
    return () => clearInterval(interval);
  }, [ultimoId]);

  const handleVerOrden = async () => {
    if (notificacion?.orden_id) {
      // Marcar como leída
      try {
        await notificacionesAPI.marcarLeida(notificacion.id);
      } catch (e) {}
      
      navigate(`/ordenes/${notificacion.orden_id}`);
      setShowPopup(false);
    }
  };

  const handleCerrar = async () => {
    if (notificacion) {
      try {
        await notificacionesAPI.marcarLeida(notificacion.id);
      } catch (e) {}
    }
    setShowPopup(false);
  };

  if (!notificacion) return null;

  return (
    <Dialog open={showPopup} onOpenChange={setShowPopup}>
      <DialogContent className="max-w-md border-4 border-green-500 shadow-2xl">
        <DialogHeader className="text-center">
          <div className="mx-auto mb-4 w-20 h-20 bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center animate-bounce">
            <PartyPopper className="w-10 h-10 text-white" />
          </div>
          <DialogTitle className="text-2xl text-green-600">
            {notificacion.titulo || '¡Presupuesto Aceptado!'}
          </DialogTitle>
          <DialogDescription className="text-base">
            {notificacion.mensaje}
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 pt-4">
          {/* Información adicional */}
          <div className="p-4 bg-green-50 rounded-lg border border-green-200">
            <div className="flex items-center gap-2 text-green-700">
              <CheckCircle2 className="w-5 h-5" />
              <span className="font-medium">
                El proveedor ha aceptado el presupuesto
              </span>
            </div>
            {notificacion.codigo_siniestro && (
              <p className="mt-2 text-sm text-muted-foreground">
                Código siniestro: <span className="font-mono font-medium">{notificacion.codigo_siniestro}</span>
              </p>
            )}
          </div>

          {/* Acciones */}
          <div className="flex gap-3">
            <Button
              variant="outline"
              className="flex-1"
              onClick={handleCerrar}
            >
              <X className="w-4 h-4 mr-2" />
              Cerrar
            </Button>
            <Button
              className="flex-1 bg-green-600 hover:bg-green-700"
              onClick={handleVerOrden}
              data-testid="ver-orden-aceptada"
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              Ver Orden
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

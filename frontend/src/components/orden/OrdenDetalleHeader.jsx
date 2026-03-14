import { 
  ArrowLeft, 
  Lock,
  AlertTriangle,
  Send,
  Tag,
  ExternalLink,
  Printer,
  Shield,
  Clock,
  CheckCircle2,
  Wrench,
  ClipboardList,
  X,
  Repeat,
  XCircle,
  Package,
  Truck
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const statusConfig = {
  pendiente_recibir: { label: 'Pendiente Recibir', icon: Clock, color: 'bg-yellow-500', step: 0 },
  recibida: { label: 'Recibida', icon: CheckCircle2, color: 'bg-blue-500', step: 1 },
  cuarentena: { label: 'Cuarentena', icon: AlertTriangle, color: 'bg-amber-700', step: 1.2 },
  en_taller: { label: 'En Taller', icon: Wrench, color: 'bg-purple-500', step: 2 },
  re_presupuestar: { label: 'Re-presupuestar', icon: AlertTriangle, color: 'bg-orange-500', step: 2.5 },
  reparado: { label: 'Reparado', icon: CheckCircle2, color: 'bg-green-500', step: 3 },
  validacion: { label: 'Validación', icon: ClipboardList, color: 'bg-indigo-500', step: 4 },
  enviado: { label: 'Enviado', icon: Send, color: 'bg-emerald-500', step: 5 },
  garantia: { label: 'Garantía', icon: Shield, color: 'bg-red-500', step: 0 },
  cancelado: { label: 'Cancelado', icon: X, color: 'bg-gray-500', step: -1 },
  reemplazo: { label: 'Reemplazo', icon: Repeat, color: 'bg-cyan-500', step: 5 },
  irreparable: { label: 'Irreparable', icon: XCircle, color: 'bg-red-600', step: -1 },
};

export function OrdenDetalleHeader({
  orden,
  metricas,
  onBack,
  onPrint,
  onPrintNoPrices,
  onPrintBlank,
  canPrintWithPrices,
  onShowEtiqueta,
  onObtenerLinkSeguimiento,
  onCrearGarantia,
  creandoGarantia,
  onEnviarNotificacion,
  enviandoNotificacion,
  onShowCambioEstado,
  onGenerarRecogida,
  onGenerarEnvio,
  onMarcarIrreparable,
  onSolicitarRepresupuestar
}) {
  const currentStatus = statusConfig[orden.estado];
  
  // Determinar si se puede generar recogida
  const puedeGenerarRecogida = !orden.codigo_recogida_entrada;
  
  // Determinar si se puede generar envío
  const estadosParaEnvio = ['reparado', 'validacion', 'enviado'];
  const puedeGenerarEnvio = estadosParaEnvio.includes(orden.estado) && !orden.codigo_recogida_salida && !orden.codigo_envio;
  
  // Estados donde se pueden aplicar acciones especiales
  const estadosEnTrabajo = ['recibida', 'en_taller', 'reparado', 'validacion'];
  const puedeRepresupuestar = estadosEnTrabajo.includes(orden.estado) && orden.estado !== 're_presupuestar';
  const puedeMarcarIrreparable = estadosEnTrabajo.includes(orden.estado) && orden.estado !== 'irreparable';

  return (
    <div className="flex flex-col gap-4">
      {/* Primera fila: Título y badges */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              {orden.numero_autorizacion ? (
                <h1 className="text-2xl font-bold tracking-tight font-mono text-blue-700" data-testid="auth-code-header">
                  {orden.numero_autorizacion}
                </h1>
              ) : (
                <h1 className="text-2xl font-bold tracking-tight font-mono">{orden.numero_orden}</h1>
              )}
              <Badge className={`badge-status status-${orden.estado}`}>
                {currentStatus?.label}
              </Badge>
              {orden.bloqueada && (
                <Badge variant="destructive" className="gap-1">
                  <Lock className="w-3 h-3" />
                  BLOQUEADA
                </Badge>
              )}
              {metricas?.en_retraso && (
                <Badge variant="destructive" className="gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  RETRASO: {metricas.retraso_dias} días
                </Badge>
              )}
            </div>
            <p className="text-muted-foreground mt-1">
              {orden.es_garantia && (
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-red-600 bg-red-50 border border-red-200 rounded px-2 py-0.5 mr-2">
                  <Shield className="w-3 h-3" />
                  GARANTÍA de {orden.numero_orden_padre || 'orden padre'}
                  {orden.orden_padre_id && (
                    <a href={`/ordenes/${orden.orden_padre_id}`} className="underline ml-1 hover:text-red-800">Ver original</a>
                  )}
                </span>
              )}
              {orden.numero_autorizacion && (
                <span className="text-xs font-mono mr-3">OT: {orden.numero_orden}</span>
              )}
              Creada el {new Date(orden.created_at).toLocaleDateString('es-ES', {
                day: '2-digit',
                month: 'long',
                year: 'numeric'
              })}
            </p>
          </div>
        </div>
      </div>
      
      {/* Segunda fila: Botones de acción */}
      <div className="flex gap-2 flex-wrap items-center">
        {/* Botones de logística */}
        {puedeGenerarRecogida && onGenerarRecogida && (
          <Button 
            variant="outline" 
            size="sm"
            onClick={onGenerarRecogida}
            className="border-amber-500 text-amber-600 hover:bg-amber-50"
            data-testid="btn-generar-recogida-header"
          >
            <Package className="w-4 h-4 mr-1" />
            Recogida
          </Button>
        )}
        {puedeGenerarEnvio && onGenerarEnvio && (
          <Button 
            variant="outline" 
            size="sm"
            onClick={onGenerarEnvio}
            className="border-green-500 text-green-600 hover:bg-green-50"
            data-testid="btn-generar-envio-header"
          >
            <Truck className="w-4 h-4 mr-1" />
            Envío
          </Button>
        )}
        
        <div className="w-px h-6 bg-border mx-1" />
        
        {/* Botones principales */}
        {canPrintWithPrices && (
          <Button variant="outline" size="sm" onClick={onPrint} data-testid="print-pdf-btn">
            <Printer className="w-4 h-4 mr-1" />
            Imprimir/PDF (Completo)
          </Button>
        )}
        <Button variant="outline" size="sm" onClick={onPrintNoPrices} data-testid="print-pdf-no-prices-btn">
          <Printer className="w-4 h-4 mr-1" />
          Imprimir/PDF (Sin precios)
        </Button>
        <Button variant="outline" size="sm" onClick={onPrintBlank} data-testid="print-blank-template-btn">
          <Printer className="w-4 h-4 mr-1" />
          Plantilla en blanco
        </Button>
        <Button variant="outline" size="sm" onClick={onShowEtiqueta}>
          <Tag className="w-4 h-4 mr-1" />
          Etiqueta
        </Button>
        <Button variant="outline" size="sm" onClick={onObtenerLinkSeguimiento} data-testid="link-seguimiento-btn">
          <ExternalLink className="w-4 h-4 mr-1" />
          Link
        </Button>
        {orden.estado === 'enviado' && !orden.es_garantia && (
          <Button 
            variant="outline"
            size="sm"
            onClick={onCrearGarantia}
            disabled={creandoGarantia}
            className="border-orange-500 text-orange-600 hover:bg-orange-50"
            data-testid="crear-garantia-btn"
          >
            <Shield className="w-4 h-4 mr-1" />
            {creandoGarantia ? '...' : 'Garantía'}
          </Button>
        )}
        <Button 
          size="sm"
          onClick={onEnviarNotificacion}
          disabled={enviandoNotificacion}
          className="bg-blue-600 hover:bg-blue-700"
          data-testid="notificar-btn"
        >
          <Send className="w-4 h-4 mr-1" />
          {enviandoNotificacion ? '...' : 'Notificar'}
        </Button>
        <Button size="sm" onClick={onShowCambioEstado} data-testid="change-status-btn">
          Estado
        </Button>
        
        {/* Botones de estados especiales - visibles para admin */}
        {puedeRepresupuestar && onSolicitarRepresupuestar && (
          <Button 
            variant="outline"
            size="sm"
            onClick={onSolicitarRepresupuestar}
            className="border-orange-500 text-orange-600 hover:bg-orange-50"
            data-testid="btn-re-presupuestar"
          >
            <AlertTriangle className="w-4 h-4 mr-1" />
            Re-presupuestar
          </Button>
        )}
        {puedeMarcarIrreparable && onMarcarIrreparable && (
          <Button 
            variant="outline"
            size="sm"
            onClick={onMarcarIrreparable}
            className="border-red-500 text-red-600 hover:bg-red-50"
            data-testid="btn-irreparable"
          >
            <XCircle className="w-4 h-4 mr-1" />
            Irreparable
          </Button>
        )}
      </div>
    </div>
  );
}

export { statusConfig };

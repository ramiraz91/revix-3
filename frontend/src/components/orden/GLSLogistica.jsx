import { useState, useEffect, useCallback } from 'react';
import { Package, Send, ArrowDown, ArrowUp, FileDown, ExternalLink, RotateCw, Loader2, Truck, AlertTriangle, CheckCircle2, Clock, MapPin, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import api from '@/lib/api';

const STATE_COLORS = {
  grabado: 'bg-slate-100 text-slate-700 border-slate-200',
  en_transito: 'bg-indigo-100 text-indigo-700 border-indigo-200',
  en_reparto: 'bg-purple-100 text-purple-700 border-purple-200',
  entregado: 'bg-green-100 text-green-700 border-green-200',
  recogido: 'bg-green-100 text-green-700 border-green-200',
  devuelto: 'bg-red-100 text-red-700 border-red-200',
  anulado: 'bg-gray-100 text-gray-500 border-gray-200',
  error: 'bg-red-200 text-red-800 border-red-300',
  incidencia: 'bg-amber-100 text-amber-700 border-amber-200',
  retenido: 'bg-orange-100 text-orange-700 border-orange-200',
};

const STATE_LABELS = {
  grabado: 'Grabado',
  en_transito: 'En Tránsito',
  en_reparto: 'En Reparto',
  entregado: 'Entregado',
  recogido: 'Recogido',
  devuelto: 'Devuelto',
  anulado: 'Anulado',
  error: 'Error',
  incidencia: 'Incidencia',
  retenido: 'Retenido',
};

const PICKUP_VALID_STATES = ['pendiente_recibir', 'recibida', 'cuarentena', 'en_taller'];
const DELIVERY_VALID_STATES = ['reparado', 'validacion', 'enviado'];
const DEVOLUCION_VALID_STATES = ['enviado', 'entregado', 'incidencia', 'reparado'];

function ShipmentBlock({ tipo, shipment, eventos, total, historial, ordenId, ordenEstado, userRole, onRefresh }) {
  const [syncing, setSyncing] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [showHistorial, setShowHistorial] = useState(false);
  
  const isRecogida = tipo === 'recogida';
  const isDevolucion = tipo === 'devolucion';
  const icon = isRecogida ? <ArrowDown className="w-4 h-4" /> : isDevolucion ? <RotateCw className="w-4 h-4" /> : <ArrowUp className="w-4 h-4" />;
  const color = isRecogida ? 'amber' : isDevolucion ? 'rose' : 'emerald';
  const label = isRecogida ? 'Recogida' : isDevolucion ? 'Devolución' : 'Envío';
  const validStates = isRecogida ? PICKUP_VALID_STATES : isDevolucion ? DEVOLUCION_VALID_STATES : DELIVERY_VALID_STATES;
  const canCreate = validStates.includes(ordenEstado) || userRole === 'master';
  const isAdmin = userRole === 'admin' || userRole === 'master';

  const handleSync = async () => {
    if (!shipment) return;
    setSyncing(true);
    try {
      await api.post(`/ordenes/${ordenId}/logistics/${shipment.id}/sync`);
      toast.success(`${label} actualizado`);
      onRefresh();
    } catch (err) {
      toast.error('Error al sincronizar');
    } finally {
      setSyncing(false);
    }
  };

  const handleDownloadLabel = async () => {
    if (!shipment) return;
    setDownloading(true);
    try {
      const res = await api.get(`/ordenes/${ordenId}/logistics/${shipment.id}/label`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `etiqueta_${tipo}_${shipment.gls_codbarras || shipment.id.slice(0, 8)}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error('Etiqueta no disponible');
    } finally {
      setDownloading(false);
    }
  };

  const estadoInterno = shipment?.estado_interno || '';
  const stateColor = STATE_COLORS[estadoInterno] || 'bg-gray-100 text-gray-600';
  const stateLabel = STATE_LABELS[estadoInterno] || estadoInterno.replace(/_/g, ' ');
  const blockTitle = isRecogida ? 'Recogida' : isDevolucion ? 'Devolución' : 'Envío';

  return (
    <Card className={`border-${color}-200`} data-testid={`logistics-block-${tipo}`}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-base">
            <div className={`p-1.5 rounded-md bg-${color}-100`}>
              {icon}
            </div>
            {blockTitle}
            {total > 1 && <Badge variant="outline" className="text-xs ml-1">{total} total</Badge>}
          </div>
          {shipment && (
            <div className="flex items-center gap-1">
              <Button
                variant="ghost" size="icon" className="h-7 w-7"
                onClick={handleSync} disabled={syncing}
                title="Sincronizar tracking"
                data-testid={`btn-sync-${tipo}`}
              >
                {syncing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCw className="w-3.5 h-3.5" />}
              </Button>
              <Button
                variant="ghost" size="icon" className="h-7 w-7"
                onClick={handleDownloadLabel} disabled={downloading}
                title="Descargar etiqueta"
                data-testid={`btn-label-${tipo}`}
              >
                {downloading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileDown className="w-3.5 h-3.5" />}
              </Button>
              {(shipment.tracking_url || shipment.gls_codbarras) && (
                <a
                  href={shipment.tracking_url || `https://www.gls-spain.es/apptracking.asp?codigo=${shipment.gls_codbarras}`}
                  target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-accent"
                  title="Ver seguimiento GLS"
                  data-testid={`btn-gls-link-${tipo}`}
                >
                  <ExternalLink className="w-3.5 h-3.5 text-blue-500" />
                </a>
              )}
            </div>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!shipment ? (
          <div className="text-center py-6" data-testid={`logistics-empty-${tipo}`}>
            <Package className="w-8 h-8 mx-auto mb-2 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              No hay {blockTitle.toLowerCase()} generada
            </p>
            {!canCreate && isAdmin && (
              <p className="text-xs text-muted-foreground mt-1">
                Estado actual: <strong>{ordenEstado}</strong>.
                {isRecogida 
                  ? ' Disponible en: pendiente_recibir, recibida, cuarentena, en_taller' 
                  : isDevolucion
                    ? ' Disponible en: enviado, entregado, incidencia, reparado'
                    : ' Disponible en: reparado, validacion, enviado'}
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {/* Status and tracking number */}
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Badge className={`text-xs ${stateColor}`}>
                  {stateLabel}
                </Badge>
                {shipment.incidencia_texto && (
                  <Badge variant="outline" className="text-xs text-amber-700 border-amber-300 bg-amber-50">
                    <AlertTriangle className="w-3 h-3 mr-1" />
                    {shipment.incidencia_texto}
                  </Badge>
                )}
              </div>
              {shipment.es_final && shipment.estado_interno === 'entregado' && (
                <CheckCircle2 className="w-4 h-4 text-green-600" />
              )}
            </div>

            {/* Tracking code */}
            <div className="p-3 bg-slate-50 rounded-lg space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground">Codigo de barras</p>
                  <p className="font-mono font-semibold text-sm">{shipment.gls_codbarras || '-'}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">Referencia</p>
                  <p className="font-mono text-sm">{shipment.referencia_interna || '-'}</p>
                </div>
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{shipment.destinatario?.nombre}</span>
                <span>{shipment.created_at ? new Date(shipment.created_at).toLocaleString('es-ES') : ''}</span>
              </div>
              {shipment.entrega_receptor && (
                <div className="flex items-center gap-1 text-xs text-green-700 bg-green-50 p-1.5 rounded">
                  <CheckCircle2 className="w-3 h-3" />
                  Entregado a: {shipment.entrega_receptor}
                  {shipment.entrega_fecha && ` - ${shipment.entrega_fecha}`}
                </div>
              )}
            </div>

            {/* Tracking events */}
            {eventos && eventos.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Ultimos eventos
                </p>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {eventos.slice(0, 5).map((ev, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs py-1 border-l-2 border-slate-200 pl-2">
                      <span className="text-muted-foreground whitespace-nowrap">{ev.fecha_evento}</span>
                      <span>{ev.descripcion_evento || ev.tipo}</span>
                      {ev.nombre_plaza && <span className="text-muted-foreground">({ev.nombre_plaza})</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}


export default function GLSLogistica({ orden, onUpdate, userRole }) {
  const [logisticsData, setLogisticsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showCrear, setShowCrear] = useState(null); // 'recogida' | 'envio' | null
  const [autoSyncing, setAutoSyncing] = useState(false);

  const loadData = useCallback(async (withSync = false) => {
    if (!orden?.id) return;
    try {
      // Si hay envíos, sincronizar automáticamente con GLS para traer el estado actual
      if (withSync) {
        setAutoSyncing(true);
        // Primero obtener los shipments existentes
        const preCheck = await api.get(`/ordenes/${orden.id}/logistics`);
        const recogidaId = preCheck.data?.recogida?.shipment?.id;
        const envioId = preCheck.data?.envio?.shipment?.id;
        
        // Sincronizar cada uno si existe y no está en estado final
        const syncPromises = [];
        if (recogidaId && !preCheck.data?.recogida?.shipment?.es_final) {
          syncPromises.push(api.post(`/ordenes/${orden.id}/logistics/${recogidaId}/sync`).catch(() => {}));
        }
        if (envioId && !preCheck.data?.envio?.shipment?.es_final) {
          syncPromises.push(api.post(`/ordenes/${orden.id}/logistics/${envioId}/sync`).catch(() => {}));
        }
        if (syncPromises.length > 0) {
          await Promise.all(syncPromises);
        }
        setAutoSyncing(false);
      }
      
      const res = await api.get(`/ordenes/${orden.id}/logistics`);
      setLogisticsData(res.data);
    } catch (err) {
      console.error('Error loading logistics:', err);
    } finally {
      setLoading(false);
      setAutoSyncing(false);
    }
  }, [orden?.id]);

  useEffect(() => {
    loadData(true); // true = auto-sync al cargar
  }, [orden?.id]);

  const handleRefresh = () => {
    loadData(true); // Sincronizar al refrescar
    // No llamar a onUpdate aquí para evitar recarga de página completa
    // El componente ya maneja su propio estado (logisticsData)
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        {autoSyncing && <p className="text-xs text-muted-foreground mt-2">Consultando estado en GLS...</p>}
      </div>
    );
  }

  if (!logisticsData?.gls_activo) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          <Truck className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="font-medium">Integracion GLS no activada</p>
          <p className="text-xs mt-1">Configura GLS desde Ajustes &gt; GLS Config</p>
        </CardContent>
      </Card>
    );
  }

  const estado = orden?.estado || '';
  const role = userRole || 'tecnico';
  const isAdmin = role === 'admin' || role === 'master';

  const canCreatePickup = isAdmin && (PICKUP_VALID_STATES.includes(estado) || role === 'master');
  const canCreateDelivery = isAdmin && (DELIVERY_VALID_STATES.includes(estado) || role === 'master');
  const canCreateDevolucion = isAdmin && (DEVOLUCION_VALID_STATES.includes(estado) || role === 'master');

  const hasPickup = !!logisticsData?.recogida?.shipment;
  const hasDelivery = !!logisticsData?.envio?.shipment;
  const hasDevolucion = !!logisticsData?.devolucion?.shipment;

  return (
    <div className="space-y-4" data-testid="gls-logistica-panel">
      {/* Action buttons */}
      {isAdmin && (
        <div className="flex gap-2 flex-wrap">
          <Button
            onClick={() => setShowCrear('recogida')}
            variant="outline" size="sm"
            disabled={!canCreatePickup}
            data-testid="btn-crear-recogida"
          >
            <ArrowDown className="w-4 h-4 mr-1 text-amber-600" />
            {hasPickup ? 'Nueva Recogida' : 'Generar Recogida'}
          </Button>
          <Button
            onClick={() => setShowCrear('envio')}
            variant="outline" size="sm"
            disabled={!canCreateDelivery}
            data-testid="btn-crear-envio"
          >
            <ArrowUp className="w-4 h-4 mr-1 text-emerald-600" />
            {hasDelivery ? 'Nuevo Envío' : 'Generar Envío'}
          </Button>
          <Button
            onClick={() => setShowCrear('devolucion')}
            variant="outline" size="sm"
            disabled={!canCreateDevolucion}
            data-testid="btn-crear-devolucion"
          >
            <RotateCw className="w-4 h-4 mr-1 text-rose-600" />
            {hasDevolucion ? 'Nueva Devolución' : 'Generar Devolución'}
          </Button>
        </div>
      )}

      {/* Three blocks: Recogida, Envio, Devolucion */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ShipmentBlock
          tipo="recogida"
          shipment={logisticsData?.recogida?.shipment}
          eventos={logisticsData?.recogida?.eventos}
          total={logisticsData?.recogida?.total || 0}
          historial={logisticsData?.recogida?.historial || []}
          ordenId={orden?.id}
          ordenEstado={estado}
          userRole={role}
          onRefresh={handleRefresh}
        />
        <ShipmentBlock
          tipo="envio"
          shipment={logisticsData?.envio?.shipment}
          eventos={logisticsData?.envio?.eventos}
          total={logisticsData?.envio?.total || 0}
          historial={logisticsData?.envio?.historial || []}
          ordenId={orden?.id}
          ordenEstado={estado}
          userRole={role}
          onRefresh={handleRefresh}
        />
        <ShipmentBlock
          tipo="devolucion"
          shipment={logisticsData?.devolucion?.shipment}
          eventos={logisticsData?.devolucion?.eventos}
          total={logisticsData?.devolucion?.total || 0}
          historial={logisticsData?.devolucion?.historial || []}
          ordenId={orden?.id}
          ordenEstado={estado}
          userRole={role}
          onRefresh={handleRefresh}
        />
      </div>

      {/* Info note */}
      {!hasPickup && !hasDelivery && !hasDevolucion && (
        <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg text-sm text-blue-700">
          <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <p>
            Usa los botones de arriba para generar recogida, envío o devolución vía GLS.
            La recogida está disponible en estados iniciales, el envío en estados finales de la reparación,
            y la devolución cuando sea necesario retornar un equipo.
          </p>
        </div>
      )}

      {/* Create shipment modal */}
      {showCrear && (
        <CrearEnvioGLSModal
          tipo={showCrear}
          orden={orden}
          onClose={() => setShowCrear(null)}
          onCreated={handleRefresh}
        />
      )}
    </div>
  );
}


function CrearEnvioGLSModal({ tipo, orden, onClose, onCreated }) {
  const [form, setForm] = useState({
    dest_nombre: '',
    dest_direccion: '',
    dest_poblacion: '',
    dest_cp: '',
    dest_provincia: '',
    dest_telefono: '',
    dest_email: '',
    dest_observaciones: '',
    bultos: 1,
    peso: 1,
    referencia: orden?.numero_orden || '',
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Pre-fill from order client data
    const c = orden?.cliente || {};
    setForm(f => ({
      ...f,
      dest_nombre: `${c.nombre || ''} ${c.apellidos || ''}`.trim(),
      dest_direccion: c.direccion || '',
      dest_poblacion: c.ciudad || '',
      dest_cp: c.codigo_postal || '',
      dest_provincia: c.provincia || '',
      dest_telefono: c.telefono || '',
      dest_email: c.email || '',
      referencia: (orden?.numero_orden || orden?.numero_autorizacion || '').slice(0, 20),
    }));
  }, [orden]);

  const handleCrear = async () => {
    if (!form.dest_nombre || !form.dest_direccion || !form.dest_cp) {
      toast.error('Nombre, dirección y CP son obligatorios');
      return;
    }
    if (!form.dest_telefono) {
      toast.error('El teléfono es obligatorio para el transportista');
      return;
    }
    setLoading(true);
    try {
      const endpoints = {
        recogida: `/ordenes/${orden.id}/logistics/pickup`,
        envio: `/ordenes/${orden.id}/logistics/delivery`,
        devolucion: `/ordenes/${orden.id}/logistics/return`,
      };
      const endpoint = endpoints[tipo];
      const payload = {
        ...form,
        bultos: parseInt(form.bultos) || 1,
        peso: parseFloat(form.peso) || 1,
      };
      await api.post(endpoint, payload);
      const labels = { recogida: 'Recogida', envio: 'Envío', devolucion: 'Devolución' };
      toast.success(`${labels[tipo]} GLS creado correctamente`);
      onClose();
      onCreated();
    } catch (err) {
      toast.error(err.response?.data?.detail || `Error al crear ${tipo}`);
    } finally {
      setLoading(false);
    }
  };

  const isRecogida = tipo === 'recogida';
  const isDevolucion = tipo === 'devolucion';
  const tipoLabel = isRecogida ? 'Recogida' : isDevolucion ? 'Devolución' : 'Envío';
  const tipoIcon = isRecogida ? <ArrowDown className="w-5 h-5 text-amber-600" /> 
    : isDevolucion ? <RotateCw className="w-5 h-5 text-rose-600" /> 
    : <ArrowUp className="w-5 h-5 text-emerald-600" />;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()} data-testid="gls-crear-modal">
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            {tipoIcon}
            <h3 className="text-lg font-semibold">
              Generar {tipoLabel} GLS
            </h3>
          </div>
          <p className="text-sm text-muted-foreground mb-4">
            {isRecogida
              ? 'Datos del punto de recogida. El transportista recogerá en esta direccion.'
              : 'Datos del destinatario. El dispositivo reparado se enviara a esta direccion.'}
          </p>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium">Nombre *</label>
              <input className="w-full mt-1 px-3 py-2 border rounded-md text-sm" value={form.dest_nombre} onChange={e => setForm(f => ({ ...f, dest_nombre: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs font-medium">Direccion *</label>
              <input className="w-full mt-1 px-3 py-2 border rounded-md text-sm" value={form.dest_direccion} onChange={e => setForm(f => ({ ...f, dest_direccion: e.target.value }))} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium">Poblacion</label>
                <input className="w-full mt-1 px-3 py-2 border rounded-md text-sm" value={form.dest_poblacion} onChange={e => setForm(f => ({ ...f, dest_poblacion: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium">CP *</label>
                <input className="w-full mt-1 px-3 py-2 border rounded-md text-sm" value={form.dest_cp} onChange={e => setForm(f => ({ ...f, dest_cp: e.target.value }))} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium">Telefono *</label>
                <input className="w-full mt-1 px-3 py-2 border rounded-md text-sm" value={form.dest_telefono} onChange={e => setForm(f => ({ ...f, dest_telefono: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium">Email</label>
                <input className="w-full mt-1 px-3 py-2 border rounded-md text-sm" value={form.dest_email} onChange={e => setForm(f => ({ ...f, dest_email: e.target.value }))} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium">Bultos</label>
                <input type="number" min={1} className="w-full mt-1 px-3 py-2 border rounded-md text-sm" value={form.bultos} onChange={e => setForm(f => ({ ...f, bultos: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium">Peso (kg)</label>
                <input type="number" min={0.1} step={0.1} className="w-full mt-1 px-3 py-2 border rounded-md text-sm" value={form.peso} onChange={e => setForm(f => ({ ...f, peso: e.target.value }))} />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium">Observaciones</label>
              <input className="w-full mt-1 px-3 py-2 border rounded-md text-sm" value={form.dest_observaciones} onChange={e => setForm(f => ({ ...f, dest_observaciones: e.target.value }))} />
            </div>
            {/* Order info */}
            <div className="p-3 bg-slate-50 rounded-lg text-xs text-muted-foreground">
              <p><strong>Orden:</strong> {orden?.numero_orden} {orden?.numero_autorizacion && `| Auth: ${orden.numero_autorizacion}`}</p>
              <p><strong>Dispositivo:</strong> {orden?.dispositivo?.modelo || 'N/A'}</p>
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-4 pt-4 border-t">
            <button className="px-4 py-2 text-sm border rounded-md hover:bg-slate-50" onClick={onClose}>Cancelar</button>
            <button
              className="px-4 py-2 text-sm bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
              onClick={handleCrear} disabled={loading}
              data-testid="btn-confirmar-gls"
            >
              {loading ? 'Creando...' : `Confirmar ${isRecogida ? 'Recogida' : 'Envio'}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

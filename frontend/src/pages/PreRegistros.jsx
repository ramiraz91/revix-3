import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  FileText, Search, Clock, CheckCircle, XCircle, ExternalLink, 
  Send, Plus, Trash2, AlertTriangle, RefreshCw, Loader2, Eye
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { useNavigate } from 'react-router-dom';
import API from '@/lib/api';
import { toast } from 'sonner';

const ESTADO_LABELS = {
  pendiente_presupuesto: { label: 'Pendiente Presupuesto', color: 'bg-amber-100 text-amber-800', icon: Clock },
  presupuesto_enviado: { label: 'Presupuesto Enviado', color: 'bg-blue-100 text-blue-800', icon: Send },
  aceptado: { label: 'Aceptado', color: 'bg-green-100 text-green-800', icon: CheckCircle },
  rechazado: { label: 'Rechazado', color: 'bg-red-100 text-red-800', icon: XCircle },
  orden_creada: { label: 'Orden Creada', color: 'bg-purple-100 text-purple-800', icon: FileText },
  cancelado: { label: 'Cancelado', color: 'bg-gray-100 text-gray-800', icon: XCircle },
  archivado: { label: 'Archivado', color: 'bg-gray-100 text-gray-800', icon: FileText },
  recotizar: { label: 'Recotizar', color: 'bg-orange-100 text-orange-800', icon: AlertTriangle },
};

export default function PreRegistros() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [estadoFilter, setEstadoFilter] = useState('activos');
  const [selected, setSelected] = useState(null);
  const [creandoOrden, setCreandoOrden] = useState(false);
  const [limpiando, setLimpiando] = useState(false);
  const [showLimpiarDialog, setShowLimpiarDialog] = useState(false);
  const navigate = useNavigate();

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      if (estadoFilter === 'activos') {
        // No filter - backend excludes cancelled by default
      } else if (estadoFilter === 'todos') {
        params.incluir_cancelados = true;
      } else {
        params.estado = estadoFilter;
        if (['cancelado', 'rechazado', 'archivado'].includes(estadoFilter)) {
          params.incluir_cancelados = true;
        }
      }
      const res = await API.get('/pre-registros', { params });
      setItems(res.data);
    } catch (err) {
      console.error(err);
      toast.error('Error cargando pre-registros');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [search, estadoFilter]);

  const handleCrearOrden = async (item) => {
    setCreandoOrden(true);
    try {
      const res = await API.post(`/pre-registros/${item.id}/crear-orden`);
      toast.success(`Orden ${res.data.numero_orden} creada correctamente`);
      setSelected(null);
      fetchData();
      // Navigate to the new order
      if (res.data.orden_id) {
        navigate(`/ordenes/${res.data.orden_id}`);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error creando orden');
    } finally {
      setCreandoOrden(false);
    }
  };

  const handleIrAPresupuesto = (codigo) => {
    navigate(`/insurama?buscar=${codigo}`);
  };

  const handleEstadoChange = async (id, nuevoEstado) => {
    try {
      await API.patch(`/pre-registros/${id}/estado`, { estado: nuevoEstado });
      toast.success(`Estado actualizado a ${ESTADO_LABELS[nuevoEstado]?.label || nuevoEstado}`);
      setItems(prev => prev.map(i => i.id === id ? {...i, estado: nuevoEstado} : i));
      setSelected(null);
    } catch (e) {
      toast.error('Error actualizando estado');
    }
  };

  const handleLimpiarCancelados = async () => {
    setLimpiando(true);
    try {
      const res = await API.delete('/pre-registros/limpiar-cancelados');
      toast.success(res.data.message);
      setShowLimpiarDialog(false);
      fetchData();
    } catch (e) {
      toast.error('Error limpiando pre-registros');
    } finally {
      setLimpiando(false);
    }
  };

  const handleEliminar = async (id) => {
    try {
      await API.delete(`/pre-registros/${id}`);
      toast.success('Pre-registro eliminado');
      setItems(prev => prev.filter(i => i.id !== id));
      setSelected(null);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error eliminando pre-registro');
    }
  };

  // Count cancelled items for cleanup button
  const cancelledCount = items.filter(i => ['cancelado', 'rechazado', 'archivado'].includes(i.estado)).length;

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="w-8 h-8 animate-spin text-primary" />
    </div>
  );

  return (
    <div className="space-y-4" data-testid="pre-registros-page">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <FileText className="w-6 h-6" /> Pre-Registros Insurama
        </h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchData}>
            <RefreshCw className="w-4 h-4 mr-1" /> Actualizar
          </Button>
          {estadoFilter === 'todos' && cancelledCount > 0 && (
            <Button 
              variant="destructive" 
              size="sm" 
              onClick={() => setShowLimpiarDialog(true)}
            >
              <Trash2 className="w-4 h-4 mr-1" /> Limpiar cancelados ({cancelledCount})
            </Button>
          )}
          <Badge variant="outline">{items.length} registros</Badge>
        </div>
      </div>

      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input 
            placeholder="Buscar por código siniestro, asunto o cliente..." 
            value={search} 
            onChange={e => setSearch(e.target.value)} 
            className="pl-10 h-9" 
          />
        </div>
        <Select value={estadoFilter} onValueChange={setEstadoFilter}>
          <SelectTrigger className="w-56 h-9"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="activos">Solo activos (sin cancelados)</SelectItem>
            <SelectItem value="todos">Todos los estados</SelectItem>
            <SelectItem value="pendiente_presupuesto">Pendiente Presupuesto</SelectItem>
            <SelectItem value="presupuesto_enviado">Presupuesto Enviado</SelectItem>
            <SelectItem value="aceptado">Aceptado</SelectItem>
            <SelectItem value="orden_creada">Con Orden Creada</SelectItem>
            <SelectItem value="rechazado">Rechazados</SelectItem>
            <SelectItem value="cancelado">Cancelados</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {items.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No hay pre-registros {estadoFilter !== 'todos' && estadoFilter !== 'activos' ? `con estado "${ESTADO_LABELS[estadoFilter]?.label}"` : ''}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {items.map(item => {
            const est = ESTADO_LABELS[item.estado] || { label: item.estado, color: 'bg-gray-100', icon: FileText };
            const IconComponent = est.icon;
            const canCreateOrder = item.estado === 'pendiente_presupuesto' || item.estado === 'aceptado' || item.estado === 'presupuesto_enviado';
            const canSendBudget = item.estado === 'pendiente_presupuesto' || item.estado === 'recotizar';
            const isCancelled = ['cancelado', 'rechazado', 'archivado'].includes(item.estado);
            
            return (
              <Card 
                key={item.id} 
                className={`hover:shadow-sm transition-shadow ${isCancelled ? 'opacity-60' : ''}`}
              >
                <CardContent className="py-3 flex items-center justify-between">
                  <div className="flex items-center gap-4 cursor-pointer flex-1" onClick={() => setSelected(item)}>
                    <div className="min-w-0">
                      <p className="font-mono font-bold text-sm">{item.codigo_siniestro}</p>
                      <p className="text-xs text-muted-foreground truncate max-w-md">
                        {item.cliente_nombre || item.email_subject || 'Sin descripción'}
                      </p>
                      {item.dispositivo_modelo && (
                        <p className="text-xs text-muted-foreground">{item.dispositivo_modelo}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={`text-xs ${est.color} flex items-center gap-1`}>
                      <IconComponent className="w-3 h-3" />
                      {est.label}
                    </Badge>
                    
                    {/* Action buttons based on state */}
                    {canSendBudget && (
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={(e) => { e.stopPropagation(); handleIrAPresupuesto(item.codigo_siniestro); }}
                        className="text-blue-600"
                      >
                        <Send className="w-3 h-3 mr-1" /> Enviar Presupuesto
                      </Button>
                    )}
                    
                    {canCreateOrder && !item.orden_id && (
                      <Button 
                        variant="default" 
                        size="sm" 
                        onClick={(e) => { e.stopPropagation(); handleCrearOrden(item); }}
                        disabled={creandoOrden}
                      >
                        {creandoOrden ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Plus className="w-3 h-3 mr-1" />}
                        Crear Orden
                      </Button>
                    )}
                    
                    {item.orden_id && (
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={e => { e.stopPropagation(); navigate(`/ordenes/${item.orden_id}`); }}
                      >
                        <ExternalLink className="w-3 h-3 mr-1" /> Ver Orden
                      </Button>
                    )}
                    
                    {isCancelled && (
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={(e) => { e.stopPropagation(); handleEliminar(item.id); }}
                        className="text-red-500 hover:text-red-700"
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    )}
                    
                    <span className="text-xs text-muted-foreground">{item.created_at?.slice(0, 10)}</span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Detail Dialog */}
      <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Pre-Registro: {selected?.codigo_siniestro}
            </DialogTitle>
          </DialogHeader>
          {selected && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Estado</p>
                  <Badge className={ESTADO_LABELS[selected.estado]?.color}>
                    {ESTADO_LABELS[selected.estado]?.label}
                  </Badge>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Fecha</p>
                  <p>{selected.created_at?.slice(0, 19).replace('T', ' ')}</p>
                </div>
                {selected.cliente_nombre && (
                  <div className="col-span-2">
                    <p className="text-xs text-muted-foreground">Cliente</p>
                    <p className="font-medium">{selected.cliente_nombre}</p>
                  </div>
                )}
                {selected.dispositivo_modelo && (
                  <div className="col-span-2">
                    <p className="text-xs text-muted-foreground">Dispositivo</p>
                    <p>{selected.dispositivo_modelo}</p>
                  </div>
                )}
                {selected.daño_descripcion && (
                  <div className="col-span-2">
                    <p className="text-xs text-muted-foreground">Descripción del daño</p>
                    <p className="text-sm">{selected.daño_descripcion}</p>
                  </div>
                )}
                {selected.sumbroker_price && (
                  <div>
                    <p className="text-xs text-muted-foreground">Precio Sumbroker</p>
                    <p className="font-bold text-green-600">{selected.sumbroker_price}€</p>
                  </div>
                )}
                {selected.sumbroker_status_text && (
                  <div>
                    <p className="text-xs text-muted-foreground">Estado Sumbroker</p>
                    <p>{selected.sumbroker_status_text}</p>
                  </div>
                )}
              </div>

              {selected.historial?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-2">Historial</p>
                  <div className="space-y-1 max-h-32 overflow-y-auto border rounded-md p-2 bg-muted/20">
                    {selected.historial.map((h, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs py-1 border-b border-border/50 last:border-0">
                        <Clock className="w-3 h-3 text-muted-foreground mt-0.5 shrink-0" />
                        <div>
                          <span className="text-muted-foreground">{h.fecha?.slice(0, 19).replace('T', ' ')}</span>
                          <span className="ml-2">{h.detalle || h.evento}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Action buttons */}
              <div className="flex flex-wrap gap-2 pt-2 border-t">
                {(selected.estado === 'pendiente_presupuesto' || selected.estado === 'recotizar') && (
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => handleIrAPresupuesto(selected.codigo_siniestro)}
                    className="text-blue-600"
                  >
                    <Send className="w-4 h-4 mr-1" /> Enviar Presupuesto
                  </Button>
                )}
                
                {(selected.estado === 'pendiente_presupuesto' || selected.estado === 'aceptado' || selected.estado === 'presupuesto_enviado') && !selected.orden_id && (
                  <Button 
                    size="sm" 
                    onClick={() => handleCrearOrden(selected)}
                    disabled={creandoOrden}
                  >
                    {creandoOrden ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Plus className="w-4 h-4 mr-1" />}
                    Crear Orden
                  </Button>
                )}
                
                {selected.orden_id && (
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => { setSelected(null); navigate(`/ordenes/${selected.orden_id}`); }}
                  >
                    <ExternalLink className="w-4 h-4 mr-1" /> Ver Orden
                  </Button>
                )}
                
                {selected.estado === 'pendiente_presupuesto' && (
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => handleEstadoChange(selected.id, 'presupuesto_enviado')}
                  >
                    Marcar Presupuesto Enviado
                  </Button>
                )}
                
                {!['cancelado', 'rechazado', 'archivado', 'orden_creada'].includes(selected.estado) && (
                  <Button 
                    size="sm" 
                    variant="destructive"
                    onClick={() => handleEstadoChange(selected.id, 'archivado')}
                  >
                    Archivar
                  </Button>
                )}
                
                {['cancelado', 'rechazado', 'archivado'].includes(selected.estado) && (
                  <Button 
                    size="sm" 
                    variant="destructive"
                    onClick={() => handleEliminar(selected.id)}
                  >
                    <Trash2 className="w-4 h-4 mr-1" /> Eliminar
                  </Button>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Confirm cleanup dialog */}
      <Dialog open={showLimpiarDialog} onOpenChange={setShowLimpiarDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="w-5 h-5" />
              Confirmar limpieza
            </DialogTitle>
            <DialogDescription>
              ¿Estás seguro de que deseas eliminar todos los pre-registros cancelados, rechazados y archivados?
              Esta acción no se puede deshacer.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLimpiarDialog(false)}>
              Cancelar
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleLimpiarCancelados}
              disabled={limpiando}
            >
              {limpiando ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Trash2 className="w-4 h-4 mr-1" />}
              Eliminar {cancelledCount} registros
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

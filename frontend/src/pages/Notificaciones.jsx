import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Bell, Check, Trash2, ExternalLink, AlertTriangle, Package, Wrench, CheckCircle2,
  MessageSquare, Unlock, Square, XSquare,
  Truck, XCircle, Edit3, MessagesSquare, Inbox,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { notificacionesAPI } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';

const notificationIcons = {
  material_añadido: AlertTriangle,
  material_pendiente: Package,
  llegada_repuesto: Package,
  orden_reparada: Wrench,
  orden_completada: CheckCircle2,
  mensaje_admin: MessageSquare,
  orden_desbloqueada: Unlock,
  orden_asignada: Wrench,
  material_aprobado: CheckCircle2,
  presupuesto_aceptado: CheckCircle2,
  presupuesto_rechazado: XCircle,
  gls_tracking_update: Truck,
  gls_incidencia: AlertTriangle,
  gls_entregado: CheckCircle2,
  orden_estado_cambiado: Edit3,
  orden_rechazada: XCircle,
  aseguradora_rechazo: XCircle,
  incidencia_abierta: AlertTriangle,
  incidencia_agente: AlertTriangle,
  mensaje_tecnico: MessagesSquare,
};

const notificationColors = {
  material_añadido: { bg: 'bg-orange-100', text: 'text-orange-600' },
  material_pendiente: { bg: 'bg-yellow-100', text: 'text-yellow-600' },
  llegada_repuesto: { bg: 'bg-green-100', text: 'text-green-600' },
  orden_reparada: { bg: 'bg-blue-100', text: 'text-blue-600' },
  orden_completada: { bg: 'bg-emerald-100', text: 'text-emerald-600' },
  mensaje_admin: { bg: 'bg-purple-100', text: 'text-purple-600' },
  orden_desbloqueada: { bg: 'bg-green-100', text: 'text-green-600' },
  orden_asignada: { bg: 'bg-blue-100', text: 'text-blue-600' },
  material_aprobado: { bg: 'bg-green-100', text: 'text-green-600' },
  presupuesto_aceptado: { bg: 'bg-green-100', text: 'text-green-600' },
  presupuesto_rechazado: { bg: 'bg-red-100', text: 'text-red-600' },
  gls_tracking_update: { bg: 'bg-blue-100', text: 'text-blue-600' },
  gls_incidencia: { bg: 'bg-red-100', text: 'text-red-600' },
  gls_entregado: { bg: 'bg-emerald-100', text: 'text-emerald-600' },
  orden_estado_cambiado: { bg: 'bg-indigo-100', text: 'text-indigo-600' },
  orden_rechazada: { bg: 'bg-red-100', text: 'text-red-600' },
  aseguradora_rechazo: { bg: 'bg-red-100', text: 'text-red-600' },
  incidencia_abierta: { bg: 'bg-red-100', text: 'text-red-600' },
  incidencia_agente: { bg: 'bg-red-100', text: 'text-red-600' },
  mensaje_tecnico: { bg: 'bg-purple-100', text: 'text-purple-600' },
};

// Tipos de notificaciones que puede ver un técnico
const TIPOS_TECNICO = [
  'mensaje_admin',
  'orden_desbloqueada',
  'orden_asignada',
  'material_aprobado',
];

// Catálogo de categorías visible en el dashboard
const CATEGORIAS = [
  { id: null,                      label: 'Todas',        icon: Inbox },
  { id: 'LOGISTICA',               label: 'Logística',    icon: Truck },
  { id: 'INCIDENCIA_LOGISTICA',    label: 'Incidencias GLS', icon: AlertTriangle },
  { id: 'INCIDENCIA',              label: 'Incidencias',  icon: AlertTriangle },
  { id: 'COMUNICACION_INTERNA',    label: 'Comunicación', icon: MessagesSquare },
  { id: 'RECHAZO',                 label: 'Rechazos',     icon: XCircle },
  { id: 'MODIFICACION',            label: 'Modificaciones', icon: Edit3 },
  { id: 'GENERAL',                 label: 'Otras',        icon: Bell },
];

// Mapeo tipo → ruta destino al clicar
function rutaDestinoClick(notif) {
  if (notif.orden_id) return `/crm/ordenes/${notif.orden_id}`;
  return null;
}

export default function Notificaciones() {
  const [notificaciones, setNotificaciones] = useState([]);
  const [contadores, setContadores] = useState({ total: 0, no_leidas: 0, por_categoria: {} });
  const [categoriaSel, setCategoriaSel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [selectionMode, setSelectionMode] = useState(false);
  const navigate = useNavigate();
  const { user, isTecnico, isAdmin } = useAuth();

  const fetchContadores = async () => {
    try {
      const res = await notificacionesAPI.contadores();
      setContadores(res.data);
    } catch {
      // silent
    }
  };

  const fetchNotificaciones = async () => {
    try {
      setLoading(true);
      const res = await notificacionesAPI.listar(false, categoriaSel);
      let data = res.data;
      if (isTecnico()) {
        data = data.filter(n => {
          const tipoPermitido = TIPOS_TECNICO.includes(n.tipo);
          const esParaMi = !n.usuario_destino || n.usuario_destino === user?.id;
          return tipoPermitido && esParaMi;
        });
      }
      setNotificaciones(data);
    } catch (error) {
      toast.error('Error al cargar notificaciones');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotificaciones();
    fetchContadores();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoriaSel]);

  // Reset selection when exiting selection mode
  useEffect(() => {
    if (!selectionMode) {
      setSelectedIds(new Set());
    }
  }, [selectionMode]);

  const toggleSelection = (id) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const selectAll = () => {
    setSelectedIds(new Set(notificaciones.map(n => n.id)));
  };

  const selectNone = () => {
    setSelectedIds(new Set());
  };

  const handleClickNotificacion = async (notificacion) => {
    if (selectionMode) {
      toggleSelection(notificacion.id);
      return;
    }

    if (!notificacion.leida) {
      try {
        await notificacionesAPI.marcarLeida(notificacion.id);
        setNotificaciones(prev =>
          prev.map(n => n.id === notificacion.id ? { ...n, leida: true } : n)
        );
        fetchContadores();
        window.dispatchEvent(new Event('notificaciones-updated'));
      } catch {
        // silent
      }
    }
    const ruta = rutaDestinoClick(notificacion);
    if (ruta) navigate(ruta);
  };

  const handleMarcarTodasLeidas = async () => {
    try {
      const res = await notificacionesAPI.marcarTodasLeidas();
      toast.success(`${res.data.modificadas} notificaciones marcadas como leídas`);
      setNotificaciones(prev => prev.map(n => ({ ...n, leida: true })));
      fetchContadores();
      window.dispatchEvent(new Event('notificaciones-updated'));
    } catch {
      toast.error('No se pudieron marcar todas como leídas');
    }
  };

  const handleMarcarLeida = async (e, id) => {
    e.stopPropagation();
    try {
      await notificacionesAPI.marcarLeida(id);
      // Actualización silenciosa del estado local
      setNotificaciones(prev => 
        prev.map(n => n.id === id ? { ...n, leida: true } : n)
      );
      window.dispatchEvent(new Event('notificaciones-updated'));
    } catch (error) {
      toast.error('Error al marcar como leída');
    }
  };

  const handleEliminar = async (e, id) => {
    e.stopPropagation();
    try {
      await notificacionesAPI.eliminar(id);
      // Actualización silenciosa del estado local
      setNotificaciones(prev => prev.filter(n => n.id !== id));
      toast.success('Notificación eliminada');
      window.dispatchEvent(new Event('notificaciones-updated'));
    } catch (error) {
      toast.error('Error al eliminar notificación');
    }
  };

  const handleEliminarSeleccionados = async () => {
    if (selectedIds.size === 0) return;
    
    try {
      const idsArray = Array.from(selectedIds);
      const res = await notificacionesAPI.eliminarMasivo(idsArray);
      // Actualización silenciosa del estado local
      setNotificaciones(prev => prev.filter(n => !selectedIds.has(n.id)));
      toast.success(`${res.data.eliminadas} notificaciones eliminadas`);
      setSelectedIds(new Set());
      setSelectionMode(false);
      window.dispatchEvent(new Event('notificaciones-updated'));
    } catch (error) {
      toast.error('Error al eliminar notificaciones');
    }
  };

  const handleMarcarLeidasSeleccionadas = async () => {
    if (selectedIds.size === 0) return;
    
    try {
      const idsArray = Array.from(selectedIds);
      const res = await notificacionesAPI.marcarLeidasMasivo(idsArray);
      // Actualización silenciosa del estado local
      setNotificaciones(prev => 
        prev.map(n => selectedIds.has(n.id) ? { ...n, leida: true } : n)
      );
      toast.success(`${res.data.modificadas} notificaciones marcadas como leídas`);
      setSelectedIds(new Set());
      setSelectionMode(false);
      window.dispatchEvent(new Event('notificaciones-updated'));
    } catch (error) {
      toast.error('Error al marcar notificaciones');
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor(diff / (1000 * 60));

    if (minutes < 60) return `Hace ${minutes} min`;
    if (hours < 24) return `Hace ${hours}h`;
    return date.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="notificaciones-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Notificaciones</h1>
          <p className="text-muted-foreground mt-1">
            {contadores.no_leidas > 0
              ? `${contadores.no_leidas} sin leer · ${contadores.total} totales`
              : 'Todas las notificaciones leídas'}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {contadores.no_leidas > 0 && (
            <Badge variant="destructive" className="h-8 px-4" data-testid="badge-no-leidas-total">
              {contadores.no_leidas} nuevas
            </Badge>
          )}
          {contadores.no_leidas > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleMarcarTodasLeidas}
              data-testid="btn-marcar-todas-leidas"
            >
              <Check className="w-4 h-4 mr-1" /> Marcar todas leídas
            </Button>
          )}
          {notificaciones.length > 0 && (
            <Button
              variant={selectionMode ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectionMode(!selectionMode)}
            >
              {selectionMode ? <XSquare className="w-4 h-4 mr-1" /> : <Square className="w-4 h-4 mr-1" />}
              {selectionMode ? 'Cancelar' : 'Seleccionar'}
            </Button>
          )}
        </div>
      </div>

      {/* Dashboard por categoría: tabs con contador */}
      <div className="flex flex-wrap gap-2" data-testid="filtro-categorias">
        {CATEGORIAS.map((cat) => {
          const isActive = categoriaSel === cat.id;
          const catStats = cat.id ? contadores.por_categoria?.[cat.id] : null;
          const totalCat = cat.id ? (catStats?.total || 0) : contadores.total;
          const noLeidasCat = cat.id ? (catStats?.no_leidas || 0) : contadores.no_leidas;
          const Icon = cat.icon;
          return (
            <button
              key={String(cat.id)}
              type="button"
              onClick={() => setCategoriaSel(cat.id)}
              data-testid={`filtro-cat-${cat.id || 'all'}`}
              className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm transition ${
                isActive
                  ? 'bg-primary text-primary-foreground border-primary shadow-sm'
                  : 'bg-white text-slate-700 border-slate-200 hover:border-primary/40 hover:bg-primary/5'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{cat.label}</span>
              <Badge
                variant={isActive ? 'secondary' : 'outline'}
                className="text-[10px] h-4 px-1.5"
              >
                {noLeidasCat > 0 ? `${noLeidasCat}/${totalCat}` : totalCat}
              </Badge>
            </button>
          );
        })}
      </div>

      {/* Selection Actions Bar */}
      {selectionMode && (
        <Card className="border-primary bg-primary/5">
          <CardContent className="py-3 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium">
                {selectedIds.size} seleccionadas
              </span>
              <Button variant="ghost" size="sm" onClick={selectAll}>
                Seleccionar todas
              </Button>
              <Button variant="ghost" size="sm" onClick={selectNone}>
                Deseleccionar
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <Button 
                variant="outline" 
                size="sm"
                onClick={handleMarcarLeidasSeleccionadas}
                disabled={selectedIds.size === 0}
              >
                <Check className="w-4 h-4 mr-1" />
                Marcar leídas
              </Button>
              <Button 
                variant="destructive" 
                size="sm"
                onClick={handleEliminarSeleccionados}
                disabled={selectedIds.size === 0}
              >
                <Trash2 className="w-4 h-4 mr-1" />
                Eliminar ({selectedIds.size})
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Notifications List */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-muted-foreground">
              Cargando notificaciones...
            </div>
          ) : notificaciones.length === 0 ? (
            <div className="p-8 text-center">
              <Bell className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-lg font-medium">No hay notificaciones</p>
              <p className="text-muted-foreground">Las alertas del sistema aparecerán aquí</p>
            </div>
          ) : (
            <div className="divide-y">
              {notificaciones.map((notificacion) => {
                const Icon = notificationIcons[notificacion.tipo] || Bell;
                const colors = notificationColors[notificacion.tipo] || { bg: 'bg-blue-100', text: 'text-blue-600' };
                const isSelected = selectedIds.has(notificacion.id);
                
                return (
                  <div 
                    key={notificacion.id}
                    className={`p-4 flex items-start gap-4 transition-colors cursor-pointer hover:bg-slate-50 ${
                      !notificacion.leida ? 'bg-blue-50/50' : ''
                    } ${isSelected ? 'bg-primary/10 hover:bg-primary/15' : ''}`}
                    data-testid={`notificacion-${notificacion.id}`}
                    onClick={() => handleClickNotificacion(notificacion)}
                  >
                    {/* Checkbox for selection mode */}
                    {selectionMode && (
                      <div className="flex items-center pt-1" onClick={(e) => e.stopPropagation()}>
                        <Checkbox 
                          checked={isSelected}
                          onCheckedChange={() => toggleSelection(notificacion.id)}
                          data-testid={`checkbox-${notificacion.id}`}
                        />
                      </div>
                    )}
                    
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${colors.bg}`}>
                      <Icon className={`w-5 h-5 ${colors.text}`} />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          {notificacion.titulo && (
                            <p className={`text-sm ${!notificacion.leida ? 'font-semibold' : 'font-medium'}`}>
                              {notificacion.titulo}
                            </p>
                          )}
                          <p className={`text-sm ${!notificacion.leida ? 'text-slate-700' : 'text-muted-foreground'}`}>
                            {notificacion.mensaje}
                          </p>
                          <div className="flex items-center gap-2 mt-1 flex-wrap">
                            <p className="text-xs text-muted-foreground">
                              {formatDate(notificacion.created_at)}
                            </p>
                            {notificacion.categoria && (
                              <Badge variant="outline" className="text-[9px] h-4">
                                {notificacion.categoria.replace(/_/g, ' ')}
                              </Badge>
                            )}
                            <Badge variant="outline" className="text-[9px] h-4">
                              {notificacion.tipo?.replace(/_/g, ' ')}
                            </Badge>
                          </div>
                        </div>
                        {!notificacion.leida && !selectionMode && (
                          <div className="w-2 h-2 rounded-full bg-blue-500 mt-2 flex-shrink-0" />
                        )}
                      </div>
                      
                      {!selectionMode && (
                        <div className="flex items-center gap-2 mt-2">
                          {notificacion.orden_id && (
                            <Badge variant="secondary" className="text-[10px]">
                              <ExternalLink className="w-3 h-3 mr-1" />
                              Ver Ficha
                            </Badge>
                          )}
                          {!notificacion.leida && (
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="h-7 text-xs"
                              onClick={(e) => handleMarcarLeida(e, notificacion.id)}
                            >
                              <Check className="w-3 h-3 mr-1" />
                              Leída
                            </Button>
                          )}
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="h-7 text-xs text-destructive hover:text-destructive"
                            onClick={(e) => handleEliminar(e, notificacion.id)}
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

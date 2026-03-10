import { useState, useEffect } from 'react';
import { 
  Calendar as CalendarIcon, 
  ChevronLeft, 
  ChevronRight,
  Plus,
  Wrench,
  Package,
  Truck,
  Palmtree,
  UserX,
  Users,
  Clock,
  Loader2,
  X,
  Edit,
  Trash2
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { calendarioAPI, usuariosAPI, ordenesAPI } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

const tipoEventoConfig = {
  orden_asignada: { label: 'Orden Asignada', icon: Wrench, color: '#3b82f6', bgColor: 'bg-blue-100' },
  llegada_dispositivo: { label: 'Llegada Dispositivo', icon: Package, color: '#10b981', bgColor: 'bg-green-100' },
  llegada_repuesto: { label: 'Llegada Repuesto', icon: Truck, color: '#f59e0b', bgColor: 'bg-amber-100' },
  vacaciones: { label: 'Vacaciones', icon: Palmtree, color: '#8b5cf6', bgColor: 'bg-purple-100' },
  ausencia: { label: 'Ausencia', icon: UserX, color: '#ef4444', bgColor: 'bg-red-100' },
  reunion: { label: 'Reunión', icon: Users, color: '#06b6d4', bgColor: 'bg-cyan-100' },
  otro: { label: 'Otro', icon: Clock, color: '#6b7280', bgColor: 'bg-slate-100' },
};

const DAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
const MONTHS = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

export default function Calendario() {
  const { user, isAdmin } = useAuth();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [eventos, setEventos] = useState([]);
  const [tecnicos, setTecnicos] = useState([]);
  const [ordenesPendientes, setOrdenesPendientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTecnico, setSelectedTecnico] = useState('all');
  const [disponibilidadTecnicos, setDisponibilidadTecnicos] = useState([]);
  const [selectedDateForAvailability, setSelectedDateForAvailability] = useState(new Date().toISOString().split('T')[0]);
  
  // Modal states
  const [showEventModal, setShowEventModal] = useState(false);
  const [showAsignarModal, setShowAsignarModal] = useState(false);
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [eventForm, setEventForm] = useState({
    titulo: '',
    descripcion: '',
    tipo: 'otro',
    fecha_inicio: '',
    fecha_fin: '',
    todo_el_dia: true,
    usuario_id: '',
    color: '',
  });
  const [asignarForm, setAsignarForm] = useState({
    orden_id: '',
    tecnico_id: '',
    fecha_estimada: '',
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchData();
  }, [currentDate, selectedTecnico]);

  useEffect(() => {
    // Obtener disponibilidad de técnicos cuando cambia la fecha seleccionada
    const fetchDisponibilidad = async () => {
      if (isAdmin()) {
        try {
          const res = await calendarioAPI.disponibilidadTecnicos(selectedDateForAvailability);
          setDisponibilidadTecnicos(res.data || []);
        } catch (error) {
          console.error('Error obteniendo disponibilidad:', error);
          setDisponibilidadTecnicos([]);
        }
      }
    };
    fetchDisponibilidad();
  }, [selectedDateForAvailability, eventos]);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Get first and last day of current month view (including overflow from adjacent months)
      const year = currentDate.getFullYear();
      const month = currentDate.getMonth();
      const firstDay = new Date(year, month, 1);
      const lastDay = new Date(year, month + 1, 0);
      
      // Extend to include days shown from prev/next month
      const startOffset = (firstDay.getDay() + 6) % 7;
      const viewStart = new Date(firstDay);
      viewStart.setDate(viewStart.getDate() - startOffset);
      
      const endOffset = (7 - lastDay.getDay()) % 7;
      const viewEnd = new Date(lastDay);
      viewEnd.setDate(viewEnd.getDate() + endOffset);

      const params = {
        fecha_desde: viewStart.toISOString().split('T')[0],
        fecha_hasta: viewEnd.toISOString().split('T')[0],
      };
      
      if (selectedTecnico !== 'all') {
        params.usuario_id = selectedTecnico;
      }

      // Realizar las llamadas por separado para manejar errores individualmente
      let eventosData = [];
      let tecnicosData = [];
      let ordenesData = [];
      
      try {
        const eventosRes = await calendarioAPI.listarEventos(params);
        eventosData = eventosRes.data || [];
      } catch (e) {
        console.error('Error cargando eventos:', e);
      }
      
      try {
        const tecnicosRes = await usuariosAPI.listar({ role: 'tecnico', activo: true });
        tecnicosData = tecnicosRes.data || [];
      } catch (e) {
        console.error('Error cargando técnicos:', e);
      }
      
      try {
        const ordenesRes = await ordenesAPI.listarPaginado({ estado: 'pendiente_recibir', page_size: 100 });
        ordenesData = ordenesRes.data.data || [];
      } catch (e) {
        console.error('Error cargando órdenes:', e);
      }

      setEventos(eventosData);
      setTecnicos(tecnicosData);
      setOrdenesPendientes(ordenesData);
    } catch (error) {
      console.error('Error al cargar calendario:', error);
      toast.error('Error al cargar el calendario. Intente de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  const prevMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  };

  const nextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  const getDaysInMonth = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    
    const days = [];
    
    // Add days from previous month
    const startOffset = (firstDay.getDay() + 6) % 7; // Monday = 0
    for (let i = startOffset - 1; i >= 0; i--) {
      const date = new Date(year, month, -i);
      days.push({ date, isCurrentMonth: false });
    }
    
    // Add days of current month
    for (let i = 1; i <= lastDay.getDate(); i++) {
      days.push({ date: new Date(year, month, i), isCurrentMonth: true });
    }
    
    // Add days from next month
    const remaining = 42 - days.length; // 6 weeks * 7 days
    for (let i = 1; i <= remaining; i++) {
      days.push({ date: new Date(year, month + 1, i), isCurrentMonth: false });
    }
    
    return days;
  };

  const getEventsForDate = (date) => {
    const dateStr = date.toISOString().split('T')[0];
    return eventos.filter(e => {
      const eventStart = e.fecha_inicio?.split('T')[0];
      const eventEnd = e.fecha_fin?.split('T')[0] || eventStart;
      return dateStr >= eventStart && dateStr <= eventEnd;
    });
  };

  const isToday = (date) => {
    const today = new Date();
    return date.getDate() === today.getDate() &&
           date.getMonth() === today.getMonth() &&
           date.getFullYear() === today.getFullYear();
  };

  const handleDayClick = (date) => {
    if (!isAdmin()) return;
    setSelectedDate(date);
    setEventForm({
      titulo: '',
      descripcion: '',
      tipo: 'otro',
      fecha_inicio: date.toISOString().split('T')[0],
      fecha_fin: date.toISOString().split('T')[0],
      todo_el_dia: true,
      usuario_id: '',
      color: '',
    });
    setSelectedEvent(null);
    setShowEventModal(true);
  };

  const handleEventClick = (event, e) => {
    e.stopPropagation();
    if (!isAdmin()) return;
    setSelectedEvent(event);
    setEventForm({
      titulo: event.titulo,
      descripcion: event.descripcion || '',
      tipo: event.tipo,
      fecha_inicio: event.fecha_inicio?.split('T')[0] || '',
      fecha_fin: event.fecha_fin?.split('T')[0] || event.fecha_inicio?.split('T')[0] || '',
      todo_el_dia: event.todo_el_dia !== false,
      usuario_id: event.usuario_id || '',
      color: event.color || '',
    });
    setShowEventModal(true);
  };

  const handleSaveEvent = async () => {
    if (!eventForm.titulo || !eventForm.fecha_inicio) {
      toast.error('Título y fecha son obligatorios');
      return;
    }

    setSaving(true);
    try {
      const data = {
        ...eventForm,
        color: eventForm.color || tipoEventoConfig[eventForm.tipo]?.color,
      };

      if (selectedEvent) {
        await calendarioAPI.actualizarEvento(selectedEvent.id, data);
        toast.success('Evento actualizado');
      } else {
        await calendarioAPI.crearEvento(data);
        toast.success('Evento creado');
      }
      
      setShowEventModal(false);
      fetchData();
    } catch (error) {
      toast.error('Error al guardar evento');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteEvent = async () => {
    if (!selectedEvent) return;
    
    try {
      await calendarioAPI.eliminarEvento(selectedEvent.id);
      toast.success('Evento eliminado');
      setShowEventModal(false);
      fetchData();
    } catch (error) {
      toast.error('Error al eliminar evento');
    }
  };

  const handleOpenAsignar = () => {
    setAsignarForm({
      orden_id: '',
      tecnico_id: '',
      fecha_estimada: new Date().toISOString().split('T')[0],
    });
    setShowAsignarModal(true);
  };

  const handleAsignarOrden = async () => {
    if (!asignarForm.orden_id || !asignarForm.tecnico_id || !asignarForm.fecha_estimada) {
      toast.error('Todos los campos son obligatorios');
      return;
    }

    setSaving(true);
    try {
      await calendarioAPI.asignarOrden(
        asignarForm.orden_id,
        asignarForm.tecnico_id,
        asignarForm.fecha_estimada
      );
      toast.success('Orden asignada al técnico');
      setShowAsignarModal(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al asignar orden');
    } finally {
      setSaving(false);
    }
  };

  const days = getDaysInMonth();

  return (
    <div className="space-y-6 animate-fade-in" data-testid="calendario-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <CalendarIcon className="w-8 h-8" />
            Calendario
          </h1>
          <p className="text-muted-foreground mt-1">
            Gestiona asignaciones, llegadas y eventos
          </p>
        </div>
        {isAdmin() && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleOpenAsignar} className="gap-2">
              <Wrench className="w-4 h-4" />
              Asignar Orden
            </Button>
            <Button onClick={() => handleDayClick(new Date())} className="gap-2">
              <Plus className="w-4 h-4" />
              Nuevo Evento
            </Button>
          </div>
        )}
      </div>

      {/* Controls */}
      <Card>
        <CardContent className="py-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Button variant="outline" size="icon" onClick={prevMonth}>
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <h2 className="text-xl font-semibold min-w-48 text-center">
                {MONTHS[currentDate.getMonth()]} {currentDate.getFullYear()}
              </h2>
              <Button variant="outline" size="icon" onClick={nextMonth}>
                <ChevronRight className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={goToToday} className="ml-2">
                Hoy
              </Button>
            </div>
            
            <Select value={selectedTecnico} onValueChange={setSelectedTecnico}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Filtrar por técnico" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los técnicos</SelectItem>
                {tecnicos.map(t => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.nombre} {t.apellidos}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Legend */}
      <div className="flex flex-wrap gap-3">
        {Object.entries(tipoEventoConfig).map(([key, config]) => {
          const Icon = config.icon;
          return (
            <Badge key={key} variant="outline" className={`${config.bgColor} gap-1`}>
              <Icon className="w-3 h-3" style={{ color: config.color }} />
              {config.label}
            </Badge>
          );
        })}
      </div>

      {/* Calendar Grid */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-40">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : (
            <div>
              {/* Day Headers */}
              <div className="grid grid-cols-7 border-b">
                {DAYS.map(day => (
                  <div key={day} className="p-3 text-center text-sm font-medium text-muted-foreground border-r last:border-r-0">
                    {day}
                  </div>
                ))}
              </div>
              
              {/* Calendar Days */}
              <div className="grid grid-cols-7">
                {days.map(({ date, isCurrentMonth }, index) => {
                  const dayEvents = getEventsForDate(date);
                  const isWeekend = date.getDay() === 0 || date.getDay() === 6;
                  
                  return (
                    <div
                      key={index}
                      className={`min-h-28 p-1 border-r border-b last:border-r-0 cursor-pointer hover:bg-slate-50 transition-colors
                        ${!isCurrentMonth ? 'bg-slate-50/50' : ''}
                        ${isWeekend ? 'bg-slate-50/30' : ''}
                        ${isToday(date) ? 'bg-blue-50' : ''}
                      `}
                      onClick={() => handleDayClick(date)}
                      data-testid={`calendar-day-${date.toISOString().split('T')[0]}`}
                    >
                      <div className={`text-sm font-medium mb-1 ${
                        isToday(date) 
                          ? 'w-7 h-7 bg-primary text-white rounded-full flex items-center justify-center' 
                          : !isCurrentMonth ? 'text-muted-foreground' : ''
                      }`}>
                        {date.getDate()}
                      </div>
                      
                      <div className="space-y-1">
                        {dayEvents.slice(0, 3).map((event, i) => {
                          const config = tipoEventoConfig[event.tipo] || tipoEventoConfig.otro;
                          return (
                            <div
                              key={i}
                              className={`text-xs p-1 rounded truncate ${config.bgColor} cursor-pointer hover:opacity-80`}
                              style={{ borderLeft: `3px solid ${event.color || config.color}` }}
                              onClick={(e) => handleEventClick(event, e)}
                              title={event.titulo}
                            >
                              {event.titulo}
                            </div>
                          );
                        })}
                        {dayEvents.length > 3 && (
                          <div className="text-xs text-muted-foreground pl-1">
                            +{dayEvents.length - 3} más
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Panel de Disponibilidad de Técnicos */}
      {isAdmin() && (
        <Card data-testid="disponibilidad-tecnicos-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="w-5 h-5" />
              Disponibilidad de Técnicos
            </CardTitle>
            <CardDescription>
              Selecciona una fecha para ver qué técnicos tienen huecos disponibles
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <Label>Fecha:</Label>
                <Input
                  type="date"
                  value={selectedDateForAvailability}
                  onChange={(e) => setSelectedDateForAvailability(e.target.value)}
                  className="w-48"
                />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {disponibilidadTecnicos.map((item) => (
                  <div 
                    key={item.tecnico.id}
                    className={`p-4 rounded-lg border-2 ${
                      !item.disponible 
                        ? 'border-red-300 bg-red-50' 
                        : item.ordenes_asignadas === 0 
                          ? 'border-green-300 bg-green-50' 
                          : item.ordenes_asignadas >= 3 
                            ? 'border-orange-300 bg-orange-50'
                            : 'border-blue-300 bg-blue-50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">
                        {item.tecnico.nombre} {item.tecnico.apellidos}
                      </span>
                      {!item.disponible ? (
                        <Badge variant="destructive">
                          {item.motivo_no_disponible === 'vacaciones' ? 'Vacaciones' : 'Ausente'}
                        </Badge>
                      ) : item.ordenes_asignadas === 0 ? (
                        <Badge className="bg-green-500">Libre</Badge>
                      ) : (
                        <Badge variant={item.ordenes_asignadas >= 3 ? "warning" : "secondary"}>
                          {item.ordenes_asignadas} orden(es)
                        </Badge>
                      )}
                    </div>
                    {item.disponible && (
                      <p className="text-sm text-muted-foreground">
                        {item.ordenes_asignadas === 0 
                          ? '✅ Sin órdenes asignadas - Totalmente disponible'
                          : item.ordenes_asignadas >= 3
                            ? '⚠️ Carga alta de trabajo'
                            : `📋 ${item.ordenes_asignadas} orden(es) asignada(s)`
                        }
                      </p>
                    )}
                  </div>
                ))}
                {disponibilidadTecnicos.length === 0 && (
                  <p className="text-muted-foreground col-span-full text-center py-4">
                    No hay técnicos activos registrados
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Event Modal */}
      <Dialog open={showEventModal} onOpenChange={setShowEventModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {selectedEvent ? 'Editar Evento' : 'Nuevo Evento'}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label>Título *</Label>
              <Input
                value={eventForm.titulo}
                onChange={(e) => setEventForm(prev => ({ ...prev, titulo: e.target.value }))}
                placeholder="Título del evento"
              />
            </div>

            <div>
              <Label>Tipo</Label>
              <Select 
                value={eventForm.tipo} 
                onValueChange={(v) => setEventForm(prev => ({ ...prev, tipo: v }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(tipoEventoConfig).map(([key, config]) => (
                    <SelectItem key={key} value={key}>
                      <div className="flex items-center gap-2">
                        <config.icon className="w-4 h-4" style={{ color: config.color }} />
                        {config.label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Fecha Inicio *</Label>
                <Input
                  type="date"
                  value={eventForm.fecha_inicio}
                  onChange={(e) => setEventForm(prev => ({ ...prev, fecha_inicio: e.target.value }))}
                />
              </div>
              <div>
                <Label>Fecha Fin</Label>
                <Input
                  type="date"
                  value={eventForm.fecha_fin}
                  onChange={(e) => setEventForm(prev => ({ ...prev, fecha_fin: e.target.value }))}
                />
              </div>
            </div>

            <div>
              <Label>Técnico (opcional)</Label>
              <Select 
                value={eventForm.usuario_id || 'none'} 
                onValueChange={(v) => setEventForm(prev => ({ ...prev, usuario_id: v === 'none' ? '' : v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Sin asignar" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Sin asignar</SelectItem>
                  {tecnicos.map(t => (
                    <SelectItem key={t.id} value={t.id}>
                      {t.nombre} {t.apellidos}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Descripción</Label>
              <Textarea
                value={eventForm.descripcion}
                onChange={(e) => setEventForm(prev => ({ ...prev, descripcion: e.target.value }))}
                placeholder="Detalles adicionales..."
                rows={3}
              />
            </div>

            <div className="flex items-center gap-2">
              <Switch
                checked={eventForm.todo_el_dia}
                onCheckedChange={(v) => setEventForm(prev => ({ ...prev, todo_el_dia: v }))}
              />
              <Label>Todo el día</Label>
            </div>
          </div>

          <DialogFooter className="flex justify-between">
            <div>
              {selectedEvent && (
                <Button variant="destructive" onClick={handleDeleteEvent}>
                  <Trash2 className="w-4 h-4 mr-2" />
                  Eliminar
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setShowEventModal(false)}>
                Cancelar
              </Button>
              <Button onClick={handleSaveEvent} disabled={saving}>
                {saving && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
                {selectedEvent ? 'Guardar' : 'Crear'}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Asignar Orden Modal */}
      <Dialog open={showAsignarModal} onOpenChange={setShowAsignarModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Asignar Orden a Técnico</DialogTitle>
            <DialogDescription>
              Selecciona una orden pendiente y asígnala a un técnico con una fecha estimada
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label>Orden *</Label>
              <Select 
                value={asignarForm.orden_id} 
                onValueChange={(v) => setAsignarForm(prev => ({ ...prev, orden_id: v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar orden..." />
                </SelectTrigger>
                <SelectContent>
                  {ordenesPendientes.length === 0 ? (
                    <SelectItem value="_empty" disabled>
                      No hay órdenes pendientes
                    </SelectItem>
                  ) : (
                    ordenesPendientes.map(orden => (
                      <SelectItem key={orden.id} value={orden.id}>
                        {orden.numero_orden} - {orden.dispositivo?.modelo}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Técnico *</Label>
              <Select 
                value={asignarForm.tecnico_id} 
                onValueChange={(v) => setAsignarForm(prev => ({ ...prev, tecnico_id: v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar técnico..." />
                </SelectTrigger>
                <SelectContent>
                  {tecnicos.map(t => (
                    <SelectItem key={t.id} value={t.id}>
                      {t.nombre} {t.apellidos}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Fecha Estimada *</Label>
              <Input
                type="date"
                value={asignarForm.fecha_estimada}
                onChange={(e) => setAsignarForm(prev => ({ ...prev, fecha_estimada: e.target.value }))}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAsignarModal(false)}>
              Cancelar
            </Button>
            <Button onClick={handleAsignarOrden} disabled={saving}>
              {saving && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
              Asignar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

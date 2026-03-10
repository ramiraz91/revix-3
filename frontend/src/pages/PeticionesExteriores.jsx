import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { 
  Phone, PhoneCall, PhoneOff, PhoneForwarded,
  CheckCircle2, XCircle, Clock, Search, RefreshCw,
  ArrowRight, FileText, User, Mail, MapPin,
  Smartphone, MessageSquare, Calendar, Euro,
  Filter, AlertTriangle, CheckCheck
} from 'lucide-react';
import api from '@/lib/api';

const ESTADOS = {
  pendiente: { label: 'Pendiente', color: 'bg-yellow-100 text-yellow-800', icon: Clock },
  contactado: { label: 'Contactado', color: 'bg-blue-100 text-blue-800', icon: PhoneCall },
  presupuestado: { label: 'Presupuestado', color: 'bg-purple-100 text-purple-800', icon: Euro },
  aceptado: { label: 'Aceptado', color: 'bg-green-100 text-green-800', icon: CheckCircle2 },
  rechazado: { label: 'Rechazado', color: 'bg-red-100 text-red-800', icon: XCircle },
  convertido: { label: 'Convertido', color: 'bg-emerald-100 text-emerald-800', icon: CheckCheck }
};

export default function PeticionesExteriores() {
  const { isAdmin } = useAuth();
  const [peticiones, setPeticiones] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filtroEstado, setFiltroEstado] = useState('all');
  const [busqueda, setBusqueda] = useState('');
  
  // Modal states
  const [peticionSeleccionada, setPeticionSeleccionada] = useState(null);
  const [showDetalleModal, setShowDetalleModal] = useState(false);
  const [showLlamadaModal, setShowLlamadaModal] = useState(false);
  const [showAceptarModal, setShowAceptarModal] = useState(false);
  
  // Form states
  const [resultadoLlamada, setResultadoLlamada] = useState('');
  const [notasLlamada, setNotasLlamada] = useState('');
  const [presupuesto, setPresupuesto] = useState('');
  const [tiempoEstimado, setTiempoEstimado] = useState('24-48 horas');
  const [notasPresupuesto, setNotasPresupuesto] = useState('');

  const cargarPeticiones = useCallback(async () => {
    try {
      setLoading(true);
      const params = filtroEstado !== 'all' ? `?estado=${filtroEstado}` : '';
      const res = await api.get(`/peticiones-exteriores${params}`);
      setPeticiones(res.data.peticiones || []);
      
      // Cargar stats
      const statsRes = await api.get('/peticiones-exteriores/stats/resumen');
      setStats(statsRes.data);
    } catch (error) {
      toast.error('Error cargando peticiones');
    } finally {
      setLoading(false);
    }
  }, [filtroEstado]);

  useEffect(() => {
    cargarPeticiones();
  }, [cargarPeticiones]);

  const handleMarcarContactado = async () => {
    if (!resultadoLlamada) {
      toast.error('Selecciona el resultado de la llamada');
      return;
    }
    
    try {
      await api.post(`/peticiones-exteriores/${peticionSeleccionada.id}/contactar?resultado=${resultadoLlamada}&notas=${encodeURIComponent(notasLlamada)}`);
      toast.success('Estado actualizado');
      setShowLlamadaModal(false);
      setResultadoLlamada('');
      setNotasLlamada('');
      cargarPeticiones();
    } catch (error) {
      toast.error('Error actualizando estado');
    }
  };

  const handleAceptarPresupuesto = async () => {
    if (!presupuesto || parseFloat(presupuesto) <= 0) {
      toast.error('Introduce un presupuesto válido');
      return;
    }
    
    try {
      await api.post(`/peticiones-exteriores/${peticionSeleccionada.id}/aceptar?presupuesto=${presupuesto}&tiempo_estimado=${encodeURIComponent(tiempoEstimado)}&notas=${encodeURIComponent(notasPresupuesto)}`);
      toast.success('Presupuesto aceptado. Se ha enviado email al cliente.');
      setShowAceptarModal(false);
      setPresupuesto('');
      setNotasPresupuesto('');
      cargarPeticiones();
    } catch (error) {
      toast.error('Error aceptando presupuesto');
    }
  };

  const handleConvertirAOrden = async (peticion) => {
    if (!confirm('¿Convertir esta petición en una Orden de Trabajo?')) return;
    
    try {
      const res = await api.post(`/peticiones-exteriores/${peticion.id}/convertir`, {
        crear_cliente: true,
        notas: 'Convertido desde panel de peticiones exteriores'
      });
      toast.success(`Orden creada: ${res.data.numero_orden}`);
      cargarPeticiones();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error convirtiendo a orden');
    }
  };

  const peticionesFiltradas = peticiones.filter(p => {
    if (busqueda) {
      const search = busqueda.toLowerCase();
      return (
        p.nombre?.toLowerCase().includes(search) ||
        p.email?.toLowerCase().includes(search) ||
        p.telefono?.includes(search) ||
        p.dispositivo?.toLowerCase().includes(search) ||
        p.numero?.toLowerCase().includes(search)
      );
    }
    return true;
  });

  const formatFecha = (fecha) => {
    if (!fecha) return '-';
    return new Date(fecha).toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (!isAdmin()) {
    return (
      <div className="p-8 text-center">
        <AlertTriangle className="w-12 h-12 mx-auto text-yellow-500 mb-4" />
        <p className="text-gray-500">No tienes permisos para acceder a esta sección</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Peticiones Exteriores</h1>
          <p className="text-muted-foreground">Solicitudes de presupuesto de clientes externos</p>
        </div>
        <Button onClick={cargarPeticiones} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Actualizar
        </Button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card className="bg-yellow-50 border-yellow-200">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-yellow-700">{stats.por_estado?.pendiente || 0}</p>
                  <p className="text-xs text-yellow-600">Pendientes llamar</p>
                </div>
                <Phone className="w-8 h-8 text-yellow-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-blue-700">{stats.por_estado?.contactado || 0}</p>
                  <p className="text-xs text-blue-600">Contactados</p>
                </div>
                <PhoneCall className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-purple-50 border-purple-200">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-purple-700">{stats.por_estado?.aceptado || 0}</p>
                  <p className="text-xs text-purple-600">Aceptados</p>
                </div>
                <CheckCircle2 className="w-8 h-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-emerald-50 border-emerald-200">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-emerald-700">{stats.por_estado?.convertido || 0}</p>
                  <p className="text-xs text-emerald-600">Convertidos</p>
                </div>
                <FileText className="w-8 h-8 text-emerald-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-slate-50 border-slate-200">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-slate-700">{stats.tasa_conversion || 0}%</p>
                  <p className="text-xs text-slate-600">Tasa conversión</p>
                </div>
                <ArrowRight className="w-8 h-8 text-slate-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Buscar por nombre, email, teléfono..."
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <div className="flex gap-2 flex-wrap">
              <Button
                variant={filtroEstado === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFiltroEstado('all')}
              >
                Todos
              </Button>
              {Object.entries(ESTADOS).map(([key, { label, color }]) => (
                <Button
                  key={key}
                  variant={filtroEstado === key ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFiltroEstado(key)}
                  className={filtroEstado === key ? '' : color}
                >
                  {label}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Peticiones List */}
      <Card>
        <CardHeader>
          <CardTitle>Peticiones ({peticionesFiltradas.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto text-muted-foreground" />
            </div>
          ) : peticionesFiltradas.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No hay peticiones {filtroEstado !== 'all' ? `en estado "${ESTADOS[filtroEstado]?.label}"` : ''}
            </div>
          ) : (
            <div className="space-y-3">
              {peticionesFiltradas.map((peticion) => {
                const estadoInfo = ESTADOS[peticion.estado] || ESTADOS.pendiente;
                const EstadoIcon = estadoInfo.icon;
                
                return (
                  <div
                    key={peticion.id}
                    className="border rounded-lg p-4 hover:bg-slate-50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      {/* Info principal */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-mono text-sm text-muted-foreground">{peticion.numero}</span>
                          <Badge className={estadoInfo.color}>
                            <EstadoIcon className="w-3 h-3 mr-1" />
                            {estadoInfo.label}
                          </Badge>
                          {peticion.tipo_pieza && peticion.tipo_pieza !== 'sin_preferencia' && (
                            <Badge variant="outline">
                              {peticion.tipo_pieza === 'original' ? '🏷️ Original' : '⚙️ Compatible'}
                            </Badge>
                          )}
                        </div>
                        
                        <div className="grid md:grid-cols-2 gap-2">
                          <div className="flex items-center gap-2">
                            <User className="w-4 h-4 text-muted-foreground" />
                            <span className="font-medium">{peticion.nombre}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Phone className="w-4 h-4 text-muted-foreground" />
                            <a href={`tel:${peticion.telefono}`} className="text-blue-600 hover:underline">
                              {peticion.telefono}
                            </a>
                          </div>
                          <div className="flex items-center gap-2">
                            <Smartphone className="w-4 h-4 text-muted-foreground" />
                            <span>{peticion.dispositivo}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Calendar className="w-4 h-4 text-muted-foreground" />
                            <span className="text-sm text-muted-foreground">{formatFecha(peticion.created_at)}</span>
                          </div>
                        </div>
                        
                        <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
                          <MessageSquare className="w-3 h-3 inline mr-1" />
                          {peticion.problema}
                        </p>
                        
                        {peticion.presupuesto_estimado && (
                          <p className="text-sm font-medium text-green-600 mt-1">
                            <Euro className="w-3 h-3 inline mr-1" />
                            Presupuesto: {peticion.presupuesto_estimado}€
                          </p>
                        )}
                      </div>
                      
                      {/* Acciones */}
                      <div className="flex flex-col gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setPeticionSeleccionada(peticion);
                            setShowDetalleModal(true);
                          }}
                        >
                          Ver detalle
                        </Button>
                        
                        {peticion.estado === 'pendiente' && (
                          <Button
                            size="sm"
                            onClick={() => {
                              setPeticionSeleccionada(peticion);
                              setShowLlamadaModal(true);
                            }}
                          >
                            <PhoneCall className="w-4 h-4 mr-1" />
                            Llamar
                          </Button>
                        )}
                        
                        {(peticion.estado === 'contactado' || peticion.estado === 'presupuestado') && (
                          <Button
                            size="sm"
                            variant="default"
                            className="bg-green-600 hover:bg-green-700"
                            onClick={() => {
                              setPeticionSeleccionada(peticion);
                              setShowAceptarModal(true);
                            }}
                          >
                            <CheckCircle2 className="w-4 h-4 mr-1" />
                            Aceptar
                          </Button>
                        )}
                        
                        {peticion.estado === 'aceptado' && (
                          <Button
                            size="sm"
                            variant="default"
                            className="bg-emerald-600 hover:bg-emerald-700"
                            onClick={() => handleConvertirAOrden(peticion)}
                          >
                            <ArrowRight className="w-4 h-4 mr-1" />
                            Crear Orden
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal: Detalle */}
      <Dialog open={showDetalleModal} onOpenChange={setShowDetalleModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Detalle de Petición {peticionSeleccionada?.numero}</DialogTitle>
          </DialogHeader>
          
          {peticionSeleccionada && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Cliente</p>
                  <p className="font-medium">{peticionSeleccionada.nombre}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Email</p>
                  <p className="font-medium">{peticionSeleccionada.email}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Teléfono</p>
                  <p className="font-medium">{peticionSeleccionada.telefono}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Dispositivo</p>
                  <p className="font-medium">{peticionSeleccionada.dispositivo}</p>
                </div>
                <div className="col-span-2">
                  <p className="text-sm text-muted-foreground">Problema</p>
                  <p className="font-medium">{peticionSeleccionada.problema}</p>
                </div>
                {peticionSeleccionada.direccion && (
                  <div className="col-span-2">
                    <p className="text-sm text-muted-foreground">Dirección</p>
                    <p className="font-medium">
                      {peticionSeleccionada.direccion}, {peticionSeleccionada.codigo_postal} {peticionSeleccionada.ciudad}
                    </p>
                  </div>
                )}
                {peticionSeleccionada.comentarios && (
                  <div className="col-span-2">
                    <p className="text-sm text-muted-foreground">Comentarios</p>
                    <p className="font-medium">{peticionSeleccionada.comentarios}</p>
                  </div>
                )}
              </div>
              
              {peticionSeleccionada.notas_internas && (
                <div className="bg-slate-50 rounded-lg p-4">
                  <p className="text-sm font-medium mb-2">Notas internas</p>
                  <pre className="text-sm whitespace-pre-wrap text-muted-foreground">
                    {peticionSeleccionada.notas_internas}
                  </pre>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Modal: Registrar llamada */}
      <Dialog open={showLlamadaModal} onOpenChange={setShowLlamadaModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Registrar Llamada</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="font-medium">{peticionSeleccionada?.nombre}</p>
              <a href={`tel:${peticionSeleccionada?.telefono}`} className="text-blue-600 text-lg font-bold">
                📞 {peticionSeleccionada?.telefono}
              </a>
            </div>
            
            <div>
              <label className="text-sm font-medium">Resultado de la llamada</label>
              <Select value={resultadoLlamada} onValueChange={setResultadoLlamada}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar resultado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="exito">✅ Contactado con éxito</SelectItem>
                  <SelectItem value="no_contesta">📵 No contesta</SelectItem>
                  <SelectItem value="llamar_luego">🕐 Llamar más tarde</SelectItem>
                  <SelectItem value="rechazado">❌ No interesado</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="text-sm font-medium">Notas</label>
              <Textarea
                value={notasLlamada}
                onChange={(e) => setNotasLlamada(e.target.value)}
                placeholder="Detalles de la conversación..."
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLlamadaModal(false)}>Cancelar</Button>
            <Button onClick={handleMarcarContactado}>Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal: Aceptar presupuesto */}
      <Dialog open={showAceptarModal} onOpenChange={setShowAceptarModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirmar Presupuesto Aceptado</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="bg-green-50 rounded-lg p-4">
              <p className="font-medium">{peticionSeleccionada?.nombre}</p>
              <p className="text-sm text-muted-foreground">{peticionSeleccionada?.dispositivo}</p>
            </div>
            
            <div>
              <label className="text-sm font-medium">Presupuesto (€)</label>
              <Input
                type="number"
                value={presupuesto}
                onChange={(e) => setPresupuesto(e.target.value)}
                placeholder="Ej: 85.00"
              />
            </div>
            
            <div>
              <label className="text-sm font-medium">Tiempo estimado</label>
              <Select value={tiempoEstimado} onValueChange={setTiempoEstimado}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="24 horas">24 horas</SelectItem>
                  <SelectItem value="24-48 horas">24-48 horas</SelectItem>
                  <SelectItem value="48-72 horas">48-72 horas</SelectItem>
                  <SelectItem value="3-5 días">3-5 días</SelectItem>
                  <SelectItem value="1 semana">1 semana</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="text-sm font-medium">Notas adicionales</label>
              <Textarea
                value={notasPresupuesto}
                onChange={(e) => setNotasPresupuesto(e.target.value)}
                placeholder="Detalles del presupuesto..."
              />
            </div>
            
            <p className="text-sm text-muted-foreground">
              Se enviará un email de confirmación al cliente automáticamente.
            </p>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAceptarModal(false)}>Cancelar</Button>
            <Button className="bg-green-600 hover:bg-green-700" onClick={handleAceptarPresupuesto}>
              <CheckCircle2 className="w-4 h-4 mr-2" />
              Confirmar Aceptación
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

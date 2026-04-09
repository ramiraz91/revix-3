import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { 
  History, 
  Search, 
  RefreshCw, 
  User, 
  Clock, 
  FileText,
  ChevronRight,
  Filter,
  Download,
  Calendar
} from 'lucide-react';
import { toast } from 'sonner';
import API from '@/lib/api';

export default function ControlCambios() {
  const navigate = useNavigate();
  const [cambios, setCambios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({
    fecha_desde: '',
    fecha_hasta: '',
    tipo_cambio: '',
    usuario: '',
    orden_id: ''
  });
  const [showFiltros, setShowFiltros] = useState(false);

  useEffect(() => {
    fetchCambios();
  }, []);

  const fetchCambios = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filtros.fecha_desde) params.append('fecha_desde', filtros.fecha_desde);
      if (filtros.fecha_hasta) params.append('fecha_hasta', filtros.fecha_hasta);
      if (filtros.tipo_cambio) params.append('tipo_cambio', filtros.tipo_cambio);
      if (filtros.usuario) params.append('usuario', filtros.usuario);
      if (filtros.orden_id) params.append('orden_id', filtros.orden_id);
      
      const res = await API.get(`/control-cambios?${params.toString()}`);
      setCambios(res.data.data || []);
    } catch (err) {
      console.error('Error cargando cambios:', err);
      toast.error('Error al cargar el historial de cambios');
    } finally {
      setLoading(false);
    }
  };

  const handleFiltrar = () => {
    fetchCambios();
  };

  const handleLimpiarFiltros = () => {
    setFiltros({
      fecha_desde: '',
      fecha_hasta: '',
      tipo_cambio: '',
      usuario: '',
      orden_id: ''
    });
    setTimeout(fetchCambios, 100);
  };

  const formatFecha = (fecha) => {
    if (!fecha) return '-';
    try {
      return new Date(fecha).toLocaleString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return fecha;
    }
  };

  const getTipoBadge = (tipo) => {
    const tipos = {
      'cambio_estado': { label: 'Estado', color: 'bg-blue-100 text-blue-800' },
      'cambiar_subestado': { label: 'Subestado', color: 'bg-purple-100 text-purple-800' },
      'crear_orden': { label: 'Nueva Orden', color: 'bg-green-100 text-green-800' },
      'actualizar_orden': { label: 'Actualización', color: 'bg-yellow-100 text-yellow-800' },
      'crear_cliente': { label: 'Cliente', color: 'bg-cyan-100 text-cyan-800' },
      'agregar_material': { label: 'Material', color: 'bg-orange-100 text-orange-800' },
      'validar_material': { label: 'Validación', color: 'bg-emerald-100 text-emerald-800' },
      'enviar_orden': { label: 'Envío', color: 'bg-indigo-100 text-indigo-800' },
      'recibir_orden': { label: 'Recepción', color: 'bg-teal-100 text-teal-800' },
    };
    const config = tipos[tipo] || { label: tipo || 'Cambio', color: 'bg-gray-100 text-gray-800' };
    return <Badge className={`${config.color} text-xs`}>{config.label}</Badge>;
  };

  const exportarCSV = () => {
    const headers = ['Fecha', 'Tipo', 'Usuario', 'Entidad', 'Descripción'];
    const rows = cambios.map(c => [
      formatFecha(c.fecha),
      c.tipo,
      c.usuario_nombre || c.usuario_email || '-',
      c.entidad || '-',
      c.descripcion || '-'
    ]);
    
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `control_cambios_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    toast.success('CSV exportado correctamente');
  };

  return (
    <div className="space-y-6" data-testid="control-cambios-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <History className="w-6 h-6 text-primary" />
            Control de Cambios
          </h1>
          <p className="text-muted-foreground text-sm">
            Historial completo de todos los cambios en el sistema
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowFiltros(!showFiltros)}>
            <Filter className="w-4 h-4 mr-2" />
            Filtros
          </Button>
          <Button variant="outline" size="sm" onClick={exportarCSV}>
            <Download className="w-4 h-4 mr-2" />
            Exportar
          </Button>
          <Button variant="outline" size="sm" onClick={fetchCambios} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>
      </div>

      {/* Filtros */}
      {showFiltros && (
        <Card>
          <CardContent className="pt-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <div>
                <label className="text-xs font-medium mb-1 block">Desde</label>
                <Input
                  type="date"
                  value={filtros.fecha_desde}
                  onChange={(e) => setFiltros({...filtros, fecha_desde: e.target.value})}
                />
              </div>
              <div>
                <label className="text-xs font-medium mb-1 block">Hasta</label>
                <Input
                  type="date"
                  value={filtros.fecha_hasta}
                  onChange={(e) => setFiltros({...filtros, fecha_hasta: e.target.value})}
                />
              </div>
              <div>
                <label className="text-xs font-medium mb-1 block">Tipo de Cambio</label>
                <Select value={filtros.tipo_cambio} onValueChange={(v) => setFiltros({...filtros, tipo_cambio: v})}>
                  <SelectTrigger>
                    <SelectValue placeholder="Todos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todos</SelectItem>
                    <SelectItem value="estado">Estados</SelectItem>
                    <SelectItem value="subestado">Subestados</SelectItem>
                    <SelectItem value="material">Materiales</SelectItem>
                    <SelectItem value="orden">Órdenes</SelectItem>
                    <SelectItem value="cliente">Clientes</SelectItem>
                    <SelectItem value="enviar">Envíos</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs font-medium mb-1 block">Usuario</label>
                <Input
                  placeholder="Nombre o email..."
                  value={filtros.usuario}
                  onChange={(e) => setFiltros({...filtros, usuario: e.target.value})}
                />
              </div>
              <div>
                <label className="text-xs font-medium mb-1 block">ID Orden</label>
                <Input
                  placeholder="ID o número..."
                  value={filtros.orden_id}
                  onChange={(e) => setFiltros({...filtros, orden_id: e.target.value})}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="ghost" size="sm" onClick={handleLimpiarFiltros}>
                Limpiar
              </Button>
              <Button size="sm" onClick={handleFiltrar}>
                <Search className="w-4 h-4 mr-2" />
                Buscar
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Lista de cambios */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Historial de Cambios</CardTitle>
          <CardDescription>
            {cambios.length} cambios registrados
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="w-8 h-8 animate-spin text-muted-foreground" />
            </div>
          ) : cambios.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <History className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No hay cambios registrados</p>
            </div>
          ) : (
            <div className="space-y-2">
              {cambios.map((cambio, idx) => (
                <div 
                  key={cambio.id || idx}
                  className="flex items-start gap-4 p-3 rounded-lg bg-slate-50 hover:bg-slate-100 transition-colors"
                >
                  {/* Timestamp */}
                  <div className="flex flex-col items-center text-xs text-muted-foreground min-w-[80px]">
                    <Clock className="w-4 h-4 mb-1" />
                    <span>{formatFecha(cambio.fecha)}</span>
                  </div>

                  {/* Tipo */}
                  <div className="min-w-[100px]">
                    {getTipoBadge(cambio.tipo)}
                  </div>

                  {/* Contenido */}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{cambio.descripcion}</p>
                    {cambio.numero_orden && (
                      <button 
                        onClick={() => navigate(`/crm/ordenes/${cambio.entidad_id}`)}
                        className="text-xs text-primary hover:underline"
                      >
                        {cambio.numero_orden}
                      </button>
                    )}
                    {cambio.detalles?.mensaje && (
                      <p className="text-xs text-muted-foreground mt-1 italic">
                        "{cambio.detalles.mensaje}"
                      </p>
                    )}
                    {cambio.detalles?.estado && !cambio.detalles?.mensaje && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Estado: <span className="font-medium">{cambio.detalles.estado}</span>
                      </p>
                    )}
                  </div>

                  {/* Usuario */}
                  <div className="flex items-center gap-2 text-xs text-muted-foreground min-w-[150px]">
                    <User className="w-4 h-4" />
                    <div className="truncate">
                      <p className="font-medium">{cambio.usuario_nombre || cambio.usuario_email || 'Sistema'}</p>
                      {cambio.rol && <p className="text-[10px]">{cambio.rol}</p>}
                    </div>
                  </div>

                  {/* Acción */}
                  {cambio.entidad_id && cambio.entidad === 'orden' && (
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => navigate(`/crm/ordenes/${cambio.entidad_id}`)}
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

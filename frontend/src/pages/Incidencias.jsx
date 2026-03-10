import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  AlertTriangle, 
  Plus, 
  Search, 
  Filter,
  Eye,
  Edit,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  User,
  FileText,
  Calendar,
  Shield,
  RefreshCw,
  Package,
  MessageSquare
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { incidenciasAPI, clientesAPI, ordenesAPI } from '@/lib/api';
import { toast } from 'sonner';

const TIPOS_INCIDENCIA = {
  reemplazo_dispositivo: { label: 'Reemplazo Dispositivo', icon: RefreshCw, color: 'bg-blue-100 text-blue-800' },
  reclamacion: { label: 'Reclamación', icon: MessageSquare, color: 'bg-orange-100 text-orange-800' },
  garantia: { label: 'Garantía', icon: Shield, color: 'bg-purple-100 text-purple-800' },
  daño_transporte: { label: 'Daño en Transporte', icon: Package, color: 'bg-red-100 text-red-800' },
  otro: { label: 'Otro', icon: FileText, color: 'bg-gray-100 text-gray-800' },
};

const ESTADOS_INCIDENCIA = {
  abierta: { label: 'Abierta', color: 'bg-red-100 text-red-800 border-red-300' },
  en_proceso: { label: 'En Proceso', color: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
  resuelta: { label: 'Resuelta', color: 'bg-green-100 text-green-800 border-green-300' },
  cerrada: { label: 'Cerrada', color: 'bg-gray-100 text-gray-800 border-gray-300' },
};

const PRIORIDADES = {
  baja: { label: 'Baja', color: 'bg-gray-100 text-gray-700' },
  media: { label: 'Media', color: 'bg-blue-100 text-blue-700' },
  alta: { label: 'Alta', color: 'bg-orange-100 text-orange-700' },
  critica: { label: 'Crítica', color: 'bg-red-100 text-red-700' },
};

const SEVERIDADES_NCM = {
  baja: { label: 'Baja', color: 'bg-gray-100 text-gray-700' },
  media: { label: 'Media', color: 'bg-yellow-100 text-yellow-700' },
  alta: { label: 'Alta', color: 'bg-orange-100 text-orange-700' },
  critica: { label: 'Crítica', color: 'bg-red-100 text-red-700' },
};

const DISPOSICIONES_NCM = {
  retrabajo: 'Retrabajo',
  reemplazo: 'Reemplazo',
  devolucion: 'Devolución',
  scrap: 'Scrap',
  bloqueo: 'Bloqueo',
};


export default function Incidencias() {
  const [loading, setLoading] = useState(true);
  const [incidencias, setIncidencias] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [ordenes, setOrdenes] = useState([]);
  const [filtroEstado, setFiltroEstado] = useState('all');
  const [filtroTipo, setFiltroTipo] = useState('all');
  const [busqueda, setBusqueda] = useState('');
  
  // Modal crear/editar
  const [showModal, setShowModal] = useState(false);
  const [modoEditar, setModoEditar] = useState(false);
  const [incidenciaActual, setIncidenciaActual] = useState(null);
  const [formData, setFormData] = useState({
    cliente_id: '',
    orden_id: '',
    tipo: 'otro',
    titulo: '',
    descripcion: '',
    prioridad: 'media',
    origen_ncm: 'proceso_reparacion',
    severidad_ncm: 'media',
    disposicion_ncm: 'retrabajo',
    impacto_ncm: '',
    contencion_ncm: '',
  });
  const [saving, setSaving] = useState(false);
  
  // Modal detalle
  const [showDetalleModal, setShowDetalleModal] = useState(false);
  const [incidenciaDetalle, setIncidenciaDetalle] = useState(null);
  const [notasResolucion, setNotasResolucion] = useState('');
  const [capaData, setCapaData] = useState({
    causa_raiz: '',
    accion_correctiva: '',
    responsable: '',
    fecha_objetivo: '',
    verificacion_eficacia: '',
    fecha_verificacion: '',
    eficaz: false,
  });

  useEffect(() => {
    fetchData();
  }, [filtroEstado, filtroTipo]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const params = {};
      if (filtroEstado !== 'all') params.estado = filtroEstado;
      if (filtroTipo !== 'all') params.tipo = filtroTipo;
      
      const [incidenciasRes, clientesRes] = await Promise.all([
        incidenciasAPI.listar(params),
        clientesAPI.listar()
      ]);
      
      setIncidencias(incidenciasRes.data);
      setClientes(clientesRes.data);
    } catch (error) {
      toast.error('Error al cargar incidencias');
    } finally {
      setLoading(false);
    }
  };

  const fetchOrdenesCliente = async (clienteId) => {
    if (!clienteId) {
      setOrdenes([]);
      return;
    }
    try {
      const res = await ordenesAPI.listarPaginado({ cliente_id: clienteId, page_size: 100 });
      setOrdenes(res.data.data || []);
    } catch (error) {
      console.error('Error cargando órdenes:', error);
    }
  };

  const handleNuevaIncidencia = () => {
    setModoEditar(false);
    setIncidenciaActual(null);
    setFormData({
      cliente_id: '',
      orden_id: '',
      tipo: 'otro',
      titulo: '',
      descripcion: '',
      prioridad: 'media',
      origen_ncm: 'proceso_reparacion',
      severidad_ncm: 'media',
      disposicion_ncm: 'retrabajo',
      impacto_ncm: '',
      contencion_ncm: '',
    });
    setOrdenes([]);
    setShowModal(true);
  };

  const handleEditarIncidencia = (incidencia) => {
    setModoEditar(true);
    setIncidenciaActual(incidencia);
    setFormData({
      cliente_id: incidencia.cliente_id,
      orden_id: incidencia.orden_id || '',
      tipo: incidencia.tipo,
      titulo: incidencia.titulo,
      descripcion: incidencia.descripcion,
      prioridad: incidencia.prioridad,
      origen_ncm: incidencia.origen_ncm || 'proceso_reparacion',
      severidad_ncm: incidencia.severidad_ncm || 'media',
      disposicion_ncm: incidencia.disposicion_ncm || 'retrabajo',
      impacto_ncm: incidencia.impacto_ncm || '',
      contencion_ncm: incidencia.contencion_ncm || '',
    });
    fetchOrdenesCliente(incidencia.cliente_id);
    setShowModal(true);
  };

  const handleVerDetalle = (incidencia) => {
    setIncidenciaDetalle(incidencia);
    setNotasResolucion(incidencia.notas_resolucion || '');
    setCapaData({
      causa_raiz: incidencia.capa_causa_raiz || '',
      accion_correctiva: incidencia.capa_accion_correctiva || '',
      responsable: incidencia.capa_responsable || '',
      fecha_objetivo: incidencia.capa_fecha_objetivo || '',
      verificacion_eficacia: incidencia.capa_verificacion_eficacia || '',
      fecha_verificacion: incidencia.capa_fecha_verificacion || '',
      eficaz: Boolean(incidencia.capa_eficaz),
    });
    setShowDetalleModal(true);
  };

  const handleGuardar = async () => {
    if (!formData.cliente_id || !formData.titulo || !formData.descripcion) {
      toast.error('Completa los campos obligatorios');
      return;
    }
    
    setSaving(true);
    try {
      if (modoEditar && incidenciaActual) {
        await incidenciasAPI.actualizar(incidenciaActual.id, formData);
        toast.success('Incidencia actualizada');
      } else {
        await incidenciasAPI.crear(formData);
        toast.success('Incidencia creada');
      }
      setShowModal(false);
      fetchData();
    } catch (error) {
      toast.error('Error al guardar la incidencia');
    } finally {
      setSaving(false);
    }
  };

  const handleCambiarEstado = async (nuevoEstado) => {
    if (!incidenciaDetalle) return;

    const payload = {
      estado: nuevoEstado,
      notas_resolucion: notasResolucion,
      capa_causa_raiz: capaData.causa_raiz,
      capa_accion_correctiva: capaData.accion_correctiva,
      capa_responsable: capaData.responsable,
      capa_fecha_objetivo: capaData.fecha_objetivo || null,
      capa_verificacion_eficacia: capaData.verificacion_eficacia,
      capa_fecha_verificacion: capaData.fecha_verificacion || null,
      capa_eficaz: capaData.eficaz,
    };

    setSaving(true);
    try {
      await incidenciasAPI.actualizar(incidenciaDetalle.id, payload);
      toast.success(`Incidencia marcada como ${ESTADOS_INCIDENCIA[nuevoEstado]?.label}`);
      setShowDetalleModal(false);
      fetchData();
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(detail || 'Error al actualizar el estado');
    } finally {
      setSaving(false);
    }
  };

  const handleGuardarCapa = async () => {
    if (!incidenciaDetalle) return;
    setSaving(true);
    try {
      await incidenciasAPI.actualizar(incidenciaDetalle.id, {
        capa_causa_raiz: capaData.causa_raiz,
        capa_accion_correctiva: capaData.accion_correctiva,
        capa_responsable: capaData.responsable,
        capa_fecha_objetivo: capaData.fecha_objetivo || null,
        capa_verificacion_eficacia: capaData.verificacion_eficacia,
        capa_fecha_verificacion: capaData.fecha_verificacion || null,
        capa_eficaz: capaData.eficaz,
        capa_estado: capaData.eficaz ? 'verificada' : 'en_progreso',
      });
      toast.success('CAPA guardada correctamente');
      fetchData();
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(detail || 'Error al guardar CAPA');
    } finally {
      setSaving(false);
    }
  };

  const formatFecha = (fecha) => {
    if (!fecha) return '-';
    return new Date(fecha).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const esTipoNCM = ['reclamacion', 'garantia', 'daño_transporte'].includes(formData.tipo);

  const incidenciasFiltradas = incidencias.filter(inc => {
    if (!busqueda) return true;
    const search = busqueda.toLowerCase();
    return (
      inc.titulo?.toLowerCase().includes(search) ||
      inc.numero_incidencia?.toLowerCase().includes(search) ||
      inc.descripcion?.toLowerCase().includes(search)
    );
  });

  // Contadores
  const abiertas = incidencias.filter(i => i.estado === 'abierta').length;
  const enProceso = incidencias.filter(i => i.estado === 'en_proceso').length;
  const criticas = incidencias.filter(i => i.prioridad === 'critica' && i.estado !== 'cerrada').length;

  if (loading && incidencias.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="incidencias-page">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <AlertTriangle className="w-7 h-7" />
            Incidencias
          </h1>
          <p className="text-muted-foreground">
            Gestiona reclamaciones, garantías y problemas con clientes
          </p>
        </div>
        
        <div className="flex gap-2 items-center">
          {criticas > 0 && (
            <Badge variant="destructive" className="text-sm">
              {criticas} críticas
            </Badge>
          )}
          <Button onClick={handleNuevaIncidencia} data-testid="nueva-incidencia-btn">
            <Plus className="w-4 h-4 mr-2" />
            Nueva Incidencia
          </Button>
        </div>
      </div>

      {/* Resumen */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Abiertas</p>
                <p className="text-2xl font-bold text-red-600">{abiertas}</p>
              </div>
              <XCircle className="w-8 h-8 text-red-200" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">En Proceso</p>
                <p className="text-2xl font-bold text-yellow-600">{enProceso}</p>
              </div>
              <Clock className="w-8 h-8 text-yellow-200" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Resueltas</p>
                <p className="text-2xl font-bold text-green-600">
                  {incidencias.filter(i => i.estado === 'resuelta').length}
                </p>
              </div>
              <CheckCircle2 className="w-8 h-8 text-green-200" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total</p>
                <p className="text-2xl font-bold">{incidencias.length}</p>
              </div>
              <FileText className="w-8 h-8 text-gray-200" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                <Input
                  placeholder="Buscar por título, número o descripción..."
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  className="pl-10"
                  data-testid="buscar-incidencias"
                />
              </div>
            </div>
            
            <Select value={filtroEstado} onValueChange={setFiltroEstado}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                {Object.entries(ESTADOS_INCIDENCIA).map(([key, val]) => (
                  <SelectItem key={key} value={key}>{val.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            <Select value={filtroTipo} onValueChange={setFiltroTipo}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Tipo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                {Object.entries(TIPOS_INCIDENCIA).map(([key, val]) => (
                  <SelectItem key={key} value={key}>{val.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Tabla */}
      <Card>
        <CardContent className="p-0">
          {incidenciasFiltradas.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No hay incidencias que mostrar</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Número</TableHead>
                  <TableHead>Título</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Prioridad</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {incidenciasFiltradas.map((inc) => {
                  const TipoIcon = TIPOS_INCIDENCIA[inc.tipo]?.icon || FileText;
                  return (
                    <TableRow key={inc.id} data-testid={`incidencia-row-${inc.id}`}>
                      <TableCell className="font-mono text-sm">
                        {inc.numero_incidencia}
                      </TableCell>
                      <TableCell className="font-medium max-w-xs truncate">
                        {inc.titulo}
                      </TableCell>
                      <TableCell>
                        <Badge className={`gap-1 ${TIPOS_INCIDENCIA[inc.tipo]?.color || ''}`}>
                          <TipoIcon className="w-3 h-3" />
                          {TIPOS_INCIDENCIA[inc.tipo]?.label || inc.tipo}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={PRIORIDADES[inc.prioridad]?.color || ''}>
                          {PRIORIDADES[inc.prioridad]?.label || inc.prioridad}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={ESTADOS_INCIDENCIA[inc.estado]?.color || ''}>
                          {ESTADOS_INCIDENCIA[inc.estado]?.label || inc.estado}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatFecha(inc.created_at)}</TableCell>
                      <TableCell className="text-right space-x-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleVerDetalle(inc)}
                          data-testid={`ver-incidencia-${inc.id}`}
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEditarIncidencia(inc)}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Modal Crear/Editar */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {modoEditar ? 'Editar Incidencia' : 'Nueva Incidencia'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Cliente *</Label>
              <Select
                value={formData.cliente_id}
                onValueChange={(value) => {
                  setFormData({ ...formData, cliente_id: value, orden_id: '' });
                  fetchOrdenesCliente(value);
                }}
              >
                <SelectTrigger data-testid="select-cliente-incidencia">
                  <SelectValue placeholder="Selecciona un cliente" />
                </SelectTrigger>
                <SelectContent>
                  {clientes.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.nombre} {c.apellidos} - {c.telefono}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {ordenes.length > 0 && (
              <div className="space-y-2">
                <Label>Orden relacionada (opcional)</Label>
                <Select
                  value={formData.orden_id}
                  onValueChange={(value) => setFormData({ ...formData, orden_id: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Selecciona una orden" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Sin orden</SelectItem>
                    {ordenes.map((o) => (
                      <SelectItem key={o.id} value={o.id}>
                        {o.numero_orden} - {o.dispositivo?.modelo}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Tipo *</Label>
                <Select
                  value={formData.tipo}
                  onValueChange={(value) => setFormData({ ...formData, tipo: value })}
                >
                  <SelectTrigger data-testid="select-tipo-incidencia">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(TIPOS_INCIDENCIA).map(([key, val]) => (
                      <SelectItem key={key} value={key}>{val.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              

            {esTipoNCM && (
              <div className="space-y-3 p-3 border rounded-lg bg-amber-50/40" data-testid="ncm-fields-form">
                <p className="text-sm font-medium">Datos NCM (ISO 8.7 / WISE 3.13.1)</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Severidad NCM</Label>
                    <Select value={formData.severidad_ncm} onValueChange={(value) => setFormData({ ...formData, severidad_ncm: value })}>
                      <SelectTrigger data-testid="incidencia-severidad-ncm-select"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {Object.entries(SEVERIDADES_NCM).map(([key, val]) => (
                          <SelectItem key={key} value={key}>{val.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Disposición</Label>
                    <Select value={formData.disposicion_ncm} onValueChange={(value) => setFormData({ ...formData, disposicion_ncm: value })}>
                      <SelectTrigger data-testid="incidencia-disposicion-ncm-select"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {Object.entries(DISPOSICIONES_NCM).map(([key, label]) => (
                          <SelectItem key={key} value={key}>{label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Impacto</Label>
                  <Input
                    value={formData.impacto_ncm}
                    onChange={(e) => setFormData({ ...formData, impacto_ncm: e.target.value })}
                    placeholder="Impacto en cliente/proceso/seguridad"
                    data-testid="incidencia-impacto-ncm-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Contención inmediata</Label>
                  <Textarea
                    value={formData.contencion_ncm}
                    onChange={(e) => setFormData({ ...formData, contencion_ncm: e.target.value })}
                    placeholder="Acción inmediata para contener el problema"
                    className="min-h-[70px]"
                    data-testid="incidencia-contencion-ncm-textarea"
                  />
                </div>
              </div>
            )}

              <div className="space-y-2">
                <Label>Prioridad *</Label>
                <Select
                  value={formData.prioridad}
                  onValueChange={(value) => setFormData({ ...formData, prioridad: value })}
                >
                  <SelectTrigger data-testid="select-prioridad-incidencia">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(PRIORIDADES).map(([key, val]) => (
                      <SelectItem key={key} value={key}>{val.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Título *</Label>
              <Input
                placeholder="Breve descripción del problema"


                value={formData.titulo}
                onChange={(e) => setFormData({ ...formData, titulo: e.target.value })}
                data-testid="input-titulo-incidencia"
              />
            </div>

            <div className="space-y-2">
              <Label>Descripción detallada *</Label>
              <Textarea
                placeholder="Describe el problema con todos los detalles relevantes..."
                value={formData.descripcion}
                onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                className="min-h-[100px]"
                data-testid="input-descripcion-incidencia"
              />
            </div>
          </div>




          <DialogFooter>
            <Button variant="outline" onClick={() => setShowModal(false)}>
              Cancelar
            </Button>
            <Button onClick={handleGuardar} disabled={saving} data-testid="guardar-incidencia-btn">
              {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              {modoEditar ? 'Actualizar' : 'Crear'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal Detalle */}
      <Dialog open={showDetalleModal} onOpenChange={setShowDetalleModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              Incidencia {incidenciaDetalle?.numero_incidencia}
              <Badge className={ESTADOS_INCIDENCIA[incidenciaDetalle?.estado]?.color || ''}>
                {ESTADOS_INCIDENCIA[incidenciaDetalle?.estado]?.label}
              </Badge>
            </DialogTitle>
          </DialogHeader>
          
          {incidenciaDetalle && (
            <div className="space-y-4">
              <div className="p-4 bg-muted rounded-lg space-y-3">
                <h3 className="font-semibold text-lg">{incidenciaDetalle.titulo}</h3>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {incidenciaDetalle.descripcion}
                </p>
                <div className="flex gap-2 flex-wrap">
                  <Badge className={TIPOS_INCIDENCIA[incidenciaDetalle.tipo]?.color || ''}>
                    {TIPOS_INCIDENCIA[incidenciaDetalle.tipo]?.label}
                  </Badge>
                  <Badge className={PRIORIDADES[incidenciaDetalle.prioridad]?.color || ''}>
                    Prioridad: {PRIORIDADES[incidenciaDetalle.prioridad]?.label}
                  </Badge>
                  {incidenciaDetalle.severidad_ncm && (
                    <Badge className={SEVERIDADES_NCM[incidenciaDetalle.severidad_ncm]?.color || 'bg-gray-100 text-gray-700'}>
                      Severidad NCM: {SEVERIDADES_NCM[incidenciaDetalle.severidad_ncm]?.label || incidenciaDetalle.severidad_ncm}
                    </Badge>
                  )}
                  {incidenciaDetalle.disposicion_ncm && (
                    <Badge variant="outline">
                      Disposición: {DISPOSICIONES_NCM[incidenciaDetalle.disposicion_ncm] || incidenciaDetalle.disposicion_ncm}
                    </Badge>
                  )}

                </div>
              </div>

              {incidenciaDetalle.estado !== 'cerrada' && (
                <div className="space-y-2">
                  <Label>Notas de resolución</Label>
                  <Textarea
                    placeholder="Añade notas sobre cómo se resolvió o el estado actual..."
                    value={notasResolucion}
                    onChange={(e) => setNotasResolucion(e.target.value)}
                    className="min-h-[80px]"
                  />
                </div>
              )}

              {(incidenciaDetalle.es_no_conformidad || ['reclamacion', 'garantia', 'daño_transporte'].includes(incidenciaDetalle.tipo)) && (
                <div className="space-y-3 p-4 border rounded-lg bg-amber-50/40" data-testid="incidencia-capa-section">
                  <div className="flex items-center justify-between gap-3">
                    <h4 className="font-semibold text-sm">No Conformidad / CAPA</h4>
                    <Badge variant="outline" data-testid="incidencia-capa-estado-badge">
                      {incidenciaDetalle.capa_estado || 'abierta'}
                    </Badge>
                  </div>

                  <div className="space-y-2">
                    <Label>Causa raíz (5 porqués) *</Label>
                    <Textarea
                      value={capaData.causa_raiz}
                      onChange={(e) => setCapaData({ ...capaData, causa_raiz: e.target.value })}
                      placeholder="Describe la causa raíz"
                      className="min-h-[70px]"
                      data-testid="incidencia-capa-causa-raiz-input"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Acción correctiva *</Label>
                    <Textarea
                      value={capaData.accion_correctiva}
                      onChange={(e) => setCapaData({ ...capaData, accion_correctiva: e.target.value })}
                      placeholder="Qué acción se implementará para evitar recurrencia"
                      className="min-h-[70px]"
                      data-testid="incidencia-capa-accion-correctiva-input"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label>Responsable CAPA</Label>
                      <Input
                        value={capaData.responsable}
                        onChange={(e) => setCapaData({ ...capaData, responsable: e.target.value })}
                        placeholder="Nombre responsable"
                        data-testid="incidencia-capa-responsable-input"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Fecha objetivo</Label>
                      <Input
                        type="date"
                        value={capaData.fecha_objetivo}
                        onChange={(e) => setCapaData({ ...capaData, fecha_objetivo: e.target.value })}
                        data-testid="incidencia-capa-fecha-objetivo-input"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Verificación de eficacia</Label>
                    <Textarea
                      value={capaData.verificacion_eficacia}
                      onChange={(e) => setCapaData({ ...capaData, verificacion_eficacia: e.target.value })}
                      placeholder="Cómo y cuándo se verificó la eficacia"
                      className="min-h-[70px]"
                      data-testid="incidencia-capa-verificacion-input"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label>Fecha verificación</Label>
                      <Input
                        type="date"
                        value={capaData.fecha_verificacion}
                        onChange={(e) => setCapaData({ ...capaData, fecha_verificacion: e.target.value })}
                        data-testid="incidencia-capa-fecha-verificacion-input"
                      />
                    </div>
                    <div className="flex items-center gap-2 mt-7">
                      <Checkbox
                        id="capa-eficaz"
                        checked={capaData.eficaz}
                        onCheckedChange={(checked) => setCapaData({ ...capaData, eficaz: Boolean(checked) })}
                        data-testid="incidencia-capa-eficaz-checkbox"
                      />
                      <Label htmlFor="capa-eficaz">CAPA eficaz verificada</Label>
                    </div>
                  </div>

                  <Button
                    variant="outline"
                    onClick={handleGuardarCapa}
                    disabled={saving}
                    data-testid="incidencia-capa-guardar-button"
                  >
                    Guardar CAPA
                  </Button>
                </div>
              )}


              {incidenciaDetalle.notas_resolucion && incidenciaDetalle.estado === 'cerrada' && (
                <div className="p-3 bg-green-50 rounded-lg">
                  <p className="text-sm font-medium text-green-800">Resolución:</p>
                  <p className="text-sm text-green-700">{incidenciaDetalle.notas_resolucion}</p>
                </div>
              )}

              <div className="text-xs text-muted-foreground space-y-1">
                <p>Creada: {formatFecha(incidenciaDetalle.created_at)}</p>
                {incidenciaDetalle.fecha_resolucion && (
                  <p>Resuelta: {formatFecha(incidenciaDetalle.fecha_resolucion)}</p>
                )}
              </div>
            </div>
          )}

          <DialogFooter className="flex-col sm:flex-row gap-2">
            {incidenciaDetalle?.estado === 'abierta' && (
              <Button 
                variant="outline" 
                onClick={() => handleCambiarEstado('en_proceso')}
                disabled={saving}
              >
                <Clock className="w-4 h-4 mr-2" />
                En Proceso
              </Button>
            )}
            {(incidenciaDetalle?.estado === 'abierta' || incidenciaDetalle?.estado === 'en_proceso') && (
              <Button 
                onClick={() => handleCambiarEstado('resuelta')}
                disabled={saving}
                className="bg-green-600 hover:bg-green-700"
              >
                <CheckCircle2 className="w-4 h-4 mr-2" />
                Marcar Resuelta
              </Button>
            )}
            {incidenciaDetalle?.estado === 'resuelta' && (
              <Button 
                onClick={() => handleCambiarEstado('cerrada')}
                disabled={saving}
              >
                Cerrar Incidencia
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

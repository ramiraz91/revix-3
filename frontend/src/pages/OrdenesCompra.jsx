import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  ShoppingCart, 
  Package, 
  Check, 
  X, 
  Clock, 
  AlertTriangle,
  Filter,
  Search,
  Eye,
  CheckCircle2,
  XCircle,
  Loader2,
  Building2,
  Truck,
  Calendar
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
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
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import { ordenesCompraAPI } from '@/lib/api';
import { toast } from 'sonner';

const ESTADOS = {
  pendiente: { label: 'Pendiente', color: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
  aprobada: { label: 'Aprobada', color: 'bg-blue-100 text-blue-800 border-blue-300' },
  rechazada: { label: 'Rechazada', color: 'bg-red-100 text-red-800 border-red-300' },
  pedida: { label: 'Pedida', color: 'bg-purple-100 text-purple-800 border-purple-300' },
  recibida: { label: 'Recibida', color: 'bg-green-100 text-green-800 border-green-300' },
};

const PRIORIDADES = {
  normal: { label: 'Normal', color: 'bg-gray-100 text-gray-700' },
  urgente: { label: 'Urgente', color: 'bg-red-100 text-red-700' },
};

export default function OrdenesCompra() {
  const [loading, setLoading] = useState(true);
  const [ordenes, setOrdenes] = useState([]);
  const [filtroEstado, setFiltroEstado] = useState('all');
  const [filtroPrioridad, setFiltroPrioridad] = useState('all');
  const [busqueda, setBusqueda] = useState('');
  
  // Modal de detalle/acción
  const [showModal, setShowModal] = useState(false);
  const [ordenSeleccionada, setOrdenSeleccionada] = useState(null);
  const [accion, setAccion] = useState(null); // 'aprobar', 'rechazar', 'pedida', 'recibida'
  const [notasAccion, setNotasAccion] = useState('');
  const [numeroPedido, setNumeroPedido] = useState('');
  const [processing, setProcessing] = useState(false);
  
  // Búsqueda por número de pedido
  const [busquedaPedido, setBusquedaPedido] = useState('');
  const [resultadosBusqueda, setResultadosBusqueda] = useState(null);
  const [buscandoPedido, setBuscandoPedido] = useState(false);

  useEffect(() => {
    fetchOrdenes();
  }, [filtroEstado, filtroPrioridad]);

  const fetchOrdenes = async () => {
    try {
      setLoading(true);
      const params = {};
      if (filtroEstado !== 'all') params.estado = filtroEstado;
      if (filtroPrioridad !== 'all') params.prioridad = filtroPrioridad;
      
      const res = await ordenesCompraAPI.listar(params);
      setOrdenes(res.data);
    } catch (error) {
      toast.error('Error al cargar órdenes de compra');
    } finally {
      setLoading(false);
    }
  };

  const handleAccion = async () => {
    if (!ordenSeleccionada || !accion) return;
    
    setProcessing(true);
    try {
      let nuevoEstado = accion;
      if (accion === 'aprobar') nuevoEstado = 'aprobada';
      if (accion === 'rechazar') nuevoEstado = 'rechazada';
      
      const updateData = {
        estado: nuevoEstado,
        notas: notasAccion || undefined
      };
      
      // Si es estado "pedida", requerir número de pedido
      if (accion === 'pedida') {
        if (!numeroPedido.trim()) {
          toast.error('El número de pedido del proveedor es obligatorio');
          setProcessing(false);
          return;
        }
        updateData.numero_pedido_proveedor = numeroPedido.trim();
      }
      
      await ordenesCompraAPI.actualizar(ordenSeleccionada.id, updateData);
      
      toast.success(`Orden ${nuevoEstado} correctamente`);
      setShowModal(false);
      setOrdenSeleccionada(null);
      setAccion(null);
      setNotasAccion('');
      setNumeroPedido('');
      fetchOrdenes();
    } catch (error) {
      toast.error('Error al procesar la orden');
    } finally {
      setProcessing(false);
    }
  };
  
  // Buscar por número de pedido del proveedor
  const buscarPorNumeroPedido = async () => {
    if (!busquedaPedido.trim()) {
      toast.error('Ingresa un número de pedido');
      return;
    }
    try {
      setBuscandoPedido(true);
      const res = await ordenesCompraAPI.buscarPorPedido(busquedaPedido.trim());
      setResultadosBusqueda(res.data);
    } catch (error) {
      toast.error('Error al buscar');
    } finally {
      setBuscandoPedido(false);
    }
  };

  const abrirModal = (orden, accionTipo) => {
    setOrdenSeleccionada(orden);
    setAccion(accionTipo);
    setNotasAccion('');
    setNumeroPedido('');
    setShowModal(true);
  };

  const formatFecha = (fecha) => {
    if (!fecha) return '-';
    return new Date(fecha).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  const ordenesFiltradas = ordenes.filter(o => {
    if (!busqueda) return true;
    const search = busqueda.toLowerCase();
    return (
      o.nombre_pieza?.toLowerCase().includes(search) ||
      o.proveedor_nombre?.toLowerCase().includes(search) ||
      o.numero_orden_trabajo?.toLowerCase().includes(search)
    );
  });

  // Contadores
  const pendientes = ordenes.filter(o => o.estado === 'pendiente').length;
  const urgentes = ordenes.filter(o => o.prioridad === 'urgente' && o.estado === 'pendiente').length;

  if (loading && ordenes.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="ordenes-compra-page">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ShoppingCart className="w-7 h-7" />
            Órdenes de Compra
          </h1>
          <p className="text-muted-foreground">
            Gestiona las solicitudes de piezas y materiales
          </p>
        </div>
        
        <div className="flex gap-2">
          {urgentes > 0 && (
            <Badge variant="destructive" className="text-sm px-3 py-1">
              <AlertTriangle className="w-4 h-4 mr-1" />
              {urgentes} urgentes
            </Badge>
          )}
          {pendientes > 0 && (
            <Badge variant="warning" className="text-sm px-3 py-1 bg-yellow-100 text-yellow-800">
              <Clock className="w-4 h-4 mr-1" />
              {pendientes} pendientes
            </Badge>
          )}
        </div>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                <Input
                  placeholder="Buscar por pieza, proveedor u orden..."
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  className="pl-10"
                  data-testid="buscar-ordenes-compra"
                />
              </div>
            </div>
            
            <Select value={filtroEstado} onValueChange={setFiltroEstado}>
              <SelectTrigger className="w-40" data-testid="filtro-estado">
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="pendiente">Pendientes</SelectItem>
                <SelectItem value="aprobada">Aprobadas</SelectItem>
                <SelectItem value="pedida">Pedidas</SelectItem>
                <SelectItem value="recibida">Recibidas</SelectItem>
                <SelectItem value="rechazada">Rechazadas</SelectItem>
              </SelectContent>
            </Select>
            
            <Select value={filtroPrioridad} onValueChange={setFiltroPrioridad}>
              <SelectTrigger className="w-40" data-testid="filtro-prioridad">
                <SelectValue placeholder="Prioridad" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                <SelectItem value="urgente">Urgentes</SelectItem>
                <SelectItem value="normal">Normales</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Panel de búsqueda por número de pedido */}
      <Card className="border-dashed border-2">
        <CardContent className="pt-4">
          <div className="flex flex-col sm:flex-row gap-4 items-start">
            <div className="flex-1">
              <Label className="text-sm mb-2 block">Buscar por Nº de Pedido del Proveedor</Label>
              <div className="flex gap-2">
                <Input
                  placeholder="PED-2026-001234, FAC-12345..."
                  value={busquedaPedido}
                  onChange={(e) => setBusquedaPedido(e.target.value)}
                  className="font-mono"
                  onKeyDown={(e) => e.key === 'Enter' && buscarPorNumeroPedido()}
                  data-testid="busqueda-pedido-input"
                />
                <Button onClick={buscarPorNumeroPedido} disabled={buscandoPedido} data-testid="btn-buscar-pedido">
                  {buscandoPedido ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                </Button>
              </div>
            </div>
            {resultadosBusqueda && (
              <div className="flex-1 bg-muted rounded-lg p-3">
                <p className="text-sm font-medium mb-2">
                  Resultados para "{resultadosBusqueda.numero_pedido}": {resultadosBusqueda.total}
                </p>
                {resultadosBusqueda.resultados.map((r, idx) => (
                  <div key={idx} className="text-sm border-b last:border-0 py-2">
                    <div><strong>OC:</strong> {r.orden_compra?.numero_oc} - {r.orden_compra?.nombre_pieza}</div>
                    <div><strong>Orden:</strong> <Link to={`/ordenes/${r.orden_trabajo?.id}`} className="text-blue-600 hover:underline">{r.orden_trabajo?.numero_orden || 'N/A'}</Link></div>
                    <div><strong>Cliente:</strong> {r.cliente?.nombre} {r.cliente?.apellidos} ({r.cliente?.telefono})</div>
                    <div><strong>Estado:</strong> <Badge className={ESTADOS[r.orden_compra?.estado]?.color}>{ESTADOS[r.orden_compra?.estado]?.label}</Badge></div>
                  </div>
                ))}
                <Button variant="ghost" size="sm" onClick={() => setResultadosBusqueda(null)} className="mt-2">
                  Cerrar
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Tabs por estado */}
      <Tabs defaultValue="pendientes" className="space-y-4">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="pendientes" className="gap-2">
            <Clock className="w-4 h-4" />
            Pendientes ({ordenes.filter(o => o.estado === 'pendiente').length})
          </TabsTrigger>
          <TabsTrigger value="aprobadas" className="gap-2">
            <CheckCircle2 className="w-4 h-4" />
            Aprobadas ({ordenes.filter(o => o.estado === 'aprobada').length})
          </TabsTrigger>
          <TabsTrigger value="pedidas" className="gap-2">
            <Truck className="w-4 h-4" />
            Pedidas ({ordenes.filter(o => o.estado === 'pedida').length})
          </TabsTrigger>
          <TabsTrigger value="recibidas" className="gap-2">
            <CheckCircle2 className="w-4 h-4 text-green-600" />
            Recibidas ({ordenes.filter(o => o.estado === 'recibida').length})
          </TabsTrigger>
          <TabsTrigger value="todas" className="gap-2">
            <Package className="w-4 h-4" />
            Todas ({ordenes.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="pendientes">
          <OrdenesTable 
            ordenes={ordenesFiltradas.filter(o => o.estado === 'pendiente')}
            onAprobar={(o) => abrirModal(o, 'aprobar')}
            onRechazar={(o) => abrirModal(o, 'rechazar')}
            formatFecha={formatFecha}
            showActions
          />
        </TabsContent>

        <TabsContent value="aprobadas">
          <OrdenesTable 
            ordenes={ordenesFiltradas.filter(o => o.estado === 'aprobada')}
            onPedida={(o) => abrirModal(o, 'pedida')}
            formatFecha={formatFecha}
            showPedidaAction
          />
        </TabsContent>

        <TabsContent value="pedidas">
          <OrdenesTable 
            ordenes={ordenesFiltradas.filter(o => o.estado === 'pedida')}
            onRecibida={(o) => abrirModal(o, 'recibida')}
            formatFecha={formatFecha}
            showRecibidaAction
          />
        </TabsContent>

        <TabsContent value="recibidas">
          <OrdenesTable 
            ordenes={ordenesFiltradas.filter(o => o.estado === 'recibida')}
            formatFecha={formatFecha}
          />
        </TabsContent>

        <TabsContent value="todas">
          <OrdenesTable 
            ordenes={ordenesFiltradas}
            formatFecha={formatFecha}
          />
        </TabsContent>
      </Tabs>

      {/* Modal de Acción */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {accion === 'aprobar' && 'Aprobar Orden de Compra'}
              {accion === 'rechazar' && 'Rechazar Orden de Compra'}
              {accion === 'pedida' && 'Marcar como Pedida'}
              {accion === 'recibida' && 'Marcar como Recibida'}
            </DialogTitle>
            <DialogDescription>
              {ordenSeleccionada?.nombre_pieza} - Cantidad: {ordenSeleccionada?.cantidad}
            </DialogDescription>
          </DialogHeader>
          
          {ordenSeleccionada && (
            <div className="space-y-4">
              <div className="p-4 bg-muted rounded-lg space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Pieza:</span>
                  <span className="font-medium">{ordenSeleccionada.nombre_pieza}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Cantidad:</span>
                  <span className="font-medium">{ordenSeleccionada.cantidad}</span>
                </div>
                {ordenSeleccionada.proveedor_nombre && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Proveedor:</span>
                    <span className="font-medium">{ordenSeleccionada.proveedor_nombre}</span>
                  </div>
                )}
                {ordenSeleccionada.numero_orden_trabajo && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Orden de trabajo:</span>
                    <Link 
                      to={`/ordenes/${ordenSeleccionada.orden_trabajo_id}`}
                      className="font-medium text-blue-600 hover:underline"
                    >
                      {ordenSeleccionada.numero_orden_trabajo}
                    </Link>
                  </div>
                )}
                {ordenSeleccionada.numero_pedido_proveedor && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Nº Pedido Proveedor:</span>
                    <span className="font-medium font-mono">{ordenSeleccionada.numero_pedido_proveedor}</span>
                  </div>
                )}
                {ordenSeleccionada.prioridad === 'urgente' && (
                  <Badge variant="destructive" className="mt-2">
                    <AlertTriangle className="w-3 h-3 mr-1" />
                    URGENTE
                  </Badge>
                )}
              </div>

              {/* Campo para número de pedido (solo al marcar como pedida) */}
              {accion === 'pedida' && (
                <div className="space-y-2">
                  <Label className="text-red-600">Nº Pedido Proveedor *</Label>
                  <Input
                    placeholder="Ej: PED-2026-001234, FAC-12345..."
                    value={numeroPedido}
                    onChange={(e) => setNumeroPedido(e.target.value)}
                    className="font-mono"
                    data-testid="numero-pedido-input"
                  />
                  <p className="text-xs text-muted-foreground">
                    Este número permite rastrear el pedido y asignarlo cuando llegue el material
                  </p>
                </div>
              )}

              <div className="space-y-2">
                <Label>Notas (opcional)</Label>
                <Textarea
                  placeholder={
                    accion === 'rechazar' 
                      ? 'Motivo del rechazo...' 
                      : 'Añade notas adicionales...'
                  }
                  value={notasAccion}
                  onChange={(e) => setNotasAccion(e.target.value)}
                  data-testid="notas-accion"
                />
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowModal(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleAccion} 
              disabled={processing}
              variant={accion === 'rechazar' ? 'destructive' : 'default'}
              data-testid="confirmar-accion-btn"
            >
              {processing && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              {accion === 'aprobar' && 'Aprobar'}
              {accion === 'rechazar' && 'Rechazar'}
              {accion === 'pedida' && 'Marcar Pedida'}
              {accion === 'recibida' && 'Marcar Recibida'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Componente de tabla reutilizable
function OrdenesTable({ ordenes, onAprobar, onRechazar, onPedida, onRecibida, formatFecha, showActions, showPedidaAction, showRecibidaAction }) {
  if (ordenes.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No hay órdenes de compra en esta categoría</p>
        </CardContent>
      </Card>
    );
  }

  const showAnyAction = showActions || showPedidaAction || showRecibidaAction;

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Pieza</TableHead>
              <TableHead>Cantidad</TableHead>
              <TableHead>Proveedor</TableHead>
              <TableHead>Orden Trabajo</TableHead>
              <TableHead>Nº Pedido</TableHead>
              <TableHead>Prioridad</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Fecha</TableHead>
              {showAnyAction && (
                <TableHead className="text-right">Acciones</TableHead>
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {ordenes.map((orden) => (
              <TableRow key={orden.id} data-testid={`orden-compra-row-${orden.id}`}>
                <TableCell className="font-medium">{orden.nombre_pieza}</TableCell>
                <TableCell>{orden.cantidad}</TableCell>
                <TableCell>{orden.proveedor_nombre || '-'}</TableCell>
                <TableCell>
                  {orden.orden_trabajo_id ? (
                    <Link 
                      to={`/ordenes/${orden.orden_trabajo_id}`}
                      className="text-blue-600 hover:underline"
                    >
                      {orden.orden_trabajo_info?.numero_orden || orden.numero_orden_trabajo || 'Ver'}
                    </Link>
                  ) : '-'}
                </TableCell>
                <TableCell className="font-mono text-sm">
                  {orden.numero_pedido_proveedor || '-'}
                </TableCell>
                <TableCell>
                  <Badge className={PRIORIDADES[orden.prioridad]?.color || 'bg-gray-100'}>
                    {PRIORIDADES[orden.prioridad]?.label || orden.prioridad}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge className={ESTADOS[orden.estado]?.color || 'bg-gray-100'}>
                    {ESTADOS[orden.estado]?.label || orden.estado}
                  </Badge>
                </TableCell>
                <TableCell>{formatFecha(orden.created_at)}</TableCell>
                
                {showActions && (
                  <TableCell className="text-right space-x-2">
                    <Button
                      size="sm"
                      onClick={() => onAprobar(orden)}
                      className="bg-green-600 hover:bg-green-700"
                      data-testid={`aprobar-${orden.id}`}
                    >
                      <Check className="w-4 h-4 mr-1" />
                      Aprobar
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => onRechazar(orden)}
                      data-testid={`rechazar-${orden.id}`}
                    >
                      <X className="w-4 h-4 mr-1" />
                      Rechazar
                    </Button>
                  </TableCell>
                )}
                
                {showPedidaAction && (
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onPedida(orden)}
                      data-testid={`pedida-${orden.id}`}
                    >
                      <Truck className="w-4 h-4 mr-1" />
                      Marcar Pedida
                    </Button>
                  </TableCell>
                )}

                {showRecibidaAction && (
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      onClick={() => onRecibida(orden)}
                      className="bg-green-600 hover:bg-green-700"
                      data-testid={`recibida-${orden.id}`}
                    >
                      <CheckCircle2 className="w-4 h-4 mr-1" />
                      Marcar Recibida
                    </Button>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  User, 
  Smartphone, 
  Phone, 
  Mail, 
  MapPin,
  Calendar,
  ClipboardList,
  Shield,
  XCircle,
  Repeat,
  Euro,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Plus,
  MessageSquare,
  RefreshCw,
  Package,
  FileText,
  Clock
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { clientesAPI, incidenciasAPI } from '@/lib/api';
import { toast } from 'sonner';

const statusConfig = {
  pendiente_recibir: { label: 'Pendiente', color: 'bg-yellow-500' },
  recibida: { label: 'Recibida', color: 'bg-blue-500' },
  en_taller: { label: 'En Taller', color: 'bg-purple-500' },
  reparado: { label: 'Reparado', color: 'bg-green-500' },
  enviado: { label: 'Enviado', color: 'bg-emerald-500' },
  garantia: { label: 'Garantía', color: 'bg-red-500' },
  reemplazo: { label: 'Reemplazo', color: 'bg-cyan-500' },
  irreparable: { label: 'Irreparable', color: 'bg-red-600' },
  cancelado: { label: 'Cancelado', color: 'bg-gray-500' },
};

const TIPOS_INCIDENCIA = {
  reemplazo_dispositivo: { label: 'Reemplazo', icon: RefreshCw, color: 'bg-blue-100 text-blue-800' },
  reclamacion: { label: 'Reclamación', icon: MessageSquare, color: 'bg-orange-100 text-orange-800' },
  garantia: { label: 'Garantía', icon: Shield, color: 'bg-purple-100 text-purple-800' },
  daño_transporte: { label: 'Daño Transporte', icon: Package, color: 'bg-red-100 text-red-800' },
  otro: { label: 'Otro', icon: FileText, color: 'bg-gray-100 text-gray-800' },
};

const ESTADOS_INCIDENCIA = {
  abierta: { label: 'Abierta', color: 'bg-red-100 text-red-800' },
  en_proceso: { label: 'En Proceso', color: 'bg-yellow-100 text-yellow-800' },
  resuelta: { label: 'Resuelta', color: 'bg-green-100 text-green-800' },
  cerrada: { label: 'Cerrada', color: 'bg-gray-100 text-gray-800' },
};

export default function ClienteDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [incidencias, setIncidencias] = useState([]);
  const [loadingIncidencias, setLoadingIncidencias] = useState(true);

  useEffect(() => {
    fetchHistorial();
    fetchIncidencias();
  }, [id]);

  const fetchHistorial = async () => {
    try {
      setLoading(true);
      const response = await clientesAPI.historial(id);
      setData(response.data);
    } catch (error) {
      toast.error('Error al cargar datos del cliente');
      navigate('/clientes');
    } finally {
      setLoading(false);
    }
  };

  const fetchIncidencias = async () => {
    try {
      setLoadingIncidencias(true);
      const response = await incidenciasAPI.porCliente(id);
      setIncidencias(response.data);
    } catch (error) {
      console.error('Error cargando incidencias:', error);
    } finally {
      setLoadingIncidencias(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!data) return null;

  const { cliente, ordenes, dispositivos, estadisticas } = data;

  return (
    <div className="space-y-6 animate-fade-in" data-testid="cliente-detalle-page">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/clientes')}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <User className="w-7 h-7" />
            {cliente.nombre}
          </h1>
          <p className="text-muted-foreground">Ficha completa del cliente</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <ClipboardList className="w-8 h-8 mx-auto text-blue-500 mb-2" />
            <p className="text-3xl font-bold">{estadisticas.total_ordenes}</p>
            <p className="text-sm text-muted-foreground">Órdenes</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <CheckCircle2 className="w-8 h-8 mx-auto text-green-500 mb-2" />
            <p className="text-3xl font-bold">{estadisticas.ordenes_completadas}</p>
            <p className="text-sm text-muted-foreground">Completadas</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <Shield className="w-8 h-8 mx-auto text-orange-500 mb-2" />
            <p className="text-3xl font-bold">{estadisticas.ordenes_garantia}</p>
            <p className="text-sm text-muted-foreground">Garantías</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <Smartphone className="w-8 h-8 mx-auto text-purple-500 mb-2" />
            <p className="text-3xl font-bold">{estadisticas.dispositivos_unicos}</p>
            <p className="text-sm text-muted-foreground">Dispositivos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <Euro className="w-8 h-8 mx-auto text-emerald-500 mb-2" />
            <p className="text-3xl font-bold">€{estadisticas.total_gastado}</p>
            <p className="text-sm text-muted-foreground">Total</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Info Cliente */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="w-5 h-5" />
              Datos del Cliente
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-3">
              <Phone className="w-4 h-4 text-muted-foreground" />
              <span>{cliente.telefono}</span>
            </div>
            {cliente.telefono_secundario && (
              <div className="flex items-center gap-3">
                <Phone className="w-4 h-4 text-muted-foreground" />
                <span>{cliente.telefono_secundario}</span>
              </div>
            )}
            {cliente.email && (
              <div className="flex items-center gap-3">
                <Mail className="w-4 h-4 text-muted-foreground" />
                <span>{cliente.email}</span>
              </div>
            )}
            {cliente.direccion && (
              <div className="flex items-center gap-3">
                <MapPin className="w-4 h-4 text-muted-foreground" />
                <span>{cliente.direccion}</span>
              </div>
            )}
            {cliente.dni && (
              <div className="flex items-center gap-3">
                <User className="w-4 h-4 text-muted-foreground" />
                <span>DNI: {cliente.dni}</span>
              </div>
            )}
            <Separator />
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Calendar className="w-4 h-4" />
              <span>Cliente desde: {new Date(cliente.created_at).toLocaleDateString('es-ES')}</span>
            </div>
          </CardContent>
        </Card>

        {/* Dispositivos */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Smartphone className="w-5 h-5" />
              Dispositivos del Cliente
            </CardTitle>
            <CardDescription>Historial de dispositivos reparados</CardDescription>
          </CardHeader>
          <CardContent>
            {dispositivos.length === 0 ? (
              <p className="text-center text-muted-foreground py-4">No hay dispositivos registrados</p>
            ) : (
              <div className="space-y-3">
                {dispositivos.map((disp, idx) => (
                  <div 
                    key={idx} 
                    className={`p-4 rounded-lg border ${
                      disp.irreparable ? 'border-red-300 bg-red-50' :
                      disp.reemplazado ? 'border-cyan-300 bg-cyan-50' :
                      'bg-slate-50'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-semibold flex items-center gap-2">
                          <Smartphone className="w-4 h-4" />
                          {disp.modelo}
                          {disp.reemplazado && (
                            <Badge variant="outline" className="bg-cyan-100 text-cyan-700">
                              <Repeat className="w-3 h-3 mr-1" />
                              Reemplazado
                            </Badge>
                          )}
                          {disp.irreparable && (
                            <Badge variant="destructive">
                              <XCircle className="w-3 h-3 mr-1" />
                              Irreparable
                            </Badge>
                          )}
                        </h4>
                        <p className="text-sm text-muted-foreground">
                          IMEI: {disp.imei} • Color: {disp.color || 'N/A'}
                        </p>
                      </div>
                      <Badge variant="secondary">
                        {disp.total_reparaciones} reparación{disp.total_reparaciones !== 1 ? 'es' : ''}
                      </Badge>
                    </div>
                    <div className="mt-2 text-sm">
                      <p className="text-muted-foreground">Últimos servicios:</p>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {disp.servicios.slice(0, 3).map((serv, i) => (
                          <Link 
                            key={i} 
                            to={`/ordenes/${serv.numero_orden}`}
                            className="text-xs px-2 py-1 bg-white rounded border hover:bg-slate-100"
                          >
                            {serv.numero_orden}
                            {serv.es_garantia && <Shield className="w-3 h-3 inline ml-1 text-orange-500" />}
                          </Link>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Historial de Órdenes */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ClipboardList className="w-5 h-5" />
            Historial de Servicios
          </CardTitle>
          <CardDescription>Todas las órdenes de trabajo del cliente</CardDescription>
        </CardHeader>
        <CardContent>
          {ordenes.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">No hay órdenes registradas</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nº Orden</TableHead>
                  <TableHead>Dispositivo</TableHead>
                  <TableHead>Daños</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ordenes.map((orden) => (
                  <TableRow key={orden.id}>
                    <TableCell className="font-mono font-medium">
                      {orden.numero_orden}
                      {orden.es_garantia && (
                        <Badge variant="outline" className="ml-2 text-xs">
                          <Shield className="w-3 h-3 mr-1" />
                          Garantía
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <div>
                        <p className="font-medium">{orden.dispositivo?.modelo}</p>
                        <p className="text-xs text-muted-foreground">IMEI: {orden.dispositivo?.imei}</p>
                      </div>
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate text-sm text-muted-foreground">
                      {orden.dispositivo?.daños || '-'}
                    </TableCell>
                    <TableCell>
                      <Badge className={`${statusConfig[orden.estado]?.color || 'bg-gray-500'} text-white`}>
                        {statusConfig[orden.estado]?.label || orden.estado}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(orden.created_at).toLocaleDateString('es-ES')}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" asChild>
                        <Link to={`/ordenes/${orden.id}`}>
                          <ExternalLink className="w-4 h-4" />
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Incidencias del Cliente */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" />
                Incidencias
              </CardTitle>
              <CardDescription>Reclamaciones, garantías y problemas reportados</CardDescription>
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => navigate(`/incidencias?cliente_id=${id}`)}
              data-testid="nueva-incidencia-cliente-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              Nueva Incidencia
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loadingIncidencias ? (
            <div className="text-center py-6">
              <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full mx-auto" />
            </div>
          ) : incidencias.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              <CheckCircle2 className="w-12 h-12 mx-auto mb-3 text-green-200" />
              <p>Este cliente no tiene incidencias registradas</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Número</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Título</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {incidencias.map((inc) => {
                  const TipoIcon = TIPOS_INCIDENCIA[inc.tipo]?.icon || FileText;
                  return (
                    <TableRow key={inc.id}>
                      <TableCell className="font-mono text-sm">
                        {inc.numero_incidencia}
                      </TableCell>
                      <TableCell>
                        <Badge className={`gap-1 ${TIPOS_INCIDENCIA[inc.tipo]?.color || ''}`}>
                          <TipoIcon className="w-3 h-3" />
                          {TIPOS_INCIDENCIA[inc.tipo]?.label || inc.tipo}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate font-medium">
                        {inc.titulo}
                      </TableCell>
                      <TableCell>
                        <Badge className={ESTADOS_INCIDENCIA[inc.estado]?.color || ''}>
                          {inc.estado === 'abierta' && <Clock className="w-3 h-3 mr-1" />}
                          {ESTADOS_INCIDENCIA[inc.estado]?.label || inc.estado}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(inc.created_at).toLocaleDateString('es-ES')}
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" asChild>
                          <Link to={`/incidencias?id=${inc.id}`}>
                            <ExternalLink className="w-4 h-4" />
                          </Link>
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
    </div>
  );
}

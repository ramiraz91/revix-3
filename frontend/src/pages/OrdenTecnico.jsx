import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import QRCode from 'react-qr-code';
import { 
  ArrowLeft, 
  Lock,
  Clock,
  CheckCircle2,
  Wrench,
  AlertTriangle,
  Package,
  Repeat,
  XCircle as XCircleIcon,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ordenesAPI, repuestosAPI } from '@/lib/api';
import { toast } from 'sonner';

// Import refactored components
import {
  TecnicoDispositivoCard,
  TecnicoDiagnosticoIA,
  TecnicoDiagnosticoForm,
  TecnicoMaterialesCard,
  TecnicoFotosCard,
  TecnicoCierreReparacion,
  TecnicoMensajesCard,
  TecnicoRICard,
  TecnicoCPICard,
  TecnicoAccionesCard,
} from '@/components/tecnico';

import { OrdenSubestadoCard } from '@/components/orden';

const statusConfig = {
  pendiente_recibir: { label: 'Pendiente Recibir', icon: Clock, color: 'bg-yellow-500' },
  recibida: { label: 'Recibida', icon: CheckCircle2, color: 'bg-blue-500' },
  en_taller: { label: 'En Taller', icon: Wrench, color: 'bg-purple-500' },
  re_presupuestar: { label: 'Re-presupuestar', icon: AlertTriangle, color: 'bg-orange-500' },
  reparado: { label: 'Reparado', icon: CheckCircle2, color: 'bg-green-500' },
  validacion: { label: 'Validación', icon: Package, color: 'bg-indigo-500' },
  enviado: { label: 'Enviado', icon: CheckCircle2, color: 'bg-emerald-500' },
  reemplazo: { label: 'Reemplazo', icon: Repeat, color: 'bg-cyan-500' },
  irreparable: { label: 'Irreparable', icon: XCircleIcon, color: 'bg-red-500' },
};

export default function OrdenTecnico() {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [orden, setOrden] = useState(null);
  const [repuestos, setRepuestos] = useState([]);
  const [mensajes, setMensajes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [diagnostico, setDiagnostico] = useState('');
  const [imeiValidado, setImeiValidado] = useState(false);

  const fetchOrden = async () => {
    try {
      setLoading(true);
      const [ordenRes, repuestosRes, mensajesRes] = await Promise.all([
        ordenesAPI.obtener(id),
        repuestosAPI.listar({ page_size: 100 }),
        ordenesAPI.obtenerMensajes(id)
      ]);
      setOrden(ordenRes.data);
      // La API devuelve {items: [], total: X, ...} - extraer items
      setRepuestos(repuestosRes.data.items || []);
      setMensajes(mensajesRes.data);
      setDiagnostico(ordenRes.data.diagnostico_tecnico || '');
      setImeiValidado(ordenRes.data.imei_validado === true);
    } catch (error) {
      toast.error('Error al cargar la orden');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrden();
  }, [id]);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-10 bg-slate-200 rounded w-48" />
        <div className="h-64 bg-slate-200 rounded-xl" />
      </div>
    );
  }

  if (!orden) {
    return (
      <div className="text-center py-16">
        <p className="text-lg">Orden no encontrada</p>
        <Button onClick={() => navigate('/ordenes')} className="mt-4">
          Volver a órdenes
        </Button>
      </div>
    );
  }

  const currentStatus = statusConfig[orden.estado];

  return (
    <div className="space-y-6 animate-fade-in" data-testid="orden-tecnico-page">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight font-mono">{orden.numero_orden}</h1>
            <Badge className={`badge-status status-${orden.estado}`}>
              {currentStatus?.label}
            </Badge>
            {orden.bloqueada && (
              <Badge variant="destructive" className="gap-1">
                <Lock className="w-3 h-3" />
                BLOQUEADA
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground mt-1">Vista de Técnico</p>
        </div>
        {orden.numero_autorizacion && (
          <div className="text-right px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-xs text-blue-600 uppercase tracking-wider">Nº Autorización</p>
            <p className="font-mono font-bold text-lg text-blue-800">{orden.numero_autorizacion}</p>
          </div>
        )}
      </div>

      {/* Blocked Warning */}
      {orden.bloqueada && (
        <Card className="border-red-500 border-2 bg-red-50">
          <CardContent className="py-4 flex items-center gap-4">
            <Lock className="w-8 h-8 text-red-500" />
            <div>
              <p className="font-semibold text-red-700">Orden Bloqueada</p>
              <p className="text-sm text-red-600">
                Has añadido materiales que requieren aprobación del administrador.
                No puedes continuar hasta que se aprueben.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Dispositivo */}
          <TecnicoDispositivoCard 
            orden={orden}
            imeiValidado={imeiValidado}
            setImeiValidado={setImeiValidado}
            onRefresh={fetchOrden}
          />

          {/* Inspección de Entrada (RI) — ISO 9001 obligatorio */}
          <TecnicoRICard orden={orden} onRefresh={fetchOrden} />

          {/* Privacidad del dispositivo (CPI / NIST 800-88) — ISO/WISE obligatorio */}
          <TecnicoCPICard orden={orden} onRefresh={fetchOrden} />

          {/* Diagnóstico IA */}
          <TecnicoDiagnosticoIA 
            orden={orden}
            diagnostico={diagnostico}
            setDiagnostico={setDiagnostico}
          />

          {/* Diagnóstico Técnico */}
          <TecnicoDiagnosticoForm 
            orden={orden}
            diagnostico={diagnostico}
            setDiagnostico={setDiagnostico}
            onRefresh={fetchOrden}
          />

          {/* Materiales */}
          <TecnicoMaterialesCard 
            orden={orden}
            repuestos={repuestos}
            onRefresh={fetchOrden}
          />

          {/* Fotos */}
          <TecnicoFotosCard 
            orden={orden}
            onRefresh={fetchOrden}
          />

          {/* Mensajes */}
          <TecnicoMensajesCard 
            orden={orden}
            mensajes={mensajes}
            onRefresh={fetchOrden}
          />

          {/* Cierre Reparación */}
          <TecnicoCierreReparacion 
            orden={orden}
            onRefresh={fetchOrden}
          />
        </div>

        {/* Right Column - Acciones + QR + Estado */}
        <div className="space-y-6">

          {/* Acciones de la reparación — siempre arriba */}
          <TecnicoAccionesCard orden={orden} onRefresh={fetchOrden} />

          <Card>
            <CardHeader>
              <CardTitle className="text-center">Código de Barras</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col items-center">
              <div className="qr-container p-6 bg-white">
                <QRCode value={orden.numero_orden} size={180} />
              </div>
              <p className="mt-4 font-mono text-sm text-muted-foreground">
                {orden.numero_orden}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Estado Actual</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                <div className={`w-4 h-4 rounded-full ${currentStatus?.color}`} />
                <span className="font-medium">{currentStatus?.label}</span>
              </div>
            </CardContent>
          </Card>

          {/* Subestado Card - permite al técnico indicar estado intermedio (ej: esperando piezas) */}
          <OrdenSubestadoCard 
            ordenId={orden.id}
            subestadoActual={orden.subestado}
            motivoActual={orden.motivo_subestado}
            fechaRevision={orden.fecha_revision_subestado}
            onUpdate={fetchOrden}
          />
        </div>
      </div>
    </div>
  );
}

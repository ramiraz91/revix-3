/**
 * Nuevas Órdenes - Gestión de pre-registros aceptados pendientes de tramitar.
 * El tramitador revisa, añade código de recogida y confirma la creación de la orden.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  PackagePlus, RefreshCw, Truck, User, Smartphone, AlertCircle,
  CheckCircle, XCircle, Clock, FileText, ArrowRight, Phone, Mail, MapPin
} from 'lucide-react';
import API from '@/lib/api';
import { toast } from 'sonner';

export default function NuevasOrdenes() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState([]);
  const [polling, setPolling] = useState(false);

  const cargarDatos = useCallback(async () => {
    setLoading(true);
    try {
      const res = await API.get('/nuevas-ordenes/');
      setItems(res.data?.items || []);
    } catch (error) {
      console.error('Error cargando nuevas órdenes:', error);
      toast.error('Error cargando nuevas órdenes');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { cargarDatos(); }, [cargarDatos]);

  const handleActualizarInsurama = async () => {
    setPolling(true);
    try {
      const res = await API.post('/nuevas-ordenes/actualizar-insurama');
      toast.info(res.data?.message || 'Consultando Insurama...');
      // Recargar después de unos segundos para dar tiempo al polling
      setTimeout(() => { cargarDatos(); setPolling(false); }, 5000);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error consultando Insurama');
      setPolling(false);
    }
  };

  const handleRechazar = async (item) => {
    if (!window.confirm(`¿Archivar el siniestro ${item.codigo_siniestro}?`)) return;
    try {
      await API.post(`/nuevas-ordenes/${item.id}/rechazar`);
      toast.success('Nueva orden archivada');
      cargarDatos();
    } catch (error) {
      toast.error('Error al archivar');
    }
  };

  const fmt = (v) => v ? new Date(v).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-';

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <RefreshCw className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="nuevas-ordenes-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <PackagePlus className="w-6 h-6" />
            Nuevas Órdenes
            {items.length > 0 && (
              <Badge variant="destructive" className="text-sm">{items.length}</Badge>
            )}
          </h1>
          <p className="text-muted-foreground text-sm">
            Órdenes autorizadas por Insurama pendientes de tramitar
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleActualizarInsurama} disabled={polling} data-testid="actualizar-insurama-btn">
            {polling ? <RefreshCw className="w-4 h-4 animate-spin mr-1" /> : <RefreshCw className="w-4 h-4 mr-1" />}
            {polling ? 'Consultando...' : 'Consultar Insurama'}
          </Button>
          <Button variant="ghost" size="icon" onClick={cargarDatos} data-testid="refresh-nuevas-btn">
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Empty State */}
      {items.length === 0 && (
        <Card>
          <CardContent className="py-16 text-center">
            <CheckCircle className="w-12 h-12 mx-auto text-green-400 mb-4" />
            <p className="text-lg font-medium">No hay nuevas órdenes pendientes</p>
            <p className="text-sm text-muted-foreground mt-1">
              Las órdenes autorizadas aparecerán aquí automáticamente (polling cada 2h)
            </p>
          </CardContent>
        </Card>
      )}

      {/* Items */}
      <div className="space-y-3">
        {items.map((item) => (
          <Card key={item.id} className="hover:shadow-md transition-shadow cursor-pointer" 
                onClick={() => navigate(`/nuevas-ordenes/${item.id}`)}
                data-testid={`nueva-orden-${item.id}`}>
            <CardContent className="pt-4">
              <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                {/* Info principal */}
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="font-mono font-bold text-base text-primary">{item.codigo_siniestro}</span>
                    <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 text-xs">
                      <Clock className="w-3 h-3 mr-1" /> Pendiente tramitar
                    </Badge>
                    {item.sumbroker_price && (
                      <Badge variant="secondary" className="text-xs font-mono">
                        {parseFloat(item.sumbroker_price).toFixed(2)}€
                      </Badge>
                    )}
                  </div>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-1 text-sm">
                    <div className="flex items-center gap-2">
                      <User className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                      <span className="font-medium truncate">{item.cliente_nombre || 'Sin nombre'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Phone className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                      <span className="truncate">{item.cliente_telefono || '-'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Mail className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                      <span className="truncate">{item.cliente_email || '-'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Smartphone className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                      <span className="truncate">{item.dispositivo_modelo || 'Sin modelo'}</span>
                    </div>
                    <div className="flex items-center gap-2 sm:col-span-2">
                      <FileText className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                      <span className="truncate">{item.daño_descripcion || 'Sin descripción'}</span>
                    </div>
                  </div>
                  
                  {(item.cliente_direccion || item.cliente_codigo_postal || item.cliente_ciudad) && (
                    <p className="text-xs text-muted-foreground flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {[item.cliente_direccion, item.cliente_codigo_postal, item.cliente_ciudad].filter(Boolean).join(', ')}
                    </p>
                  )}
                  
                  <p className="text-xs text-muted-foreground">
                    Detectado: {fmt(item.updated_at)}
                  </p>
                </div>

                {/* Acciones */}
                <div className="flex gap-2 shrink-0" onClick={(e) => e.stopPropagation()}>
                  <Button size="sm" variant="outline" onClick={() => handleRechazar(item)} data-testid={`archivar-${item.id}`}>
                    <XCircle className="w-4 h-4 mr-1" /> Archivar
                  </Button>
                  <Button size="sm" onClick={() => navigate(`/nuevas-ordenes/${item.id}`)} data-testid={`ver-${item.id}`}>
                    Ver detalle <ArrowRight className="w-4 h-4 ml-1" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

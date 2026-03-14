/**
 * Nuevas Órdenes - Gestión de pre-registros aceptados pendientes de tramitar.
 * El tramitador revisa, añade código de recogida y confirma la creación de la orden.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '@/components/ui/dialog';
import { 
  PackagePlus, RefreshCw, Truck, User, Smartphone, AlertCircle,
  CheckCircle, XCircle, Clock, FileText, ArrowRight
} from 'lucide-react';
import API from '@/lib/api';
import { toast } from 'sonner';

export default function NuevasOrdenes() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState([]);
  const [showTramitar, setShowTramitar] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [tramitarForm, setTramitarForm] = useState({ codigo_recogida: '', agencia_envio: '', notas: '' });
  const [submitting, setSubmitting] = useState(false);
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

  const handleOpenTramitar = (item) => {
    setSelectedItem(item);
    setTramitarForm({
      codigo_recogida: item.codigo_recogida_sugerido || '',
      agencia_envio: '',
      notas: ''
    });
    setShowTramitar(true);
  };

  const handleTramitar = async () => {
    if (!tramitarForm.codigo_recogida.trim()) {
      toast.error('El código de recogida es obligatorio');
      return;
    }
    setSubmitting(true);
    try {
      const res = await API.post(`/nuevas-ordenes/${selectedItem.id}/tramitar`, tramitarForm);
      toast.success(`Orden ${res.data.numero_orden} creada correctamente`);
      setShowTramitar(false);
      cargarDatos();
      // Navigate to the new order
      navigate(`/ordenes/${res.data.orden_id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al tramitar');
    } finally {
      setSubmitting(false);
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
          <Card key={item.id} className="hover:shadow-md transition-shadow" data-testid={`nueva-orden-${item.id}`}>
            <CardContent className="pt-4">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
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
                  
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <User className="w-3.5 h-3.5 flex-shrink-0" />
                      <span className="truncate">{item.cliente_nombre || 'Sin nombre'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Smartphone className="w-3.5 h-3.5 flex-shrink-0" />
                      <span className="truncate">{item.dispositivo_modelo || 'Sin modelo'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <FileText className="w-3.5 h-3.5 flex-shrink-0" />
                      <span className="truncate">{item.daño_descripcion || 'Sin descripción'}</span>
                    </div>
                  </div>
                  
                  {item.cliente_telefono && (
                    <p className="text-xs text-muted-foreground">Tel: {item.cliente_telefono} {item.cliente_email ? `| ${item.cliente_email}` : ''}</p>
                  )}
                  
                  <p className="text-xs text-muted-foreground">
                    Detectado: {fmt(item.updated_at)}
                  </p>
                </div>

                {/* Acciones */}
                <div className="flex gap-2 shrink-0">
                  <Button size="sm" variant="outline" onClick={() => handleRechazar(item)} data-testid={`archivar-${item.id}`}>
                    <XCircle className="w-4 h-4 mr-1" /> Archivar
                  </Button>
                  <Button size="sm" onClick={() => handleOpenTramitar(item)} data-testid={`tramitar-${item.id}`}>
                    <Truck className="w-4 h-4 mr-1" /> Tramitar
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Modal Tramitar */}
      <Dialog open={showTramitar} onOpenChange={setShowTramitar}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Tramitar Orden</DialogTitle>
            <DialogDescription>
              Siniestro: <strong>{selectedItem?.codigo_siniestro}</strong> — {selectedItem?.cliente_nombre}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {/* Resumen */}
            <div className="p-3 bg-muted/50 rounded-lg space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Dispositivo:</span>
                <span className="font-medium">{selectedItem?.dispositivo_modelo}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Daño:</span>
                <span className="font-medium truncate max-w-[200px]">{selectedItem?.daño_descripcion}</span>
              </div>
              {selectedItem?.sumbroker_price && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Importe:</span>
                  <span className="font-bold text-green-600">{parseFloat(selectedItem.sumbroker_price).toFixed(2)}€</span>
                </div>
              )}
            </div>

            {/* Código recogida - OBLIGATORIO */}
            <div>
              <label className="text-sm font-medium mb-1 block">
                Código de Recogida <span className="text-red-500">*</span>
              </label>
              <Input
                placeholder="Ej: GLS-12345678"
                value={tramitarForm.codigo_recogida}
                onChange={(e) => setTramitarForm(prev => ({ ...prev, codigo_recogida: e.target.value }))}
                data-testid="input-codigo-recogida"
              />
            </div>

            {/* Agencia envío */}
            <div>
              <label className="text-sm font-medium mb-1 block">Agencia de envío</label>
              <Input
                placeholder="Ej: GLS, SEUR, MRW..."
                value={tramitarForm.agencia_envio}
                onChange={(e) => setTramitarForm(prev => ({ ...prev, agencia_envio: e.target.value }))}
                data-testid="input-agencia-envio"
              />
            </div>

            {/* Notas */}
            <div>
              <label className="text-sm font-medium mb-1 block">Notas</label>
              <Textarea
                placeholder="Notas adicionales..."
                value={tramitarForm.notas}
                onChange={(e) => setTramitarForm(prev => ({ ...prev, notas: e.target.value }))}
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTramitar(false)}>Cancelar</Button>
            <Button onClick={handleTramitar} disabled={submitting || !tramitarForm.codigo_recogida.trim()} data-testid="confirmar-tramitar-btn">
              {submitting ? <RefreshCw className="w-4 h-4 animate-spin mr-1" /> : <ArrowRight className="w-4 h-4 mr-1" />}
              Crear Orden de Trabajo
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

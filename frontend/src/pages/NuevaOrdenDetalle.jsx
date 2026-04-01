/**
 * NuevaOrdenDetalle - Vista detallada de pre-orden pendiente de tramitar.
 * Muestra todos los datos como una orden de trabajo, permite edición.
 * Al introducir código de recogida y tramitar → se crea la orden real.
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '@/components/ui/dialog';
import {
  ArrowLeft, User, Smartphone, MapPin, Mail, Phone, FileText, Shield,
  Truck, RefreshCw, Save, CheckCircle, XCircle, Clock, CreditCard,
  Hash, Palette, AlertTriangle, ArrowRight, Pencil, Trash2, RotateCw
} from 'lucide-react';
import API from '@/lib/api';
import { toast } from 'sonner';

export default function NuevaOrdenDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [data, setData] = useState(null);
  const [form, setForm] = useState({});
  const [editMode, setEditMode] = useState(false);
  const [showTramitar, setShowTramitar] = useState(false);
  const [tramitarForm, setTramitarForm] = useState({ codigo_recogida: '', agencia_envio: '', notas: '' });
  const [submitting, setSubmitting] = useState(false);
  const [refreshingData, setRefreshingData] = useState(false);

  const cargar = useCallback(async () => {
    setLoading(true);
    try {
      const res = await API.get(`/nuevas-ordenes/${id}`);
      setData(res.data);
      setForm(res.data);
      setTramitarForm(prev => ({
        ...prev,
        codigo_recogida: res.data.codigo_recogida_sugerido || '',
        agencia_envio: res.data.agencia_envio || ''
      }));
    } catch (error) {
      toast.error('Error cargando pre-orden');
      navigate('/nuevas-ordenes');
    } finally {
      setLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => { cargar(); }, [cargar]);

  const handleChange = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handleGuardar = async () => {
    setSaving(true);
    try {
      const res = await API.put(`/nuevas-ordenes/${id}`, form);
      setData(res.data);
      setForm(res.data);
      setEditMode(false);
      toast.success('Datos guardados correctamente');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error guardando');
    } finally {
      setSaving(false);
    }
  };

  const handleTramitar = async () => {
    if (!tramitarForm.codigo_recogida.trim()) {
      toast.error('El código de recogida es obligatorio');
      return;
    }
    setSubmitting(true);
    try {
      const res = await API.post(`/nuevas-ordenes/${id}/tramitar`, tramitarForm);
      toast.success(`Orden ${res.data.numero_orden} creada correctamente`);
      setShowTramitar(false);
      navigate(`/ordenes/${res.data.orden_id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al tramitar');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRechazar = async () => {
    if (!window.confirm('¿Archivar esta pre-orden? No se creará orden de trabajo.')) return;
    try {
      await API.post(`/nuevas-ordenes/${id}/rechazar`);
      toast.success('Pre-orden archivada');
      navigate('/nuevas-ordenes');
    } catch (error) {
      toast.error('Error al archivar');
    }
  };

  const handleEliminar = async () => {
    if (!window.confirm('¿ELIMINAR PERMANENTEMENTE esta pre-orden? Esta acción no se puede deshacer.')) return;
    try {
      await API.delete(`/nuevas-ordenes/${id}`);
      toast.success('Pre-orden eliminada permanentemente');
      navigate('/nuevas-ordenes');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  const handleRefrescarDatos = async () => {
    setRefreshingData(true);
    try {
      const res = await API.post(`/nuevas-ordenes/${id}/refrescar-datos`);
      setData(res.data);
      setForm(res.data);
      toast.success('Datos actualizados desde el portal');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error obteniendo datos del portal');
    } finally {
      setRefreshingData(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <RefreshCw className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  if (!data) return null;

  const fmt = (v) => v ? new Date(v).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-';

  const Field = ({ label, icon: Icon, field, type = 'text', placeholder = '', colSpan = 1 }) => (
    <div className={colSpan === 2 ? 'sm:col-span-2' : ''}>
      <Label className="text-xs text-muted-foreground flex items-center gap-1 mb-1">
        {Icon && <Icon className="w-3 h-3" />} {label}
      </Label>
      {editMode ? (
        type === 'textarea' ? (
          <Textarea
            value={form[field] || ''}
            onChange={(e) => handleChange(field, e.target.value)}
            placeholder={placeholder}
            rows={2}
            className="text-sm"
          />
        ) : (
          <Input
            value={form[field] || ''}
            onChange={(e) => handleChange(field, e.target.value)}
            placeholder={placeholder}
            className="text-sm"
          />
        )
      ) : (
        <p className="text-sm font-medium min-h-[20px]">{data[field] || <span className="text-muted-foreground italic">Sin datos</span>}</p>
      )}
    </div>
  );

  return (
    <div className="space-y-4 max-w-5xl mx-auto" data-testid="nueva-orden-detalle">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate('/nuevas-ordenes')} data-testid="back-btn">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-bold font-mono">{data.codigo_siniestro}</h1>
              <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                <Clock className="w-3 h-3 mr-1" /> Pendiente tramitar
              </Badge>
              {data.sumbroker_price && (
                <Badge variant="secondary" className="font-mono text-sm">
                  {parseFloat(data.sumbroker_price).toFixed(2)}€
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">Detectado: {fmt(data.updated_at)}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleRefrescarDatos} disabled={refreshingData} data-testid="refrescar-datos-btn">
            {refreshingData ? <RotateCw className="w-4 h-4 animate-spin mr-1" /> : <RotateCw className="w-4 h-4 mr-1" />}
            {refreshingData ? 'Obteniendo...' : 'Refrescar datos'}
          </Button>
          {editMode ? (
            <>
              <Button variant="outline" size="sm" onClick={() => { setForm(data); setEditMode(false); }}>
                Cancelar
              </Button>
              <Button size="sm" onClick={handleGuardar} disabled={saving} data-testid="guardar-btn">
                {saving ? <RefreshCw className="w-4 h-4 animate-spin mr-1" /> : <Save className="w-4 h-4 mr-1" />}
                Guardar
              </Button>
            </>
          ) : (
            <Button variant="outline" size="sm" onClick={() => setEditMode(true)} data-testid="editar-btn">
              <Pencil className="w-4 h-4 mr-1" /> Editar datos
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Col 1-2: Datos principales */}
        <div className="lg:col-span-2 space-y-4">
          {/* Cliente */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <User className="w-4 h-4 text-blue-500" /> Datos del Cliente
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Field label="Nombre completo" icon={User} field="cliente_nombre" placeholder="Nombre y apellidos" colSpan={2} />
                <Field label="Email" icon={Mail} field="cliente_email" placeholder="email@ejemplo.com" />
                <Field label="Teléfono" icon={Phone} field="cliente_telefono" placeholder="612345678" />
                <Field label="DNI/NIE" icon={Hash} field="cliente_dni" placeholder="12345678A" />
                <Field label="Dirección" icon={MapPin} field="cliente_direccion" placeholder="Calle, número, piso" colSpan={2} />
                <Field label="Código Postal" icon={MapPin} field="cliente_codigo_postal" placeholder="28001" />
                <Field label="Ciudad" icon={MapPin} field="cliente_ciudad" placeholder="Madrid" />
                <Field label="Provincia" icon={MapPin} field="cliente_provincia" placeholder="Madrid" />
              </div>
            </CardContent>
          </Card>

          {/* Dispositivo */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Smartphone className="w-4 h-4 text-green-500" /> Dispositivo
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Field label="Marca" icon={Smartphone} field="dispositivo_marca" placeholder="Apple, Samsung..." />
                <Field label="Modelo" icon={Smartphone} field="dispositivo_modelo" placeholder="iPhone 15 Pro..." />
                <Field label="Color" icon={Palette} field="dispositivo_color" placeholder="Negro, Blanco..." />
                <Field label="IMEI" icon={Hash} field="dispositivo_imei" placeholder="123456789012345" />
                <Field label="Número de serie" icon={Hash} field="numero_serie" placeholder="Nº serie" />
              </div>
            </CardContent>
          </Card>

          {/* Descripción del daño */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-500" /> Descripción del Daño
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Field label="Descripción" icon={FileText} field="daño_descripcion" type="textarea" placeholder="Descripción detallada del daño..." colSpan={2} />
              <div className="mt-3">
                <Field label="Notas adicionales" icon={FileText} field="notas" type="textarea" placeholder="Notas internas..." colSpan={2} />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Col 3: Seguro, acciones, historial */}
        <div className="space-y-4">
          {/* Seguro */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Shield className="w-4 h-4 text-violet-500" /> Datos del Seguro
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Field label="Código Siniestro" icon={Hash} field="codigo_siniestro" />
              <Field label="Póliza" icon={FileText} field="poliza" />
              <Field label="Compañía" icon={Shield} field="compania" />
              <Field label="Tipo servicio" icon={FileText} field="tipo_servicio" />
              <Field label="Producto" icon={Smartphone} field="producto" />
              <Separator />
              <div>
                <Label className="text-xs text-muted-foreground flex items-center gap-1 mb-1">
                  <CreditCard className="w-3 h-3" /> Importe presupuesto
                </Label>
                <p className="text-lg font-bold text-green-600">
                  {data.sumbroker_price ? `${parseFloat(data.sumbroker_price).toFixed(2)}€` : 'Sin importe'}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Envío sugerido */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Truck className="w-4 h-4 text-orange-500" /> Envío
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Field label="Código recogida sugerido" icon={Hash} field="codigo_recogida_sugerido" placeholder="Código tracking..." />
              <Field label="Agencia de envío" icon={Truck} field="agencia_envio" placeholder="GLS, SEUR, MRW..." />
            </CardContent>
          </Card>

          {/* Acciones */}
          <Card className="border-primary/30">
            <CardContent className="pt-4 space-y-2">
              <Button className="w-full" size="lg" onClick={() => setShowTramitar(true)} data-testid="btn-tramitar">
                <Truck className="w-5 h-5 mr-2" /> Tramitar y crear orden
              </Button>
              <Button variant="outline" className="w-full" onClick={handleRechazar} data-testid="btn-archivar">
                <XCircle className="w-4 h-4 mr-2" /> Archivar
              </Button>
              <Button variant="ghost" className="w-full text-red-600 hover:text-red-700 hover:bg-red-50" onClick={handleEliminar} data-testid="btn-eliminar">
                <Trash2 className="w-4 h-4 mr-2" /> Eliminar permanentemente
              </Button>
            </CardContent>
          </Card>

          {/* Historial */}
          {data.historial && data.historial.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">Historial</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-[200px] overflow-y-auto">
                  {data.historial.map((h, i) => (
                    <div key={i} className="text-xs border-l-2 border-muted pl-2">
                      <p className="font-medium">{h.evento}</p>
                      <p className="text-muted-foreground">{h.detalle}</p>
                      <p className="text-muted-foreground">{fmt(h.fecha)}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Modal Tramitar */}
      <Dialog open={showTramitar} onOpenChange={setShowTramitar}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Crear Orden de Trabajo</DialogTitle>
            <DialogDescription>
              Confirma el código de recogida para crear la orden de trabajo de <strong>{data.codigo_siniestro}</strong>
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="p-3 bg-muted/50 rounded-lg space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Cliente:</span>
                <span className="font-medium">{form.cliente_nombre}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Dispositivo:</span>
                <span className="font-medium">{form.dispositivo_modelo}</span>
              </div>
              {data.sumbroker_price && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Importe:</span>
                  <span className="font-bold text-green-600">{parseFloat(data.sumbroker_price).toFixed(2)}€</span>
                </div>
              )}
            </div>

            <div>
              <Label className="text-sm font-medium mb-1 block">
                Código de Recogida <span className="text-red-500">*</span>
              </Label>
              <Input
                placeholder="Ej: GLS-12345678"
                value={tramitarForm.codigo_recogida}
                onChange={(e) => setTramitarForm(prev => ({ ...prev, codigo_recogida: e.target.value }))}
                data-testid="input-codigo-recogida"
              />
            </div>
            <div>
              <Label className="text-sm font-medium mb-1 block">Agencia de envío</Label>
              <Input
                placeholder="Ej: GLS, SEUR, MRW..."
                value={tramitarForm.agencia_envio}
                onChange={(e) => setTramitarForm(prev => ({ ...prev, agencia_envio: e.target.value }))}
              />
            </div>
            <div>
              <Label className="text-sm font-medium mb-1 block">Notas</Label>
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

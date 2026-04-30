import { useState } from 'react';
import { Truck, Loader2, Download, ExternalLink, User, MapPin, Phone, Mail, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import api from '@/lib/api';

/**
 * Botón "Crear etiqueta GLS" con campos precargados.
 *
 * Precarga automática desde /api/logistica/gls/orden/{order_id}:
 *   - Nombre, dirección completa, CP, población, provincia
 *   - Teléfono, móvil, email
 *   - Peso sugerido 0,5 kg (móviles)
 *   - Referencia = número de OT
 *   - Observaciones (editable, libre)
 *
 * Tras crear:
 *   - Decodifica base64 → abre PDF en pestaña nueva
 *   - Invoca onCreated() para que el padre refresque datos
 */
export default function CrearEtiquetaGLSButton({
  orden, onCreated,
  autoOpen = false,
  variant = 'outline',
  label = 'Crear etiqueta GLS',
}) {
  const [open, setOpen] = useState(Boolean(autoOpen));
  const [prefillLoading, setPrefillLoading] = useState(false);
  const [form, setForm] = useState(null); // todos los campos editables
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const loadPrefill = async () => {
    setPrefillLoading(true);
    try {
      const { data } = await api.get(`/logistica/gls/orden/${orden.id}`);
      setForm({
        dest_nombre: data.destinatario.nombre || '',
        dest_direccion: data.destinatario.direccion || '',
        dest_poblacion: data.destinatario.poblacion || '',
        dest_provincia: data.destinatario.provincia || '',
        dest_cp: data.destinatario.cp || '',
        dest_telefono: data.destinatario.telefono || '',
        dest_movil: data.destinatario.movil || '',
        dest_email: data.destinatario.email || '',
        observaciones: '',
        peso_kg: String(data.peso_kg_sugerido ?? 0.5),
        referencia: data.referencia_sugerida || orden.numero_orden || '',
      });
    } catch (e) {
      toast.error('No se pudo precargar los datos del cliente');
      setForm({
        dest_nombre: '', dest_direccion: '', dest_poblacion: '',
        dest_provincia: '', dest_cp: '', dest_telefono: '',
        dest_movil: '', dest_email: '', observaciones: '',
        peso_kg: '0.5', referencia: orden.numero_orden || '',
      });
    } finally {
      setPrefillLoading(false);
    }
  };

  const handleOpen = async () => {
    setOpen(true);
    setResult(null);
    if (!form) await loadPrefill();
  };

  const upd = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const abrirPdfDesdeBase64 = (b64) => {
    try {
      const bin = atob(b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const url = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
      window.open(url, '_blank', 'noopener,noreferrer');
      return url;
    } catch {
      toast.error('PDF recibido pero no se pudo abrir');
      return null;
    }
  };

  const handleCrear = async (forceDuplicate = false) => {
    const pesoNum = parseFloat(form.peso_kg);
    if (!pesoNum || pesoNum <= 0 || pesoNum > 40) {
      toast.error('Peso inválido (0 < kg ≤ 40)');
      return;
    }
    if (!(form.dest_cp || '').match(/^\d{5}$/)) {
      toast.error('Código postal inválido (5 dígitos)');
      return;
    }
    setLoading(true);
    try {
      const payload = {
        order_id: orden.id,
        peso_kg: pesoNum,
        referencia: form.referencia || undefined,
        observaciones: form.observaciones || undefined,
        dest_nombre: form.dest_nombre,
        dest_direccion: form.dest_direccion,
        dest_poblacion: form.dest_poblacion,
        dest_provincia: form.dest_provincia,
        dest_cp: form.dest_cp,
        dest_telefono: form.dest_telefono,
        dest_movil: form.dest_movil,
        dest_email: form.dest_email,
        force_duplicate: forceDuplicate || undefined,
      };
      const { data } = await api.post('/logistica/gls/crear-envio', payload);
      const pdfUrl = abrirPdfDesdeBase64(data.etiqueta_pdf_base64);
      setResult({
        codbarras: data.codbarras,
        tracking_url: data.tracking_url,
        pdfUrl,
        mock_preview: data.mock_preview,
      });
      toast.success(
        data.mock_preview
          ? `Etiqueta (preview) creada · ${data.codbarras}`
          : `Etiqueta GLS creada · ${data.codbarras}`,
      );
      if (onCreated) onCreated(data);
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      let msg = 'Error desconocido';
      if (typeof detail === 'string') msg = detail;
      else if (detail && typeof detail === 'object') {
        msg = detail.message || detail.msg || JSON.stringify(detail);
      } else if (err?.message) {
        msg = err.message;
      }
      // Si es 409 (duplicado), preguntar al usuario si quiere forzar
      if (status === 409 && !forceDuplicate) {
        if (window.confirm(
          `${msg}\n\n¿Crear igualmente otra etiqueta? (Atención: generará un nuevo envío en GLS)`,
        )) {
          setLoading(false);
          return handleCrear(true);
        }
      } else {
        toast.error(`No se pudo crear la etiqueta: ${msg}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const cerrar = () => {
    setOpen(false);
    setResult(null);
    setForm(null);
  };

  return (
    <>
      <Button
        type="button"
        variant={variant}
        size="sm"
        className="gap-2 border-blue-300 text-blue-700 hover:bg-blue-50"
        onClick={handleOpen}
        data-testid="btn-crear-etiqueta-gls-v2"
      >
        <Truck className="w-4 h-4" />
        {label}
      </Button>

      <Dialog open={open} onOpenChange={(v) => (v ? setOpen(true) : cerrar())}>
        <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto"
                       data-testid="dialog-crear-etiqueta-gls">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Truck className="w-5 h-5 text-blue-600" />
              Crear etiqueta GLS
            </DialogTitle>
            <DialogDescription>
              Orden <span className="font-mono">{orden?.numero_orden || orden?.id}</span>.
              Revisa los datos, ajusta peso u observaciones y confirma.
            </DialogDescription>
          </DialogHeader>

          {prefillLoading || !form ? (
            <div className="py-10 flex items-center justify-center text-muted-foreground">
              <Loader2 className="w-5 h-5 animate-spin mr-2" /> Cargando datos del cliente…
            </div>
          ) : !result ? (
            <div className="space-y-3 py-2">
              {/* Destinatario */}
              <div className="space-y-3 rounded-md border p-3 bg-slate-50">
                <p className="text-xs font-semibold uppercase text-slate-600 flex items-center gap-1">
                  <User className="w-3 h-3" /> Destinatario
                </p>
                <div>
                  <Label htmlFor="gls-nombre" className="text-xs">Nombre</Label>
                  <Input id="gls-nombre" value={form.dest_nombre}
                         onChange={upd('dest_nombre')}
                         data-testid="gls-input-nombre"
                         disabled={loading} />
                </div>
                <div>
                  <Label htmlFor="gls-direccion" className="text-xs flex items-center gap-1">
                    <MapPin className="w-3 h-3" /> Dirección
                  </Label>
                  <Input id="gls-direccion" value={form.dest_direccion}
                         onChange={upd('dest_direccion')}
                         data-testid="gls-input-direccion"
                         disabled={loading} />
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <Label htmlFor="gls-cp" className="text-xs">CP</Label>
                    <Input id="gls-cp" value={form.dest_cp}
                           onChange={upd('dest_cp')} maxLength={5}
                           data-testid="gls-input-cp"
                           disabled={loading} />
                  </div>
                  <div className="col-span-2">
                    <Label htmlFor="gls-pob" className="text-xs">Población</Label>
                    <Input id="gls-pob" value={form.dest_poblacion}
                           onChange={upd('dest_poblacion')}
                           data-testid="gls-input-poblacion"
                           disabled={loading} />
                  </div>
                </div>
                <div>
                  <Label htmlFor="gls-prov" className="text-xs">Provincia</Label>
                  <Input id="gls-prov" value={form.dest_provincia}
                         onChange={upd('dest_provincia')}
                         disabled={loading} />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label htmlFor="gls-tel" className="text-xs flex items-center gap-1">
                      <Phone className="w-3 h-3" /> Teléfono
                    </Label>
                    <Input id="gls-tel" value={form.dest_telefono}
                           onChange={upd('dest_telefono')}
                           disabled={loading} />
                  </div>
                  <div>
                    <Label htmlFor="gls-movil" className="text-xs">Móvil</Label>
                    <Input id="gls-movil" value={form.dest_movil}
                           onChange={upd('dest_movil')}
                           disabled={loading} />
                  </div>
                </div>
                <div>
                  <Label htmlFor="gls-email" className="text-xs flex items-center gap-1">
                    <Mail className="w-3 h-3" /> Email
                  </Label>
                  <Input id="gls-email" type="email" value={form.dest_email}
                         onChange={upd('dest_email')}
                         disabled={loading} />
                </div>
              </div>

              {/* Envío */}
              <div className="space-y-3 rounded-md border p-3">
                <p className="text-xs font-semibold uppercase text-slate-600 flex items-center gap-1">
                  <FileText className="w-3 h-3" /> Envío
                </p>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label htmlFor="gls-peso" className="text-xs">Peso (kg)</Label>
                    <Input id="gls-peso" type="number" min="0.1" max="40" step="0.1"
                           value={form.peso_kg}
                           onChange={upd('peso_kg')}
                           data-testid="gls-input-peso"
                           disabled={loading} />
                  </div>
                  <div>
                    <Label htmlFor="gls-ref" className="text-xs">Referencia</Label>
                    <Input id="gls-ref" value={form.referencia}
                           onChange={upd('referencia')}
                           data-testid="gls-input-referencia"
                           disabled={loading} />
                  </div>
                </div>
                <div>
                  <Label htmlFor="gls-obs" className="text-xs">Observaciones (opcional)</Label>
                  <Textarea id="gls-obs" rows={2} value={form.observaciones}
                            onChange={upd('observaciones')}
                            placeholder="Instrucciones para el transportista…"
                            data-testid="gls-input-observaciones"
                            disabled={loading} />
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-3 py-2" data-testid="result-etiqueta-gls">
              {result.mock_preview && (
                <Badge variant="outline" className="border-amber-400 bg-amber-50 text-amber-800">
                  Preview · etiqueta mock
                </Badge>
              )}
              <div className="rounded-md border bg-slate-50 p-3 space-y-2 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground">Código de barras</span>
                  <span className="font-mono font-semibold" data-testid="result-codbarras">
                    {result.codbarras}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground">Tracking</span>
                  <a href={result.tracking_url} target="_blank" rel="noopener noreferrer"
                     className="inline-flex items-center gap-1 text-blue-600 hover:underline text-xs">
                    Abrir en GLS <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
              {result.pdfUrl && (
                <Button type="button" variant="secondary" className="w-full gap-2"
                        onClick={() => window.open(result.pdfUrl, '_blank', 'noopener,noreferrer')}>
                  <Download className="w-4 h-4" /> Reabrir PDF
                </Button>
              )}
            </div>
          )}

          <DialogFooter>
            {!result ? (
              <>
                <Button variant="ghost" onClick={cerrar} disabled={loading || prefillLoading}>
                  Cancelar
                </Button>
                <Button onClick={handleCrear} disabled={loading || prefillLoading || !form}
                        data-testid="btn-confirmar-crear-etiqueta-gls">
                  {loading ? (
                    <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Creando…</>
                  ) : 'Crear etiqueta'}
                </Button>
              </>
            ) : (
              <Button onClick={cerrar} data-testid="btn-cerrar-etiqueta-gls">Cerrar</Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

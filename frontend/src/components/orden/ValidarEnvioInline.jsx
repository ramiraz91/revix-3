import { useEffect, useState } from 'react';
import { Truck, Loader2, MapPin, User, Phone, Mail, AlertTriangle, Check, Download, SkipForward, PackageCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import api, { ordenesAPI } from '@/lib/api';

/**
 * Flujo inline "Validar y enviar": precarga de datos del cliente + peso editable,
 * genera etiqueta GLS usando el código de autorización como referencia, y marca la
 * orden como ENVIADA en un único paso (sin código de envío manual).
 *
 * props:
 *   orden           — OT actual
 *   onDone(result)  — callback cuando el flujo termina correctamente
 *   onCancel()      — callback para cerrar
 */
export default function ValidarEnvioInline({ orden, onDone, onCancel }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [forzarDuplicado, setForzarDuplicado] = useState(false);

  // Modo "Saltar etiqueta" — el envío ya se hizo de forma manual
  const [modoManual, setModoManual] = useState(false);
  const [manual, setManual] = useState({
    agencia: '',
    codigo_envio: '',
    observaciones: '',
  });

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const { data } = await api.get(`/logistica/gls/orden/${orden.id}`);
        setDetail(data);
        setForm({
          dest_nombre: data.destinatario.nombre,
          dest_direccion: data.destinatario.direccion,
          dest_poblacion: data.destinatario.poblacion,
          dest_provincia: data.destinatario.provincia,
          dest_cp: data.destinatario.cp,
          dest_telefono: data.destinatario.telefono,
          dest_movil: data.destinatario.movil,
          dest_email: data.destinatario.email,
          peso_kg: String(data.peso_kg_sugerido || 0.5),
          observaciones: '',
        });
      } catch {
        toast.error('No se pudieron cargar los datos de la orden');
      } finally {
        setLoading(false);
      }
    })();
  }, [orden.id]);

  const upd = (field) => (e) => setForm((p) => ({ ...p, [field]: e.target.value }));

  const abrirPdf = (b64) => {
    try {
      const bin = atob(b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const url = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
      window.open(url, '_blank', 'noopener,noreferrer');
      return url;
    } catch {
      return null;
    }
  };

  const handleGenerar = async () => {
    if (!detail?.tiene_autorizacion) {
      toast.error('Esta orden no tiene código de autorización de aseguradora. Añádelo antes de generar el envío.');
      return;
    }
    const peso = parseFloat(form.peso_kg);
    if (!peso || peso <= 0 || peso > 40) {
      toast.error('Peso inválido');
      return;
    }
    if (!form.dest_cp || !form.dest_cp.match(/^\d{5}$/)) {
      toast.error('CP inválido (5 dígitos)');
      return;
    }

    setSubmitting(true);
    try {
      // 1) Crear etiqueta GLS (referencia = codigo autorización, lo calcula el backend)
      const { data: envio } = await api.post('/logistica/gls/crear-envio', {
        order_id: orden.id,
        peso_kg: peso,
        observaciones: form.observaciones || undefined,
        force_duplicate: forzarDuplicado,
        require_autorizacion: true,
        dest_nombre: form.dest_nombre,
        dest_direccion: form.dest_direccion,
        dest_poblacion: form.dest_poblacion,
        dest_provincia: form.dest_provincia,
        dest_cp: form.dest_cp,
        dest_telefono: form.dest_telefono,
        dest_movil: form.dest_movil,
        dest_email: form.dest_email,
      });

      // 2) Abrir PDF
      const pdfUrl = abrirPdf(envio.etiqueta_pdf_base64);

      // 3) Marcar orden como ENVIADA
      try {
        await ordenesAPI.cambiarEstado(orden.id, {
          nuevo_estado: 'enviado',
          codigo_envio: envio.codbarras,
          mensaje: `Envío GLS creado · ref ${envio.referencia}`,
          usuario: 'admin',
        });
      } catch (e) {
        // Etiqueta creada pero no cambió estado — informamos, no bloquea.
        console.error('cambiar_estado fallo:', e);
        toast.warning('Etiqueta creada, pero no se pudo cambiar estado automáticamente');
      }

      setResult({ envio, pdfUrl });
      toast.success(`Etiqueta GLS ${envio.codbarras} · orden ENVIADA`);
    } catch (err) {
      const detail_err = err?.response?.data?.detail;
      if (detail_err?.code === 'envio_ya_existe') {
        toast.warning(detail_err.message);
        setForzarDuplicado(true);
        return;
      }
      toast.error(typeof detail_err === 'string' ? detail_err : 'Error al crear el envío');
    } finally {
      setSubmitting(false);
    }
  };

  const updManual = (field) => (e) =>
    setManual((p) => ({ ...p, [field]: e.target.value }));

  const handleSkip = async () => {
    const codigo = (manual.codigo_envio || '').trim();
    const agencia = (manual.agencia || '').trim();
    const obs = (manual.observaciones || '').trim();

    setSubmitting(true);
    try {
      // 1) Si el admin proporciona agencia y/o código manual, los guardamos en la OT
      if (agencia || codigo) {
        const payload = {};
        if (agencia) payload.agencia_envio = agencia;
        if (codigo) payload.codigo_recogida_salida = codigo;
        try {
          await api.patch(`/ordenes/${orden.id}/envio`, payload);
        } catch (e) {
          console.error('No se pudo actualizar agencia/código manual:', e);
        }
      }

      // 2) Marcar como ENVIADA con mensaje claro de "envío manual"
      const mensaje = obs
        ? `Envío manual (sin etiqueta GLS) · ${obs}`
        : 'Envío manual realizado fuera del sistema (sin etiqueta GLS)';

      await ordenesAPI.cambiarEstado(orden.id, {
        nuevo_estado: 'enviado',
        codigo_envio: codigo || undefined,
        mensaje,
        usuario: 'admin',
      });

      setResult({
        manual: true,
        envio: {
          codbarras: codigo || '—',
          referencia: agencia || 'Manual',
          tracking_url: null,
        },
        pdfUrl: null,
      });
      toast.success('Orden marcada como ENVIADA (manual)');
    } catch (err) {
      const detail_err = err?.response?.data?.detail;
      toast.error(
        typeof detail_err === 'string'
          ? detail_err
          : 'No se pudo marcar la orden como enviada'
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !form) {
    return (
      <div className="py-10 flex items-center justify-center text-muted-foreground">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Preparando envío…
      </div>
    );
  }

  // Estado warning: sin autorización (sólo bloquea modo GLS, modo manual sigue disponible)
  const sinAutorizacion = !detail.tiene_autorizacion;

  // Resultado OK
  if (result) {
    return (
      <div className="space-y-3 py-2" data-testid="validar-envio-result">
        <div className="flex items-center gap-2 text-emerald-700">
          <Check className="w-5 h-5" />
          <span className="font-semibold">
            {result.manual ? 'Orden marcada como ENVIADA (manual)' : 'Envío creado y orden enviada'}
          </span>
        </div>
        <div className="rounded-md border bg-slate-50 p-3 space-y-2 text-sm">
          {result.manual ? (
            <>
              <InfoRow label="Modo" value="Manual (sin etiqueta GLS)" />
              {result.envio.codbarras !== '—' && (
                <InfoRow label="Código de envío" value={result.envio.codbarras} mono />
              )}
              {result.envio.referencia !== 'Manual' && (
                <InfoRow label="Agencia" value={result.envio.referencia} />
              )}
            </>
          ) : (
            <>
              <InfoRow label="Código de barras GLS" value={result.envio.codbarras} mono />
              <InfoRow label="Referencia (aseguradora)" value={result.envio.referencia} mono />
              <InfoRow label="Tracking" value={<a href={result.envio.tracking_url} target="_blank" rel="noopener noreferrer"
                        className="text-blue-600 hover:underline">Ver en GLS →</a>} />
            </>
          )}
        </div>
        {result.pdfUrl && (
          <Button type="button" variant="secondary" className="w-full gap-2"
                  onClick={() => window.open(result.pdfUrl, '_blank', 'noopener,noreferrer')}>
            <Download className="w-4 h-4" /> Reabrir PDF etiqueta
          </Button>
        )}
        <Button onClick={() => onDone?.(result)} className="w-full"
                data-testid="validar-envio-cerrar">
          Cerrar
        </Button>
      </div>
    );
  }

  // Formulario precargado
  return (
    <div className="space-y-3" data-testid="validar-envio-inline">
      {/* Selector de modo: GLS automático vs envío manual */}
      <div className="rounded-md border bg-slate-50 p-2 grid grid-cols-2 gap-2"
           data-testid="validar-envio-modo-selector">
        <button
          type="button"
          onClick={() => setModoManual(false)}
          disabled={submitting}
          data-testid="validar-envio-modo-gls"
          className={`px-3 py-2 rounded-md text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
            !modoManual
              ? 'bg-blue-600 text-white shadow-sm'
              : 'bg-white text-slate-700 hover:bg-slate-100 border'
          }`}
        >
          <Truck className="w-4 h-4" />
          Generar etiqueta GLS
        </button>
        <button
          type="button"
          onClick={() => setModoManual(true)}
          disabled={submitting}
          data-testid="validar-envio-modo-manual"
          className={`px-3 py-2 rounded-md text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
            modoManual
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'bg-white text-slate-700 hover:bg-slate-100 border'
          }`}
        >
          <SkipForward className="w-4 h-4" />
          Saltar (envío manual)
        </button>
      </div>

      {modoManual ? (
        <>
          {/* Aviso modo manual */}
          <div className="rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm flex gap-2"
               data-testid="validar-envio-aviso-manual">
            <PackageCheck className="w-4 h-4 text-emerald-700 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-emerald-900">Modo envío manual</p>
              <p className="text-emerald-800 text-xs">
                No se generará etiqueta GLS. La orden pasará a <b>ENVIADA</b> registrando
                que el envío se realizó por fuera del sistema. Los datos de agencia y
                código de seguimiento son opcionales pero recomendados para trazabilidad.
              </p>
            </div>
          </div>

          {/* Formulario manual mínimo */}
          <div className="rounded-md border p-3 space-y-3">
            <p className="text-xs font-semibold uppercase text-slate-600">
              Datos del envío manual (opcional)
            </p>
            <div>
              <Label className="text-xs">Agencia / Transportista</Label>
              <Input
                value={manual.agencia}
                onChange={updManual('agencia')}
                placeholder="Ej. SEUR, Correos, Mensajería local…"
                data-testid="validar-envio-manual-agencia"
              />
            </div>
            <div>
              <Label className="text-xs">Código de seguimiento / albarán</Label>
              <Input
                value={manual.codigo_envio}
                onChange={updManual('codigo_envio')}
                placeholder="Tracking number o número de albarán"
                className="font-mono"
                data-testid="validar-envio-manual-codigo"
              />
            </div>
            <div>
              <Label className="text-xs">Observaciones</Label>
              <Textarea
                rows={2}
                value={manual.observaciones}
                onChange={updManual('observaciones')}
                placeholder="Motivo o detalles del envío manual…"
                data-testid="validar-envio-manual-observaciones"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onCancel} disabled={submitting}>
              Cancelar
            </Button>
            <Button
              onClick={handleSkip}
              disabled={submitting}
              data-testid="validar-envio-confirmar-manual-btn"
              className="gap-2 bg-emerald-600 hover:bg-emerald-700"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Guardando…
                </>
              ) : (
                <>
                  <PackageCheck className="w-4 h-4" /> Marcar como ENVIADA (manual)
                </>
              )}
            </Button>
          </div>
        </>
      ) : (
        <>
      {/* Aviso si la orden no tiene código de autorización (sólo afecta a modo GLS) */}
      {sinAutorizacion && (
        <div className="rounded-md border-2 border-red-300 bg-red-50 p-3 flex gap-2"
             data-testid="validar-envio-sin-auth">
          <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold text-red-900">Sin código de autorización</p>
            <p className="text-red-800 text-xs">
              Esta orden no tiene código de autorización de aseguradora.
              Añádelo en la ficha antes de generar la etiqueta GLS, o utiliza el modo
              <b> envío manual</b> si ya has gestionado el envío por fuera.
            </p>
          </div>
        </div>
      )}

      {/* Alerta si ya hay envío previo */}
      {detail.envios.length > 0 && (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm flex gap-2"
             data-testid="validar-envio-aviso-duplicado">
          <AlertTriangle className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-amber-900">Ya existe un envío para esta orden</p>
            <p className="text-amber-800 text-xs">
              Último codbarras: <span className="font-mono">{detail.envios[detail.envios.length - 1].codbarras}</span>.
              Activa <em>Forzar duplicado</em> para crear otro.
            </p>
            <label className="mt-2 inline-flex items-center gap-2 text-xs text-amber-900">
              <input type="checkbox" checked={forzarDuplicado}
                     onChange={(e) => setForzarDuplicado(e.target.checked)}
                     data-testid="validar-envio-forzar-dup" />
              Forzar duplicado
            </label>
          </div>
        </div>
      )}

      {/* Destinatario precargado */}
      <div className="rounded-md border bg-slate-50 p-3 space-y-3">
        <p className="text-xs font-semibold uppercase text-slate-600 flex items-center gap-1">
          <User className="w-3 h-3" /> Destinatario
        </p>
        <Field id="v-nom" label="Nombre" icon={User} value={form.dest_nombre} onChange={upd('dest_nombre')} />
        <Field id="v-dir" label="Dirección" icon={MapPin} value={form.dest_direccion} onChange={upd('dest_direccion')} />
        <div className="grid grid-cols-3 gap-2">
          <Field id="v-cp" label="CP" value={form.dest_cp} onChange={upd('dest_cp')} maxLength={5} />
          <Field id="v-pob" label="Población" value={form.dest_poblacion} onChange={upd('dest_poblacion')} className="col-span-2" />
        </div>
        <Field id="v-prov" label="Provincia" value={form.dest_provincia} onChange={upd('dest_provincia')} />
        <div className="grid grid-cols-2 gap-2">
          <Field id="v-tel" label="Teléfono" icon={Phone} value={form.dest_telefono} onChange={upd('dest_telefono')} />
          <Field id="v-mov" label="Móvil" value={form.dest_movil} onChange={upd('dest_movil')} />
        </div>
        <Field id="v-email" label="Email" icon={Mail} type="email" value={form.dest_email} onChange={upd('dest_email')} />
      </div>

      {/* Envío */}
      <div className="rounded-md border p-3 space-y-3">
        <p className="text-xs font-semibold uppercase text-slate-600">Envío</p>
        <div>
          <Label className="text-xs">Referencia (código autorización aseguradora)</Label>
          <Input value={detail.referencia_sugerida} readOnly disabled
                 className="font-mono bg-slate-100 cursor-not-allowed"
                 data-testid="validar-envio-referencia" />
          <p className="text-[10px] text-muted-foreground mt-1">
            <Badge variant="outline" className="text-[9px] h-4 mr-1">
              {detail.referencia_fuente === 'autorizacion' ? 'autorización' : 'nº OT'}
            </Badge>
            Este valor no es editable (se usa siempre el código de autorización si existe).
          </p>
        </div>
        <div>
          <Label className="text-xs">Peso (kg) — editable</Label>
          <Input type="number" min="0.1" max="40" step="0.1"
                 value={form.peso_kg} onChange={upd('peso_kg')}
                 data-testid="validar-envio-peso" />
        </div>
        <div>
          <Label className="text-xs">Observaciones (opcional)</Label>
          <Textarea rows={2} value={form.observaciones} onChange={upd('observaciones')}
                    placeholder="Instrucciones para el transportista…"
                    data-testid="validar-envio-observaciones" />
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onCancel} disabled={submitting}>
          Cancelar
        </Button>
        <Button onClick={handleGenerar} disabled={submitting}
                data-testid="validar-envio-generar-btn"
                className="gap-2">
          {submitting
            ? <><Loader2 className="w-4 h-4 animate-spin" /> Generando…</>
            : <><Truck className="w-4 h-4" /> Generar etiqueta GLS</>}
        </Button>
      </div>
        </>
      )}
    </div>
  );
}

function Field({ id, label, icon: Icon, className, ...rest }) {
  return (
    <div className={className}>
      <Label htmlFor={id} className="text-xs flex items-center gap-1">
        {Icon ? <Icon className="w-3 h-3" /> : null}
        {label}
      </Label>
      <Input id={id} {...rest} />
    </div>
  );
}

function InfoRow({ label, value, mono }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className={mono ? 'font-mono font-semibold' : 'font-medium'}>
        {value}
      </span>
    </div>
  );
}

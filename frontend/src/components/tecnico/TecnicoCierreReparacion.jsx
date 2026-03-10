import { useState } from 'react';
import {
  CheckCircle2, AlertTriangle, ClipboardCheck, Loader2,
  Battery, Wifi, Bluetooth, Camera, Mic, Volume2,
  Smartphone, Fingerprint, Signal, ZapIcon
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog';
import { ordenesAPI } from '@/lib/api';
import { toast } from 'sonner';

// ─── Funciones del sistema a verificar (WISE ASC) ────────────────────────────
const FUNCIONES_SISTEMA = [
  { id: 'pantalla_touch',    label: 'Pantalla / Touch',              icon: Smartphone,   required: true  },
  { id: 'wifi',              label: 'WiFi',                          icon: Wifi,          required: true  },
  { id: 'bluetooth',         label: 'Bluetooth',                     icon: Bluetooth,     required: true  },
  { id: 'camara_trasera',    label: 'Cámara trasera',                icon: Camera,        required: true  },
  { id: 'camara_frontal',    label: 'Cámara frontal',                icon: Camera,        required: false },
  { id: 'microfono',         label: 'Micrófono',                     icon: Mic,           required: true  },
  { id: 'altavoz_auricular', label: 'Altavoz / Auricular',           icon: Volume2,       required: true  },
  { id: 'carga',             label: 'Puerto de carga',               icon: ZapIcon,       required: true  },
  { id: 'botones_fisicos',   label: 'Botones físicos',               icon: Smartphone,    required: true  },
  { id: 'sim_red',           label: 'SIM / Red móvil',               icon: Signal,        required: false },
  { id: 'biometria',         label: 'Biometría (Face ID / Touch ID)', icon: Fingerprint,  required: false },
];

const ESTADO_BATERIA_OPS = [
  { value: 'ok',          label: 'OK — Estado óptimo (>80%)' },
  { value: 'degradada',   label: 'Degradada (<80%) — informado al cliente' },
  { value: 'reemplazada', label: 'Reemplazada en esta reparación' },
  { value: 'no_aplica',   label: 'No aplica / No accesible' },
];

export function TecnicoCierreReparacion({ orden, onRefresh }) {
  const [showDialog, setShowDialog] = useState(false);
  const [guardando, setGuardando] = useState(false);

  // ── QC Checks ─────────────────────────────────────────────────────────────
  const [avariaReparada,    setAvariaReparada]    = useState(false);
  const [diagnosticoSalida, setDiagnosticoSalida] = useState(false);
  const [limpieza,          setLimpieza]           = useState(false);

  // ── Batería (WISE ASC) ────────────────────────────────────────────────────
  const [bateriaNivel,   setBateriaNivel]   = useState('');  // porcentaje
  const [bateriaCiclos,  setBateriaCiclos]  = useState('');  // nº ciclos
  const [bateriaEstado,  setBateriaEstado]  = useState('');  // ok | degradada | reemplazada | no_aplica

  // ── Funciones del sistema (grid de checks) ────────────────────────────────
  const [funcionesCheck, setFuncionesCheck] = useState(
    Object.fromEntries(FUNCIONES_SISTEMA.map(f => [f.id, false]))
  );
  const toggleFuncion = (id) =>
    setFuncionesCheck(prev => ({ ...prev, [id]: !prev[id] }));

  // ── Notas ─────────────────────────────────────────────────────────────────
  const [notas, setNotas] = useState('');

  // ── Validaciones previas ──────────────────────────────────────────────────
  const materiales        = orden.materiales || [];
  const matPendientes     = materiales.filter(m => !m.validado_tecnico);
  const hayMatPendientes  = matPendientes.length > 0;
  const cpiCompletado     = Boolean(orden.cpi_opcion);
  const riCompletada      = Boolean(orden.ri_completada);

  // Funciones requeridas marcadas
  const funcRequeridas    = FUNCIONES_SISTEMA.filter(f => f.required);
  const funcReqOK         = funcRequeridas.every(f => funcionesCheck[f.id]);

  const puedeAbrir = !orden.bloqueada
    && Boolean(orden.diagnostico_tecnico)
    && !hayMatPendientes;

  const puedeConfirmar = avariaReparada && diagnosticoSalida && Boolean(bateriaEstado) && funcReqOK;

  // ── Handler cierre ────────────────────────────────────────────────────────
  const handleCerrar = async () => {
    if (!puedeConfirmar) {
      toast.error('Completa todos los checks obligatorios antes de cerrar');
      return;
    }

    const qcPayload = {
      diagnostico_salida_realizado: true,
      funciones_verificadas:        funcReqOK,
      limpieza_realizada:           limpieza,
      bateria_nivel:                bateriaNivel ? parseInt(bateriaNivel) : null,
      bateria_ciclos:               bateriaCiclos ? parseInt(bateriaCiclos) : null,
      bateria_estado:               bateriaEstado,
      qc_funciones:                 funcionesCheck,
      notas_cierre_tecnico:         notas || null,
      fecha_fin_reparacion:         new Date().toISOString(),
    };

    setGuardando(true);
    try {
      // 1. Cambiar estado → reparado
      await ordenesAPI.cambiarEstado(orden.id, {
        nuevo_estado: 'reparado',
        usuario: 'tecnico',
      });
      // 2. Guardar datos de QC
      await ordenesAPI.actualizar(orden.id, qcPayload);

      toast.success('Reparación cerrada — la orden pasa a REPARADO / VALIDACIÓN');
      setShowDialog(false);
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al cerrar la reparación');
    } finally {
      setGuardando(false);
    }
  };

  if (orden.bloqueada || orden.estado !== 'en_taller') return null;

  return (
    <>
      {/* ── Tarjeta resumen de bloqueos ──────────────────────────────────── */}
      <Card className="border-green-200" data-testid="tecnico-cierre-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-green-700">
            <CheckCircle2 className="w-5 h-5" />
            Finalizar Reparación (QC)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">

          {/* Pre-requisitos */}
          <div className="space-y-1.5">
            <PreReqRow ok={Boolean(orden.diagnostico_tecnico)} label="Diagnóstico técnico guardado" required />
            <PreReqRow ok={riCompletada}   label="Inspección de entrada (RI) completada" required />
            <PreReqRow ok={cpiCompletado}  label="Privacidad/CPI registrada" required />
            <PreReqRow ok={!hayMatPendientes} label={hayMatPendientes ? `${matPendientes.length} material(es) pendiente(s) de validar` : 'Materiales validados'} required />
          </div>

          <Button
            className="w-full h-12 bg-green-600 hover:bg-green-700 gap-2"
            onClick={() => setShowDialog(true)}
            disabled={!puedeAbrir}
            data-testid="cerrar-reparacion-btn"
          >
            <ClipboardCheck className="w-5 h-5" />
            {!puedeAbrir ? 'Completa los requisitos previos' : 'Abrir Checklist QC Final'}
          </Button>
        </CardContent>
      </Card>

      {/* ── Dialog QC completo ──────────────────────────────────────────── */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="dialog-qc-final">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-green-700">
              <ClipboardCheck className="w-5 h-5" />
              Control de Calidad Final — ISO 9001 / WISE ASC
            </DialogTitle>
            <DialogDescription>
              {orden?.dispositivo?.modelo} · {orden?.dispositivo?.imei || 'Sin IMEI'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-5 py-2">

            {/* ══ 1. AVERÍA Y DIAGNÓSTICO ══ */}
            <Section title="1. Avería y diagnóstico de salida" required>
              <CheckItem
                id="avaria-reparada"
                checked={avariaReparada}
                onChange={setAvariaReparada}
                label="La avería original ha sido reparada correctamente"
                desc={`Avería: ${orden?.averia_descripcion || orden?.dispositivo?.daños || '(sin descripción)'}`}
                required
                testId="check-avaria-reparada"
              />
              <CheckItem
                id="diagnostico-salida"
                checked={diagnosticoSalida}
                onChange={setDiagnosticoSalida}
                label="He realizado el diagnóstico de salida y verificado la reparación"
                required
                testId="check-diagnostico-salida"
              />
            </Section>

            {/* ══ 2. BATERÍA (WISE ASC) ══ */}
            <Section title="2. Verificación de batería (WISE ASC)" required>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Nivel de batería (%)</Label>
                  <Input
                    type="number"
                    min="0" max="100"
                    value={bateriaNivel}
                    onChange={e => setBateriaNivel(e.target.value)}
                    placeholder="Ej: 87"
                    className="mt-1"
                    data-testid="bateria-nivel-input"
                  />
                </div>
                <div>
                  <Label className="text-xs">Ciclos de carga (si disponible)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={bateriaCiclos}
                    onChange={e => setBateriaCiclos(e.target.value)}
                    placeholder="Ej: 342"
                    className="mt-1"
                    data-testid="bateria-ciclos-input"
                  />
                </div>
              </div>
              <div className="space-y-1 mt-2">
                <Label className="text-xs">Estado de la batería <span className="text-red-500">*</span></Label>
                <div className="grid grid-cols-2 gap-2" data-testid="bateria-estado-options">
                  {ESTADO_BATERIA_OPS.map(op => (
                    <label
                      key={op.value}
                      className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer text-sm transition-colors ${
                        bateriaEstado === op.value
                          ? 'border-green-500 bg-green-50 font-medium'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <input
                        type="radio"
                        name="bateria_estado"
                        value={op.value}
                        checked={bateriaEstado === op.value}
                        onChange={() => setBateriaEstado(op.value)}
                        data-testid={`bateria-estado-${op.value}`}
                      />
                      {op.label}
                    </label>
                  ))}
                </div>
              </div>
            </Section>

            {/* ══ 3. FUNCIONES DEL SISTEMA ══ */}
            <Section title="3. Verificación de funciones del sistema" required>
              <p className="text-xs text-muted-foreground mb-2">
                Marca las funciones verificadas. Las marcadas con <span className="text-red-500">*</span> son obligatorias (WISE ASC).
              </p>
              <div className="grid grid-cols-2 gap-2" data-testid="funciones-sistema-grid">
                {FUNCIONES_SISTEMA.map(f => {
                  const Icon = f.icon;
                  const checked = funcionesCheck[f.id];
                  return (
                    <label
                      key={f.id}
                      className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer text-sm transition-colors ${
                        checked
                          ? 'border-green-500 bg-green-50'
                          : f.required
                            ? 'border-orange-200 bg-orange-50/40'
                            : 'border-gray-200'
                      }`}
                    >
                      <Checkbox
                        checked={checked}
                        onCheckedChange={() => toggleFuncion(f.id)}
                        data-testid={`func-${f.id}`}
                      />
                      <Icon className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
                      <span>{f.label}{f.required && <span className="text-red-500 ml-0.5">*</span>}</span>
                    </label>
                  );
                })}
              </div>
              {!funcReqOK && (
                <p className="text-xs text-orange-600 mt-1">
                  <AlertTriangle className="w-3 h-3 inline mr-1" />
                  Faltan funciones obligatorias por verificar
                </p>
              )}
            </Section>

            {/* ══ 4. ISO/WISE: CPI + RI ══ */}
            <Section title="4. Checklist ISO/WISE" required>
              <PreReqRow ok={riCompletada} label="Inspección de entrada (RI) registrada" required />
              <PreReqRow ok={cpiCompletado} label={
                cpiCompletado
                  ? `CPI/NIST: ${{'cliente_ya_restablecio':'Ya restablecido por cliente','cliente_no_autoriza':'Cliente no autoriza','sat_realizo_restablecimiento':'SAT realizó restablecimiento'}[orden.cpi_opcion] || orden.cpi_opcion}`
                  : 'CPI/NIST — PENDIENTE (ve a la tarjeta CPI arriba)'
              } required />
            </Section>

            {/* ══ 5. LIMPIEZA Y NOTAS ══ */}
            <Section title="5. Acabado y notas">
              <CheckItem
                id="limpieza"
                checked={limpieza}
                onChange={setLimpieza}
                label="Limpieza exterior del dispositivo realizada"
                testId="check-limpieza"
              />
              <div className="mt-2">
                <Label className="text-xs">Notas de cierre técnico (opcional)</Label>
                <Textarea
                  value={notas}
                  onChange={e => setNotas(e.target.value)}
                  placeholder="Observaciones, recomendaciones para el cliente, próximas revisiones..."
                  rows={2}
                  className="mt-1"
                  data-testid="notas-cierre-textarea"
                />
              </div>
            </Section>

          </div>

          {/* Resumen de estado */}
          {!puedeConfirmar && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
              <AlertTriangle className="w-4 h-4 inline mr-1" />
              Completa los campos obligatorios: avería reparada, diagnóstico de salida, estado de batería y funciones requeridas.
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2 border-t">
            <Button variant="outline" onClick={() => setShowDialog(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleCerrar}
              disabled={guardando || !puedeConfirmar}
              className="bg-green-600 hover:bg-green-700 gap-2"
              data-testid="btn-confirmar-cierre"
            >
              {guardando
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <CheckCircle2 className="w-4 h-4" />}
              Cerrar Reparación — Marcar como REPARADO
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function Section({ title, children, required }) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-slate-700 border-b pb-1">
        {title}
        {required && <span className="text-red-500 ml-1 text-xs">(obligatorio)</span>}
      </h3>
      {children}
    </div>
  );
}

function CheckItem({ id, checked, onChange, label, desc, required, testId }) {
  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border ${
      checked ? 'border-green-400 bg-green-50' : required ? 'border-orange-200 bg-orange-50/30' : 'border-gray-200'
    }`}>
      <Checkbox
        id={id}
        checked={checked}
        onCheckedChange={onChange}
        data-testid={testId}
        className="mt-0.5"
      />
      <div>
        <label htmlFor={id} className="text-sm font-medium cursor-pointer">
          {label}{required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
        {desc && <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>}
      </div>
    </div>
  );
}

function PreReqRow({ ok, label, required }) {
  return (
    <div className={`flex items-center gap-2 text-sm px-2 py-1 rounded ${
      ok ? 'text-green-700' : required ? 'text-orange-600' : 'text-gray-500'
    }`}>
      {ok
        ? <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
        : <AlertTriangle className="w-4 h-4 flex-shrink-0" />}
      {label}
    </div>
  );
}

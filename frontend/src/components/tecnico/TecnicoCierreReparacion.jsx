import { useState } from 'react';
import {
  CheckCircle2, AlertTriangle, ClipboardCheck, Loader2,
  Battery, Wifi, Bluetooth, Camera, Mic, Volume2,
  Smartphone, Fingerprint, Signal, ZapIcon, Shield
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
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
  // Resultado de la avería: 'reparada' | 'parcial' | 'no_reparada'
  const [resultadoAveria,   setResultadoAveria]   = useState('reparada');
  const [motivoNoReparada,  setMotivoNoReparada]  = useState('');
  const [diagnosticoSalida, setDiagnosticoSalida] = useState(false);
  const [limpieza,          setLimpieza]           = useState(false);

  // ── Tipo de dispositivo ───────────────────────────────────────────────────
  // Si el dispositivo NO es smartphone (consola, TV, otros) la batería y
  // las funciones de smartphone no aplican. El técnico puede marcarlo aquí.
  const [esSmartphone, setEsSmartphone] = useState(true);

  const averiaNoReparada = resultadoAveria === 'no_reparada';

  // ── Batería (WISE ASC) ────────────────────────────────────────────────────
  const [bateriaNivel,   setBateriaNivel]   = useState('');  // porcentaje
  const [bateriaCiclos,  setBateriaCiclos]  = useState('');  // nº ciclos
  const [bateriaEstado,  setBateriaEstado]  = useState('');  // ok | degradada | reemplazada | no_aplica

  // ── Funciones del sistema (grid de checks) ────────────────────────────────
  // Si funcionesNoAplica → omitir validación (consolas, TVs, otros).
  const [funcionesNoAplica, setFuncionesNoAplica] = useState(false);
  const [funcionesCheck, setFuncionesCheck] = useState(
    Object.fromEntries(FUNCIONES_SISTEMA.map(f => [f.id, false]))
  );
  const toggleFuncion = (id) =>
    setFuncionesCheck(prev => ({ ...prev, [id]: !prev[id] }));
  const marcarTodasFunciones = () =>
    setFuncionesCheck(Object.fromEntries(FUNCIONES_SISTEMA.map(f => [f.id, true])));
  const desmarcarTodasFunciones = () =>
    setFuncionesCheck(Object.fromEntries(FUNCIONES_SISTEMA.map(f => [f.id, false])));
  const marcarSoloRequeridas = () =>
    setFuncionesCheck(Object.fromEntries(FUNCIONES_SISTEMA.map(f => [f.id, f.required])));

  // ── Notas ─────────────────────────────────────────────────────────────────
  const [notas, setNotas] = useState('');

  // ── Garantía ──────────────────────────────────────────────────────────────
  const esGarantia = orden?.es_garantia === true;
  const [resultadoGarantia, setResultadoGarantia] = useState('procede'); // procede | no_procede
  const [motivoNoGarantia, setMotivoNoGarantia] = useState('');

  // ── Validaciones previas ──────────────────────────────────────────────────
  const materiales        = orden.materiales || [];
  const matPendientes     = materiales.filter(m => !m.validado_tecnico);
  const hayMatPendientes  = matPendientes.length > 0;
  const cpiCompletado     = Boolean(orden.cpi_opcion);
  const riCompletada      = Boolean(orden.ri_completada);

  // Funciones requeridas marcadas
  const funcRequeridas    = FUNCIONES_SISTEMA.filter(f => f.required);
  const funcReqOK         = funcionesNoAplica || !esSmartphone || funcRequeridas.every(f => funcionesCheck[f.id]);
  // Batería se omite si no es smartphone (consola/TV) o si el tecnico marca no_aplica
  const bateriaOK         = !esSmartphone || Boolean(bateriaEstado);

  const puedeAbrir = !orden.bloqueada
    && Boolean(orden.diagnostico_tecnico)
    && !hayMatPendientes;

  // Si es garantía y no procede, no requiere los checks normales
  const garantiaNoProcede = esGarantia && resultadoGarantia === 'no_procede';
  const puedeConfirmar = (() => {
    if (garantiaNoProcede) return Boolean(motivoNoGarantia?.trim());
    if (averiaNoReparada)  return Boolean(motivoNoReparada?.trim());
    // Reparada o parcial: exigir QC normal
    return diagnosticoSalida && bateriaOK && funcReqOK;
  })();

  // ── Handler cierre ────────────────────────────────────────────────────────
  const handleCerrar = async () => {
    if (!puedeConfirmar) {
      toast.error('Completa todos los checks obligatorios antes de cerrar');
      return;
    }

    // Payload base
    const qcPayload = {
      notas_cierre_tecnico:         notas || null,
      fecha_fin_reparacion:         new Date().toISOString(),
      qc_es_smartphone:             esSmartphone,
    };

    // Si es garantía que no procede, guardar motivo y saltar QC
    if (garantiaNoProcede) {
      qcPayload.garantia_resultado = 'no_procede';
      qcPayload.garantia_motivo_no_procede = motivoNoGarantia.trim();
      qcPayload.garantia_tests_omitidos = true;
    } else if (averiaNoReparada) {
      // Avería NO reparada → orden va a IRREPARABLE
      qcPayload.diagnostico_salida_realizado = true;
      qcPayload.funciones_verificadas = false;
      qcPayload.qc_resultado_averia = 'no_reparada';
      qcPayload.qc_motivo_no_reparada = motivoNoReparada.trim();
    } else {
      // QC normal (reparada total o parcialmente)
      qcPayload.diagnostico_salida_realizado = true;
      qcPayload.funciones_verificadas = funcReqOK;
      qcPayload.qc_resultado_averia = resultadoAveria;  // 'reparada' | 'parcial'
      qcPayload.qc_funciones_no_aplica = funcionesNoAplica;
      qcPayload.limpieza_realizada = limpieza;
      qcPayload.bateria_nivel = bateriaNivel ? parseInt(bateriaNivel) : null;
      qcPayload.bateria_ciclos = bateriaCiclos ? parseInt(bateriaCiclos) : null;
      qcPayload.bateria_estado = bateriaEstado || (esSmartphone ? null : 'no_aplica');
      qcPayload.qc_funciones = funcionesCheck;

      // Si es garantía que SÍ procede
      if (esGarantia) {
        qcPayload.garantia_resultado = 'procede';
      }
    }

    // Estado destino:
    // - garantía no procede → reparado (cerrada, no procede)
    // - avería no reparada → irreparable
    // - resto → reparado
    const estadoDestino = averiaNoReparada ? 'irreparable' : 'reparado';

    setGuardando(true);
    try {
      const mensajeCambio = (() => {
        if (garantiaNoProcede) return `GARANTÍA NO PROCEDE: ${motivoNoGarantia.trim()}`;
        if (averiaNoReparada)  return `AVERÍA NO REPARADA: ${motivoNoReparada.trim()}`;
        if (resultadoAveria === 'parcial') return `Reparación PARCIAL: ${notas?.trim() || 'Algunas funciones siguen sin operar al 100%'}`;
        return notas?.trim() || 'Reparación completada - QC verificado';
      })();

      await ordenesAPI.cambiarEstado(orden.id, {
        nuevo_estado: estadoDestino,
        usuario: 'tecnico',
        mensaje: mensajeCambio,
      });
      // 2. Guardar datos de QC
      await ordenesAPI.actualizar(orden.id, qcPayload);

      const okMsg = (() => {
        if (garantiaNoProcede) return 'Orden cerrada — Garantía NO PROCEDE';
        if (averiaNoReparada)  return 'Orden marcada como IRREPARABLE — admin gestionará la devolución';
        return 'Reparación cerrada — la orden pasa a REPARADO / VALIDACIÓN';
      })();
      toast.success(okMsg);
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

            {/* ══ 0. SECCIÓN DE GARANTÍA (solo si es_garantia) ══ */}
            {esGarantia && (
              <div className="p-4 bg-amber-50 border-2 border-amber-300 rounded-lg space-y-3">
                <div className="flex items-center gap-2 text-amber-700 font-semibold">
                  <Shield className="w-5 h-5" />
                  Esta es una orden de GARANTÍA
                </div>
                
                {orden?.indicaciones_garantia_cliente && (
                  <div className="p-2 bg-white rounded border border-amber-200">
                    <p className="text-xs text-amber-600 font-medium">Avería reportada por el cliente:</p>
                    <p className="text-sm whitespace-pre-wrap">{orden.indicaciones_garantia_cliente}</p>
                  </div>
                )}

                {orden?.indicaciones_admin_garantia && (
                  <div className="p-2 bg-blue-50 rounded border border-blue-300" data-testid="tecnico-indicaciones-admin-garantia">
                    <p className="text-xs text-blue-700 font-semibold">Observaciones del admin (recepción):</p>
                    <p className="text-sm whitespace-pre-wrap">{orden.indicaciones_admin_garantia}</p>
                  </div>
                )}
                
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Resultado de la garantía:</Label>
                  <RadioGroup 
                    value={resultadoGarantia} 
                    onValueChange={setResultadoGarantia}
                    className="space-y-2"
                  >
                    <div className="flex items-center space-x-2 p-3 bg-white rounded border hover:border-green-400 transition-colors">
                      <RadioGroupItem value="procede" id="garantia-procede" />
                      <Label htmlFor="garantia-procede" className="cursor-pointer flex-1">
                        <span className="font-medium text-green-700">✅ Garantía PROCEDE</span>
                        <p className="text-xs text-muted-foreground">La avería está cubierta y será reparada bajo garantía</p>
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2 p-3 bg-white rounded border hover:border-red-400 transition-colors">
                      <RadioGroupItem value="no_procede" id="garantia-no-procede" />
                      <Label htmlFor="garantia-no-procede" className="cursor-pointer flex-1">
                        <span className="font-medium text-red-700">❌ Garantía NO PROCEDE</span>
                        <p className="text-xs text-muted-foreground">La avería NO está cubierta (daño externo, mal uso, etc.)</p>
                      </Label>
                    </div>
                  </RadioGroup>
                </div>

                {garantiaNoProcede && (
                  <div className="space-y-2 pt-2 border-t border-amber-200">
                    <Label className="flex items-center gap-1 text-red-700 font-medium">
                      <AlertTriangle className="w-4 h-4" />
                      Motivo de no garantía *
                    </Label>
                    <Textarea
                      value={motivoNoGarantia}
                      onChange={(e) => setMotivoNoGarantia(e.target.value)}
                      placeholder="Ej: Daño por líquido detectado en placa, golpe en esquina con fractura de chasis, manipulación por terceros no autorizados..."
                      rows={3}
                      className="bg-white"
                    />
                    <p className="text-xs text-amber-700">
                      ⚠️ Este motivo aparecerá en el PDF de la orden. Los tests de QC se omitirán.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* ══ 1. AVERÍA Y DIAGNÓSTICO ══ (ocultar si garantía no procede) */}
            {!garantiaNoProcede && (
            <Section title="1. Avería y diagnóstico de salida" required>
              <div className="space-y-2">
                <Label className="text-xs font-medium">Resultado de la reparación <span className="text-red-500">*</span></Label>
                <RadioGroup value={resultadoAveria} onValueChange={setResultadoAveria} className="space-y-1.5">
                  <label className={`flex items-start gap-2 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                    resultadoAveria === 'reparada' ? 'border-green-500 bg-green-50' : 'border-gray-200 hover:border-gray-300'
                  }`}>
                    <RadioGroupItem value="reparada" id="averia-reparada" className="mt-0.5" data-testid="radio-averia-reparada" />
                    <div className="text-sm">
                      <span className="font-medium text-green-700">✅ Avería reparada correctamente</span>
                      <p className="text-xs text-muted-foreground mt-0.5">El dispositivo funciona como debería</p>
                    </div>
                  </label>
                  <label className={`flex items-start gap-2 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                    resultadoAveria === 'parcial' ? 'border-amber-500 bg-amber-50' : 'border-gray-200 hover:border-gray-300'
                  }`}>
                    <RadioGroupItem value="parcial" id="averia-parcial" className="mt-0.5" data-testid="radio-averia-parcial" />
                    <div className="text-sm">
                      <span className="font-medium text-amber-700">⚠️ Reparada parcialmente</span>
                      <p className="text-xs text-muted-foreground mt-0.5">Funciona pero con limitaciones (anota cuáles en notas)</p>
                    </div>
                  </label>
                  <label className={`flex items-start gap-2 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                    resultadoAveria === 'no_reparada' ? 'border-red-500 bg-red-50' : 'border-gray-200 hover:border-gray-300'
                  }`}>
                    <RadioGroupItem value="no_reparada" id="averia-no-reparada" className="mt-0.5" data-testid="radio-averia-no-reparada" />
                    <div className="text-sm">
                      <span className="font-medium text-red-700">❌ La avería NO ha sido reparada</span>
                      <p className="text-xs text-muted-foreground mt-0.5">Dispositivo irreparable o reparación no viable. La orden pasará a IRREPARABLE.</p>
                    </div>
                  </label>
                </RadioGroup>

                <p className="text-xs text-muted-foreground italic mt-2">
                  Avería original: {orden?.averia_descripcion || orden?.dispositivo?.daños || '(sin descripción)'}
                </p>

                {averiaNoReparada && (
                  <div className="space-y-1.5 pt-2 border-t border-red-200">
                    <Label className="flex items-center gap-1 text-red-700 font-medium text-sm">
                      <AlertTriangle className="w-4 h-4" />
                      Motivo por el que no se ha podido reparar *
                    </Label>
                    <Textarea
                      value={motivoNoReparada}
                      onChange={(e) => setMotivoNoReparada(e.target.value)}
                      placeholder="Ej: placa base con corrosión avanzada, no hay disponibilidad del repuesto compatible, daño irreversible en chip de gestión..."
                      rows={3}
                      className="bg-white"
                      data-testid="textarea-motivo-no-reparada"
                    />
                    <p className="text-xs text-amber-700">
                      ⚠️ El motivo aparecerá en el PDF y se notificará al cliente. Las secciones de QC se omitirán.
                    </p>
                  </div>
                )}
              </div>

              {!averiaNoReparada && (
                <CheckItem
                  id="diagnostico-salida"
                  checked={diagnosticoSalida}
                  onChange={setDiagnosticoSalida}
                  label="He realizado el diagnóstico de salida y verificado la reparación"
                  required
                  testId="check-diagnostico-salida"
                />
              )}

              {!averiaNoReparada && (
                <div className="flex items-center gap-2 p-2 mt-2 rounded-md bg-slate-50 border border-slate-200">
                  <Checkbox
                    id="es-smartphone"
                    checked={esSmartphone}
                    onCheckedChange={(c) => setEsSmartphone(Boolean(c))}
                    data-testid="check-es-smartphone"
                  />
                  <Label htmlFor="es-smartphone" className="text-xs cursor-pointer flex-1">
                    El dispositivo <strong>es un smartphone/tablet</strong> (verificar batería y funciones).
                    <br />
                    <span className="text-muted-foreground">Desmarca para consolas, TVs, portátiles u otros aparatos electrónicos.</span>
                  </Label>
                </div>
              )}
            </Section>
            )}

            {/* Secciones de QC - ocultar si garantía no procede O si avería no reparada */}
            {!garantiaNoProcede && !averiaNoReparada && (
            <>
            {/* Sección 2 (batería) y 3 (funciones) son específicas de smartphone */}
            {esSmartphone && (
            <>
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
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <p className="text-xs text-muted-foreground">
                  Marca las funciones verificadas. Las marcadas con <span className="text-red-500">*</span> son obligatorias (WISE ASC).
                </p>
                <div className="flex gap-1.5">
                  <Button
                    type="button" variant="outline" size="sm"
                    className="h-7 text-xs px-2"
                    onClick={marcarTodasFunciones}
                    disabled={funcionesNoAplica}
                    data-testid="btn-marcar-todas-funciones"
                  >
                    ✓ Marcar todas
                  </Button>
                  <Button
                    type="button" variant="outline" size="sm"
                    className="h-7 text-xs px-2"
                    onClick={marcarSoloRequeridas}
                    disabled={funcionesNoAplica}
                    data-testid="btn-marcar-requeridas"
                  >
                    Sólo requeridas
                  </Button>
                  <Button
                    type="button" variant="ghost" size="sm"
                    className="h-7 text-xs px-2 text-slate-500"
                    onClick={desmarcarTodasFunciones}
                    disabled={funcionesNoAplica}
                    data-testid="btn-desmarcar-todas-funciones"
                  >
                    Limpiar
                  </Button>
                </div>
              </div>

              <div className="flex items-center gap-2 p-2 mb-2 rounded-md bg-slate-50 border border-slate-200">
                <Checkbox
                  id="funciones-no-aplica"
                  checked={funcionesNoAplica}
                  onCheckedChange={(c) => setFuncionesNoAplica(Boolean(c))}
                  data-testid="check-funciones-no-aplica"
                />
                <Label htmlFor="funciones-no-aplica" className="text-xs cursor-pointer flex-1">
                  <strong>No aplica</strong> — el dispositivo no tiene estas funciones (consola, TV, periférico, …)
                </Label>
              </div>

              <div
                className={`grid grid-cols-2 gap-2 ${funcionesNoAplica ? 'opacity-40 pointer-events-none' : ''}`}
                data-testid="funciones-sistema-grid"
              >
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
              {!funcReqOK && !funcionesNoAplica && (
                <p className="text-xs text-orange-600 mt-1">
                  <AlertTriangle className="w-3 h-3 inline mr-1" />
                  Faltan funciones obligatorias por verificar
                </p>
              )}
              {funcionesNoAplica && (
                <p className="text-xs text-slate-500 italic mt-1">
                  Verificación de funciones marcada como <strong>no aplica</strong> para este tipo de dispositivo.
                </p>
              )}
            </Section>
            </>
            )}

            {/* ══ 4. ISO/WISE: CPI + RI ══ (aplica a todos los dispositivos) */}
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
            </Section>
            </>
            )}

            {/* Notas - siempre visible */}
            <Section title={garantiaNoProcede ? "Notas adicionales" : "6. Notas adicionales"}>
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
              {garantiaNoProcede
                ? 'Indica el motivo por el que la garantía no procede.'
                : averiaNoReparada
                  ? 'Indica el motivo por el que no se ha podido reparar la avería.'
                  : 'Completa los campos obligatorios: diagnóstico de salida' +
                    (esSmartphone ? ', estado de batería y funciones requeridas' : '') + '.'}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2 border-t">
            <Button variant="outline" onClick={() => setShowDialog(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleCerrar}
              disabled={guardando || !puedeConfirmar}
              className={`gap-2 ${averiaNoReparada
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-green-600 hover:bg-green-700'}`}
              data-testid="btn-confirmar-cierre"
            >
              {guardando
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <CheckCircle2 className="w-4 h-4" />}
              {averiaNoReparada
                ? 'Cerrar como IRREPARABLE'
                : 'Cerrar Reparación — Marcar como REPARADO'}
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

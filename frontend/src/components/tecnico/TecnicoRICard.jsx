import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { CheckCircle2, AlertTriangle, XCircle, ShieldCheck, Info, ClipboardCheck, Smartphone, Package, Loader2 } from 'lucide-react';
import { ordenesAPI } from '@/lib/api';
import { toast } from 'sonner';

export function TecnicoRICard({ orden, onRefresh }) {
  const [registrando, setRegistrando] = useState(false);
  const [mostrarInfo, setMostrarInfo] = useState(false);

  // Estado local con updates optimistas
  const [checklistCompleto, setChecklistCompleto] = useState(orden?.recepcion_checklist_completo || false);
  const [estadoFisicoRegistrado, setEstadoFisicoRegistrado] = useState(orden?.recepcion_estado_fisico_registrado || false);
  const [accesoriosRegistrados, setAccesoriosRegistrados] = useState(orden?.recepcion_accesorios_registrados || false);
  const [observaciones, setObservaciones] = useState(orden?.recepcion_notas || orden?.ri_observaciones || '');
  const [diagnosticoRecepcion, setDiagnosticoRecepcion] = useState(orden?.diagnostico_recepcion || '');
  const [savingField, setSavingField] = useState(null); // indicador discreto qué campo se está guardando

  // Sincronizar cuando llega una orden nueva (id distinto) — NO sobreescribir cambios pendientes
  const lastOrdenId = useRef(orden?.id);
  useEffect(() => {
    if (orden?.id !== lastOrdenId.current) {
      lastOrdenId.current = orden?.id;
      setChecklistCompleto(orden?.recepcion_checklist_completo || false);
      setEstadoFisicoRegistrado(orden?.recepcion_estado_fisico_registrado || false);
      setAccesoriosRegistrados(orden?.recepcion_accesorios_registrados || false);
      setObservaciones(orden?.recepcion_notas || orden?.ri_observaciones || '');
      setDiagnosticoRecepcion(orden?.diagnostico_recepcion || '');
    }
  }, [orden?.id, orden?.recepcion_checklist_completo, orden?.recepcion_estado_fisico_registrado, orden?.recepcion_accesorios_registrados, orden?.recepcion_notas, orden?.ri_observaciones, orden?.diagnostico_recepcion]);

  // Persiste un campo en background SIN bloquear la UI ni recargar la orden
  const persistirCampo = async (campo, valor) => {
    setSavingField(campo);
    try {
      await ordenesAPI.actualizar(orden.id, { [campo]: valor });
    } catch (err) {
      toast.error('No se pudo guardar el cambio. Reintenta.');
      // Revertir si falla
      if (campo === 'recepcion_checklist_completo') setChecklistCompleto((prev) => !prev);
      else if (campo === 'recepcion_estado_fisico_registrado') setEstadoFisicoRegistrado((prev) => !prev);
      else if (campo === 'recepcion_accesorios_registrados') setAccesoriosRegistrados((prev) => !prev);
    } finally {
      setSavingField(null);
    }
  };

  // Toggle de checks: actualiza estado local INMEDIATAMENTE y persiste en background
  const toggleCheck = (campo, setter, valorActual) => {
    const nuevo = !valorActual;
    setter(nuevo);
    persistirCampo(campo, nuevo);
  };

  // Debounce para guardar observaciones al dejar de escribir
  const obsTimeout = useRef(null);
  const handleObservacionesChange = (val) => {
    setObservaciones(val);
    if (obsTimeout.current) clearTimeout(obsTimeout.current);
    obsTimeout.current = setTimeout(() => {
      persistirCampo('recepcion_notas', val);
    }, 800);
  };

  // Debounce para guardar diagnóstico de recepción
  const diagRecTimeout = useRef(null);
  const handleDiagnosticoRecepcionChange = (val) => {
    setDiagnosticoRecepcion(val);
    if (diagRecTimeout.current) clearTimeout(diagRecTimeout.current);
    diagRecTimeout.current = setTimeout(() => {
      persistirCampo('diagnostico_recepcion', val);
    }, 800);
  };

  const handleRI = async (resultado) => {
    setRegistrando(true);
    try {
      const fotos = (orden?.evidencias || []).slice(0, 3);
      const fotosPadded = fotos.length >= 3
        ? fotos
        : [...fotos, ...Array(3 - fotos.length).fill('sin_foto')];

      await ordenesAPI.registrarReceivingInspection(orden.id, {
        resultado_ri: resultado,
        checklist_visual: {
          inspeccion_visual: true,
          checklist_completo: checklistCompleto,
          estado_fisico: estadoFisicoRegistrado,
          accesorios: accesoriosRegistrados,
        },
        fotos_recepcion: fotosPadded,
        observaciones: observaciones,
      });

      // Persistir checklist final + observaciones (una sola llamada)
      await ordenesAPI.actualizar(orden.id, {
        recepcion_checklist_completo: checklistCompleto,
        recepcion_estado_fisico_registrado: estadoFisicoRegistrado,
        recepcion_accesorios_registrados: accesoriosRegistrados,
        recepcion_notas: observaciones || null,
      });

      if (resultado === 'ok') toast.success('RI OK — Reparación iniciada automáticamente');
      else if (resultado === 'sospechoso') toast.warning('RI Sospechoso — Orden en cuarentena para revisión');
      else toast.error('RI No Conforme — Orden en cuarentena');

      onRefresh?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al registrar RI');
    } finally {
      setRegistrando(false);
    }
  };

  const riCompletada = Boolean(orden?.ri_completada);
  const riResultado = orden?.ri_resultado;
  const todosLosChequeosCompletos = checklistCompleto && estadoFisicoRegistrado && accesoriosRegistrados;

  return (
    <Card data-testid="tecnico-ri-card">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <ShieldCheck className="w-4 h-4" />
          Inspección de Entrada (RI)
          {riCompletada && (
            <Badge variant={riResultado === 'ok' ? 'success' : riResultado === 'no_conforme' ? 'destructive' : 'warning'}>
              {riResultado?.toUpperCase()}
            </Badge>
          )}
          {savingField && (
            <span className="ml-2 inline-flex items-center gap-1 text-[10px] text-muted-foreground">
              <Loader2 className="w-3 h-3 animate-spin" /> guardando…
            </span>
          )}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="ml-auto h-6 w-6 p-0"
            onClick={() => setMostrarInfo(!mostrarInfo)}
          >
            <Info className="w-4 h-4 text-blue-500" />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {mostrarInfo && (
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs space-y-2">
            <p className="font-semibold text-blue-800">¿Cuándo usar cada opción?</p>
            <div className="space-y-1.5">
              <p className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-green-600 mt-0.5 flex-shrink-0" />
                <span><strong>RI OK:</strong> El dispositivo llega en las condiciones esperadas. Sin daños adicionales, IMEI coincide, accesorios correctos. <em className="text-green-700">→ Inicia reparación automáticamente</em></span>
              </p>
              <p className="flex items-start gap-2">
                <AlertTriangle className="w-3.5 h-3.5 text-yellow-500 mt-0.5 flex-shrink-0" />
                <span><strong>RI Sospechoso:</strong> Hay algo que no cuadra pero no es grave. Ej: golpes menores no declarados, falta un accesorio, embalaje dañado. <em className="text-yellow-700">→ Cuarentena para revisión</em></span>
              </p>
              <p className="flex items-start gap-2">
                <XCircle className="w-3.5 h-3.5 text-red-500 mt-0.5 flex-shrink-0" />
                <span><strong>RI No Conforme:</strong> Problema grave. Ej: IMEI no coincide, dispositivo diferente al declarado, daños severos ocultos, posible fraude. <em className="text-red-700">→ Cuarentena obligatoria</em></span>
              </p>
            </div>
          </div>
        )}

        {/* Checklist (siempre editable, incluso después de completar el RI) */}
        <div className="p-3 bg-slate-50 rounded-lg border space-y-3">
          <p className="text-sm font-semibold flex items-center gap-2">
            <ClipboardCheck className="w-4 h-4 text-blue-600" />
            Checklist de Recepción
          </p>
          <div className="grid grid-cols-1 gap-3">
            <label
              htmlFor="checklist-completo"
              className="flex items-center gap-3 p-2 bg-white rounded border cursor-pointer hover:bg-slate-50"
            >
              <Checkbox
                id="checklist-completo"
                checked={checklistCompleto}
                onCheckedChange={() => toggleCheck('recepcion_checklist_completo', setChecklistCompleto, checklistCompleto)}
                data-testid="ri-checklist-completo"
              />
              <span className="flex items-center gap-2 text-sm">
                <ClipboardCheck className="w-4 h-4 text-slate-500" />
                Checklist de recepción completo
              </span>
            </label>
            <label
              htmlFor="estado-fisico"
              className="flex items-center gap-3 p-2 bg-white rounded border cursor-pointer hover:bg-slate-50"
            >
              <Checkbox
                id="estado-fisico"
                checked={estadoFisicoRegistrado}
                onCheckedChange={() => toggleCheck('recepcion_estado_fisico_registrado', setEstadoFisicoRegistrado, estadoFisicoRegistrado)}
                data-testid="ri-estado-fisico"
              />
              <span className="flex items-center gap-2 text-sm">
                <Smartphone className="w-4 h-4 text-slate-500" />
                Estado físico registrado (fotos, golpes, rayones)
              </span>
            </label>
            <label
              htmlFor="accesorios"
              className="flex items-center gap-3 p-2 bg-white rounded border cursor-pointer hover:bg-slate-50"
            >
              <Checkbox
                id="accesorios"
                checked={accesoriosRegistrados}
                onCheckedChange={() => toggleCheck('recepcion_accesorios_registrados', setAccesoriosRegistrados, accesoriosRegistrados)}
                data-testid="ri-accesorios"
              />
              <span className="flex items-center gap-2 text-sm">
                <Package className="w-4 h-4 text-slate-500" />
                Accesorios registrados (cargador, funda, SIM, etc.)
              </span>
            </label>
          </div>

          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Observaciones de recepción (opcional)</Label>
            <Textarea
              placeholder="Ej: Dispositivo llega con pantalla rota, sin cargador..."
              value={observaciones}
              onChange={(e) => handleObservacionesChange(e.target.value)}
              className="min-h-[60px] text-sm"
              data-testid="ri-observaciones"
            />
          </div>

          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground flex items-center gap-1">
              Diagnóstico de recepción
              <span className="text-[10px] text-muted-foreground/70 italic">
                (inspección visual + breve diagnóstico inicial — visible para el admin)
              </span>
            </Label>
            <Textarea
              placeholder="Ej: La pantalla muestra líneas verticales, el touch responde parcialmente. Posible fallo del flex. Pendiente de abrir."
              value={diagnosticoRecepcion}
              onChange={(e) => handleDiagnosticoRecepcionChange(e.target.value)}
              className="min-h-[80px] text-sm"
              data-testid="ri-diagnostico-recepcion"
            />
          </div>
        </div>

        {riCompletada ? (
          <div className="p-3 bg-green-50 rounded-lg border border-green-200 space-y-2">
            <p className="text-sm font-medium flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-600" />
              RI completada: <Badge variant={riResultado === 'ok' ? 'success' : riResultado === 'no_conforme' ? 'destructive' : 'warning'}>{riResultado?.toUpperCase()}</Badge>
            </p>
            {orden?.ri_observaciones && (
              <p className="text-xs text-gray-600">Obs guardadas: {orden.ri_observaciones}</p>
            )}
            {orden?.ri_usuario_nombre && (
              <p className="text-xs text-gray-500">Técnico: {orden.ri_usuario_nombre}</p>
            )}
            <p className="text-xs text-gray-600">
              Puedes cambiar los checks y observaciones arriba; al pulsar <strong>Modificar RI</strong> se reescribirá la inspección.
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleRI('ok')}
                disabled={registrando}
                data-testid="orden-ri-modificar-ok"
                className="gap-1 border-green-300 hover:bg-green-50"
              >
                <CheckCircle2 className="w-4 h-4 text-green-600" />
                Modificar a OK
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => handleRI('sospechoso')}
                disabled={registrando}
                data-testid="orden-ri-modificar-sospechoso"
                className="gap-1"
              >
                <AlertTriangle className="w-4 h-4 text-yellow-500" />
                Modificar a Sospechoso
              </Button>
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={() => handleRI('no_conforme')}
                disabled={registrando}
                data-testid="orden-ri-modificar-no-conforme"
                className="gap-1"
              >
                <XCircle className="w-4 h-4" />
                Modificar a No Conforme
              </Button>
            </div>
          </div>
        ) : (
          <>
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">
                Completa el checklist y selecciona el resultado de la inspección. Al marcar <strong>RI OK</strong>, la reparación se inicia automáticamente.
              </p>
              {!todosLosChequeosCompletos && (
                <p className="text-xs text-amber-600 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  Recomendado: Marca todos los checks del checklist antes de finalizar el RI
                </p>
              )}
            </div>
            <div className="flex flex-wrap gap-2" data-testid="ri-botones-tecnico">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={registrando}
                onClick={() => handleRI('ok')}
                data-testid="orden-ri-registrar-ok-button"
                className="gap-1 border-green-300 hover:bg-green-50"
              >
                <CheckCircle2 className="w-4 h-4 text-green-600" />
                RI OK
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={registrando}
                onClick={() => handleRI('sospechoso')}
                data-testid="orden-ri-registrar-sospechoso-button"
                className="gap-1"
              >
                <AlertTriangle className="w-4 h-4 text-yellow-500" />
                RI Sospechoso
              </Button>
              <Button
                type="button"
                variant="destructive"
                size="sm"
                disabled={registrando}
                onClick={() => handleRI('no_conforme')}
                data-testid="orden-ri-registrar-no-conforme-button"
                className="gap-1"
              >
                <XCircle className="w-4 h-4" />
                RI No Conforme
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

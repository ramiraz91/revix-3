import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { CheckCircle2, AlertTriangle, XCircle, ShieldCheck, Info, ClipboardCheck, Smartphone, Package } from 'lucide-react';
import { ordenesAPI } from '@/lib/api';
import { toast } from 'sonner';

export function TecnicoRICard({ orden, onRefresh }) {
  const [registrando, setRegistrando] = useState(false);
  const [mostrarInfo, setMostrarInfo] = useState(false);
  const [observaciones, setObservaciones] = useState('');
  
  // Estados del checklist de recepción
  const [checklistCompleto, setChecklistCompleto] = useState(orden?.recepcion_checklist_completo || false);
  const [estadoFisicoRegistrado, setEstadoFisicoRegistrado] = useState(orden?.recepcion_estado_fisico_registrado || false);
  const [accesoriosRegistrados, setAccesoriosRegistrados] = useState(orden?.recepcion_accesorios_registrados || false);

  // Sincronizar cuando cambia la orden
  useEffect(() => {
    setChecklistCompleto(orden?.recepcion_checklist_completo || false);
    setEstadoFisicoRegistrado(orden?.recepcion_estado_fisico_registrado || false);
    setAccesoriosRegistrados(orden?.recepcion_accesorios_registrados || false);
  }, [orden?.recepcion_checklist_completo, orden?.recepcion_estado_fisico_registrado, orden?.recepcion_accesorios_registrados]);

  // Guardar cambios de checklist automáticamente
  const handleChecklistChange = async (campo, valor) => {
    try {
      await ordenesAPI.actualizar(orden.id, { [campo]: valor });
      // Actualizar estado local
      if (campo === 'recepcion_checklist_completo') setChecklistCompleto(valor);
      if (campo === 'recepcion_estado_fisico_registrado') setEstadoFisicoRegistrado(valor);
      if (campo === 'recepcion_accesorios_registrados') setAccesoriosRegistrados(valor);
    } catch (err) {
      toast.error('Error al guardar');
    }
  };

  const handleRI = async (resultado) => {
    setRegistrando(true);
    try {
      // Use first 3 evidencias as fotos_recepcion; pad to 3 if fewer available
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
      
      // También guardar los campos del checklist
      await ordenesAPI.actualizar(orden.id, {
        recepcion_checklist_completo: checklistCompleto,
        recepcion_estado_fisico_registrado: estadoFisicoRegistrado,
        recepcion_accesorios_registrados: accesoriosRegistrados,
        recepcion_notas: observaciones || null,
      });
      
      // Mensaje según resultado
      if (resultado === 'ok') {
        toast.success('RI OK — Reparación iniciada automáticamente');
      } else if (resultado === 'sospechoso') {
        toast.warning('RI Sospechoso — Orden en cuarentena para revisión');
      } else {
        toast.error('RI No Conforme — Orden en cuarentena');
      }
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al registrar RI');
    } finally {
      setRegistrando(false);
    }
  };

  const riCompletada = Boolean(orden?.ri_completada);
  const riResultado = orden?.ri_resultado;
  
  // Verificar si todos los checks están marcados
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
          <Button
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
        {/* Panel informativo */}
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

        {/* Checklist de Recepción - SIEMPRE visible */}
        <div className="p-3 bg-slate-50 rounded-lg border space-y-3">
          <p className="text-sm font-semibold flex items-center gap-2">
            <ClipboardCheck className="w-4 h-4 text-blue-600" />
            Checklist de Recepción
          </p>
          <div className="grid grid-cols-1 gap-3">
            <div className="flex items-center gap-3 p-2 bg-white rounded border">
              <Checkbox 
                id="checklist-completo"
                checked={checklistCompleto}
                onCheckedChange={(checked) => handleChecklistChange('recepcion_checklist_completo', Boolean(checked))}
                data-testid="ri-checklist-completo"
              />
              <Label htmlFor="checklist-completo" className="flex items-center gap-2 cursor-pointer text-sm">
                <ClipboardCheck className="w-4 h-4 text-slate-500" />
                Checklist de recepción completo
              </Label>
            </div>
            <div className="flex items-center gap-3 p-2 bg-white rounded border">
              <Checkbox 
                id="estado-fisico"
                checked={estadoFisicoRegistrado}
                onCheckedChange={(checked) => handleChecklistChange('recepcion_estado_fisico_registrado', Boolean(checked))}
                data-testid="ri-estado-fisico"
              />
              <Label htmlFor="estado-fisico" className="flex items-center gap-2 cursor-pointer text-sm">
                <Smartphone className="w-4 h-4 text-slate-500" />
                Estado físico registrado (fotos, golpes, rayones)
              </Label>
            </div>
            <div className="flex items-center gap-3 p-2 bg-white rounded border">
              <Checkbox 
                id="accesorios"
                checked={accesoriosRegistrados}
                onCheckedChange={(checked) => handleChecklistChange('recepcion_accesorios_registrados', Boolean(checked))}
                data-testid="ri-accesorios"
              />
              <Label htmlFor="accesorios" className="flex items-center gap-2 cursor-pointer text-sm">
                <Package className="w-4 h-4 text-slate-500" />
                Accesorios registrados (cargador, funda, SIM, etc.)
              </Label>
            </div>
          </div>
          
          {/* Observaciones */}
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Observaciones de recepción (opcional)</Label>
            <Textarea
              placeholder="Ej: Dispositivo llega con pantalla rota, sin cargador..."
              value={observaciones}
              onChange={(e) => setObservaciones(e.target.value)}
              className="min-h-[60px] text-sm"
              data-testid="ri-observaciones"
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
              <p className="text-xs text-gray-600">Obs: {orden.ri_observaciones}</p>
            )}
            {orden?.ri_usuario_nombre && (
              <p className="text-xs text-gray-500">Técnico: {orden.ri_usuario_nombre}</p>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleRI(riResultado)}
              disabled={registrando}
              data-testid="orden-ri-reregistrar-button"
              className="mt-2"
            >
              Modificar RI
            </Button>
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

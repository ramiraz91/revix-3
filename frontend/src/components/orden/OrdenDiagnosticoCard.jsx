import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText, ShieldCheck, Edit3, Save, X } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export function OrdenDiagnosticoCard({
  orden,
  tecnicoAsignado,
  onGuardarChecklist,
  onGuardarDiagnostico,
  guardandoChecklist,
  puedeEditarDiagnosticoQC,
  puedeEditarBateria,
  puedeEditarDiagnostico = false,
  esAdmin = false,
}) {
  const [editandoDiagnostico, setEditandoDiagnostico] = useState(false);
  const [diagnosticoEditado, setDiagnosticoEditado] = useState(orden?.diagnostico_tecnico || '');
  const [guardandoDiagnostico, setGuardandoDiagnostico] = useState(false);
  
  const diagnostico = orden?.diagnostico_tecnico;

  const handleGuardarDiagnostico = async () => {
    if (!onGuardarDiagnostico) return;
    setGuardandoDiagnostico(true);
    try {
      await onGuardarDiagnostico(diagnosticoEditado);
      setEditandoDiagnostico(false);
    } finally {
      setGuardandoDiagnostico(false);
    }
  };

  const handleCancelarEdicion = () => {
    setDiagnosticoEditado(orden?.diagnostico_tecnico || '');
    setEditandoDiagnostico(false);
  };

  return (
    <Card className="border-purple-200 bg-purple-50/50" data-testid="orden-calidad-checklist-card">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-purple-700">
            <FileText className="w-5 h-5" />
            Diagnóstico Técnico y Control de Calidad
          </div>
          {esAdmin && (
            <Badge variant="outline" className="text-xs">Vista Admin</Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Sección de Diagnóstico Técnico */}
        <div className="p-4 bg-white rounded-lg border space-y-3">
          <div className="flex items-center justify-between">
            <Label className="text-sm font-semibold flex items-center gap-2">
              <FileText className="w-4 h-4 text-purple-600" />
              Diagnóstico del Técnico
            </Label>
            {puedeEditarDiagnostico && !editandoDiagnostico && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setEditandoDiagnostico(true)}
                data-testid="btn-editar-diagnostico"
              >
                <Edit3 className="w-4 h-4 mr-1" />
                Editar
              </Button>
            )}
          </div>
          
          {editandoDiagnostico ? (
            <div className="space-y-3">
              <Textarea
                value={diagnosticoEditado}
                onChange={(e) => setDiagnosticoEditado(e.target.value)}
                placeholder="Escribe el diagnóstico técnico..."
                className="min-h-[120px]"
                data-testid="diagnostico-tecnico-textarea"
              />
              <div className="flex gap-2 justify-end">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleCancelarEdicion}
                  disabled={guardandoDiagnostico}
                >
                  <X className="w-4 h-4 mr-1" />
                  Cancelar
                </Button>
                <Button 
                  size="sm" 
                  onClick={handleGuardarDiagnostico}
                  disabled={guardandoDiagnostico}
                  data-testid="btn-guardar-diagnostico"
                >
                  <Save className="w-4 h-4 mr-1" />
                  {guardandoDiagnostico ? 'Guardando...' : 'Guardar'}
                </Button>
              </div>
            </div>
          ) : diagnostico ? (
            <p className="whitespace-pre-wrap text-slate-700 bg-slate-50 p-3 rounded border">{diagnostico}</p>
          ) : (
            <p className="text-sm text-muted-foreground italic p-3 bg-slate-50 rounded border border-dashed">
              Sin diagnóstico técnico registrado.
            </p>
          )}
        </div>

        {tecnicoAsignado && (
          <p className="text-sm text-muted-foreground">
            <strong>Técnico asignado:</strong> {tecnicoAsignado}
          </p>
        )}

        {/* Checklist de Recepción y QC */}
        <div className="p-3 bg-white rounded-lg border">
          <p className="text-sm font-semibold mb-3 text-purple-700">Checklist de Recepción y QC</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="flex items-center gap-2">
              <Checkbox checked={Boolean(orden?.recepcion_checklist_completo)} disabled={!puedeEditarDiagnosticoQC} onCheckedChange={(checked) => onGuardarChecklist({ recepcion_checklist_completo: Boolean(checked) })} data-testid="orden-recepcion-checklist-completo-checkbox" />
              <Label className="text-sm">Recepción checklist completo</Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox checked={Boolean(orden?.recepcion_estado_fisico_registrado)} disabled={!puedeEditarDiagnosticoQC} onCheckedChange={(checked) => onGuardarChecklist({ recepcion_estado_fisico_registrado: Boolean(checked) })} data-testid="orden-recepcion-estado-fisico-checkbox" />
              <Label className="text-sm">Estado físico registrado</Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox checked={Boolean(orden?.recepcion_accesorios_registrados)} disabled={!puedeEditarDiagnosticoQC} onCheckedChange={(checked) => onGuardarChecklist({ recepcion_accesorios_registrados: Boolean(checked) })} data-testid="orden-recepcion-accesorios-checkbox" />
              <Label className="text-sm">Accesorios registrados</Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox checked={Boolean(orden?.diagnostico_salida_realizado)} disabled={!puedeEditarDiagnosticoQC} onCheckedChange={(checked) => onGuardarChecklist({ diagnostico_salida_realizado: Boolean(checked) })} data-testid="orden-qc-diagnostico-salida-checkbox" />
              <Label className="text-sm">Diagnóstico final realizado</Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox checked={Boolean(orden?.funciones_verificadas)} disabled={!puedeEditarDiagnosticoQC} onCheckedChange={(checked) => onGuardarChecklist({ funciones_verificadas: Boolean(checked) })} data-testid="orden-qc-funciones-verificadas-checkbox" />
              <Label className="text-sm">Funciones verificadas (QC)</Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox checked={Boolean(orden?.limpieza_realizada)} disabled={!puedeEditarDiagnosticoQC} onCheckedChange={(checked) => onGuardarChecklist({ limpieza_realizada: Boolean(checked) })} data-testid="orden-qc-limpieza-realizada-checkbox" />
              <Label className="text-sm">Limpieza final realizada</Label>
            </div>
          </div>
        </div>

        {/* Trazabilidad de baterías */}
        <div className="p-3 bg-white rounded-lg border space-y-3">
          <p className="text-sm font-medium flex items-center gap-2"><ShieldCheck className="w-4 h-4" />Trazabilidad de baterías</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="flex items-center gap-2">
              <Checkbox checked={Boolean(orden?.bateria_reemplazada)} disabled={!puedeEditarBateria} onCheckedChange={(checked) => onGuardarChecklist({ bateria_reemplazada: Boolean(checked) })} data-testid="orden-bateria-reemplazada-checkbox" />
              <Label className="text-sm">Batería reemplazada</Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox checked={Boolean(orden?.bateria_almacenamiento_temporal)} disabled={!puedeEditarBateria} onCheckedChange={(checked) => onGuardarChecklist({ bateria_almacenamiento_temporal: Boolean(checked) })} data-testid="orden-bateria-almacenamiento-checkbox" />
              <Label className="text-sm">Almacenamiento temporal aplicado</Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox checked={Boolean(orden?.bateria_residuo_pendiente)} disabled={!puedeEditarBateria} onCheckedChange={(checked) => onGuardarChecklist({ bateria_residuo_pendiente: Boolean(checked) })} data-testid="orden-bateria-residuo-pendiente-checkbox" />
              <Label className="text-sm">Residuo pendiente de gestor</Label>
            </div>
            <div className="space-y-1">
              <Label className="text-sm">Gestor autorizado (si aplica)</Label>
              <Input defaultValue={orden?.bateria_gestor_autorizado || ''} disabled={!puedeEditarBateria} onBlur={(e) => onGuardarChecklist({ bateria_gestor_autorizado: e.target.value || null })} data-testid="orden-bateria-gestor-input" />
            </div>
            <div className="space-y-1">
              <Label className="text-sm">Fecha entrega gestor</Label>
              <Input type="date" defaultValue={orden?.bateria_fecha_entrega_gestor || ''} disabled={!puedeEditarBateria} onBlur={(e) => onGuardarChecklist({ bateria_fecha_entrega_gestor: e.target.value || null })} data-testid="orden-bateria-fecha-gestor-input" />
            </div>
          </div>
        </div>

        {/* Notas de cierre técnico */}
        <div className="space-y-2">
          <Label className="text-sm font-semibold">Notas de cierre técnico / QC</Label>
          <Textarea
            defaultValue={orden?.notas_cierre_tecnico || ''}
            onBlur={(e) => onGuardarChecklist({ notas_cierre_tecnico: e.target.value || null })}
            disabled={!puedeEditarDiagnosticoQC}
            className="min-h-[80px]"
            placeholder="Notas adicionales del cierre técnico..."
            data-testid="orden-qc-notas-cierre-textarea"
          />
        </div>

        {(puedeEditarDiagnosticoQC || puedeEditarBateria) && (
          <div className="flex items-center justify-between pt-2 border-t">
            <span className="text-xs text-muted-foreground">
              Los cambios en los checkboxes se guardan automáticamente
            </span>
            {guardandoChecklist && (
              <Badge variant="secondary" className="text-xs">Guardando...</Badge>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText, ShieldCheck } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export function OrdenDiagnosticoCard({
  orden,
  tecnicoAsignado,
  onGuardarChecklist,
  guardandoChecklist,
  puedeEditarDiagnosticoQC,
  puedeEditarBateria,
}) {
  const diagnostico = orden?.diagnostico_tecnico;

  return (
    <Card className="border-purple-200 bg-purple-50/50" data-testid="orden-calidad-checklist-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-purple-700">
          <FileText className="w-5 h-5" />
          Diagnóstico y Control de Calidad
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {diagnostico ? (
          <p className="whitespace-pre-wrap text-slate-700">{diagnostico}</p>
        ) : (
          <p className="text-sm text-muted-foreground">Sin diagnóstico técnico registrado.</p>
        )}

        {tecnicoAsignado && (
          <p className="text-sm text-muted-foreground mt-1">
            Técnico asignado: {tecnicoAsignado}
          </p>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3 bg-white rounded-lg border">
          <div className="flex items-center gap-2">
            <Checkbox checked={Boolean(orden?.recepcion_checklist_completo)} disabled={!puedeEditarDiagnosticoQC} onCheckedChange={(checked) => onGuardarChecklist({ recepcion_checklist_completo: Boolean(checked) })} data-testid="orden-recepcion-checklist-completo-checkbox" />
            <Label>Recepción checklist completo</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox checked={Boolean(orden?.recepcion_estado_fisico_registrado)} disabled={!puedeEditarDiagnosticoQC} onCheckedChange={(checked) => onGuardarChecklist({ recepcion_estado_fisico_registrado: Boolean(checked) })} data-testid="orden-recepcion-estado-fisico-checkbox" />
            <Label>Estado físico registrado</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox checked={Boolean(orden?.recepcion_accesorios_registrados)} disabled={!puedeEditarDiagnosticoQC} onCheckedChange={(checked) => onGuardarChecklist({ recepcion_accesorios_registrados: Boolean(checked) })} data-testid="orden-recepcion-accesorios-checkbox" />
            <Label>Accesorios registrados</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox checked={Boolean(orden?.diagnostico_salida_realizado)} disabled={!puedeEditarDiagnosticoQC} onCheckedChange={(checked) => onGuardarChecklist({ diagnostico_salida_realizado: Boolean(checked) })} data-testid="orden-qc-diagnostico-salida-checkbox" />
            <Label>Diagnóstico final realizado</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox checked={Boolean(orden?.funciones_verificadas)} disabled={!puedeEditarDiagnosticoQC} onCheckedChange={(checked) => onGuardarChecklist({ funciones_verificadas: Boolean(checked) })} data-testid="orden-qc-funciones-verificadas-checkbox" />
            <Label>Funciones verificadas (QC)</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox checked={Boolean(orden?.limpieza_realizada)} disabled={!puedeEditarDiagnosticoQC} onCheckedChange={(checked) => onGuardarChecklist({ limpieza_realizada: Boolean(checked) })} data-testid="orden-qc-limpieza-realizada-checkbox" />
            <Label>Limpieza final realizada</Label>
          </div>
        </div>

        <div className="p-3 bg-white rounded-lg border space-y-3">
          <p className="text-sm font-medium flex items-center gap-2"><ShieldCheck className="w-4 h-4" />Trazabilidad de baterías</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="flex items-center gap-2">
              <Checkbox checked={Boolean(orden?.bateria_reemplazada)} disabled={!puedeEditarBateria} onCheckedChange={(checked) => onGuardarChecklist({ bateria_reemplazada: Boolean(checked) })} data-testid="orden-bateria-reemplazada-checkbox" />
              <Label>Batería reemplazada</Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox checked={Boolean(orden?.bateria_almacenamiento_temporal)} disabled={!puedeEditarBateria} onCheckedChange={(checked) => onGuardarChecklist({ bateria_almacenamiento_temporal: Boolean(checked) })} data-testid="orden-bateria-almacenamiento-checkbox" />
              <Label>Almacenamiento temporal aplicado</Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox checked={Boolean(orden?.bateria_residuo_pendiente)} disabled={!puedeEditarBateria} onCheckedChange={(checked) => onGuardarChecklist({ bateria_residuo_pendiente: Boolean(checked) })} data-testid="orden-bateria-residuo-pendiente-checkbox" />
              <Label>Residuo pendiente de gestor</Label>
            </div>
            <div className="space-y-1">
              <Label>Gestor autorizado (si aplica)</Label>
              <Input defaultValue={orden?.bateria_gestor_autorizado || ''} disabled={!puedeEditarBateria} onBlur={(e) => onGuardarChecklist({ bateria_gestor_autorizado: e.target.value || null })} data-testid="orden-bateria-gestor-input" />
            </div>
            <div className="space-y-1">
              <Label>Fecha entrega gestor</Label>
              <Input type="date" defaultValue={orden?.bateria_fecha_entrega_gestor || ''} disabled={!puedeEditarBateria} onBlur={(e) => onGuardarChecklist({ bateria_fecha_entrega_gestor: e.target.value || null })} data-testid="orden-bateria-fecha-gestor-input" />
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <Label>Notas de cierre técnico / QC</Label>
          <Textarea
            defaultValue={orden?.notas_cierre_tecnico || ''}
            onBlur={(e) => onGuardarChecklist({ notas_cierre_tecnico: e.target.value || null })}
            disabled={!puedeEditarDiagnosticoQC}
            className="min-h-[80px]"
            data-testid="orden-qc-notas-cierre-textarea"
          />
        </div>

        {(puedeEditarDiagnosticoQC || puedeEditarBateria) && (
          <Button variant="outline" size="sm" disabled={guardandoChecklist} data-testid="orden-checklist-save-indicator-button">
            {guardandoChecklist ? 'Guardando checklist...' : 'Checklist activo (autoguardado por campo)'}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

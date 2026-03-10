import { useState } from 'react';
import { FileText, Save, Clock, Sparkles, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { ordenesAPI, iaAPI } from '@/lib/api';
import { toast } from 'sonner';

export function TecnicoDiagnosticoForm({ orden, diagnostico, setDiagnostico, onRefresh }) {
  const [guardandoDiagnostico, setGuardandoDiagnostico] = useState(false);
  const [mejorandoDiagnostico, setMejorandoDiagnostico] = useState(false);

  const handleGuardarDiagnostico = async () => {
    setGuardandoDiagnostico(true);
    try {
      await ordenesAPI.guardarDiagnostico(orden.id, diagnostico);
      toast.success('Diagnóstico guardado correctamente');
      onRefresh();
    } catch (error) {
      toast.error('Error al guardar el diagnóstico');
    } finally {
      setGuardandoDiagnostico(false);
    }
  };

  const handleMejorarDiagnosticoIA = async () => {
    if (!diagnostico.trim()) return;
    
    setMejorandoDiagnostico(true);
    try {
      const res = await iaAPI.mejorarDiagnostico(
        diagnostico,
        orden?.dispositivo?.modelo,
        orden?.dispositivo?.daños
      );
      setDiagnostico(res.data.diagnostico_mejorado);
      toast.success('Diagnóstico mejorado con IA');
    } catch (error) {
      console.error('Error mejorando diagnóstico:', error);
      toast.error('Error al mejorar el diagnóstico con IA');
    } finally {
      setMejorandoDiagnostico(false);
    }
  };

  return (
    <Card className="border-blue-200">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-600" />
          Diagnóstico Técnico
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <Label htmlFor="diagnostico">
            Escribe tu diagnóstico y observaciones sobre la reparación
          </Label>
          <Textarea
            id="diagnostico"
            placeholder="Describe el estado del dispositivo, el diagnóstico realizado, las reparaciones efectuadas y cualquier observación relevante..."
            value={diagnostico}
            onChange={(e) => setDiagnostico(e.target.value)}
            className="min-h-[120px]"
            data-testid="diagnostico-input"
          />
          <div className="flex justify-between items-center gap-2">
            <Button 
              variant="outline"
              onClick={handleMejorarDiagnosticoIA}
              disabled={mejorandoDiagnostico || !diagnostico.trim()}
              className="gap-2 text-purple-600 border-purple-300 hover:bg-purple-50"
              data-testid="mejorar-diagnostico-ia-btn"
            >
              {mejorandoDiagnostico ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Mejorando...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Mejorar con IA
                </>
              )}
            </Button>
            <Button 
              onClick={handleGuardarDiagnostico} 
              disabled={guardandoDiagnostico || diagnostico === (orden.diagnostico_tecnico || '')}
              data-testid="guardar-diagnostico-btn"
            >
              {guardandoDiagnostico ? (
                <>
                  <Clock className="w-4 h-4 mr-2 animate-spin" />
                  Guardando...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Guardar Diagnóstico
                </>
              )}
            </Button>
          </div>
          {orden.diagnostico_tecnico && (
            <p className="text-xs text-muted-foreground">
              Último guardado: {diagnostico === orden.diagnostico_tecnico ? 'Sin cambios' : 'Hay cambios sin guardar'}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

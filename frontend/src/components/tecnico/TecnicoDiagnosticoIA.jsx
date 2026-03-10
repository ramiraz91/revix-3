import { useState } from 'react';
import { Sparkles, Loader2, Lightbulb, ChevronDown, ChevronUp, Plus } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { iaAPI } from '@/lib/api';
import { toast } from 'sonner';

export function TecnicoDiagnosticoIA({ orden, diagnostico, setDiagnostico }) {
  const [diagnosticoIA, setDiagnosticoIA] = useState('');
  const [cargandoDiagnosticoIA, setCargandoDiagnosticoIA] = useState(false);
  const [mostrarDiagnosticoIA, setMostrarDiagnosticoIA] = useState(true);

  const obtenerDiagnosticoIA = async () => {
    if (!orden?.dispositivo?.modelo || !orden?.dispositivo?.daños) return;
    
    setCargandoDiagnosticoIA(true);
    try {
      const res = await iaAPI.diagnostico(
        orden.dispositivo.modelo,
        orden.dispositivo.daños
      );
      setDiagnosticoIA(res.data.diagnostico);
    } catch (error) {
      console.error('Error obteniendo diagnóstico IA:', error);
    } finally {
      setCargandoDiagnosticoIA(false);
    }
  };

  // Obtener diagnóstico IA al montar si no hay diagnóstico del técnico
  useState(() => {
    if (!orden?.diagnostico_tecnico && orden?.dispositivo?.modelo && orden?.dispositivo?.daños) {
      obtenerDiagnosticoIA();
    }
  }, [orden]);

  if (!cargandoDiagnosticoIA && !diagnosticoIA) return null;

  return (
    <Card className="border-purple-200 bg-gradient-to-br from-purple-50 to-blue-50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-purple-700">
            <Sparkles className="w-5 h-5" />
            Sugerencias IA
            <Badge variant="outline" className="text-[10px] bg-purple-100">Gemini</Badge>
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={obtenerDiagnosticoIA}
              disabled={cargandoDiagnosticoIA}
              className="text-xs"
            >
              {cargandoDiagnosticoIA ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                'Regenerar'
              )}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setMostrarDiagnosticoIA(!mostrarDiagnosticoIA)}
            >
              {mostrarDiagnosticoIA ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>
      </CardHeader>
      {mostrarDiagnosticoIA && (
        <CardContent>
          {cargandoDiagnosticoIA ? (
            <div className="flex items-center gap-3 py-4">
              <Loader2 className="w-5 h-5 animate-spin text-purple-600" />
              <span className="text-sm text-muted-foreground">Analizando síntomas...</span>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="p-3 bg-white rounded-lg border text-sm whitespace-pre-wrap">
                {diagnosticoIA}
              </div>
              <div className="flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-amber-500" />
                <span className="text-xs text-muted-foreground">
                  Estas son sugerencias basadas en IA. Usa tu criterio profesional.
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setDiagnostico(prev => prev ? `${prev}\n\n--- Sugerencias IA ---\n${diagnosticoIA}` : diagnosticoIA);
                  toast.success('Sugerencias añadidas al diagnóstico');
                }}
                className="text-xs"
              >
                <Plus className="w-3 h-3 mr-1" />
                Añadir a mi diagnóstico
              </Button>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}

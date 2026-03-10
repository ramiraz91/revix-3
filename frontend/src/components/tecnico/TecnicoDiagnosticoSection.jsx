import { useState } from 'react';
import { FileText, Save, Sparkles, Loader2, ChevronDown, ChevronUp, Lightbulb } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

export function TecnicoDiagnosticoSection({
  diagnostico,
  setDiagnostico,
  diagnosticoIA,
  cargandoDiagnosticoIA,
  mostrarDiagnosticoIA,
  setMostrarDiagnosticoIA,
  onGuardarDiagnostico,
  guardandoDiagnostico,
  onMejorarDiagnosticoIA,
  mejorandoDiagnostico
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="w-5 h-5" />
          Diagnóstico del Técnico
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Sugerencia IA (colapsable) */}
        {(diagnosticoIA || cargandoDiagnosticoIA) && (
          <div className="bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-lg">
            <button
              onClick={() => setMostrarDiagnosticoIA(!mostrarDiagnosticoIA)}
              className="w-full flex items-center justify-between p-3 text-left"
            >
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-600" />
                <span className="text-sm font-medium text-purple-700">
                  Sugerencia del Asistente IA
                </span>
              </div>
              {mostrarDiagnosticoIA ? (
                <ChevronUp className="w-4 h-4 text-purple-600" />
              ) : (
                <ChevronDown className="w-4 h-4 text-purple-600" />
              )}
            </button>
            {mostrarDiagnosticoIA && (
              <div className="px-3 pb-3">
                {cargandoDiagnosticoIA ? (
                  <div className="flex items-center gap-2 text-sm text-purple-600">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Analizando dispositivo...
                  </div>
                ) : (
                  <>
                    <p className="text-sm text-purple-800 whitespace-pre-wrap">{diagnosticoIA}</p>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="mt-2 text-purple-600 hover:text-purple-700"
                      onClick={() => setDiagnostico(diagnosticoIA)}
                    >
                      <Lightbulb className="w-4 h-4 mr-1" />
                      Usar esta sugerencia
                    </Button>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* Campo de diagnóstico */}
        <Textarea
          placeholder="Escribe el diagnóstico detallado del dispositivo..."
          value={diagnostico}
          onChange={(e) => setDiagnostico(e.target.value)}
          rows={4}
          className="resize-none"
        />

        {/* Botones de acción */}
        <div className="flex gap-2 justify-end">
          {diagnostico.trim() && (
            <Button
              variant="outline"
              size="sm"
              onClick={onMejorarDiagnosticoIA}
              disabled={mejorandoDiagnostico}
              className="text-purple-600 border-purple-300 hover:bg-purple-50"
            >
              {mejorandoDiagnostico ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Mejorando...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Mejorar con IA
                </>
              )}
            </Button>
          )}
          <Button
            size="sm"
            onClick={onGuardarDiagnostico}
            disabled={guardandoDiagnostico || !diagnostico.trim()}
          >
            {guardandoDiagnostico ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
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
      </CardContent>
    </Card>
  );
}

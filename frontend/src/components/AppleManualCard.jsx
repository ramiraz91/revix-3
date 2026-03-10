import { useState, useEffect } from 'react';
import { ExternalLink, BookOpen, Wrench, AlertCircle, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

const API_URL = process.env.REACT_APP_BACKEND_URL;

/**
 * Componente que muestra la documentación de reparación de Apple
 * para un dispositivo específico basándose en el modelo y problema.
 */
export default function AppleManualCard({ dispositivo, problema }) {
  const [documentation, setDocumentation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const fetchDocumentation = async () => {
      // Solo buscar si es un iPhone
      const modelo = dispositivo?.modelo || '';
      if (!modelo.toLowerCase().includes('iphone')) {
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams({ model: modelo });
        if (problema) {
          params.append('problem', problema);
        }

        const response = await fetch(`${API_URL}/api/apple-manuals/lookup?${params}`);
        if (!response.ok) throw new Error('Error al buscar documentación');
        
        const data = await response.json();
        if (data.found) {
          setDocumentation(data);
          setIsOpen(true); // Abrir automáticamente si se encuentra
        }
      } catch (err) {
        console.error('Error fetching Apple documentation:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDocumentation();
  }, [dispositivo?.modelo, problema]);

  // No mostrar si no es iPhone
  if (!dispositivo?.modelo?.toLowerCase().includes('iphone')) {
    return null;
  }

  // Loading state
  if (loading) {
    return (
      <Card className="border-slate-200 bg-slate-50">
        <CardContent className="py-4">
          <div className="flex items-center gap-2 text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">Buscando documentación de Apple...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  // No documentation found
  if (!documentation) {
    return null;
  }

  return (
    <Card className="border-blue-200 bg-gradient-to-br from-blue-50 to-slate-50" data-testid="apple-manual-card">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CardHeader className="pb-2">
          <CollapsibleTrigger className="w-full">
            <div className="flex items-center justify-between cursor-pointer">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-white rounded-lg shadow-sm">
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
                  </svg>
                </div>
                <div className="text-left">
                  <CardTitle className="text-base font-semibold text-slate-800">
                    Manual de Reparación Apple
                  </CardTitle>
                  <p className="text-xs text-slate-500">
                    {documentation.model_info?.name} ({documentation.model_info?.year})
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {documentation.manual_url && (
                  <Badge variant="secondary" className="bg-green-100 text-green-700 text-xs">
                    Manual disponible
                  </Badge>
                )}
                {isOpen ? (
                  <ChevronUp className="h-4 w-4 text-slate-400" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-slate-400" />
                )}
              </div>
            </div>
          </CollapsibleTrigger>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="pt-0 space-y-3">
            {/* Enlaces principales */}
            <div className="flex flex-wrap gap-2">
              {documentation.main_page_url && (
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs h-8"
                  onClick={() => window.open(documentation.main_page_url, '_blank')}
                  data-testid="apple-main-page-btn"
                >
                  <BookOpen className="h-3 w-3 mr-1" />
                  Página del dispositivo
                  <ExternalLink className="h-3 w-3 ml-1" />
                </Button>
              )}
              
              {documentation.manual_url && (
                <Button
                  variant="default"
                  size="sm"
                  className="text-xs h-8 bg-blue-600 hover:bg-blue-700"
                  onClick={() => window.open(documentation.manual_url, '_blank')}
                  data-testid="apple-manual-btn"
                >
                  <Wrench className="h-3 w-3 mr-1" />
                  Manual de Reparación
                  <ExternalLink className="h-3 w-3 ml-1" />
                </Button>
              )}

              {documentation.specs_url && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs h-8"
                  onClick={() => window.open(documentation.specs_url, '_blank')}
                >
                  Especificaciones
                  <ExternalLink className="h-3 w-3 ml-1" />
                </Button>
              )}
            </div>

            {/* Secciones relevantes detectadas */}
            {documentation.relevant_sections?.length > 0 && (
              <div className="pt-2 border-t border-blue-100">
                <p className="text-xs font-medium text-slate-600 mb-2">
                  <AlertCircle className="h-3 w-3 inline mr-1" />
                  Secciones relevantes para el problema:
                </p>
                <div className="flex flex-wrap gap-2">
                  {documentation.relevant_sections.map((section, idx) => (
                    <Button
                      key={idx}
                      variant="outline"
                      size="sm"
                      className="text-xs h-7 border-amber-200 bg-amber-50 hover:bg-amber-100 text-amber-700"
                      onClick={() => {
                        if (section.troubleshooting_url) {
                          window.open(section.troubleshooting_url, '_blank');
                        } else if (documentation.manual_url) {
                          window.open(documentation.manual_url, '_blank');
                        }
                      }}
                      data-testid={`apple-section-${section.type}`}
                    >
                      {section.name}
                      <ExternalLink className="h-3 w-3 ml-1" />
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {/* Mensaje informativo si no hay manual */}
            {!documentation.manual_url && (
              <div className="text-xs text-slate-500 bg-slate-100 p-2 rounded flex items-start gap-2">
                <AlertCircle className="h-4 w-4 text-slate-400 mt-0.5 flex-shrink-0" />
                <span>
                  Este modelo no tiene manual de reparación oficial de Apple. 
                  La página del dispositivo puede contener información útil.
                </span>
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}

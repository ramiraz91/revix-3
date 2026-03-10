/**
 * Panel de Recomendación de Precios
 * Se muestra cuando se busca un siniestro para dar contexto de precios
 */
import { useState, useEffect } from 'react';
import {
  Lightbulb,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Trophy,
  Target,
  Users,
  RefreshCw,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { inteligenciaPreciosAPI } from '@/lib/api';

export default function RecomendacionPrecios({ dispositivo, tipoReparacion, cargando }) {
  const [recomendacion, setRecomendacion] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    // Cargar recomendación general si no hay datos específicos
    cargarRecomendacion();
  }, [dispositivo, tipoReparacion]);

  const cargarRecomendacion = async () => {
    try {
      setLoading(true);
      const data = await inteligenciaPreciosAPI.getRecomendacion({
        dispositivo: dispositivo || '',
        tipo_reparacion: tipoReparacion || ''
      });
      setRecomendacion(data);
    } catch (error) {
      console.error('Error cargando recomendación:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || cargando) {
    return (
      <Card className="border-blue-200 bg-blue-50/50">
        <CardContent className="py-4 flex items-center justify-center">
          <RefreshCw className="w-5 h-5 animate-spin text-blue-500 mr-2" />
          <span className="text-blue-700">Analizando datos históricos...</span>
        </CardContent>
      </Card>
    );
  }

  if (!recomendacion || !recomendacion.tiene_datos) {
    return (
      <Card className="border-gray-200 bg-gray-50">
        <CardContent className="py-4 text-center">
          <Lightbulb className="w-6 h-6 mx-auto text-gray-400 mb-2" />
          <p className="text-sm text-gray-500">
            Sin datos históricos para este tipo de reparación.
            <br />
            Los datos se irán acumulando automáticamente.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50">
      <CardHeader className="pb-2">
        <div 
          className="flex items-center justify-between cursor-pointer"
          onClick={() => setExpanded(!expanded)}
        >
          <CardTitle className="text-base flex items-center gap-2 text-blue-800">
            <Lightbulb className="w-5 h-5 text-amber-500" />
            Recomendación de Precio
          </CardTitle>
          <Button variant="ghost" size="sm">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </Button>
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="space-y-4">
          {/* Precio recomendado destacado */}
          {recomendacion.precio_recomendado && (
            <div className="bg-white rounded-lg p-4 border border-blue-200 text-center">
              <p className="text-sm text-gray-500 mb-1">Precio sugerido</p>
              <p className="text-3xl font-bold text-blue-700">
                {recomendacion.precio_recomendado}€
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Basado en {recomendacion.total_casos_analizados} casos similares
              </p>
            </div>
          )}

          {/* Estadísticas rápidas */}
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="bg-white/80 rounded p-2">
              <p className="text-lg font-bold text-green-600">{recomendacion.casos_ganados}</p>
              <p className="text-xs text-gray-500">Ganados</p>
            </div>
            <div className="bg-white/80 rounded p-2">
              <p className="text-lg font-bold text-red-600">{recomendacion.casos_perdidos}</p>
              <p className="text-xs text-gray-500">Perdidos</p>
            </div>
            <div className="bg-white/80 rounded p-2">
              <p className="text-lg font-bold text-blue-600">{recomendacion.tasa_exito}%</p>
              <p className="text-xs text-gray-500">Tasa éxito</p>
            </div>
          </div>

          {/* Barra de tasa de éxito */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-500">Tu tasa de éxito en casos similares</span>
              <span className={recomendacion.tasa_exito >= 50 ? 'text-green-600' : 'text-red-600'}>
                {recomendacion.tasa_exito}%
              </span>
            </div>
            <Progress 
              value={recomendacion.tasa_exito} 
              className={recomendacion.tasa_exito >= 50 ? 'bg-green-100' : 'bg-red-100'}
            />
          </div>

          {/* Rango de precios */}
          {recomendacion.precio_minimo_historico && (
            <div className="flex items-center justify-between text-sm bg-white/60 rounded p-2">
              <span className="text-gray-500">Rango histórico:</span>
              <span className="font-medium">
                {recomendacion.precio_minimo_historico}€ - {recomendacion.precio_maximo_historico}€
              </span>
            </div>
          )}

          {/* Competidores peligrosos */}
          {recomendacion.competidores_peligrosos?.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <p className="text-sm font-medium text-amber-800 flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4" />
                Competidores agresivos en este tipo
              </p>
              <div className="space-y-1">
                {recomendacion.competidores_peligrosos.map((comp, idx) => (
                  <div key={idx} className="flex justify-between text-sm">
                    <span className="text-amber-900">{comp.nombre}</span>
                    <span className="text-amber-700">
                      ~{comp.precio_promedio}€ ({comp.veces_ganado}x)
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Consejos */}
          {recomendacion.consejos?.length > 0 && (
            <div className="space-y-2">
              {recomendacion.consejos.map((consejo, idx) => (
                <div 
                  key={idx}
                  className={`text-sm p-2 rounded ${
                    consejo.tipo === 'success' ? 'bg-green-100 text-green-800' :
                    consejo.tipo === 'warning' ? 'bg-amber-100 text-amber-800' :
                    consejo.tipo === 'alert' ? 'bg-red-100 text-red-800' :
                    consejo.tipo === 'recommendation' ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  }`}
                >
                  {consejo.mensaje}
                </div>
              ))}
            </div>
          )}

          {/* Últimos casos similares */}
          {recomendacion.ultimos_casos?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2">Casos recientes similares:</p>
              <div className="space-y-1">
                {recomendacion.ultimos_casos.slice(0, 3).map((caso, idx) => (
                  <div key={idx} className="flex items-center justify-between text-xs bg-white/60 rounded px-2 py-1">
                    <span className="text-gray-500">{caso.fecha}</span>
                    <Badge 
                      variant={caso.resultado === 'ganado' ? 'default' : 'destructive'}
                      className="text-[10px]"
                    >
                      {caso.resultado === 'ganado' ? 'Ganado' : 'Perdido'}
                    </Badge>
                    <span className="font-medium">{caso.mi_precio}€</span>
                    {caso.resultado === 'perdido' && caso.precio_ganador && (
                      <span className="text-red-500">vs {caso.precio_ganador}€</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}

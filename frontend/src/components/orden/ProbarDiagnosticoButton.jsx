import { useState } from 'react';
import {
  Stethoscope, Loader2, Package, UserCog, AlertTriangle,
  CheckCircle2, Sparkles, TrendingUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import API from '@/lib/api';
import { toast } from 'sonner';

export default function ProbarDiagnosticoButton({ orderId, numeroOrden, sintomas }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleProbar = async () => {
    setLoading(true);
    setResult(null);
    try {
      const { data } = await API.post(`/ordenes/${orderId}/triador-diagnostico`);
      setResult(data);
      setOpen(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error ejecutando triador');
    } finally {
      setLoading(false);
    }
  };

  const confianza = result?.diagnostico?.confianza_global || 0;
  const confianzaPct = Math.round(confianza * 100);
  const confianzaColor = confianza >= 0.8 ? 'text-green-700'
    : confianza >= 0.5 ? 'text-amber-700'
    : 'text-red-700';

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={handleProbar}
        disabled={loading || !sintomas?.trim()}
        data-testid="btn-probar-diagnostico"
        className="gap-1.5"
        title={!sintomas?.trim() ? 'Añade descripción de avería primero' : 'Ejecutar agente triador'}
      >
        {loading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <Sparkles className="w-3.5 h-3.5 text-orange-500" />
        )}
        Probar diagnóstico
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" data-testid="dialog-diagnostico">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Stethoscope className="w-5 h-5 text-orange-500" />
              Triador de Averías — Análisis OT {numeroOrden}
              {result?.preview && (
                <Badge variant="outline" className="text-[10px] bg-amber-50 border-amber-300 text-amber-800">
                  sugerencia IA
                </Badge>
              )}
            </DialogTitle>
            <DialogDescription>
              Resultado del agente `triador_averias`. No modifica la orden: la decisión final es tuya.
            </DialogDescription>
          </DialogHeader>

          {result && (
            <div className="space-y-5 mt-2">
              {/* 1. Diagnóstico */}
              <section data-testid="seccion-diagnostico">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold flex items-center gap-2">
                    <Stethoscope className="w-4 h-4 text-blue-600" /> 1. Diagnóstico
                  </h3>
                  {result.diagnostico?.diagnostico_match && (
                    <Badge className={`${confianzaColor} bg-slate-100`}>
                      <TrendingUp className="w-3 h-3 mr-1" />
                      {confianzaPct}% confianza
                    </Badge>
                  )}
                </div>

                {result.diagnostico?.diagnostico_match === false ? (
                  <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 flex gap-2 text-sm">
                    <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium text-amber-900">Sin coincidencias automáticas</p>
                      <p className="text-amber-700 text-xs mt-0.5">
                        {result.diagnostico?.mensaje || 'Escalar a diagnóstico manual.'}
                      </p>
                    </div>
                  </div>
                ) : result.diagnostico?.success === false ? (
                  <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-800">
                    {result.diagnostico?.mensaje || 'Error'}
                  </div>
                ) : (
                  <>
                    <p className="text-xs text-muted-foreground mb-2">
                      Síntomas: <span className="italic">&quot;{result.diagnostico?.sintomas_analizados}&quot;</span>
                    </p>
                    <div className="space-y-1.5">
                      {(result.diagnostico?.causas_probables || []).map((c, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <div className="flex-1 bg-slate-100 rounded h-6 relative overflow-hidden">
                            <div
                              className="absolute inset-y-0 left-0 bg-blue-400"
                              style={{ width: `${Math.round(c.confianza * 100)}%` }}
                            />
                            <span className="relative z-10 px-2 text-xs font-medium leading-6">
                              {c.causa}
                            </span>
                          </div>
                          <span className="text-xs font-mono text-muted-foreground w-10 text-right">
                            {Math.round(c.confianza * 100)}%
                          </span>
                        </div>
                      ))}
                    </div>
                    <div className="flex gap-2 mt-3 text-xs">
                      <Badge variant="outline">
                        Tipo: <b className="ml-1">{result.diagnostico?.tipo_reparacion_sugerido || '—'}</b>
                      </Badge>
                      <Badge variant="outline">
                        Repuestos: {(result.diagnostico?.repuestos_ref || []).join(', ') || '—'}
                      </Badge>
                    </div>
                  </>
                )}
              </section>

              {/* 2. Repuestos */}
              {result.repuestos && (
                <>
                  <Separator />
                  <section data-testid="seccion-repuestos">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold flex items-center gap-2">
                        <Package className="w-4 h-4 text-purple-600" /> 2. Repuestos en inventario
                      </h3>
                      <Badge className={
                        result.repuestos.con_stock_inmediato === result.repuestos.total_repuestos_consultados
                          ? 'bg-green-100 text-green-800 border-green-300'
                          : result.repuestos.con_stock_inmediato > 0
                            ? 'bg-amber-100 text-amber-800 border-amber-300'
                            : 'bg-red-100 text-red-800 border-red-300'
                      }>
                        {result.repuestos.con_stock_inmediato}/{result.repuestos.total_repuestos_consultados} con stock
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mb-2">{result.repuestos.veredicto}</p>
                    <div className="space-y-2">
                      {(result.repuestos.sugerencias || []).map((s, i) => (
                        <div key={i} className="border rounded-lg p-2 text-sm">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium capitalize">{s.repuesto_ref}</span>
                            {s.hay_stock_directo ? (
                              <Badge className="bg-green-100 text-green-800 border-green-300 text-[10px]">
                                <CheckCircle2 className="w-3 h-3 mr-1" /> stock OK
                              </Badge>
                            ) : (
                              <Badge className="bg-red-100 text-red-800 border-red-300 text-[10px]">
                                sin stock
                              </Badge>
                            )}
                          </div>
                          {s.mejor_opcion ? (
                            <div className="text-xs text-muted-foreground">
                              <span className="font-mono font-medium text-slate-700">
                                {s.mejor_opcion.sku_corto || '—'}
                              </span> · {s.mejor_opcion.nombre}
                              {' · '}
                              <span>stock: <b>{s.mejor_opcion.stock || 0}</b></span>
                              {s.mejor_opcion.precio_venta ? <span> · {s.mejor_opcion.precio_venta}€</span> : null}
                              {s.mejor_opcion.proveedor && <span> · {s.mejor_opcion.proveedor}</span>}
                            </div>
                          ) : (
                            <p className="text-xs text-red-600">Sin coincidencias en inventario.</p>
                          )}
                          {s.alternativas?.length > 0 && (
                            <p className="text-[10px] text-muted-foreground mt-1">
                              +{s.alternativas.length} alternativa(s) disponibles.
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </section>
                </>
              )}

              {/* 3. Técnico */}
              {result.tecnico && result.tecnico.success && (
                <>
                  <Separator />
                  <section data-testid="seccion-tecnico">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold flex items-center gap-2">
                        <UserCog className="w-4 h-4 text-emerald-600" /> 3. Técnico recomendado
                      </h3>
                      <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px]">
                        score {result.tecnico.recomendado?.score}
                      </Badge>
                    </div>
                    <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-sm">
                      <p className="font-semibold">
                        {result.tecnico.recomendado?.nombre}
                        {result.tecnico.recomendado?.especialista_en_tipo && (
                          <Badge className="ml-2 bg-emerald-600 text-white text-[9px]">especialista</Badge>
                        )}
                      </p>
                      <p className="text-xs text-emerald-700 mt-0.5">{result.tecnico.razon}</p>
                      <div className="flex gap-3 mt-2 text-xs text-muted-foreground">
                        <span>En curso: <b>{result.tecnico.recomendado?.carga_actual}</b></span>
                        <span>Reparadas 30d: <b>{result.tecnico.recomendado?.reparadas_30d}</b></span>
                      </div>
                    </div>
                    {result.tecnico.ranking?.length > 1 && (
                      <details className="mt-2 text-xs">
                        <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                          Ver ranking completo ({result.tecnico.ranking.length})
                        </summary>
                        <div className="mt-1 space-y-1">
                          {result.tecnico.ranking.map((r, i) => (
                            <div key={r.id} className="flex justify-between border-b py-1">
                              <span>#{i + 1} {r.nombre}</span>
                              <span className="text-muted-foreground">
                                carga {r.carga_actual} · reparadas {r.reparadas_30d} · score {r.score}
                              </span>
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </section>
                </>
              )}

              <Separator />
              <div className="flex items-start gap-2 text-xs text-muted-foreground italic bg-slate-50 rounded p-2">
                <Sparkles className="w-3.5 h-3.5 shrink-0 mt-0.5 text-orange-500" />
                <p>
                  Este es un análisis del agente <b>triador_averias</b>. No se ha modificado la OT.
                  Revisa y aplica manualmente las sugerencias desde el panel de la orden.
                </p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

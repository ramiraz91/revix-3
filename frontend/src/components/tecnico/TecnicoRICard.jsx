import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, AlertTriangle, XCircle, ShieldCheck, Info } from 'lucide-react';
import { ordenesAPI } from '@/lib/api';
import { toast } from 'sonner';

export function TecnicoRICard({ orden, onRefresh }) {
  const [registrando, setRegistrando] = useState(false);
  const [mostrarInfo, setMostrarInfo] = useState(false);

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
        checklist_visual: { inspeccion_visual: true },
        fotos_recepcion: fotosPadded,
        observaciones: '',
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
      <CardContent className="space-y-3">
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

        {riCompletada ? (
          <div className="p-3 bg-slate-50 rounded-lg space-y-1">
            <p className="text-sm font-medium">RI completada: {riResultado?.toUpperCase()}</p>
            {orden?.ri_observaciones && (
              <p className="text-xs text-gray-500">Obs: {orden.ri_observaciones}</p>
            )}
            {orden?.ri_usuario_nombre && (
              <p className="text-xs text-gray-400">Técnico: {orden.ri_usuario_nombre}</p>
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
            <p className="text-xs text-muted-foreground">
              Verifica el estado del dispositivo antes de iniciar. Al marcar <strong>RI OK</strong>, la reparación se inicia automáticamente.
            </p>
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

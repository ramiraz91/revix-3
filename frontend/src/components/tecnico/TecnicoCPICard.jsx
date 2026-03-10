import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Shield } from 'lucide-react';
import { ordenesAPI } from '@/lib/api';
import { toast } from 'sonner';

const CPI_OPCIONES = {
  cliente_ya_restablecio: {
    label: 'Ya venía restablecido por el cliente (verificado)',
    requiere_borrado: false,
    resultado: 'no_aplica',
    autorizacion: true,
  },
  cliente_no_autoriza: {
    label: 'Cliente NO autoriza restablecer/borrar (Privacidad alta)',
    requiere_borrado: false,
    resultado: 'no_aplica',
    autorizacion: false,
  },
  sat_realizo_restablecimiento: {
    label: 'Restablecimiento realizado por el SAT (NIST 800-88)',
    requiere_borrado: true,
    resultado: 'completado',
    autorizacion: true,
  },
};

export function TecnicoCPICard({ orden, onRefresh }) {
  const existing = orden?.cpi_opcion || '';
  const [opcion, setOpcion] = useState(existing);
  const [metodo, setMetodo] = useState(orden?.cpi_metodo || '');
  const [observaciones, setObservaciones] = useState(orden?.cpi_observaciones || '');
  const [guardando, setGuardando] = useState(false);

  const handleGuardar = async () => {
    if (!opcion) {
      toast.error('Selecciona una opción de privacidad/CPI');
      return;
    }
    if (opcion === 'sat_realizo_restablecimiento' && !metodo) {
      toast.error('Selecciona el método de restablecimiento');
      return;
    }
    const meta = CPI_OPCIONES[opcion];
    const payload = {
      opcion,
      requiere_borrado: meta.requiere_borrado,
      autorizacion_cliente: meta.autorizacion,
      metodo: opcion === 'sat_realizo_restablecimiento' ? metodo : null,
      resultado: meta.resultado,
      observaciones: observaciones || null,
    };

    setGuardando(true);
    try {
      await ordenesAPI.registrarCPI(orden.id, payload);
      toast.success('CPI/NIST registrado correctamente');
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error guardando CPI/NIST');
    } finally {
      setGuardando(false);
    }
  };

  const cpiCompletado = Boolean(orden?.cpi_opcion);

  return (
    <Card data-testid="tecnico-cpi-card">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Shield className="w-4 h-4" />
          Privacidad del Dispositivo (CPI / NIST 800-88)
          {cpiCompletado && (
            <Badge variant="success" className="text-xs">Registrado</Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2" data-testid="cpi-opciones-radio">
          {Object.entries(CPI_OPCIONES).map(([key, opt]) => (
            <label
              key={key}
              className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                opcion === key
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 bg-white'
              }`}
            >
              <input
                type="radio"
                name="cpi_opcion"
                value={key}
                checked={opcion === key}
                onChange={() => setOpcion(key)}
                className="mt-0.5"
                data-testid={`cpi-opcion-${key}`}
              />
              <span className="text-sm font-medium leading-snug">{opt.label}</span>
            </label>
          ))}
        </div>

        {/* Sub-formulario opción SAT */}
        {opcion === 'sat_realizo_restablecimiento' && (
          <div className="ml-6 space-y-2 border-l-2 border-blue-300 pl-3">
            <Label className="text-xs font-semibold">Método de restablecimiento</Label>
            <select
              className="w-full text-sm border rounded px-2 py-1.5"
              value={metodo}
              onChange={(e) => setMetodo(e.target.value)}
              data-testid="cpi-metodo-select"
            >
              <option value="">-- Selecciona método --</option>
              <option value="factory_reset">Factory Reset (iOS/Android)</option>
              <option value="herramienta_validada">Herramienta validada (NIST 800-88)</option>
              <option value="no_aplica_misma_unidad">No aplica – misma unidad restaurada al cliente</option>
            </select>
          </div>
        )}

        <div className="space-y-1">
          <Label className="text-xs">Observaciones (opcional)</Label>
          <Textarea
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
            className="min-h-[60px] text-sm"
            placeholder="Notas adicionales..."
            data-testid="cpi-observaciones-tecnico"
          />
        </div>

        {orden?.cpi_fecha && (
          <p className="text-xs text-gray-400">
            Último registro: {new Date(orden.cpi_fecha).toLocaleString('es-ES')}
          </p>
        )}

        <Button
          onClick={handleGuardar}
          disabled={guardando || !opcion}
          data-testid="cpi-guardar-tecnico-button"
          className="w-full"
        >
          {guardando ? 'Guardando...' : cpiCompletado ? 'Actualizar CPI/NIST' : 'Registrar CPI/NIST'}
        </Button>
      </CardContent>
    </Card>
  );
}

import { useState } from 'react';
import { Truck, Loader2, Download, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import api from '@/lib/api';

/**
 * Botón "Crear etiqueta GLS" — usa el módulo nuevo /api/logistica/gls/*.
 *
 * Flujo:
 *   1. Abre modal con input de peso (kg).
 *   2. POST /api/logistica/gls/crear-envio → { codbarras, etiqueta_pdf_base64, tracking_url, mock_preview }
 *   3. Decodifica base64 → Blob PDF → URL.createObjectURL → abre en pestaña nueva.
 *   4. Muestra resumen con codbarras + tracking_url.
 */
export default function CrearEtiquetaGLSButton({ orden, onCreated }) {
  const [open, setOpen] = useState(false);
  const [peso, setPeso] = useState('1.0');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null); // { codbarras, tracking_url, pdfUrl, mock_preview }

  const abrirPdfDesdeBase64 = (b64) => {
    try {
      const bin = atob(b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const blob = new Blob([bytes], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener,noreferrer');
      return url;
    } catch (e) {
      console.error('Error decodificando PDF base64:', e);
      toast.error('PDF recibido pero no se pudo abrir');
      return null;
    }
  };

  const handleCrear = async () => {
    const pesoNum = parseFloat(peso);
    if (!pesoNum || pesoNum <= 0 || pesoNum > 40) {
      toast.error('Peso inválido (0 < kg ≤ 40)');
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.post('/logistica/gls/crear-envio', {
        order_id: orden.id,
        peso_kg: pesoNum,
      });
      const pdfUrl = abrirPdfDesdeBase64(data.etiqueta_pdf_base64);
      setResult({
        codbarras: data.codbarras,
        tracking_url: data.tracking_url,
        pdfUrl,
        mock_preview: data.mock_preview,
      });
      toast.success(
        data.mock_preview
          ? `Etiqueta (preview/mock) creada · ${data.codbarras}`
          : `Etiqueta GLS creada · ${data.codbarras}`,
      );
      if (onCreated) onCreated(data);
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || 'Error desconocido';
      toast.error(`No se pudo crear la etiqueta: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const resetYCerrar = () => {
    setOpen(false);
    setResult(null);
    setPeso('1.0');
  };

  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="gap-2 border-blue-300 text-blue-700 hover:bg-blue-50"
        onClick={() => setOpen(true)}
        data-testid="btn-crear-etiqueta-gls-v2"
      >
        <Truck className="w-4 h-4" />
        Crear etiqueta GLS
      </Button>

      <Dialog open={open} onOpenChange={(v) => (v ? setOpen(true) : resetYCerrar())}>
        <DialogContent className="sm:max-w-md" data-testid="dialog-crear-etiqueta-gls">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Truck className="w-5 h-5 text-blue-600" />
              Crear etiqueta GLS
            </DialogTitle>
            <DialogDescription>
              Orden <span className="font-mono">{orden?.numero_orden || orden?.id}</span>.
              Se enviará a la dirección del cliente registrada en la ficha.
            </DialogDescription>
          </DialogHeader>

          {!result ? (
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="gls-peso">Peso (kg)</Label>
                <Input
                  id="gls-peso"
                  type="number"
                  min="0.1"
                  max="40"
                  step="0.1"
                  value={peso}
                  onChange={(e) => setPeso(e.target.value)}
                  disabled={loading}
                  data-testid="input-peso-gls"
                />
                <p className="text-xs text-muted-foreground">
                  Rango admitido: 0,1 a 40 kg. El destinatario se toma del cliente asociado a la orden.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3 py-2" data-testid="result-etiqueta-gls">
              {result.mock_preview && (
                <Badge variant="outline" className="border-amber-400 bg-amber-50 text-amber-800">
                  Modo preview · etiqueta mock (no se ha llamado a GLS real)
                </Badge>
              )}
              <div className="rounded-md border bg-slate-50 p-3 space-y-2 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground">Código de barras</span>
                  <span className="font-mono font-semibold" data-testid="result-codbarras">
                    {result.codbarras}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground">Tracking</span>
                  <a
                    href={result.tracking_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-blue-600 hover:underline text-xs"
                    data-testid="link-tracking-gls"
                  >
                    Abrir en GLS <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
              {result.pdfUrl && (
                <Button
                  type="button"
                  variant="secondary"
                  className="w-full gap-2"
                  onClick={() => window.open(result.pdfUrl, '_blank', 'noopener,noreferrer')}
                  data-testid="btn-reabrir-pdf-gls"
                >
                  <Download className="w-4 h-4" /> Reabrir PDF
                </Button>
              )}
            </div>
          )}

          <DialogFooter>
            {!result ? (
              <>
                <Button variant="ghost" onClick={resetYCerrar} disabled={loading}
                        data-testid="btn-cancelar-etiqueta-gls">
                  Cancelar
                </Button>
                <Button onClick={handleCrear} disabled={loading}
                        data-testid="btn-confirmar-crear-etiqueta-gls">
                  {loading ? (
                    <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Creando…</>
                  ) : (
                    'Crear etiqueta'
                  )}
                </Button>
              </>
            ) : (
              <Button onClick={resetYCerrar} data-testid="btn-cerrar-etiqueta-gls">
                Cerrar
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

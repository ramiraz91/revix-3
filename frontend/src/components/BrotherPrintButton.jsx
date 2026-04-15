import { useState, useEffect, useCallback, useRef } from 'react';
import { Printer, CheckCircle2, XCircle, Loader2, RefreshCw, AlertTriangle, Wifi, WifiOff, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';

const AGENT_URL = 'http://127.0.0.1:5555';
const POLL_INTERVAL = 15000; // 15s

/**
 * BrotherPrintButton
 *
 * Componente de impresion directa Brother QL-800.
 * Se comunica con el agente local en localhost:5555.
 *
 * Props:
 *   - orden: objeto de la orden de trabajo
 *   - mode: 'ot' | 'inventory'
 *   - inventoryData: { sku, nombre, precio } (solo si mode='inventory')
 */
export function BrotherPrintButton({ orden, mode = 'ot', inventoryData }) {
  const [agentStatus, setAgentStatus] = useState('checking'); // 'checking' | 'online' | 'offline' | 'printer_error'
  const [printerName, setPrinterName] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [printing, setPrinting] = useState(false);
  const [testing, setTesting] = useState(false);
  const [lastPrint, setLastPrint] = useState(null);
  const pollRef = useRef(null);

  // ------------------------------------------------------------------
  // Health check
  // ------------------------------------------------------------------
  const checkHealth = useCallback(async () => {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3000);

      const res = await fetch(`${AGENT_URL}/health`, {
        signal: controller.signal,
      });
      clearTimeout(timeout);

      if (!res.ok) throw new Error('Agent error');

      const data = await res.json();
      setPrinterName(data.defaultPrinter || '');

      if (data.ok && data.printerOnline) {
        setAgentStatus('online');
        setStatusMessage('');
      } else if (data.ok && !data.printerOnline) {
        setAgentStatus('printer_error');
        setStatusMessage(data.reason || 'Impresora no disponible');
      } else {
        setAgentStatus('offline');
        setStatusMessage(data.error || 'Error del agente');
      }
    } catch {
      setAgentStatus('offline');
      setStatusMessage('');
    }
  }, []);

  useEffect(() => {
    checkHealth();
    pollRef.current = setInterval(checkHealth, POLL_INTERVAL);
    return () => clearInterval(pollRef.current);
  }, [checkHealth]);

  // ------------------------------------------------------------------
  // Imprimir etiqueta
  // ------------------------------------------------------------------
  const handlePrint = async () => {
    if (agentStatus !== 'online') {
      toast.error('El agente de impresion no esta conectado');
      return;
    }

    setPrinting(true);
    try {
      let payload;

      if (mode === 'inventory' && inventoryData) {
        payload = {
          printerName,
          template: 'inventory_label',
          jobId: `inv-${inventoryData.sku || 'x'}`,
          data: {
            barcodeValue: inventoryData.sku || inventoryData.id || 'SIN-SKU',
            productName: inventoryData.nombre || '',
            price: inventoryData.precio ? `${inventoryData.precio} EUR` : '',
          },
        };
      } else {
        payload = {
          printerName,
          template: 'ot_barcode_minimal',
          jobId: `ot-${orden?.numero_orden || 'x'}`,
          data: {
            orderId: orden?.id || '',
            orderNumber: orden?.numero_orden || '',
            barcodeValue: orden?.id || orden?.numero_orden || '',
            deviceModel: orden?.dispositivo?.modelo || orden?.dispositivo_modelo || '',
          },
        };
      }

      const res = await fetch(`${AGENT_URL}/print`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (data.ok && data.printed) {
        setLastPrint(new Date().toLocaleTimeString('es-ES'));
        toast.success('Etiqueta impresa correctamente');
      } else {
        toast.error(data.error || 'Error al imprimir');
      }
    } catch (err) {
      toast.error('No se pudo conectar con el agente de impresion');
    } finally {
      setPrinting(false);
    }
  };

  // ------------------------------------------------------------------
  // Prueba de impresion
  // ------------------------------------------------------------------
  const handleTestPrint = async () => {
    setTesting(true);
    try {
      const res = await fetch(`${AGENT_URL}/test-print`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ printerName }),
      });

      const data = await res.json();
      if (data.ok && data.printed) {
        toast.success('Etiqueta de prueba impresa');
      } else {
        toast.error(data.error || 'Error en la prueba');
      }
    } catch {
      toast.error('No se pudo conectar con el agente');
    } finally {
      setTesting(false);
    }
  };

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------
  const statusConfig = {
    checking: { icon: Loader2, color: 'text-slate-400', bg: 'bg-slate-50', label: 'Verificando agente...', spin: true },
    online:   { icon: Wifi, color: 'text-emerald-600', bg: 'bg-emerald-50', label: 'Impresora conectada', spin: false },
    offline:  { icon: WifiOff, color: 'text-red-500', bg: 'bg-red-50', label: 'Agente no detectado', spin: false },
    printer_error: { icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50', label: 'Error de impresora', spin: false },
  };

  const cfg = statusConfig[agentStatus];
  const StatusIcon = cfg.icon;
  const canPrint = agentStatus === 'online';

  return (
    <Card data-testid="brother-print-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Printer className="w-4 h-4" />
            Impresion Directa
          </span>
          <button
            onClick={checkHealth}
            className="p-1 rounded hover:bg-slate-100 transition-colors"
            title="Actualizar estado"
            data-testid="brother-refresh-status"
          >
            <RefreshCw className="w-3.5 h-3.5 text-muted-foreground" />
          </button>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Estado */}
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${cfg.bg}`} data-testid="brother-status">
          <StatusIcon className={`w-4 h-4 ${cfg.color} ${cfg.spin ? 'animate-spin' : ''}`} />
          <div className="flex-1 min-w-0">
            <p className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</p>
            {agentStatus === 'online' && printerName && (
              <p className="text-[10px] text-muted-foreground truncate">{printerName} &middot; DK-11204</p>
            )}
            {statusMessage && agentStatus !== 'online' && (
              <p className="text-[10px] text-muted-foreground truncate">{statusMessage}</p>
            )}
          </div>
        </div>

        {/* Agente offline: instrucciones */}
        {agentStatus === 'offline' && (
          <div className="text-[11px] text-muted-foreground space-y-1 px-1">
            <p>El agente local no responde en <code className="text-xs bg-slate-100 px-1 rounded">127.0.0.1:5555</code></p>
            <p>Ejecute <strong>start.bat</strong> en el PC del taller.</p>
          </div>
        )}

        {/* Botones */}
        <div className="flex gap-2">
          <Button
            size="sm"
            className="flex-1"
            onClick={handlePrint}
            disabled={!canPrint || printing}
            data-testid="brother-print-btn"
          >
            {printing ? (
              <>
                <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                Imprimiendo...
              </>
            ) : (
              <>
                <Printer className="w-4 h-4 mr-1.5" />
                Imprimir Etiqueta
              </>
            )}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleTestPrint}
            disabled={!canPrint || testing}
            title="Imprimir etiqueta de prueba"
            data-testid="brother-test-btn"
          >
            {testing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
          </Button>
        </div>

        {/* Ultimo trabajo */}
        {lastPrint && (
          <div className="flex items-center gap-1.5 text-[10px] text-emerald-600" data-testid="brother-last-print">
            <CheckCircle2 className="w-3 h-3" />
            Ultima impresion: {lastPrint}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

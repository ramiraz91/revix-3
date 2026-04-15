import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Printer, CheckCircle2, XCircle, Loader2, RefreshCw,
  AlertTriangle, Wifi, WifiOff, Download, Clock, History,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import api from '@/lib/api';

const API = process.env.REACT_APP_BACKEND_URL;
const POLL_STATUS = 12000; // 12s

/**
 * BrotherPrintButton — Impresion centralizada Brother QL-800.
 *
 * Flujo:
 *   1. Frontend -> POST /api/print/send (backend CRM, JWT)
 *   2. Backend guarda job en MongoDB (status: pending)
 *   3. Agente del taller hace polling, imprime, reporta
 *   4. Frontend consulta GET /api/print/status para estado
 *
 * Funciona desde CUALQUIER dispositivo con sesion activa.
 */
export function BrotherPrintButton({ orden, mode = 'ot', inventoryData }) {
  const [agentStatus, setAgentStatus] = useState('checking');
  const [printerName, setPrinterName] = useState('');
  const [statusMsg, setStatusMsg] = useState('');
  const [printing, setPrinting] = useState(false);
  const [lastResult, setLastResult] = useState(null); // {ok, time, jobId}
  const [jobPolling, setJobPolling] = useState(null); // job_id en espera
  const pollRef = useRef(null);
  const jobPollRef = useRef(null);

  // ── Check status via backend ────────────────────────────────────
  const checkStatus = useCallback(async () => {
    try {
      const res = await api.get(`${API}/api/print/status`);
      const d = res.data;
      setPrinterName(d.printer_name || '');
      if (d.agent_connected && d.printer_online) {
        setAgentStatus('online');
        setStatusMsg('');
      } else if (d.agent_connected && !d.printer_online) {
        setAgentStatus('printer_error');
        setStatusMsg(d.reason || 'Impresora no disponible');
      } else {
        setAgentStatus('offline');
        setStatusMsg(d.message || 'Agente no conectado');
      }
    } catch {
      setAgentStatus('offline');
      setStatusMsg('No se pudo consultar el estado');
    }
  }, []);

  useEffect(() => {
    checkStatus();
    pollRef.current = setInterval(checkStatus, POLL_STATUS);
    return () => clearInterval(pollRef.current);
  }, [checkStatus]);

  // ── Poll job result ─────────────────────────────────────────────
  useEffect(() => {
    if (!jobPolling) return;
    let attempts = 0;
    const maxAttempts = 20; // 20 * 1.5s = 30s max

    jobPollRef.current = setInterval(async () => {
      attempts++;
      try {
        const res = await api.get(`${API}/api/print/job/${jobPolling}`);
        const job = res.data.job;
        if (job.status === 'completed') {
          clearInterval(jobPollRef.current);
          setJobPolling(null);
          setPrinting(false);
          setLastResult({ ok: true, time: new Date().toLocaleTimeString('es-ES'), jobId: jobPolling });
          toast.success('Etiqueta impresa correctamente');
        } else if (job.status === 'error') {
          clearInterval(jobPollRef.current);
          setJobPolling(null);
          setPrinting(false);
          setLastResult({ ok: false, time: new Date().toLocaleTimeString('es-ES'), jobId: jobPolling });
          toast.error(job.error_message || 'Error al imprimir');
        }
      } catch { /* keep polling */ }

      if (attempts >= maxAttempts) {
        clearInterval(jobPollRef.current);
        setJobPolling(null);
        setPrinting(false);
        toast.warning('La impresion esta en cola. Se procesara cuando el agente responda.');
      }
    }, 1500);

    return () => clearInterval(jobPollRef.current);
  }, [jobPolling]);

  // ── Send print job ──────────────────────────────────────────────
  const handlePrint = async () => {
    setPrinting(true);
    setLastResult(null);

    try {
      let payload;
      if (mode === 'inventory' && inventoryData) {
        payload = {
          template: 'inventory_label',
          data: {
            barcodeValue: inventoryData.sku || inventoryData.id || 'SIN-SKU',
            productName: inventoryData.nombre || '',
            price: inventoryData.precio ? `${inventoryData.precio} EUR` : '',
          },
        };
      } else {
        // Usar numero_autorizacion como barcode (mas corto, mejor calidad)
        const barcodeVal = orden?.numero_autorizacion || orden?.numero_orden || orden?.id || '';
        payload = {
          template: 'ot_barcode_minimal',
          data: {
            orderId: orden?.id || '',
            orderNumber: orden?.numero_orden || '',
            barcodeValue: barcodeVal,
            deviceModel: orden?.dispositivo?.modelo || orden?.dispositivo_modelo || '',
          },
        };
      }

      const res = await api.post(`${API}/api/print/send`, payload);
      const d = res.data;

      if (d.ok) {
        toast.info('Trabajo enviado a la impresora...');
        setJobPolling(d.job_id);
      } else {
        setPrinting(false);
        toast.error('Error al enviar el trabajo');
      }
    } catch (err) {
      setPrinting(false);
      const msg = err?.response?.data?.detail || 'Error de comunicacion con el servidor';
      toast.error(msg);
    }
  };

  // ── Test print ──────────────────────────────────────────────────
  const handleTestPrint = async () => {
    try {
      const res = await api.post(`${API}/api/print/send`, {
        template: 'ot_barcode_minimal',
        data: {
          barcodeValue: 'TEST-BROTHER-QL800',
          orderNumber: 'OT-TEST-001',
          deviceModel: 'Test Label - Brother QL-800',
        },
      });
      if (res.data.ok) {
        toast.info('Prueba enviada a la impresora');
      }
    } catch {
      toast.error('Error al enviar prueba');
    }
  };

  // ── Download agent ──────────────────────────────────────────────
  const handleDownload = () => {
    window.open(`${API}/api/print/agent/download`, '_blank');
  };

  // ── Render ──────────────────────────────────────────────────────
  const cfg = {
    checking:      { icon: Loader2,        color: 'text-slate-400',   bg: 'bg-slate-50',   label: 'Verificando agente...', spin: true },
    online:        { icon: Wifi,           color: 'text-emerald-600', bg: 'bg-emerald-50',  label: 'Impresora conectada',   spin: false },
    offline:       { icon: WifiOff,        color: 'text-red-500',     bg: 'bg-red-50',      label: 'Agente no conectado',   spin: false },
    printer_error: { icon: AlertTriangle,  color: 'text-amber-600',   bg: 'bg-amber-50',    label: 'Error de impresora',    spin: false },
  }[agentStatus];

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
            onClick={checkStatus}
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
          <StatusIcon className={`w-4 h-4 flex-shrink-0 ${cfg.color} ${cfg.spin ? 'animate-spin' : ''}`} />
          <div className="flex-1 min-w-0">
            <p className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</p>
            {agentStatus === 'online' && printerName && (
              <p className="text-[10px] text-muted-foreground truncate">{printerName} &middot; DK-11204</p>
            )}
            {statusMsg && agentStatus !== 'online' && (
              <p className="text-[10px] text-muted-foreground truncate">{statusMsg}</p>
            )}
          </div>
        </div>

        {/* Instrucciones offline + descarga */}
        {agentStatus === 'offline' && (
          <div className="space-y-2">
            <p className="text-[11px] text-muted-foreground px-1">
              Instale y ejecute el agente en el PC del taller donde esta la Brother QL-800.
            </p>
            <Button
              size="sm"
              variant="outline"
              className="w-full text-xs"
              onClick={handleDownload}
              data-testid="brother-download-btn"
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              Descargar Agente de Impresion
            </Button>
          </div>
        )}

        {/* Botones de impresion */}
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
            disabled={!canPrint}
            title="Enviar etiqueta de prueba"
            data-testid="brother-test-btn"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>

        {/* Resultado ultima impresion */}
        {lastResult && (
          <div
            className={`flex items-center gap-1.5 text-[10px] ${lastResult.ok ? 'text-emerald-600' : 'text-red-500'}`}
            data-testid="brother-last-print"
          >
            {lastResult.ok ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
            {lastResult.ok ? 'Impresa' : 'Error'} a las {lastResult.time}
          </div>
        )}

        {/* Info */}
        <p className="text-[10px] text-muted-foreground text-center">
          Accesible desde cualquier sesion del CRM
        </p>
      </CardContent>
    </Card>
  );
}

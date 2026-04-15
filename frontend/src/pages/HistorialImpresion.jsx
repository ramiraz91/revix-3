import { useState, useEffect, useCallback } from 'react';
import {
  Printer, CheckCircle2, XCircle, Clock, RefreshCw, Download,
  ChevronLeft, ChevronRight, Wifi, WifiOff, AlertTriangle, Filter,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import api from '@/lib/api';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const PAGE_SIZE = 20;

export default function HistorialImpresion() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [agentStatus, setAgentStatus] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(1);

  // ── Cargar estado del agente ─────────────────────────────────
  const loadStatus = useCallback(async () => {
    try {
      const res = await api.get(`${API}/api/print/status`);
      setAgentStatus(res.data);
    } catch {
      setAgentStatus(null);
    }
  }, []);

  // ── Cargar trabajos ──────────────────────────────────────────
  const loadJobs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`${API}/api/print/jobs?limit=100`);
      setJobs(res.data.jobs || []);
    } catch {
      toast.error('Error al cargar el historial');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
    loadJobs();
  }, [loadStatus, loadJobs]);

  // ── Filtrar ──────────────────────────────────────────────────
  const filtered = statusFilter === 'all'
    ? jobs
    : jobs.filter(j => j.status === statusFilter);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // ── Reimprimir ───────────────────────────────────────────────
  const handleReprint = async (job) => {
    try {
      const res = await api.post(`${API}/api/print/send`, {
        template: job.template,
        data: job.data,
      });
      if (res.data.ok) {
        toast.success('Trabajo reenviado a la impresora');
        setTimeout(loadJobs, 2000);
      }
    } catch {
      toast.error('Error al reenviar');
    }
  };

  // ── Status badge ─────────────────────────────────────────────
  const StatusBadge = ({ status }) => {
    const cfg = {
      pending:   { label: 'Pendiente',  icon: Clock,        variant: 'outline',    color: 'text-amber-600' },
      printing:  { label: 'Imprimiendo', icon: Printer,     variant: 'outline',    color: 'text-blue-600' },
      completed: { label: 'Impresa',    icon: CheckCircle2, variant: 'default',    color: 'text-emerald-600' },
      error:     { label: 'Error',      icon: XCircle,      variant: 'destructive', color: 'text-red-600' },
    }[status] || { label: status, icon: Clock, variant: 'outline', color: '' };

    const Icon = cfg.icon;
    return (
      <Badge variant={cfg.variant} className={`gap-1 ${cfg.color}`} data-testid={`job-status-${status}`}>
        <Icon className="w-3 h-3" />
        {cfg.label}
      </Badge>
    );
  };

  // ── Formato fecha ────────────────────────────────────────────
  const fmtDate = (d) => {
    if (!d) return '-';
    return new Date(d).toLocaleString('es-ES', {
      day: '2-digit', month: '2-digit', year: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  };

  // ── Stats ────────────────────────────────────────────────────
  const stats = {
    total: jobs.length,
    completed: jobs.filter(j => j.status === 'completed').length,
    errors: jobs.filter(j => j.status === 'error').length,
    pending: jobs.filter(j => j.status === 'pending' || j.status === 'printing').length,
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="historial-impresion-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Historial de Impresion</h1>
          <p className="text-muted-foreground mt-1">Brother QL-800 — DK-11204</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => { loadStatus(); loadJobs(); }} data-testid="refresh-history">
            <RefreshCw className="w-4 h-4 mr-1" />
            Actualizar
          </Button>
          <Button variant="outline" size="sm" onClick={() => window.open(`${API}/api/print/agent/download`, '_blank')} data-testid="download-agent">
            <Download className="w-4 h-4 mr-1" />
            Descargar Agente
          </Button>
        </div>
      </div>

      {/* KPIs + Estado agente */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {/* Estado del agente */}
        <Card data-testid="agent-status-card">
          <CardContent className="pt-4 pb-3 text-center">
            {agentStatus?.agent_connected ? (
              <>
                <Wifi className="w-6 h-6 text-emerald-500 mx-auto mb-1" />
                <p className="text-sm font-semibold text-emerald-600">Conectado</p>
                <p className="text-[10px] text-muted-foreground">{agentStatus.printer_name || 'Brother QL-800'}</p>
              </>
            ) : (
              <>
                <WifiOff className="w-6 h-6 text-red-500 mx-auto mb-1" />
                <p className="text-sm font-semibold text-red-500">Desconectado</p>
                <p className="text-[10px] text-muted-foreground">Agente no responde</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4 pb-3 text-center">
            <p className="text-2xl font-bold">{stats.total}</p>
            <p className="text-xs text-muted-foreground">Total trabajos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 text-center">
            <p className="text-2xl font-bold text-emerald-600">{stats.completed}</p>
            <p className="text-xs text-muted-foreground">Impresas</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 text-center">
            <p className="text-2xl font-bold text-red-500">{stats.errors}</p>
            <p className="text-xs text-muted-foreground">Errores</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 text-center">
            <p className="text-2xl font-bold text-amber-600">{stats.pending}</p>
            <p className="text-xs text-muted-foreground">Pendientes</p>
          </CardContent>
        </Card>
      </div>

      {/* Filtro + Tabla */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Printer className="w-4 h-4" />
              Trabajos de Impresion
            </CardTitle>
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-muted-foreground" />
              <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1); }}>
                <SelectTrigger className="h-8 w-[150px]" data-testid="status-filter">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="completed">Impresas</SelectItem>
                  <SelectItem value="error">Errores</SelectItem>
                  <SelectItem value="pending">Pendientes</SelectItem>
                  <SelectItem value="printing">Imprimiendo</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : paged.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              No hay trabajos de impresion registrados
            </p>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[140px]">Fecha</TableHead>
                    <TableHead>Usuario</TableHead>
                    <TableHead>Plantilla</TableHead>
                    <TableHead>Referencia</TableHead>
                    <TableHead className="w-[110px]">Estado</TableHead>
                    <TableHead className="w-[140px]">Impresa</TableHead>
                    <TableHead className="w-[70px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paged.map((job) => {
                    const isOT = job.template !== 'inventory_label';
                    const ref = isOT
                      ? (job.data?.orderNumber || job.data?.barcodeValue || '-')
                      : (job.data?.barcodeValue || '-');
                    const desc = isOT
                      ? (job.data?.deviceModel || '')
                      : (job.data?.productName || '');

                    return (
                      <TableRow key={job.job_id} data-testid={`job-row-${job.job_id}`}>
                        <TableCell className="text-xs font-mono">{fmtDate(job.requested_at)}</TableCell>
                        <TableCell className="text-xs">{job.requested_by_name || job.requested_by || '-'}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-[10px]">
                            {isOT ? 'OT' : 'Inventario'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <p className="text-xs font-mono font-semibold">{ref}</p>
                          {desc && <p className="text-[10px] text-muted-foreground truncate max-w-[200px]">{desc}</p>}
                        </TableCell>
                        <TableCell><StatusBadge status={job.status} /></TableCell>
                        <TableCell className="text-xs font-mono">{fmtDate(job.printed_at)}</TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2"
                            onClick={() => handleReprint(job)}
                            title="Reimprimir"
                            data-testid={`reprint-${job.job_id}`}
                          >
                            <Printer className="w-3.5 h-3.5" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>

              {/* Paginacion */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-2 py-3 border-t mt-2">
                  <p className="text-xs text-muted-foreground">
                    {filtered.length} trabajo(s) — Pagina {page} de {totalPages}
                  </p>
                  <div className="flex gap-1">
                    <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Errores recientes */}
          {jobs.filter(j => j.status === 'error').length > 0 && statusFilter === 'all' && (
            <div className="mt-4 p-3 bg-red-50 rounded-lg border border-red-200">
              <p className="text-xs font-semibold text-red-700 flex items-center gap-1 mb-2">
                <AlertTriangle className="w-3.5 h-3.5" />
                Ultimos errores
              </p>
              {jobs.filter(j => j.status === 'error').slice(0, 3).map(j => (
                <p key={j.job_id} className="text-[11px] text-red-600 mb-1">
                  {fmtDate(j.requested_at)} — {j.error_message || 'Error desconocido'}
                </p>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

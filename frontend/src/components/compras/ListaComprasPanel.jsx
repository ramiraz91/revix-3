import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { ShoppingCart, RefreshCw, CheckCircle2, Send, Package, Truck, AlertTriangle, Mail, X, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import API from '@/lib/api';

const URGENCIA_COLORS = {
  critica: 'bg-red-600 hover:bg-red-700 text-white',
  alta: 'bg-orange-500 hover:bg-orange-600 text-white',
  normal: 'bg-yellow-400 hover:bg-yellow-500 text-slate-900',
  baja: 'bg-green-100 hover:bg-green-200 text-green-800 border border-green-300',
};

const ESTADO_COLORS = {
  pendiente: 'bg-slate-200 text-slate-800',
  aprobado: 'bg-blue-200 text-blue-900',
  pedido: 'bg-indigo-200 text-indigo-900',
  recibido: 'bg-green-200 text-green-900',
  cancelado: 'bg-zinc-200 text-zinc-700 line-through',
};

export default function ListaComprasPanel() {
  const [items, setItems] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filtroEstado, setFiltroEstado] = useState('abiertos');
  const [filtroUrgencia, setFiltroUrgencia] = useState('all');
  const [filtroProveedor, setFiltroProveedor] = useState('all');
  const [seleccion, setSeleccion] = useState(new Set());
  const [emailDialog, setEmailDialog] = useState(null);
  const [proveedores, setProveedores] = useState([]);

  const cargar = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filtroEstado === 'abiertos') params.solo_abiertos = true;
      else if (filtroEstado !== 'all') params.estado = filtroEstado;
      if (filtroUrgencia !== 'all') params.urgencia = filtroUrgencia;
      if (filtroProveedor !== 'all') params.proveedor_id = filtroProveedor;
      const qs = new URLSearchParams(params).toString();
      const [{ data }, { data: r }] = await Promise.all([
        API.get(`/compras/lista${qs ? `?${qs}` : ''}`),
        API.get('/compras/lista/resumen'),
      ]);
      setItems(data.items || []);
      setResumen(r);
      setSeleccion(new Set());
    } catch {
      toast.error('Error al cargar lista de compras');
    } finally {
      setLoading(false);
    }
  }, [filtroEstado, filtroUrgencia, filtroProveedor]);

  useEffect(() => {
    cargar();
    API.get('/proveedores').then(({ data }) => setProveedores(data || [])).catch(() => {});
  }, [cargar]);

  const toggleSel = (id) => {
    setSeleccion((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleSelAll = () => {
    setSeleccion((prev) => {
      if (prev.size === items.filter(i => i.estado === 'pendiente').length) return new Set();
      return new Set(items.filter(i => i.estado === 'pendiente').map(i => i.id));
    });
  };

  const aprobarSeleccionadas = async () => {
    if (seleccion.size === 0) return;
    if (!window.confirm(`Aprobar ${seleccion.size} item(s)?`)) return;
    try {
      const { data } = await API.post('/compras/lista/aprobar', { ids: [...seleccion] });
      toast.success(`${data.aprobadas} aprobadas`);
      cargar();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al aprobar');
    }
  };

  const marcarPedido = async (id) => {
    try {
      await API.post(`/compras/lista/${id}/marcar-pedido`);
      toast.success('Marcado como pedido');
      cargar();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  const marcarRecibido = async (it) => {
    const cant = window.prompt(
      `Cantidad recibida para "${it.repuesto_nombre}":`,
      String(it.cantidad),
    );
    if (cant === null) return;
    const cantNum = parseInt(cant, 10);
    if (!cantNum || cantNum < 1) return toast.error('Cantidad inválida');
    try {
      const { data } = await API.post(`/compras/lista/${it.id}/marcar-recibido`,
        { cantidad_recibida: cantNum });
      toast.success(`Recibido ✓ Stock +${data.cantidad_recibida}`);
      cargar();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  const cancelar = async (id) => {
    if (!window.confirm('Cancelar este item?')) return;
    try {
      await API.post(`/compras/lista/${id}/cancelar`);
      toast.success('Cancelado');
      cargar();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  const generarEmail = async (proveedor_id) => {
    try {
      const { data } = await API.get(`/compras/lista/email-pedido/${proveedor_id}`);
      if (!data.ok) {
        toast.error('Sin items pendientes para este proveedor');
        return;
      }
      setEmailDialog(data);
    } catch {
      toast.error('Error generando email');
    }
  };

  const copiarAlPortapapeles = (texto) => {
    navigator.clipboard.writeText(texto).then(
      () => toast.success('Copiado al portapapeles'),
      () => toast.error('No se pudo copiar'),
    );
  };

  const scanStockMin = async () => {
    try {
      const { data } = await API.post('/compras/lista/scan-stock-minimo');
      toast.success(`Scan completado · ${data.creados} nuevos / ${data.actualizados} actualizados`);
      cargar();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  return (
    <div className="space-y-4" data-testid="lista-compras-panel">
      {/* Resumen */}
      {resumen && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <Card className="border-orange-300">
            <CardContent className="p-3 text-center">
              <p className="text-3xl font-bold text-orange-700" data-testid="kpi-total-abiertos">
                {resumen.total_abiertos}
              </p>
              <p className="text-xs text-muted-foreground">Items abiertos</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <p className="text-2xl font-bold text-red-600">{resumen.urgencias?.critica || 0}</p>
              <p className="text-xs text-muted-foreground">Crítica</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <p className="text-2xl font-bold text-orange-500">{resumen.urgencias?.alta || 0}</p>
              <p className="text-xs text-muted-foreground">Alta</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <p className="text-2xl font-bold text-yellow-600">{resumen.urgencias?.normal || 0}</p>
              <p className="text-xs text-muted-foreground">Normal</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <p className="text-2xl font-bold text-indigo-600">{resumen.total_pedidos || 0}</p>
              <p className="text-xs text-muted-foreground">En pedido</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Toolbar */}
      <Card>
        <CardContent className="p-3 flex flex-wrap items-end gap-3">
          <div>
            <Label className="text-xs">Estado</Label>
            <Select value={filtroEstado} onValueChange={setFiltroEstado}>
              <SelectTrigger className="w-40 h-9" data-testid="filter-estado"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="abiertos">Abiertos (default)</SelectItem>
                <SelectItem value="pendiente">Pendientes</SelectItem>
                <SelectItem value="aprobado">Aprobados</SelectItem>
                <SelectItem value="pedido">En pedido</SelectItem>
                <SelectItem value="recibido">Recibidos</SelectItem>
                <SelectItem value="cancelado">Cancelados</SelectItem>
                <SelectItem value="all">Todos</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Urgencia</Label>
            <Select value={filtroUrgencia} onValueChange={setFiltroUrgencia}>
              <SelectTrigger className="w-32 h-9" data-testid="filter-urgencia"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                <SelectItem value="critica">Crítica</SelectItem>
                <SelectItem value="alta">Alta</SelectItem>
                <SelectItem value="normal">Normal</SelectItem>
                <SelectItem value="baja">Baja</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Proveedor</Label>
            <Select value={filtroProveedor} onValueChange={setFiltroProveedor}>
              <SelectTrigger className="w-48 h-9" data-testid="filter-proveedor"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                {proveedores.map((p) => (
                  <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex-1" />
          <Button variant="outline" onClick={cargar} disabled={loading} data-testid="btn-refresh-lista">
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Recargar
          </Button>
          <Button variant="outline" onClick={scanStockMin} data-testid="btn-scan-stock">
            <AlertTriangle className="w-4 h-4 mr-2" />
            Scan stock mínimo
          </Button>
          <Button
            disabled={seleccion.size === 0}
            onClick={aprobarSeleccionadas}
            className="bg-blue-600 hover:bg-blue-700"
            data-testid="btn-aprobar-seleccion"
          >
            <CheckCircle2 className="w-4 h-4 mr-2" />
            Aprobar {seleccion.size > 0 ? `(${seleccion.size})` : 'seleccionadas'}
          </Button>
        </CardContent>
      </Card>

      {/* Email proveedor — accesos rápidos */}
      {resumen?.proveedores_pendientes?.length > 0 && (
        <Card>
          <CardContent className="p-3">
            <div className="flex items-center gap-2 mb-2">
              <Mail className="w-4 h-4 text-blue-600" />
              <p className="text-sm font-semibold">Generar email de pedido por proveedor</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {resumen.proveedores_pendientes.filter(p => p.proveedor_id).map((p) => (
                <Button
                  key={p.proveedor_id} variant="outline" size="sm"
                  onClick={() => generarEmail(p.proveedor_id)}
                  data-testid={`btn-email-proveedor-${p.proveedor_id}`}
                >
                  <Send className="w-3 h-3 mr-1.5" />
                  {p.proveedor_nombre} <span className="ml-1 text-xs text-muted-foreground">({p.items})</span>
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabla */}
      <Card>
        <CardContent className="p-0">
          {items.length === 0 && !loading && (
            <div className="text-center py-12 text-muted-foreground">
              <ShoppingCart className="w-10 h-10 mx-auto mb-2 opacity-30" />
              <p>Lista vacía. Cuando alguna pieza llegue a stock mínimo o el triador detecte falta, aparecerá aquí.</p>
            </div>
          )}
          {items.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 border-b">
                  <tr>
                    <th className="p-2 w-8">
                      <input
                        type="checkbox"
                        onChange={toggleSelAll}
                        checked={seleccion.size > 0 && seleccion.size === items.filter(i => i.estado === 'pendiente').length}
                        data-testid="check-select-all"
                      />
                    </th>
                    <th className="p-2 text-left">Pieza</th>
                    <th className="p-2 text-center">Cant</th>
                    <th className="p-2 text-center">Urg</th>
                    <th className="p-2 text-left">Proveedor</th>
                    <th className="p-2 text-center">Estado</th>
                    <th className="p-2 text-left">OTs</th>
                    <th className="p-2 text-left">Origen</th>
                    <th className="p-2 text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it) => (
                    <tr key={it.id} className="border-b hover:bg-slate-50" data-testid={`row-lista-${it.id}`}>
                      <td className="p-2">
                        {it.estado === 'pendiente' && (
                          <input
                            type="checkbox"
                            checked={seleccion.has(it.id)}
                            onChange={() => toggleSel(it.id)}
                            data-testid={`check-${it.id}`}
                          />
                        )}
                      </td>
                      <td className="p-2">
                        <div className="font-medium">{it.repuesto_nombre || '—'}</div>
                        {it.repuesto_sku && (
                          <div className="text-[11px] text-muted-foreground font-mono">{it.repuesto_sku}</div>
                        )}
                      </td>
                      <td className="p-2 text-center font-bold">{it.cantidad}</td>
                      <td className="p-2 text-center">
                        <Badge className={URGENCIA_COLORS[it.urgencia] || ''}>{it.urgencia}</Badge>
                      </td>
                      <td className="p-2 text-xs">{it.proveedor_nombre || '—'}</td>
                      <td className="p-2 text-center">
                        <Badge className={ESTADO_COLORS[it.estado] || ''}>{it.estado}</Badge>
                      </td>
                      <td className="p-2 text-[11px]">
                        {(it.ordenes_relacionadas || []).slice(0, 2).join(', ')}
                        {(it.ordenes_relacionadas || []).length > 2 && (
                          <span className="text-muted-foreground"> +{it.ordenes_relacionadas.length - 2}</span>
                        )}
                      </td>
                      <td className="p-2 text-[11px] text-muted-foreground">{it.fuente?.replace('auto_', 'auto·') || '—'}</td>
                      <td className="p-2 text-right">
                        <div className="inline-flex gap-1">
                          {(it.estado === 'pendiente' || it.estado === 'aprobado') && (
                            <Button size="sm" variant="outline" className="h-7 text-[11px]"
                                    onClick={() => marcarPedido(it.id)}
                                    data-testid={`btn-pedido-${it.id}`}>
                              <Send className="w-3 h-3 mr-1" /> Pedido
                            </Button>
                          )}
                          {(it.estado === 'aprobado' || it.estado === 'pedido') && (
                            <Button size="sm" className="h-7 text-[11px] bg-green-600 hover:bg-green-700"
                                    onClick={() => marcarRecibido(it)}
                                    data-testid={`btn-recibido-${it.id}`}>
                              <Truck className="w-3 h-3 mr-1" /> Recibido
                            </Button>
                          )}
                          {it.estado !== 'recibido' && it.estado !== 'cancelado' && (
                            <Button size="sm" variant="ghost" className="h-7 w-7 p-0"
                                    onClick={() => cancelar(it.id)}
                                    data-testid={`btn-cancelar-${it.id}`}>
                              <Trash2 className="w-3 h-3" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialog email */}
      <Dialog open={!!emailDialog} onOpenChange={(open) => !open && setEmailDialog(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Email de pedido — {emailDialog?.proveedor?.nombre}</DialogTitle>
          </DialogHeader>
          {emailDialog && (
            <div className="space-y-3">
              <div>
                <Label className="text-xs">Para</Label>
                <Input value={emailDialog.proveedor?.email || '— sin email registrado —'} readOnly />
              </div>
              <div>
                <Label className="text-xs">Asunto</Label>
                <Input value={emailDialog.asunto} readOnly data-testid="email-dialog-asunto" />
              </div>
              <div>
                <Label className="text-xs">Cuerpo</Label>
                <Textarea value={emailDialog.cuerpo_text} readOnly className="font-mono text-xs h-72"
                          data-testid="email-dialog-cuerpo" />
              </div>
              <p className="text-[11px] text-muted-foreground">
                Total estimado: {emailDialog.total_estimado?.toLocaleString('es-ES', { minimumFractionDigits: 2 })} € · {emailDialog.total_items} items
              </p>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEmailDialog(null)}><X className="w-4 h-4 mr-1" />Cerrar</Button>
            <Button onClick={() => copiarAlPortapapeles(`${emailDialog.asunto}\n\n${emailDialog.cuerpo_text}`)}
                    data-testid="btn-copiar-email">
              <Mail className="w-4 h-4 mr-1" />Copiar email completo
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

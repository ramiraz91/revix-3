/**
 * Página de Liquidaciones - Solo para Master
 * Gestión de pagos mensuales de siniestros Insurama
 */
import { useState, useEffect, useRef } from 'react';
import {
  Receipt,
  Upload,
  Download,
  Check,
  Clock,
  AlertTriangle,
  FileSpreadsheet,
  Calendar,
  Euro,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertCircle,
  FileWarning,
  Shield
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { liquidacionesAPI } from '@/lib/api';
import { toast } from 'sonner';

export default function Liquidaciones() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [mesSeleccionado, setMesSeleccionado] = useState(getMesActual());
  const [tabActiva, setTabActiva] = useState('pendientes');
  const [busqueda, setBusqueda] = useState('');
  const [seleccionados, setSeleccionados] = useState([]);
  const [historialMeses, setHistorialMeses] = useState([]);
  
  // Modal de garantía
  const [showGarantiaModal, setShowGarantiaModal] = useState(false);
  const [garantiaItem, setGarantiaItem] = useState(null);
  const [garantiaForm, setGarantiaForm] = useState({
    tiene_garantia: false,
    codigo_garantia: '',
    costes_garantia: 0
  });
  
  // Modal de notas/reclamación
  const [showNotasModal, setShowNotasModal] = useState(false);
  const [notasItem, setNotasItem] = useState(null);
  const [notasForm, setNotasForm] = useState({ notas: '', estado: 'reclamado' });
  
  // Import
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    cargarDatos();
    cargarHistorial();
  }, []);

  function getMesActual() {
    return new Date().toISOString().slice(0, 7);
  }

  function getMesAnterior(mes) {
    const [year, month] = mes.split('-').map(Number);
    const date = new Date(year, month - 2, 1);
    return date.toISOString().slice(0, 7);
  }

  function getMesSiguiente(mes) {
    const [year, month] = mes.split('-').map(Number);
    const date = new Date(year, month, 1);
    return date.toISOString().slice(0, 7);
  }

  function formatMes(mes) {
    if (!mes) return '';
    const [year, month] = mes.split('-');
    const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                   'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
    return `${meses[parseInt(month) - 1]} ${year}`;
  }

  const cargarDatos = async () => {
    try {
      setLoading(true);
      const res = await liquidacionesAPI.getPendientes();
      setData(res);
    } catch (error) {
      console.error('Error cargando datos:', error);
      toast.error('Error al cargar liquidaciones');
    } finally {
      setLoading(false);
    }
  };

  const cargarHistorial = async () => {
    try {
      const res = await liquidacionesAPI.getHistorialMeses();
      setHistorialMeses(res.meses || []);
    } catch (error) {
      console.error('Error cargando historial:', error);
    }
  };

  const handleImportarExcel = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setImporting(true);
    try {
      const res = await liquidacionesAPI.importarExcel(file, mesSeleccionado);
      toast.success(`Importados ${res.importados} siniestros, ${res.actualizados} actualizados. Total: ${res.total_importe}€`);
      cargarDatos();
      cargarHistorial();
    } catch (error) {
      console.error('Error importando:', error);
      toast.error(error.response?.data?.detail || 'Error al importar archivo');
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleMarcarPagados = async () => {
    if (seleccionados.length === 0) {
      toast.warning('Selecciona al menos un siniestro');
      return;
    }
    
    try {
      await liquidacionesAPI.marcarPagados(seleccionados, mesSeleccionado);
      toast.success(`${seleccionados.length} siniestros marcados como pagados`);
      setSeleccionados([]);
      cargarDatos();
      cargarHistorial();
    } catch (error) {
      toast.error('Error al marcar pagados');
    }
  };

  const handleCambiarEstado = async (codigo, nuevoEstado, notas = null) => {
    try {
      await liquidacionesAPI.actualizarEstado(codigo, nuevoEstado, notas);
      toast.success(`Estado actualizado: ${nuevoEstado}`);
      cargarDatos();
    } catch (error) {
      toast.error('Error al actualizar estado');
    }
  };

  const handleGuardarGarantia = async () => {
    if (!garantiaItem) return;
    
    try {
      await liquidacionesAPI.actualizarGarantia(
        garantiaItem.codigo_siniestro,
        garantiaForm.tiene_garantia,
        garantiaForm.codigo_garantia,
        garantiaForm.costes_garantia
      );
      toast.success('Garantía actualizada');
      setShowGarantiaModal(false);
      cargarDatos();
    } catch (error) {
      toast.error('Error al actualizar garantía');
    }
  };

  const handleGuardarNotas = async () => {
    if (!notasItem) return;
    
    try {
      await liquidacionesAPI.actualizarEstado(
        notasItem.codigo_siniestro,
        notasForm.estado,
        notasForm.notas
      );
      toast.success('Reclamación registrada');
      setShowNotasModal(false);
      cargarDatos();
    } catch (error) {
      toast.error('Error al registrar reclamación');
    }
  };

  const abrirGarantiaModal = (item) => {
    setGarantiaItem(item);
    setGarantiaForm({
      tiene_garantia: item.tiene_garantia || false,
      codigo_garantia: item.codigo_garantia || '',
      costes_garantia: item.costes_garantia || 0
    });
    setShowGarantiaModal(true);
  };

  const abrirNotasModal = (item) => {
    setNotasItem(item);
    setNotasForm({
      notas: item.notas || '',
      estado: item.estado_liquidacion === 'en_resolucion' ? 'en_resolucion' : 'reclamado'
    });
    setShowNotasModal(true);
  };

  const toggleSeleccion = (codigo) => {
    setSeleccionados(prev => 
      prev.includes(codigo) 
        ? prev.filter(c => c !== codigo)
        : [...prev, codigo]
    );
  };

  const toggleSeleccionTodos = (items) => {
    const codigos = items.map(i => i.codigo_siniestro);
    const todosSeleccionados = codigos.every(c => seleccionados.includes(c));
    
    if (todosSeleccionados) {
      setSeleccionados(prev => prev.filter(c => !codigos.includes(c)));
    } else {
      setSeleccionados(prev => [...new Set([...prev, ...codigos])]);
    }
  };

  // Filtrar por búsqueda
  const filtrarItems = (items) => {
    if (!busqueda) return items;
    const term = busqueda.toLowerCase();
    return items.filter(i => 
      i.codigo_siniestro?.toLowerCase().includes(term) ||
      i.cliente?.toLowerCase().includes(term) ||
      i.dispositivo?.toLowerCase().includes(term)
    );
  };

  const pendientes = filtrarItems(data?.pendientes || []);
  const pagados = filtrarItems(data?.pagados || []);
  const reclamados = filtrarItems(data?.reclamados || []);
  const impagados = data?.impagados || [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="liquidaciones-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Receipt className="w-8 h-8 text-green-600" />
            Liquidaciones Insurama
          </h1>
          <p className="text-muted-foreground mt-1">
            Gestión de pagos mensuales de siniestros
          </p>
        </div>
        <div className="flex gap-2">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleImportarExcel}
            accept=".xlsx,.xls"
            className="hidden"
          />
          <Button 
            variant="outline" 
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
          >
            {importing ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Upload className="w-4 h-4 mr-2" />}
            Importar Excel
          </Button>
          <Button onClick={cargarDatos}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Actualizar
          </Button>
        </div>
      </div>

      {/* Alertas de impagados */}
      {impagados.length > 0 && (
        <Card className="border-red-300 bg-red-50">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-6 h-6 text-red-600" />
              <div>
                <p className="font-medium text-red-800">
                  {impagados.length} siniestro(s) con más de 60 días sin pagar
                </p>
                <p className="text-sm text-red-600">
                  Importe pendiente: {impagados.reduce((sum, i) => sum + (i.importe || 0), 0).toFixed(2)}€
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-amber-600">
              <Clock className="w-5 h-5" />
              <span className="text-sm font-medium">Pendientes</span>
            </div>
            <p className="text-2xl font-bold mt-1">{data?.resumen?.total_pendientes || 0}</p>
            <p className="text-xs text-muted-foreground">
              {(data?.resumen?.importe_pendiente || 0).toFixed(2)}€
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-green-600">
              <CheckCircle2 className="w-5 h-5" />
              <span className="text-sm font-medium">Pagados</span>
            </div>
            <p className="text-2xl font-bold mt-1">{data?.resumen?.total_pagados || 0}</p>
            <p className="text-xs text-muted-foreground">
              {(data?.resumen?.importe_pagado || 0).toFixed(2)}€
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-orange-600">
              <AlertCircle className="w-5 h-5" />
              <span className="text-sm font-medium">Reclamados</span>
            </div>
            <p className="text-2xl font-bold mt-1">{data?.resumen?.total_reclamados || 0}</p>
            <p className="text-xs text-muted-foreground">
              {(data?.resumen?.importe_reclamado || 0).toFixed(2)}€
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-red-600">
              <FileWarning className="w-5 h-5" />
              <span className="text-sm font-medium">Impagados (+60d)</span>
            </div>
            <p className="text-2xl font-bold mt-1">{data?.resumen?.total_impagados || 0}</p>
            <p className="text-xs text-muted-foreground">Requieren reclamación</p>
          </CardContent>
        </Card>
      </div>

      {/* Selector de mes y búsqueda */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => setMesSeleccionado(getMesAnterior(mesSeleccionado))}>
            <ChevronLeft className="w-4 h-4" />
          </Button>
          <div className="flex items-center gap-2 px-4 py-2 border rounded-md bg-white">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <span className="font-medium">{formatMes(mesSeleccionado)}</span>
          </div>
          <Button variant="outline" size="icon" onClick={() => setMesSeleccionado(getMesSiguiente(mesSeleccionado))}>
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
        
        <div className="flex-1 max-w-sm">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Buscar código, cliente o dispositivo..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {seleccionados.length > 0 && (
          <Button onClick={handleMarcarPagados} className="bg-green-600 hover:bg-green-700">
            <Check className="w-4 h-4 mr-2" />
            Marcar {seleccionados.length} como pagados
          </Button>
        )}
      </div>

      {/* Tabs de estados */}
      <Tabs value={tabActiva} onValueChange={setTabActiva}>
        <TabsList>
          <TabsTrigger value="pendientes" className="flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Pendientes ({pendientes.length})
          </TabsTrigger>
          <TabsTrigger value="pagados" className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            Pagados ({pagados.length})
          </TabsTrigger>
          <TabsTrigger value="reclamados" className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            En Reclamación ({reclamados.length})
          </TabsTrigger>
          <TabsTrigger value="historial" className="flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4" />
            Historial
          </TabsTrigger>
        </TabsList>

        {/* Tab Pendientes */}
        <TabsContent value="pendientes">
          <LiquidacionesTable
            items={pendientes}
            seleccionados={seleccionados}
            onToggleSeleccion={toggleSeleccion}
            onToggleSeleccionTodos={() => toggleSeleccionTodos(pendientes)}
            onMarcarPagado={(codigo) => handleCambiarEstado(codigo, 'pagado')}
            onReclamar={abrirNotasModal}
            onEditarGarantia={abrirGarantiaModal}
            showCheckbox
            showAcciones
          />
        </TabsContent>

        {/* Tab Pagados */}
        <TabsContent value="pagados">
          <LiquidacionesTable
            items={pagados}
            onEditarGarantia={abrirGarantiaModal}
            showFechaPago
          />
        </TabsContent>

        {/* Tab Reclamados */}
        <TabsContent value="reclamados">
          <LiquidacionesTable
            items={reclamados}
            onMarcarPagado={(codigo) => handleCambiarEstado(codigo, 'pagado')}
            onReclamar={abrirNotasModal}
            onEditarGarantia={abrirGarantiaModal}
            showAcciones
            showNotas
          />
        </TabsContent>

        {/* Tab Historial */}
        <TabsContent value="historial">
          <Card>
            <CardHeader>
              <CardTitle>Historial de Liquidaciones por Mes</CardTitle>
            </CardHeader>
            <CardContent>
              {historialMeses.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Mes</TableHead>
                      <TableHead className="text-center">Siniestros</TableHead>
                      <TableHead className="text-right">Importe</TableHead>
                      <TableHead className="text-right">Garantías</TableHead>
                      <TableHead className="text-right">Neto</TableHead>
                      <TableHead className="text-center">Pagados</TableHead>
                      <TableHead className="text-center">Pendientes</TableHead>
                      <TableHead className="text-center">Reclamados</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {historialMeses.map((mes) => (
                      <TableRow key={mes.mes}>
                        <TableCell className="font-medium">{formatMes(mes.mes)}</TableCell>
                        <TableCell className="text-center">{mes.total_siniestros}</TableCell>
                        <TableCell className="text-right">{mes.total_importe.toFixed(2)}€</TableCell>
                        <TableCell className="text-right text-red-600">-{mes.total_garantias.toFixed(2)}€</TableCell>
                        <TableCell className="text-right font-medium">{mes.importe_neto.toFixed(2)}€</TableCell>
                        <TableCell className="text-center">
                          <Badge variant="default" className="bg-green-500">{mes.pagados}</Badge>
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge variant="secondary">{mes.pendientes}</Badge>
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge variant="destructive">{mes.reclamados}</Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-center text-muted-foreground py-8">
                  No hay datos de historial. Importa un archivo de liquidación para comenzar.
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Modal de Garantía */}
      <Dialog open={showGarantiaModal} onOpenChange={setShowGarantiaModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Gestión de Garantía - {garantiaItem?.codigo_siniestro}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Checkbox
                id="tiene_garantia"
                checked={garantiaForm.tiene_garantia}
                onCheckedChange={(checked) => setGarantiaForm(prev => ({ ...prev, tiene_garantia: checked }))}
              />
              <label htmlFor="tiene_garantia" className="text-sm font-medium">
                Se ha abierto garantía para este siniestro
              </label>
            </div>
            
            {garantiaForm.tiene_garantia && (
              <>
                <div>
                  <label className="text-sm font-medium">Código de Garantía</label>
                  <Input
                    placeholder="Código del siniestro de garantía"
                    value={garantiaForm.codigo_garantia}
                    onChange={(e) => setGarantiaForm(prev => ({ ...prev, codigo_garantia: e.target.value.toUpperCase() }))}
                    className="font-mono"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Costes adicionales de garantía (€)</label>
                  <Input
                    type="number"
                    step="0.01"
                    value={garantiaForm.costes_garantia}
                    onChange={(e) => setGarantiaForm(prev => ({ ...prev, costes_garantia: parseFloat(e.target.value) || 0 }))}
                  />
                </div>
              </>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowGarantiaModal(false)}>Cancelar</Button>
            <Button onClick={handleGuardarGarantia}>Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal de Reclamación */}
      <Dialog open={showNotasModal} onOpenChange={setShowNotasModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              Reclamación - {notasItem?.codigo_siniestro}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Estado</label>
              <Select 
                value={notasForm.estado} 
                onValueChange={(v) => setNotasForm(prev => ({ ...prev, estado: v }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="reclamado">Reclamado</SelectItem>
                  <SelectItem value="en_resolucion">En Resolución</SelectItem>
                  <SelectItem value="pendiente">Volver a Pendiente</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">Notas / Motivo de reclamación</label>
              <Textarea
                placeholder="Describe el motivo de la reclamación..."
                value={notasForm.notas}
                onChange={(e) => setNotasForm(prev => ({ ...prev, notas: e.target.value }))}
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowNotasModal(false)}>Cancelar</Button>
            <Button onClick={handleGuardarNotas}>Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Componente de tabla reutilizable
function LiquidacionesTable({
  items,
  seleccionados = [],
  onToggleSeleccion,
  onToggleSeleccionTodos,
  onMarcarPagado,
  onReclamar,
  onEditarGarantia,
  showCheckbox,
  showAcciones,
  showFechaPago,
  showNotas
}) {
  if (items.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Receipt className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          <p className="text-muted-foreground">No hay siniestros en esta categoría</p>
        </CardContent>
      </Card>
    );
  }

  const todosSeleccionados = showCheckbox && items.every(i => seleccionados.includes(i.codigo_siniestro));

  return (
    <Card>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                {showCheckbox && (
                  <TableHead className="w-12">
                    <Checkbox
                      checked={todosSeleccionados}
                      onCheckedChange={onToggleSeleccionTodos}
                    />
                  </TableHead>
                )}
                <TableHead>Código</TableHead>
                <TableHead>Cliente</TableHead>
                <TableHead>Dispositivo</TableHead>
                <TableHead className="text-right">Importe</TableHead>
                <TableHead>Garantía</TableHead>
                {showFechaPago && <TableHead>Fecha Pago</TableHead>}
                {showNotas && <TableHead>Notas</TableHead>}
                {showAcciones && <TableHead className="text-right">Acciones</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.codigo_siniestro}>
                  {showCheckbox && (
                    <TableCell>
                      <Checkbox
                        checked={seleccionados.includes(item.codigo_siniestro)}
                        onCheckedChange={() => onToggleSeleccion(item.codigo_siniestro)}
                      />
                    </TableCell>
                  )}
                  <TableCell className="font-mono font-medium">{item.codigo_siniestro}</TableCell>
                  <TableCell>{item.cliente || '-'}</TableCell>
                  <TableCell className="max-w-[150px] truncate">{item.dispositivo || '-'}</TableCell>
                  <TableCell className="text-right font-medium">{(item.importe || 0).toFixed(2)}€</TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onEditarGarantia?.(item)}
                      className={item.tiene_garantia ? 'text-amber-600' : 'text-gray-400'}
                    >
                      <Shield className="w-4 h-4 mr-1" />
                      {item.tiene_garantia ? (
                        <span className="text-xs">{item.codigo_garantia || 'Sí'} (-{item.costes_garantia}€)</span>
                      ) : 'No'}
                    </Button>
                  </TableCell>
                  {showFechaPago && (
                    <TableCell className="text-sm text-muted-foreground">
                      {item.fecha_pago?.slice(0, 10) || '-'}
                    </TableCell>
                  )}
                  {showNotas && (
                    <TableCell className="max-w-[200px] truncate text-sm text-muted-foreground">
                      {item.notas || '-'}
                    </TableCell>
                  )}
                  {showAcciones && (
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onMarcarPagado?.(item.codigo_siniestro)}
                          className="text-green-600 hover:text-green-700"
                        >
                          <Check className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onReclamar?.(item)}
                          className="text-amber-600 hover:text-amber-700"
                        >
                          <AlertTriangle className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

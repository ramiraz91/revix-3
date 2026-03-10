import { useState, useEffect } from 'react';
import { 
  ClipboardCheck, FileText, Users, BarChart3, 
  Plus, Search, Filter, CheckCircle2, XCircle, AlertTriangle,
  ChevronRight, Download, Eye, RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import API from '@/lib/api';

// API helpers
const isoAPI = {
  // Dashboard
  dashboard: () => API.get('/iso/dashboard'),
  
  // QA Muestreo
  crearMuestreo: (data) => API.post('/iso/qa/muestreo', data),
  listarMuestreos: (params = {}) => API.get('/iso/qa/muestreos', { params }),
  obtenerMuestreo: (id) => API.get(`/iso/qa/muestreo/${id}`),
  registrarResultado: (id, data) => API.post(`/iso/qa/muestreo/${id}/resultado`, data),
  
  // Proveedores
  crearEvaluacion: (data) => API.post('/iso/proveedores/evaluacion', data),
  listarEvaluaciones: (params = {}) => API.get('/iso/proveedores/evaluaciones', { params }),
  rankingProveedores: () => API.get('/iso/proveedores/ranking'),
  
  // Documentos
  crearDocumento: (data) => API.post('/iso/documentos', data),
  listarDocumentos: (params = {}) => API.get('/iso/documentos', { params }),
  obtenerDocumento: (id) => API.get(`/iso/documentos/${id}`),
  actualizarDocumento: (id, data) => API.put(`/iso/documentos/${id}`, data),
  registrarAcuse: (id) => API.post(`/iso/documentos/${id}/acuse`),
  listarAcuses: (id) => API.get(`/iso/documentos/${id}/acuses`),
};

// Componente principal
export default function ISOModule() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const res = await isoAPI.dashboard();
      setDashboard(res.data);
    } catch (err) {
      toast.error('Error al cargar dashboard ISO');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6" data-testid="iso-module">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Módulo ISO / WISE</h1>
          <p className="text-muted-foreground">Sistema de Gestión de Calidad</p>
        </div>
        <Button variant="outline" onClick={loadDashboard}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Actualizar
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="dashboard" className="gap-2">
            <BarChart3 className="w-4 h-4" />
            Dashboard
          </TabsTrigger>
          <TabsTrigger value="qa" className="gap-2">
            <ClipboardCheck className="w-4 h-4" />
            QA Muestreo
          </TabsTrigger>
          <TabsTrigger value="proveedores" className="gap-2">
            <Users className="w-4 h-4" />
            Proveedores
          </TabsTrigger>
          <TabsTrigger value="documentos" className="gap-2">
            <FileText className="w-4 h-4" />
            Documentos
          </TabsTrigger>
        </TabsList>

        <TabsContent value="dashboard">
          <DashboardISO dashboard={dashboard} loading={loading} />
        </TabsContent>

        <TabsContent value="qa">
          <QAMuestreoTab />
        </TabsContent>

        <TabsContent value="proveedores">
          <ProveedoresTab />
        </TabsContent>

        <TabsContent value="documentos">
          <DocumentosTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Dashboard ISO
function DashboardISO({ dashboard, loading }) {
  if (loading) {
    return <div className="text-center py-8">Cargando...</div>;
  }

  if (!dashboard) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
      {/* QA Muestreo */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <ClipboardCheck className="w-5 h-5 text-blue-600" />
            QA Muestreo
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold">{dashboard.qa_muestreo?.activos || 0}</div>
          <p className="text-sm text-muted-foreground">Muestreos activos</p>
          {dashboard.qa_muestreo?.ultimo_resultado && (
            <Badge className="mt-2" variant={dashboard.qa_muestreo.ultimo_resultado === 'LOTE_APROBADO' ? 'success' : 'destructive'}>
              Último: {dashboard.qa_muestreo.ultimo_resultado}
            </Badge>
          )}
        </CardContent>
      </Card>

      {/* Proveedores */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="w-5 h-5 text-green-600" />
            Clasificación Proveedores
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 flex-wrap">
            <Badge variant="success">A: {dashboard.proveedores?.clasificacion_A || 0}</Badge>
            <Badge variant="default">B: {dashboard.proveedores?.clasificacion_B || 0}</Badge>
            <Badge variant="warning">C: {dashboard.proveedores?.clasificacion_C || 0}</Badge>
            <Badge variant="destructive">D: {dashboard.proveedores?.clasificacion_D || 0}</Badge>
          </div>
        </CardContent>
      </Card>

      {/* Documentos */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="w-5 h-5 text-purple-600" />
            Control Documental
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold">{dashboard.documentos?.vigentes || 0}</div>
          <p className="text-sm text-muted-foreground">Documentos vigentes</p>
          {dashboard.documentos?.pendientes_acuse > 0 && (
            <Badge variant="warning" className="mt-2">
              {dashboard.documentos.pendientes_acuse} pendientes de acuse
            </Badge>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// QA Muestreo Tab
function QAMuestreoTab() {
  const [muestreos, setMuestreos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNuevo, setShowNuevo] = useState(false);
  const [selectedMuestreo, setSelectedMuestreo] = useState(null);

  useEffect(() => {
    loadMuestreos();
  }, []);

  const loadMuestreos = async () => {
    try {
      const res = await isoAPI.listarMuestreos();
      setMuestreos(res.data);
    } catch (err) {
      toast.error('Error al cargar muestreos');
    } finally {
      setLoading(false);
    }
  };

  const handleCrearMuestreo = async (data) => {
    try {
      await isoAPI.crearMuestreo(data);
      toast.success('Muestreo creado correctamente');
      setShowNuevo(false);
      loadMuestreos();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al crear muestreo');
    }
  };

  return (
    <div className="space-y-4 mt-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Muestreos QA (AQL)</h2>
        <Button onClick={() => setShowNuevo(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Muestreo
        </Button>
      </div>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Período</TableHead>
              <TableHead>Lote</TableHead>
              <TableHead>Muestra</TableHead>
              <TableHead>Nivel</TableHead>
              <TableHead>Progreso</TableHead>
              <TableHead>Resultado</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={7} className="text-center">Cargando...</TableCell></TableRow>
            ) : muestreos.length === 0 ? (
              <TableRow><TableCell colSpan={7} className="text-center text-muted-foreground">No hay muestreos</TableCell></TableRow>
            ) : muestreos.map((m) => (
              <TableRow key={m.id}>
                <TableCell className="font-medium">{m.lote_fecha_inicio?.slice(0, 10)} - {m.lote_fecha_fin?.slice(0, 10)}</TableCell>
                <TableCell>{m.tamano_lote}</TableCell>
                <TableCell>{m.tamano_muestra}</TableCell>
                <TableCell>
                  <Badge variant="outline">{m.nivel_inspeccion}</Badge>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Progress value={((m.aprobados + m.rechazados) / m.tamano_muestra) * 100} className="w-20 h-2" />
                    <span className="text-xs">{m.aprobados + m.rechazados}/{m.tamano_muestra}</span>
                  </div>
                </TableCell>
                <TableCell>
                  {m.resultado_final ? (
                    <Badge variant={m.resultado_final === 'LOTE_APROBADO' ? 'success' : 'destructive'}>
                      {m.resultado_final === 'LOTE_APROBADO' ? 'Aprobado' : 'Rechazado'}
                    </Badge>
                  ) : (
                    <Badge variant="secondary">{m.estado}</Badge>
                  )}
                </TableCell>
                <TableCell>
                  <Button variant="ghost" size="sm" onClick={() => setSelectedMuestreo(m)}>
                    <Eye className="w-4 h-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Modal Nuevo Muestreo */}
      <NuevoMuestreoDialog open={showNuevo} onClose={() => setShowNuevo(false)} onSubmit={handleCrearMuestreo} />
      
      {/* Modal Detalle Muestreo */}
      {selectedMuestreo && (
        <DetalleMuestreoDialog 
          muestreo={selectedMuestreo} 
          onClose={() => { setSelectedMuestreo(null); loadMuestreos(); }} 
        />
      )}
    </div>
  );
}

// Dialog Nuevo Muestreo
function NuevoMuestreoDialog({ open, onClose, onSubmit }) {
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  const [nivel, setNivel] = useState('normal');
  const [aql, setAql] = useState('2.5');

  const handleSubmit = () => {
    if (!fechaInicio || !fechaFin) {
      toast.error('Completa las fechas del período');
      return;
    }
    onSubmit({
      lote_fecha_inicio: fechaInicio,
      lote_fecha_fin: fechaFin,
      nivel_inspeccion: nivel,
      criterio_aql: parseFloat(aql)
    });
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nuevo Muestreo QA</DialogTitle>
          <DialogDescription>
            Crea un plan de muestreo para un período de órdenes reparadas
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Fecha Inicio</Label>
              <Input type="date" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} />
            </div>
            <div>
              <Label>Fecha Fin</Label>
              <Input type="date" value={fechaFin} onChange={(e) => setFechaFin(e.target.value)} />
            </div>
          </div>
          <div>
            <Label>Nivel de Inspección</Label>
            <Select value={nivel} onValueChange={setNivel}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="reducida">Reducida (menos muestras)</SelectItem>
                <SelectItem value="normal">Normal</SelectItem>
                <SelectItem value="estricta">Estricta (más muestras)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>AQL (Nivel de Calidad Aceptable)</Label>
            <Select value={aql} onValueChange={setAql}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="1.0">1.0% (Muy estricto)</SelectItem>
                <SelectItem value="2.5">2.5% (Estándar)</SelectItem>
                <SelectItem value="4.0">4.0% (Permisivo)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button onClick={handleSubmit}>Crear Muestreo</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Dialog Detalle Muestreo
function DetalleMuestreoDialog({ muestreo, onClose }) {
  const [resultados, setResultados] = useState({});

  const handleRegistrarResultado = async (ordenId) => {
    const resultado = resultados[ordenId];
    if (!resultado) {
      toast.error('Selecciona un resultado');
      return;
    }
    try {
      const res = await isoAPI.registrarResultado(muestreo.id, {
        orden_id: ordenId,
        resultado: resultado,
        hallazgos: '',
        accion_correctiva: ''
      });
      toast.success(res.data.message);
      if (res.data.resultado_final) {
        toast.info(`Muestreo finalizado: ${res.data.resultado_final}`);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  const ordenesInspeccionadas = new Set(muestreo.resultados?.map(r => r.orden_id) || []);

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Detalle Muestreo QA</DialogTitle>
          <DialogDescription>
            {muestreo.lote_fecha_inicio?.slice(0, 10)} - {muestreo.lote_fecha_fin?.slice(0, 10)} | 
            AQL: {muestreo.criterio_aql}% | Nivel: {muestreo.nivel_inspeccion}
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="flex gap-4 text-sm">
            <div>Lote: <strong>{muestreo.tamano_lote}</strong> órdenes</div>
            <div>Muestra: <strong>{muestreo.tamano_muestra}</strong></div>
            <div>Aceptación: <strong>≤{muestreo.numero_aceptacion}</strong> defectos</div>
            <div className="text-green-600">Aprobados: <strong>{muestreo.aprobados}</strong></div>
            <div className="text-red-600">Rechazados: <strong>{muestreo.rechazados}</strong></div>
          </div>

          {muestreo.resultado_final && (
            <Badge variant={muestreo.resultado_final === 'LOTE_APROBADO' ? 'success' : 'destructive'} className="text-lg px-4 py-2">
              {muestreo.resultado_final === 'LOTE_APROBADO' ? '✓ LOTE APROBADO' : '✗ LOTE RECHAZADO'}
            </Badge>
          )}

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Orden</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Resultado</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {muestreo.ordenes_seleccionadas?.map((orden) => {
                const yaInspeccionada = ordenesInspeccionadas.has(orden.id);
                const resultado = muestreo.resultados?.find(r => r.orden_id === orden.id);
                return (
                  <TableRow key={orden.id}>
                    <TableCell className="font-mono">{orden.numero_orden}</TableCell>
                    <TableCell>
                      {yaInspeccionada ? (
                        <Badge variant={resultado?.resultado === 'aprobado' ? 'success' : 'destructive'}>
                          {resultado?.resultado}
                        </Badge>
                      ) : (
                        <Badge variant="secondary">Pendiente</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {!yaInspeccionada && !muestreo.resultado_final && (
                        <Select value={resultados[orden.id] || ''} onValueChange={(v) => setResultados({...resultados, [orden.id]: v})}>
                          <SelectTrigger className="w-32"><SelectValue placeholder="Resultado" /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="aprobado">Aprobado</SelectItem>
                            <SelectItem value="rechazado">Rechazado</SelectItem>
                          </SelectContent>
                        </Select>
                      )}
                    </TableCell>
                    <TableCell>
                      {!yaInspeccionada && !muestreo.resultado_final && (
                        <Button size="sm" onClick={() => handleRegistrarResultado(orden.id)}>
                          Guardar
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
        
        <DialogFooter>
          <Button onClick={onClose}>Cerrar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Proveedores Tab
function ProveedoresTab() {
  const [ranking, setRanking] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNueva, setShowNueva] = useState(false);
  const [proveedores, setProveedores] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [rankRes, provRes] = await Promise.all([
        isoAPI.rankingProveedores(),
        API.get('/proveedores')
      ]);
      setRanking(rankRes.data);
      setProveedores(provRes.data);
    } catch (err) {
      toast.error('Error al cargar proveedores');
    } finally {
      setLoading(false);
    }
  };

  const handleCrearEvaluacion = async (data) => {
    try {
      await isoAPI.crearEvaluacion(data);
      toast.success('Evaluación registrada');
      setShowNueva(false);
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  const getClasificacionColor = (c) => {
    switch(c) {
      case 'A': return 'bg-green-500';
      case 'B': return 'bg-blue-500';
      case 'C': return 'bg-yellow-500';
      case 'D': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="space-y-4 mt-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Evaluación de Proveedores</h2>
        <Button onClick={() => setShowNueva(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Nueva Evaluación
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Ranking de Proveedores</CardTitle>
        </CardHeader>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Posición</TableHead>
              <TableHead>Proveedor</TableHead>
              <TableHead>Período</TableHead>
              <TableHead>Puntuación</TableHead>
              <TableHead>Clasificación</TableHead>
              <TableHead>NC</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={6} className="text-center">Cargando...</TableCell></TableRow>
            ) : ranking.length === 0 ? (
              <TableRow><TableCell colSpan={6} className="text-center text-muted-foreground">No hay evaluaciones</TableCell></TableRow>
            ) : ranking.map((p, idx) => (
              <TableRow key={p.proveedor_id}>
                <TableCell className="font-bold">#{idx + 1}</TableCell>
                <TableCell>{p.proveedor_nombre}</TableCell>
                <TableCell>{p.periodo}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Progress value={p.puntuacion_global} className="w-20 h-2" />
                    <span className="font-semibold">{p.puntuacion_global}%</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge className={getClasificacionColor(p.clasificacion)}>
                    Clase {p.clasificacion}
                  </Badge>
                </TableCell>
                <TableCell>{p.no_conformidades}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Modal Nueva Evaluación */}
      <NuevaEvaluacionDialog 
        open={showNueva} 
        onClose={() => setShowNueva(false)} 
        onSubmit={handleCrearEvaluacion}
        proveedores={proveedores}
      />
    </div>
  );
}

// Dialog Nueva Evaluación
function NuevaEvaluacionDialog({ open, onClose, onSubmit, proveedores }) {
  const [form, setForm] = useState({
    proveedor_id: '',
    periodo: '',
    calidad_puntuacion: 80,
    entrega_puntuacion: 80,
    precio_puntuacion: 80,
    servicio_puntuacion: 80,
    observaciones: '',
    no_conformidades: 0,
    entregas_tardias: 0,
    total_pedidos: 0
  });

  const handleSubmit = () => {
    if (!form.proveedor_id || !form.periodo) {
      toast.error('Selecciona proveedor y período');
      return;
    }
    onSubmit(form);
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Nueva Evaluación de Proveedor</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Proveedor</Label>
            <Select value={form.proveedor_id} onValueChange={(v) => setForm({...form, proveedor_id: v})}>
              <SelectTrigger><SelectValue placeholder="Seleccionar..." /></SelectTrigger>
              <SelectContent>
                {proveedores.map(p => (
                  <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Período</Label>
            <Input placeholder="Ej: 2026-Q1, 2026-H1" value={form.periodo} onChange={(e) => setForm({...form, periodo: e.target.value})} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Calidad ({form.calidad_puntuacion}%)</Label>
              <Input type="range" min="0" max="100" value={form.calidad_puntuacion} onChange={(e) => setForm({...form, calidad_puntuacion: parseInt(e.target.value)})} />
            </div>
            <div>
              <Label>Entrega ({form.entrega_puntuacion}%)</Label>
              <Input type="range" min="0" max="100" value={form.entrega_puntuacion} onChange={(e) => setForm({...form, entrega_puntuacion: parseInt(e.target.value)})} />
            </div>
            <div>
              <Label>Precio ({form.precio_puntuacion}%)</Label>
              <Input type="range" min="0" max="100" value={form.precio_puntuacion} onChange={(e) => setForm({...form, precio_puntuacion: parseInt(e.target.value)})} />
            </div>
            <div>
              <Label>Servicio ({form.servicio_puntuacion}%)</Label>
              <Input type="range" min="0" max="100" value={form.servicio_puntuacion} onChange={(e) => setForm({...form, servicio_puntuacion: parseInt(e.target.value)})} />
            </div>
          </div>
          <div>
            <Label>Observaciones</Label>
            <Textarea value={form.observaciones} onChange={(e) => setForm({...form, observaciones: e.target.value})} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button onClick={handleSubmit}>Guardar Evaluación</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Documentos Tab
function DocumentosTab() {
  const [documentos, setDocumentos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNuevo, setShowNuevo] = useState(false);

  useEffect(() => {
    loadDocumentos();
  }, []);

  const loadDocumentos = async () => {
    try {
      const res = await isoAPI.listarDocumentos();
      setDocumentos(res.data);
    } catch (err) {
      toast.error('Error al cargar documentos');
    } finally {
      setLoading(false);
    }
  };

  const handleCrearDocumento = async (data) => {
    try {
      await isoAPI.crearDocumento(data);
      toast.success('Documento creado');
      setShowNuevo(false);
      loadDocumentos();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  const handleAcuse = async (docId) => {
    try {
      await isoAPI.registrarAcuse(docId);
      toast.success('Acuse de lectura registrado');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  const tipoIcon = (tipo) => {
    switch(tipo) {
      case 'procedimiento': return '📋';
      case 'instruccion': return '📝';
      case 'formato': return '📄';
      case 'registro': return '📁';
      case 'politica': return '📜';
      default: return '📄';
    }
  };

  return (
    <div className="space-y-4 mt-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Control Documental ISO</h2>
        <Button onClick={() => setShowNuevo(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Documento
        </Button>
      </div>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Código</TableHead>
              <TableHead>Título</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Versión</TableHead>
              <TableHead>Vigencia</TableHead>
              <TableHead>Acuse</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={7} className="text-center">Cargando...</TableCell></TableRow>
            ) : documentos.length === 0 ? (
              <TableRow><TableCell colSpan={7} className="text-center text-muted-foreground">No hay documentos</TableCell></TableRow>
            ) : documentos.map((doc) => (
              <TableRow key={doc.id}>
                <TableCell className="font-mono font-bold">{doc.codigo}</TableCell>
                <TableCell>{doc.titulo}</TableCell>
                <TableCell>
                  <span className="mr-1">{tipoIcon(doc.tipo)}</span>
                  {doc.tipo}
                </TableCell>
                <TableCell><Badge variant="outline">v{doc.version}</Badge></TableCell>
                <TableCell>{doc.fecha_vigencia?.slice(0, 10)}</TableCell>
                <TableCell>
                  {doc.requiere_acuse ? (
                    <Badge variant="warning">Requerido</Badge>
                  ) : (
                    <Badge variant="secondary">No</Badge>
                  )}
                </TableCell>
                <TableCell>
                  <Button variant="ghost" size="sm" onClick={() => handleAcuse(doc.id)}>
                    <CheckCircle2 className="w-4 h-4 mr-1" />
                    Firmar
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Modal Nuevo Documento */}
      <NuevoDocumentoDialog open={showNuevo} onClose={() => setShowNuevo(false)} onSubmit={handleCrearDocumento} />
    </div>
  );
}

// Dialog Nuevo Documento
function NuevoDocumentoDialog({ open, onClose, onSubmit }) {
  const [form, setForm] = useState({
    codigo: '',
    titulo: '',
    tipo: 'procedimiento',
    version: '1.0',
    responsable: '',
    fecha_vigencia: '',
    requiere_acuse: false,
    contenido: ''
  });

  const handleSubmit = () => {
    if (!form.codigo || !form.titulo || !form.fecha_vigencia) {
      toast.error('Completa los campos obligatorios');
      return;
    }
    onSubmit(form);
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Nuevo Documento ISO</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Código *</Label>
              <Input placeholder="PRO-001" value={form.codigo} onChange={(e) => setForm({...form, codigo: e.target.value.toUpperCase()})} />
            </div>
            <div>
              <Label>Tipo</Label>
              <Select value={form.tipo} onValueChange={(v) => setForm({...form, tipo: v})}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="politica">Política</SelectItem>
                  <SelectItem value="procedimiento">Procedimiento</SelectItem>
                  <SelectItem value="instruccion">Instrucción</SelectItem>
                  <SelectItem value="formato">Formato</SelectItem>
                  <SelectItem value="registro">Registro</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div>
            <Label>Título *</Label>
            <Input value={form.titulo} onChange={(e) => setForm({...form, titulo: e.target.value})} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Responsable</Label>
              <Input value={form.responsable} onChange={(e) => setForm({...form, responsable: e.target.value})} />
            </div>
            <div>
              <Label>Fecha Vigencia *</Label>
              <Input type="date" value={form.fecha_vigencia} onChange={(e) => setForm({...form, fecha_vigencia: e.target.value})} />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="acuse" checked={form.requiere_acuse} onChange={(e) => setForm({...form, requiere_acuse: e.target.checked})} />
            <Label htmlFor="acuse">Requiere acuse de lectura</Label>
          </div>
          <div>
            <Label>Contenido</Label>
            <Textarea rows={4} value={form.contenido} onChange={(e) => setForm({...form, contenido: e.target.value})} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button onClick={handleSubmit}>Crear Documento</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Bot, Play, Square, RefreshCw, Settings, Mail, Server, Shield, Clock, AlertTriangle, CheckCircle, XCircle, Search, Image, Download } from 'lucide-react';
import API from '@/lib/api';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';

export default function AgenteEmail() {
  const { isMaster } = useAuth();
  const [status, setStatus] = useState(null);
  const [config, setConfig] = useState(null);
  const [configForm, setConfigForm] = useState({});
  const [logs, setLogs] = useState([]);
  const [showConfig, setShowConfig] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [scrapeCode, setScrapeCode] = useState('');
  const [scrapeLoading, setScrapeLoading] = useState(false);
  const [scrapeResult, setScrapeResult] = useState(null);
  const [simCode, setSimCode] = useState('');
  const [simLoading, setSimLoading] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [downloadingPhotos, setDownloadingPhotos] = useState(false);

  // Budget simulation states
  const [budgetCode, setBudgetCode] = useState('');
  const [budgetLoading, setBudgetLoading] = useState(false);
  const [budgetResult, setBudgetResult] = useState(null);
  const [budgetPrice, setBudgetPrice] = useState('');
  const [budgetNotes, setBudgetNotes] = useState('');
  const [emitLoading, setEmitLoading] = useState(false);
  const [emitResult, setEmitResult] = useState(null);

  const handleSimularPresupuesto = async () => {
    if (!budgetCode.trim()) return toast.error('Introduce un código de siniestro');
    setBudgetLoading(true);
    setBudgetResult(null);
    setEmitResult(null);
    try {
      const res = await API.post(`/agente/simular-presupuesto/${budgetCode.trim()}`);
      setBudgetResult(res.data);
      toast.success('Solicitud de presupuesto creada');
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error en simulación');
    } finally { setBudgetLoading(false); }
  };

  const handleEmitirPresupuesto = async () => {
    if (!budgetCode.trim() || !budgetPrice) return toast.error('Código y precio son obligatorios');
    setEmitLoading(true);
    setEmitResult(null);
    try {
      const res = await API.post('/agente/emitir-presupuesto', {
        codigo_siniestro: budgetCode.trim(),
        precio: parseFloat(budgetPrice),
        notas: budgetNotes,
      });
      setEmitResult(res.data);
      toast.success(res.data.message);
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error emitiendo presupuesto');
    } finally { setEmitLoading(false); }
  };

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, logsRes] = await Promise.all([
        API.get('/agente/status'),
        isMaster() ? API.get('/agente/logs?limit=30') : Promise.resolve({ data: [] })
      ]);
      setStatus(statusRes.data);
      setLogs(logsRes.data);
      if (isMaster()) {
        const cfgRes = await API.get('/agente/config');
        setConfig(cfgRes.data);
        if (cfgRes.data.datos) {
          setConfigForm(cfgRes.data.datos);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [isMaster]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleStart = async () => {
    try {
      await API.post('/agente/start');
      toast.success('Agente iniciado');
      fetchData();
    } catch (e) { toast.error('Error al iniciar'); }
  };

  const handleStop = async () => {
    try {
      await API.post('/agente/stop');
      toast.success('Agente detenido');
      fetchData();
    } catch (e) { toast.error('Error al detener'); }
  };

  const handlePollNow = async () => {
    try {
      await API.post('/agente/poll-now');
      toast.success('Poll ejecutado');
      fetchData();
    } catch (e) { toast.error('Error: ' + (e.response?.data?.detail || e.message)); }
  };

  const handleTestImap = async () => {
    try {
      const res = await API.post('/agente/test-imap');
      if (res.data.success) {
        toast.success(`Conexión OK. Carpetas: ${res.data.folders?.join(', ')}`);
      } else {
        toast.error(`Error: ${res.data.error}`);
      }
    } catch (e) { toast.error('Error de conexión'); }
  };

  const handleTestPortal = async () => {
    try {
      const res = await API.post('/agente/test-portal');
      if (res.data.success) {
        toast.success(`Portal OK — Usuario: ${res.data.user}, Presupuestos: ${res.data.store_budgets_total}`);
      } else {
        toast.error(`Error: ${res.data.error}`);
      }
    } catch (e) { toast.error('Error conectando al portal'); }
  };

  const handleScrapeManual = async () => {
    if (!scrapeCode.trim()) return toast.error('Introduce un código de siniestro');
    setScrapeLoading(true);
    setScrapeResult(null);
    try {
      const res = await API.post(`/agente/scrape/${scrapeCode.trim()}`);
      setScrapeResult(res.data.datos);
      toast.success('Datos extraídos correctamente');
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al extraer datos');
    } finally { setScrapeLoading(false); }
  };

  const handleDescargarFotos = async () => {
    if (!scrapeCode.trim()) return;
    setDownloadingPhotos(true);
    try {
      const res = await API.post(`/agente/scrape/${scrapeCode.trim()}/descargar-fotos`);
      toast.success(res.data.message);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error descargando fotos');
    } finally { setDownloadingPhotos(false); }
  };

  const handleSimularAceptacion = async () => {
    if (!simCode.trim()) return toast.error('Introduce un código de siniestro');
    setSimLoading(true);
    setSimResult(null);
    try {
      const res = await API.post(`/agente/simular-aceptacion/${simCode.trim()}`);
      setSimResult(res.data);
      if (res.data.success) {
        toast.success(res.data.message);
      } else {
        toast.error(res.data.message || 'Error en la simulación');
      }
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error en la simulación');
    } finally { setSimLoading(false); }
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      await API.post('/agente/config', configForm);
      toast.success('Configuración guardada');
      fetchData();
    } catch (e) { toast.error('Error guardando'); }
    finally { setSaving(false); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" /></div>;

  return (
    <div className="space-y-6" data-testid="agente-email-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><Bot className="w-6 h-6" /> Agente Email</h1>
          <p className="text-muted-foreground">Motor de integración con proveedor externo</p>
        </div>
        {isMaster() && (
          <div className="flex gap-2">
            {status?.running ? (
              <Button variant="destructive" onClick={handleStop} size="sm"><Square className="w-4 h-4 mr-1" /> Detener</Button>
            ) : (
              <Button onClick={handleStart} size="sm" className="bg-green-600 hover:bg-green-700"><Play className="w-4 h-4 mr-1" /> Iniciar</Button>
            )}
            <Button variant="outline" onClick={handlePollNow} size="sm"><RefreshCw className="w-4 h-4 mr-1" /> Poll Manual</Button>
            <Button variant="outline" onClick={() => setShowConfig(!showConfig)} size="sm"><Settings className="w-4 h-4 mr-1" /> Config</Button>
          </div>
        )}
      </div>

      {/* Status cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Estado</p>
                <div className="flex items-center gap-2 mt-1">
                  <div className={`w-2.5 h-2.5 rounded-full ${status?.running ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
                  <span className="font-semibold text-sm">{status?.running ? 'Activo' : 'Pausado'}</span>
                </div>
              </div>
              <Bot className={`w-8 h-8 ${status?.running ? 'text-green-500' : 'text-gray-300'}`} />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-muted-foreground">Pre-Registros Pendientes</p>
            <p className="text-2xl font-bold">{status?.stats?.pre_registros_pendientes || 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-muted-foreground">Órdenes por Agente</p>
            <p className="text-2xl font-bold">{status?.stats?.ordenes_creadas_agente || 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-muted-foreground">Notif. Ext. Sin Leer</p>
            <p className="text-2xl font-bold text-orange-600">{status?.stats?.notif_ext_no_leidas || 0}</p>
          </CardContent>
        </Card>
      </div>

      {status?.stats?.eventos_en_consolidacion > 0 && (
        <Card className="border-amber-400 bg-amber-50">
          <CardContent className="py-3 flex items-center gap-2">
            <Clock className="w-4 h-4 text-amber-600" />
            <span className="text-sm text-amber-800">
              <b>{status.stats.eventos_en_consolidacion}</b> evento(s) en ventana de consolidación (5 min)
            </span>
          </CardContent>
        </Card>
      )}

      {/* Configuration panel (master only) */}
      {showConfig && isMaster() && (
        <Card>
          <CardHeader><CardTitle className="text-base flex items-center gap-2"><Settings className="w-4 h-4" /> Configuración del Agente</CardTitle></CardHeader>
          <CardContent className="space-y-6">
            {/* IMAP Section */}
            <div>
              <h3 className="font-semibold text-sm mb-3 flex items-center gap-2"><Mail className="w-4 h-4" /> Conexión IMAP</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground">Servidor IMAP</label>
                  <Input value={configForm.imap_host || ''} onChange={e => setConfigForm(f => ({...f, imap_host: e.target.value}))} placeholder="mail.example.com" className="h-8 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Puerto</label>
                  <Input type="number" value={configForm.imap_port || 993} onChange={e => setConfigForm(f => ({...f, imap_port: parseInt(e.target.value)}))} className="h-8 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Usuario</label>
                  <Input value={configForm.imap_user || ''} onChange={e => setConfigForm(f => ({...f, imap_user: e.target.value}))} className="h-8 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Contraseña</label>
                  <Input type="password" value={configForm.imap_password || ''} onChange={e => setConfigForm(f => ({...f, imap_password: e.target.value}))} placeholder="••••••" className="h-8 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Carpeta</label>
                  <Input value={configForm.imap_folder || 'INBOX'} onChange={e => setConfigForm(f => ({...f, imap_folder: e.target.value}))} className="h-8 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Intervalo poll (seg)</label>
                  <Input type="number" value={configForm.poll_interval || 180} onChange={e => setConfigForm(f => ({...f, poll_interval: parseInt(e.target.value)}))} className="h-8 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Regex código</label>
                  <Input value={configForm.codigo_pattern || ''} onChange={e => setConfigForm(f => ({...f, codigo_pattern: e.target.value}))} placeholder="\b(\d{2}[A-Z]{2}\d{6})\b" className="h-8 text-sm font-mono" />
                </div>
                <div className="flex items-end">
                  <Button variant="outline" size="sm" onClick={handleTestImap} className="h-8 w-full"><Mail className="w-3 h-3 mr-1" /> Test IMAP</Button>
                </div>
              </div>
            </div>

            {/* Portal Section */}
            <div>
              <h3 className="font-semibold text-sm mb-3 flex items-center gap-2"><Server className="w-4 h-4" /> Portal Proveedor (API REST)</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground">Usuario Portal</label>
                  <Input value={configForm.portal_user || ''} onChange={e => setConfigForm(f => ({...f, portal_user: e.target.value}))} className="h-8 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Contraseña Portal</label>
                  <Input type="password" value={configForm.portal_password || ''} onChange={e => setConfigForm(f => ({...f, portal_password: e.target.value}))} placeholder="••••••" className="h-8 text-sm" />
                </div>
                <div className="flex items-end">
                  <Button variant="outline" size="sm" onClick={handleTestPortal} className="h-8 w-full"><Server className="w-3 h-3 mr-1" /> Test Portal</Button>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowConfig(false)}>Cancelar</Button>
              <Button size="sm" onClick={handleSaveConfig} disabled={saving}>{saving ? 'Guardando...' : 'Guardar Config'}</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Manual Scrape Tool (master only) */}
      {isMaster() && (
        <Card>
          <CardHeader><CardTitle className="text-base flex items-center gap-2"><Search className="w-4 h-4" /> Consulta Manual al Portal</CardTitle></CardHeader>
          <CardContent>
            <div className="flex gap-2 items-end">
              <div className="flex-1">
                <label className="text-xs text-muted-foreground">Código de siniestro</label>
                <Input value={scrapeCode} onChange={e => setScrapeCode(e.target.value)} placeholder="Ej: 25BE005754" className="h-8 text-sm font-mono" onKeyDown={e => e.key === 'Enter' && handleScrapeManual()} />
              </div>
              <Button size="sm" onClick={handleScrapeManual} disabled={scrapeLoading} className="h-8">
                {scrapeLoading ? <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> : <Search className="w-3 h-3 mr-1" />}
                Consultar
              </Button>
            </div>
            {scrapeResult && (
              <div className="mt-4 p-3 bg-muted/50 rounded-lg text-xs space-y-3">
                <p className="font-semibold text-sm mb-2">Datos extraídos del portal:</p>
                
                {/* Device Section */}
                <div>
                  <p className="font-semibold text-xs text-blue-600 mb-1">Dispositivo</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-1">
                    {scrapeResult.device_brand && <p><span className="text-muted-foreground">Marca:</span> <b>{scrapeResult.device_brand}</b></p>}
                    {scrapeResult.device_model && <p><span className="text-muted-foreground">Modelo:</span> <b>{scrapeResult.device_model}</b></p>}
                    {scrapeResult.device_imei && <p><span className="text-muted-foreground">IMEI:</span> <span className="font-mono">{scrapeResult.device_imei}</span></p>}
                    {scrapeResult.device_colour && <p><span className="text-muted-foreground">Color:</span> {scrapeResult.device_colour}</p>}
                    {scrapeResult.device_type && <p><span className="text-muted-foreground">Tipo:</span> {scrapeResult.device_type}</p>}
                    {scrapeResult.device_purchase_date && <p><span className="text-muted-foreground">Fecha compra:</span> {scrapeResult.device_purchase_date}</p>}
                  </div>
                </div>

                {/* Damage Section */}
                <div>
                  <p className="font-semibold text-xs text-red-600 mb-1">Daño / Siniestro</p>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1">
                    {scrapeResult.claim_identifier && <p><span className="text-muted-foreground">Código:</span> <span className="font-mono font-bold">{scrapeResult.claim_identifier}</span></p>}
                    {scrapeResult.damage_type_text && <p><span className="text-muted-foreground">Tipo daño:</span> {scrapeResult.damage_type_text}</p>}
                    {scrapeResult.damage_description && <p className="col-span-2 md:col-span-3"><span className="text-muted-foreground">Descripción:</span> {scrapeResult.damage_description}</p>}
                    {scrapeResult.claim_type_text && <p><span className="text-muted-foreground">Tipo siniestro:</span> {scrapeResult.claim_type_text}</p>}
                    {scrapeResult.status_text && <p><span className="text-muted-foreground">Estado:</span> <Badge variant="outline" className="text-[10px]">{scrapeResult.status_text}</Badge></p>}
                    {scrapeResult.external_status_text && <p className="col-span-2"><span className="text-muted-foreground">Estado externo:</span> {scrapeResult.external_status_text}</p>}
                  </div>
                </div>

                {/* Client Section */}
                <div>
                  <p className="font-semibold text-xs text-green-600 mb-1">Cliente</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-1">
                    {scrapeResult.client_full_name && <p><span className="text-muted-foreground">Nombre:</span> <b>{scrapeResult.client_full_name}</b></p>}
                    {scrapeResult.client_nif && <p><span className="text-muted-foreground">NIF/NIE:</span> <span className="font-mono">{scrapeResult.client_nif}</span></p>}
                    {scrapeResult.client_phone && <p><span className="text-muted-foreground">Móvil:</span> {scrapeResult.client_phone}</p>}
                    {scrapeResult.client_email && <p><span className="text-muted-foreground">Email:</span> {scrapeResult.client_email}</p>}
                    {scrapeResult.client_address && <p className="col-span-2"><span className="text-muted-foreground">Dirección:</span> {scrapeResult.client_address}</p>}
                    {scrapeResult.client_city && <p><span className="text-muted-foreground">Localidad:</span> {scrapeResult.client_city}</p>}
                    {scrapeResult.client_province && <p><span className="text-muted-foreground">Provincia:</span> {scrapeResult.client_province}</p>}
                    {scrapeResult.client_zip && <p><span className="text-muted-foreground">C.P.:</span> {scrapeResult.client_zip}</p>}
                  </div>
                </div>

                {/* Policy / Budget Section */}
                <div>
                  <p className="font-semibold text-xs text-purple-600 mb-1">Póliza / Presupuesto</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-1">
                    {scrapeResult.policy_number && <p className="col-span-2"><span className="text-muted-foreground">Póliza:</span> <span className="font-mono text-[10px]">{scrapeResult.policy_number}</span></p>}
                    {scrapeResult.product_name && <p><span className="text-muted-foreground">Producto:</span> {scrapeResult.product_name}</p>}
                    {scrapeResult.price != null && <p><span className="text-muted-foreground">Precio:</span> <b>{scrapeResult.price}€</b></p>}
                    {scrapeResult.repair_type_text && <p><span className="text-muted-foreground">Tipo reparación:</span> {scrapeResult.repair_type_text}</p>}
                    {scrapeResult.warranty_type_text && <p><span className="text-muted-foreground">Garantía:</span> {scrapeResult.warranty_type_text}</p>}
                    {scrapeResult.accepted_date && <p><span className="text-muted-foreground">Aceptado:</span> {scrapeResult.accepted_date?.slice(0,10)}</p>}
                    {scrapeResult.pickup_date && <p><span className="text-muted-foreground">Recogida:</span> {scrapeResult.pickup_date?.slice(0,10)}</p>}
                  </div>
                </div>

                {/* Photos/Documents section */}
                {scrapeResult.docs && scrapeResult.docs.length > 0 && (
                  <div className="border-t pt-2">
                    <div className="flex items-center justify-between mb-2">
                      <p className="font-semibold text-sm flex items-center gap-1"><Image className="w-3.5 h-3.5" /> Fotos/Documentos del proveedor ({scrapeResult.docs.length})</p>
                      <Button size="sm" variant="outline" className="h-7 text-xs" onClick={handleDescargarFotos} disabled={downloadingPhotos}>
                        {downloadingPhotos ? <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> : <Download className="w-3 h-3 mr-1" />}
                        Descargar todo
                      </Button>
                    </div>
                    <div className="grid grid-cols-3 md:grid-cols-4 gap-2">
                      {scrapeResult.docs.map((doc, i) => (
                        <div key={doc.doc_id || i} className="bg-background border rounded p-2 text-center">
                          {doc.is_image ? <Image className="w-8 h-8 mx-auto text-blue-400 mb-1" /> : <Image className="w-8 h-8 mx-auto text-gray-400 mb-1" />}
                          <p className="text-[10px] truncate">{doc.name}</p>
                          <Badge variant="secondary" className="text-[9px] mt-1">{doc.doc_type || 'Documento'}</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Simulate Full Acceptance Flow (master only) */}
      {isMaster() && (
        <Card className="border-blue-200">
          <CardHeader><CardTitle className="text-base flex items-center gap-2"><Play className="w-4 h-4" /> Simular Aceptación Completa</CardTitle></CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground mb-3">Simula el flujo completo: Pre-registro → Aceptación → Datos portal → Orden de trabajo. Usa un código de siniestro real del portal.</p>
            <div className="flex gap-2 items-end">
              <div className="flex-1">
                <label className="text-xs text-muted-foreground">Código de siniestro</label>
                <Input value={simCode} onChange={e => setSimCode(e.target.value)} placeholder="Ej: 25BE005825" className="h-8 text-sm font-mono" onKeyDown={e => e.key === 'Enter' && handleSimularAceptacion()} />
              </div>
              <Button size="sm" onClick={handleSimularAceptacion} disabled={simLoading} className="h-8 bg-blue-600 hover:bg-blue-700">
                {simLoading ? <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> : <Play className="w-3 h-3 mr-1" />}
                Simular
              </Button>
            </div>
            {simResult && (
              <div className={`mt-4 p-3 rounded-lg text-xs ${simResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <p className={`font-semibold text-sm mb-2 ${simResult.success ? 'text-green-700' : 'text-red-700'}`}>
                  {simResult.success ? '✅ ' : '❌ '}{simResult.message}
                </p>
                <div className="space-y-1">
                  {simResult.steps?.map((step, i) => (
                    <p key={i} className="text-muted-foreground">
                      <span className="font-mono">Paso {step.step}:</span> {step.action}
                      {step.numero_orden && <span className="ml-1 font-semibold text-foreground">{step.numero_orden}</span>}
                      {step.damage && <span className="ml-1 italic">{step.damage}</span>}
                      {step.device && <span className="ml-1">[{step.device}]</span>}
                      {step.imei && <span className="ml-1 font-mono text-[10px]">IMEI: {step.imei}</span>}
                      {step.phone && <span className="ml-1">({step.phone})</span>}
                      {step.fotos_disponibles > 0 && <Badge variant="secondary" className="ml-1 text-[9px]">{step.fotos_disponibles} fotos</Badge>}
                      {step.fotos_descargadas > 0 && <Badge className="ml-1 text-[9px] bg-green-100 text-green-700">{step.fotos_descargadas} fotos descargadas</Badge>}
                    </p>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Budget Simulation */}
      <Card className="border-purple-200">
        <CardHeader><CardTitle className="text-base flex items-center gap-2"><Search className="w-4 h-4 text-purple-600" /> Simular Solicitud de Presupuesto</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <p className="text-xs text-muted-foreground">Paso 1: Simula la llegada de un nuevo siniestro → crea Pre-Registro en estado "pendiente_presupuesto".</p>
          <div className="flex gap-2">
            <Input placeholder="Ej: 26BE000774" value={budgetCode} onChange={(e) => setBudgetCode(e.target.value)} className="h-9 font-mono" />
            <Button size="sm" onClick={handleSimularPresupuesto} disabled={budgetLoading} className="bg-purple-600 hover:bg-purple-700">
              {budgetLoading ? <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> : null} Solicitar Presupuesto
            </Button>
          </div>

          {budgetResult && (
            <div className="p-3 bg-purple-50 rounded-lg text-xs space-y-2 border border-purple-200">
              <p className="font-semibold text-purple-700">Solicitud creada correctamente</p>
              {budgetResult.steps?.map((step, i) => (
                <p key={i} className="text-muted-foreground">
                  <span className="font-mono">Paso {step.step}:</span> {step.action}
                  {step.device && <span className="ml-1">[{step.device}]</span>}
                  {step.client && <span className="ml-1">— {step.client}</span>}
                  {step.damage && <span className="ml-1 italic">({step.damage})</span>}
                </p>
              ))}
              
              {/* Emit Budget Form */}
              <div className="mt-3 pt-3 border-t border-purple-200">
                <p className="font-semibold text-purple-700 mb-1">Paso 2: Registrar respuesta de presupuesto</p>
                <p className="text-[10px] text-muted-foreground mb-2">La respuesta real se envía vía portal web del proveedor. Aquí solo se registra internamente.</p>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-muted-foreground">Precio (€)</label>
                    <Input type="number" step="0.01" value={budgetPrice} onChange={(e) => setBudgetPrice(e.target.value)} placeholder="60.00" className="h-8 text-sm font-mono" />
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground">Notas</label>
                    <Input value={budgetNotes} onChange={(e) => setBudgetNotes(e.target.value)} placeholder="Reparación tapa trasera..." className="h-8 text-sm" />
                  </div>
                </div>
                <Button size="sm" className="mt-2 bg-green-600 hover:bg-green-700" onClick={handleEmitirPresupuesto} disabled={emitLoading}>
                  {emitLoading ? <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> : <CheckCircle className="w-3 h-3 mr-1" />}
                  Registrar Presupuesto
                </Button>
              </div>
            </div>
          )}

          {emitResult && (
            <div className="p-3 bg-green-50 rounded-lg text-xs space-y-1 border border-green-200">
              <p className="font-semibold text-green-700">{emitResult.message}</p>
              {emitResult.steps?.map((step, i) => (
                <p key={i} className="text-muted-foreground">
                  <span className="font-mono">Paso {step.step}:</span> {step.action}
                  {step.precio && <span className="ml-1 font-bold">{step.precio}€</span>}
                </p>
              ))}
              <p className="text-[10px] text-yellow-600 mt-2 font-medium">⏳ Pendiente: respuesta del proveedor (aceptado/rechazado) vía email.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent logs */}
      {isMaster() && logs.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-base">Últimos Logs del Agente</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {logs.map(log => (
                <div key={log.id} className="flex items-center gap-3 py-1.5 border-b border-border/50 text-xs">
                  {log.nivel === 'error' ? <XCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" /> :
                   log.nivel === 'warning' ? <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" /> :
                   <CheckCircle className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />}
                  <span className="text-muted-foreground w-32 flex-shrink-0">{log.created_at?.slice(0, 19).replace('T', ' ')}</span>
                  <span className="font-mono">{log.accion}</span>
                  {log.codigo_siniestro && <Badge variant="outline" className="text-xs">{log.codigo_siniestro}</Badge>}
                  <span className="text-muted-foreground">{log.resultado}</span>
                  {log.error && <span className="text-red-500 truncate max-w-xs">{log.error}</span>}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* SMTP Email Test */}
      {isMaster() && (
        <Card className="border-green-200">
          <CardHeader><CardTitle className="text-base flex items-center gap-2"><Mail className="w-4 h-4" /> Prueba Email SMTP</CardTitle></CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground mb-3">Envía un email de prueba para verificar la configuración SMTP (notificaciones@revix.es).</p>
            <div className="flex gap-2 items-end">
              <div className="flex-1">
                <label className="text-xs text-muted-foreground">Email destino</label>
                <Input id="testEmailTo" defaultValue="" placeholder="correo@ejemplo.com" className="h-8 text-sm" />
              </div>
              <Button size="sm" className="h-8 bg-green-600 hover:bg-green-700" onClick={async () => {
                const to = document.getElementById('testEmailTo').value;
                if (!to) return toast.error('Introduce un email');
                try {
                  const res = await API.post('/email/test', { to });
                  res.data.success ? toast.success(`Email enviado a ${to}`) : toast.error('Error al enviar');
                } catch (e) { toast.error(e.response?.data?.detail || 'Error SMTP'); }
              }}>
                <Mail className="w-3 h-3 mr-1" /> Enviar Prueba
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {status?.last_poll && (
        <p className="text-xs text-muted-foreground text-right">Último poll: {status.last_poll?.slice(0, 19).replace('T', ' ')} UTC</p>
      )}
    </div>
  );
}

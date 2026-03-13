import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import QRCode from 'react-qr-code';
import { useReactToPrint } from 'react-to-print';
import { 
  ArrowLeft, 
  User, 
  Smartphone, 
  Package,
  Clock,
  CheckCircle2,
  Wrench,
  AlertTriangle,
  Send,
  ClipboardList,
  Upload,
  Check,
  X,
  FileImage,
  Lock,
  Timer,
  MessageSquare,
  Copy,
  ExternalLink,
  Shield,
  Repeat,
  XCircle,
  QrCode,
  Download,
  FileText,
  Truck,
  DollarSign
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import { ordenesAPI, clientesAPI, repuestosAPI, ordenesCompraAPI, seguimientoAPI, getUploadUrl } from '@/lib/api';
import { EtiquetaOrden } from '@/components/EtiquetaOrden';
import OrdenPDF from '@/components/OrdenPDF';
import TablaMaterialesEditable from '@/components/TablaMaterialesEditable';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import CalidadPantallaBadge from '@/components/CalidadPantallaBadge';
import AppleManualCard from '@/components/AppleManualCard';

// Import refactored components
import {
  OrdenDetalleHeader,
  statusConfig,
  OrdenBloqueadaWarning,
  OrdenDesbloquearModal,
  OrdenCambioEstadoModal,
  OrdenClienteCard,
  OrdenDispositivoCard,
  OrdenEnvioCard,
  OrdenHistorialEstados,
  OrdenInsuramaPanel,
  OrdenMensajesTab,
  OrdenFotosTab,
  OrdenBloqueosTab,
  OrdenDiagnosticoCard,
  GenerarEnvioModal,
  OrdenSubestadoCard,
} from '@/components/orden';


const statusOrder = ['pendiente_recibir', 'recibida', 'cuarentena', 'en_taller', 'reparado', 'validacion', 'enviado'];

function formatHours(hours) {
  if (hours === null || hours === undefined) return '-';
  if (hours < 1) return `${Math.round(hours * 60)} min`;
  if (hours < 24) return `${Math.round(hours)} horas`;
  const days = Math.floor(hours / 24);
  const remainingHours = Math.round(hours % 24);
  return `${days}d ${remainingHours}h`;
}

export default function OrdenDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, isAdmin, isTecnico, isMaster } = useAuth();
  const fileInputRef = useRef(null);
  const pdfRefFull = useRef(null);
  const pdfRefNoPrices = useRef(null);
  const pdfRefBlank = useRef(null);
  
  // Core data states
  const [orden, setOrden] = useState(null);
  const [cliente, setCliente] = useState(null);
  const [repuestos, setRepuestos] = useState([]);
  const [mensajes, setMensajes] = useState([]);
  const [metricas, setMetricas] = useState(null);
  const [ordenesGarantia, setOrdenesGarantia] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Tab state - mantiene el tab activo después de actualizar
  const [activeTab, setActiveTab] = useState('info');
  
  // Dialog visibility states
  const [showCambioEstado, setShowCambioEstado] = useState(false);
  const [showEtiqueta, setShowEtiqueta] = useState(false);
  const [showLinkSeguimiento, setShowLinkSeguimiento] = useState(false);
  const [showDesbloquearModal, setShowDesbloquearModal] = useState(false);
  const [showImagePreview, setShowImagePreview] = useState(false);
  const [showEditCliente, setShowEditCliente] = useState(false);
  const [showNuevoRepuesto, setShowNuevoRepuesto] = useState(false);
  const [showAddMaterialDialog, setShowAddMaterialDialog] = useState(false);
  const [showEditMaterialDialog, setShowEditMaterialDialog] = useState(false);
  const [showSolicitarReemplazo, setShowSolicitarReemplazo] = useState(false);
  const [showAutorizarReemplazo, setShowAutorizarReemplazo] = useState(false);
  const [showGenerarRecogida, setShowGenerarRecogida] = useState(false);
  const [showGenerarEnvio, setShowGenerarEnvio] = useState(false);
  const [showValidacionPopup, setShowValidacionPopup] = useState(false);
  const [showFinalizarOrden, setShowFinalizarOrden] = useState(false);
  
  // Form data states
  const [linkSeguimiento, setLinkSeguimiento] = useState(null);
  const [nuevoEstado, setNuevoEstado] = useState('');
  const [codigoEnvio, setCodigoEnvio] = useState('');
  const [nuevoMensaje, setNuevoMensaje] = useState('');
  const [mensajeVisibleTecnico, setMensajeVisibleTecnico] = useState(true);
  const [previewImage, setPreviewImage] = useState(null);
  const [codigoEnvioFinal, setCodigoEnvioFinal] = useState('');
  const [finalizando, setFinalizando] = useState(false);
  
  // Loading states
  const [uploading, setUploading] = useState(false);
  const [enviandoMensaje, setEnviandoMensaje] = useState(false);
  const [enviandoNotificacion, setEnviandoNotificacion] = useState(false);
  const [creandoGarantia, setCreandoGarantia] = useState(false);
  const [desbloqueando, setDesbloqueando] = useState(false);
  const [guardandoEnvio, setGuardandoEnvio] = useState(false);
  const [guardandoCliente, setGuardandoCliente] = useState(false);
  const [guardandoRepuesto, setGuardandoRepuesto] = useState(false);
  const [guardandoMaterial, setGuardandoMaterial] = useState(false);
  const [guardandoChecklist, setGuardandoChecklist] = useState(false);
  const [registrandoRI, setRegistrandoRI] = useState(false);
  const [guardandoCPI, setGuardandoCPI] = useState(false);
  const [solicitandoReemplazo, setSolicitandoReemplazo] = useState(false);
  const [autorizandoReemplazo, setAutorizandoReemplazo] = useState(false);
  const [generandoLogistica, setGenerandoLogistica] = useState(false);
  
  // Material search states
  const [materialSearchQuery, setMaterialSearchQuery] = useState('');
  const [materialSearchResults, setMaterialSearchResults] = useState([]);
  const [searchingMaterial, setSearchingMaterial] = useState(false);
  const searchTimeoutRef = useRef(null);
  
  // Edit states
  const [editingEnvio, setEditingEnvio] = useState(false);
  const [envioData, setEnvioData] = useState({});
  const [editClienteData, setEditClienteData] = useState(null);
  const [desbloqueoData, setDesbloqueoData] = useState({ imei_correcto: '', modelo: '', color: '', notas_resolucion: '' });
  
  // Material states
  const [materialSeleccionado, setMaterialSeleccionado] = useState(null);
  const [nuevoMaterialData, setNuevoMaterialData] = useState({ nombre: '', cantidad: 1, precio_unitario: '', coste: '', iva: 21 });
  const [materialEditIndex, setMaterialEditIndex] = useState(null);
  const [editMaterialData, setEditMaterialData] = useState({ precio_unitario: '', coste: '', iva: 21 });
  const [nuevoRepuestoData, setNuevoRepuestoData] = useState({ nombre: '', descripcion: '', precio_compra: '', precio_venta: '', stock: '1', stock_minimo: '5' });
  
  // Reemplazo states
  const [reemplazoData, setReemplazoData] = useState({ motivo: '', diagnostico_final: '' });
  const [autorizarReemplazoData, setAutorizarReemplazoData] = useState({ nuevo_modelo: '', nuevo_color: '', nuevo_imei: '', valor_dispositivo: '', notas: '' });

  const [cpiData, setCpiData] = useState({
    tipo_ot: 'b2c',
    opcion: '',      // 'cliente_ya_restablecio' | 'cliente_no_autoriza' | 'sat_realizo_restablecimiento'
    metodo: '',
    observaciones: '',
    // backward compat
    requiere_borrado: false,
    autorizacion_cliente: false,
    resultado: '',
  });


  // ===== DATA FETCHING =====
  const fetchOrden = async () => {
    try {
      setLoading(true);
      const [ordenRes, repuestosRes, mensajesRes, metricasRes] = await Promise.all([
        ordenesAPI.obtener(id),
        repuestosAPI.listar({ page_size: 100 }),
        ordenesAPI.obtenerMensajes(id),
        ordenesAPI.obtenerMetricas(id)
      ]);
      setOrden(ordenRes.data);
      setCpiData({
        tipo_ot: ordenRes.data?.cpi_tipo_ot || 'b2c',
        opcion: ordenRes.data?.cpi_opcion || derivarOpcionCPI(ordenRes.data),
        metodo: ordenRes.data?.cpi_metodo || '',
        observaciones: ordenRes.data?.cpi_observaciones || '',
        // backward compat
        requiere_borrado: Boolean(ordenRes.data?.cpi_requiere_borrado),
        autorizacion_cliente: Boolean(ordenRes.data?.cpi_autorizacion_cliente),
        resultado: ordenRes.data?.cpi_resultado || '',
      });
      // La API devuelve {items: [], total: X, ...} - extraer items
      setRepuestos(repuestosRes.data.items || []);
      setMensajes(mensajesRes.data);
      setMetricas(metricasRes.data);
      
      if (ordenRes.data.cliente_id) {
        const clienteRes = await clientesAPI.obtener(ordenRes.data.cliente_id);
        setCliente(clienteRes.data);
      }
      
      try {
        const garantiasRes = await ordenesAPI.obtenerGarantias(id);
        setOrdenesGarantia(garantiasRes.data || []);
      } catch (e) {}
    } catch (error) {
      toast.error('Error al cargar la orden');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrden();
    import('@/lib/api').then(({ notificacionesAPI }) => {
      notificacionesAPI.marcarLeidasPorOrden(id).then(() => {
        window.dispatchEvent(new Event('notificaciones-updated'));
      }).catch(() => {});
    });
  }, [id]);

  // Mostrar popup automático cuando la orden está en validación o reparado (admin o master)
  useEffect(() => {
    if (orden && (orden.estado === 'validacion' || orden.estado === 'reparado') && (isAdmin() || isMaster())) {
      setShowValidacionPopup(true);
    }
  }, [orden?.estado]);

  // ===== HANDLERS =====
  const canPrintWithPrices = isAdmin() || isMaster();

  const doPrintFull = useReactToPrint({
    contentRef: pdfRefFull,
    documentTitle: `Orden_${orden?.numero_orden || id}`,
  });

  const doPrintNoPrices = useReactToPrint({
    contentRef: pdfRefNoPrices,
    documentTitle: `Orden_${orden?.numero_orden || id}_sin_precios`,
  });

  const doPrintBlank = useReactToPrint({
    contentRef: pdfRefBlank,
    documentTitle: `Plantilla_Blanca_OT`,
  });

  const registrarImpresion = async (mode) => {
    try {
      await ordenesAPI.registrarImpresion(id, {
        mode,
        output: 'print',
        document_version: 'OT-PDF v1.1',
      });
    } catch (error) {
      console.warn('No se pudo registrar log de impresión', error?.response?.data || error?.message);
    }
  };

  const handlePrint = async () => {
    if (!canPrintWithPrices) {
      toast.error('Solo admin/master pueden generar la ficha completa con precios');
      return;
    }
    await registrarImpresion('full');
    doPrintFull();
  };

  const handlePrintNoPrices = async () => {
    await registrarImpresion('no_prices');
    doPrintNoPrices();
  };

  const handlePrintBlank = async () => {
    await registrarImpresion('blank_no_prices');
    doPrintBlank();
  };

  const handleCrearGarantia = async () => {
    setCreandoGarantia(true);
    try {
      const response = await ordenesAPI.crearGarantia(id);
      toast.success('Orden de garantía creada');
      navigate(`/ordenes/${response.data.id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al crear garantía');
    } finally {
      setCreandoGarantia(false);
    }
  };

  // Descargar ZIP de fotos
  const handleDescargarFotos = () => {
    const url = ordenesAPI.descargarFotosZip(id);
    window.open(url, '_blank');
    toast.success('Descargando fotos...');
  };

  // Finalizar orden: cambiar a enviado, registrar en contabilidad y liquidación
  const handleFinalizarOrden = async () => {
    if (!codigoEnvioFinal.trim()) {
      toast.error('Introduce el código de envío');
      return;
    }
    
    setFinalizando(true);
    try {
      // 1. Primero marcar QC como completado (el admin confirma que validó)
      await ordenesAPI.actualizar(id, {
        diagnostico_salida_realizado: true,
        funciones_verificadas: true,
        limpieza_realizada: true
      });
      
      // 2. Cambiar estado a enviado con código de envío
      await ordenesAPI.cambiarEstado(id, {
        nuevo_estado: 'enviado',
        codigo_envio: codigoEnvioFinal.trim(),
        usuario: user?.email || 'admin'
      });
      
      // 3. Registrar en liquidación si es de seguro
      if (orden?.tipo_servicio === 'seguro' || orden?.origen === 'insurama') {
        try {
          await ordenesAPI.registrarLiquidacion(id, {
            estado: 'pendiente_cobro',
            importe: orden?.presupuesto_total || 0,
            fecha_cierre: new Date().toISOString()
          });
        } catch (e) {
          console.log('Liquidación no disponible o ya registrada');
        }
      }
      
      toast.success('Orden finalizada y registrada correctamente');
      setShowFinalizarOrden(false);
      setShowValidacionPopup(false);
      setCodigoEnvioFinal('');
      fetchOrden();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al finalizar orden');
    } finally {
      setFinalizando(false);
    }
  };

  const handleSolicitarPieza = async (nombrePieza) => {
    try {
      await ordenesCompraAPI.crear({
        nombre_pieza: nombrePieza,
        orden_trabajo_id: id,
        solicitado_por: user?.username || 'admin'
      });
      toast.success('Solicitud de pieza enviada al administrador');
    } catch (error) {
      toast.error('Error al crear solicitud');
    }
  };

  const handleCambiarEstado = async (forzar = false) => {
    if (!nuevoEstado) return;
    if (nuevoEstado === 'enviado' && !codigoEnvio) {
      toast.error('Introduce el código de envío');
      return;
    }
    try {
      await ordenesAPI.cambiarEstado(id, {
        nuevo_estado: nuevoEstado,
        codigo_envio: codigoEnvio || undefined,
        usuario: 'admin',
        forzar_sin_validacion: forzar
      });
      toast.success(forzar ? 'Estado actualizado (forzado sin validar materiales)' : 'Estado actualizado');
      setShowCambioEstado(false);
      setNuevoEstado('');
      setCodigoEnvio('');
      fetchOrden();
    } catch (error) {
      const detail = error.response?.data?.detail || 'Error al cambiar estado';
      // Si el error es por materiales sin validar, ofrecer opción de forzar
      if (nuevoEstado === 'reparado' && detail.includes('material(es) sin validar')) {
        if (window.confirm(`${detail}\n\n¿Deseas FORZAR el cambio como administrador? (Se registrará en el historial)`)) {
          handleCambiarEstado(true);
          return;
        }
      }
      toast.error(detail);
    }
  };

  const handleRepresupuestar = async () => {
    if (!window.confirm('¿Estás seguro de marcar esta orden como "Re-presupuestar"? Se notificará al cliente.')) {
      return;
    }
    try {
      await ordenesAPI.cambiarEstado(id, {
        nuevo_estado: 're_presupuestar',
        usuario: 'admin'
      });
      toast.success('Orden marcada para re-presupuestar');
      fetchOrden();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al cambiar estado');
    }
  };

  const handleMarcarIrreparable = async () => {
    if (!window.confirm('¿Estás seguro de marcar esta orden como "Irreparable"? Esta acción indica que el dispositivo no se puede reparar.')) {
      return;
    }
    try {
      await ordenesAPI.cambiarEstado(id, {
        nuevo_estado: 'irreparable',
        usuario: 'admin'
      });
      toast.success('Orden marcada como irreparable');
      fetchOrden();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al cambiar estado');
    }
  };

  const handleAddMaterial = async (repuesto) => {
    setMaterialSeleccionado(repuesto);
    setNuevoMaterialData({
      nombre: repuesto ? repuesto.nombre : '',
      cantidad: 1,
      precio_unitario: repuesto ? repuesto.precio_venta : '',
      coste: repuesto ? repuesto.precio_compra : '',
      iva: 21
    });
    setShowAddMaterialDialog(true);
  };
  
  const handleConfirmAddMaterial = async () => {
    setGuardandoMaterial(true);
    try {
      const data = {
        cantidad: parseInt(nuevoMaterialData.cantidad),
        precio_unitario: parseFloat(nuevoMaterialData.precio_unitario) || 0,
        coste: parseFloat(nuevoMaterialData.coste) || 0,
        iva: parseFloat(nuevoMaterialData.iva) || 21,
        añadido_por_tecnico: false
      };
      if (materialSeleccionado) {
        data.repuesto_id = materialSeleccionado.id;
      } else {
        data.nombre = nuevoMaterialData.nombre;
      }
      await ordenesAPI.añadirMaterial(id, data);
      toast.success('Material añadido');
      setShowAddMaterialDialog(false);
      setMaterialSeleccionado(null);
      fetchOrden();
    } catch (error) {
      toast.error('Error al añadir material');
    } finally {
      setGuardandoMaterial(false);
    }
  };

  const handleConfirmEditMaterial = async () => {
    setGuardandoMaterial(true);
    try {
      await ordenesAPI.actualizarMaterial(id, materialEditIndex, {
        precio_unitario: parseFloat(editMaterialData.precio_unitario) || 0,
        coste: parseFloat(editMaterialData.coste) || 0,
        iva: parseFloat(editMaterialData.iva) || 21
      });
      toast.success('Precios actualizados');
      setShowEditMaterialDialog(false);
      fetchOrden();
    } catch (error) {
      toast.error('Error al actualizar precios');
    } finally {
      setGuardandoMaterial(false);
    }
  };

  // Búsqueda de materiales por nombre, SKU, etc.
  const handleMaterialSearch = (query) => {
    // Limpiar timeout anterior
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    
    if (!query || query.length < 2) {
      setMaterialSearchResults([]);
      return;
    }
    
    setSearchingMaterial(true);
    
    // Debounce de 300ms para no hacer muchas peticiones
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        // Usar endpoint de búsqueda rápida optimizado para autocompletado
        const res = await repuestosAPI.buscarRapido(query, null, 10);
        setMaterialSearchResults(res.data || []); // El endpoint devuelve array directo
      } catch (error) {
        console.error('Error buscando materiales:', error);
        setMaterialSearchResults([]);
      } finally {
        setSearchingMaterial(false);
      }
    }, 300);
  };

  const handleAbrirDesbloqueo = () => {
    setDesbloqueoData({
      imei_correcto: orden?.dispositivo?.imei || '',
      modelo: orden?.dispositivo?.modelo || '',
      color: orden?.dispositivo?.color || '',
      notas_resolucion: ''
    });
    setShowDesbloquearModal(true);
  };

  const handleDesbloquearConDatos = async () => {
    setDesbloqueando(true);
    try {
      const updateData = {
        bloqueada: false,
        notas_desbloqueo: desbloqueoData.notas_resolucion || 'Aprobado por administrador',
      };
      if (desbloqueoData.imei_correcto && desbloqueoData.imei_correcto !== orden?.dispositivo?.imei) {
        updateData['dispositivo.imei'] = desbloqueoData.imei_correcto;
        updateData.imei_actualizado = true;
        updateData.imei_anterior = orden?.dispositivo?.imei;
      }
      if (desbloqueoData.modelo && desbloqueoData.modelo !== orden?.dispositivo?.modelo) {
        updateData['dispositivo.modelo'] = desbloqueoData.modelo;
      }
      if (desbloqueoData.color && desbloqueoData.color !== orden?.dispositivo?.color) {
        updateData['dispositivo.color'] = desbloqueoData.color;
      }
      await ordenesAPI.actualizar(id, updateData);
      toast.success('Orden desbloqueada y datos actualizados correctamente');
      setShowDesbloquearModal(false);
      setDesbloqueoData({ imei_correcto: '', modelo: '', color: '', notas_resolucion: '' });
      fetchOrden();
    } catch (error) {
      toast.error('Error al desbloquear la orden');
    } finally {
      setDesbloqueando(false);
    }
  };

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    try {
      setUploading(true);
      let successCount = 0;
      for (const file of files) {
        try {
          await ordenesAPI.subirEvidencia(id, file);
          successCount++;
        } catch (err) {
          console.error('Error subiendo archivo:', err);
        }
      }
      if (successCount > 0) {
        toast.success(`${successCount} evidencia${successCount > 1 ? 's' : ''} subida${successCount > 1 ? 's' : ''}`);
        fetchOrden();
      }
    } catch (error) {
      toast.error('Error al subir evidencias');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleEnviarMensaje = async () => {
    if (!nuevoMensaje.trim()) return;
    setEnviandoMensaje(true);
    try {
      await ordenesAPI.añadirMensaje(id, {
        mensaje: nuevoMensaje.trim(),
        visible_tecnico: mensajeVisibleTecnico
      });
      setNuevoMensaje('');
      setMensajeVisibleTecnico(true);
      const mensajesRes = await ordenesAPI.obtenerMensajes(id);
      setMensajes(mensajesRes.data);
      toast.success('Mensaje enviado');
    } catch (error) {
      toast.error('Error al enviar mensaje');
    } finally {
      setEnviandoMensaje(false);
    }
  };

  const handleObtenerLinkSeguimiento = async () => {
    try {
      const response = await seguimientoAPI.obtenerLink(id);
      setLinkSeguimiento(response.data);
      setShowLinkSeguimiento(true);
    } catch (error) {
      toast.error('Error al obtener el link de seguimiento');
    }
  };

  const copyLinkToClipboard = () => {
    if (!linkSeguimiento) return;
    const link = `${window.location.origin}/seguimiento?codigo=${linkSeguimiento.token}`;
    navigator.clipboard.writeText(link);
    toast.success('Link copiado al portapapeles');
  };

  const handleEnviarNotificacion = async () => {
    setEnviandoNotificacion(true);
    try {
      const response = await ordenesAPI.enviarWhatsApp(id);
      toast.success(`✅ ${response.data.message}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al enviar notificación');
    } finally {
      setEnviandoNotificacion(false);
    }
  };

  // Handlers para generar recogida/envío
  const handleGenerarRecogida = async (datosEnvio) => {
    setGenerandoLogistica(true);
    try {
      // Por ahora guardamos los datos y mostramos mensaje de que la integración no está configurada
      // Cuando se configure la API de logística, aquí se llamará al endpoint
      await ordenesAPI.actualizarEnvio(id, {
        datos_recogida: datosEnvio,
        // codigo_recogida_entrada se rellenará automáticamente cuando haya integración
      });
      
      toast.info('Datos de recogida guardados. Configure la integración de logística para generar automáticamente el código de recogida.');
      setShowGenerarRecogida(false);
      fetchOrden();
    } catch (error) {
      toast.error('Error al guardar datos de recogida');
    } finally {
      setGenerandoLogistica(false);
    }
  };

  const handleGenerarEnvio = async (datosEnvio) => {
    setGenerandoLogistica(true);
    try {
      // Por ahora guardamos los datos y mostramos mensaje de que la integración no está configurada
      await ordenesAPI.actualizarEnvio(id, {
        datos_envio: datosEnvio,
        // codigo_recogida_salida se rellenará automáticamente cuando haya integración
      });
      
      toast.info('Datos de envío guardados. Configure la integración de logística para generar automáticamente el código de envío.');
      setShowGenerarEnvio(false);
      fetchOrden();
    } catch (error) {
      toast.error('Error al guardar datos de envío');
    } finally {
      setGenerandoLogistica(false);
    }
  };

  const handleEditCliente = () => {
    if (cliente) {
      setEditClienteData({ ...cliente });
      setShowEditCliente(true);
    }
  };

  const handleEditEnvio = () => {
    setEnvioData({
      numero_autorizacion: orden.numero_autorizacion || '',
      agencia_envio: orden.agencia_envio || '',
      codigo_recogida_entrada: orden.codigo_recogida_entrada || '',
      codigo_recogida_salida: orden.codigo_recogida_salida || '',
    });
    setEditingEnvio(true);
  };

  const handleGuardarEnvio = async () => {
    setGuardandoEnvio(true);
    try {
      await ordenesAPI.actualizarEnvio(id, envioData);
      toast.success('Datos de envío actualizados');
      setEditingEnvio(false);
      fetchOrden();
    } catch (error) {
      toast.error('Error al guardar datos de envío');
    } finally {
      setGuardandoEnvio(false);
    }
  };

  const handleGuardarCliente = async () => {
    if (!editClienteData) return;
    setGuardandoCliente(true);
    try {
      await clientesAPI.actualizar(editClienteData.id, editClienteData);
      setCliente(editClienteData);
      setShowEditCliente(false);
      toast.success('Cliente actualizado correctamente');
    } catch (error) {
      toast.error('Error al actualizar el cliente');
    } finally {
      setGuardandoCliente(false);
    }
  };

  const handleGuardarChecklist = async (partialData) => {
    setGuardandoChecklist(true);
    const ordenAnterior = orden;
    setOrden((prev) => ({ ...prev, ...partialData }));
    try {
      await ordenesAPI.actualizar(id, partialData);
    } catch (error) {
      setOrden(ordenAnterior);
      toast.error(error.response?.data?.detail || 'Error guardando checklist de calidad');
    } finally {
      setGuardandoChecklist(false);
    }
  };

  const handleRegistrarRI = async (resultado) => {
    if (!orden?.evidencias || orden.evidencias.length < 3) {
      toast.error('Para registrar RI necesitas al menos 3 evidencias/fotos en la OT');
      return;
    }

    setRegistrandoRI(true);
    try {
      await ordenesAPI.registrarReceivingInspection(id, {
        resultado_ri: resultado,
        checklist_visual: {
          estado_fisico_registrado: Boolean(orden.recepcion_estado_fisico_registrado),
          accesorios_registrados: Boolean(orden.recepcion_accesorios_registrados),
          checklist_recepcion: Boolean(orden.recepcion_checklist_completo),
        },
        fotos_recepcion: orden.evidencias.slice(0, 3),
        observaciones: orden.recepcion_notas || 'RI registrada desde OT',
        propiedad_cliente_estado: resultado === 'no_conforme' ? 'no_apto' : 'ok',
        propiedad_cliente_nota: resultado === 'no_conforme' ? 'Producto del cliente en no conformidad durante RI' : null,
      });
      toast.success(`Receiving Inspection registrada (${resultado})`);
      fetchOrden();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error registrando RI');
    } finally {
      setRegistrandoRI(false);
    }
  };

  // Inferir opción CPI desde campos legacy (backward compat)
  const derivarOpcionCPI = (data) => {
    if (!data?.cpi_resultado) return '';
    if (data.cpi_requiere_borrado) return 'sat_realizo_restablecimiento';
    if (data.cpi_autorizacion_cliente === false) return 'cliente_no_autoriza';
    return 'cliente_ya_restablecio';
  };

  const CPI_OPCIONES = {
    cliente_ya_restablecio:         { label: 'Ya venía restablecido por el cliente (verificado)', requiere_borrado: false, resultado: 'no_aplica', autorizacion: true },
    cliente_no_autoriza:            { label: 'Cliente NO autoriza restablecer/borrar (Privacidad alta)', requiere_borrado: false, resultado: 'no_aplica', autorizacion: false },
    sat_realizo_restablecimiento:   { label: 'Restablecimiento realizado por el SAT (NIST 800-88)', requiere_borrado: true, resultado: 'completado', autorizacion: true },
  };

  const handleGuardarCPI = async () => {
    if (!cpiData.opcion) {
      toast.error('Debes seleccionar una opción de privacidad/CPI');
      return;
    }
    if (cpiData.opcion === 'sat_realizo_restablecimiento' && !cpiData.metodo) {
      toast.error('Selecciona el método de restablecimiento (SAT)');
      return;
    }

    const opcionMeta = CPI_OPCIONES[cpiData.opcion] || {};
    const payload = {
      opcion:             cpiData.opcion,
      tipo_ot:            cpiData.tipo_ot,
      requiere_borrado:   opcionMeta.requiere_borrado ?? false,
      autorizacion_cliente: opcionMeta.autorizacion ?? null,
      metodo:             cpiData.opcion === 'sat_realizo_restablecimiento' ? (cpiData.metodo || null) : null,
      resultado:          opcionMeta.resultado || null,
      observaciones:      cpiData.observaciones || null,
    };

    setGuardandoCPI(true);
    try {
      await ordenesAPI.registrarCPI(id, payload);
      toast.success('Registro CPI/NIST actualizado');
      fetchOrden();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error guardando CPI/NIST');
    } finally {
      setGuardandoCPI(false);
    }
  };

  const handleCrearRepuesto = async () => {
    if (!nuevoRepuestoData.nombre || !nuevoRepuestoData.precio_venta) {
      toast.error('El nombre y precio de venta son obligatorios');
      return;
    }
    setGuardandoRepuesto(true);
    try {
      const response = await repuestosAPI.crear({
        nombre: nuevoRepuestoData.nombre,
        descripcion: nuevoRepuestoData.descripcion,
        precio_compra: parseFloat(nuevoRepuestoData.precio_compra) || 0,
        precio_venta: parseFloat(nuevoRepuestoData.precio_venta),
        stock: parseInt(nuevoRepuestoData.stock) || 1,
        stock_minimo: parseInt(nuevoRepuestoData.stock_minimo) || 5
      });
      setRepuestos([...repuestos, response.data]);
      setNuevoRepuestoData({ nombre: '', descripcion: '', precio_compra: '', precio_venta: '', stock: '1', stock_minimo: '5' });
      setShowNuevoRepuesto(false);
      toast.success('Repuesto creado correctamente');
      handleAddMaterial(response.data);
    } catch (error) {
      toast.error('Error al crear el repuesto');
    } finally {
      setGuardandoRepuesto(false);
    }
  };

  const handleSolicitarReemplazo = async () => {
    if (!reemplazoData.motivo.trim()) {
      toast.error('Debes indicar el motivo del reemplazo');
      return;
    }
    setSolicitandoReemplazo(true);
    try {
      await ordenesAPI.solicitarReemplazo(orden.id, {
        motivo: reemplazoData.motivo,
        diagnostico_final: reemplazoData.diagnostico_final || null
      });
      toast.success('Solicitud de reemplazo enviada. La orden está bloqueada hasta autorización del administrador.');
      setShowSolicitarReemplazo(false);
      setReemplazoData({ motivo: '', diagnostico_final: '' });
      fetchOrden();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al enviar solicitud');
    } finally {
      setSolicitandoReemplazo(false);
    }
  };

  const handleAutorizarReemplazo = async () => {
    if (!autorizarReemplazoData.nuevo_modelo || !autorizarReemplazoData.nuevo_imei || !autorizarReemplazoData.valor_dispositivo) {
      toast.error('Modelo, IMEI y valor del dispositivo son obligatorios');
      return;
    }
    setAutorizandoReemplazo(true);
    try {
      await ordenesAPI.autorizarReemplazo(orden.id, {
        nuevo_modelo: autorizarReemplazoData.nuevo_modelo,
        nuevo_color: autorizarReemplazoData.nuevo_color || '',
        nuevo_imei: autorizarReemplazoData.nuevo_imei,
        valor_dispositivo: parseFloat(autorizarReemplazoData.valor_dispositivo),
        notas: autorizarReemplazoData.notas || null
      });
      toast.success('Reemplazo autorizado. Los materiales de reparación han sido eliminados.');
      setShowAutorizarReemplazo(false);
      setAutorizarReemplazoData({ nuevo_modelo: '', nuevo_color: '', nuevo_imei: '', valor_dispositivo: '', notas: '' });
      fetchOrden();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al autorizar reemplazo');
    } finally {
      setAutorizandoReemplazo(false);
    }
  };

  const handleRechazarReemplazo = async (motivo) => {
    try {
      await ordenesAPI.rechazarReemplazo(orden.id, motivo);
      toast.success('Solicitud de reemplazo rechazada');
      fetchOrden();
    } catch (error) {
      toast.error('Error al rechazar reemplazo');
    }
  };

  // ===== LOADING / NOT FOUND =====
  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-10 bg-slate-200 rounded w-48" />
        <div className="h-64 bg-slate-200 rounded-xl" />
      </div>
    );
  }

  if (!orden) {
    return (
      <div className="text-center py-16">
        <p className="text-lg">Orden no encontrada</p>
        <Link to="/ordenes">
          <Button className="mt-4">Volver a órdenes</Button>
        </Link>
      </div>
    );
  }

  // ===== COMPUTED VALUES =====
  const currentStatus = statusConfig[orden.estado];
  const currentStep = currentStatus?.step || 0;
  const totalMateriales = orden.materiales?.reduce((acc, m) => acc + (m.precio_unitario * m.cantidad), 0) || 0;
  const todasLasFotos = [
    ...(orden.evidencias || []).map(f => ({ src: getUploadUrl(f), tipo: 'admin' })),
    ...(orden.evidencias_tecnico || []).map(f => ({ src: getUploadUrl(f), tipo: 'tecnico' })),
    ...(orden.fotos_antes || []).map(f => ({ src: getUploadUrl(f), tipo: 'tecnico', categoria: 'antes' })),
    ...(orden.fotos_despues || []).map(f => ({ src: getUploadUrl(f), tipo: 'tecnico', categoria: 'despues' }))
  ];

  // ===== RENDER =====
  return (
    <div className="space-y-6 animate-fade-in" data-testid="orden-detalle-page">
      {/* Header - Using refactored component */}
      <OrdenDetalleHeader
        orden={orden}
        metricas={metricas}
        onBack={() => navigate(-1)}
        onPrint={handlePrint}
        onPrintNoPrices={handlePrintNoPrices}
        onPrintBlank={handlePrintBlank}
        canPrintWithPrices={canPrintWithPrices}
        onShowEtiqueta={() => setShowEtiqueta(true)}
        onObtenerLinkSeguimiento={handleObtenerLinkSeguimiento}
        onCrearGarantia={handleCrearGarantia}
        creandoGarantia={creandoGarantia}
        onEnviarNotificacion={handleEnviarNotificacion}
        enviandoNotificacion={enviandoNotificacion}
        onShowCambioEstado={() => setShowCambioEstado(true)}
        onGenerarRecogida={() => setShowGenerarRecogida(true)}
        onGenerarEnvio={() => setShowGenerarEnvio(true)}
        onSolicitarRepresupuestar={handleRepresupuestar}
        onMarcarIrreparable={handleMarcarIrreparable}
      />

      {/* Banner de Validación - Cuando la orden está lista para validar */}
      {(orden.estado === 'validacion' || orden.estado === 'reparado') && (isAdmin() || isMaster()) && (
        <Card className="border-green-300 bg-green-50">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-8 h-8 text-green-600" />
                <div>
                  <p className="font-semibold text-green-800">Orden lista para envío</p>
                  <p className="text-sm text-green-600">El técnico ha completado la reparación. Valida y procede con el envío.</p>
                </div>
              </div>
              <Button 
                className="bg-green-600 hover:bg-green-700"
                onClick={() => setShowValidacionPopup(true)}
                data-testid="btn-iniciar-validacion"
              >
                <Send className="w-4 h-4 mr-2" />
                Iniciar Validación y Envío
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Blocked Warning - Using refactored component */}
      <OrdenBloqueadaWarning orden={orden} onAbrirDesbloqueo={handleAbrirDesbloqueo} />

      {/* Métricas de Tiempo */}
      {metricas && (
        <Card className={metricas.en_retraso ? 'border-red-300' : ''}>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Timer className="w-5 h-5" />
              Métricas de Tiempo
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="text-center p-3 bg-slate-50 rounded-lg">
                <p className="text-xs text-muted-foreground uppercase">Desde Creación</p>
                <p className="text-xl font-bold">{metricas.dias_desde_creacion || 0}d</p>
                <p className="text-xs text-muted-foreground">{formatHours(metricas.tiempo_desde_creacion_horas)}</p>
              </div>
              <div className="text-center p-3 bg-blue-50 rounded-lg">
                <p className="text-xs text-muted-foreground uppercase">Logística</p>
                <p className="text-xl font-bold text-blue-600">{formatHours(metricas.tiempo_logistica_horas)}</p>
                <p className="text-xs text-muted-foreground">Creación → Recepción</p>
              </div>
              <div className="text-center p-3 bg-purple-50 rounded-lg">
                <p className="text-xs text-muted-foreground uppercase">Espera Taller</p>
                <p className="text-xl font-bold text-purple-600">{formatHours(metricas.tiempo_espera_taller_horas)}</p>
                <p className="text-xs text-muted-foreground">Recepción → Inicio</p>
              </div>
              <div className="text-center p-3 bg-green-50 rounded-lg">
                <p className="text-xs text-muted-foreground uppercase">Reparación</p>
                <p className="text-xl font-bold text-green-600">{formatHours(metricas.tiempo_reparacion_horas)}</p>
                <p className="text-xs text-muted-foreground">Inicio → Fin</p>
              </div>
              <div className={`text-center p-3 rounded-lg ${metricas.en_retraso ? 'bg-red-50' : 'bg-emerald-50'}`}>
                <p className="text-xs text-muted-foreground uppercase">Total Proceso</p>
                <p className={`text-xl font-bold ${metricas.en_retraso ? 'text-red-600' : 'text-emerald-600'}`}>
                  {formatHours(metricas.tiempo_total_proceso_horas)}
                </p>
                <p className="text-xs text-muted-foreground">Creación → Envío</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Status Progress */}
      <Card className="print:hidden">
        <CardContent className="py-6">
          <div className="flex items-center justify-between overflow-x-auto">
            {statusOrder.map((status, index) => {
              const config = statusConfig[status];
              const Icon = config?.icon || Clock;
              const isCompleted = currentStep > (config?.step || 0);
              const isCurrent = orden.estado === status;
              
              return (
                <div key={status} className="flex items-center flex-1 min-w-0">
                  <div className="flex flex-col items-center">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                      isCompleted ? 'bg-green-500 text-white' :
                      isCurrent ? 'bg-primary text-white' :
                      'bg-slate-200 text-slate-500'
                    }`}>
                      {isCompleted ? <Check className="w-5 h-5" /> : <Icon className="w-5 h-5" />}
                    </div>
                    <span className={`text-xs mt-2 text-center whitespace-nowrap ${
                      isCurrent ? 'font-semibold text-primary' : 'text-muted-foreground'
                    }`}>
                      {config?.label || status}
                    </span>
                  </div>
                  {index < statusOrder.length - 1 && (
                    <div className={`flex-1 h-1 mx-2 rounded min-w-4 ${
                      currentStep > (config?.step || 0) ? 'bg-green-500' : 'bg-slate-200'
                    }`} />
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="info">Información</TabsTrigger>
          <TabsTrigger value="materiales">Materiales</TabsTrigger>
          <TabsTrigger value="fotos">Fotos ({todasLasFotos.length})</TabsTrigger>
          <TabsTrigger value="bloqueos">
            Bloqueos {(orden.historial_bloqueos?.length || 0) > 0 && (
              <Badge variant="destructive" className="ml-1 px-1.5 py-0 text-xs">
                {orden.historial_bloqueos.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="comunicaciones">Mensajes ({mensajes.length})</TabsTrigger>
        </TabsList>

        {/* Tab: Información */}
        <TabsContent value="info" className="space-y-6 mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              {/* RI (Receiving Inspection) y Cuarentena Card */}
              <Card data-testid="orden-ri-card">
                <CardHeader>
                  <CardTitle className="text-base">Receiving Inspection (RI) y Cuarentena</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">

              <Card data-testid="orden-cpi-card">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    CPI / NIST 800-88 — Privacidad del dispositivo
                    <span className="text-xs font-normal text-amber-600 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded" data-testid="cpi-solo-tecnico-badge">
                      Solo técnico
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {/* Admin/master: solo lectura */}
                  <div className="space-y-2 opacity-70 pointer-events-none" data-testid="cpi-readonly-view">
                    {orden?.cpi_opcion ? (
                      <div className="p-3 bg-gray-50 border rounded-lg">
                        <p className="text-xs text-gray-500 mb-1">Opción seleccionada</p>
                        <p className="text-sm font-medium">
                          {{
                            cliente_ya_restablecio: 'Ya venía restablecido por el cliente (verificado)',
                            cliente_no_autoriza:    'Cliente NO autoriza restablecer/borrar (Privacidad alta)',
                            sat_realizo_restablecimiento: 'Restablecimiento realizado por el SAT (NIST 800-88)',
                          }[orden.cpi_opcion] || orden.cpi_opcion}
                        </p>
                        {orden?.cpi_metodo && (
                          <p className="text-xs text-gray-500 mt-1">Método: {orden.cpi_metodo}</p>
                        )}
                        {orden?.cpi_observaciones && (
                          <p className="text-xs text-gray-500 mt-1">Obs: {orden.cpi_observaciones}</p>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-400 italic">CPI pendiente de registro por el técnico</p>
                    )}
                    {orden?.cpi_fecha && (
                      <p className="text-xs text-gray-400">
                        Registrado por {orden.cpi_usuario_nombre || 'Nombre no configurado'} · {new Date(orden.cpi_fecha).toLocaleString('es-ES')}
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>

                  <div className="text-sm text-muted-foreground">
                    RI obligatoria: {orden.ri_obligatoria ? 'Sí' : 'No'} · RI completada: {orden.ri_completada ? 'Sí' : 'No'} · Resultado: {orden.ri_resultado || '-'}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Para registrar RI se usarán las primeras 3 evidencias subidas en la OT.
                  </div>
                  {!isTecnico() ? (
                    <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-2 py-1.5" data-testid="ri-solo-tecnico-notice">
                      Solo técnico — Los botones de RI solo están disponibles para el rol técnico
                    </p>
                  ) : (
                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" size="sm" disabled={registrandoRI} onClick={() => handleRegistrarRI('ok')} data-testid="orden-ri-registrar-ok-button">
                      RI OK
                    </Button>
                    <Button variant="secondary" size="sm" disabled={registrandoRI} onClick={() => handleRegistrarRI('sospechoso')} data-testid="orden-ri-registrar-sospechoso-button">
                      RI Sospechoso
                    </Button>
                    <Button variant="destructive" size="sm" disabled={registrandoRI} onClick={() => handleRegistrarRI('no_conforme')} data-testid="orden-ri-registrar-no-conforme-button">
                      RI No Conforme (Cuarentena)
                    </Button>
                  </div>
                  )}
                </CardContent>
              </Card>
              <OrdenClienteCard cliente={cliente} onEdit={handleEditCliente} />
              <OrdenDispositivoCard dispositivo={orden.dispositivo} />
              
              {/* Manual de Reparación Apple - Solo visible para técnicos */}
              {isTecnico() && (
                <AppleManualCard 
                  dispositivo={orden.dispositivo} 
                  problema={orden.problema_reportado || orden.diagnostico_tecnico}
                />
              )}
              <OrdenEnvioCard
                orden={orden}
                isAdmin={isAdmin()}
                editingEnvio={editingEnvio}
                envioData={envioData}
                setEnvioData={setEnvioData}
                onEditEnvio={handleEditEnvio}
                onGuardarEnvio={handleGuardarEnvio}
                onCancelEdit={() => setEditingEnvio(false)}
                guardandoEnvio={guardandoEnvio}
                onGenerarRecogida={() => setShowGenerarRecogida(true)}
                onGenerarEnvio={() => setShowGenerarEnvio(true)}
              />
              <OrdenInsuramaPanel orden={orden} />
              {/* Diagnóstico y Control de Calidad - SOLO visible para técnicos */}
              {isTecnico() && (
                <OrdenDiagnosticoCard
                  orden={orden}
                  tecnicoAsignado={orden.tecnico_asignado}
                  onGuardarChecklist={handleGuardarChecklist}
                  guardandoChecklist={guardandoChecklist}
                  puedeEditarDiagnosticoQC={true}
                  puedeEditarBateria={true}
                />
              )}
              <OrdenHistorialEstados historial={orden.historial_estados} statusConfig={statusConfig} />
            </div>

            {/* Right Column - QR Code */}
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-center">Código de Barras</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col items-center">
                  <div className="qr-container p-6 bg-white">
                    <QRCode value={orden.numero_orden} size={200} />
                  </div>
                  <p className="mt-4 font-mono text-sm text-muted-foreground">{orden.numero_orden}</p>
                  <p className="text-xs text-muted-foreground mt-1">Escanea para cambiar estado</p>
                </CardContent>
              </Card>
              
              {/* Subestado Card */}
              <OrdenSubestadoCard 
                ordenId={orden.id}
                subestadoActual={orden.subestado}
                motivoActual={orden.motivo_subestado}
                fechaRevision={orden.fecha_revision_subestado}
                onUpdate={fetchOrden}
              />
              
              {orden.notas && (
                <Card>
                  <CardHeader><CardTitle>Notas</CardTitle></CardHeader>
                  <CardContent><p className="text-sm">{orden.notas}</p></CardContent>
                </Card>
              )}
            </div>
          </div>
        </TabsContent>

        {/* Tab: Materiales */}
        <TabsContent value="materiales" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Package className="w-5 h-5" />
                  Materiales y Servicios
                </div>
                <div className="flex gap-2">
                  {isTecnico() && !orden.bloqueada && !orden.reemplazo_solicitado && orden.estado !== 'reemplazo' && (
                    <Button variant="destructive" onClick={() => setShowSolicitarReemplazo(true)} data-testid="btn-solicitar-reemplazo">
                      <Repeat className="w-4 h-4 mr-2" />
                      Dispositivo NO Reparable
                    </Button>
                  )}
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {/* Alerta de reemplazo solicitado (para admin) */}
              {isAdmin() && orden.reemplazo_solicitado && !orden.reemplazo_autorizado && (
                <div className="mb-4 p-4 bg-red-50 border-2 border-red-300 rounded-lg">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-bold text-red-700 flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5" />
                        REEMPLAZO SOLICITADO
                      </p>
                      <p className="text-sm text-red-600 mt-1">El técnico ha determinado que el dispositivo NO es reparable.</p>
                      <p className="text-sm text-muted-foreground mt-2"><strong>Motivo:</strong> {orden.reemplazo_motivo}</p>
                      {orden.reemplazo_diagnostico && (
                        <p className="text-sm text-muted-foreground"><strong>Diagnóstico:</strong> {orden.reemplazo_diagnostico}</p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="destructive" onClick={() => {
                        const motivo = prompt('Motivo del rechazo:');
                        if (motivo !== null) handleRechazarReemplazo(motivo);
                      }}>Rechazar</Button>
                      <Button size="sm" onClick={() => setShowAutorizarReemplazo(true)} className="bg-green-600 hover:bg-green-700">
                        Autorizar Reemplazo
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {/* Info de reemplazo autorizado */}
              {orden.reemplazo_autorizado && orden.dispositivo_reemplazo && (
                <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <p className="font-bold text-green-700 flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5" />
                    REEMPLAZO AUTORIZADO
                  </p>
                  <div className="grid grid-cols-2 gap-2 mt-2 text-sm">
                    <div><strong>Nuevo Dispositivo:</strong> {orden.dispositivo_reemplazo.modelo}</div>
                    <div><strong>Color:</strong> {orden.dispositivo_reemplazo.color}</div>
                    <div><strong>IMEI:</strong> <span className="font-mono">{orden.dispositivo_reemplazo.imei}</span></div>
                    <div><strong>Valor:</strong> {orden.dispositivo_reemplazo.valor?.toFixed(2)}€</div>
                  </div>
                </div>
              )}

              {/* SKU Scanner / Material Search (solo admin) */}
              {isAdmin() && (
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <QrCode className="w-4 h-4 text-blue-600" />
                    <span className="text-sm font-medium text-blue-700">Buscar Material (nombre, SKU o código)</span>
                  </div>
                  <div className="relative">
                    <Input
                      placeholder="Escribe iPhone, batería, Samsung, SKU..."
                      className="h-9"
                      data-testid="material-search-input"
                      value={materialSearchQuery}
                      onChange={(e) => {
                        setMaterialSearchQuery(e.target.value);
                        handleMaterialSearch(e.target.value);
                      }}
                      onKeyDown={async (e) => {
                        if (e.key === 'Enter' && materialSearchResults.length > 0) {
                          await handleAddMaterial(materialSearchResults[0]);
                          setMaterialSearchQuery('');
                          setMaterialSearchResults([]);
                          toast.success(`${materialSearchResults[0].nombre} añadido`);
                        } else if (e.key === 'Escape') {
                          setMaterialSearchResults([]);
                        }
                      }}
                    />
                    {/* Dropdown de resultados */}
                    {materialSearchResults.length > 0 && (
                      <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-64 overflow-y-auto">
                        {materialSearchResults.map((item, idx) => (
                          <div
                            key={item.id}
                            className={`p-2 cursor-pointer hover:bg-blue-50 border-b last:border-b-0 ${idx === 0 ? 'bg-blue-50' : ''}`}
                            onClick={async () => {
                              await handleAddMaterial(item);
                              setMaterialSearchQuery('');
                              setMaterialSearchResults([]);
                              toast.success(`${item.nombre} añadido`);
                            }}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-sm truncate" title={item.nombre}>
                                  {item.nombre_es || item.nombre}
                                </p>
                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                  <span>SKU: {item.sku || item.sku_proveedor || '-'}</span>
                                  <span>|</span>
                                  <span>Stock: {item.stock}</span>
                                  <span>|</span>
                                  <span className="font-medium">{item.precio_venta?.toFixed(2)}€</span>
                                </div>
                              </div>
                              <div className="flex items-center gap-1 ml-2">
                                {item.calidad_pantalla && (
                                  <CalidadPantallaBadge calidad={item.calidad_pantalla} size="xs" showIcon={false} />
                                )}
                                <Badge variant="secondary" className="text-xs">{item.proveedor || item.categoria}</Badge>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    {materialSearchQuery && materialSearchResults.length === 0 && !searchingMaterial && (
                      <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg p-3 text-center text-muted-foreground text-sm">
                        No se encontraron materiales con "{materialSearchQuery}"
                      </div>
                    )}
                    {searchingMaterial && (
                      <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg p-3 text-center text-muted-foreground text-sm">
                        Buscando...
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Enter para añadir el primero, click para seleccionar</p>
                </div>
              )}

              <TablaMaterialesEditable
                ordenId={id}
                materiales={orden.materiales || []}
                onUpdate={fetchOrden}
                readOnly={!isAdmin()}
                mostrarCoste={isAdmin()}
              />

              {/* Resumen Financiero */}
              {(orden.materiales?.length > 0 || orden.mano_obra > 0) && (
                <div className="mt-6 p-4 bg-gradient-to-r from-slate-50 to-slate-100 border rounded-lg" data-testid="resumen-financiero">
                  <h4 className="font-semibold text-lg mb-3 flex items-center gap-2">
                    <DollarSign className="w-5 h-5 text-green-600" />
                    Resumen Financiero
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="p-3 bg-white rounded-lg border">
                      <p className="text-xs text-muted-foreground">Subtotal Materiales</p>
                      <p className="text-lg font-semibold">{(orden.subtotal_materiales || 0).toFixed(2)}€</p>
                    </div>
                    {orden.mano_obra > 0 && (
                      <div className="p-3 bg-white rounded-lg border">
                        <p className="text-xs text-muted-foreground">Mano de Obra</p>
                        <p className="text-lg font-semibold">{(orden.mano_obra || 0).toFixed(2)}€</p>
                      </div>
                    )}
                    <div className="p-3 bg-white rounded-lg border">
                      <p className="text-xs text-muted-foreground">IVA</p>
                      <p className="text-lg font-semibold">{(orden.total_iva || 0).toFixed(2)}€</p>
                    </div>
                    <div className="p-3 bg-green-50 rounded-lg border-2 border-green-200">
                      <p className="text-xs text-green-600 font-medium">TOTAL PRESUPUESTO</p>
                      <p className="text-xl font-bold text-green-700">{(orden.presupuesto_total || 0).toFixed(2)}€</p>
                    </div>
                    {isAdmin() && (
                      <>
                        <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                          <p className="text-xs text-amber-600">Coste Total</p>
                          <p className="text-lg font-semibold text-amber-700">{(orden.coste_total || 0).toFixed(2)}€</p>
                        </div>
                        <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                          <p className="text-xs text-blue-600">Beneficio Estimado</p>
                          <p className="text-lg font-semibold text-blue-700">{(orden.beneficio_estimado || 0).toFixed(2)}€</p>
                        </div>
                      </>
                    )}
                  </div>
                  
                  {/* Input de mano de obra para admin */}
                  {isAdmin() && (
                    <div className="mt-4 pt-4 border-t flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        <Label className="text-sm whitespace-nowrap">Mano de obra:</Label>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          className="w-28"
                          defaultValue={orden.mano_obra || 0}
                          onBlur={async (e) => {
                            const valor = parseFloat(e.target.value) || 0;
                            if (valor !== (orden.mano_obra || 0)) {
                              try {
                                await ordenesAPI.actualizarManoObra(id, valor);
                                toast.success('Mano de obra actualizada');
                                fetchOrden();
                              } catch (err) {
                                toast.error('Error al actualizar mano de obra');
                              }
                            }
                          }}
                        />
                        <span className="text-sm text-muted-foreground">€</span>
                      </div>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={async () => {
                          try {
                            await ordenesAPI.recalcularTotales(id);
                            toast.success('Totales recalculados');
                            fetchOrden();
                          } catch (err) {
                            toast.error('Error al recalcular');
                          }
                        }}
                      >
                        <Calculator className="w-4 h-4 mr-2" />
                        Recalcular
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Fotos */}
        <TabsContent value="fotos" className="mt-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <FileImage className="w-5 h-5" />
                Fotos del Dispositivo
              </CardTitle>
              <div className="flex gap-2">
                {todasLasFotos.length > 0 && (
                  <Button variant="outline" onClick={() => {
                    const token = localStorage.getItem('token');
                    const url = `${process.env.REACT_APP_BACKEND_URL}/api/ordenes/${id}/fotos-zip`;
                    fetch(url, { headers: { 'Authorization': `Bearer ${token}` }})
                      .then(res => {
                        if (!res.ok) throw new Error('Error en la descarga');
                        return res.blob();
                      })
                      .then(blob => {
                        const downloadUrl = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = downloadUrl;
                        a.download = `${orden.numero_orden}_fotos.zip`;
                        a.click();
                        window.URL.revokeObjectURL(downloadUrl);
                        toast.success('Descarga iniciada');
                      })
                      .catch(() => toast.error('Error al descargar fotos'));
                  }} data-testid="btn-descargar-zip">
                    <Package className="w-4 h-4 mr-2" />
                    Descargar ZIP
                  </Button>
                )}
                <input type="file" ref={fileInputRef} onChange={handleFileUpload} accept="image/*" multiple className="hidden" />
                <Button variant="outline" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
                  <Upload className="w-4 h-4 mr-2" />
                  {uploading ? 'Subiendo...' : 'Subir Fotos'}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {todasLasFotos.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No hay fotos del dispositivo</p>
              ) : (
                <>
                  {/* Sección ANTES */}
                  {(() => {
                    const fotosAntes = todasLasFotos.filter(f => f.categoria === 'antes');
                    return fotosAntes.length > 0 && (
                      <div>
                        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                          <Badge className="bg-amber-500 text-white">ANTES</Badge>
                          <span className="text-muted-foreground text-sm">({fotosAntes.length} fotos)</span>
                        </h3>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                          {fotosAntes.map((foto, index) => (
                            <div key={`antes-${index}`} className="relative aspect-square rounded-lg border-2 border-amber-300 overflow-hidden cursor-pointer hover:opacity-90 transition-opacity"
                              onClick={() => { setPreviewImage(foto.src); setShowImagePreview(true); }}>
                              <img src={foto.src} alt={`Antes ${index + 1}`} className="w-full h-full object-cover" />
                              <Badge className="absolute bottom-1 left-1 text-[10px]" variant="secondary">
                                Técnico
                              </Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })()}

                  {/* Sección DESPUÉS */}
                  {(() => {
                    const fotosDespues = todasLasFotos.filter(f => f.categoria === 'despues');
                    return fotosDespues.length > 0 && (
                      <div>
                        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                          <Badge className="bg-green-500 text-white">DESPUÉS</Badge>
                          <span className="text-muted-foreground text-sm">({fotosDespues.length} fotos)</span>
                        </h3>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                          {fotosDespues.map((foto, index) => (
                            <div key={`despues-${index}`} className="relative aspect-square rounded-lg border-2 border-green-300 overflow-hidden cursor-pointer hover:opacity-90 transition-opacity"
                              onClick={() => { setPreviewImage(foto.src); setShowImagePreview(true); }}>
                              <img src={foto.src} alt={`Después ${index + 1}`} className="w-full h-full object-cover" />
                              <Badge className="absolute bottom-1 left-1 text-[10px]" variant="secondary">
                                Técnico
                              </Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })()}

                  {/* Sección OTRAS FOTOS (Admin y técnico generales) */}
                  {(() => {
                    const otrasfotos = todasLasFotos.filter(f => !f.categoria);
                    return otrasfotos.length > 0 && (
                      <div>
                        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                          <Badge variant="outline">OTRAS FOTOS</Badge>
                          <span className="text-muted-foreground text-sm">({otrasfotos.length} fotos)</span>
                        </h3>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                          {otrasfotos.map((foto, index) => (
                            <div key={`otras-${index}`} className="relative aspect-square rounded-lg border overflow-hidden cursor-pointer hover:opacity-90 transition-opacity"
                              onClick={() => { setPreviewImage(foto.src); setShowImagePreview(true); }}>
                              <img src={foto.src} alt={`Foto ${index + 1}`} className="w-full h-full object-cover" />
                              <Badge className="absolute bottom-1 left-1 text-[10px]" variant={foto.tipo === 'admin' ? 'default' : 'secondary'}>
                                {foto.tipo === 'admin' ? 'Admin' : 'Técnico'}
                              </Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })()}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Bloqueos - Using refactored component */}
        <TabsContent value="bloqueos" className="mt-6">
          <OrdenBloqueosTab orden={orden} />
        </TabsContent>

        {/* Tab: Comunicaciones - Using refactored component */}
        <TabsContent value="comunicaciones" className="mt-6">
          <OrdenMensajesTab
            mensajes={mensajes}
            nuevoMensaje={nuevoMensaje}
            setNuevoMensaje={setNuevoMensaje}
            mensajeVisibleTecnico={mensajeVisibleTecnico}
            setMensajeVisibleTecnico={setMensajeVisibleTecnico}
            onEnviarMensaje={handleEnviarMensaje}
            enviandoMensaje={enviandoMensaje}
            isAdmin={isAdmin()}
          />
        </TabsContent>
      </Tabs>

      {/* ===== DIALOGS ===== */}
      
      {/* Etiqueta Dialog */}
      {showEtiqueta && <EtiquetaOrden orden={orden} onClose={() => setShowEtiqueta(false)} />}

      {/* Cambio Estado Modal */}
      <OrdenCambioEstadoModal
        open={showCambioEstado}
        onOpenChange={setShowCambioEstado}
        nuevoEstado={nuevoEstado}
        setNuevoEstado={setNuevoEstado}
        codigoEnvio={codigoEnvio}
        setCodigoEnvio={setCodigoEnvio}
        onCambiarEstado={handleCambiarEstado}
        isTecnico={isTecnico()}
      />

      {/* Desbloquear Modal */}
      <OrdenDesbloquearModal
        open={showDesbloquearModal}
        onOpenChange={setShowDesbloquearModal}
        orden={orden}
        desbloqueoData={desbloqueoData}
        setDesbloqueoData={setDesbloqueoData}
        onDesbloquear={handleDesbloquearConDatos}
        desbloqueando={desbloqueando}
      />

      {/* Image Preview Dialog */}
      <Dialog open={showImagePreview} onOpenChange={setShowImagePreview}>
        <DialogContent className="max-w-3xl p-2">
          <Button variant="ghost" size="icon" className="absolute right-2 top-2 z-10" onClick={() => setShowImagePreview(false)}>
            <X className="w-4 h-4" />
          </Button>
          {previewImage && <img src={previewImage} alt="Preview" className="w-full h-auto rounded-lg" />}
        </DialogContent>
      </Dialog>

      {/* Link de Seguimiento Dialog */}
      <Dialog open={showLinkSeguimiento} onOpenChange={setShowLinkSeguimiento}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ExternalLink className="w-5 h-5" />
              Link de Seguimiento para el Cliente
            </DialogTitle>
            <DialogDescription>
              Comparte este link con el cliente para que pueda seguir el estado de su reparación.
            </DialogDescription>
          </DialogHeader>
          {linkSeguimiento && (
            <div className="space-y-4">
              <div className="p-4 bg-slate-50 rounded-lg space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground uppercase">Código de Seguimiento</p>
                  <p className="font-mono text-xl font-bold">{linkSeguimiento.token}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase">Teléfono (para verificar)</p>
                  <p className="font-medium">{linkSeguimiento.telefono_hint}</p>
                </div>
              </div>
              <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                <p className="text-xs text-blue-600 mb-2">Link completo:</p>
                <p className="font-mono text-sm break-all text-blue-800">
                  {window.location.origin}/seguimiento?codigo={linkSeguimiento.token}
                </p>
              </div>
              <div className="flex gap-2">
                <Button onClick={copyLinkToClipboard} className="flex-1">
                  <Copy className="w-4 h-4 mr-2" />
                  Copiar Link
                </Button>
                <Button variant="outline" onClick={() => window.open(`/seguimiento?codigo=${linkSeguimiento.token}`, '_blank')}>
                  <ExternalLink className="w-4 h-4 mr-2" />
                  Abrir
                </Button>
              </div>
              <Separator />
              <div className="space-y-2">
                <p className="text-sm font-medium">Enviar notificación al cliente</p>
                <Button onClick={handleEnviarNotificacion} disabled={enviandoNotificacion} className="w-full bg-blue-600 hover:bg-blue-700" data-testid="send-notification-btn">
                  <Send className="w-4 h-4 mr-2" />
                  {enviandoNotificacion ? 'Enviando...' : 'Enviar SMS y Email'}
                </Button>
                <p className="text-xs text-muted-foreground text-center">
                  Se enviará el link de seguimiento por SMS ({linkSeguimiento.telefono_hint}) y Email
                </p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialog Editar Cliente */}
      <Dialog open={showEditCliente} onOpenChange={setShowEditCliente}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <User className="w-5 h-5" />
              Editar Datos del Cliente
            </DialogTitle>
          </DialogHeader>
          {editClienteData && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="edit-nombre">Nombre</Label>
                  <Input id="edit-nombre" value={editClienteData.nombre || ''} onChange={(e) => setEditClienteData({...editClienteData, nombre: e.target.value})} />
                </div>
                <div>
                  <Label htmlFor="edit-apellidos">Apellidos</Label>
                  <Input id="edit-apellidos" value={editClienteData.apellidos || ''} onChange={(e) => setEditClienteData({...editClienteData, apellidos: e.target.value})} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="edit-dni">DNI</Label>
                  <Input id="edit-dni" value={editClienteData.dni || ''} onChange={(e) => setEditClienteData({...editClienteData, dni: e.target.value})} />
                </div>
                <div>
                  <Label htmlFor="edit-telefono">Teléfono</Label>
                  <Input id="edit-telefono" value={editClienteData.telefono || ''} onChange={(e) => setEditClienteData({...editClienteData, telefono: e.target.value})} />
                </div>
              </div>
              <div>
                <Label htmlFor="edit-email">Email</Label>
                <Input id="edit-email" type="email" value={editClienteData.email || ''} onChange={(e) => setEditClienteData({...editClienteData, email: e.target.value})} />
              </div>
              <div>
                <Label htmlFor="edit-direccion">Dirección</Label>
                <Input id="edit-direccion" value={editClienteData.direccion || ''} onChange={(e) => setEditClienteData({...editClienteData, direccion: e.target.value})} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="edit-planta">Planta</Label>
                  <Input id="edit-planta" value={editClienteData.planta || ''} onChange={(e) => setEditClienteData({...editClienteData, planta: e.target.value})} />
                </div>
                <div>
                  <Label htmlFor="edit-puerta">Puerta</Label>
                  <Input id="edit-puerta" value={editClienteData.puerta || ''} onChange={(e) => setEditClienteData({...editClienteData, puerta: e.target.value})} />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-4">
                <Button variant="outline" onClick={() => setShowEditCliente(false)}>Cancelar</Button>
                <Button onClick={handleGuardarCliente} disabled={guardandoCliente}>
                  {guardandoCliente ? 'Guardando...' : 'Guardar Cambios'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialog Nuevo Repuesto */}
      <Dialog open={showNuevoRepuesto} onOpenChange={setShowNuevoRepuesto}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="w-5 h-5" />
              Crear Nuevo Repuesto
            </DialogTitle>
            <DialogDescription>El repuesto se creará y añadirá automáticamente a esta orden.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="nuevo-nombre">Nombre del Repuesto *</Label>
              <Input id="nuevo-nombre" placeholder="Ej: Pantalla iPhone 14 Pro" value={nuevoRepuestoData.nombre}
                onChange={(e) => setNuevoRepuestoData({...nuevoRepuestoData, nombre: e.target.value})} />
            </div>
            <div>
              <Label htmlFor="nuevo-descripcion">Descripción</Label>
              <Input id="nuevo-descripcion" placeholder="Descripción opcional" value={nuevoRepuestoData.descripcion}
                onChange={(e) => setNuevoRepuestoData({...nuevoRepuestoData, descripcion: e.target.value})} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="nuevo-precio-compra">Precio Compra (€)</Label>
                <Input id="nuevo-precio-compra" type="number" step="0.01" placeholder="0.00" value={nuevoRepuestoData.precio_compra}
                  onChange={(e) => setNuevoRepuestoData({...nuevoRepuestoData, precio_compra: e.target.value})} />
              </div>
              <div>
                <Label htmlFor="nuevo-precio-venta">Precio Venta (€) *</Label>
                <Input id="nuevo-precio-venta" type="number" step="0.01" placeholder="0.00" value={nuevoRepuestoData.precio_venta}
                  onChange={(e) => setNuevoRepuestoData({...nuevoRepuestoData, precio_venta: e.target.value})} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="nuevo-stock">Stock Inicial</Label>
                <Input id="nuevo-stock" type="number" value={nuevoRepuestoData.stock}
                  onChange={(e) => setNuevoRepuestoData({...nuevoRepuestoData, stock: e.target.value})} />
              </div>
              <div>
                <Label htmlFor="nuevo-stock-minimo">Stock Mínimo</Label>
                <Input id="nuevo-stock-minimo" type="number" value={nuevoRepuestoData.stock_minimo}
                  onChange={(e) => setNuevoRepuestoData({...nuevoRepuestoData, stock_minimo: e.target.value})} />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => setShowNuevoRepuesto(false)}>Cancelar</Button>
              <Button onClick={handleCrearRepuesto} disabled={guardandoRepuesto}>
                {guardandoRepuesto ? 'Creando...' : 'Crear y Añadir'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Dialog Añadir Material con Precios */}
      <Dialog open={showAddMaterialDialog} onOpenChange={setShowAddMaterialDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{materialSeleccionado ? `Añadir: ${materialSeleccionado.nombre}` : 'Añadir Material Personalizado'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {!materialSeleccionado && (
              <div>
                <Label>Nombre del Material *</Label>
                <Input value={nuevoMaterialData.nombre} onChange={(e) => setNuevoMaterialData(prev => ({ ...prev, nombre: e.target.value }))}
                  placeholder="Ej: Pantalla LCD iPhone 12" />
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Cantidad *</Label>
                <Input type="number" min="1" value={nuevoMaterialData.cantidad}
                  onChange={(e) => setNuevoMaterialData(prev => ({ ...prev, cantidad: e.target.value }))} />
              </div>
              <div>
                <Label>IVA (%)</Label>
                <Input type="number" value={nuevoMaterialData.iva}
                  onChange={(e) => setNuevoMaterialData(prev => ({ ...prev, iva: e.target.value }))} />
              </div>
              <div>
                <Label>Coste (€)</Label>
                <Input type="number" step="0.01" value={nuevoMaterialData.coste}
                  onChange={(e) => setNuevoMaterialData(prev => ({ ...prev, coste: e.target.value }))} placeholder="0.00" />
              </div>
              <div>
                <Label>Precio Venta (€) *</Label>
                <Input type="number" step="0.01" value={nuevoMaterialData.precio_unitario}
                  onChange={(e) => setNuevoMaterialData(prev => ({ ...prev, precio_unitario: e.target.value }))} placeholder="0.00" />
              </div>
            </div>
            <div className="p-3 bg-slate-100 rounded-lg">
              <div className="flex justify-between text-sm">
                <span>Subtotal:</span>
                <span>€{((parseFloat(nuevoMaterialData.cantidad) || 0) * (parseFloat(nuevoMaterialData.precio_unitario) || 0)).toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm text-muted-foreground">
                <span>IVA ({nuevoMaterialData.iva}%):</span>
                <span>€{(((parseFloat(nuevoMaterialData.cantidad) || 0) * (parseFloat(nuevoMaterialData.precio_unitario) || 0)) * ((parseFloat(nuevoMaterialData.iva) || 0) / 100)).toFixed(2)}</span>
              </div>
              <Separator className="my-2" />
              <div className="flex justify-between font-semibold">
                <span>Total:</span>
                <span>€{(((parseFloat(nuevoMaterialData.cantidad) || 0) * (parseFloat(nuevoMaterialData.precio_unitario) || 0)) * (1 + ((parseFloat(nuevoMaterialData.iva) || 0) / 100))).toFixed(2)}</span>
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setShowAddMaterialDialog(false)}>Cancelar</Button>
            <Button onClick={handleConfirmAddMaterial} disabled={guardandoMaterial || (!materialSeleccionado && !nuevoMaterialData.nombre)}>
              {guardandoMaterial ? 'Añadiendo...' : 'Añadir Material'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Dialog Editar Precios de Material */}
      <Dialog open={showEditMaterialDialog} onOpenChange={setShowEditMaterialDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Precios del Material</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Coste (€)</Label>
                <Input type="number" step="0.01" value={editMaterialData.coste}
                  onChange={(e) => setEditMaterialData(prev => ({ ...prev, coste: e.target.value }))} placeholder="0.00" />
              </div>
              <div>
                <Label>Precio Venta (€)</Label>
                <Input type="number" step="0.01" value={editMaterialData.precio_unitario}
                  onChange={(e) => setEditMaterialData(prev => ({ ...prev, precio_unitario: e.target.value }))} placeholder="0.00" />
              </div>
              <div className="col-span-2">
                <Label>IVA (%)</Label>
                <Input type="number" value={editMaterialData.iva}
                  onChange={(e) => setEditMaterialData(prev => ({ ...prev, iva: e.target.value }))} />
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setShowEditMaterialDialog(false)}>Cancelar</Button>
            <Button onClick={handleConfirmEditMaterial} disabled={guardandoMaterial}>
              {guardandoMaterial ? 'Guardando...' : 'Guardar Precios'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Modal Solicitar Reemplazo (Técnico) */}
      <Dialog open={showSolicitarReemplazo} onOpenChange={setShowSolicitarReemplazo}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="w-5 h-5" />
              Dispositivo NO Reparable
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              <p className="font-medium">⚠️ Atención:</p>
              <p>Al solicitar reemplazo, estás indicando que el dispositivo NO se puede reparar y se debe enviar un dispositivo NUEVO al cliente.</p>
              <p className="mt-2">La orden quedará <strong>BLOQUEADA</strong> hasta que administración autorice el reemplazo.</p>
            </div>
            <div className="space-y-2">
              <Label>Motivo del reemplazo *</Label>
              <Textarea placeholder="Explica por qué el dispositivo no es reparable..." value={reemplazoData.motivo}
                onChange={(e) => setReemplazoData(prev => ({ ...prev, motivo: e.target.value }))} rows={3} data-testid="reemplazo-motivo" />
            </div>
            <div className="space-y-2">
              <Label>Diagnóstico final (opcional)</Label>
              <Textarea placeholder="Describe el diagnóstico técnico final..." value={reemplazoData.diagnostico_final}
                onChange={(e) => setReemplazoData(prev => ({ ...prev, diagnostico_final: e.target.value }))} rows={2} data-testid="reemplazo-diagnostico" />
            </div>
            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => setShowSolicitarReemplazo(false)}>Cancelar</Button>
              <Button onClick={handleSolicitarReemplazo} disabled={solicitandoReemplazo || !reemplazoData.motivo.trim()}
                variant="destructive" data-testid="btn-confirmar-reemplazo">
                {solicitandoReemplazo ? 'Enviando...' : 'Confirmar Reemplazo'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Modal Autorizar Reemplazo (Admin) */}
      <Dialog open={showAutorizarReemplazo} onOpenChange={setShowAutorizarReemplazo}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-green-600">
              <CheckCircle2 className="w-5 h-5" />
              Autorizar Reemplazo de Dispositivo
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700">
              <p>Al autorizar, los materiales de reparación serán <strong>ELIMINADOS</strong> y solo se registrará el valor del nuevo dispositivo.</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Modelo del nuevo dispositivo *</Label>
                <Input placeholder="Ej: iPhone 14 Pro" value={autorizarReemplazoData.nuevo_modelo}
                  onChange={(e) => setAutorizarReemplazoData(prev => ({ ...prev, nuevo_modelo: e.target.value }))} data-testid="nuevo-modelo" />
              </div>
              <div className="space-y-2">
                <Label>Color</Label>
                <Input placeholder="Ej: Negro" value={autorizarReemplazoData.nuevo_color}
                  onChange={(e) => setAutorizarReemplazoData(prev => ({ ...prev, nuevo_color: e.target.value }))} data-testid="nuevo-color" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>IMEI del nuevo dispositivo *</Label>
                <Input placeholder="Ej: 353456789012345" value={autorizarReemplazoData.nuevo_imei}
                  onChange={(e) => setAutorizarReemplazoData(prev => ({ ...prev, nuevo_imei: e.target.value }))}
                  className="font-mono" data-testid="nuevo-imei" />
              </div>
              <div className="space-y-2">
                <Label>Valor del dispositivo (€) *</Label>
                <Input type="number" step="0.01" placeholder="0.00" value={autorizarReemplazoData.valor_dispositivo}
                  onChange={(e) => setAutorizarReemplazoData(prev => ({ ...prev, valor_dispositivo: e.target.value }))} data-testid="valor-dispositivo" />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Notas adicionales</Label>
              <Textarea placeholder="Notas sobre el reemplazo..." value={autorizarReemplazoData.notas}
                onChange={(e) => setAutorizarReemplazoData(prev => ({ ...prev, notas: e.target.value }))} rows={2} />
            </div>
            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => setShowAutorizarReemplazo(false)}>Cancelar</Button>
              <Button onClick={handleAutorizarReemplazo}
                disabled={autorizandoReemplazo || !autorizarReemplazoData.nuevo_modelo || !autorizarReemplazoData.nuevo_imei || !autorizarReemplazoData.valor_dispositivo}
                className="bg-green-600 hover:bg-green-700" data-testid="btn-autorizar-reemplazo">
                {autorizandoReemplazo ? 'Autorizando...' : 'Autorizar Reemplazo'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Modal Generar Recogida */}
      <GenerarEnvioModal
        open={showGenerarRecogida}
        onOpenChange={setShowGenerarRecogida}
        tipo="recogida"
        cliente={cliente}
        orden={orden}
        onConfirm={handleGenerarRecogida}
        loading={generandoLogistica}
      />

      {/* Modal Generar Envío */}
      <GenerarEnvioModal
        open={showGenerarEnvio}
        onOpenChange={setShowGenerarEnvio}
        tipo="envio"
        cliente={cliente}
        orden={orden}
        onConfirm={handleGenerarEnvio}
        loading={generandoLogistica}
      />

      {/* Popup Validación - Aparece automáticamente cuando la orden está en validación */}
      <Dialog open={showValidacionPopup} onOpenChange={setShowValidacionPopup}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-green-700">
              <CheckCircle2 className="w-6 h-6" />
              Orden lista para envío
            </DialogTitle>
            <DialogDescription>
              Esta orden está en validación. Descarga los documentos necesarios y finaliza el proceso.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Info de la orden */}
            <div className="bg-slate-50 rounded-lg p-4 space-y-2">
              <p className="text-sm"><strong>Orden:</strong> {orden?.numero_orden || orden?.numero_autorizacion}</p>
              <p className="text-sm"><strong>Cliente:</strong> {cliente?.nombre} {cliente?.apellidos}</p>
              <p className="text-sm"><strong>Dispositivo:</strong> {orden?.dispositivo?.marca} {orden?.dispositivo?.modelo}</p>
              <p className="text-sm"><strong>Importe:</strong> {orden?.presupuesto_total?.toFixed(2) || 0}€</p>
            </div>

            {/* Botones de descarga */}
            <div className="grid grid-cols-2 gap-3">
              <Button 
                variant="outline" 
                className="h-20 flex flex-col items-center justify-center gap-2 border-2 border-blue-200 hover:border-blue-400 hover:bg-blue-50"
                onClick={handleDescargarFotos}
              >
                <FileImage className="w-8 h-8 text-blue-600" />
                <span className="text-sm font-medium">Descargar Fotos (ZIP)</span>
              </Button>
              
              <Button 
                variant="outline" 
                className="h-20 flex flex-col items-center justify-center gap-2 border-2 border-purple-200 hover:border-purple-400 hover:bg-purple-50"
                onClick={handlePrint}
              >
                <FileText className="w-8 h-8 text-purple-600" />
                <span className="text-sm font-medium">Descargar Orden (PDF)</span>
              </Button>
            </div>

            {/* Separador */}
            <Separator />

            {/* Botón continuar a finalización */}
            <Button 
              className="w-full h-12 bg-green-600 hover:bg-green-700"
              onClick={() => { setShowValidacionPopup(false); setShowFinalizarOrden(true); }}
            >
              <Truck className="w-5 h-5 mr-2" />
              Continuar con Envío y Cierre
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Popup Finalizar Orden - Código de envío y cierre */}
      <Dialog open={showFinalizarOrden} onOpenChange={setShowFinalizarOrden}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Send className="w-5 h-5 text-blue-600" />
              Finalizar y Enviar Orden
            </DialogTitle>
            <DialogDescription>
              Introduce el código de seguimiento para marcar como enviada y cerrar la orden.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="codigoEnvioFinal">Código de envío / Tracking</Label>
              <Input
                id="codigoEnvioFinal"
                placeholder="Ej: MRW123456789, SEUR000123..."
                value={codigoEnvioFinal}
                onChange={(e) => setCodigoEnvioFinal(e.target.value)}
                autoFocus
              />
            </div>

            {orden?.tipo_servicio === 'seguro' || orden?.origen === 'insurama' ? (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm">
                <p className="font-medium text-amber-800 flex items-center gap-2">
                  <DollarSign className="w-4 h-4" />
                  Orden de seguro
                </p>
                <p className="text-amber-700 mt-1">
                  Se registrará automáticamente en liquidaciones pendientes de cobro.
                </p>
              </div>
            ) : null}

            <div className="flex gap-2 pt-2">
              <Button variant="outline" onClick={() => setShowFinalizarOrden(false)} className="flex-1">
                Cancelar
              </Button>
              <Button 
                onClick={handleFinalizarOrden} 
                disabled={finalizando || !codigoEnvioFinal.trim()}
                className="flex-1 bg-green-600 hover:bg-green-700"
              >
                {finalizando ? 'Finalizando...' : 'Finalizar Orden'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Hidden PDF for printing */}
      <div className="hidden">
        <OrdenPDF
          ref={pdfRefFull}
          orden={orden}
          cliente={cliente}
          materiales={orden?.materiales || []}
          mode="full"
          modoB2B={(cliente?.tipo_cliente || '').toLowerCase() === 'empresa'}
          includeFotos={true}
        />
        <OrdenPDF
          ref={pdfRefNoPrices}
          orden={orden}
          cliente={cliente}
          materiales={orden?.materiales || []}
          mode="no_prices"
          modoB2B={(cliente?.tipo_cliente || '').toLowerCase() === 'empresa'}
        />
        <OrdenPDF
          ref={pdfRefBlank}
          orden={orden}
          cliente={cliente}
          materiales={orden?.materiales || []}
          mode="blank_no_prices"
          modoB2B={(cliente?.tipo_cliente || '').toLowerCase() === 'empresa'}
        />
      </div>
    </div>
  );
}

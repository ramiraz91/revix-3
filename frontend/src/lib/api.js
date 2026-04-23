import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Separate instance for slow Insurama/Sumbroker calls
const API_SLOW = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  timeout: 200000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
API.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Add token to slow API requests
API_SLOW.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors (except for login endpoint)
const handle401 = (error) => {
  const isLoginEndpoint = error.config?.url?.includes('/auth/login');
  if (error.response?.status === 401 && !isLoginEndpoint) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
  }
  return Promise.reject(error);
};

API.interceptors.response.use((response) => response, handle401);
API_SLOW.interceptors.response.use((response) => response, handle401);

// ==================== AUTH ====================
export const authAPI = {
  login: (data) => API.post('/auth/login', data),  // data: { email, password }
  register: (data) => API.post('/auth/register', data),
  me: () => API.get('/auth/me'),
  users: () => API.get('/auth/users'),
  // Recuperación de contraseña
  recuperarPassword: (email) => API.post('/auth/recuperar-password', { email }),
  resetPassword: (token, nueva_password) => API.post('/auth/reset-password', { token, nueva_password }),
  verificarTokenReset: (token) => API.get(`/auth/verificar-token-reset?token=${token}`),
};

// ==================== USUARIOS (GESTIÓN COMPLETA) ====================
export const usuariosAPI = {
  listar: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.role) queryParams.append('role', params.role);
    if (params.activo !== undefined) queryParams.append('activo', params.activo);
    if (params.search) queryParams.append('search', params.search);
    const query = queryParams.toString();
    return API.get(`/usuarios${query ? `?${query}` : ''}`);
  },
  obtener: (id) => API.get(`/usuarios/${id}`),
  crear: (data) => API.post('/usuarios', data),
  actualizar: (id, data) => API.put(`/usuarios/${id}`, data),
  eliminar: (id) => API.delete(`/usuarios/${id}`),
  toggleActivo: (id) => API.patch(`/usuarios/${id}/toggle-activo`),
  cambiarPassword: (id, nuevaPassword) => API.patch(`/usuarios/${id}/cambiar-password`, { nueva_password: nuevaPassword }),
  enviarResetPassword: (id) => API.post(`/usuarios/${id}/enviar-reset-password`),
};

// ==================== CALENDARIO ====================
export const calendarioAPI = {
  listarEventos: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.fecha_desde) queryParams.append('fecha_desde', params.fecha_desde);
    if (params.fecha_hasta) queryParams.append('fecha_hasta', params.fecha_hasta);
    if (params.usuario_id) queryParams.append('usuario_id', params.usuario_id);
    if (params.tipo) queryParams.append('tipo', params.tipo);
    const query = queryParams.toString();
    return API.get(`/calendario/eventos${query ? `?${query}` : ''}`);
  },
  crearEvento: (data) => API.post('/calendario/eventos', data),
  actualizarEvento: (id, data) => API.put(`/calendario/eventos/${id}`, data),
  eliminarEvento: (id) => API.delete(`/calendario/eventos/${id}`),
  asignarOrden: (ordenId, tecnicoId, fechaEstimada) => 
    API.post('/calendario/asignar-orden', {
      orden_id: ordenId,
      tecnico_id: tecnicoId,
      fecha_estimada: fechaEstimada
    }),
  disponibilidadTecnicos: (fecha) => API.get(`/tecnicos/disponibilidad?fecha=${fecha}`),
};

// ==================== PROVEEDORES ====================
export const proveedoresAPI = {
  listar: (search = '') => API.get(`/proveedores${search ? `?search=${search}` : ''}`),
  obtener: (id) => API.get(`/proveedores/${id}`),
  crear: (data) => API.post('/proveedores', data),
  actualizar: (id, data) => API.put(`/proveedores/${id}`, data),
  eliminar: (id) => API.delete(`/proveedores/${id}`),
};

// ==================== INVENTARIO/REPUESTOS ====================
export const repuestosAPI = {
  listar: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.search) queryParams.append('search', params.search);
    if (params.categoria) queryParams.append('categoria', params.categoria);
    if (params.proveedor) queryParams.append('proveedor', params.proveedor);
    if (params.low_stock) queryParams.append('low_stock', 'true');
    if (params.page) queryParams.append('page', params.page);
    if (params.page_size) queryParams.append('page_size', params.page_size);
    const query = queryParams.toString();
    return API.get(`/repuestos${query ? `?${query}` : ''}`);
  },
  // Búsqueda rápida optimizada para autocompletado (devuelve array directo)
  buscarRapido: (q, proveedor = null, limit = 20) => {
    const queryParams = new URLSearchParams();
    queryParams.append('q', q);
    if (proveedor) queryParams.append('proveedor', proveedor);
    queryParams.append('limit', limit);
    return API.get(`/repuestos/buscar/rapido?${queryParams.toString()}`);
  },
  obtener: (id) => API.get(`/repuestos/${id}`),
  crear: (data) => API.post('/repuestos', data),
  actualizar: (id, data) => API.put(`/repuestos/${id}`, data),
  eliminar: (id) => API.delete(`/repuestos/${id}`),
  actualizarStock: (id, cantidad, operacion = 'set') => 
    API.patch(`/repuestos/${id}/stock?cantidad=${cantidad}&operacion=${operacion}`),
  categorias: () => API.get('/repuestos/categorias'),
  buscarSku: (sku) => API.get(`/repuestos/buscar-sku/${sku}`),
  // Calidades de pantalla
  calidadesPantalla: () => API.get('/repuestos/calidades-pantalla'),
  alternativas: (id, limit = 10) => API.get(`/repuestos/${id}/alternativas?limit=${limit}`),
  actualizarCalidadPantalla: (id, calidad) => API.patch(`/repuestos/${id}/calidad-pantalla?calidad=${calidad}`),
  clasificarPantallas: () => API.post('/repuestos/clasificar-pantallas'),
};

// ==================== ÓRDENES ====================
export const ordenesAPI = {
  // Endpoint optimizado con paginación (recomendado para listados)
  listarPaginado: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.estado) queryParams.append('estado', params.estado);
    if (params.cliente_id) queryParams.append('cliente_id', params.cliente_id);
    if (params.search) queryParams.append('search', params.search);
    if (params.telefono) queryParams.append('telefono', params.telefono);
    if (params.autorizacion) queryParams.append('autorizacion', params.autorizacion);
    if (params.fecha_desde) queryParams.append('fecha_desde', params.fecha_desde);
    if (params.fecha_hasta) queryParams.append('fecha_hasta', params.fecha_hasta);
    if (params.solo_garantias) queryParams.append('solo_garantias', 'true');
    queryParams.append('page', params.page || 1);
    queryParams.append('page_size', params.page_size || 50);
    return API.get(`/ordenes/v2?${queryParams.toString()}`);
  },
  // Endpoint original (compatibilidad - evitar en listados grandes)
  listar: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.estado) queryParams.append('estado', params.estado);
    if (params.cliente_id) queryParams.append('cliente_id', params.cliente_id);
    if (params.search) queryParams.append('search', params.search);
    if (params.telefono) queryParams.append('telefono', params.telefono);
    if (params.autorizacion) queryParams.append('autorizacion', params.autorizacion);
    if (params.fecha_desde) queryParams.append('fecha_desde', params.fecha_desde);
    if (params.fecha_hasta) queryParams.append('fecha_hasta', params.fecha_hasta);
    if (params.solo_garantias) queryParams.append('solo_garantias', 'true');
    const query = queryParams.toString();
    return API.get(`/ordenes${query ? `?${query}` : ''}`);
  },
  obtener: (id) => API.get(`/ordenes/${id}`),
  crear: (data) => API.post('/ordenes', data),
  actualizar: (id, data) => API.patch(`/ordenes/${id}`, data),
  actualizarEnvio: (id, data) => API.patch(`/ordenes/${id}/envio`, data),
  eliminar: (id) => API.delete(`/ordenes/${id}`),
  cambiarEstado: (id, data) => API.patch(`/ordenes/${id}/estado`, data),
  registrarReceivingInspection: (id, data) => API.post(`/ordenes/${id}/receiving-inspection`, data),
  registrarCPI: (id, data) => API.patch(`/ordenes/${id}/cpi`, data),
  registrarImpresion: (id, data) => API.post(`/ordenes/${id}/registro-impresion`, data),
  obtenerEventosAuditoria: (id) => API.get(`/ordenes/${id}/eventos-auditoria`),
  escanear: (id, data) => API.post(`/ordenes/${id}/scan`, data),
  buscarPorCodigo: (q) => API.get(`/ordenes/buscar?q=${encodeURIComponent(q)}`),
  añadirMaterial: (id, data) => API.post(`/ordenes/${id}/materiales`, data),
  actualizarMaterial: (id, index, data) => API.patch(`/ordenes/${id}/materiales/${index}`, data),
  editarMaterialCompleto: (id, index, data) => API.put(`/ordenes/${id}/materiales/${index}`, data),
  eliminarMaterial: (id, index) => API.delete(`/ordenes/${id}/materiales/${index}`),
  validarMaterial: (id, index) => API.post(`/ordenes/${id}/materiales/${index}/validar`),
  validarMaterialPorCodigo: (id, codigo) => API.post(`/ordenes/${id}/materiales/validar-por-codigo`, { codigo }),
  aprobarMateriales: (id) => API.post(`/ordenes/${id}/aprobar-materiales`),
  // Evidencias admin
  subirEvidencia: (id, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return API.post(`/ordenes/${id}/evidencias`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  // Evidencias técnico
  subirEvidenciaTecnico: (id, file, tipoFoto = 'general') => {
    const formData = new FormData();
    formData.append('file', file);
    return API.post(`/ordenes/${id}/evidencias-tecnico?tipo_foto=${tipoFoto}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  // Fotos específicas (antes/después)
  subirFotoAntes: (id, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return API.post(`/ordenes/${id}/evidencias-tecnico?tipo_foto=antes`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  subirFotoDespues: (id, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return API.post(`/ordenes/${id}/evidencias-tecnico?tipo_foto=despues`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  // Mensajes/Comunicaciones
  obtenerMensajes: (id) => API.get(`/ordenes/${id}/mensajes`),
  añadirMensaje: (id, data) => API.post(`/ordenes/${id}/mensajes`, data),
  // Métricas de tiempo
  obtenerMetricas: (id) => API.get(`/ordenes/${id}/metricas`),
  // Notificaciones
  enviarWhatsApp: (id) => API.post(`/ordenes/${id}/enviar-whatsapp`),
  enviarNotificacion: (id) => API.post(`/ordenes/${id}/enviar-notificacion`),
  // Garantías
  crearGarantia: (id) => API.post(`/ordenes/${id}/crear-garantia`),
  obtenerGarantias: (id) => API.get(`/ordenes/${id}/garantias`),
  activarGarantia: (id, meses = 3) => API.patch(`/ordenes/${id}/activar-garantia?meses=${meses}`),
  // Diagnóstico técnico
  guardarDiagnostico: (id, diagnostico) => API.post(`/ordenes/${id}/diagnostico`, { diagnostico }),
  // Descargar fotos en ZIP
  descargarFotosZip: (id) => `${API.defaults.baseURL}/ordenes/${id}/fotos-zip`,
  // Reemplazo de dispositivo
  solicitarReemplazo: (id, data) => API.post(`/ordenes/${id}/solicitar-reemplazo`, data),
  autorizarReemplazo: (id, data) => API.post(`/ordenes/${id}/autorizar-reemplazo`, data),
  rechazarReemplazo: (id, motivo) => API.post(`/ordenes/${id}/rechazar-reemplazo?motivo=${encodeURIComponent(motivo || '')}`),
  // Subestados
  obtenerSubestado: (id) => API.get(`/ordenes/${id}/subestado`),
  cambiarSubestado: (id, data) => API.patch(`/ordenes/${id}/subestado`, data),
  // Liquidación
  registrarLiquidacion: (id, data) => API.post(`/ordenes/${id}/registrar-liquidacion`, data),
  // Mano de obra y totales
  actualizarManoObra: (id, valor) => API.patch(`/ordenes/${id}/mano-obra`, { mano_obra: valor }),
  recalcularTotales: (id) => API.post(`/ordenes/${id}/recalcular-totales`),
  // Re-presupuesto
  rePresupuesto: (id, data) => API.post(`/ordenes/${id}/re-presupuesto`, data),
  aprobarRePresupuesto: (id) => API.post(`/ordenes/${id}/aprobar-re-presupuesto`),
};

// ==================== ÓRDENES DE COMPRA ====================
export const ordenesCompraAPI = {
  listar: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.estado) queryParams.append('estado', params.estado);
    if (params.prioridad) queryParams.append('prioridad', params.prioridad);
    if (params.numero_pedido) queryParams.append('numero_pedido', params.numero_pedido);
    const query = queryParams.toString();
    return API.get(`/ordenes-compra${query ? `?${query}` : ''}`);
  },
  obtener: (id) => API.get(`/ordenes-compra/${id}`),
  crear: (data) => API.post('/ordenes-compra', data),
  actualizar: (id, data) => API.patch(`/ordenes-compra/${id}`, data),
  buscarPorPedido: (numeroPedido) => API.get(`/ordenes-compra/buscar-pedido/${encodeURIComponent(numeroPedido)}`),
};

// ==================== CLIENTES (extendido) ====================
export const clientesAPI = {
  listar: (search = '') => API.get(`/clientes${search ? `?search=${search}` : ''}`),
  obtener: (id) => API.get(`/clientes/${id}`),
  crear: (data) => API.post('/clientes', data),
  actualizar: (id, data) => API.put(`/clientes/${id}`, data),
  eliminar: (id) => API.delete(`/clientes/${id}`),
  historial: (id) => API.get(`/clientes/${id}/historial`),
};

// ==================== NOTIFICACIONES ====================
export const notificacionesAPI = {
  listar: (no_leidas = false, categoria = null) => {
    const qs = new URLSearchParams();
    if (no_leidas) qs.set('no_leidas', 'true');
    if (categoria) qs.set('categoria', categoria);
    const s = qs.toString();
    return API.get(`/notificaciones${s ? `?${s}` : ''}`);
  },
  contadores: () => API.get('/notificaciones/contadores'),
  marcarLeida: (id) => API.patch(`/notificaciones/${id}/leer`),
  marcarLeidasPorOrden: (ordenId) => API.patch(`/notificaciones/marcar-leidas-orden/${ordenId}`),
  marcarTodasLeidas: () => API.post('/notificaciones/marcar-todas-leidas'),
  eliminar: (id) => API.delete(`/notificaciones/${id}`),
  eliminarMasivo: (ids) => API.post('/notificaciones/eliminar-masivo', { ids }),
  marcarLeidasMasivo: (ids) => API.post('/notificaciones/marcar-leidas-masivo', { ids }),
};

// ==================== DASHBOARD ====================
export const dashboardAPI = {
  stats: () => API.get('/dashboard/stats'),
  metricasAvanzadas: () => API.get('/dashboard/metricas-avanzadas'),
  alertasStock: () => API.get('/dashboard/alertas-stock'),
  ordenesCompraUrgentes: () => API.get('/dashboard/ordenes-compra-urgentes'),
};

// ==================== INCIDENCIAS ====================
export const incidenciasAPI = {
  listar: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.cliente_id) queryParams.append('cliente_id', params.cliente_id);
    if (params.estado) queryParams.append('estado', params.estado);
    if (params.tipo) queryParams.append('tipo', params.tipo);
    const query = queryParams.toString();
    return API.get(`/incidencias${query ? `?${query}` : ''}`);
  },
  obtener: (id) => API.get(`/incidencias/${id}`),
  crear: (data) => API.post('/incidencias', data),
  actualizar: (id, data) => API.put(`/incidencias/${id}`, data),
  porCliente: (clienteId) => API.get(`/clientes/${clienteId}/incidencias`),
};

// ==================== EXPORTAR/IMPORTAR ====================
export const exportarAPI = {
  clientes: () => API.get('/exportar/clientes'),
  ordenes: () => API.get('/exportar/ordenes'),
  inventario: () => API.get('/exportar/inventario'),
};

export const importarAPI = {
  clientes: (data) => API.post('/importar/clientes', data),
  inventario: (data) => API.post('/importar/inventario', data),
};

// ==================== SEGUIMIENTO CLIENTE (PÚBLICO) ====================
export const seguimientoAPI = {
  verificar: (token, telefono, consentimientos = {}) => API.post('/seguimiento/verificar', { token, telefono, ...consentimientos }),
  obtenerLink: (ordenId) => API.get(`/ordenes/${ordenId}/link-seguimiento`),
  restablecerToken: (ordenId) => API.post(`/ordenes/${ordenId}/restablecer-seguimiento`),
  recuperar: (data) => API.post('/seguimiento/recuperar', data),
};

// ==================== CONFIGURACIÓN EMPRESA ====================
export const empresaAPI = {
  obtener: () => API.get('/configuracion/empresa'),
  guardar: (data) => API.post('/configuracion/empresa', data),
  obtenerPublica: () => API.get('/configuracion/empresa/publica'),
  subirLogo: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return API.post('/configuracion/empresa/logo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// ==================== MASTER (métricas avanzadas) ====================
export const masterAPI = {
  metricasTecnicos: () => API.get('/master/metricas-tecnicos'),
  facturacion: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.fecha_desde) queryParams.append('fecha_desde', params.fecha_desde);
    if (params.fecha_hasta) queryParams.append('fecha_hasta', params.fecha_hasta);
    const query = queryParams.toString();
    return API.get(`/master/facturacion${query ? `?${query}` : ''}`);
  },
  isoKpis: () => API.get('/master/iso/kpis'),
  isoDocumentos: () => API.get('/master/iso/documentos'),
  guardarIsoDocumento: (data) => API.post('/master/iso/documentos', data),
  isoProveedores: () => API.get('/master/iso/proveedores'),
  evaluarIsoProveedor: (data) => API.post('/master/iso/proveedores/evaluar', data),
  exportarIsoReportePdf: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.orden_id) queryParams.append('orden_id', params.orden_id);
    if (params.fecha_desde) queryParams.append('fecha_desde', params.fecha_desde);
    if (params.fecha_hasta) queryParams.append('fecha_hasta', params.fecha_hasta);
    const query = queryParams.toString();
    return `${API.defaults.baseURL}/master/iso/reporte-pdf${query ? `?${query}` : ''}`;
  },
  auditPackOt: (ordenId) => API.get(`/master/iso/audit-pack/ot/${ordenId}`),
  auditPackPeriodo: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.fecha_desde) queryParams.append('fecha_desde', params.fecha_desde);
    if (params.fecha_hasta) queryParams.append('fecha_hasta', params.fecha_hasta);
    const query = queryParams.toString();
    return API.get(`/master/iso/audit-pack/periodo${query ? `?${query}` : ''}`);
  },
  exportarAuditPackCsv: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.fecha_desde) queryParams.append('fecha_desde', params.fecha_desde);
    if (params.fecha_hasta) queryParams.append('fecha_hasta', params.fecha_hasta);
    const query = queryParams.toString();
    return `${API.defaults.baseURL}/master/iso/audit-pack/periodo/csv${query ? `?${query}` : ''}`;
  },
  qaConfig: () => API.get('/master/iso/qa-config'),
  guardarQaConfig: (data) => API.post('/master/iso/qa-config', data),
  ejecutarQaMuestreo: () => API.post('/master/iso/qa-muestreo/ejecutar', {}),
  registrarResultadoQa: (muestreoId, data) => API.post(`/master/iso/qa-muestreo/${muestreoId}/resultado`, data),
  capaDashboard: () => API.get('/master/iso/capa-dashboard'),
};

// ==================== DISPOSITIVOS DE RESTOS ====================
export const restosAPI = {
  listar: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.search) queryParams.append('search', params.search);
    if (params.activo !== undefined) queryParams.append('activo', params.activo);
    if (params.estado) queryParams.append('estado', params.estado);
    if (params.tipo) queryParams.append('tipo', params.tipo);
    const query = queryParams.toString();
    return API.get(`/restos${query ? `?${query}` : ''}`);
  },
  obtener: (id) => API.get(`/restos/${id}`),
  crear: (data) => API.post('/restos', data),
  actualizar: (id, data) => API.put(`/restos/${id}`, data),
  usarPieza: (id, pieza, ordenId) => 
    API.patch(`/restos/${id}/usar-pieza?pieza=${encodeURIComponent(pieza)}&orden_id=${ordenId}`),
  eliminar: (id) => API.delete(`/restos/${id}`),
  // Nuevos endpoints para despiece
  añadirPieza: (restoId, pieza) => API.post(`/restos/${restoId}/piezas`, pieza),
  eliminarPieza: (restoId, piezaId) => API.delete(`/restos/${restoId}/piezas/${piezaId}`),
  enviarOrdenARestos: (ordenId, data) => API.post(`/ordenes/${ordenId}/enviar-a-restos`, data),
};

// ==================== IA ASISTENTE ====================
export const iaAPI = {
  mejorarTexto: (texto, tipo = 'mejorar', contexto = null) => 
    API.post('/ia/mejorar-texto', { texto, tipo, contexto }),
  consulta: (mensaje, session_id = 'default') => 
    API.post('/ia/consulta', { mensaje, session_id }),
  historial: (session_id) => API.get(`/ia/historial/${session_id}`),
  limpiarHistorial: (session_id) => API.delete(`/ia/historial/${session_id}`),
  diagnostico: (modelo, sintomas) => 
    API.post(`/ia/diagnostico?modelo=${encodeURIComponent(modelo)}&sintomas=${encodeURIComponent(sintomas)}`),
  mejorarDiagnostico: (diagnostico, modelo_dispositivo = null, sintomas = null) =>
    API.post('/ia/mejorar-diagnostico', { diagnostico, modelo_dispositivo, sintomas }),
};

// ==================== AUDITORÍA ====================
export const auditoriaAPI = {
  listar: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return API.get(`/auditoria${queryString ? `?${queryString}` : ''}`);
  },
  porEntidad: (entidad, entidadId) => API.get(`/auditoria/entidad/${entidad}/${entidadId}`),
};

// ==================== ALERTAS SLA ====================
export const alertasSLAAPI = {
  listar: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return API.get(`/alertas-sla${queryString ? `?${queryString}` : ''}`);
  },
  verificar: () => API.post('/alertas-sla/verificar'),
  resolver: (alertaId) => API.patch(`/alertas-sla/${alertaId}/resolver`),
};

// ==================== COMISIONES ====================
export const comisionesAPI = {
  listar: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return API.get(`/comisiones${queryString ? `?${queryString}` : ''}`);
  },
  resumen: (periodo) => API.get(`/comisiones/resumen${periodo ? `?periodo=${periodo}` : ''}`),
  aprobar: (id) => API.post(`/comisiones/${id}/aprobar`),
  pagar: (id) => API.post(`/comisiones/${id}/pagar`),
  getConfig: () => API.get('/comisiones/config'),
  updateConfig: (config) => API.put('/comisiones/config', config),
};

// ==================== TRANSPORTISTAS Y ETIQUETAS ====================
export const transportistasAPI = {
  listar: () => API.get('/transportistas'),
  obtener: (codigo) => API.get(`/transportistas/${codigo}`),
  actualizar: (codigo, data) => API.put(`/transportistas/${codigo}`, data),
};

export const etiquetasEnvioAPI = {
  listar: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return API.get(`/etiquetas-envio${queryString ? `?${queryString}` : ''}`);
  },
  crear: (data) => API.post('/etiquetas-envio', data),
  obtener: (id) => API.get(`/etiquetas-envio/${id}`),
  eliminar: (id) => API.delete(`/etiquetas-envio/${id}`),
};

// ==================== PLANTILLAS EMAIL ====================
export const plantillasEmailAPI = {
  listar: () => API.get('/plantillas-email'),
  obtener: (tipo) => API.get(`/plantillas-email/${tipo}`),
  actualizar: (id, data) => API.put(`/plantillas-email/${id}`, data),
  resetear: (id) => API.post(`/plantillas-email/${id}/reset`),
};

// ==================== INSURAMA / SUMBROKER ====================
export const insuramaAPI = {
  // Configuración
  obtenerConfig: () => API.get('/insurama/config'),
  guardarConfig: (data) => API.post('/insurama/config', data),
  testConexion: () => API_SLOW.post('/insurama/test-conexion'),
  
  // Presupuestos (lectura) - uses cache, fast response
  listarPresupuestos: (page = 1, pageSize = 20) => API.get(`/insurama/presupuestos?page=${page}&page_size=${pageSize}`),
  obtenerPresupuesto: (codigo) => API_SLOW.get(`/insurama/presupuesto/${codigo}`),
  obtenerCompetidores: (codigo) => API.get(`/insurama/presupuesto/${codigo}/competidores`),
  
  // Sincronización en background
  sincronizar: () => API.post('/insurama/sync'),
  
  // Búsqueda múltiple (pre-carga todos los datos de mercado en paralelo)
  busquedaMultiple: (codigos) => API_SLOW.post('/insurama/busqueda-multiple', { codigos }),
  
  // Fotos y documentos
  obtenerFotos: (codigo) => API_SLOW.get(`/insurama/presupuesto/${codigo}/fotos`),
  descargarFotos: (codigo) => API_SLOW.post(`/insurama/presupuesto/${codigo}/descargar-fotos`),
  subirFotosDesdeOrden: (codigo) => API_SLOW.post(`/insurama/presupuesto/${codigo}/fotos/subir-desde-orden`),
  
  // Observaciones
  obtenerObservaciones: (codigo) => API_SLOW.get(`/insurama/presupuesto/${codigo}/observaciones`),
  enviarObservacion: (codigo, data) => API_SLOW.post(`/insurama/presupuesto/${codigo}/observacion`, data),
  
  // Acciones de escritura
  enviarPresupuesto: (codigo, data) => API_SLOW.post(`/insurama/presupuesto/${codigo}/enviar-presupuesto`, data),
  actualizarEstado: (codigo, data) => API_SLOW.post(`/insurama/presupuesto/${codigo}/estado`, data),
  enviarTracking: (codigo, tracking, transportista) => API_SLOW.post(`/insurama/presupuesto/${codigo}/tracking?tracking_number=${tracking}${transportista ? `&transportista=${transportista}` : ''}`),
  rechazarPresupuesto: (codigo, data) => API_SLOW.post(`/insurama/presupuesto/${codigo}/rechazar`, data),
  
  // Importar al CRM
  importarPresupuesto: (codigo) => API_SLOW.post(`/insurama/presupuesto/${codigo}/importar`),
  
  // Carga masiva desde Excel
  precheckCargaMasiva: (formData) => API_SLOW.post('/insurama/carga-masiva/precheck', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  cargaMasiva: (formData) => API_SLOW.post('/insurama/carga-masiva', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
};

// ==================== INTELIGENCIA DE PRECIOS ====================
export const inteligenciaPreciosAPI = {
  // Dashboard con filtros de período
  getDashboard: async (queryString = '') => {
    const response = await API_SLOW.get(`/inteligencia-precios/dashboard${queryString}`);
    return response.data;
  },
  
  // Historial
  getHistorial: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await API_SLOW.get(`/inteligencia-precios/historial${queryString ? `?${queryString}` : ''}`);
    return response.data;
  },
  
  // Recomendación de precios
  getRecomendacion: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await API_SLOW.get(`/inteligencia-precios/recomendar-precio${queryString ? `?${queryString}` : ''}`);
    return response.data;
  },
  
  // Registrar resultado manual
  registrarResultado: (data) => API_SLOW.post('/inteligencia-precios/registrar-resultado', data),
  
  // Capturar datos desde competidores (para testing manual)
  capturarDesdeCompetidores: (codigo) => API.post(`/inteligencia-precios/capturar-desde-competidores/${codigo}`),
  
  // Análisis de competidor
  analizarCompetidor: async (nombre) => {
    const response = await API.get(`/inteligencia-precios/analisis-competidor/${encodeURIComponent(nombre)}`);
    return response.data;
  },
};

// ==================== LIQUIDACIONES ====================
export const liquidacionesAPI = {
  // Obtener pendientes
  getPendientes: async () => {
    const response = await API.get('/liquidaciones/pendientes');
    return response.data;
  },
  
  // Obtener por mes
  getPorMes: async (mes) => {
    const response = await API.get(`/liquidaciones/por-mes/${mes}`);
    return response.data;
  },
  
  // Historial de meses
  getHistorialMeses: async () => {
    const response = await API.get('/liquidaciones/historial-meses');
    return response.data;
  },
  
  // Impagados
  getImpagados: async () => {
    const response = await API.get('/liquidaciones/impagados');
    return response.data;
  },
  
  // Actualizar estado
  actualizarEstado: async (codigo, estado, notas = null) => {
    const params = new URLSearchParams({ estado });
    if (notas) params.append('notas', notas);
    const response = await API.patch(`/liquidaciones/${codigo}/estado?${params}`);
    return response.data;
  },
  
  // Actualizar garantía
  actualizarGarantia: async (codigo, tieneGarantia, codigoGarantia = null, costesGarantia = 0) => {
    const params = new URLSearchParams({ 
      tiene_garantia: tieneGarantia,
      costes_garantia: costesGarantia
    });
    if (codigoGarantia) params.append('codigo_garantia', codigoGarantia);
    const response = await API.patch(`/liquidaciones/${codigo}/garantia?${params}`);
    return response.data;
  },
  
  // Marcar pagados masivo
  marcarPagados: async (codigos, mes) => {
    const response = await API.post('/liquidaciones/marcar-pagados', { codigos, mes });
    return response.data;
  },
  
  // Importar Excel
  importarExcel: async (file, mes) => {
    const formData = new FormData();
    formData.append('file', file);
    if (mes) formData.append('mes', mes);
    
    const response = await API.post('/liquidaciones/importar-excel', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },
  
  // Eliminar
  eliminar: (codigo) => API.delete(`/liquidaciones/${codigo}`),
};

// ==================== SYNC SCHEDULER ====================
export const schedulerAPI = {
  getConfig: () => API.get('/mobilesentrix/scheduler/config'),
  saveConfig: (config) => API.post('/mobilesentrix/scheduler/config', config),
  start: () => API.post('/mobilesentrix/scheduler/start'),
  stop: () => API.post('/mobilesentrix/scheduler/stop'),
  runNow: () => API.post('/mobilesentrix/scheduler/run-now'),
};

// ==================== MOBILESENTRIX API ADICIONAL ====================
export const mobilesentrixAPI = {
  syncPrecios: () => API.post('/mobilesentrix/sync-precios'),
  syncProgress: () => API.get('/mobilesentrix/sync-catalogo/progress'),
};

// ==================== CONTABILIDAD ====================
export const contabilidadAPI = {
  // Estadísticas
  stats: () => API.get('/contabilidad/stats'),
  
  // Facturas
  listarFacturas: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return API.get(`/contabilidad/facturas${queryString ? `?${queryString}` : ''}`);
  },
  obtenerFactura: (id) => API.get(`/contabilidad/facturas/${id}`),
  crearFactura: (data) => API.post('/contabilidad/facturas', data),
  actualizarFactura: (id, data) => API.patch(`/contabilidad/facturas/${id}`, data),
  emitirFactura: (id) => API.post(`/contabilidad/facturas/${id}/emitir`),
  anularFactura: (id, motivo) => API.post(`/contabilidad/facturas/${id}/anular`, { motivo }),
  
  // Pagos
  registrarPago: (data) => API.post('/contabilidad/pagos', data),
  listarPagos: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return API.get(`/contabilidad/pagos${queryString ? `?${queryString}` : ''}`);
  },
  
  // Abonos
  crearAbono: (data) => API.post('/contabilidad/abonos', data),
  listarAbonos: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return API.get(`/contabilidad/abonos${queryString ? `?${queryString}` : ''}`);
  },
  
  // Albaranes
  listarAlbaranes: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return API.get(`/contabilidad/albaranes${queryString ? `?${queryString}` : ''}`);
  },
  obtenerAlbaran: (id) => API.get(`/contabilidad/albaranes/${id}`),
  crearAlbaranDesdeOrden: (ordenId) => API.post(`/contabilidad/albaranes/desde-orden/${ordenId}`),
  facturarAlbaran: (id) => API.post(`/contabilidad/albaranes/${id}/facturar`),
  
  // Informes
  resumen: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return API.get(`/contabilidad/informes/resumen${queryString ? `?${queryString}` : ''}`);
  },
  ivaTrimestral: (año, trimestre) => API.get(`/contabilidad/informes/iva-trimestral?año=${año}&trimestre=${trimestre}`),
  pendientes: () => API.get('/contabilidad/informes/pendientes'),
  
  // Recordatorios
  enviarRecordatorio: (facturaId) => API.post(`/contabilidad/recordatorios/enviar/${facturaId}`),
};

// ==================== FINANZAS (DASHBOARD CENTRALIZADO) ====================
export const finanzasAPI = {
  // Dashboard principal
  getDashboard: (periodo = 'mes') => API.get(`/finanzas/dashboard?periodo=${periodo}`),
  
  // Evolución mensual
  getEvolucion: (meses = 6) => API.get(`/finanzas/evolucion?meses=${meses}`),
  
  // Detalle de gastos
  getDetalleGastos: (periodo = 'mes') => API.get(`/finanzas/gastos/detalle?periodo=${periodo}`),
  
  // Valor del inventario
  getValorInventario: () => API.get('/finanzas/inventario/valor'),
  
  // Balance general
  getBalance: (año) => API.get(`/finanzas/balance${año ? `?año=${año}` : ''}`),
  
  // Registrar compra en contabilidad
  registrarCompra: (compraId) => API.post(`/finanzas/registrar-compra/${compraId}`),
  
  // Registrar orden como factura
  registrarOrden: (ordenId) => API.post(`/finanzas/registrar-orden/${ordenId}`),
};

// ==================== UPLOADS ====================
// Soporta tanto URLs de Cloudinary como archivos locales
export const getUploadUrl = (fileRef) => {
  if (!fileRef) return '';
  
  // Si es un objeto con src (formato de fotos del portal), extraer el src
  if (typeof fileRef === 'object' && fileRef.src) {
    fileRef = fileRef.src;
  }
  
  // Si no es string después de la extracción, retornar vacío
  if (typeof fileRef !== 'string') return '';
  
  // Si ya es una URL completa (Cloudinary u otra), devolverla directamente
  if (fileRef.startsWith('http://') || fileRef.startsWith('https://')) {
    return fileRef;
  }
  
  // Si ya tiene /api/uploads, construir solo con el backend
  if (fileRef.startsWith('/api/uploads/')) {
    return `${BACKEND_URL}${fileRef}`;
  }
  
  // Si es un nombre de archivo local, construir la URL del backend
  return `${BACKEND_URL}/api/uploads/${fileRef}`;
};

export { API_SLOW };
export default API;

import { forwardRef, useState, useEffect } from 'react';
import { empresaAPI, getUploadUrl } from '@/lib/api';

const S = {
  page: {
    padding: '12mm 15mm',
    backgroundColor: 'white',
    color: '#111',
    fontFamily: "'Helvetica Neue', Helvetica, Arial, sans-serif",
    fontSize: '8.5px',
    lineHeight: '1.4',
    width: '210mm',
    boxSizing: 'border-box',
    printColorAdjust: 'exact',
    WebkitPrintColorAdjust: 'exact',
  },
  label: {
    color: '#888',
    fontSize: '7px',
    textTransform: 'uppercase',
    letterSpacing: '0.6px',
    marginBottom: '1mm',
    display: 'block',
  },
  value: {
    color: '#111',
    fontWeight: '500',
    fontSize: '8.5px',
  },
  hrLight: { border: 'none', borderTop: '1px solid #e5e5e5', margin: '3mm 0' },
  hrDark:  { border: 'none', borderTop: '2px solid #111',    margin: '4mm 0' },
};

const statusLabels = {
  pendiente_recibir: 'Pendiente Recibir',
  recibida:          'Recibida',
  cuarentena:        'Cuarentena',
  en_taller:         'En Taller',
  reparado:          'Reparado',
  validacion:        'Validación',
  enviado:           'Enviado',
  garantia:          'Garantía',
  cancelado:         'Cancelado',
  reemplazo:         'Reemplazo',
  irreparable:       'Irreparable',
};

const OrdenPDF = forwardRef(function OrdenPDF(
  { orden, cliente, materiales = [], mode = 'full', modoB2B = false, includeFotos = false },
  ref
) {
  const [empresa, setEmpresa] = useState(null);

  useEffect(() => {
    empresaAPI.obtener().then(r => setEmpresa(r.data)).catch(() => {});
  }, []);

  const isBlank  = mode === 'blank_no_prices';
  const isNoPrices = mode === 'no_prices' || isBlank;
  const isFull   = mode === 'full';

  const val = (v, fb = '—') => {
    if (isBlank) return '_____';
    return (v == null || v === '') ? fb : v;
  };

  const boolLabel = (v) => {
    if (isBlank) return '_____';
    if (v == null) return 'PEND.';
    return v ? 'Sí' : 'No';
  };

  const fmtDate = (d) => {
    if (!d) return isBlank ? '__/__/____' : '—';
    return new Date(d).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
  };

  const fmtDT = (d) => {
    if (!d) return isBlank ? '__/__/____' : '—';
    return new Date(d).toLocaleString('es-ES', {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  };

  const totales = (() => {
    const base = materiales.reduce((s, m) => {
      const st = (m.cantidad || 0) * (m.precio_unitario || 0);
      return s + st - (m.descuento ? st * m.descuento / 100 : 0);
    }, 0);
    const ivaPct = empresa?.iva_por_defecto || 21;
    const iva = base * ivaPct / 100;
    return { base, iva, total: base + iva, ivaPct };
  })();

  const logoSrc = (() => {
    const raw = empresa?.logo?.url || empresa?.logo_url;
    if (!raw) return null;
    return raw.startsWith('http') ? raw : getUploadUrl(raw);
  })();

  const getCreador = () => (orden?.historial_estados || [])[0]?.usuario || 'Sistema';

  // ── Fotos para el Anexo ─────────────────────────────────────────────────
  const allFotos = [
    ...(orden?.evidencias         || []).map(f => ({ url: getUploadUrl(f), tipo: 'Admin' })),
    ...(orden?.evidencias_tecnico || []).map(f => ({ url: getUploadUrl(f), tipo: 'Técnico' })),
  ].slice(0, 16);

  const photoPages = [];
  if (includeFotos && !isBlank && allFotos.length > 0) {
    for (let i = 0; i < allFotos.length; i += 8) {
      photoPages.push(allFotos.slice(i, i + 8));
    }
  }

  const totalPages = 1 + photoPages.length;

  return (
    <div ref={ref}>

      {/* ══════════════════════════════════════════════════════════
          PÁGINA PRINCIPAL
      ══════════════════════════════════════════════════════════ */}
      <div style={S.page}>

        {/* CABECERA */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4mm' }}>
          <div>
            {logoSrc ? (
              <img src={logoSrc} alt="Logo" style={{ height: '44px', maxWidth: '150px', objectFit: 'contain' }} />
            ) : (
              <p style={{ fontSize: '18px', fontWeight: '800', margin: 0 }}>{empresa?.nombre || 'Mi Empresa'}</p>
            )}
            <p style={{ fontSize: '7.5px', color: '#666', margin: '1.5mm 0 0' }}>
              {empresa?.direccion}{empresa?.codigo_postal && `, ${empresa.codigo_postal}`}{empresa?.ciudad && ` ${empresa.ciudad}`}
            </p>
            <p style={{ fontSize: '7.5px', color: '#666', margin: '0.5mm 0 0' }}>
              {empresa?.cif && `CIF: ${empresa.cif}`}{empresa?.telefono && ` · Tel: ${empresa.telefono}`}
            </p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <p style={{ fontSize: '20px', fontWeight: '800', margin: 0, letterSpacing: '-0.5px', fontFamily: 'monospace' }}>
              {isBlank ? 'OT-________' : (orden?.numero_orden || 'OT-000000')}
            </p>
            <p style={{ fontSize: '9px', color: '#555', margin: '1mm 0', textTransform: 'uppercase', fontWeight: '600' }}>
              {isBlank ? '—' : (statusLabels[orden?.estado] || orden?.estado || '—')}
            </p>
            <p style={{ fontSize: '7.5px', color: '#999', margin: 0 }}>{fmtDate(orden?.created_at)}</p>
            {orden?.numero_autorizacion && !isBlank && (
              <p style={{ fontSize: '8px', color: '#444', margin: '1mm 0 0', fontFamily: 'monospace' }}>
                Aut: {orden.numero_autorizacion}
              </p>
            )}
          </div>
        </div>

        <div style={S.hrDark} />

        {/* BLOQUE 1: CLIENTE + DISPOSITIVO (2 columnas) */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8mm', marginBottom: '3mm' }}>

          {/* Columna izquierda: Cliente */}
          <div>
            <span style={S.label}>Cliente</span>
            <p style={{ fontSize: '11px', fontWeight: '700', margin: '0 0 1.5mm' }}>
              {isBlank
                ? '___________________________'
                : `${cliente?.nombre || ''} ${cliente?.apellidos || ''}`.trim() || '—'}
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2mm' }}>
              <div>
                <span style={S.label}>DNI</span>
                <span style={S.value}>{val(cliente?.dni)}</span>
              </div>
              <div>
                <span style={S.label}>Teléfono</span>
                <span style={S.value}>{val(cliente?.telefono)}</span>
              </div>
            </div>
            <p style={{ fontSize: '7.5px', margin: '1mm 0', color: '#555' }}>{val(cliente?.email, '')}</p>
            <p style={{ fontSize: '7.5px', margin: 0, color: '#888' }}>
              {isBlank
                ? '________________________________'
                : `${cliente?.direccion || ''}${cliente?.codigo_postal ? `, ${cliente.codigo_postal}` : ''}${cliente?.ciudad ? ` ${cliente.ciudad}` : ''}` || '—'}
            </p>
          </div>

          {/* Columna derecha: Dispositivo */}
          <div>
            <span style={S.label}>Dispositivo</span>
            <p style={{ fontSize: '11px', fontWeight: '700', margin: '0 0 1.5mm' }}>
              {val(orden?.dispositivo?.modelo || orden?.dispositivo_modelo, 'Sin especificar')}
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2mm' }}>
              <div>
                <span style={S.label}>IMEI / SN</span>
                <span style={{ ...S.value, fontFamily: 'monospace', fontSize: '8px' }}>
                  {val(orden?.dispositivo?.imei || orden?.dispositivo_imei, 'PENDIENTE')}
                </span>
              </div>
              <div>
                <span style={S.label}>Color</span>
                <span style={S.value}>{val(orden?.dispositivo?.color || orden?.dispositivo_color)}</span>
              </div>
            </div>
            <div style={{ marginTop: '2mm', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2mm' }}>
              <div>
                <span style={S.label}>Técnico</span>
                <span style={S.value}>{val(orden?.tecnico_asignado)}</span>
              </div>
              <div>
                <span style={S.label}>Tipo</span>
                <span style={S.value}>{val(orden?.tipo_servicio || orden?.origen || (modoB2B ? 'B2B' : 'B2C'))}</span>
              </div>
            </div>
          </div>
        </div>

        {/* FECHAS (5 columnas) */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '3mm', marginBottom: '3mm', paddingTop: '2mm', borderTop: '1px solid #eee' }}>
          <div><span style={S.label}>Creación</span><span style={{ ...S.value, fontSize: '7.5px' }}>{fmtDT(orden?.created_at)}</span></div>
          <div><span style={S.label}>Recepción</span><span style={{ ...S.value, fontSize: '7.5px' }}>{fmtDT(orden?.fecha_recibida_centro)}</span></div>
          <div><span style={S.label}>Inicio rep.</span><span style={{ ...S.value, fontSize: '7.5px' }}>{fmtDT(orden?.fecha_inicio_reparacion)}</span></div>
          <div><span style={S.label}>Fin rep.</span><span style={{ ...S.value, fontSize: '7.5px' }}>{fmtDT(orden?.fecha_fin_reparacion)}</span></div>
          <div><span style={S.label}>Envío</span><span style={{ ...S.value, fontSize: '7.5px' }}>{fmtDT(orden?.fecha_enviado)}</span></div>
        </div>

        {/* REFERENCIAS (4 columnas) */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '3mm', marginBottom: '3mm', paddingTop: '2mm', borderTop: '1px solid #eee' }}>
          <div>
            <span style={S.label}>OT ID</span>
            <span style={{ ...S.value, fontFamily: 'monospace', fontSize: '7.5px' }}>
              {isBlank ? '______' : val(orden?.id)}
            </span>
          </div>
          <div>
            <span style={S.label}>Cliente corporativo</span>
            <span style={S.value}>{isBlank ? '______' : val(orden?.cliente_corporativo || (modoB2B ? 'B2B' : '—'))}</span>
          </div>
          <div>
            <span style={S.label}>Caso externo</span>
            <span style={{ ...S.value, fontFamily: 'monospace' }}>
              {isBlank ? '______' : val(orden?.numero_autorizacion || orden?.caso_externo)}
            </span>
          </div>
          <div>
            <span style={S.label}>Creado por</span>
            <span style={S.value}>{isBlank ? '______' : getCreador()}</span>
          </div>
        </div>

        <div style={S.hrDark} />

        {/* BLOQUE 2: TÉCNICO — Izq: Avería+Diagnóstico / Der: RI+QC+Log+CPI */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8mm', marginBottom: '3mm' }}>

          {/* Columna izquierda */}
          <div>
            <span style={S.label}>Avería reportada</span>
            <p style={{ margin: '0 0 3mm', fontSize: '8px', lineHeight: '1.5', whiteSpace: 'pre-wrap', maxHeight: '17mm', overflow: 'hidden' }}>
              {isBlank
                ? '________________________________\n________________________________\n________________________________'
                : (orden?.dispositivo?.daños || orden?.averia_descripcion || 'Sin descripción')}
            </p>

            <span style={S.label}>Diagnóstico técnico</span>
            <p style={{
              margin: 0,
              fontSize: '8px',
              lineHeight: '1.5',
              whiteSpace: 'pre-wrap',
              maxHeight: '22mm',
              overflow: 'hidden',
              color: (isBlank || orden?.diagnostico_tecnico) ? '#111' : '#999',
              fontStyle: (!isBlank && !orden?.diagnostico_tecnico) ? 'italic' : 'normal',
            }}>
              {isBlank
                ? '________________________________\n________________________________\n________________________________\n________________________________'
                : (orden?.diagnostico_tecnico || 'Pendiente de diagnóstico')}
            </p>
            {orden?.tecnico_asignado && !isBlank && (
              <p style={{ margin: '1mm 0 0', fontSize: '7.5px', color: '#666' }}>— {orden.tecnico_asignado}</p>
            )}
          </div>

          {/* Columna derecha */}
          <div>
            {/* RI */}
            <span style={S.label}>Inspección de entrada (RI)</span>
            <div style={{ fontSize: '7.5px', marginBottom: '2.5mm', lineHeight: '1.5' }}>
              <p style={{ margin: 0 }}>
                Resultado: <strong>{isBlank ? '_____' : val(orden?.ri_resultado, 'PENDIENTE')}</strong>
                {' '}· Completada: {boolLabel(orden?.ri_completada)}
              </p>
              <p style={{ margin: 0 }}>
                Checklist: {boolLabel(orden?.recepcion_checklist_completo)}
                {' '}· Físico: {boolLabel(orden?.recepcion_estado_fisico_registrado)}
                {' '}· Accesorios: {boolLabel(orden?.recepcion_accesorios_registrados)}
              </p>
              <p style={{ margin: 0 }}>
                Resp.: {isBlank ? '_____' : (orden?.ri_usuario_nombre || (orden?.ri_usuario ? 'Nombre no configurado' : '—'))}
                {' '}· Evidencias: {isBlank ? '_____' : `${(orden?.evidencias || []).length} foto(s)`}
              </p>
            </div>

            {/* QC - Control de Calidad de Diagnóstico de Salida */}
            <span style={S.label}>Control de calidad final (QC) - Diagnóstico de Salida</span>
            <div style={{ fontSize: '7.5px', marginBottom: '2.5mm', lineHeight: '1.5', padding: '2mm', backgroundColor: orden?.diagnostico_salida_realizado && orden?.funciones_verificadas ? '#f0fdf4' : '#fef2f2', border: '1px solid', borderColor: orden?.diagnostico_salida_realizado && orden?.funciones_verificadas ? '#22c55e' : '#ef4444', borderRadius: '2mm' }}>
              <p style={{ margin: 0, fontWeight: '600', fontSize: '8px' }}>
                ✓ Estado del Dispositivo: <strong style={{ color: (orden?.diagnostico_salida_realizado && orden?.funciones_verificadas && orden?.limpieza_realizada) ? '#16a34a' : '#dc2626' }}>
                  {isBlank
                    ? '_____'
                    : ((orden?.diagnostico_salida_realizado && orden?.funciones_verificadas && orden?.limpieza_realizada) ? '✅ VERIFICADO - CONFORME' : '⚠️ PENDIENTE DE VERIFICACIÓN')}
                </strong>
              </p>
              <div style={{ marginTop: '1.5mm', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '2mm' }}>
                <p style={{ margin: 0 }}>
                  <span style={{ fontSize: '6px', color: '#666' }}>Diagnóstico salida:</span><br/>
                  <strong>{orden?.diagnostico_salida_realizado ? '✓ Realizado' : '✗ Pendiente'}</strong>
                </p>
                <p style={{ margin: 0 }}>
                  <span style={{ fontSize: '6px', color: '#666' }}>Funciones verificadas:</span><br/>
                  <strong>{orden?.funciones_verificadas ? '✓ OK' : '✗ Pendiente'}</strong>
                </p>
                <p style={{ margin: 0 }}>
                  <span style={{ fontSize: '6px', color: '#666' }}>Limpieza:</span><br/>
                  <strong>{orden?.limpieza_realizada ? '✓ Realizada' : '✗ Pendiente'}</strong>
                </p>
              </div>
              {orden?.qc_funciones && !isBlank && (
                <div style={{ marginTop: '2mm', paddingTop: '1.5mm', borderTop: '1px dashed #ccc' }}>
                  <span style={{ fontSize: '6px', color: '#666' }}>Funciones del sistema verificadas:</span>
                  <p style={{ margin: '0.5mm 0 0 0', fontSize: '7px' }}>
                    {Object.entries(orden.qc_funciones || {})
                      .filter(([_, checked]) => checked)
                      .map(([func]) => {
                        const labels = {
                          pantalla_touch: 'Pantalla/Touch',
                          wifi: 'WiFi',
                          bluetooth: 'Bluetooth',
                          camara_trasera: 'Cám. trasera',
                          camara_frontal: 'Cám. frontal',
                          microfono: 'Micrófono',
                          altavoz_auricular: 'Altavoz',
                          carga: 'Carga',
                          botones_fisicos: 'Botones',
                          sim_red: 'SIM/Red',
                          biometria: 'Biometría'
                        };
                        return labels[func] || func;
                      })
                      .join(' · ') || 'N/A'}
                  </p>
                </div>
              )}
              {orden?.bateria_estado && !isBlank && (
                <p style={{ margin: '1.5mm 0 0 0', fontSize: '7px' }}>
                  <span style={{ fontSize: '6px', color: '#666' }}>Batería:</span>{' '}
                  {orden.bateria_estado === 'ok' ? '✓ OK (>80%)' : 
                   orden.bateria_estado === 'degradada' ? '⚠️ Degradada (<80%)' :
                   orden.bateria_estado === 'reemplazada' ? '🔄 Reemplazada' : 'N/A'}
                  {orden.bateria_nivel ? ` · ${orden.bateria_nivel}%` : ''}
                  {orden.bateria_ciclos ? ` · ${orden.bateria_ciclos} ciclos` : ''}
                </p>
              )}
              <p style={{ margin: '1.5mm 0 0 0' }}>
                <span style={{ fontSize: '6px', color: '#666' }}>Técnico responsable:</span>{' '}
                {isBlank ? '_____' : val(orden?.tecnico_asignado)}
                {' '}·{' '}
                <span style={{ fontSize: '6px', color: '#666' }}>Fecha QC:</span>{' '}
                {isBlank ? '_____' : fmtDT(orden?.fecha_fin_reparacion || orden?.updated_at)}
              </p>
            </div>

            {/* Logística */}
            {(orden?.agencia_envio || orden?.codigo_recogida_entrada || orden?.codigo_recogida_salida || isBlank) && (
              <div style={{ marginBottom: '2.5mm' }}>
                <span style={S.label}>Logística</span>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '2mm', fontSize: '7.5px' }}>
                  <div>
                    <span style={{ ...S.label, fontSize: '6.5px' }}>Agencia</span>
                    <span>{val(orden?.agencia_envio)}</span>
                  </div>
                  <div>
                    <span style={{ ...S.label, fontSize: '6.5px' }}>Cód. Entrada</span>
                    <span style={{ fontFamily: 'monospace' }}>{val(orden?.codigo_recogida_entrada)}</span>
                  </div>
                  <div>
                    <span style={{ ...S.label, fontSize: '6.5px' }}>Cód. Salida</span>
                    <span style={{ fontFamily: 'monospace' }}>{val(orden?.codigo_recogida_salida)}</span>
                  </div>
                </div>
              </div>
            )}

            {/* CPI / NIST */}
            <span style={S.label}>Privacidad / CPI-NIST 800-88</span>
            <div style={{ fontSize: '7.5px', lineHeight: '1.5' }}>
              {(() => {
                const opcionLabels = {
                  cliente_ya_restablecio:       'Ya venía restablecido por el cliente (verificado)',
                  cliente_no_autoriza:           'Cliente NO autoriza restablecer/borrar (Privacidad alta)',
                  sat_realizo_restablecimiento:  'Restablecimiento realizado por el SAT',
                };
                const opcionLabel = orden?.cpi_opcion
                  ? (opcionLabels[orden.cpi_opcion] || orden.cpi_opcion)
                  : (orden?.cpi_resultado ? '(registro anterior)' : null);
                // Nombre del técnico: nunca mostrar email
                const nombreTecnico = orden?.cpi_usuario_nombre || 'Nombre no configurado';
                return (
                  <>
                    <p style={{ margin: 0, fontWeight: '500' }}>
                      {isBlank ? '_____' : (opcionLabel || 'PENDIENTE')}
                    </p>
                    {orden?.cpi_opcion === 'sat_realizo_restablecimiento' && !isBlank && (
                      <p style={{ margin: 0 }}>Método: {val(orden?.cpi_metodo)}</p>
                    )}
                    <p style={{ margin: 0 }}>
                      Resp.: {isBlank ? '_____' : nombreTecnico}
                      {' '}· Fecha: {isBlank ? '_____' : (orden?.cpi_fecha ? fmtDT(orden.cpi_fecha) : 'PENDIENTE')}
                    </p>
                  </>
                );
              })()}
            </div>
          </div>
        </div>

        <div style={S.hrDark} />

        {/* MATERIALES Y SERVICIOS */}
        <div style={{ marginBottom: '3mm' }}>
          <span style={{ ...S.label, marginBottom: '2mm', display: 'block' }}>Materiales y servicios</span>

          {materiales.length === 0 && !isBlank ? (
            <p style={{ color: '#999', fontStyle: 'italic', fontSize: '8px', margin: 0 }}>Sin materiales registrados</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '7.5px' }}>
              <thead>
                <tr style={{ borderBottom: '1.5px solid #ddd' }}>
                  <th style={{ textAlign: 'left', padding: '1.5mm 0', fontWeight: '700' }}>SKU / Descripción</th>
                  <th style={{ textAlign: 'left', padding: '1.5mm 2mm', width: '80px', fontWeight: '700' }}>Proveedor</th>
                  <th style={{ textAlign: 'center', padding: '1.5mm 2mm', width: '40px', fontWeight: '700' }}>Cant.</th>
                  {isFull && !isBlank && <th style={{ textAlign: 'right', padding: '1.5mm 2mm', width: '60px', fontWeight: '700' }}>P. Unit.</th>}
                  {isFull && !isBlank && <th style={{ textAlign: 'right', padding: '1.5mm 2mm', width: '45px', fontWeight: '700' }}>Dto.</th>}
                  {isFull && !isBlank && <th style={{ textAlign: 'right', padding: '1.5mm 0', width: '60px', fontWeight: '700' }}>Subtotal</th>}
                </tr>
              </thead>
              <tbody>
                {(isBlank ? [{}, {}, {}] : materiales).map((m, i) => {
                  const st = (m.cantidad || 0) * (m.precio_unitario || 0);
                  const dto = m.descuento ? st * m.descuento / 100 : 0;
                  return (
                    <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '1.5mm 0' }}>
                        {isBlank ? '________________________' : `${m.sku || ''} ${m.nombre || '—'}`.trim()}
                      </td>
                      <td style={{ padding: '1.5mm 2mm' }}>{isBlank ? '________' : (m.proveedor || '—')}</td>
                      <td style={{ textAlign: 'center', padding: '1.5mm 2mm' }}>{isBlank ? '___' : (m.cantidad || 0)}</td>
                      {isFull && !isBlank && (
                        <td style={{ textAlign: 'right', padding: '1.5mm 2mm' }}>{(m.precio_unitario || 0).toFixed(2)} €</td>
                      )}
                      {isFull && !isBlank && (
                        <td style={{ textAlign: 'right', padding: '1.5mm 2mm', color: m.descuento ? '#111' : '#ccc' }}>
                          {m.descuento ? `-${m.descuento}%` : '—'}
                        </td>
                      )}
                      {isFull && !isBlank && (
                        <td style={{ textAlign: 'right', padding: '1.5mm 0' }}>{(st - dto).toFixed(2)} €</td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}

          {/* Totales — solo modo full */}
          {isFull && !isBlank && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '3mm' }}>
              <div style={{ width: '160px', fontSize: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.8mm 0' }}>
                  <span style={{ color: '#666' }}>Base imponible</span>
                  <span>{totales.base.toFixed(2)} €</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.8mm 0' }}>
                  <span style={{ color: '#666' }}>IVA {totales.ivaPct}%</span>
                  <span>{totales.iva.toFixed(2)} €</span>
                </div>
                {(orden?.coste_transporte || 0) > 0 && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.8mm 0' }}>
                    <span style={{ color: '#666' }}>Transporte</span>
                    <span>{(orden.coste_transporte).toFixed(2)} €</span>
                  </div>
                )}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '1.5mm 0',
                  fontWeight: '800',
                  fontSize: '11px',
                  borderTop: '2px solid #111',
                  marginTop: '1.5mm',
                }}>
                  <span>Total</span>
                  <span>{(totales.total + (orden?.coste_transporte || 0)).toFixed(2)} €</span>
                </div>
              </div>
            </div>
          )}
        </div>

        <div style={S.hrLight} />

        {/* GARANTÍA + NOTAS + QR */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '6mm', marginBottom: '3mm' }}>
          <div>
            <span style={S.label}>Garantía</span>
            <p style={{ margin: 0, fontSize: '8px' }}>
              {orden?.garantia_meses ? `${orden.garantia_meses} meses` : '6 meses'} desde la entrega
            </p>
            <p style={{ margin: '1mm 0 0', fontSize: '6.5px', color: '#777', lineHeight: '1.4' }}>
              {(empresa?.textos_legales?.clausulas_documentos || '').substring(0, 200) ||
               'Garantía válida para la avería reparada. Excluye daños por mal uso, golpes, líquidos o manipulación por terceros.'}
            </p>
          </div>

          {(orden?.notas || isBlank) ? (
            <div>
              <span style={S.label}>Notas</span>
              <p style={{ margin: 0, fontSize: '8px', maxHeight: '15mm', overflow: 'hidden' }}>
                {isBlank ? '________________________\n________________________' : (orden.notas || '—')}
              </p>
            </div>
          ) : <div />}

          <div style={{ textAlign: 'center' }}>
            <span style={{ ...S.label, display: 'block', textAlign: 'center' }}>Seguimiento</span>
            {orden?.qr_code ? (
              <img
                src={orden.qr_code.startsWith('data:') ? orden.qr_code : `data:image/png;base64,${orden.qr_code}`}
                alt="QR"
                style={{ width: '22mm', height: '22mm' }}
              />
            ) : (
              <p style={{ fontFamily: 'monospace', fontSize: '9px', fontWeight: '600', margin: 0 }}>
                {orden?.token_seguimiento || orden?.numero_orden}
              </p>
            )}
          </div>
        </div>

        <div style={S.hrLight} />

        {/* TEXTO LEGAL */}
        <p style={{ fontSize: '6px', color: '#bbb', lineHeight: '1.4', margin: '0 0 3mm' }}>
          {empresa?.textos_legales?.politica_privacidad
            ? empresa.textos_legales.politica_privacidad
                .replace('[NOMBRE_EMPRESA]', empresa?.nombre || 'Mi Empresa')
                .substring(0, 350) + '...'
            : `En cumplimiento del RGPD, sus datos serán tratados por ${empresa?.nombre || 'Mi Empresa'} para gestionar este servicio técnico. Puede ejercer sus derechos en ${empresa?.email || 'info@empresa.es'}.`}
        </p>

        {/* FIRMAS */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20mm' }}>
          <div style={{ textAlign: 'center' }}>
            <p style={{ ...S.label, marginBottom: '12mm' }}>Conforme del cliente</p>
            <div style={{ borderTop: '1px solid #ccc', paddingTop: '1.5mm' }}>
              <p style={{ fontSize: '6.5px', color: '#aaa', margin: 0 }}>Firma y DNI</p>
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <p style={{ ...S.label, marginBottom: '12mm' }}>Sello empresa</p>
            <div style={{ borderTop: '1px solid #ccc', paddingTop: '1.5mm' }}>
              <p style={{ fontSize: '6.5px', color: '#aaa', margin: 0 }}>{empresa?.nombre || ''}</p>
            </div>
          </div>
        </div>

        {/* PIE DE PÁGINA */}
        <div style={{ marginTop: '5mm', textAlign: 'center', fontSize: '6.5px', color: '#bbb' }}>
          <p style={{ margin: 0 }}>
            {empresa?.nombre} · {empresa?.web || empresa?.email || ''} · {empresa?.telefono || ''}
          </p>
          <p style={{ margin: '0.8mm 0 0', fontSize: '6px' }}>
            OT-PDF v2.0 · Modo: {mode}
            {includeFotos && photoPages.length > 0 ? ` · ${allFotos.length} foto(s) en anexo` : ''}
            {' '}· Pág. 1/{totalPages}
            {' '}· Generado: {isBlank ? '__/__/____' : new Date().toLocaleString('es-ES')}
          </p>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════
          PÁGINAS DE ANEXO FOTOGRÁFICO
      ══════════════════════════════════════════════════════════ */}
      {photoPages.map((group, pageIdx) => (
        <div key={pageIdx} style={{ ...S.page, pageBreakBefore: 'always', breakBefore: 'page' }}>

          {/* Cabecera anexo */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4mm' }}>
            <div>
              <p style={{ fontSize: '16px', fontWeight: '800', margin: 0, letterSpacing: '-0.3px' }}>
                ANEXO FOTOGRÁFICO
              </p>
              <p style={{ fontSize: '8px', color: '#666', margin: '1mm 0 0' }}>
                Orden: {orden?.numero_orden || '—'} · Dispositivo: {orden?.dispositivo?.modelo || '—'} · IMEI: {orden?.dispositivo?.imei || '—'}
              </p>
            </div>
            <div style={{ textAlign: 'right' }}>
              <p style={{ fontSize: '12px', fontFamily: 'monospace', fontWeight: '700', margin: 0 }}>
                {orden?.numero_orden || '—'}
              </p>
              <p style={{ fontSize: '7.5px', color: '#999', margin: '0.5mm 0 0' }}>
                Pág. {pageIdx + 2}/{totalPages}
                {' '}· Fotos {pageIdx * 8 + 1}–{Math.min((pageIdx + 1) * 8, allFotos.length)} de {allFotos.length}
              </p>
            </div>
          </div>

          <div style={S.hrDark} />

          {/* Grid 4 × 2 de fotos */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '4mm', marginTop: '4mm' }}>
            {group.map((foto, fIdx) => {
              const globalIdx = pageIdx * 8 + fIdx + 1;
              return (
                <div key={fIdx} style={{ display: 'flex', flexDirection: 'column' }}>
                  <div style={{
                    border: '1px solid #ddd',
                    borderRadius: '2px',
                    overflow: 'hidden',
                    height: '55mm',
                    backgroundColor: '#f5f5f5',
                  }}>
                    <img
                      src={foto.url}
                      alt={`Foto ${globalIdx}`}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  </div>
                  <div style={{ marginTop: '1mm', fontSize: '6.5px', color: '#666', textAlign: 'center' }}>
                    <strong style={{ color: '#111' }}>#{globalIdx}</strong> · {foto.tipo}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pie de página anexo */}
          <div style={{ marginTop: '6mm', textAlign: 'center', fontSize: '6.5px', color: '#bbb' }}>
            <p style={{ margin: 0 }}>
              {empresa?.nombre || 'Revix'} · Generado: {new Date().toLocaleString('es-ES')} · OT-PDF v2.0
            </p>
          </div>
        </div>
      ))}
    </div>
  );
});

export default OrdenPDF;

/**
 * Helper unificado para construir el enlace de seguimiento GLS en el frontend.
 *
 * Orden de preferencia:
 *   1. `shipment.tracking_url` (el backend ya lo genera correctamente al crear el envío).
 *   2. Construcción manual con el formato oficial MyGLS:
 *        https://mygls.gls-spain.es/e/{codexp}/{cp_destinatario}
 *      cuando tenemos ambos campos en el documento (BD persistida).
 *   3. Fallback moderno con codbarras (funciona aunque sea menos informativo):
 *        https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/?match={codbarras}
 *
 * NOTA: Nunca devolver `apptracking.asp?codigo=...` — ese endpoint está obsoleto
 * desde hace años y devuelve error.
 */

const MYGLS_BASE = "https://mygls.gls-spain.es/e";
const FALLBACK_MATCH = "https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/?match=";
const GENERIC_HOME = "https://mygls.gls-spain.es/";

/**
 * @param {object} shipment - Documento del envío GLS.
 *   Campos esperados (cualquier combinación):
 *     tracking_url, gls_codbarras | codbarras,
 *     gls_codexp | codexp, destinatario.cp | cp_destinatario.
 * @returns {string} URL de tracking lista para <a href>.
 */
export function buildGLSTrackingUrl(shipment) {
  if (!shipment) return GENERIC_HOME;

  // 1. Backend ya nos dio URL — siempre preferirla
  if (shipment.tracking_url) return shipment.tracking_url;

  const codexp = shipment.gls_codexp || shipment.codexp;
  const cp =
    shipment.cp_destinatario ||
    shipment.destinatario?.cp ||
    shipment.cliente?.cp;

  // 2. Construcción MyGLS oficial
  if (codexp && cp) {
    return `${MYGLS_BASE}/${encodeURIComponent(codexp)}/${encodeURIComponent(cp)}`;
  }

  // 3. Fallback moderno por codbarras
  const codbarras = shipment.gls_codbarras || shipment.codbarras;
  if (codbarras) {
    return `${FALLBACK_MATCH}${encodeURIComponent(codbarras)}`;
  }

  return GENERIC_HOME;
}

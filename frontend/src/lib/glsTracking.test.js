/**
 * Tests del helper buildGLSTrackingUrl.
 * Ejecutar: yarn test src/lib/glsTracking.test.js
 */
import { buildGLSTrackingUrl } from './glsTracking';

describe('buildGLSTrackingUrl', () => {
  test('null/undefined → home MyGLS', () => {
    expect(buildGLSTrackingUrl(null)).toBe('https://mygls.gls-spain.es/');
    expect(buildGLSTrackingUrl(undefined)).toBe('https://mygls.gls-spain.es/');
  });

  test('shipment.tracking_url presente → se respeta (prioridad máxima)', () => {
    const s = { tracking_url: 'https://mygls.gls-spain.es/e/1234567890/28001', gls_codbarras: '9876' };
    expect(buildGLSTrackingUrl(s)).toBe('https://mygls.gls-spain.es/e/1234567890/28001');
  });

  test('sin tracking_url, con codexp + destinatario.cp → construye formato MyGLS', () => {
    const s = { gls_codexp: '4021344762', destinatario: { cp: '14007' } };
    expect(buildGLSTrackingUrl(s)).toBe('https://mygls.gls-spain.es/e/4021344762/14007');
  });

  test('sin tracking_url, con codexp + cp_destinatario → construye formato MyGLS', () => {
    const s = { codexp: '4021344762', cp_destinatario: '14007' };
    expect(buildGLSTrackingUrl(s)).toBe('https://mygls.gls-spain.es/e/4021344762/14007');
  });

  test('sin codexp, solo codbarras → fallback moderno /?match=', () => {
    const s = { gls_codbarras: '98765432101234' };
    expect(buildGLSTrackingUrl(s)).toBe(
      'https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/?match=98765432101234',
    );
  });

  test('solo codbarras (campo "codbarras") → fallback moderno', () => {
    const s = { codbarras: '98765432101234' };
    expect(buildGLSTrackingUrl(s)).toBe(
      'https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/?match=98765432101234',
    );
  });

  test('sin nada útil → home MyGLS', () => {
    expect(buildGLSTrackingUrl({})).toBe('https://mygls.gls-spain.es/');
  });

  test('NUNCA devuelve apptracking.asp (URL obsoleta)', () => {
    const inputs = [
      {},
      { gls_codbarras: '123' },
      { codbarras: '456', codexp: '789' },
      { tracking_url: 'https://foo.com' },
      { destinatario: { cp: '28001' } },
    ];
    inputs.forEach((s) => {
      expect(buildGLSTrackingUrl(s)).not.toMatch(/apptracking\.asp/);
    });
  });

  test('encode URL cuando codexp o cp contienen caracteres especiales', () => {
    const s = { gls_codexp: 'abc/def', cp_destinatario: '280 01' };
    const url = buildGLSTrackingUrl(s);
    expect(url).toContain('abc%2Fdef');
    expect(url).toContain('280%2001');
  });
});

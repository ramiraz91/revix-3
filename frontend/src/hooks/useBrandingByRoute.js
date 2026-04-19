import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

// Rutas que pertenecen al CRM privado (Nexora)
const CRM_PREFIXES = [
  '/crm',
  '/login',
  '/dashboard',
  '/master',
  '/forgot-password',
  '/reset-password',
  '/ordenes',
  '/nuevas-ordenes',
  '/clientes',
  '/inventario',
  '/proveedores',
  '/calendario',
  '/notificaciones',
  '/configuracion',
  '/empresa',
  '/usuarios',
  '/scanner',
  '/restos',
  '/incidencias',
  '/analiticas',
  '/ordenes-compra',
  '/iso',
  '/contabilidad',
  '/logistica',
  '/comisiones',
  '/kits',
  '/liquidaciones',
  '/email-config',
  '/etiquetas-envio',
  '/gls-config',
  '/insurama',
  '/agente-aria',
  '/historial-impresion',
  '/buscar-siniestro',
  '/peticiones-exteriores',
  '/faqs-admin',
  '/compras',
];

// Favicon SVG Revix: "R" blanca sobre cuadrado azul #0055FF redondeado
const REVIX_FAVICON =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
      <rect width="64" height="64" rx="14" fill="#0055FF"/>
      <text x="50%" y="50%" dominant-baseline="central" text-anchor="middle"
            font-family="Plus Jakarta Sans, Inter, Arial, sans-serif"
            font-size="40" font-weight="800" fill="#ffffff">R</text>
    </svg>`
  );

// Favicon Nexora (el que ya está en index.html)
const NEXORA_FAVICON =
  'https://customer-assets.emergentagent.com/job_repair-sync/artifacts/5mieqqov_ChatGPT%20Image%2012%20feb%202026%2C%2022_23_32.png';

function isCRMRoute(pathname) {
  return CRM_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

function setFavicon(href) {
  const existing = document.querySelectorAll("link[rel='icon'], link[rel='apple-touch-icon']");
  existing.forEach((el) => el.parentNode.removeChild(el));
  const link = document.createElement('link');
  link.rel = 'icon';
  link.href = href;
  document.head.appendChild(link);
  const apple = document.createElement('link');
  apple.rel = 'apple-touch-icon';
  apple.href = href;
  document.head.appendChild(apple);
}

function setRobots(noindex) {
  let meta = document.querySelector("meta[name='robots']");
  if (!meta) {
    meta = document.createElement('meta');
    meta.name = 'robots';
    document.head.appendChild(meta);
  }
  meta.content = noindex ? 'noindex, nofollow' : 'index, follow';
}

export default function useBrandingByRoute() {
  const { pathname } = useLocation();

  useEffect(() => {
    const isCRM = isCRMRoute(pathname);
    if (isCRM) {
      document.title = 'NEXORA - CRM/ERP';
      setFavicon(NEXORA_FAVICON);
      // El CRM es privado — no debe indexarse ni aparecer en buscadores
      setRobots(true);
    } else {
      document.title = 'Revix.es - Servicio técnico de telefonía móvil';
      setFavicon(REVIX_FAVICON);
      setRobots(false);
    }
  }, [pathname]);
}

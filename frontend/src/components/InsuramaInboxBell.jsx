import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Inbox } from 'lucide-react';
import { insuramaAPI } from '@/lib/api';
import { Badge } from '@/components/ui/badge';

/**
 * Campanita dedicada a mensajes internos Insurama (categoría PROVEEDORES).
 * - Badge naranja con el nº de mensajes NO LEÍDOS del inbox Insurama.
 * - Click → navega a /crm/notificaciones?cat=PROVEEDORES.
 * - Polling cada 60s (complementa el polling 6h del backend).
 * - Escucha `insurama-inbox-updated` para refresco instantáneo.
 */
export default function InsuramaInboxBell({ variant = 'floating' }) {
  const [noLeidas, setNoLeidas] = useState(0);
  const [ordenesConMensajes, setOrdenesConMensajes] = useState(0);

  const fetchCount = async () => {
    try {
      const { data } = await insuramaAPI.inboxResumen();
      setNoLeidas(data?.no_leidas || 0);
      setOrdenesConMensajes(data?.ordenes_con_mensajes || 0);
    } catch {
      // silencio
    }
  };

  useEffect(() => {
    fetchCount();
    const interval = setInterval(fetchCount, 60000);
    const handler = () => fetchCount();
    window.addEventListener('insurama-inbox-updated', handler);
    window.addEventListener('notificaciones-updated', handler);
    return () => {
      clearInterval(interval);
      window.removeEventListener('insurama-inbox-updated', handler);
      window.removeEventListener('notificaciones-updated', handler);
    };
  }, []);

  const pulse = noLeidas > 0;
  const titulo = noLeidas > 0
    ? `${noLeidas} mensajes Insurama sin leer · ${ordenesConMensajes} OT(s) afectada(s)`
    : 'Bandeja Insurama (sin novedades)';

  const base = (
    <Link
      to="/crm/notificaciones?cat=PROVEEDORES"
      data-testid="header-insurama-inbox"
      className={`relative inline-flex items-center justify-center w-10 h-10 rounded-full shadow-md transition-all border
        ${pulse
          ? 'bg-orange-50 border-orange-300 text-orange-700 hover:bg-orange-100 animate-pulse'
          : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50 hover:shadow-lg'}`}
      aria-label={titulo}
      title={titulo}
    >
      <Inbox className="w-5 h-5" />
      {noLeidas > 0 && (
        <Badge
          className="absolute -top-1 -right-1 h-5 min-w-[20px] px-1 rounded-full text-[10px] font-bold leading-none flex items-center justify-center bg-orange-600 hover:bg-orange-600 text-white border-0"
          data-testid="header-insurama-inbox-badge"
        >
          {noLeidas > 99 ? '99+' : noLeidas}
        </Badge>
      )}
    </Link>
  );

  if (variant === 'floating') {
    return (
      <div className="fixed top-4 right-20 z-40 hidden lg:block">
        {base}
      </div>
    );
  }
  return base;
}

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { notificacionesAPI } from '@/lib/api';
import { Badge } from '@/components/ui/badge';

/**
 * Campanita de notificaciones.
 *
 * - Muestra icono con badge del nº de notificaciones NO LEÍDAS (totales).
 * - Click → navega a /crm/notificaciones.
 * - Polling cada 30s + reacciona al evento `notificaciones-updated`
 *   (disparado cuando el usuario marca leídas o por websocket).
 */
export default function NotificacionBell({ variant = 'floating' }) {
  const [noLeidas, setNoLeidas] = useState(0);

  const fetchCount = async () => {
    try {
      const { data } = await notificacionesAPI.contadores();
      setNoLeidas(data?.no_leidas || 0);
    } catch {
      // silent
    }
  };

  useEffect(() => {
    fetchCount();
    const interval = setInterval(fetchCount, 30000);
    const handler = () => fetchCount();
    window.addEventListener('notificaciones-updated', handler);
    window.addEventListener('ws-notification', handler);
    return () => {
      clearInterval(interval);
      window.removeEventListener('notificaciones-updated', handler);
      window.removeEventListener('ws-notification', handler);
    };
  }, []);

  const base = (
    <Link
      to="/crm/notificaciones"
      data-testid="header-bell"
      className="relative inline-flex items-center justify-center w-10 h-10 rounded-full bg-white shadow-md hover:shadow-lg hover:bg-slate-50 text-slate-700 transition-all border border-slate-200"
      aria-label={noLeidas > 0 ? `${noLeidas} notificaciones sin leer` : 'Notificaciones'}
    >
      <Bell className="w-5 h-5" />
      {noLeidas > 0 && (
        <Badge
          variant="destructive"
          className="absolute -top-1 -right-1 h-5 min-w-[20px] px-1 rounded-full text-[10px] font-bold leading-none flex items-center justify-center"
          data-testid="header-bell-badge"
        >
          {noLeidas > 99 ? '99+' : noLeidas}
        </Badge>
      )}
    </Link>
  );

  if (variant === 'floating') {
    return (
      <div className="fixed top-4 right-6 z-40 hidden lg:block">
        {base}
      </div>
    );
  }
  return base;
}

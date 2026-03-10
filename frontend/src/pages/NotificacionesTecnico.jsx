import { Navigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import Notificaciones from './Notificaciones';

// Redirect to Notificaciones - the component already filters by role
export default function NotificacionesTecnico() {
  const { isTecnico } = useAuth();
  
  // Only technicians should access this route
  if (!isTecnico()) {
    return <Navigate to="/notificaciones" replace />;
  }
  
  return <Notificaciones />;
}

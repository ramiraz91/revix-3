import { useState, useEffect } from 'react';
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  ClipboardList, 
  Users, 
  Package, 
  Truck, 
  QrCode, 
  Bell,
  Menu,
  X,
  Smartphone,
  LogOut,
  User,
  Settings,
  Building2,
  Recycle,
  Crown,
  UserCog,
  Calendar,
  Phone,
  PhoneIncoming,
  ShoppingCart,
  AlertTriangle,
  BarChart3,
  ChevronDown,
  DollarSign,
  Shield,
  Receipt,
  ClipboardCheck,
  HelpCircle,
  Bot,
  FileText,
  History
} from 'lucide-react';
import { PackagePlus, Store } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { notificacionesAPI, empresaAPI, getUploadUrl } from '@/lib/api';
import API from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { useWebSocket } from '@/hooks/useWebSocket';
import AsistenteIA from '@/components/AsistenteIA';
import PresupuestoAceptadoPopup from '@/components/PresupuestoAceptadoPopup';

function SidebarGroup({ label, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const hasActiveChild = children?.some?.(child => child?.props?.className?.includes?.('active'));
  
  useEffect(() => {
    if (hasActiveChild) setOpen(true);
  }, [hasActiveChild]);

  return (
    <div className="mb-1">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors"
      >
        {label}
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? '' : '-rotate-90'}`} />
      </button>
      {open && <div className="space-y-0.5">{children}</div>}
    </div>
  );
}

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [notificacionesPendientes, setNotificacionesPendientes] = useState(0);
  const [nuevasOrdenesCount, setNuevasOrdenesCount] = useState(0);
  const [empresaLogo, setEmpresaLogo] = useState(null);
  const [empresaNombre, setEmpresaNombre] = useState('Mi Empresa');
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, isAdmin, isTecnico, isMaster } = useAuth();

  // WebSocket real-time notifications
  const wsToken = user?.token || localStorage.getItem('token');
  const { connected: wsConnected } = useWebSocket(wsToken);

  // Refresh notification count when WS message arrives
  useEffect(() => {
    const handleWsNotification = () => {
      // Re-fetch notification count
      notificacionesAPI.listar(true).then(res => {
        let data = res.data || [];
        if (isTecnico() && user) {
          const TIPOS_TECNICO = ['mensaje_admin', 'orden_desbloqueada', 'orden_asignada', 'material_aprobado'];
          data = data.filter(n => TIPOS_TECNICO.includes(n.tipo) && (!n.usuario_destino || n.usuario_destino === user?.id));
        }
        setNotificacionesPendientes(data.length);
      }).catch(() => {});
    };
    window.addEventListener('ws-notification', handleWsNotification);
    return () => window.removeEventListener('ws-notification', handleWsNotification);
  }, [isTecnico, user]);

  const navItemClass = ({ isActive }) => `nav-item ${isActive ? 'active' : ''}`;

  useEffect(() => {
    const fetchEmpresa = async () => {
      try {
        const res = await empresaAPI.obtener();
        if (res.data) {
          setEmpresaNombre(res.data.nombre || 'Mi Empresa');
          const raw = res.data.logo?.url || res.data.logo_url;
          if (raw) {
            setEmpresaLogo(raw.startsWith('http') ? raw : getUploadUrl(raw));
          }
        }
      } catch (error) {
        // silently fail
      }
    };
    fetchEmpresa();
  }, []);

  useEffect(() => {
    const fetchNotificaciones = async () => {
      try {
        const res = await notificacionesAPI.listar(true);
        let data = res.data || [];
        
        // Si es técnico, filtrar solo las notificaciones permitidas
        if (isTecnico() && user) {
          const TIPOS_TECNICO = [
            'mensaje_admin',
            'orden_desbloqueada',
            'orden_asignada',
            'material_aprobado',
          ];
          data = data.filter(n => {
            const tipoPermitido = TIPOS_TECNICO.includes(n.tipo);
            const esParaMi = !n.usuario_destino || n.usuario_destino === user?.id;
            return tipoPermitido && esParaMi;
          });
        }
        
        setNotificacionesPendientes(data.length);
      } catch (error) {
        console.error('Error fetching notifications:', error);
      }
    };
    
    if (isAdmin() || isTecnico()) {
      fetchNotificaciones();
      // Polling cada 3 minutos (antes era 30s - reducido para mejorar rendimiento)
      const interval = setInterval(fetchNotificaciones, 180000);
      
      const handleUpdate = () => {
        fetchNotificaciones();
      };
      window.addEventListener('notificaciones-updated', handleUpdate);
      
      return () => {
        clearInterval(interval);
        window.removeEventListener('notificaciones-updated', handleUpdate);
      };
    }
  }, [isAdmin, isTecnico, user]);

  // Cargar count de nuevas órdenes
  useEffect(() => {
    const fetchNuevasOrdenes = async () => {
      try {
        const res = await API.get('/nuevas-ordenes/count');
        setNuevasOrdenesCount(res.data?.count || 0);
      } catch { /* silently fail */ }
    };
    if (isAdmin()) {
      fetchNuevasOrdenes();
      const interval = setInterval(fetchNuevasOrdenes, 180000);
      window.addEventListener('ws-notification', fetchNuevasOrdenes);
      return () => {
        clearInterval(interval);
        window.removeEventListener('ws-notification', fetchNuevasOrdenes);
      };
    }
  }, [isAdmin]);

  useEffect(() => {
    setSidebarOpen(false);
  }, [location]);

  const handleLogout = () => {
    logout();
    navigate('/crm/login');
  };

  const NavItem = ({ path, icon: Icon, label, badge }) => (
    <NavLink to={`/crm${path}`} className={navItemClass} data-testid={`nav-${path.slice(1)}`}>
      <Icon className="w-4 h-4" />
      <span className="text-sm">{label}</span>
      {badge && (
        <Badge 
          variant={typeof badge === 'string' ? 'secondary' : 'destructive'} 
          className={`ml-auto text-[10px] h-5 min-w-5 flex items-center justify-center ${typeof badge === 'string' ? 'bg-violet-100 text-violet-700' : ''}`}
        >
          {badge}
        </Badge>
      )}
    </NavLink>
  );

  return (
    <div className="min-h-screen bg-slate-50/50">
      {/* Mobile header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-14 bg-white border-b border-border z-50 flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
          {empresaLogo ? (
            <img src={empresaLogo} alt={empresaNombre} className="h-8 w-auto object-contain" />
          ) : (
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Smartphone className="w-4 h-4 text-white" />
            </div>
          )}
          <span className="font-semibold">{empresaNombre}</span>
        </div>
        <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(!sidebarOpen)} data-testid="mobile-menu-toggle">
          {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </Button>
      </div>

      {/* Overlay */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 bg-black/50 z-40" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside 
        className={`fixed left-0 top-0 h-full w-56 bg-white border-r border-border z-50 transition-transform duration-300 lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        data-testid="sidebar"
      >
        {/* Logo */}
        <div className="h-14 flex items-center gap-2 px-4 border-b border-border">
          {empresaLogo ? (
            <img src={empresaLogo} alt={empresaNombre} className="h-8 w-auto object-contain" />
          ) : (
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Smartphone className="w-4 h-4 text-white" />
            </div>
          )}
          <div>
            <h1 className="font-bold text-sm tracking-tight">{empresaNombre}</h1>
            <p className="text-[9px] text-muted-foreground uppercase tracking-widest">CRM / ERP</p>
          </div>
        </div>

        {/* User info - compact */}
        <div className="px-3 py-2 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
              <User className="w-3.5 h-3.5 text-primary" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="font-medium text-xs truncate">{user?.nombre}</p>
              <Badge variant={isMaster() ? "destructive" : isAdmin() ? "default" : "secondary"} className="text-[9px] h-4">
                {isMaster() ? 'Master' : isAdmin() ? 'Admin' : 'Técnico'}
              </Badge>
            </div>
          </div>
        </div>

        {/* Navigation - grouped & scrollable */}
        <nav className="px-2 py-2 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 170px)' }}>
          {/* Principal - Contenido diferente para técnicos */}
          <SidebarGroup label="Principal" defaultOpen>
            <NavItem path="/dashboard" icon={LayoutDashboard} label="Dashboard" />
            {isAdmin() && <NavItem path="/nuevas-ordenes" icon={PackagePlus} label="Nuevas Órdenes" badge={nuevasOrdenesCount} />}
            <NavItem path="/ordenes" icon={ClipboardList} label="Órdenes de Trabajo" />
            {isAdmin() && <NavItem path="/logistica" icon={Truck} label="Envíos y Recogidas" />}
            {isAdmin() && <NavItem path="/calendario" icon={Calendar} label="Calendario" />}
            <NavItem path="/scanner" icon={QrCode} label="Escáner QR" />
            {isAdmin() && <NavItem path="/incidencias" icon={AlertTriangle} label="Incidencias" />}
            <NavItem path="/notificaciones" icon={Bell} label="Notificaciones" badge={notificacionesPendientes} />
          </SidebarGroup>

          {isAdmin() && (
            <>
              {/* Gestión */}
              <SidebarGroup label="Gestión">
                <NavItem path="/clientes" icon={Users} label="Clientes" />
                <NavItem path="/peticiones-exteriores" icon={PhoneIncoming} label="Peticiones Ext." />
                <NavItem path="/inventario" icon={Package} label="Inventario" />
                <NavItem path="/proveedores" icon={Truck} label="Proveedores" />
                <NavItem path="/compras" icon={FileText} label="Compras" />
                <NavItem path="/ordenes-compra" icon={ShoppingCart} label="Órdenes Compra" />
              </SidebarGroup>

              {/* Operaciones */}
              <SidebarGroup label="Operaciones">
                <NavItem path="/restos" icon={Recycle} label="Restos" />
              </SidebarGroup>

              {/* Comunicaciones */}
              <SidebarGroup label="Comunicaciones">
                <NavItem path="/email-config" icon={Settings} label="Notificaciones Auto" />
              </SidebarGroup>

              {/* Finanzas y Logística */}
              <SidebarGroup label="Finanzas y Logística">
                <NavItem path="/finanzas" icon={BarChart3} label="Finanzas" />
                <NavItem path="/contabilidad" icon={Receipt} label="Facturas y Albaranes" />
                <NavItem path="/comisiones" icon={DollarSign} label="Comisiones" />
                <NavItem path="/etiquetas-envio" icon={Truck} label="Etiquetas Envío" />
                <NavItem path="/gls-config" icon={Truck} label="GLS Config" />
              </SidebarGroup>

              {/* Integraciones */}
              <SidebarGroup label="Integraciones">
                <NavItem path="/buscar-siniestro" icon={Shield} label="Buscar Siniestro" />
                {isMaster() && <NavItem path="/insurama" icon={Settings} label="Config. Insurama" />}
                {isMaster() && <NavItem path="/liquidaciones" icon={Receipt} label="Liquidaciones" />}
              </SidebarGroup>
            </>
          )}
          
          {/* Administración - Master only */}
          {/* Sección Admin (Admin + Master) */}
          {isAdmin() && (
            <SidebarGroup label="Herramientas Admin">
              <NavItem path="/agente-aria" icon={Bot} label="ARIA (IA)" badge="Nuevo" />
            </SidebarGroup>
          )}
          
          {isMaster() && (
            <SidebarGroup label="Administración">
              <NavItem path="/control-cambios" icon={History} label="Control Cambios" />
              <NavItem path="/analiticas" icon={BarChart3} label="Analíticas" />
              <NavItem path="/iso" icon={ClipboardCheck} label="ISO / WISE" />
              <NavItem path="/faqs-admin" icon={HelpCircle} label="FAQs Web" />
              <NavItem path="/usuarios" icon={UserCog} label="Usuarios" />
              <NavItem path="/empresa" icon={Building2} label="Empresa" />
              <NavItem path="/configuracion" icon={Settings} label="Configuración" />
              <NavItem path="/master" icon={Crown} label="Panel Master" />
            </SidebarGroup>
          )}
        </nav>

        {/* Logout */}
        <div className="absolute bottom-0 left-0 right-0 p-2 border-t border-border bg-white">
          <p className="text-[10px] text-muted-foreground text-center mb-1">v1.3.0</p>
          <Button 
            variant="ghost" 
            className="w-full justify-start gap-2 text-muted-foreground hover:text-destructive h-8 text-xs"
            onClick={handleLogout}
            data-testid="logout-btn"
          >
            <LogOut className="w-3.5 h-3.5" />
            Cerrar Sesión
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main className="lg:ml-56 min-h-screen pt-14 lg:pt-0">
        <div className="p-4 lg:p-8">
          <Outlet />
        </div>
      </main>

      {/* Asistente IA flotante */}
      <AsistenteIA />
      
      {/* Popup de presupuesto aceptado */}
      <PresupuestoAceptadoPopup />
    </div>
  );
}

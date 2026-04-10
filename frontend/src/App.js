import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";

// Redirige /seguimiento?codigo=X → /consulta?codigo=X (ahora en raíz)
function SeguimientoRedirect() {
  const location = useLocation();
  return <Navigate to={`/consulta${location.search}`} replace />;
}

// Redirige /web/* → /* (compatibilidad con links antiguos)
function WebRedirect() {
  const location = useLocation();
  const newPath = location.pathname.replace('/web', '') || '/';
  return <Navigate to={`${newPath}${location.search}`} replace />;
}

// Redirige rutas CRM antiguas sin prefijo /crm → /crm/*
function LegacyCRMRedirect() {
  const location = useLocation();
  // Evitar doble /crm si la ruta ya empieza con /crm
  if (location.pathname.startsWith('/crm')) {
    return <Navigate to={`${location.pathname}${location.search}`} replace />;
  }
  return <Navigate to={`/crm${location.pathname}${location.search}`} replace />;
}

import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import Dashboard from "@/pages/Dashboard";
import Ordenes from "@/pages/Ordenes";
import NuevasOrdenes from "@/pages/NuevasOrdenes";
import NuevaOrdenDetalle from "@/pages/NuevaOrdenDetalle";
import OrdenDetalle from "@/pages/OrdenDetalle";
import OrdenTecnico from "@/pages/OrdenTecnico";
import NuevaOrden from "@/pages/NuevaOrden";
import Clientes from "@/pages/Clientes";
import ClienteDetalle from "@/pages/ClienteDetalle";
import Inventario from "@/pages/Inventario";
import Proveedores from "@/pages/Proveedores";
import Compras from "@/pages/Compras";
import Scanner from "@/pages/Scanner";
import Notificaciones from "@/pages/Notificaciones";
import Seguimiento from "@/pages/Seguimiento";
import Configuracion from "@/pages/Configuracion";
import EmpresaConfig from "@/pages/EmpresaConfig";
import PanelMaster from "@/pages/PanelMaster";
import ControlCambios from "@/pages/ControlCambios";
import Restos from "@/pages/Restos";
import Usuarios from "@/pages/Usuarios";
import Calendario from "@/pages/Calendario";
import OrdenesCompra from "@/pages/OrdenesCompra";
import Incidencias from "@/pages/Incidencias";
import Analiticas from "@/pages/Analiticas";
import EmailConfig from "@/pages/EmailConfig";
import GLSConfigPage from "@/pages/GLSConfigPage";
import GLSAdmin from "@/pages/GLSAdmin";
import Comisiones from "@/pages/Comisiones";
import EtiquetasEnvio from "@/pages/EtiquetasEnvio";
import NotificacionesTecnico from "@/pages/NotificacionesTecnico";
import Insurama from "@/pages/Insurama";
// Logistica page removed - replaced by GLSAdmin
import Contabilidad from "@/pages/Contabilidad";
import FinanzasDashboard from "@/pages/FinanzasDashboard";
import FacturaDetalle from "@/pages/FacturaDetalle";
import Modelo347 from "@/pages/Modelo347";
import Kits from "@/pages/Kits";
import BuscarSiniestro from "@/pages/BuscarSiniestro";
import Liquidaciones from "@/pages/Liquidaciones";
import ISOModule from "@/pages/ISOModule";
import PeticionesExteriores from "@/pages/PeticionesExteriores";
import FAQsAdmin from "@/pages/FAQsAdmin";
import AgentARIA from "@/pages/AgentARIA";

// Public website pages
import PublicLayout from "@/components/public/PublicLayout";
import PublicHome from "@/pages/public/PublicHome";
import PublicServicios from "@/pages/public/PublicServicios";
import PublicContacto from "@/pages/public/PublicContacto";
import PublicPresupuesto from "@/pages/public/PublicPresupuesto";
import PublicAseguradoras from "@/pages/public/PublicAseguradoras";
import PublicGarantia from "@/pages/public/PublicGarantia";
import PublicGarantiaExtendida from "@/pages/public/PublicGarantiaExtendida";
import PublicPartners from "@/pages/public/PublicPartners";
import PublicFAQs from "@/pages/public/PublicFAQs";

// Protected Route component
function ProtectedRoute({ children, adminOnly = false, masterOnly = false }) {
  const { user, loading, isAdmin, isMaster } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/crm/login" replace />;
  }
  
  if (masterOnly && !isMaster()) {
    return <Navigate to="/crm/dashboard" replace />;
  }
  
  if (adminOnly && !isAdmin()) {
    return <Navigate to="/crm/dashboard" replace />;
  }
  
  return children;
}

// Route that redirects based on role
function OrdenRoute() {
  const { isTecnico } = useAuth();
  return isTecnico() ? <OrdenTecnico /> : <OrdenDetalle />;
}

function AppRoutes() {
  const { user } = useAuth();
  
  return (
    <Routes>
      {/* ===== WEB PÚBLICA (www.revix.es/) ===== */}
      <Route path="/" element={<PublicLayout />}>
        <Route index element={<PublicHome />} />
        <Route path="servicios" element={<PublicServicios />} />
        <Route path="contacto" element={<PublicContacto />} />
        <Route path="presupuesto" element={<PublicPresupuesto />} />
        <Route path="aseguradoras" element={<PublicAseguradoras />} />
        <Route path="partners" element={<PublicPartners />} />
        <Route path="garantia" element={<PublicGarantia />} />
        <Route path="garantia-extendida" element={<PublicGarantiaExtendida />} />
        <Route path="consulta" element={<Seguimiento />} />
        <Route path="faqs" element={<PublicFAQs />} />
        <Route path="preguntas-frecuentes" element={<PublicFAQs />} />
      </Route>

      {/* Redirecciones de compatibilidad con URLs antiguas */}
      <Route path="/seguimiento" element={<SeguimientoRedirect />} />
      <Route path="/web/*" element={<WebRedirect />} />
      
      {/* Redirecciones de rutas CRM antiguas sin prefijo /crm */}
      <Route path="/dashboard" element={<LegacyCRMRedirect />} />
      <Route path="/ordenes/*" element={<LegacyCRMRedirect />} />
      <Route path="/ordenes" element={<LegacyCRMRedirect />} />
      <Route path="/clientes/*" element={<LegacyCRMRedirect />} />
      <Route path="/clientes" element={<LegacyCRMRedirect />} />
      <Route path="/inventario" element={<LegacyCRMRedirect />} />
      <Route path="/proveedores" element={<LegacyCRMRedirect />} />
      <Route path="/calendario" element={<LegacyCRMRedirect />} />
      <Route path="/notificaciones" element={<LegacyCRMRedirect />} />
      <Route path="/nuevas-ordenes/*" element={<LegacyCRMRedirect />} />
      <Route path="/nuevas-ordenes" element={<LegacyCRMRedirect />} />
      <Route path="/configuracion" element={<LegacyCRMRedirect />} />
      <Route path="/empresa" element={<LegacyCRMRedirect />} />
      <Route path="/usuarios" element={<LegacyCRMRedirect />} />
      <Route path="/scanner" element={<LegacyCRMRedirect />} />
      <Route path="/restos" element={<LegacyCRMRedirect />} />
      <Route path="/incidencias" element={<LegacyCRMRedirect />} />
      <Route path="/master" element={<LegacyCRMRedirect />} />
      <Route path="/analiticas" element={<LegacyCRMRedirect />} />
      <Route path="/ordenes-compra" element={<LegacyCRMRedirect />} />
      <Route path="/iso" element={<LegacyCRMRedirect />} />
      <Route path="/contabilidad/*" element={<LegacyCRMRedirect />} />
      <Route path="/contabilidad" element={<LegacyCRMRedirect />} />
      <Route path="/logistica" element={<LegacyCRMRedirect />} />
      <Route path="/comisiones" element={<LegacyCRMRedirect />} />
      <Route path="/kits" element={<LegacyCRMRedirect />} />
      <Route path="/liquidaciones" element={<LegacyCRMRedirect />} />
      <Route path="/email-config" element={<LegacyCRMRedirect />} />
      <Route path="/etiquetas-envio" element={<LegacyCRMRedirect />} />
      <Route path="/gls-config" element={<LegacyCRMRedirect />} />
      <Route path="/insurama" element={<LegacyCRMRedirect />} />
      <Route path="/agente-aria" element={<LegacyCRMRedirect />} />
      <Route path="/buscar-siniestro" element={<LegacyCRMRedirect />} />
      <Route path="/peticiones-exteriores" element={<LegacyCRMRedirect />} />
      <Route path="/faqs-admin" element={<LegacyCRMRedirect />} />
      <Route path="/compras" element={<LegacyCRMRedirect />} />
      
      {/* ===== CRM (www.revix.es/crm) ===== */}
      <Route path="/crm/login" element={user ? <Navigate to="/crm/dashboard" replace /> : <Login />} />
      <Route path="/crm/forgot-password" element={user ? <Navigate to="/crm/dashboard" replace /> : <ForgotPassword />} />
      <Route path="/crm/reset-password" element={user ? <Navigate to="/crm/dashboard" replace /> : <ResetPassword />} />
      
      {/* Rutas alternativas sin /crm para compatibilidad */}
      <Route path="/login" element={<Navigate to="/crm/login" replace />} />
      <Route path="/forgot-password" element={<Navigate to="/crm/forgot-password" replace />} />
      <Route path="/reset-password" element={<Navigate to="/crm/reset-password" replace />} />
      
      <Route path="/crm" element={
        <ProtectedRoute>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<Navigate to="/crm/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="nuevas-ordenes" element={
          <ProtectedRoute adminOnly>
            <NuevasOrdenes />
          </ProtectedRoute>
        } />
        <Route path="nuevas-ordenes/:id" element={
          <ProtectedRoute adminOnly>
            <NuevaOrdenDetalle />
          </ProtectedRoute>
        } />
        <Route path="ordenes" element={<Ordenes />} />
        <Route path="ordenes/nueva" element={
          <ProtectedRoute adminOnly>
            <NuevaOrden />
          </ProtectedRoute>
        } />
        <Route path="ordenes/:id" element={<OrdenRoute />} />
        <Route path="clientes" element={
          <ProtectedRoute adminOnly>
            <Clientes />
          </ProtectedRoute>
        } />
        <Route path="clientes/:id" element={
          <ProtectedRoute adminOnly>
            <ClienteDetalle />
          </ProtectedRoute>
        } />
        <Route path="inventario" element={
          <ProtectedRoute adminOnly>
            <Inventario />
          </ProtectedRoute>
        } />
        <Route path="proveedores" element={
          <ProtectedRoute adminOnly>
            <Proveedores />
          </ProtectedRoute>
        } />
        <Route path="compras" element={
          <ProtectedRoute adminOnly>
            <Compras />
          </ProtectedRoute>
        } />
        <Route path="scanner" element={<Scanner />} />
        <Route path="notificaciones" element={
          <ProtectedRoute>
            <Notificaciones />
          </ProtectedRoute>
        } />
        <Route path="configuracion" element={
          <ProtectedRoute masterOnly>
            <Configuracion />
          </ProtectedRoute>
        } />
        <Route path="empresa" element={
          <ProtectedRoute masterOnly>
            <EmpresaConfig />
          </ProtectedRoute>
        } />
        <Route path="restos" element={
          <ProtectedRoute adminOnly>
            <Restos />
          </ProtectedRoute>
        } />
        <Route path="usuarios" element={
          <ProtectedRoute masterOnly>
            <Usuarios />
          </ProtectedRoute>
        } />
        <Route path="calendario" element={
          <ProtectedRoute adminOnly>
            <Calendario />
          </ProtectedRoute>
        } />
        <Route path="iso" element={
          <ProtectedRoute adminOnly>
            <ISOModule />
          </ProtectedRoute>
        } />
        <Route path="ordenes-compra" element={
          <ProtectedRoute adminOnly>
            <OrdenesCompra />
          </ProtectedRoute>
        } />
        <Route path="incidencias" element={
          <ProtectedRoute adminOnly>
            <Incidencias />
          </ProtectedRoute>
        } />
        <Route path="master" element={
          <ProtectedRoute masterOnly>
            <PanelMaster />
          </ProtectedRoute>
        } />
        <Route path="control-cambios" element={
          <ProtectedRoute masterOnly>
            <ControlCambios />
          </ProtectedRoute>
        } />
        <Route path="analiticas" element={
          <ProtectedRoute masterOnly>
            <Analiticas />
          </ProtectedRoute>
        } />
        <Route path="email-config" element={
          <ProtectedRoute adminOnly>
            <EmailConfig />
          </ProtectedRoute>
        } />
        <Route path="gls-config" element={
          <ProtectedRoute adminOnly>
            <GLSConfigPage />
          </ProtectedRoute>
        } />
        <Route path="comisiones" element={
          <ProtectedRoute adminOnly>
            <Comisiones />
          </ProtectedRoute>
        } />
        <Route path="etiquetas-envio" element={
          <ProtectedRoute adminOnly>
            <EtiquetasEnvio />
          </ProtectedRoute>
        } />
        <Route path="insurama" element={
          <ProtectedRoute masterOnly>
            <Insurama />
          </ProtectedRoute>
        } />
        <Route path="peticiones-exteriores" element={
          <ProtectedRoute adminOnly>
            <PeticionesExteriores />
          </ProtectedRoute>
        } />
        <Route path="faqs-admin" element={
          <ProtectedRoute masterOnly>
            <FAQsAdmin />
          </ProtectedRoute>
        } />
        <Route path="agente-aria" element={
          <ProtectedRoute adminOnly>
            <AgentARIA />
          </ProtectedRoute>
        } />
        <Route path="liquidaciones" element={
          <ProtectedRoute masterOnly>
            <Liquidaciones />
          </ProtectedRoute>
        } />
        <Route path="buscar-siniestro" element={
          <ProtectedRoute adminOnly>
            <BuscarSiniestro />
          </ProtectedRoute>
        } />
        <Route path="logistica" element={
          <ProtectedRoute adminOnly>
            <GLSAdmin />
          </ProtectedRoute>
        } />
        <Route path="contabilidad" element={
          <ProtectedRoute adminOnly>
            <Contabilidad />
          </ProtectedRoute>
        } />
        <Route path="finanzas" element={
          <ProtectedRoute adminOnly>
            <FinanzasDashboard />
          </ProtectedRoute>
        } />
        <Route path="contabilidad/factura/:id" element={
          <ProtectedRoute adminOnly>
            <FacturaDetalle />
          </ProtectedRoute>
        } />
        <Route path="contabilidad/informe/modelo347" element={
          <ProtectedRoute adminOnly>
            <Modelo347 />
          </ProtectedRoute>
        } />
        <Route path="kits" element={
          <ProtectedRoute adminOnly>
            <Kits />
          </ProtectedRoute>
        } />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster position="top-right" richColors />
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;

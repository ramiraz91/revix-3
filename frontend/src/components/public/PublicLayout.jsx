import { useState, useEffect } from 'react';
import { Outlet, Link, NavLink, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Menu, X, MessageCircle, Mail, MapPin, ArrowRight, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import ChatBot from './ChatBot';

const navLinks = [
  { path: '/web', label: 'Inicio', exact: true },
  { path: '/web/servicios', label: 'Servicios' },
  { path: '/web/partners', label: 'Partners' },
  { path: '/web/aseguradoras', label: 'Aseguradoras' },
  { path: '/web/contacto', label: 'Contacto' },
];

export default function PublicLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    setMenuOpen(false);
  }, [location]);

  return (
    <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }} className="min-h-screen bg-white text-[#0F172A]">

      {/* Navbar */}
      <header className={`fixed top-0 left-0 right-0 z-40 transition-all duration-300 ${scrolled ? 'bg-white/95 backdrop-blur-sm border-b border-slate-100 shadow-sm' : 'bg-white'}`}>
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">

          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl md:text-3xl font-bold tracking-tight text-[#0F172A]">
              Revix<span className="text-[#0055FF]">.</span>es
            </span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <NavLink
                key={link.path}
                to={link.path}
                end={link.exact}
                className={({ isActive }) =>
                  `px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150 ${
                    isActive
                      ? 'text-[#0055FF] bg-blue-50'
                      : 'text-slate-600 hover:text-[#0F172A] hover:bg-slate-50'
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>

          {/* CTA buttons */}
          <div className="hidden md:flex items-center gap-3">
            <Link
              to="/consulta"
              className="text-sm font-medium text-slate-600 hover:text-[#0F172A] transition-colors px-3 py-2"
            >
              Mi reparación
            </Link>
            <Link
              to="/presupuesto"
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0055FF] text-white rounded-lg text-sm font-semibold hover:bg-[#0044DD] transition-colors"
            >
              Pedir presupuesto
              <ChevronRight size={14} />
            </Link>
          </div>

          {/* Mobile toggle */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden p-2 rounded-lg hover:bg-slate-100 transition-colors"
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Mobile menu */}
        <AnimatePresence>
          {menuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="md:hidden border-t border-slate-100 bg-white"
            >
              <div className="max-w-6xl mx-auto px-6 py-4 flex flex-col gap-1">
                {navLinks.map((link) => (
                  <NavLink
                    key={link.path}
                    to={link.path}
                    end={link.exact}
                    className={({ isActive }) =>
                      `px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                        isActive ? 'text-[#0055FF] bg-blue-50' : 'text-slate-700 hover:bg-slate-50'
                      }`
                    }
                  >
                    {link.label}
                  </NavLink>
                ))}
                <div className="pt-3 border-t border-slate-100 mt-2 flex flex-col gap-2">
                  <Link to="/consulta" className="px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 rounded-lg">
                    Consultar mi reparación
                  </Link>
                  <Link to="/presupuesto" className="px-4 py-3 bg-[#0055FF] text-white rounded-lg text-sm font-semibold text-center">
                    Pedir presupuesto gratis
                  </Link>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </header>

      {/* Page content */}
      <main className="pt-16">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-[#0F172A] text-slate-400 mt-24">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-10">
            {/* Brand */}
            <div className="md:col-span-1">
              <span className="text-xl font-bold text-white">
                Revix<span className="text-[#0055FF]">.</span>es
              </span>
              <p className="mt-3 text-sm text-slate-400 leading-relaxed">
                Servicio técnico especializado. Certificación WISE y estándares ACS.
              </p>
              <div className="mt-4 space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <Mail size={14} className="text-slate-500 flex-shrink-0" />
                  <a href="mailto:help@revix.es" className="hover:text-white transition-colors">help@revix.es</a>
                </div>
                <div className="flex items-start gap-2">
                  <MapPin size={14} className="text-slate-500 flex-shrink-0 mt-0.5" />
                  <span>Cobertura Nacional<br />Toda España</span>
                </div>
              </div>
            </div>

            {/* Servicios */}
            <div>
              <h4 className="text-white text-sm font-semibold mb-4">Servicios</h4>
              <ul className="space-y-2.5 text-sm">
                {['Smartphones', 'Tablets', 'Smartwatches', 'Consolas', 'Microsoladura'].map(s => (
                  <li key={s}>
                    <Link to="/servicios" className="hover:text-white transition-colors">{s}</Link>
                  </li>
                ))}
              </ul>
            </div>

            {/* Empresa */}
            <div>
              <h4 className="text-white text-sm font-semibold mb-4">Empresa</h4>
              <ul className="space-y-2.5 text-sm">
                <li><Link to="/garantia" className="hover:text-white transition-colors">Garantía 6 meses</Link></li>
                <li><Link to="/garantia-extendida" className="hover:text-white transition-colors">Garantía extendida</Link></li>
                <li><Link to="/aseguradoras" className="hover:text-white transition-colors">Para aseguradoras</Link></li>
                <li><Link to="/contacto" className="hover:text-white transition-colors">Contacto</Link></li>
              </ul>
            </div>

            {/* Clientes */}
            <div>
              <h4 className="text-white text-sm font-semibold mb-4">Clientes</h4>
              <ul className="space-y-2.5 text-sm">
                <li><Link to="/consulta" className="hover:text-white transition-colors">Consultar reparación</Link></li>
                <li><Link to="/presupuesto" className="hover:text-white transition-colors">Pedir presupuesto</Link></li>
                <li><Link to="/faqs" className="hover:text-white transition-colors">Preguntas frecuentes</Link></li>
              </ul>
              <div className="mt-6">
                <Link
                  to="/presupuesto"
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0055FF] text-white rounded-lg text-sm font-semibold hover:bg-[#0044DD] transition-colors"
                >
                  Presupuesto gratis
                  <ArrowRight size={14} />
                </Link>
              </div>
            </div>
          </div>

          <div className="mt-12 pt-8 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
            <p>© {new Date().getFullYear()} Revix.es · Todos los derechos reservados</p>
            <p>Servicio a toda España</p>
          </div>
        </div>
      </footer>

      {/* Chatbot flotante */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
        <AnimatePresence>
          {chatOpen && <ChatBot onClose={() => setChatOpen(false)} />}
        </AnimatePresence>
        <motion.button
          onClick={() => setChatOpen(!chatOpen)}
          data-testid="chatbot-toggle"
          className={`w-13 h-13 rounded-full flex items-center justify-center shadow-lg transition-colors ${chatOpen ? 'bg-slate-700' : 'bg-[#0055FF]'}`}
          style={{ width: 52, height: 52 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          {chatOpen ? <X size={20} className="text-white" /> : <MessageCircle size={20} className="text-white" />}
        </motion.button>
      </div>
    </div>
  );
}

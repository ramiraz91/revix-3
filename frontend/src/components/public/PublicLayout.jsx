import { useState, useEffect } from 'react';
import { Outlet, Link, NavLink, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Menu, X, ArrowUpRight } from 'lucide-react';
import Logo from './Logo';
import FloatingChat from './FloatingChat';

const navLinks = [
  { path: '/', label: 'Inicio', end: true },
  { path: '/servicios', label: 'Servicios' },
  { path: '/partners', label: 'Partners' },
  { path: '/aseguradoras', label: 'Aseguradoras' },
  { path: '/faqs', label: 'Ayuda' },
];

const footerCols = [
  {
    title: 'Servicios',
    links: [
      { label: 'Reparación de móvil', to: '/servicios' },
      { label: 'Pedir presupuesto', to: '/presupuesto' },
      { label: 'Seguimiento', to: '/consulta' },
      { label: 'Garantía', to: '/garantia' },
    ],
  },
  {
    title: 'Empresa',
    links: [
      { label: 'Aseguradoras', to: '/aseguradoras' },
      { label: 'Partners', to: '/partners' },
      { label: 'Contacto', to: '/contacto' },
    ],
  },
  {
    title: 'Soporte',
    links: [
      { label: 'Preguntas frecuentes', to: '/faqs' },
      { label: 'Garantía extendida', to: '/garantia-extendida' },
      { label: 'Marca y logos', to: '/marca' },
    ],
  },
];

export default function PublicLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    setMenuOpen(false);
    window.scrollTo(0, 0);
  }, [location]);

  return (
    <div className="min-h-screen bg-white text-[#111111] antialiased" style={{ fontFamily: "'Inter', 'Plus Jakarta Sans', system-ui, sans-serif" }}>
      {/* ═══════════ HEADER ═══════════ */}
      <header
        className={`fixed top-0 inset-x-0 z-40 transition-all duration-300 ${
          scrolled
            ? 'bg-white/75 backdrop-blur-xl border-b border-[#E5E5EA]/60'
            : 'bg-transparent'
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 h-16 sm:h-20 flex items-center justify-between">
          <Logo size="md" />

          <nav className="hidden lg:flex items-center gap-1">
            {navLinks.map((link) => (
              <NavLink
                key={link.path}
                to={link.path}
                end={link.end}
                className={({ isActive }) =>
                  `px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                    isActive
                      ? 'text-[#0055FF]'
                      : 'text-[#3A3A3C] hover:text-[#111111]'
                  }`
                }
                data-testid={`nav-${link.label.toLowerCase()}`}
              >
                {link.label}
              </NavLink>
            ))}
          </nav>

          <div className="hidden lg:flex items-center gap-3">
            <Link
              to="/consulta"
              className="text-sm font-medium text-[#3A3A3C] hover:text-[#111111] px-3 py-2"
              data-testid="nav-seguimiento"
            >
              Mi reparación
            </Link>
            <Link
              to="/presupuesto"
              className="inline-flex items-center gap-1.5 bg-[#0055FF] text-white text-sm font-semibold rounded-full px-5 py-2.5 hover:bg-[#0044CC] transition-colors"
              data-testid="nav-cta-presupuesto"
            >
              Pedir presupuesto
              <ArrowUpRight className="w-3.5 h-3.5" strokeWidth={2.5} />
            </Link>
          </div>

          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label="Abrir menú"
            className="lg:hidden w-10 h-10 inline-flex items-center justify-center rounded-full hover:bg-[#F5F5F7]"
            data-testid="mobile-menu-toggle"
          >
            {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        <AnimatePresence>
          {menuOpen && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
              className="lg:hidden bg-white border-t border-[#E5E5EA]"
            >
              <div className="px-6 py-6 space-y-1">
                {navLinks.map((link) => (
                  <NavLink
                    key={link.path}
                    to={link.path}
                    end={link.end}
                    className={({ isActive }) =>
                      `block px-4 py-3 rounded-xl text-base font-medium ${
                        isActive ? 'bg-[#F5F5F7] text-[#0055FF]' : 'text-[#111111] hover:bg-[#F5F5F7]'
                      }`
                    }
                  >
                    {link.label}
                  </NavLink>
                ))}
                <div className="pt-3 flex flex-col gap-2">
                  <Link
                    to="/consulta"
                    className="w-full text-center px-4 py-3 rounded-full bg-[#F5F5F7] font-semibold text-[#111111]"
                  >
                    Mi reparación
                  </Link>
                  <Link
                    to="/presupuesto"
                    className="w-full text-center px-4 py-3 rounded-full bg-[#0055FF] text-white font-semibold"
                  >
                    Pedir presupuesto
                  </Link>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </header>

      {/* ═══════════ MAIN ═══════════ */}
      <main>
        <Outlet />
      </main>

      {/* ═══════════ FOOTER ═══════════ */}
      <footer className="bg-[#F5F5F7] border-t border-[#E5E5EA]">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 py-20">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
            <div className="lg:col-span-4">
              <Logo size="md" />
              <p className="mt-4 text-sm font-semibold text-[#0055FF] tracking-tight">
                Repara. Reutiliza. Recicla.
              </p>
              <p className="mt-4 text-sm text-[#6E6E73] max-w-xs leading-relaxed">
                Servicio técnico especializado en reparación de telefonía móvil. Más de 10 años dando una segunda vida a tus dispositivos.
              </p>
            </div>
            {footerCols.map((col) => (
              <div key={col.title} className="lg:col-span-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#111111] mb-4">{col.title}</p>
                <ul className="space-y-3">
                  {col.links.map((l) => (
                    <li key={l.to}>
                      <Link to={l.to} className="text-sm text-[#6E6E73] hover:text-[#111111] transition-colors">
                        {l.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            <div className="lg:col-span-2">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#111111] mb-4">Contacto</p>
              <ul className="space-y-3 text-sm text-[#6E6E73]">
                <li>
                  <a href="mailto:help@revix.es" className="hover:text-[#111111] transition-colors">
                    help@revix.es
                  </a>
                </li>
                <li>España</li>
              </ul>
            </div>
          </div>

          <div className="mt-16 pt-8 border-t border-[#E5E5EA] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs text-[#6E6E73]">
            <p>© {new Date().getFullYear()} Revix.es · Todos los derechos reservados</p>
            <div className="flex items-center gap-6">
              <Link to="/garantia" className="hover:text-[#111111]">Garantía</Link>
              <Link to="/faqs" className="hover:text-[#111111]">Ayuda</Link>
            </div>
          </div>
        </div>
      </footer>

      <FloatingChat />
    </div>
  );
}

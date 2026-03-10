import { useRef, useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion, useInView, AnimatePresence } from 'framer-motion';
import {
  Smartphone, Tablet, Watch, Gamepad2,
  Shield, Clock, Award, Cpu,
  ArrowRight, CheckCircle2, Star, Quote,
  ChevronRight, Wrench, Zap
} from 'lucide-react';

// Animación de entrada por sección
function Reveal({ children, delay = 0, className = '' }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-60px' });
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 24 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay, ease: [0.25, 0.1, 0.25, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// Eslogan animado: Repara, Recicla, Reutiliza
function AnimatedSlogan() {
  const words = ['Repara', 'Recicla', 'Reutiliza'];
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % words.length);
    }, 1800); // Más rápido: 1.8 segundos
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="py-8 md:py-10 overflow-hidden">
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex flex-col md:flex-row items-center justify-center gap-3 md:gap-5">
          <span className="text-base md:text-lg font-bold uppercase tracking-widest text-slate-600">
            Nuestra filosofía
          </span>
          <div className="relative h-14 md:h-16 flex items-center justify-center min-w-[260px] md:min-w-[340px]">
            <AnimatePresence mode="wait">
              <motion.span
                key={currentIndex}
                initial={{ opacity: 0, y: 24, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -24, scale: 0.95 }}
                transition={{ 
                  duration: 0.4, 
                  ease: [0.25, 0.1, 0.25, 1]
                }}
                className="absolute text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight"
                style={{
                  background: 'linear-gradient(135deg, #84CC16 0%, #A3E635 30%, #BEF264 50%, #84CC16 70%, #65A30D 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                  textShadow: '0 4px 24px rgba(132, 204, 22, 0.2)',
                }}
              >
                {words[currentIndex]}
              </motion.span>
            </AnimatePresence>
          </div>
        </div>
        {/* Indicadores de progreso */}
        <div className="flex items-center justify-center gap-2 mt-4">
          {words.map((word, idx) => (
            <motion.div
              key={word}
              className="h-1.5 rounded-full transition-all duration-300"
              style={{
                width: idx === currentIndex ? '32px' : '8px',
                background: idx === currentIndex 
                  ? 'linear-gradient(90deg, #84CC16, #A3E635)' 
                  : '#E2E8F0',
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function PublicHome() {
  return (
    <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }} className="bg-white text-[#0F172A]">

      {/* ESLOGAN ANIMADO - Visible inmediatamente */}
      <AnimatedSlogan />

      {/* HERO */}
      <section className="max-w-6xl mx-auto px-6 pt-8 pb-24 md:pt-12 md:pb-32">
        <div className="max-w-3xl">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-100 rounded-full text-xs font-semibold text-[#0055FF] mb-6"
          >
            <span className="w-1.5 h-1.5 bg-[#0055FF] rounded-full" />
            Certificación WISE · Estándares ACS
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-5xl md:text-6xl font-bold tracking-tight text-[#0F172A] leading-[1.1] mb-6"
          >
            Reparamos lo que otros<br />
            <span className="text-[#0055FF]">no pueden.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-lg text-slate-500 leading-relaxed mb-8 max-w-xl"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            Servicio técnico especializado a nivel nacional. Recogemos tu dispositivo en cualquier punto de España con reparación express y garantía de 6 meses.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex flex-wrap items-center gap-3"
          >
            <Link
              to="/presupuesto"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#0055FF] text-white rounded-lg text-sm font-semibold hover:bg-[#0044DD] transition-colors shadow-sm shadow-blue-200"
            >
              Pedir presupuesto gratis
              <ArrowRight size={16} />
            </Link>
            <Link
              to="/consulta"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-white border border-slate-200 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition-colors"
            >
              Consultar mi reparación
            </Link>
          </motion.div>

          {/* Stats en línea */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="flex flex-wrap gap-8 mt-12 pt-10 border-t border-slate-100"
          >
            {[
              { value: '+5.000', label: 'Reparaciones' },
              { value: '98%', label: 'Satisfacción' },
              { value: '6 meses', label: 'Garantía' },
              { value: '+8 años', label: 'Experiencia' },
            ].map((s) => (
              <div key={s.label}>
                <p className="text-2xl font-bold text-[#0F172A]">{s.value}</p>
                <p className="text-sm text-slate-400 mt-0.5" style={{ fontFamily: "'Inter', sans-serif" }}>{s.label}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* PROCESO DE REPARACIÓN */}
      <section className="bg-gradient-to-b from-[#0055FF] to-[#003ACC] text-white">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <Reveal>
            <div className="text-center mb-16">
              <p className="text-xs font-semibold uppercase tracking-widest text-blue-200 mb-2">Cómo funciona</p>
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">Tu dispositivo reparado en 72 horas*</h2>
              <p className="text-blue-100 text-lg max-w-2xl mx-auto">
                Recogemos en tu casa, reparamos con piezas a tu elección y devolvemos tu dispositivo como nuevo
              </p>
            </div>
          </Reveal>

          {/* Timeline del proceso */}
          <div className="grid md:grid-cols-4 gap-6 md:gap-4">
            {[
              {
                step: '1',
                title: 'Solicita recogida',
                desc: 'Pide presupuesto online y programamos la recogida en tu domicilio sin coste adicional',
                icon: '📦'
              },
              {
                step: '2',
                title: 'Elige tus piezas',
                desc: 'Tú decides: piezas originales para máxima calidad o compatibles para mejor precio',
                icon: '⚙️'
              },
              {
                step: '3',
                title: 'Reparación express',
                desc: 'Nuestros técnicos certificados reparan tu dispositivo con la máxima calidad',
                icon: '🔧'
              },
              {
                step: '4',
                title: 'Devolución rápida',
                desc: 'Te devolvemos el dispositivo reparado a domicilio con 6 meses de garantía',
                icon: '🚀'
              }
            ].map((item, i) => (
              <Reveal key={i} delay={i * 0.1}>
                <div className="relative bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-6 h-full">
                  {/* Número de paso */}
                  <div className="absolute -top-4 left-6 w-8 h-8 bg-white text-[#0055FF] rounded-full flex items-center justify-center font-bold text-sm shadow-lg">
                    {item.step}
                  </div>
                  
                  {/* Icono */}
                  <div className="text-4xl mb-4 mt-2">{item.icon}</div>
                  
                  {/* Contenido */}
                  <h3 className="font-bold text-lg mb-2">{item.title}</h3>
                  <p className="text-blue-100 text-sm leading-relaxed">{item.desc}</p>
                  
                  {/* Flecha conectora (solo en desktop, no en último) */}
                  {i < 3 && (
                    <div className="hidden md:block absolute top-1/2 -right-4 transform -translate-y-1/2 text-white/40">
                      <ChevronRight size={24} />
                    </div>
                  )}
                </div>
              </Reveal>
            ))}
          </div>

          {/* Destacado: Tú eliges */}
          <Reveal delay={0.4}>
            <div className="mt-12 bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-8 md:flex md:items-center md:justify-between gap-8">
              <div className="mb-6 md:mb-0">
                <h3 className="font-bold text-xl mb-2 flex items-center gap-2">
                  <span className="text-2xl">✨</span> Tú eliges el tipo de pieza
                </h3>
                <p className="text-blue-100">
                  <strong className="text-white">Originales:</strong> Máxima calidad y durabilidad certificada<br/>
                  <strong className="text-white">Compatibles:</strong> Excelente relación calidad-precio con garantía
                </p>
              </div>
              <Link 
                to="/presupuesto" 
                className="inline-flex items-center gap-2 px-6 py-3 bg-white text-[#0055FF] rounded-xl font-semibold hover:bg-blue-50 transition-colors whitespace-nowrap"
              >
                Pedir presupuesto gratis <ArrowRight size={18} />
              </Link>
            </div>
          </Reveal>

          {/* Nota 72h */}
          <p className="text-center text-blue-200 text-xs mt-8">
            *El tiempo de 72 horas aplica a reparaciones estándar con disponibilidad de piezas. 
            Algunas reparaciones pueden requerir más tiempo según la complejidad y disponibilidad.
          </p>
        </div>
      </section>

      {/* SERVICIOS */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <Reveal>
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-12">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-[#0055FF] mb-2">Qué reparamos</p>
              <h2 className="text-3xl font-bold tracking-tight text-[#0F172A]">Todo tipo de dispositivos</h2>
            </div>
            <Link to="/servicios" className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-500 hover:text-[#0055FF] transition-colors">
              Ver todos los servicios <ChevronRight size={14} />
            </Link>
          </div>
        </Reveal>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { icon: Smartphone, label: 'Smartphones', desc: 'iPhone, Samsung, Xiaomi y todas las marcas' },
            { icon: Tablet, label: 'Tablets', desc: 'iPad, Samsung Tab, Huawei y más' },
            { icon: Watch, label: 'Smartwatches', desc: 'Apple Watch, Galaxy Watch, Garmin' },
            { icon: Gamepad2, label: 'Consolas', desc: 'Nintendo Switch, Steam Deck' },
          ].map((item, i) => (
            <Reveal key={i} delay={i * 0.08}>
              <Link to="/servicios" className="group block p-6 border border-slate-100 rounded-xl hover:border-slate-200 hover:shadow-sm transition-all duration-200 bg-white">
                <div className="w-10 h-10 bg-slate-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-blue-50 transition-colors">
                  <item.icon size={20} className="text-slate-500 group-hover:text-[#0055FF] transition-colors" />
                </div>
                <h3 className="font-semibold text-[#0F172A] mb-1">{item.label}</h3>
                <p className="text-sm text-slate-400 leading-snug" style={{ fontFamily: "'Inter', sans-serif" }}>{item.desc}</p>
              </Link>
            </Reveal>
          ))}
        </div>
      </section>

      {/* POR QUÉ REVIX - bento */}
      <section className="bg-slate-50 border-y border-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <Reveal>
            <p className="text-xs font-semibold uppercase tracking-widest text-[#0055FF] mb-2">Por qué elegirnos</p>
            <h2 className="text-3xl font-bold tracking-tight text-[#0F172A] mb-12">Calidad que se certifica</h2>
          </Reveal>

          <div className="grid md:grid-cols-3 gap-4">
            <Reveal delay={0.05} className="md:col-span-1">
              <div className="h-full bg-white border border-slate-100 rounded-xl p-6">
                <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center mb-4">
                  <Award size={20} className="text-[#0055FF]" />
                </div>
                <h3 className="font-semibold text-[#0F172A] mb-2">Certificación WISE</h3>
                <p className="text-sm text-slate-500 leading-relaxed" style={{ fontFamily: "'Inter', sans-serif" }}>
                  Técnicos certificados con los más altos estándares internacionales del sector de la reparación.
                </p>
              </div>
            </Reveal>

            <Reveal delay={0.1} className="md:col-span-1">
              <div className="h-full bg-white border border-slate-100 rounded-xl p-6">
                <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center mb-4">
                  <Shield size={20} className="text-[#0055FF]" />
                </div>
                <h3 className="font-semibold text-[#0F172A] mb-2">Estándares ACS</h3>
                <p className="text-sm text-slate-500 leading-relaxed" style={{ fontFamily: "'Inter', sans-serif" }}>
                  Cada reparación sigue protocolos de calidad ACS para garantizar resultados óptimos y duraderos.
                </p>
              </div>
            </Reveal>

            <Reveal delay={0.15} className="md:col-span-1">
              <div className="h-full bg-white border border-slate-100 rounded-xl p-6">
                <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center mb-4">
                  <Cpu size={20} className="text-[#0055FF]" />
                </div>
                <h3 className="font-semibold text-[#0F172A] mb-2">Microsoladura BGA</h3>
                <p className="text-sm text-slate-500 leading-relaxed" style={{ fontFamily: "'Inter', sans-serif" }}>
                  Reparaciones a nivel de componente que otros talleres no aceptan. Equipo especializado de última generación.
                </p>
              </div>
            </Reveal>

            <Reveal delay={0.05} className="md:col-span-2">
              <div className="h-full bg-[#0055FF] rounded-xl p-8 text-white">
                <Zap size={24} className="text-blue-200 mb-4" />
                <h3 className="text-xl font-bold mb-2">Las reparaciones más difíciles son nuestra especialidad</h3>
                <p className="text-blue-100 text-sm leading-relaxed mb-6" style={{ fontFamily: "'Inter', sans-serif" }}>
                  Contamos con equipamiento de microsoladura de última generación para reparaciones a nivel de componente: placa base, Face ID, Touch ID, recuperación de datos y daños graves por agua.
                </p>
                <ul className="grid grid-cols-2 gap-2 mb-6">
                  {[
                    'Placa base (BGA)', 'Face ID / Touch ID',
                    'Recuperación de datos', 'Daños por agua',
                    'Cámaras OIS', 'Problemas de red',
                  ].map((item) => (
                    <li key={item} className="flex items-center gap-1.5 text-sm text-blue-100" style={{ fontFamily: "'Inter', sans-serif" }}>
                      <CheckCircle2 size={13} className="text-blue-300 flex-shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
                <Link to="/presupuesto" className="inline-flex items-center gap-1.5 px-4 py-2 bg-white text-[#0055FF] rounded-lg text-sm font-semibold hover:bg-blue-50 transition-colors">
                  Solicitar presupuesto <ArrowRight size={14} />
                </Link>
              </div>
            </Reveal>

            <Reveal delay={0.1}>
              <div className="h-full bg-white border border-slate-100 rounded-xl p-6 flex flex-col justify-between">
                <div>
                  <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center mb-4">
                    <Clock size={20} className="text-[#0055FF]" />
                  </div>
                  <h3 className="font-semibold text-[#0F172A] mb-2">Servicio rápido</h3>
                  <p className="text-sm text-slate-500 leading-relaxed" style={{ fontFamily: "'Inter', sans-serif" }}>
                    La mayoría de reparaciones habituales se resuelven en el mismo día de entrega.
                  </p>
                </div>
                <div className="mt-6 pt-4 border-t border-slate-100">
                  <p className="text-xs text-slate-400" style={{ fontFamily: "'Inter', sans-serif" }}>Horario de taller</p>
                  <p className="text-sm font-medium text-slate-700 mt-1">L–V: 10–14h / 17–20h</p>
                  <p className="text-sm text-slate-500">Sáb: 10–14h</p>
                </div>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* GARANTÍA banner */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <Reveal>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 p-8 border border-slate-200 rounded-2xl">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center flex-shrink-0">
                <Wrench size={22} className="text-[#0055FF]" />
              </div>
              <div>
                <h3 className="font-semibold text-[#0F172A]">Garantía de 6 meses en todas las reparaciones</h3>
                <p className="text-sm text-slate-500 mt-1" style={{ fontFamily: "'Inter', sans-serif" }}>
                  Si la reparación falla en los 6 meses siguientes por el mismo motivo, la repetimos sin coste.
                </p>
              </div>
            </div>
            <Link to="/garantia" className="flex-shrink-0 inline-flex items-center gap-1.5 text-sm font-semibold text-[#0055FF] hover:gap-2.5 transition-all">
              Saber más <ChevronRight size={14} />
            </Link>
          </div>
        </Reveal>
      </section>

      {/* ASEGURADORAS */}
      <section className="bg-slate-50 border-y border-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <Reveal>
              <p className="text-xs font-semibold uppercase tracking-widest text-[#0055FF] mb-2">Colaboradores</p>
              <h2 className="text-3xl font-bold tracking-tight text-[#0F172A] mb-4">
                Servicio técnico de confianza para aseguradoras
              </h2>
              <p className="text-slate-500 text-sm leading-relaxed mb-6" style={{ fontFamily: "'Inter', sans-serif" }}>
                Colaboramos con compañías aseguradoras para gestionar siniestros de dispositivos móviles con agilidad, transparencia y los más altos estándares de calidad.
              </p>
              <ul className="space-y-3 mb-8">
                {[
                  'Gestión ágil de siniestros',
                  'Informes técnicos detallados',
                  'Presupuestos ajustados al mercado',
                  'Portal de seguimiento en tiempo real',
                ].map((item) => (
                  <li key={item} className="flex items-center gap-2.5 text-sm text-slate-600" style={{ fontFamily: "'Inter', sans-serif" }}>
                    <CheckCircle2 size={15} className="text-[#0055FF] flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
              <Link to="/aseguradoras" className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#0055FF] hover:gap-2.5 transition-all">
                Información para aseguradoras <ChevronRight size={14} />
              </Link>
            </Reveal>

            <Reveal delay={0.1}>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { value: '+5.000', label: 'Reparaciones', sub: 'completadas' },
                  { value: '98%', label: 'Satisfacción', sub: 'cliente' },
                  { value: '<24h', label: 'Presupuesto', sub: 'garantizado' },
                  { value: '6 meses', label: 'Garantía', sub: 'en toda reparación' },
                ].map((stat) => (
                  <div key={stat.label} className="bg-white border border-slate-100 rounded-xl p-5">
                    <p className="text-2xl font-bold text-[#0F172A]">{stat.value}</p>
                    <p className="text-sm font-medium text-slate-700 mt-1">{stat.label}</p>
                    <p className="text-xs text-slate-400" style={{ fontFamily: "'Inter', sans-serif" }}>{stat.sub}</p>
                  </div>
                ))}
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* TESTIMONIOS */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <Reveal>
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-12">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-[#0055FF] mb-2">Opiniones</p>
              <h2 className="text-3xl font-bold tracking-tight text-[#0F172A]">Lo que dicen nuestros clientes</h2>
            </div>
            <div className="flex items-center gap-1.5">
              {[...Array(5)].map((_, i) => <Star key={i} size={14} className="text-amber-400 fill-amber-400" />)}
              <span className="text-sm text-slate-500 ml-1" style={{ fontFamily: "'Inter', sans-serif" }}>4.9 · +300 reseñas</span>
            </div>
          </div>
        </Reveal>

        <div className="grid md:grid-cols-3 gap-5">
          {[
            { nombre: 'María G.', tiempo: 'Hace 2 semanas', texto: 'Llevé mi iPhone 14 Pro con la pantalla destrozada y lo tuve listo el mismo día. El precio fue justo y la calidad de la reparación es perfecta.', dispositivo: 'iPhone 14 Pro · Pantalla' },
            { nombre: 'Carlos M.', tiempo: 'Hace 1 mes', texto: 'Mi aseguradora me derivó a Revix y fue una experiencia excelente. Rápidos, profesionales y con mucha transparencia en todo el proceso.', dispositivo: 'Samsung S23 · Seguro' },
            { nombre: 'Ana L.', tiempo: 'Hace 3 semanas', texto: 'El conector de carga roto, en menos de 2 horas solucionado. El precio es muy razonable y el trato fue genial desde el principio.', dispositivo: 'Xiaomi 12 · Conector' },
            { nombre: 'Roberto S.', tiempo: 'Hace 1 semana', texto: 'Tenía un Samsung con daños por agua que otros talleres rechazaron. En Revix lo aceptaron sin problema y lo recuperaron completamente.', dispositivo: 'Samsung A54 · Agua' },
            { nombre: 'Laura F.', tiempo: 'Hace 2 meses', texto: 'El presupuesto fue el más competitivo de todos los que pedí y la reparación quedó como nueva. Muy contentos con el resultado.', dispositivo: 'iPad Pro 11" · Pantalla' },
            { nombre: 'Diego T.', tiempo: 'Hace 3 días', texto: 'Servicio de 10. Me informaron del estado en todo momento. El portal online para ver el estado es muy útil. Mi sitio de confianza.', dispositivo: 'iPhone 13 · Batería' },
          ].map((review, idx) => (
            <Reveal key={idx} delay={idx * 0.06}>
              <div className="p-5 border border-slate-100 rounded-xl hover:border-slate-200 hover:shadow-sm transition-all duration-200 bg-white relative">
                <Quote size={20} className="text-slate-100 absolute top-4 right-4 fill-current" />
                <div className="flex gap-1 mb-3">
                  {[...Array(5)].map((_, i) => <Star key={i} size={12} className="text-amber-400 fill-amber-400" />)}
                </div>
                <p className="text-sm text-slate-600 leading-relaxed mb-4" style={{ fontFamily: "'Inter', sans-serif" }}>
                  "{review.texto}"
                </p>
                <span className="inline-block px-2 py-0.5 bg-slate-50 border border-slate-100 text-slate-500 rounded text-xs mb-4" style={{ fontFamily: "'Inter', sans-serif" }}>
                  {review.dispositivo}
                </span>
                <div className="flex items-center gap-2.5 pt-3 border-t border-slate-100">
                  <div className="w-7 h-7 bg-[#0055FF] rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                    {review.nombre.charAt(0)}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-[#0F172A]">{review.nombre}</p>
                    <p className="text-xs text-slate-400" style={{ fontFamily: "'Inter', sans-serif" }}>{review.tiempo}</p>
                  </div>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* CTA FINAL */}
      <section className="border-t border-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <Reveal>
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-8">
              <div>
                <h2 className="text-3xl font-bold tracking-tight text-[#0F172A] mb-2">
                  ¿Listo para reparar tu dispositivo?
                </h2>
                <p className="text-slate-500 text-sm" style={{ fontFamily: "'Inter', sans-serif" }}>
                  Presupuesto gratuito y sin compromiso. Respuesta en menos de 24 horas.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3 flex-shrink-0">
                <Link
                  to="/presupuesto"
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#0055FF] text-white rounded-lg text-sm font-semibold hover:bg-[#0044DD] transition-colors shadow-sm shadow-blue-200"
                >
                  Pedir presupuesto gratis
                  <ArrowRight size={16} />
                </Link>
                <Link
                  to="/contacto"
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-white border border-slate-200 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition-colors"
                >
                  Contactar
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

    </div>
  );
}

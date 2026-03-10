import { useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, useInView } from 'framer-motion';
import { Handshake, Building2, Package, Shield, CheckCircle2, ArrowRight, Users, Truck } from 'lucide-react';

function Reveal({ children, delay = 0, className = '' }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-50px' });
  return (
    <motion.div ref={ref} initial={{ opacity: 0, y: 20 }} animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.45, delay }} className={className}>
      {children}
    </motion.div>
  );
}

// Partners de servicios (confían en nosotros)
const partnersServicios = [
  {
    nombre: 'Insurama',
    tipo: 'Aseguradora',
    descripcion: 'Gestión integral de siniestros de dispositivos móviles. Partner oficial para reparaciones de asegurados.',
    beneficios: ['Gestión ágil de siniestros', 'Presupuestos en <24h', 'Seguimiento en tiempo real'],
    logo: null,
    bgColor: 'bg-[#00B4D8]',
  },
  {
    nombre: 'Samsung',
    tipo: 'Fabricante oficial',
    descripcion: 'Partner autorizado de Samsung para reparaciones con acceso a repuestos originales y formación certificada.',
    beneficios: ['Repuestos 100% originales', 'Técnicos certificados Samsung', 'Garantía oficial'],
    logo: '/logos/samsung-white.png',
    bgColor: 'bg-[#1428A0]',
  },
  {
    nombre: 'AXA Seguros',
    tipo: 'Aseguradora',
    descripcion: 'Servicio técnico de confianza para la reparación de dispositivos de asegurados AXA.',
    beneficios: ['Calidad certificada WISE', 'Garantía extendida', 'Atención preferente'],
    logo: null,
    bgColor: 'bg-[#00008F]',
  },
];

// Colaboradores de repuestos (con quienes trabajamos)
const colaboradoresRepuestos = [
  {
    nombre: 'Apple',
    tipo: 'Componentes compatibles',
    descripcion: 'Componentes de alta calidad para dispositivos Apple con garantía completa.',
    color: 'bg-slate-800',
  },
  {
    nombre: 'MobileSentrix',
    tipo: 'Distribuidor internacional',
    descripcion: 'Proveedor premium de repuestos para smartphones y tablets de todas las marcas.',
    color: 'bg-green-600',
  },
  {
    nombre: 'Utopya',
    tipo: 'Distribuidor español',
    descripcion: 'Proveedor especializado en componentes y accesorios para reparación profesional.',
    color: 'bg-orange-500',
  },
];

export default function PublicPartners() {
  return (
    <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }} className="bg-white text-[#0F172A]">
      {/* Header */}
      <div className="border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-xs font-semibold uppercase tracking-widest text-[#0055FF] mb-3">
            Partners y Colaboradores
          </motion.p>
          <motion.h1 initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="text-4xl font-bold tracking-tight text-[#0F172A] mb-4">
            Red de confianza profesional
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
            className="text-slate-500 text-base max-w-xl" style={{ fontFamily: "'Inter', sans-serif" }}>
            Trabajamos con los mejores partners de servicios y colaboradores de repuestos para ofrecer calidad certificada en cada reparación.
          </motion.p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-16">

        {/* SECCIÓN 1: Partners de Servicios */}
        <Reveal>
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center">
              <Handshake size={24} className="text-[#0055FF]" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-[#0F172A]">Partners de servicios</h2>
              <p className="text-sm text-slate-500" style={{ fontFamily: "'Inter', sans-serif" }}>Empresas que confían en nosotros para sus clientes</p>
            </div>
          </div>
        </Reveal>

        <div className="grid md:grid-cols-3 gap-5 mb-16">
          {partnersServicios.map((partner, i) => (
            <Reveal key={partner.nombre} delay={i * 0.08}>
              <div className="p-6 border border-slate-100 rounded-xl h-full hover:border-blue-200 hover:shadow-md transition-all duration-200 group">
                <div className="flex items-center gap-4 mb-4">
                  <div className={`w-14 h-14 ${partner.bgColor} rounded-xl flex items-center justify-center overflow-hidden`}>
                    {partner.logo ? (
                      <img 
                        src={partner.logo} 
                        alt={partner.nombre}
                        className="w-10 h-auto object-contain"
                      />
                    ) : (
                      <span className="text-white font-bold text-xl">{partner.nombre.charAt(0)}</span>
                    )}
                  </div>
                  <div>
                    <h3 className="font-bold text-[#0F172A] text-lg group-hover:text-[#0055FF] transition-colors">{partner.nombre}</h3>
                    <p className="text-xs text-slate-400 font-medium">{partner.tipo}</p>
                  </div>
                </div>
                <p className="text-sm text-slate-500 leading-relaxed mb-4" style={{ fontFamily: "'Inter', sans-serif" }}>
                  {partner.descripcion}
                </p>
                <ul className="space-y-1.5">
                  {partner.beneficios.map((b) => (
                    <li key={b} className="flex items-center gap-2 text-xs text-slate-600" style={{ fontFamily: "'Inter', sans-serif" }}>
                      <CheckCircle2 size={12} className="text-[#0055FF] flex-shrink-0" />
                      {b}
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          ))}
        </div>

        {/* Divider */}
        <div className="border-t border-slate-100 my-12" />

        {/* SECCIÓN 2: Colaboradores de Repuestos */}
        <Reveal>
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 bg-green-50 rounded-xl flex items-center justify-center">
              <Package size={24} className="text-green-600" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-[#0F172A]">Colaboradores de repuestos</h2>
              <p className="text-sm text-slate-500" style={{ fontFamily: "'Inter', sans-serif" }}>Proveedores con los que contamos para ofrecerte calidad</p>
            </div>
          </div>
        </Reveal>

        <div className="grid md:grid-cols-3 gap-4 mb-16">
          {colaboradoresRepuestos.map((colab, i) => (
            <Reveal key={colab.nombre} delay={i * 0.06}>
              <div className="p-5 border border-slate-100 rounded-xl hover:border-green-200 hover:shadow-sm transition-all duration-200 group">
                <div className="flex items-center gap-3 mb-3">
                  <div className={`w-10 h-10 ${colab.color} rounded-lg flex items-center justify-center`}>
                    <span className="text-white font-bold text-sm">{colab.nombre.charAt(0)}</span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-[#0F172A] group-hover:text-green-600 transition-colors">{colab.nombre}</h3>
                    <p className="text-xs text-slate-400">{colab.tipo}</p>
                  </div>
                </div>
                <p className="text-sm text-slate-500 leading-relaxed" style={{ fontFamily: "'Inter', sans-serif" }}>
                  {colab.descripcion}
                </p>
              </div>
            </Reveal>
          ))}
        </div>

        {/* Beneficios */}
        <Reveal>
          <div className="bg-slate-50 border border-slate-100 rounded-2xl p-8 mb-12">
            <h3 className="text-xl font-bold text-[#0F172A] mb-6 text-center">¿Por qué trabajamos con partners?</h3>
            <div className="grid md:grid-cols-3 gap-6">
              {[
                { icon: Shield, title: 'Calidad garantizada', desc: 'Repuestos originales y homologados que aseguran durabilidad.' },
                { icon: Truck, title: 'Disponibilidad', desc: 'Acceso rápido a piezas para minimizar tiempos de espera.' },
                { icon: Users, title: 'Confianza mutua', desc: 'Relaciones a largo plazo basadas en resultados y profesionalidad.' },
              ].map((item, i) => (
                <div key={i} className="text-center">
                  <div className="w-12 h-12 bg-white border border-slate-200 rounded-xl flex items-center justify-center mx-auto mb-3">
                    <item.icon size={20} className="text-slate-600" />
                  </div>
                  <h4 className="font-semibold text-[#0F172A] text-sm mb-1">{item.title}</h4>
                  <p className="text-xs text-slate-500" style={{ fontFamily: "'Inter', sans-serif" }}>{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </Reveal>

        {/* CTA: Ser partner */}
        <Reveal>
          <div className="p-8 bg-[#0055FF] rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="text-white">
              <h3 className="font-bold text-xl mb-2">¿Quieres ser partner de Revix?</h3>
              <p className="text-blue-100 text-sm" style={{ fontFamily: "'Inter', sans-serif" }}>
                Buscamos aseguradoras, distribuidores y empresas que quieran colaborar con un servicio técnico de confianza.
              </p>
            </div>
            <Link
              to="/contacto"
              className="inline-flex items-center gap-1.5 px-5 py-3 bg-white text-[#0055FF] rounded-lg text-sm font-semibold hover:bg-blue-50 transition-colors flex-shrink-0"
            >
              Contactar <ArrowRight size={14} />
            </Link>
          </div>
        </Reveal>
      </div>
    </div>
  );
}

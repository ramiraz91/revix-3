import { useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, useInView } from 'framer-motion';
import { Building2, Shield, Clock, BarChart3, FileText, CheckCircle2, ArrowRight, Mail } from 'lucide-react';

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

const ventajas = [
  { icon: Clock, title: 'Agilidad en la gestión', desc: 'Presupuestos detallados en menos de 24 horas. Coordinación directa con el gestor del siniestro.' },
  { icon: Shield, title: 'Calidad certificada', desc: 'Técnicos con certificación WISE y estándares de calidad ACS en todas las reparaciones.' },
  { icon: BarChart3, title: 'Informes técnicos', desc: 'Informes completos con diagnóstico, fotografías y justificación de cada intervención.' },
  { icon: FileText, title: 'Documentación', desc: 'Toda la documentación necesaria para el expediente de siniestro, lista y ordenada.' },
  { icon: Building2, title: 'Experiencia en seguros', desc: 'Colaboramos activamente con aseguradoras como Insurama y otras compañías del sector.' },
  { icon: Shield, title: 'Garantía incluida', desc: '6 meses de garantía en cada reparación gestionada a través de aseguradora.' },
];

export default function PublicAseguradoras() {
  return (
    <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }} className="bg-white text-[#0F172A]">
      <div className="border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-xs font-semibold uppercase tracking-widest text-[#0055FF] mb-3">
            Para aseguradoras
          </motion.p>
          <motion.h1 initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="text-4xl font-bold tracking-tight text-[#0F172A] mb-4 max-w-2xl">
            Servicio técnico de confianza para la gestión de siniestros
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
            className="text-slate-500 text-base max-w-xl" style={{ fontFamily: "'Inter', sans-serif" }}>
            Gestionamos la reparación de dispositivos móviles con la agilidad, transparencia y calidad que requiere el sector asegurador.
          </motion.p>
        </div>
      </div>

      {/* Stats */}
      <div className="border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-10">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { value: '+5.000', label: 'Reparaciones completadas' },
              { value: '98%', label: 'Satisfacción del cliente' },
              { value: '<24h', label: 'Presupuesto garantizado' },
              { value: '6 meses', label: 'Garantía en cada reparación' },
            ].map((s) => (
              <div key={s.label} className="py-2">
                <p className="text-2xl font-bold text-[#0F172A]">{s.value}</p>
                <p className="text-sm text-slate-400 mt-0.5" style={{ fontFamily: "'Inter', sans-serif" }}>{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Ventajas */}
      <div className="max-w-6xl mx-auto px-6 py-16">
        <Reveal>
          <h2 className="text-2xl font-bold tracking-tight text-[#0F172A] mb-10">¿Por qué trabajar con Revix?</h2>
        </Reveal>
        <div className="grid md:grid-cols-3 gap-5">
          {ventajas.map((v, i) => (
            <Reveal key={i} delay={i * 0.06}>
              <div className="p-6 border border-slate-100 rounded-xl hover:border-slate-200 hover:shadow-sm transition-all">
                <div className="w-10 h-10 bg-slate-50 rounded-lg flex items-center justify-center mb-4">
                  <v.icon size={18} className="text-slate-500" />
                </div>
                <h3 className="font-semibold text-[#0F172A] mb-2">{v.title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed" style={{ fontFamily: "'Inter', sans-serif" }}>{v.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div className="bg-slate-50 border-y border-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-14">
          <Reveal>
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div>
                <h2 className="text-2xl font-bold tracking-tight text-[#0F172A] mb-2">¿Tu compañía necesita un servicio técnico de confianza?</h2>
                <p className="text-slate-500 text-sm" style={{ fontFamily: "'Inter', sans-serif" }}>Contacta con nosotros para establecer un acuerdo de colaboración.</p>
              </div>
              <div className="flex items-center gap-3 flex-shrink-0">
                <a href="mailto:help@revix.es"
                  className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#0055FF] text-white rounded-lg text-sm font-semibold hover:bg-[#0044DD] transition-colors">
                  <Mail size={15} /> help@revix.es
                </a>
                <Link to="/contacto"
                  className="inline-flex items-center gap-1.5 px-4 py-2.5 border border-slate-200 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition-colors">
                  Formulario <ArrowRight size={13} />
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </div>
  );
}

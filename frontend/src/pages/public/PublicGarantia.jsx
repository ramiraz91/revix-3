import { useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, useInView } from 'framer-motion';
import { Shield, CheckCircle2, Award, ArrowRight, Clock } from 'lucide-react';

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

export default function PublicGarantia() {
  return (
    <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }} className="bg-white text-[#0F172A]">
      <div className="border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-xs font-semibold uppercase tracking-widest text-[#0055FF] mb-3">
            Garantía
          </motion.p>
          <motion.h1 initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="text-4xl font-bold tracking-tight text-[#0F172A] mb-4">
            6 meses de garantía en todas las reparaciones
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
            className="text-slate-500 text-base max-w-xl" style={{ fontFamily: "'Inter', sans-serif" }}>
            Tu tranquilidad está garantizada. Si la reparación falla en los primeros 6 meses por el mismo motivo, la repetimos sin coste adicional.
          </motion.p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-16">
        <div className="grid md:grid-cols-3 gap-5 mb-14">
          {[
            { icon: Shield, title: '6 meses de cobertura', desc: 'Cubre cualquier fallo relacionado con la reparación original durante los 6 meses siguientes.' },
            { icon: Award, title: 'Certificación WISE', desc: 'Todos nuestros técnicos están certificados bajo el estándar WISE, garantía de calidad internacional.' },
            { icon: Clock, title: 'Reparación express', desc: 'Si la garantía se activa, la atendemos con máxima prioridad para que no pierdas tiempo.' },
          ].map((item, i) => (
            <Reveal key={i} delay={i * 0.07}>
              <div className="p-6 border border-slate-100 rounded-xl h-full">
                <div className="w-10 h-10 bg-slate-50 rounded-lg flex items-center justify-center mb-4">
                  <item.icon size={18} className="text-slate-500" />
                </div>
                <h3 className="font-semibold text-[#0F172A] mb-2">{item.title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed" style={{ fontFamily: "'Inter', sans-serif" }}>{item.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>

        {/* Qué cubre y qué no */}
        <div className="grid md:grid-cols-2 gap-6 mb-14">
          <Reveal>
            <div className="p-6 border border-slate-100 rounded-xl">
              <h3 className="font-semibold text-[#0F172A] mb-4">¿Qué cubre la garantía?</h3>
              <ul className="space-y-2.5">
                {[
                  'Fallo de la pieza reparada por defecto de fabricación',
                  'Problemas derivados directamente de la reparación',
                  'Fallos en el funcionamiento del componente sustituido',
                  'Defectos en la mano de obra del técnico',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2 text-sm text-slate-600" style={{ fontFamily: "'Inter', sans-serif" }}>
                    <CheckCircle2 size={15} className="text-[#0055FF] flex-shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>

          <Reveal delay={0.08}>
            <div className="p-6 border border-slate-100 rounded-xl">
              <h3 className="font-semibold text-[#0F172A] mb-4">¿Qué no cubre?</h3>
              <ul className="space-y-2.5">
                {[
                  'Daños físicos posteriores (caídas, golpes)',
                  'Daños por exposición a líquidos tras la reparación',
                  'Intervenciones de terceros en el dispositivo',
                  'Averías no relacionadas con la reparación original',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2 text-sm text-slate-500" style={{ fontFamily: "'Inter', sans-serif" }}>
                    <span className="w-3.5 h-3.5 border border-slate-300 rounded-full flex-shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>

        {/* CTA */}
        <Reveal>
          <div className="p-8 bg-slate-50 border border-slate-100 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <h3 className="font-semibold text-[#0F172A] mb-1">¿Quieres más cobertura?</h3>
              <p className="text-sm text-slate-500" style={{ fontFamily: "'Inter', sans-serif" }}>
                Amplía tu garantía hasta 12 o 24 meses con nuestros planes de garantía extendida.
              </p>
            </div>
            <div className="flex items-center gap-3 flex-shrink-0">
              <Link to="/garantia-extendida"
                className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-[#0055FF] text-white rounded-lg text-sm font-semibold hover:bg-[#0044DD] transition-colors">
                Ver garantía extendida <ArrowRight size={13} />
              </Link>
              <Link to="/contacto"
                className="inline-flex items-center gap-1.5 px-4 py-2.5 border border-slate-200 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition-colors">
                Contactar
              </Link>
            </div>
          </div>
        </Reveal>
      </div>
    </div>
  );
}

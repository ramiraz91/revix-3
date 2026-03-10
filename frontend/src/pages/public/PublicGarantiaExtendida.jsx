import { useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, useInView } from 'framer-motion';
import {
  Shield, Clock, CheckCircle2, ArrowRight,
  ShieldCheck, ShieldPlus, Star, Mail, Info
} from 'lucide-react';

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

const planes = [
  {
    icon: Shield,
    nombre: 'Garantía Estándar',
    duracion: '6 meses',
    descripcion: 'Incluida en todas las reparaciones, sin coste adicional.',
    incluye: [
      'Cobertura de la pieza sustituida',
      'Fallos de mano de obra',
      'Atención prioritaria en garantía',
    ],
    cta: null,
    destacado: false,
    badge: 'Incluida gratis',
  },
  {
    icon: ShieldCheck,
    nombre: 'Garantía Plus',
    duracion: '12 meses',
    descripcion: 'Ampliación a 12 meses para una tranquilidad completa.',
    incluye: [
      'Todo lo incluido en Estándar',
      'Cobertura ampliada a 12 meses',
      'Revisión técnica a los 6 meses',
      'Diagnóstico gratuito de incidencias',
    ],
    cta: 'Consultar precio',
    destacado: true,
    badge: 'Más popular',
  },
  {
    icon: ShieldPlus,
    nombre: 'Garantía Premium',
    duracion: '24 meses',
    descripcion: 'La máxima protección para tu dispositivo durante 2 años.',
    incluye: [
      'Todo lo incluido en Plus',
      'Cobertura ampliada a 24 meses',
      'Asistencia técnica remota',
      '2 revisiones técnicas incluidas',
      'Presupuesto preferente en nuevas reparaciones',
    ],
    cta: 'Consultar precio',
    destacado: false,
    badge: 'Máxima cobertura',
  },
];

export default function PublicGarantiaExtendida() {
  return (
    <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }} className="bg-white text-[#0F172A]">

      {/* Header */}
      <div className="border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-100 rounded-full text-xs font-semibold text-[#0055FF] mb-5"
          >
            <ShieldPlus size={13} />
            Próximamente disponible
          </motion.div>
          <motion.h1 initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="text-4xl md:text-5xl font-bold tracking-tight text-[#0F172A] mb-4">
            Garantía extendida
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
            className="text-slate-500 text-base max-w-xl leading-relaxed" style={{ fontFamily: "'Inter', sans-serif" }}>
            Amplía la cobertura de tu reparación más allá de los 6 meses estándar. Planes flexibles adaptados a cada tipo de dispositivo y necesidad.
          </motion.p>
        </div>
      </div>

      {/* Aviso informativo */}
      <div className="max-w-6xl mx-auto px-6 pt-10">
        <Reveal>
          <div className="flex items-start gap-3 p-4 bg-slate-50 border border-slate-200 rounded-xl">
            <Info size={16} className="text-slate-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-slate-500" style={{ fontFamily: "'Inter', sans-serif" }}>
              Los planes de garantía extendida están <strong className="text-slate-700">en fase de activación</strong>. Puedes consultarnos por email para conocer disponibilidad y precios actualizados.
            </p>
          </div>
        </Reveal>
      </div>

      {/* Planes */}
      <div className="max-w-6xl mx-auto px-6 py-14">
        <Reveal>
          <p className="text-xs font-semibold uppercase tracking-widest text-[#0055FF] mb-2">Planes disponibles</p>
          <h2 className="text-2xl font-bold tracking-tight text-[#0F172A] mb-10">Elige tu nivel de protección</h2>
        </Reveal>

        <div className="grid md:grid-cols-3 gap-5">
          {planes.map((plan, i) => (
            <Reveal key={i} delay={i * 0.08}>
              <div className={`relative h-full flex flex-col p-6 border rounded-xl transition-all duration-200 ${
                plan.destacado
                  ? 'border-[#0055FF] shadow-sm shadow-blue-100'
                  : 'border-slate-100 hover:border-slate-200 hover:shadow-sm'
              }`}>
                {/* Badge */}
                <div className="mb-5 flex items-start justify-between">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    plan.destacado ? 'bg-[#0055FF]' : 'bg-slate-50'
                  }`}>
                    <plan.icon size={18} className={plan.destacado ? 'text-white' : 'text-slate-500'} />
                  </div>
                  <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${
                    plan.destacado
                      ? 'bg-blue-50 text-[#0055FF]'
                      : 'bg-slate-100 text-slate-500'
                  }`}>
                    {plan.badge}
                  </span>
                </div>

                <h3 className="text-lg font-bold text-[#0F172A] mb-1">{plan.nombre}</h3>
                <div className="flex items-center gap-2 mb-3">
                  <Clock size={14} className="text-slate-400" />
                  <span className="text-sm font-semibold text-slate-600" style={{ fontFamily: "'Inter', sans-serif" }}>
                    {plan.duracion} de cobertura
                  </span>
                </div>
                <p className="text-sm text-slate-400 mb-5 leading-relaxed" style={{ fontFamily: "'Inter', sans-serif" }}>
                  {plan.descripcion}
                </p>

                <ul className="space-y-2.5 flex-1 mb-6">
                  {plan.incluye.map((item) => (
                    <li key={item} className="flex items-start gap-2 text-sm text-slate-600" style={{ fontFamily: "'Inter', sans-serif" }}>
                      <CheckCircle2 size={14} className="text-[#0055FF] flex-shrink-0 mt-0.5" />
                      {item}
                    </li>
                  ))}
                </ul>

                {plan.cta ? (
                  <a href="mailto:help@revix.es?subject=Consulta garantía extendida"
                    className={`w-full py-2.5 rounded-lg text-sm font-semibold text-center transition-colors flex items-center justify-center gap-1.5 ${
                      plan.destacado
                        ? 'bg-[#0055FF] text-white hover:bg-[#0044DD]'
                        : 'border border-slate-200 text-slate-700 hover:bg-slate-50'
                    }`}>
                    {plan.cta} <ArrowRight size={13} />
                  </a>
                ) : (
                  <div className="w-full py-2.5 rounded-lg text-sm font-medium text-center bg-slate-50 text-slate-400 border border-slate-100">
                    Incluida en tu reparación
                  </div>
                )}
              </div>
            </Reveal>
          ))}
        </div>
      </div>

      {/* Qué cubre */}
      <div className="bg-slate-50 border-y border-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-14">
          <Reveal>
            <h2 className="text-xl font-bold tracking-tight text-[#0F172A] mb-8">¿Qué cubre la garantía extendida?</h2>
          </Reveal>

          <div className="grid md:grid-cols-2 gap-5">
            <Reveal delay={0.05}>
              <div className="bg-white border border-slate-100 rounded-xl p-6">
                <h3 className="font-semibold text-[#0F172A] mb-4 flex items-center gap-2">
                  <CheckCircle2 size={16} className="text-[#0055FF]" /> Qué está cubierto
                </h3>
                <ul className="space-y-2.5">
                  {[
                    'Fallo de la pieza reparada por defecto',
                    'Problemas derivados de la reparación original',
                    'Defectos en materiales y mano de obra',
                    'Revisiones técnicas periódicas (según plan)',
                    'Asesoramiento técnico durante la vigencia',
                  ].map((item) => (
                    <li key={item} className="flex items-start gap-2 text-sm text-slate-600" style={{ fontFamily: "'Inter', sans-serif" }}>
                      <span className="w-1.5 h-1.5 bg-[#0055FF] rounded-full flex-shrink-0 mt-1.5" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>

            <Reveal delay={0.1}>
              <div className="bg-white border border-slate-100 rounded-xl p-6">
                <h3 className="font-semibold text-[#0F172A] mb-4 flex items-center gap-2">
                  <span className="w-4 h-4 border border-slate-300 rounded-full flex items-center justify-center">
                    <span className="w-1.5 h-1.5 bg-slate-300 rounded-full" />
                  </span>
                  Qué no está cubierto
                </h3>
                <ul className="space-y-2.5">
                  {[
                    'Daños físicos posteriores (caídas, golpes)',
                    'Exposición a líquidos tras la reparación',
                    'Intervenciones de terceros',
                    'Daños no relacionados con la reparación original',
                    'Pérdida o robo del dispositivo',
                  ].map((item) => (
                    <li key={item} className="flex items-start gap-2 text-sm text-slate-500" style={{ fontFamily: "'Inter', sans-serif" }}>
                      <span className="w-1.5 h-1.5 bg-slate-300 rounded-full flex-shrink-0 mt-1.5" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="max-w-6xl mx-auto px-6 py-14">
        <Reveal>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 p-8 border border-slate-100 rounded-2xl">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Star size={15} className="text-amber-400 fill-amber-400" />
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide" style={{ fontFamily: "'Inter', sans-serif" }}>
                  Disponible próximamente
                </span>
              </div>
              <h3 className="font-bold text-[#0F172A] mb-1">¿Te interesa la garantía extendida?</h3>
              <p className="text-sm text-slate-500" style={{ fontFamily: "'Inter', sans-serif" }}>
                Contacta con nosotros y te informamos cuando estén activos los planes de contratación.
              </p>
            </div>
            <div className="flex items-center gap-3 flex-shrink-0">
              <a href="mailto:help@revix.es?subject=Interés en garantía extendida"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#0055FF] text-white rounded-lg text-sm font-semibold hover:bg-[#0044DD] transition-colors">
                <Mail size={15} />
                Contactar
              </a>
              <Link to="/garantia"
                className="inline-flex items-center gap-1.5 px-4 py-2.5 border border-slate-200 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition-colors">
                Ver garantía estándar
              </Link>
            </div>
          </div>
        </Reveal>
      </div>

    </div>
  );
}

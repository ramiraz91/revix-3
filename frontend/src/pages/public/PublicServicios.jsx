import { useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, useInView } from 'framer-motion';
import { Smartphone, Tablet, Watch, Gamepad2, CheckCircle2, ArrowRight, Cpu } from 'lucide-react';

function Reveal({ children, delay = 0, className = '' }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-50px' });
  return (
    <motion.div ref={ref} initial={{ opacity: 0, y: 20 }} animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.45, delay, ease: [0.25, 0.1, 0.25, 1] }} className={className}>
      {children}
    </motion.div>
  );
}

const servicios = [
  {
    icon: Smartphone,
    categoria: 'Smartphones',
    desc: 'iPhone, Samsung, Xiaomi, Huawei, OnePlus y todas las marcas',
    reparaciones: ['Pantalla (OLED, AMOLED, LCD)', 'Batería', 'Cámara trasera y frontal', 'Conector de carga', 'Daños por agua', 'Altavoz y micrófono', 'Face ID / Touch ID', 'Botones y táctil', 'Microsoladura y placa base', 'Software y diagnóstico'],
  },
  {
    icon: Tablet,
    categoria: 'Tablets',
    desc: 'iPad, Samsung Galaxy Tab, Lenovo, Huawei MediaPad',
    reparaciones: ['Pantalla y digitalizador', 'Carcasa y cristal trasero', 'Batería', 'Conector de carga', 'Cámara', 'Botones', 'Daños por agua', 'Software'],
  },
  {
    icon: Watch,
    categoria: 'Smartwatches',
    desc: 'Apple Watch, Samsung Galaxy Watch, Garmin, Fitbit',
    reparaciones: ['Pantalla y cristal', 'Batería', 'Corona y botones', 'Sensor de pulso', 'Daños por agua', 'Carcasa y correas'],
  },
  {
    icon: Gamepad2,
    categoria: 'Consolas portátiles',
    desc: 'Nintendo Switch, Steam Deck',
    reparaciones: ['Pantalla', 'Joy-Con drift y botones', 'Batería', 'Puerto de carga', 'Ventilador y limpieza', 'Problemas de software'],
  },
];

export default function PublicServicios() {
  return (
    <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }} className="bg-white text-[#0F172A]">

      {/* Hero */}
      <div className="border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-xs font-semibold uppercase tracking-widest text-[#0055FF] mb-3">
            Catálogo de servicios
          </motion.p>
          <motion.h1 initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="text-4xl md:text-5xl font-bold tracking-tight text-[#0F172A] mb-4">
            Reparamos todo lo que otros no pueden
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
            className="text-slate-500 text-base max-w-xl" style={{ fontFamily: "'Inter', sans-serif" }}>
            Técnicos con certificación WISE y estándares ACS. Equipamiento especializado para las reparaciones más complejas.
          </motion.p>
        </div>
      </div>

      {/* Servicios */}
      <div className="max-w-6xl mx-auto px-6 py-16 space-y-5">
        {servicios.map((s, idx) => (
          <Reveal key={idx} delay={idx * 0.05}>
            <div className="border border-slate-100 rounded-xl overflow-hidden hover:border-slate-200 hover:shadow-sm transition-all duration-200">
              <div className="p-6 flex flex-col md:flex-row md:items-start gap-6">
                <div className="flex-shrink-0">
                  <div className="w-11 h-11 bg-slate-50 rounded-lg flex items-center justify-center">
                    <s.icon size={22} className="text-slate-500" />
                  </div>
                </div>
                <div className="flex-1">
                  <h2 className="text-lg font-semibold text-[#0F172A] mb-1">{s.categoria}</h2>
                  <p className="text-sm text-slate-400 mb-4" style={{ fontFamily: "'Inter', sans-serif" }}>{s.desc}</p>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-x-4 gap-y-2">
                    {s.reparaciones.map((r) => (
                      <div key={r} className="flex items-center gap-1.5 text-sm text-slate-600" style={{ fontFamily: "'Inter', sans-serif" }}>
                        <CheckCircle2 size={13} className="text-[#0055FF] flex-shrink-0" />
                        {r}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="flex-shrink-0">
                  <Link to="/presupuesto" className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0055FF] text-white rounded-lg text-sm font-semibold hover:bg-[#0044DD] transition-colors">
                    Presupuesto <ArrowRight size={13} />
                  </Link>
                </div>
              </div>
            </div>
          </Reveal>
        ))}
      </div>

      {/* Reparaciones difíciles */}
      <div className="bg-slate-50 border-y border-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <Reveal>
            <div className="flex flex-col md:flex-row gap-12 items-start">
              <div className="flex-1">
                <div className="w-11 h-11 bg-white border border-slate-200 rounded-lg flex items-center justify-center mb-5">
                  <Cpu size={22} className="text-[#0055FF]" />
                </div>
                <h2 className="text-2xl font-bold tracking-tight text-[#0F172A] mb-3">
                  Reparaciones avanzadas
                </h2>
                <p className="text-slate-500 text-sm leading-relaxed mb-6" style={{ fontFamily: "'Inter', sans-serif" }}>
                  Contamos con equipamiento de microsoladura de última generación para afrontar reparaciones a nivel de componente que muchos talleres rechazan.
                </p>
                <Link to="/presupuesto" className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0055FF] text-white rounded-lg text-sm font-semibold hover:bg-[#0044DD] transition-colors">
                  Solicitar presupuesto <ArrowRight size={13} />
                </Link>
              </div>
              <div className="flex-1 grid grid-cols-2 gap-3">
                {['Placa base (microsoladura BGA)', 'Recuperación de datos', 'Face ID / Touch ID', 'Daños graves por agua', 'Problemas de red y antena', 'Cámaras con estabilizador OIS'].map((item) => (
                  <div key={item} className="flex items-center gap-2 p-3 bg-white border border-slate-100 rounded-lg text-sm text-slate-600" style={{ fontFamily: "'Inter', sans-serif" }}>
                    <CheckCircle2 size={14} className="text-[#0055FF] flex-shrink-0" />
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </Reveal>
        </div>
      </div>

    </div>
  );
}

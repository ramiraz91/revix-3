import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ShieldCheck,
  Camera,
  Award,
  FileCheck2,
  Truck,
  Leaf,
  Recycle,
  ArrowRight,
  CheckCircle2,
  Sparkles,
  Smartphone,
  Building2,
  Handshake,
  Clock3,
} from 'lucide-react';
import {
  Section,
  Container,
  Eyebrow,
  H2,
  H3,
  Lead,
  CTAButton,
  Card,
  FadeUp,
} from '../../components/public/ui';
import CountUp from '../../components/public/CountUp';

const HERO_IMG =
  'https://images.unsplash.com/photo-1595284842948-0d0530153883?auto=format&fit=crop&w=1400&q=80';

const SEGUIMIENTO_IMG =
  'https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?auto=format&fit=crop&w=1200&q=80';

const pilares = [
  {
    icon: Award,
    title: 'Técnicos certificados',
    desc: 'Equipo formado en los estándares de Apple, Samsung y los principales fabricantes.',
  },
  {
    icon: ShieldCheck,
    title: 'Recambios OEM verificados',
    desc: 'Sólo piezas originales o equivalentes homologadas. Nunca imitaciones.',
  },
  {
    icon: Camera,
    title: 'Transparencia en foto y vídeo',
    desc: 'Documentamos cada diagnóstico con imágenes reales. Tú ves lo que ve el técnico.',
  },
  {
    icon: FileCheck2,
    title: 'Procesos con calidad ISO',
    desc: 'Protocolos certificados en cada fase: recepción, reparación, control y entrega.',
  },
];

const pasos = [
  { n: '01', title: 'Cuéntanos la avería', desc: 'En 2 minutos desde el móvil o el ordenador. Sin registro obligatorio.' },
  { n: '02', title: 'Nosotros lo recogemos', desc: 'Recogida gratuita en tu domicilio. Embalaje y seguro incluidos.' },
  { n: '03', title: 'Diagnóstico documentado', desc: 'Recibes fotos reales del interior de tu dispositivo y un presupuesto cerrado.' },
  { n: '04', title: 'Reparado y devuelto', desc: 'Con garantía escrita, informe técnico y envío certificado.' },
];

const tresR = [
  { icon: Sparkles, title: 'Repara', desc: 'Damos una segunda vida a tu dispositivo antes que a una caja nueva.' },
  { icon: Recycle, title: 'Reutiliza', desc: 'Componentes recuperados que vuelven a funcionar como el primer día.' },
  { icon: Leaf, title: 'Recicla', desc: 'Lo irreparable se recicla con gestores autorizados. Cero residuos al vertedero.' },
];

export default function PublicHome() {
  return (
    <>
      {/* ═════════ HERO ═════════ */}
      <section className="relative pt-32 sm:pt-40 pb-20 sm:pb-28 bg-white overflow-hidden">
        {/* Glow decorativo */}
        <div className="absolute top-0 right-[-10%] w-[60%] h-[60%] bg-[#0055FF]/5 rounded-full blur-3xl pointer-events-none" aria-hidden />
        <Container className="relative">
          <div className="grid lg:grid-cols-12 gap-12 lg:gap-16 items-center">
            <div className="lg:col-span-6">
              <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                className="space-y-8"
              >
                <div className="inline-flex items-center gap-2 bg-[#F5F5F7] border border-[#E5E5EA] rounded-full px-4 py-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#00C24F] animate-pulse" />
                  <span className="text-xs font-semibold text-[#3A3A3C]">Más de 10 años reparando dispositivos</span>
                </div>
                <h1 className="font-[800] text-[#111111] tracking-[-0.04em] text-4xl sm:text-6xl md:text-7xl leading-[1.02]">
                  Repara.<br />
                  Reutiliza.<br />
                  <span className="text-[#0055FF]">Recicla.</span>
                </h1>
                <Lead className="max-w-xl">
                  Servicio técnico profesional para móviles, tablets y consolas. Con recambios verificados, garantía escrita y seguimiento en tiempo real.
                </Lead>
                <div className="flex flex-wrap items-center gap-3 pt-2">
                  <CTAButton to="/presupuesto" variant="primary" withArrow testid="home-cta-presupuesto">
                    Pedir presupuesto
                  </CTAButton>
                  <CTAButton to="/consulta" variant="secondary" testid="home-cta-seguimiento">
                    Seguir mi reparación
                  </CTAButton>
                </div>
                <div className="pt-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-[#6E6E73]">
                  <span className="inline-flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-[#0055FF]" strokeWidth={2.5} />
                    Diagnóstico gratuito
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-[#0055FF]" strokeWidth={2.5} />
                    Recogida a domicilio
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-[#0055FF]" strokeWidth={2.5} />
                    Garantía escrita
                  </span>
                </div>
              </motion.div>
            </div>

            <motion.div
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.9, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
              className="lg:col-span-6"
            >
              <div className="relative">
                <div className="relative rounded-[2rem] overflow-hidden bg-[#F5F5F7] aspect-[4/3] lg:aspect-[5/4] shadow-[0_20px_80px_-20px_rgba(0,0,0,0.2)]">
                  <img src={HERO_IMG} alt="Técnico reparando un smartphone" className="w-full h-full object-cover" loading="eager" />
                </div>
                {/* Floating badge */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.6, duration: 0.6 }}
                  className="absolute -bottom-6 -left-6 sm:-left-10 bg-white rounded-2xl shadow-[0_16px_48px_-12px_rgba(0,0,0,0.18)] px-6 py-5 border border-[#E5E5EA]"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-11 h-11 rounded-full bg-[#EEF4FF] flex items-center justify-center">
                      <Clock3 className="w-5 h-5 text-[#0055FF]" strokeWidth={2} />
                    </div>
                    <div>
                      <p className="text-2xl font-[800] text-[#111111] leading-none tracking-tight">
                        <CountUp to={1.6} decimals={1} suffix=" d" />
                      </p>
                      <p className="text-xs text-[#6E6E73] mt-1">Reparaciones express en 70% de los casos</p>
                    </div>
                  </div>
                </motion.div>
              </div>
            </motion.div>
          </div>
        </Container>
      </section>

      {/* ═════════ STATS ═════════ */}
      <section className="py-20 sm:py-28 border-y border-[#E5E5EA] bg-white">
        <Container>
          <FadeUp>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-10 lg:gap-6">
              {[
                { value: 10, suffix: '+', label: 'Años en el sector' },
                { value: 1800, suffix: '+', label: 'Reparaciones al año' },
                { value: 2.6, decimals: 1, suffix: ' d', label: 'Tiempo medio puerta a puerta' },
                { value: 70, suffix: '%', label: 'Reparaciones en menos de 1,6 d' },
              ].map((s) => (
                <div key={s.label} className="text-center lg:text-left">
                  <p className="text-4xl sm:text-5xl lg:text-6xl font-[800] tracking-[-0.04em] text-[#111111] leading-none">
                    <CountUp to={s.value} decimals={s.decimals || 0} suffix={s.suffix} />
                  </p>
                  <p className="mt-3 text-sm text-[#6E6E73] max-w-[18ch] mx-auto lg:mx-0 leading-snug">{s.label}</p>
                </div>
              ))}
            </div>
          </FadeUp>
        </Container>
      </section>

      {/* ═════════ POR QUÉ CONFIAR ═════════ */}
      <Section tone="subtle">
        <div className="text-center max-w-3xl mx-auto mb-16 sm:mb-20">
          <FadeUp>
            <Eyebrow className="mb-4">Por qué confiar en Revix</Eyebrow>
            <H2>Calidad que se puede verificar.</H2>
            <Lead className="mt-6 max-w-2xl mx-auto">
              Reparar un dispositivo importante exige estándares claros. Aquí tienes los nuestros.
            </Lead>
          </FadeUp>
        </div>
        <div className="grid sm:grid-cols-2 gap-5">
          {pilares.map((p, i) => (
            <FadeUp key={p.title} delay={i * 0.06}>
              <div className="group bg-white rounded-3xl p-8 sm:p-10 border border-[#E5E5EA] h-full transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_20px_60px_-20px_rgba(0,85,255,0.15)]">
                <div className="w-12 h-12 rounded-2xl bg-[#EEF4FF] text-[#0055FF] flex items-center justify-center group-hover:scale-110 transition-transform">
                  <p.icon className="w-6 h-6" strokeWidth={1.75} />
                </div>
                <H3 className="mt-8">{p.title}</H3>
                <p className="mt-3 text-[#6E6E73] leading-relaxed">{p.desc}</p>
              </div>
            </FadeUp>
          ))}
        </div>
      </Section>

      {/* ═════════ SEGUIMIENTO EN TIEMPO REAL ═════════ */}
      <Section>
        <div className="grid lg:grid-cols-12 gap-12 lg:gap-20 items-center">
          <FadeUp className="lg:col-span-6 order-2 lg:order-1">
            <div className="relative rounded-[2rem] overflow-hidden bg-[#111111] aspect-[4/3]">
              <img src={SEGUIMIENTO_IMG} alt="Seguimiento en tiempo real" className="w-full h-full object-cover opacity-70" loading="lazy" />
              {/* Mockup overlay */}
              <div className="absolute inset-0 flex items-center justify-center p-4 sm:p-10">
                <div className="w-full max-w-sm bg-white rounded-3xl shadow-2xl p-5 sm:p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold uppercase tracking-widest text-[#6E6E73]">OT-2026-4832</p>
                    <span className="text-xs bg-[#EEF4FF] text-[#0055FF] font-semibold px-2.5 py-1 rounded-full">En reparación</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-[#F5F5F7] flex items-center justify-center">
                      <Smartphone className="w-5 h-5 text-[#111111]" strokeWidth={1.75} />
                    </div>
                    <div>
                      <p className="font-semibold text-[#111111] text-sm">iPhone 14 · Pantalla</p>
                      <p className="text-xs text-[#6E6E73] mt-0.5">Entrada · 18 abr · 10:24</p>
                    </div>
                  </div>
                  <div className="space-y-2.5">
                    {[
                      { label: 'Recibido', done: true },
                      { label: 'Diagnóstico', done: true },
                      { label: 'Reparando', done: false, active: true },
                      { label: 'Enviando', done: false },
                    ].map((step) => (
                      <div key={step.label} className="flex items-center gap-2.5">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            step.done ? 'bg-[#00C24F]' : step.active ? 'bg-[#0055FF] animate-pulse' : 'bg-[#E5E5EA]'
                          }`}
                        />
                        <span className={`text-sm ${step.done || step.active ? 'text-[#111111]' : 'text-[#9E9EA3]'}`}>
                          {step.label}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="pt-3 border-t border-[#E5E5EA]">
                    <p className="text-xs text-[#6E6E73]">Última actualización hace 2 min · 3 imágenes</p>
                  </div>
                </div>
              </div>
            </div>
          </FadeUp>

          <FadeUp className="lg:col-span-6 order-1 lg:order-2" delay={0.1}>
            <Eyebrow className="mb-4">Tu reparación, bajo control</Eyebrow>
            <H2>Seguimiento en tiempo real.<br />Con fotos de verdad.</H2>
            <p className="mt-6 text-lg text-[#6E6E73] leading-relaxed">
              Cada cliente tiene un panel con el estado de su reparación: diagnóstico, imágenes del interior, horas dedicadas y presupuesto detallado. Sin llamadas, sin preguntas, sin sorpresas.
            </p>
            <ul className="mt-8 space-y-4">
              {[
                'Imágenes reales del dispositivo en cada fase.',
                'Histórico de estados con marca de tiempo.',
                'Mensajería directa con el técnico asignado.',
                'Descarga del informe técnico al finalizar.',
              ].map((f) => (
                <li key={f} className="flex gap-3 text-[#3A3A3C] leading-relaxed">
                  <CheckCircle2 className="w-5 h-5 text-[#0055FF] mt-0.5 flex-shrink-0" strokeWidth={2.5} />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
            <div className="mt-10">
              <CTAButton to="/consulta" variant="dark" withArrow testid="home-cta-portal">
                Ver un ejemplo
              </CTAButton>
            </div>
          </FadeUp>
        </div>
      </Section>

      {/* ═════════ CÓMO FUNCIONA ═════════ */}
      <Section tone="subtle">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <FadeUp>
            <Eyebrow className="mb-4">Cómo funciona</Eyebrow>
            <H2>Cuatro pasos. Sin intermediarios.</H2>
          </FadeUp>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
          {pasos.map((p, i) => (
            <FadeUp key={p.n} delay={i * 0.08}>
              <Card tone="default" className="h-full">
                <span className="text-[#0055FF] font-[800] text-2xl tracking-tight">{p.n}</span>
                <H3 className="mt-4">{p.title}</H3>
                <p className="mt-2 text-[#6E6E73] leading-relaxed">{p.desc}</p>
              </Card>
            </FadeUp>
          ))}
        </div>
      </Section>

      {/* ═════════ LAS 3 R — SOSTENIBILIDAD ═════════ */}
      <Section tone="dark">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <FadeUp>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5C86FF] mb-5">Nuestro compromiso</p>
            <h2 className="font-[700] tracking-[-0.035em] text-3xl sm:text-5xl leading-[1.05] text-white">
              Alargar la vida útil<br />es el mejor reciclaje.
            </h2>
            <p className="mt-6 text-lg text-white/70 leading-relaxed">
              Cada reparación es un dispositivo menos en el vertedero. Y una factura menos de 1.000€.
            </p>
          </FadeUp>
        </div>
        <div className="grid md:grid-cols-3 gap-5">
          {tresR.map((r, i) => (
            <FadeUp key={r.title} delay={i * 0.1}>
              <div className="rounded-3xl bg-white/5 border border-white/10 p-8 sm:p-10 h-full hover:bg-white/10 transition-colors">
                <div className="w-12 h-12 rounded-2xl bg-[#5C86FF]/20 text-[#5C86FF] flex items-center justify-center">
                  <r.icon className="w-6 h-6" strokeWidth={1.75} />
                </div>
                <h3 className="mt-8 font-[700] text-2xl text-white tracking-tight">{r.title}</h3>
                <p className="mt-3 text-white/60 leading-relaxed">{r.desc}</p>
              </div>
            </FadeUp>
          ))}
        </div>
      </Section>

      {/* ═════════ B2B SECTION ═════════ */}
      <Section>
        <div className="grid lg:grid-cols-12 gap-10 items-center">
          <FadeUp className="lg:col-span-6">
            <Eyebrow className="mb-4">Canal profesional</Eyebrow>
            <H2>Trabajamos también con aseguradoras y partners.</H2>
            <p className="mt-6 text-lg text-[#6E6E73] max-w-xl leading-relaxed">
              Volumen, SLA contractuales, trazabilidad completa y un equipo dedicado. Si representas a una aseguradora o una red de puntos de venta, tienes en Revix un aliado técnico serio.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <CTAButton to="/aseguradoras" variant="primary" withArrow testid="home-cta-aseguradoras">
                Soy aseguradora
              </CTAButton>
              <CTAButton to="/partners" variant="secondary" testid="home-cta-partners">
                Soy partner
              </CTAButton>
            </div>
          </FadeUp>
          <FadeUp className="lg:col-span-6" delay={0.1}>
            <div className="grid grid-cols-1 gap-4">
              <div className="rounded-3xl bg-[#F5F5F7] border border-[#E5E5EA] p-8 flex items-start gap-4">
                <span className="w-10 h-10 rounded-full bg-white inline-flex items-center justify-center shadow-sm flex-shrink-0">
                  <Building2 className="w-5 h-5 text-[#0055FF]" strokeWidth={1.75} />
                </span>
                <div>
                  <p className="font-semibold text-[#111111]">SLA contractual</p>
                  <p className="text-sm text-[#6E6E73] mt-1">Compromiso medible en cada ticket.</p>
                </div>
              </div>
              <div className="rounded-3xl bg-[#F5F5F7] border border-[#E5E5EA] p-8 flex items-start gap-4">
                <span className="w-10 h-10 rounded-full bg-white inline-flex items-center justify-center shadow-sm flex-shrink-0">
                  <Truck className="w-5 h-5 text-[#0055FF]" strokeWidth={1.75} />
                </span>
                <div>
                  <p className="font-semibold text-[#111111]">Logística nacional</p>
                  <p className="text-sm text-[#6E6E73] mt-1">Cobertura en toda España con recogida y entrega certificadas.</p>
                </div>
              </div>
              <div className="rounded-3xl bg-[#F5F5F7] border border-[#E5E5EA] p-8 flex items-start gap-4">
                <span className="w-10 h-10 rounded-full bg-white inline-flex items-center justify-center shadow-sm flex-shrink-0">
                  <Handshake className="w-5 h-5 text-[#0055FF]" strokeWidth={1.75} />
                </span>
                <div>
                  <p className="font-semibold text-[#111111]">Integraciones a medida</p>
                  <p className="text-sm text-[#6E6E73] mt-1">API, portales de siniestros y reporting personalizado.</p>
                </div>
              </div>
            </div>
          </FadeUp>
        </div>
      </Section>

      {/* ═════════ CTA FINAL ═════════ */}
      <Section tone="subtle">
        <FadeUp>
          <div className="rounded-[2rem] bg-[#111111] px-6 sm:px-16 py-16 sm:py-28 text-center relative overflow-hidden">
            <div className="absolute -top-20 -right-20 w-80 h-80 bg-[#0055FF]/30 rounded-full blur-3xl pointer-events-none" aria-hidden />
            <div className="absolute -bottom-20 -left-20 w-80 h-80 bg-[#0055FF]/20 rounded-full blur-3xl pointer-events-none" aria-hidden />
            <div className="relative">
              <h2 className="font-[700] tracking-[-0.035em] text-3xl sm:text-5xl leading-[1.05] text-white max-w-3xl mx-auto">
                Tu móvil merece una segunda vida.
              </h2>
              <p className="mt-6 text-lg text-white/70 max-w-xl mx-auto leading-relaxed">
                Diagnóstico gratuito. Recogida a domicilio. Reparación en 1,6 días de media.
              </p>
              <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
                <CTAButton to="/presupuesto" variant="primary" withArrow testid="home-bottomcta-presupuesto">
                  Pedir presupuesto ahora
                </CTAButton>
                <Link
                  to="/consulta"
                  className="inline-flex items-center gap-2 text-white/80 hover:text-white px-5 py-3 text-sm font-medium transition-colors"
                >
                  Seguir una reparación
                  <ArrowRight className="w-4 h-4" strokeWidth={2.5} />
                </Link>
              </div>
            </div>
          </div>
        </FadeUp>
      </Section>
    </>
  );
}

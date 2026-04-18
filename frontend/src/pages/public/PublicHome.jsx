import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Smartphone,
  ShieldCheck,
  Clock3,
  Star,
  Truck,
  Building2,
  Handshake,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';
import {
  Section,
  Container,
  Eyebrow,
  H1,
  H2,
  H3,
  Lead,
  Body,
  CTAButton,
  Card,
  FadeUp,
} from '../../components/public/ui';

const HERO_IMG =
  'https://images.unsplash.com/photo-1595284842948-0d0530153883?auto=format&fit=crop&w=1400&q=80';

const servicios = [
  { icon: Smartphone, title: 'Pantalla', desc: 'OLED, táctil, cristal. Originales.' },
  { icon: ShieldCheck, title: 'Batería', desc: 'Autonomía como el primer día.' },
  { icon: Clock3, title: 'Placa base', desc: 'Diagnóstico microscópico.' },
  { icon: Star, title: 'Cámara', desc: 'Lente y sensor restaurados.' },
];

const razones = [
  {
    title: 'Diagnóstico gratis en 15 min.',
    desc: 'Te decimos qué tiene y cuánto cuesta antes de tocar nada.',
  },
  {
    title: 'Reparado el mismo día.',
    desc: 'El 80% de las reparaciones salen del taller en menos de 24 horas.',
  },
  {
    title: '3 meses de garantía.',
    desc: 'Escrita y real. Si algo falla en la reparación, te lo resolvemos.',
  },
];

export default function PublicHome() {
  return (
    <>
      {/* ══════ HERO ══════ */}
      <section className="pt-32 sm:pt-40 pb-16 sm:pb-24 bg-white overflow-hidden">
        <Container>
          <div className="grid lg:grid-cols-12 gap-12 lg:gap-16 items-center">
            <div className="lg:col-span-6">
              <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                className="space-y-8"
              >
                <Eyebrow>Servicio técnico oficial · España</Eyebrow>
                <H1>
                  Tu móvil, como el <span className="text-[#0055FF]">primer día</span>.
                </H1>
                <Lead className="max-w-xl">
                  Reparación profesional de smartphones con diagnóstico gratuito, recambios de calidad y garantía escrita. Sin sorpresas.
                </Lead>
                <div className="flex flex-wrap items-center gap-3 pt-2">
                  <CTAButton to="/presupuesto" variant="primary" withArrow testid="home-cta-presupuesto">
                    Pedir presupuesto
                  </CTAButton>
                  <CTAButton to="/consulta" variant="secondary" testid="home-cta-seguimiento">
                    Seguir mi reparación
                  </CTAButton>
                </div>
                <div className="pt-4 flex items-center gap-6 text-sm text-[#6E6E73]">
                  <span className="inline-flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-[#0055FF]" strokeWidth={2.5} />
                    Diagnóstico gratuito
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-[#0055FF]" strokeWidth={2.5} />
                    Recogida a domicilio
                  </span>
                </div>
              </motion.div>
            </div>

            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
              className="lg:col-span-6"
            >
              <div className="relative rounded-3xl overflow-hidden bg-[#F5F5F7] aspect-[4/3] lg:aspect-[5/4]">
                <img
                  src={HERO_IMG}
                  alt="Técnico reparando un smartphone"
                  className="w-full h-full object-cover"
                  loading="eager"
                />
              </div>
            </motion.div>
          </div>
        </Container>
      </section>

      {/* ══════ SERVICIOS — grid minimal ══════ */}
      <Section tone="subtle" id="servicios">
        <div className="text-center max-w-2xl mx-auto mb-16 sm:mb-20">
          <FadeUp>
            <Eyebrow className="mb-4">Qué reparamos</Eyebrow>
            <H2>Todo lo que tu móvil necesita.</H2>
          </FadeUp>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {servicios.map((s, i) => (
            <FadeUp key={s.title} delay={i * 0.05}>
              <Card tone="default" className="h-full">
                <s.icon className="w-7 h-7 text-[#0055FF]" strokeWidth={1.75} />
                <H3 className="mt-6">{s.title}</H3>
                <p className="mt-2 text-[#6E6E73]">{s.desc}</p>
              </Card>
            </FadeUp>
          ))}
        </div>
        <div className="mt-14 text-center">
          <CTAButton to="/servicios" variant="ghost" withArrow testid="home-link-todos-servicios">
            Ver todos los servicios
          </CTAButton>
        </div>
      </Section>

      {/* ══════ POR QUÉ REVIX ══════ */}
      <Section>
        <div className="grid lg:grid-cols-12 gap-12 lg:gap-20 items-start">
          <div className="lg:col-span-5 lg:sticky lg:top-28">
            <FadeUp>
              <Eyebrow className="mb-4">Por qué Revix</Eyebrow>
              <H2>
                Claridad,<br />velocidad,<br />respaldo.
              </H2>
            </FadeUp>
          </div>
          <div className="lg:col-span-7 space-y-14">
            {razones.map((r, i) => (
              <FadeUp key={r.title} delay={i * 0.05}>
                <div className="border-t border-[#E5E5EA] pt-10">
                  <H3>{r.title}</H3>
                  <p className="mt-3 text-lg text-[#6E6E73] leading-relaxed">{r.desc}</p>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </Section>

      {/* ══════ CÓMO FUNCIONA ══════ */}
      <Section tone="subtle">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <FadeUp>
            <Eyebrow className="mb-4">Cómo funciona</Eyebrow>
            <H2>Tres pasos. Sin complicaciones.</H2>
          </FadeUp>
        </div>
        <div className="grid md:grid-cols-3 gap-5">
          {[
            { n: '01', title: 'Cuéntanos la avería', desc: 'En 2 minutos, desde el móvil o el ordenador.' },
            { n: '02', title: 'Nosotros lo recogemos', desc: 'Recogida a domicilio gratuita en toda España.' },
            { n: '03', title: 'Lo recibes reparado', desc: 'Con garantía escrita y seguimiento online.' },
          ].map((p, i) => (
            <FadeUp key={p.n} delay={i * 0.08}>
              <Card tone="default" className="h-full">
                <span className="text-[#0055FF] font-[800] text-2xl tracking-tight">{p.n}</span>
                <H3 className="mt-4">{p.title}</H3>
                <p className="mt-2 text-[#6E6E73]">{p.desc}</p>
              </Card>
            </FadeUp>
          ))}
        </div>
      </Section>

      {/* ══════ B2B SECTION ══════ */}
      <Section tone="dark">
        <div className="grid lg:grid-cols-12 gap-10 items-center">
          <FadeUp className="lg:col-span-7">
            <Eyebrow className="mb-4 text-[#5C86FF]">Canal profesional</Eyebrow>
            <h2 className="font-[700] tracking-[-0.035em] text-3xl sm:text-5xl leading-[1.05] text-white">
              Partners y aseguradoras.<br />
              <span className="text-white/60">Un único proveedor técnico.</span>
            </h2>
            <p className="mt-6 text-lg text-white/70 max-w-xl leading-relaxed">
              Integración directa con Insurama, SLA por reparación, trazabilidad completa y un panel dedicado a tu volumen. Operamos para aseguradoras y talleres en toda España.
            </p>
          </FadeUp>
          <FadeUp className="lg:col-span-5" delay={0.1}>
            <div className="grid grid-cols-1 gap-4">
              <Link
                to="/aseguradoras"
                className="group rounded-3xl bg-white/5 hover:bg-white/10 border border-white/10 p-8 transition-colors"
                data-testid="home-link-aseguradoras"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <span className="w-10 h-10 rounded-full bg-white/10 inline-flex items-center justify-center">
                      <Building2 className="w-5 h-5 text-white" strokeWidth={1.75} />
                    </span>
                    <div>
                      <p className="text-white font-semibold text-lg">Aseguradoras</p>
                      <p className="text-white/60 text-sm mt-0.5">Volumen, SLA y reporting.</p>
                    </div>
                  </div>
                  <ArrowRight className="w-5 h-5 text-white/60 group-hover:text-white group-hover:translate-x-0.5 transition-all" />
                </div>
              </Link>
              <Link
                to="/partners"
                className="group rounded-3xl bg-white/5 hover:bg-white/10 border border-white/10 p-8 transition-colors"
                data-testid="home-link-partners"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <span className="w-10 h-10 rounded-full bg-white/10 inline-flex items-center justify-center">
                      <Handshake className="w-5 h-5 text-white" strokeWidth={1.75} />
                    </span>
                    <div>
                      <p className="text-white font-semibold text-lg">Partners</p>
                      <p className="text-white/60 text-sm mt-0.5">Reparaciones white-label.</p>
                    </div>
                  </div>
                  <ArrowRight className="w-5 h-5 text-white/60 group-hover:text-white group-hover:translate-x-0.5 transition-all" />
                </div>
              </Link>
            </div>
          </FadeUp>
        </div>
      </Section>

      {/* ══════ CTA FINAL ══════ */}
      <Section>
        <FadeUp>
          <div className="rounded-[2rem] bg-[#F5F5F7] px-8 sm:px-16 py-20 sm:py-28 text-center">
            <H2 className="max-w-3xl mx-auto">¿Listo para recuperar tu móvil?</H2>
            <p className="mt-6 text-lg text-[#6E6E73] max-w-xl mx-auto leading-relaxed">
              Diagnóstico gratuito. Recogida a domicilio. Sin compromiso.
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
              <CTAButton to="/presupuesto" variant="primary" withArrow testid="home-bottomcta-presupuesto">
                Pedir presupuesto
              </CTAButton>
              <CTAButton to="/contacto" variant="secondary" testid="home-bottomcta-contacto">
                Hablar con alguien
              </CTAButton>
            </div>
          </div>
        </FadeUp>
      </Section>
    </>
  );
}

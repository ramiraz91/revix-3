import { ShieldCheck, LineChart, Clock, Building2, FileText, Plug, Headphones, CheckCircle2, PhoneCall, FileCheck2, Radar } from 'lucide-react';
import {
  PageHero,
  Section,
  Container,
  H2,
  H3,
  Eyebrow,
  Lead,
  Card,
  CTAButton,
  FadeUp,
} from '../../components/public/ui';

const ventajas = [
  { icon: Plug, title: 'Integración Insurama', desc: 'Recepción y cierre de siniestros directamente en nuestro sistema, sin intermediarios ni emails.' },
  { icon: Clock, title: 'SLA por reparación', desc: 'Recogida, diagnóstico y entrega con tiempos medidos y reportados por ticket.' },
  { icon: Headphones, title: 'Call center dedicado', desc: 'Un equipo asignado exclusivamente a tu operativa. Sin colas ni tickets al vacío.' },
  { icon: LineChart, title: 'Reporting mensual', desc: 'Volumen, desviaciones, coste medio y NPS. En abierto, sin cajas negras.' },
  { icon: Building2, title: 'Cobertura nacional', desc: 'Red logística propia y protocolos homologados para toda España.' },
  { icon: ShieldCheck, title: 'Garantía escrita', desc: '3 meses mínimo por cada reparación autorizada. Trazabilidad completa.' },
  { icon: FileText, title: 'Facturación centralizada', desc: 'Liquidaciones agrupadas por nº de autorización y conciliadas por siniestro.' },
];

const fases = [
  { icon: Radar, step: '01', title: 'Minuto 1 — Recepción', desc: 'Apertura automática del siniestro desde Insurama con asignación inmediata de técnico y ticket.' },
  { icon: FileCheck2, step: '02', title: 'Verificación', desc: 'Validación de cobertura, comprobación de IMEI, peritaje técnico y documentación fotográfica del estado del dispositivo.' },
  { icon: PhoneCall, step: '03', title: 'Gestión activa', desc: 'Call center dedicado comunicando al asegurado y al gestor en cada hito. Nada queda al azar.' },
  { icon: CheckCircle2, step: '04', title: 'Cierre', desc: 'Entrega con garantía escrita, informe técnico firmado y liquidación conciliada con el número de autorización.' },
];

export default function PublicAseguradoras() {
  return (
    <>
      <PageHero
        eyebrow="Canal aseguradoras"
        title="El proveedor técnico de tus siniestros de telefonía."
        subtitle="Operativo con integración directa a Insurama. Un único interlocutor para toda la cadena técnica."
      >
        <CTAButton to="/contacto" variant="primary" withArrow testid="aseguradoras-cta-contacto">
          Hablar con nosotros
        </CTAButton>
      </PageHero>

      {/* ═════════ CONTROL TOTAL DEL SINIESTRO ═════════ */}
      <Section>
        <div className="grid lg:grid-cols-12 gap-12 lg:gap-16 mb-16 lg:mb-20">
          <FadeUp className="lg:col-span-5">
            <Eyebrow className="mb-4">Control end-to-end</Eyebrow>
            <H2>Control total del siniestro.<br />Desde el minuto 1 hasta el cierre.</H2>
          </FadeUp>
          <FadeUp className="lg:col-span-7" delay={0.1}>
            <Lead>
              Asumimos todo el recorrido técnico del siniestro: apertura, verificación, gestión con el asegurado y cierre con liquidación. Un <strong className="text-[#111111] font-semibold">call center dedicado</strong> a tu cuenta se encarga de que cada caso llegue a buen puerto — sin fricciones ni seguimiento por tu parte.
            </Lead>
          </FadeUp>
        </div>

        {/* Timeline visual de las 4 fases */}
        <div className="relative">
          {/* Línea conectora (solo desktop) */}
          <div className="hidden lg:block absolute top-[44px] left-[10%] right-[10%] h-px bg-gradient-to-r from-[#0055FF]/20 via-[#0055FF]/40 to-[#0055FF]/20" aria-hidden />
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5 relative">
            {fases.map((f, i) => (
              <FadeUp key={f.step} delay={i * 0.08}>
                <div className="bg-white rounded-3xl p-8 border border-[#E5E5EA] h-full hover:shadow-[0_20px_60px_-20px_rgba(0,85,255,0.15)] hover:-translate-y-1 transition-all duration-300">
                  <div className="flex items-start justify-between mb-8">
                    <div className="w-12 h-12 rounded-2xl bg-[#0055FF] text-white flex items-center justify-center shadow-[0_8px_24px_-8px_rgba(0,85,255,0.5)]">
                      <f.icon className="w-5 h-5" strokeWidth={2} />
                    </div>
                    <span className="text-[#0055FF] font-[800] text-sm tracking-widest">{f.step}</span>
                  </div>
                  <H3>{f.title}</H3>
                  <p className="mt-3 text-[#6E6E73] leading-relaxed">{f.desc}</p>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </Section>

      {/* ═════════ VENTAJAS ═════════ */}
      <Section tone="subtle">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <FadeUp>
            <Eyebrow className="mb-4">Por qué Revix</Eyebrow>
            <H2>Operación en serio,<br />sin letra pequeña.</H2>
          </FadeUp>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {ventajas.map((v, i) => (
            <FadeUp key={v.title} delay={i * 0.05}>
              <Card tone="default" className="h-full">
                <v.icon className="w-7 h-7 text-[#0055FF]" strokeWidth={1.75} />
                <H3 className="mt-6">{v.title}</H3>
                <p className="mt-3 text-[#6E6E73] leading-relaxed">{v.desc}</p>
              </Card>
            </FadeUp>
          ))}
        </div>
      </Section>

      <Section tone="dark">
        <Container className="max-w-3xl text-center">
          <FadeUp>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5C86FF] mb-5">¿Eres aseguradora?</p>
            <h2 className="font-[700] tracking-[-0.035em] text-3xl sm:text-5xl leading-[1.05] text-white">
              Hablemos de tu volumen.
            </h2>
            <p className="mt-6 text-lg text-white/70 leading-relaxed">
              En 30 minutos te explicamos cómo operamos y evaluamos si podemos encajar en tu SLA actual.
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
              <CTAButton to="/contacto" variant="primary" withArrow testid="aseguradoras-bottomcta-contacto">
                Solicitar reunión
              </CTAButton>
            </div>
          </FadeUp>
        </Container>
      </Section>
    </>
  );
}

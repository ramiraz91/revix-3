import { ShieldCheck, LineChart, Clock, Building2, FileText, Plug } from 'lucide-react';
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
  { icon: LineChart, title: 'Reporting mensual', desc: 'Volumen, desviaciones, coste medio y NPS. En abierto, sin cajas negras.' },
  { icon: Building2, title: 'Cobertura nacional', desc: 'Red logística propia y protocolos homologados para toda España.' },
  { icon: ShieldCheck, title: 'Garantía escrita', desc: '3 meses mínimo por cada reparación autorizada. Trazabilidad completa.' },
  { icon: FileText, title: 'Facturación centralizada', desc: 'Liquidaciones agrupadas por nº de autorización y conciliadas por siniestro.' },
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

      <Section>
        <div className="text-center max-w-2xl mx-auto mb-16">
          <FadeUp>
            <Eyebrow className="mb-4">Por qué Revix</Eyebrow>
            <H2>Operación en serio,<br />sin letra pequeña.</H2>
          </FadeUp>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {ventajas.map((v, i) => (
            <FadeUp key={v.title} delay={i * 0.05}>
              <Card tone="subtle" className="h-full">
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

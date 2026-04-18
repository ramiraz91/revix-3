import { Handshake, Wrench, Package, TrendingUp, UserCheck, Sparkles } from 'lucide-react';
import {
  PageHero,
  Section,
  Container,
  H2,
  H3,
  Eyebrow,
  Card,
  CTAButton,
  FadeUp,
} from '../../components/public/ui';

const ventajas = [
  { icon: Wrench, title: 'Reparaciones white-label', desc: 'Tú cobras a tu cliente, nosotros ejecutamos. Entregamos con tu marca o la nuestra.' },
  { icon: Package, title: 'Logística integrada', desc: 'Recogida y entrega en tu punto de venta. Sin que tu cliente salga de tu tienda.' },
  { icon: TrendingUp, title: 'Margen mejorado', desc: 'Precios de partner y sin estructura propia de taller.' },
  { icon: UserCheck, title: 'Tu contacto dedicado', desc: 'Una persona asignada a tu cuenta. Sin tickets al vacío.' },
  { icon: Sparkles, title: 'Formación continua', desc: 'Boletines técnicos y soporte en casos difíciles para tu equipo.' },
  { icon: Handshake, title: 'Acuerdos flexibles', desc: 'Adaptamos volumen, tarifa y SLA a tu realidad de negocio.' },
];

export default function PublicPartners() {
  return (
    <>
      <PageHero
        eyebrow="Canal partners"
        title="Reparaciones para tu tienda o distribución."
        subtitle="Convertimos reparaciones complejas en una línea más de tu negocio. Tú vendes, nosotros ejecutamos."
      >
        <CTAButton to="/contacto" variant="primary" withArrow testid="partners-cta-contacto">
          Ser partner
        </CTAButton>
      </PageHero>

      <Section>
        <div className="text-center max-w-2xl mx-auto mb-16">
          <FadeUp>
            <Eyebrow className="mb-4">El acuerdo</Eyebrow>
            <H2>Simple, serio, escalable.</H2>
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

      <Section tone="subtle">
        <Container className="max-w-3xl text-center">
          <FadeUp>
            <H2>¿Hablamos de tu caso?</H2>
            <p className="mt-6 text-lg text-[#6E6E73] leading-relaxed">
              Nos cuentas qué vendes, qué volumen mueves y te proponemos el esquema que mejor encaja.
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
              <CTAButton to="/contacto" variant="primary" withArrow testid="partners-bottomcta-contacto">
                Solicitar reunión
              </CTAButton>
              <CTAButton to="/aseguradoras" variant="secondary" testid="partners-link-aseguradoras">
                Soy aseguradora
              </CTAButton>
            </div>
          </FadeUp>
        </Container>
      </Section>
    </>
  );
}

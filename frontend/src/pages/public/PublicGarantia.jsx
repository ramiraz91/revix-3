import { ShieldCheck, CheckCircle2, XCircle } from 'lucide-react';
import {
  PageHero,
  Section,
  Container,
  H2,
  H3,
  Card,
  FadeUp,
  CTAButton,
} from '../../components/public/ui';

const incluye = [
  'Mano de obra: cualquier manipulación posterior derivada de la reparación original.',
  'Componentes sustituidos: el recambio exacto que hemos cambiado.',
  'Funcionamiento correcto: si algo de lo reparado falla, lo solucionamos sin coste.',
];

const noIncluye = [
  'Daños por caídas, golpes o líquidos ocurridos después de la reparación.',
  'Averías en componentes distintos al reparado.',
  'Modificaciones o reparaciones realizadas por terceros.',
];

export default function PublicGarantia() {
  return (
    <>
      <PageHero
        eyebrow="Nuestra garantía"
        title="3 meses. Escrita y real."
        subtitle="Toda reparación que pasa por Revix sale con garantía escrita. Sin asteriscos. Sin laberintos."
      >
        <CTAButton to="/presupuesto" variant="primary" withArrow testid="garantia-cta-presupuesto">
          Pedir presupuesto
        </CTAButton>
      </PageHero>

      <Section>
        <Container className="max-w-4xl">
          <div className="grid md:grid-cols-2 gap-6">
            <FadeUp>
              <Card tone="subtle" className="h-full">
                <ShieldCheck className="w-7 h-7 text-[#0055FF]" strokeWidth={1.75} />
                <H3 className="mt-6">Qué cubre</H3>
                <ul className="mt-6 space-y-4">
                  {incluye.map((x) => (
                    <li key={x} className="flex gap-3">
                      <CheckCircle2 className="w-5 h-5 text-[#0055FF] mt-0.5 flex-shrink-0" strokeWidth={2} />
                      <span className="text-[#3A3A3C] leading-relaxed">{x}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            </FadeUp>
            <FadeUp delay={0.08}>
              <Card tone="subtle" className="h-full">
                <XCircle className="w-7 h-7 text-[#6E6E73]" strokeWidth={1.75} />
                <H3 className="mt-6">Qué no cubre</H3>
                <ul className="mt-6 space-y-4">
                  {noIncluye.map((x) => (
                    <li key={x} className="flex gap-3">
                      <XCircle className="w-5 h-5 text-[#6E6E73] mt-0.5 flex-shrink-0" strokeWidth={2} />
                      <span className="text-[#3A3A3C] leading-relaxed">{x}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            </FadeUp>
          </div>
        </Container>
      </Section>

      <Section tone="subtle">
        <Container className="max-w-2xl text-center">
          <FadeUp>
            <H2>¿Quieres más tranquilidad?</H2>
            <p className="mt-6 text-lg text-[#6E6E73] leading-relaxed">
              Con la garantía extendida amplías cobertura hasta 12 meses y añades protección ante accidentes.
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
              <CTAButton to="/garantia-extendida" variant="primary" withArrow testid="garantia-link-extendida">
                Ver garantía extendida
              </CTAButton>
              <CTAButton to="/contacto" variant="secondary" testid="garantia-link-contacto">
                Tengo una duda
              </CTAButton>
            </div>
          </FadeUp>
        </Container>
      </Section>
    </>
  );
}

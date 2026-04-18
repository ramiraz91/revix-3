import { Check } from 'lucide-react';
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

const planes = [
  {
    nombre: 'Básica',
    precio: 'Incluida',
    duracion: '3 meses',
    destacado: false,
    features: [
      'Cobertura sobre la reparación realizada',
      'Mano de obra',
      'Componente sustituido',
    ],
  },
  {
    nombre: 'Extendida',
    precio: 'Desde 4,90 €/mes',
    duracion: '12 meses',
    destacado: true,
    features: [
      'Todo lo de la garantía básica',
      'Ampliación a 12 meses',
      'Descuento en próximas reparaciones',
      'Prioridad en cola de servicio',
    ],
  },
  {
    nombre: 'Total',
    precio: 'Consultar',
    duracion: '12 meses',
    destacado: false,
    features: [
      'Todo lo de la Extendida',
      'Protección por accidente (1 evento)',
      'Sustitución urgente disponible',
      'Seguimiento VIP',
    ],
  },
];

export default function PublicGarantiaExtendida() {
  return (
    <>
      <PageHero
        eyebrow="Garantía extendida"
        title="Tranquilidad que se puede medir."
        subtitle="Amplía tu garantía hasta 12 meses y añade protección ante accidentes. Sin letra pequeña."
      >
        <CTAButton to="/contacto" variant="primary" withArrow testid="ge-cta-contratar">
          Contratar ahora
        </CTAButton>
      </PageHero>

      <Section>
        <div className="grid md:grid-cols-3 gap-5">
          {planes.map((p, i) => (
            <FadeUp key={p.nombre} delay={i * 0.05}>
              <div
                className={`rounded-3xl p-8 sm:p-10 h-full flex flex-col transition-all ${
                  p.destacado
                    ? 'bg-[#111111] text-white border-2 border-[#0055FF]'
                    : 'bg-[#F5F5F7] border border-transparent'
                }`}
              >
                {p.destacado && (
                  <span className="self-start text-xs font-semibold uppercase tracking-[0.14em] bg-[#0055FF] text-white px-3 py-1 rounded-full mb-6">
                    Recomendado
                  </span>
                )}
                <H3 className={p.destacado ? '!text-white' : ''}>{p.nombre}</H3>
                <p className={`mt-4 text-3xl font-[700] tracking-tight ${p.destacado ? 'text-white' : 'text-[#111111]'}`}>
                  {p.precio}
                </p>
                <p className={`text-sm mt-1 ${p.destacado ? 'text-white/60' : 'text-[#6E6E73]'}`}>Duración: {p.duracion}</p>

                <ul className="mt-8 space-y-3 flex-1">
                  {p.features.map((f) => (
                    <li key={f} className="flex gap-3">
                      <Check className={`w-5 h-5 mt-0.5 flex-shrink-0 ${p.destacado ? 'text-[#5C86FF]' : 'text-[#0055FF]'}`} strokeWidth={2.5} />
                      <span className={`${p.destacado ? 'text-white/80' : 'text-[#3A3A3C]'} leading-relaxed`}>{f}</span>
                    </li>
                  ))}
                </ul>

                <CTAButton
                  to="/contacto"
                  variant={p.destacado ? 'primary' : 'dark'}
                  className="mt-10 w-full"
                  testid={`ge-plan-${p.nombre.toLowerCase()}`}
                >
                  Contratar
                </CTAButton>
              </div>
            </FadeUp>
          ))}
        </div>
      </Section>

      <Section tone="subtle">
        <Container className="max-w-2xl text-center">
          <FadeUp>
            <H2>¿Dudas sobre qué plan elegir?</H2>
            <p className="mt-6 text-lg text-[#6E6E73] leading-relaxed">
              Escríbenos y te asesoramos sin compromiso según el valor de tu dispositivo y tu uso.
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
              <CTAButton to="/contacto" variant="primary" withArrow testid="ge-bottomcta-contacto">
                Contactar
              </CTAButton>
              <CTAButton to="/garantia" variant="secondary" testid="ge-link-garantia">
                Ver garantía estándar
              </CTAButton>
            </div>
          </FadeUp>
        </Container>
      </Section>
    </>
  );
}

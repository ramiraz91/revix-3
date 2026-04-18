import {
  Smartphone,
  BatteryFull,
  Cpu,
  Camera,
  Speaker,
  Droplets,
  Wifi,
  MicVocal,
} from 'lucide-react';
import {
  PageHero,
  Section,
  H3,
  CTAButton,
  Card,
  FadeUp,
} from '../../components/public/ui';

const servicios = [
  { icon: Smartphone, title: 'Pantalla', desc: 'Cambio de pantalla completa, táctil, cristal. OEM y originales.' },
  { icon: BatteryFull, title: 'Batería', desc: 'Sustitución con diagnóstico de ciclos y salud de la celda.' },
  { icon: Cpu, title: 'Placa base', desc: 'Microsoldadura y reparación de componentes con lupa binocular.' },
  { icon: Camera, title: 'Cámara', desc: 'Cambio de módulo, lente y sensor. Calibración posterior.' },
  { icon: Speaker, title: 'Altavoz', desc: 'Auricular, altavoz principal y limpieza por ultrasonidos.' },
  { icon: MicVocal, title: 'Micrófono', desc: 'Sustitución y pruebas de grabación y llamada.' },
  { icon: Droplets, title: 'Mojado / daño por líquido', desc: 'Tratamiento completo en cámara de ultrasonidos.' },
  { icon: Wifi, title: 'Antena y conectividad', desc: 'Wi-Fi, Bluetooth y cobertura móvil.' },
];

export default function PublicServicios() {
  return (
    <>
      <PageHero
        eyebrow="Catálogo de servicios"
        title="Reparaciones con criterio técnico."
        subtitle="Usamos recambios de calidad y protocolos verificados en cada paso. Diagnóstico gratuito, sin compromiso."
      >
        <CTAButton to="/presupuesto" variant="primary" withArrow testid="servicios-cta-presupuesto">
          Pedir presupuesto
        </CTAButton>
      </PageHero>

      <Section>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {servicios.map((s, i) => (
            <FadeUp key={s.title} delay={i * 0.04}>
              <Card tone="subtle" className="h-full">
                <s.icon className="w-7 h-7 text-[#0055FF]" strokeWidth={1.75} />
                <H3 className="mt-6">{s.title}</H3>
                <p className="mt-3 text-[#6E6E73] leading-relaxed">{s.desc}</p>
              </Card>
            </FadeUp>
          ))}
        </div>
      </Section>

      <Section tone="subtle">
        <FadeUp>
          <div className="text-center max-w-2xl mx-auto">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#0055FF]">
              ¿Tu modelo no está en la lista?
            </p>
            <h2 className="mt-4 font-[700] text-[#111111] tracking-[-0.035em] text-3xl sm:text-5xl leading-[1.05]">
              Reparamos cualquier marca.
            </h2>
            <p className="mt-5 text-lg text-[#6E6E73] leading-relaxed">
              Apple, Samsung, Xiaomi, Google, Huawei, OPPO, Realme, OnePlus y más. Cuéntanos qué le pasa y en minutos tienes una estimación.
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
              <CTAButton to="/presupuesto" variant="primary" withArrow testid="servicios-bottomcta-presupuesto">
                Pedir presupuesto
              </CTAButton>
              <CTAButton to="/contacto" variant="secondary" testid="servicios-bottomcta-contacto">
                Contactar
              </CTAButton>
            </div>
          </div>
        </FadeUp>
      </Section>
    </>
  );
}

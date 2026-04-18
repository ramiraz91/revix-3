import { Download, Check } from 'lucide-react';
import {
  PageHero,
  Section,
  Container,
  H3,
  Card,
  FadeUp,
  CTAButton,
} from '../../components/public/ui';

const assets = [
  {
    title: 'Logo principal — SVG',
    desc: 'Vectorizado. Escala infinita, peso mínimo.',
    file: '/brand/revix-logo.svg',
    preview: '/brand/revix-logo.svg',
    bg: 'bg-white',
  },
  {
    title: 'Logo principal — PNG @4x (2048px)',
    desc: 'Alta resolución para web, presentaciones y papelería.',
    file: '/brand/revix-logo.png',
    preview: '/brand/revix-logo.png',
    bg: 'bg-white',
  },
  {
    title: 'Logo sobre fondo oscuro — SVG',
    desc: 'Vectorizado, texto blanco. Para fondos oscuros y vídeo.',
    file: '/brand/revix-logo-dark.svg',
    preview: '/brand/revix-logo-dark.svg',
    bg: 'bg-[#111111]',
  },
  {
    title: 'Logo sobre fondo oscuro — PNG (2048px)',
    desc: 'Versión rasterizada para fondos oscuros.',
    file: '/brand/revix-logo-dark.png',
    preview: '/brand/revix-logo-dark.png',
    bg: 'bg-[#111111]',
  },
  {
    title: 'Isologo "R" — SVG',
    desc: 'Icono cuadrado con la "R" blanca sobre fondo azul. Para favicons, app icons y redes.',
    file: '/brand/revix-isologo.svg',
    preview: '/brand/revix-isologo.svg',
    bg: 'bg-[#F5F5F7]',
  },
  {
    title: 'Isologo "R" — PNG 1024px',
    desc: 'Para apps, avatares de perfil y redes sociales.',
    file: '/brand/revix-isologo-1024.png',
    preview: '/brand/revix-isologo-1024.png',
    bg: 'bg-[#F5F5F7]',
  },
];

const reglas = [
  'Usa el logo sobre fondos con suficiente contraste.',
  'Mantén el color azul oficial #0055FF en el punto.',
  'Respeta un margen libre equivalente a la altura de la "R" alrededor del logo.',
  'No rotes, deformes, ni añadas sombras o efectos.',
];

export default function PublicBrand() {
  return (
    <>
      <PageHero
        eyebrow="Marca"
        title="Assets de Revix.es"
        subtitle="Descarga el logotipo en SVG vectorizado y PNG en alta resolución. Para medios, partners y material interno."
      >
        <CTAButton
          href="/brand/revix-logo.svg"
          variant="primary"
          withArrow
          testid="brand-cta-download-svg"
        >
          Descargar SVG
        </CTAButton>
        <CTAButton
          href="/brand/revix-logo.png"
          variant="secondary"
          testid="brand-cta-download-png"
        >
          Descargar PNG
        </CTAButton>
      </PageHero>

      <Section>
        <div className="grid md:grid-cols-2 gap-5">
          {assets.map((a, i) => (
            <FadeUp key={a.file} delay={i * 0.04}>
              <Card tone="default" className="h-full flex flex-col">
                <div className={`rounded-2xl ${a.bg} aspect-[16/7] flex items-center justify-center overflow-hidden mb-6`}>
                  <img
                    src={a.preview}
                    alt={a.title}
                    className="max-h-20 sm:max-h-24 w-auto"
                    loading="lazy"
                  />
                </div>
                <H3>{a.title}</H3>
                <p className="mt-2 text-[#6E6E73] leading-relaxed flex-1">{a.desc}</p>
                <a
                  href={a.file}
                  download
                  className="mt-6 inline-flex items-center justify-center gap-2 w-full sm:w-auto self-start bg-[#F5F5F7] hover:bg-[#E5E5EA] text-[#111111] font-semibold rounded-full px-6 py-3 transition-colors text-sm"
                  data-testid={`brand-download-${a.file}`}
                >
                  <Download className="w-4 h-4" strokeWidth={2.5} />
                  Descargar
                </a>
              </Card>
            </FadeUp>
          ))}
        </div>
      </Section>

      <Section tone="subtle">
        <Container className="max-w-3xl">
          <FadeUp>
            <H3>Uso correcto del logo</H3>
            <ul className="mt-8 space-y-4">
              {reglas.map((r) => (
                <li key={r} className="flex gap-3 text-lg text-[#3A3A3C] leading-relaxed">
                  <Check className="w-5 h-5 text-[#0055FF] mt-1.5 flex-shrink-0" strokeWidth={2.5} />
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </FadeUp>
        </Container>
      </Section>
    </>
  );
}

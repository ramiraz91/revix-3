import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Search } from 'lucide-react';
import {
  PageHero,
  Section,
  Container,
  H3,
  FadeUp,
  CTAButton,
} from '../../components/public/ui';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function PublicFAQs() {
  const [faqs, setFaqs] = useState({});
  const [loading, setLoading] = useState(true);
  const [busqueda, setBusqueda] = useState('');
  const [expandido, setExpandido] = useState({});

  useEffect(() => {
    const cargarFaqs = async () => {
      try {
        const res = await fetch(`${API_URL}/api/faqs/public`);
        const data = await res.json();
        setFaqs(data.faqs_por_categoria || {});
      } catch (error) {
        console.error('Error cargando FAQs:', error);
      } finally {
        setLoading(false);
      }
    };
    cargarFaqs();
  }, []);

  const togglePregunta = (id) => setExpandido((p) => ({ ...p, [id]: !p[id] }));

  const faqsFiltradas = {};
  Object.entries(faqs).forEach(([catKey, catData]) => {
    const filtradas = (catData.faqs || []).filter((faq) => {
      if (!busqueda) return true;
      const s = busqueda.toLowerCase();
      return faq.pregunta.toLowerCase().includes(s) || faq.respuesta.toLowerCase().includes(s);
    });
    if (filtradas.length > 0) faqsFiltradas[catKey] = { ...catData, faqs: filtradas };
  });

  const categorias = Object.entries(faqsFiltradas);
  const totalFaqs = categorias.reduce((acc, [, d]) => acc + (d.faqs?.length || 0), 0);

  return (
    <>
      <PageHero
        eyebrow="Centro de ayuda"
        title="Preguntas frecuentes."
        subtitle="Encuentra respuesta en segundos. Si no está aquí, escríbenos."
      >
        <div className="w-full max-w-xl relative">
          <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-[#6E6E73]" strokeWidth={1.75} />
          <input
            type="text"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Busca tu duda…"
            className="w-full pl-14 pr-5 py-4 rounded-full bg-[#F5F5F7] border border-transparent focus:border-[#0055FF] focus:bg-white focus:ring-4 focus:ring-[#0055FF]/10 outline-none text-base"
            data-testid="faqs-search"
          />
        </div>
      </PageHero>

      <Section className="!pt-0">
        <Container className="max-w-3xl">
          {loading ? (
            <div className="text-center text-[#6E6E73] py-20">Cargando…</div>
          ) : totalFaqs === 0 ? (
            <FadeUp>
              <div className="text-center py-16">
                <p className="text-[#6E6E73]">No encontramos resultados para "{busqueda}".</p>
                <div className="mt-8">
                  <CTAButton to="/contacto" variant="primary" withArrow testid="faqs-no-results-cta">
                    Escríbenos
                  </CTAButton>
                </div>
              </div>
            </FadeUp>
          ) : (
            <div className="space-y-16">
              {categorias.map(([catKey, catData]) => (
                <FadeUp key={catKey}>
                  <div>
                    <H3 className="mb-8">{catData.nombre || catKey}</H3>
                    <div className="divide-y divide-[#E5E5EA]">
                      {catData.faqs.map((faq) => {
                        const isOpen = expandido[faq.id];
                        return (
                          <div key={faq.id} className="py-6">
                            <button
                              type="button"
                              onClick={() => togglePregunta(faq.id)}
                              className="w-full flex items-start justify-between gap-6 text-left group"
                              data-testid={`faq-${faq.id}`}
                            >
                              <span className="text-lg font-semibold text-[#111111] group-hover:text-[#0055FF] transition-colors">
                                {faq.pregunta}
                              </span>
                              <ChevronDown
                                className={`w-5 h-5 flex-shrink-0 mt-1 text-[#6E6E73] transition-transform ${
                                  isOpen ? 'rotate-180 text-[#0055FF]' : ''
                                }`}
                                strokeWidth={2.5}
                              />
                            </button>
                            <AnimatePresence initial={false}>
                              {isOpen && (
                                <motion.div
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: 'auto', opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  transition={{ duration: 0.25 }}
                                  className="overflow-hidden"
                                >
                                  <p className="mt-4 text-[#6E6E73] leading-relaxed whitespace-pre-wrap">
                                    {faq.respuesta}
                                  </p>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </FadeUp>
              ))}
            </div>
          )}
        </Container>
      </Section>

      <Section tone="subtle">
        <Container className="max-w-2xl text-center">
          <FadeUp>
            <h2 className="font-[700] text-[#111111] tracking-[-0.035em] text-3xl sm:text-4xl">
              ¿No encuentras lo que buscas?
            </h2>
            <p className="mt-4 text-lg text-[#6E6E73]">Nuestro equipo responde en menos de 24 horas.</p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <CTAButton to="/contacto" variant="primary" withArrow testid="faqs-bottomcta-contacto">
                Contactar soporte
              </CTAButton>
            </div>
          </FadeUp>
        </Container>
      </Section>
    </>
  );
}

import { useState } from 'react';
import { Send, Mail, Clock, CheckCircle2, Loader2 } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import {
  PageHero,
  Section,
  Container,
  H3,
  Body,
  FadeUp,
} from '../../components/public/ui';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const fieldClass =
  'w-full rounded-2xl bg-[#F5F5F7] border border-transparent focus:border-[#0055FF] focus:bg-white focus:ring-4 focus:ring-[#0055FF]/10 px-5 py-4 text-base text-[#111111] placeholder:text-[#9E9EA3] outline-none transition-all';

export default function PublicContacto() {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [form, setForm] = useState({ nombre: '', email: '', telefono: '', asunto: '', mensaje: '' });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${BACKEND_URL}/api/web/contacto`, form);
      setSuccess(true);
    } catch {
      toast.error('Error al enviar. Inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <>
        <PageHero
          eyebrow="Mensaje recibido"
          title="Gracias por escribirnos."
          subtitle="Te respondemos en menos de 24 horas laborables al correo indicado."
        />
      </>
    );
  }

  return (
    <>
      <PageHero
        eyebrow="Contacto"
        title="¿Hablamos?"
        subtitle="Escríbenos y te respondemos por el canal que prefieras. Estamos aquí para ayudarte."
      />

      <Section className="!pt-0">
        <Container className="max-w-5xl">
          <div className="grid lg:grid-cols-5 gap-14 lg:gap-20">
            {/* Columna izquierda — info */}
            <FadeUp className="lg:col-span-2 space-y-10">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#111111] mb-4">Email</p>
                <a href="mailto:help@revix.es" className="inline-flex items-center gap-2 text-lg text-[#111111] hover:text-[#0055FF] transition-colors">
                  <Mail className="w-5 h-5 text-[#0055FF]" strokeWidth={1.75} />
                  help@revix.es
                </a>
                <p className="mt-2 text-sm text-[#6E6E73]">Respuesta en menos de 24h laborables.</p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#111111] mb-4">Horario</p>
                <div className="inline-flex items-start gap-2 text-[#111111]">
                  <Clock className="w-5 h-5 mt-0.5 text-[#0055FF]" strokeWidth={1.75} />
                  <div>
                    <p>Lunes a viernes · 9:00 – 19:00</p>
                    <p className="text-sm text-[#6E6E73] mt-1">Sábados · 10:00 – 14:00</p>
                  </div>
                </div>
              </div>
            </FadeUp>

            {/* Columna derecha — formulario */}
            <FadeUp className="lg:col-span-3" delay={0.1}>
              <form onSubmit={handleSubmit} className="space-y-4" data-testid="form-contacto">
                <div className="grid sm:grid-cols-2 gap-4">
                  <input
                    required
                    value={form.nombre}
                    onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                    placeholder="Nombre y apellidos"
                    className={fieldClass}
                    data-testid="input-nombre"
                  />
                  <input
                    required
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    placeholder="Email"
                    className={fieldClass}
                    data-testid="input-email"
                  />
                </div>
                <input
                  value={form.telefono}
                  onChange={(e) => setForm({ ...form, telefono: e.target.value })}
                  placeholder="Teléfono (opcional)"
                  className={fieldClass}
                  data-testid="input-telefono"
                />
                <input
                  required
                  value={form.asunto}
                  onChange={(e) => setForm({ ...form, asunto: e.target.value })}
                  placeholder="Asunto"
                  className={fieldClass}
                  data-testid="input-asunto"
                />
                <textarea
                  required
                  value={form.mensaje}
                  onChange={(e) => setForm({ ...form, mensaje: e.target.value })}
                  placeholder="Cuéntanos qué necesitas..."
                  rows={6}
                  className={`${fieldClass} resize-none`}
                  data-testid="input-mensaje"
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full mt-2 inline-flex items-center justify-center gap-2 bg-[#0055FF] text-white font-semibold rounded-full px-7 py-4 hover:bg-[#0044CC] transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                  data-testid="btn-submit-contacto"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Enviando…
                    </>
                  ) : (
                    <>
                      Enviar mensaje
                      <Send className="w-4 h-4" strokeWidth={2.5} />
                    </>
                  )}
                </button>
              </form>
            </FadeUp>
          </div>
        </Container>
      </Section>
    </>
  );
}

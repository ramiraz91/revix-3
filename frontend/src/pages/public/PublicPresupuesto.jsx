import { useState } from 'react';
import {
  Smartphone, Tablet, Watch, Gamepad2, CheckCircle2, Loader2, ArrowRight,
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import {
  PageHero,
  Section,
  Container,
  H3,
  FadeUp,
  CTAButton,
} from '../../components/public/ui';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const tiposDispositivo = [
  { id: 'smartphone', icon: Smartphone, label: 'Smartphone' },
  { id: 'tablet', icon: Tablet, label: 'Tablet' },
  { id: 'smartwatch', icon: Watch, label: 'Smartwatch' },
  { id: 'consola', icon: Gamepad2, label: 'Consola' },
];

const averiasPorTipo = {
  smartphone: ['Pantalla rota', 'Batería', 'Conector de carga', 'Cámara trasera', 'Cámara frontal', 'Daños por agua', 'Altavoz', 'Micrófono', 'Botones', 'Face ID / Touch ID', 'Placa base', 'Software', 'Tapa trasera', 'Marco/Chasis', 'Otro'],
  tablet: ['Pantalla rota', 'Batería', 'Conector de carga', 'Cámara', 'Daños por agua', 'Botones', 'Altavoz', 'Software', 'Otro'],
  smartwatch: ['Pantalla', 'Batería', 'Corona/botones', 'Sensor de pulso', 'Daños por agua', 'Correa', 'Otro'],
  consola: ['Pantalla', 'Botones/Joy-Con', 'Batería', 'Puerto de carga', 'Ventilador', 'Lector de discos', 'Software', 'Otro'],
};

const comoNosConociste = [
  { id: 'google', label: 'Google / Buscador' },
  { id: 'aseguradora', label: 'Mi compañía aseguradora' },
  { id: 'referido', label: 'Recomendación' },
  { id: 'redes_sociales', label: 'Redes sociales' },
  { id: 'publicidad', label: 'Publicidad online' },
  { id: 'repetidor', label: 'Ya he sido cliente' },
  { id: 'otro', label: 'Otro' },
];

const inputCls =
  'w-full rounded-2xl bg-[#F5F5F7] border border-transparent focus:border-[#0055FF] focus:bg-white focus:ring-4 focus:ring-[#0055FF]/10 px-5 py-4 text-base text-[#111111] placeholder:text-[#9E9EA3] outline-none transition-all';

function Label({ children }) {
  return <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#111111] mb-3">{children}</p>;
}

export default function PublicPresupuesto() {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [form, setForm] = useState({
    tipo_dispositivo: '', marca: '', modelo: '', averias: [], descripcion: '',
    nombre: '', apellidos: '', dni: '', email: '', telefono: '', telefono_alternativo: '',
    direccion: '', codigo_postal: '', ciudad: '', provincia: '',
    como_conociste: '', como_conociste_otro: '',
    notas_adicionales: '',
    acepta_condiciones: false,
  });

  const update = (field) => (e) => setForm((p) => ({ ...p, [field]: e.target.value }));
  const toggleAveria = (a) =>
    setForm((p) => ({ ...p, averias: p.averias.includes(a) ? p.averias.filter((x) => x !== a) : [...p.averias, a] }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.acepta_condiciones) {
      toast.error('Debes aceptar las condiciones para continuar');
      return;
    }
    if (!form.tipo_dispositivo) {
      toast.error('Selecciona un tipo de dispositivo');
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${BACKEND_URL}/api/web/presupuesto`, form);
      setSuccess(true);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch {
      toast.error('Error al enviar. Inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <PageHero
        eyebrow="Solicitud recibida"
        title="Recibido. Revisamos tu caso."
        subtitle="En menos de 24h laborables un técnico te escribe con una estimación y los siguientes pasos."
      >
        <CTAButton to="/" variant="primary" testid="presupuesto-success-home">
          Volver al inicio
        </CTAButton>
      </PageHero>
    );
  }

  const averiasDisponibles = averiasPorTipo[form.tipo_dispositivo] || [];

  return (
    <>
      <PageHero
        eyebrow="Presupuesto gratuito"
        title="Cuéntanos la avería."
        subtitle="Sin compromiso, sin letra pequeña. En 24 horas tienes una estimación real de un técnico."
      />

      <Section className="!pt-0">
        <Container className="max-w-3xl">
          <form onSubmit={handleSubmit} className="space-y-14" data-testid="form-presupuesto">
            {/* 1. Dispositivo */}
            <FadeUp>
              <div className="space-y-6">
                <H3>1 · Tu dispositivo</H3>
                <div>
                  <Label>Tipo</Label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {tiposDispositivo.map((t) => {
                      const active = form.tipo_dispositivo === t.id;
                      return (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => setForm({ ...form, tipo_dispositivo: t.id, averias: [] })}
                          className={`rounded-2xl p-5 flex flex-col items-center gap-2 border transition-all ${
                            active
                              ? 'bg-[#0055FF] border-[#0055FF] text-white'
                              : 'bg-[#F5F5F7] border-transparent text-[#111111] hover:bg-[#EFEFF2]'
                          }`}
                          data-testid={`dispositivo-${t.id}`}
                        >
                          <t.icon className="w-6 h-6" strokeWidth={1.75} />
                          <span className="text-sm font-semibold">{t.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="grid sm:grid-cols-2 gap-4">
                  <input className={inputCls} placeholder="Marca (ej. Apple)" value={form.marca} onChange={update('marca')} data-testid="input-marca" />
                  <input className={inputCls} placeholder="Modelo (ej. iPhone 14)" value={form.modelo} onChange={update('modelo')} data-testid="input-modelo" />
                </div>
              </div>
            </FadeUp>

            {/* 2. Avería */}
            {form.tipo_dispositivo && (
              <FadeUp>
                <div className="space-y-6">
                  <H3>2 · ¿Qué le pasa?</H3>
                  <div>
                    <Label>Selecciona todas las que apliquen</Label>
                    <div className="flex flex-wrap gap-2">
                      {averiasDisponibles.map((a) => {
                        const active = form.averias.includes(a);
                        return (
                          <button
                            key={a}
                            type="button"
                            onClick={() => toggleAveria(a)}
                            className={`px-4 py-2.5 rounded-full text-sm font-medium border transition-all ${
                              active
                                ? 'bg-[#111111] border-[#111111] text-white'
                                : 'bg-white border-[#E5E5EA] text-[#111111] hover:border-[#111111]'
                            }`}
                          >
                            {a}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  <textarea
                    className={`${inputCls} resize-none`}
                    placeholder="Cuéntanos detalles: cómo ocurrió, si enciende, si responde..."
                    rows={4}
                    value={form.descripcion}
                    onChange={update('descripcion')}
                    data-testid="input-descripcion"
                  />
                </div>
              </FadeUp>
            )}

            {/* 3. Tus datos */}
            <FadeUp>
              <div className="space-y-6">
                <H3>3 · Tus datos</H3>
                <div className="grid sm:grid-cols-2 gap-4">
                  <input required className={inputCls} placeholder="Nombre" value={form.nombre} onChange={update('nombre')} data-testid="input-nombre" />
                  <input required className={inputCls} placeholder="Apellidos" value={form.apellidos} onChange={update('apellidos')} data-testid="input-apellidos" />
                </div>
                <div className="grid sm:grid-cols-2 gap-4">
                  <input required type="email" className={inputCls} placeholder="Email" value={form.email} onChange={update('email')} data-testid="input-email" />
                  <input required className={inputCls} placeholder="Teléfono" value={form.telefono} onChange={update('telefono')} data-testid="input-telefono" />
                </div>
                <input className={inputCls} placeholder="DNI (opcional)" value={form.dni} onChange={update('dni')} data-testid="input-dni" />
              </div>
            </FadeUp>

            {/* 4. Recogida */}
            <FadeUp>
              <div className="space-y-6">
                <H3>4 · Recogida</H3>
                <input className={inputCls} placeholder="Dirección" value={form.direccion} onChange={update('direccion')} data-testid="input-direccion" />
                <div className="grid sm:grid-cols-3 gap-4">
                  <input className={inputCls} placeholder="Código postal" value={form.codigo_postal} onChange={update('codigo_postal')} data-testid="input-cp" />
                  <input className={inputCls} placeholder="Ciudad" value={form.ciudad} onChange={update('ciudad')} data-testid="input-ciudad" />
                  <input className={inputCls} placeholder="Provincia" value={form.provincia} onChange={update('provincia')} data-testid="input-provincia" />
                </div>
              </div>
            </FadeUp>

            {/* 5. Marketing */}
            <FadeUp>
              <div className="space-y-6">
                <H3>5 · ¿Cómo nos conociste?</H3>
                <div className="flex flex-wrap gap-2">
                  {comoNosConociste.map((c) => {
                    const active = form.como_conociste === c.id;
                    return (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => setForm({ ...form, como_conociste: c.id })}
                        className={`px-4 py-2.5 rounded-full text-sm font-medium border transition-all ${
                          active ? 'bg-[#0055FF] border-[#0055FF] text-white' : 'bg-white border-[#E5E5EA] text-[#111111] hover:border-[#0055FF]'
                        }`}
                      >
                        {c.label}
                      </button>
                    );
                  })}
                </div>
                {form.como_conociste === 'otro' && (
                  <input className={inputCls} placeholder="Cuéntanos" value={form.como_conociste_otro} onChange={update('como_conociste_otro')} />
                )}
                <textarea
                  className={`${inputCls} resize-none`}
                  placeholder="Notas adicionales (opcional)"
                  rows={3}
                  value={form.notas_adicionales}
                  onChange={update('notas_adicionales')}
                />
              </div>
            </FadeUp>

            {/* Submit */}
            <FadeUp>
              <div className="space-y-5 pt-4">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.acepta_condiciones}
                    onChange={(e) => setForm({ ...form, acepta_condiciones: e.target.checked })}
                    className="mt-1 accent-[#0055FF] w-4 h-4"
                    data-testid="check-condiciones"
                  />
                  <span className="text-sm text-[#6E6E73] leading-relaxed">
                    Acepto la política de privacidad y el tratamiento de mis datos para gestionar este presupuesto.
                  </span>
                </label>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full inline-flex items-center justify-center gap-2 bg-[#0055FF] text-white font-semibold rounded-full px-7 py-5 hover:bg-[#0044CC] transition-colors disabled:opacity-60 disabled:cursor-not-allowed text-base"
                  data-testid="btn-submit-presupuesto"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Enviando…
                    </>
                  ) : (
                    <>
                      Enviar presupuesto
                      <ArrowRight className="w-4 h-4" strokeWidth={2.5} />
                    </>
                  )}
                </button>
                <p className="text-center text-xs text-[#6E6E73] inline-flex items-center justify-center gap-1.5 w-full">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#0055FF]" strokeWidth={2.5} />
                  Respuesta en menos de 24h laborables
                </p>
              </div>
            </FadeUp>
          </form>
        </Container>
      </Section>
    </>
  );
}

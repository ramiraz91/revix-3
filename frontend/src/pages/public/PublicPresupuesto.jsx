import { useState } from 'react';
import { motion } from 'framer-motion';
import { Smartphone, Tablet, Watch, Gamepad2, CheckCircle2, Loader2, ArrowRight } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const tiposDispositivo = [
  { id: 'smartphone', icon: Smartphone, label: 'Smartphone' },
  { id: 'tablet', icon: Tablet, label: 'Tablet' },
  { id: 'smartwatch', icon: Watch, label: 'Smartwatch' },
  { id: 'consola', icon: Gamepad2, label: 'Consola' },
];

const averiasPorTipo = {
  smartphone: ['Pantalla rota', 'Batería', 'Conector de carga', 'Cámara', 'Daños por agua', 'Altavoz/micrófono', 'Botones', 'Placa base', 'Software'],
  tablet: ['Pantalla rota', 'Batería', 'Conector de carga', 'Cámara', 'Daños por agua', 'Botones', 'Software'],
  smartwatch: ['Pantalla', 'Batería', 'Corona/botones', 'Sensor de pulso', 'Daños por agua', 'Correa'],
  consola: ['Pantalla', 'Botones/Joy-Con', 'Batería', 'Puerto de carga', 'Ventilador', 'Software'],
};

export default function PublicPresupuesto() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [form, setForm] = useState({
    tipo_dispositivo: '', marca: '', modelo: '', averias: [],
    descripcion: '', nombre: '', email: '', telefono: '',
  });

  const toggleAveria = (a) => {
    setForm(p => ({
      ...p,
      averias: p.averias.includes(a) ? p.averias.filter(x => x !== a) : [...p.averias, a],
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${BACKEND_URL}/api/web/presupuesto`, form);
      setSuccess(true);
    } catch {
      toast.error('Error al enviar. Inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }} className="bg-white text-[#0F172A]">
      <div className="border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-xs font-semibold uppercase tracking-widest text-[#0055FF] mb-3">Presupuesto</motion.p>
          <motion.h1 initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="text-4xl font-bold tracking-tight text-[#0F172A] mb-2">Solicitar presupuesto gratuito</motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
            className="text-slate-500 text-sm" style={{ fontFamily: "'Inter', sans-serif" }}>
            Sin compromiso. Te respondemos en menos de 24 horas.
          </motion.p>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-16">
        {success ? (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            className="border border-slate-100 rounded-2xl p-12 text-center">
            <div className="w-12 h-12 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-5">
              <CheckCircle2 size={22} className="text-[#0055FF]" />
            </div>
            <h2 className="text-xl font-bold mb-2">Solicitud recibida</h2>
            <p className="text-slate-500 text-sm" style={{ fontFamily: "'Inter', sans-serif" }}>
              Te contactaremos en <span className="font-medium text-[#0F172A]">{form.email}</span> en menos de 24 horas.
            </p>
          </motion.div>
        ) : (
          <div className="space-y-6">

            {/* Paso 1: Tipo dispositivo */}
            <div className="border border-slate-100 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-[#0F172A] mb-4">1. ¿Qué dispositivo?</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {tiposDispositivo.map((t) => (
                  <button key={t.id} type="button"
                    onClick={() => { setForm(p => ({ ...p, tipo_dispositivo: t.id, averias: [] })); setStep(2); }}
                    className={`flex flex-col items-center gap-2 p-4 border rounded-lg text-sm font-medium transition-all ${
                      form.tipo_dispositivo === t.id
                        ? 'border-[#0055FF] bg-blue-50 text-[#0055FF]'
                        : 'border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50'
                    }`}>
                    <t.icon size={20} />
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Paso 2: Marca, modelo, averías */}
            {form.tipo_dispositivo && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                className="border border-slate-100 rounded-xl p-6 space-y-5">
                <h3 className="text-sm font-semibold text-[#0F172A]">2. Marca, modelo y avería</h3>
                <div className="grid md:grid-cols-2 gap-4">
                  {[
                    { id: 'marca', label: 'Marca', placeholder: 'Ej: Apple, Samsung...' },
                    { id: 'modelo', label: 'Modelo', placeholder: 'Ej: iPhone 15, Galaxy S24...' },
                  ].map((f) => (
                    <div key={f.id}>
                      <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1.5" style={{ fontFamily: "'Inter', sans-serif" }}>{f.label} *</label>
                      <input type="text" required placeholder={f.placeholder} value={form[f.id]}
                        onChange={(e) => setForm(p => ({ ...p, [f.id]: e.target.value }))}
                        className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0055FF] focus:border-transparent"
                        style={{ fontFamily: "'Inter', sans-serif" }} />
                    </div>
                  ))}
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2" style={{ fontFamily: "'Inter', sans-serif" }}>Tipo de avería *</label>
                  <div className="flex flex-wrap gap-2">
                    {(averiasPorTipo[form.tipo_dispositivo] || []).map((a) => (
                      <button key={a} type="button" onClick={() => toggleAveria(a)}
                        className={`px-3 py-1.5 border rounded-lg text-sm transition-all ${
                          form.averias.includes(a)
                            ? 'border-[#0055FF] bg-blue-50 text-[#0055FF] font-medium'
                            : 'border-slate-200 text-slate-600 hover:border-slate-300'
                        }`} style={{ fontFamily: "'Inter', sans-serif" }}>
                        {a}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1.5" style={{ fontFamily: "'Inter', sans-serif" }}>Descripción adicional</label>
                  <textarea rows={3} value={form.descripcion}
                    onChange={(e) => setForm(p => ({ ...p, descripcion: e.target.value }))}
                    placeholder="Cuéntanos más sobre el problema..."
                    className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0055FF] focus:border-transparent resize-none"
                    style={{ fontFamily: "'Inter', sans-serif" }} />
                </div>
              </motion.div>
            )}

            {/* Paso 3: Datos de contacto */}
            {form.tipo_dispositivo && form.marca && form.averias.length > 0 && (
              <motion.form initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                onSubmit={handleSubmit}
                className="border border-slate-100 rounded-xl p-6 space-y-5">
                <h3 className="text-sm font-semibold text-[#0F172A]">3. Tus datos de contacto</h3>
                <div className="grid md:grid-cols-2 gap-4">
                  {[
                    { id: 'nombre', label: 'Nombre', type: 'text', required: true },
                    { id: 'email', label: 'Email', type: 'email', required: true },
                    { id: 'telefono', label: 'Teléfono', type: 'tel', required: true },
                  ].map((f) => (
                    <div key={f.id}>
                      <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1.5" style={{ fontFamily: "'Inter', sans-serif" }}>{f.label} *</label>
                      <input type={f.type} required value={form[f.id]}
                        onChange={(e) => setForm(p => ({ ...p, [f.id]: e.target.value }))}
                        className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0055FF] focus:border-transparent"
                        style={{ fontFamily: "'Inter', sans-serif" }} />
                    </div>
                  ))}
                </div>
                <button type="submit" disabled={loading}
                  className="w-full py-2.5 bg-[#0055FF] text-white rounded-lg text-sm font-semibold hover:bg-[#0044DD] transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                  {loading ? <><Loader2 size={16} className="animate-spin" />Enviando...</> : <>Solicitar presupuesto <ArrowRight size={16} /></>}
                </button>
              </motion.form>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

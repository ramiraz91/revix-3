import { useState } from 'react';
import { motion } from 'framer-motion';
import { Send, Mail, MapPin, Clock, MessageSquare, CheckCircle2, Loader2 } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

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

  return (
    <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }} className="bg-white text-[#0F172A]">
      <div className="border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-xs font-semibold uppercase tracking-widest text-[#0055FF] mb-3">
            Contacto
          </motion.p>
          <motion.h1 initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="text-4xl font-bold tracking-tight text-[#0F172A]">
            ¿Hablamos?
          </motion.h1>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-16">
        <div className="grid lg:grid-cols-3 gap-12">

          {/* Info */}
          <div className="space-y-4">
            {[
              { icon: Mail, label: 'Email', value: 'help@revix.es', href: 'mailto:help@revix.es', sub: 'Respuesta en menos de 24h' },
              { icon: MapPin, label: 'Cobertura', value: 'Toda España', sub: 'Recogida y entrega a domicilio' },
              { icon: Clock, label: 'Horario', value: 'L–V: 10–14h / 17–20h', sub: 'Sáb: 10–14h · Dom: cerrado' },
            ].map((item, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
                className="p-5 border border-slate-100 rounded-xl">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 bg-slate-50 rounded-lg flex items-center justify-center flex-shrink-0">
                    <item.icon size={16} className="text-slate-500" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 uppercase tracking-wide font-medium mb-1" style={{ fontFamily: "'Inter', sans-serif" }}>{item.label}</p>
                    {item.href
                      ? <a href={item.href} className="text-sm font-semibold text-[#0055FF] hover:underline">{item.value}</a>
                      : <p className="text-sm font-semibold text-[#0F172A]">{item.value}</p>}
                    <p className="text-xs text-slate-400 mt-0.5" style={{ fontFamily: "'Inter', sans-serif" }}>{item.sub}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Formulario */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
            className="lg:col-span-2">
            {success ? (
              <div className="border border-slate-100 rounded-2xl p-12 text-center">
                <div className="w-12 h-12 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-5">
                  <CheckCircle2 size={22} className="text-[#0055FF]" />
                </div>
                <h2 className="text-xl font-bold mb-2">Mensaje enviado</h2>
                <p className="text-slate-500 text-sm" style={{ fontFamily: "'Inter', sans-serif" }}>
                  Te responderemos en <span className="font-medium text-[#0F172A]">help@revix.es</span> en menos de 24 horas.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="border border-slate-100 rounded-2xl p-8 space-y-5">
                <div className="flex items-center gap-2.5 mb-6">
                  <MessageSquare size={18} className="text-[#0055FF]" />
                  <h2 className="font-semibold text-[#0F172A]">Envíanos un mensaje</h2>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  {[
                    { id: 'nombre', label: 'Nombre', type: 'text', required: true },
                    { id: 'email', label: 'Email', type: 'email', required: true },
                    { id: 'telefono', label: 'Teléfono', type: 'tel', required: false },
                    { id: 'asunto', label: 'Asunto', type: 'text', required: true },
                  ].map((f) => (
                    <div key={f.id}>
                      <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1.5" style={{ fontFamily: "'Inter', sans-serif" }}>
                        {f.label}{f.required && ' *'}
                      </label>
                      <input type={f.type} required={f.required} value={form[f.id]}
                        onChange={(e) => setForm(p => ({ ...p, [f.id]: e.target.value }))}
                        className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0055FF] focus:border-transparent transition-all"
                        style={{ fontFamily: "'Inter', sans-serif" }} />
                    </div>
                  ))}
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1.5" style={{ fontFamily: "'Inter', sans-serif" }}>
                    Mensaje *
                  </label>
                  <textarea rows={5} required value={form.mensaje}
                    onChange={(e) => setForm(p => ({ ...p, mensaje: e.target.value }))}
                    className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0055FF] focus:border-transparent transition-all resize-none"
                    style={{ fontFamily: "'Inter', sans-serif" }} />
                </div>

                <button type="submit" disabled={loading}
                  className="w-full py-2.5 bg-[#0055FF] text-white rounded-lg text-sm font-semibold hover:bg-[#0044DD] transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                  {loading ? <><Loader2 size={16} className="animate-spin" />Enviando...</> : <><Send size={16} />Enviar mensaje</>}
                </button>
              </form>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  );
}

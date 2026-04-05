import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Smartphone, Tablet, Watch, Gamepad2, CheckCircle2, Loader2, ArrowRight, 
  User, Mail, Phone, MapPin, FileText, MessageSquare, Truck, Shield, Clock,
  HelpCircle, ChevronDown
} from 'lucide-react';
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
  smartphone: ['Pantalla rota', 'Batería', 'Conector de carga', 'Cámara trasera', 'Cámara frontal', 'Daños por agua', 'Altavoz', 'Micrófono', 'Botones', 'Face ID / Touch ID', 'Placa base', 'Software', 'Tapa trasera', 'Marco/Chasis', 'Otro'],
  tablet: ['Pantalla rota', 'Batería', 'Conector de carga', 'Cámara', 'Daños por agua', 'Botones', 'Altavoz', 'Software', 'Otro'],
  smartwatch: ['Pantalla', 'Batería', 'Corona/botones', 'Sensor de pulso', 'Daños por agua', 'Correa', 'Otro'],
  consola: ['Pantalla', 'Botones/Joy-Con', 'Batería', 'Puerto de carga', 'Ventilador', 'Lector de discos', 'Software', 'Otro'],
};

const comoNosConociste = [
  { id: 'google', label: 'Google / Buscador' },
  { id: 'aseguradora', label: 'Mi compañía aseguradora' },
  { id: 'referido', label: 'Recomendación de un conocido' },
  { id: 'redes_sociales', label: 'Redes sociales (Instagram, Facebook, etc.)' },
  { id: 'publicidad', label: 'Publicidad online' },
  { id: 'repetidor', label: 'Ya he sido cliente antes' },
  { id: 'otro', label: 'Otro' },
];

export default function PublicPresupuesto() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [form, setForm] = useState({
    // Dispositivo
    tipo_dispositivo: '', 
    marca: '', 
    modelo: '', 
    averias: [],
    descripcion: '',
    // Cliente
    nombre: '', 
    apellidos: '',
    dni: '',
    email: '', 
    telefono: '',
    telefono_alternativo: '',
    // Dirección
    direccion: '',
    codigo_postal: '',
    ciudad: '',
    provincia: '',
    // Marketing
    como_conociste: '',
    como_conociste_otro: '',
    // Notas
    notas_adicionales: '',
    acepta_condiciones: false,
  });

  const toggleAveria = (a) => {
    setForm(p => ({
      ...p,
      averias: p.averias.includes(a) ? p.averias.filter(x => x !== a) : [...p.averias, a],
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.acepta_condiciones) {
      toast.error('Debes aceptar las condiciones para continuar');
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

  const InputField = ({ id, label, type = 'text', required = false, placeholder = '', colSpan = 1 }) => (
    <div className={colSpan === 2 ? 'md:col-span-2' : ''}>
      <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1.5" style={{ fontFamily: "'Inter', sans-serif" }}>
        {label}{required && ' *'}
      </label>
      <input 
        type={type} 
        required={required} 
        placeholder={placeholder}
        value={form[id] || ''}
        onChange={(e) => setForm(p => ({ ...p, [id]: e.target.value }))}
        className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0055FF] focus:border-transparent transition-all"
        style={{ fontFamily: "'Inter', sans-serif" }} 
      />
    </div>
  );

  return (
    <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }} className="bg-white text-[#0F172A]">
      {/* Header */}
      <div className="border-b border-slate-100 bg-gradient-to-r from-blue-50 to-white">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-xs font-semibold uppercase tracking-widest text-[#0055FF] mb-3">
            Presupuesto gratuito
          </motion.p>
          <motion.h1 initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="text-4xl font-bold tracking-tight text-[#0F172A] mb-3">
            Solicitar presupuesto sin compromiso
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
            className="text-slate-500 text-sm max-w-xl" style={{ fontFamily: "'Inter', sans-serif" }}>
            Completa el formulario y te contactaremos en menos de 24 horas. La recogida a domicilio es gratuita en toda España.
          </motion.p>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-12">
        {success ? (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            className="border border-green-200 bg-green-50 rounded-2xl p-8 md:p-12">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-5">
                <CheckCircle2 size={32} className="text-green-600" />
              </div>
              <h2 className="text-2xl font-bold mb-2 text-green-800">¡Solicitud recibida correctamente!</h2>
              <p className="text-green-700 text-sm" style={{ fontFamily: "'Inter', sans-serif" }}>
                Te contactaremos en <span className="font-semibold">{form.email}</span> o al teléfono <span className="font-semibold">{form.telefono}</span>
              </p>
            </div>

            <div className="space-y-4">
              <div className="bg-white rounded-xl p-5 border border-green-200">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Clock size={20} className="text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-[#0F172A] mb-1">Te contactaremos en breve</h3>
                    <p className="text-sm text-slate-600" style={{ fontFamily: "'Inter', sans-serif" }}>
                      Un técnico especializado revisará tu solicitud y te llamará para confirmar los detalles y coordinar la recogida.
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl p-5 border border-green-200">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Truck size={20} className="text-amber-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-[#0F172A] mb-1">Recogida en 24-48 horas</h3>
                    <p className="text-sm text-slate-600" style={{ fontFamily: "'Inter', sans-serif" }}>
                      La recogida se realiza a domicilio <span className="font-semibold text-green-600">sin ningún coste</span> para ti. 
                      El mensajero te contactará para acordar la hora de recogida.
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl p-5 border border-green-200">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-violet-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <FileText size={20} className="text-violet-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-[#0F172A] mb-1">Presupuesto definitivo tras diagnóstico</h3>
                    <p className="text-sm text-slate-600" style={{ fontFamily: "'Inter', sans-serif" }}>
                      El presupuesto inicial es orientativo. Una vez recibamos tu dispositivo, nuestros técnicos realizarán 
                      un diagnóstico completo y te enviaremos el <span className="font-semibold">presupuesto definitivo</span> antes de realizar cualquier reparación.
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl p-5 border border-green-200">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Shield size={20} className="text-green-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-[#0F172A] mb-1">6 meses de garantía</h3>
                    <p className="text-sm text-slate-600" style={{ fontFamily: "'Inter', sans-serif" }}>
                      Todas nuestras reparaciones incluyen 6 meses de garantía. Trabajamos con técnicos certificados y piezas de calidad.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-8 text-center">
              <p className="text-xs text-slate-500 mb-4" style={{ fontFamily: "'Inter', sans-serif" }}>
                ¿Tienes alguna pregunta? Escríbenos a <a href="mailto:help@revix.es" className="text-[#0055FF] hover:underline">help@revix.es</a>
              </p>
              <a href="/" className="inline-flex items-center gap-2 text-sm font-semibold text-[#0055FF] hover:underline">
                Volver a la página principal <ArrowRight size={16} />
              </a>
            </div>
          </motion.div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">

            {/* Paso 1: Tipo dispositivo */}
            <div className="border border-slate-200 rounded-xl p-6 bg-white shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-7 h-7 bg-[#0055FF] text-white rounded-full flex items-center justify-center text-xs font-bold">1</div>
                <h3 className="text-sm font-semibold text-[#0F172A]">¿Qué dispositivo necesitas reparar?</h3>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {tiposDispositivo.map((t) => (
                  <button key={t.id} type="button"
                    onClick={() => { setForm(p => ({ ...p, tipo_dispositivo: t.id, averias: [] })); setStep(2); }}
                    className={`flex flex-col items-center gap-2 p-4 border rounded-lg text-sm font-medium transition-all ${
                      form.tipo_dispositivo === t.id
                        ? 'border-[#0055FF] bg-blue-50 text-[#0055FF] ring-2 ring-[#0055FF]/20'
                        : 'border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50'
                    }`}>
                    <t.icon size={24} />
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Paso 2: Marca, modelo, averías */}
            {form.tipo_dispositivo && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                className="border border-slate-200 rounded-xl p-6 bg-white shadow-sm space-y-5">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 bg-[#0055FF] text-white rounded-full flex items-center justify-center text-xs font-bold">2</div>
                  <h3 className="text-sm font-semibold text-[#0F172A]">Información del dispositivo</h3>
                </div>
                
                <div className="grid md:grid-cols-2 gap-4">
                  <InputField id="marca" label="Marca" required placeholder="Ej: Apple, Samsung, Xiaomi..." />
                  <InputField id="modelo" label="Modelo" required placeholder="Ej: iPhone 15 Pro, Galaxy S24..." />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2" style={{ fontFamily: "'Inter', sans-serif" }}>
                    Tipo de avería (selecciona todas las que apliquen) *
                  </label>
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
                  <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1.5" style={{ fontFamily: "'Inter', sans-serif" }}>
                    Descripción detallada del problema *
                  </label>
                  <textarea rows={4} required value={form.descripcion}
                    onChange={(e) => setForm(p => ({ ...p, descripcion: e.target.value }))}
                    placeholder="Cuéntanos con detalle qué le ocurre a tu dispositivo: cuándo empezó el problema, si hubo algún golpe o contacto con agua, si funciona parcialmente, etc."
                    className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0055FF] focus:border-transparent resize-none"
                    style={{ fontFamily: "'Inter', sans-serif" }} />
                </div>
              </motion.div>
            )}

            {/* Paso 3: Datos personales */}
            {form.tipo_dispositivo && form.marca && form.averias.length > 0 && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                className="border border-slate-200 rounded-xl p-6 bg-white shadow-sm space-y-5">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 bg-[#0055FF] text-white rounded-full flex items-center justify-center text-xs font-bold">3</div>
                  <h3 className="text-sm font-semibold text-[#0F172A]">Tus datos de contacto</h3>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <InputField id="nombre" label="Nombre" required placeholder="Tu nombre" />
                  <InputField id="apellidos" label="Apellidos" required placeholder="Tus apellidos" />
                  <InputField id="dni" label="DNI / NIE" required placeholder="12345678A" />
                  <InputField id="email" label="Email" type="email" required placeholder="tu@email.com" />
                  <InputField id="telefono" label="Teléfono principal" type="tel" required placeholder="612 345 678" />
                  <InputField id="telefono_alternativo" label="Teléfono alternativo" type="tel" placeholder="Otro teléfono de contacto (opcional)" />
                </div>
              </motion.div>
            )}

            {/* Paso 4: Dirección */}
            {form.tipo_dispositivo && form.marca && form.averias.length > 0 && form.nombre && form.telefono && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                className="border border-slate-200 rounded-xl p-6 bg-white shadow-sm space-y-5">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 bg-[#0055FF] text-white rounded-full flex items-center justify-center text-xs font-bold">4</div>
                  <h3 className="text-sm font-semibold text-[#0F172A]">Dirección de recogida</h3>
                </div>
                <p className="text-xs text-slate-500" style={{ fontFamily: "'Inter', sans-serif" }}>
                  Indica la dirección donde recogeremos tu dispositivo. La recogida es gratuita en toda España.
                </p>

                <div className="grid md:grid-cols-2 gap-4">
                  <InputField id="direccion" label="Dirección completa" required placeholder="Calle, número, piso, puerta..." colSpan={2} />
                  <InputField id="codigo_postal" label="Código Postal" required placeholder="28001" />
                  <InputField id="ciudad" label="Ciudad / Localidad" required placeholder="Madrid" />
                  <InputField id="provincia" label="Provincia" required placeholder="Madrid" />
                </div>
              </motion.div>
            )}

            {/* Paso 5: Cómo nos conociste */}
            {form.tipo_dispositivo && form.marca && form.averias.length > 0 && form.direccion && form.codigo_postal && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                className="border border-slate-200 rounded-xl p-6 bg-white shadow-sm space-y-5">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 bg-[#0055FF] text-white rounded-full flex items-center justify-center text-xs font-bold">5</div>
                  <h3 className="text-sm font-semibold text-[#0F172A]">¿Cómo nos conociste?</h3>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {comoNosConociste.map((opt) => (
                    <button key={opt.id} type="button"
                      onClick={() => setForm(p => ({ ...p, como_conociste: opt.id }))}
                      className={`p-3 border rounded-lg text-sm text-left transition-all ${
                        form.como_conociste === opt.id
                          ? 'border-[#0055FF] bg-blue-50 text-[#0055FF] font-medium'
                          : 'border-slate-200 text-slate-600 hover:border-slate-300'
                      }`} style={{ fontFamily: "'Inter', sans-serif" }}>
                      {opt.label}
                    </button>
                  ))}
                </div>

                {form.como_conociste === 'otro' && (
                  <InputField id="como_conociste_otro" label="Especifica cómo nos conociste" placeholder="Cuéntanos..." />
                )}

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1.5" style={{ fontFamily: "'Inter', sans-serif" }}>
                    Notas adicionales (opcional)
                  </label>
                  <textarea rows={3} value={form.notas_adicionales}
                    onChange={(e) => setForm(p => ({ ...p, notas_adicionales: e.target.value }))}
                    placeholder="¿Hay algo más que debamos saber? Horario preferido de contacto, instrucciones especiales para la recogida..."
                    className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0055FF] focus:border-transparent resize-none"
                    style={{ fontFamily: "'Inter', sans-serif" }} />
                </div>
              </motion.div>
            )}

            {/* Condiciones y envío */}
            {form.tipo_dispositivo && form.marca && form.averias.length > 0 && form.direccion && form.codigo_postal && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                className="space-y-4">
                
                {/* Info importante */}
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
                  <div className="flex items-start gap-3">
                    <HelpCircle size={20} className="text-amber-600 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-amber-800" style={{ fontFamily: "'Inter', sans-serif" }}>
                      <p className="font-semibold mb-2">Información importante:</p>
                      <ul className="space-y-1.5 text-amber-700">
                        <li>• La recogida se realiza en un plazo de <strong>24-48 horas laborables</strong></li>
                        <li>• La recogida y el envío de vuelta son <strong>totalmente gratuitos</strong></li>
                        <li>• El presupuesto inicial es orientativo y <strong>no es definitivo hasta que el dispositivo sea diagnosticado</strong> por nuestros técnicos</li>
                        <li>• Si no aceptas el presupuesto definitivo, te devolvemos el dispositivo sin coste</li>
                        <li>• Todas las reparaciones incluyen <strong>6 meses de garantía</strong></li>
                      </ul>
                    </div>
                  </div>
                </div>

                {/* Checkbox condiciones */}
                <label className="flex items-start gap-3 cursor-pointer p-4 border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors">
                  <input 
                    type="checkbox" 
                    checked={form.acepta_condiciones}
                    onChange={(e) => setForm(p => ({ ...p, acepta_condiciones: e.target.checked }))}
                    className="mt-1 w-4 h-4 text-[#0055FF] border-slate-300 rounded focus:ring-[#0055FF]"
                  />
                  <span className="text-sm text-slate-600" style={{ fontFamily: "'Inter', sans-serif" }}>
                    He leído y acepto la <a href="/politica-privacidad" className="text-[#0055FF] hover:underline" target="_blank">política de privacidad</a> y 
                    las <a href="/condiciones" className="text-[#0055FF] hover:underline" target="_blank">condiciones del servicio</a>. 
                    Entiendo que el presupuesto definitivo se confirmará tras el diagnóstico del dispositivo.
                  </span>
                </label>

                {/* Botón enviar */}
                <button type="submit" disabled={loading || !form.acepta_condiciones}
                  className="w-full py-3.5 bg-[#0055FF] text-white rounded-xl text-sm font-semibold hover:bg-[#0044DD] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg shadow-blue-500/20">
                  {loading ? (
                    <><Loader2 size={18} className="animate-spin" />Enviando solicitud...</>
                  ) : (
                    <>Solicitar presupuesto gratuito <ArrowRight size={18} /></>
                  )}
                </button>

                <p className="text-center text-xs text-slate-400" style={{ fontFamily: "'Inter', sans-serif" }}>
                  Tus datos están protegidos. No los compartimos con terceros.
                </p>
              </motion.div>
            )}
          </form>
        )}
      </div>
    </div>
  );
}

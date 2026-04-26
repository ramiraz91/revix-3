import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Bot, X, Mail } from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const SESSION_ID = `web-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

export default function ChatBot({ onClose }) {
  const [messages, setMessages] = useState([
    { type: 'bot', text: '¡Hola! Soy el asistente de Revix.es. ¿En qué puedo ayudarte?' },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showLead, setShowLead] = useState(false);
  const [leadSent, setLeadSent] = useState(false);
  const [lead, setLead] = useState({ nombre: '', email: '', telefono: '', consent: false });
  const [leadError, setLeadError] = useState('');
  const [leadSubmitting, setLeadSubmitting] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, showLead]);

  const userTurns = messages.filter((m) => m.type === 'user').length;

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;
    const userMessage = input.trim();
    setMessages((prev) => [...prev, { type: 'user', text: userMessage }]);
    setInput('');
    setIsTyping(true);
    try {
      const res = await axios.post(`${BACKEND_URL}/api/web/chatbot`, {
        mensaje: userMessage,
        session_id: SESSION_ID,
      });
      setMessages((prev) => [
        ...prev,
        { type: 'bot', text: res.data.respuesta, disclaimer: res.data.disclaimer },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { type: 'bot', text: 'No puedo responder ahora mismo. Escríbenos a help@revix.es' },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const submitLead = async () => {
    setLeadError('');
    if (lead.nombre.trim().length < 2) return setLeadError('Indica tu nombre');
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(lead.email)) return setLeadError('Email no válido');
    if (!lead.consent) return setLeadError('Necesitamos tu consentimiento RGPD');
    setLeadSubmitting(true);
    try {
      await axios.post(`${BACKEND_URL}/api/web/lead`, {
        nombre: lead.nombre.trim(),
        email: lead.email.trim(),
        telefono: lead.telefono.trim() || null,
        session_id: SESSION_ID,
        consent: true,
      });
      setLeadSent(true);
      setShowLead(false);
      setMessages((prev) => [
        ...prev,
        {
          type: 'bot',
          text: `✅ ¡Recibido, ${lead.nombre.trim()}! Te contactaremos en horario laboral. Mientras tanto, si tienes más dudas pregúntame aquí.`,
        },
      ]);
    } catch {
      setLeadError('No pudimos enviar tus datos. Inténtalo de nuevo.');
    } finally {
      setLeadSubmitting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 16, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
      className="w-[360px] max-w-[calc(100vw-3rem)] bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-200"
      data-testid="chatbot-panel"
    >
      {/* Header */}
      <div className="px-4 py-3.5 border-b border-slate-100 flex items-center justify-between bg-white">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-[#0055FF] rounded-full flex items-center justify-center">
            <Bot size={15} className="text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-[#0F172A]">Asistente Revix</p>
            <div className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
              <p className="text-xs text-slate-400" style={{ fontFamily: "'Inter', sans-serif" }}>IA activa</p>
            </div>
          </div>
        </div>
        <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors text-slate-400 hover:text-slate-600">
          <X size={16} />
        </button>
      </div>

      {/* Messages */}
      <div className="h-72 overflow-y-auto p-4 space-y-3 bg-slate-50" data-testid="chatbot-messages">
        {messages.map((msg, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className="max-w-[85%]">
              <div
                className={`px-3.5 py-2.5 rounded-xl text-sm ${
                  msg.type === 'user'
                    ? 'bg-[#0055FF] text-white rounded-br-sm'
                    : 'bg-white text-[#0F172A] rounded-bl-sm border border-slate-100 shadow-sm'
                }`}
                style={{ fontFamily: "'Inter', sans-serif" }}
                data-testid={`chatbot-msg-${msg.type}`}
              >
                <p className="whitespace-pre-line leading-relaxed">{msg.text}</p>
              </div>
              {msg.disclaimer && (
                <p
                  className="text-[10.5px] italic text-slate-400 mt-1 px-1 leading-snug"
                  style={{ fontFamily: "'Inter', sans-serif" }}
                  data-testid="chatbot-disclaimer"
                >
                  ⚠️ {msg.disclaimer}
                </p>
              )}
            </div>
          </motion.div>
        ))}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-white border border-slate-100 rounded-xl rounded-bl-sm px-4 py-3 shadow-sm flex gap-1">
              {[0, 150, 300].map((d) => (
                <span key={d} className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: `${d}ms` }} />
              ))}
            </div>
          </div>
        )}

        {/* CTA inline para abrir lead capture */}
        {!showLead && !leadSent && userTurns >= 1 && (
          <div className="flex justify-start" data-testid="chatbot-cta-lead-row">
            <button
              type="button"
              onClick={() => setShowLead(true)}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-[#0055FF] bg-[#0055FF]/10 hover:bg-[#0055FF] hover:text-white border border-[#0055FF]/30 rounded-full px-3 py-1.5 transition-colors"
              data-testid="chatbot-cta-lead"
              style={{ fontFamily: "'Inter', sans-serif" }}
            >
              <Mail size={12} />
              Quiero que me contactéis
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Lead capture form */}
      {showLead && (
        <div className="px-4 py-3 bg-white border-t border-slate-100 space-y-2.5" data-testid="chatbot-lead-form">
          <p className="text-xs font-semibold text-[#0F172A]" style={{ fontFamily: "'Inter', sans-serif" }}>
            📋 Déjanos tus datos y te contactamos
          </p>
          <input
            type="text"
            placeholder="Tu nombre"
            value={lead.nombre}
            onChange={(e) => setLead({ ...lead, nombre: e.target.value })}
            maxLength={100}
            className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-[#0055FF] focus:border-transparent"
            style={{ fontFamily: "'Inter', sans-serif" }}
            data-testid="chatbot-lead-nombre"
          />
          <input
            type="email"
            placeholder="tu@email.com"
            value={lead.email}
            onChange={(e) => setLead({ ...lead, email: e.target.value })}
            maxLength={120}
            className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-[#0055FF] focus:border-transparent"
            style={{ fontFamily: "'Inter', sans-serif" }}
            data-testid="chatbot-lead-email"
          />
          <input
            type="tel"
            placeholder="Teléfono (opcional)"
            value={lead.telefono}
            onChange={(e) => setLead({ ...lead, telefono: e.target.value })}
            maxLength={30}
            className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-[#0055FF] focus:border-transparent"
            style={{ fontFamily: "'Inter', sans-serif" }}
            data-testid="chatbot-lead-telefono"
          />
          <label className="flex items-start gap-1.5 text-[10.5px] text-slate-500 leading-snug cursor-pointer" style={{ fontFamily: "'Inter', sans-serif" }}>
            <input
              type="checkbox"
              checked={lead.consent}
              onChange={(e) => setLead({ ...lead, consent: e.target.checked })}
              className="mt-0.5 flex-shrink-0"
              data-testid="chatbot-lead-consent"
            />
            <span>Acepto que Revix procese mis datos para responder a esta consulta (RGPD).</span>
          </label>
          {leadError && (
            <p className="text-[10.5px] text-red-600" style={{ fontFamily: "'Inter', sans-serif" }} data-testid="chatbot-lead-error">
              {leadError}
            </p>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => { setShowLead(false); setLeadError(''); }}
              className="flex-1 py-1.5 rounded-md text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
              style={{ fontFamily: "'Inter', sans-serif" }}
              data-testid="chatbot-lead-cancel"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={submitLead}
              disabled={leadSubmitting}
              className="flex-1 py-1.5 rounded-md text-xs font-medium bg-[#0055FF] hover:bg-[#0044DD] text-white transition-colors disabled:opacity-50"
              style={{ fontFamily: "'Inter', sans-serif" }}
              data-testid="chatbot-lead-submit"
            >
              {leadSubmitting ? 'Enviando…' : 'Enviar'}
            </button>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-3.5 border-t border-slate-100 bg-white">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
            placeholder="Escribe tu pregunta..."
            className="flex-1 px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0055FF] focus:border-transparent transition-all"
            style={{ fontFamily: "'Inter', sans-serif" }}
            disabled={isTyping}
            data-testid="chatbot-input"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="w-9 h-9 bg-[#0055FF] text-white rounded-lg flex items-center justify-center hover:bg-[#0044DD] transition-colors disabled:opacity-40"
            data-testid="chatbot-send"
          >
            <Send size={15} />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

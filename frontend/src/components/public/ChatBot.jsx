import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Bot, X } from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const SESSION_ID = `web-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

export default function ChatBot({ onClose }) {
  const [messages, setMessages] = useState([
    { type: 'bot', text: '¡Hola! Soy el asistente de Revix.es. ¿En qué puedo ayudarte?' }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;
    const userMessage = input.trim();
    setMessages(prev => [...prev, { type: 'user', text: userMessage }]);
    setInput('');
    setIsTyping(true);
    try {
      const res = await axios.post(`${BACKEND_URL}/api/web/chatbot`, {
        mensaje: userMessage, session_id: SESSION_ID
      });
      setMessages(prev => [...prev, { type: 'bot', text: res.data.respuesta }]);
    } catch {
      setMessages(prev => [...prev, { type: 'bot', text: 'No puedo responder ahora mismo. Escríbenos a help@revix.es' }]);
    } finally {
      setIsTyping(false);
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
      <div className="h-72 overflow-y-auto p-4 space-y-3 bg-slate-50">
        {messages.map((msg, idx) => (
          <motion.div key={idx} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] px-3.5 py-2.5 rounded-xl text-sm ${
              msg.type === 'user'
                ? 'bg-[#0055FF] text-white rounded-br-sm'
                : 'bg-white text-[#0F172A] rounded-bl-sm border border-slate-100 shadow-sm'
            }`} style={{ fontFamily: "'Inter', sans-serif" }}>
              <p className="whitespace-pre-line leading-relaxed">{msg.text}</p>
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
        <div ref={messagesEndRef} />
      </div>

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
          />
          <button onClick={handleSend} disabled={!input.trim() || isTyping}
            className="w-9 h-9 bg-[#0055FF] text-white rounded-lg flex items-center justify-center hover:bg-[#0044DD] transition-colors disabled:opacity-40">
            <Send size={15} />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { MessageCircle, X } from 'lucide-react';
import ChatBot from './ChatBot';

/**
 * FAB de chat flotante — bottom-right, responsive, accesible.
 * Mantiene <ChatBot /> intacto; sólo gestiona visibilidad y posición.
 */
export default function FloatingChat() {
  const [open, setOpen] = useState(false);

  return (
    <div className="fixed bottom-5 right-5 sm:bottom-6 sm:right-6 z-50 pointer-events-none">
      <AnimatePresence>
        {open && (
          <motion.div
            key="panel"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.18 }}
            className="pointer-events-auto mb-3"
          >
            <ChatBot onClose={() => setOpen(false)} />
          </motion.div>
        )}
      </AnimatePresence>
      <button
        type="button"
        aria-label={open ? 'Cerrar chat' : 'Abrir chat'}
        onClick={() => setOpen((v) => !v)}
        className="pointer-events-auto ml-auto flex items-center justify-center w-14 h-14 rounded-full bg-[#0055FF] hover:bg-[#0044CC] text-white shadow-[0_12px_32px_-8px_rgba(0,85,255,0.6)] transition-colors"
        data-testid="floating-chat-toggle"
      >
        <AnimatePresence mode="wait" initial={false}>
          {open ? (
            <motion.span key="x" initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }} transition={{ duration: 0.18 }}>
              <X className="w-5 h-5" strokeWidth={2.5} />
            </motion.span>
          ) : (
            <motion.span key="m" initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }} transition={{ duration: 0.18 }}>
              <MessageCircle className="w-5 h-5" strokeWidth={2} />
            </motion.span>
          )}
        </AnimatePresence>
      </button>
    </div>
  );
}

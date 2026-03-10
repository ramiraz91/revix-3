import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ChevronDown, Search, HelpCircle } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function PublicFAQs() {
  const [faqs, setFaqs] = useState({});
  const [categorias, setCategorias] = useState({});
  const [loading, setLoading] = useState(true);
  const [busqueda, setBusqueda] = useState('');
  const [expandido, setExpandido] = useState({});

  useEffect(() => {
    const cargarFaqs = async () => {
      try {
        const res = await fetch(`${API_URL}/api/faqs/public`);
        const data = await res.json();
        setFaqs(data.faqs_por_categoria || {});
        setCategorias(data.categorias || {});
      } catch (error) {
        console.error('Error cargando FAQs:', error);
      } finally {
        setLoading(false);
      }
    };
    cargarFaqs();
  }, []);

  const togglePregunta = (id) => {
    setExpandido(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  // Filtrar FAQs por búsqueda
  const faqsFiltradas = {};
  Object.entries(faqs).forEach(([catKey, catData]) => {
    const faqsFiltradasCat = catData.faqs.filter(faq => {
      if (!busqueda) return true;
      const search = busqueda.toLowerCase();
      return faq.pregunta.toLowerCase().includes(search) || 
             faq.respuesta.toLowerCase().includes(search);
    });
    if (faqsFiltradasCat.length > 0) {
      faqsFiltradas[catKey] = { ...catData, faqs: faqsFiltradasCat };
    }
  });

  return (
    <div className="min-h-screen bg-white">
      {/* Hero */}
      <section className="bg-gradient-to-br from-[#0055FF] to-[#003ACC] text-white py-16">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <HelpCircle className="w-16 h-16 mx-auto mb-4 opacity-80" />
            <h1 className="text-4xl font-bold mb-4">Preguntas Frecuentes</h1>
            <p className="text-xl text-blue-100 max-w-2xl mx-auto">
              Encuentra respuestas a las dudas más comunes sobre nuestro servicio de reparación
            </p>
          </motion.div>
          
          {/* Buscador */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mt-8 max-w-xl mx-auto"
          >
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar pregunta..."
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                className="w-full pl-12 pr-4 py-4 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
            </div>
          </motion.div>
        </div>
      </section>

      {/* FAQs */}
      <section className="max-w-4xl mx-auto px-6 py-16">
        {loading ? (
          <div className="text-center py-12">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
          </div>
        ) : Object.keys(faqsFiltradas).length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">
              {busqueda ? 'No se encontraron resultados para tu búsqueda' : 'No hay FAQs disponibles'}
            </p>
          </div>
        ) : (
          <div className="space-y-12">
            {Object.entries(faqsFiltradas).map(([catKey, catData], catIndex) => (
              <motion.div
                key={catKey}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: catIndex * 0.1 }}
              >
                {/* Título de categoría */}
                <div className="flex items-center gap-3 mb-6">
                  <span className="text-3xl">{catData.info.icono}</span>
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">{catData.info.nombre}</h2>
                    <p className="text-sm text-gray-500">{catData.info.descripcion}</p>
                  </div>
                </div>
                
                {/* Lista de preguntas */}
                <div className="space-y-3">
                  {catData.faqs.map((faq, faqIndex) => (
                    <motion.div
                      key={faq.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: catIndex * 0.1 + faqIndex * 0.05 }}
                      className="border border-gray-200 rounded-xl overflow-hidden hover:border-blue-200 transition-colors"
                    >
                      <button
                        onClick={() => togglePregunta(faq.id)}
                        className="w-full flex items-center justify-between p-5 text-left bg-white hover:bg-gray-50 transition-colors"
                      >
                        <span className="font-medium text-gray-900 pr-4">{faq.pregunta}</span>
                        <ChevronDown 
                          className={`w-5 h-5 text-gray-400 flex-shrink-0 transition-transform duration-200 ${
                            expandido[faq.id] ? 'rotate-180' : ''
                          }`}
                        />
                      </button>
                      
                      {expandido[faq.id] && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          transition={{ duration: 0.2 }}
                          className="border-t border-gray-100"
                        >
                          <div className="p-5 bg-gray-50">
                            <p className="text-gray-600 leading-relaxed whitespace-pre-line">
                              {faq.respuesta}
                            </p>
                          </div>
                        </motion.div>
                      )}
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </section>

      {/* CTA */}
      <section className="bg-gray-50 py-16">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-2xl font-bold mb-4">¿No encuentras lo que buscas?</h2>
          <p className="text-gray-600 mb-6">
            Nuestro equipo está aquí para ayudarte con cualquier duda
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <a
              href="/contacto"
              className="px-6 py-3 bg-[#0055FF] text-white rounded-xl font-semibold hover:bg-[#0044DD] transition-colors"
            >
              Contactar
            </a>
            <a
              href="/presupuesto"
              className="px-6 py-3 bg-white border border-gray-200 text-gray-900 rounded-xl font-semibold hover:bg-gray-50 transition-colors"
            >
              Pedir presupuesto
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}

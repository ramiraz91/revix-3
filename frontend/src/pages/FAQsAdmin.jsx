import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { 
  Plus, Edit, Trash2, RefreshCw, HelpCircle,
  ChevronDown, ChevronUp, Eye, EyeOff, Save,
  AlertTriangle, Sparkles
} from 'lucide-react';
import api from '@/lib/api';

const CATEGORIAS = {
  envio: { nombre: 'Envíos y Logística', icono: '📦' },
  privacidad: { nombre: 'Privacidad y Seguridad', icono: '🛡️' },
  pagos: { nombre: 'Presupuestos y Pagos', icono: '💰' },
  garantia: { nombre: 'Reparaciones y Garantía', icono: '🔧' },
  tecnologia: { nombre: 'Tecnología e IA', icono: '🤖' },
  otras: { nombre: 'Casos Especiales', icono: '💡' }
};

export default function FAQsAdmin() {
  const { isMaster } = useAuth();
  const [faqs, setFaqs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingFaq, setEditingFaq] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    pregunta: '',
    respuesta: '',
    categoria: 'proceso',
    activo: true
  });

  const cargarFaqs = async () => {
    try {
      setLoading(true);
      const res = await api.get('/faqs');
      setFaqs(res.data.faqs || []);
    } catch (error) {
      toast.error('Error cargando FAQs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarFaqs();
  }, []);

  const handleInicializar = async () => {
    if (!confirm('¿Crear las FAQs predeterminadas?')) return;
    
    try {
      const res = await api.post('/faqs/inicializar');
      toast.success(res.data.message);
      cargarFaqs();
    } catch (error) {
      toast.error('Error inicializando FAQs');
    }
  };

  const handleSubmit = async () => {
    if (!formData.pregunta || !formData.respuesta) {
      toast.error('Completa todos los campos');
      return;
    }
    
    try {
      if (editingFaq) {
        await api.put(`/faqs/${editingFaq.id}`, formData);
        toast.success('FAQ actualizada');
      } else {
        await api.post('/faqs', formData);
        toast.success('FAQ creada');
      }
      setShowModal(false);
      resetForm();
      cargarFaqs();
    } catch (error) {
      toast.error('Error guardando FAQ');
    }
  };

  const handleDelete = async (faq) => {
    if (!confirm(`¿Eliminar esta FAQ?\n\n"${faq.pregunta}"`)) return;
    
    try {
      await api.delete(`/faqs/${faq.id}`);
      toast.success('FAQ eliminada');
      cargarFaqs();
    } catch (error) {
      toast.error('Error eliminando FAQ');
    }
  };

  const handleToggleActivo = async (faq) => {
    try {
      await api.put(`/faqs/${faq.id}`, { activo: !faq.activo });
      cargarFaqs();
    } catch (error) {
      toast.error('Error actualizando FAQ');
    }
  };

  const openEditModal = (faq) => {
    setEditingFaq(faq);
    setFormData({
      pregunta: faq.pregunta,
      respuesta: faq.respuesta,
      categoria: faq.categoria,
      activo: faq.activo
    });
    setShowModal(true);
  };

  const resetForm = () => {
    setEditingFaq(null);
    setFormData({
      pregunta: '',
      respuesta: '',
      categoria: 'proceso',
      activo: true
    });
  };

  // Agrupar por categoría
  const faqsPorCategoria = {};
  Object.keys(CATEGORIAS).forEach(cat => {
    faqsPorCategoria[cat] = faqs.filter(f => f.categoria === cat);
  });

  if (!isMaster()) {
    return (
      <div className="p-8 text-center">
        <AlertTriangle className="w-12 h-12 mx-auto text-yellow-500 mb-4" />
        <p className="text-gray-500">Solo el usuario Master puede gestionar las FAQs</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <HelpCircle className="w-6 h-6" />
            Gestión de FAQs
          </h1>
          <p className="text-muted-foreground">Preguntas frecuentes para la web pública</p>
        </div>
        <div className="flex gap-2">
          {faqs.length === 0 && (
            <Button variant="outline" onClick={handleInicializar}>
              <Sparkles className="w-4 h-4 mr-2" />
              Crear FAQs predeterminadas
            </Button>
          )}
          <Button onClick={() => { resetForm(); setShowModal(true); }}>
            <Plus className="w-4 h-4 mr-2" />
            Nueva FAQ
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <p className="text-2xl font-bold">{faqs.length}</p>
            <p className="text-sm text-muted-foreground">Total FAQs</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-2xl font-bold text-green-600">{faqs.filter(f => f.activo).length}</p>
            <p className="text-sm text-muted-foreground">Activas</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-2xl font-bold text-gray-400">{faqs.filter(f => !f.activo).length}</p>
            <p className="text-sm text-muted-foreground">Ocultas</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-2xl font-bold">{Object.keys(CATEGORIAS).length}</p>
            <p className="text-sm text-muted-foreground">Categorías</p>
          </CardContent>
        </Card>
      </div>

      {/* FAQs por categoría */}
      {loading ? (
        <Card>
          <CardContent className="py-12 text-center">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-muted-foreground" />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {Object.entries(CATEGORIAS).map(([catKey, catInfo]) => {
            const faqsCat = faqsPorCategoria[catKey] || [];
            
            return (
              <Card key={catKey}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <span className="text-2xl">{catInfo.icono}</span>
                    {catInfo.nombre}
                    <Badge variant="secondary">{faqsCat.length}</Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {faqsCat.length === 0 ? (
                    <p className="text-muted-foreground text-center py-4">
                      No hay FAQs en esta categoría
                    </p>
                  ) : (
                    <div className="space-y-3">
                      {faqsCat.map((faq) => (
                        <div
                          key={faq.id}
                          className={`border rounded-lg p-4 ${!faq.activo ? 'opacity-50 bg-gray-50' : ''}`}
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                {faq.activo ? (
                                  <Eye className="w-4 h-4 text-green-500" />
                                ) : (
                                  <EyeOff className="w-4 h-4 text-gray-400" />
                                )}
                                <p className="font-medium">{faq.pregunta}</p>
                              </div>
                              <p className="text-sm text-muted-foreground line-clamp-2">
                                {faq.respuesta}
                              </p>
                            </div>
                            
                            <div className="flex items-center gap-2">
                              <Switch
                                checked={faq.activo}
                                onCheckedChange={() => handleToggleActivo(faq)}
                              />
                              <Button
                                size="icon"
                                variant="ghost"
                                onClick={() => openEditModal(faq)}
                              >
                                <Edit className="w-4 h-4" />
                              </Button>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="text-red-500 hover:text-red-700"
                                onClick={() => handleDelete(faq)}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Modal: Crear/Editar FAQ */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editingFaq ? 'Editar FAQ' : 'Nueva FAQ'}</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Categoría</label>
              <Select
                value={formData.categoria}
                onValueChange={(v) => setFormData({ ...formData, categoria: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(CATEGORIAS).map(([key, info]) => (
                    <SelectItem key={key} value={key}>
                      {info.icono} {info.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="text-sm font-medium">Pregunta</label>
              <Input
                value={formData.pregunta}
                onChange={(e) => setFormData({ ...formData, pregunta: e.target.value })}
                placeholder="¿Cómo funciona...?"
              />
            </div>
            
            <div>
              <label className="text-sm font-medium">Respuesta</label>
              <Textarea
                value={formData.respuesta}
                onChange={(e) => setFormData({ ...formData, respuesta: e.target.value })}
                placeholder="Escribe la respuesta detallada..."
                rows={6}
              />
            </div>
            
            <div className="flex items-center gap-2">
              <Switch
                checked={formData.activo}
                onCheckedChange={(v) => setFormData({ ...formData, activo: v })}
              />
              <label className="text-sm">Visible en la web pública</label>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowModal(false)}>Cancelar</Button>
            <Button onClick={handleSubmit}>
              <Save className="w-4 h-4 mr-2" />
              {editingFaq ? 'Guardar cambios' : 'Crear FAQ'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

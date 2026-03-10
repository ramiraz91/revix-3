import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Bell, AlertTriangle, Info, AlertOctagon, Check, ExternalLink, Eye } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useNavigate } from 'react-router-dom';
import API from '@/lib/api';
import { toast } from 'sonner';

const SEV_CONFIG = {
  info: { icon: Info, color: 'text-blue-600', bg: 'bg-blue-50 border-blue-200', badge: 'bg-blue-100 text-blue-800' },
  warning: { icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50 border-amber-200', badge: 'bg-amber-100 text-amber-800' },
  critical: { icon: AlertOctagon, color: 'text-red-600', bg: 'bg-red-50 border-red-200', badge: 'bg-red-100 text-red-800' },
};

const TIPO_LABELS = {
  imagenes_faltantes: 'Imágenes Faltantes',
  documentacion_faltante: 'Documentación',
  sla_24h: 'Aviso 24h',
  sla_48h: 'Aviso 48h',
  recordatorio: 'Recordatorio',
  incidencia_proveedor: 'Incidencia',
  nuevo_siniestro: 'Nuevo Siniestro',
  presupuesto_aceptado: 'Aceptado',
  presupuesto_rechazado: 'Rechazado',
  desconocido: 'Otro',
};

export default function NotificacionesExternas() {
  const [items, setItems] = useState([]);
  const [resumen, setResumen] = useState({ info: 0, warning: 0, critical: 0, total: 0 });
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('todas');
  const [selected, setSelected] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetch = async () => {
      try {
        const params = {};
        if (filter === 'no_leidas') params.no_leidas = true;
        if (filter === 'no_resueltas') params.no_resueltas = true;
        if (['info', 'warning', 'critical'].includes(filter)) params.severidad = filter;
        const [res, sumRes] = await Promise.all([
          API.get('/notificaciones-externas', { params }),
          API.get('/notificaciones-externas/resumen')
        ]);
        setItems(res.data);
        setResumen(sumRes.data);
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    };
    fetch();
  }, [filter]);

  const handleLeer = async (id) => {
    try {
      await API.patch(`/notificaciones-externas/${id}/leer`);
      setItems(prev => prev.map(i => i.id === id ? {...i, leida: true} : i));
    } catch (e) { toast.error('Error'); }
  };

  const handleResolver = async (id) => {
    try {
      await API.patch(`/notificaciones-externas/${id}/resolver`);
      toast.success('Notificación resuelta');
      setItems(prev => prev.map(i => i.id === id ? {...i, resuelta: true, leida: true} : i));
      setSelected(null);
    } catch (e) { toast.error('Error'); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" /></div>;

  return (
    <div className="space-y-4" data-testid="notificaciones-externas-page">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2"><Bell className="w-6 h-6" /> Notificaciones Externas</h1>
        <div className="flex gap-2">
          {resumen.critical > 0 && <Badge className="bg-red-100 text-red-800">{resumen.critical} críticas</Badge>}
          {resumen.warning > 0 && <Badge className="bg-amber-100 text-amber-800">{resumen.warning} avisos</Badge>}
          <Badge variant="outline">{resumen.total} pendientes</Badge>
        </div>
      </div>

      <Select value={filter} onValueChange={setFilter}>
        <SelectTrigger className="w-52 h-9"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="todas">Todas</SelectItem>
          <SelectItem value="no_leidas">No leídas</SelectItem>
          <SelectItem value="no_resueltas">No resueltas</SelectItem>
          <SelectItem value="critical">Críticas</SelectItem>
          <SelectItem value="warning">Avisos</SelectItem>
          <SelectItem value="info">Info</SelectItem>
        </SelectContent>
      </Select>

      {items.length === 0 ? (
        <Card><CardContent className="py-12 text-center text-muted-foreground">No hay notificaciones externas</CardContent></Card>
      ) : (
        <div className="space-y-2">
          {items.map(item => {
            const sev = SEV_CONFIG[item.severidad] || SEV_CONFIG.info;
            const Icon = sev.icon;
            return (
              <Card key={item.id} className={`border ${item.resuelta ? 'opacity-60' : sev.bg} cursor-pointer hover:shadow-sm transition`} onClick={() => { setSelected(item); if (!item.leida) handleLeer(item.id); }}>
                <CardContent className="py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Icon className={`w-5 h-5 ${sev.color} flex-shrink-0`} />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold">{item.codigo_siniestro}</span>
                        <Badge className={`text-xs ${sev.badge}`}>{TIPO_LABELS[item.tipo] || item.tipo}</Badge>
                        {!item.leida && <div className="w-2 h-2 bg-blue-500 rounded-full" />}
                      </div>
                      <p className="text-xs text-muted-foreground truncate max-w-md mt-0.5">{item.titulo}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {item.resuelta && <Check className="w-4 h-4 text-green-500" />}
                    {item.orden_id && (
                      <Button variant="ghost" size="sm" onClick={e => { e.stopPropagation(); navigate(`/ordenes/${item.orden_id}`); }}>
                        <ExternalLink className="w-3 h-3" />
                      </Button>
                    )}
                    <span className="text-xs text-muted-foreground">{item.created_at?.slice(0, 10)}</span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle className="flex items-center gap-2">{selected?.codigo_siniestro} - {TIPO_LABELS[selected?.tipo] || selected?.tipo}</DialogTitle></DialogHeader>
          {selected && (
            <div className="space-y-4">
              <div className="text-sm">
                <p className="text-xs text-muted-foreground mb-1">Asunto email</p>
                <p>{selected.email_subject}</p>
              </div>
              <div className="text-sm max-h-48 overflow-y-auto">
                <p className="text-xs text-muted-foreground mb-1">Contenido</p>
                <pre className="whitespace-pre-wrap text-xs bg-muted p-3 rounded">{selected.contenido?.slice(0, 2000)}</pre>
              </div>
              {!selected.resuelta && (
                <Button size="sm" onClick={() => handleResolver(selected.id)} className="bg-green-600 hover:bg-green-700">
                  <Check className="w-4 h-4 mr-1" /> Marcar como Resuelta
                </Button>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

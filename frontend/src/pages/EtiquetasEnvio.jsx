import { useState } from 'react';
import { Search, FileDown, ExternalLink, Package, ArrowDown, ArrowUp, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import api from '@/lib/api';

const STATE_COLORS = {
  grabado: 'bg-slate-100 text-slate-700',
  en_transito: 'bg-indigo-100 text-indigo-700',
  entregado: 'bg-green-100 text-green-700',
  devuelto: 'bg-red-100 text-red-700',
  anulado: 'bg-gray-100 text-gray-500',
  error: 'bg-red-200 text-red-800',
};

export default function EtiquetasEnvio() {
  const [search, setSearch] = useState('');
  const [fecha, setFecha] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [codigoDirecto, setCodigoDirecto] = useState('');

  const handleBuscar = async (e) => {
    e?.preventDefault();
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: 100 });
      if (search) params.set('search', search);
      if (fecha) {
        params.set('fecha_desde', `${fecha}T00:00:00`);
        params.set('fecha_hasta', `${fecha}T23:59:59`);
      }
      const res = await api.get(`/gls/envios?${params}`);
      setResults(res.data.data || []);
      if (res.data.total === 0) toast.info('No se encontraron resultados');
    } catch (err) {
      toast.error('Error buscando etiquetas');
    } finally {
      setLoading(false);
    }
  };

  const handleDescargar = async (id) => {
    try {
      const res = await api.get(`/gls/etiqueta/${id}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `etiqueta_gls_${id.substring(0, 8)}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      toast.error('Etiqueta no disponible');
    }
  };

  const handleDescargarDirecto = async () => {
    if (!codigoDirecto.trim()) return toast.error('Introduce un código');
    try {
      const res = await api.get(`/gls/etiqueta-por-codigo/${codigoDirecto.trim()}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `etiqueta_gls_${codigoDirecto.trim()}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('Etiqueta descargada');
    } catch (err) {
      toast.error('Etiqueta no encontrada para este código');
    }
  };

  return (
    <div className="space-y-6" data-testid="etiquetas-page">
      <h1 className="text-2xl font-bold flex items-center gap-2"><FileDown className="w-6 h-6" /> Etiquetas de Envío</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Búsqueda por referencia/fecha */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Buscar Etiquetas GLS</CardTitle>
            <CardDescription>Por referencia, código de barras o fecha</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleBuscar} className="space-y-3">
              <div>
                <Label className="text-xs">Referencia / Código barras</Label>
                <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Código, referencia, cliente..." data-testid="etiqueta-search" />
              </div>
              <div>
                <Label className="text-xs">Fecha</Label>
                <Input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} data-testid="etiqueta-fecha" />
              </div>
              <Button type="submit" disabled={loading} className="w-full" data-testid="btn-buscar-etiquetas">
                {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Search className="w-4 h-4 mr-2" />}
                Buscar
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Descarga directa por código */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Reimprimir por Código</CardTitle>
            <CardDescription>Descarga directa por código de barras GLS</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Label className="text-xs">Código de barras GLS</Label>
              <Input value={codigoDirecto} onChange={(e) => setCodigoDirecto(e.target.value)} placeholder="61771001452051" className="font-mono" data-testid="etiqueta-codigo-directo" />
            </div>
            <Button onClick={handleDescargarDirecto} variant="outline" className="w-full" data-testid="btn-reimprimir">
              <FileDown className="w-4 h-4 mr-2" /> Descargar Etiqueta
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Resultados */}
      {results.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Resultados ({results.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {results.map((e) => (
                <div key={e.id} className="p-3 bg-slate-50 rounded-lg border hover:border-orange-200 transition-colors flex items-center justify-between" data-testid={`etiqueta-row-${e.id}`}>
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    {e.tipo === 'recogida' ? <ArrowDown className="w-4 h-4 text-amber-600 shrink-0" /> : <ArrowUp className="w-4 h-4 text-green-600 shrink-0" />}
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant="outline" className="font-mono text-xs">{e.gls_codbarras || '-'}</Badge>
                        <Badge className={`text-xs ${STATE_COLORS[e.estado_interno] || 'bg-gray-100'}`}>{e.estado_interno?.replace(/_/g, ' ')}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground truncate">
                        {e.destinatario?.nombre} · Ref: {e.referencia_interna} · {new Date(e.created_at).toLocaleDateString('es-ES')}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button size="sm" variant="outline" onClick={() => handleDescargar(e.id)} data-testid={`btn-download-${e.id}`}>
                      <FileDown className="w-4 h-4 mr-1" /> Descargar
                    </Button>
                    {e.gls_codbarras && (
                      <a href={`https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/?match=${e.gls_codbarras}`} target="_blank" rel="noopener noreferrer">
                        <Button size="sm" variant="ghost"><ExternalLink className="w-4 h-4" /></Button>
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {results.length === 0 && !loading && (
        <div className="text-center py-12 text-muted-foreground">
          <Package className="w-16 h-16 mx-auto mb-4 opacity-20" />
          <p>Busca etiquetas por referencia, código de barras o fecha</p>
        </div>
      )}
    </div>
  );
}

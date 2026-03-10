/**
 * Historial de Mercado
 * Tabla con filtros de todos los presupuestos cerrados
 */
import { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  Download,
  RefreshCw,
  Trophy,
  XCircle,
  MinusCircle,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { inteligenciaPreciosAPI } from '@/lib/api';
import { toast } from 'sonner';

export default function HistorialMercado() {
  const [historial, setHistorial] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [filters, setFilters] = useState({
    resultado: '',
    dispositivo: '',
    competidor: ''
  });

  const LIMIT = 20;

  useEffect(() => {
    cargarHistorial();
  }, [page, filters]);

  const cargarHistorial = async () => {
    try {
      setLoading(true);
      const params = {
        skip: page * LIMIT,
        limit: LIMIT,
        ...(filters.resultado && { resultado: filters.resultado }),
        ...(filters.dispositivo && { dispositivo: filters.dispositivo }),
        ...(filters.competidor && { competidor: filters.competidor })
      };
      
      const data = await inteligenciaPreciosAPI.getHistorial(params);
      setHistorial(data.registros || []);
      setTotal(data.total || 0);
    } catch (error) {
      console.error('Error cargando historial:', error);
      toast.error('Error al cargar historial');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(0);
  };

  const limpiarFiltros = () => {
    setFilters({ resultado: '', dispositivo: '', competidor: '' });
    setPage(0);
  };

  const getResultadoBadge = (resultado) => {
    switch (resultado) {
      case 'ganado':
        return <Badge className="bg-green-500"><Trophy className="w-3 h-3 mr-1" /> Ganado</Badge>;
      case 'perdido':
        return <Badge variant="destructive"><XCircle className="w-3 h-3 mr-1" /> Perdido</Badge>;
      case 'cancelado_cliente':
        return <Badge variant="secondary"><MinusCircle className="w-3 h-3 mr-1" /> Cancelado</Badge>;
      default:
        return <Badge variant="outline">{resultado}</Badge>;
    }
  };

  const totalPages = Math.ceil(total / LIMIT);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Historial de Mercado</CardTitle>
            <CardDescription>
              {total} registros de presupuestos cerrados
            </CardDescription>
          </div>
          <Button variant="outline" onClick={cargarHistorial} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {/* Filtros */}
        <div className="flex flex-wrap gap-3 mb-4">
          <Select 
            value={filters.resultado || "all"} 
            onValueChange={(v) => handleFilterChange('resultado', v === "all" ? '' : v)}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Resultado" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              <SelectItem value="ganado">Ganados</SelectItem>
              <SelectItem value="perdido">Perdidos</SelectItem>
              <SelectItem value="cancelado_cliente">Cancelados</SelectItem>
            </SelectContent>
          </Select>

          <Input
            placeholder="Buscar dispositivo..."
            value={filters.dispositivo}
            onChange={(e) => handleFilterChange('dispositivo', e.target.value)}
            className="w-48"
          />

          <Input
            placeholder="Buscar competidor..."
            value={filters.competidor}
            onChange={(e) => handleFilterChange('competidor', e.target.value)}
            className="w-48"
          />

          {(filters.resultado || filters.dispositivo || filters.competidor) && (
            <Button variant="ghost" size="sm" onClick={limpiarFiltros}>
              <XCircle className="w-4 h-4 mr-1" />
              Limpiar
            </Button>
          )}
        </div>

        {/* Tabla */}
        {loading ? (
          <div className="flex justify-center py-8">
            <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : historial.length > 0 ? (
          <>
            <div className="rounded-md border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Código</TableHead>
                    <TableHead>Dispositivo</TableHead>
                    <TableHead>Reparación</TableHead>
                    <TableHead>Resultado</TableHead>
                    <TableHead className="text-right">Tu Precio</TableHead>
                    <TableHead className="text-right">Ganador</TableHead>
                    <TableHead>Competidores</TableHead>
                    <TableHead>Fecha</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {historial.map((reg, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-mono text-sm">{reg.codigo_siniestro}</TableCell>
                      <TableCell>
                        <div className="max-w-[150px] truncate" title={reg.dispositivo_key}>
                          {reg.dispositivo_key || '-'}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {reg.tipo_reparacion_key || 'OTROS'}
                        </Badge>
                      </TableCell>
                      <TableCell>{getResultadoBadge(reg.resultado)}</TableCell>
                      <TableCell className="text-right font-medium">
                        {reg.mi_precio ? `${reg.mi_precio}€` : '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        {reg.resultado === 'perdido' && reg.precio_ganador ? (
                          <div>
                            <div className="font-medium text-red-600">{reg.precio_ganador}€</div>
                            <div className="text-xs text-gray-500 truncate max-w-[120px]" title={reg.ganador_nombre}>
                              {reg.ganador_nombre}
                            </div>
                          </div>
                        ) : reg.resultado === 'ganado' ? (
                          <span className="text-green-600 font-medium">TÚ</span>
                        ) : '-'}
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge variant="secondary">{reg.num_competidores}</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {reg.fecha_cierre?.slice(0, 10)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Paginación */}
            <div className="flex items-center justify-between mt-4">
              <div className="text-sm text-gray-500">
                Mostrando {page * LIMIT + 1}-{Math.min((page + 1) * LIMIT, total)} de {total}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="flex items-center px-3 text-sm">
                  {page + 1} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => p + 1)}
                  disabled={page >= totalPages - 1}
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <Search className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No hay registros que coincidan con los filtros</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

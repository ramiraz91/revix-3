import { useState, useEffect } from 'react';
import { 
  Recycle, 
  Plus, 
  Search, 
  Smartphone,
  Package,
  MapPin,
  Trash2,
  Eye,
  ChevronRight,
  Loader2,
  X
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { toast } from 'sonner';
import { restosAPI } from '@/lib/api';

const estadoFisicoConfig = {
  bueno: { label: 'Bueno', color: 'bg-green-500' },
  regular: { label: 'Regular', color: 'bg-yellow-500' },
  malo: { label: 'Malo', color: 'bg-red-500' }
};

export default function Restos() {
  const [restos, setRestos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showNuevoDialog, setShowNuevoDialog] = useState(false);
  const [showDetalleDialog, setShowDetalleDialog] = useState(false);
  const [restoSeleccionado, setRestoSeleccionado] = useState(null);
  const [nuevaPieza, setNuevaPieza] = useState('');
  const [formData, setFormData] = useState({
    modelo: '',
    imei: '',
    color: '',
    estado_fisico: 'regular',
    descripcion: '',
    piezas_aprovechables: [],
    ubicacion_almacen: ''
  });

  useEffect(() => {
    fetchRestos();
  }, []);

  const fetchRestos = async () => {
    try {
      setLoading(true);
      const response = await restosAPI.listar({ search, activo: true });
      setRestos(response.data);
    } catch (error) {
      toast.error('Error al cargar dispositivos');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    fetchRestos();
  };

  const handleCrear = async () => {
    if (!formData.modelo) {
      toast.error('El modelo es obligatorio');
      return;
    }
    try {
      await restosAPI.crear(formData);
      toast.success('Dispositivo registrado');
      setShowNuevoDialog(false);
      resetForm();
      fetchRestos();
    } catch (error) {
      toast.error('Error al crear dispositivo');
    }
  };

  const handleEliminar = async (id) => {
    if (!confirm('¿Desactivar este dispositivo de restos?')) return;
    try {
      await restosAPI.eliminar(id);
      toast.success('Dispositivo desactivado');
      fetchRestos();
    } catch (error) {
      toast.error('Error al eliminar');
    }
  };

  const agregarPieza = () => {
    if (!nuevaPieza.trim()) return;
    setFormData(prev => ({
      ...prev,
      piezas_aprovechables: [...prev.piezas_aprovechables, nuevaPieza.trim()]
    }));
    setNuevaPieza('');
  };

  const quitarPieza = (index) => {
    setFormData(prev => ({
      ...prev,
      piezas_aprovechables: prev.piezas_aprovechables.filter((_, i) => i !== index)
    }));
  };

  const resetForm = () => {
    setFormData({
      modelo: '',
      imei: '',
      color: '',
      estado_fisico: 'regular',
      descripcion: '',
      piezas_aprovechables: [],
      ubicacion_almacen: ''
    });
  };

  const verDetalle = (resto) => {
    setRestoSeleccionado(resto);
    setShowDetalleDialog(true);
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="restos-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Recycle className="w-8 h-8 text-teal-600" />
            Dispositivos de Restos
          </h1>
          <p className="text-muted-foreground mt-1">
            Gestión de dispositivos abandonados y piezas aprovechables
          </p>
        </div>
        <Button onClick={() => setShowNuevoDialog(true)} data-testid="nuevo-resto-btn">
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Dispositivo
        </Button>
      </div>

      {/* Búsqueda */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por modelo, código o IMEI..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="pl-10"
              />
            </div>
            <Button onClick={handleSearch}>Buscar</Button>
          </div>
        </CardContent>
      </Card>

      {/* Lista */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : restos.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Recycle className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
            <h3 className="font-semibold text-lg">No hay dispositivos de restos</h3>
            <p className="text-muted-foreground">
              Registra dispositivos abandonados para aprovechar sus piezas
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Código</TableHead>
                <TableHead>Modelo</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Piezas Disp.</TableHead>
                <TableHead>Ubicación</TableHead>
                <TableHead>Fecha</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {restos.map((resto) => (
                <TableRow key={resto.id} className="cursor-pointer hover:bg-slate-50">
                  <TableCell className="font-mono font-medium">{resto.codigo}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Smartphone className="w-4 h-4 text-muted-foreground" />
                      {resto.modelo}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge 
                      variant="outline" 
                      className={`${estadoFisicoConfig[resto.estado_fisico]?.color} text-white border-0`}
                    >
                      {estadoFisicoConfig[resto.estado_fisico]?.label}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">
                      {resto.piezas_aprovechables?.length || 0} piezas
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {resto.ubicacion_almacen || '-'}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(resto.fecha_ingreso).toLocaleDateString('es-ES')}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" onClick={() => verDetalle(resto)}>
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="text-red-500 hover:text-red-600"
                        onClick={() => handleEliminar(resto.id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Dialog Nuevo Dispositivo */}
      <Dialog open={showNuevoDialog} onOpenChange={setShowNuevoDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Registrar Dispositivo de Restos</DialogTitle>
            <DialogDescription>
              Añade un dispositivo abandonado para gestionar sus piezas aprovechables
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label>Modelo *</Label>
                <Input
                  value={formData.modelo}
                  onChange={(e) => setFormData(prev => ({ ...prev, modelo: e.target.value }))}
                  placeholder="iPhone 12 Pro Max"
                />
              </div>
              <div>
                <Label>IMEI</Label>
                <Input
                  value={formData.imei}
                  onChange={(e) => setFormData(prev => ({ ...prev, imei: e.target.value }))}
                  placeholder="123456789012345"
                />
              </div>
              <div>
                <Label>Color</Label>
                <Input
                  value={formData.color}
                  onChange={(e) => setFormData(prev => ({ ...prev, color: e.target.value }))}
                  placeholder="Negro"
                />
              </div>
              <div>
                <Label>Estado Físico</Label>
                <Select
                  value={formData.estado_fisico}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, estado_fisico: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bueno">Bueno</SelectItem>
                    <SelectItem value="regular">Regular</SelectItem>
                    <SelectItem value="malo">Malo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Ubicación en Almacén</Label>
                <Input
                  value={formData.ubicacion_almacen}
                  onChange={(e) => setFormData(prev => ({ ...prev, ubicacion_almacen: e.target.value }))}
                  placeholder="Estante A-3"
                />
              </div>
            </div>

            <div>
              <Label>Descripción</Label>
              <Textarea
                value={formData.descripcion}
                onChange={(e) => setFormData(prev => ({ ...prev, descripcion: e.target.value }))}
                placeholder="Notas sobre el estado del dispositivo..."
              />
            </div>

            {/* Piezas aprovechables */}
            <div>
              <Label>Piezas Aprovechables</Label>
              <div className="flex gap-2 mt-1">
                <Input
                  value={nuevaPieza}
                  onChange={(e) => setNuevaPieza(e.target.value)}
                  placeholder="Ej: Pantalla, Batería, Cámara..."
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), agregarPieza())}
                />
                <Button type="button" variant="outline" onClick={agregarPieza}>
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
              {formData.piezas_aprovechables.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {formData.piezas_aprovechables.map((pieza, index) => (
                    <Badge key={index} variant="secondary" className="gap-1">
                      {pieza}
                      <X 
                        className="w-3 h-3 cursor-pointer hover:text-red-500" 
                        onClick={() => quitarPieza(index)}
                      />
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowNuevoDialog(false)}>
              Cancelar
            </Button>
            <Button onClick={handleCrear}>
              Registrar Dispositivo
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog Detalle */}
      <Dialog open={showDetalleDialog} onOpenChange={setShowDetalleDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Smartphone className="w-5 h-5" />
              {restoSeleccionado?.modelo}
            </DialogTitle>
            <DialogDescription>
              Código: {restoSeleccionado?.codigo}
            </DialogDescription>
          </DialogHeader>

          {restoSeleccionado && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">IMEI</p>
                  <p className="font-mono">{restoSeleccionado.imei || '-'}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Color</p>
                  <p>{restoSeleccionado.color || '-'}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Estado Físico</p>
                  <Badge 
                    className={`${estadoFisicoConfig[restoSeleccionado.estado_fisico]?.color} text-white`}
                  >
                    {estadoFisicoConfig[restoSeleccionado.estado_fisico]?.label}
                  </Badge>
                </div>
                <div>
                  <p className="text-muted-foreground">Ubicación</p>
                  <p>{restoSeleccionado.ubicacion_almacen || '-'}</p>
                </div>
              </div>

              {restoSeleccionado.descripcion && (
                <div>
                  <p className="text-muted-foreground text-sm">Descripción</p>
                  <p className="p-2 bg-slate-50 rounded mt-1">{restoSeleccionado.descripcion}</p>
                </div>
              )}

              <div>
                <p className="text-muted-foreground text-sm mb-2">Piezas Disponibles</p>
                {restoSeleccionado.piezas_aprovechables?.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {restoSeleccionado.piezas_aprovechables.map((pieza, idx) => (
                      <Badge key={idx} variant="outline" className="bg-green-50 text-green-700">
                        <Package className="w-3 h-3 mr-1" />
                        {pieza}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground italic">No hay piezas disponibles</p>
                )}
              </div>

              {restoSeleccionado.piezas_usadas?.length > 0 && (
                <div>
                  <p className="text-muted-foreground text-sm mb-2">Historial de Piezas Usadas</p>
                  <div className="space-y-2">
                    {restoSeleccionado.piezas_usadas.map((uso, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2 bg-slate-50 rounded text-sm">
                        <span>{uso.pieza}</span>
                        <span className="text-muted-foreground">
                          {new Date(uso.fecha).toLocaleDateString('es-ES')}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

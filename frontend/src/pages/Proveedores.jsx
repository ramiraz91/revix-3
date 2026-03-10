import { useState, useEffect } from 'react';
import { Plus, Search, MoreVertical, Edit, Trash2, Truck } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { proveedoresAPI } from '@/lib/api';
import { toast } from 'sonner';

const emptyProveedor = {
  nombre: '',
  contacto: '',
  telefono: '',
  email: '',
  direccion: '',
  notas: ''
};

export default function Proveedores() {
  const [proveedores, setProveedores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingProveedor, setEditingProveedor] = useState(null);
  const [formData, setFormData] = useState(emptyProveedor);

  const fetchProveedores = async () => {
    try {
      setLoading(true);
      const res = await proveedoresAPI.listar(search);
      setProveedores(res.data);
    } catch (error) {
      toast.error('Error al cargar proveedores');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProveedores();
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchProveedores();
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleOpenDialog = (proveedor = null) => {
    if (proveedor) {
      setEditingProveedor(proveedor);
      setFormData(proveedor);
    } else {
      setEditingProveedor(null);
      setFormData(emptyProveedor);
    }
    setShowDialog(true);
  };

  const handleSubmit = async () => {
    try {
      if (editingProveedor) {
        await proveedoresAPI.actualizar(editingProveedor.id, formData);
        toast.success('Proveedor actualizado');
      } else {
        await proveedoresAPI.crear(formData);
        toast.success('Proveedor creado');
      }
      setShowDialog(false);
      fetchProveedores();
    } catch (error) {
      toast.error('Error al guardar proveedor');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Estás seguro de eliminar este proveedor?')) return;
    try {
      await proveedoresAPI.eliminar(id);
      toast.success('Proveedor eliminado');
      fetchProveedores();
    } catch (error) {
      toast.error('Error al eliminar proveedor');
    }
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="proveedores-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Proveedores</h1>
          <p className="text-muted-foreground mt-1">Gestiona tus proveedores de repuestos</p>
        </div>
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogTrigger asChild>
            <Button onClick={() => handleOpenDialog()} data-testid="new-proveedor-btn">
              <Plus className="w-4 h-4 mr-2" />
              Nuevo Proveedor
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>{editingProveedor ? 'Editar Proveedor' : 'Nuevo Proveedor'}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Nombre de la Empresa *</Label>
                <Input 
                  value={formData.nombre}
                  onChange={(e) => handleInputChange('nombre', e.target.value)}
                  data-testid="input-nombre"
                />
              </div>
              <div>
                <Label>Persona de Contacto</Label>
                <Input 
                  value={formData.contacto}
                  onChange={(e) => handleInputChange('contacto', e.target.value)}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Teléfono</Label>
                  <Input 
                    value={formData.telefono}
                    onChange={(e) => handleInputChange('telefono', e.target.value)}
                  />
                </div>
                <div>
                  <Label>Email</Label>
                  <Input 
                    type="email"
                    value={formData.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                  />
                </div>
              </div>
              <div>
                <Label>Dirección</Label>
                <Input 
                  value={formData.direccion}
                  onChange={(e) => handleInputChange('direccion', e.target.value)}
                />
              </div>
              <div>
                <Label>Notas</Label>
                <Textarea 
                  value={formData.notas}
                  onChange={(e) => handleInputChange('notas', e.target.value)}
                  rows={3}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="outline" onClick={() => setShowDialog(false)}>
                Cancelar
              </Button>
              <Button onClick={handleSubmit} data-testid="save-proveedor-btn">
                {editingProveedor ? 'Guardar Cambios' : 'Crear Proveedor'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="p-4">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por nombre..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
                data-testid="search-input"
              />
            </div>
            <Button type="submit" variant="secondary">
              Buscar
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-muted-foreground">
              Cargando proveedores...
            </div>
          ) : proveedores.length === 0 ? (
            <div className="p-8 text-center">
              <Truck className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-lg font-medium">No hay proveedores</p>
              <p className="text-muted-foreground">Añade tu primer proveedor</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Empresa</TableHead>
                    <TableHead>Contacto</TableHead>
                    <TableHead>Teléfono</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Dirección</TableHead>
                    <TableHead className="w-12"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {proveedores.map((proveedor) => (
                    <TableRow key={proveedor.id} data-testid={`proveedor-row-${proveedor.id}`}>
                      <TableCell className="font-medium">{proveedor.nombre}</TableCell>
                      <TableCell>{proveedor.contacto || '-'}</TableCell>
                      <TableCell>{proveedor.telefono || '-'}</TableCell>
                      <TableCell>{proveedor.email || '-'}</TableCell>
                      <TableCell className="max-w-xs truncate">{proveedor.direccion || '-'}</TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleOpenDialog(proveedor)}>
                              <Edit className="w-4 h-4 mr-2" />
                              Editar
                            </DropdownMenuItem>
                            <DropdownMenuItem 
                              className="text-destructive"
                              onClick={() => handleDelete(proveedor.id)}
                            >
                              <Trash2 className="w-4 h-4 mr-2" />
                              Eliminar
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

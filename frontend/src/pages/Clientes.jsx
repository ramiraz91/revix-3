import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, MoreVertical, Edit, Trash2, Users, Eye } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { clientesAPI } from '@/lib/api';
import { toast } from 'sonner';

const emptyCliente = {
  nombre: '',
  apellidos: '',
  dni: '',
  telefono: '',
  email: '',
  direccion: '',
  planta: '',
  puerta: '',
  ciudad: '',
  codigo_postal: ''
};

export default function Clientes() {
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingCliente, setEditingCliente] = useState(null);
  const [formData, setFormData] = useState(emptyCliente);
  const navigate = useNavigate();

  const fetchClientes = async () => {
    try {
      setLoading(true);
      const res = await clientesAPI.listar(search);
      setClientes(res.data);
    } catch (error) {
      toast.error('Error al cargar clientes');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClientes();
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchClientes();
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleOpenDialog = (cliente = null) => {
    if (cliente) {
      setEditingCliente(cliente);
      setFormData(cliente);
    } else {
      setEditingCliente(null);
      setFormData(emptyCliente);
    }
    setShowDialog(true);
  };

  const handleSubmit = async () => {
    try {
      if (editingCliente) {
        await clientesAPI.actualizar(editingCliente.id, formData);
        toast.success('Cliente actualizado');
      } else {
        await clientesAPI.crear(formData);
        toast.success('Cliente creado');
      }
      setShowDialog(false);
      fetchClientes();
    } catch (error) {
      toast.error('Error al guardar cliente');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Estás seguro de eliminar este cliente?')) return;
    try {
      await clientesAPI.eliminar(id);
      toast.success('Cliente eliminado');
      fetchClientes();
    } catch (error) {
      toast.error('Error al eliminar cliente');
    }
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="clientes-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Clientes</h1>
          <p className="text-muted-foreground mt-1">Gestiona tu base de clientes</p>
        </div>
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogTrigger asChild>
            <Button onClick={() => handleOpenDialog()} data-testid="new-client-btn">
              <Plus className="w-4 h-4 mr-2" />
              Nuevo Cliente
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{editingCliente ? 'Editar Cliente' : 'Nuevo Cliente'}</DialogTitle>
            </DialogHeader>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Nombre *</Label>
                <Input 
                  value={formData.nombre}
                  onChange={(e) => handleInputChange('nombre', e.target.value)}
                  data-testid="input-nombre"
                />
              </div>
              <div>
                <Label>Apellidos *</Label>
                <Input 
                  value={formData.apellidos}
                  onChange={(e) => handleInputChange('apellidos', e.target.value)}
                  data-testid="input-apellidos"
                />
              </div>
              <div>
                <Label>DNI *</Label>
                <Input 
                  value={formData.dni}
                  onChange={(e) => handleInputChange('dni', e.target.value)}
                  data-testid="input-dni"
                />
              </div>
              <div>
                <Label>Teléfono *</Label>
                <Input 
                  value={formData.telefono}
                  onChange={(e) => handleInputChange('telefono', e.target.value)}
                  data-testid="input-telefono"
                />
              </div>
              <div className="col-span-2">
                <Label>Email</Label>
                <Input 
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleInputChange('email', e.target.value)}
                />
              </div>
              <div className="col-span-2">
                <Label>Dirección *</Label>
                <Input 
                  value={formData.direccion}
                  onChange={(e) => handleInputChange('direccion', e.target.value)}
                  data-testid="input-direccion"
                />
              </div>
              <div>
                <Label>Planta</Label>
                <Input 
                  value={formData.planta}
                  onChange={(e) => handleInputChange('planta', e.target.value)}
                />
              </div>
              <div>
                <Label>Puerta</Label>
                <Input 
                  value={formData.puerta}
                  onChange={(e) => handleInputChange('puerta', e.target.value)}
                />
              </div>
              <div>
                <Label>Ciudad</Label>
                <Input 
                  value={formData.ciudad}
                  onChange={(e) => handleInputChange('ciudad', e.target.value)}
                />
              </div>
              <div>
                <Label>Código Postal</Label>
                <Input 
                  value={formData.codigo_postal}
                  onChange={(e) => handleInputChange('codigo_postal', e.target.value)}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="outline" onClick={() => setShowDialog(false)}>
                Cancelar
              </Button>
              <Button onClick={handleSubmit} data-testid="save-client-btn">
                {editingCliente ? 'Guardar Cambios' : 'Crear Cliente'}
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
                placeholder="Buscar por nombre, DNI o teléfono..."
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
              Cargando clientes...
            </div>
          ) : clientes.length === 0 ? (
            <div className="p-8 text-center">
              <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-lg font-medium">No hay clientes</p>
              <p className="text-muted-foreground">Crea tu primer cliente</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nombre</TableHead>
                    <TableHead>DNI</TableHead>
                    <TableHead>Teléfono</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Dirección</TableHead>
                    <TableHead className="w-12"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {clientes.map((cliente) => (
                    <TableRow 
                      key={cliente.id} 
                      data-testid={`cliente-row-${cliente.id}`}
                      className="cursor-pointer hover:bg-slate-50"
                      onClick={() => navigate(`/clientes/${cliente.id}`)}
                    >
                      <TableCell className="font-medium">
                        {cliente.nombre} {cliente.apellidos}
                      </TableCell>
                      <TableCell className="font-mono">{cliente.dni}</TableCell>
                      <TableCell>{cliente.telefono}</TableCell>
                      <TableCell>{cliente.email || '-'}</TableCell>
                      <TableCell className="max-w-xs truncate">{cliente.direccion}</TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <Button variant="ghost" size="icon">
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); navigate(`/clientes/${cliente.id}`); }}>
                              <Eye className="w-4 h-4 mr-2" />
                              Ver Ficha
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleOpenDialog(cliente); }}>
                              <Edit className="w-4 h-4 mr-2" />
                              Editar
                            </DropdownMenuItem>
                            <DropdownMenuItem 
                              className="text-destructive"
                              onClick={(e) => { e.stopPropagation(); handleDelete(cliente.id); }}
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

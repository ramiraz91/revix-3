import { useState, useEffect } from 'react';
import { 
  Users, 
  Plus, 
  Search, 
  Edit, 
  Trash2, 
  Eye,
  EyeOff,
  UserCog,
  Shield,
  Wrench,
  Crown,
  Mail,
  Phone,
  Calendar,
  DollarSign,
  Clock,
  Loader2,
  CheckCircle,
  XCircle,
  MoreVertical,
  FileText,
  KeyRound,
  Send
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '@/components/ui/dropdown-menu';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { usuariosAPI } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

const roleConfig = {
  master: { label: 'Master', icon: Crown, color: 'bg-purple-500' },
  admin: { label: 'Admin', icon: Shield, color: 'bg-blue-500' },
  tecnico: { label: 'Técnico', icon: Wrench, color: 'bg-green-500' },
};

const jornadaOptions = [
  { value: 'completa', label: 'Jornada Completa' },
  { value: 'parcial', label: 'Jornada Parcial' },
  { value: 'media_jornada', label: 'Media Jornada' },
];

const defaultHorario = {
  lunes: '09:00-18:00',
  martes: '09:00-18:00',
  miercoles: '09:00-18:00',
  jueves: '09:00-18:00',
  viernes: '09:00-18:00',
  sabado: '',
  domingo: '',
};

const emptyForm = {
  email: '',
  password: '',
  nombre: '',
  apellidos: '',
  role: 'tecnico',
  activo: true,
  ficha: {
    dni: '',
    telefono: '',
    direccion: '',
    ciudad: '',
    codigo_postal: '',
    fecha_nacimiento: '',
    fecha_alta: '',
    numero_ss: '',
    cuenta_bancaria: '',
    contacto_emergencia: '',
    telefono_emergencia: '',
  },
  info_laboral: {
    tipo_jornada: 'completa',
    horas_semanales: 40,
    horario: { ...defaultHorario },
    sueldo_bruto: '',
    sueldo_neto: '',
    puesto: '',
    departamento: '',
    vacaciones: {
      dias_totales: 22,
      dias_usados: 0,
      dias_pendientes: 22,
      periodos: [],
    },
  },
};

export default function Usuarios() {
  const { isMaster, user: currentUser } = useAuth();
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterRole, setFilterRole] = useState('all');
  const [filterActivo, setFilterActivo] = useState('all');
  
  // Modal states
  const [showModal, setShowModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [formData, setFormData] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [activeTab, setActiveTab] = useState('general');

  // Password management
  const [nuevaPassword, setNuevaPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [passwordAction, setPasswordAction] = useState(null); // 'cambiar' | 'enviar'
  const [passwordLoading, setPasswordLoading] = useState(false);

  useEffect(() => {
    fetchUsuarios();
  }, []);

  const fetchUsuarios = async () => {
    try {
      setLoading(true);
      const params = {};
      if (search) params.search = search;
      if (filterRole !== 'all') params.role = filterRole;
      if (filterActivo !== 'all') params.activo = filterActivo === 'true';
      
      const response = await usuariosAPI.listar(params);
      setUsuarios(response.data);
    } catch (error) {
      toast.error('Error al cargar usuarios');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchUsuarios();
    }, 300);
    return () => clearTimeout(timer);
  }, [search, filterRole, filterActivo]);

  const handleNew = () => {
    setSelectedUser(null);
    setFormData(emptyForm);
    setActiveTab('general');
    setShowModal(true);
  };

  const handleEdit = (usuario) => {
    setSelectedUser(usuario);
    setFormData({
      email: usuario.email || '',
      password: '', // No mostrar contraseña
      nombre: usuario.nombre || '',
      apellidos: usuario.apellidos || '',
      role: usuario.role || 'tecnico',
      activo: usuario.activo !== false,
      ficha: {
        dni: usuario.ficha?.dni || '',
        telefono: usuario.ficha?.telefono || '',
        direccion: usuario.ficha?.direccion || '',
        ciudad: usuario.ficha?.ciudad || '',
        codigo_postal: usuario.ficha?.codigo_postal || '',
        fecha_nacimiento: usuario.ficha?.fecha_nacimiento || '',
        fecha_alta: usuario.ficha?.fecha_alta || '',
        numero_ss: usuario.ficha?.numero_ss || '',
        cuenta_bancaria: usuario.ficha?.cuenta_bancaria || '',
        contacto_emergencia: usuario.ficha?.contacto_emergencia || '',
        telefono_emergencia: usuario.ficha?.telefono_emergencia || '',
      },
      info_laboral: {
        tipo_jornada: usuario.info_laboral?.tipo_jornada || 'completa',
        horas_semanales: usuario.info_laboral?.horas_semanales || 40,
        horario: usuario.info_laboral?.horario || { ...defaultHorario },
        sueldo_bruto: usuario.info_laboral?.sueldo_bruto || '',
        sueldo_neto: usuario.info_laboral?.sueldo_neto || '',
        puesto: usuario.info_laboral?.puesto || '',
        departamento: usuario.info_laboral?.departamento || '',
        vacaciones: usuario.info_laboral?.vacaciones || {
          dias_totales: 22,
          dias_usados: 0,
          dias_pendientes: 22,
          periodos: [],
        },
      },
    });
    setActiveTab('general');
    setShowModal(true);
  };

  const handleDelete = (usuario) => {
    setSelectedUser(usuario);
    setShowDeleteModal(true);
  };

  const handlePasswordModal = (usuario, action) => {
    setSelectedUser(usuario);
    setPasswordAction(action);
    setNuevaPassword('');
    setShowNewPassword(false);
    setShowPasswordModal(true);
  };

  const handleCambiarPassword = async () => {
    if (!nuevaPassword || nuevaPassword.length < 6) {
      toast.error('La contraseña debe tener al menos 6 caracteres');
      return;
    }
    setPasswordLoading(true);
    try {
      const res = await usuariosAPI.cambiarPassword(selectedUser.id, nuevaPassword);
      toast.success(res.data.message);
      setShowPasswordModal(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al cambiar contraseña');
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleEnviarReset = async () => {
    setPasswordLoading(true);
    try {
      const res = await usuariosAPI.enviarResetPassword(selectedUser.id);
      if (res.data.email_enviado) {
        toast.success(`Contraseña temporal enviada a ${res.data.email_destino}`);
      } else {
        toast.warning(`Contraseña generada, pero no se pudo enviar el email a ${res.data.email_destino}`);
      }
      setShowPasswordModal(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al enviar restablecimiento');
    } finally {
      setPasswordLoading(false);
    }
  };

  const confirmDelete = async () => {
    try {
      await usuariosAPI.eliminar(selectedUser.id);
      toast.success('Usuario eliminado');
      setShowDeleteModal(false);
      fetchUsuarios();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al eliminar usuario');
    }
  };

  const handleToggleActivo = async (usuario) => {
    try {
      const res = await usuariosAPI.toggleActivo(usuario.id);
      toast.success(res.data.message);
      fetchUsuarios();
    } catch (error) {
      toast.error('Error al cambiar estado');
    }
  };

  const handleSave = async () => {
    if (!formData.email || !formData.nombre) {
      toast.error('Email y nombre son obligatorios');
      return;
    }
    
    if (!selectedUser && !formData.password) {
      toast.error('La contraseña es obligatoria para nuevos usuarios');
      return;
    }

    setSaving(true);
    try {
      const dataToSend = {
        ...formData,
        info_laboral: {
          ...formData.info_laboral,
          sueldo_bruto: formData.info_laboral.sueldo_bruto ? parseFloat(formData.info_laboral.sueldo_bruto) : null,
          sueldo_neto: formData.info_laboral.sueldo_neto ? parseFloat(formData.info_laboral.sueldo_neto) : null,
        }
      };
      
      // Si es edición y no hay contraseña nueva, no enviarla
      if (selectedUser && !formData.password) {
        delete dataToSend.password;
      }

      if (selectedUser) {
        await usuariosAPI.actualizar(selectedUser.id, dataToSend);
        toast.success('Usuario actualizado');
      } else {
        await usuariosAPI.crear(dataToSend);
        toast.success('Usuario creado');
      }
      
      setShowModal(false);
      fetchUsuarios();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  const handleFormChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleFichaChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      ficha: { ...prev.ficha, [field]: value }
    }));
  };

  const handleLaboralChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      info_laboral: { ...prev.info_laboral, [field]: value }
    }));
  };

  const handleHorarioChange = (dia, value) => {
    setFormData(prev => ({
      ...prev,
      info_laboral: {
        ...prev.info_laboral,
        horario: { ...prev.info_laboral.horario, [dia]: value }
      }
    }));
  };

  const handleVacacionesChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      info_laboral: {
        ...prev.info_laboral,
        vacaciones: { ...prev.info_laboral.vacaciones, [field]: parseInt(value) || 0 }
      }
    }));
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="usuarios-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Users className="w-8 h-8" />
            Gestión de Usuarios
          </h1>
          <p className="text-muted-foreground mt-1">
            Administra los usuarios y sus permisos
          </p>
        </div>
        <Button onClick={handleNew} className="gap-2" data-testid="nuevo-usuario-btn">
          <Plus className="w-4 h-4" />
          Nuevo Usuario
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por nombre, email, DNI..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
                data-testid="search-usuarios"
              />
            </div>
            <Select value={filterRole} onValueChange={setFilterRole}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Rol" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los roles</SelectItem>
                <SelectItem value="master">Master</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="tecnico">Técnico</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterActivo} onValueChange={setFilterActivo}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="true">Activos</SelectItem>
                <SelectItem value="false">Inactivos</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold">{usuarios.length}</p>
            <p className="text-xs text-muted-foreground">Total Usuarios</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-green-600">
              {usuarios.filter(u => u.activo !== false).length}
            </p>
            <p className="text-xs text-muted-foreground">Activos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-blue-600">
              {usuarios.filter(u => u.role === 'tecnico').length}
            </p>
            <p className="text-xs text-muted-foreground">Técnicos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-purple-600">
              {usuarios.filter(u => u.role === 'admin' || u.role === 'master').length}
            </p>
            <p className="text-xs text-muted-foreground">Admins</p>
          </CardContent>
        </Card>
      </div>

      {/* Users List */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : usuarios.length === 0 ? (
            <div className="text-center py-20">
              <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No hay usuarios</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 border-b">
                  <tr>
                    <th className="text-left p-4 font-medium">Usuario</th>
                    <th className="text-left p-4 font-medium">Email</th>
                    <th className="text-left p-4 font-medium">Rol</th>
                    <th className="text-left p-4 font-medium">Jornada</th>
                    <th className="text-left p-4 font-medium">Estado</th>
                    <th className="text-right p-4 font-medium">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {usuarios.map((usuario) => {
                    const role = roleConfig[usuario.role] || roleConfig.tecnico;
                    const RoleIcon = role.icon;
                    
                    return (
                      <tr 
                        key={usuario.id} 
                        className="hover:bg-slate-50 transition-colors"
                        data-testid={`usuario-row-${usuario.id}`}
                      >
                        <td className="p-4">
                          <div className="flex items-center gap-3">
                            <div className={`w-10 h-10 rounded-full ${role.color} flex items-center justify-center text-white font-semibold`}>
                              {usuario.nombre?.charAt(0) || '?'}
                            </div>
                            <div>
                              <p className="font-medium">{usuario.nombre} {usuario.apellidos}</p>
                              <p className="text-xs text-muted-foreground">
                                {usuario.info_laboral?.puesto || 'Sin puesto'}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="p-4">
                          <div className="flex items-center gap-2 text-sm">
                            <Mail className="w-3 h-3 text-muted-foreground" />
                            {usuario.email}
                          </div>
                        </td>
                        <td className="p-4">
                          <Badge className={`${role.color} text-white gap-1`}>
                            <RoleIcon className="w-3 h-3" />
                            {role.label}
                          </Badge>
                        </td>
                        <td className="p-4">
                          <span className="text-sm">
                            {jornadaOptions.find(j => j.value === usuario.info_laboral?.tipo_jornada)?.label || '-'}
                          </span>
                        </td>
                        <td className="p-4">
                          {usuario.activo !== false ? (
                            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                              <CheckCircle className="w-3 h-3 mr-1" />
                              Activo
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                              <XCircle className="w-3 h-3 mr-1" />
                              Inactivo
                            </Badge>
                          )}
                        </td>
                        <td className="p-4 text-right">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreVertical className="w-4 h-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => handleEdit(usuario)}>
                                <Edit className="w-4 h-4 mr-2" />
                                Editar
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => handleToggleActivo(usuario)}>
                                {usuario.activo !== false ? (
                                  <>
                                    <EyeOff className="w-4 h-4 mr-2" />
                                    Desactivar
                                  </>
                                ) : (
                                  <>
                                    <Eye className="w-4 h-4 mr-2" />
                                    Activar
                                  </>
                                )}
                              </DropdownMenuItem>
                              {isMaster() && (
                                <>
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem onClick={() => handlePasswordModal(usuario, 'cambiar')}>
                                    <KeyRound className="w-4 h-4 mr-2" />
                                    Cambiar contraseña
                                  </DropdownMenuItem>
                                  <DropdownMenuItem onClick={() => handlePasswordModal(usuario, 'enviar')}>
                                    <Send className="w-4 h-4 mr-2" />
                                    Enviar restablecimiento
                                  </DropdownMenuItem>
                                </>
                              )}
                              {isMaster() && usuario.id !== currentUser?.id && (
                                <>
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem 
                                    onClick={() => handleDelete(usuario)}
                                    className="text-red-600"
                                  >
                                    <Trash2 className="w-4 h-4 mr-2" />
                                    Eliminar
                                  </DropdownMenuItem>
                                </>
                              )}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Modal */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {selectedUser ? 'Editar Usuario' : 'Nuevo Usuario'}
            </DialogTitle>
            <DialogDescription>
              {selectedUser ? 'Modifica los datos del usuario' : 'Completa la información del nuevo usuario'}
            </DialogDescription>
          </DialogHeader>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-4">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="general">General</TabsTrigger>
              <TabsTrigger value="personal">Personal</TabsTrigger>
              <TabsTrigger value="laboral">Laboral</TabsTrigger>
              <TabsTrigger value="horario">Horario</TabsTrigger>
            </TabsList>

            {/* TAB: General */}
            <TabsContent value="general" className="space-y-4 mt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Email *</Label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => handleFormChange('email', e.target.value)}
                    placeholder="usuario@empresa.com"
                    data-testid="usuario-email"
                  />
                </div>
                <div>
                  <Label>{selectedUser ? 'Nueva Contraseña' : 'Contraseña *'}</Label>
                  <div className="relative">
                    <Input
                      type={showPassword ? 'text' : 'password'}
                      value={formData.password}
                      onChange={(e) => handleFormChange('password', e.target.value)}
                      placeholder={selectedUser ? 'Dejar vacío para no cambiar' : 'Contraseña segura'}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </Button>
                  </div>
                </div>
                <div>
                  <Label>Nombre *</Label>
                  <Input
                    value={formData.nombre}
                    onChange={(e) => handleFormChange('nombre', e.target.value)}
                    placeholder="Nombre"
                    data-testid="usuario-nombre"
                  />
                </div>
                <div>
                  <Label>Apellidos</Label>
                  <Input
                    value={formData.apellidos}
                    onChange={(e) => handleFormChange('apellidos', e.target.value)}
                    placeholder="Apellidos"
                  />
                </div>
                <div>
                  <Label>Rol</Label>
                  <Select 
                    value={formData.role} 
                    onValueChange={(v) => handleFormChange('role', v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {isMaster() && <SelectItem value="master">Master</SelectItem>}
                      <SelectItem value="admin">Admin</SelectItem>
                      <SelectItem value="tecnico">Técnico</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center gap-3 pt-6">
                  <Switch
                    checked={formData.activo}
                    onCheckedChange={(v) => handleFormChange('activo', v)}
                  />
                  <Label>Usuario Activo</Label>
                </div>
              </div>
            </TabsContent>

            {/* TAB: Personal */}
            <TabsContent value="personal" className="space-y-4 mt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>DNI / NIE</Label>
                  <Input
                    value={formData.ficha.dni}
                    onChange={(e) => handleFichaChange('dni', e.target.value)}
                    placeholder="12345678A"
                  />
                </div>
                <div>
                  <Label>Teléfono</Label>
                  <Input
                    value={formData.ficha.telefono}
                    onChange={(e) => handleFichaChange('telefono', e.target.value)}
                    placeholder="+34 600 000 000"
                  />
                </div>
                <div>
                  <Label>Fecha de Nacimiento</Label>
                  <Input
                    type="date"
                    value={formData.ficha.fecha_nacimiento}
                    onChange={(e) => handleFichaChange('fecha_nacimiento', e.target.value)}
                  />
                </div>
                <div>
                  <Label>Número Seguridad Social</Label>
                  <Input
                    value={formData.ficha.numero_ss}
                    onChange={(e) => handleFichaChange('numero_ss', e.target.value)}
                    placeholder="XX-XXXXXXXXXX-XX"
                  />
                </div>
                <div className="md:col-span-2">
                  <Label>Dirección</Label>
                  <Input
                    value={formData.ficha.direccion}
                    onChange={(e) => handleFichaChange('direccion', e.target.value)}
                    placeholder="Calle, número, piso..."
                  />
                </div>
                <div>
                  <Label>Ciudad</Label>
                  <Input
                    value={formData.ficha.ciudad}
                    onChange={(e) => handleFichaChange('ciudad', e.target.value)}
                    placeholder="Ciudad"
                  />
                </div>
                <div>
                  <Label>Código Postal</Label>
                  <Input
                    value={formData.ficha.codigo_postal}
                    onChange={(e) => handleFichaChange('codigo_postal', e.target.value)}
                    placeholder="00000"
                  />
                </div>
                <div>
                  <Label>Cuenta Bancaria (IBAN)</Label>
                  <Input
                    value={formData.ficha.cuenta_bancaria}
                    onChange={(e) => handleFichaChange('cuenta_bancaria', e.target.value)}
                    placeholder="ESXX XXXX XXXX XXXX XXXX XXXX"
                  />
                </div>
              </div>

              <Separator />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Contacto de Emergencia</Label>
                  <Input
                    value={formData.ficha.contacto_emergencia}
                    onChange={(e) => handleFichaChange('contacto_emergencia', e.target.value)}
                    placeholder="Nombre del contacto"
                  />
                </div>
                <div>
                  <Label>Teléfono de Emergencia</Label>
                  <Input
                    value={formData.ficha.telefono_emergencia}
                    onChange={(e) => handleFichaChange('telefono_emergencia', e.target.value)}
                    placeholder="+34 600 000 000"
                  />
                </div>
              </div>
            </TabsContent>

            {/* TAB: Laboral */}
            <TabsContent value="laboral" className="space-y-4 mt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Fecha de Alta</Label>
                  <Input
                    type="date"
                    value={formData.ficha.fecha_alta}
                    onChange={(e) => handleFichaChange('fecha_alta', e.target.value)}
                  />
                </div>
                <div>
                  <Label>Puesto</Label>
                  <Input
                    value={formData.info_laboral.puesto}
                    onChange={(e) => handleLaboralChange('puesto', e.target.value)}
                    placeholder="Ej: Técnico Senior"
                  />
                </div>
                <div>
                  <Label>Departamento</Label>
                  <Input
                    value={formData.info_laboral.departamento}
                    onChange={(e) => handleLaboralChange('departamento', e.target.value)}
                    placeholder="Ej: Reparaciones"
                  />
                </div>
                <div>
                  <Label>Tipo de Jornada</Label>
                  <Select 
                    value={formData.info_laboral.tipo_jornada} 
                    onValueChange={(v) => handleLaboralChange('tipo_jornada', v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {jornadaOptions.map(j => (
                        <SelectItem key={j.value} value={j.value}>{j.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Horas Semanales</Label>
                  <Input
                    type="number"
                    value={formData.info_laboral.horas_semanales}
                    onChange={(e) => handleLaboralChange('horas_semanales', parseInt(e.target.value) || 0)}
                    min={0}
                    max={60}
                  />
                </div>
              </div>

              <Separator />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Sueldo Bruto Anual (€)</Label>
                  <Input
                    type="number"
                    value={formData.info_laboral.sueldo_bruto}
                    onChange={(e) => handleLaboralChange('sueldo_bruto', e.target.value)}
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <Label>Sueldo Neto Mensual (€)</Label>
                  <Input
                    type="number"
                    value={formData.info_laboral.sueldo_neto}
                    onChange={(e) => handleLaboralChange('sueldo_neto', e.target.value)}
                    placeholder="0.00"
                  />
                </div>
              </div>

              <Separator />

              <div className="p-4 bg-blue-50 rounded-lg">
                <h4 className="font-medium flex items-center gap-2 mb-4">
                  <Calendar className="w-4 h-4" />
                  Vacaciones
                </h4>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-xs">Días Totales/Año</Label>
                    <Input
                      type="number"
                      value={formData.info_laboral.vacaciones.dias_totales}
                      onChange={(e) => handleVacacionesChange('dias_totales', e.target.value)}
                      min={0}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Días Usados</Label>
                    <Input
                      type="number"
                      value={formData.info_laboral.vacaciones.dias_usados}
                      onChange={(e) => handleVacacionesChange('dias_usados', e.target.value)}
                      min={0}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Días Pendientes</Label>
                    <Input
                      type="number"
                      value={formData.info_laboral.vacaciones.dias_pendientes}
                      onChange={(e) => handleVacacionesChange('dias_pendientes', e.target.value)}
                      min={0}
                      readOnly
                      className="bg-slate-100"
                    />
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* TAB: Horario */}
            <TabsContent value="horario" className="space-y-4 mt-4">
              <p className="text-sm text-muted-foreground mb-4">
                Define el horario de trabajo. Deja vacío los días no laborables.
                Formato: HH:MM-HH:MM (ej: 09:00-18:00)
              </p>
              <div className="space-y-3">
                {['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'].map(dia => (
                  <div key={dia} className="flex items-center gap-4">
                    <Label className="w-24 capitalize">{dia}</Label>
                    <Input
                      value={formData.info_laboral.horario[dia] || ''}
                      onChange={(e) => handleHorarioChange(dia, e.target.value)}
                      placeholder="09:00-18:00"
                      className="flex-1"
                    />
                  </div>
                ))}
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setShowModal(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={saving} data-testid="guardar-usuario-btn">
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              {selectedUser ? 'Guardar Cambios' : 'Crear Usuario'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Modal */}
      <Dialog open={showDeleteModal} onOpenChange={setShowDeleteModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-600">Eliminar Usuario</DialogTitle>
            <DialogDescription>
              ¿Estás seguro de que quieres eliminar al usuario <strong>{selectedUser?.nombre}</strong>?
              Esta acción no se puede deshacer.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteModal(false)}>
              Cancelar
            </Button>
            <Button variant="destructive" onClick={confirmDelete}>
              Eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Password Management Modal */}
      <Dialog open={showPasswordModal} onOpenChange={setShowPasswordModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <KeyRound className="w-5 h-5" />
              {passwordAction === 'cambiar' ? 'Cambiar contraseña' : 'Enviar restablecimiento'}
            </DialogTitle>
            <DialogDescription>
              Usuario: <strong>{selectedUser?.nombre} {selectedUser?.apellidos}</strong>
              <br />
              <span className="text-xs">{selectedUser?.email}</span>
            </DialogDescription>
          </DialogHeader>

          {passwordAction === 'cambiar' ? (
            <div className="space-y-4 py-2">
              <div>
                <Label>Nueva contraseña</Label>
                <div className="relative mt-1">
                  <Input
                    type={showNewPassword ? 'text' : 'password'}
                    value={nuevaPassword}
                    onChange={(e) => setNuevaPassword(e.target.value)}
                    placeholder="Mínimo 6 caracteres"
                    data-testid="nueva-password-input"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                  >
                    {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  La nueva contraseña será efectiva de inmediato.
                </p>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowPasswordModal(false)}>
                  Cancelar
                </Button>
                <Button onClick={handleCambiarPassword} disabled={passwordLoading} data-testid="confirmar-cambio-password-btn">
                  {passwordLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <KeyRound className="w-4 h-4 mr-2" />}
                  Cambiar contraseña
                </Button>
              </DialogFooter>
            </div>
          ) : (
            <div className="space-y-4 py-2">
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                <div className="flex items-start gap-3">
                  <Mail className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-blue-900">Se enviará un email a:</p>
                    <p className="text-sm text-blue-700 mt-0.5">{selectedUser?.email}</p>
                    <p className="text-xs text-blue-600 mt-2">
                      El email incluirá una contraseña temporal generada automáticamente. El trabajador podrá acceder con ella y cambiarla desde su perfil.
                    </p>
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowPasswordModal(false)}>
                  Cancelar
                </Button>
                <Button onClick={handleEnviarReset} disabled={passwordLoading} data-testid="confirmar-envio-reset-btn">
                  {passwordLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
                  Enviar restablecimiento
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { User, UserPlus, Check, X } from 'lucide-react';
import { toast } from 'sonner';
import API, { ordenesAPI, usuariosAPI } from '@/lib/api';

export function OrdenAsignarTecnico({ ordenId, tecnicoAsignado, onAsignar }) {
  const [tecnicos, setTecnicos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editando, setEditando] = useState(false);
  const [tecnicoSeleccionado, setTecnicoSeleccionado] = useState(tecnicoAsignado || '');

  useEffect(() => {
    fetchTecnicos();
  }, []);

  useEffect(() => {
    setTecnicoSeleccionado(tecnicoAsignado || '');
  }, [tecnicoAsignado]);

  const fetchTecnicos = async () => {
    try {
      const res = await usuariosAPI.listar();
      // Filtrar solo técnicos y admins activos
      const tecnicosActivos = res.data.filter(u => 
        (u.role === 'tecnico' || u.role === 'admin') && u.activo
      );
      setTecnicos(tecnicosActivos);
    } catch (err) {
      console.error('Error cargando técnicos:', err);
    }
  };

  const handleAsignar = async () => {
    if (!tecnicoSeleccionado) {
      toast.error('Selecciona un técnico');
      return;
    }
    
    const tecObj = tecnicos.find(t => t.email === tecnicoSeleccionado);
    const nombreCompleto = tecObj 
      ? `${tecObj.nombre || ''}${tecObj.apellidos ? ' ' + tecObj.apellidos : ''}`.trim() || tecObj.email
      : tecnicoSeleccionado;

    setLoading(true);
    try {
      await ordenesAPI.actualizar(ordenId, { 
        tecnico_asignado: tecnicoSeleccionado,
        tecnico_nombre: nombreCompleto,
      });
      toast.success(`Orden asignada a ${nombreCompleto}`);
      setEditando(false);
      if (onAsignar) onAsignar(tecnicoSeleccionado, nombreCompleto);
    } catch (err) {
      console.error('Error asignando técnico:', err);
      toast.error('Error al asignar técnico');
    } finally {
      setLoading(false);
    }
  };

  const handleDesasignar = async () => {
    setLoading(true);
    try {
      await ordenesAPI.actualizar(ordenId, { 
        tecnico_asignado: null,
        tecnico_nombre: null,
      });
      toast.success('Técnico desasignado');
      setEditando(false);
      setTecnicoSeleccionado('');
      if (onAsignar) onAsignar(null);
    } catch (err) {
      console.error('Error desasignando:', err);
      toast.error('Error al desasignar');
    } finally {
      setLoading(false);
    }
  };

  const tecnicoActual = tecnicos.find(t => t.email === tecnicoAsignado);

  return (
    <Card data-testid="asignar-tecnico-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <User className="w-4 h-4" />
          Técnico Asignado
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!editando ? (
          <div className="flex items-center justify-between">
            {tecnicoAsignado ? (
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="gap-1">
                  <User className="w-3 h-3" />
                  {tecnicoActual?.nombre || tecnicoAsignado}
                </Badge>
                {tecnicoActual?.role && (
                  <span className="text-xs text-muted-foreground">
                    ({tecnicoActual.role})
                  </span>
                )}
              </div>
            ) : (
              <span className="text-sm text-muted-foreground">Sin asignar</span>
            )}
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => setEditando(true)}
              data-testid="btn-editar-tecnico"
            >
              <UserPlus className="w-4 h-4 mr-1" />
              {tecnicoAsignado ? 'Cambiar' : 'Asignar'}
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <Select 
              value={tecnicoSeleccionado} 
              onValueChange={setTecnicoSeleccionado}
            >
              <SelectTrigger data-testid="select-tecnico">
                <SelectValue placeholder="Seleccionar técnico..." />
              </SelectTrigger>
              <SelectContent>
                {tecnicos.map(t => (
                  <SelectItem key={t.id} value={t.email}>
                    <div className="flex items-center gap-2">
                      <span>{t.nombre || t.email}</span>
                      <Badge variant="outline" className="text-[10px]">
                        {t.role}
                      </Badge>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            <div className="flex items-center gap-2">
              <Button 
                size="sm" 
                onClick={handleAsignar} 
                disabled={loading}
                data-testid="btn-confirmar-asignar"
              >
                <Check className="w-4 h-4 mr-1" />
                Confirmar
              </Button>
              {tecnicoAsignado && (
                <Button 
                  variant="destructive" 
                  size="sm" 
                  onClick={handleDesasignar}
                  disabled={loading}
                >
                  <X className="w-4 h-4 mr-1" />
                  Desasignar
                </Button>
              )}
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => {
                  setEditando(false);
                  setTecnicoSeleccionado(tecnicoAsignado || '');
                }}
              >
                Cancelar
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

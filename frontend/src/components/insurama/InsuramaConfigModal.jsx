import { useState } from 'react';
import { Settings, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { insuramaAPI } from '@/lib/api';
import { toast } from 'sonner';

export function InsuramaConfigModal({ open, onOpenChange, onConfigSaved }) {
  const [configForm, setConfigForm] = useState({ login: '', password: '' });
  const [savingConfig, setSavingConfig] = useState(false);

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    if (!configForm.login || !configForm.password) {
      toast.error('Completa todos los campos');
      return;
    }
    
    setSavingConfig(true);
    try {
      const res = await insuramaAPI.guardarConfig(configForm);
      toast.success('Credenciales guardadas y verificadas');
      onConfigSaved({
        configurado: true,
        login: configForm.login,
        conexion_ok: true,
        ...res.data.conexion
      });
      onOpenChange(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar credenciales');
    } finally {
      setSavingConfig(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Configuración de Sumbroker
          </DialogTitle>
          <DialogDescription>
            Introduce las credenciales del portal distribuidor.sumbroker.es
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSaveConfig} className="space-y-4 pt-4">
          <div>
            <Label>Usuario / Login</Label>
            <Input
              value={configForm.login}
              onChange={(e) => setConfigForm(prev => ({ ...prev, login: e.target.value }))}
              placeholder="tu_usuario"
            />
          </div>
          <div>
            <Label>Contraseña</Label>
            <Input
              type="password"
              value={configForm.password}
              onChange={(e) => setConfigForm(prev => ({ ...prev, password: e.target.value }))}
              placeholder="••••••••"
            />
          </div>
          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={savingConfig}>
              {savingConfig ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Guardar y Verificar
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

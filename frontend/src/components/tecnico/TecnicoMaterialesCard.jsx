import { useState } from 'react';
import { Package, Plus, AlertTriangle, CheckCircle2, QrCode, Scan, Check } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { ordenesAPI } from '@/lib/api';
import { toast } from 'sonner';

export function TecnicoMaterialesCard({ orden, repuestos, onRefresh }) {
  const [openMaterialSearch, setOpenMaterialSearch] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [selectedRepuesto, setSelectedRepuesto] = useState(null);
  const [showMaterialPersonalizado, setShowMaterialPersonalizado] = useState(false);
  const [materialPersonalizado, setMaterialPersonalizado] = useState({ nombre: '', cantidad: 1 });
  const [guardandoMaterial, setGuardandoMaterial] = useState(false);
  
  // Estados para validación
  const [showValidacionModal, setShowValidacionModal] = useState(false);
  const [codigoValidacion, setCodigoValidacion] = useState('');
  const [validando, setValidando] = useState(false);

  const handleSelectMaterial = (repuesto) => {
    setSelectedRepuesto(repuesto);
    setOpenMaterialSearch(false);
    setShowConfirmDialog(true);
  };

  const handleConfirmAddMaterial = async () => {
    if (!selectedRepuesto) return;
    
    try {
      await ordenesAPI.añadirMaterial(orden.id, {
        repuesto_id: selectedRepuesto.id,
        cantidad: 1,
        añadido_por_tecnico: true
      });
      
      toast.warning('Material añadido. La orden ha sido BLOQUEADA hasta que el administrador apruebe el material.');
      setShowConfirmDialog(false);
      setSelectedRepuesto(null);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al añadir material');
    }
  };
  
  const handleAddMaterialPersonalizado = async () => {
    if (!materialPersonalizado.nombre.trim()) {
      toast.error('El nombre del material es obligatorio');
      return;
    }
    
    setGuardandoMaterial(true);
    try {
      await ordenesAPI.añadirMaterial(orden.id, {
        nombre: materialPersonalizado.nombre.trim(),
        cantidad: parseInt(materialPersonalizado.cantidad) || 1,
        añadido_por_tecnico: true
      });
      
      toast.warning('Material añadido sin precios. La orden ha sido BLOQUEADA hasta que el administrador apruebe y asigne precios.');
      setShowMaterialPersonalizado(false);
      setMaterialPersonalizado({ nombre: '', cantidad: 1 });
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al añadir material');
    } finally {
      setGuardandoMaterial(false);
    }
  };

  // Validar material por código (SKU o código de barras)
  const handleValidarPorCodigo = async () => {
    if (!codigoValidacion.trim()) {
      toast.error('Introduce o escanea el código del material');
      return;
    }
    
    setValidando(true);
    try {
      const res = await ordenesAPI.validarMaterialPorCodigo(orden.id, codigoValidacion.trim());
      
      if (res.data.ya_validado) {
        toast.info(`"${res.data.material.nombre}" ya estaba validado`);
      } else {
        toast.success(`✓ ${res.data.material.nombre} validado (${res.data.total - res.data.pendientes}/${res.data.total})`);
      }
      
      setCodigoValidacion('');
      onRefresh();
      
      // Si ya no quedan materiales pendientes, cerrar modal
      if (res.data.pendientes === 0) {
        toast.success('🎉 ¡Todos los materiales han sido validados!');
        setShowValidacionModal(false);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Material no encontrado en esta orden');
    } finally {
      setValidando(false);
    }
  };

  // Validar material individual (click en botón)
  const handleValidarMaterial = async (index) => {
    try {
      await ordenesAPI.validarMaterial(orden.id, index);
      toast.success('Material validado');
      onRefresh();
    } catch (error) {
      toast.error('Error al validar material');
    }
  };

  // Calcular estadísticas de validación
  const materiales = orden.materiales || [];
  const materialesValidados = materiales.filter(m => m.validado_tecnico).length;
  const materialesPendientes = materiales.length - materialesValidados;
  const porcentajeValidado = materiales.length > 0 ? (materialesValidados / materiales.length) * 100 : 0;
  const todosValidados = materiales.length > 0 && materialesPendientes === 0;

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Package className="w-5 h-5" />
            Materiales
            {materiales.length > 0 && (
              <Badge variant={todosValidados ? "default" : "secondary"} className="ml-2">
                {materialesValidados}/{materiales.length} validados
              </Badge>
            )}
          </CardTitle>
          <div className="flex gap-2">
            {materiales.length > 0 && (
              <Button 
                variant={materialesPendientes > 0 ? "default" : "outline"}
                size="sm"
                onClick={() => setShowValidacionModal(true)}
                data-testid="validar-materiales-btn"
              >
                <Scan className="w-4 h-4 mr-1" />
                {materialesPendientes > 0 ? `Validar (${materialesPendientes})` : 'Revisar'}
              </Button>
            )}
            {!orden.bloqueada && (
              <>
                <Popover open={openMaterialSearch} onOpenChange={setOpenMaterialSearch}>
                  <PopoverTrigger asChild>
                    <Button variant="outline" size="sm" data-testid="add-material-btn">
                      <Plus className="w-4 h-4 mr-1" />
                      Existente
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80 p-0" align="end">
                    <Command>
                      <CommandInput placeholder="Buscar repuesto..." />
                      <CommandList>
                        <CommandEmpty>No se encontraron repuestos</CommandEmpty>
                        <CommandGroup>
                          {repuestos.filter(r => r.stock > 0).map((repuesto) => (
                            <CommandItem
                              key={repuesto.id}
                              onSelect={() => handleSelectMaterial(repuesto)}
                            >
                              <div className="flex-1">
                                <p className="font-medium">{repuesto.nombre}</p>
                                <p className="text-sm text-muted-foreground">
                                  Stock: {repuesto.stock}
                                </p>
                              </div>
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
                <Button 
                  variant="secondary" 
                  size="sm"
                  onClick={() => setShowMaterialPersonalizado(true)}
                  data-testid="add-material-nuevo-btn"
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Nuevo
                </Button>
              </>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {/* Barra de progreso de validación */}
          {materiales.length > 0 && (
            <div className="mb-4">
              <div className="flex justify-between text-sm text-muted-foreground mb-1">
                <span>Progreso de validación</span>
                <span>{Math.round(porcentajeValidado)}%</span>
              </div>
              <Progress value={porcentajeValidado} className="h-2" />
            </div>
          )}
          
          {materiales.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No hay materiales asignados</p>
              <p className="text-sm">Añade los materiales necesarios para la reparación</p>
            </div>
          ) : (
            <div className="space-y-2">
              {materiales.map((material, index) => (
                <div 
                  key={index}
                  className={`flex items-center justify-between p-3 rounded-lg border transition-colors ${
                    material.validado_tecnico 
                      ? 'border-green-200 bg-green-50' 
                      : !material.aprobado 
                        ? 'border-orange-300 bg-orange-50' 
                        : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {material.validado_tecnico ? (
                      <CheckCircle2 className="w-5 h-5 text-green-600" />
                    ) : !material.aprobado ? (
                      <AlertTriangle className="w-5 h-5 text-orange-500" />
                    ) : (
                      <Package className="w-5 h-5 text-slate-400" />
                    )}
                    <div>
                      <p className="font-medium">{material.nombre}</p>
                      <p className="text-xs text-muted-foreground">
                        Cantidad: {material.cantidad}
                        {material.sku && <span className="ml-2">SKU: {material.sku}</span>}
                        {material.validado_tecnico && (
                          <span className="text-green-600 ml-2">
                            ✓ Validado {material.validado_at?.slice(0, 10)}
                          </span>
                        )}
                        {material.añadido_por_tecnico && !material.aprobado && (
                          <span className="text-orange-600 ml-2">(Pendiente aprobación)</span>
                        )}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {!material.validado_tecnico && material.aprobado && (
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => handleValidarMaterial(index)}
                        className="text-green-600 hover:text-green-700"
                      >
                        <Check className="w-3 h-3 mr-1" />
                        Validar
                      </Button>
                    )}
                    <Badge variant={
                      material.validado_tecnico ? "default" : 
                      material.aprobado ? "secondary" : "outline"
                    }>
                      {material.validado_tecnico ? 'Validado' : 
                       material.aprobado ? 'Pendiente' : 'No aprobado'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal de Validación con Escáner */}
      <Dialog open={showValidacionModal} onOpenChange={setShowValidacionModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Scan className="w-5 h-5" />
              Validar Materiales
            </DialogTitle>
            <DialogDescription>
              Escanea o introduce el SKU/código de barras de cada material para confirmar que ha sido utilizado.
            </DialogDescription>
          </DialogHeader>
          
          {/* Progreso */}
          <div className="mb-4">
            <div className="flex justify-between text-sm mb-1">
              <span className="font-medium">
                {todosValidados ? '¡Todos validados!' : `${materialesPendientes} pendientes`}
              </span>
              <span>{materialesValidados}/{materiales.length}</span>
            </div>
            <Progress value={porcentajeValidado} className="h-3" />
          </div>
          
          {/* Input de escaneo */}
          {!todosValidados && (
            <div className="space-y-3">
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <QrCode className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    placeholder="Escanea o escribe el código..."
                    className="pl-10 font-mono"
                    value={codigoValidacion}
                    onChange={(e) => setCodigoValidacion(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleValidarPorCodigo()}
                    autoFocus
                    data-testid="codigo-validacion-input"
                  />
                </div>
                <Button onClick={handleValidarPorCodigo} disabled={validando}>
                  {validando ? 'Validando...' : 'Validar'}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground text-center">
                Presiona Enter después de escanear para validar automáticamente
              </p>
            </div>
          )}
          
          {/* Lista de materiales */}
          <div className="space-y-2 max-h-64 overflow-y-auto mt-4">
            <p className="text-sm font-medium text-muted-foreground">Materiales asignados:</p>
            {materiales.map((material, index) => (
              <div 
                key={index}
                className={`flex items-center justify-between p-2 rounded border text-sm ${
                  material.validado_tecnico ? 'bg-green-50 border-green-200' : 'bg-slate-50'
                }`}
              >
                <div className="flex items-center gap-2">
                  {material.validado_tecnico ? (
                    <CheckCircle2 className="w-4 h-4 text-green-600" />
                  ) : (
                    <Package className="w-4 h-4 text-slate-400" />
                  )}
                  <span>{material.nombre}</span>
                </div>
                {material.validado_tecnico ? (
                  <Badge variant="default" className="text-xs">✓</Badge>
                ) : (
                  <Badge variant="outline" className="text-xs">Pendiente</Badge>
                )}
              </div>
            ))}
          </div>
          
          {todosValidados && (
            <div className="text-center py-4">
              <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-2" />
              <p className="font-medium text-green-700">¡Todos los materiales validados!</p>
              <Button className="mt-3" onClick={() => setShowValidacionModal(false)}>
                Cerrar
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Confirm Add Material Dialog */}
      <Dialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-500" />
              Confirmar Añadir Material
            </DialogTitle>
            <DialogDescription>
              Al añadir este material, la orden será <strong>BLOQUEADA</strong> hasta que el administrador lo apruebe.
            </DialogDescription>
          </DialogHeader>
          
          {selectedRepuesto && (
            <div className="p-4 bg-slate-50 rounded-lg">
              <p className="font-medium">{selectedRepuesto.nombre}</p>
              <p className="text-sm text-muted-foreground">
                Stock disponible: {selectedRepuesto.stock}
              </p>
            </div>
          )}
          
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setShowConfirmDialog(false)}>
              Cancelar
            </Button>
            <Button onClick={handleConfirmAddMaterial} className="bg-orange-500 hover:bg-orange-600">
              Confirmar y Bloquear
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Dialog para añadir material personalizado */}
      <Dialog open={showMaterialPersonalizado} onOpenChange={setShowMaterialPersonalizado}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Añadir Material No Registrado</DialogTitle>
            <DialogDescription>
              Añade un material que no está en el inventario. El administrador asignará los precios posteriormente.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Nombre del Material *</Label>
              <Input
                value={materialPersonalizado.nombre}
                onChange={(e) => setMaterialPersonalizado(prev => ({ ...prev, nombre: e.target.value }))}
                placeholder="Ej: Pantalla LCD Samsung S21"
              />
            </div>
            <div>
              <Label>Cantidad</Label>
              <Input
                type="number"
                min="1"
                value={materialPersonalizado.cantidad}
                onChange={(e) => setMaterialPersonalizado(prev => ({ ...prev, cantidad: e.target.value }))}
              />
            </div>
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
              <AlertTriangle className="w-4 h-4 inline mr-2" />
              Este material será añadido <strong>sin precios</strong>. El administrador deberá asignar el coste y precio de venta antes de aprobar la orden.
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setShowMaterialPersonalizado(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleAddMaterialPersonalizado} 
              disabled={guardandoMaterial || !materialPersonalizado.nombre.trim()}
            >
              {guardandoMaterial ? 'Añadiendo...' : 'Añadir Material'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

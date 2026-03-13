import { useState, useEffect } from 'react';
import { 
  Plus, 
  Trash2, 
  Save, 
  X, 
  AlertTriangle,
  Check,
  Loader2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ordenesAPI } from '@/lib/api';
import { toast } from 'sonner';

const TIPOS_IVA = [
  { value: 0, label: '0%' },
  { value: 4, label: '4%' },
  { value: 10, label: '10%' },
  { value: 21, label: '21%' },
];

export default function TablaMaterialesEditable({ 
  ordenId, 
  materiales: materialesIniciales = [], 
  onUpdate, 
  readOnly = false,
  mostrarCoste = true 
}) {
  const [editingIndex, setEditingIndex] = useState(null);
  const [editData, setEditData] = useState({});
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(null);
  // Estado local de materiales para evitar recargar toda la página
  const [localMateriales, setLocalMateriales] = useState(materialesIniciales);
  
  // Sincronizar cuando cambian los materiales desde el padre
  useEffect(() => {
    setLocalMateriales(materialesIniciales);
  }, [materialesIniciales]);
  
  // Nueva fila para añadir
  const [showNewRow, setShowNewRow] = useState(false);
  const [newMaterial, setNewMaterial] = useState({
    nombre: '',
    cantidad: 1,
    precio_unitario: '',
    coste: '',
    iva: 21,
    descuento: 0
  });
  const [addingSaving, setAddingSaving] = useState(false);

  // Calcular totales
  const calcularTotales = () => {
    let base = 0;
    let totalIva = 0;
    
    materiales.forEach(m => {
      const subtotal = m.cantidad * (m.precio_unitario || 0);
      const descuento = m.descuento ? subtotal * (m.descuento / 100) : 0;
      const baseItem = subtotal - descuento;
      const ivaItem = baseItem * ((m.iva || 21) / 100);
      
      base += baseItem;
      totalIva += ivaItem;
    });
    
    return { base, totalIva, total: base + totalIva };
  };

  const { base, totalIva, total } = calcularTotales();

  // Iniciar edición
  const handleStartEdit = (index) => {
    const material = materiales[index];
    setEditData({
      nombre: material.nombre || '',
      cantidad: material.cantidad || 1,
      precio_unitario: material.precio_unitario || 0,
      coste: material.coste || 0,
      iva: material.iva || 21,
      descuento: material.descuento || 0
    });
    setEditingIndex(index);
  };

  // Cancelar edición
  const handleCancelEdit = () => {
    setEditingIndex(null);
    setEditData({});
  };

  // Guardar edición
  const handleSaveEdit = async (index) => {
    setSaving(true);
    try {
      await ordenesAPI.editarMaterialCompleto(ordenId, index, {
        nombre: editData.nombre,
        cantidad: parseInt(editData.cantidad) || 1,
        precio_unitario: parseFloat(editData.precio_unitario) || 0,
        coste: parseFloat(editData.coste) || 0,
        iva: parseFloat(editData.iva) || 21,
        descuento: parseFloat(editData.descuento) || 0
      });
      toast.success('Material actualizado');
      setEditingIndex(null);
      setEditData({});
      onUpdate?.();
    } catch (error) {
      toast.error('Error al actualizar material');
    } finally {
      setSaving(false);
    }
  };

  // Eliminar material
  const handleDelete = async (index) => {
    if (!confirm('¿Eliminar este material de la orden?')) return;
    
    setDeleting(index);
    try {
      await ordenesAPI.eliminarMaterial(ordenId, index);
      toast.success('Material eliminado');
      onUpdate?.();
    } catch (error) {
      toast.error('Error al eliminar material');
    } finally {
      setDeleting(null);
    }
  };

  // Añadir nuevo material
  const handleAddNew = async () => {
    if (!newMaterial.nombre.trim()) {
      toast.error('Escribe una descripción');
      return;
    }
    
    setAddingSaving(true);
    try {
      await ordenesAPI.añadirMaterial(ordenId, {
        nombre: newMaterial.nombre,
        cantidad: parseInt(newMaterial.cantidad) || 1,
        precio_unitario: parseFloat(newMaterial.precio_unitario) || 0,
        coste: parseFloat(newMaterial.coste) || 0,
        iva: parseFloat(newMaterial.iva) || 21,
        descuento: parseFloat(newMaterial.descuento) || 0,
        es_personalizado: true
      });
      toast.success('Material añadido');
      setShowNewRow(false);
      setNewMaterial({
        nombre: '',
        cantidad: 1,
        precio_unitario: '',
        coste: '',
        iva: 21,
        descuento: 0
      });
      onUpdate?.();
    } catch (error) {
      toast.error('Error al añadir material');
    } finally {
      setAddingSaving(false);
    }
  };

  // Calcular total de una fila
  const calcularTotalFila = (cantidad, precio, descuento, iva) => {
    const subtotal = (cantidad || 0) * (precio || 0);
    const desc = descuento ? subtotal * (descuento / 100) : 0;
    const baseItem = subtotal - desc;
    const ivaItem = baseItem * ((iva || 21) / 100);
    return { base: baseItem, conIva: baseItem + ivaItem };
  };

  return (
    <div className="space-y-4">
      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-100">
              <TableHead className="w-[35%]">Descripción</TableHead>
              <TableHead className="text-center w-[8%]">Cant.</TableHead>
              <TableHead className="text-right w-[12%]">Precio</TableHead>
              {mostrarCoste && (
                <TableHead className="text-right w-[10%]">Coste</TableHead>
              )}
              <TableHead className="text-center w-[8%]">IVA</TableHead>
              <TableHead className="text-center w-[8%]">Dto.</TableHead>
              <TableHead className="text-right w-[12%]">Total Base</TableHead>
              <TableHead className="text-right w-[12%]">Total c/IVA</TableHead>
              {!readOnly && <TableHead className="w-[60px]"></TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {materiales.map((material, index) => {
              const isEditing = editingIndex === index;
              const totals = calcularTotalFila(
                isEditing ? editData.cantidad : material.cantidad,
                isEditing ? editData.precio_unitario : material.precio_unitario,
                isEditing ? editData.descuento : material.descuento,
                isEditing ? editData.iva : material.iva
              );
              
              return (
                <TableRow 
                  key={index}
                  className={`
                    ${material.pendiente_precios ? 'bg-red-50' : ''}
                    ${!material.aprobado && !material.pendiente_precios ? 'bg-orange-50' : ''}
                    ${isEditing ? 'bg-blue-50' : ''}
                  `}
                >
                  {/* Descripción */}
                  <TableCell>
                    {isEditing ? (
                      <Input
                        value={editData.nombre}
                        onChange={(e) => setEditData({...editData, nombre: e.target.value})}
                        className="h-8"
                        autoFocus
                      />
                    ) : (
                      <div className="flex items-center gap-2">
                        {material.pendiente_precios && (
                          <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />
                        )}
                        <span 
                          className={`${!readOnly ? 'cursor-pointer hover:text-blue-600' : ''}`}
                          onClick={() => !readOnly && handleStartEdit(index)}
                        >
                          {material.nombre}
                        </span>
                        {material.añadido_por_tecnico && (
                          <Badge variant="outline" className="text-[10px]">Téc</Badge>
                        )}
                      </div>
                    )}
                  </TableCell>
                  
                  {/* Cantidad */}
                  <TableCell className="text-center">
                    {isEditing ? (
                      <Input
                        type="number"
                        min="1"
                        value={editData.cantidad}
                        onChange={(e) => setEditData({...editData, cantidad: e.target.value})}
                        className="h-8 w-16 text-center"
                      />
                    ) : (
                      <span 
                        className={`${!readOnly ? 'cursor-pointer hover:text-blue-600' : ''}`}
                        onClick={() => !readOnly && handleStartEdit(index)}
                      >
                        {material.cantidad}
                      </span>
                    )}
                  </TableCell>
                  
                  {/* Precio */}
                  <TableCell className="text-right">
                    {isEditing ? (
                      <Input
                        type="number"
                        step="0.01"
                        value={editData.precio_unitario}
                        onChange={(e) => setEditData({...editData, precio_unitario: e.target.value})}
                        className="h-8 w-20 text-right"
                      />
                    ) : (
                      <span 
                        className={`${!readOnly ? 'cursor-pointer hover:text-blue-600' : ''}`}
                        onClick={() => !readOnly && handleStartEdit(index)}
                      >
                        {(material.precio_unitario || 0).toFixed(2)} €
                      </span>
                    )}
                  </TableCell>
                  
                  {/* Coste */}
                  {mostrarCoste && (
                    <TableCell className="text-right">
                      {isEditing ? (
                        <Input
                          type="number"
                          step="0.01"
                          value={editData.coste}
                          onChange={(e) => setEditData({...editData, coste: e.target.value})}
                          className="h-8 w-20 text-right"
                        />
                      ) : (
                        <span 
                          className={`text-muted-foreground ${!readOnly ? 'cursor-pointer hover:text-blue-600' : ''}`}
                          onClick={() => !readOnly && handleStartEdit(index)}
                        >
                          {(material.coste || 0).toFixed(2)} €
                        </span>
                      )}
                    </TableCell>
                  )}
                  
                  {/* IVA */}
                  <TableCell className="text-center">
                    {isEditing ? (
                      <Select
                        value={String(editData.iva)}
                        onValueChange={(v) => setEditData({...editData, iva: parseInt(v)})}
                      >
                        <SelectTrigger className="h-8 w-16">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {TIPOS_IVA.map(t => (
                            <SelectItem key={t.value} value={String(t.value)}>{t.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <span 
                        className={`${!readOnly ? 'cursor-pointer hover:text-blue-600' : ''}`}
                        onClick={() => !readOnly && handleStartEdit(index)}
                      >
                        {material.iva || 21}%
                      </span>
                    )}
                  </TableCell>
                  
                  {/* Descuento */}
                  <TableCell className="text-center">
                    {isEditing ? (
                      <Input
                        type="number"
                        min="0"
                        max="100"
                        value={editData.descuento}
                        onChange={(e) => setEditData({...editData, descuento: e.target.value})}
                        className="h-8 w-14 text-center"
                      />
                    ) : (
                      <span 
                        className={`${!readOnly ? 'cursor-pointer hover:text-blue-600' : ''}`}
                        onClick={() => !readOnly && handleStartEdit(index)}
                      >
                        {material.descuento || 0}%
                      </span>
                    )}
                  </TableCell>
                  
                  {/* Total Base */}
                  <TableCell className="text-right font-medium">
                    {totals.base.toFixed(2)} €
                  </TableCell>
                  
                  {/* Total con IVA */}
                  <TableCell className="text-right font-semibold">
                    {totals.conIva.toFixed(2)} €
                  </TableCell>
                  
                  {/* Acciones */}
                  {!readOnly && (
                    <TableCell>
                      <div className="flex items-center gap-1">
                        {isEditing ? (
                          <>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => handleSaveEdit(index)}
                              disabled={saving}
                            >
                              {saving ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <Check className="w-4 h-4 text-green-600" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={handleCancelEdit}
                            >
                              <X className="w-4 h-4 text-gray-500" />
                            </Button>
                          </>
                        ) : (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => handleDelete(index)}
                            disabled={deleting === index}
                          >
                            {deleting === index ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Trash2 className="w-4 h-4 text-red-500" />
                            )}
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              );
            })}
            
            {/* Nueva fila para añadir */}
            {!readOnly && showNewRow && (
              <TableRow className="bg-green-50">
                <TableCell>
                  <Input
                    placeholder="Descripción del artículo..."
                    value={newMaterial.nombre}
                    onChange={(e) => setNewMaterial({...newMaterial, nombre: e.target.value})}
                    className="h-8"
                    autoFocus
                  />
                </TableCell>
                <TableCell className="text-center">
                  <Input
                    type="number"
                    min="1"
                    value={newMaterial.cantidad}
                    onChange={(e) => setNewMaterial({...newMaterial, cantidad: e.target.value})}
                    className="h-8 w-16 text-center"
                  />
                </TableCell>
                <TableCell className="text-right">
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={newMaterial.precio_unitario}
                    onChange={(e) => setNewMaterial({...newMaterial, precio_unitario: e.target.value})}
                    className="h-8 w-20 text-right"
                  />
                </TableCell>
                {mostrarCoste && (
                  <TableCell className="text-right">
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      value={newMaterial.coste}
                      onChange={(e) => setNewMaterial({...newMaterial, coste: e.target.value})}
                      className="h-8 w-20 text-right"
                    />
                  </TableCell>
                )}
                <TableCell className="text-center">
                  <Select
                    value={String(newMaterial.iva)}
                    onValueChange={(v) => setNewMaterial({...newMaterial, iva: parseInt(v)})}
                  >
                    <SelectTrigger className="h-8 w-16">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TIPOS_IVA.map(t => (
                        <SelectItem key={t.value} value={String(t.value)}>{t.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </TableCell>
                <TableCell className="text-center">
                  <Input
                    type="number"
                    min="0"
                    max="100"
                    value={newMaterial.descuento}
                    onChange={(e) => setNewMaterial({...newMaterial, descuento: e.target.value})}
                    className="h-8 w-14 text-center"
                  />
                </TableCell>
                <TableCell className="text-right">-</TableCell>
                <TableCell className="text-right">-</TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={handleAddNew}
                      disabled={addingSaving}
                    >
                      {addingSaving ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Check className="w-4 h-4 text-green-600" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => setShowNewRow(false)}
                    >
                      <X className="w-4 h-4 text-gray-500" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            )}
            
            {/* Fila vacía para añadir nuevo (click para activar) */}
            {!readOnly && !showNewRow && (
              <TableRow 
                className="cursor-pointer hover:bg-slate-50"
                onClick={() => setShowNewRow(true)}
              >
                <TableCell colSpan={mostrarCoste ? 9 : 8} className="text-center text-muted-foreground py-3">
                  <Plus className="w-4 h-4 inline mr-2" />
                  Click para añadir nuevo artículo
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      
      {/* Totales */}
      <div className="flex justify-end">
        <div className="w-64 space-y-1 text-sm">
          <div className="flex justify-between py-1">
            <span className="text-muted-foreground">Base Imponible:</span>
            <span className="font-medium">{base.toFixed(2)} €</span>
          </div>
          <div className="flex justify-between py-1">
            <span className="text-muted-foreground">IVA:</span>
            <span className="font-medium">{totalIva.toFixed(2)} €</span>
          </div>
          <div className="flex justify-between py-2 border-t text-lg font-bold">
            <span>TOTAL:</span>
            <span>{total.toFixed(2)} €</span>
          </div>
        </div>
      </div>
    </div>
  );
}

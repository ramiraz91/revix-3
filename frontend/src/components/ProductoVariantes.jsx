import { useState, useEffect } from 'react';
import { 
  Package, Loader2, ArrowLeftRight, Palette, Tag, 
  TrendingUp, TrendingDown, Equal, ChevronRight,
  Check, X
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import api from '@/lib/api';
import { toast } from 'sonner';

const COLORES_PREDEFINIDOS = [
  { value: 'Negro', hex: '#1a1a1a', textColor: 'white' },
  { value: 'Blanco', hex: '#ffffff', textColor: 'black' },
  { value: 'Azul', hex: '#3b82f6', textColor: 'white' },
  { value: 'Rojo', hex: '#ef4444', textColor: 'white' },
  { value: 'Verde', hex: '#22c55e', textColor: 'white' },
  { value: 'Dorado', hex: '#eab308', textColor: 'black' },
  { value: 'Plateado', hex: '#94a3b8', textColor: 'black' },
  { value: 'Morado', hex: '#a855f7', textColor: 'white' },
  { value: 'Rosa', hex: '#ec4899', textColor: 'white' },
  { value: 'Gris', hex: '#6b7280', textColor: 'white' },
  { value: 'Naranja', hex: '#f97316', textColor: 'white' },
  { value: 'Amarillo', hex: '#fbbf24', textColor: 'black' },
];

export default function ProductoVariantes({ productoId, productoNombre, onClose }) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const [editingColor, setEditingColor] = useState(null);

  useEffect(() => {
    if (productoId) {
      cargarVariantes();
    }
  }, [productoId]);

  const cargarVariantes = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/repuestos/${productoId}/variantes`);
      setData(res.data);
    } catch (error) {
      toast.error('Error cargando variantes');
    } finally {
      setLoading(false);
    }
  };

  const handleSetColor = async (repuestoId, color) => {
    try {
      await api.patch(`/repuestos/${repuestoId}/color`, null, { params: { color } });
      toast.success('Color actualizado');
      cargarVariantes();
      setEditingColor(null);
    } catch (error) {
      toast.error('Error actualizando color');
    }
  };

  const toggleSelect = (id) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(i => i !== id));
    } else if (selectedIds.length < 4) {
      setSelectedIds([...selectedIds, id]);
    } else {
      toast.info('Máximo 4 productos para comparar');
    }
  };

  const getColorInfo = (colorName) => {
    if (!colorName) return null;
    const found = COLORES_PREDEFINIDOS.find(c => 
      c.value.toLowerCase() === colorName.toLowerCase()
    );
    return found || { value: colorName, hex: '#9ca3af', textColor: 'white' };
  };

  const getPriceComparison = (precio, precioBase) => {
    if (!precio || !precioBase) return null;
    const diff = ((precio - precioBase) / precioBase) * 100;
    if (Math.abs(diff) < 1) return { icon: Equal, color: 'text-gray-500', text: 'Igual' };
    if (diff > 0) return { icon: TrendingUp, color: 'text-red-500', text: `+${diff.toFixed(0)}%` };
    return { icon: TrendingDown, color: 'text-green-500', text: `${diff.toFixed(0)}%` };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No se pudieron cargar las variantes
      </div>
    );
  }

  const { producto_base, variantes, modelo_detectado, tipo_detectado, total_variantes } = data;
  const todosProductos = [producto_base, ...variantes];
  const productosComparar = todosProductos.filter(p => selectedIds.includes(p.id));

  return (
    <div className="space-y-6">
      {/* Header con info del producto base */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold">{producto_base.nombre}</h3>
          <div className="flex gap-2 mt-1">
            {modelo_detectado && (
              <Badge variant="outline" className="text-xs">
                Modelo: {modelo_detectado}
              </Badge>
            )}
            {tipo_detectado && (
              <Badge variant="secondary" className="text-xs">
                {tipo_detectado}
              </Badge>
            )}
            <Badge className="text-xs bg-purple-100 text-purple-700">
              {total_variantes + 1} variantes encontradas
            </Badge>
          </div>
        </div>
      </div>

      {/* Tabla de variantes */}
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-sm flex items-center justify-between">
            <span className="flex items-center gap-2">
              <ArrowLeftRight className="w-4 h-4" />
              Variantes del Producto
            </span>
            {selectedIds.length > 1 && (
              <Badge variant="default">{selectedIds.length} seleccionados para comparar</Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="max-h-[400px] overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <input 
                      type="checkbox" 
                      className="rounded"
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedIds(todosProductos.slice(0, 4).map(p => p.id));
                        } else {
                          setSelectedIds([]);
                        }
                      }}
                    />
                  </TableHead>
                  <TableHead>Producto</TableHead>
                  <TableHead>Color</TableHead>
                  <TableHead>Calidad</TableHead>
                  <TableHead>Proveedor</TableHead>
                  <TableHead className="text-center">Stock</TableHead>
                  <TableHead className="text-right">Precio</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {todosProductos.map((producto, idx) => {
                  const isBase = idx === 0;
                  const colorInfo = getColorInfo(producto.color || producto.color_detectado);
                  const priceComp = !isBase ? getPriceComparison(producto.precio_venta, producto_base.precio_venta) : null;
                  
                  return (
                    <TableRow 
                      key={producto.id} 
                      className={`${isBase ? 'bg-blue-50' : ''} ${selectedIds.includes(producto.id) ? 'bg-purple-50' : ''}`}
                    >
                      <TableCell>
                        <input 
                          type="checkbox"
                          className="rounded"
                          checked={selectedIds.includes(producto.id)}
                          onChange={() => toggleSelect(producto.id)}
                        />
                      </TableCell>
                      <TableCell>
                        <div>
                          <p className="text-sm font-medium line-clamp-1">{producto.nombre_es || producto.nombre}</p>
                          {producto.sku && (
                            <p className="text-xs text-muted-foreground">{producto.sku}</p>
                          )}
                          {isBase && (
                            <Badge variant="outline" className="text-[10px] mt-1">Base</Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Popover open={editingColor === producto.id} onOpenChange={(open) => setEditingColor(open ? producto.id : null)}>
                          <PopoverTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-7 px-2">
                              {colorInfo ? (
                                <div className="flex items-center gap-1.5">
                                  <div 
                                    className="w-4 h-4 rounded-full border"
                                    style={{ backgroundColor: colorInfo.hex }}
                                  />
                                  <span className="text-xs">{colorInfo.value}</span>
                                </div>
                              ) : (
                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                  <Palette className="w-3 h-3" />
                                  Asignar
                                </span>
                              )}
                            </Button>
                          </PopoverTrigger>
                          <PopoverContent className="w-48 p-2">
                            <div className="grid grid-cols-4 gap-1">
                              {COLORES_PREDEFINIDOS.map((color) => (
                                <button
                                  key={color.value}
                                  className="w-8 h-8 rounded-full border-2 hover:scale-110 transition-transform"
                                  style={{ 
                                    backgroundColor: color.hex,
                                    borderColor: producto.color === color.value ? '#3b82f6' : 'transparent'
                                  }}
                                  title={color.value}
                                  onClick={() => handleSetColor(producto.id, color.value)}
                                />
                              ))}
                            </div>
                            {producto.color && (
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                className="w-full mt-2 text-xs"
                                onClick={() => handleSetColor(producto.id, '')}
                              >
                                <X className="w-3 h-3 mr-1" />
                                Quitar color
                              </Button>
                            )}
                          </PopoverContent>
                        </Popover>
                      </TableCell>
                      <TableCell>
                        {producto.calidad_pantalla ? (
                          <Badge 
                            variant="outline" 
                            className="text-xs"
                            style={{
                              backgroundColor: producto.calidad_info?.color || '#f3f4f6',
                              color: producto.calidad_info?.textColor || '#374151'
                            }}
                          >
                            {producto.calidad_info?.label || producto.calidad_pantalla}
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="text-xs">
                          {producto.proveedor || '-'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge variant={producto.stock > 0 ? 'default' : 'secondary'}>
                          {producto.stock || 0}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <span className="font-mono font-medium">
                            €{(producto.precio_venta || 0).toFixed(2)}
                          </span>
                          {priceComp && (
                            <span className={`text-xs ${priceComp.color}`}>
                              {priceComp.text}
                            </span>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Comparación seleccionada */}
      {productosComparar.length > 1 && (
        <Card className="border-purple-200 bg-purple-50/50">
          <CardHeader className="py-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <ArrowLeftRight className="w-4 h-4 text-purple-600" />
              Comparación de {productosComparar.length} variantes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {productosComparar.map((p) => {
                const colorInfo = getColorInfo(p.color);
                return (
                  <div key={p.id} className="bg-white rounded-lg p-3 border">
                    {colorInfo && (
                      <div 
                        className="w-full h-2 rounded-full mb-2"
                        style={{ backgroundColor: colorInfo.hex }}
                      />
                    )}
                    <p className="text-xs font-medium line-clamp-2">{p.nombre_es || p.nombre}</p>
                    <div className="mt-2 space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Precio:</span>
                        <span className="font-bold">€{(p.precio_venta || 0).toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Coste:</span>
                        <span>€{(p.precio_compra || 0).toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Margen:</span>
                        <span className="text-green-600">
                          {p.precio_venta && p.precio_compra 
                            ? `${(((p.precio_venta - p.precio_compra) / p.precio_venta) * 100).toFixed(0)}%`
                            : '-'}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Stock:</span>
                        <span>{p.stock || 0} uds</span>
                      </div>
                    </div>
                    <Badge variant="secondary" className="w-full justify-center mt-2 text-[10px]">
                      {p.proveedor || '-'}
                    </Badge>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {variantes.length === 0 && (
        <div className="text-center py-8 text-muted-foreground">
          <Package className="w-12 h-12 mx-auto mb-2 opacity-30" />
          <p>No se encontraron variantes similares</p>
          <p className="text-sm mt-1">Este producto parece ser único en el inventario</p>
        </div>
      )}
    </div>
  );
}

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import API from '../lib/api';
import {
  Search, Package, Settings, Plus, Trash2, RefreshCw, ExternalLink,
  CheckCircle, XCircle, ShoppingCart, TrendingDown, Eye, Download,
  Store, Loader2, AlertCircle, DollarSign
} from 'lucide-react';

export default function CatalogoProveedores() {
  const [proveedoresDisponibles, setProveedoresDisponibles] = useState([]);
  const [proveedoresConfigurados, setProveedoresConfigurados] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchMarca, setSearchMarca] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [configForm, setConfigForm] = useState({ nombre: '', username: '', password: '', activo: true });
  const [saving, setSaving] = useState(false);
  const [selectedProveedores, setSelectedProveedores] = useState([]);
  const [ordenarPor, setOrdenarPor] = useState('precio');

  useEffect(() => {
    cargarProveedores();
  }, []);

  const cargarProveedores = async () => {
    try {
      setLoading(true);
      const [disponibles, configurados] = await Promise.all([
        API.get('/catalogo-proveedores/disponibles'),
        API.get('/catalogo-proveedores/configurados')
      ]);
      setProveedoresDisponibles(disponibles.data.proveedores || []);
      setProveedoresConfigurados(configurados.data.proveedores || []);
    } catch (error) {
      toast.error('Error cargando proveedores');
    } finally {
      setLoading(false);
    }
  };

  const guardarProveedor = async () => {
    if (!configForm.nombre) {
      toast.error('Selecciona un proveedor');
      return;
    }
    setSaving(true);
    try {
      await API.post('/catalogo-proveedores/configurar', configForm);
      toast.success('Proveedor configurado correctamente');
      setShowConfigDialog(false);
      setConfigForm({ nombre: '', username: '', password: '', activo: true });
      cargarProveedores();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error guardando configuración');
    } finally {
      setSaving(false);
    }
  };

  const eliminarProveedor = async (nombre) => {
    if (!window.confirm(`¿Eliminar configuración de ${nombre}?`)) return;
    try {
      await API.delete(`/catalogo-proveedores/configurar/${nombre}`);
      toast.success('Proveedor eliminado');
      cargarProveedores();
    } catch (error) {
      toast.error('Error eliminando proveedor');
    }
  };

  const testConexion = async (nombre) => {
    try {
      const res = await API.post(`/catalogo-proveedores/test-conexion/${nombre}`);
      if (res.data.conexion_exitosa) {
        toast.success(`${nombre}: Conexión exitosa`);
      } else {
        toast.error(`${nombre}: ${res.data.mensaje}`);
      }
    } catch (error) {
      toast.error(`Error probando conexión: ${error.response?.data?.detail || error.message}`);
    }
  };

  const buscarProductos = async () => {
    if (!searchQuery.trim()) {
      toast.error('Introduce un término de búsqueda');
      return;
    }
    if (proveedoresConfigurados.length === 0) {
      toast.error('Configura al menos un proveedor primero');
      return;
    }
    
    setSearching(true);
    try {
      const res = await API.post('/catalogo-proveedores/buscar', {
        query: searchQuery,
        marca: searchMarca && searchMarca !== 'todas' ? searchMarca : null,
        proveedores: selectedProveedores.length > 0 ? selectedProveedores : null,
        solo_disponibles: true,
        ordenar_por: ordenarPor
      });
      setSearchResults(res.data.productos || []);
      if (res.data.total === 0) {
        toast.info('No se encontraron productos');
      } else {
        toast.success(`${res.data.total} productos encontrados`);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error en la búsqueda');
    } finally {
      setSearching(false);
    }
  };

  const importarProducto = async (producto) => {
    try {
      const res = await API.post('/catalogo-proveedores/importar-a-inventario', {
        sku_proveedor: producto.sku_proveedor,
        nombre: producto.nombre,
        precio: producto.precio,
        proveedor: producto.proveedor,
        cantidad: 1,
        tipo: producto.tipo || 'compatible'
      });
      toast.success(`Producto importado: ${res.data.producto?.sku}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error importando producto');
    }
  };

  const toggleProveedor = (nombre) => {
    setSelectedProveedores(prev => 
      prev.includes(nombre) 
        ? prev.filter(p => p !== nombre)
        : [...prev, nombre]
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Catálogo de Proveedores</h1>
          <p className="text-muted-foreground text-sm">
            Busca y compara productos de tus proveedores de repuestos
          </p>
        </div>
        <Button onClick={() => setShowConfigDialog(true)} data-testid="add-proveedor-btn">
          <Plus className="w-4 h-4 mr-2" /> Configurar Proveedor
        </Button>
      </div>

      <Tabs defaultValue="buscar" className="w-full">
        <TabsList>
          <TabsTrigger value="buscar" data-testid="tab-buscar">
            <Search className="w-4 h-4 mr-2" /> Buscar Productos
          </TabsTrigger>
          <TabsTrigger value="proveedores" data-testid="tab-proveedores">
            <Store className="w-4 h-4 mr-2" /> Proveedores ({proveedoresConfigurados.length})
          </TabsTrigger>
        </TabsList>

        {/* TAB: BUSCAR PRODUCTOS */}
        <TabsContent value="buscar" className="space-y-4">
          {proveedoresConfigurados.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="pt-6 text-center">
                <AlertCircle className="w-12 h-12 mx-auto text-amber-500 mb-4" />
                <h3 className="font-semibold mb-2">Sin proveedores configurados</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Configura al menos un proveedor para poder buscar productos
                </p>
                <Button onClick={() => setShowConfigDialog(true)}>
                  <Plus className="w-4 h-4 mr-2" /> Añadir Proveedor
                </Button>
              </CardContent>
            </Card>
          ) : (
            <>
              {/* Barra de búsqueda */}
              <Card>
                <CardContent className="pt-4">
                  <div className="flex flex-wrap gap-4">
                    <div className="flex-1 min-w-[200px]">
                      <Label className="text-xs mb-1 block">Buscar producto</Label>
                      <Input
                        placeholder="Ej: pantalla iphone 14 pro, batería samsung s24..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && buscarProductos()}
                        data-testid="search-input"
                      />
                    </div>
                    <div className="w-40">
                      <Label className="text-xs mb-1 block">Marca (opcional)</Label>
                      <Select value={searchMarca} onValueChange={setSearchMarca}>
                        <SelectTrigger>
                          <SelectValue placeholder="Todas" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="todas">Todas</SelectItem>
                          <SelectItem value="Apple">Apple</SelectItem>
                          <SelectItem value="Samsung">Samsung</SelectItem>
                          <SelectItem value="Xiaomi">Xiaomi</SelectItem>
                          <SelectItem value="Huawei">Huawei</SelectItem>
                          <SelectItem value="Oppo">Oppo</SelectItem>
                          <SelectItem value="OnePlus">OnePlus</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="w-36">
                      <Label className="text-xs mb-1 block">Ordenar por</Label>
                      <Select value={ordenarPor} onValueChange={setOrdenarPor}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="precio">Precio (menor)</SelectItem>
                          <SelectItem value="nombre">Nombre</SelectItem>
                          <SelectItem value="proveedor">Proveedor</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex items-end">
                      <Button onClick={buscarProductos} disabled={searching} data-testid="search-btn">
                        {searching ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Search className="w-4 h-4 mr-2" />}
                        Buscar
                      </Button>
                    </div>
                  </div>

                  {/* Filtro de proveedores */}
                  <div className="mt-4 pt-4 border-t">
                    <Label className="text-xs mb-2 block">Buscar en:</Label>
                    <div className="flex flex-wrap gap-2">
                      {proveedoresConfigurados.map((p) => (
                        <Badge
                          key={p.nombre}
                          variant={selectedProveedores.includes(p.nombre) || selectedProveedores.length === 0 ? "default" : "outline"}
                          className="cursor-pointer"
                          onClick={() => toggleProveedor(p.nombre)}
                        >
                          {p.autenticado ? <CheckCircle className="w-3 h-3 mr-1" /> : <XCircle className="w-3 h-3 mr-1" />}
                          {p.nombre}
                        </Badge>
                      ))}
                      {selectedProveedores.length > 0 && (
                        <Button variant="ghost" size="sm" onClick={() => setSelectedProveedores([])}>
                          Limpiar filtros
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Resultados */}
              {searchResults.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Package className="w-5 h-5" />
                      {searchResults.length} productos encontrados
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b bg-muted/50">
                            <th className="text-left p-2 font-medium">Producto</th>
                            <th className="text-left p-2 font-medium w-24">Proveedor</th>
                            <th className="text-right p-2 font-medium w-24">Precio</th>
                            <th className="text-center p-2 font-medium w-20">Stock</th>
                            <th className="text-center p-2 font-medium w-32">Acciones</th>
                          </tr>
                        </thead>
                        <tbody>
                          {searchResults.map((p, idx) => (
                            <tr key={`${p.proveedor}-${p.sku_proveedor}-${idx}`} className="border-b hover:bg-muted/30">
                              <td className="p-2">
                                <div className="flex items-center gap-3">
                                  {p.imagen_url && (
                                    <img src={p.imagen_url} alt="" className="w-12 h-12 object-contain rounded border" />
                                  )}
                                  <div>
                                    <p className="font-medium line-clamp-2">{p.nombre}</p>
                                    <p className="text-xs text-muted-foreground font-mono">{p.sku_proveedor}</p>
                                    {p.marca && <Badge variant="outline" className="mt-1 text-xs">{p.marca}</Badge>}
                                  </div>
                                </div>
                              </td>
                              <td className="p-2">
                                <Badge variant="secondary">{p.proveedor}</Badge>
                              </td>
                              <td className="p-2 text-right">
                                <span className="font-bold text-green-600">{p.precio.toFixed(2)} €</span>
                                <p className="text-xs text-muted-foreground">{p.precio_sin_iva.toFixed(2)} € sin IVA</p>
                              </td>
                              <td className="p-2 text-center">
                                {p.disponible ? (
                                  <Badge className="bg-green-100 text-green-700">En stock</Badge>
                                ) : (
                                  <Badge variant="destructive">Agotado</Badge>
                                )}
                              </td>
                              <td className="p-2">
                                <div className="flex justify-center gap-1">
                                  {p.url_producto && (
                                    <Button size="sm" variant="ghost" asChild>
                                      <a href={p.url_producto} target="_blank" rel="noopener noreferrer">
                                        <ExternalLink className="w-4 h-4" />
                                      </a>
                                    </Button>
                                  )}
                                  <Button size="sm" variant="outline" onClick={() => importarProducto(p)} data-testid={`import-${idx}`}>
                                    <Download className="w-4 h-4 mr-1" /> Importar
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </TabsContent>

        {/* TAB: PROVEEDORES CONFIGURADOS */}
        <TabsContent value="proveedores" className="space-y-4">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {proveedoresDisponibles.map((p) => {
              const configurado = proveedoresConfigurados.find(c => c.nombre === p.id);
              return (
                <Card key={p.id} className={configurado ? 'border-green-200 bg-green-50/30' : 'border-dashed'}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Store className="w-5 h-5" />
                        {p.nombre}
                      </CardTitle>
                      {configurado ? (
                        <Badge className="bg-green-100 text-green-700">Configurado</Badge>
                      ) : (
                        <Badge variant="outline">No configurado</Badge>
                      )}
                    </div>
                    <CardDescription>
                      <a href={p.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-xs">
                        {p.url}
                      </a>
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {configurado ? (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 text-sm">
                          {configurado.autenticado ? (
                            <><CheckCircle className="w-4 h-4 text-green-600" /> Autenticado</>
                          ) : (
                            <><XCircle className="w-4 h-4 text-amber-600" /> Sin autenticar</>
                          )}
                        </div>
                        <div className="flex gap-2 mt-3">
                          <Button size="sm" variant="outline" onClick={() => testConexion(p.id)}>
                            <RefreshCw className="w-4 h-4 mr-1" /> Test
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => {
                            setConfigForm({ nombre: p.id, username: '', password: '', activo: true });
                            setShowConfigDialog(true);
                          }}>
                            <Settings className="w-4 h-4 mr-1" /> Editar
                          </Button>
                          <Button size="sm" variant="ghost" className="text-red-600" onClick={() => eliminarProveedor(p.id)}>
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <Button size="sm" className="w-full" onClick={() => {
                        setConfigForm({ nombre: p.id, username: '', password: '', activo: true });
                        setShowConfigDialog(true);
                      }}>
                        <Plus className="w-4 h-4 mr-1" /> Configurar
                      </Button>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>
      </Tabs>

      {/* Dialog para configurar proveedor */}
      <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Configurar Proveedor</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Proveedor</Label>
              <Select value={configForm.nombre} onValueChange={(v) => setConfigForm(p => ({ ...p, nombre: v }))}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona un proveedor" />
                </SelectTrigger>
                <SelectContent>
                  {proveedoresDisponibles.map((p) => (
                    <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Usuario / Email</Label>
              <Input
                value={configForm.username}
                onChange={(e) => setConfigForm(p => ({ ...p, username: e.target.value }))}
                placeholder="Tu usuario del portal del proveedor"
              />
            </div>
            <div>
              <Label>Contraseña</Label>
              <Input
                type="password"
                value={configForm.password}
                onChange={(e) => setConfigForm(p => ({ ...p, password: e.target.value }))}
                placeholder="Tu contraseña del portal"
              />
            </div>
            <div className="flex items-center gap-2">
              <Switch
                checked={configForm.activo}
                onCheckedChange={(v) => setConfigForm(p => ({ ...p, activo: v }))}
              />
              <Label>Proveedor activo</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConfigDialog(false)}>Cancelar</Button>
            <Button onClick={guardarProveedor} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Guardar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { 
  Settings, 
  RefreshCw, 
  Download,
  Check,
  AlertTriangle,
  Eye,
  EyeOff,
  Database,
  ChevronDown,
  ChevronRight,
  Square,
  Play
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { toast } from 'sonner';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const utopyaAPI = {
  getConfig: () => axios.get(`${API_URL}/api/utopya/config`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  saveConfig: (data) => axios.post(`${API_URL}/api/utopya/config`, data, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  getCategories: () => axios.get(`${API_URL}/api/utopya/categories`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  syncCatalogo: () => axios.post(`${API_URL}/api/utopya/sync-catalogo`, {}, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  getSyncProgress: () => axios.get(`${API_URL}/api/utopya/sync-catalogo/progress`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  stopSync: () => axios.post(`${API_URL}/api/utopya/sync-catalogo/stop`, {}, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  getStats: () => axios.get(`${API_URL}/api/utopya/stats`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
};

export default function UtopyaConfig() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  
  const [config, setConfig] = useState({
    email: '',
    password: '',
    active: false,
    selected_categories: []
  });
  
  const [categories, setCategories] = useState({});
  const [stats, setStats] = useState(null);
  const [syncProgress, setSyncProgress] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [expandedBrands, setExpandedBrands] = useState({});

  useEffect(() => {
    fetchData();
    checkSyncRunning();
  }, []);
  
  const checkSyncRunning = async () => {
    try {
      const res = await utopyaAPI.getSyncProgress();
      if (res.data && res.data.running) {
        setSyncing(true);
        setSyncProgress(res.data);
      }
    } catch (err) { console.error('UtopyaConfig error:', err); }
  };
  
  // Polling para progreso
  useEffect(() => {
    let interval;
    if (syncing) {
      interval = setInterval(async () => {
        try {
          const res = await utopyaAPI.getSyncProgress();
          setSyncProgress(res.data);
          
          if (res.data.status === 'completed' || res.data.status === 'error') {
            setSyncing(false);
            fetchStats();
            if (res.data.status === 'completed') {
              toast.success(`✅ Sincronización completada: ${res.data.imported} nuevos, ${res.data.updated} actualizados`);
            }
          }
        } catch (error) {
          console.log('Error getting progress');
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [syncing]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [configRes, catsRes, statsRes] = await Promise.all([
        utopyaAPI.getConfig(),
        utopyaAPI.getCategories(),
        utopyaAPI.getStats()
      ]);
      
      if (configRes.data) {
        setConfig(prev => ({ ...prev, ...configRes.data }));
      }
      setCategories(catsRes.data || {});
      setStats(statsRes.data);
    } catch (error) {
      console.log('Error loading data');
    } finally {
      setLoading(false);
    }
  };
  
  const fetchStats = async () => {
    try {
      const res = await utopyaAPI.getStats();
      setStats(res.data);
    } catch (err) { console.error('UtopyaConfig error:', err); }
  };

  const handleSaveConfig = async () => {
    try {
      setSaving(true);
      await utopyaAPI.saveConfig(config);
      toast.success('Configuración guardada');
    } catch (error) {
      toast.error('Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  const handleSync = async () => {
    if (config.selected_categories.length === 0) {
      toast.error('Selecciona al menos una categoría');
      return;
    }
    
    try {
      // Guardar config con categorías seleccionadas primero
      await utopyaAPI.saveConfig(config);
      
      setSyncing(true);
      setSyncProgress({ status: 'starting', total: 0, processed: 0, imported: 0, updated: 0, errors: 0, categories_done: 0, categories_total: 0 });
      await utopyaAPI.syncCatalogo();
      toast.info('Sincronización iniciada...');
    } catch (error) {
      setSyncing(false);
      toast.error(error.response?.data?.detail || 'Error al iniciar');
    }
  };
  
  const handleStopSync = async () => {
    try {
      await utopyaAPI.stopSync();
      setSyncing(false);
      toast.info('Sincronización detenida');
    } catch (error) {
      toast.error('Error al detener');
    }
  };

  const toggleCategory = (brandKey, subKey) => {
    const categoryId = `${brandKey}.${subKey}`;
    setConfig(prev => {
      const current = prev.selected_categories || [];
      if (current.includes(categoryId)) {
        return { ...prev, selected_categories: current.filter(c => c !== categoryId) };
      } else {
        return { ...prev, selected_categories: [...current, categoryId] };
      }
    });
  };
  
  const toggleAllBrand = (brandKey) => {
    const brand = categories[brandKey];
    if (!brand) return;
    
    const allSubKeys = Object.keys(brand.subcategories || {});
    const allCatIds = allSubKeys.map(sub => `${brandKey}.${sub}`);
    
    setConfig(prev => {
      const current = prev.selected_categories || [];
      const allSelected = allCatIds.every(id => current.includes(id));
      
      if (allSelected) {
        // Deseleccionar todos
        return { ...prev, selected_categories: current.filter(c => !allCatIds.includes(c)) };
      } else {
        // Seleccionar todos
        const newSelection = [...new Set([...current, ...allCatIds])];
        return { ...prev, selected_categories: newSelection };
      }
    });
  };
  
  const isBrandFullySelected = (brandKey) => {
    const brand = categories[brandKey];
    if (!brand) return false;
    const allSubKeys = Object.keys(brand.subcategories || {});
    const allCatIds = allSubKeys.map(sub => `${brandKey}.${sub}`);
    return allCatIds.every(id => (config.selected_categories || []).includes(id));
  };
  
  const isBrandPartiallySelected = (brandKey) => {
    const brand = categories[brandKey];
    if (!brand) return false;
    const allSubKeys = Object.keys(brand.subcategories || {});
    const allCatIds = allSubKeys.map(sub => `${brandKey}.${sub}`);
    const selected = (config.selected_categories || []);
    return allCatIds.some(id => selected.includes(id)) && !allCatIds.every(id => selected.includes(id));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="utopya-config-page">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold">Utopya</h1>
          <p className="text-muted-foreground">Integración con proveedor de repuestos (scraping)</p>
        </div>
        <Badge variant={stats?.configurado ? "default" : "secondary"} className="h-8 px-3">
          {stats?.configurado ? "Configurado" : "No configurado"}
        </Badge>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">Productos importados</p>
              <p className="text-2xl font-bold">{stats.productos_importados}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">Categorías seleccionadas</p>
              <p className="text-2xl font-bold">{config.selected_categories?.length || 0}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">Última sincronización</p>
              <p className="text-sm font-medium">
                {stats.ultima_sync ? new Date(stats.ultima_sync).toLocaleString() : 'Nunca'}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Credenciales */}
      <Card>
        <CardHeader>
          <CardTitle>Credenciales de Utopya</CardTitle>
          <CardDescription>
            Introduce tus credenciales de acceso a utopya.es
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                type="email"
                value={config.email}
                onChange={(e) => setConfig(prev => ({ ...prev, email: e.target.value }))}
                placeholder="tu@email.com"
              />
            </div>
            <div className="space-y-2">
              <Label>Contraseña</Label>
              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  value={config.password}
                  onChange={(e) => setConfig(prev => ({ ...prev, password: e.target.value }))}
                  placeholder="••••••••"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-1/2 -translate-y-1/2"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Selección de categorías */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5" />
            Categorías a Sincronizar
          </CardTitle>
          <CardDescription>
            Selecciona las categorías de productos que quieres descargar de Utopya
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {Object.entries(categories).map(([brandKey, brand]) => (
            <Collapsible
              key={brandKey}
              open={expandedBrands[brandKey]}
              onOpenChange={(open) => setExpandedBrands(prev => ({ ...prev, [brandKey]: open }))}
            >
              <div className="flex items-center gap-2 p-2 hover:bg-slate-50 rounded-lg">
                <Checkbox
                  checked={isBrandFullySelected(brandKey)}
                  className={isBrandPartiallySelected(brandKey) ? "data-[state=checked]:bg-blue-400" : ""}
                  onCheckedChange={() => toggleAllBrand(brandKey)}
                />
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" size="sm" className="flex-1 justify-start gap-2">
                    {expandedBrands[brandKey] ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                    <span className="font-medium">{brand.name}</span>
                    <Badge variant="outline" className="ml-auto">
                      {Object.keys(brand.subcategories || {}).length} subcategorías
                    </Badge>
                  </Button>
                </CollapsibleTrigger>
              </div>
              <CollapsibleContent>
                <div className="ml-8 space-y-1 pb-2">
                  {Object.entries(brand.subcategories || {}).map(([subKey, subcat]) => {
                    const categoryId = `${brandKey}.${subKey}`;
                    const isSelected = (config.selected_categories || []).includes(categoryId);
                    
                    return (
                      <div
                        key={subKey}
                        className="flex items-center gap-2 p-2 hover:bg-slate-50 rounded cursor-pointer"
                        onClick={() => toggleCategory(brandKey, subKey)}
                      >
                        <Checkbox checked={isSelected} />
                        <span className="text-sm">{subcat.name}</span>
                      </div>
                    );
                  })}
                </div>
              </CollapsibleContent>
            </Collapsible>
          ))}
          
          <div className="pt-4 flex justify-between items-center">
            <p className="text-sm text-muted-foreground">
              {config.selected_categories?.length || 0} categorías seleccionadas
            </p>
            <Button onClick={handleSaveConfig} disabled={saving}>
              {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Check className="w-4 h-4 mr-2" />}
              Guardar Configuración
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Sincronización */}
      <Card>
        <CardHeader>
          <CardTitle>Sincronizar Catálogo</CardTitle>
          <CardDescription>
            Descarga los productos de las categorías seleccionadas a tu inventario
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Productos en inventario</p>
              <p className="text-2xl font-bold text-primary">{stats?.productos_importados || 0}</p>
            </div>
            
            {syncing ? (
              <Button variant="destructive" onClick={handleStopSync}>
                <Square className="w-4 h-4 mr-2" />
                Detener
              </Button>
            ) : (
              <Button 
                onClick={handleSync} 
                size="lg"
                disabled={!config.email || !config.password || config.selected_categories?.length === 0}
              >
                <Download className="w-4 h-4 mr-2" />
                Sincronizar ({config.selected_categories?.length || 0} categorías)
              </Button>
            )}
          </div>
          
          {/* Progreso */}
          {syncProgress && syncProgress.status !== 'idle' && (
            <div className="p-4 border rounded-lg space-y-3" data-testid="utopya-sync-progress">
              <div className="flex items-center justify-between">
                <span className="font-medium">
                  {syncProgress.status === 'starting' && 'Iniciando...'}
                  {syncProgress.status === 'launching_browser' && 'Abriendo navegador...'}
                  {syncProgress.status === 'logging_in' && 'Iniciando sesión en Utopya...'}
                  {syncProgress.status === 'scraping' && `Descargando: ${syncProgress.current_category}`}
                  {syncProgress.status === 'processing' && 'Guardando productos en base de datos...'}
                  {syncProgress.status === 'completed' && 'Completado'}
                  {syncProgress.status === 'error' && 'Error'}
                  {syncProgress.status === 'stopped' && 'Detenido'}
                </span>
                <div className="flex items-center gap-2">
                  {syncProgress.categories_total > 0 && (
                    <Badge variant="secondary">
                      Cat. {syncProgress.categories_done || 0}/{syncProgress.categories_total}
                    </Badge>
                  )}
                  <Badge>{syncProgress.processed || 0} / {syncProgress.total || 0}</Badge>
                </div>
              </div>
              
              {syncProgress.total > 0 && (
                <Progress value={(syncProgress.processed / syncProgress.total) * 100} className="h-2" />
              )}
              
              <div className="grid grid-cols-4 gap-3 text-sm">
                <div className="text-center p-2 bg-slate-50 rounded">
                  <p className="font-bold">{syncProgress.total || 0}</p>
                  <p className="text-muted-foreground">Encontrados</p>
                </div>
                <div className="text-center p-2 bg-green-50 rounded">
                  <p className="font-bold text-green-600">{syncProgress.imported || 0}</p>
                  <p className="text-green-700">Nuevos</p>
                </div>
                <div className="text-center p-2 bg-blue-50 rounded">
                  <p className="font-bold text-blue-600">{syncProgress.updated || 0}</p>
                  <p className="text-blue-700">Actualizados</p>
                </div>
                <div className="text-center p-2 bg-red-50 rounded">
                  <p className="font-bold text-red-600">{syncProgress.errors || 0}</p>
                  <p className="text-red-700">Errores</p>
                </div>
              </div>
              
              {syncProgress.last_error && (
                <p className="text-sm text-red-600">Error: {syncProgress.last_error}</p>
              )}
            </div>
          )}
          
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm text-amber-800">
              <strong>Nota:</strong> La sincronización puede tardar varios minutos dependiendo de las categorías seleccionadas.
              Los precios se calcularán automáticamente con el margen configurado (25% por defecto).
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

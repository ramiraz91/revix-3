import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { 
  Settings, 
  RefreshCw, 
  Package, 
  DollarSign, 
  Boxes,
  ShoppingCart,
  Check,
  X,
  AlertTriangle,
  Plug,
  Search,
  Download,
  Clock,
  Eye,
  EyeOff,
  ExternalLink,
  Key,
  Database,
  Percent,
  Play,
  Square
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// API helper
const mobilesentrixAPI = {
  getConfig: () => axios.get(`${API_URL}/api/mobilesentrix/config`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  saveConfig: (data) => axios.post(`${API_URL}/api/mobilesentrix/config`, data, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  startOAuth: () => axios.get(`${API_URL}/api/mobilesentrix/oauth/start`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  exchangeTokens: (data) => axios.post(`${API_URL}/api/mobilesentrix/oauth/exchange`, data, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  testConnection: () => axios.post(`${API_URL}/api/mobilesentrix/test-connection`, {}, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  getCategories: () => axios.get(`${API_URL}/api/mobilesentrix/categories`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  searchProducts: (data) => axios.post(`${API_URL}/api/mobilesentrix/products/search`, data, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  importProducts: (data) => axios.post(`${API_URL}/api/mobilesentrix/import-products`, data, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  syncPrices: () => axios.post(`${API_URL}/api/mobilesentrix/sync-prices`, {}, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  syncStock: () => axios.post(`${API_URL}/api/mobilesentrix/sync-stock`, {}, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  getStats: () => axios.get(`${API_URL}/api/mobilesentrix/stats`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  getOrders: () => axios.get(`${API_URL}/api/mobilesentrix/orders`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  // Nuevos endpoints para catálogo completo
  syncCatalogo: () => axios.post(`${API_URL}/api/mobilesentrix/sync-catalogo`, {}, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  getSyncProgress: () => axios.get(`${API_URL}/api/mobilesentrix/sync-catalogo/progress`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  stopSync: () => axios.post(`${API_URL}/api/mobilesentrix/sync-catalogo/stop`, {}, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  // Categorías seleccionadas
  getSelectedCategories: () => axios.get(`${API_URL}/api/mobilesentrix/selected-categories`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  saveSelectedCategories: (categories) => axios.post(`${API_URL}/api/mobilesentrix/selected-categories`, { categories }, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  // Márgenes
  getMargenes: () => axios.get(`${API_URL}/api/mobilesentrix/margenes`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  saveMargenes: (data) => axios.post(`${API_URL}/api/mobilesentrix/margenes`, data, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
  recalcularPrecios: (proveedor) => axios.post(`${API_URL}/api/mobilesentrix/recalcular-precios?proveedor=${proveedor}`, {}, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }),
};

export default function MobileSentrixConfig() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [startingOAuth, setStartingOAuth] = useState(false);
  const [showManualTokens, setShowManualTokens] = useState(false);
  const [manualTokens, setManualTokens] = useState({ oauth_token: '', oauth_verifier: '' });
  
  // Config state
  const [config, setConfig] = useState({
    consumer_key: '',
    consumer_secret: '',
    access_token: '',
    access_token_secret: '',
    environment: 'staging',
    sync_products: false,
    sync_prices: false,
    sync_stock: false,
    auto_orders: false,
    sync_interval_minutes: 60,
    active: false,
    oauth_completed: false
  });
  
  // Stats
  const [stats, setStats] = useState(null);
  
  // Categories
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [loadingCategories, setLoadingCategories] = useState(false);
  
  // Product search
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selectedProducts, setSelectedProducts] = useState([]);
  const [importing, setImporting] = useState(false);
  
  // Orders
  const [orders, setOrders] = useState([]);
  
  // Sync status
  const [syncing, setSyncing] = useState({ prices: false, stock: false });
  
  // Sincronización catálogo completo
  const [syncProgress, setSyncProgress] = useState(null);
  const [syncingCatalogo, setSyncingCatalogo] = useState(false);
  
  // Categorías seleccionadas para sync
  const [selectedSyncCategories, setSelectedSyncCategories] = useState([]);
  const [loadingSyncCategories, setLoadingSyncCategories] = useState(false);
  
  // Márgenes por proveedor
  const [margenes, setMargenes] = useState({
    MobileSentrix: { margen: 27.0, activo: true },
    Utopya: { margen: 25.0, activo: true },
    Otro: { margen: 30.0, activo: true }
  });
  const [savingMargenes, setSavingMargenes] = useState(false);

  useEffect(() => {
    // Check for OAuth callback parameters
    const oauthStatus = searchParams.get('oauth');
    const errorMessage = searchParams.get('message');
    
    if (oauthStatus === 'success') {
      toast.success('✅ Autorización completada correctamente');
      setSearchParams({});
    } else if (oauthStatus === 'error') {
      toast.error(`Error en autorización: ${decodeURIComponent(errorMessage || 'desconocido')}`);
      setSearchParams({});
    }
    
    fetchConfig();
    fetchStats();
    fetchMargenes();
    fetchSelectedSyncCategories();
    checkSyncRunning();
  }, []);
  
  // Polling para progreso de sincronización
  useEffect(() => {
    let interval;
    if (syncingCatalogo) {
      interval = setInterval(async () => {
        try {
          const res = await mobilesentrixAPI.getSyncProgress();
          setSyncProgress(res.data);
          
          if (res.data.status === 'completed' || res.data.status === 'error') {
            setSyncingCatalogo(false);
            fetchStats();
            if (res.data.status === 'completed') {
              toast.success(`✅ Catálogo sincronizado: ${res.data.imported} nuevos, ${res.data.updated} actualizados`);
            } else {
              toast.error(`Error: ${res.data.last_error}`);
            }
          }
        } catch (error) {
          console.log('Error getting sync progress');
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [syncingCatalogo]);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const res = await mobilesentrixAPI.getConfig();
      if (res.data) {
        setConfig(prev => ({ ...prev, ...res.data }));
      }
    } catch (error) {
      // Config might not exist yet
      console.log('No config found, using defaults');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await mobilesentrixAPI.getStats();
      setStats(res.data);
    } catch (error) {
      console.log('Could not fetch stats');
    }
  };
  
  const fetchMargenes = async () => {
    try {
      const res = await mobilesentrixAPI.getMargenes();
      if (res.data) {
        setMargenes(res.data);
      }
    } catch (error) {
      console.log('Could not fetch margenes');
    }
  };

  const fetchSelectedSyncCategories = async () => {
    try {
      const res = await mobilesentrixAPI.getSelectedCategories();
      setSelectedSyncCategories(res.data || []);
    } catch (error) {
      console.log('Could not fetch selected categories');
    }
  };

  const checkSyncRunning = async () => {
    try {
      const res = await mobilesentrixAPI.getSyncProgress();
      if (res.data && res.data.running) {
        setSyncingCatalogo(true);
        setSyncProgress(res.data);
      }
    } catch (error) { console.error('Sync progress error:', error); }
  };

  const handleToggleSyncCategory = (catId) => {
    setSelectedSyncCategories(prev => 
      prev.includes(String(catId))
        ? prev.filter(c => c !== String(catId))
        : [...prev, String(catId)]
    );
  };

  const handleSaveSelectedCategories = async () => {
    try {
      await mobilesentrixAPI.saveSelectedCategories(selectedSyncCategories);
      toast.success(`${selectedSyncCategories.length} categorías guardadas`);
    } catch (error) {
      toast.error('Error al guardar categorías');
    }
  };

  const fetchCategories = async () => {
    try {
      setLoadingCategories(true);
      const res = await mobilesentrixAPI.getCategories();
      
      // Aplanar las categorías para el selector
      const flattenCategories = (cats, result = []) => {
        for (const cat of cats) {
          result.push({ id: cat.id, name: cat.full_name || cat.name });
          if (cat.children && cat.children.length > 0) {
            flattenCategories(cat.children, result);
          }
        }
        return result;
      };
      
      const flatCats = flattenCategories(res.data || []);
      setCategories(flatCats);
    } catch (error) {
      console.log('Could not fetch categories:', error);
      toast.error('Error al cargar categorías');
    } finally {
      setLoadingCategories(false);
    }
  };

  const fetchOrders = async () => {
    try {
      const res = await mobilesentrixAPI.getOrders();
      setOrders(res.data || []);
    } catch (error) {
      console.log('Could not fetch orders');
    }
  };

  const handleSaveConfig = async () => {
    try {
      setSaving(true);
      await mobilesentrixAPI.saveConfig(config);
      toast.success('Configuración guardada correctamente');
      fetchStats();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar configuración');
    } finally {
      setSaving(false);
    }
  };

  const handleStartOAuth = async () => {
    if (!config.consumer_key || !config.consumer_secret) {
      toast.error('Primero guarda Consumer Key y Consumer Secret');
      return;
    }
    
    try {
      setStartingOAuth(true);
      // Primero guardar la config actual
      await mobilesentrixAPI.saveConfig(config);
      
      // Obtener URL de autorización
      const res = await mobilesentrixAPI.startOAuth();
      const { authorization_url, instructions } = res.data;
      
      toast.info(instructions);
      
      // Abrir en nueva ventana
      window.open(authorization_url, '_blank', 'width=800,height=600');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al iniciar autorización');
    } finally {
      setStartingOAuth(false);
    }
  };

  const handleManualTokenExchange = async () => {
    if (!manualTokens.oauth_token || !manualTokens.oauth_verifier) {
      toast.error('Introduce oauth_token y oauth_verifier');
      return;
    }
    
    try {
      const res = await mobilesentrixAPI.exchangeTokens(manualTokens);
      if (res.data.success) {
        toast.success('✅ Access Token obtenido correctamente');
        setShowManualTokens(false);
        setManualTokens({ oauth_token: '', oauth_verifier: '' });
        fetchConfig();
      } else {
        toast.error(res.data.error || 'Error al intercambiar tokens');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al intercambiar tokens');
    }
  };

  const handleTestConnection = async () => {
    try {
      setTesting(true);
      const res = await mobilesentrixAPI.testConnection();
      if (res.data.success) {
        toast.success('✅ Conexión exitosa con MobileSentrix');
        fetchStats();
        // Cargar categorías después de conexión exitosa
        fetchCategories();
      } else {
        toast.error(`Error: ${res.data.error}`);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al probar conexión');
    } finally {
      setTesting(false);
    }
  };

  const handleSearchProducts = async () => {
    // Necesita al menos una categoría o una búsqueda
    if (!searchQuery.trim() && !selectedCategory) {
      toast.error('Selecciona una categoría o escribe un término de búsqueda');
      return;
    }
    
    try {
      setSearching(true);
      const searchData = {
        page_size: 50
      };
      
      if (searchQuery.trim()) {
        searchData.query = searchQuery;
      }
      if (selectedCategory) {
        searchData.category_id = selectedCategory;
      }
      
      const res = await mobilesentrixAPI.searchProducts(searchData);
      setSearchResults(res.data?.items || []);
      setSelectedProducts([]);
      
      if ((res.data?.items || []).length === 0) {
        toast.info('No se encontraron productos con esos criterios');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al buscar productos');
    } finally {
      setSearching(false);
    }
  };

  const handleImportProducts = async () => {
    if (selectedProducts.length === 0) {
      toast.error('Selecciona al menos un producto');
      return;
    }
    
    try {
      setImporting(true);
      const res = await mobilesentrixAPI.importProducts({
        product_ids: selectedProducts,
        update_prices: true,
        update_stock: true
      });
      
      toast.success(`Importados: ${res.data.total_imported} | Errores: ${res.data.total_errors}`);
      setSelectedProducts([]);
      fetchStats();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al importar productos');
    } finally {
      setImporting(false);
    }
  };

  const handleSyncPrices = async () => {
    try {
      setSyncing(prev => ({ ...prev, prices: true }));
      await mobilesentrixAPI.syncPrices();
      toast.success('Sincronización de precios iniciada');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al sincronizar precios');
    } finally {
      setSyncing(prev => ({ ...prev, prices: false }));
    }
  };

  const handleSyncStock = async () => {
    try {
      setSyncing(prev => ({ ...prev, stock: true }));
      await mobilesentrixAPI.syncStock();
      toast.success('Sincronización de stock iniciada');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al sincronizar stock');
    } finally {
      setSyncing(prev => ({ ...prev, stock: false }));
    }
  };
  
  // Sincronizar catálogo completo
  const handleSyncCatalogo = async () => {
    try {
      // Guardar categorías seleccionadas primero
      if (selectedSyncCategories.length > 0) {
        await mobilesentrixAPI.saveSelectedCategories(selectedSyncCategories);
      }
      setSyncingCatalogo(true);
      setSyncProgress({ status: 'starting', total: 0, processed: 0, imported: 0, updated: 0, errors: 0, categories_done: 0, categories_total: 0 });
      await mobilesentrixAPI.syncCatalogo();
      toast.info('Sincronización del catálogo iniciada...');
    } catch (error) {
      setSyncingCatalogo(false);
      toast.error(error.response?.data?.detail || 'Error al iniciar sincronización');
    }
  };
  
  const handleStopSync = async () => {
    try {
      await mobilesentrixAPI.stopSync();
      setSyncingCatalogo(false);
      toast.info('Sincronización detenida');
    } catch (error) {
      toast.error('Error al detener sincronización');
    }
  };
  
  // Guardar márgenes
  const handleSaveMargenes = async () => {
    try {
      setSavingMargenes(true);
      await mobilesentrixAPI.saveMargenes(margenes);
      toast.success('Márgenes guardados correctamente');
    } catch (error) {
      toast.error('Error al guardar márgenes');
    } finally {
      setSavingMargenes(false);
    }
  };
  
  // Recalcular precios con nuevo margen
  const handleRecalcularPrecios = async (proveedor) => {
    try {
      const res = await mobilesentrixAPI.recalcularPrecios(proveedor);
      toast.success(`${res.data.productos_actualizados} productos actualizados con margen ${res.data.margen_aplicado}%`);
    } catch (error) {
      toast.error('Error al recalcular precios');
    }
  };
  
  // Actualizar margen de un proveedor
  const handleMargenChange = (proveedor, valor) => {
    setMargenes(prev => ({
      ...prev,
      [proveedor]: { ...prev[proveedor], margen: parseFloat(valor) || 0 }
    }));
  };

  const toggleProductSelection = (sku) => {
    setSelectedProducts(prev => 
      prev.includes(sku) 
        ? prev.filter(s => s !== sku)
        : [...prev, sku]
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="mobilesentrix-config-page">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold">MobileSentrix</h1>
          <p className="text-muted-foreground">Integración con proveedor de repuestos</p>
        </div>
        <div className="flex gap-2">
          <Badge variant={config.active ? "default" : "secondary"} className="h-8 px-3">
            {config.active ? "Activo" : "Inactivo"}
          </Badge>
          <Badge variant="outline" className="h-8 px-3">
            {config.environment === 'production' ? '🔴 Producción' : '🟡 Staging'}
          </Badge>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Package className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.productos_importados}</p>
                  <p className="text-sm text-muted-foreground">Productos importados</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <ShoppingCart className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.pedidos_realizados}</p>
                  <p className="text-sm text-muted-foreground">Pedidos realizados</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Clock className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm font-medium">
                    {stats.ultima_sync ? new Date(stats.ultima_sync).toLocaleString('es-ES') : 'Nunca'}
                  </p>
                  <p className="text-sm text-muted-foreground">Última sincronización</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${stats.connection_status === 'ok' ? 'bg-green-100' : 'bg-gray-100'}`}>
                  <Plug className={`w-5 h-5 ${stats.connection_status === 'ok' ? 'text-green-600' : 'text-gray-400'}`} />
                </div>
                <div>
                  <p className="text-sm font-medium">
                    {stats.connection_status === 'ok' ? 'Conectado' : 'Sin verificar'}
                  </p>
                  <p className="text-sm text-muted-foreground">Estado conexión</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Tabs */}
      <Tabs defaultValue="config" className="space-y-4">
        <TabsList>
          <TabsTrigger value="config">
            <Settings className="w-4 h-4 mr-2" />
            Configuración
          </TabsTrigger>
          <TabsTrigger value="catalogo">
            <Database className="w-4 h-4 mr-2" />
            Catálogo
          </TabsTrigger>
          <TabsTrigger value="products">
            <Package className="w-4 h-4 mr-2" />
            Buscar
          </TabsTrigger>
          <TabsTrigger value="sync">
            <RefreshCw className="w-4 h-4 mr-2" />
            Sincronización
          </TabsTrigger>
          <TabsTrigger value="orders" onClick={fetchOrders}>
            <ShoppingCart className="w-4 h-4 mr-2" />
            Pedidos
          </TabsTrigger>
        </TabsList>

        {/* CONFIG TAB */}
        <TabsContent value="config" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Credenciales API</CardTitle>
              <CardDescription>
                Configura las credenciales OAuth para conectar con MobileSentrix
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Consumer Key</Label>
                  <Input
                    value={config.consumer_key}
                    onChange={(e) => setConfig(prev => ({ ...prev, consumer_key: e.target.value }))}
                    placeholder="fdfc9509793d786d..."
                    data-testid="consumer-key-input"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Consumer Secret</Label>
                  <div className="relative">
                    <Input
                      type={showSecret ? "text" : "password"}
                      value={config.consumer_secret}
                      onChange={(e) => setConfig(prev => ({ ...prev, consumer_secret: e.target.value }))}
                      placeholder="c4b850b6df7cdd5d..."
                      data-testid="consumer-secret-input"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-2 top-1/2 -translate-y-1/2 h-7 w-7"
                      onClick={() => setShowSecret(!showSecret)}
                    >
                      {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </Button>
                  </div>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Entorno</Label>
                <Select
                  value={config.environment}
                  onValueChange={(value) => setConfig(prev => ({ ...prev, environment: value }))}
                >
                  <SelectTrigger className="w-64">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="staging">🟡 Staging (preprod.mobilesentrix.eu)</SelectItem>
                    <SelectItem value="production">🔴 Producción (www.mobilesentrix.eu)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* OAuth Authorization */}
          <Card className={config.oauth_completed ? "border-green-200 bg-green-50/30" : "border-orange-200 bg-orange-50/30"}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className={`w-5 h-5 ${config.oauth_completed ? 'text-green-600' : 'text-orange-600'}`} />
                Autorización OAuth
              </CardTitle>
              <CardDescription>
                {config.oauth_completed 
                  ? "✅ Autorización completada. Ya puedes usar la API."
                  : "Paso 2: Autoriza NEXORA para acceder a tu cuenta de MobileSentrix"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {config.oauth_completed ? (
                <div className="p-4 bg-green-100 border border-green-200 rounded-lg">
                  <div className="flex items-center gap-2 text-green-800">
                    <Check className="w-5 h-5" />
                    <span className="font-medium">Access Token configurado</span>
                  </div>
                  {config.oauth_completed_at && (
                    <p className="text-sm text-green-700 mt-1">
                      Autorizado el: {new Date(config.oauth_completed_at).toLocaleString('es-ES')}
                    </p>
                  )}
                </div>
              ) : (
                <>
                  <div className="p-4 bg-orange-100 border border-orange-200 rounded-lg text-orange-800">
                    <p className="font-medium mb-2">Pasos para autorizar:</p>
                    <ol className="list-decimal list-inside space-y-1 text-sm">
                      <li>Guarda las credenciales (Consumer Key y Secret) arriba</li>
                      <li>Haz clic en "Iniciar Autorización"</li>
                      <li>Se abrirá una ventana de MobileSentrix</li>
                      <li>Inicia sesión y autoriza el acceso</li>
                      <li>Serás redirigido de vuelta automáticamente</li>
                    </ol>
                  </div>
                  
                  <div className="flex gap-2">
                    <Button onClick={handleStartOAuth} disabled={startingOAuth || !config.consumer_key}>
                      {startingOAuth ? (
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <ExternalLink className="w-4 h-4 mr-2" />
                      )}
                      Iniciar Autorización
                    </Button>
                    
                    <Button variant="outline" onClick={() => setShowManualTokens(true)}>
                      Introducir tokens manualmente
                    </Button>
                  </div>
                </>
              )}
              
              <div className="flex gap-2 pt-2">
                <Button onClick={handleTestConnection} disabled={testing} variant="outline">
                  {testing ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Plug className="w-4 h-4 mr-2" />}
                  Probar Conexión
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Manual Token Dialog */}
          <Dialog open={showManualTokens} onOpenChange={setShowManualTokens}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Introducir Tokens Manualmente</DialogTitle>
                <DialogDescription>
                  Si el callback automático no funciona, copia los tokens de la URL de redirección
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 pt-4">
                <div className="space-y-2">
                  <Label>OAuth Token</Label>
                  <Input
                    value={manualTokens.oauth_token}
                    onChange={(e) => setManualTokens(prev => ({ ...prev, oauth_token: e.target.value }))}
                    placeholder="720b17cf13fd15e7cf77b0314851751"
                  />
                </div>
                <div className="space-y-2">
                  <Label>OAuth Verifier</Label>
                  <Input
                    value={manualTokens.oauth_verifier}
                    onChange={(e) => setManualTokens(prev => ({ ...prev, oauth_verifier: e.target.value }))}
                    placeholder="c44efcdc5d53b9f01ee de749cdd4e242"
                  />
                </div>
                <Button onClick={handleManualTokenExchange} className="w-full">
                  Obtener Access Token
                </Button>
              </div>
            </DialogContent>
          </Dialog>

          <Card>
            <CardHeader>
              <CardTitle>Funcionalidades</CardTitle>
              <CardDescription>
                Activa o desactiva las funcionalidades de la integración
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <Package className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="font-medium">Sincronizar Productos</p>
                    <p className="text-sm text-muted-foreground">Permite buscar e importar productos del catálogo</p>
                  </div>
                </div>
                <Switch
                  checked={config.sync_products}
                  onCheckedChange={(checked) => setConfig(prev => ({ ...prev, sync_products: checked }))}
                />
              </div>
              
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <DollarSign className="w-5 h-5 text-green-600" />
                  </div>
                  <div>
                    <p className="font-medium">Sincronizar Precios</p>
                    <p className="text-sm text-muted-foreground">Actualiza automáticamente los precios de coste</p>
                  </div>
                </div>
                <Switch
                  checked={config.sync_prices}
                  onCheckedChange={(checked) => setConfig(prev => ({ ...prev, sync_prices: checked }))}
                />
              </div>
              
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-orange-100 rounded-lg">
                    <Boxes className="w-5 h-5 text-orange-600" />
                  </div>
                  <div>
                    <p className="font-medium">Sincronizar Stock</p>
                    <p className="text-sm text-muted-foreground">Consulta stock disponible en el proveedor</p>
                  </div>
                </div>
                <Switch
                  checked={config.sync_stock}
                  onCheckedChange={(checked) => setConfig(prev => ({ ...prev, sync_stock: checked }))}
                />
              </div>
              
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <ShoppingCart className="w-5 h-5 text-purple-600" />
                  </div>
                  <div>
                    <p className="font-medium">Pedidos Automáticos</p>
                    <p className="text-sm text-muted-foreground">Permite realizar pedidos directamente desde NEXORA</p>
                  </div>
                </div>
                <Switch
                  checked={config.auto_orders}
                  onCheckedChange={(checked) => setConfig(prev => ({ ...prev, auto_orders: checked }))}
                />
              </div>
              
              <div className="flex items-center justify-between p-4 border rounded-lg bg-slate-50">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${config.active ? 'bg-green-100' : 'bg-gray-100'}`}>
                    {config.active ? <Check className="w-5 h-5 text-green-600" /> : <X className="w-5 h-5 text-gray-400" />}
                  </div>
                  <div>
                    <p className="font-medium">Integración Activa</p>
                    <p className="text-sm text-muted-foreground">Activa/desactiva toda la integración</p>
                  </div>
                </div>
                <Switch
                  checked={config.active}
                  onCheckedChange={(checked) => setConfig(prev => ({ ...prev, active: checked }))}
                />
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSaveConfig} disabled={saving} size="lg">
              {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Check className="w-4 h-4 mr-2" />}
              Guardar Configuración
            </Button>
          </div>
        </TabsContent>

        {/* CATÁLOGO TAB - Descarga y márgenes */}
        <TabsContent value="catalogo" className="space-y-4">
          {/* Selección de categorías para sincronizar */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="w-5 h-5" />
                Categorías a Sincronizar
              </CardTitle>
              <CardDescription>
                Selecciona las categorías que quieres descargar de MobileSentrix.
                Si no seleccionas ninguna, se descargará todo el catálogo.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!config.sync_products ? (
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-center gap-3">
                  <AlertTriangle className="w-5 h-5 text-yellow-600" />
                  <p className="text-yellow-800">
                    Activa "Sincronizar Productos" en la configuración primero
                  </p>
                </div>
              ) : (
                <>
                  {categories.length === 0 ? (
                    <div className="text-center py-4">
                      <p className="text-muted-foreground mb-3">Carga las categorías desde la API primero</p>
                      <Button onClick={fetchCategories} disabled={loadingCategories}>
                        {loadingCategories ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
                        Cargar Categorías
                      </Button>
                    </div>
                  ) : (
                    <>
                      <div className="max-h-64 overflow-y-auto border rounded-lg p-2 space-y-1">
                        {categories.map((cat) => {
                          const isSelected = selectedSyncCategories.includes(String(cat.id));
                          return (
                            <div
                              key={cat.id}
                              className="flex items-center gap-2 p-2 hover:bg-slate-50 rounded cursor-pointer"
                              onClick={() => handleToggleSyncCategory(cat.id)}
                            >
                              <Checkbox checked={isSelected} />
                              <span className="text-sm">{cat.name}</span>
                            </div>
                          );
                        })}
                      </div>
                      <div className="flex justify-between items-center">
                        <p className="text-sm text-muted-foreground">
                          {selectedSyncCategories.length} categorías seleccionadas
                          {selectedSyncCategories.length === 0 && " (se descargará todo)"}
                        </p>
                        <Button variant="outline" onClick={handleSaveSelectedCategories}>
                          <Check className="w-4 h-4 mr-2" />
                          Guardar Selección
                        </Button>
                      </div>
                    </>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          {/* Sincronización del catálogo */}
          <Card>
            <CardHeader>
              <CardTitle>Sincronizar Catálogo</CardTitle>
              <CardDescription>
                Descarga los productos seleccionados a tu inventario local
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {config.sync_products && (
                <>
                  <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                    <div>
                      <p className="font-medium">Productos en inventario</p>
                      <p className="text-2xl font-bold text-primary">{stats?.productos_importados || 0}</p>
                      {stats?.ultima_sync && (
                        <p className="text-xs text-muted-foreground">
                          Última sync: {new Date(stats.ultima_sync).toLocaleString()}
                        </p>
                      )}
                    </div>
                    
                    {syncingCatalogo ? (
                      <Button variant="destructive" onClick={handleStopSync}>
                        <Square className="w-4 h-4 mr-2" />
                        Detener
                      </Button>
                    ) : (
                      <Button onClick={handleSyncCatalogo} size="lg" data-testid="sync-catalogo-btn">
                        <Download className="w-4 h-4 mr-2" />
                        Sincronizar {selectedSyncCategories.length > 0 ? `(${selectedSyncCategories.length} cat.)` : '(Todo)'}
                      </Button>
                    )}
                  </div>
                  
                  {/* Progreso de sincronización */}
                  {syncProgress && syncProgress.status !== 'idle' && (
                    <div className="p-4 border rounded-lg space-y-3" data-testid="sync-progress">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">
                          {syncProgress.status === 'starting' && 'Iniciando...'}
                          {syncProgress.status === 'loading_categories' && 'Cargando categorías...'}
                          {syncProgress.status === 'downloading' && (
                            <>Descargando: {syncProgress.current_category} (pág. {syncProgress.current_page})</>
                          )}
                          {syncProgress.status === 'completed' && 'Completado'}
                          {syncProgress.status === 'error' && 'Error'}
                          {syncProgress.status === 'stopping' && 'Deteniendo...'}
                        </span>
                        {syncProgress.categories_total > 0 && (
                          <Badge variant="secondary">
                            Cat. {syncProgress.categories_done}/{syncProgress.categories_total}
                          </Badge>
                        )}
                      </div>
                      
                      {syncProgress.categories_total > 0 && (
                        <Progress 
                          value={(syncProgress.categories_done / syncProgress.categories_total) * 100} 
                          className="h-2"
                        />
                      )}
                      
                      <div className="grid grid-cols-4 gap-3 text-sm">
                        <div className="text-center p-2 bg-slate-50 rounded">
                          <p className="font-bold">{syncProgress.processed || 0}</p>
                          <p className="text-muted-foreground">Procesados</p>
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
                </>
              )}
            </CardContent>
          </Card>
          
          {/* Configuración de márgenes por proveedor */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Percent className="w-5 h-5" />
                Márgenes por Proveedor
              </CardTitle>
              <CardDescription>
                Configura el margen de beneficio que se aplicará automáticamente a los precios de cada proveedor
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4">
                {Object.entries(margenes).map(([proveedor, config]) => (
                  <div key={proveedor} className="flex items-center gap-4 p-4 border rounded-lg">
                    <div className="flex-1">
                      <Label className="font-medium">{proveedor}</Label>
                      <p className="text-xs text-muted-foreground">
                        Precio venta = Precio compra × (1 + {config.margen}%)
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        value={config.margen}
                        onChange={(e) => handleMargenChange(proveedor, e.target.value)}
                        className="w-24 text-right"
                        min="0"
                        max="200"
                        step="0.5"
                      />
                      <span className="text-muted-foreground">%</span>
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => handleRecalcularPrecios(proveedor)}
                      title="Recalcular precios de venta"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
              
              <div className="flex justify-end">
                <Button onClick={handleSaveMargenes} disabled={savingMargenes}>
                  {savingMargenes ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Check className="w-4 h-4 mr-2" />}
                  Guardar Márgenes
                </Button>
              </div>
              
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-sm text-amber-800">
                  <strong>Ejemplo:</strong> Con un margen del 27%, un producto con precio de compra de 10€ 
                  tendrá un precio de venta de 12.70€
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* PRODUCTS TAB */}
        <TabsContent value="products" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Buscar Productos</CardTitle>
              <CardDescription>
                Selecciona una categoría y/o busca por nombre para encontrar productos
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!config.sync_products ? (
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-center gap-3">
                  <AlertTriangle className="w-5 h-5 text-yellow-600" />
                  <p className="text-yellow-800">
                    Activa "Sincronizar Productos" en la configuración para usar esta función
                  </p>
                </div>
              ) : (
                <>
                  {/* Selector de categoría */}
                  <div className="space-y-2">
                    <Label>Categoría (recomendado para búsquedas más rápidas)</Label>
                    <div className="flex gap-2">
                      <Select
                        value={selectedCategory?.toString() || 'all'}
                        onValueChange={(val) => setSelectedCategory(val === 'all' ? null : parseInt(val))}
                      >
                        <SelectTrigger className="flex-1">
                          <SelectValue placeholder="Selecciona una categoría..." />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">Todas las categorías</SelectItem>
                          {categories.map((cat) => (
                            <SelectItem key={cat.id} value={cat.id.toString()}>
                              {cat.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button 
                        variant="outline" 
                        onClick={fetchCategories}
                        disabled={loadingCategories}
                      >
                        {loadingCategories ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <RefreshCw className="w-4 h-4" />
                        )}
                      </Button>
                    </div>
                    {categories.length === 0 && (
                      <p className="text-xs text-muted-foreground">
                        Haz clic en el botón de recargar para obtener las categorías de MobileSentrix
                      </p>
                    )}
                  </div>
                  
                  {/* Búsqueda por texto */}
                  <div className="space-y-2">
                    <Label>Buscar por nombre o SKU</Label>
                    <div className="flex gap-2">
                      <Input
                        placeholder="Ej: iPhone 15, pantalla Samsung..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSearchProducts()}
                        className="flex-1"
                      />
                      <Button onClick={handleSearchProducts} disabled={searching}>
                        {searching ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                        <span className="ml-2">Buscar</span>
                      </Button>
                    </div>
                  </div>
                  
                  {searchResults.length > 0 && (
                    <>
                      <div className="flex justify-between items-center">
                        <p className="text-sm text-muted-foreground">
                          {searchResults.length} resultados | {selectedProducts.length} seleccionados
                        </p>
                        <Button 
                          onClick={handleImportProducts} 
                          disabled={importing || selectedProducts.length === 0}
                        >
                          {importing ? (
                            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                          ) : (
                            <Download className="w-4 h-4 mr-2" />
                          )}
                          Importar Seleccionados ({selectedProducts.length})
                        </Button>
                      </div>
                      
                      <div className="border rounded-lg max-h-96 overflow-y-auto">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="w-12"></TableHead>
                              <TableHead>SKU</TableHead>
                              <TableHead>Nombre</TableHead>
                              <TableHead className="text-right">Precio</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {searchResults.map((product) => (
                              <TableRow key={product.sku}>
                                <TableCell>
                                  <Checkbox
                                    checked={selectedProducts.includes(product.sku)}
                                    onCheckedChange={() => toggleProductSelection(product.sku)}
                                  />
                                </TableCell>
                                <TableCell className="font-mono text-sm">{product.sku}</TableCell>
                                <TableCell>{product.name}</TableCell>
                                <TableCell className="text-right">€{product.price?.toFixed(2) || '0.00'}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* SYNC TAB */}
        <TabsContent value="sync" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-green-600" />
                  Sincronizar Precios
                </CardTitle>
                <CardDescription>
                  Actualiza los precios de coste de todos los productos importados
                </CardDescription>
              </CardHeader>
              <CardContent>
                {!config.sync_prices ? (
                  <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
                    Función desactivada en configuración
                  </div>
                ) : (
                  <Button 
                    onClick={handleSyncPrices} 
                    disabled={syncing.prices}
                    className="w-full"
                  >
                    {syncing.prices ? (
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <RefreshCw className="w-4 h-4 mr-2" />
                    )}
                    Sincronizar Precios Ahora
                  </Button>
                )}
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Boxes className="w-5 h-5 text-orange-600" />
                  Sincronizar Stock
                </CardTitle>
                <CardDescription>
                  Consulta el stock disponible en el proveedor
                </CardDescription>
              </CardHeader>
              <CardContent>
                {!config.sync_stock ? (
                  <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
                    Función desactivada en configuración
                  </div>
                ) : (
                  <Button 
                    onClick={handleSyncStock} 
                    disabled={syncing.stock}
                    className="w-full"
                  >
                    {syncing.stock ? (
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <RefreshCw className="w-4 h-4 mr-2" />
                    )}
                    Sincronizar Stock Ahora
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
          
          <Card>
            <CardHeader>
              <CardTitle>Sincronización Automática</CardTitle>
              <CardDescription>
                Configura la frecuencia de sincronización automática
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <Label>Intervalo (minutos)</Label>
                <Input
                  type="number"
                  min="15"
                  max="1440"
                  value={config.sync_interval_minutes}
                  onChange={(e) => setConfig(prev => ({ ...prev, sync_interval_minutes: parseInt(e.target.value) || 60 }))}
                  className="w-24"
                />
                <p className="text-sm text-muted-foreground">
                  (mínimo 15 minutos, máximo 24 horas)
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ORDERS TAB */}
        <TabsContent value="orders" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Historial de Pedidos</CardTitle>
              <CardDescription>
                Pedidos realizados a MobileSentrix desde NEXORA
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!config.auto_orders ? (
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-center gap-3">
                  <AlertTriangle className="w-5 h-5 text-yellow-600" />
                  <p className="text-yellow-800">
                    Activa "Pedidos Automáticos" en la configuración para usar esta función
                  </p>
                </div>
              ) : orders.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <ShoppingCart className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No hay pedidos realizados</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>Fecha</TableHead>
                      <TableHead>Items</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Creado por</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {orders.map((order) => (
                      <TableRow key={order.id}>
                        <TableCell className="font-mono text-sm">{order.id.slice(0, 8)}...</TableCell>
                        <TableCell>{new Date(order.created_at).toLocaleString('es-ES')}</TableCell>
                        <TableCell>{order.items?.length || 0} productos</TableCell>
                        <TableCell>
                          <Badge variant="outline">{order.status}</Badge>
                        </TableCell>
                        <TableCell>{order.created_by}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

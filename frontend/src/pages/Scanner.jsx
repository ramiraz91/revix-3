import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import QrScanner from 'qr-scanner';
import { QrCode, Camera, StopCircle, Search, CheckCircle2, Eye, ArrowRight, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ordenesAPI } from '@/lib/api';
import { toast } from 'sonner';

const scanTypes = {
  consulta: { 
    label: '👁️ Solo Consulta', 
    description: 'Ver información de la orden sin cambiar estado',
    color: 'bg-blue-500'
  },
  recepcion: { 
    label: '📦 Recepción (Centro)', 
    description: 'Marca la orden como RECIBIDA',
    color: 'bg-green-500'
  },
  tecnico: { 
    label: '🔧 Técnico (Taller)', 
    description: 'Marca la orden como EN TALLER',
    color: 'bg-purple-500'
  }
};

const statusLabels = {
  pendiente_recibir: 'Pendiente Recibir',
  recibida: 'Recibida',
  en_taller: 'En Taller',
  re_presupuestar: 'Re-presupuestar',
  reparado: 'Reparado',
  validacion: 'Validación',
  enviado: 'Enviado',
  garantia: 'Garantía',
  cancelado: 'Cancelado',
  reemplazo: 'Reemplazo',
  irreparable: 'Irreparable',
};

export default function Scanner() {
  const navigate = useNavigate();
  const videoRef = useRef(null);
  const scannerRef = useRef(null);
  
  const [scanning, setScanning] = useState(false);
  const [tipoEscaneo, setTipoEscaneo] = useState('consulta'); // Por defecto: solo consulta
  const [manualId, setManualId] = useState('');
  const [lastScanned, setLastScanned] = useState(null);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    return () => {
      if (scannerRef.current) {
        scannerRef.current.stop();
        scannerRef.current.destroy();
      }
    };
  }, []);

  const startScanning = async () => {
    try {
      if (!videoRef.current) return;
      
      scannerRef.current = new QrScanner(
        videoRef.current,
        result => handleScan(result.data),
        {
          highlightScanRegion: true,
          highlightCodeOutline: true,
        }
      );
      
      await scannerRef.current.start();
      setScanning(true);
      toast.success('Cámara iniciada');
    } catch (error) {
      console.error('Error starting scanner:', error);
      toast.error('Error al acceder a la cámara');
    }
  };

  const stopScanning = () => {
    if (scannerRef.current) {
      scannerRef.current.stop();
    }
    setScanning(false);
  };

  const handleScan = async (data) => {
    if (processing) return;
    
    setProcessing(true);
    
    try {
      // Limpiar el código: eliminar caracteres de control, espacios, enters, etc.
      const ordenRef = data.replace(/[\x00-\x1F\x7F\r\n\t]/g, '').trim();
      
      console.log('Código escaneado (limpio):', ordenRef);
      
      // Primero obtener la orden para ver su información
      const ordenRes = await ordenesAPI.obtener(ordenRef);
      const orden = ordenRes.data;
      
      // MODO CONSULTA: Solo mostrar información, no cambiar estado
      if (tipoEscaneo === 'consulta') {
        setLastScanned({
          id: orden.id,
          numero_orden: orden.numero_orden,
          estado_actual: orden.estado,
          dispositivo: orden.dispositivo,
          cliente_id: orden.cliente_id,
          bloqueada: orden.bloqueada,
          success: true,
          modo: 'consulta'
        });
        
        toast.success(`Orden encontrada: ${orden.numero_orden}`);
        
        // Reproducir sonido de éxito
        playSuccessSound();
        return;
      }
      
      // MODO CAMBIO DE ESTADO: Intentar cambiar el estado
      try {
        const res = await ordenesAPI.escanear(ordenRef, {
          tipo_escaneo: tipoEscaneo,
          usuario: 'scanner'
        });
        
        setLastScanned({
          id: orden.id,
          numero_orden: orden.numero_orden,
          estado_anterior: orden.estado,
          nuevo_estado: res.data.nuevo_estado,
          dispositivo: orden.dispositivo,
          success: true,
          modo: 'cambio_estado'
        });
        
        toast.success(res.data.message);
        playSuccessSound();
        
      } catch (scanError) {
        // Si el escaneo falla (por ejemplo, estado incorrecto), mostrar la orden de todas formas
        const errorMessage = scanError.response?.data?.detail || 'No se pudo cambiar el estado';
        
        setLastScanned({
          id: orden.id,
          numero_orden: orden.numero_orden,
          estado_actual: orden.estado,
          dispositivo: orden.dispositivo,
          bloqueada: orden.bloqueada,
          success: true,
          modo: 'consulta',
          warning: errorMessage
        });
        
        toast.warning(`${errorMessage}. Mostrando información de la orden.`);
        playWarningSound();
      }
      
    } catch (error) {
      const message = error.response?.data?.detail || 'Orden no encontrada';
      toast.error(message);
      setLastScanned({
        id: data,
        success: false,
        error: message
      });
      playErrorSound();
    } finally {
      setProcessing(false);
    }
  };

  const playSuccessSound = () => {
    const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdH2DhYWAe3V0dnuBhoaFf3l0dnuAhoeFgHp0dXl/hYeGgXx2dXh+hIaGgn13dnl+g4WFgX57eHl+goSEgH99enp9gYOCf399fH1/gYGBfn9/fn9/gIB/f4CAgH9/gIB/f4CAgH9/gIB/f4CAgH9/gIB/');
    audio.play().catch(() => {});
  };

  const playWarningSound = () => {
    // Sonido diferente para warning
    const audio = new Audio('data:audio/wav;base64,UklGRl9vAABXQVZFZm10IBIAAAABAAEAQB8AAEAfAAABAAgAAABkYXRhQW8AAICAgICAgICAgICAgICAgICAhYmLi4uJhYKAf4CCg4SEg4KBgIGChYiJiYiGg4GAgIKFh4iIh4WDgYGChIaHh4eGhIOCgoOEhoeHhoWEg4KDhIWGhoaFhIOD');
    audio.play().catch(() => {});
  };

  const playErrorSound = () => {
    // Sonido de error
  };

  const handleManualSearch = async (e) => {
    e.preventDefault();
    if (!manualId.trim()) {
      toast.error('Introduce un número de orden o ID');
      return;
    }
    await handleScan(manualId.trim());
  };

  const handleViewOrder = () => {
    if (lastScanned?.id) {
      navigate(`/crm/ordenes/${lastScanned.id}`);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="scanner-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Escáner QR</h1>
        <p className="text-muted-foreground mt-1">Escanea códigos para consultar o cambiar estado de órdenes</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Scanner Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <QrCode className="w-5 h-5" />
              Escáner de Cámara
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Scan Type Selection */}
              <div>
                <Label>Modo de Escaneo</Label>
                <Select value={tipoEscaneo} onValueChange={setTipoEscaneo}>
                  <SelectTrigger data-testid="scan-type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(scanTypes).map(([key, { label, description, color }]) => (
                      <SelectItem key={key} value={key}>
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${color}`} />
                          <div>
                            <p className="font-medium">{label}</p>
                            <p className="text-xs text-muted-foreground">{description}</p>
                          </div>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                
                {/* Indicador de modo actual */}
                <div className={`mt-2 p-2 rounded-lg text-sm ${
                  tipoEscaneo === 'consulta' 
                    ? 'bg-blue-50 text-blue-700 border border-blue-200' 
                    : 'bg-amber-50 text-amber-700 border border-amber-200'
                }`}>
                  {tipoEscaneo === 'consulta' ? (
                    <span className="flex items-center gap-2">
                      <Eye className="w-4 h-4" />
                      Modo consulta: solo verás la información
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <ArrowRight className="w-4 h-4" />
                      Se cambiará el estado al escanear
                    </span>
                  )}
                </div>
              </div>

              {/* Video Preview */}
              <div className="relative aspect-video bg-slate-900 rounded-lg overflow-hidden">
                <video 
                  ref={videoRef}
                  className="w-full h-full object-cover"
                />
                {!scanning && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center text-white">
                      <Camera className="w-16 h-16 mx-auto mb-4 opacity-50" />
                      <p>Presiona "Iniciar" para activar la cámara</p>
                    </div>
                  </div>
                )}
                {processing && (
                  <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                    <div className="text-white text-center">
                      <div className="animate-spin w-8 h-8 border-4 border-white border-t-transparent rounded-full mx-auto mb-2" />
                      <p>Procesando...</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Control Buttons */}
              <div className="flex gap-2">
                {!scanning ? (
                  <Button onClick={startScanning} className="flex-1" data-testid="start-scan-btn">
                    <Camera className="w-4 h-4 mr-2" />
                    Iniciar Cámara
                  </Button>
                ) : (
                  <Button onClick={stopScanning} variant="destructive" className="flex-1" data-testid="stop-scan-btn">
                    <StopCircle className="w-4 h-4 mr-2" />
                    Detener
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Manual Search & Results */}
        <div className="space-y-6">
          {/* Manual Search */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="w-5 h-5" />
                Búsqueda Manual
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleManualSearch} className="space-y-4">
                <div>
                  <Label>Número de Orden o ID</Label>
                  <Input 
                    value={manualId}
                    onChange={(e) => setManualId(e.target.value)}
                    placeholder="Ej: OT-20260208-8AF0080E"
                    className="font-mono"
                    data-testid="manual-id-input"
                  />
                </div>
                <Button type="submit" className="w-full" disabled={processing}>
                  <Search className="w-4 h-4 mr-2" />
                  {tipoEscaneo === 'consulta' ? 'Buscar Orden' : 'Buscar y Procesar'}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Last Scanned Result */}
          {lastScanned && (
            <Card className={lastScanned.success ? (lastScanned.warning ? 'border-amber-500' : 'border-green-500') : 'border-red-500'}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {lastScanned.success ? (
                    lastScanned.warning ? (
                      <Info className="w-5 h-5 text-amber-500" />
                    ) : (
                      <CheckCircle2 className="w-5 h-5 text-green-500" />
                    )
                  ) : (
                    <QrCode className="w-5 h-5 text-red-500" />
                  )}
                  {lastScanned.success ? 'Orden Encontrada' : 'Error'}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {lastScanned.success ? (
                  <div className="space-y-3">
                    {/* Warning si lo hay */}
                    {lastScanned.warning && (
                      <div className="p-2 bg-amber-50 border border-amber-200 rounded text-sm text-amber-700">
                        ⚠️ {lastScanned.warning}
                      </div>
                    )}
                    
                    {/* Info de la orden */}
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Orden:</span>
                      <span className="font-mono font-bold text-lg">{lastScanned.numero_orden}</span>
                    </div>
                    
                    {/* Estado */}
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Estado:</span>
                      {lastScanned.modo === 'cambio_estado' && lastScanned.nuevo_estado ? (
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-muted-foreground line-through">
                            {statusLabels[lastScanned.estado_anterior] || lastScanned.estado_anterior}
                          </Badge>
                          <ArrowRight className="w-4 h-4" />
                          <Badge className={`status-${lastScanned.nuevo_estado}`}>
                            {statusLabels[lastScanned.nuevo_estado] || lastScanned.nuevo_estado}
                          </Badge>
                        </div>
                      ) : (
                        <Badge className={`status-${lastScanned.estado_actual}`}>
                          {statusLabels[lastScanned.estado_actual] || lastScanned.estado_actual}
                        </Badge>
                      )}
                    </div>
                    
                    {/* Dispositivo */}
                    {lastScanned.dispositivo && (
                      <div className="pt-2 border-t">
                        <p className="text-sm text-muted-foreground mb-1">Dispositivo:</p>
                        <p className="font-medium">{lastScanned.dispositivo.modelo}</p>
                        {lastScanned.dispositivo.imei && (
                          <p className="text-xs font-mono text-muted-foreground">IMEI: {lastScanned.dispositivo.imei}</p>
                        )}
                      </div>
                    )}
                    
                    {/* Bloqueada */}
                    {lastScanned.bloqueada && (
                      <div className="p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                        🔒 Esta orden está BLOQUEADA
                      </div>
                    )}
                    
                    <Button 
                      onClick={handleViewOrder} 
                      variant="outline" 
                      className="w-full mt-4"
                      data-testid="view-scanned-order-btn"
                    >
                      <Eye className="w-4 h-4 mr-2" />
                      Ver Detalles Completos
                    </Button>
                  </div>
                ) : (
                  <div className="text-center text-red-500">
                    <p className="font-medium">Error</p>
                    <p className="text-sm">{lastScanned.error}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Instructions */}
          <Card>
            <CardHeader>
              <CardTitle>Modos de Escaneo</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex items-start gap-3 p-2 bg-blue-50 rounded">
                <div className="w-3 h-3 rounded-full bg-blue-500 mt-1" />
                <div>
                  <p className="font-medium text-blue-800">Solo Consulta</p>
                  <p className="text-blue-600">Ver información de cualquier orden sin modificar su estado</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-2 bg-green-50 rounded">
                <div className="w-3 h-3 rounded-full bg-green-500 mt-1" />
                <div>
                  <p className="font-medium text-green-800">Recepción</p>
                  <p className="text-green-600">Cambiar estado a "Recibida" al llegar el paquete</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-2 bg-purple-50 rounded">
                <div className="w-3 h-3 rounded-full bg-purple-500 mt-1" />
                <div>
                  <p className="font-medium text-purple-800">Técnico</p>
                  <p className="text-purple-600">Cambiar estado a "En Taller" al iniciar reparación</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

import { useState, useRef, useEffect } from 'react';
import { 
  FileImage, 
  Camera, 
  Upload, 
  CheckCircle2, 
  X, 
  SwitchCamera,
  Loader2,
  Image
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
} from '@/components/ui/dialog';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import { ordenesAPI, getUploadUrl } from '@/lib/api';
import { toast } from 'sonner';

export function TecnicoFotosCard({ orden, onRefresh }) {
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  
  const [uploading, setUploading] = useState(false);
  const [showImagePreview, setShowImagePreview] = useState(false);
  const [previewImage, setPreviewImage] = useState(null);
  const [showCamera, setShowCamera] = useState(false);
  const [cameraStream, setCameraStream] = useState(null);
  const [facingMode, setFacingMode] = useState('environment');
  const [cameraPhotoType, setCameraPhotoType] = useState('general');

  // Cleanup camera on unmount
  useEffect(() => {
    return () => {
      if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
      }
    };
  }, [cameraStream]);

  const startCamera = async () => {
    try {
      if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
      }
      
      const constraints = {
        video: {
          facingMode: facingMode,
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        },
        audio: false
      };
      
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      setCameraStream(stream);
      setShowCamera(true);
      
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      }, 100);
      
    } catch (error) {
      console.error('Error al acceder a la cámara:', error);
      if (error.name === 'NotAllowedError') {
        toast.error('Permiso de cámara denegado. Por favor habilita el acceso a la cámara.');
      } else if (error.name === 'NotFoundError') {
        toast.error('No se encontró ninguna cámara en el dispositivo.');
      } else {
        toast.error('Error al acceder a la cámara: ' + error.message);
      }
    }
  };

  const stopCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      setCameraStream(null);
    }
    setShowCamera(false);
  };

  const switchCamera = async () => {
    const newMode = facingMode === 'environment' ? 'user' : 'environment';
    setFacingMode(newMode);
    
    if (showCamera) {
      stopCamera();
      setTimeout(() => {
        setFacingMode(newMode);
        startCamera();
      }, 100);
    }
  };

  const capturePhoto = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    canvas.toBlob(async (blob) => {
      if (!blob) {
        toast.error('Error al capturar la foto');
        return;
      }
      
      try {
        setUploading(true);
        const file = new File([blob], `foto_${Date.now()}.jpg`, { type: 'image/jpeg' });
        await ordenesAPI.subirEvidenciaTecnico(orden.id, file, cameraPhotoType);
        toast.success(`Foto ${cameraPhotoType !== 'general' ? `(${cameraPhotoType})` : ''} capturada y subida`);
        onRefresh();
      } catch (error) {
        console.error('Error al subir foto:', error);
        toast.error('Error al subir la foto capturada');
      } finally {
        setUploading(false);
      }
    }, 'image/jpeg', 0.85);
  };

  const startCameraWithType = (tipo) => {
    setCameraPhotoType(tipo);
    startCamera();
  };

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    try {
      setUploading(true);
      let successCount = 0;
      for (const file of files) {
        try {
          await ordenesAPI.subirEvidenciaTecnico(orden.id, file);
          successCount++;
        } catch (err) {
          console.error('Error subiendo archivo:', err);
        }
      }
      if (successCount > 0) {
        toast.success(`${successCount} foto${successCount > 1 ? 's' : ''} subida${successCount > 1 ? 's' : ''} correctamente`);
        onRefresh();
      }
    } catch (error) {
      toast.error('Error al subir las fotos');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleFileUploadWithType = async (e, tipo) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    try {
      setUploading(true);
      let successCount = 0;
      for (const file of files) {
        try {
          await ordenesAPI.subirEvidenciaTecnico(orden.id, file, tipo);
          successCount++;
        } catch (err) {
          console.error('Error subiendo archivo:', err);
        }
      }
      if (successCount > 0) {
        toast.success(`${successCount} foto${successCount > 1 ? 's' : ''} "${tipo}" subida${successCount > 1 ? 's' : ''} correctamente`);
        onRefresh();
      }
    } catch (error) {
      toast.error('Error al subir las fotos');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const openPreview = (imageUrl) => {
    setPreviewImage(imageUrl);
    setShowImagePreview(true);
  };

  const todasLasFotos = [
    ...(orden.evidencias || []).map(f => ({ src: getUploadUrl(f), tipo: 'admin' })),
    ...(orden.evidencias_tecnico || []).map(f => ({ src: getUploadUrl(f), tipo: 'tecnico' }))
  ];

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileImage className="w-5 h-5" />
            Fotos del Dispositivo
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="antes" className="w-full">
            <TabsList className="grid w-full grid-cols-3 mb-4">
              <TabsTrigger value="antes" className="gap-2">
                📷 ANTES
                <Badge variant="outline" className="text-xs">
                  {(orden.fotos_antes || []).length}
                </Badge>
              </TabsTrigger>
              <TabsTrigger value="despues" className="gap-2">
                ✅ DESPUÉS
                <Badge variant="outline" className="text-xs">
                  {(orden.fotos_despues || []).length}
                </Badge>
              </TabsTrigger>
              <TabsTrigger value="general" className="gap-2">
                📁 General
                <Badge variant="outline" className="text-xs">
                  {(orden.evidencias_tecnico || []).length}
                </Badge>
              </TabsTrigger>
            </TabsList>

            {/* Tab ANTES */}
            <TabsContent value="antes">
              <div className="space-y-4">
                <div className="flex justify-between items-center p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <div>
                    <p className="font-medium text-amber-800">📷 Fotos del estado ANTES</p>
                    <p className="text-sm text-amber-600">Documenta el estado inicial</p>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="file"
                      id="file-antes"
                      onChange={(e) => handleFileUploadWithType(e, 'antes')}
                      accept="image/*"
                      className="hidden"
                    />
                    <Button 
                      variant="outline"
                      onClick={() => startCameraWithType('antes')}
                      disabled={uploading}
                      size="sm"
                    >
                      <Camera className="w-4 h-4 mr-1" />
                      Cámara
                    </Button>
                    <Button 
                      variant="outline"
                      onClick={() => document.getElementById('file-antes')?.click()}
                      disabled={uploading}
                      size="sm"
                    >
                      <Upload className="w-4 h-4 mr-1" />
                      Galería
                    </Button>
                  </div>
                </div>
                {(orden.fotos_antes || []).length === 0 ? (
                  <div className="text-center py-6 text-muted-foreground border-2 border-dashed rounded-lg">
                    <Camera className="w-10 h-10 mx-auto mb-2 opacity-50" />
                    <p>Sin fotos del estado inicial</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-3 gap-3">
                    {(orden.fotos_antes || []).map((foto, index) => (
                      <div 
                        key={index}
                        className="relative aspect-square rounded-lg border-2 border-amber-200 overflow-hidden cursor-pointer hover:opacity-90"
                        onClick={() => openPreview(`${getUploadUrl(foto)}`)}
                      >
                        <img
                          src={getUploadUrl(foto)}
                          alt={`Antes ${index + 1}`}
                          className="w-full h-full object-cover"
                        />
                        <Badge className="absolute top-1 left-1 bg-amber-500 text-xs">ANTES</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Tab DESPUÉS */}
            <TabsContent value="despues">
              <div className="space-y-4">
                <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg border border-green-200">
                  <div>
                    <p className="font-medium text-green-800">✅ Fotos del estado DESPUÉS</p>
                    <p className="text-sm text-green-600">Documenta el resultado</p>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="file"
                      id="file-despues"
                      onChange={(e) => handleFileUploadWithType(e, 'despues')}
                      accept="image/*"
                      className="hidden"
                    />
                    <Button 
                      variant="outline"
                      onClick={() => startCameraWithType('despues')}
                      disabled={uploading}
                      size="sm"
                    >
                      <Camera className="w-4 h-4 mr-1" />
                      Cámara
                    </Button>
                    <Button 
                      variant="outline"
                      onClick={() => document.getElementById('file-despues')?.click()}
                      disabled={uploading}
                      size="sm"
                    >
                      <Upload className="w-4 h-4 mr-1" />
                      Galería
                    </Button>
                  </div>
                </div>
                {(orden.fotos_despues || []).length === 0 ? (
                  <div className="text-center py-6 text-muted-foreground border-2 border-dashed rounded-lg">
                    <CheckCircle2 className="w-10 h-10 mx-auto mb-2 opacity-50" />
                    <p>Sin fotos del resultado</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-3 gap-3">
                    {(orden.fotos_despues || []).map((foto, index) => (
                      <div 
                        key={index}
                        className="relative aspect-square rounded-lg border-2 border-green-200 overflow-hidden cursor-pointer hover:opacity-90"
                        onClick={() => openPreview(`${getUploadUrl(foto)}`)}
                      >
                        <img
                          src={getUploadUrl(foto)}
                          alt={`Después ${index + 1}`}
                          className="w-full h-full object-cover"
                        />
                        <Badge className="absolute top-1 left-1 bg-green-500 text-xs">DESPUÉS</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Tab General */}
            <TabsContent value="general">
              <div className="space-y-4">
                <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg border">
                  <div>
                    <p className="font-medium">📁 Otras fotos y evidencias</p>
                    <p className="text-sm text-muted-foreground">Fotos adicionales</p>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileUpload}
                      accept="image/*"
                      className="hidden"
                    />
                    <Button 
                      variant="outline"
                      onClick={() => startCameraWithType('general')}
                      disabled={uploading}
                      size="sm"
                    >
                      <Camera className="w-4 h-4 mr-1" />
                      Cámara
                    </Button>
                    <Button 
                      variant="outline"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploading}
                      size="sm"
                    >
                      <Upload className="w-4 h-4 mr-1" />
                      Galería
                    </Button>
                  </div>
                </div>
                {todasLasFotos.length === 0 ? (
                  <div className="text-center py-6 text-muted-foreground border-2 border-dashed rounded-lg">
                    <Image className="w-10 h-10 mx-auto mb-2 opacity-50" />
                    <p>Sin fotos adicionales</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-3 gap-3">
                    {todasLasFotos.map((foto, index) => (
                      <div 
                        key={index}
                        className="relative aspect-square rounded-lg border overflow-hidden cursor-pointer hover:opacity-90"
                        onClick={() => openPreview(foto.src)}
                      >
                        <img
                          src={foto.src}
                          alt={`Foto ${index + 1}`}
                          className="w-full h-full object-cover"
                        />
                        <Badge 
                          className="absolute bottom-1 left-1 text-[10px]"
                          variant={foto.tipo === 'admin' ? 'default' : 'secondary'}
                        >
                          {foto.tipo === 'admin' ? 'Admin' : 'Técnico'}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Image Preview Dialog */}
      <Dialog open={showImagePreview} onOpenChange={setShowImagePreview}>
        <DialogContent className="max-w-3xl p-2">
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-2 top-2 z-10"
            onClick={() => setShowImagePreview(false)}
          >
            <X className="w-4 h-4" />
          </Button>
          {previewImage && (
            <img
              src={previewImage}
              alt="Preview"
              className="w-full h-auto rounded-lg"
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Camera Dialog */}
      <Dialog open={showCamera} onOpenChange={(open) => {
        if (!open) stopCamera();
        setShowCamera(open);
      }}>
        <DialogContent className="max-w-2xl p-0 overflow-hidden">
          <div className="relative bg-black">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-auto min-h-[300px] max-h-[60vh] object-cover"
            />
            
            <canvas ref={canvasRef} className="hidden" />
            
            <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 to-transparent">
              <div className="flex items-center justify-center gap-6">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={switchCamera}
                  className="h-12 w-12 rounded-full bg-white/20 border-white/40 hover:bg-white/30"
                >
                  <SwitchCamera className="w-5 h-5 text-white" />
                </Button>
                
                <Button
                  onClick={capturePhoto}
                  disabled={uploading}
                  className="h-16 w-16 rounded-full bg-white hover:bg-gray-100 border-4 border-white shadow-lg"
                  data-testid="btn-capturar-foto"
                >
                  {uploading ? (
                    <Loader2 className="w-6 h-6 text-gray-800 animate-spin" />
                  ) : (
                    <Camera className="w-6 h-6 text-gray-800" />
                  )}
                </Button>
                
                <Button
                  variant="outline"
                  size="icon"
                  onClick={stopCamera}
                  className="h-12 w-12 rounded-full bg-white/20 border-white/40 hover:bg-white/30"
                >
                  <X className="w-5 h-5 text-white" />
                </Button>
              </div>
            </div>
            
            <div className="absolute top-4 left-4 flex items-center gap-2 px-3 py-1 rounded-full bg-red-500/80 text-white text-sm">
              <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
              Cámara {facingMode === 'user' ? 'Frontal' : 'Trasera'}
            </div>
          </div>
          
          <div className="p-4 bg-slate-900 text-white text-center text-sm">
            <p>Pulsa el botón central para capturar la foto</p>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

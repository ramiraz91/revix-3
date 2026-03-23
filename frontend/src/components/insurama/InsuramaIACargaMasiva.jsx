import { useState, useRef } from 'react';
import {
  Brain,
  Upload,
  FileImage,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Package,
  Euro,
  RefreshCw,
  Download
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import api from '@/lib/api';

export default function InsuramaIACargaMasiva() {
  const [archivo, setArchivo] = useState(null);
  const [preview, setPreview] = useState(null);
  const [extrayendo, setExtrayendo] = useState(false);
  const [codigosExtraidos, setCodigosExtraidos] = useState([]);
  const [codigosSeleccionados, setCodigosSeleccionados] = useState(new Set());
  const [importando, setImportando] = useState(false);
  const [resultadoImportacion, setResultadoImportacion] = useState(null);
  const [mensajeIA, setMensajeIA] = useState(null);
  
  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validar que sea imagen
    if (!file.type.startsWith('image/')) {
      toast.error('Por favor selecciona una imagen (PNG, JPG, WEBP)');
      return;
    }

    setArchivo(file);
    setCodigosExtraidos([]);
    setCodigosSeleccionados(new Set());
    setResultadoImportacion(null);
    setMensajeIA(null);

    // Crear preview
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(file);
  };

  const handleExtraerCodigos = async () => {
    if (!archivo) {
      toast.error('Selecciona una imagen primero');
      return;
    }

    setExtrayendo(true);
    setCodigosExtraidos([]);
    setMensajeIA(null);

    try {
      const formData = new FormData();
      formData.append('file', archivo);

      const response = await api.post('/insurama/ia/extraer-codigos', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const data = response.data;
      setCodigosExtraidos(data.codigos || []);
      setMensajeIA(data.mensaje);
      
      // Seleccionar todos por defecto
      const nuevaSeleccion = new Set(data.codigos.map(c => c.codigo));
      setCodigosSeleccionados(nuevaSeleccion);

      if (data.codigos.length > 0) {
        toast.success(`Se encontraron ${data.codigos.length} códigos con estado ACEPTADO`);
      } else {
        toast.warning('No se encontraron códigos 25BE/26BE con estado aceptado en la imagen');
      }

    } catch (error) {
      console.error('Error extrayendo códigos:', error);
      toast.error(error.response?.data?.detail || 'Error al procesar la imagen');
    } finally {
      setExtrayendo(false);
    }
  };

  const handleToggleSeleccion = (codigo) => {
    const nueva = new Set(codigosSeleccionados);
    if (nueva.has(codigo)) {
      nueva.delete(codigo);
    } else {
      nueva.add(codigo);
    }
    setCodigosSeleccionados(nueva);
  };

  const handleSeleccionarTodos = () => {
    if (codigosSeleccionados.size === codigosExtraidos.length) {
      setCodigosSeleccionados(new Set());
    } else {
      setCodigosSeleccionados(new Set(codigosExtraidos.map(c => c.codigo)));
    }
  };

  const handleImportar = async () => {
    const codigosAImportar = codigosExtraidos.filter(c => codigosSeleccionados.has(c.codigo));
    
    if (codigosAImportar.length === 0) {
      toast.error('Selecciona al menos un código para importar');
      return;
    }

    setImportando(true);
    setResultadoImportacion(null);

    try {
      const response = await api.post('/insurama/ia/importar-codigos', {
        codigos: codigosAImportar
      });

      setResultadoImportacion(response.data);
      
      if (response.data.creados > 0 || response.data.actualizados > 0) {
        toast.success(`Importación completada: ${response.data.creados} creados, ${response.data.actualizados} actualizados`);
      }
      if (response.data.errores > 0) {
        toast.warning(`${response.data.errores} códigos con errores`);
      }

    } catch (error) {
      console.error('Error importando:', error);
      toast.error(error.response?.data?.detail || 'Error al importar códigos');
    } finally {
      setImportando(false);
    }
  };

  const handleLimpiar = () => {
    setArchivo(null);
    setPreview(null);
    setCodigosExtraidos([]);
    setCodigosSeleccionados(new Set());
    setResultadoImportacion(null);
    setMensajeIA(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const totalSeleccionado = codigosExtraidos
    .filter(c => codigosSeleccionados.has(c.codigo))
    .reduce((acc, c) => acc + (c.cantidad || 0), 0);

  return (
    <div className="space-y-6" data-testid="insurama-ia-carga-masiva">
      {/* Header */}
      <Card className="border-purple-200 bg-gradient-to-r from-purple-50 to-indigo-50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-purple-700">
            <Brain className="w-6 h-6" />
            Carga Masiva con IA
          </CardTitle>
          <CardDescription>
            Sube una captura de pantalla y la IA extraerá automáticamente los códigos de servicio (25BE*, 26BE*) con estado ACEPTADO.
            Se creará una partida de materiales por cada código importado.
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Área de carga */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Selector de imagen */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <FileImage className="w-5 h-5" />
              Captura de Pantalla
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
              data-testid="ia-file-input"
            />
            
            {!preview ? (
              <div 
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center cursor-pointer hover:border-purple-400 hover:bg-purple-50/50 transition-all"
              >
                <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 font-medium">Click para seleccionar imagen</p>
                <p className="text-sm text-muted-foreground mt-1">PNG, JPG o WEBP</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="relative border rounded-lg overflow-hidden">
                  <img 
                    src={preview} 
                    alt="Preview" 
                    className="w-full h-auto max-h-[400px] object-contain bg-gray-100"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">
                    {archivo?.name}
                  </div>
                  <Button variant="outline" size="sm" onClick={handleLimpiar}>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Cambiar
                  </Button>
                </div>
              </div>
            )}

            <Button 
              onClick={handleExtraerCodigos} 
              disabled={!archivo || extrayendo}
              className="w-full bg-purple-600 hover:bg-purple-700"
              data-testid="btn-extraer-codigos"
            >
              {extrayendo ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Analizando imagen con IA...
                </>
              ) : (
                <>
                  <Brain className="w-4 h-4 mr-2" />
                  Extraer Códigos con IA
                </>
              )}
            </Button>

            {extrayendo && (
              <div className="space-y-2">
                <Progress value={undefined} className="h-2" />
                <p className="text-sm text-center text-muted-foreground">
                  La IA está analizando la imagen...
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Resultado de extracción */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <Package className="w-5 h-5" />
                Códigos Extraídos
              </CardTitle>
              {codigosExtraidos.length > 0 && (
                <Badge variant="secondary" className="text-purple-700">
                  {codigosSeleccionados.size} de {codigosExtraidos.length} seleccionados
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {codigosExtraidos.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Brain className="w-12 h-12 mx-auto text-gray-300 mb-4" />
                <p>Los códigos extraídos aparecerán aquí</p>
                {mensajeIA && (
                  <p className="text-sm mt-2 text-amber-600">{mensajeIA}</p>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                {mensajeIA && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700">
                    <AlertTriangle className="w-4 h-4 inline mr-2" />
                    {mensajeIA}
                  </div>
                )}

                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12">
                          <Checkbox 
                            checked={codigosSeleccionados.size === codigosExtraidos.length}
                            onCheckedChange={handleSeleccionarTodos}
                          />
                        </TableHead>
                        <TableHead>Código</TableHead>
                        <TableHead>Cantidad</TableHead>
                        <TableHead>Estado</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {codigosExtraidos.map((item) => (
                        <TableRow 
                          key={item.codigo}
                          className={codigosSeleccionados.has(item.codigo) ? 'bg-purple-50' : ''}
                        >
                          <TableCell>
                            <Checkbox 
                              checked={codigosSeleccionados.has(item.codigo)}
                              onCheckedChange={() => handleToggleSeleccion(item.codigo)}
                            />
                          </TableCell>
                          <TableCell className="font-mono font-medium">
                            {item.codigo}
                          </TableCell>
                          <TableCell>
                            <span className="font-semibold text-green-600">
                              {item.cantidad?.toFixed(2)}€
                            </span>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                              {item.estado}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Resumen */}
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <p className="text-sm text-muted-foreground">Total seleccionado</p>
                    <p className="text-2xl font-bold text-green-600">
                      {totalSeleccionado.toFixed(2)}€
                    </p>
                  </div>
                  <Button 
                    onClick={handleImportar}
                    disabled={codigosSeleccionados.size === 0 || importando}
                    className="bg-green-600 hover:bg-green-700"
                    data-testid="btn-importar-codigos"
                  >
                    {importando ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Importando...
                      </>
                    ) : (
                      <>
                        <Download className="w-4 h-4 mr-2" />
                        Importar {codigosSeleccionados.size} códigos
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Resultado de importación */}
      {resultadoImportacion && (
        <Card className="border-green-200 bg-green-50/50" data-testid="resultado-importacion">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2 text-green-700">
              <CheckCircle2 className="w-5 h-5" />
              Resultado de Importación
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-4 mb-4">
              <div className="text-center p-4 bg-white rounded-lg border">
                <p className="text-2xl font-bold text-slate-700">
                  {resultadoImportacion.total_procesados}
                </p>
                <p className="text-xs text-muted-foreground">Total procesados</p>
              </div>
              <div className="text-center p-4 bg-white rounded-lg border border-green-200">
                <p className="text-2xl font-bold text-green-600">
                  {resultadoImportacion.creados}
                </p>
                <p className="text-xs text-muted-foreground">Creados</p>
              </div>
              <div className="text-center p-4 bg-white rounded-lg border border-blue-200">
                <p className="text-2xl font-bold text-blue-600">
                  {resultadoImportacion.actualizados}
                </p>
                <p className="text-xs text-muted-foreground">Actualizados</p>
              </div>
              <div className="text-center p-4 bg-white rounded-lg border border-red-200">
                <p className="text-2xl font-bold text-red-600">
                  {resultadoImportacion.errores}
                </p>
                <p className="text-xs text-muted-foreground">Errores</p>
              </div>
            </div>

            {resultadoImportacion.detalles?.length > 0 && (
              <div className="max-h-48 overflow-y-auto space-y-1 text-sm">
                {resultadoImportacion.detalles.map((d, i) => (
                  <div 
                    key={i} 
                    className={`flex items-center gap-2 p-2 rounded ${
                      d.status === 'creado' ? 'bg-green-100' : 
                      d.status === 'actualizado' ? 'bg-blue-100' : 'bg-red-100'
                    }`}
                  >
                    {d.status === 'creado' ? (
                      <CheckCircle2 className="w-4 h-4 text-green-600" />
                    ) : d.status === 'actualizado' ? (
                      <RefreshCw className="w-4 h-4 text-blue-600" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-600" />
                    )}
                    <span className="font-mono">{d.codigo}</span>
                    <span className="text-muted-foreground">-</span>
                    <span className="truncate">{d.mensaje}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

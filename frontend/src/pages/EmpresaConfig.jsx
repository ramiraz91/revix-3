import { useState, useEffect, useRef } from 'react';
import { 
  Building2, 
  Save, 
  Loader2,
  Phone,
  Mail,
  Globe,
  MapPin,
  Percent,
  Plus,
  Trash2,
  Upload,
  Image,
  FileText,
  Scale,
  AlertTriangle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { empresaAPI, getUploadUrl } from '@/lib/api';

export default function EmpresaConfig() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const fileInputRef = useRef(null);
  
  const [config, setConfig] = useState({
    nombre: '',
    cif: '',
    direccion: '',
    ciudad: '',
    codigo_postal: '',
    telefono: '',
    email: '',
    web: '',
    logo: {
      url: '',
      ancho_web: 200,
      alto_web: 60,
      ancho_pdf: 150,
      alto_pdf: 45
    },
    logo_url: '',
    textos_legales: {
      aceptacion_seguimiento: 'Al acceder a este portal de seguimiento, el cliente acepta que [NOMBRE_EMPRESA] no se hace responsable de los daños externos que pueda presentar el dispositivo, tales como arañazos, abolladuras o defectos cosméticos preexistentes. La responsabilidad de la empresa se limita exclusivamente a la reparación contratada. El cliente declara haber entregado el dispositivo en el estado actual y acepta las condiciones del servicio.',
      clausulas_documentos: 'Garantía de reparación: 3 meses desde la fecha de entrega. La garantía cubre únicamente la avería reparada. Quedan excluidos de la garantía los daños por mal uso, golpes, líquidos o manipulación por terceros.',
      politica_privacidad: 'Sus datos personales serán tratados conforme al RGPD. Para más información, consulte nuestra política de privacidad completa.',
      titulo_aceptacion: 'Condiciones del Servicio'
    },
    tipos_iva: [
      { nombre: 'General', porcentaje: 21, activo: true },
      { nombre: 'Reducido', porcentaje: 10, activo: true },
      { nombre: 'Superreducido', porcentaje: 4, activo: true },
      { nombre: 'Exento', porcentaje: 0, activo: true }
    ],
    iva_por_defecto: 21
  });

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const response = await empresaAPI.obtener();
      if (response.data) {
        setConfig(prev => ({ 
          ...prev, 
          ...response.data,
          logo: response.data.logo || prev.logo,
          textos_legales: response.data.textos_legales || prev.textos_legales
        }));
      }
    } catch (error) {
      console.error('Error fetching config:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setConfig(prev => ({ ...prev, [field]: value }));
  };

  const handleLogoChange = (field, value) => {
    setConfig(prev => ({
      ...prev,
      logo: { ...prev.logo, [field]: value }
    }));
  };

  const handleTextosLegalesChange = (field, value) => {
    setConfig(prev => ({
      ...prev,
      textos_legales: { ...prev.textos_legales, [field]: value }
    }));
  };

  const handleIVAChange = (index, field, value) => {
    setConfig(prev => {
      const newTipos = [...prev.tipos_iva];
      newTipos[index] = { ...newTipos[index], [field]: value };
      return { ...prev, tipos_iva: newTipos };
    });
  };

  const addTipoIVA = () => {
    setConfig(prev => ({
      ...prev,
      tipos_iva: [...prev.tipos_iva, { nombre: '', porcentaje: 0, activo: true }]
    }));
  };

  const removeTipoIVA = (index) => {
    setConfig(prev => ({
      ...prev,
      tipos_iva: prev.tipos_iva.filter((_, i) => i !== index)
    }));
  };

  const handleLogoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validar tipo
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/svg+xml'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Formato no soportado. Use PNG, JPEG, WebP o SVG.');
      return;
    }

    // Validar tamaño (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('El archivo es demasiado grande. Máximo 5MB.');
      return;
    }

    setUploadingLogo(true);
    try {
      const response = await empresaAPI.subirLogo(file);
      const fileName = response.data.file_name;
      
      setConfig(prev => ({
        ...prev,
        logo: { ...prev.logo, url: fileName },
        logo_url: fileName
      }));
      
      toast.success('Logo subido correctamente');
    } catch (error) {
      toast.error('Error al subir el logo');
    } finally {
      setUploadingLogo(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await empresaAPI.guardar(config);
      toast.success('Configuración guardada correctamente');
    } catch (error) {
      toast.error('Error al guardar la configuración');
    } finally {
      setSaving(false);
    }
  };

  // Reemplazar placeholder en texto legal
  const getPreviewText = (text) => {
    return text.replace('[NOMBRE_EMPRESA]', config.nombre || 'Mi Empresa');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const logoUrl = config.logo?.url || config.logo_url;

  return (
    <div className="space-y-6 animate-fade-in" data-testid="empresa-config-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Building2 className="w-8 h-8" />
          Configuración de Empresa
        </h1>
        <p className="text-muted-foreground mt-1">
          Datos de la empresa para facturas, informes y documentos
        </p>
      </div>

      <Tabs defaultValue="general" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="logo">Logo</TabsTrigger>
          <TabsTrigger value="legal">Legal</TabsTrigger>
          <TabsTrigger value="iva">IVA</TabsTrigger>
        </TabsList>

        {/* TAB: Datos Generales */}
        <TabsContent value="general" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Datos Generales</CardTitle>
              <CardDescription>Información básica de la empresa</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <Label htmlFor="nombre">Nombre de la Empresa *</Label>
                  <Input
                    id="nombre"
                    value={config.nombre}
                    onChange={(e) => handleChange('nombre', e.target.value)}
                    placeholder="Mi Empresa S.L."
                    data-testid="empresa-nombre-input"
                  />
                </div>
                <div>
                  <Label htmlFor="cif">CIF / NIF</Label>
                  <Input
                    id="cif"
                    value={config.cif}
                    onChange={(e) => handleChange('cif', e.target.value)}
                    placeholder="B12345678"
                  />
                </div>
                <div>
                  <Label htmlFor="telefono">Teléfono</Label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="telefono"
                      value={config.telefono}
                      onChange={(e) => handleChange('telefono', e.target.value)}
                      placeholder="+34 912 345 678"
                      className="pl-10"
                    />
                  </div>
                </div>
                <div>
                  <Label htmlFor="email">Email</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="email"
                      type="email"
                      value={config.email}
                      onChange={(e) => handleChange('email', e.target.value)}
                      placeholder="info@empresa.com"
                      className="pl-10"
                    />
                  </div>
                </div>
                <div>
                  <Label htmlFor="web">Página Web</Label>
                  <div className="relative">
                    <Globe className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="web"
                      value={config.web}
                      onChange={(e) => handleChange('web', e.target.value)}
                      placeholder="https://www.empresa.com"
                      className="pl-10"
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="w-5 h-5" />
                Dirección
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <Label htmlFor="direccion">Dirección</Label>
                  <Input
                    id="direccion"
                    value={config.direccion}
                    onChange={(e) => handleChange('direccion', e.target.value)}
                    placeholder="Calle Principal, 123"
                  />
                </div>
                <div>
                  <Label htmlFor="ciudad">Ciudad</Label>
                  <Input
                    id="ciudad"
                    value={config.ciudad}
                    onChange={(e) => handleChange('ciudad', e.target.value)}
                    placeholder="Madrid"
                  />
                </div>
                <div>
                  <Label htmlFor="codigo_postal">Código Postal</Label>
                  <Input
                    id="codigo_postal"
                    value={config.codigo_postal}
                    onChange={(e) => handleChange('codigo_postal', e.target.value)}
                    placeholder="28001"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB: Logo */}
        <TabsContent value="logo" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Image className="w-5 h-5" />
                Logo de la Empresa
              </CardTitle>
              <CardDescription>
                Sube el logo de tu empresa. Se usará en la web y en los documentos PDF generados.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Upload Area */}
              <div className="flex flex-col items-center gap-4">
                {logoUrl ? (
                  <div className="p-4 border rounded-lg bg-slate-50">
                    <img 
                      src={getUploadUrl(logoUrl)} 
                      alt="Logo de la empresa"
                      className="max-h-32 object-contain"
                      style={{ 
                        maxWidth: config.logo?.ancho_web || 200,
                        maxHeight: config.logo?.alto_web || 60
                      }}
                    />
                  </div>
                ) : (
                  <div className="w-full max-w-md p-8 border-2 border-dashed rounded-lg bg-slate-50 flex flex-col items-center gap-2">
                    <Image className="w-12 h-12 text-slate-300" />
                    <p className="text-sm text-muted-foreground">No hay logo configurado</p>
                  </div>
                )}
                
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleLogoUpload}
                  accept="image/png,image/jpeg,image/jpg,image/webp,image/svg+xml"
                  className="hidden"
                />
                
                <Button 
                  variant="outline" 
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadingLogo}
                  data-testid="upload-logo-btn"
                >
                  {uploadingLogo ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Upload className="w-4 h-4 mr-2" />
                  )}
                  {logoUrl ? 'Cambiar Logo' : 'Subir Logo'}
                </Button>
                
                <p className="text-xs text-muted-foreground text-center">
                  Formatos: PNG, JPEG, WebP, SVG • Máximo 5MB<br/>
                  Recomendado: fondo transparente (PNG/SVG)
                </p>
              </div>

              <Separator />

              {/* Medidas */}
              <div className="space-y-4">
                <h4 className="font-medium flex items-center gap-2">
                  <Scale className="w-4 h-4" />
                  Medidas del Logo
                </h4>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Web */}
                  <div className="p-4 bg-blue-50 rounded-lg space-y-3">
                    <p className="font-medium text-blue-800 text-sm">Para la Web</p>
                    <p className="text-xs text-blue-600">Header, portal de seguimiento, etc.</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs">Ancho (px)</Label>
                        <Input
                          type="number"
                          value={config.logo?.ancho_web || 200}
                          onChange={(e) => handleLogoChange('ancho_web', parseInt(e.target.value) || 200)}
                          min={50}
                          max={500}
                        />
                      </div>
                      <div>
                        <Label className="text-xs">Alto (px)</Label>
                        <Input
                          type="number"
                          value={config.logo?.alto_web || 60}
                          onChange={(e) => handleLogoChange('alto_web', parseInt(e.target.value) || 60)}
                          min={20}
                          max={200}
                        />
                      </div>
                    </div>
                  </div>

                  {/* PDF */}
                  <div className="p-4 bg-amber-50 rounded-lg space-y-3">
                    <p className="font-medium text-amber-800 text-sm">Para PDFs / Documentos</p>
                    <p className="text-xs text-amber-600">Facturas, presupuestos, informes</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs">Ancho (px)</Label>
                        <Input
                          type="number"
                          value={config.logo?.ancho_pdf || 150}
                          onChange={(e) => handleLogoChange('ancho_pdf', parseInt(e.target.value) || 150)}
                          min={50}
                          max={400}
                        />
                      </div>
                      <div>
                        <Label className="text-xs">Alto (px)</Label>
                        <Input
                          type="number"
                          value={config.logo?.alto_pdf || 45}
                          onChange={(e) => handleLogoChange('alto_pdf', parseInt(e.target.value) || 45)}
                          min={20}
                          max={150}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB: Textos Legales */}
        <TabsContent value="legal" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                Aceptación del Portal de Seguimiento
              </CardTitle>
              <CardDescription>
                Este texto se mostrará al cliente ANTES de poder ver el estado de su reparación. 
                El cliente deberá aceptar las condiciones para continuar.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Título del Modal</Label>
                <Input
                  value={config.textos_legales?.titulo_aceptacion || ''}
                  onChange={(e) => handleTextosLegalesChange('titulo_aceptacion', e.target.value)}
                  placeholder="Condiciones del Servicio"
                  data-testid="titulo-aceptacion-input"
                />
              </div>
              <div>
                <Label>Texto de Aceptación *</Label>
                <Textarea
                  value={config.textos_legales?.aceptacion_seguimiento || ''}
                  onChange={(e) => handleTextosLegalesChange('aceptacion_seguimiento', e.target.value)}
                  placeholder="Escribe aquí el texto legal que el cliente debe aceptar..."
                  rows={6}
                  className="font-mono text-sm"
                  data-testid="texto-aceptacion-input"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Usa [NOMBRE_EMPRESA] para insertar automáticamente el nombre de tu empresa.
                </p>
              </div>
              
              {/* Vista previa */}
              <div className="p-4 bg-slate-50 rounded-lg border">
                <p className="text-xs text-muted-foreground mb-2 font-medium">Vista previa:</p>
                <p className="text-sm">{getPreviewText(config.textos_legales?.aceptacion_seguimiento || '')}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Cláusulas para Documentos
              </CardTitle>
              <CardDescription>
                Este texto aparecerá en facturas, presupuestos y otros documentos generados.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Cláusulas Legales</Label>
                <Textarea
                  value={config.textos_legales?.clausulas_documentos || ''}
                  onChange={(e) => handleTextosLegalesChange('clausulas_documentos', e.target.value)}
                  placeholder="Garantía de reparación: 3 meses desde la fecha de entrega..."
                  rows={4}
                  className="font-mono text-sm"
                  data-testid="clausulas-documentos-input"
                />
              </div>
              <div>
                <Label>Política de Privacidad (resumen)</Label>
                <Textarea
                  value={config.textos_legales?.politica_privacidad || ''}
                  onChange={(e) => handleTextosLegalesChange('politica_privacidad', e.target.value)}
                  placeholder="Sus datos personales serán tratados conforme al RGPD..."
                  rows={2}
                  className="font-mono text-sm"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB: IVA */}
        <TabsContent value="iva" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Percent className="w-5 h-5" />
                Tipos de IVA
              </CardTitle>
              <CardDescription>Configura los tipos de IVA aplicables a los servicios</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {config.tipos_iva.map((tipo, index) => (
                <div key={index} className="flex items-center gap-4 p-3 bg-slate-50 rounded-lg">
                  <div className="flex-1 grid grid-cols-3 gap-3">
                    <Input
                      value={tipo.nombre}
                      onChange={(e) => handleIVAChange(index, 'nombre', e.target.value)}
                      placeholder="Nombre del tipo"
                    />
                    <div className="relative">
                      <Input
                        type="number"
                        value={tipo.porcentaje}
                        onChange={(e) => handleIVAChange(index, 'porcentaje', parseFloat(e.target.value) || 0)}
                        placeholder="0"
                        className="pr-8"
                      />
                      <span className="absolute right-3 top-2.5 text-muted-foreground">%</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={tipo.activo}
                        onCheckedChange={(checked) => handleIVAChange(index, 'activo', checked)}
                      />
                      <span className="text-sm text-muted-foreground">
                        {tipo.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </div>
                  </div>
                  {config.tipos_iva.length > 1 && (
                    <Button 
                      variant="ghost" 
                      size="icon"
                      onClick={() => removeTipoIVA(index)}
                      className="text-red-500 hover:text-red-600 hover:bg-red-50"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
              
              <Button variant="outline" onClick={addTipoIVA} className="w-full">
                <Plus className="w-4 h-4 mr-2" />
                Añadir Tipo de IVA
              </Button>

              <Separator />

              <div className="flex items-center justify-between">
                <Label>IVA por defecto</Label>
                <select
                  value={config.iva_por_defecto}
                  onChange={(e) => handleChange('iva_por_defecto', parseFloat(e.target.value))}
                  className="px-3 py-2 border rounded-md"
                >
                  {config.tipos_iva.filter(t => t.activo).map((tipo, index) => (
                    <option key={index} value={tipo.porcentaje}>
                      {tipo.nombre} ({tipo.porcentaje}%)
                    </option>
                  ))}
                </select>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={saving} size="lg" className="gap-2" data-testid="guardar-config-btn">
          {saving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          Guardar Configuración
        </Button>
      </div>
    </div>
  );
}

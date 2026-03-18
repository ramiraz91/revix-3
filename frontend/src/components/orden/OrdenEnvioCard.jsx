import { Truck, Pencil, Save, X, Package, Send, MapPin, Phone, User, ExternalLink, ArrowDown, ArrowUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';

const ESTADO_BADGE = {
  grabado: 'bg-blue-100 text-blue-800',
  en_transito: 'bg-amber-100 text-amber-800',
  en_reparto: 'bg-purple-100 text-purple-800',
  entregado: 'bg-green-100 text-green-800',
  devuelto: 'bg-red-100 text-red-800',
  incidencia: 'bg-orange-100 text-orange-800',
  anulado: 'bg-gray-100 text-gray-600',
  error: 'bg-red-100 text-red-800',
};

export function OrdenEnvioCard({ 
  orden, 
  isAdmin, 
  editingEnvio, 
  envioData, 
  setEnvioData,
  onEditEnvio, 
  onGuardarEnvio, 
  onCancelEdit,
  guardandoEnvio,
  onGenerarRecogida,
  onGenerarEnvio
}) {
  const puedeGenerarRecogida = isAdmin && !orden.codigo_recogida_entrada;
  const estadosParaEnvio = ['reparado', 'validacion', 'enviado'];
  const puedeGenerarEnvio = isAdmin && estadosParaEnvio.includes(orden.estado) && !orden.codigo_recogida_salida && !orden.codigo_envio;
  const datosRecogida = orden.datos_recogida;
  const datosEnvio = orden.datos_envio;
  const glsEnvios = orden.gls_envios || [];
  const esGLS = orden.agencia_envio === 'GLS';

  const DatosLogistica = ({ datos, titulo }) => {
    if (!datos) return null;
    return (
      <div className="mt-1 p-2 bg-slate-50 rounded text-xs space-y-1">
        <p className="font-medium text-muted-foreground">{titulo}:</p>
        {datos.nombre && <p className="flex items-center gap-1"><User className="w-3 h-3" /> {datos.nombre}</p>}
        {datos.direccion && (
          <p className="flex items-center gap-1">
            <MapPin className="w-3 h-3" /> 
            {datos.direccion}{datos.planta && `, ${datos.planta}`}{datos.puerta && ` ${datos.puerta}`}{datos.codigo_postal && `, ${datos.codigo_postal}`}{datos.ciudad && ` ${datos.ciudad}`}
          </p>
        )}
        {datos.telefono && <p className="flex items-center gap-1"><Phone className="w-3 h-3" /> {datos.telefono}</p>}
        {datos.observaciones && <p className="text-muted-foreground italic">"{datos.observaciones}"</p>}
      </div>
    );
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Truck className="w-5 h-5" />
            Datos de Envío
            {esGLS && <Badge className="bg-orange-100 text-orange-700 text-xs">GLS</Badge>}
          </div>
          <div className="flex items-center gap-1">
            {isAdmin && !editingEnvio && (
              <Button variant="ghost" size="sm" onClick={onEditEnvio} title="Editar datos" data-testid="btn-edit-envio">
                <Pencil className="w-4 h-4" />
              </Button>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {editingEnvio ? (
          <div className="space-y-3">
            <div>
              <Label className="text-xs">Nº Autorización</Label>
              <Input value={envioData.numero_autorizacion} onChange={(e) => setEnvioData(prev => ({ ...prev, numero_autorizacion: e.target.value }))} placeholder="Número autorización" className="h-8" />
            </div>
            <div>
              <Label className="text-xs">Agencia</Label>
              <Input value={envioData.agencia_envio} onChange={(e) => setEnvioData(prev => ({ ...prev, agencia_envio: e.target.value }))} placeholder="Agencia de envío" className="h-8" />
            </div>
            <div>
              <Label className="text-xs">Código Recogida Entrada</Label>
              <Input value={envioData.codigo_recogida_entrada} onChange={(e) => setEnvioData(prev => ({ ...prev, codigo_recogida_entrada: e.target.value }))} placeholder="Código entrada" className="h-8 font-mono" />
            </div>
            <div>
              <Label className="text-xs">Código Recogida Salida</Label>
              <Input value={envioData.codigo_recogida_salida} onChange={(e) => setEnvioData(prev => ({ ...prev, codigo_recogida_salida: e.target.value }))} placeholder="Código salida" className="h-8 font-mono" />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" size="sm" onClick={onCancelEdit}><X className="w-4 h-4" /></Button>
              <Button size="sm" onClick={onGuardarEnvio} disabled={guardandoEnvio}>
                <Save className="w-4 h-4 mr-1" />{guardandoEnvio ? 'Guardando...' : 'Guardar'}
              </Button>
            </div>
          </div>
        ) : (
          <>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Nº Autorización:</span>
                <span className="font-mono">{orden.numero_autorizacion || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Agencia:</span>
                <span>{orden.agencia_envio || '-'}</span>
              </div>
              
              {/* Código Entrada */}
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Código Entrada:</span>
                <div className="flex items-center gap-2">
                  {orden.codigo_recogida_entrada ? (
                    <Badge variant="outline" className="font-mono" data-testid="badge-codigo-entrada">
                      {orden.codigo_recogida_entrada}
                    </Badge>
                  ) : <span className="text-muted-foreground">-</span>}
                  {puedeGenerarRecogida && onGenerarRecogida && (
                    <Button variant="outline" size="sm" onClick={onGenerarRecogida} className="h-7 text-xs px-2" data-testid="btn-generar-recogida">
                      <Package className="w-3 h-3 mr-1" />Generar
                    </Button>
                  )}
                </div>
              </div>
              <DatosLogistica datos={datosRecogida} titulo="Dirección recogida" />
              
              {/* Código Salida */}
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Código Salida:</span>
                <div className="flex items-center gap-2">
                  {(orden.codigo_recogida_salida || orden.codigo_envio) ? (
                    <Badge variant="outline" className="font-mono" data-testid="badge-codigo-salida">
                      {orden.codigo_recogida_salida || orden.codigo_envio}
                    </Badge>
                  ) : <span className="text-muted-foreground">-</span>}
                  {puedeGenerarEnvio && onGenerarEnvio && (
                    <Button variant="outline" size="sm" onClick={onGenerarEnvio} className="h-7 text-xs px-2" data-testid="btn-generar-envio">
                      <Send className="w-3 h-3 mr-1" />Generar
                    </Button>
                  )}
                </div>
              </div>
              <DatosLogistica datos={datosEnvio} titulo="Dirección envío" />
            </div>

            {/* GLS Shipments Detail */}
            {glsEnvios.length > 0 && (
              <div className="mt-3 pt-3 border-t space-y-2">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Envíos GLS vinculados</p>
                {glsEnvios.map((gls, idx) => (
                  <div key={gls.id || idx} className="p-2.5 bg-orange-50 rounded-lg border border-orange-100 text-sm" data-testid={`gls-envio-${idx}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {gls.tipo === 'recogida' ? (
                          <ArrowDown className="w-4 h-4 text-amber-600" />
                        ) : (
                          <ArrowUp className="w-4 h-4 text-green-600" />
                        )}
                        <span className="font-medium capitalize">{gls.tipo}</span>
                        <Badge className={`text-xs ${ESTADO_BADGE[gls.estado_gls] || 'bg-gray-100 text-gray-700'}`}>
                          {gls.estado_gls || 'grabado'}
                        </Badge>
                      </div>
                      {gls.codbarras && (
                        <a
                          href={`https://www.gls-spain.es/es/ayuda/seguimiento-de-envio/?match=${gls.codbarras}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:underline flex items-center gap-1"
                          data-testid={`gls-tracking-link-${idx}`}
                        >
                          <ExternalLink className="w-3 h-3" /> Tracking
                        </a>
                      )}
                    </div>
                    <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                      {gls.codbarras && <span className="font-mono">{gls.codbarras}</span>}
                      {gls.created_at && <span>{new Date(gls.created_at).toLocaleString('es-ES', {day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit'})}</span>}
                      {gls.created_by && <span>por {gls.created_by}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

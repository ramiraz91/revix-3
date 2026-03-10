import { useRef, useState } from 'react';
import QRCode from 'react-qr-code';
import { Printer, X, Settings, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

// Tamaños de etiquetas con configuración de contenido proporcional
const LABEL_SIZES = {
  '50x30': { 
    width: '50mm', 
    height: '30mm', 
    name: '50x30mm (Pequeña)',
    qrSize: 36,
    headerSize: '7pt',
    orderSize: '8pt',
    labelSize: '5pt',
    valueSize: '6pt',
    damageHeight: '8mm',
    showImei: false,
    padding: '1.5mm'
  },
  '60x40': { 
    width: '60mm', 
    height: '40mm', 
    name: '60x40mm (Mediana)',
    qrSize: 48,
    headerSize: '9pt',
    orderSize: '10pt',
    labelSize: '6pt',
    valueSize: '7pt',
    damageHeight: '10mm',
    showImei: true,
    padding: '2mm'
  },
  '70x50': { 
    width: '70mm', 
    height: '50mm', 
    name: '70x50mm (Grande)',
    qrSize: 56,
    headerSize: '10pt',
    orderSize: '12pt',
    labelSize: '7pt',
    valueSize: '8pt',
    damageHeight: '14mm',
    showImei: true,
    padding: '2.5mm'
  },
  '80x40': { 
    width: '80mm', 
    height: '40mm', 
    name: '80x40mm (Alargada)',
    qrSize: 48,
    headerSize: '9pt',
    orderSize: '11pt',
    labelSize: '6pt',
    valueSize: '8pt',
    damageHeight: '10mm',
    showImei: true,
    padding: '2mm'
  },
};

export function EtiquetaOrden({ orden, onClose }) {
  const [labelSize, setLabelSize] = useState('60x40');
  const [printing, setPrinting] = useState(false);
  const etiquetaRef = useRef(null);

  if (!orden) return null;

  const size = LABEL_SIZES[labelSize];

  // Función para imprimir solo la etiqueta usando un iframe aislado
  const handlePrintLabel = () => {
    setPrinting(true);
    
    const printContent = etiquetaRef.current;
    if (!printContent) {
      setPrinting(false);
      return;
    }

    // Crear un iframe oculto para impresión aislada
    const printFrame = document.createElement('iframe');
    printFrame.style.position = 'absolute';
    printFrame.style.top = '-9999px';
    printFrame.style.left = '-9999px';
    printFrame.style.width = '0';
    printFrame.style.height = '0';
    document.body.appendChild(printFrame);

    const printDocument = printFrame.contentDocument || printFrame.contentWindow.document;
    
    // Estilos optimizados para impresoras de etiquetas térmicas
    const styles = `
      @page {
        size: ${size.width} ${size.height};
        margin: 0;
      }
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }
      body {
        font-family: 'Arial Narrow', Arial, sans-serif;
        width: ${size.width};
        height: ${size.height};
        padding: ${size.padding};
        display: flex;
        flex-direction: column;
      }
      .label-container {
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
      }
      .header {
        text-align: center;
        border-bottom: 0.5pt solid #000;
        padding-bottom: 1mm;
        margin-bottom: 1mm;
        font-size: ${size.headerSize};
        font-weight: bold;
      }
      .content {
        display: flex;
        gap: 2mm;
        flex: 1;
      }
      .qr-section {
        flex-shrink: 0;
      }
      .qr-section svg {
        width: ${size.qrSize}px !important;
        height: ${size.qrSize}px !important;
      }
      .info-section {
        flex: 1;
        min-width: 0;
      }
      .order-number {
        font-family: 'Courier New', monospace;
        font-size: ${size.orderSize};
        font-weight: bold;
        margin-bottom: 1mm;
      }
      .info-row {
        margin-bottom: 0.5mm;
      }
      .info-label {
        font-size: ${size.labelSize};
        text-transform: uppercase;
        color: #666;
      }
      .info-value {
        font-size: ${size.valueSize};
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .damage-box {
        border: 0.5pt solid #000;
        padding: 1mm;
        margin-top: 1mm;
        max-height: ${size.damageHeight};
        overflow: hidden;
      }
      .damage-label {
        font-size: ${size.labelSize};
        text-transform: uppercase;
        color: #666;
      }
      .damage-value {
        font-size: ${size.labelSize};
      }
      .footer {
        text-align: center;
        font-size: ${size.labelSize};
        border-top: 0.5pt solid #000;
        padding-top: 1mm;
        margin-top: auto;
      }
    `;

    // Renderizar QR como string SVG
    const qrSvg = etiquetaRef.current.querySelector('.qr-code-container svg');
    const qrHtml = qrSvg ? qrSvg.outerHTML : '';

    // Calcular caracteres máximos para avería según tamaño
    const maxDamageChars = labelSize === '50x30' ? 40 : labelSize === '70x50' ? 100 : 60;

    printDocument.open();
    printDocument.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="utf-8">
          <title>Etiqueta ${orden.numero_orden}</title>
          <style>${styles}</style>
        </head>
        <body>
          <div class="label-container">
            <div class="header">NEXORA</div>
            <div class="content">
              <div class="qr-section">
                ${qrHtml}
              </div>
              <div class="info-section">
                <div class="order-number">${orden.numero_orden}</div>
                <div class="info-row">
                  <div class="info-label">Modelo</div>
                  <div class="info-value">${orden.dispositivo?.modelo || '-'}</div>
                </div>
                <div class="info-row">
                  <div class="info-label">Color</div>
                  <div class="info-value">${orden.dispositivo?.color || '-'}</div>
                </div>
                ${size.showImei && orden.dispositivo?.imei ? `
                <div class="info-row">
                  <div class="info-label">IMEI</div>
                  <div class="info-value" style="font-family: monospace;">${orden.dispositivo.imei}</div>
                </div>
                ` : ''}
              </div>
            </div>
            <div class="damage-box">
              <div class="damage-label">Avería</div>
              <div class="damage-value">${(orden.dispositivo?.daños || '-').substring(0, maxDamageChars)}</div>
            </div>
            <div class="footer">
              ${new Date(orden.created_at).toLocaleDateString('es-ES')}
            </div>
          </div>
        </body>
      </html>
    `);
    printDocument.close();

    // Esperar a que cargue y luego imprimir
    printFrame.onload = () => {
      setTimeout(() => {
        try {
          printFrame.contentWindow.focus();
          printFrame.contentWindow.print();
        } catch (e) {
          console.error('Error al imprimir:', e);
        }
        
        // Limpiar después de un momento
        setTimeout(() => {
          document.body.removeChild(printFrame);
          setPrinting(false);
        }, 1000);
      }, 250);
    };
  };

  return (
    <Dialog open={true} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md" data-testid="etiqueta-orden-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Printer className="w-5 h-5" />
            Etiqueta de Dispositivo
          </DialogTitle>
        </DialogHeader>

        {/* Selector de tamaño */}
        <div className="flex items-center gap-4 p-3 bg-slate-50 rounded-lg">
          <Settings className="w-4 h-4 text-muted-foreground" />
          <div className="flex-1">
            <Label className="text-xs text-muted-foreground">Tamaño de etiqueta</Label>
            <Select value={labelSize} onValueChange={setLabelSize}>
              <SelectTrigger className="h-8 mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(LABEL_SIZES).map(([key, { name }]) => (
                  <SelectItem key={key} value={key}>{name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Vista previa de la etiqueta */}
        <div className="flex justify-center p-4 bg-slate-100 rounded-lg">
          <div 
            ref={etiquetaRef}
            className="bg-white border-2 border-dashed border-slate-300 overflow-hidden flex flex-col"
            style={{ 
              width: size.width, 
              height: size.height,
              padding: size.padding,
              fontFamily: "'Arial Narrow', Arial, sans-serif"
            }}
          >
            {/* Header */}
            <div 
              className="text-center border-b border-black"
              style={{ 
                fontSize: size.headerSize, 
                fontWeight: 'bold',
                paddingBottom: '1mm',
                marginBottom: '1mm'
              }}
            >
              NEXORA
            </div>

            {/* Content */}
            <div className="flex gap-2 flex-1">
              {/* QR */}
              <div className="flex-shrink-0 qr-code-container">
                <QRCode value={orden.numero_orden} size={size.qrSize} />
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p 
                  className="font-mono font-bold truncate"
                  style={{ fontSize: size.orderSize, marginBottom: '1mm' }}
                >
                  {orden.numero_orden}
                </p>
                <div style={{ lineHeight: 1.2 }}>
                  <div style={{ marginBottom: '0.5mm' }}>
                    <p style={{ fontSize: size.labelSize, color: '#666', textTransform: 'uppercase' }}>Modelo</p>
                    <p style={{ fontSize: size.valueSize, fontWeight: 500 }} className="truncate">{orden.dispositivo?.modelo}</p>
                  </div>
                  <div style={{ marginBottom: '0.5mm' }}>
                    <p style={{ fontSize: size.labelSize, color: '#666', textTransform: 'uppercase' }}>Color</p>
                    <p style={{ fontSize: size.valueSize }} className="truncate">{orden.dispositivo?.color || '-'}</p>
                  </div>
                  {size.showImei && orden.dispositivo?.imei && (
                    <div>
                      <p style={{ fontSize: size.labelSize, color: '#666', textTransform: 'uppercase' }}>IMEI</p>
                      <p style={{ fontSize: size.labelSize, fontFamily: 'monospace' }} className="truncate">{orden.dispositivo.imei}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Damage box */}
            <div 
              className="border border-black overflow-hidden"
              style={{ 
                padding: '1mm', 
                marginTop: '1mm',
                maxHeight: size.damageHeight
              }}
            >
              <p style={{ fontSize: size.labelSize, color: '#666', textTransform: 'uppercase' }}>Avería</p>
              <p style={{ fontSize: size.labelSize }} className="line-clamp-2">{orden.dispositivo?.daños}</p>
            </div>

            {/* Footer */}
            <div 
              className="text-center border-t border-black mt-auto"
              style={{ fontSize: size.labelSize, paddingTop: '1mm' }}
            >
              {new Date(orden.created_at).toLocaleDateString('es-ES')}
            </div>
          </div>
        </div>

        {/* Acciones */}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={onClose}>
            <X className="w-4 h-4 mr-2" />
            Cerrar
          </Button>
          <Button 
            onClick={handlePrintLabel} 
            disabled={printing}
            data-testid="btn-imprimir-etiqueta"
          >
            {printing ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Imprimiendo...
              </>
            ) : (
              <>
                <Printer className="w-4 h-4 mr-2" />
                Imprimir Etiqueta
              </>
            )}
          </Button>
        </div>

        <p className="text-xs text-muted-foreground text-center">
          💡 Solo se imprimirá la etiqueta, sin otros documentos.
        </p>
      </DialogContent>
    </Dialog>
  );
}

// Componente de etiqueta pequeña para uso interno (backup)
export function EtiquetaPequena({ orden }) {
  if (!orden) return null;

  return (
    <div className="w-[58mm] p-2 bg-white text-black" style={{ fontFamily: 'monospace' }}>
      <div className="text-center border-b border-black pb-1 mb-2">
        <p className="font-bold text-sm">NEXORA</p>
      </div>
      
      <div className="flex items-center gap-2 mb-2">
        <QRCode value={orden.numero_orden} size={40} />
        <div className="text-[10px]">
          <p className="font-bold">{orden.numero_orden}</p>
        </div>
      </div>
      
      <div className="text-[9px] space-y-1">
        <p><strong>Modelo:</strong> {orden.dispositivo?.modelo}</p>
        <p><strong>Color:</strong> {orden.dispositivo?.color || '-'}</p>
        <p><strong>Daño:</strong> {orden.dispositivo?.daños?.substring(0, 50)}</p>
      </div>
      
      <div className="border-t border-black mt-2 pt-1 text-[8px] text-center">
        {new Date(orden.created_at).toLocaleDateString('es-ES')}
      </div>
    </div>
  );
}

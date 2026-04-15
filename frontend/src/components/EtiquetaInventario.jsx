import { useRef, useState, useEffect } from 'react';
import JsBarcode from 'jsbarcode';
import { Printer, X, Settings, Loader2, Package } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
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

// Componente de código de barras para etiquetas
const BarcodeLabel = ({ value, width = 1.5, height = 30, fontSize = 10 }) => {
  const svgRef = useRef(null);

  useEffect(() => {
    if (svgRef.current && value) {
      try {
        JsBarcode(svgRef.current, value, {
          format: 'CODE128',
          width,
          height,
          displayValue: true,
          fontSize,
          textMargin: 1,
          margin: 2,
          background: '#ffffff',
          lineColor: '#000000',
        });
      } catch (error) {
        console.error('Error generating barcode:', error);
      }
    }
  }, [value, width, height, fontSize]);

  if (!value) return null;
  return <svg ref={svgRef} />;
};

// Tamaños de etiquetas
const LABEL_SIZES = {
  '29x90': {
    width: '90mm',
    height: '29mm',
    name: '29x90mm (Brother QL-800)',
    barcodeWidth: 1.2,
    barcodeHeight: 18,
    barcodeFontSize: 8,
    nameSize: '8pt',
    skuSize: '7pt',
    priceSize: '10pt',
    padding: '2mm',
    layout: 'horizontal'
  },
  '50x30': {
    width: '50mm',
    height: '30mm',
    name: '50x30mm (Pequena)',
    barcodeWidth: 1.0,
    barcodeHeight: 18,
    barcodeFontSize: 7,
    nameSize: '7pt',
    skuSize: '6pt',
    priceSize: '9pt',
    padding: '1.5mm',
    layout: 'horizontal'
  },
  '60x40': {
    width: '60mm',
    height: '40mm',
    name: '60x40mm (Mediana)',
    barcodeWidth: 1.2,
    barcodeHeight: 24,
    barcodeFontSize: 8,
    nameSize: '8pt',
    skuSize: '7pt',
    priceSize: '11pt',
    padding: '2mm',
    layout: 'vertical'
  },
  '70x50': {
    width: '70mm',
    height: '50mm',
    name: '70x50mm (Grande)',
    barcodeWidth: 1.4,
    barcodeHeight: 30,
    barcodeFontSize: 9,
    nameSize: '9pt',
    skuSize: '8pt',
    priceSize: '12pt',
    padding: '2.5mm',
    layout: 'vertical'
  },
};

export function EtiquetaInventario({ producto, onClose }) {
  const [labelSize, setLabelSize] = useState('29x90');
  const [cantidad, setCantidad] = useState(1);
  const [printing, setPrinting] = useState(false);
  const [barcodeDataUrl, setBarcodeDataUrl] = useState(null);

  const codigoBarras = producto?.sku || producto?.codigo_barras || producto?.id || 'SIN-SKU';
  const size = LABEL_SIZES[labelSize];

  // Generar código de barras como imagen para impresión
  useEffect(() => {
    if (codigoBarras) {
      const canvas = document.createElement('canvas');
      try {
        JsBarcode(canvas, codigoBarras, {
          format: 'CODE128',
          width: size.barcodeWidth,
          height: size.barcodeHeight,
          displayValue: true,
          fontSize: size.barcodeFontSize,
          textMargin: 1,
          margin: 2,
          background: '#ffffff',
          lineColor: '#000000',
        });
        setBarcodeDataUrl(canvas.toDataURL('image/png'));
      } catch (error) {
        console.error('Error generating barcode:', error);
      }
    }
  }, [codigoBarras, labelSize, size]);

  if (!producto) return null;

  const precio = producto.precio_venta ? `${producto.precio_venta.toFixed(2)}\u20AC` : '';
  const nombre = (producto.nombre || '').substring(0, 60);

  const handlePrint = () => {
    setPrinting(true);

    const printFrame = document.createElement('iframe');
    printFrame.style.position = 'absolute';
    printFrame.style.top = '-9999px';
    printFrame.style.left = '-9999px';
    printFrame.style.width = '0';
    printFrame.style.height = '0';
    document.body.appendChild(printFrame);

    const doc = printFrame.contentDocument || printFrame.contentWindow.document;

    const isHorizontal = size.layout === 'horizontal';

    const labelHTML = `
      <div class="etiqueta">
        ${isHorizontal ? `
          <div class="h-layout">
            <div class="info-col">
              <div class="nombre">${nombre}</div>
              ${precio ? `<div class="precio">${precio}</div>` : ''}
            </div>
            <div class="barcode-col">
              ${barcodeDataUrl ? `<img src="${barcodeDataUrl}" alt="barcode" />` : ''}
            </div>
          </div>
        ` : `
          <div class="v-layout">
            <div class="nombre">${nombre}</div>
            <div class="barcode-center">
              ${barcodeDataUrl ? `<img src="${barcodeDataUrl}" alt="barcode" />` : ''}
            </div>
            ${precio ? `<div class="precio">${precio}</div>` : ''}
          </div>
        `}
      </div>
    `;

    const labels = Array(cantidad).fill(labelHTML).join('');

    doc.open();
    doc.write(`<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Etiqueta Inventario</title>
  <style>
    @page { size: ${size.width} ${size.height}; margin: 0; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Arial Narrow', Arial, sans-serif; }
    .etiqueta {
      width: ${size.width};
      height: ${size.height};
      padding: ${size.padding};
      page-break-after: always;
      page-break-inside: avoid;
      overflow: hidden;
    }
    .h-layout {
      display: flex;
      align-items: center;
      height: 100%;
      gap: 2mm;
    }
    .info-col {
      flex: 0 0 35%;
      overflow: hidden;
    }
    .barcode-col {
      flex: 1;
      text-align: center;
    }
    .barcode-col img { max-width: 100%; height: auto; }
    .v-layout {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      gap: 1mm;
    }
    .barcode-center img { max-width: 100%; height: auto; }
    .nombre {
      font-size: ${size.nameSize};
      font-weight: bold;
      line-height: 1.2;
      overflow: hidden;
      word-break: break-word;
      text-align: center;
    }
    .precio {
      font-size: ${size.priceSize};
      font-weight: bold;
      text-align: center;
    }
  </style>
</head>
<body>${labels}</body>
</html>`);
    doc.close();

    printFrame.onload = () => {
      setTimeout(() => {
        try {
          printFrame.contentWindow.focus();
          printFrame.contentWindow.print();
        } catch (e) {
          console.error('Error al imprimir:', e);
        }
        setTimeout(() => {
          document.body.removeChild(printFrame);
          setPrinting(false);
        }, 1000);
      }, 250);
    };
  };

  return (
    <Dialog open={true} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md" data-testid="etiqueta-inventario-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="w-5 h-5" />
            Etiqueta de Producto
          </DialogTitle>
        </DialogHeader>

        {/* Configuración */}
        <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
          <Settings className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          <div className="flex-1">
            <Label className="text-xs text-muted-foreground">Tamano</Label>
            <Select value={labelSize} onValueChange={setLabelSize}>
              <SelectTrigger className="h-8 mt-1" data-testid="label-size-selector">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(LABEL_SIZES).map(([key, { name }]) => (
                  <SelectItem key={key} value={key}>{name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="w-20">
            <Label className="text-xs text-muted-foreground">Copias</Label>
            <Input
              type="number"
              min={1}
              max={50}
              value={cantidad}
              onChange={e => setCantidad(Math.max(1, parseInt(e.target.value) || 1))}
              className="h-8 mt-1"
              data-testid="label-copies-input"
            />
          </div>
        </div>

        {/* Vista previa */}
        <div className="flex justify-center p-4 bg-slate-100 rounded-lg">
          <div
            className="bg-white border-2 border-dashed border-slate-300 overflow-hidden flex"
            style={{
              width: size.width,
              height: size.height,
              padding: size.padding,
              fontFamily: "'Arial Narrow', Arial, sans-serif",
              alignItems: 'center',
              justifyContent: size.layout === 'vertical' ? 'center' : 'space-between',
              flexDirection: size.layout === 'vertical' ? 'column' : 'row',
              gap: '2mm'
            }}
          >
            {size.layout === 'horizontal' ? (
              <>
                <div style={{ flex: '0 0 35%', overflow: 'hidden' }}>
                  <p style={{ fontSize: size.nameSize, fontWeight: 'bold', lineHeight: 1.2, wordBreak: 'break-word' }}>{nombre}</p>
                  {precio && <p style={{ fontSize: size.priceSize, fontWeight: 'bold', marginTop: '1mm' }}>{precio}</p>}
                </div>
                <div style={{ flex: 1, textAlign: 'center' }}>
                  <BarcodeLabel
                    value={codigoBarras}
                    width={size.barcodeWidth}
                    height={size.barcodeHeight}
                    fontSize={size.barcodeFontSize}
                  />
                </div>
              </>
            ) : (
              <>
                <p style={{ fontSize: size.nameSize, fontWeight: 'bold', lineHeight: 1.2, textAlign: 'center', wordBreak: 'break-word' }}>{nombre}</p>
                <BarcodeLabel
                  value={codigoBarras}
                  width={size.barcodeWidth}
                  height={size.barcodeHeight}
                  fontSize={size.barcodeFontSize}
                />
                {precio && <p style={{ fontSize: size.priceSize, fontWeight: 'bold' }}>{precio}</p>}
              </>
            )}
          </div>
        </div>

        {/* Acciones */}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={onClose}>
            <X className="w-4 h-4 mr-2" />
            Cerrar
          </Button>
          <Button
            onClick={handlePrint}
            disabled={printing}
            data-testid="btn-imprimir-etiqueta-inventario"
          >
            {printing ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Imprimiendo...
              </>
            ) : (
              <>
                <Printer className="w-4 h-4 mr-2" />
                Imprimir {cantidad > 1 ? `${cantidad} Etiquetas` : 'Etiqueta'}
              </>
            )}
          </Button>
        </div>

        <p className="text-xs text-muted-foreground text-center">
          Producto: {codigoBarras}
        </p>
      </DialogContent>
    </Dialog>
  );
}

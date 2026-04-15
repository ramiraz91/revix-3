import { useEffect, useRef } from 'react';
import JsBarcode from 'jsbarcode';

/**
 * Componente de código de barras usando JsBarcode
 * @param {string} value - Valor a codificar
 * @param {string} format - Formato: CODE128, CODE39, EAN13, UPC, etc. (default: CODE128)
 * @param {number} width - Ancho de cada barra (default: 2)
 * @param {number} height - Alto del código de barras (default: 50)
 * @param {boolean} displayValue - Mostrar valor debajo (default: true)
 * @param {string} fontSize - Tamaño de fuente del texto (default: 14)
 * @param {string} textMargin - Margen del texto (default: 2)
 * @param {string} background - Color de fondo (default: #ffffff)
 * @param {string} lineColor - Color de las barras (default: #000000)
 * @param {string} className - Clase CSS adicional
 */
export function Barcode({ 
  value, 
  format = 'CODE128',
  width = 2,
  height = 50,
  displayValue = true,
  fontSize = 14,
  textMargin = 2,
  background = '#ffffff',
  lineColor = '#000000',
  className = '',
  margin = 10,
  marginTop,
  marginBottom,
  marginLeft,
  marginRight
}) {
  const svgRef = useRef(null);

  useEffect(() => {
    if (svgRef.current && value) {
      try {
        JsBarcode(svgRef.current, value, {
          format,
          width,
          height,
          displayValue,
          fontSize,
          textMargin,
          background,
          lineColor,
          margin,
          marginTop,
          marginBottom,
          marginLeft,
          marginRight,
          valid: () => true // Aceptar todos los valores
        });
      } catch (error) {
        console.error('Error generating barcode:', error);
      }
    }
  }, [value, format, width, height, displayValue, fontSize, textMargin, background, lineColor, margin]);

  if (!value) return null;

  return <svg ref={svgRef} className={className} />;
}

/**
 * Genera un código de barras como imagen base64 (para PDFs)
 * @param {string} value - Valor a codificar
 * @param {object} options - Opciones de JsBarcode
 * @returns {string} - Data URL de la imagen PNG
 */
export function generateBarcodeDataURL(value, options = {}) {
  if (!value) return null;
  
  const canvas = document.createElement('canvas');
  
  try {
    JsBarcode(canvas, value, {
      format: options.format || 'CODE128',
      width: options.width || 2,
      height: options.height || 50,
      displayValue: options.displayValue !== false,
      fontSize: options.fontSize || 12,
      textMargin: options.textMargin || 2,
      background: options.background || '#ffffff',
      lineColor: options.lineColor || '#000000',
      margin: options.margin || 5,
      valid: () => true
    });
    
    return canvas.toDataURL('image/png');
  } catch (error) {
    console.error('Error generating barcode data URL:', error);
    return null;
  }
}

export default Barcode;

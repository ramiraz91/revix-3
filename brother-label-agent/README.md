# Brother Label Agent v1.0.0

Agente local de impresion directa para **Brother QL-800** con etiquetas **DK-11204** (17mm x 54mm).

---

## Requisitos del PC

| Componente | Detalle |
|---|---|
| Sistema operativo | Windows 10 / 11 |
| Python | 3.10 o superior |
| Impresora | Brother QL-800 conectada por USB |
| Driver | Driver oficial Brother QL-800 instalado |
| Etiquetas | DK-11204 (17 x 54 mm) cargadas en la impresora |

---

## Instalacion

### 1. Descargar el agente

Desde el CRM, acceda a **Herramientas Admin > Descarga Agente de Impresion** o descargue el ZIP desde la seccion correspondiente.

Descomprima el contenido en una carpeta, por ejemplo:

```
C:\RevixAgent\
```

### 2. Instalar dependencias

Haga doble clic en **`install.bat`** o ejecute en terminal:

```cmd
cd C:\RevixAgent
install.bat
```

Esto creara un entorno virtual de Python e instalara:
- Flask (servidor HTTP local)
- Pillow (generacion de imagenes)
- python-barcode (Code128)
- pywin32 (impresion via Windows GDI)

### 3. Verificar la impresora

Antes de iniciar el agente, compruebe que:

1. La Brother QL-800 esta **encendida y conectada por USB**.
2. Las etiquetas **DK-11204** estan correctamente cargadas.
3. En **Panel de control > Dispositivos e impresoras**, aparece "Brother QL-800".

---

## Uso diario

### Iniciar el agente

Haga doble clic en **`start.bat`**.

Vera en la consola:

```
Brother Label Agent v1.0.0
Puerto: 5555
Impresora por defecto: Brother QL-800
Formato de etiqueta: DK-11204 (17mm x 54mm)
```

### Dejar el agente abierto

Minimice la ventana de consola. El agente debe permanecer ejecutandose mientras use el CRM para imprimir etiquetas.

### Detener el agente

Pulse **Ctrl+C** en la ventana de consola o simplemente cierrela.

---

## Configuracion

Edite el archivo **`config.json`**:

```json
{
    "port": 5555,
    "default_printer": "Brother QL-800",
    "label_format": "DK-11204",
    "label_width_mm": 54,
    "label_height_mm": 17
}
```

| Campo | Descripcion |
|---|---|
| `port` | Puerto HTTP local (por defecto 5555) |
| `default_printer` | Nombre exacto de la impresora en Windows |

> **Importante**: El nombre de la impresora debe coincidir **exactamente** con el que aparece en Panel de control > Dispositivos e impresoras.

---

## Endpoints del agente

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/health` | Estado del agente y la impresora |
| GET | `/printers` | Lista de impresoras instaladas |
| POST | `/print` | Imprimir una etiqueta |
| POST | `/test-print` | Imprimir etiqueta de prueba |

### Ejemplo: Imprimir etiqueta OT

```bash
curl -X POST http://127.0.0.1:5555/print ^
  -H "Content-Type: application/json" ^
  -d "{\"printerName\":\"Brother QL-800\",\"template\":\"ot_barcode_minimal\",\"jobId\":\"ot-001\",\"data\":{\"orderId\":\"abc123\",\"orderNumber\":\"OT-000482\",\"barcodeValue\":\"abc123\",\"deviceModel\":\"Samsung Galaxy S24\"}}"
```

### Ejemplo: Imprimir etiqueta de inventario

```bash
curl -X POST http://127.0.0.1:5555/print ^
  -H "Content-Type: application/json" ^
  -d "{\"printerName\":\"Brother QL-800\",\"template\":\"inventory_label\",\"jobId\":\"inv-001\",\"data\":{\"barcodeValue\":\"SKU-12345\",\"productName\":\"Pantalla iPhone 15 Pro\",\"price\":\"189.00 EUR\"}}"
```

---

## Solucion de problemas

| Problema | Solucion |
|---|---|
| "Impresora no encontrada" | Verifique que la QL-800 esta encendida y conectada. El nombre en `config.json` debe coincidir exactamente con Windows. |
| "Error del spooler" | Reinicie el servicio "Cola de impresion" en Windows (`services.msc`). |
| "pywin32 no disponible" | Ejecute `pip install pywin32` en el entorno virtual. |
| Etiqueta sale cortada | Verifique que las DK-11204 estan bien colocadas y el sensor detecta las etiquetas. |
| El CRM dice "Agente no detectado" | Asegurese de que `start.bat` esta ejecutandose. Compruebe que el puerto 5555 no esta bloqueado por firewall. |
| Barcode no se escanea bien | Limpie el cabezal de la QL-800. Verifique que la cinta DK-11204 no esta agotada. |

---

## Logs

El agente escribe logs en **`agent.log`** en el mismo directorio. Revise este archivo si hay errores.

---

## Inicio automatico con Windows (opcional)

Para que el agente arranque automaticamente al encender el PC:

1. Pulse `Win + R`, escriba `shell:startup`, pulse Enter.
2. Copie un acceso directo de `start.bat` en la carpeta que se abrio.

---

## Arquitectura tecnica

```
PC Windows (taller)
+-------------------------------------------+
|  Brother Label Agent (Flask, puerto 5555) |
|    |                                       |
|    +-> label_generator.py                 |
|    |     Pillow + python-barcode          |
|    |     DK-11204: 638x201 px @ 300 DPI   |
|    |                                       |
|    +-> printer_service.py                 |
|         Win32 GDI (pywin32)               |
|         -> Brother QL-800 (USB)           |
+-------------------------------------------+
         ^
         | HTTP localhost:5555
         |
+-------------------------------------------+
|  Navegador: CRM Revix                     |
|    fetch("http://127.0.0.1:5555/print")   |
+-------------------------------------------+
```

No hay comunicacion con el servidor del CRM para la impresion. El navegador se comunica directamente con el agente local.

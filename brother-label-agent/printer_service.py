"""
Servicio de impresion para Windows via Win32 GDI.

Flujo:
  1. Detecta impresoras instaladas en Windows.
  2. Configura DEVMODE con el tamano de papel DK-11204 (17x54mm).
  3. Abre un Device Context (DC) para la impresora.
  4. Si la imagen no coincide en orientacion, rota automaticamente.
  5. Envia la imagen como DIB al spooler.

Requisitos en el PC destino:
  - Windows 10/11
  - Driver Brother QL-800 instalado
  - pywin32 (pip install pywin32)
"""

import os
import sys
import logging
import platform
import tempfile

from PIL import Image

log = logging.getLogger("brother-agent")

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    try:
        import win32print
        import win32ui
        import win32con
        from PIL import ImageWin

        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
        log.warning("pywin32 no disponible. Instale: pip install pywin32")
else:
    WIN32_AVAILABLE = False


# DK-11204 en decimas de milimetro (para DEVMODE)
DK11204_WIDTH_DMM = 170    # 17.0 mm
DK11204_HEIGHT_DMM = 540   # 54.0 mm


class PrinterService:
    """Gestiona deteccion e impresion en impresoras Windows."""

    def __init__(self, default_printer="Brother QL-800"):
        self.default_printer = default_printer

    # ------------------------------------------------------------------
    # Listado de impresoras
    # ------------------------------------------------------------------
    def list_printers(self):
        if not WIN32_AVAILABLE:
            return [
                {
                    "name": self.default_printer,
                    "isDefault": True,
                    "online": False,
                    "note": "Modo simulacion (Win32 no disponible)",
                }
            ]

        result = []
        try:
            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            printers = win32print.EnumPrinters(flags)
            for _flags, _desc, name, _comment in printers:
                result.append(
                    {
                        "name": name,
                        "isDefault": name == self.default_printer,
                        "online": True,
                    }
                )
        except Exception as exc:
            log.error("Error enumerando impresoras: %s", exc)

        return result

    # ------------------------------------------------------------------
    # Estado de la impresora
    # ------------------------------------------------------------------
    def check_status(self):
        if not WIN32_AVAILABLE:
            return {
                "online": False,
                "reason": "Win32 no disponible (no es Windows o falta pywin32)",
            }

        try:
            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            printers = win32print.EnumPrinters(flags)
            names = [p[2] for p in printers]

            if self.default_printer not in names:
                return {
                    "online": False,
                    "reason": f"Impresora '{self.default_printer}' no encontrada. "
                    f"Disponibles: {', '.join(names) or 'ninguna'}",
                }

            handle = win32print.OpenPrinter(self.default_printer)
            try:
                info = win32print.GetPrinter(handle, 2)
                status_code = info.get("Status", 0)
            finally:
                win32print.ClosePrinter(handle)

            if status_code != 0:
                status_map = {
                    0x00000001: "Pausada",
                    0x00000002: "Error",
                    0x00000004: "Eliminando",
                    0x00000008: "Atasco de papel",
                    0x00000010: "Sin papel",
                    0x00000020: "Alimentacion manual",
                    0x00000040: "Problema de papel",
                    0x00000080: "Offline",
                    0x00000100: "E/S activa",
                    0x00000200: "Ocupada",
                    0x00000400: "Imprimiendo",
                    0x00000800: "Bandeja de salida llena",
                    0x00001000: "No disponible",
                    0x00002000: "Esperando",
                    0x00004000: "Procesando",
                    0x00008000: "Inicializando",
                    0x00010000: "Calentando",
                    0x00020000: "Toner bajo",
                    0x00040000: "Sin toner",
                    0x00080000: "Fallo de pagina",
                    0x00100000: "Intervencion requerida",
                    0x00200000: "Sin memoria",
                    0x00400000: "Puerta abierta",
                    0x00800000: "Error de servidor",
                    0x01000000: "Modo ahorro de energia",
                }
                reasons = [
                    desc for code, desc in status_map.items()
                    if status_code & code
                ]
                reason_str = ", ".join(reasons) if reasons else f"Codigo: {status_code}"
                return {"online": False, "reason": reason_str}

            return {"online": True, "reason": ""}

        except Exception as exc:
            return {"online": False, "reason": str(exc)}

    # ------------------------------------------------------------------
    # Configurar DEVMODE para DK-11204
    # ------------------------------------------------------------------
    @staticmethod
    def _get_devmode_dk11204(printer_name):
        """
        Obtiene el DEVMODE de la impresora y fuerza tamano de papel
        personalizado a DK-11204 (17mm x 54mm).
        """
        handle = win32print.OpenPrinter(printer_name)
        try:
            # Obtener DEVMODE actual
            devmode = win32print.GetPrinter(handle, 2)["pDevMode"]

            # Forzar tamano de papel personalizado
            devmode.PaperSize = 256  # DMPAPER_USER (tamano personalizado)
            devmode.PaperWidth = DK11204_WIDTH_DMM     # 17.0 mm en decimas de mm
            devmode.PaperLength = DK11204_HEIGHT_DMM   # 54.0 mm en decimas de mm
            devmode.Orientation = 1  # Portrait (la QL-800 alimenta por el lado corto)

            # Marcar que hemos modificado estos campos
            devmode.Fields |= (
                0x00000002 |  # DM_PAPERSIZE
                0x00000008 |  # DM_PAPERLENGTH
                0x00000010 |  # DM_PAPERWIDTH
                0x00000001    # DM_ORIENTATION
            )

            return devmode
        finally:
            win32print.ClosePrinter(handle)

    # ------------------------------------------------------------------
    # Impresion
    # ------------------------------------------------------------------
    def print_image(self, pil_image, printer_name=None):
        """
        Envia una imagen PIL a la impresora via Win32 GDI.
        Fuerza el tamano de papel a DK-11204 (17x54mm) mediante DEVMODE.
        """
        printer_name = printer_name or self.default_printer

        if not WIN32_AVAILABLE:
            preview_path = os.path.join(
                tempfile.gettempdir(), "brother_last_label.png"
            )
            pil_image.save(preview_path)
            log.info(
                "[SIMULACION] Imagen guardada en %s (%s px)",
                preview_path,
                pil_image.size,
            )
            return True

        hdc = None
        try:
            # Intentar configurar DEVMODE con tamano DK-11204
            devmode = None
            try:
                devmode = self._get_devmode_dk11204(printer_name)
                log.info(
                    "DEVMODE configurado: PaperSize=%s  Width=%s  Length=%s",
                    devmode.PaperSize, devmode.PaperWidth, devmode.PaperLength,
                )
            except Exception as dm_err:
                log.warning("No se pudo configurar DEVMODE: %s (usando defaults)", dm_err)

            # Crear DC con DEVMODE personalizado
            hdc = win32ui.CreateDC()
            if devmode:
                hdc.CreatePrinterDC(printer_name)
                # Aplicar DEVMODE al DC
                try:
                    hdc.ResetDC(devmode)
                except Exception as reset_err:
                    log.warning("ResetDC fallo: %s (continuando con defaults)", reset_err)
            else:
                hdc.CreatePrinterDC(printer_name)

            pw = hdc.GetDeviceCaps(win32con.PHYSICALWIDTH)
            ph = hdc.GetDeviceCaps(win32con.PHYSICALHEIGHT)
            log.info("Printer DC: %s  physical=%dx%d px", printer_name, pw, ph)

            img_w, img_h = pil_image.size
            img_landscape = img_w > img_h
            printer_landscape = pw > ph

            # Rotar si la orientacion no coincide
            if img_landscape != printer_landscape:
                pil_image = pil_image.rotate(90, expand=True)
                log.info("Imagen rotada 90 grados para ajustar orientacion")

            if pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")

            hdc.StartDoc("Brother Label - DK-11204")
            hdc.StartPage()

            dib = ImageWin.Dib(pil_image)
            dib.draw(hdc.GetHandleOutput(), (0, 0, pw, ph))

            hdc.EndPage()
            hdc.EndDoc()

            log.info("Impresion completada: %s", printer_name)
            return True

        except Exception as exc:
            log.error("Error de impresion en '%s': %s", printer_name, exc)

            err = str(exc).lower()
            if "no existe" in err or "not found" in err or "invalidprinter" in err:
                raise Exception(
                    f"Impresora '{printer_name}' no encontrada. "
                    "Verifique que esta instalada y encendida."
                )
            if "spooler" in err:
                raise Exception(
                    "Error del spooler de impresion de Windows. "
                    "Reinicie el servicio 'Cola de impresion'."
                )
            raise Exception(f"Error de impresion: {exc}")

        finally:
            if hdc:
                try:
                    hdc.DeleteDC()
                except Exception:
                    pass

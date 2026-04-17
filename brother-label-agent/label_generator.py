"""
Generador de etiquetas para DK-11204 (17mm x 54mm) a 300 DPI.

Dimensiones fisicas: 17 mm alto x 54 mm ancho
Resolucion Brother QL-800: 300 x 300 DPI

Pixels:
  ancho  = 54 mm * 300 / 25.4 = 638 px
  alto   = 17 mm * 300 / 25.4 = 201 px
"""

import os
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

import barcode
from barcode.writer import ImageWriter

# ---- Constantes DK-11204 a 300 DPI ----
LABEL_W = 638   # 54 mm
LABEL_H = 201   # 17 mm
DPI = 300

MX = 8    # margen horizontal
MY = 4    # margen superior


def _font(size, bold=False):
    """Carga fuente TrueType de Windows o fallback."""
    if bold:
        candidates = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


FONT_OT    = _font(22, bold=True)
FONT_MODEL = _font(18)
FONT_SKU   = _font(16)
FONT_TEST  = _font(20, bold=True)


class LabelGenerator:
    """Genera imagenes de etiqueta DK-11204 listas para imprimir a 300 DPI."""

    @staticmethod
    def _make_barcode(value, target_w, target_h):
        """
        Code128 de alta calidad.
        module_width alto = barras mas anchas = mejor lectura con escaner.
        """
        code128_class = barcode.get_barcode_class("code128")
        writer = ImageWriter()
        instance = code128_class(str(value), writer=writer)

        buf = BytesIO()
        # Generar a resolucion alta y luego recortar
        instance.write(buf, {
            "module_width":  0.45,     # barras anchas para mejor lectura
            "module_height": 15.0,
            "quiet_zone":    3.0,
            "write_text":    False,
            "text_distance": 0,
            "font_size":     0,
            "dpi":           DPI,
        })
        buf.seek(0)

        img = Image.open(buf).convert("1")  # 1-bit para maxima nitidez

        # Recortar bordes blancos
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

        # Redimensionar con NEAREST para barcode (sin antialiasing)
        img = img.resize((target_w, target_h), Image.NEAREST)
        return img.convert("RGB")

    @staticmethod
    def _truncate(text, draw, font, max_w):
        if not text:
            return ""
        bbox = draw.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            return text
        while len(text) > 1:
            text = text[:-1]
            candidate = text.rstrip() + "..."
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if (bbox[2] - bbox[0]) <= max_w:
                return candidate
        return "..."

    @staticmethod
    def _center_x(text, draw, font, canvas_w):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        return (canvas_w - tw) // 2

    # ------------------------------------------------------------------
    # Plantilla OT — DK-11204
    # ------------------------------------------------------------------
    def generate_ot_label(self, barcode_value, order_number, device_model):
        """
        barcode_value: numero de autorizacion (corto, ej: 26BE001378)
        order_number:  numero OT completo
        device_model:  modelo del dispositivo
        """
        img = Image.new("RGB", (LABEL_W, LABEL_H), "white")
        draw = ImageDraw.Draw(img)

        usable_w = LABEL_W - 2 * MX

        # 1) Barcode — elemento dominante
        bc_h = 105
        bc_y = MY
        bc_img = self._make_barcode(barcode_value, usable_w, bc_h)
        img.paste(bc_img, (MX, bc_y))

        # 2) Numero de autorizacion como texto principal
        ot_y = bc_y + bc_h + 3
        ot_text = barcode_value or order_number or ""
        ot_text = self._truncate(ot_text, draw, FONT_OT, usable_w)
        ot_x = self._center_x(ot_text, draw, FONT_OT, LABEL_W)
        draw.text((ot_x, ot_y), ot_text, fill="black", font=FONT_OT)

        # 3) Modelo dispositivo
        model_y = ot_y + 28
        model_text = self._truncate(device_model or "", draw, FONT_MODEL, usable_w)
        model_x = self._center_x(model_text, draw, FONT_MODEL, LABEL_W)
        draw.text((model_x, model_y), model_text, fill="#333333", font=FONT_MODEL)

        return img

    # ------------------------------------------------------------------
    # Plantilla Inventario — DK-11204
    # ------------------------------------------------------------------
    def generate_inventory_label(self, barcode_value, product_name, price=""):
        img = Image.new("RGB", (LABEL_W, LABEL_H), "white")
        draw = ImageDraw.Draw(img)

        usable_w = LABEL_W - 2 * MX

        bc_h = 95
        bc_y = MY
        bc_img = self._make_barcode(barcode_value, usable_w, bc_h)
        img.paste(bc_img, (MX, bc_y))

        name_y = bc_y + bc_h + 3
        name_text = self._truncate(product_name or "", draw, FONT_MODEL, usable_w)
        name_x = self._center_x(name_text, draw, FONT_MODEL, LABEL_W)
        draw.text((name_x, name_y), name_text, fill="black", font=FONT_MODEL)

        info_y = name_y + 24
        if price:
            info_text = f"{price}  |  {barcode_value}"
        else:
            info_text = barcode_value
        info_text = self._truncate(info_text, draw, FONT_SKU, usable_w)
        info_x = self._center_x(info_text, draw, FONT_SKU, LABEL_W)
        draw.text((info_x, info_y), info_text, fill="#333333", font=FONT_SKU)

        return img

    # ------------------------------------------------------------------
    # Test label
    # ------------------------------------------------------------------
    def generate_test_label(self):
        img = Image.new("RGB", (LABEL_W, LABEL_H), "white")
        draw = ImageDraw.Draw(img)
        draw.rectangle([2, 2, LABEL_W - 3, LABEL_H - 3], outline="black", width=2)
        lines = [
            ("BROTHER QL-800", FONT_TEST, 25),
            ("DK-11204 | 17x54mm | 300DPI", FONT_MODEL, 55),
            ("TEST OK", FONT_TEST, 90),
            (f"{LABEL_W}x{LABEL_H} px", FONT_SKU, 130),
        ]
        for text, font, y in lines:
            x = self._center_x(text, draw, font, LABEL_W)
            draw.text((x, y), text, fill="black", font=font)
        return img


if __name__ == "__main__":
    gen = LabelGenerator()

    ot = gen.generate_ot_label(
        barcode_value="26BE001378",
        order_number="OT-000482",
        device_model="Samsung Galaxy S24 Ultra 256GB",
    )
    ot.save("preview_ot_label.png")
    print(f"Guardado: preview_ot_label.png ({ot.size[0]}x{ot.size[1]})")

    inv = gen.generate_inventory_label(
        barcode_value="PANT-IPHO-15PRO",
        product_name="Pantalla iPhone 15 Pro Original",
        price="189.00 EUR",
    )
    inv.save("preview_inv_label.png")
    print(f"Guardado: preview_inv_label.png ({inv.size[0]}x{inv.size[1]})")

    test = gen.generate_test_label()
    test.save("preview_test_label.png")
    print(f"Guardado: preview_test_label.png ({test.size[0]}x{test.size[1]})")

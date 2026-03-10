"""
Utilidad para comprimir imágenes antes de guardarlas.
Reduce el tamaño de las imágenes manteniendo calidad aceptable.
"""
from PIL import Image
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

# Configuración de compresión
MAX_WIDTH = 1920  # Ancho máximo
MAX_HEIGHT = 1080  # Alto máximo
JPEG_QUALITY = 75  # Calidad JPEG (1-100)
MAX_FILE_SIZE_KB = 300  # Tamaño máximo en KB


def compress_image(image_bytes: bytes, filename: str = "image.jpg") -> tuple[bytes, str]:
    """
    Comprime una imagen para reducir su tamaño.
    
    Args:
        image_bytes: Bytes de la imagen original
        filename: Nombre del archivo original
    
    Returns:
        tuple: (bytes comprimidos, nuevo nombre de archivo)
    """
    try:
        # Abrir imagen
        img = Image.open(BytesIO(image_bytes))
        
        # Convertir a RGB si es necesario (para JPEG)
        if img.mode in ('RGBA', 'P', 'LA'):
            # Crear fondo blanco para transparencias
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Redimensionar si es muy grande
        original_size = img.size
        img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
        
        if img.size != original_size:
            logger.info(f"Imagen redimensionada de {original_size} a {img.size}")
        
        # Comprimir a JPEG
        output = BytesIO()
        quality = JPEG_QUALITY
        
        # Intentar comprimir hasta alcanzar el tamaño objetivo
        for attempt in range(3):
            output.seek(0)
            output.truncate()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            size_kb = output.tell() / 1024
            
            if size_kb <= MAX_FILE_SIZE_KB:
                break
            
            # Reducir calidad si es necesario
            quality -= 15
            if quality < 30:
                quality = 30
                break
        
        output.seek(0)
        compressed_bytes = output.read()
        
        # Cambiar extensión a .jpg
        new_filename = filename.rsplit('.', 1)[0] + '.jpg' if '.' in filename else filename + '.jpg'
        
        original_kb = len(image_bytes) / 1024
        compressed_kb = len(compressed_bytes) / 1024
        reduction = (1 - compressed_kb / original_kb) * 100 if original_kb > 0 else 0
        
        logger.info(f"Imagen comprimida: {original_kb:.1f}KB -> {compressed_kb:.1f}KB ({reduction:.1f}% reducción)")
        
        return compressed_bytes, new_filename
        
    except Exception as e:
        logger.warning(f"Error comprimiendo imagen, usando original: {e}")
        return image_bytes, filename


def is_image(filename: str) -> bool:
    """Verifica si el archivo es una imagen por su extensión."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
    ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in image_extensions

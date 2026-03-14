"""
Servicio de Cloudinary para almacenamiento permanente de imágenes
Las imágenes se organizan por orden de trabajo y nunca se eliminan
"""
import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
from typing import Optional
from fastapi import UploadFile
import uuid

# Configurar Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

async def upload_image(
    file: UploadFile,
    orden_id: str,
    tipo: str = "general",
    numero_orden: str = None
) -> dict:
    """
    Sube una imagen a Cloudinary y retorna la información.
    
    Args:
        file: Archivo a subir
        orden_id: ID de la orden de trabajo
        tipo: Tipo de foto (antes, despues, general, admin)
        numero_orden: Número de orden para organizar carpetas
    
    Returns:
        dict con url, public_id, y metadata
    """
    try:
        # Leer contenido del archivo
        contents = await file.read()
        
        # Generar nombre único
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{tipo}_{unique_id}"
        
        # Organizar en carpetas: revix/ordenes/{numero_orden}/{tipo}/
        folder = f"revix/ordenes/{numero_orden or orden_id}/{tipo}"
        
        # Subir a Cloudinary
        result = cloudinary.uploader.upload(
            contents,
            folder=folder,
            public_id=filename,
            resource_type="image",
            overwrite=False,  # No sobrescribir si existe
            invalidate=False,  # No invalidar caché
            # Transformaciones automáticas para optimizar
            transformation=[
                {"quality": "auto:good", "fetch_format": "auto"}
            ]
        )
        
        return {
            "success": True,
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "width": result.get("width"),
            "height": result.get("height"),
            "format": result.get("format"),
            "bytes": result.get("bytes"),
            "created_at": result.get("created_at")
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        # Resetear posición del archivo por si se necesita de nuevo
        await file.seek(0)


def get_download_url(public_id: str, as_attachment: bool = True) -> str:
    """
    Genera URL de descarga para una imagen.
    
    Args:
        public_id: ID público de Cloudinary
        as_attachment: Si debe forzar descarga
    
    Returns:
        URL de descarga
    """
    options = {
        "resource_type": "image",
        "type": "upload",
        "secure": True
    }
    
    if as_attachment:
        options["flags"] = "attachment"
    
    url, _ = cloudinary.utils.cloudinary_url(public_id, **options)
    return url


def get_optimized_url(url: str, width: int = None, height: int = None) -> str:
    """
    Genera URL optimizada con transformaciones.
    """
    if not url or "cloudinary" not in url:
        return url
    
    # Añadir transformaciones a la URL existente
    transformations = "f_auto,q_auto"
    if width:
        transformations += f",w_{width}"
    if height:
        transformations += f",h_{height}"
    
    # Insertar transformaciones en la URL
    parts = url.split("/upload/")
    if len(parts) == 2:
        return f"{parts[0]}/upload/{transformations}/{parts[1]}"
    
    return url


async def upload_multiple_images(
    files: list,
    orden_id: str,
    tipo: str,
    numero_orden: str = None
) -> list:
    """
    Sube múltiples imágenes a Cloudinary.
    
    Returns:
        Lista de resultados de cada subida
    """
    results = []
    for file in files:
        result = await upload_image(file, orden_id, tipo, numero_orden)
        results.append(result)
    return results


def is_cloudinary_url(url: str) -> bool:
    """Verifica si una URL es de Cloudinary"""
    return url and "cloudinary.com" in url


def extract_public_id(url: str) -> Optional[str]:
    """Extrae el public_id de una URL de Cloudinary"""
    if not is_cloudinary_url(url):
        return None
    
    try:
        # URL format: https://res.cloudinary.com/{cloud}/image/upload/{transformations}/{public_id}.{ext}
        parts = url.split("/upload/")
        if len(parts) == 2:
            # Quitar extensión y transformaciones
            path = parts[1]
            # Quitar extensión
            if "." in path:
                path = path.rsplit(".", 1)[0]
            # Si hay transformaciones (empiezan con f_, q_, w_, etc), saltarlas
            segments = path.split("/")
            # Buscar el inicio del public_id real (después de las transformaciones)
            for i, seg in enumerate(segments):
                if not any(seg.startswith(p) for p in ["f_", "q_", "w_", "h_", "c_", "g_"]):
                    return "/".join(segments[i:])
            return path
    except:
        pass
    return None

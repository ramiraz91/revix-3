"""
Rutas para el sistema de impresion Brother QL-800.
- Descarga del agente local como ZIP.
"""

import os
import io
import zipfile
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/print", tags=["print"])

AGENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "brother-label-agent")

# Archivos que se incluyen en el ZIP del agente
AGENT_FILES = [
    "agent.py",
    "label_generator.py",
    "printer_service.py",
    "config.json",
    "requirements.txt",
    "install.bat",
    "start.bat",
    "README.md",
]


@router.get("/agent/download")
async def download_agent():
    """Descarga el agente de impresion Brother como archivo ZIP."""
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename in AGENT_FILES:
            filepath = os.path.join(AGENT_DIR, filename)
            if os.path.exists(filepath):
                zf.write(filepath, f"brother-label-agent/{filename}")

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=brother-label-agent.zip"
        },
    )


@router.get("/agent/status")
async def agent_info():
    """Informacion del agente disponible para descarga."""
    return {
        "version": "1.0.0",
        "label_format": "DK-11204",
        "label_size": "17mm x 54mm",
        "printer": "Brother QL-800",
        "agent_port": 5555,
        "download_url": "/api/print/agent/download",
    }

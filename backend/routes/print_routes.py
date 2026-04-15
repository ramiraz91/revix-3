"""
Sistema centralizado de impresion Brother QL-800.

Arquitectura:
  Frontend (cualquier dispositivo)
    -> POST /api/print/send  (Backend CRM, autenticado JWT)
    -> Backend guarda job en MongoDB (print_jobs, status=pending)
    -> Agente del taller hace polling GET /api/print/pending
    -> Agente imprime y reporta POST /api/print/complete
    -> Frontend consulta estado via GET /api/print/status

Colecciones MongoDB:
  - print_jobs:   Cola de trabajos de impresion
  - print_agents: Heartbeat y estado del agente
"""

import os
import io
import zipfile
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends, Query, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from config import db
from auth import require_auth

router = APIRouter(prefix="/print", tags=["print"])

AGENT_KEY = os.environ.get("BROTHER_AGENT_KEY", "")
AGENT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "brother-label-agent",
)
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

# ── Helpers ──────────────────────────────────────────────────────────

def _verify_agent_key(x_agent_key: str = Header(None)):
    if not AGENT_KEY:
        raise HTTPException(503, "BROTHER_AGENT_KEY no configurada en el servidor")
    if x_agent_key != AGENT_KEY:
        raise HTTPException(403, "Agent key invalida")
    return True


def _now():
    return datetime.now(timezone.utc)


# ── Models ───────────────────────────────────────────────────────────

class PrintJobRequest(BaseModel):
    template: str = "ot_barcode_minimal"
    data: dict = {}

class JobCompleteRequest(BaseModel):
    job_id: str
    status: str  # "completed" | "error"
    error_message: Optional[str] = None

class HeartbeatRequest(BaseModel):
    agent_id: str
    printer_online: bool = False
    printer_name: str = ""
    reason: str = ""


# ═══════════════════════════════════════════════════════════════════
#  FRONTEND ENDPOINTS (requieren JWT)
# ═══════════════════════════════════════════════════════════════════

@router.post("/send")
async def send_print_job(body: PrintJobRequest, user=Depends(require_auth)):
    """Envia un trabajo de impresion a la cola."""
    job_id = f"pj-{_now().strftime('%Y%m%d%H%M%S')}-{user.get('user_id','x')[:8]}"

    job = {
        "job_id": job_id,
        "template": body.template,
        "data": body.data,
        "status": "pending",
        "error_message": None,
        "requested_by": user.get("email", ""),
        "requested_by_name": user.get("nombre", user.get("email", "")),
        "requested_at": _now().isoformat(),
        "printed_at": None,
        "printer_name": "Brother QL-800",
    }

    await db.print_jobs.insert_one(job)

    return {
        "ok": True,
        "job_id": job_id,
        "status": "pending",
        "message": "Trabajo enviado a la cola de impresion",
    }


@router.get("/status")
async def print_status(user=Depends(require_auth)):
    """Estado del agente y la impresora (consultado por el frontend)."""
    agent = await db.print_agents.find_one(
        {}, {"_id": 0}, sort=[("last_heartbeat", -1)]
    )

    if not agent:
        return {
            "ok": True,
            "agent_connected": False,
            "printer_online": False,
            "message": "Ningun agente registrado. Instale el agente en el PC del taller.",
        }

    last_hb = agent.get("last_heartbeat", "")
    if isinstance(last_hb, str):
        try:
            last_hb_dt = datetime.fromisoformat(last_hb.replace("Z", "+00:00"))
        except Exception:
            last_hb_dt = _now() - timedelta(hours=1)
    else:
        last_hb_dt = last_hb

    stale = (_now() - last_hb_dt) > timedelta(seconds=30)

    return {
        "ok": True,
        "agent_connected": not stale,
        "printer_online": agent.get("printer_online", False) and not stale,
        "printer_name": agent.get("printer_name", ""),
        "agent_id": agent.get("agent_id", ""),
        "last_heartbeat": agent.get("last_heartbeat", ""),
        "reason": agent.get("reason", "") if not stale else "Agente sin respuesta",
        "message": "" if not stale else "El agente no responde. Verifique que start.bat esta ejecutandose.",
    }


@router.get("/jobs")
async def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    user=Depends(require_auth),
):
    """Historial de trabajos de impresion."""
    cursor = db.print_jobs.find(
        {}, {"_id": 0}
    ).sort("requested_at", -1).limit(limit)

    jobs = await cursor.to_list(length=limit)
    return {"ok": True, "jobs": jobs}


@router.get("/job/{job_id}")
async def get_job(job_id: str, user=Depends(require_auth)):
    """Estado de un trabajo concreto."""
    job = await db.print_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")
    return {"ok": True, "job": job}


# ═══════════════════════════════════════════════════════════════════
#  AGENT ENDPOINTS (requieren Agent Key)
# ═══════════════════════════════════════════════════════════════════

@router.get("/pending")
async def get_pending_jobs(
    agent_key: str = Query(...),
    agent_id: str = Query("default"),
):
    """El agente del taller consulta trabajos pendientes."""
    if agent_key != AGENT_KEY:
        raise HTTPException(403, "Agent key invalida")

    cursor = db.print_jobs.find(
        {"status": "pending"}, {"_id": 0}
    ).sort("requested_at", 1).limit(10)

    jobs = await cursor.to_list(length=10)

    # Marcar como "printing" para evitar doble procesamiento
    for job in jobs:
        await db.print_jobs.update_one(
            {"job_id": job["job_id"], "status": "pending"},
            {"$set": {"status": "printing"}},
        )

    return {"ok": True, "jobs": jobs}


@router.post("/complete")
async def complete_job(body: JobCompleteRequest, x_agent_key: str = Header(None)):
    """El agente reporta que termino un trabajo."""
    if x_agent_key != AGENT_KEY:
        raise HTTPException(403, "Agent key invalida")

    update = {
        "status": body.status,
        "printed_at": _now().isoformat() if body.status == "completed" else None,
        "error_message": body.error_message,
    }

    result = await db.print_jobs.update_one(
        {"job_id": body.job_id},
        {"$set": update},
    )

    if result.matched_count == 0:
        raise HTTPException(404, "Trabajo no encontrado")

    return {"ok": True, "job_id": body.job_id, "status": body.status}


@router.post("/heartbeat")
async def agent_heartbeat(body: HeartbeatRequest, x_agent_key: str = Header(None)):
    """El agente envia heartbeat periodico."""
    if x_agent_key != AGENT_KEY:
        raise HTTPException(403, "Agent key invalida")

    await db.print_agents.update_one(
        {"agent_id": body.agent_id},
        {
            "$set": {
                "agent_id": body.agent_id,
                "last_heartbeat": _now().isoformat(),
                "printer_online": body.printer_online,
                "printer_name": body.printer_name,
                "reason": body.reason,
            }
        },
        upsert=True,
    )

    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════
#  AGENT DOWNLOAD
# ═══════════════════════════════════════════════════════════════════

@router.get("/agent/download")
async def download_agent():
    """Descarga el agente de impresion Brother como ZIP."""
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
        headers={"Content-Disposition": "attachment; filename=brother-label-agent.zip"},
    )


@router.get("/agent/info")
async def agent_info():
    """Informacion del agente disponible."""
    return {
        "version": "1.0.0",
        "label_format": "DK-11204",
        "label_size": "17mm x 54mm",
        "printer": "Brother QL-800",
        "download_url": "/api/print/agent/download",
    }

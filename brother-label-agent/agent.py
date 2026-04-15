"""
Brother Label Agent v2.1.0 — Produccion
Agente centralizado de impresion para Brother QL-800.
Formato: DK-11204 (17mm x 54mm)

Servidor: Waitress (produccion, Windows-compatible)
"""
import os
import sys
import json
import logging
import logging.handlers
import traceback
import threading
import time
import queue

from datetime import datetime, timezone

import requests as http_client
from flask import Flask, request, jsonify
from flask_cors import CORS

from label_generator import LabelGenerator
from printer_service import PrinterService

# -------------------------------------------------------------------
# Configuracion
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


config = load_config()
PORT = config.get("port", 5555)
HOST = config.get("host", "0.0.0.0")
DEFAULT_PRINTER = config.get("default_printer", "Brother QL-800")
CRM_URL = config.get("crm_url", "")
AGENT_KEY = config.get("agent_key", "")
AGENT_ID = config.get("agent_id", "taller-principal")
POLL_INTERVAL = config.get("poll_interval", 3)
HEARTBEAT_INTERVAL = config.get("heartbeat_interval", 10)
ALLOWED_ORIGINS = config.get("allowed_origins", [])

# -------------------------------------------------------------------
# Logging con rotacion
# -------------------------------------------------------------------
LOG_PATH = os.path.join(BASE_DIR, "agent.log")

log = logging.getLogger("brother-agent")
log.setLevel(logging.INFO)

# Rotacion: max 5 MB por archivo, 3 archivos de backup
file_handler = logging.handlers.RotatingFileHandler(
    LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(console_handler)

# Silenciar logs de waitress excepto errores
logging.getLogger("waitress").setLevel(logging.ERROR)

# -------------------------------------------------------------------
# Servicios
# -------------------------------------------------------------------
printer = PrinterService(DEFAULT_PRINTER)
label_gen = LabelGenerator()

# Cola interna para serializar impresiones (evita conflictos en spooler)
print_queue = queue.Queue(maxsize=50)


# ===================================================================
#  PRINT WORKER — Procesa la cola interna de impresion
# ===================================================================
class PrintWorker(threading.Thread):
    """Hilo dedicado a procesar trabajos de impresion en orden."""

    def __init__(self):
        super().__init__(daemon=True, name="PrintWorker")
        self.running = True
        self._last_error = None
        self._jobs_printed = 0

    def run(self):
        log.info("PrintWorker iniciado")
        while self.running:
            try:
                job = print_queue.get(timeout=1)
            except queue.Empty:
                continue

            job_id = job.get("job_id", "?")
            template = job.get("template", "ot_barcode_minimal")
            label_data = job.get("data", {})
            callback = job.get("callback")  # funcion para reportar resultado
            status = "completed"
            error_msg = None

            try:
                if template == "inventory_label":
                    img = label_gen.generate_inventory_label(
                        barcode_value=label_data.get("barcodeValue", ""),
                        product_name=label_data.get("productName", ""),
                        price=label_data.get("price", ""),
                    )
                else:
                    img = label_gen.generate_ot_label(
                        barcode_value=label_data.get("barcodeValue", ""),
                        order_number=label_data.get("orderNumber", ""),
                        device_model=label_data.get("deviceModel", ""),
                    )

                printer.print_image(img, DEFAULT_PRINTER)
                self._jobs_printed += 1
                self._last_error = None
                log.info("IMPRESO  job=%s  template=%s  total=%d", job_id, template, self._jobs_printed)

            except Exception as exc:
                status = "error"
                error_msg = str(exc)
                self._last_error = error_msg
                log.error("ERROR  job=%s: %s", job_id, exc)

            # Reportar resultado
            if callback:
                try:
                    callback(job_id, status, error_msg)
                except Exception:
                    pass

            print_queue.task_done()

    @property
    def stats(self):
        return {
            "queue_size": print_queue.qsize(),
            "jobs_printed": self._jobs_printed,
            "last_error": self._last_error,
        }


# ===================================================================
#  CRM POLLER — Obtiene trabajos del CRM
# ===================================================================
class PrintJobPoller(threading.Thread):
    """Consulta el backend CRM por trabajos pendientes."""

    def __init__(self):
        super().__init__(daemon=True, name="CRM-Poller")
        self.running = True
        self._consecutive_errors = 0
        self._last_poll_ok = False

    def run(self):
        if not CRM_URL or not AGENT_KEY:
            log.warning("CRM_URL o AGENT_KEY no configurados. Polling desactivado.")
            return
        log.info("Polling activo -> %s (cada %ds)", CRM_URL, POLL_INTERVAL)

        while self.running:
            try:
                self._poll()
                self._consecutive_errors = 0
                self._last_poll_ok = True
            except Exception as exc:
                self._consecutive_errors += 1
                self._last_poll_ok = False
                if self._consecutive_errors <= 3 or self._consecutive_errors % 20 == 0:
                    log.error("Error polling (x%d): %s", self._consecutive_errors, exc)

            # Backoff: si hay errores consecutivos, esperar mas
            wait = POLL_INTERVAL
            if self._consecutive_errors > 5:
                wait = min(POLL_INTERVAL * 3, 15)
            time.sleep(wait)

    def _poll(self):
        url = f"{CRM_URL}/api/print/pending"
        params = {"agent_key": AGENT_KEY, "agent_id": AGENT_ID}

        resp = http_client.get(url, params=params, timeout=10)
        if resp.status_code == 403:
            raise Exception("Agent key rechazada por el servidor")
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}")

        data = resp.json()
        jobs = data.get("jobs", [])

        for job in jobs:
            job["callback"] = self._report_result
            try:
                print_queue.put_nowait(job)
            except queue.Full:
                log.error("Cola de impresion llena. Descartando job %s", job.get("job_id"))
                self._report_result(job.get("job_id", "?"), "error", "Cola de impresion llena")

    def _report_result(self, job_id, status, error_message):
        try:
            http_client.post(
                f"{CRM_URL}/api/print/complete",
                json={
                    "job_id": job_id,
                    "status": status,
                    "error_message": error_message,
                },
                headers={"X-Agent-Key": AGENT_KEY},
                timeout=10,
            )
        except Exception as exc:
            log.error("No se pudo reportar resultado de %s: %s", job_id, exc)

    @property
    def connected(self):
        return self._last_poll_ok


# ===================================================================
#  HEARTBEAT
# ===================================================================
class HeartbeatSender(threading.Thread):
    """Envia heartbeat periodico al CRM."""

    def __init__(self):
        super().__init__(daemon=True, name="Heartbeat")
        self.running = True

    def run(self):
        if not CRM_URL or not AGENT_KEY:
            return
        log.info("Heartbeat activo (cada %ds)", HEARTBEAT_INTERVAL)

        while self.running:
            try:
                status = printer.check_status()
                http_client.post(
                    f"{CRM_URL}/api/print/heartbeat",
                    json={
                        "agent_id": AGENT_ID,
                        "printer_online": status.get("online", False),
                        "printer_name": DEFAULT_PRINTER,
                        "reason": status.get("reason", ""),
                    },
                    headers={"X-Agent-Key": AGENT_KEY},
                    timeout=10,
                )
            except Exception:
                pass
            time.sleep(HEARTBEAT_INTERVAL)


# ===================================================================
#  FLASK APP
# ===================================================================
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


@app.after_request
def add_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-Agent-Key"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Server"] = "BrotherLabelAgent/2.1"
    return response


@app.route("/health", methods=["GET"])
def health():
    try:
        status = printer.check_status()
        return jsonify({
            "ok": True,
            "service": "brother-label-agent",
            "version": "2.1.0",
            "mode": "centralized" if CRM_URL else "local-only",
            "printerConfigured": True,
            "printerOnline": status["online"],
            "defaultPrinter": DEFAULT_PRINTER,
            "labelFormat": "DK-11204 (17mm x 54mm)",
            "crm_connected": poller.connected if CRM_URL else False,
            "queue": print_worker.stats,
            "reason": status.get("reason", ""),
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/printers", methods=["GET"])
def list_printers():
    try:
        return jsonify({"ok": True, "printers": printer.list_printers()})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/print", methods=["POST", "OPTIONS"])
def local_print():
    """Impresion local directa (fallback si el CRM no esta configurado)."""
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200

    data = request.json or {}
    job_id = data.get("jobId", f"local-{datetime.now().strftime('%H%M%S')}")

    result = {"status": None, "error": None}
    event = threading.Event()

    def on_complete(jid, status, error):
        result["status"] = status
        result["error"] = error
        event.set()

    job = {
        "job_id": job_id,
        "template": data.get("template", "ot_barcode_minimal"),
        "data": data.get("data", {}),
        "callback": on_complete,
    }

    try:
        print_queue.put_nowait(job)
    except queue.Full:
        return jsonify({"ok": False, "error": "Cola de impresion llena"}), 503

    # Esperar resultado (max 30s)
    event.wait(timeout=30)

    if result["status"] == "completed":
        return jsonify({
            "ok": True,
            "jobId": job_id,
            "printed": True,
            "printer": DEFAULT_PRINTER,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    elif result["status"] == "error":
        return jsonify({"ok": False, "jobId": job_id, "printed": False, "error": result["error"]}), 500
    else:
        return jsonify({"ok": False, "jobId": job_id, "printed": False, "error": "Timeout esperando impresion"}), 504


@app.route("/test-print", methods=["POST", "OPTIONS"])
def test_print():
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200
    try:
        img = label_gen.generate_test_label()
        printer.print_image(img, DEFAULT_PRINTER)
        return jsonify({"ok": True, "printed": True})
    except Exception as exc:
        return jsonify({"ok": False, "printed": False, "error": str(exc)}), 500


# ===================================================================
#  MAIN
# ===================================================================

# Iniciar hilos de trabajo
print_worker = PrintWorker()
poller = PrintJobPoller()
heartbeat = HeartbeatSender()


def main():
    log.info("=" * 60)
    log.info("Brother Label Agent v2.1.0 — Produccion")
    log.info("Impresora: %s", DEFAULT_PRINTER)
    log.info("Formato:   DK-11204 (17mm x 54mm)")
    log.info("Servidor:  Waitress (produccion)")
    log.info("Escuchando: %s:%s", HOST, PORT)

    if CRM_URL:
        log.info("CRM URL:   %s", CRM_URL)
        log.info("Agent ID:  %s", AGENT_ID)
    else:
        log.info("MODO LOCAL — CRM no configurado")

    log.info("=" * 60)

    # Iniciar hilos
    print_worker.start()
    poller.start()
    heartbeat.start()

    # Servidor de produccion
    try:
        from waitress import serve
        log.info("Servidor Waitress iniciado en %s:%s", HOST, PORT)
        serve(app, host=HOST, port=PORT, threads=4, channel_timeout=30)
    except ImportError:
        log.warning("waitress no instalado. Usando servidor de desarrollo.")
        log.warning("Instale: pip install waitress")
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()

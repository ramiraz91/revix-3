"""
Brother Label Agent v2.0.0
Agente centralizado de impresion para Brother QL-800.
Formato: DK-11204 (17mm x 54mm)

Arquitectura:
  - Hace polling al backend CRM para obtener trabajos pendientes.
  - Envia heartbeat periodico para que el CRM sepa que esta vivo.
  - Tambien expone servidor HTTP local (fallback/testing).
"""
import os
import sys
import json
import logging
import traceback
import threading
import time

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
DEFAULT_PRINTER = config.get("default_printer", "Brother QL-800")
CRM_URL = config.get("crm_url", "")
AGENT_KEY = config.get("agent_key", "")
AGENT_ID = config.get("agent_id", "taller-principal")
POLL_INTERVAL = config.get("poll_interval", 3)
HEARTBEAT_INTERVAL = config.get("heartbeat_interval", 10)

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
LOG_PATH = os.path.join(BASE_DIR, "agent.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("brother-agent")

# -------------------------------------------------------------------
# Servicios
# -------------------------------------------------------------------
printer = PrinterService(DEFAULT_PRINTER)
label_gen = LabelGenerator()


# ===================================================================
#  POLLING CLIENT — Obtiene trabajos del CRM y los imprime
# ===================================================================
class PrintJobPoller:
    """Consulta el backend CRM por trabajos pendientes y los imprime."""

    def __init__(self):
        self.running = False
        self._thread = None

    def start(self):
        if not CRM_URL or not AGENT_KEY:
            log.warning(
                "CRM_URL o AGENT_KEY no configurados. "
                "El polling esta desactivado. Solo modo local."
            )
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("Polling activo -> %s (cada %ds)", CRM_URL, POLL_INTERVAL)

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                self._poll()
            except Exception:
                log.error("Error en ciclo de polling:\n%s", traceback.format_exc())
            time.sleep(POLL_INTERVAL)

    def _poll(self):
        url = f"{CRM_URL}/api/print/pending"
        params = {"agent_key": AGENT_KEY, "agent_id": AGENT_ID}

        resp = http_client.get(url, params=params, timeout=10)
        if resp.status_code == 403:
            log.error("Agent key rechazada por el servidor. Verifique config.json")
            return
        if resp.status_code != 200:
            return

        data = resp.json()
        jobs = data.get("jobs", [])

        for job in jobs:
            self._process(job)

    def _process(self, job):
        job_id = job.get("job_id", "?")
        template = job.get("template", "ot_barcode_minimal")
        label_data = job.get("data", {})
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
            log.info("IMPRESO  job=%s  template=%s", job_id, template)

        except Exception as exc:
            status = "error"
            error_msg = str(exc)
            log.error("ERROR  job=%s: %s", job_id, exc)

        # Reportar resultado al CRM
        try:
            http_client.post(
                f"{CRM_URL}/api/print/complete",
                json={
                    "job_id": job_id,
                    "status": status,
                    "error_message": error_msg,
                },
                headers={"X-Agent-Key": AGENT_KEY},
                timeout=10,
            )
        except Exception as exc:
            log.error("No se pudo reportar resultado de %s: %s", job_id, exc)


# ===================================================================
#  HEARTBEAT — Informa al CRM que el agente esta vivo
# ===================================================================
class HeartbeatSender:
    def __init__(self):
        self.running = False
        self._thread = None

    def start(self):
        if not CRM_URL or not AGENT_KEY:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("Heartbeat activo (cada %ds)", HEARTBEAT_INTERVAL)

    def stop(self):
        self.running = False

    def _loop(self):
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
                pass  # Silencioso — se reintenta en el siguiente ciclo
            time.sleep(HEARTBEAT_INTERVAL)


# ===================================================================
#  FLASK — Servidor HTTP local (fallback y testing)
# ===================================================================
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-Agent-Key"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


@app.route("/health", methods=["GET"])
def health():
    try:
        status = printer.check_status()
        return jsonify({
            "ok": True,
            "service": "brother-label-agent",
            "version": "2.0.0",
            "mode": "centralized" if CRM_URL else "local-only",
            "printerConfigured": True,
            "printerOnline": status["online"],
            "defaultPrinter": DEFAULT_PRINTER,
            "labelFormat": "DK-11204 (17mm x 54mm)",
            "crm_connected": bool(CRM_URL),
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
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200

    data = request.json or {}
    job_id = data.get("jobId", f"local-{datetime.now().strftime('%H%M%S')}")
    template = data.get("template", "ot_barcode_minimal")
    label_data = data.get("data", {})

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

        printer.print_image(img, data.get("printerName", DEFAULT_PRINTER))
        log.info("LOCAL PRINT OK  job=%s", job_id)

        return jsonify({
            "ok": True,
            "jobId": job_id,
            "printed": True,
            "printer": DEFAULT_PRINTER,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        log.error("LOCAL PRINT FAIL  job=%s: %s", job_id, traceback.format_exc())
        return jsonify({"ok": False, "jobId": job_id, "printed": False, "error": str(exc)}), 500


@app.route("/test-print", methods=["POST", "OPTIONS"])
def test_print():
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200
    try:
        img = label_gen.generate_test_label()
        printer.print_image(img, DEFAULT_PRINTER)
        log.info("TEST PRINT OK")
        return jsonify({"ok": True, "printed": True})
    except Exception as exc:
        log.error("TEST PRINT FAIL: %s", traceback.format_exc())
        return jsonify({"ok": False, "printed": False, "error": str(exc)}), 500


# ===================================================================
#  MAIN
# ===================================================================
if __name__ == "__main__":
    log.info("=" * 60)
    log.info("Brother Label Agent v2.0.0 — Centralizado")
    log.info("Impresora: %s", DEFAULT_PRINTER)
    log.info("Formato:   DK-11204 (17mm x 54mm)")
    log.info("Puerto local: %s", PORT)

    if CRM_URL:
        log.info("CRM URL:   %s", CRM_URL)
        log.info("Agent ID:  %s", AGENT_ID)
    else:
        log.info("MODO LOCAL — CRM no configurado")

    log.info("=" * 60)

    # Iniciar polling y heartbeat
    poller = PrintJobPoller()
    heartbeat = HeartbeatSender()
    poller.start()
    heartbeat.start()

    # Iniciar servidor HTTP local
    try:
        app.run(host="0.0.0.0", port=PORT, debug=False)
    except KeyboardInterrupt:
        poller.stop()
        heartbeat.stop()
        log.info("Agente detenido")

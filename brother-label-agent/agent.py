"""
Brother Label Agent v1.0.0
Agente local para impresion directa en Brother QL-800
Formato: DK-11204 (17mm x 54mm)
"""
import os
import sys
import json
import logging
import traceback
from datetime import datetime, timezone

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

# -------------------------------------------------------------------
# Flask app
# -------------------------------------------------------------------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


# ======================== ENDPOINTS ================================

@app.route("/health", methods=["GET"])
def health():
    try:
        status = printer.check_status()
        return jsonify({
            "ok": True,
            "service": "brother-label-agent",
            "version": "1.0.0",
            "printerConfigured": True,
            "printerOnline": status["online"],
            "defaultPrinter": DEFAULT_PRINTER,
            "labelFormat": "DK-11204 (17mm x 54mm)",
            "reason": status.get("reason", ""),
        })
    except Exception as exc:
        log.error("health check error: %s", traceback.format_exc())
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/printers", methods=["GET"])
def list_printers():
    try:
        printers = printer.list_printers()
        return jsonify({"ok": True, "printers": printers})
    except Exception as exc:
        log.error("list printers error: %s", traceback.format_exc())
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/print", methods=["POST", "OPTIONS"])
def print_label():
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200

    data = request.json or {}
    job_id = data.get("jobId", f"job-{datetime.now().strftime('%H%M%S')}")
    template = data.get("template", "ot_barcode_minimal")
    printer_name = data.get("printerName", DEFAULT_PRINTER)
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

        printer.print_image(img, printer_name)
        log.info("OK  template=%s  job=%s  printer=%s", template, job_id, printer_name)

        return jsonify({
            "ok": True,
            "jobId": job_id,
            "printed": True,
            "printer": printer_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        log.error("PRINT FAIL  job=%s: %s", job_id, traceback.format_exc())
        return jsonify({
            "ok": False,
            "jobId": job_id,
            "printed": False,
            "error": str(exc),
        }), 500


@app.route("/test-print", methods=["POST", "OPTIONS"])
def test_print():
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200

    data = request.json or {}
    printer_name = data.get("printerName", DEFAULT_PRINTER)

    try:
        img = label_gen.generate_test_label()
        printer.print_image(img, printer_name)
        log.info("TEST PRINT OK  printer=%s", printer_name)
        return jsonify({"ok": True, "printed": True})
    except Exception as exc:
        log.error("TEST PRINT FAIL: %s", traceback.format_exc())
        return jsonify({"ok": False, "printed": False, "error": str(exc)}), 500


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
if __name__ == "__main__":
    log.info("=" * 60)
    log.info("Brother Label Agent v1.0.0")
    log.info("Puerto: %s", PORT)
    log.info("Impresora por defecto: %s", DEFAULT_PRINTER)
    log.info("Formato de etiqueta: DK-11204 (17mm x 54mm)")
    log.info("=" * 60)
    app.run(host="127.0.0.1", port=PORT, debug=False)

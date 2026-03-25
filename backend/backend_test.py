#!/usr/bin/env python3
"""
backend_test.py — Tests de la API del CRM
Ejecutar con: python backend_test.py
"""

import requests
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://backend-perf-test.preview.emergentagent.com")
ADMIN_USER = os.getenv("ADMIN_USERNAME", "ramiraz91@gmail.com")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "@100918Vm")


class MobileRepairAPITester:

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.token: Optional[str] = None

        self.test_data: Dict[str, Optional[str]] = {
            "cliente_id": None,
            "proveedor_id": None,
            "repuesto_id": None,
            "orden_id": None,
        }

        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests: list = []

    def log_test(self, name: str, success: bool, details: str = "") -> None:
        self.tests_run += 1
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"   {details}")
        if success:
            self.tests_passed += 1
        else:
            self.failed_tests.append(f"{name}: {details}")
        print()

    def make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        expected_status: int = 200,
        params: Optional[Dict] = None,
    ) -> tuple:
        url = f"{self.api_url}/{endpoint}"

        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})

        try:
            method = method.upper()
            if method == "GET":
                response = self.session.get(url, params=params)
            elif method == "POST":
                response = self.session.post(url, json=data)
            elif method == "PUT":
                response = self.session.put(url, json=data)
            elif method == "PATCH":
                response = self.session.patch(url, json=data, params=params)
            elif method == "DELETE":
                response = self.session.delete(url)
            else:
                return False, {"error": f"Método no soportado: {method}"}

            success = response.status_code == expected_status

            try:
                response_data = response.json()
            except (json.JSONDecodeError, ValueError):
                response_data = {
                    "status_code": response.status_code,
                    "text": response.text,
                }

            return success, response_data

        except requests.exceptions.ConnectionError:
            return False, {"error": f"No se pudo conectar a {url}"}
        except Exception as e:
            return False, {"error": str(e)}

    def login(self, username: str, password: str) -> bool:
        success, response = self.make_request(
            "POST", "auth/login", {"email": username, "password": password}
        )
        if success and "token" in response:
            self.token = response["token"]
            return True
        return False

    def test_login(self) -> None:
        ok = self.login(ADMIN_USER, ADMIN_PASS)
        self.log_test(
            "Login como admin",
            ok,
            "Token obtenido correctamente" if ok else "Fallo en login",
        )

    def test_health(self) -> None:
        success, response = self.make_request("GET", "health")
        self.log_test(
            "API Health Check",
            success and response.get("status") == "ok",
            f"Status: {response.get('status')}" if success else str(response),
        )

    def test_dashboard_stats(self) -> None:
        success, response = self.make_request("GET", "dashboard/stats")
        if not success:
            self.log_test("Dashboard Stats", False, f"Petición fallida: {response}")
            return

        required = ["ordenes_por_estado", "total_ordenes"]
        missing = [f for f in required if f not in response]
        ok = not missing
        self.log_test(
            "Dashboard Stats",
            ok,
            "Campos presentes" if ok else f"Campos ausentes: {missing}",
        )

    def test_inventario_alertas(self) -> None:
        success, response = self.make_request("GET", "inventario/alertas")
        self.log_test(
            "Inventario - Alertas de stock",
            success and "alertas" in response,
            f"Total alertas: {response.get('total_alertas', 0)}" if success else str(response),
        )

    def test_ordenes_estados_validos(self) -> None:
        success, response = self.make_request("GET", "ordenes-v2/estados-validos")
        self.log_test(
            "Órdenes - Estados válidos",
            success and "estados" in response and "transiciones" in response,
            f"Estados: {len(response.get('estados', []))}" if success else str(response),
        )

    def test_ordenes_alertas_retraso(self) -> None:
        success, response = self.make_request("GET", "ordenes-v2/alertas-retraso")
        self.log_test(
            "Órdenes - Alertas de retraso",
            success and "ordenes_retrasadas" in response,
            f"Retrasadas: {response.get('total_retrasadas', 0)}" if success else str(response),
        )

    def run_all_tests(self) -> bool:
        print("🚀 Mobile Repair CRM/ERP — Tests de Backend")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 60)

        self.test_health()
        self.test_login()
        self.test_dashboard_stats()
        self.test_inventario_alertas()
        self.test_ordenes_estados_validos()
        self.test_ordenes_alertas_retraso()

        print("=" * 60)
        total = self.tests_run
        passed = self.tests_passed
        failed = total - passed
        print(f"📊 RESUMEN: {passed}/{total} pasados — {failed} fallidos")
        print(f"   Tasa de éxito: {passed / total * 100:.1f}%" if total else "")

        if self.failed_tests:
            print("\n❌ Tests fallidos:")
            for t in self.failed_tests:
                print(f"   • {t}")

        return failed == 0


def main() -> int:
    tester = MobileRepairAPITester()
    return 0 if tester.run_all_tests() else 1


if __name__ == "__main__":
    sys.exit(main())

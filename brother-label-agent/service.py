"""
Wrapper de servicio Windows para Brother Label Agent.
Permite instalar el agente como servicio del sistema para que:
  - Arranque automaticamente con Windows
  - Se ejecute en segundo plano sin ventana de consola
  - Se reinicie automaticamente si falla

USO:
  python service.py install   -> Instala el servicio
  python service.py start     -> Inicia el servicio
  python service.py stop      -> Detiene el servicio
  python service.py remove    -> Desinstala el servicio
  python service.py restart   -> Reinicia el servicio

REQUISITOS:
  - Ejecutar como Administrador
  - pywin32 instalado
"""

import os
import sys
import time

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
except ImportError:
    print("Error: pywin32 no instalado.")
    print("Ejecute: pip install pywin32")
    sys.exit(1)


class BrotherLabelService(win32serviceutil.ServiceFramework):
    _svc_name_ = "BrotherLabelAgent"
    _svc_display_name_ = "Brother Label Agent - Revix"
    _svc_description_ = "Agente de impresion de etiquetas Brother QL-800 para CRM Revix. DK-11204 (17x54mm)."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )

        # Cambiar al directorio del agente
        agent_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(agent_dir)
        sys.path.insert(0, agent_dir)

        # Importar y ejecutar el agente
        from agent import print_worker, poller, heartbeat, app, HOST, PORT, log

        log.info("Servicio Windows iniciado")

        print_worker.start()
        poller.start()
        heartbeat.start()

        # Ejecutar Waitress en un hilo
        import threading
        try:
            from waitress import serve
            server_thread = threading.Thread(
                target=serve,
                kwargs={"app": app, "host": HOST, "port": PORT, "threads": 4},
                daemon=True,
            )
        except ImportError:
            server_thread = threading.Thread(
                target=app.run,
                kwargs={"host": HOST, "port": PORT, "debug": False, "use_reloader": False},
                daemon=True,
            )

        server_thread.start()

        # Esperar señal de parada
        while self.running:
            rc = win32event.WaitForSingleObject(self.stop_event, 5000)
            if rc == win32event.WAIT_OBJECT_0:
                break

        log.info("Servicio Windows detenido")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Si se ejecuta sin argumentos, mostrar ayuda
        print("Brother Label Agent — Servicio Windows")
        print()
        print("Uso (ejecutar como Administrador):")
        print("  python service.py install   - Instalar servicio")
        print("  python service.py start     - Iniciar servicio")
        print("  python service.py stop      - Detener servicio")
        print("  python service.py remove    - Desinstalar servicio")
        print("  python service.py restart   - Reiniciar servicio")
        print()
        print("Una vez instalado, el agente arrancara automaticamente")
        print("con Windows y se ejecutara en segundo plano.")
    else:
        win32serviceutil.HandleCommandLine(BrotherLabelService)

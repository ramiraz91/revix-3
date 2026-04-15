# Brother Label Agent v2.1.0 — Produccion

Agente centralizado de impresion para **Brother QL-800** con etiquetas **DK-11204** (17x54mm).
Servidor de produccion **Waitress**. Listo para uso diario en taller.

---

## Arquitectura

```
  Cualquier PC/Movil (CRM)     Servidor CRM (nube)         PC Taller (Agente)
  +-------------------+        +------------------+        +--------------------+
  | "Imprimir" -------|--JWT-->| POST /print/send |        |                    |
  |                   |        |  (MongoDB cola)  |<-poll--| agent.py           |
  |                   |        |                  |        |  Waitress (prod)   |
  |                   |        | job: completed   |<-report|  PrintWorker       |
  | "Impresa OK" <----|--poll--|                  |        |  -> Brother QL-800 |
  +-------------------+        +------------------+        +--------------------+
```

- La impresion **no depende del navegador** del usuario
- Cualquier sesion autenticada del CRM puede imprimir
- Cada trabajo queda registrado: usuario, fecha, hora, resultado
- Si la impresora esta ocupada, los trabajos se encolan ordenadamente
- Si la impresora esta offline, el error se reporta al CRM y al usuario

---

## Requisitos del PC del taller

| Componente | Detalle |
|---|---|
| SO | Windows 10 / 11 |
| Python | 3.10+ |
| Impresora | Brother QL-800 (USB) |
| Driver | Driver oficial Brother QL-800 |
| Etiquetas | DK-11204 (17x54mm) |
| Internet | Si (para comunicar con el CRM) |

---

## Instalacion rapida

```cmd
cd C:\RevixAgent
install.bat
```

Edite `config.json`:
```json
{
    "port": 5555,
    "default_printer": "Brother QL-800",
    "crm_url": "https://revix.es",
    "agent_key": "revix-brother-agent-2026-key",
    "agent_id": "taller-principal",
    "poll_interval": 3,
    "heartbeat_interval": 10
}
```

---

## Modos de ejecucion

### Opcion A: Ventana de consola (simple)

```cmd
start.bat
```
- Se reinicia automaticamente si falla
- Debe mantener la ventana abierta (minimizada)
- Ideal para pruebas iniciales

### Opcion B: Servicio de Windows (recomendado para produccion)

Ejecutar **como Administrador**:

```cmd
install-service.bat
python service.py start
```

Ventajas:
- Arranca automaticamente con Windows
- Se ejecuta en segundo plano (sin ventana)
- Se reinicia automaticamente tras fallos (5s, 10s, 30s)
- Visible en `services.msc` como "Brother Label Agent - Revix"

Para gestionar:
```cmd
python service.py stop      :: Detener
python service.py restart   :: Reiniciar
python service.py remove    :: Desinstalar
```

---

## Seguridad

| Medida | Detalle |
|---|---|
| Agent Key | Cada peticion del agente al CRM incluye `agent_key`. Si no coincide, se rechaza (403). |
| JWT | Los usuarios del CRM deben estar autenticados para enviar trabajos de impresion. |
| Registro | Cada impresion se registra en MongoDB: usuario, fecha, hora, resultado, error. |
| Red | El agente escucha en `0.0.0.0:5555`. Proteger con firewall de Windows si es necesario. |

Para restringir el acceso al agente local, configure el firewall de Windows:
```cmd
netsh advfirewall firewall add rule name="Brother Label Agent" dir=in action=allow protocol=tcp localport=5555 remoteip=localsubnet
```

---

## Manejo de errores

| Situacion | Comportamiento |
|---|---|
| Impresora apagada | Heartbeat reporta `printer_online: false`. CRM muestra "Error de impresora". |
| Impresora ocupada | Trabajos se encolan (max 50). Se procesan en orden. |
| Internet caido | Polling falla con backoff progresivo. Se reanuda automaticamente. |
| Agente se cierra | `start.bat` lo reinicia en 5s. Servicio Windows lo reinicia en 5/10/30s. |
| Cola llena | Trabajo rechazado con error "Cola llena". Se reporta al CRM. |
| Agent key incorrecta | Error 403. Log: "Agent key rechazada". |
| CRM no responde | Backoff: 3s -> 9s -> 15s max. Log solo cada 20 intentos para no saturar. |

---

## Logs

Archivo: `agent.log` (en el directorio del agente)
- Rotacion automatica: max 5 MB, 3 archivos de backup
- Formato: `2026-04-15 12:30:00 [INFO] IMPRESO job=pj-xxx template=ot_barcode_minimal total=42`

---

## Verificacion

1. Abra el CRM desde **cualquier dispositivo**
2. Acceda a una orden de trabajo
3. El panel "Impresion Directa" debe mostrar: **Impresora conectada** (verde)
4. Pulse **Imprimir Etiqueta**
5. La etiqueta sale por la Brother QL-800 del taller

---

## Especificaciones tecnicas

| Parametro | Valor |
|---|---|
| Servidor HTTP | Waitress 3.x (produccion, multi-thread) |
| Threads HTTP | 4 |
| Cola de impresion | queue.Queue (serializada, max 50 jobs) |
| Polling CRM | Cada 3s (configurable) |
| Heartbeat | Cada 10s (configurable) |
| Timeout heartbeat CRM | 30s (si no recibe heartbeat, marca offline) |
| Imagen etiqueta | 638x201 px, 1-bit, 300 DPI |
| Barcode | Code128, module_width 0.45, reescalado NEAREST |
| Impresion | Win32 GDI, DEVMODE forzado a DK-11204 |

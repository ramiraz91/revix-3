# Brother Label Agent v2.0.0 — Centralizado

Agente de impresion para **Brother QL-800** con etiquetas **DK-11204** (17mm x 54mm).

Arquitectura centralizada: la impresora del taller recibe trabajos de cualquier sesion del CRM.

---

## Como funciona

```
  PC/Movil (CRM Revix)        Servidor CRM (nube)           PC Taller (Agente)
  +-----------------+         +------------------+          +------------------+
  | Boton "Imprimir"|--HTTP-->| POST /print/send |          |                  |
  |                 |         |   (MongoDB cola)  |<--poll---| agent.py         |
  |                 |         |                  |          |   genera imagen  |
  |                 |         | job: completed   |<--report-|   imprime QL-800 |
  |  "Impresa OK"  |<--poll--|                  |          |                  |
  +-----------------+         +------------------+          +------------------+
```

1. El usuario pulsa "Imprimir Etiqueta" en el CRM (desde cualquier PC o movil)
2. El CRM guarda el trabajo en MongoDB (status: pending)
3. El agente del taller consulta cada 3 segundos si hay trabajos pendientes
4. El agente genera la etiqueta, la imprime y reporta el resultado
5. El CRM muestra "Impresa correctamente" al usuario

---

## Requisitos del PC del taller

| Componente | Detalle |
|---|---|
| Sistema operativo | Windows 10 / 11 |
| Python | 3.10 o superior |
| Impresora | Brother QL-800 conectada por USB |
| Driver | Driver oficial Brother QL-800 instalado |
| Etiquetas | DK-11204 (17 x 54 mm) cargadas |
| Internet | Conexion a internet (para comunicar con el CRM) |

---

## Instalacion

### 1. Descargar

Desde el CRM: en cualquier orden de trabajo, el panel "Impresion Directa" muestra un boton **Descargar Agente** si el agente no esta conectado.

O descargue el ZIP desde el menu del CRM.

Descomprima en una carpeta, por ejemplo: `C:\RevixAgent\`

### 2. Configurar

Edite **`config.json`**:

```json
{
    "port": 5555,
    "default_printer": "Brother QL-800",
    "label_format": "DK-11204",

    "crm_url": "https://SU-DOMINIO-CRM.com",
    "agent_key": "revix-brother-agent-2026-key",
    "agent_id": "taller-principal",
    "poll_interval": 3,
    "heartbeat_interval": 10
}
```

| Campo | Descripcion |
|---|---|
| `crm_url` | URL completa del CRM (sin barra final). Ejemplo: `https://revix.es` |
| `agent_key` | Clave compartida con el servidor CRM. Debe coincidir exactamente. |
| `agent_id` | Identificador de este puesto de impresion |
| `default_printer` | Nombre exacto de la impresora en Windows |
| `poll_interval` | Segundos entre consultas al CRM (por defecto 3) |
| `heartbeat_interval` | Segundos entre envios de estado (por defecto 10) |

### 3. Instalar dependencias

Doble clic en **`install.bat`** o:

```cmd
cd C:\RevixAgent
install.bat
```

### 4. Iniciar

Doble clic en **`start.bat`**. Vera:

```
Brother Label Agent v2.0.0 — Centralizado
Impresora: Brother QL-800
Formato:   DK-11204 (17mm x 54mm)
CRM URL:   https://su-dominio.com
Agent ID:  taller-principal
Polling activo -> https://su-dominio.com (cada 3s)
Heartbeat activo (cada 10s)
```

Minimice la ventana y deje el agente ejecutandose.

---

## Verificacion

1. Abra el CRM desde cualquier dispositivo
2. Entre en una orden de trabajo
3. El panel "Impresion Directa" debe mostrar: **Impresora conectada** (verde)
4. Pulse **Imprimir Etiqueta**
5. La etiqueta debe salir por la Brother QL-800 del taller

---

## Seguridad

- El agente se autentica con `agent_key` en cada peticion
- Solo usuarios autenticados en el CRM pueden enviar trabajos de impresion
- Cada impresion queda registrada en MongoDB: usuario, fecha, hora, resultado
- El agente solo procesa trabajos del servidor CRM configurado

---

## Inicio automatico con Windows

1. Pulse `Win + R`, escriba `shell:startup`, Enter
2. Copie un acceso directo de `start.bat` en esa carpeta

---

## Solucion de problemas

| Problema | Solucion |
|---|---|
| CRM dice "Agente no conectado" | Verifique que `start.bat` esta ejecutandose y que `crm_url` y `agent_key` son correctos en `config.json` |
| "Agent key rechazada" | La clave en `config.json` no coincide con la del servidor CRM |
| Impresora no encontrada | Verifique que la QL-800 esta encendida y el nombre coincide en `config.json` |
| Error del spooler | Reinicie "Cola de impresion" en `services.msc` |
| Etiqueta sale cortada | Verifique DK-11204 bien colocadas |

Logs detallados en **`agent.log`**.

"""
Envía una alerta al SOC desde la terminal.
El supervisor la analiza y el notification_agent manda el email.

La alerta puede ser un JSON, con los campos que sean, o texto libre:
unas líneas de log, un hash o una IP. Los ejemplos están en la carpeta ejemplos/.

Uso:
    python probar_alerta.py                                     (usa ejemplos/alerta_ejemplo.json)
    python probar_alerta.py ejemplos/alerta_verdadero_positivo.json
    python probar_alerta.py ejemplos/alerta_falso_positivo.json
    python probar_alerta.py ejemplos/log_edr.txt
    python probar_alerta.py ejemplos/indicador_ip.txt
"""

import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent      # la carpeta de este fichero
# Trabajar en esta carpeta: aquí están .env, credenciales, token y la carpeta ejemplos/
os.chdir(BASE_DIR)

from supervisor import Run_All_process_related_to_alert_security

# Para que la consola de Windows muestre bien tildes y emojis
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if len(sys.argv) > 1:              # ¿han escrito algo detrás del nombre del script?
    fichero = sys.argv[1]          # sí: uso ese fichero
else:
    fichero = "ejemplos/alerta_ejemplo.json"  # no: uso la alerta de ejemplo

with open(fichero, encoding="utf-8") as f:
    contenido = f.read()                    # el fichero, tal cual, como texto

# La alerta puede ser un JSON (con cualquier plantilla) o texto libre
try:
    alerta = json.loads(contenido)          # un JSON con campos, como alerta_ejemplo.json
except json.JSONDecodeError:
    alerta = None                           # no es JSON
if not isinstance(alerta, dict):            # texto libre: un log, un hash, una IP...
    alerta = {"texto": contenido.strip()}


resultado = Run_All_process_related_to_alert_security(alerta, alerta.get("id", "ALERT-TEST")) # Resultado ejecuta el servicio Run_All_process_related_to_alert_security
print("\nEstado:", resultado["status"])
if resultado["status"] == "error":
    print("Error:", resultado["error"])
else:
    print("Email:", resultado["notification_sent"])

# SOC multiagente con LangGraph

Sistema multiagente que analiza alertas de seguridad. Un **supervisor** (`langgraph-supervisor`) coordina tres agentes:

1. **alert_analyzer** – extrae los IOCs (IPs, URLs, hashes) y los analiza con **VirusTotal** y **Tavily** → verdadero o falso positivo.
2. **threat_analyzer** – solo si es verdadero positivo: severidad, TTPs y mitigaciones.
3. **notification_agent** – envía el informe por **Gmail**.

## Estructura

| Fichero | Qué hace |
|---|---|
| `probar_alerta.py` | Lanza una alerta desde la terminal: `python probar_alerta.py ejemplos/log_edr.txt` |
| `supervisor.py` | El supervisor y `Run_All_process_related_to_alert_security()` |
| `agents.py` | Los tres agentes |
| `tools.py` | VirusTotal, Tavily y Gmail |
| `config.py` | Lee las claves del `.env` |
| `ejemplos/` | Alertas de prueba: JSON, logs de texto e indicadores sueltos |

## Ejecutar en local

```bash
pip install -r requirements.txt
cp .env.example .env          # y rellena tus claves
python tools.py               # la primera vez abre el navegador para autorizar Gmail y crea token.json
python probar_alerta.py       # ejemplos/alerta_ejemplo.json: el informe llega por email
```

La alerta puede ser un JSON, con cualquier plantilla (la del curso, ECS, la de tu SIEM…), o texto libre: unas líneas
de log, un hash o una IP. Con datos reales de tu empresa, pide antes permiso a tu equipo de seguridad y anonimízalos
(mira el README de la carpeta superior).

## Compartir en GitHub

El repositorio es la carpeta superior, `Sesion_3_Vscode`: los ejemplos de la sesión y este taller. Los `.gitignore`
ya excluyen `.env`, los tokens, `credenciales_google.json` y `venv/`. **Comprueba con `git status` que no aparecen
antes del primer commit.**

```bash
cd ..                         # a la carpeta Sesion_3_Vscode
git init
git add .
git status                    # .env, token.json y credenciales_google.json NO deben salir
git commit -m "sesion 3_Vs_code"
git branch -M main
git remote add origin https://github.com/<tu-usuario>/<tu-repo>.git
git push -u origin main
```

Después, cada cambio: `git add .`, `git commit -m "…"` y `git push`. Tu equipo lo recibe con `git pull`.

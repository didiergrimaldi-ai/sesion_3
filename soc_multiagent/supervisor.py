"""
Supervisor del SOC: coordina a los tres agentes especialistas.
    Run_All_process_related_to_alert_security()   procesa una alerta y devuelve el informe (la usa probar_alerta.py)
"""
import json
from datetime import datetime

from langgraph_supervisor import create_supervisor

from agents import llm, alert_analyzer, threat_analyzer, notification_agent  # el LLM y los tres agentes
from config import config


# 1. El guion del supervisor: quién hay, en qué orden y qué no debe hacer
PROMPT = """Eres el supervisor de un SOC. No analizas alertas: decides qué agente trabaja en cada momento.
Tienes tres agentes y una herramienta para pasarle el turno a cada uno:
- alert_analyzer (transfer_to_alert_analyzer): analiza la alerta y concluye VERDADERO POSITIVO o FALSO POSITIVO.
- threat_analyzer (transfer_to_threat_analyzer): evalúa la gravedad y propone medidas.
- notification_agent (transfer_to_notification_agent): envía el email final con los resultados.

Sigue siempre estos pasos, en este orden:
1. Pasa el turno a alert_analyzer.
2. Lee su CONCLUSIÓN FINAL:
   - Si es FALSO POSITIVO: NO llames a threat_analyzer. Ve directamente al paso 3.
   - En cualquier otro caso (VERDADERO POSITIVO o si no está claro): pasa el turno a threat_analyzer.
3. Pasa el turno a notification_agent.
4. Cuando notification_agent termine, responde solo "PROCESO COMPLETADO".

Reglas:
- Cada agente trabaja una sola vez.
- No escribas tú el análisis, la evaluación ni el email: eso lo hacen los agentes."""


# 2. El grafo: el supervisor y sus tres agentes
supervisor = create_supervisor(
    agents=[alert_analyzer, threat_analyzer, notification_agent],
    model=llm,                      # el mismo LLM que usan los agentes
    prompt=PROMPT,
    output_mode="full_history",     # guardar todos los mensajes de cada agente
)
soc_workflow = supervisor.compile()


# 3. La entrada del grafo: un mensaje con el ID, el email y la alerta
def _build_input(alert_data: dict, incident_id: str) -> dict: # _:uso interno
    text = f"""Nueva alerta de seguridad.
ID: {incident_id}
EMAIL: {config.SOC_EMAIL_RECIPIENT}
DATOS: {json.dumps(alert_data, indent=2)}""" # convierte el diccionario de la alerta (el JSON o {"texto": ...}) en texto legible en varias líneas, para que el LLM lo entienda mejor
    return {"messages": [{"role": "user", "content": text}]} # la alerta convertida en texto


# 4. La respuesta final de un agente: su último mensaje que no pide herramientas
def _agent_answer(messages: list, agent_name: str) -> str:
    for message in reversed(messages):          # empezando por el final
        if message.name == agent_name and message.type == "ai" and not message.tool_calls: # de todo lo que se ha dicho en la conversación, quédate con lo último que escribió ese agente sin pedir herramientas: esa es su respuesta
            return message.content
    return ""


# 5. El informe: un diccionario con la respuesta de cada agente
def _build_report(messages: list, incident_id: str) -> dict:
    return {
        "incident_id": incident_id,
        "status": "completed",
        "analysis_result": _agent_answer(messages, "alert_analyzer") or "No analysis found",
        "threat_assessment": _agent_answer(messages, "threat_analyzer") or "No threat assessment performed",
        "notification_sent": _agent_answer(messages, "notification_agent") or "No notification sent",
        "timestamp": datetime.now().isoformat(),
        "full_conversation": messages,
    }

# 6. Procesar una alerta de principio a fin (la usa probar_alerta.py)
def Run_All_process_related_to_alert_security(alert_data: dict, incident_id: str) -> dict: # avisa en la terminal, porque el proceso tarda entre 45 y 90 segundos.
    print(f"Procesando {incident_id}: el supervisor coordina a los agentes...")
    graph_input = _build_input(alert_data, incident_id)  # la entrada del grafo: un mensaje con el ID, el email y la alerta
    try:  # si algo falla (una clave, la red...), avisa en lugar de romperse
        result = soc_workflow.invoke(graph_input) # el supervisor coordina a los agentes y devuelve todos sus mensajes
        return _build_report(result["messages"], incident_id)
    except Exception as e:      # si algo falla (una clave, la red...), avisa en lugar de romperse
        return {"incident_id": incident_id, "status": "error", "error": str(e)}

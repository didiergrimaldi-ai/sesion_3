"""Sesión 3 · Controlar el agente: una persona revisa antes de que actúe
Mismo agente de soporte que 3_agente_con_herramientas.py, con un nodo «revisar» entre el
modelo y las herramientas: interrupt() para el grafo y una persona decide si la herramienta
se ejecuta. Para poder pararse y seguir después, el grafo necesita un checkpointer (memoria).
Requiere: OPENAI_API_KEY.
"""
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command

INCIDENCIAS = {"28013": "Corte programado por obras hasta las 14:00.",
               "28012": "Sin incidencias abiertas.",
               "28011": "Avería en la línea, técnico asignado.",
               "28010": "Sin incidencias abiertas.",
               "28009": "Corte programado por obras hasta las 16:00.",
               "28008": "Avería en la línea, técnico asignado.",
               "28007": "Sin incidencias abiertas.",
               "28006": "Avería en la línea, técnico asignado.",
               "28005": "Sin incidencias abiertas.",
               "28004": "Corte programado por obras hasta las 15:00."}

LINEAS = {"666123456": "activa - fibra 600Mb - router conectado",
          "666123457": "inactiva - el cliente ha dejado de pagar la factura, se le ha cortado el servicio",
          "666123458": "inactiva - avería en la línea, técnico asignado",
          "666123459": "activa - fibra 600Mb - router conectado"
          }



@tool
def consultar_incidencias(cp: str) -> str:
    """Consulta incidencias abiertas en la red para un código postal.
    Úsala cuando el cliente diga que no tiene servicio."""
    estado = INCIDENCIAS.get(cp, "Sin incidencias abiertas.")
    return f"Código postal {cp}: {estado}"


@tool
def consultar_linea(telefono: str):
    """Consulta el estado de la línea de un cliente a partir de su teléfono.
    Si el telefono no está en la base de datos, se asume que está activa y que podria comprobar que su telefono funciona bien o que reinicie
    su dispositivo y vuelva a intentarlo."""
    estado = LINEAS.get(telefono, "activa - fibra 600Mb - router conectado") # busca el telefono en la base de datos de lineas activas
    return f"Línea {telefono}: {estado}." # devuelve el estado si coincide con algún teléfono de la base de datos sino devuelve el mensaje por defecto


herramientas = [consultar_incidencias, consultar_linea]
llm_con_tools = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(herramientas)
SISTEMA = SystemMessage(content="Eres soporte técnico. Usa las herramientas antes de responder. "
                                "Responde en español y en dos o tres frases. Sea comprensivo y empático con el cliente.")


def modelo(state: MessagesState) :                 # PENSAR
    return {"messages": [llm_con_tools.invoke([SISTEMA, *state["messages"]])]} # tiene acceso [instrucciones, pregunta, petición_herramienta, resultado]


def revisar(state: MessagesState) :              # CONTROLAR: una persona decide
    llamada = state["messages"][-1].tool_calls[0] # coge la primera herramienta que pidió el LLM en su último mensaje.
    decision = interrupt(f"¿Ejecutar {llamada['name']}({llamada['args']})? (s/n)")
    if decision == "s":
        return Command(goto="tools")
    rechazo = ToolMessage(content="Eres incapaz de responder a esta consulta: no tienes el dato necesario. "
                                 "Dile al cliente que no has podido comprobar las incidencias y que mejor el clientecontacte con el servicio de atención al cliente"
                                 "de su distribuidora. El problema es a nivel local y no al nivel de la operadora. Por eso, que no" \
                                 "investigamos para no cargar la agenda de nuestros tecnicos de forma innecesaria.", tool_call_id=llamada["id"]) # el LLM diga claramente que no ha podido comprobarlo
    # el mensaje de rechazo es lo que el LLM recibe en lugar del resultado de la herramienta.
    return Command(goto="modelo", update={"messages": [rechazo]})


g = StateGraph(MessagesState)

g.add_node("modelo", modelo) #PENSAR: llama al LLM y añade su respuesta a la conversación
g.add_node("revisar", revisar, destinations=("tools", "modelo")) #CONTROLAR: una persona decide si se ejecuta la herramienta o no
g.add_node("tools", ToolNode(herramientas))   #ACTUAR: ejecuta la herramienta y añade el resultado a la conversación


g.add_edge(START, "modelo")
g.add_edge("tools", "modelo")
g.add_conditional_edges("modelo", tools_condition, {"tools": "revisar", END: END})
                    
agente = g.compile(checkpointer=InMemorySaver())           # memoria para poder pausar y seguir

config = {"configurable": {"thread_id": "cliente-1"}}     # una conversación = un thread_id

#pregunta = "Justamente han venido los amigos de mi hijo esta mañana.No tengo internet en casa, vivo en Madrid en el código postal 29013. La fiesta de su cumpleaños comienza ahora"
#pregunta = "Vivimos en Madrid y estamos en el codigos postal 28013 y la linea no funciona."
pregunta = "Vivimos en Madrid y estamos en el codigos postal 28013 y la linea no funciona. Aprovecho para pedirte tambien que está pasando con la linea de mi vecino, que es el 666123457."

resultado = agente.invoke({"messages": [("user", pregunta)]}, config)
while "__interrupt__" in resultado:                        # el grafo se ha parado a preguntar
    texto = resultado["__interrupt__"][0].value
    decision = input(texto + " ").strip().lower()
    resultado = agente.invoke(Command(resume=decision), config)   # sigue donde se paró
print("La respuesta es:", resultado["messages"][-1].content)

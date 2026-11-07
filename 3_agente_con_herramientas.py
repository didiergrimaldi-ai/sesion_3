"""Sesión 3 · Agente con herramientas: el bucle del agente como grafo
El patrón ReAct construido con LangGraph: un nodo «modelo» (el LLM con herramientas), un nodo
«herramientas» (ToolNode, que las ejecuta) y una arista condicional (tools_condition) que vuelve
al modelo mientras pida herramientas. Requiere: OPENAI_API_KEY.
"""
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition

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
          "666123457": "inactiva - avería en la línea, técnico asignado",
          "666123458": "inactiva - avería en la línea, técnico asignado",
          "666123459": "activa - fibra 600Mb - router conectado"
          }


@tool
def consultar_incidencias(cp: str):
    """Consulta incidencias abiertas en la red para un código postal.
    Úsala cuando el cliente diga que no tiene servicio."""
    estado = INCIDENCIAS.get(cp, "Sin incidencias abiertas.") # busca el codigo postal en la base de datos de incidencias abiertas
    return f"Código postal {cp}: {estado}" # devuelve el estado si coincide con algún código postal de la base de datos sino devuelve el mensaje por defecto


@tool
def consultar_linea(telefono: str):
    """Consulta el estado de la línea de un cliente a partir de su teléfono.
    Si el telefono no está en la base de datos, se asume que está activa y que podria comprobar que su telefono funciona bien o que reinicie
    su dispositivo y vuelva a intentarlo."""
    estado = LINEAS.get(telefono, "activa - fibra 600Mb - router conectado") # busca el telefono en la base de datos de lineas activas
    return f"Línea {telefono}: {estado}." # devuelve el estado si coincide con algún teléfono de la base de datos sino devuelve el mensaje por defecto


herramientas = [consultar_incidencias, consultar_linea]
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_con_tools = llm.bind_tools(herramientas)     # Le dice qué herramientas existen: el LLM las asocia a sus descripciones y las puede invocar con tool_calls


def modelo(state: MessagesState):    # nodo PENSAR: llama al LLM y añade su respuesta a la conversación
    instrucciones = ("system", "Eres soporte técnico de Orange. Usa las herramientas antes de responder. "
                               "Responde en español y en dos o tres frases. Sea comprensivo y empático con el cliente. ")
    respuesta = llm_con_tools.invoke([instrucciones, *state["messages"]]) # tiene acceso [instrucciones, pregunta, petición_herramienta, resultado]
    return {"messages": [respuesta]}


g = StateGraph(MessagesState)                    # lista de mensajes

g.add_node("modelo", modelo) # nodo que piensa y llama al LLM con herramientas
g.add_node("tools", ToolNode(herramientas)) # nodo que actúa: ejecuta las herramientas

g.add_edge(START, "modelo")                      # se empieza en el nodo modelo, que llama al LLM con herramientas
g.add_conditional_edges("modelo", tools_condition, {"tools": "tools", END: END})   # si el ultimo mensaje del modelo pide un tool, se va al nodo tools y devuelve el resultado al modelo. Sino, va a END
g.add_edge("tools", "modelo")                    # tras ejecutar, vuelve al modelo para observar el resultado y decidir si necesita otra herramienta o responder al usuario
agente = g.compile()

pregunta = "Justamente han venido los amigos de mi hijo esta mañana.No tengo internet en casa, vivo en Madrid en el código postal 28013. La fiesta de su cumpleaños comienza ahora" # pregunta del usuario que activa el bucle del agente
#pregunta = "Apreto el boton de mi telefono 766123458 y no oigo nada, no tiene línea."  # otra pregunta del usuario que activa el bucle del agente

for paso in agente.stream({"messages": [("user", pregunta)]}, stream_mode="values"):
    paso["messages"][-1].pretty_print()


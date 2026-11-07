"""Sesión 3 · Un mini sistema multiagente: un supervisor y dos especialistas.
El supervisor (create_supervisor) lee la petición y delega en el agente adecuado
con una herramienta de traspaso (transfer_to_...). El investigador busca de verdad
en internet con TavilySearch (la usaremos también en el taller).
Requiere: OPENAI_API_KEY y TAVILY_API_KEY.
"""
import textwrap

from langchain.agents import create_agent
from langgraph_supervisor import create_supervisor
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch

model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Herramienta ya hecha: búsqueda web real (lee TAVILY_API_KEY del entorno)
buscar_web = TavilySearch(max_results=3) # cuantos resultados devuelve la búsqueda

# Herramienta propia
@tool
def calcular(a: float, operacion: str, b: float) -> float:
    """Hace una operación con dos números: "+", "-", "*", "/" o "**" (potencia).
    Ejemplo: pi al cuadrado → a=3.141592653589793, operacion="**", b=2"""
    if operacion == "+":
        return a + b
    if operacion == "-":
        return a - b
    if operacion == "*":
        return a * b
    if operacion == "/":
        return a / b
    return a ** b

# Crear agentes especializados
agente_investigacion = create_agent(
    model=model,
    tools=[buscar_web],
    system_prompt=("Eres un especialista en investigacion web. Busca y resume en una o dos frases. "
                   "No hagas calculos: de eso se encarga otro agente."),
    name="investigador"
)

agente_matematicas = create_agent(
    model=model,
    tools=[calcular],
    system_prompt=("Eres un especialista en calculos. Usa siempre la herramienta calcular. "
                   "Responde solo con el resultado, sin explicaciones ni formato LaTeX. "
                   "El resto de la pregunta lo responden otros agentes."),
    name="matematico"
)

# Crear supervisor que coordina los agentes
supervisor_graph = create_supervisor(
    [agente_matematicas, agente_investigacion],
    model=model,
    prompt=("Eres un supervisor. Delega cada parte de la pregunta en el especialista adecuado: "
            "investigador para buscar, matematico para calcular. Al final, junta sus respuestas."),
    output_mode="full_history",   # guarda todo lo que hace cada agente, también sus herramientas
)

supervisor = supervisor_graph.compile()

# Mostrar el resultado: quién tiene la pelota en cada paso
def mostrar_conversacion(response):
    """Imprime quién habla en cada paso: el supervisor a la izquierda, los agentes con sangría."""
    mensajes = response["messages"]
    for i, msg in enumerate(mensajes):
        quien = msg.name or msg.type
        llamadas = getattr(msg, "tool_calls", [])
        sangria = "" if quien in ("supervisor", "human") else "        "   # los agentes, más a la derecha

        if msg.type == "human":                                   # la pregunta
            print("\n" + "=" * 70)
            print(textwrap.fill("PREGUNTA: " + msg.content, 70))
            print("=" * 70)

        elif msg.type == "ai":                                    # habla el supervisor o un agente
            final = i == len(mensajes) - 1
            print(f"\n{sangria}[{quien}]" + ("   ← RESPUESTA FINAL" if final else ""))
            if msg.content and not any(t["name"].startswith("transfer") for t in llamadas):
                print(textwrap.fill(msg.content, 70, initial_indent=sangria + "   ", subsequent_indent=sangria + "   "))
            for t in llamadas:
                if t["name"].startswith("transfer_to_"):          # el supervisor delega
                    print(f"{sangria}   ──► pasa la pelota a: {t['name'].removeprefix('transfer_to_')}")
                elif t["name"].startswith("transfer_back_to_"):   # el agente termina
                    print(f"{sangria}   ◄── devuelve la pelota al supervisor")
                else:                                             # el agente usa una herramienta
                    print(f"{sangria}   usa la herramienta {t['name']}: {t['args']}")

        elif msg.type == "tool" and not msg.name.startswith("transfer"):   # resultado de una herramienta
            texto = msg.content if len(msg.content) < 150 else msg.content[:150] + " …"
            print(textwrap.fill(f"resultado: {texto}", 70, initial_indent=sangria + "   ", subsequent_indent=sangria + "   "))
    print()


# Uso del sistema multi-agente
response = supervisor.invoke({
    "messages": [{
        "role": "user",
        #content": "Busca qué es el número pi y calcula su valor al cuadrado."   # usa los dos agentes
         "content": "Calcula que vale pi al cuadrado."
        # "content": "Busca informacion sobre las ultimas noticias de inteligencia artificial."
    }]
})

mostrar_conversacion(response)

import json
import os
import difflib
from langchain.memory import ConversationBufferWindowMemory
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from deep_translator import GoogleTranslator  # Para traducción automática

# Ruta del archivo auth.json
auth_path = os.path.expanduser("C:\\Users\\FarceF\\.openai\\auth.json")

# Cargar la API key desde el archivo
with open(auth_path, "r") as auth_file:
    auth_data = json.load(auth_file)
    api_key = auth_data.get("api_key")

# Inicializar modelo de lenguaje
llm = ChatOpenAI(openai_api_key=api_key, model_name="gpt-4o-mini")

# Configurar memoria
buffer_memory = ConversationBufferWindowMemory(k=5)  # Guarda las últimas 5 interacciones

# Cadena de conversación con memoria
conversation = ConversationChain(
    llm=llm,
    memory=buffer_memory
)

# Rutas de archivos JSON
json_path = os.path.join(os.path.dirname(__file__), "conversation_memory.json")
conversation_data_path = os.path.join(os.path.dirname(__file__), "conversation_data.json")

# Contexto adicional sobre la EMI
emi_description = """
SIEMPRE RESPODERAS La Escuela Militar de Ingeniería es un centro de estudios con especialidad en ingeniería de Bolivia...
"""

# Asegurar que el archivo de memoria existe
if not os.path.exists(json_path):
    initial_data = {
        "messages": [
            {
                "role": "system",
                "content": "Eres un asistente virtual de la EMI. Responde preguntas sobre la institución."
            }
        ]
    }
    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(initial_data, json_file, ensure_ascii=False, indent=4)

def update_conversation_memory(role, content):
    """Actualiza la memoria de la conversación en conversation_memory.json."""
    with open(json_path, "r", encoding="utf-8") as json_file:
        data = json.load(json_file)

    data["messages"].append({"role": role, "content": content})

    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

def find_best_match(user_input, interactions):
    """Encuentra la mejor coincidencia en la base de datos de preguntas frecuentes."""
    preguntas = [i["pregunta"].strip().lower() for i in interactions]
    match = difflib.get_close_matches(user_input.strip().lower(), preguntas, n=1, cutoff=0.6)  # Ajusta sensibilidad

    if match:
        for i in interactions:
            if i["pregunta"].strip().lower() == match[0]:
                print(f"✅ Coincidencia encontrada: {match[0]}")
                return i["respuesta"]
    print("❌ No se encontró coincidencia exacta en preguntas frecuentes.")
    return None

def chat_with_memory(user_input: str):
    """Busca una respuesta predefinida o genera una con GPT."""
    try:
        # Traducir la pregunta al español si está en inglés
        detected_language = GoogleTranslator(source='auto', target='es').translate(user_input)
        print(f"🌎 Traducción detectada: {detected_language}")

        if not os.path.exists(conversation_data_path):
            return "Error: No se encontró el archivo de respuestas predefinidas."

        with open(conversation_data_path, "r", encoding="utf-8") as json_file:
            interactions = json.load(json_file)

        interactions = interactions.get("preguntas_frecuentes", [])

        # Buscar coincidencia con preguntas predefinidas
        response = find_best_match(detected_language, interactions)

        # Si no hay coincidencia, generar con GPT
        if not response:
            input_with_context = f"Contexto sobre la EMI: {emi_description}\n\nPregunta: {user_input}\nResponde basándote en este contexto."
            try:
                response = conversation.predict(input=input_with_context)
            except Exception as e:
                response = f"Error al generar respuesta con GPT: {str(e)}"

        # Guardar en la memoria de conversación
        update_conversation_memory("user", user_input)
        update_conversation_memory("assistant", response)

        return response

    except Exception as e:
        return f"Error inesperado en chat_with_memory: {str(e)}"

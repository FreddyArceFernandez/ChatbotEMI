from langchain_community.utilities import SQLDatabase
from langchain.chat_models import ChatOpenAI
from langchain.chains import SQLDatabaseChain

# Cargar la clave de API
load_dotenv()
OPENAI_API_KEY = os.getenv("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")

# Crear conexión a la base de datos con LangChain
db = SQLDatabase.from_uri("mysql+pymysql://root:root@localhost/chinook")

# Inicializar el modelo de OpenAI
llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model="gpt-4", temperature=0)

# Crear la cadena de consulta
db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)

# Función para interactuar con la base de datos
def preguntar_a_bd(pregunta):
    try:
        respuesta = db_chain.run(pregunta)
        return respuesta
    except Exception as e:  
        return f"Error: {e}"
def chatbot():
    print("💬 Chatbot con acceso a MySQL. Escribe 'salir' para terminar.")
    while True:
        pregunta = input("Tú: ")
        if pregunta.lower() == "salir":
            print("👋 ¡Hasta luego!")
            break
        respuesta = preguntar_a_bd(pregunta)
        print(f"🤖 Bot: {respuesta}")

if __name__ == "__main__":
    chatbot()

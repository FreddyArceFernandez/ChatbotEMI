import json
import unicodedata
import string
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_openai import ChatOpenAI
from fuzzywuzzy import fuzz
import difflib
import mysql.connector
from deep_translator import GoogleTranslator
import re
import logging

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='chatbot.log'
)

# ============ Configuraciones iniciales ============
INSTITUTION_SYNONYMS = {
    "emi": ["emmy", "em i", "emmi", "emie", "emil", "en", "me", "escuela militar"],
    "escuela militar de ingeniería": ["emi", "emmy", "emil", "military school of engineering"],
    "campus": ["sede", "ubicación", "localización"],
    "carrera": ["programa", "estudio", "especialidad", "race"],
    "técnico superior": ["tecnico", "ts", "técnico", "tec superior", "technical"],
    "licenciatura": ["pregrado", "profesional", "degree", "licenciado"]
}

COMMON_ERRORS_PATTERNS = [
    (r"\b(emmy|emmi|emie|emil|en|me)\b", "emi"),
    (r"\b(ingneria|ingenieriaa|ingeniera|ingnieria)\b", "ingeniería"),
    (r"\b(tecnico|tecnic|tecnologia)\b", "técnico"),
    (r"\b(licenciado|licenciada|licenciat)\b", "licenciatura"),
    (r"\b(carrera|programa|estudio)\b", "carrera"),
    (r"\b(admicion|admicion|admision)\b", "admisión")
]

STOPWORDS = set([
    "de", "la", "el", "que", "y", "a", "al", "en", "los", "del", "las",
    "un", "una", "por", "con", "para", "es", "se", "lo", "como", "más",
    "o", "sus", "le", "ha", "me", "si", "sin", "sobre", "este", "ya",
    "entre", "cuando", "todo", "esta", "ser", "son", "dos", "también",
    "fue", "ha", "muy", "años", "hasta", "desde", "está", "mi", "porque",
    "qué", "quién", "cuál", "dónde", "cómo", "para", "por", "nos", "vos",
    "yo", "tú", "cuales", "cual", "tiene", "tienen", "ofrece", "cuenta"
])

TEMAS_SOPORTADOS = {
    "institucional": ["emi", "escuela militar", "historia", "fundación", "misión"],
    "academico": ["carrera", "carreras", "licenciaturas", "licenciatura", "técnico", "tecnico", "tecnico superior", "técnico superior", "materia", "plan", "curso"],
    "admision": ["inscripción", "admisión", "requisito", "requisitos", "examen", "modalidad"],
    "infraestructura": ["campus", "instalación", "instalaciones", "laboratorio", "aula", "parqueo"],
    "servicios": ["beneficios", "beca", "becas", "biblioteca", "comedor"],
    "militar": ["uniforme", "servicio militar", "libreta", "rango", "disciplina"]
}

# ============ Prompt de Reformulación ============
PROMPT_REFORMULADOR = """
Eres un lingüista experto en reformulación de preguntas para sistemas educativos. Tu tarea es mejorar la estructura de la pregunta conservando exactamente su intención original. Sigue estas reglas:

1. CONSERVACIÓN DEL SIGNIFICADO:
   - Mantén fielmente la intención original del usuario
   - No agregues información que no esté implícita
   - Preserva los términos técnicos específicos

2. MEJORA ESTRUCTURAL:
   - Convierte a pregunta gramaticalmente correcta (sujeto + verbo + complemento)
   - Asegura concordancia gramatical (género, número, tiempo verbal)
   - Usa artículos y preposiciones correctas
   - Máximo 25 palabras

3. ADECUACIÓN INSTITUCIONAL:
   - Usa los nombres oficiales (ej: "EMI" en lugar de "la escuela")
   - Mantén términos académicos precisos (ej: "técnico superior" en lugar de "carrera corta")

4. FORMATO DE SALIDA:
   - Solo devuelve la pregunta reformulada
   - No incluyas explicaciones
   - Usa signos de interrogación completos (¿?)

Ejemplos:
Input: "kiero saber carreras"
Output: "¿Qué carreras ofrece la EMI?"

Input: "como es admision"
Output: "¿Cómo es el proceso de admisión en la EMI?"

Ahora reformula esta pregunta conservando exactamente su intención original:

{pregunta}
"""

# ============ Conexión a base de datos ============
db = SQLDatabase.from_uri("mysql+mysqlconnector://root:root@localhost/emi_db")
llm = ChatOpenAI(model="gpt-4o", temperature=0)
agent_executor = create_sql_agent(
    llm=llm,
    db=db,
    agent_type="openai-tools",
    verbose=True
)

faq_file_path = "ruta/a/tu/archivo_faq.json"

# ============ Funciones auxiliares ============
def normalizar(texto: str) -> str:
    if not texto:
        return ""
    
    texto = re.sub(r"\?+", "?", texto)
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")
    texto = texto.lower().strip()
    
    for pattern, replacement in COMMON_ERRORS_PATTERNS:
        texto = re.sub(pattern, replacement, texto)
    
    texto = re.sub(rf"[{re.escape(string.punctuation.replace('?', ''))}]", " ", texto)
    texto = " ".join(texto.split())
    
    for base, synonyms in INSTITUTION_SYNONYMS.items():
        for synonym in synonyms:
            texto = re.sub(rf"\b{synonym}\b", base, texto)
    
    return texto.strip()

def extraer_palabras_clave(texto: str) -> str:
    palabras = texto.split()
    palabras_clave = [p for p in palabras if p not in STOPWORDS and len(p) > 2]
    
    keyword_priority = {
        "carrera": 10, "carreras": 10, "licenciatura": 9, "técnico": 9,
        "superior": 8, "beneficio": 7, "beca": 7, "admision": 6,
        "modalidad": 6, "requisito": 5, "campus": 5, "emi": 4
    }
    
    palabras_clave.sort(key=lambda x: keyword_priority.get(x, 0), reverse=True)
    return " ".join(palabras_clave)

def corregir_errores_comunes(pregunta: str) -> str:
    correcciones = {
        "emmy": "emi",
        "ingneria": "ingeniería",
        "tecnico": "técnico",
        "admicion": "admisión",
        "que becas": "qué becas",
        "que beneficios": "qué beneficios",
        "que carreras": "qué carreras"
    }
    
    for error, correccion in correcciones.items():
        pregunta = pregunta.replace(error, correccion)
    
    return pregunta

def limpiar_y_traducir_pregunta(pregunta: str) -> str:
    try:
        if any(c in string.ascii_letters for c in pregunta[:10]):
            traduccion = GoogleTranslator(source='auto', target='es').translate(pregunta)
            return normalizar(traduccion)
        return normalizar(pregunta)
    except Exception as e:
        logging.error(f"Error al traducir/limpiar: {e}")
        return normalizar(pregunta)

def limpiar_respuesta_tts(respuesta: str) -> str:
    if not respuesta:
        return respuesta

    caracteres_problematicos = ["*", "#", "•", "~", "_", "**", "__", "```", ">", "`"]
    
    for char in caracteres_problematicos:
        respuesta = respuesta.replace(char, "")

    respuesta = re.sub(r'\n{2,}', '\n', respuesta)
    respuesta = re.sub(r' {2,}', ' ', respuesta)
    respuesta = respuesta.replace('- ', '• ')
    respuesta = re.sub(r'\(\s*\)', '', respuesta)
    
    return respuesta.strip()

def formatear_beneficios(texto: str) -> str:
    if not texto:
        return texto
    
    texto = texto.replace("La EMI ofrece beneficios como", "").strip()
    beneficios = [b.strip() for b in re.split(r'[,;]', texto) if b.strip()]
    
    if len(beneficios) > 1:
        return "Los principales beneficios son: " + ". ".join(beneficios) + "."
    return texto

def es_pregunta_relevante(consulta: str, pregunta_faq: str) -> bool:
    palabras_clave_importantes = {
        "beneficio", "beca", "carrera", "licenciatura", 
        "técnico", "admision", "requisito", "campus", "emi"
    }
    
    consulta_palabras = set(consulta.split())
    pregunta_palabras = set(pregunta_faq.split())
    
    interseccion_importante = palabras_clave_importantes & consulta_palabras & pregunta_palabras
    
    if not interseccion_importante:
        return False
    
    terminos_excluyentes = [
        ("beneficio", "beca"),
        ("licenciatura", "técnico"),
        ("admision", "graduacion")
    ]
    
    for term1, term2 in terminos_excluyentes:
        if (term1 in consulta_palabras and term2 in pregunta_palabras) or \
           (term2 in consulta_palabras and term1 in pregunta_palabras):
            return False
    
    return True

def pregunta_es_valida(pregunta: str) -> bool:
    pregunta_norm = normalizar(pregunta)
    tiene_institucional = any(term in pregunta_norm for term in TEMAS_SOPORTADOS["institucional"])
    tiene_otro_tema = any(
        term in pregunta_norm
        for category in TEMAS_SOPORTADOS.values()
        if category != "institucional"
        for term in category
    )
    return tiene_institucional and tiene_otro_tema

def es_respuesta_relevante(pregunta: str, respuesta: str) -> bool:
    pregunta_norm = normalizar(pregunta)
    respuesta_norm = normalizar(respuesta)
    
    terminos_clave = {
        "beneficio": ["beneficio", "ventaja", "título", "libreta", "laboratorio"],
        "beca": ["beca", "descuento", "financiero", "apoyo económico"],
        "carrera": ["carrera", "licenciatura", "técnico", "plan", "estudio"]
    }
    
    tipo_pregunta = next((k for k in terminos_clave if k in pregunta_norm), None)
    if tipo_pregunta:
        return any(termino in respuesta_norm for termino in terminos_clave[tipo_pregunta])
    
    similitud = fuzz.token_set_ratio(
        extraer_palabras_clave(pregunta_norm),
        extraer_palabras_clave(respuesta_norm)
    )
    return similitud >= 40

def reformular_pregunta(pregunta: str) -> str:
    try:
        prompt = PROMPT_REFORMULADOR.format(pregunta=pregunta)
        respuesta = llm.invoke(prompt)
        return respuesta.content.strip()
    except Exception as e:
        logging.error(f"Error al reformular pregunta: {e}")
        return pregunta  # Devuelve la original si hay error

def guardar_en_base_datos(pregunta: str, respuesta: str):
    try:
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="emi_db"
        )
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO preguntas_frecuentes (pregunta, respuesta) VALUES (%s, %s)",
            (pregunta.strip(), respuesta.strip())
        )
        conexion.commit()
        cursor.close()
        conexion.close()
    except mysql.connector.Error as err:
        logging.error(f"Error al guardar en BD: {err}")

def guardar_pregunta_no_respondida(pregunta: str):
    try:
        pregunta_reformulada = reformular_pregunta(pregunta)
        
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="emi_db"
        )
        cursor = conexion.cursor()
        
        cursor.execute(
            "INSERT INTO preguntas_no_respondidas (pregunta, estado) VALUES (%s, %s)",
            (pregunta_reformulada, "pendiente")
        )
        
        conexion.commit()
        cursor.close()
        conexion.close()
        logging.info(f"Pregunta no respondida guardada: {pregunta_reformulada}")
        
    except mysql.connector.Error as err:
        logging.error(f"Error al guardar pregunta no respondida: {err}")
        
        # Intento alternativo sin reformulación
        try:
            conexion = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root",
                database="emi_db"
            )
            cursor = conexion.cursor()
            cursor.execute(
                "INSERT INTO preguntas_no_respondidas (pregunta) VALUES (%s)",
                (pregunta.strip(),)
            )
            conexion.commit()
            cursor.close()
            conexion.close()
            logging.info(f"Pregunta no respondida (fallback) guardada: {pregunta}")
        except mysql.connector.Error as err_fallback:
            logging.error(f"Error crítico en fallback al guardar pregunta: {err_fallback}")

def responder_sin_informacion(query: str) -> str:
    """Función auxiliar para manejar consistentemente las respuestas sin información"""
    guardar_pregunta_no_respondida(query)
    return "No cuento con esta información en este momento."

def search_faq(query: str, threshold: int = 95) -> str:
    try:
        with open(faq_file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        preguntas = [(item["pregunta"], item["respuesta"]) for item in data.get("preguntas_frecuentes", [])]
        query_procesada = corregir_errores_comunes(normalizar(query))

        # 1. Coincidencia exacta
        for pregunta, respuesta in preguntas:
            if query.strip().lower() == pregunta.strip().lower():
                return respuesta

        # 2. Coincidencia normalizada
        for pregunta, respuesta in preguntas:
            if normalizar(query) == normalizar(pregunta):
                return respuesta

        # 3. Fuzzy matching
        mejor_puntaje = 0
        mejor_respuesta = ""
        mejor_pregunta = ""
        
        for pregunta, respuesta in preguntas:
            pregunta_procesada = corregir_errores_comunes(normalizar(pregunta))
            puntaje = fuzz.token_set_ratio(query_procesada, pregunta_procesada)
            
            palabras_coincidentes = set(query_procesada.split()) & set(pregunta_procesada.split())
            
            if (puntaje > mejor_puntaje and puntaje >= threshold and 
                len(palabras_coincidentes) >= 3 and 
                es_pregunta_relevante(query_procesada, pregunta_procesada)):
                
                mejor_puntaje = puntaje
                mejor_respuesta = respuesta
                mejor_pregunta = pregunta

        if mejor_puntaje >= threshold:
            logging.info(f"Match FAQ encontrado (Puntaje: {mejor_puntaje}): {mejor_pregunta}")
            return mejor_respuesta

        return ""

    except Exception as e:
        logging.error(f"Error en búsqueda FAQ: {e}")
        return ""

# ============ Función principal del chatbot ============
def chat_with_memory(query: str) -> str:
    try:
        # Paso 1: Búsqueda en FAQ
        respuesta_faq = search_faq(query, threshold=95)
        
        if respuesta_faq:
            query_procesada = limpiar_y_traducir_pregunta(query)
            query_procesada = corregir_errores_comunes(query_procesada)
            
            if es_respuesta_relevante(query_procesada, respuesta_faq):
                guardar_en_base_datos(query_procesada, respuesta_faq)
                return limpiar_respuesta_tts(respuesta_faq)
            else:
                logging.info("Respuesta FAQ descartada por falta de relevancia")
                return responder_sin_informacion(query)
        
        # Paso 2: Preprocesamiento
        query_procesada = limpiar_y_traducir_pregunta(query)
        query_procesada = corregir_errores_comunes(query_procesada)

        # Paso 3: Validación
        if not pregunta_es_valida(query_procesada):
            return responder_sin_informacion(query)

        # Paso 4: Consulta específica para beneficios
        if "beneficio" in query_procesada:
            prompt = (
                "Lista los beneficios de la EMI de forma clara y concisa. "
                "Usa solo información de la tabla beneficios.\n"
                f"Pregunta: {query_procesada}"
            )
            result = agent_executor.invoke({"input": prompt})
            respuesta_bd = result.get("output", "").strip()
            
            if respuesta_bd and "no tengo" not in respuesta_bd.lower():
                respuesta_limpia = limpiar_respuesta_tts(formatear_beneficios(respuesta_bd))
                guardar_en_base_datos(query_procesada, respuesta_limpia)
                return respuesta_limpia
            else:
                return responder_sin_informacion(query)
        
        # Consulta normal
        prompt = (
            "Responde de forma concisa y directa a la pregunta sobre la EMI.\n"
            f"Pregunta: {query_procesada}\n\n"
            "Si no sabes, di exactamente: 'No cuento con esta información en este momento.'"
        )
        result = agent_executor.invoke({"input": prompt})
        respuesta_bd = result.get("output", "").strip()

        # Paso 5: Validación y retorno
        if not respuesta_bd or "no cuento con esta información" in respuesta_bd.lower():
            return responder_sin_informacion(query)
        
        respuesta_limpia = limpiar_respuesta_tts(respuesta_bd)
        guardar_en_base_datos(query_procesada, respuesta_limpia)
        return respuesta_limpia

    except Exception as e:
        logging.error(f"Error general: {e}")
        guardar_pregunta_no_respondida(query)
        return "Ocurrió un error al procesar tu consulta."
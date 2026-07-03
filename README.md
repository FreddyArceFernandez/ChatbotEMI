# ChatbotEMI

Asistente virtual inteligente para la Escuela Militar de Ingeniería (EMI), integrado en un
entorno virtual 3D desarrollado en Unity. Proyecto de tesis de grado — Ingeniería de Sistemas.

## Descripción

Los usuarios interactúan con un personaje virtual dentro de un entorno modelado en Unity 3D.
Las preguntas del usuario se envían a un backend en Python que combina dos estrategias de
respuesta:

1. **Coincidencia de preguntas frecuentes** — búsqueda por similitud (`difflib`) sobre una base
   de preguntas y respuestas predefinidas sobre la institución.
2. **Generación con LLM** — cuando no hay coincidencia suficiente, se genera una respuesta con
   GPT-4o-mini vía LangChain, usando contexto institucional y memoria de las últimas
   interacciones de la conversación.

Incluye traducción automática de la entrada del usuario (vía `deep_translator`), lo que permite
recibir preguntas en distintos idiomas.

**Entrada por voz:** Unity ejecuta un modelo Whisper instalado localmente en el equipo, que
transcribe el audio del usuario a texto antes de enviarlo como petición al backend. La
transcripción ocurre del lado del cliente (Unity), no en este repositorio.

Un panel de administración independiente (FastAPI + MySQL) permite gestionar un banco de
preguntas frecuentes. Actualmente esta base MySQL es independiente de la fuente de datos que usa
`chat_with_memory()` para el matching de preguntas frecuentes — es una mejora pendiente
sincronizar ambas fuentes.

## Arquitectura

```
Unity 3D (cliente)
      │  audio del usuario
      ▼
Whisper (modelo local, transcripción en el cliente)
      │  texto de la petición
      ▼
Servidor Python (FastAPI)
      │
      ├─► chat_with_memory()  →  LangChain + GPT-4o-mini (fallback)
      │         │
      │         └─► Matching de preguntas frecuentes (difflib, fuente local)
      │
      └─► Memoria de conversación (ventana de últimas interacciones)

Panel de administración (independiente, no sincronizado aún con el matching local)
Frontend + FastAPI + MySQL  →  gestión de preguntas frecuentes
```

## Stack técnico

- **IA / NLP:** LangChain, OpenAI GPT-4o-mini, Whisper (local, transcripción de voz en el cliente), `deep_translator`
- **Backend:** Python, FastAPI, SQLAlchemy
- **Base de datos:** MySQL
- **Entorno virtual:** Unity 3D
- **Frontend (panel admin y demos de chat):** HTML/CSS/JS

## Estructura del proyecto

```
ChatbotEMI/
├─ src/
│  ├─ chatbot/       # Lógica principal del asistente y servidor
│  ├─ auth/          # Autenticación
│  ├─ persistence/   # Acceso a datos y memoria de conversación
│  └─ admin/         # Panel de administración (backend + frontend, CRUD de FAQs)
├─ frontend/
│  ├─ templates/      # Vistas de demostración (chat con memoria, audio, imágenes)
│  └─ resources/      # CSS, JS, imágenes
├─ requirements.txt
└─ README.md
```

## Instalación y uso

```bash
git clone https://github.com/FreddyArceFernandez/ChatbotEMI.git
cd ChatbotEMI
pip install -r requirements.txt
```

Configura tu API key de OpenAI y las credenciales de MySQL según corresponda (ver `.env.example`
<!-- TODO: crear un .env.example con las variables necesarias, sin valores reales --> ).

```bash
# Backend principal del chatbot
uvicorn src.chatbot.server:app --reload

# Panel de administración
uvicorn src.admin.backend.main:app --reload
```

<!-- TODO: confirmar comandos exactos de arranque una vez revisados server.py y
     src/admin/backend/main.py -->

## Estado del proyecto

Proyecto de tesis, funcional en su núcleo (lógica de IA + integración Unity + panel admin).



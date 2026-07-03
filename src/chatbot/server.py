from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .chatbot import chat_with_memory
import os
import tempfile
import simpleaudio as sa
from fastapi.responses import FileResponse
import edge_tts
import asyncio
import threading
from typing import Optional
import subprocess

app = FastAPI()

# Configuración de Edge TTS
VOICES = {
    'mexicana': 'es-MX-DaliaNeural',
    'colombiana': 'es-CO-SalomeNeural',
    'argentina': 'es-AR-ElenaNeural',
    'mexicano': 'es-MX-JorgeNeural',
    'peruano': 'es-PE-AlexNeural',
    'colombiano': 'es-CO-GonzaloNeural'
}
SELECTED_VOICE = VOICES['mexicano']
RATE = "+10%"
PITCH = "+5Hz"

class Message(BaseModel):
    text: str

async def convert_to_wav(input_path: str, output_path: str) -> bool:
    """Convierte el audio a formato WAV usando ffmpeg"""
    try:
        cmd = [
            'ffmpeg',
            '-y',  # Sobrescribir sin preguntar
            '-i', input_path,
            '-acodec', 'pcm_s16le',  # Códec PCM para WAV
            '-ar', '44100',  # Tasa de muestreo
            '-ac', '2',  # Audio estéreo
            output_path
        ]
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except Exception as e:
        print(f"⚠️ Error al convertir audio: {e}")
        return False

async def generate_audio(text: str) -> Optional[str]:
    """Genera audio y devuelve la ruta del archivo WAV"""
    try:
        # Primero generar archivo MP3 con Edge TTS
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as mp3_file:
            mp3_path = mp3_file.name
        
        communicate = edge_tts.Communicate(
            text=text,
            voice=SELECTED_VOICE,
            rate=RATE,
            pitch=PITCH
        )
        await communicate.save(mp3_path)

        # Convertir a WAV
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as wav_file:
            wav_path = wav_file.name
        
        if not await convert_to_wav(mp3_path, wav_path):
            return None

        return wav_path
    except Exception as e:
        print(f"⚠️ Error al generar audio: {e}")
        return None
    finally:
        # Limpiar archivo MP3 temporal
        if 'mp3_path' in locals() and os.path.exists(mp3_path):
            try:
                os.unlink(mp3_path)
            except Exception as e:
                print(f"⚠️ No se pudo eliminar archivo MP3 temporal: {e}")

def play_audio(temp_path: str) -> None:
    """Reproduce audio y elimina el archivo temporal"""
    try:
        wave_obj = sa.WaveObject.from_wave_file(temp_path)
        play_obj = wave_obj.play()
        play_obj.wait_done()
    except Exception as e:
        print(f"⚠️ Error al reproducir audio: {e}")
    finally:
        try:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
        except Exception as e:
            print(f"⚠️ No se pudo eliminar archivo temporal: {e}")

@app.post("/send")
async def chat_with_gpt(message: Message):
    try:
        print(f"📩 Mensaje recibido: {message.text}")
        response = chat_with_memory(message.text)
        print(f"📤 Respuesta generada: {response}")
        
        temp_path = await generate_audio(response)
        if temp_path:
            threading.Thread(target=play_audio, args=(temp_path,)).start()
        
        return {"response": response}
    except Exception as e:
        print(f"⚠️ Error en el endpoint /send: {e}")
        return {"response": f"Error: {str(e)}"}

@app.post("/get_audio")
async def get_audio(message: Message):
    try:
        print(f"📩 Solicitud de audio para: {message.text}")
        temp_path = await generate_audio(message.text)
        if not temp_path:
            raise HTTPException(status_code=500, detail="Error al generar audio")

        # Se usa BackgroundTask (de Starlette) para que play_audio se ejecute después de enviar el archivo
        return FileResponse(
            path=temp_path,
            media_type="audio/wav",
            filename="respuesta.wav",
            background=BackgroundTask(play_audio, temp_path)
        )
    except HTTPException:
        # Si ya se levantó un HTTPException, se vuelve a lanzar
        raise
    except Exception as e:
        print(f"⚠️ Error en el endpoint /get_audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
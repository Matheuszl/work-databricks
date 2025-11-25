from fastapi import FastAPI, HTTPException
from databricks import sql
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Literal
import agents as agents 
import database
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from io import BytesIO
from dotenv import load_dotenv
import base64
import wave
import time

load_dotenv()

app = FastAPI()

# Initialize database
database.init_db()

# Adiciona o middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

class PerguntaRequest(BaseModel):
    pergunta: str
    tipo_conta: Literal["conta-corrente", "vale-alimentacao", "cartao-credito"]
    conversation_id: Optional[int] = None

class PerguntaResponse(BaseModel):
    sql_gerado: str
    dados: Any
    grafico: Dict[str, Any]
    analise_texto: str
    conversation_id: int

class Conversation(BaseModel):
    id: int
    title: str
    created_at: str

class Message(BaseModel):
    id: int
    conversation_id: int
    sender: str
    content: str
    chart_data: Optional[Dict[str, Any]] = None
    created_at: str

class RenameRequest(BaseModel):
    title: str

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "Puck"

@app.post("/conta-corrente", response_model=PerguntaResponse)
def ask_question(request: PerguntaRequest):
    try:
        conversation_id = request.conversation_id
        
        # Create new conversation if not provided
        if not conversation_id:
            # Use the first few words of the question as the title
            title = " ".join(request.pergunta.split()[:5])
            conversation_id = database.create_conversation(title)
        
        # Save user message
        database.add_message(conversation_id, "user", request.pergunta)

        # O módulo sql já está importado no topo do arquivo
        # Agora passe-o para agents.main()
        sql_gerado, dados, grafico, texto = agents.main(
            request.pergunta, 
            request.tipo_conta,
            sql  # Passa o módulo sql do databricks importado no topo
        )
        
        # Se `grafico` for None, use um dicionário vazio no lugar
        grafico_para_retorno = grafico if grafico is not None else {}
        
        # Save AI response
        database.add_message(conversation_id, "ai", texto, grafico_para_retorno)

        return {
            "sql_gerado": sql_gerado,
            "dados": dados,
            "grafico": grafico_para_retorno,
            "analise_texto": texto,
            "conversation_id": conversation_id
        }

    except NotImplementedError as e:
        print(f"❌ NotImplementedError: {e}")
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        print(f"❌ ERRO COMPLETO: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@app.get("/conversations", response_model=List[Conversation])
def get_conversations():
    return database.get_conversations()

@app.post("/conversations", response_model=Conversation)
def create_conversation():
    id = database.create_conversation("Nova Conversa")
    conversations = database.get_conversations()
    for c in conversations:
        if c['id'] == id:
             return c
    return {"id": id, "title": "Nova Conversa", "created_at": ""}

@app.patch("/conversations/{conversation_id}")
def rename_conversation(conversation_id: int, request: RenameRequest):
    try:
        database.update_conversation_title(conversation_id, request.title)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int):
    try:
        database.delete_conversation(conversation_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations/{conversation_id}/messages", response_model=List[Message])
def get_messages(conversation_id: int):
    return database.get_messages(conversation_id)

@app.post("/tts")
def text_to_speech(request: TTSRequest):
    try:
        print(f"🎵 TTS Request - Text: '{request.text[:50]}...', Voice: {request.voice}")

        client = genai.Client(api_key=os.getenv("IA_STUDIO"))

        # Validação da voz
        valid_voices = ["Puck", "Charon", "Kore", "Fenrir", "Aoede"]
        voice_name = request.voice if request.voice in valid_voices else "Puck"

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                print(f"Gerando áudio (Tentativa {attempt + 1}/{max_retries})...")
                response = client.models.generate_content(
                    model='gemini-2.5-flash-preview-tts',
                    contents=[
                        types.Content(
                            parts=[
                                types.Part(text=request.text)
                            ]
                        )
                    ],
                    config=types.GenerateContentConfig(
                        response_modalities=['AUDIO'],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=voice_name
                                )
                            )
                        )
                    )
                )

                print(f"✅ Response received from Gemini")

                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.inline_data:
                            # 1. Pegamos os dados crus (PCM)
                            raw_audio_data = part.inline_data.data 
                            
                            print(f"MIME Type recebido: {part.inline_data.mime_type}")
                            
                            # 2. Configurações baseadas no retorno 'audio/L16;codec=pcm;rate=24000'
                            # L16 = 16 bits = 2 bytes
                            # Rate = 24000
                            
                            # 3. Usamos a biblioteca wave para criar o cabeçalho correto em memória
                            wav_buffer = BytesIO()
                            with wave.open(wav_buffer, "wb") as wav_file:
                                wav_file.setnchannels(1)      # Geralmente é Mono (1 canal)
                                wav_file.setsampwidth(2)      # 2 bytes (16 bits)
                                wav_file.setframerate(24000)  # Taxa de amostragem de 24kHz
                                wav_file.writeframes(raw_audio_data)
                            
                            wav_buffer.seek(0)
                            print(f"✅ Áudio encapsulado corretamente (WAV) - Size: {wav_buffer.getbuffer().nbytes} bytes")
                                
                            return StreamingResponse(
                                wav_buffer, 
                                media_type="audio/wav",
                                headers={
                                    "Content-Disposition": "inline; filename=tts_output.wav",
                                }
                            )
                
                print("❌ No audio data found in response")
                raise Exception("A resposta da IA não conteve dados de áudio.")

            except Exception as e:
                error_str = str(e)
                if "503" in error_str or "overloaded" in error_str.lower():
                    if attempt < max_retries - 1:
                        print(f"⚠️ Modelo sobrecarregado. Tentando novamente em {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                raise e

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error generating audio: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Erro no Gemini: {error_msg}")      


@app.get("/")
def serve_frontend():
    caminho = os.path.join(os.path.dirname(__file__), "index.html")
    return FileResponse(caminho)
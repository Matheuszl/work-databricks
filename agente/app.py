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

        # Instancia o cliente do NOVO SDK
        client = genai.Client(api_key=os.getenv("IA_STUDIO"))

        # Validar voz (Puck, Charon, Kore, Fenrir, Aoede)
        # Se a voz não for uma dessas, pode causar erro, então defina um fallback
        valid_voices = ["Puck", "Charon", "Kore", "Fenrir", "Aoede"]
        voice_name = request.voice if request.voice in valid_voices else "Puck"

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            # Dica: Às vezes, adicionar uma instrução explícita ajuda o modelo a focar no áudio
            contents=f"Please read the following text aloud naturally: {request.text}",
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
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

        # Extração dos dados de áudio
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                # Verifica se é dados inline (blob)
                if part.inline_data:
                    audio_data = part.inline_data.data
                    # O Gemini retorna 'audio/pcm' ou 'audio/wav' geralmente
                    mime_type = part.inline_data.mime_type or 'audio/wav'
                    
                    # Se vier como string base64, decodifica. Se vier bytes, usa direto.
                    if isinstance(audio_data, str):
                        audio_bytes = base64.b64decode(audio_data)
                    else:
                        audio_bytes = audio_data
                    
                    print(f"✅ Audio bytes ready - Size: {len(audio_bytes)} bytes")
                        
                    return StreamingResponse(
                        BytesIO(audio_bytes), 
                        media_type=mime_type,
                        headers={
                            "Content-Disposition": "inline; filename=tts_output.wav",
                        }
                    )
        
        print("❌ No audio data found in response")
        raise Exception("A resposta da IA não conteve dados de áudio.")

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error generating audio: {error_msg}")
        # ... (seu tratamento de erro existente) ...
        raise HTTPException(status_code=500, detail=f"Erro ao gerar áudio: {error_msg}")
        
@app.get("/")
def serve_frontend():
    caminho = os.path.join(os.path.dirname(__file__), "index.html")
    return FileResponse(caminho)
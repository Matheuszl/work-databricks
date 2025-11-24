from fastapi import FastAPI, HTTPException
from databricks import sql
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import agents as agents 
from typing import Literal
import database

from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from gtts import gTTS
from io import BytesIO

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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    # Assuming the last one is the new one, or just returning a placeholder to satisfy the model if the original code was broken.
    # I'll try to find the created conversation.
    for c in conversations:
        if c['id'] == id: # Assuming dictionary or object
             return c
    # Fallback if not found (should not happen)
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
        # Generate audio using gTTS with Brazilian Portuguese accent
        tts = gTTS(text=request.text, lang='pt', tld='com.br', slow=False)
        audio_fp = BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        return StreamingResponse(audio_fp, media_type="audio/mpeg")
    except Exception as e:
        print(f"Error generating audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def serve_frontend():
    caminho = os.path.join(os.path.dirname(__file__), "index.html")
    return FileResponse(caminho)
from fastapi import FastAPI, HTTPException
from databricks import sql
from pydantic import BaseModel
from typing import Any, Dict
import agents as agents 
from typing import Literal

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Adiciona o middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PerguntaRequest(BaseModel):
    pergunta: str
    tipo_conta: Literal["conta-corrente", "vale-alimentacao", "cartao-credito"]

class PerguntaResponse(BaseModel):
    sql_gerado: str
    dados: Any
    grafico: Dict[str, Any]
    analise_texto: str

        
@app.post("/conta-corrente", response_model=PerguntaResponse)
def ask_question(request: PerguntaRequest):  # ← Removido o parâmetro "sql"
    try:
        # O módulo sql já está importado no topo do arquivo
        # Agora passe-o para agents.main()
        sql_gerado, dados, grafico, texto = agents.main(
            request.pergunta, 
            request.tipo_conta,
            sql  # ← Passa o módulo sql do databricks importado no topo
        )
        
        # Se `grafico` for None, use um dicionário vazio no lugar
        grafico_para_retorno = grafico if grafico is not None else {}

        return {
            "sql_gerado": sql_gerado,  # ← Renomeei para evitar confusão com o módulo
            "dados": dados,
            "grafico": grafico_para_retorno,
            "analise_texto": texto
        }

    except NotImplementedError as e:
        print(f"❌ NotImplementedError: {e}")  # ← Debug
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        print(f"❌ ERRO COMPLETO: {e}")  # ← Debug
        import traceback
        traceback.print_exc()  # ← Mostra o stack trace completo
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")  # ← Mostra o erro
    

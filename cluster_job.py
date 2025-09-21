import os
import json
import requests
import pandas as pd

from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()


DATABRICKS_INSTANCE = os.getenv("DATABRICKS_HOST")  # coloque sua URL no .env
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")  # coloque seu token no .env
JOB_ID = os.getenv("DATABRICKS_ID_JOB")


df = pd.DataFrame({
    "id": [1, 2, 3],
    "nome": ["Alice", "Bob", "Carol"],
    "idade": [25, 30, 22]
})
data_json = df.to_json(orient="records")



def enviar_para_databricks(job_id: str, payload: str):
    url = f"{DATABRICKS_INSTANCE}/api/2.1/jobs/run-now"

    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json"
    }

    body = {
        "job_id": job_id,
        "notebook_params": {
            "dados": payload
        }
    }

    response = requests.post(url, headers=headers, data=json.dumps(body))

    if response.status_code == 200:
        print("Dados enviados com sucesso!")
        print(response.json())
    else:
        print("Erro ao enviar:", response.status_code, response.text)


if __name__ == "__main__":
    enviar_para_databricks(JOB_ID, data_json)

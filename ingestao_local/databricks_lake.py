from databricks import sql
import os

from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
HTTPS_PATH = os.getenv("HTTP_PATH")
SERVER_HOSTNAME = os.getenv("SERVER_HOSTNAME")

connection = sql.connect(
                        server_hostname = SERVER_HOSTNAME,
                        http_path = HTTPS_PATH,
                        access_token = DATABRICKS_TOKEN)

cursor = connection.cursor()

cursor.execute("SELECT * FROM workspace.db_work_databricks.prata_cc WHERE tipo_movimentacao = 'Entrada'")
print(cursor.fetchall())

cursor.close()
connection.close()
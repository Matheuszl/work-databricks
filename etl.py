import pandas as pd
import numpy as np
import json
import re
import os
import requests
import argparse
from datetime import datetime

from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

DATABRICKS_INSTANCE = os.getenv("DATABRICKS_HOST")  # coloque sua URL no .env
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")  # coloque seu token no .env
JOB_ID = os.getenv("DATABRICKS_ID_JOB")

def processar_arquivo_excel(caminho_arquivo):
    """
    Processa um arquivo Excel (.xls/.xlsx) e retorna um DataFrame com os dados limpos
    """
    try:
        # Lê o arquivo Excel ignorando as 10 primeiras linhas
        df = pd.read_excel(caminho_arquivo, skiprows=10, header=None)
        
        # Encontra o índice onde está "Saldo da Conta" ou uma linha em branco
        indice_final = None
        
        for idx, row in df.iterrows():
            # Verifica se todos os valores da linha são NaN ou espaços em branco
            is_linha_vazia = all(
                pd.isna(valor) or (isinstance(valor, str) and valor.strip() == '')
                for valor in row
            )
            
            # Se encontrar "Saldo da Conta" ou linha vazia, para a leitura
            if is_linha_vazia or any(str(valor).strip().lower() == "saldo da conta" for valor in row):
                indice_final = idx
                break
        
        # Se encontrou ponto de parada, corta o DataFrame
        if indice_final is not None:
            df = df.iloc[:indice_final]
        
        # Remove linhas com todos os valores NaN
        df = df.dropna(how='all')
        
        # Remove linhas onde todos os valores são espaços em branco
        df = df[~df.astype(str).apply(lambda x: x.str.strip().eq('').all(), axis=1)]
        
        # Adiciona os cabeçalhos específicos
        novos_cabecalhos = ['data', 'descricao', 'documento', 'valor', 'saldo']
        
        # Verifica se o número de colunas corresponde ao número de cabeçalhos
        if len(df.columns) == len(novos_cabecalhos):
            df.columns = novos_cabecalhos
        else:
            print(f"Aviso: O número de colunas ({len(df.columns)}) não corresponde ao número de cabeçalhos ({len(novos_cabecalhos)})")
            if len(df.columns) > len(novos_cabecalhos):
                df.columns = novos_cabecalhos + [f'coluna_{i+1}' for i in range(len(df.columns) - len(novos_cabecalhos))]
            else:
                df.columns = novos_cabecalhos[:len(df.columns)]
        
        # Aplica as limpezas nos dados
        df_limpo = limpar_dados(df)
        
        return df_limpo
    
    except Exception as e:
        print(f"Erro ao processar o arquivo: {str(e)}")
        return None

def limpar_dados(df):
    """
    Aplica todas as limpezas necessárias no DataFrame
    """
    try:
        # Converte a coluna de data para datetime
        df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
        
        # Limpa os números da coluna descrição
        # Remove números, converte para minúsculas e remove espaços
        df['descricao'] = df['descricao'].apply(
            lambda x: re.sub(r'[0-9]', '', str(x)).lower().strip() if pd.notna(x) else x
        )
        
        # Converte valor e saldo para número
        for coluna in ['valor', 'saldo']:
            if coluna in df.columns:
                df[coluna] = pd.to_numeric(
                    df[coluna].astype(str).str.replace(',', '.').str.replace('R$', '').str.strip(),
                    errors='coerce'
                )
        
        # Armazena o valor original (com sinal negativo se for saída)
        df['valor_original'] = df['valor'].copy()
        
        # Cria a coluna tipo_movimentacao
        df['tipo_movimentacao'] = df.apply(
            lambda row: 'Transferências para Investimentos' if row['descricao'] == 'aplic.financ.aviso previo'
            else ('Entrada' if row['valor'] > 0 else 'Saída' if row['valor'] < 0 else 'Neutra'),
            axis=1
        )
        
        # Cria coluna com valor absoluto
        df['valor'] = df['valor'].abs()
        
        # Adiciona timestamp de processamento
        df['data_processamento'] = datetime.now()
        
        return df
        
    except Exception as e:
        print(f"Erro durante a limpeza dos dados: {str(e)}")
        return df


def verificar_arquivo(caminho_arquivo):
    """
    Verifica se o arquivo existe e fornece informações sobre o problema
    """
    import os
    
    print(f"🔍 Verificando arquivo: {caminho_arquivo}")
    
    # Verifica se o arquivo existe
    if os.path.exists(caminho_arquivo):
        print("✅ Arquivo encontrado!")
        return True
    else:
        print("❌ Arquivo não encontrado!")
        
        # Verifica se o diretório existe
        diretorio = os.path.dirname(caminho_arquivo)
        if os.path.exists(diretorio):
            print(f"📁 Diretório existe: {diretorio}")
            print("📋 Arquivos no diretório:")
            try:
                arquivos = os.listdir(diretorio)
                for arquivo in arquivos:
                    if arquivo.endswith(('.xlsx', '.xls')):
                        print(f"   📄 {arquivo}")
                if not any(arquivo.endswith(('.xlsx', '.xls')) for arquivo in arquivos):
                    print("   ⚠️ Nenhum arquivo Excel encontrado neste diretório")
            except PermissionError:
                print("   ❌ Sem permissão para listar arquivos do diretório")
        else:
            print(f"❌ Diretório não existe: {diretorio}")
            
            # Sugere diretórios alternativos
            partes_caminho = caminho_arquivo.split('/')
            for i in range(len(partes_caminho) - 1, 0, -1):
                caminho_parcial = '/'.join(partes_caminho[:i])
                if os.path.exists(caminho_parcial):
                    print(f"✅ Diretório pai existe: {caminho_parcial}")
                    break
        
        return False

def enviar_databricks(df):
    url = f"{DATABRICKS_INSTANCE}/api/2.1/jobs/run-now"
    
    data_json = df.to_json(orient="records")

    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json"
    }

    body = {
        "job_id": JOB_ID,
        "notebook_params": {
            "dados": data_json
        }
    }

    response = requests.post(url, headers=headers, data=json.dumps(body))

    if response.status_code == 200:
        print("Dados enviados com sucesso!")
        print(response.json())
    else:
        print("Erro ao enviar:", response.status_code, response.text)

def processar_arquivo_unico(caminho_arquivo, enviar_para_databricks=False):
    """
    Processa um único arquivo Excel
    """
    print(f"🔄 Processando arquivo: {os.path.basename(caminho_arquivo)}")
    
    if not verificar_arquivo(caminho_arquivo):
        return None
    
    df_limpo = processar_arquivo_excel(caminho_arquivo)
    
    if df_limpo is not None:
        print(f"✅ Arquivo processado com sucesso! {len(df_limpo)} registros")
        
        if enviar_para_databricks:
            enviar_databricks(df_limpo)
        
        return df_limpo
    else:
        print("❌ Falha no processamento do arquivo.")
        return None


""" 
    - Interface de linha de comando para processar arquivos ou pastas
    - Exemplo de uso:
        python etl.py --modo arquivo --caminho caminho/para/arquivo.xlsx

    - python etl.py --modo arquivo --caminho "C:/Users/mathe/Desktop/Banco de Dados/ContaCorrente/abril22.xls"
    
    Executando o modo arquivo é só alterar o nome do arquivo se ele existir na pasta.
"""
def main():
    parser = argparse.ArgumentParser(description="Processamento de arquivos de conta corrente")
    parser.add_argument(
        "--modo",
        choices=["arquivo"],
        required=True,
        help="Escolha se deseja processar um único arquivo ou uma pasta inteira"
    )
    parser.add_argument(
        "--caminho",
        required=True,
        help="Caminho do arquivo ou da pasta"
    )
    args = parser.parse_args()

    if args.modo == "arquivo":
        print(f"Processando arquivo único: {args.caminho}")
        processar_arquivo_unico(args.caminho, enviar_para_databricks=True)


if __name__ == "__main__":
    main()
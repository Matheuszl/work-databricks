import google.generativeai as genai
import os
import re
import json
from dotenv import load_dotenv

load_dotenv()

# Configuração do Google Gemini
MODEL = genai.GenerativeModel('gemini-2.0-flash')
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)


     
contexto_tabela_conta_corrente = """
    Contexto da tabela 'workspace.db_work_databricks.prata_cc':
    A tabela armazena informações sobre operações financeiras. Cada linha representa um movimento financeiro individual.
    Os dados podem ser utilizados para análises de gastos, receitas e investimentos.
    A tabela contém as seguintes colunas:

    - id (BIGINT): identificador primário da tabela.
    - tipo_movimentacao (TEXT): indica se o movimento foi uma Entrada, Saída ou Transferência para Investimentos.
    - meio_de_pagamento (TEXT): descreve o meio de pagamento utilizado, como Fatura Cartão de Crédito, Boleto (Débito Conta), Compra no Débito, PIX ou Outros.
    - categoria (TEXT): define a categoria do movimento, podendo ser Investimento, Salario, Contas Fixas, Cartão de Crédito ou Outros.
    - motivo (TEXT): descreve o motivo do movimento, como Internet, Luz, Academia, entre outros.
    - valor (DOUBLE): representa o valor financeiro do movimento.
    - data (DATE): armazena a data do movimento no formato AAAA-MM-DD.
    """
    
contexto_tabela_vale_alimentacao = """
    Contexto da tabela 'view_vale_alimentacao':
    Armazena os dados das transações realizadas com o cartão de vale-alimentação, que pode ser utilizado para compras de alimentos, medicamentos, abastecimento de veículos e outros insumos.


    id (INT) identificador unico de cada transacao.
    categoria_estabelecimento (TEXT) identifica a categoria do estabelecimento, contem categorias como: "Mercados", "Farmácias", "Posto de Combustivel", "Restaurantes" ou "Outros".
    valor_transacao (DECIMA) contem o valor da transação.
    data_transacao (DATE) armazena a data da transacao no formato AAAA-MM-DD.
    nome_estabelecimento (TEXT) descreve o nome do estabelecimento de onde ocorreu a transação.
    """
    

def main(pergunta_usuario, falg_tabela, sql):
    if falg_tabela == "conta-corrente":
    
        sql_gerado = gerar_sql_agent_conta_corrente(pergunta_usuario, contexto_tabela_conta_corrente)
        dados_recuperados = processar_sql_bd(sql_gerado, sql)
        grafico_gerado = gerar_grafico_agent_visualizacao(dados_recuperados)
        analise_gerada = gerar_anase_agent_negocios(dados_recuperados, contexto_tabela_conta_corrente, pergunta_usuario)
    
        return sql_gerado, dados_recuperados, grafico_gerado, analise_gerada
    
    elif falg_tabela == "vale-alimentacao":

        sql_gerado = gerar_sql_agent_conta_corrente(pergunta_usuario, contexto_tabela_vale_alimentacao)
        dados_recuperados = processar_sql_bd(sql_gerado)
        grafico_gerado = gerar_grafico_agent_visualizacao(dados_recuperados)
        analise_gerada = gerar_anase_agent_negocios(dados_recuperados, contexto_tabela_vale_alimentacao, pergunta_usuario)
    
        return sql_gerado, dados_recuperados, grafico_gerado, analise_gerada
    
    else:
        print("Endpoint invalido!")
               
def gerar_sql_agent_conta_corrente(pergunta_usuario, contexto_tabela):
    print("Executando: Geração do SQL")

    prompt = f"""{contexto_tabela}

        Sua tarefa é converter a pergunta abaixo em uma consulta SQL para Databricks (Spark SQL) do tipo SELECT. 

        IMPORTANTE - Regras de sintaxe do Databricks:
        - Use DATE_FORMAT(coluna, 'formato') para formatar datas
        - Use YEAR(coluna), MONTH(coluna), DAY(coluna) para extrair partes de datas
        - NUNCA use STRFTIME (não existe no Databricks)
        - Para agrupar por mês/ano: use DATE_FORMAT(data, 'yyyy-MM')
        - Formato de data: 'yyyy-MM-dd' (não '%Y-%m-%d')
        
        Exemplos de conversão:
        Errado: STRFTIME('%Y-%m', data)
        Correto: DATE_FORMAT(data, 'yyyy-MM')
        
        Errado: STRFTIME('%Y', data)
        Correto: YEAR(data)

        - Retorne apenas o código SQL, sem explicações.
        - Use nomes de colunas exatamente como estão no contexto.
        - Caso haja filtros de data, considere o formato AAAA-MM-DD (yyyy-MM-dd).

        Pergunta do usuário: {pergunta_usuario}
        """

    response = MODEL.generate_content(prompt)
    
    # Junta todas as partes da resposta em uma string única
    sql_query_raw = "".join(part.text for part in response.parts)

    # Remove blocos markdown e espaços extras
    sql_query = sql_query_raw.strip().replace("```sql", "").replace("```", "").strip()
    
    # Adicione print para debug
    print("📝 SQL Gerado")
    #print_logs(sql_query)
    
    return sql_query


def processar_sql_bd(resposta_sql, sql):
    print("Executando: Processamento do SQL")

    DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
    HTTPS_PATH = os.getenv("HTTP_PATH")
    SERVER_HOSTNAME = os.getenv("SERVER_HOSTNAME")

    connection = sql.connect(
                            server_hostname = SERVER_HOSTNAME,
                            http_path = HTTPS_PATH,
                            access_token = DATABRICKS_TOKEN)

    cursor = connection.cursor()

    cursor.execute(resposta_sql)
    resposta = cursor.fetchall()

    cursor.close()
    connection.close()
        
    return resposta

def gerar_grafico_agent_visualizacao(dados_recuperados):
    print("Executando: Geração do Gráfico")
    
    prompt_agente_visualizacao = f"""
        <ROLE>
        Você é um especialista em visualização de dados que gera exclusivamente configurações JSON para Chart.js.
        </ROLE>

        <DADOS>
        {dados_recuperados}
        </DADOS>

        <TAREFA_PRIMARIA>
        Analise os dados fornecidos e retorne EXCLUSIVAMENTE uma configuração JSON válida para Chart.js no formato especificado.
        </TAREFA_PRIMARIA>

        <FORMATO_OBRIGATORIO>
        Sua resposta deve conter APENAS uma linha no seguinte formato exato:
        grafico = {{"type": "TIPO", "data": {{"labels": [ARRAY_LABELS], "datasets": [{{"label": "NOME_SERIE", "data": [ARRAY_VALORES]}}]}}}}

        Onde:
        - TIPO: "bar", "line", "pie", ou "scatter"
        - ARRAY_LABELS: array com strings das chaves/categorias dos dados
        - NOME_SERIE: nome descritivo para a série de dados
        - ARRAY_VALORES: array com valores numéricos extraídos dos dados
        </FORMATO_OBRIGATORIO>

        <REGRAS_CRITICAS>
        PROIBIDO:
        - Código Python (import, print, loops, variáveis, etc.)
        - Comentários ou explicações
        - Múltiplas linhas de resposta
        - Propriedades CSS/visuais (backgroundColor, borderColor, etc.)
        - Texto antes ou depois da linha "grafico = "
        - Usar aspas simples (use apenas aspas duplas)
        - Quebras de linha no JSON

        OBRIGATÓRIO:
        - Resposta de uma única linha
        - JSON válido e bem formatado
        - Começar com "grafico = "
        - Usar apenas aspas duplas no JSON
        - Converter valores Decimal para números
        - Escolher tipo de gráfico apropriado aos dados
        </REGRAS_CRITICAS>

        <SELECAO_TIPO_GRAFICO>
        - bar: Para comparações categóricas (padrão para a maioria dos casos)
        - line: Para dados temporais/sequenciais com tendências
        - pie: Para proporções de um total (máximo 6 categorias)
        - scatter: Para correlações entre duas variáveis numéricas
        </SELECAO_TIPO_GRAFICO>

        <EXEMPLOS_CORRETOS>
        Dados: [{{'categoria': 'A', 'valor': 10}}, {{'categoria': 'B', 'valor': 20}}]
        Saída: grafico = {{"type": "bar", "data": {{"labels": ["A", "B"], "datasets": [{{"label": "Valor", "data": [10, 20]}}]}}}}

        Dados: [{{'mes': '2025-01', 'vendas': 100}}, {{'mes': '2025-02', 'vendas': 150}}]
        Saída: grafico = {{"type": "line", "data": {{"labels": ["2025-01", "2025-02"], "datasets": [{{"label": "Vendas", "data": [100, 150]}}]}}}}
        </EXEMPLOS_CORRETOS>

        <EXEMPLO_INCORRETO>
        NÃO FAÇA ISSO:
        ```python
        dados = [...]
        labels = [...]
        # Comentário
        print("grafico = " + json.dumps(...))
        ```
        </EXEMPLO_INCORRETO>

        <VALIDACAO_FINAL>
        Antes de responder, verifique:
        1. ✓ Resposta é uma única linha?
        2. ✓ Começa com "grafico = "?
        3. ✓ JSON usa apenas aspas duplas?
        4. ✓ Não há código Python?
        5. ✓ Valores numéricos estão convertidos de Decimal?
        6. ✓ Tipo de gráfico é apropriado?
        </VALIDACAO_FINAL>

        <INSTRUCAO_FINAL>
        RESPONDA AGORA com apenas a linha de configuração JSON, seguindo rigorosamente o formato especificado.
        </INSTRUCAO_FINAL>
        """
    
    response_visualizacao = MODEL.generate_content(prompt_agente_visualizacao)
    code_vizualizacao = "".join(part.text for part in response_visualizacao.parts)

    # Remove blocos de markdown se existirem
    code_vizualizacao = code_vizualizacao.replace("```json", "").replace("```", "").strip()

    # print_logs(code_vizualizacao)

    # Extrai apenas o JSON após 'grafico ='
    match = re.search(r"grafico\s*=\s*(\{.*\})", code_vizualizacao, re.DOTALL)
    
    if match:
        json_string = match.group(1)
        try:
            grafico_dict = json.loads(json_string)
            
            print("Gráfico gerado com sucesso.")

            return grafico_dict
        except json.JSONDecodeError as e:
            print("Erro ao decodificar JSON:", e)
            return None
    else:
        print("Formato inválido na resposta do modelo.")
        return None

def gerar_anase_agent_negocios(dados_recuperados, contexto_tabela, pergunta_usuario):

    
    prompt_analise = f"""
        Você é um analista de dados especialista em finanças pessoais. Sua tarefa é analisar um conjunto de dados extraído em resposta a uma pergunta de um usuário e apresentar os resultados de forma clara e estruturada.

        Pergunta Original do Usuário:
        "{pergunta_usuario}"

        Contexto do Banco de Dados:
        {contexto_tabela}

        Dados Extraídos para Análise:
        {dados_recuperados}

        Sua Resposta (Siga esta estrutura rigorosamente):

        (Comece com uma frase única e objetiva que responda diretamente à pergunta do usuário. Ex: "No total, você gastou R$ X em Y nos últimos Z meses.")

        (Aqui, detalhe os dados. Descreva as tendências, compare os períodos, aponte o mês de maior e menor valor e calcule a média, se aplicável. Apresente os fatos observados nos dados.)

        (Esta é a parte mais importante. O que os dados significam? Qual é a história por trás dos números? Se houve um aumento, qual poderia ser a causa? Ofereça uma interpretação. Ex: "O aumento de 17% em junho pode indicar mais deslocamentos ou uma alta no preço dos combustíveis.")

        Regras Adicionais:
        - Baseie-se estritamente nos dados fornecidos.
        - Não use formatação como negrito ou itálico. Use os marcadores de seção como [TÍTULO] exatamente como mostrado.
        - Lembre-se, você é um analista, não um consultor financeiro. Não dê conselhos de investimento.
        """
    
    print("Executando: Geração da Análise de descritiva e prescritiva")
        
    response = MODEL.generate_content(prompt_analise)

    #print_logs(response)

    return "".join(part.text for part in response.parts).strip()


def print_logs(msg):
    return print(msg)
# Analista Financeiro (Assessor 2.0)

Este projeto é uma aplicação web de assistente financeiro inteligente que permite aos usuários interagir com seus dados financeiros através de linguagem natural. Utilizando o poder do Google Gemini AI e Databricks, o sistema converte perguntas em consultas SQL, gera visualizações gráficas e fornece análises detalhadas sobre gastos e transações.

## Funcionalidades Principais

*   **Chat Inteligente:** Interface de chat para fazer perguntas sobre dados financeiros (ex: "Quanto gastei com alimentação mês passado?").
*   **Geração Automática de SQL:** O sistema converte perguntas em linguagem natural para SQL compatível com Databricks.
*   **Visualização de Dados:** Geração automática de gráficos interativos (barras, linhas, pizza, dispersão) usando Chart.js.
*   **Análise Descritiva e Prescritiva:** A IA analisa os dados recuperados para fornecer insights, identificar tendências e explicar o comportamento financeiro.
*   **Histórico de Conversas:** As conversas são salvas localmente, permitindo criar novos chats, renomear e excluir históricos.
*   **Text-to-Speech (TTS):** Funcionalidade para ouvir as respostas da IA com diferentes opções de voz, utilizando o modelo de áudio do Gemini.
*   **Modo Escuro:** Interface responsiva com suporte a tema claro e escuro.

## Estrutura do Projeto e Documentação dos Arquivos

Abaixo está a descrição da responsabilidade de cada arquivo principal no diretório `agente/`:

### Backend (`agente/`)

*   **`app.py`**: O coração da aplicação backend, construído com **FastAPI**.
    *   Gerencia as rotas da API (endpoints) para o chat (`/conta-corrente`), gestão de conversas (`/conversations`) e síntese de voz (`/tts`).
    *   Serve os arquivos estáticos do frontend.
    *   Orquestra a comunicação entre a requisição do usuário, os agentes de IA e o banco de dados.
    *   Configura CORS e variáveis de ambiente.

*   **`agents.py`**: Contém a lógica dos agentes de Inteligência Artificial utilizando **Google Gemini**.
    *   `main()`: Função principal que coordena o fluxo de geração de SQL, execução no banco, criação de gráficos e análise textual.
    *   `gerar_sql_agent_conta_corrente()`: Cria queries SQL baseadas na pergunta do usuário e no contexto das tabelas.
    *   `processar_sql_bd()`: Conecta ao **Databricks** para executar as queries geradas.
    *   `gerar_grafico_agent_visualizacao()`: Analisa os dados retornados e gera uma configuração JSON para renderização de gráficos no frontend.
    *   `gerar_anase_agent_negocios()`: Produz uma análise textual explicativa sobre os dados encontrados.

*   **`database.py`**: Gerencia o banco de dados local **SQLite** (`chat_history.db`) para persistência do histórico.
    *   Inicializa as tabelas `conversations` e `messages`.
    *   Fornece funções para criar, ler, atualizar e deletar (CRUD) conversas e mensagens.

### Frontend (`agente/` e `agente/static/`)

*   **`index.html`**: A estrutura principal da interface web.
    *   Define o layout da aplicação, incluindo a barra lateral de histórico e a área principal de chat.
    *   Importa as bibliotecas necessárias (como Chart.js) e os arquivos estáticos locais.

*   **`static/script.js`**: Contém toda a lógica de interatividade do frontend (JavaScript).
    *   Gerencia o envio de mensagens e chamadas assíncronas (fetch) para o backend.
    *   Manipula o DOM para exibir mensagens, indicadores de carregamento e erros.
    *   Renderiza os gráficos utilizando a biblioteca **Chart.js**.
    *   Controla o player de áudio para a funcionalidade de TTS.
    *   Gerencia o estado da aplicação (conversa atual, tema, modal de gráficos).

*   **`static/styles.css`**: Folha de estilos CSS.
    *   Define a aparência da aplicação, incluindo layouts flexbox, cores, tipografia e animações.
    *   Implementa as variáveis CSS para suportar a alternância entre temas claro e escuro.

### Raiz

*   **`requirements.txt`**: Lista todas as dependências Python necessárias para executar o projeto (ex: `fastapi`, `uvicorn`, `google-genai`, `databricks-sql-connector`).

## Como Executar

1.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure as variáveis de ambiente:**
    Crie um arquivo `.env` na raiz ou em `agente/` com as chaves necessárias (ex: `IA_STUDIO` para Gemini, credenciais do Databricks).

3.  **Inicie o servidor:**
    Navegue até a pasta `agente` e execute:
    ```bash
    uvicorn app:app --reload
    ```

4.  **Acesse a aplicação:**
    Abra o navegador em `http://127.0.0.1:8000`.

# Diário do projeto

Registro de cada etapa: o que foi feito, o que foi medido, o que deu errado e o que foi aprendido. Os erros ficam registrados de propósito, porque é neles que está boa parte do aprendizado.

---

## Day 1: Serving de modelos com Ollama

**Fase:** 1 (Núcleo) · **Competência:** model serving  
**Retorno:** prática (serving de modelos e medição de latência) e visibilidade (post sobre o experimento de alucinação)

### Objetivo
Colocar um LLM e um modelo de embedding para rodar localmente, servidos por uma API HTTP.

### O que foi feito
- Instalação do Ollama
- Download dos modelos `llama3.2:3b` (2,0 GB) e `nomic-embed-text` (274 MB)
- Testes pela linha de comando e pela API HTTP (`/api/generate` e `/api/embed`)

### Medições
Resposta do LLM para "Diga oi em português":

| Métrica | Valor |
|---|---|
| Tokens gerados | 12 |
| Tempo de geração | 56 ms |
| Velocidade | cerca de 214 tokens por segundo |
| Tokens do prompt vindos de cache | 20 de 32 |

Carga do modelo de embedding:

| Situação | `load_duration` |
|---|---|
| Primeira chamada (cold start) | 20,8 s |
| Chamadas seguintes, modelo na memória | cerca de 1,8 s |

O comando `ollama ps` confirmou o modelo carregado 100% na GPU, ocupando 323 MB, com o tempo restante até ser descarregado (`keep_alive`).

**Observação:** mesmo com o modelo já na memória, restou um custo de cerca de 1,8 s por chamada. A hipótese é um custo fixo de preparar cada requisição de inferência, separado do custo de carregar o modelo. Ainda não foi investigado a fundo.

### Experimento: alucinação
A mesma pergunta, com pequenas variações de escrita:

| Pergunta | Resposta do modelo |
|---|---|
| "o que é rag" | Estilo musical (ragtime) |
| "o que é Rag" | Estilo musical, com década de 1920 |
| "o que é retrieval-augmented generation" | Definição técnica correta |
| "o que é RAG" | Inventou a ONG "Rede de Acolhimento e Apoio à Gente" |
| "o que é RAG, baseie em dados reais" | Mesma ONG, agora com ano de fundação (2002) e áreas de atuação, tudo inventado |

### Aprendizados
- A sigla em caixa alta levou o modelo a tratar "RAG" como nome de instituição e, sem informação, ele inventou uma
- Pedir precisão não ativa nenhuma verificação: só deixa o texto inventado mais convincente
- Um LLM sozinho não tem como dizer "não sei". Essa é a justificativa do projeto inteiro

---

## Day 2: Banco vetorial e isolamento multi-tenant

**Fase:** 1 (Núcleo) · **Competência:** armazenamento vetorial, isolamento de dados  
**Retorno:** prática (pgvector, troubleshooting de volume Docker), produto (isolamento por tenant, base de um produto multi-cliente) e visibilidade (post sobre isolamento)

### Objetivo
Guardar documentos e vetores no Postgres com pgvector, com separação por cliente, e fazer buscas via Python.

### O que foi feito
- Postgres 16 com pgvector via Docker Compose, com volume nomeado para persistir os dados
- Tabela `documents` com `tenant_id`, `content` e `embedding VECTOR(768)`
- Índice HNSW para busca por similaridade e índice em `tenant_id`
- Ambiente virtual Python (`.venv`) com `psycopg2-binary` e `requests`
- Funções `generate_embedding`, `insert_document` e `search_similar`

### Problemas e como foram resolvidos

**Disco do Docker.** O disco D: estava com pouco espaço e saúde em 86%. Como o Docker Desktop no Windows guarda imagens e volumes dentro do disco virtual do WSL2, e não na pasta do projeto, o local desse disco virtual foi movido para o G:.

**Usuário que "não existia".** Os nomes de usuário e banco foram trocados de hífen para underscore no `docker-compose.yaml` (hífen em nomes SQL exige aspas em todo lugar). Mesmo recriando o container, o usuário novo não existia.

Causa: as variáveis `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB` só são aplicadas quando o volume está **vazio**, na primeira inicialização. O volume antigo continuava lá, com o usuário antigo.

| Tentativa | Resultado |
|---|---|
| `docker compose up -d` de novo | Não resolveu: volume antigo mantido |
| `docker compose down` | Não resolveu: remove container e rede, mas não volumes |
| `docker compose down -v` | Resolveu: remove também o volume, e o banco foi inicializado do zero |

Isso só foi aceitável porque não havia dados importantes. Em produção, credenciais são alteradas dentro do banco em execução, nunca recriando o volume.

### Experimento: isolamento entre tenants
Dois tenants fictícios na mesma tabela. A mesma pergunta sobre Kubernetes:

| Tenant | Documento retornado | Distância |
|---|---|---|
| tenant_a | Kubernetes usa gang scheduling... | 0.2589 |
| tenant_a | Kueue trata todo o Job como unidade... | 0.3749 |
| tenant_b | O cliente reclamou do prazo de entrega... | 0.4565 |

O tenant_b recebeu seu único documento, mesmo irrelevante, e **não** recebeu os documentos de Kubernetes do tenant_a, que eram muito mais relevantes.

### Aprendizados
- `tenant_id` não é chave primária: ele agrupa documentos de um mesmo dono. A chave primária é `id`
- Relevância e isolamento são garantias diferentes, e as duas precisam funcionar juntas
- Queries parametrizadas (`%s`) protegem contra SQL injection

---

## Day 3: RAG completo

**Fase:** 1 (Núcleo) · **Competência:** redução de alucinação por arquitetura  
**Retorno:** prática (fluxo completo de RAG), produto (redução de alucinação por arquitetura) e visibilidade (post antes e depois)

### Objetivo
Passar os documentos encontrados para o LLM e gerar uma resposta final.

### O que foi feito
- `build_prompt`: monta o prompt com os documentos e a instrução de responder apenas com base neles
- `generate_answer`: chama o LLM
- `rag_query`: junta busca, prompt e geração

### Resultados

| Pergunta (tenant_a) | Resposta |
|---|---|
| "Como o Kubernetes agenda pods de treino distribuído?" | "O Kubernetes agenda pods de treino distribuído usando gang scheduling." |
| "O que é RAG?" | "Não sabe." |

### Aprendizados
- A mesma pergunta que gerou a ONG inventada no Day 1 recebeu "Não sabe.", porque a base do tenant não tinha nada sobre RAG
- A primeira resposta correta, sozinha, não prova nada: o modelo poderia já saber sobre gang scheduling. O teste que importa é a pergunta **sem** resposta na base
- "Não sabe." repete a instrução do prompt ao pé da letra. Funciona, mas precisa de uma mensagem melhor para o usuário final
- Um teste não é garantia: modelos pequenos variam entre execuções

---

## Day 4: Limite de relevância

**Fase:** 1 (Núcleo) · **Competência:** custo e confiabilidade  
**Retorno:** os quatro. Prática (calibração a partir de medições), produto (regra determinística antes do LLM, com menos custo e sem alucinação nos casos sem resposta), empregabilidade (relatório de resposta a incidente no repositório) e visibilidade (posts do incidente e do limite)

### Objetivo
Decidir **antes** de chamar o LLM se existe informação suficiente. Se nenhum documento for relevante o bastante, responder direto com uma mensagem padrão, sem gastar uma chamada de modelo e sem risco de alucinação.

### Abordagem
O limite de distância não pode ser chutado: a escala depende do modelo de embedding. O valor foi escolhido a partir de medições com perguntas relevantes e irrelevantes para a base.

### Incidente: credencial publicada no repositório

Antes de continuar o Day 4, uma revisão do repositório encontrou uma credencial exposta. O registro segue o formato de um relatório de incidente.

**O que aconteceu.** O primeiro commit foi enviado para um repositório **público** no GitHub contendo a senha do banco em texto, em dois arquivos:

| Arquivo | Exposição |
|---|---|
| `docker-compose.yaml` | Senha em `POSTGRES_PASSWORD` |
| `ingest.py` | Mesma senha no `DB_CONFIG` |

**Causa.** Configuração escrita diretamente no código durante a fase de testes, sem `.gitignore` nem separação de segredos antes do primeiro push.

**Impacto.** Baixo. Senha de laboratório, banco com documentos de teste, sem acesso externo à rede local. Mesmo assim, foi tratada como comprometida: credencial publicada em repositório público é considerada vazada, independente do impacto imediato.

**Fator agravante encontrado na revisão.** A porta do banco estava publicada como `5432:5432`, o que aceita conexões de qualquer máquina da rede local, e não só da própria máquina.

**Resposta, na ordem executada:**

| Passo | Ação | Por quê |
|---|---|---|
| 1 | `.gitignore` criado (`.venv/`, `.env`, `__pycache__/`, `*.pyc`) | Impedir que segredos e arquivos gerados voltem a entrar no repositório |
| 2 | Senha nova gerada com `secrets.token_urlsafe(24)` | Valor aleatório adequado para segurança, sem caracteres que exijam tratamento especial |
| 3 | Senha trocada com `ALTER USER`, com o banco em execução | Contenção: a senha publicada deixa de funcionar. Diferente do Day 2, o volume **não** foi recriado, que é o procedimento correto quando há dados |
| 4 | `.env` (local) e `.env.example` (no repositório) criados | Separar os valores reais da documentação de quais variáveis existem |
| 5 | `docker-compose.yaml` passou a ler `${POSTGRES_...}` e a porta foi restrita a `127.0.0.1` | Remover o segredo da configuração e fechar o banco para a rede |
| 6 | `ingest.py` passou a ler as credenciais com `python-dotenv` e `os.environ` | Remover o segredo do código |
| 7 | Arquivo vazio `queryes.psql` removido | Limpeza |
| 8 | Commit substituído com `git commit --amend` e enviado com `git push --force-with-lease` | Tirar a senha antiga do histórico do repositório |

**Limitação conhecida.** Reescrever o histórico não garante que a versão antiga sumiu do GitHub: o commit anterior pode continuar acessível por algum tempo para quem tiver o identificador dele. Por isso a troca de senha (passo 3) é o que de fato resolve o incidente. A reescrita do histórico só mantém o repositório limpo.

**Aprendizados**
- Segredo nunca vai para o código, nem em laboratório. O `.gitignore` e o `.env` precisam existir **antes** do primeiro commit
- A ordem da resposta importa: primeiro invalidar a credencial, depois limpar o código, por último o histórico
- `ALTER USER` troca a senha sem perder dados. Recriar o volume só é aceitável quando não há nada a preservar
- Os comandos digitados ficam salvos no histórico do terminal, inclusive senhas. No PowerShell, o arquivo fica em `(Get-PSReadLineOption).HistorySavePath`
- Na Fase 6, uma verificação automática de segredos antes de cada commit (por exemplo, com gitleaks) evita que isso se repita

### Preparação: renomeação dos tenants
Os tenants de teste foram renomeados para nomes neutros (`tenant_a` e `tenant_b`), no código e no banco ao mesmo tempo:

```sql
UPDATE documents SET tenant_id = 'tenant_a' WHERE tenant_id = 'tenant_carlos';
UPDATE documents SET tenant_id = 'tenant_b' WHERE tenant_id = 'tenant_maria';
```

**Armadilha encontrada:** com o código já usando `tenant_a` e o banco ainda com o nome antigo, a pergunta "O que é RAG?" respondia "Não sabe." do mesmo jeito. Só que por outro motivo: a busca não encontrava nenhum documento e o LLM recebia o contexto vazio. O teste passava sem provar nada. A confirmação real veio com uma pergunta que **tem** resposta na base.

### Medições
Distância de cosseno para três perguntas no `tenant_a` (quanto menor, mais parecido):

| Pergunta | Documento mais próximo | Distância | Tipo |
|---|---|---|---|
| Como o Kubernetes agenda pods de treino distribuído? | Gang scheduling | 0.2589 | Relevante |
| Como o Kubernetes agenda pods de treino distribuído? | Kueue (2º documento) | 0.3749 | Relacionado |
| O que é RAG? | Kueue | 0.4540 | Sem resposta na base |
| Qual a receita de bolo de cenoura? | Kueue | 0.4663 | Fora do assunto |

Referência do Day 2: o documento sobre atraso de entrega contra a pergunta de Kubernetes ficou em 0.4565, na mesma faixa dos irrelevantes.

**Observações**
- Existe um intervalo vazio entre 0.3749 e 0.4540: tudo que é relevante ficou abaixo, tudo que é irrelevante ficou acima
- As distâncias dos irrelevantes se concentram numa faixa estreita (0.45 a 0.52). "Bolo de cenoura" quase não fica mais longe que "O que é RAG?". O modelo separa bem relevante de irrelevante, mas não mede o quanto algo é irrelevante

### Decisão: limite de 0.42
Como num threshold de alerta, há dois erros possíveis:

| Limite | Erro | Efeito |
|---|---|---|
| Baixo demais (ex.: 0.35) | Falso negativo | Corta o documento do Kueue, que é relevante, e o sistema diz "não encontrei" com a resposta na base |
| Alto demais (ex.: 0.50) | Falso positivo | Deixa passar documentos irrelevantes e volta a depender só da instrução do prompt |

O valor escolhido foi **0.42**, perto do meio do intervalo. Em caso de dúvida, o limite erra para o lado de deixar passar, porque o prompt restrito ao contexto continua funcionando como segunda camada de proteção (defesa em profundidade).

**É um limite provisório:** foi calibrado com 3 documentos e 3 perguntas. Na Fase 8, ele será recalibrado com um conjunto de avaliação maior.

### O que foi feito
- Constantes `RELEVANCE_THRESHOLD = 0.42` e `NOT_FOUND_MESSAGE` no topo do `ingest.py`, para recalibrar mudando uma linha
- `rag_query` passou a filtrar os documentos pela distância **antes** de montar o prompt. Se nenhum passar, a função devolve a mensagem padrão e o LLM não é chamado
- Só os documentos que passaram no filtro vão para o prompt, mesmo quando a busca traz outros
- O prompt passou a instruir o modelo a responder exatamente com a `NOT_FOUND_MESSAGE` quando o contexto não bastar, em vez de inventar a própria frase (o "Não sabe." do Day 3)

### Resultados

| Pergunta | Resposta | LLM chamado? |
|---|---|---|
| Como o Kubernetes agenda pods de treino distribuído? | "Kubernetes agenda pods de treino distribuído usando gang scheduling." | Sim |
| O que é RAG? | "Não encontrei informações sobre isso na base de conhecimento." | Não |
| Qual a receita de bolo de cenoura? | "Não encontrei informações sobre isso na base de conhecimento." | Não |

### Aprendizados
- O valor de um limite sai dos dados, não de um número genérico. Ele depende do modelo de embedding: se o modelo mudar, o limite precisa ser medido de novo
- Uma regra determinística antes do LLM elimina a chance de alucinação nos casos sem resposta e economiza uma chamada de modelo
- O filtro e o prompt restrito são duas camadas independentes. Se uma falhar, a outra ainda protege
- Um teste que passa não prova nada se ele passaria também no cenário errado. Escolher a pergunta de teste é parte do teste

### Fase 1 concluída
Com o Day 4, o núcleo está provado: serving local dos modelos, busca vetorial com isolamento por tenant, geração restrita ao contexto e limite de relevância. A próxima fase transforma o script em um serviço.

---

## Day 5: Chaves de API e esqueleto da API

**Fase:** 2 (Serviço) · **Competência:** autenticação, design de API  
**Retorno:** prática (primeiro código escrito com o raciocínio de desenho explicado antes), produto (autenticação por cliente e o primeiro endpoint da API) e empregabilidade (armazenamento seguro de credenciais)

### Objetivo
Preparar a base da API: um jeito de identificar cada cliente sem confiar no que ele envia, e o primeiro endpoint rodando.

### Contrato da API
Antes de qualquer código, o contrato foi desenhado e registrado em [API.md](API.md). As principais decisões:
- O tenant vem da chave de API; o cliente nunca informa qual tenant é
- Nenhum detalhe interno (modelo, limite, distância) entra ou sai pelo contrato
- `/health` público e mínimo; `/v1/status` detalhado e protegido
- Campo `found` na resposta, para que agentes decidam o próximo passo sem interpretar texto

### O que foi feito
- `sql/002_api_keys.sql`: tabela `api_keys` com `tenant_id`, `name`, `key_hash` (único), `created_at` e `revoked_at`
- `create_api_key.py`: gera a chave com `secrets`, grava **só o hash** e mostra a chave uma única vez
- `api.py`: aplicação FastAPI com `GET /health`, que verifica banco e Ollama

### Decisões
| Decisão | Motivo |
|---|---|
| Guardar só o hash da chave | Se o banco vazar, as chaves não vazam junto |
| SHA-256, e não bcrypt | Chaves geradas pela máquina são longas e aleatórias, impossíveis de adivinhar por tentativa. O hash rápido e determinístico permite buscar a chave direto pelo índice. Hash lento é para senhas escolhidas por pessoas |
| Prefixo `rag_` nas chaves | Facilita identificar uma chave vazada, por pessoas e por ferramentas de varredura de segredos |
| Revogar com data em `revoked_at`, sem apagar | Mantém o histórico para auditoria |
| Migration numerada (`002`) | O `001` já foi aplicado; o histórico do banco fica registrado em ordem |
| `/health` como verificação de *readiness* | Checa as dependências. Na Fase 5, com Kubernetes, será separado em *liveness* e *readiness* |
| Capturar só `psycopg2.Error` e `requests.RequestException` | Um erro de código não deve ser confundido com dependência fora do ar |

### Resultados
- Chave criada para `tenant_a`. O SHA-256 recalculado a partir da chave impressa bateu com o hash guardado no banco, e a chave em si não aparece em lugar nenhum da tabela
- `GET /health` com tudo funcionando: `200 OK` e `{"status":"ok"}`
- `GET /health` com o banco parado (`docker stop rag-postgres`): `503 Service Unavailable` e `{"status":"unavailable"}`. O endpoint foi provado também no cenário de falha, e não só no caminho feliz
- Com o banco de volta (`docker start rag-postgres`), o `/health` voltou a responder `200 OK` **sem reiniciar a API**: ela se recupera sozinha quando a dependência volta, porque cada verificação abre uma conexão nova

### Aprendizados
- Hash é um caminho de mão única: quem perde a chave não recupera, e quem rouba o hash não consegue usar a API
- Antes de escrever código: objetivo em uma frase, entradas e saídas, passos em português, divisão em funções, ferramentas. Só então o código
- O cabeçalho `server: uvicorn` revela a tecnologia do servidor. Será removido no endurecimento da Fase 6

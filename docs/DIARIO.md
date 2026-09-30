# Diário do projeto

Registro de cada etapa: o que foi feito, o que foi medido, o que deu errado e o que foi aprendido. Os erros ficam registrados de propósito, porque é neles que está boa parte do aprendizado.

---

## Day 1: Serving de modelos com Ollama

**Fase:** 1 (Núcleo) · **Competência:** model serving

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

## Day 4: Limite de relevância (em andamento)

**Fase:** 1 (Núcleo) · **Competência:** custo e confiabilidade

### Objetivo
Decidir **antes** de chamar o LLM se existe informação suficiente. Se nenhum documento for relevante o bastante, responder direto com uma mensagem padrão, sem gastar uma chamada de modelo e sem risco de alucinação.

### Abordagem
O limite de distância não pode ser chutado: a escala depende do modelo de embedding. O valor será escolhido a partir de medições com perguntas relevantes e irrelevantes para a base.

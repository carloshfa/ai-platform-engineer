# Conceitos para iniciantes

Este guia explica, sem pressupor conhecimento prévio em IA, os conceitos usados no projeto.

---

## LLM (Large Language Model)

Um modelo que **gera texto**. Recebe um texto de entrada (o prompt) e produz a continuação mais provável, palavra por palavra (tecnicamente, token por token).

O ponto mais importante sobre um LLM: **ele não tem um mecanismo interno para dizer "não sei"**. Quando não tem informação, ele gera o texto mais plausível, com a mesma fluência de uma resposta verdadeira. Isso se chama **alucinação**.

Neste projeto usamos o `llama3.2:3b` (3 bilhões de parâmetros), pequeno o bastante para rodar em uma GPU doméstica.

> Exemplo real deste projeto: ao perguntar "O que é RAG?", o modelo inventou uma ONG brasileira chamada "Rede de Acolhimento e Apoio à Gente". Ao pedir para basear a resposta em dados reais, ele acrescentou ano de fundação e áreas de atuação, todos inventados. Detalhes no [Diário](DIARIO.md).

---

## Embedding

Um modelo de embedding **não gera texto**. Ele transforma um texto em uma lista de números, chamada **vetor**.

```
"Kubernetes agenda pods"  →  [-0.0229, 0.0549, -0.2035, ... ]   (768 números)
```

Esses números representam o **significado** do texto. Textos com significado parecido geram vetores parecidos, mesmo sem nenhuma palavra em comum.

Neste projeto usamos o `nomic-embed-text`, que gera vetores de 768 números.

**Por que isso é útil?** Computadores não sabem comparar o significado de duas frases diretamente. Mas sabem calcular muito rápido a distância entre duas listas de números.

---

## LLM vs embedding: resumo

| | LLM | Modelo de embedding |
|---|---|---|
| Recebe | Texto | Texto |
| Devolve | Texto novo | Números (vetor) |
| Serve para | Escrever a resposta | Encontrar documentos relevantes |
| Aparece para o usuário? | Sim | Não, trabalha nos bastidores |

---

## Busca por similaridade

Para encontrar documentos relevantes para uma pergunta:

1. A pergunta vira um vetor
2. O banco calcula a distância entre esse vetor e o vetor de cada documento
3. Os documentos com **menor distância** são os mais parecidos

Neste projeto usamos a **distância de cosseno**, com o operador `<=>` do pgvector. Quanto menor o valor, mais parecido.

Exemplo real, para a pergunta "Como o Kubernetes agenda pods de treino distribuído?":

| Documento | Distância |
|---|---|
| Kubernetes usa gang scheduling para garantir que todos os pods... | 0.2589 (muito parecido) |
| Kueue trata todo o Job como unidade de admissão... | 0.3749 (relacionado) |
| O cliente reclamou que o prazo de entrega está atrasado... | 0.4565 (não relacionado) |

---

## pgvector

Uma **extensão** do PostgreSQL que adiciona o tipo de dado `vector` e as operações de distância. Não é um banco separado: é o mesmo Postgres, com uma capacidade a mais.

Ele também oferece índices especiais para vetores, como o **HNSW**, que evitam comparar a pergunta com todos os documentos da tabela, um por um.

---

## RAG (Retrieval-Augmented Generation)

A técnica que junta as peças acima:

1. **Retrieval (recuperação):** busca os documentos mais relevantes para a pergunta
2. **Augmented (aumentada):** coloca esses documentos no prompt, como contexto
3. **Generation (geração):** o LLM escreve a resposta com base nesse contexto

A instrução enviada ao LLM é explícita: *responda apenas com base no contexto e, se a informação não estiver lá, diga que não sabe*.

> Resultado real: a mesma pergunta "O que é RAG?", que antes gerou a ONG inventada, passou a receber a resposta "Não sabe.", porque a base de conhecimento não tinha nada sobre o assunto.

RAG **reduz** alucinação, mas não elimina. Modelos pequenos podem variar entre execuções.

---

## Multi-tenant

Uma única plataforma atendendo **vários clientes** (tenants) ao mesmo tempo, cada um com seus próprios documentos, sem que um cliente jamais veja os dados de outro.

Neste projeto, todos os documentos ficam na mesma tabela, com uma coluna `tenant_id`. Toda busca filtra por essa coluna.

Duas garantias diferentes precisam funcionar juntas:

- **Relevância:** trazer os documentos mais úteis para a pergunta
- **Isolamento:** nunca trazer documentos de outro cliente, **mesmo que sejam mais relevantes**

---

## Cold start

Antes de responder, um modelo precisa ser carregado do disco para a memória da GPU. Isso leva tempo.

Medição real neste projeto (modelo de embedding):

| Situação | Tempo de carga |
|---|---|
| Modelo fora da memória (cold start) | cerca de 20,8 s |
| Modelo já carregado | cerca de 1,8 s |

O Ollama mantém o modelo na memória por 5 minutos após o último uso (parâmetro `keep_alive`). Manter o modelo carregado reduz a latência, mas ocupa memória da GPU permanentemente. É uma troca clássica de plataforma: latência versus uso de recurso.

---

## Limite de relevância

A busca vetorial **sempre** devolve os documentos mais próximos, mesmo quando nenhum deles tem a ver com a pergunta. "Mais próximo" não quer dizer "relevante".

O limite de relevância é uma regra aplicada antes de chamar o LLM: documentos com distância acima do limite são descartados. Se nenhum sobrar, o sistema responde com uma mensagem padrão, sem chamar o modelo.

Valores medidos neste projeto:

| Situação | Distância |
|---|---|
| Documentos relevantes | 0.26 a 0.37 |
| Documentos irrelevantes | 0.45 a 0.52 |
| **Limite escolhido** | **0.42** |

Esse valor só vale para o modelo de embedding usado aqui. Outro modelo gera distâncias em outra escala, e o limite precisa ser medido de novo.

---

# Python para este projeto

Esta parte cobre o mínimo de Python necessário para ler o código do projeto, sem pressupor experiência com a linguagem.

## Imports: trazer código pronto para o seu arquivo

Um `import` traz para o seu arquivo um código que outra pessoa já escreveu. Em vez de escrever do zero como fazer uma requisição HTTP ou conversar com o Postgres, você importa quem já faz isso e usa as funções prontas.

### De onde vem cada import

| Origem | Precisa instalar? | Exemplo neste projeto |
|---|---|---|
| **Biblioteca padrão** (vem com o Python) | Não | `os` |
| **Bibliotecas de terceiros** | Sim, com `pip install` | `requests`, `psycopg2`, `dotenv` |
| **Arquivos do próprio projeto** | Não, basta estar na pasta | (ainda não usamos) |

O `pip install` baixa a biblioteca e coloca dentro de `.venv/Lib/site-packages`. Por isso o ambiente virtual precisa estar **ativado** (com `(.venv)` aparecendo no terminal) na hora de instalar e de rodar o código.

### As duas formas de escrever

**Importar o módulo inteiro:**

```python
import requests

requests.post(...)   # sempre com o nome do módulo na frente
```

**Importar só uma peça de dentro dele:**

```python
from dotenv import load_dotenv

load_dotenv()        # chamada direto, sem prefixo
```

As duas fazem a mesma coisa. `import dotenv` seguido de `dotenv.load_dotenv()` também funcionaria. A segunda forma costuma ser usada quando você precisa de uma ou duas funções só.

### Nome do pacote vs nome do módulo

O nome que você instala nem sempre é o nome que você importa:

| `pip install` | `import` |
|---|---|
| `requests` | `requests` |
| `psycopg2-binary` | `psycopg2` |
| `python-dotenv` | `dotenv` |

### O topo do `ingest.py`, linha por linha

```python
import os                        # padrão: acesso ao sistema, incluindo variáveis de ambiente
import requests                  # terceiro: chamadas HTTP, usado para falar com o Ollama
import psycopg2                  # terceiro: conexão com o Postgres
from dotenv import load_dotenv   # terceiro: só a função que lê o arquivo .env
```

## Variáveis de ambiente e o arquivo `.env`

Variável de ambiente é um valor guardado no sistema, fora do código, que qualquer programa em execução consegue ler. É a forma padrão de passar configuração e segredos (como senhas) sem escrevê-los no código.

O arquivo `.env` é só um arquivo de texto com essas variáveis. O Python **não lê esse arquivo sozinho**. Quem faz isso é a função `load_dotenv()`:

```python
from dotenv import load_dotenv   # 1. traz a função para o arquivo
load_dotenv()                    # 2. lê o .env e carrega os valores no os.environ
os.environ["POSTGRES_PASSWORD"]  # 3. agora o valor está disponível
```

`os.environ` funciona como um dicionário: você pede pelo nome da variável e recebe o valor.

## Erros comuns

| Erro | Causa mais provável |
|---|---|
| `ModuleNotFoundError: No module named 'dotenv'` | Faltou o `pip install`, ou ele foi feito com o venv desativado |
| `KeyError: 'POSTGRES_PASSWORD'` | O `.env` não existe, não tem essa variável, ou o `load_dotenv()` não foi chamado antes |
| `SyntaxError` na linha do import | Erro de digitação, por exemplo `from dotenvimport load_dotenv` sem o espaço |

## Como descobrir o que uma biblioteca oferece

1. **No editor:** passe o mouse sobre o nome da função para ver a descrição e os parâmetros
2. **Na documentação:** toda biblioteca tem uma página no [pypi.org](https://pypi.org) com link para a documentação
3. **No terminal:** `python -c "import requests; help(requests.post)"`

## List comprehension: filtrar uma lista em uma linha

```python
relevant = [doc for doc in documents if doc[2] <= RELEVANCE_THRESHOLD]
```

Lendo em português: "monte uma lista com cada `doc` de `documents`, mas só os que tiverem distância menor ou igual ao limite". É o mesmo que este laço, escrito de forma mais curta:

```python
relevant = []
for doc in documents:
    if doc[2] <= RELEVANCE_THRESHOLD:
        relevant.append(doc)
```

Cada `doc` é uma tupla `(id, content, distance)`. O `[2]` pega o terceiro item, porque em Python a contagem começa em 0.

## Retorno antecipado

```python
if not relevant:
    return NOT_FOUND_MESSAGE
```

Uma lista vazia conta como "falso" em Python, então `not relevant` é verdadeiro quando nenhum documento passou no filtro. O `return` encerra a função ali mesmo, e o código abaixo dele (que chamaria o LLM) não é executado.


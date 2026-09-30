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

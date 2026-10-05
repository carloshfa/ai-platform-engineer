# API da plataforma (v1)

> **Status:** contrato definido na Fase 2. A implementação está em andamento; cada endpoint indica se já existe.

Este documento é a referência para qualquer sistema ou agente que consuma a plataforma. Ele descreve **o que entra e o que sai**. Como a plataforma funciona por dentro (modelos, banco, limites) não faz parte do contrato e pode mudar sem afetar os clientes.

---

## Autenticação

Toda chamada, exceto o `GET /health`, precisa de uma chave de API no cabeçalho:

```
Authorization: Bearer <sua-chave>
```

- Cada chave pertence a **um** cliente (tenant). A plataforma descobre o cliente pela chave; não existe parâmetro para escolher o cliente
- A chave é exibida **uma única vez**, no momento em que é criada. A plataforma guarda apenas o hash dela
- Uma chave pode ser revogada a qualquer momento, sem afetar as outras chaves do mesmo cliente

---

## Endpoints

| Método | Caminho | Autenticação | Status |
|---|---|---|---|
| `GET` | `/health` | Não | Implementado |
| `POST` | `/v1/query` | Sim | Planejado |
| `POST` | `/v1/documents` | Sim | Planejado |
| `GET` | `/v1/status` | Sim | Planejado |

### `GET /health`

Indica se a plataforma está funcionando. Pensado para balanceadores de carga e orquestradores. Não revela nenhum detalhe interno.

**Resposta `200`**
```json
{ "status": "ok" }
```

**Resposta `503`**
```json
{ "status": "unavailable" }
```

### `POST /v1/query`

Responde a uma pergunta usando **somente** os documentos do cliente dono da chave.

**Requisição**
```json
{ "question": "Qual o horário de atendimento?" }
```

**Resposta `200`, quando encontra a informação**
```json
{
  "answer": "O atendimento é de segunda a sexta, das 8h às 18h.",
  "found": true,
  "sources": [
    { "document_id": 4, "excerpt": "Nosso horário de atendimento é de segunda a sexta..." }
  ]
}
```

**Resposta `200`, quando não encontra**
```json
{
  "answer": "Não encontrei informações sobre isso na base de conhecimento.",
  "found": false,
  "sources": []
}
```

| Campo | Descrição |
|---|---|
| `answer` | Resposta em texto, pronta para exibir |
| `found` | `true` se a resposta veio de documentos do cliente; `false` se a base não tinha a informação. Agentes devem usar este campo para decidir o próximo passo, e não interpretar o texto |
| `sources` | Trechos dos documentos usados na resposta, para verificação |

### `POST /v1/documents`

Adiciona um documento à base do cliente dono da chave.

**Requisição**
```json
{ "content": "Nosso horário de atendimento é de segunda a sexta, das 8h às 18h." }
```

**Resposta `201`**
```json
{ "id": 4 }
```

### `GET /v1/status`

Estado detalhado dos componentes. Exige chave porque revela informações internas.

**Resposta `200`**
```json
{
  "database": "ok",
  "ollama": "ok",
  "models": ["llama3.2:3b", "nomic-embed-text"]
}
```

---

## Erros

| Código | Quando |
|---|---|
| `401` | Chave ausente, inválida ou revogada |
| `422` | Requisição inválida, por exemplo `question` vazia ou ausente |
| `503` | Um componente interno (banco ou modelos) está indisponível |

"Não encontrei a informação" **não** é erro: a resposta é `200` com `found: false`.

---

## Versionamento

O caminho começa com a versão (`/v1`). Mudanças incompatíveis geram uma nova versão (`/v2`), e a anterior continua funcionando por um período de transição.

---

## Fora do escopo desta versão

| Recurso | Previsto para |
|---|---|
| Listar e apagar documentos | Fase 3 |
| Upload de arquivos (PDF etc.) | Fase 3 |
| Limite de requisições e quota por cliente | Fase 6 |
| Acesso como ferramenta para agentes (MCP) | Depois da API estável |

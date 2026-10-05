# Roadmap

O projeto é dividido em 8 fases. A Fase 1 constrói o núcleo que prova que o RAG funciona. As fases seguintes transformam esse núcleo em uma **plataforma**: algo que outros times conseguem usar com segurança, que pode ser observado, escalado e que tem custo controlado.

Cada fase responde a uma pergunta que um AI Platform Engineer faz sobre qualquer sistema de IA.

O projeto tem dois objetivos, perseguidos ao mesmo tempo: **aprender AI Platform Engineering na prática** e **construir a base de um produto**. Por isso, cada fase é desenhada para servir aos dois. Veja a [Visão de produto](#visão-de-produto) no final.

### Regra de retorno

Tempo sem retorno vira conhecimento que se perde por falta de uso. Por isso, **todo Day precisa entregar pelo menos dois** destes retornos, e cada Day registra no [Diário](docs/DIARIO.md) quais entregou:

| Retorno | O que é | Evidência |
|---|---|---|
| **Empregabilidade** | Prova pública de que a habilidade existe | Algo no repositório que vale mostrar numa entrevista |
| **Visibilidade** | O trabalho chega às pessoas certas | Um post com conteúdo técnico real |
| **Produto** | Peça que serve ao futuro produto | Código ou decisão que um cliente usaria |
| **Prática** | Conhecimento exercitado, não só lido | Feito com as próprias mãos e explicável |

Se um Day planejado entrega só um retorno, ele é repensado ou cortado. A ordem das fases também pode mudar com base nisso.

| Fase | Pergunta que responde | Status |
|---|---|---|
| 1. Núcleo | Funciona? | ✅ Concluída |
| 2. Serviço | Outro time consegue usar sem entender a infraestrutura? | 🟡 Próxima |
| 3. Ingestão | Os dados entram de forma confiável e reprocessável? | ⚪ Planejada |
| 4. Observabilidade | Conseguimos ver o que está acontecendo? | ⚪ Planejada |
| 5. Kubernetes | Escala e se recupera de falhas? | ⚪ Planejada |
| 6. Segurança | Um cliente consegue ver dados de outro? Os segredos estão protegidos? | ⚪ Planejada |
| 7. Custo | Quanto custa cada cliente e como reduzir? | ⚪ Planejada |
| 8. LLMOps | Conseguimos mudar o sistema sem piorar as respostas? | ⚪ Planejada |

---

## Fase 1: Núcleo

Provar que o fluxo completo de RAG funciona, com isolamento por tenant.

- [x] Day 1: Ollama servindo LLM e modelo de embedding; experimentos de alucinação
- [x] Day 2: Postgres + pgvector, schema multi-tenant, ingestão e busca via Python
- [x] Day 3: RAG completo (busca + LLM com prompt restrito ao contexto)
- [x] Day 4: limite de relevância (não chamar o LLM quando nenhum documento é relevante) e mensagem de "não encontrei" para o usuário
- [x] Endurecimento: credenciais fora do código, `.env`, porta do banco restrita a `127.0.0.1`

## Fase 2: Serviço

**Ângulo de produto:** o contrato da API é o que clientes e agentes vão consumir. Tenant definido pela chave de API, nenhum detalhe interno exposto, fontes devolvidas na resposta.

Transformar o script em um serviço que outros sistemas consomem.

- [ ] API HTTP (FastAPI) com endpoints de ingestão e consulta
- [ ] Identificação do tenant pela autenticação, não por parâmetro livre
- [ ] Aplicação em container, todos os componentes no Docker Compose
- [ ] Health checks

## Fase 3: Ingestão

**Ângulo de produto:** cada cliente mantém os próprios documentos. Ingestão simples e confiável é o que torna a base útil sem suporte constante.

- [ ] Upload de arquivos (texto, PDF)
- [ ] Divisão de documentos longos em trechos (chunking)
- [ ] Registro de qual modelo de embedding gerou cada vetor
- [ ] Reprocessamento quando o modelo de embedding mudar

## Fase 4: Observabilidade

**Ângulo de produto:** métricas por tenant viram base para SLA, suporte e cobrança.

- [ ] Latência por etapa: embedding, busca, geração
- [ ] Contagem de tokens por requisição
- [ ] Logs estruturados com tenant e identificador de requisição
- [ ] Prometheus e Grafana

## Fase 5: Kubernetes

**Ângulo de produto:** atender mais clientes sem aumentar o trabalho operacional na mesma proporção.

- [ ] Deploy em cluster local
- [ ] Limites de recurso (CPU, memória)
- [ ] Autoscaling da API
- [ ] Estratégia para o serving dos modelos (GPU)

## Fase 6: Segurança e governança

**Ângulo de produto:** isolamento comprovado e conformidade com a LGPD são argumentos de venda, principalmente para empresas que não querem os dados saindo de casa.

- [ ] Row Level Security no Postgres: isolamento garantido pelo banco
- [ ] Usuário de aplicação com privilégio mínimo
- [ ] Secrets em um gerenciador de segredos (o `.env` resolve só o laboratório)
- [ ] Verificação automática de segredos a cada commit (ex.: gitleaks)
- [ ] Quota e rate limit por tenant
- [ ] Testes de prompt injection via conteúdo de documentos

## Fase 7: Custo e performance

**Ângulo de produto:** saber quanto custa cada cliente é o que permite precificar sem prejuízo.

- [ ] Cache de embeddings e de respostas
- [ ] Roteamento entre modelos por tipo de pergunta
- [ ] Custo estimado por tenant (chargeback)

## Fase 8: LLMOps

**Ângulo de produto:** mudar modelo ou prompt sem piorar a resposta de nenhum cliente.

- [ ] Conjunto de perguntas de avaliação com respostas esperadas, incluindo casos de "não sei"
- [ ] Recalibrar o limite de relevância (hoje 0.42, medido com 3 documentos) com o conjunto de avaliação
- [ ] Avaliação automática no pipeline de CI
- [ ] Versionamento de prompts

---

## Visão de produto

**A ideia:** uma camada de conhecimento privada para empresas pequenas e médias. Cada empresa mantém os próprios documentos, isolados das demais, e sistemas e agentes de IA consultam essa base por API.

**Por que não é só "conversar com documentos":** isso já é oferecido por ferramentas prontas, várias gratuitas. O diferencial buscado está em:

- **Fonte de verdade para agentes.** Na era agêntica, agentes de atendimento, vendas e suporte precisam consultar informação confiável da empresa. A plataforma será exposta também como servidor MCP, o protocolo que os agentes usam para descobrir e chamar ferramentas
- **Integração com o que a empresa já usa**, via API: ERP, PDV, WhatsApp e sistemas internos
- **Isolamento, segurança e custo por cliente**, a parte que costuma ser ignorada em projetos de agentes

**Decisões em aberto, a validar com potenciais clientes:**

| Modelo de implantação | A favor | Contra |
|---|---|---|
| Tudo no cliente (local) | Dados nunca saem da empresa | Exige hardware; modelos pequenos respondem de forma limitada |
| Tudo na nuvem da plataforma | Melhor qualidade, sem hardware no cliente | Os dados saem da empresa |
| Híbrido | Documentos e busca ficam no cliente; só o trecho necessário vai ao modelo | Mais complexo de operar |

**Critério para cada decisão técnica:** além de "funciona?", toda decisão responde também "isso funciona para um cliente que não sou eu, e para um agente que consome a API?".


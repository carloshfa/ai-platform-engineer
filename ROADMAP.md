# Roadmap

O projeto é dividido em 8 fases. A Fase 1 constrói o núcleo que prova que o RAG funciona. As fases seguintes transformam esse núcleo em uma **plataforma**: algo que outros times conseguem usar com segurança, que pode ser observado, escalado e que tem custo controlado.

Cada fase responde a uma pergunta que um AI Platform Engineer faz sobre qualquer sistema de IA.

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

Transformar o script em um serviço que outros sistemas consomem.

- [ ] API HTTP (FastAPI) com endpoints de ingestão e consulta
- [ ] Identificação do tenant pela autenticação, não por parâmetro livre
- [ ] Aplicação em container, todos os componentes no Docker Compose
- [ ] Health checks

## Fase 3: Ingestão

- [ ] Upload de arquivos (texto, PDF)
- [ ] Divisão de documentos longos em trechos (chunking)
- [ ] Registro de qual modelo de embedding gerou cada vetor
- [ ] Reprocessamento quando o modelo de embedding mudar

## Fase 4: Observabilidade

- [ ] Latência por etapa: embedding, busca, geração
- [ ] Contagem de tokens por requisição
- [ ] Logs estruturados com tenant e identificador de requisição
- [ ] Prometheus e Grafana

## Fase 5: Kubernetes

- [ ] Deploy em cluster local
- [ ] Limites de recurso (CPU, memória)
- [ ] Autoscaling da API
- [ ] Estratégia para o serving dos modelos (GPU)

## Fase 6: Segurança e governança

- [ ] Row Level Security no Postgres: isolamento garantido pelo banco
- [ ] Usuário de aplicação com privilégio mínimo
- [ ] Secrets em um gerenciador de segredos (o `.env` resolve só o laboratório)
- [ ] Verificação automática de segredos a cada commit (ex.: gitleaks)
- [ ] Quota e rate limit por tenant
- [ ] Testes de prompt injection via conteúdo de documentos

## Fase 7: Custo e performance

- [ ] Cache de embeddings e de respostas
- [ ] Roteamento entre modelos por tipo de pergunta
- [ ] Custo estimado por tenant (chargeback)

## Fase 8: LLMOps

- [ ] Conjunto de perguntas de avaliação com respostas esperadas, incluindo casos de "não sei"
- [ ] Recalibrar o limite de relevância (hoje 0.42, medido com 3 documentos) com o conjunto de avaliação
- [ ] Avaliação automática no pipeline de CI
- [ ] Versionamento de prompts

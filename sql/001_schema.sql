-- Estrutura inicial do banco da plataforma RAG multi-tenant.
-- Pode ser executado mais de uma vez sem erro (IF NOT EXISTS).

-- Habilita o tipo de dado "vector" e as operações de distância.
CREATE EXTENSION IF NOT EXISTS vector;

-- Um documento pertence sempre a um tenant (tenant_id NOT NULL).
-- VECTOR(768) precisa bater com a dimensão do modelo de embedding (nomic-embed-text).
CREATE TABLE IF NOT EXISTS documents (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   TEXT        NOT NULL,
    content     TEXT        NOT NULL,
    embedding   VECTOR(768),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Busca aproximada por similaridade, usando distância de cosseno.
CREATE INDEX IF NOT EXISTS documents_embedding_hnsw_idx
    ON documents USING hnsw (embedding vector_cosine_ops);

-- Toda consulta filtra por tenant: este índice evita varrer a tabela inteira.
CREATE INDEX IF NOT EXISTS documents_tenant_id_idx
    ON documents (tenant_id);

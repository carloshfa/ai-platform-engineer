-- Chaves de API: cada chave pertence a um tenant.
-- A chave em si nunca é guardada, apenas o hash dela.

CREATE TABLE IF NOT EXISTS api_keys (
    id          BIGSERIAL   PRIMARY KEY,
    tenant_id   TEXT        NOT NULL,
    name        TEXT        NOT NULL,
    key_hash    TEXT        NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at  TIMESTAMPTZ
);
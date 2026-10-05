import argparse
import hashlib
import secrets

import psycopg2

from ingest import DB_CONFIG


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def create_api_key(tenant_id: str, name: str) -> str:
    key = "rag_" + secrets.token_urlsafe(32)

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO api_keys (tenant_id, name, key_hash) VALUES (%s, %s, %s)",
        (tenant_id, name, hash_key(key)),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return key


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cria uma chave de API para um tenant.")
    parser.add_argument("tenant_id", help="Tenant dono da chave, por exemplo tenant_a")
    parser.add_argument("name", help="Rótulo da chave, por exemplo 'teste local'")
    args = parser.parse_args()

    key = create_api_key(args.tenant_id, args.name)
    print("Chave criada. Guarde agora: ela não será exibida de novo.")
    print(key)
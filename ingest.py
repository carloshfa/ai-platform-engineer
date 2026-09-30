import os
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = "http://localhost:11434/api/embed"
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3.2:3b"
LLM_URL = "http://localhost:11434/api/generate"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": os.environ["POSTGRES_DB"],
    "user": os.environ["POSTGRES_USER"],
    "password": os.environ["POSTGRES_PASSWORD"],
}

def generate_embedding(text: str) -> list[float]:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": EMBEDDING_MODEL,
            "input": text
        }
    )
    response.raise_for_status()
    data = response.json()
    return data["embeddings"][0]

def insert_document(tenant_id: str, content: str, embedding: list[float]) -> None:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO documents (tenant_id, content, embedding)
        VALUES (%s, %s, %s)
        """,
        (tenant_id, content, embedding)
    )

    conn.commit()
    cursor.close()
    conn.close()

def search_similar(tenant_id: str, query_text: str, limit: int = 3):
    query_embedding = generate_embedding(query_text)

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, content, embedding <=> %s::vector AS distance
        FROM documents
        WHERE tenant_id = %s
        ORDER BY distance
        LIMIT %s
        """,
        (query_embedding, tenant_id, limit)
    )

    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

def build_prompt(question: str, documents: list[tuple]) -> str:
    context = "\n\n".join([f"- {content}" for _, content, _ in documents])

    prompt = f"""Responda à pergunta usando APENAS as informações do contexto abaixo.
Se o contexto não contiver informação suficiente para responder, diga claramente que não sabe.
Não invente informações que não estejam no contexto.

Contexto:
{context}

Pergunta: {question}

Resposta:"""

    return prompt

def generate_answer(prompt: str) -> str:
    response = requests.post(
        LLM_URL,
        json={
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False
        }
    )
    response.raise_for_status()
    data = response.json()
    return data["response"]

def rag_query(tenant_id: str, question: str) -> str:
    documents = search_similar(tenant_id, question)
    prompt = build_prompt(question, documents)
    answer = generate_answer(prompt)
    return answer

if __name__ == "__main__":
    resposta = rag_query("tenant_a", "O que é RAG?")
    print(resposta)
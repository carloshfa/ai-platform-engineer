import psycopg2
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from ingest import DB_CONFIG

OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

app = FastAPI(title="Plataforma RAG Multi-Tenant", version="0.1.0")

def check_database() -> bool:
    try:
        conn = psycopg2.connect(**DB_CONFIG, connect_timeout=3)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return True
    except psycopg2.Error:
        return False
    
def check_ollama() -> bool:
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=3)
        return response.status_code == 200
    except requests.RequestException:
        return False

@app.get("/health")
def health():
    if check_database() and check_ollama():
        return {"status": "ok"}
    return JSONResponse(status_code=503, content={"status": "unavailable"})    
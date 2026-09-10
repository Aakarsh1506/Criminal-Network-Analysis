import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    jwt_secret: str
    jwt_expires_in: str = "12h"
    cookie_name: str = "cna_token"
    production: bool = False
    frontend_origin: str = "http://localhost:3000"
    port: int = 5050
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_user: str = "postgres"
    pg_password: str = ""
    pg_database: str = "criminal_network"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    admin_username: str = ""
    admin_password: str = ""
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_extraction_model: str = "openai/gpt-oss-20b"
    groq_debug_responses: bool = False
    extraction_provider: str = "groq"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    ollama_timeout: float = 180
    extraction_mode: str = "hybrid"
    spacy_model: str = "en_core_web_sm"
    ocr_language: str = "eng"
    upload_dir: Path = BASE_DIR / "uploads"

    @classmethod
    def from_env(cls):
        # Environment variables override the backend's local .env file.
        env = {**dotenv_values(BASE_DIR / ".env"), **os.environ}
        secret = env.get("JWT_SECRET")
        if not secret:
            raise RuntimeError("JWT_SECRET is not set — add it to backend/.env")
        return cls(
            jwt_secret=secret,
            jwt_expires_in=env.get("JWT_EXPIRES_IN") or "12h",
            cookie_name=env.get("COOKIE_NAME") or "cna_token",
            production=env.get("NODE_ENV") == "production",
            frontend_origin=env.get("FRONTEND_ORIGIN") or "http://localhost:3000",
            port=int(env.get("PORT") or 5050),
            pg_host=env.get("PGHOST") or "localhost",
            pg_port=int(env.get("PGPORT") or 5432),
            pg_user=env.get("PGUSER") or "postgres",
            pg_password=env.get("PGPASSWORD") or "",
            pg_database=env.get("PGDATABASE") or "criminal_network",
            neo4j_uri=env.get("NEO4J_URI") or "bolt://localhost:7687",
            neo4j_user=env.get("NEO4J_USER") or "neo4j",
            neo4j_password=env.get("NEO4J_PASSWORD") or "",
            admin_username=env.get("ADMIN_USERNAME") or "",
            admin_password=env.get("ADMIN_PASSWORD") or "",
            groq_api_key=env.get("GROQ_API_KEY") or "",
            groq_model=env.get("GROQ_MODEL") or "openai/gpt-oss-20b",
            groq_extraction_model=env.get("GROQ_EXTRACTION_MODEL") or "openai/gpt-oss-20b",
            groq_debug_responses=(env.get("GROQ_DEBUG_RESPONSES") or "").lower()
            in ("1", "true", "yes"),
            extraction_mode=env.get("EXTRACTION_MODE") or "hybrid",
            extraction_provider=(env.get("EXTRACTION_PROVIDER") or "groq").strip().lower(),
            ollama_base_url=(env.get("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/"),
            ollama_model=env.get("OLLAMA_MODEL") or "qwen3:4b",
            ollama_timeout=float(env.get("OLLAMA_TIMEOUT") or 180),
            spacy_model=env.get("SPACY_MODEL") or "en_core_web_sm",
            ocr_language=env.get("OCR_LANGUAGE") or "eng",
        )

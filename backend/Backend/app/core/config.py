from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

# Chargement explicite du fichier Backend/.env
load_dotenv(
    dotenv_path=ENV_FILE,
    override=False,
    encoding="utf-8",
)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================
    # APPLICATION
    # ==========================================

    APP_NAME: str = "Plateforme Intelligente de Maintenance ONEE"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ==========================================
    # BASE DE DONNÉES
    # ==========================================

    DATABASE_URL: str

    # ==========================================
    # SÉCURITÉ
    # ==========================================

    SECRET_KEY: str = "CHANGE_ME"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # ==========================================
    # ADMINISTRATEUR INITIAL
    # ==========================================

    FIRST_ADMIN_EMAIL: str = "admin@onee.ma"
    FIRST_ADMIN_PASSWORD: str = "123!"
    FIRST_ADMIN_FIRST_NAME: str = "Admin"
    FIRST_ADMIN_LAST_NAME: str = "ONEE"

    # ==========================================
    # CORS
    # ==========================================

    CORS_ORIGINS: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    )

    # ==========================================
    # QDRANT
    # ==========================================

    QDRANT_URL: str = "http://127.0.0.1:6333"
    QDRANT_COLLECTION: str = "maintenance_onee_rag"

    # ==========================================
    # RAG
    # ==========================================

    RAG_EMBEDDING_MODEL: str = (
        "sentence-transformers/"
        "paraphrase-multilingual-MiniLM-L12-v2"
    )

    RAG_TOP_K: int = 8
    RAG_BATCH_SIZE: int = 64
    RAG_MIN_SCORE: float = 0.30
    RAG_MAX_CONTEXT_CHARS: int = 16000

    # ==========================================
    # OPENROUTER
    # ==========================================

    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openrouter/free"

    OPENROUTER_TIMEOUT_SECONDS: int = 90
    OPENROUTER_MAX_TOKENS: int = 1200

    OPENROUTER_SITE_URL: str = "http://localhost:3000"
    OPENROUTER_APP_NAME: str = "MaintIA ONEE"
    OPENROUTER_ZDR: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
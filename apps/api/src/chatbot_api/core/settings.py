from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["local", "staging", "production"] = "local"
    log_level: str = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # Base pública del sitio (dominio propio con HTTPS). Se usa para construir los
    # links a los PDFs que el agente comparte en sus respuestas, p. ej.
    # https://remiai.tech/docs/12/malla-si.pdf  →  endpoint proxy al S3 privado.
    # Vacío = no se adjuntan links (fallback a citar solo el título). Sin "/" final.
    public_base_url: str = ""

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    cognito_region: str = "us-east-1"

    # Admin del CRM a sembrar en la tabla `admins` (bootstrap_admin, corrido por
    # el servicio `migrate` en prod). Debe coincidir con el email del usuario de
    # Cognito. Vacío = no se siembra (en local se usa el stub X-Dev-User).
    admin_email: str = ""
    admin_name: str = ""

    firebase_project_id: str = ""
    firebase_client_email: str = ""
    firebase_private_key: str = ""
    firebase_private_key_id: str = ""

    meta_verify_token: str = ""
    meta_app_secret: str = ""
    meta_phone_number_id: str = ""
    meta_waba_id: str = ""
    meta_access_token: str = ""
    meta_graph_api_version: str = "v21.0"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_vision_model: str = "gpt-4o-mini"

    local_uploads_dir: Path = Path("./uploads")

    aws_region: str = "us-east-1"
    aws_s3_bucket: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 200
    rag_top_k: int = 5
    rag_fetch_k: int = 20
    rag_ocr_enabled: bool = True
    rag_ocr_threshold: int = 50
    rag_ocr_dpi: int = 200

    # Piso de relevancia del RAG: similitud coseno mínima (1 - distancia) para
    # que un chunk cuente como resultado. SUAVE a propósito: con el modelo de
    # embeddings actual los scores se agrupan ~0.49-0.58, así que un umbral alto
    # bloquea consultas legítimas (p. ej. "carreras" 0.555). 0.40 solo filtra
    # basura claramente fuera de tema; la decisión fina de derivar la toma el
    # LLM (prompt) + el backstop de recursión. Subir solo si hay falsos positivos.
    rag_min_score: float = 0.40

    history_cache_enabled: bool = True
    history_cache_ttl_seconds: int = 86400
    history_cache_max_messages: int = 20

    # Debounce de respuesta del bot: agrupa mensajes rápidos del estudiante en un
    # único turno. La ventana se reinicia con cada mensaje nuevo; Remi responde
    # una sola vez al lote consolidado. Off → respuesta inmediata por mensaje.
    reply_debounce_enabled: bool = True
    reply_debounce_seconds: int = 6

    intent_sbert_threshold: float = 0.55

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "chatbot-upc"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

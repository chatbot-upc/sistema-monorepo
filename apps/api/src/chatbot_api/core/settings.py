from functools import lru_cache
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

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    cognito_region: str = "us-east-1"

    meta_verify_token: str = ""
    meta_app_secret: str = ""
    meta_phone_number_id: str = ""
    meta_access_token: str = ""
    meta_graph_api_version: str = "v21.0"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

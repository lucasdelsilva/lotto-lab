"""Configuracao da aplicacao, carregada de variaveis de ambiente."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    app_name: str = "Lotto Lab API"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://lotto:lotto@localhost:5432/lottolab"
    db_echo: bool = False

    # Guardado como texto de proposito: o pydantic-settings tenta decodificar campos de
    # tipo complexo como JSON direto da variavel de ambiente, e uma lista separada por
    # virgula quebraria antes de qualquer validator rodar.
    cors_origins_raw: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_timeout_seconds: float = 30.0
    openai_max_retries: int = 2
    openai_temperature: float = 0.2

    generator_max_attempts: int = 20_000
    generator_pool_factor: int = 5

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]

    @property
    def ai_enabled(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

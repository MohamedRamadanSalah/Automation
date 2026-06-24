from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = Field(..., description="asyncpg DSN")

    # OpenRouter
    openrouter_api_key: str = Field(..., description="sk-or-... key")
    openrouter_default_model: str = Field("anthropic/claude-3-haiku", description="Shared LLM model id")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # API auth (optional — empty string disables check)
    api_key: str = ""

    # Agent behaviour
    agent_concurrency: int = Field(3, ge=1)
    agent_max_retries: int = Field(3, ge=0)
    review_max_attempts: int = Field(3, ge=1)
    review_pass_threshold: int = Field(7, ge=0, le=100)

    # Discovery thresholds
    popularity_threshold: int = Field(10, ge=0)
    top_n: int = Field(15, ge=1)

    # Storage
    storage_root: str = "storage"

    # Logging
    log_level: str = "INFO"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

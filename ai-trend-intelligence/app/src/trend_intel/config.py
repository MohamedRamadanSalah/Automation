from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = Field(..., description="asyncpg DSN")

    # OpenRouter
    openrouter_api_key: str = Field(..., description="sk-or-... key")
    openrouter_default_model: str = Field(
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        description="Primary LLM model id (strongest verified free model)",
    )
    # Comma-separated ordered list of free fallback models. OpenRouter routes to the
    # next one automatically when the primary is rate-limited (429) or errors.
    openrouter_fallback_models: str = Field(
        "nvidia/nemotron-3-super-120b-a12b:free,"
        "openai/gpt-oss-120b:free,"
        "meta-llama/llama-3.3-70b-instruct:free,"
        "qwen/qwen3-next-80b-a3b-instruct:free,"
        "nousresearch/hermes-3-llama-3.1-405b:free",
        description="Ordered comma-separated free fallback model ids",
    )
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    @property
    def fallback_model_list(self) -> list[str]:
        return [m.strip() for m in self.openrouter_fallback_models.split(",") if m.strip()]

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

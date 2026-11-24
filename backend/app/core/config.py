from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql+psycopg://patchdiff:patchdiff_secret@localhost:5432/patchdiff_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Universal OpenAI-Compatible LLM Settings (Default: Groq)
    LLM_PROVIDER: str = "groq"  # "groq", "openai", "deepseek", "offline"
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "openai/gpt-oss-20b"
    LLM_TIMEOUT_SECONDS: float = 5.0

    # Riot Data Dragon & Automatic Patch Sync
    DDRAGON_VERSION: str = "14.22.1"
    DDRAGON_LANG: str = "tr_TR"
    AUTO_SYNC_ENABLED: bool = True
    AUTO_SYNC_INTERVAL_MINUTES: int = 360

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
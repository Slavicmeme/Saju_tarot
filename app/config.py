from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    app_name: str = "Magic Tarot"
    app_env: str = "development"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    agent_llm_model: str = "gpt-4.1-mini"
    llm_timeout: float = 120
    llm_max_completion_tokens: int = 8000
    result_ttl_hours: int = 24
    expose_llm_status: bool = True
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()

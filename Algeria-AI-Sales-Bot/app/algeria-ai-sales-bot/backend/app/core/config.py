import os
from dataclasses import dataclass

def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())

@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("ENVIRONMENT", "development")
    app_name: str = "Algeria AI Sales Bot"
    allowed_origins: tuple[str, ...] = _csv(os.getenv("ALLOWED_ORIGINS", "http://localhost:5173"))
    operator_tokens: tuple[str, ...] = _csv(os.getenv("OPERATOR_TOKENS", ""))
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-5-mini")
    enable_external_delivery: bool = os.getenv("ENABLE_EXTERNAL_DELIVERY", "false").lower() == "true"

settings = Settings()

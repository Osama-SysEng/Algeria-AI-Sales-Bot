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
    # Safety controls declared in .env.example (staging defaults; delivery stays off).
    require_human_approval: bool = os.getenv("REQUIRE_HUMAN_APPROVAL", "true").lower() == "true"
    outbound_delivery_mode: str = os.getenv("OUTBOUND_DELIVERY_MODE", "dry_run")
    outbox_encryption_key: str = os.getenv("OUTBOX_ENCRYPTION_KEY", "")
    # Reserved Telegram connector group (no connector implemented in this version).
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_webhook_url: str = os.getenv("TELEGRAM_WEBHOOK_URL", "")
    telegram_webhook_secret: str = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    telegram_allowed_updates: tuple[str, ...] = _csv(os.getenv("TELEGRAM_ALLOWED_UPDATES", "message"))
    telegram_test_chat_ids: tuple[str, ...] = _csv(os.getenv("TELEGRAM_TEST_CHAT_IDS", ""))
    # Reserved CRM adapter group (no adapter implemented in this version).
    crm_provider: str = os.getenv("CRM_PROVIDER", "")
    crm_base_url: str = os.getenv("CRM_BASE_URL", "")
    crm_client_id: str = os.getenv("CRM_CLIENT_ID", "")
    crm_client_secret: str = os.getenv("CRM_CLIENT_SECRET", "")
    crm_refresh_token: str = os.getenv("CRM_REFRESH_TOKEN", "")
    crm_pipeline_id: str = os.getenv("CRM_PIPELINE_ID", "")

    @property
    def telegram_configured(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_webhook_secret)

    @property
    def crm_configured(self) -> bool:
        return bool(self.crm_base_url and self.crm_client_id and self.crm_client_secret)

settings = Settings()

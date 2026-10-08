from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND = Path(__file__).resolve().parents[2]
REPO = BACKEND.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND / ".env", extra="ignore")

    database_url: str = f"sqlite:///{BACKEND / 'var' / 'cc_smith.db'}"
    serpapi_api_key: str | None = None
    anthropic_api_key: str | None = None
    # replay: never call SerpApi or Anthropic; serve recorded fixtures only.
    mode: str = "replay"
    serp_hourly_limit: int = 45
    serp_monthly_budget: int = 250
    extract_model: str = "claude-sonnet-5-5"
    triage_model: str = "claude-haiku-4-5-20251001"
    allowlist_path: Path = REPO / "docs" / "research" / "official-domains.yaml"
    fixtures_dir: Path = BACKEND / "fixtures"
    alerts_log: Path = BACKEND / "var" / "owner-alerts.log"


settings = Settings()

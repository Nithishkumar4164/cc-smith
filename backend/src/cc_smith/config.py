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
    # Checkout card choice (D10): a quick model picks among engine-computed options.
    advisor_enabled: bool = True
    advisor_model: str = "claude-haiku-4-5-20251001"
    advisor_timeout_s: float = 2.5
    # Background jobs (Launch Radar weekly, card refresh nightly) start with the API server
    # only when this is on (SCHEDULER_ENABLED=true); otherwise run them with the CLI.
    scheduler_enabled: bool = False
    allowlist_path: Path = REPO / "docs" / "research" / "official-domains.yaml"
    fixtures_dir: Path = BACKEND / "fixtures"
    alerts_log: Path = BACKEND / "var" / "owner-alerts.log"
    # capture: Gmail OAuth (installed-app client JSON from Google Cloud console) and the
    # Fernet key that encrypts stored Gmail tokens (CAPTURE_TOKEN_KEY; generate with
    # `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
    google_oauth_client_path: Path = REPO / "private_samples" / "google_oauth_client.json"
    google_oauth_redirect_uri: str | None = None  # default: the client JSON's first redirect URI
    capture_token_key: str | None = None
    gmail_initial_days: int = 90
    capture_max_upload_bytes: int = 15_000_000


settings = Settings()

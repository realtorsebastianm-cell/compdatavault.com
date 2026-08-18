from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://dealarchive:dealarchive@localhost:5432/dealarchive"
    anthropic_api_key: str | None = None

    # Auth
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 30

    # Storage for raw flyer files
    storage_dir: str = "./storage"

    # Inbound email ingestion. SendGrid Inbound Parse is configured per
    # custom domain (via an MX record), so every address on that domain --
    # <forwarding_slug>@INBOUND_EMAIL_DOMAIN -- routes to /ingest/email.
    inbound_email_domain: str = "deals.dealarchive.app"
    inbound_webhook_secret: str | None = None

    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

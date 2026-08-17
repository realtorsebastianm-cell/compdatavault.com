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

    # Inbound email ingestion. Shared inbox provider (e.g. SendGrid Inbound
    # Parse / Postmark) posts to /ingest/email with this shared secret so we
    # can trust the sender field it reports.
    inbound_email_domain: str = "deals.dealarchive.app"
    inbound_webhook_secret: str | None = None

    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

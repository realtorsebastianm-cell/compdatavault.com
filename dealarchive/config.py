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

    # Inbound email ingestion (Postmark inbound webhook -> /ingest/email).
    # Postmark's default inbound address is one shared address per account
    # (e.g. "5ed2f034e21b10846839e79ad6e59775@inbound.postmarkapp.com"), not
    # one per user, so per-broker routing rides on Postmark's "+" mailbox
    # hash: a broker's real forwarding address is
    # "<local>+<forwarding_slug>@<domain>", and Postmark parses the part
    # after "+" into ToFull[0].MailboxHash on the webhook payload.
    inbound_base_address: str | None = None  # e.g. "5ed2f034e21b10846839e79ad6e59775@inbound.postmarkapp.com"
    inbound_webhook_secret: str | None = None

    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

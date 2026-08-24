from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://dealarchive:dealarchive@localhost:5432/dealarchive"
    anthropic_api_key: str | None = None

    # Auth
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 30

    # Storage for raw flyer files -- Cloudflare R2 (S3-compatible). Create a
    # bucket and an R2 API token in the Cloudflare dashboard (R2 -> Manage
    # API tokens -> Create API token, "Object Read & Write" permission
    # scoped to the bucket), then set these on Render.
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket_name: str = "compdatavault-flyers"

    # Inbound email ingestion (Cloudflare Email Routing exact-match rule on
    # this one address -> a Cloudflare Worker -> POSTs multipart/form-data
    # to /ingest/email). Every broker forwards flyers to this same shared
    # address; /ingest/email figures out whose vault a flyer belongs to by
    # matching the envelope From address against User.email -- not by any
    # per-user routing trick. Shown as-is to every user on /me.
    inbound_base_address: str | None = None  # e.g. "deals@compdatavault.com"
    # Shared secret the Worker sends as X-Ingest-Secret; set the identical
    # value with `wrangler secret put INGEST_SHARED_SECRET` on the Worker.
    inbound_webhook_secret: str | None = None

    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Render's env var editor (and copy/paste in general) makes it easy to
    # pick up an invisible leading/trailing space or newline along with the
    # value you meant to paste -- botocore then rejects the resulting R2
    # endpoint URL as "invalid" with no indication that whitespace is the
    # culprit. Strip every string setting so a stray space can't cause a
    # silent, hard-to-diagnose failure like that again.
    @field_validator(
        "database_url",
        "anthropic_api_key",
        "jwt_secret",
        "jwt_algorithm",
        "r2_account_id",
        "r2_access_key_id",
        "r2_secret_access_key",
        "r2_bucket_name",
        "inbound_base_address",
        "inbound_webhook_secret",
        "frontend_url",
        mode="before",
    )
    @classmethod
    def _strip_whitespace(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


settings = Settings()

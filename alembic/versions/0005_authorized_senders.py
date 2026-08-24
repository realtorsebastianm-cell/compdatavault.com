"""authorized_senders -- multiple inboxes forwarding into one account

A broker who receives flyers on two different email addresses could only
have one of them route into their vault, since /ingest/email matched the
envelope From address against a single User.email. This adds an
authorized_senders table: a broker can register a second inbox from
Settings, verify it by sending one email from that inbox to the shared
inbound address with a one-time code in the subject (reusing the ingest
pipeline that already exists -- no new outbound-email infrastructure
needed), and flyers forwarded from it after that route into their vault
same as their primary address.

email has a case-insensitive unique index, not just per-user uniqueness:
without that, one broker could register another broker's real inbox as an
"authorized sender" on their own account and hijack flyers forwarded from
it. verification_code is where the one-time code lives while the row is
unverified (verified_at IS NULL); ingestion checks that code against a
verification email's subject line.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authorized_senders",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("verification_code", sa.String(), nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_authorized_senders_user_id", "authorized_senders", ["user_id"]
    )
    op.create_index(
        "ix_authorized_senders_email", "authorized_senders", ["email"]
    )
    op.create_index(
        "ix_authorized_senders_email_lower_unique",
        "authorized_senders",
        [sa.text("lower(email)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_authorized_senders_email_lower_unique", table_name="authorized_senders")
    op.drop_index("ix_authorized_senders_email", table_name="authorized_senders")
    op.drop_index("ix_authorized_senders_user_id", table_name="authorized_senders")
    op.drop_table("authorized_senders")

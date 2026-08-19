"""drop users.forwarding_slug

Inbound routing no longer uses per-broker forwarding addresses -- every
broker forwards to one shared address (settings.inbound_base_address) and
/ingest/email matches the sender's From address against User.email instead.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_users_forwarding_slug", table_name="users")
    op.drop_column("users", "forwarding_slug")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("forwarding_slug", sa.String(), nullable=True),
    )
    op.execute("UPDATE users SET forwarding_slug = md5(random()::text || id) WHERE forwarding_slug IS NULL")
    op.alter_column("users", "forwarding_slug", nullable=False)
    op.create_unique_constraint("uq_users_forwarding_slug", "users", ["forwarding_slug"])
    op.create_index("ix_users_forwarding_slug", "users", ["forwarding_slug"])

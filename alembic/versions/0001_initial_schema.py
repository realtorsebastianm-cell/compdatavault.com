"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# create_type=False is only honored by the dialect-specific postgresql.ENUM
# -- the generic sa.Enum silently drops it (it has no such attribute), which
# is why a first pass at this migration using sa.Enum kept re-issuing
# CREATE TYPE from op.create_table's DDL events even after being told not
# to. Types are created explicitly by _create_enum_idempotent below via a
# raw DO block rather than Enum.create(checkfirst=True), since checkfirst's
# existence check was unreliable against Neon within a single migration run.
deal_type = PG_ENUM("sale", "lease", name="dealtype", create_type=False)
property_type = PG_ENUM(
    "office",
    "industrial",
    "retail",
    "land",
    "multifamily",
    "other",
    name="propertytype",
    create_type=False,
)
rate_type = PG_ENUM(
    "per_sf_year", "per_sf_month", "flat_month", name="ratetype", create_type=False
)
expense_type = PG_ENUM(
    "nnn", "gross", "modified_gross", "unknown", name="expensetype", create_type=False
)
extraction_status = PG_ENUM(
    "pending", "parsed", "needs_review", "failed", name="extractionstatus", create_type=False
)


def _create_enum_idempotent(enum_type: PG_ENUM) -> None:
    """CREATE TYPE, tolerating a concurrent/already-existing type.

    Using Enum.create(checkfirst=True) here was unreliable against Neon
    (checkfirst's existence check didn't consistently see state from
    earlier in the same migration run), so this does the check-and-create
    atomically in Postgres itself instead.
    """
    labels = ", ".join(f"'{v}'" for v in enum_type.enums)
    op.execute(
        f"""
        DO $$ BEGIN
            CREATE TYPE {enum_type.name} AS ENUM ({labels});
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )


def upgrade() -> None:
    _create_enum_idempotent(deal_type)
    _create_enum_idempotent(property_type)
    _create_enum_idempotent(rate_type)
    _create_enum_idempotent(expense_type)
    _create_enum_idempotent(extraction_status)

    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("forwarding_slug", sa.String(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_forwarding_slug", "users", ["forwarding_slug"])

    op.create_table(
        "flyers",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("storage_path", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("sender_email", sa.String()),
        sa.Column("deal_type", deal_type),
        sa.Column(
            "extraction_status", extraction_status, nullable=False, server_default="pending"
        ),
        sa.Column("extraction_error", sa.Text()),
        sa.Column("low_confidence_fields", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_flyers_user_id", "flyers", ["user_id"])

    op.create_table(
        "sale_comps",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("flyer_id", sa.String(), sa.ForeignKey("flyers.id"), nullable=False, unique=True),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("city", sa.String()),
        sa.Column("state", sa.String()),
        sa.Column("submarket", sa.String()),
        sa.Column("property_type", property_type, nullable=False, server_default="other"),
        sa.Column("size_sf", sa.Numeric()),
        sa.Column("price", sa.Numeric()),
        sa.Column("price_per_sf", sa.Numeric()),
        sa.Column("cap_rate", sa.Numeric()),
        sa.Column("broker_name", sa.String()),
        sa.Column("brokerage", sa.String()),
        sa.Column("date_received", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sale_comps_user_id", "sale_comps", ["user_id"])
    op.create_index("ix_sale_comps_submarket", "sale_comps", ["submarket"])
    op.create_index("ix_sale_comps_property_type", "sale_comps", ["property_type"])

    op.create_table(
        "lease_comps",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("flyer_id", sa.String(), sa.ForeignKey("flyers.id"), nullable=False, unique=True),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("city", sa.String()),
        sa.Column("state", sa.String()),
        sa.Column("submarket", sa.String()),
        sa.Column("property_type", property_type, nullable=False, server_default="other"),
        sa.Column("size_sf", sa.Numeric()),
        sa.Column("rate", sa.Numeric()),
        sa.Column("rate_type", rate_type),
        sa.Column("term_months", sa.Numeric()),
        sa.Column("expense_type", expense_type, nullable=False, server_default="unknown"),
        sa.Column("broker_name", sa.String()),
        sa.Column("brokerage", sa.String()),
        sa.Column("date_received", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_lease_comps_user_id", "lease_comps", ["user_id"])
    op.create_index("ix_lease_comps_submarket", "lease_comps", ["submarket"])
    op.create_index("ix_lease_comps_property_type", "lease_comps", ["property_type"])


def downgrade() -> None:
    op.drop_table("lease_comps")
    op.drop_table("sale_comps")
    op.drop_table("flyers")
    op.drop_table("users")

    for enum_name in ("extractionstatus", "expensetype", "ratetype", "propertytype", "dealtype"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

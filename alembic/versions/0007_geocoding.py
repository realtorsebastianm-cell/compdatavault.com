"""latitude/longitude on sale_comps and lease_comps -- powers the map view

Nothing in the vault had coordinates -- address/city/state only. This
adds nullable latitude/longitude columns to both comp tables, populated
best-effort at ingestion time by dealarchive/geocoding.py (US Census
Bureau's free geocoder -- no API key, no billing, fits since this app is
US-only CRE data). Existing comps that predate this column start out
null; POST /geocode-backfill fills those in after the fact.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-25

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sale_comps", sa.Column("latitude", sa.Numeric(), nullable=True))
    op.add_column("sale_comps", sa.Column("longitude", sa.Numeric(), nullable=True))

    op.add_column("lease_comps", sa.Column("latitude", sa.Numeric(), nullable=True))
    op.add_column("lease_comps", sa.Column("longitude", sa.Numeric(), nullable=True))


def downgrade() -> None:
    op.drop_column("lease_comps", "longitude")
    op.drop_column("lease_comps", "latitude")

    op.drop_column("sale_comps", "longitude")
    op.drop_column("sale_comps", "latitude")

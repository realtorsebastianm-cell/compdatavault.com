"""saved_searches + saved_search_matches -- alert on new matching comps

Ask AI answers a question about the vault as it exists right now; there
was no way to ask "and keep telling me." This adds a saved_searches table
(a query parsed into structured filters once, at save time -- see
dealarchive/matching.py::parse_query) and saved_search_matches, populated
by dealarchive/api.py::_process_flyer re-checking every newly ingested
comp against a broker's saved searches with plain field comparisons (no
LLM call per comp -- that's what keeps this cheap enough to run on every
upload/forward).

Both match FKs (sale_comp_id, lease_comp_id) and the saved_search_id FK
are ON DELETE CASCADE: a match row referencing a deleted saved search or a
deleted comp isn't meaningful on its own, so it should just disappear
along with whichever side went away, with no application code needed to
clean it up.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

# Reuses the existing "dealtype" enum type created in 0001 -- create_type=False
# so this doesn't try to (re)create it. See 0001's comment for why the
# postgresql-specific ENUM is used instead of sa.Enum here.
deal_type = PG_ENUM("sale", "lease", name="dealtype", create_type=False)


def upgrade() -> None:
    op.create_table(
        "saved_searches",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("deal_type", sa.String(), nullable=True),
        sa.Column("property_type", sa.String(), nullable=True),
        sa.Column("submarket", sa.String(), nullable=True),
        sa.Column("zoning", sa.String(), nullable=True),
        sa.Column("building_sf_min", sa.Numeric(), nullable=True),
        sa.Column("building_sf_max", sa.Numeric(), nullable=True),
        sa.Column("lot_sf_min", sa.Numeric(), nullable=True),
        sa.Column("lot_sf_max", sa.Numeric(), nullable=True),
        sa.Column("price_per_sf_min", sa.Numeric(), nullable=True),
        sa.Column("price_per_sf_max", sa.Numeric(), nullable=True),
        sa.Column("price_per_unit_min", sa.Numeric(), nullable=True),
        sa.Column("price_per_unit_max", sa.Numeric(), nullable=True),
        sa.Column("cap_rate_min", sa.Numeric(), nullable=True),
        sa.Column("cap_rate_max", sa.Numeric(), nullable=True),
        sa.Column("rate_min", sa.Numeric(), nullable=True),
        sa.Column("rate_max", sa.Numeric(), nullable=True),
        sa.Column("residual_criteria", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_saved_searches_user_id", "saved_searches", ["user_id"])

    op.create_table(
        "saved_search_matches",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "saved_search_id",
            sa.String(),
            sa.ForeignKey("saved_searches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("deal_type", deal_type, nullable=False),
        sa.Column(
            "sale_comp_id", sa.String(), sa.ForeignKey("sale_comps.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column(
            "lease_comp_id", sa.String(), sa.ForeignKey("lease_comps.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column("seen_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_saved_search_matches_saved_search_id", "saved_search_matches", ["saved_search_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_saved_search_matches_saved_search_id", table_name="saved_search_matches")
    op.drop_table("saved_search_matches")

    op.drop_index("ix_saved_searches_user_id", table_name="saved_searches")
    op.drop_table("saved_searches")

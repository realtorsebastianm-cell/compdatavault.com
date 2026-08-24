"""possible-duplicate flag on sale/lease comps

Upload/forward the same flyer twice (or two brokers on the same deal, or a
broker re-sending because the first email "didn't seem to go through") and
the vault silently gets two rows for one property. This adds a nullable
self-referencing duplicate_of_id column to both sale_comps and lease_comps
-- set at ingestion time when a new comp's address normalizes to match an
existing comp already in that broker's vault (see
dealarchive/api.py::_find_duplicate). It's a flag, not a block: the new
comp still gets created (never silently drop data the broker forwarded),
just tagged so the UI can surface "possible duplicate of ..." and let the
broker decide.

ON DELETE SET NULL so deleting the original comp a duplicate points at
doesn't get blocked by (or cascade into deleting) the duplicate itself.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sale_comps", sa.Column("duplicate_of_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_sale_comps_duplicate_of_id",
        "sale_comps",
        "sale_comps",
        ["duplicate_of_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("lease_comps", sa.Column("duplicate_of_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_lease_comps_duplicate_of_id",
        "lease_comps",
        "lease_comps",
        ["duplicate_of_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_lease_comps_duplicate_of_id", "lease_comps", type_="foreignkey")
    op.drop_column("lease_comps", "duplicate_of_id")

    op.drop_constraint("fk_sale_comps_duplicate_of_id", "sale_comps", type_="foreignkey")
    op.drop_column("sale_comps", "duplicate_of_id")

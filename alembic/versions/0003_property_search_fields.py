"""property-type-aware search fields: building/lot SF split, zoning, price-per-unit

Search only had address/submarket/property_type/date to narrow results by,
and size_sf conflated two different measurements (a warehouse's building
footprint and the lot it sits on aren't comparable the same way). This:

- Renames size_sf -> building_sf on both sale_comps and lease_comps, and
  adds a separate lot_sf column.
- Adds zoning (any property type, most useful for industrial) to both.
- Adds num_units/price_per_unit to sale_comps only -- multifamily sale
  comps are usually evaluated per-unit rather than per-SF.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("sale_comps", "size_sf", new_column_name="building_sf")
    op.add_column("sale_comps", sa.Column("lot_sf", sa.Numeric(), nullable=True))
    op.add_column("sale_comps", sa.Column("num_units", sa.Numeric(), nullable=True))
    op.add_column("sale_comps", sa.Column("price_per_unit", sa.Numeric(), nullable=True))
    op.add_column("sale_comps", sa.Column("zoning", sa.String(), nullable=True))
    op.create_index("ix_sale_comps_zoning", "sale_comps", ["zoning"])

    op.alter_column("lease_comps", "size_sf", new_column_name="building_sf")
    op.add_column("lease_comps", sa.Column("lot_sf", sa.Numeric(), nullable=True))
    op.add_column("lease_comps", sa.Column("zoning", sa.String(), nullable=True))
    op.create_index("ix_lease_comps_zoning", "lease_comps", ["zoning"])


def downgrade() -> None:
    op.drop_index("ix_lease_comps_zoning", table_name="lease_comps")
    op.drop_column("lease_comps", "zoning")
    op.drop_column("lease_comps", "lot_sf")
    op.alter_column("lease_comps", "building_sf", new_column_name="size_sf")

    op.drop_index("ix_sale_comps_zoning", table_name="sale_comps")
    op.drop_column("sale_comps", "zoning")
    op.drop_column("sale_comps", "price_per_unit")
    op.drop_column("sale_comps", "num_units")
    op.drop_column("sale_comps", "lot_sf")
    op.alter_column("sale_comps", "building_sf", new_column_name="size_sf")

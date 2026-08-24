from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dealarchive.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class DealType(str, enum.Enum):
    sale = "sale"
    lease = "lease"


class PropertyType(str, enum.Enum):
    office = "office"
    industrial = "industrial"
    retail = "retail"
    land = "land"
    multifamily = "multifamily"
    other = "other"


class RateType(str, enum.Enum):
    per_sf_year = "per_sf_year"
    per_sf_month = "per_sf_month"
    flat_month = "flat_month"


class ExpenseType(str, enum.Enum):
    nnn = "nnn"
    gross = "gross"
    modified_gross = "modified_gross"
    unknown = "unknown"


class ExtractionStatus(str, enum.Enum):
    pending = "pending"
    parsed = "parsed"
    needs_review = "needs_review"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    flyers: Mapped[list["Flyer"]] = relationship(back_populates="user")
    sale_comps: Mapped[list["SaleComp"]] = relationship(back_populates="user")
    lease_comps: Mapped[list["LeaseComp"]] = relationship(back_populates="user")
    authorized_senders: Mapped[list["AuthorizedSender"]] = relationship(back_populates="user")
    saved_searches: Mapped[list["SavedSearch"]] = relationship(back_populates="user")


class AuthorizedSender(Base):
    """A second (third, fourth...) inbox a broker forwards flyers from.

    /ingest/email files a flyer into whichever account's User.email
    case-insensitively matches the envelope From address -- that only
    covers the one address a broker signed up with. This table lets a
    broker register additional inboxes without switching to a login email
    they don't actually check.

    Email is globally unique (not just per-user): if it weren't, one
    broker could claim another's real inbox as an "authorized sender" and
    hijack flyers that broker forwards to the shared inbound address. The
    verification step (see dealarchive/api.py::_ingest_email's pending-
    sender check) proves the person adding the address can actually
    receive mail there before it's trusted for routing -- until then it
    sits unverified and doesn't affect ingestion at all.
    """

    __tablename__ = "authorized_senders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    email: Mapped[str] = mapped_column(String, index=True)
    verification_code: Mapped[str] = mapped_column(String)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="authorized_senders")


class SavedSearch(Base):
    """A broker's saved Ask AI query, re-checked against every new comp as
    it's ingested (see dealarchive/api.py::_matches_saved_search, called
    from _process_flyer) so they get alerted the moment something matching
    comes in, instead of having to remember to re-run the search.

    The query is parsed into structured filters once, at save time (same
    dealarchive/matching.py::parse_query used by /ask) and those filter
    values are what every new comp is actually checked against -- plain
    field comparisons, no LLM call per comp. residual_criteria is stored
    for display only; matching a new comp's notes against qualitative
    criteria would mean an LLM call on every single ingested flyer for
    every saved search, which doesn't scale, so v1 only alerts on the
    structured half of a query.
    """

    __tablename__ = "saved_searches"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    query: Mapped[str] = mapped_column(Text)

    deal_type: Mapped[str | None] = mapped_column(String, nullable=True)
    property_type: Mapped[str | None] = mapped_column(String, nullable=True)
    submarket: Mapped[str | None] = mapped_column(String, nullable=True)
    zoning: Mapped[str | None] = mapped_column(String, nullable=True)
    building_sf_min: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    building_sf_max: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    lot_sf_min: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    lot_sf_max: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    price_per_sf_min: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    price_per_sf_max: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    price_per_unit_min: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    price_per_unit_max: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    cap_rate_min: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    cap_rate_max: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    rate_min: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    rate_max: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    residual_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="saved_searches")


class SavedSearchMatch(Base):
    """One comp that matched a saved search at ingestion time. Deleting
    the saved search or the matched comp cascades and removes this row --
    a match record referencing either isn't meaningful on its own."""

    __tablename__ = "saved_search_matches"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    saved_search_id: Mapped[str] = mapped_column(
        ForeignKey("saved_searches.id", ondelete="CASCADE"), index=True
    )
    deal_type: Mapped[DealType] = mapped_column(Enum(DealType))
    sale_comp_id: Mapped[str | None] = mapped_column(
        ForeignKey("sale_comps.id", ondelete="CASCADE"), nullable=True
    )
    lease_comp_id: Mapped[str | None] = mapped_column(
        ForeignKey("lease_comps.id", ondelete="CASCADE"), nullable=True
    )
    seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Flyer(Base):
    """The raw uploaded/forwarded file, plus its extraction pipeline state.

    Every SaleComp/LeaseComp points back to the Flyer it was parsed from so
    the original document is always available next to the structured data.
    """

    __tablename__ = "flyers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)

    storage_path: Mapped[str] = mapped_column(String)
    original_filename: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String)

    source: Mapped[str] = mapped_column(String)  # "email" | "upload"
    sender_email: Mapped[str | None] = mapped_column(String, nullable=True)

    deal_type: Mapped[DealType | None] = mapped_column(Enum(DealType), nullable=True)
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus), default=ExtractionStatus.pending
    )
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    low_confidence_fields: Mapped[list[str]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="flyers")
    sale_comp: Mapped["SaleComp | None"] = relationship(back_populates="flyer", uselist=False)
    lease_comp: Mapped["LeaseComp | None"] = relationship(back_populates="flyer", uselist=False)


class SaleComp(Base):
    __tablename__ = "sale_comps"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    flyer_id: Mapped[str] = mapped_column(ForeignKey("flyers.id"), unique=True)

    address: Mapped[str] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String, nullable=True)
    submarket: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    property_type: Mapped[PropertyType] = mapped_column(
        Enum(PropertyType), default=PropertyType.other, index=True
    )

    # Kept separate on purpose -- building_sf drives price_per_sf, lot_sf
    # doesn't (an industrial building on a 2-acre lot and one on a 5-acre
    # lot with the same building size are not comparable the same way).
    building_sf: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    lot_sf: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    price_per_sf: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    cap_rate: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    # Multifamily sale comps are usually evaluated on a per-unit basis
    # rather than per-SF -- num_units comes off the flyer, price_per_unit is
    # computed the same way price_per_sf is (price / num_units).
    num_units: Mapped[int | None] = mapped_column(Numeric, nullable=True)
    price_per_unit: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    # Zoning matters most for industrial/land comps but isn't exclusive to
    # them, so it's on every sale comp -- just null when the flyer doesn't
    # list it.
    zoning: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    broker_name: Mapped[str | None] = mapped_column(String, nullable=True)
    brokerage: Mapped[str | None] = mapped_column(String, nullable=True)
    date_received: Mapped[date] = mapped_column(Date, default=date.today)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Set at ingestion time when this comp's address normalizes to match a
    # comp already in the same broker's vault -- see
    # dealarchive/api.py::_find_duplicate. Self-referencing, nullable, and
    # SET NULL on delete so removing the original never blocks or cascades.
    duplicate_of_id: Mapped[str | None] = mapped_column(
        ForeignKey("sale_comps.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="sale_comps")
    flyer: Mapped[Flyer] = relationship(back_populates="sale_comp")


class LeaseComp(Base):
    __tablename__ = "lease_comps"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    flyer_id: Mapped[str] = mapped_column(ForeignKey("flyers.id"), unique=True)

    address: Mapped[str] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String, nullable=True)
    submarket: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    property_type: Mapped[PropertyType] = mapped_column(
        Enum(PropertyType), default=PropertyType.other, index=True
    )

    building_sf: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    lot_sf: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    rate: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    rate_type: Mapped[RateType | None] = mapped_column(Enum(RateType), nullable=True)
    term_months: Mapped[int | None] = mapped_column(Numeric, nullable=True)
    expense_type: Mapped[ExpenseType] = mapped_column(Enum(ExpenseType), default=ExpenseType.unknown)

    zoning: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    broker_name: Mapped[str | None] = mapped_column(String, nullable=True)
    brokerage: Mapped[str | None] = mapped_column(String, nullable=True)
    date_received: Mapped[date] = mapped_column(Date, default=date.today)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    duplicate_of_id: Mapped[str | None] = mapped_column(
        ForeignKey("lease_comps.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="lease_comps")
    flyer: Mapped[Flyer] = relationship(back_populates="lease_comp")

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

    size_sf: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    price_per_sf: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    cap_rate: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    broker_name: Mapped[str | None] = mapped_column(String, nullable=True)
    brokerage: Mapped[str | None] = mapped_column(String, nullable=True)
    date_received: Mapped[date] = mapped_column(Date, default=date.today)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    size_sf: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    rate: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    rate_type: Mapped[RateType | None] = mapped_column(Enum(RateType), nullable=True)
    term_months: Mapped[int | None] = mapped_column(Numeric, nullable=True)
    expense_type: Mapped[ExpenseType] = mapped_column(Enum(ExpenseType), default=ExpenseType.unknown)

    broker_name: Mapped[str | None] = mapped_column(String, nullable=True)
    brokerage: Mapped[str | None] = mapped_column(String, nullable=True)
    date_received: Mapped[date] = mapped_column(Date, default=date.today)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="lease_comps")
    flyer: Mapped[Flyer] = relationship(back_populates="lease_comp")

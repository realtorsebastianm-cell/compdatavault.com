"""HTTP API for Deal Archive.

Run locally: uvicorn dealarchive.api:app --reload
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from dealarchive.auth import create_access_token, get_current_user, hash_password, verify_password
from dealarchive.comparison import ComparisonResult, compare_lease_comp, compare_sale_comp
from dealarchive.config import settings
from dealarchive.db import SessionLocal
from dealarchive.extraction import extract_flyer
from dealarchive.models import (
    DealType,
    ExtractionStatus,
    Flyer,
    LeaseComp,
    PropertyType,
    SaleComp,
    User,
)
from dealarchive.storage import flyer_file_path, save_flyer_file

app = FastAPI(title="Deal Archive API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------


class SignupRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    token: str


@app.post("/auth/signup", response_model=TokenResponse)
def signup(body: SignupRequest):
    with SessionLocal() as session:
        existing = session.scalar(select(User).where(User.email == body.email))
        if existing is not None:
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        user = User(email=body.email, password_hash=hash_password(body.password))
        session.add(user)
        session.commit()
        session.refresh(user)
        return TokenResponse(token=create_access_token(user.id))


@app.post("/auth/login", response_model=TokenResponse)
def login(body: SignupRequest):
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == body.email))
        if user is None or not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return TokenResponse(token=create_access_token(user.id))


class MeResponse(BaseModel):
    email: str
    forwarding_address: str


@app.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(
        email=user.email,
        forwarding_address=f"{user.forwarding_slug}@{settings.inbound_email_domain}",
    )


# --------------------------------------------------------------------------
# Ingestion (shared by manual upload and inbound email)
# --------------------------------------------------------------------------


class ComparisonOut(BaseModel):
    metric: str
    new_value: float
    baseline_avg: float
    pct_diff: float
    comp_count: int


class FlyerResult(BaseModel):
    flyer_id: str
    deal_type: Literal["sale", "lease"] | None
    status: str
    comp_id: str | None = None
    low_confidence_fields: list[str] = []
    comparison: ComparisonOut | None = None
    error: str | None = None


def _to_property_type(value: str | None) -> PropertyType:
    try:
        return PropertyType(value) if value else PropertyType.other
    except ValueError:
        return PropertyType.other


def _process_flyer(session, user: User, content: bytes, filename: str, content_type: str, source: str, sender_email: str | None) -> FlyerResult:
    storage_path = save_flyer_file(content, filename)
    flyer = Flyer(
        user_id=user.id,
        storage_path=storage_path,
        original_filename=filename,
        content_type=content_type or "application/octet-stream",
        source=source,
        sender_email=sender_email,
    )
    session.add(flyer)
    session.flush()

    try:
        result = extract_flyer(content, filename, content_type)
    except Exception as e:  # noqa: BLE001 -- surfaced to the caller, not silently swallowed
        flyer.extraction_status = ExtractionStatus.failed
        flyer.extraction_error = str(e)
        session.commit()
        return FlyerResult(flyer_id=flyer.id, deal_type=None, status="failed", error=str(e))

    flyer.deal_type = DealType(result.deal_type)
    flyer.low_confidence_fields = result.low_confidence_fields
    flyer.extraction_status = (
        ExtractionStatus.needs_review if result.low_confidence_fields else ExtractionStatus.parsed
    )

    fields = result.fields
    comparison: ComparisonResult | None = None
    comp_id: str | None = None

    if result.deal_type == "sale":
        size_sf = fields.get("size_sf")
        price = fields.get("price")
        price_per_sf = (price / size_sf) if price and size_sf else None
        comp = SaleComp(
            user_id=user.id,
            flyer_id=flyer.id,
            address=fields.get("address") or "Unknown address",
            city=fields.get("city"),
            state=fields.get("state"),
            submarket=fields.get("submarket"),
            property_type=_to_property_type(fields.get("property_type")),
            size_sf=size_sf,
            price=price,
            price_per_sf=price_per_sf,
            cap_rate=fields.get("cap_rate"),
            broker_name=fields.get("broker_name"),
            brokerage=fields.get("brokerage"),
            notes=fields.get("notes"),
        )
        session.add(comp)
        session.flush()
        comparison = compare_sale_comp(session, user.id, comp)
        comp_id = comp.id
    else:
        comp = LeaseComp(
            user_id=user.id,
            flyer_id=flyer.id,
            address=fields.get("address") or "Unknown address",
            city=fields.get("city"),
            state=fields.get("state"),
            submarket=fields.get("submarket"),
            property_type=_to_property_type(fields.get("property_type")),
            size_sf=fields.get("size_sf"),
            rate=fields.get("rate"),
            rate_type=fields.get("rate_type"),
            term_months=fields.get("term_months"),
            expense_type=fields.get("expense_type") or "unknown",
            broker_name=fields.get("broker_name"),
            brokerage=fields.get("brokerage"),
            notes=fields.get("notes"),
        )
        session.add(comp)
        session.flush()
        comparison = compare_lease_comp(session, user.id, comp)
        comp_id = comp.id

    session.commit()

    return FlyerResult(
        flyer_id=flyer.id,
        deal_type=result.deal_type,
        status=flyer.extraction_status.value,
        comp_id=comp_id,
        low_confidence_fields=result.low_confidence_fields,
        comparison=ComparisonOut(**comparison.__dict__) if comparison else None,
    )


@app.post("/upload", response_model=FlyerResult)
async def upload_flyer(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    content = await file.read()
    with SessionLocal() as session:
        return _process_flyer(
            session, user, content, file.filename or "flyer", file.content_type or "", "upload", None
        )


@app.post("/ingest/email", response_model=FlyerResult)
async def ingest_email(
    to: str = Form(...),
    sender: str = Form(...),
    file: UploadFile = File(...),
    webhook_secret: str | None = Form(default=None),
):
    """Webhook target for an inbound-email provider (e.g. SendGrid Inbound
    Parse, Postmark). The provider posts the recipient, sender, and the
    flyer attachment here after receiving mail at deals@<domain>.
    """
    if settings.inbound_webhook_secret and webhook_secret != settings.inbound_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    slug = to.split("@", 1)[0]
    content = await file.read()

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.forwarding_slug == slug))
        if user is None:
            # No matching account -- the provider-side auto-reply ("sign up
            # first") is triggered off this 404, not sent from here.
            raise HTTPException(status_code=404, detail="No account matches this forwarding address")
        return _process_flyer(
            session, user, content, file.filename or "flyer", file.content_type or "", "email", sender
        )


# --------------------------------------------------------------------------
# Vaults
# --------------------------------------------------------------------------


class SaleCompOut(BaseModel):
    id: str
    flyer_id: str
    address: str
    city: str | None
    state: str | None
    submarket: str | None
    property_type: str
    size_sf: float | None
    price: float | None
    price_per_sf: float | None
    cap_rate: float | None
    broker_name: str | None
    brokerage: str | None
    date_received: date
    notes: str | None

    model_config = {"from_attributes": True}


class LeaseCompOut(BaseModel):
    id: str
    flyer_id: str
    address: str
    city: str | None
    state: str | None
    submarket: str | None
    property_type: str
    size_sf: float | None
    rate: float | None
    rate_type: str | None
    term_months: int | None
    expense_type: str
    broker_name: str | None
    brokerage: str | None
    date_received: date
    notes: str | None

    model_config = {"from_attributes": True}


@app.get("/sale-comps", response_model=list[SaleCompOut])
def list_sale_comps(
    submarket: str | None = None,
    property_type: PropertyType | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = Query(default=None, description="matches address"),
    user: User = Depends(get_current_user),
):
    with SessionLocal() as session:
        stmt = select(SaleComp).where(SaleComp.user_id == user.id)
        if submarket:
            stmt = stmt.where(SaleComp.submarket == submarket)
        if property_type:
            stmt = stmt.where(SaleComp.property_type == property_type)
        if date_from:
            stmt = stmt.where(SaleComp.date_received >= date_from)
        if date_to:
            stmt = stmt.where(SaleComp.date_received <= date_to)
        if q:
            stmt = stmt.where(SaleComp.address.ilike(f"%{q}%"))
        stmt = stmt.order_by(SaleComp.date_received.desc())
        return session.scalars(stmt).all()


@app.get("/lease-comps", response_model=list[LeaseCompOut])
def list_lease_comps(
    submarket: str | None = None,
    property_type: PropertyType | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = Query(default=None, description="matches address"),
    user: User = Depends(get_current_user),
):
    with SessionLocal() as session:
        stmt = select(LeaseComp).where(LeaseComp.user_id == user.id)
        if submarket:
            stmt = stmt.where(LeaseComp.submarket == submarket)
        if property_type:
            stmt = stmt.where(LeaseComp.property_type == property_type)
        if date_from:
            stmt = stmt.where(LeaseComp.date_received >= date_from)
        if date_to:
            stmt = stmt.where(LeaseComp.date_received <= date_to)
        if q:
            stmt = stmt.where(LeaseComp.address.ilike(f"%{q}%"))
        stmt = stmt.order_by(LeaseComp.date_received.desc())
        return session.scalars(stmt).all()


@app.get("/sale-comps/{comp_id}", response_model=SaleCompOut)
def get_sale_comp(comp_id: str, user: User = Depends(get_current_user)):
    with SessionLocal() as session:
        comp = session.scalar(
            select(SaleComp).where(SaleComp.id == comp_id, SaleComp.user_id == user.id)
        )
        if comp is None:
            raise HTTPException(status_code=404, detail="Not found")
        return comp


@app.get("/lease-comps/{comp_id}", response_model=LeaseCompOut)
def get_lease_comp(comp_id: str, user: User = Depends(get_current_user)):
    with SessionLocal() as session:
        comp = session.scalar(
            select(LeaseComp).where(LeaseComp.id == comp_id, LeaseComp.user_id == user.id)
        )
        if comp is None:
            raise HTTPException(status_code=404, detail="Not found")
        return comp


@app.get("/flyers/{flyer_id}/file")
def get_flyer_file(flyer_id: str, user: User = Depends(get_current_user)):
    with SessionLocal() as session:
        flyer = session.scalar(
            select(Flyer).where(Flyer.id == flyer_id, Flyer.user_id == user.id)
        )
        if flyer is None:
            raise HTTPException(status_code=404, detail="Not found")
        path = flyer_file_path(flyer.storage_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="File missing from storage")
        return FileResponse(path, media_type=flyer.content_type, filename=flyer.original_filename)

"""HTTP API for Deal Archive.

Run locally: uvicorn dealarchive.api:app --reload
"""
from __future__ import annotations

import re
from datetime import date
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from typing import Literal
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func, select

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
from dealarchive.storage import read_flyer_file, save_flyer_file

app = FastAPI(title="Deal Archive API")

# FRONTEND_URL only pins down one host (e.g. "www.compdatavault.com"), but
# both the bare domain and the www subdomain resolve and get used by real
# visitors -- CORS needs to accept whichever one the browser is actually on,
# not just the exact string in the env var. Vercel preview deploys also need
# to keep working, hence the extra regex alternative.
_frontend_host = urlparse(settings.frontend_url).netloc
_frontend_bare_host = re.sub(r"^www\.", "", _frontend_host)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=rf"https://(www\.)?{re.escape(_frontend_bare_host)}|https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


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
    # Every broker forwards to the same address -- there's no per-user slug
    # anymore. /ingest/email identifies whose vault a flyer belongs to by
    # matching the sender's email against this account's `email`, so what
    # matters for a given user is that they forward *from* the address
    # they signed up with, not that they have a unique *to* address.
    return MeResponse(
        email=user.email,
        forwarding_address=settings.inbound_base_address or "(inbound email not configured yet)",
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
        building_sf = fields.get("building_sf")
        price = fields.get("price")
        price_per_sf = (price / building_sf) if price and building_sf else None
        num_units = fields.get("num_units")
        price_per_unit = (price / num_units) if price and num_units else None
        comp = SaleComp(
            user_id=user.id,
            flyer_id=flyer.id,
            address=fields.get("address") or "Unknown address",
            city=fields.get("city"),
            state=fields.get("state"),
            submarket=fields.get("submarket"),
            property_type=_to_property_type(fields.get("property_type")),
            building_sf=building_sf,
            lot_sf=fields.get("lot_sf"),
            price=price,
            price_per_sf=price_per_sf,
            cap_rate=fields.get("cap_rate"),
            num_units=num_units,
            price_per_unit=price_per_unit,
            zoning=fields.get("zoning"),
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
            building_sf=fields.get("building_sf"),
            lot_sf=fields.get("lot_sf"),
            rate=fields.get("rate"),
            rate_type=fields.get("rate_type"),
            term_months=fields.get("term_months"),
            expense_type=fields.get("expense_type") or "unknown",
            zoning=fields.get("zoning"),
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


def _sender_auth_status(headers) -> str | None:
    """Best-effort SPF/DKIM read from an Authentication-Results header, if present.

    Cloudflare Email Routing doesn't guarantee this header on every message
    (depends on the sending server's own setup), so absence isn't treated as
    failure -- only an explicit "fail" is. This exists because matching
    accounts purely on an unauthenticated From header is spoofable in
    principle; treat an explicit SPF/DKIM fail as a signal to reject rather
    than silently filing a forged email into someone's comp vault.
    """
    auth_results = headers.get("Authentication-Results", "")
    if not auth_results:
        return None
    lowered = auth_results.lower()
    if "spf=fail" in lowered or "dkim=fail" in lowered:
        return "fail"
    return "ok"


@app.post("/ingest/email", response_model=list[FlyerResult])
async def ingest_email(
    from_address: str = Form(...),
    to_address: str = Form(...),
    subject: str = Form(""),
    raw_email: UploadFile = File(...),
    x_ingest_secret: str | None = Header(default=None, alias="X-Ingest-Secret"),
):
    """Webhook target invoked by our own Cloudflare Email Worker.

    Every broker forwards flyers to the same address (settings.inbound_base_address,
    e.g. "deals@compdatavault.com") -- there's no per-user routing trick. Cloudflare
    Email Routing has one exact-match rule on that address pointing at a Worker,
    which POSTs the envelope from/to, the Subject header, and the full raw .eml as
    multipart/form-data here.

    Whose vault a flyer lands in is decided by matching the envelope From address
    against User.email (case-insensitive). This means a broker must forward from
    the same email they signed up with -- if they habitually forward from a
    different (e.g. work/brokerage) address, this will 404 until either they sign
    up with that address or account settings grow support for multiple authorized
    sender addresses.

    The Worker has no built-in request signing, so it sends a shared secret in
    X-Ingest-Secret, checked here against INBOUND_WEBHOOK_SECRET. Set the same
    value in both places (`wrangler secret put INGEST_SHARED_SECRET` on the Worker,
    INBOUND_WEBHOOK_SECRET in Render's env vars).
    """
    if settings.inbound_webhook_secret and x_ingest_secret != settings.inbound_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    _, recipient_email = parseaddr(to_address)
    if settings.inbound_base_address and recipient_email.lower() != settings.inbound_base_address.lower():
        # Defense in depth in case the Worker's own address guard is ever
        # loosened/misconfigured -- only the one address we advertise should
        # ever result in a flyer being filed.
        raise HTTPException(status_code=400, detail="Unexpected recipient address")

    _, sender_email = parseaddr(from_address)
    if not sender_email:
        raise HTTPException(status_code=400, detail="Could not parse a sender address from From")

    raw_bytes = await raw_email.read()
    parsed_message = BytesParser(policy=policy.default).parsebytes(raw_bytes)

    if _sender_auth_status(parsed_message) == "fail":
        raise HTTPException(status_code=403, detail="Sender failed SPF/DKIM verification")

    attachments: list[tuple[bytes, str, str]] = []
    for part in parsed_message.iter_attachments():
        content = part.get_content()
        if isinstance(content, str):
            content = content.encode("utf-8")
        attachments.append((content, part.get_filename() or "flyer", part.get_content_type()))

    if not attachments:
        raise HTTPException(status_code=400, detail="No attachments on this email")

    with SessionLocal() as session:
        user = session.scalar(
            select(User).where(func.lower(User.email) == sender_email.lower())
        )
        if user is None:
            # No matching account -- nothing auto-replies on our behalf, so
            # a "sign up first" / "forward from your account email" bounce
            # would need to be sent from here explicitly if that's wanted
            # later.
            raise HTTPException(
                status_code=404,
                detail="No account matches this sender address -- forward from the email you signed up with",
            )

        results = []
        for content, filename, content_type in attachments:
            results.append(
                _process_flyer(
                    session,
                    user,
                    content,
                    filename,
                    content_type,
                    "email",
                    sender_email,
                )
            )
        return results


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
    building_sf: float | None
    lot_sf: float | None
    price: float | None
    price_per_sf: float | None
    cap_rate: float | None
    num_units: float | None
    price_per_unit: float | None
    zoning: str | None
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
    building_sf: float | None
    lot_sf: float | None
    rate: float | None
    rate_type: str | None
    term_months: int | None
    expense_type: str
    zoning: str | None
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
    zoning: str | None = Query(default=None, description="matches zoning, e.g. industrial"),
    price_per_unit_min: float | None = Query(default=None, description="multifamily filter"),
    price_per_unit_max: float | None = Query(default=None, description="multifamily filter"),
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
        if zoning:
            stmt = stmt.where(SaleComp.zoning.ilike(f"%{zoning}%"))
        if price_per_unit_min is not None:
            stmt = stmt.where(SaleComp.price_per_unit >= price_per_unit_min)
        if price_per_unit_max is not None:
            stmt = stmt.where(SaleComp.price_per_unit <= price_per_unit_max)
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
    zoning: str | None = Query(default=None, description="matches zoning, e.g. industrial"),
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
        if zoning:
            stmt = stmt.where(LeaseComp.zoning.ilike(f"%{zoning}%"))
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
        try:
            content = read_flyer_file(flyer.storage_path)
        except Exception:
            raise HTTPException(status_code=404, detail="File missing from storage")
        return Response(
            content=content,
            media_type=flyer.content_type,
            headers={
                "Content-Disposition": f'inline; filename="{flyer.original_filename}"'
            },
        )

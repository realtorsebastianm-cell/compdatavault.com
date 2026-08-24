"""HTTP API for Deal Archive.

Run locally: uvicorn dealarchive.api:app --reload
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace as _dataclass_replace
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
from dealarchive.export import build_workbook
from dealarchive.extraction import extract_flyer
from dealarchive.matching import parse_query, rank_by_residual
from dealarchive.valuation import PropertyProfile, parse_property, rank_for_valuation
from dealarchive.models import (
    DealType,
    ExtractionStatus,
    Flyer,
    LeaseComp,
    PropertyType,
    SaleComp,
    User,
)
from dealarchive.storage import delete_flyer_file, read_flyer_file, save_flyer_file

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
    allow_origins=[settings.frontend_url] if settings.frontend_url.startswith("http://") else [],
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


class PossibleDuplicateOut(BaseModel):
    comp_id: str
    address: str


class FlyerResult(BaseModel):
    flyer_id: str
    deal_type: Literal["sale", "lease"] | None
    status: str
    comp_id: str | None = None
    low_confidence_fields: list[str] = []
    comparison: ComparisonOut | None = None
    possible_duplicate: PossibleDuplicateOut | None = None
    error: str | None = None


def _to_property_type(value: str | None) -> PropertyType:
    try:
        return PropertyType(value) if value else PropertyType.other
    except ValueError:
        return PropertyType.other


def _normalize_address(address: str) -> str:
    """Collapse an address down to just its alphanumerics for duplicate
    matching -- "123 Main St." vs "123 Main St" vs "123  main st" should
    all normalize the same way. Deliberately not fuzzy (no edit-distance,
    no abbreviation expansion): an exact normalized match is a strong
    signal a broker's own comp vault has the same property twice, while a
    fuzzy match risks false positives on genuinely different addresses
    (e.g. "123 Main St Unit A" vs "123 Main St Unit B")."""
    cleaned = re.sub(r"[^a-z0-9]+", " ", address.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _find_duplicate(session, model, user_id: str, address: str):
    """Best-effort duplicate lookup within one broker's vault. Fetches that
    broker's existing comps of this deal type and compares normalized
    addresses in Python rather than in SQL -- a broker's vault is small
    enough (hundreds, not millions, of comps) that this is simpler and more
    reliable than a portable SQL-side normalization, and it keeps the
    matching logic in one place shared with nothing else."""
    normalized = _normalize_address(address)
    if not normalized:
        return None
    existing = session.scalars(select(model).where(model.user_id == user_id)).all()
    for candidate in existing:
        if _normalize_address(candidate.address) == normalized:
            return candidate
    return None


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
    address = fields.get("address") or "Unknown address"
    duplicate = None

    if result.deal_type == "sale":
        if address != "Unknown address":
            duplicate = _find_duplicate(session, SaleComp, user.id, address)
        building_sf = fields.get("building_sf")
        price = fields.get("price")
        price_per_sf = (price / building_sf) if price and building_sf else None
        num_units = fields.get("num_units")
        price_per_unit = (price / num_units) if price and num_units else None
        comp = SaleComp(
            user_id=user.id,
            flyer_id=flyer.id,
            address=address,
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
            duplicate_of_id=duplicate.id if duplicate else None,
        )
        session.add(comp)
        session.flush()
        comparison = compare_sale_comp(session, user.id, comp)
        comp_id = comp.id
    else:
        if address != "Unknown address":
            duplicate = _find_duplicate(session, LeaseComp, user.id, address)
        comp = LeaseComp(
            user_id=user.id,
            flyer_id=flyer.id,
            address=address,
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
            duplicate_of_id=duplicate.id if duplicate else None,
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
        possible_duplicate=(
            PossibleDuplicateOut(comp_id=duplicate.id, address=duplicate.address)
            if duplicate
            else None
        ),
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
    duplicate_of_id: str | None = None

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
    duplicate_of_id: str | None = None

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


def _delete_comp(session, comp) -> None:
    """Delete a comp, its parent flyer row, and the flyer's raw file in R2.

    A comp's flyer_id is unique (one flyer -> at most one comp), so the
    flyer row exists only to serve this comp and is safe to remove with
    it. Storage deletion is best-effort: if R2 is unreachable or the
    object's already gone, that shouldn't block removing the comp from the
    vault, since the broker's intent here is "get this out of my vault,"
    not "prove the file was deleted."
    """
    flyer = session.get(Flyer, comp.flyer_id)
    session.delete(comp)
    if flyer is not None:
        session.delete(flyer)
    session.commit()
    if flyer is not None:
        try:
            delete_flyer_file(flyer.storage_path)
        except Exception:  # noqa: BLE001 -- storage cleanup is best-effort
            pass


@app.delete("/sale-comps/{comp_id}", status_code=204)
def delete_sale_comp(comp_id: str, user: User = Depends(get_current_user)):
    with SessionLocal() as session:
        comp = session.scalar(
            select(SaleComp).where(SaleComp.id == comp_id, SaleComp.user_id == user.id)
        )
        if comp is None:
            raise HTTPException(status_code=404, detail="Not found")
        _delete_comp(session, comp)


@app.delete("/lease-comps/{comp_id}", status_code=204)
def delete_lease_comp(comp_id: str, user: User = Depends(get_current_user)):
    with SessionLocal() as session:
        comp = session.scalar(
            select(LeaseComp).where(LeaseComp.id == comp_id, LeaseComp.user_id == user.id)
        )
        if comp is None:
            raise HTTPException(status_code=404, detail="Not found")
        _delete_comp(session, comp)


# --------------------------------------------------------------------------
# Natural-language search ("Ask AI")
# --------------------------------------------------------------------------

ASK_CANDIDATE_LIMIT = 40


class AskRequest(BaseModel):
    query: str


class AskMatch(BaseModel):
    deal_type: Literal["sale", "lease"]
    comp: SaleCompOut | LeaseCompOut
    reason: str | None = None


class AskResponse(BaseModel):
    matches: list[AskMatch]
    understood: dict
    residual_criteria: str | None = None


def _apply_common_comp_filters(stmt, model, parsed, property_type_enum):
    if property_type_enum is not None:
        stmt = stmt.where(model.property_type == property_type_enum)
    if parsed.submarket:
        stmt = stmt.where(model.submarket.ilike(f"%{parsed.submarket}%"))
    if parsed.zoning:
        stmt = stmt.where(model.zoning.ilike(f"%{parsed.zoning}%"))
    if parsed.building_sf_min is not None:
        stmt = stmt.where(model.building_sf >= parsed.building_sf_min)
    if parsed.building_sf_max is not None:
        stmt = stmt.where(model.building_sf <= parsed.building_sf_max)
    if parsed.lot_sf_min is not None:
        stmt = stmt.where(model.lot_sf >= parsed.lot_sf_min)
    if parsed.lot_sf_max is not None:
        stmt = stmt.where(model.lot_sf <= parsed.lot_sf_max)
    return stmt


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, user: User = Depends(get_current_user)):
    """Free-text search over the broker's own vault. A query gets parsed
    into structured filters (fast, deterministic, runs as ordinary SQL)
    plus optional "residual" criteria that isn't a stored column -- things
    like clear height or dock doors that only live in a flyer's notes --
    which gets a second, narrower LLM pass against just the notes of the
    already-filtered candidates. See dealarchive/matching.py."""
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query is required")

    try:
        parsed = parse_query(body.query)
    except Exception as e:  # noqa: BLE001 -- surfaced to the caller, not silently swallowed
        raise HTTPException(status_code=502, detail=f"Couldn't understand that search: {e}")

    property_type_enum = None
    if parsed.property_type:
        try:
            property_type_enum = PropertyType(parsed.property_type)
        except ValueError:
            property_type_enum = None

    with SessionLocal() as session:
        tagged: list[tuple[str, SaleComp | LeaseComp]] = []

        if parsed.deal_type in (None, "sale"):
            stmt = select(SaleComp).where(SaleComp.user_id == user.id)
            stmt = _apply_common_comp_filters(stmt, SaleComp, parsed, property_type_enum)
            if parsed.price_per_sf_min is not None:
                stmt = stmt.where(SaleComp.price_per_sf >= parsed.price_per_sf_min)
            if parsed.price_per_sf_max is not None:
                stmt = stmt.where(SaleComp.price_per_sf <= parsed.price_per_sf_max)
            if parsed.price_per_unit_min is not None:
                stmt = stmt.where(SaleComp.price_per_unit >= parsed.price_per_unit_min)
            if parsed.price_per_unit_max is not None:
                stmt = stmt.where(SaleComp.price_per_unit <= parsed.price_per_unit_max)
            if parsed.cap_rate_min is not None:
                stmt = stmt.where(SaleComp.cap_rate >= parsed.cap_rate_min)
            if parsed.cap_rate_max is not None:
                stmt = stmt.where(SaleComp.cap_rate <= parsed.cap_rate_max)
            stmt = stmt.order_by(SaleComp.date_received.desc()).limit(ASK_CANDIDATE_LIMIT)
            tagged += [("sale", c) for c in session.scalars(stmt).all()]

        if parsed.deal_type in (None, "lease"):
            stmt = select(LeaseComp).where(LeaseComp.user_id == user.id)
            stmt = _apply_common_comp_filters(stmt, LeaseComp, parsed, property_type_enum)
            if parsed.rate_min is not None:
                stmt = stmt.where(LeaseComp.rate >= parsed.rate_min)
            if parsed.rate_max is not None:
                stmt = stmt.where(LeaseComp.rate <= parsed.rate_max)
            stmt = stmt.order_by(LeaseComp.date_received.desc()).limit(ASK_CANDIDATE_LIMIT)
            tagged += [("lease", c) for c in session.scalars(stmt).all()]

        if parsed.residual_criteria and tagged:
            candidate_payload = [
                {"id": c.id, "address": c.address, "notes": c.notes or ""} for _, c in tagged
            ]
            try:
                ranked = rank_by_residual(parsed.residual_criteria, candidate_payload)
            except Exception:  # noqa: BLE001 -- fall back to the unranked filter results
                ranked = []
            if ranked:
                reason_by_id = {m.comp_id: m.reason for m in ranked}
                order = {m.comp_id: i for i, m in enumerate(ranked)}
                tagged = sorted(
                    (t for t in tagged if t[1].id in reason_by_id),
                    key=lambda t: order[t[1].id],
                )
            else:
                reason_by_id = {}
        else:
            reason_by_id = {}

        matches = [
            AskMatch(
                deal_type=dt,
                comp=(SaleCompOut if dt == "sale" else LeaseCompOut).model_validate(c),
                reason=reason_by_id.get(c.id),
            )
            for dt, c in tagged
        ]

        return AskResponse(
            matches=matches,
            understood={
                k: v
                for k, v in parsed.__dict__.items()
                if v is not None and k != "residual_criteria"
            },
            residual_criteria=parsed.residual_criteria,
        )


# --------------------------------------------------------------------------
# Valuation matcher -- paste your own property, get matched to the best
# comps in your vault plus a rough estimate.
# --------------------------------------------------------------------------

VALUE_CANDIDATE_LIMIT = 60
# A valuation needs enough comps to average across, not just the single
# closest match -- generous window on purpose, wider than Ask AI's search
# filters.
VALUE_SF_WINDOW_PCT = 0.35
VALUE_ESTIMATE_SAMPLE = 8


class ValueRequest(BaseModel):
    # "describe" sends free text through the LLM parser (dealarchive/
    # valuation.py::parse_property). "manual" skips that entirely -- the
    # structured fields below go straight into the SQL filters with no LLM
    # in the loop, for a broker who wants the number-matching to be exact
    # rather than trust an LLM's read of a paragraph. `notes` still feeds
    # the second-stage qualitative ranking pass either way, since that's
    # genuinely a text-understanding task, not a number-extraction one.
    mode: Literal["describe", "manual"] = "describe"
    deal_type: Literal["sale", "lease"]
    description: str = ""
    property_type: PropertyType | None = None
    submarket: str | None = None
    zoning: str | None = None
    building_sf: float | None = None
    lot_sf: float | None = None
    notes: str | None = None


class ValueMatch(BaseModel):
    comp: SaleCompOut | LeaseCompOut
    reason: str | None = None


class ValueEstimate(BaseModel):
    metric: Literal["price_per_sf", "rate"]
    low: float
    high: float
    average: float
    based_on: int
    rate_type: str | None = None


class ValueResponse(BaseModel):
    understood: dict
    matches: list[ValueMatch]
    estimate: ValueEstimate | None = None
    narrowed_by: list[str]


def _value_candidates(session, model, user_id, profile, property_type_enum, narrowed_by):
    stmt = select(model).where(model.user_id == user_id)
    if property_type_enum is not None:
        stmt = stmt.where(model.property_type == property_type_enum)
        narrowed_by.append("property_type")
    if profile.submarket:
        stmt = stmt.where(model.submarket.ilike(f"%{profile.submarket}%"))
        narrowed_by.append("submarket")
    if profile.zoning:
        stmt = stmt.where(model.zoning.ilike(f"%{profile.zoning}%"))
        narrowed_by.append("zoning")
    if profile.building_sf:
        low = profile.building_sf * (1 - VALUE_SF_WINDOW_PCT)
        high = profile.building_sf * (1 + VALUE_SF_WINDOW_PCT)
        stmt = stmt.where(model.building_sf.between(low, high))
        narrowed_by.append("building_sf")
    if profile.lot_sf:
        low = profile.lot_sf * (1 - VALUE_SF_WINDOW_PCT)
        high = profile.lot_sf * (1 + VALUE_SF_WINDOW_PCT)
        stmt = stmt.where(model.lot_sf.between(low, high))
        narrowed_by.append("lot_sf")
    stmt = stmt.order_by(model.date_received.desc()).limit(VALUE_CANDIDATE_LIMIT)
    return session.scalars(stmt).all()


@app.post("/value", response_model=ValueResponse)
def value_property(body: ValueRequest, user: User = Depends(get_current_user)):
    """A broker either pastes in a freeform description of a property
    they're valuing (mode="describe", parsed by an LLM -- see
    dealarchive/valuation.py) or fills out exact fields themselves
    (mode="manual", no LLM involved in the numbers at all). Either way
    this matches the resulting profile against the broker's own vault and
    returns the comps that best support a value, plus a rough estimate
    computed from them -- same two-stage shape as /ask, but oriented at
    "give me a defensible comp set" rather than "find the one thing I
    described"."""
    if body.mode == "manual":
        if not any(
            [
                body.property_type,
                body.submarket,
                body.zoning,
                body.building_sf,
                body.lot_sf,
                body.notes,
            ]
        ):
            raise HTTPException(status_code=400, detail="Fill in at least one field")
        profile = PropertyProfile(
            property_type=body.property_type.value if body.property_type else None,
            submarket=body.submarket,
            zoning=body.zoning,
            building_sf=body.building_sf,
            lot_sf=body.lot_sf,
            notes_summary=body.notes,
        )
    else:
        if not body.description.strip():
            raise HTTPException(status_code=400, detail="Property description is required")
        try:
            profile = parse_property(body.description)
        except Exception as e:  # noqa: BLE001 -- surfaced to the caller, not silently swallowed
            raise HTTPException(status_code=502, detail=f"Couldn't understand that description: {e}")

    property_type_enum = None
    if profile.property_type:
        try:
            property_type_enum = PropertyType(profile.property_type)
        except ValueError:
            property_type_enum = None

    model = SaleComp if body.deal_type == "sale" else LeaseComp

    with SessionLocal() as session:
        narrowed_by: list[str] = []
        candidates = _value_candidates(session, model, user.id, profile, property_type_enum, narrowed_by)

        # Too few comps to average across a valuation off of -- widen by
        # dropping submarket first (a $/SF estimate leans more on size and
        # property type than on submarket), then drop property_type/SF too
        # rather than return nothing.
        if len(candidates) < 3 and profile.submarket:
            narrowed_by = []
            loosened_profile = _dataclass_replace(profile, submarket=None)
            candidates = _value_candidates(session, model, user.id, loosened_profile, property_type_enum, narrowed_by)
        if len(candidates) < 3:
            narrowed_by = []
            stmt = select(model).where(model.user_id == user.id).order_by(model.date_received.desc()).limit(VALUE_CANDIDATE_LIMIT)
            broadened = session.scalars(stmt).all()
            if len(broadened) > len(candidates):
                candidates = broadened

        reason_by_id: dict[str, str] = {}
        if profile.notes_summary and candidates:
            payload = [{"id": c.id, "address": c.address, "notes": c.notes or ""} for c in candidates]
            try:
                ranked = rank_for_valuation(profile.notes_summary, payload)
            except Exception:  # noqa: BLE001 -- fall back to the unranked candidate set
                ranked = []
            if ranked:
                reason_by_id = {m.comp_id: m.reason for m in ranked}
                order = {m.comp_id: i for i, m in enumerate(ranked)}
                ranked_ids = set(reason_by_id)
                candidates = sorted(
                    (c for c in candidates if c.id in ranked_ids),
                    key=lambda c: order[c.id],
                )

        out_model = SaleCompOut if body.deal_type == "sale" else LeaseCompOut
        matches = [
            ValueMatch(comp=out_model.model_validate(c), reason=reason_by_id.get(c.id))
            for c in candidates
        ]

        estimate = None
        rate_type_out: str | None = None
        if body.deal_type == "sale":
            sample = candidates[:VALUE_ESTIMATE_SAMPLE]
            values = [float(c.price_per_sf) for c in sample if c.price_per_sf]
            metric: Literal["price_per_sf", "rate"] = "price_per_sf"
        else:
            # $/SF/yr, $/SF/mo, and flat $/mo aren't comparable numbers --
            # averaging across rate types would silently produce a
            # meaningless figure. Instead, average only within whichever
            # rate type is most common among the ranked candidates, and
            # report which one so the UI can label it correctly.
            with_rate = [c for c in candidates if c.rate and c.rate_type]
            metric = "rate"
            if with_rate:
                dominant_type = Counter(c.rate_type for c in with_rate).most_common(1)[0][0]
                rate_type_out = dominant_type.value
                same_type = [c for c in with_rate if c.rate_type == dominant_type]
                values = [float(c.rate) for c in same_type[:VALUE_ESTIMATE_SAMPLE]]
            else:
                values = []
        if values:
            estimate = ValueEstimate(
                metric=metric,
                low=min(values),
                high=max(values),
                average=sum(values) / len(values),
                based_on=len(values),
                rate_type=rate_type_out,
            )

        return ValueResponse(
            understood={
                k: v
                for k, v in profile.__dict__.items()
                if v is not None and k != "notes_summary"
            },
            matches=matches,
            estimate=estimate,
            narrowed_by=narrowed_by,
        )


# --------------------------------------------------------------------------
# Export -- selected comps to an .xlsx workbook
# --------------------------------------------------------------------------


class ExportRequest(BaseModel):
    sale_comp_ids: list[str] = []
    lease_comp_ids: list[str] = []


@app.post("/export")
def export_comps(body: ExportRequest, user: User = Depends(get_current_user)):
    if not body.sale_comp_ids and not body.lease_comp_ids:
        raise HTTPException(status_code=400, detail="No comps selected")

    with SessionLocal() as session:
        sale_comps: list[SaleComp] = []
        if body.sale_comp_ids:
            sale_comps = session.scalars(
                select(SaleComp).where(
                    SaleComp.id.in_(body.sale_comp_ids), SaleComp.user_id == user.id
                )
            ).all()

        lease_comps: list[LeaseComp] = []
        if body.lease_comp_ids:
            lease_comps = session.scalars(
                select(LeaseComp).where(
                    LeaseComp.id.in_(body.lease_comp_ids), LeaseComp.user_id == user.id
                )
            ).all()

        if not sale_comps and not lease_comps:
            raise HTTPException(status_code=404, detail="None of the selected comps were found")

        workbook_bytes = build_workbook(sale_comps, lease_comps)
        return Response(
            content=workbook_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="compdatavault-comps.xlsx"'
            },
        )


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

"""Compare a freshly-parsed comp against the broker's recent comps in the
same submarket + property type, so intake can reply "this is X% above your
last N comps" immediately.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from dealarchive.models import LeaseComp, PropertyType, SaleComp

LOOKBACK = 5


@dataclass
class ComparisonResult:
    metric: str  # "price_per_sf" | "rate"
    new_value: float
    baseline_avg: float
    pct_diff: float
    comp_count: int


def _pct_diff(new_value: float, baseline_avg: float) -> float:
    if baseline_avg == 0:
        return 0.0
    return round((new_value - baseline_avg) / baseline_avg * 100, 1)


def compare_sale_comp(session: Session, user_id: str, comp: SaleComp) -> ComparisonResult | None:
    if comp.price_per_sf is None or comp.submarket is None:
        return None
    prior = session.scalars(
        select(SaleComp)
        .where(
            SaleComp.user_id == user_id,
            SaleComp.submarket == comp.submarket,
            SaleComp.property_type == comp.property_type,
            SaleComp.id != comp.id,
            SaleComp.price_per_sf.is_not(None),
        )
        .order_by(SaleComp.date_received.desc())
        .limit(LOOKBACK)
    ).all()
    if not prior:
        return None
    avg = sum(float(c.price_per_sf) for c in prior) / len(prior)
    return ComparisonResult(
        metric="price_per_sf",
        new_value=float(comp.price_per_sf),
        baseline_avg=round(avg, 2),
        pct_diff=_pct_diff(float(comp.price_per_sf), avg),
        comp_count=len(prior),
    )


def compare_lease_comp(session: Session, user_id: str, comp: LeaseComp) -> ComparisonResult | None:
    if comp.rate is None or comp.submarket is None:
        return None
    prior = session.scalars(
        select(LeaseComp)
        .where(
            LeaseComp.user_id == user_id,
            LeaseComp.submarket == comp.submarket,
            LeaseComp.property_type == comp.property_type,
            LeaseComp.rate_type == comp.rate_type,
            LeaseComp.id != comp.id,
            LeaseComp.rate.is_not(None),
        )
        .order_by(LeaseComp.date_received.desc())
        .limit(LOOKBACK)
    ).all()
    if not prior:
        return None
    avg = sum(float(c.rate) for c in prior) / len(prior)
    return ComparisonResult(
        metric="rate",
        new_value=float(comp.rate),
        baseline_avg=round(avg, 2),
        pct_diff=_pct_diff(float(comp.rate), avg),
        comp_count=len(prior),
    )

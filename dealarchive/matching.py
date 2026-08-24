"""Natural-language search over a broker's comp vault.

Two-stage approach, deliberately not a vector store:

1. The user's free-text query gets sent to Claude once, which converts it
   into structured filters that map directly onto columns we already have
   (property_type, submarket, zoning, SF ranges, price ranges, etc) plus a
   `residual_criteria` string for anything that isn't a stored column --
   most commonly something that only lives in a flyer's freeform notes,
   like "10-18 clear height" or "roll-up doors".
2. Stage 1's structured filters run as an ordinary SQL query, same as the
   existing VaultFilters UI -- fast, deterministic, no hallucination risk.
   If there's residual criteria, the (already-narrowed) candidate set's
   notes get sent to Claude a second time to rank/filter by whatever
   wasn't a real column, since that's genuinely a text-understanding task
   the database can't do on its own.

This keeps the common case (a query that's fully expressible as filters)
cheap and deterministic, and only pays for a second LLM call when the
query actually needs one.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

import anthropic

from dealarchive.config import settings

MODEL = "claude-sonnet-4-5"

QUERY_SCHEMA_PROMPT = """\
You are turning a commercial real estate broker's natural-language search \
into structured filters over their comp database. Return ONLY a JSON object \
(no prose, no markdown fences) with this shape:

{
  "deal_type": "sale" | "lease" | null,  // null if the query doesn't specify -- search both
  "property_type": "office" | "industrial" | "retail" | "land" | "multifamily" | "other" | null,
  "submarket": string | null,
  "zoning": string | null,
  "building_sf_min": number | null,
  "building_sf_max": number | null,
  "lot_sf_min": number | null,
  "lot_sf_max": number | null,
  "price_per_sf_min": number | null,
  "price_per_sf_max": number | null,
  "price_per_unit_min": number | null,
  "price_per_unit_max": number | null,
  "cap_rate_min": number | null,
  "cap_rate_max": number | null,
  "rate_min": number | null,
  "rate_max": number | null,
  "residual_criteria": string | null  // anything in the query that ISN'T one of the fields above -- e.g. clear height, dock doors, power, proximity to something, recency of renovation. null if the whole query is covered by the fields above.
}

Rules:
- "40k SF" means building_sf around 40,000 -- since comps rarely match a number exactly, set building_sf_min to roughly 10% below and building_sf_max to roughly 10% above the stated figure, unless the query gives its own range.
- A bare number range like "10-18" that isn't clearly SF, price, or a rate belongs in residual_criteria as descriptive text (e.g. "10-18 ft clear height"), not forced into one of the numeric fields above.
- IMPORTANT: a query about lot size ("3/4 acre lot", "1-2 acre parcel") is describing the lot_sf field, which every property type has -- it is NOT, by itself, a request for property_type="land". Only set property_type="land" when the query explicitly asks for vacant, raw, or undeveloped land as the property type itself (e.g. "vacant land", "raw land parcel", "land for development"). A search for "a 3/4 acre lot" with no other context should set lot_sf_min/lot_sf_max and leave property_type null, matching industrial, retail, office, etc. alongside actual land listings.
- Only set fields the query actually implies. Leave everything else null.
- Return valid JSON only.
"""

RANK_SCHEMA_PROMPT = """\
You are ranking commercial real estate comps against a broker's search \
criteria that couldn't be expressed as a database filter (things like \
clear height, dock doors, power specs, proximity, condition -- whatever \
shows up in a flyer's freeform notes rather than a structured field).

Given the criteria and a list of candidate comps (id, address, and notes), \
return ONLY a JSON object (no prose, no markdown fences) with this shape:

{
  "matches": [
    {"id": string, "reason": string}  // one short sentence on why this comp satisfies the criteria
  ]
}

Rules:
- Only include comps that genuinely satisfy the criteria based on their notes. If a comp's notes don't mention the relevant detail at all, leave it out rather than guessing.
- Order matches best-fit first.
- Return valid JSON only.
"""


@dataclass
class ParsedQuery:
    deal_type: str | None = None
    property_type: str | None = None
    submarket: str | None = None
    zoning: str | None = None
    building_sf_min: float | None = None
    building_sf_max: float | None = None
    lot_sf_min: float | None = None
    lot_sf_max: float | None = None
    price_per_sf_min: float | None = None
    price_per_sf_max: float | None = None
    price_per_unit_min: float | None = None
    price_per_unit_max: float | None = None
    cap_rate_min: float | None = None
    cap_rate_max: float | None = None
    rate_min: float | None = None
    rate_max: float | None = None
    residual_criteria: str | None = None


@dataclass
class RankedMatch:
    comp_id: str
    reason: str


def _strip_markdown_fence(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n(.*)\n```", text, re.DOTALL)
    return match.group(1) if match else text


def _client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def parse_query(query: str) -> ParsedQuery:
    response = _client().messages.create(
        model=MODEL,
        max_tokens=800,
        messages=[
            {
                "role": "user",
                "content": f"{QUERY_SCHEMA_PROMPT}\n\nBroker's search: {query}",
            }
        ],
    )
    raw_text = "".join(block.text for block in response.content if block.type == "text")
    data = json.loads(_strip_markdown_fence(raw_text))
    return ParsedQuery(**{k: v for k, v in data.items() if k in ParsedQuery.__dataclass_fields__})


def rank_by_residual(criteria: str, candidates: list[dict]) -> list[RankedMatch]:
    if not candidates:
        return []
    response = _client().messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{RANK_SCHEMA_PROMPT}\n\nCriteria: {criteria}\n\n"
                    f"Candidates:\n{json.dumps(candidates)}"
                ),
            }
        ],
    )
    raw_text = "".join(block.text for block in response.content if block.type == "text")
    data = json.loads(_strip_markdown_fence(raw_text))
    return [RankedMatch(comp_id=m["id"], reason=m.get("reason", "")) for m in data.get("matches", [])]

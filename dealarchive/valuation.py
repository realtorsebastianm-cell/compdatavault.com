"""Paste-your-own-property valuation matcher.

The deferred follow-up to Ask AI (dealarchive/matching.py): instead of
searching for comps that fit a set of criteria, a broker describes a
property they're valuing in freeform text and gets back the comps in
their own vault that best support a value on it, plus a rough estimate
computed from those comps.

Two-stage, same shape as Ask AI:

1. The free-text property description gets parsed into a structured
   profile (property_type, submarket, zoning, building_sf, lot_sf) plus a
   `notes_summary` capturing whatever doesn't map to a column (condition,
   clear height, parking, whatever the broker mentioned).
2. Stage 1's structured fields narrow the broker's vault down to
   plausible comps via ordinary SQL (generous windows, since a valuation
   needs enough comps to average, not just the closest few). If there are
   candidates, a second LLM pass ranks them against notes_summary and
   explains the fit -- same as Ask AI's residual-criteria ranking.

The estimate itself is deliberately simple arithmetic (mean/low/high of
price-per-SF or rate across the top-ranked comps), not another LLM call --
an LLM shouldn't be the one doing the math on a number a broker might
actually rely on.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

import anthropic

from dealarchive.config import settings

MODEL = "claude-sonnet-4-5"

PROPERTY_SCHEMA_PROMPT = """\
You are turning a commercial real estate broker's freeform description of \
a property they're valuing into a structured profile for comparing \
against their comp database. Return ONLY a JSON object (no prose, no \
markdown fences) with this shape:

{
  "property_type": "office" | "industrial" | "retail" | "land" | "multifamily" | "other" | null,
  "submarket": string | null,
  "zoning": string | null,
  "building_sf": number | null,
  "lot_sf": number | null,
  "notes_summary": string | null  // condition, clear height, dock doors, parking, power, proximity, recency of renovation -- anything descriptive that isn't one of the fields above. null if there's nothing beyond the fields above.
}

Rules:
- Only set fields the description actually states or clearly implies. Leave everything else null.
- building_sf and lot_sf should be the property's own stated size, not a range -- this is a single subject property, not a search query.
- Return valid JSON only.
"""

RANK_SCHEMA_PROMPT = """\
You are ranking commercial real estate comps by how well they support a \
valuation of a subject property, based on physical/qualitative details \
that aren't in the structured comp fields (condition, clear height, dock \
doors, parking, power, proximity, recency of renovation, etc).

Given the subject property's notes and a list of candidate comps (id, \
address, and notes), return ONLY a JSON object (no prose, no markdown \
fences) with this shape:

{
  "matches": [
    {"id": string, "reason": string}  // one short sentence on why this comp is (or isn't clearly worse than any other) a good comparable
  ]
}

Rules:
- Include every candidate that isn't clearly a poor comparable based on its notes -- the goal is a usable comp set for a valuation, not just the single closest match. If a comp's notes don't mention anything relevant, that's not disqualifying on its own.
- Order matches best-fit first.
- Return valid JSON only.
"""


@dataclass
class PropertyProfile:
    property_type: str | None = None
    submarket: str | None = None
    zoning: str | None = None
    building_sf: float | None = None
    lot_sf: float | None = None
    notes_summary: str | None = None


@dataclass
class ValuationMatch:
    comp_id: str
    reason: str


def _strip_markdown_fence(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n(.*)\n```", text, re.DOTALL)
    return match.group(1) if match else text


def _client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def parse_property(description: str) -> PropertyProfile:
    response = _client().messages.create(
        model=MODEL,
        max_tokens=800,
        messages=[
            {
                "role": "user",
                "content": f"{PROPERTY_SCHEMA_PROMPT}\n\nProperty description: {description}",
            }
        ],
    )
    raw_text = "".join(block.text for block in response.content if block.type == "text")
    data = json.loads(_strip_markdown_fence(raw_text))
    return PropertyProfile(
        **{k: v for k, v in data.items() if k in PropertyProfile.__dataclass_fields__}
    )


def rank_for_valuation(notes_summary: str, candidates: list[dict]) -> list[ValuationMatch]:
    if not candidates:
        return []
    response = _client().messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{RANK_SCHEMA_PROMPT}\n\nSubject property notes: {notes_summary}\n\n"
                    f"Candidates:\n{json.dumps(candidates)}"
                ),
            }
        ],
    )
    raw_text = "".join(block.text for block in response.content if block.type == "text")
    data = json.loads(_strip_markdown_fence(raw_text))
    return [
        ValuationMatch(comp_id=m["id"], reason=m.get("reason", ""))
        for m in data.get("matches", [])
    ]

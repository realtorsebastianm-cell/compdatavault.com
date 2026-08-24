"""Flyer -> structured comp data, via Claude's vision/document input.

This is the core of the product: read a sale or lease flyer (PDF or image)
and return JSON matching one of the two comp schemas. Fields the model isn't
confident about are listed in `low_confidence_fields` instead of guessed.
"""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field

import anthropic

from dealarchive.config import settings

MODEL = "claude-sonnet-4-5"

_PDF_MEDIA_TYPE = "application/pdf"
_IMAGE_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

EXTRACTION_SCHEMA_PROMPT = """\
You are reading a commercial real estate flyer. Return ONLY a JSON object \
(no prose, no markdown fences) with this shape:

{
  "deal_type": "sale" | "lease",
  "address": string,
  "city": string | null,
  "state": string | null,
  "submarket": string | null,
  "property_type": "office" | "industrial" | "retail" | "land" | "multifamily" | "other",
  "building_sf": number | null,  // building/improvement square footage
  "lot_sf": number | null,  // land/lot square footage -- convert acres to SF (1 acre = 43,560 SF) if that's what's listed
  "zoning": string | null,  // e.g. "M-1", "I-2", "C-3" -- whatever's on the flyer, any property type
  "broker_name": string | null,
  "brokerage": string | null,
  "notes": string | null,

  // sale only, null if deal_type is "lease"
  "price": number | null,
  "cap_rate": number | null,
  "num_units": number | null,  // multifamily sale comps -- total unit count, if listed

  // lease only, null if deal_type is "sale"
  "rate": number | null,
  "rate_type": "per_sf_year" | "per_sf_month" | "flat_month" | null,
  "term_months": number | null,
  "expense_type": "nnn" | "gross" | "modified_gross" | "unknown" | null,

  "low_confidence_fields": string[]  // names of the fields above you're not confident about
}

Rules:
- deal_type is required: decide sale vs lease from context (asking price vs. asking rate, "for sale" vs "for lease", cap rate presence, etc).
- Never fabricate a number. If a field isn't on the flyer or you're unsure, set it null AND add its name to low_confidence_fields.
- building_sf and lot_sf are plain numbers (no commas, no "SF"/"acres" suffix). Land/lot size is frequently given in acres on flyers -- convert to square feet.
- price and rate are plain numbers (no "$", no commas).
- Return valid JSON only.
"""


@dataclass
class ExtractionResult:
    deal_type: str
    fields: dict = field(default_factory=dict)
    low_confidence_fields: list[str] = field(default_factory=list)


def _strip_markdown_fence(text: str) -> str:
    """Claude sometimes wraps its JSON in a ```json ... ``` fence despite
    being told not to; unwrap it if present."""
    match = re.search(r"```(?:json)?\s*\n(.*)\n```", text, re.DOTALL)
    return match.group(1) if match else text


def _media_type_for(filename: str, content_type: str | None) -> str:
    if content_type in _IMAGE_MEDIA_TYPES.values():
        return content_type
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _IMAGE_MEDIA_TYPES.get(suffix, "application/pdf")


def extract_flyer(content: bytes, filename: str, content_type: str | None) -> ExtractionResult:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    media_type = _media_type_for(filename, content_type)
    encoded = base64.standard_b64encode(content).decode("ascii")

    doc_block_type = "document" if media_type == _PDF_MEDIA_TYPE else "image"
    document_block = {
        "type": doc_block_type,
        "source": {"type": "base64", "media_type": media_type, "data": encoded},
    }

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[
            {
                "role": "user",
                "content": [
                    document_block,
                    {"type": "text", "text": EXTRACTION_SCHEMA_PROMPT},
                ],
            }
        ],
    )

    raw_text = "".join(block.text for block in response.content if block.type == "text")
    data = json.loads(_strip_markdown_fence(raw_text))

    deal_type = data.get("deal_type")
    if deal_type not in ("sale", "lease"):
        raise ValueError(f"Extraction returned unrecognized deal_type: {deal_type!r}")

    return ExtractionResult(
        deal_type=deal_type,
        fields=data,
        low_confidence_fields=data.get("low_confidence_fields") or [],
    )

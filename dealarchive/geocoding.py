"""Address -> (latitude, longitude), for the map view.

Uses the US Census Bureau's public geocoder rather than Google/Mapbox --
no API key, no billing, and every comp in this app is a US address
anyway. It's slower and less forgiving of messy input than a commercial
geocoder, so this is deliberately best-effort: a failed or ambiguous
lookup just leaves a comp's coordinates null rather than raising, since a
broker's flyer extraction succeeding shouldn't be held hostage to a
geocoding service being flaky.
"""
from __future__ import annotations

import httpx

CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
_TIMEOUT_SECONDS = 8.0


def geocode_address(address: str, city: str | None, state: str | None) -> tuple[float, float] | None:
    """Best-effort geocode. Returns (latitude, longitude) or None -- never
    raises, since callers run this inline during flyer ingestion and a
    geocoding hiccup shouldn't turn into a failed upload."""
    full_address = ", ".join(part for part in [address, city, state] if part)
    if not full_address.strip():
        return None

    try:
        response = httpx.get(
            CENSUS_GEOCODER_URL,
            params={
                "address": full_address,
                "benchmark": "Public_AR_Current",
                "format": "json",
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        matches = response.json().get("result", {}).get("addressMatches", [])
        if not matches:
            return None
        coordinates = matches[0]["coordinates"]
        return float(coordinates["y"]), float(coordinates["x"])
    except Exception:  # noqa: BLE001 -- geocoding is best-effort by design
        return None

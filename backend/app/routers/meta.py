import re

import httpx
from fastapi import APIRouter, HTTPException, status


router = APIRouter(prefix="/api/meta", tags=["meta"])

_ZIP_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \-]{1,18}[A-Za-z0-9]$")


def _normalize_country(country: str) -> str:
    return (country or "").strip().upper()


@router.get("/resolve-city")
def resolve_city(country: str, zip: str):
    """
    Resolve city name from (country, zip/postal code).
    Uses Zippopotam.us where supported.
    """
    country = _normalize_country(country)
    zip_clean = (zip or "").strip()
    if not country or len(country) != 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Country must be a 2-letter code (e.g. PL).",
        )
    if not zip_clean or len(zip_clean) < 2 or len(zip_clean) > 20 or not _ZIP_RE.match(zip_clean):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid ZIP / postal code format.",
        )

    url = f"https://api.zippopotam.us/{country}/{zip_clean}"
    try:
        resp = httpx.get(url, timeout=8.0)
        if resp.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ZIP / postal code not found for this country.",
            )
        resp.raise_for_status()
        data = resp.json()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to resolve city from ZIP code.",
        )

    places = data.get("places") or []
    if not places:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ZIP / postal code not found for this country.",
        )

    # Zippopotam returns a list; pick first (most zips map to a single place)
    city = (places[0].get("place name") or "").strip()
    state = (places[0].get("state") or "").strip()
    latitude = places[0].get("latitude")
    longitude = places[0].get("longitude")

    if not city:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ZIP / postal code not found for this country.",
        )

    return {
        "country": country,
        "zip": zip_clean,
        "city": city,
        "region": state or None,
        "latitude": latitude,
        "longitude": longitude,
        "source": "zippopotam",
    }


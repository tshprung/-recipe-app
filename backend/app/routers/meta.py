import re

import httpx
from fastapi import APIRouter, Request, HTTPException, status


router = APIRouter(prefix="/api/meta", tags=["meta"])

# IP geolocation: ip-api.com (free, no key; 45 req/min from same IP)
IP_GEO_URL = "http://ip-api.com/json/?fields=status,countryCode,regionName,city,zip"

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


@router.get("/geo")
def geo_from_ip(request: Request):
    """
    Guess country and city from the client's IP (e.g. for registration defaults).
    Uses ip-api.com; no auth required. Returns 2-letter country code, city, region, zip.
    """
    # Prefer X-Forwarded-For when behind a proxy (e.g. Cloudflare)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else None
    if not client_ip or client_ip in ("127.0.0.1", "::1"):
        # Localhost: return a safe default or skip external call
        return {
            "country_code": None,
            "city": None,
            "region": None,
            "zip": None,
            "source": "local",
        }
    try:
        # ip-api.com: /json/{ip} returns geo for that IP
        url = f"http://ip-api.com/json/{client_ip}"
        resp = httpx.get(
            url,
            params={"fields": "status,countryCode,regionName,city,zip", "lang": "en"},
            timeout=5.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {
            "country_code": None,
            "city": None,
            "region": None,
            "zip": None,
            "source": None,
        }
    if data.get("status") != "success":
        return {
            "country_code": None,
            "city": None,
            "region": None,
            "zip": None,
            "source": "ip-api",
        }
    return {
        "country_code": (data.get("countryCode") or "").strip().upper() or None,
        "city": (data.get("city") or "").strip() or None,
        "region": (data.get("regionName") or "").strip() or None,
        "zip": (data.get("zip") or "").strip() or None,
        "source": "ip-api",
    }


import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import httpx

logger = logging.getLogger(__name__)

CATEGORY_ICONS = {
    "Warzywa i owoce": "🥦",
    "Nabiał": "🧀",
    "Mięso i ryby": "🥩",
    "Przyprawy i sosy": "🫙",
    "Inne": "🛒",
}


def send_shopping_list_email(to_email: str, items: dict) -> None:
    """Send the categorized shopping list to the given email address via Resend.com."""
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured on the server.")

    lines = ["Shopping list", "=" * 30]
    for cat, ingredients in items.items():
        if ingredients:
            icon = CATEGORY_ICONS.get(cat, "")
            lines.append(f"\n{icon} {cat}:")
            for ing in ingredients:
                lines.append(f"  - {ing}")

    body = "\n".join(lines)

    payload = {
        "from": os.getenv("RESEND_FROM_EMAIL", "no-reply@example.com"),
        "to": [to_email],
        "subject": "Your shopping list",
        "text": body,
    }

    headers = {"Authorization": f"Bearer {api_key}"}
    resp = httpx.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=10.0)
    resp.raise_for_status()


def send_verification_email(to_email: str, token: str) -> None:
    """Send an email verification link using Resend.com."""
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured on the server.")

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    verify_link = f"{frontend_url.rstrip('/')}/verify?token={token}"

    payload = {
        "from": os.getenv("RESEND_FROM_EMAIL", "no-reply@example.com"),
        "to": [to_email],
        "subject": "Verify your email address",
        "html": (
            f"<p>Hi!</p>"
            f"<p>To start using the app, please verify your email address by clicking the link below:</p>"
            f'<p><a href="{verify_link}">{verify_link}</a></p>'
            f"<p>This link expires in 24 hours.</p>"
        ),
    }

    logger.info("Sending verification email to %s", to_email)
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = httpx.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=10.0)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        body = e.response.text
        logger.error(
            "Resend API error: status=%s body=%s",
            e.response.status_code,
            body[:500] if body else "(empty)",
        )
        if e.response.status_code == 401:
            raise RuntimeError("RESEND_API_KEY is invalid or expired. Check your Resend dashboard.") from e
        if e.response.status_code == 422:
            raise RuntimeError(
                "Resend rejected the email (e.g. RESEND_FROM_EMAIL not verified). Check Resend dashboard → Domains."
            ) from e
        raise RuntimeError(f"Resend API error {e.response.status_code}: {body[:200] if body else 'unknown'}") from e

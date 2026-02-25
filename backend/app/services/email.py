import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

CATEGORY_ICONS = {
    "Warzywa i owoce": "🥦",
    "Nabiał": "🧀",
    "Mięso i ryby": "🥩",
    "Przyprawy i sosy": "🫙",
    "Inne": "🛒",
}


def send_shopping_list_email(to_email: str, items: dict) -> None:
    """Send the categorized shopping list to the given email address.

    Requires SMTP_HOST, SMTP_USER, SMTP_PASSWORD env vars.
    Raises RuntimeError if not configured, or smtplib exceptions on failure.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM", smtp_user)

    if not all([smtp_host, smtp_user, smtp_password]):
        raise RuntimeError(
            "Email service not configured. "
            "Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD in your .env file."
        )

    lines = ["Lista zakupów", "=" * 30]
    for cat, ingredients in items.items():
        if ingredients:
            icon = CATEGORY_ICONS.get(cat, "")
            lines.append(f"\n{icon} {cat}:")
            for ing in ingredients:
                lines.append(f"  - {ing}")

    body = "\n".join(lines)

    msg = MIMEMultipart()
    msg["Subject"] = "Twoja lista zakupów"
    msg["From"] = from_email
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, to_email, msg.as_string())
